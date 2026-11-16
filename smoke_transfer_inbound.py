# -*- coding: utf-8 -*-
"""调拨入库（transferIn）提交报文 + 拆行对齐 Web/安卓端的冒烟测试。

对齐依据（Web 为真理源 + 17 份 HAR 提交实证 117 行明细）：
- 桌面/调拨入库/_inboundDialog_beauty.txt
  · initPage：addForm.transferType = a.transferType（列表行**原始数字**直传）、
              addForm.remark = a.remark；
              并给**每一行**注入 2 字段 select_LOCATION_OPTIONS
              = [{locationId: realInboundLocationNoId || inboundLocationId,
                  locationNo: realInboundLocationNo  || inboundLocation}]
  · locationOptionRemoteMethod（用户在该行库位框打字/搜索）→ $set 该行
    select_locationOptionLoading=true→false，并把 select_LOCATION_OPTIONS 置为
    findAllLocationValid 结果的 6 字段对象列表
  · changeStorg（选中下拉项）→ 只按 locationId 反查写回 realInboundLocationNo，**不改写 SLO**
  · splitRow（L383-407）→ 子行是 **13 字段白名单构造**（detailId/brand/brandId/brandName/
    partId/partCode/partName/shelfLocationNo/waitInboundQty/pickingLocationNo/salesPrice/
    priceIncreaseRate/splitRow=10041001），**不含** 库位/数量/SLO —— 干净空行
  · infoSave（入库）报文含 remark；tempStorage（暂存）报文**不含** remark
  · checkStatus 两处调用点均传 10041001
  · 提交闸门：至少一行 realInboundLocationNoId!=null 且 inboundQuantity 非 0
- HAR 全量核对结论（32 文件 / 17 份 transferIn 提交 / 117 行明细）：
  · select_LOCATION_OPTIONS 恒为**单元素列表**（长度分布 {1: 117}，从无 len>1）
  · 未改库位行 → 2 字段（65 行，且**无** select_locationOptionLoading 键）
  · 改过库位行 → 6 字段（52 行，且**带** select_locationOptionLoading 键）
  · 拆行子行实例：带 splitRow=10041001，键集为 13 白名单 + 库位/数量/SLO/loading
    （用户已填过；未填的干净子行不出现该行样本）
- 安卓端 commit 0341b95（transferType 改数字 + 补 remark）、85c6024（select_locationOptionLoading）、
  TransferManagement.vue splitRow / mergeSplitRow / maxQtyForRow / qtyValidate / validateAllGroups

注意：本脚本不实例化 Tk，只对纯逻辑方法做绑定调用（Tk 控件用鸭子类型桩替代）。
"""
import sys
import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"

import transfer_manager as tm

PASS, FAIL = [], []


def check(name, cond, extra=''):
    if cond:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL  %s  %s" % (name, extra))


class Stub:
    """只为绑定纯逻辑方法用的空壳（这两个方法只依赖 self.original_data / 入参）"""
    def __init__(self, original_data):
        self.original_data = original_data
        self.transfer_type_mapping = {"平价调拨": 47171001, "加价调拨": 47171002}
        self.transfer_status_mapping = {"待签收": 47161008, "待上架": 47161009, "已入库": 47161006}


class FakeTree:
    """详情树桩：只提供 selection/focus/selection_set/see"""
    def __init__(self, iid=None):
        self._sel = (iid,) if iid else ()

    def selection(self):
        return self._sel

    def focus(self):
        return self._sel[0] if self._sel else ""

    def selection_set(self, iid):
        self._sel = (iid,)

    def see(self, iid):
        pass


class SplitStub:
    """拆行/合并/校验方法的桩：用真实 dict 承载缓存，_rerender_detail 打桩计数。"""
    def __init__(self, rows, status="待上架", selected_idx=0):
        self.transfer_detail_cache = {777: rows}
        self._detail_transfer_id = 777
        self._detail_status = status
        self._detail_log_data = None
        self.rendered = 0
        self.detail_item_ids = ["%s__%d" % (r.get("detailId"), i + 1) for i, r in enumerate(rows)]
        sel_iid = self.detail_item_ids[selected_idx] if rows else None
        self.transfer_detail_tree = FakeTree(sel_iid)

    def _rerender_detail(self):
        self.rendered += 1
        # 模拟重绘：iid 列表随行数重建（拆行/合并后行数变化）
        self.detail_item_ids = ["%s__%d" % (r.get("detailId"), i + 1)
                                for i, r in enumerate(self.transfer_detail_cache[777])]

    def select(self, idx):
        self.transfer_detail_tree = FakeTree(self.detail_item_ids[idx])


# split_detail_row / merge_detail_row 内部会互相调用同类方法，桩上需补绑真实实现
# （这些方法只依赖桩已具备的属性 + 被覆盖的 _rerender_detail，不触碰 Tk 控件本体）
for _name in ('_selected_detail_index', 'split_detail_row',
              'merge_detail_row', 'validate_detail_groups', 'has_valid_inbound_row'):
    setattr(SplitStub, _name, getattr(tm.TransferProcessPage, _name))
# staticmethod 需保持静态属性，否则会被当成实例方法多收一个 self
SplitStub._is_split_row = staticmethod(getattr(tm.TransferProcessPage, '_is_split_row'))


SPLIT_WHITELIST = {
    "detailId", "brand", "brandId", "brandName", "partId", "partCode", "partName",
    "shelfLocationNo", "waitInboundQty", "pickingLocationNo", "salesPrice",
    "priceIncreaseRate", "splitRow",
}


def main():
    print("\n[1] parse_and_convert_json：文本转展示、原始数字另存 _transferTypeRaw")
    s = Stub([])
    raw = {"data": {"rows": [
        {"id": 1025, "transferType": 47171002, "transferStatus": 47161009,
         "remark": None, "recordVersion": 4},
        {"id": 1026, "transferType": 47171001, "transferStatus": 47161006,
         "remark": "整箱调拨", "recordVersion": 9},
    ]}}
    rows = tm.TransferProcessPage.parse_and_convert_json(s, raw)
    check("transferType 展示值转中文", rows[0]["transferType"] == "加价调拨", repr(rows[0]["transferType"]))
    check("★ 原始数字另存 _transferTypeRaw=47171002", rows[0]["_transferTypeRaw"] == 47171002,
          repr(rows[0].get("_transferTypeRaw")))
    check("transferStatus 展示值转中文", rows[1]["transferStatus"] == "已入库")
    check("remark 原样保留", rows[1]["remark"] == "整箱调拨" and rows[0]["remark"] is None)
    s.original_data = rows

    print("\n[2] record_field：提交取值用原始字段，None 按调用方 default 归一")
    check("★ transferType 取原值（数字，非界面文本）",
          tm.TransferProcessPage.record_field(s, 1025, "_transferTypeRaw") == 47171002,
          repr(tm.TransferProcessPage.record_field(s, 1025, "_transferTypeRaw")))
    check("默认 default='' → remark 为空时返回 ''",
          tm.TransferProcessPage.record_field(s, 1025, "remark") == "",
          repr(tm.TransferProcessPage.record_field(s, 1025, "remark")))
    check("★ 显式 default=None → 保留 None（入库侧用法，对齐 Web 的 null）",
          tm.TransferProcessPage.record_field(s, 1025, "remark", None) is None,
          repr(tm.TransferProcessPage.record_field(s, 1025, "remark", None)))
    check("remark 有值则原样返回",
          tm.TransferProcessPage.record_field(s, 1026, "remark") == "整箱调拨")
    check("recordVersion 取原值 4",
          tm.TransferProcessPage.record_field(s, 1025, "recordVersion") == 4)
    check("不存在的 id 返回默认值 ''",
          tm.TransferProcessPage.record_field(s, 9999, "remark") == "")
    check("不存在的 id + default=None 返回 None",
          tm.TransferProcessPage.record_field(s, 9999, "remark", None) is None)

    print("\n[3] prepare_detail_data_for_submission：SLO 形态 / 深拷贝 / 不提前退出")
    detail = [
        # ① 载入即有 2 字段 SLO（库位齐全）
        {"id": 1, "realInboundLocationNo": "A-01", "realInboundLocationNoId": 11,
         "select_LOCATION_OPTIONS": [{"locationNo": "A-01", "locationId": 11}]},
        # ② 无 SLO，但 realInboundLocationNo 有值
        {"id": 2, "realInboundLocationNo": "B-02", "realInboundLocationNoId": 22},
        # ③ 无 SLO 且库位为空（旧实现会在此 return，导致 ④ 漏处理）—— 关键回归
        {"id": 3, "realInboundLocationNo": "", "realInboundLocationNoId": None},
        # ④ 用户搜索过的行：6 字段完整对象 + select_locationOptionLoading=False
        {"id": 4, "realInboundLocationNo": "C-03", "realInboundLocationNoId": 33,
         "select_LOCATION_OPTIONS": [{"locationNo": "C-03", "locationId": 33,
                                      "locationType": 1, "warehouseId": 11,
                                      "enabledStatus": 1, "isValid": True}],
         "select_locationOptionLoading": False},
        # ⑤ 有 inboundLocation 兜底（Web 三元判断的 fallback 分支）
        {"id": 5, "realInboundLocationNo": None, "inboundLocation": "D-04", "inboundLocationId": 44},
    ]
    snapshot = repr(detail)
    out = tm.TransferProcessPage.prepare_detail_data_for_submission(s, detail)
    check("返回行数不变（无提前 return）", len(out) == 5, "len=%d" % len(out))
    check("★ 不污染入参缓存（返回深拷贝，原列表未被写入 SLO）", repr(detail) == snapshot)
    check("★ 第③行（库位空）也被处理，且有 SLO 键", "select_LOCATION_OPTIONS" in out[2],
          repr(out[2].get("select_LOCATION_OPTIONS")))
    check("★ 第⑤行（仅 inboundLocation）也生成 SLO",
          out[4]["select_LOCATION_OPTIONS"][0]["locationNo"] == "D-04",
          repr(out[4].get("select_LOCATION_OPTIONS")))
    check("第②行 SLO 补为 2 字段且值正确",
          out[1]["select_LOCATION_OPTIONS"] == [{"locationNo": "B-02", "locationId": 22}],
          repr(out[1]["select_LOCATION_OPTIONS"]))
    check("★ 第④行 6 字段对象原样保留（不被降级为 2 字段）",
          len(out[3]["select_LOCATION_OPTIONS"][0]) == 6,
          repr(out[3]["select_LOCATION_OPTIONS"][0]))
    check("★ select_locationOptionLoading 未被剥离", out[3].get("select_locationOptionLoading") is False,
          repr(out[3].get("select_locationOptionLoading")))
    check("未搜索过的行仍无该键", "select_locationOptionLoading" not in out[0])
    check("已存在 SLO 的行不被重复包裹（仍是单元素列表）",
          isinstance(out[0]["select_LOCATION_OPTIONS"], list) and len(out[0]["select_LOCATION_OPTIONS"]) == 1)

    print("\n[3b] prepare：拆行子行的 splitRow / SLO 处理")
    split_cases = [
        # 普通行：splitRow 必须被剔除
        {"detailId": 9001, "realInboundLocationNo": "A-01", "realInboundLocationNoId": 11,
         "splitRow": "10041001" if False else 12345},
        # 拆行子行（未填库位）：保留 splitRow=10041001、剥离 _isSplit、整键不发 SLO
        {"detailId": 9002, "splitRow": 10041001, "_isSplit": True,
         "realInboundLocationNo": "", "realInboundLocationNoId": None},
        # 拆行子行（已填库位 + 用户搜索过）：保留 splitRow + 6 字段 SLO
        {"detailId": 9003, "splitRow": "10041001", "_isSplit": True,
         "realInboundLocationNo": "E-09", "realInboundLocationNoId": 99,
         "select_LOCATION_OPTIONS": [{"locationNo": "E-09", "locationId": 99,
                                      "locationType": 1, "warehouseId": 11,
                                      "enabledStatus": 1, "isValid": True}],
         "select_locationOptionLoading": False},
    ]
    sout = tm.TransferProcessPage.prepare_detail_data_for_submission(s, split_cases)
    check("普通行不带 splitRow", "splitRow" not in sout[0], repr(sout[0].get("splitRow")))
    check("★ 未填库位的拆行子行：splitRow=10041001 且【无】SLO 键",
          sout[1].get("splitRow") == 10041001 and "select_LOCATION_OPTIONS" not in sout[1],
          repr(sout[1]))
    check("★ 拆行子行 _isSplit 内部字段被剥离", "_isSplit" not in sout[1] and "_isSplit" not in sout[2])
    check("★ 已填库位的拆行子行：splitRow 保留 + 6 字段 SLO 原样",
          sout[2].get("splitRow") == 10041001 and len(sout[2]["select_LOCATION_OPTIONS"][0]) == 6,
          repr(sout[2].get("select_LOCATION_OPTIONS")))
    # 幂等：重复调用结果一致（splitRow 是持久标记，_isSplit 已被剥离）
    out2 = tm.TransferProcessPage.prepare_detail_data_for_submission(s, sout)
    check("★ prepare 幂等（重复调用不退化：子行 SLO 仍缺失、splitRow 仍保留）",
          "select_LOCATION_OPTIONS" not in out2[1] and out2[1].get("splitRow") == 10041001 and "_isSplit" not in out2[1],
          repr(out2[1]))

    print("\n[4] split_detail_row / merge_detail_row：13 字段白名单 + 触发条件")
    base_rows = [
        {"detailId": 501, "brand": 1, "brandId": 1, "brandName": "福耀玻璃", "partId": 53891,
         "partCode": "GLW15526SGTN", "partName": "前挡", "shelfLocationNo": "C1-015",
         "waitInboundQty": 5, "pickingLocationNo": "A1-103", "salesPrice": 301.75,
         "priceIncreaseRate": 1.1, "outboundQuantity": 5, "remarks": "送货",
         "realInboundLocationNo": "C1-015", "realInboundLocationNoId": 14846,
         "inboundQuantity": 1},
    ]
    st = SplitStub([dict(r) for r in base_rows])
    tm.TransferProcessPage.split_detail_row(st)
    rows = st.transfer_detail_cache[777]
    check("拆行后行数 +1", len(rows) == 2, "len=%d" % len(rows))
    child = rows[1]
    check("★ 子行落在父行之后且共享 detailId", child.get("detailId") == 501 and rows[0].get("detailId") == 501)
    check("★ 子行键集 = Web 13 字段白名单 + 内部 _isSplit",
          set(child.keys()) == SPLIT_WHITELIST | {"_isSplit"}, repr(sorted(child.keys())))
    check("★ 子行不含 库位/数量/SLO/loading（干净空行）",
          not any(k in child for k in ("realInboundLocationNo", "realInboundLocationNoId",
                                       "inboundQuantity", "select_LOCATION_OPTIONS",
                                       "select_locationOptionLoading", "outboundQuantity",
                                       "remarks")),
          repr(sorted(child.keys())))
    check("★ 子行 splitRow=10041001", child.get("splitRow") == 10041001)
    check("拆行后触发重绘", st.rendered == 1)

    # 待入库 < 2 → 不拆
    st2 = SplitStub([{"detailId": 502, "waitInboundQty": 1, "inboundQuantity": 0, "outboundQuantity": 1}])
    tm.TransferProcessPage.split_detail_row(st2)
    check("★ 待入库<2 不拆行（对齐 Web disabled: waitInboundQty<2）",
          len(st2.transfer_detail_cache[777]) == 1, "len=%d" % len(st2.transfer_detail_cache[777]))

    # 可分配数量已用完 → 不拆
    st3 = SplitStub([{"detailId": 503, "waitInboundQty": 3, "inboundQuantity": 3, "outboundQuantity": 3}])
    tm.TransferProcessPage.split_detail_row(st3)
    check("★ 组内已分配满（used>=wait）不拆行",
          len(st3.transfer_detail_cache[777]) == 1, "len=%d" % len(st3.transfer_detail_cache[777]))

    # 非待上架 → 不拆
    st4 = SplitStub([dict(base_rows[0])], status="待签收")
    tm.TransferProcessPage.split_detail_row(st4)
    check("★ 非待上架状态不拆行", len(st4.transfer_detail_cache[777]) == 1)

    # 合并：子行数量并回主行
    st5 = SplitStub([dict(base_rows[0])])
    tm.TransferProcessPage.split_detail_row(st5)
    st5.transfer_detail_cache[777][1]["inboundQuantity"] = 2
    st5.select(1)
    tm.TransferProcessPage.merge_detail_row(st5)
    merged = st5.transfer_detail_cache[777]
    check("合并后行数 -1", len(merged) == 1, "len=%d" % len(merged))
    check("★ 子行数量已并回主行（1+2=3）", merged[0].get("inboundQuantity") == 3,
          repr(merged[0].get("inboundQuantity")))

    # 合并主行 → 拒绝
    st6 = SplitStub([dict(base_rows[0])])
    tm.TransferProcessPage.merge_detail_row(st6)
    check("★ 选中非拆行子行时不合并", len(st6.transfer_detail_cache[777]) == 1)

    print("\n[5] validate_detail_groups / has_valid_inbound_row：提交闸门")
    v1 = SplitStub([
        {"detailId": 601, "partCode": "P1", "waitInboundQty": 5, "inboundQuantity": 3},
        {"detailId": 601, "partCode": "P1", "waitInboundQty": 5, "inboundQuantity": 2, "_isSplit": True},
    ])
    check("★ 组内合计 == 待入库 → 通过", tm.TransferProcessPage.validate_detail_groups(v1) == "",
          repr(tm.TransferProcessPage.validate_detail_groups(v1)))
    v2 = SplitStub([
        {"detailId": 602, "partCode": "P2", "waitInboundQty": 5, "inboundQuantity": 4},
        {"detailId": 602, "partCode": "P2", "waitInboundQty": 5, "inboundQuantity": 2, "_isSplit": True},
    ])
    err = tm.TransferProcessPage.validate_detail_groups(v2)
    check("★ 拆行后组内合计 6 > 待入库 5 → 报错", bool(err) and "超过待入库" in err, repr(err))

    g1 = SplitStub([{"detailId": 603, "realInboundLocationNoId": None, "inboundQuantity": 0}])
    check("★ 无任何有效行 → 闸门失败", tm.TransferProcessPage.has_valid_inbound_row(g1) is False)
    g2 = SplitStub([{"detailId": 604, "realInboundLocationNoId": 14845, "inboundQuantity": 2}])
    check("★ 有一行库位+数量 → 闸门通过", tm.TransferProcessPage.has_valid_inbound_row(g2) is True)
    g3 = SplitStub([{"detailId": 605, "realInboundLocationNoId": None, "inboundLocationId": 7,
                     "inboundQuantity": 1}])
    check("★ inboundLocationId 兜底也算有效库位（对齐 Web 载入归一）",
          tm.TransferProcessPage.has_valid_inbound_row(g3) is True)
    g4 = SplitStub([{"detailId": 606, "realInboundLocationNoId": 9, "inboundQuantity": 0}])
    check("★ 有库位但数量为 0 → 闸门失败", tm.TransferProcessPage.has_valid_inbound_row(g4) is False)

    print("\n[6] 提交报文键集合（源码级断言，按活代码函数段提取，避开被注释的旧版本）")
    src = open(tm.__file__.replace('.pyc', '.py'), encoding='utf-8').read()

    def extract_func(source, name):
        """提取活代码 `    def name(self):` 到下一个类成员/顶层 def 之间的源码段"""
        lines = source.splitlines()
        start = None
        for i, ln in enumerate(lines):
            if ln.startswith('    def %s(self' % name):
                start = i
                break
        if start is None:
            return ''
        out = []
        for ln in lines[start + 1:]:
            if ln.startswith('    def ') or (ln and not ln[0].isspace()):
                break
            out.append(ln)
        return '\n'.join(out)

    seg_temp = extract_func(src, 'temp_storage')
    seg_in = extract_func(src, 'transfer_in')
    check("能提取到两个活代码函数段", len(seg_temp) > 500 and len(seg_in) > 500,
          "temp=%d in=%d" % (len(seg_temp), len(seg_in)))

    # tempStorage：对齐 Web —— 不含 remark
    check("★ 暂存(tempStorage) 报文【不含】remark（对齐 Web，HAR 4/4 无该键）",
          '"remark"' not in seg_temp,
          [ln.strip() for ln in seg_temp.splitlines() if 'remark' in ln])
    check("暂存 transferType 用 _transferTypeRaw 兜底",
          'record_field(transfer_id, "_transferTypeRaw") or transfer_type' in seg_temp)
    check("暂存 checkStatus=10041001", '"checkStatus": 10041001' in seg_temp)
    check("★ 暂存提交前调用组内校验 + 有效行闸门",
          'validate_detail_groups(transfer_id)' in seg_temp and 'has_valid_inbound_row(transfer_id)' in seg_temp)

    # transferInbound：对齐 Web —— 含 remark，且保留 null 语义
    check("★ 入库(transferInbound) 报文【含】remark（对齐 Web，HAR 8/8 有该键）",
          '"remark": self.record_field(transfer_id, "remark", None)' in seg_in,
          [ln.strip() for ln in seg_in.splitlines() if 'remark' in ln])
    check("★ 入库 remark 用 default=None 保留 null 语义（Web 取不到值发 null，非 \"\"）",
          'record_field(transfer_id, "remark", None)' in seg_in)
    check("入库 transferType 用 _transferTypeRaw 兜底",
          'record_field(transfer_id, "_transferTypeRaw") or transfer_type' in seg_in)
    check("入库 checkStatus=10041001", '"checkStatus": 10041001' in seg_in)
    check("★ 入库提交前调用组内校验 + 有效行闸门",
          'validate_detail_groups(transfer_id)' in seg_in and 'has_valid_inbound_row(transfer_id)' in seg_in)
    check("★ 入库不再要求「每一行都有库位」（改为 Web/安卓端的「有数量必须有库位」）",
          'empty_location_items' not in seg_in and 'missing_loc_rows' in seg_in)

    print("\n" + "=" * 60)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  -", f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

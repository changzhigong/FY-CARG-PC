# -*- coding: utf-8 -*-
"""调拨入库「拆行」UI 级冒烟测试（真实 Tk Treeview，不出网）。

覆盖：
1. display_detail_data 在新增「拆」列后正常渲染；拆行子行带 splitrow 标签与「拆」标记
2. split_detail_row 走真实 Tk 路径：缓存插行 → 重绘 → 树行数变化，编辑控件数量同步
3. on_quantity_change 组内上限收敛（拆行合计 ≤ waitInboundQty）
4. merge_detail_row 走真实 Tk 路径
5. update_split_buttons 仅待上架可用

环境：managed python 3.13.12 无 tkinter，须用系统 Python312。
"""
import sys
import tkinter as tk

import transfer_manager as tm

# 屏蔽所有模态弹窗（否则会阻塞）
_MSGS = []
tm.messagebox.showinfo = lambda *a, **k: _MSGS.append(("info", a))
tm.messagebox.showerror = lambda *a, **k: _MSGS.append(("error", a))
tm.messagebox.showwarning = lambda *a, **k: _MSGS.append(("warn", a))
tm.messagebox.askyesno = lambda *a, **k: True

# 建表阶段跳过出网逻辑
tm.TransferProcessPage.refresh_table = lambda self: None
tm.TransferProcessPage.load_onshelf_persons = lambda self: None

PASS, FAIL = [], []


def check(name, cond, extra=''):
    if cond:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL  %s  %s" % (name, extra))


class FakeSession:
    def get(self, *a, **k):
        raise AssertionError("UI 冒烟不应发起网络请求")


class FakeController:
    session = FakeSession()
    options = {"郑州库": {}, "商丘库": {}}
    root = None

    def check_login_status(self, response):
        return False

    def after(self, ms, fn, *a):
        # 立即执行（等价于主线程回调）
        return fn(*a) if a else fn()

    def show_status(self, *a, **k):
        pass

    def hide_status(self, *a, **k):
        pass


def make_page():
    root = tk.Tk()
    root.withdraw()
    page = tm.TransferProcessPage(root, FakeController())
    page.original_data = [{"id": 777, "moveWarehouseId": 11}]
    return root, page


def rows_fixture():
    return [
        {"detailId": 501, "brand": 1, "brandId": 1, "brandName": "福耀玻璃", "partId": 53891,
         "partCode": "GLW15526SGTN", "partName": "前挡", "shelfLocationNo": "C1-015",
         "waitInboundQty": 5, "pickingLocationNo": "A1-103", "salesPrice": 301.75,
         "priceIncreaseRate": 1.1, "outboundQuantity": 5, "remarks": "送货",
         "realInboundLocationNo": "C1-015", "realInboundLocationNoId": 14846,
         "inboundQuantity": 1},
        {"detailId": 502, "brand": 1, "brandId": 1, "brandName": "福耀玻璃", "partId": 53892,
         "partCode": "CLW24446NCLN", "partName": "后挡", "shelfLocationNo": "E2-006",
         "waitInboundQty": 4, "pickingLocationNo": "E2-002", "salesPrice": 190.9,
         "priceIncreaseRate": 1.1, "outboundQuantity": 4, "remarks": "",
         "realInboundLocationNo": "E1-009", "realInboundLocationNoId": 15400,
         "inboundQuantity": 0},
    ]


def main():
    print("\n[UI-1] display_detail_data：新列 / 拆行标记 / 唯一 iid")
    root, page = make_page()
    page.transfer_detail_cache[777] = rows_fixture()
    page.display_detail_data(page.transfer_detail_cache[777], None, "待上架", 777)

    kids = page.transfer_detail_tree.get_children()
    check("树行数 = 明细 2 行 + 汇总 1 行", len(kids) == 3, "len=%d" % len(kids))
    check("★ iid 唯一且不等于 detailId（避免同 detailId 多行冲突）",
          str(page.transfer_detail_tree.item(kids[0], 'values')[0]) == "1" and kids[0] != "501",
          repr(kids))
    check("普通行「拆」列为空", page.transfer_detail_tree.item(kids[0], 'values')[11] == "",
          repr(page.transfer_detail_tree.item(kids[0], 'values')[11]))
    check("汇总行末列为空", page.transfer_detail_tree.item(kids[-1], 'values')[0] == "合计")
    check("★ 编辑控件数量与明细行数一致",
          len(page.location_entries) == 2 and len(page.quantity_spins) == 2,
          "loc=%d spin=%d" % (len(page.location_entries), len(page.quantity_spins)))

    print("\n[UI-2] split_detail_row：真实 Tk 路径（插行→重绘）")
    page.transfer_detail_tree.selection_set(kids[0])
    before = len(page.transfer_detail_cache[777])
    page.split_detail_row()
    rows = page.transfer_detail_cache[777]
    kids2 = page.transfer_detail_tree.get_children()
    check("★ 缓存插行 +1", len(rows) == before + 1, "len=%d" % len(rows))
    check("★ 子行 splitRow=10041001", rows[1].get("splitRow") == 10041001)
    check("★ 重绘后树行数 = 明细 3 + 汇总 1", len(kids2) == 4, "len=%d" % len(kids2))
    check("★ 重绘后编辑控件 3 套", len(page.location_entries) == 3 and len(page.quantity_spins) == 3,
          "loc=%d spin=%d" % (len(page.location_entries), len(page.quantity_spins)))
    check("★ 子行「拆」列渲染为「拆」",
          page.transfer_detail_tree.item(kids2[1], 'values')[11] == "拆",
          repr(page.transfer_detail_tree.item(kids2[1], 'values')[11]))
    check("★ 子行带 splitrow 标签",
          "splitrow" in page.transfer_detail_tree.item(kids2[1], 'tags'),
          repr(page.transfer_detail_tree.item(kids2[1], 'tags')))

    print("\n[UI-3] on_quantity_change：组内上限收敛")
    # 主行已填 4，待入库 5 → 子行最多 1
    page.transfer_detail_cache[777][0]["inboundQuantity"] = 4
    _MSGS.clear()
    page.on_quantity_change(1, 777)
    page.quantity_spins[1].delete(0, tk.END)
    page.quantity_spins[1].insert(0, "3")
    page.on_quantity_change(1, 777)
    check("★ 子行超上限被收敛为 1（5-4）",
          page.transfer_detail_cache[777][1].get("inboundQuantity") == 1,
          repr(page.transfer_detail_cache[777][1].get("inboundQuantity")))
    check("★ 收敛时给出提示", any(m[0] == "warn" for m in _MSGS), repr(_MSGS))

    _MSGS.clear()
    page.quantity_spins[0].delete(0, tk.END)
    page.quantity_spins[0].insert(0, "5")
    page.on_quantity_change(0, 777)
    # 子行已占 1，主行最多只能 4（组内合计不得超过 waitInboundQty=5）
    check("★ 主行受组内约束收敛为 4（5 - 子行 1）",
          page.transfer_detail_cache[777][0].get("inboundQuantity") == 4,
          repr(page.transfer_detail_cache[777][0].get("inboundQuantity")))
    check("★ 组内合计恰为待入库 5",
          sum(int(r.get("inboundQuantity") or 0) for r in page.transfer_detail_cache[777]) == 5,
          repr([r.get("inboundQuantity") for r in page.transfer_detail_cache[777]]))

    print("\n[UI-4] merge_detail_row：真实 Tk 路径")
    page.transfer_detail_cache[777][1]["inboundQuantity"] = 2
    kids3 = page.transfer_detail_tree.get_children()
    page.transfer_detail_tree.selection_set(kids3[1])
    page.merge_detail_row()
    rows2 = page.transfer_detail_cache[777]
    kids4 = page.transfer_detail_tree.get_children()
    check("★ 合并后缓存行数 -1", len(rows2) == 2, "len=%d" % len(rows2))
    check("★ 合并后树行数 = 明细 2 + 汇总 1", len(kids4) == 3, "len=%d" % len(kids4))
    check("★ 子行数量并回主行（5+2 收敛到 wait=5）",
          rows2[0].get("inboundQuantity") == 5, repr(rows2[0].get("inboundQuantity")))

    print("\n[UI-5] update_split_buttons：仅待上架可用")
    page.display_detail_data(rows_fixture(), None, "待签收", 777)
    check("★ 待签收 → 拆行/合并按钮禁用",
          str(page.split_row_btn.cget("state")) == "disabled"
          and str(page.merge_row_btn.cget("state")) == "disabled",
          "%s / %s" % (page.split_row_btn.cget("state"), page.merge_row_btn.cget("state")))
    page.display_detail_data(rows_fixture(), None, "待上架", 777)
    check("★ 待上架 → 拆行/合并按钮启用",
          str(page.split_row_btn.cget("state")) == "normal"
          and str(page.merge_row_btn.cget("state")) == "normal",
          "%s / %s" % (page.split_row_btn.cget("state"), page.merge_row_btn.cget("state")))

    # 整单提交报文（不含 remark / 含拆行 splitRow）——直接看 prepare 结果
    print("\n[UI-6] prepare 后的明细报文形态")
    page.transfer_detail_cache[777][1] = dict(page.transfer_detail_cache[777][1])
    page.transfer_detail_cache[777].insert(1, {"detailId": 501, "splitRow": 10041001, "_isSplit": True,
                                              "partCode": "GLW15526SGTN", "waitInboundQty": 5})
    payload = tm.TransferProcessPage.prepare_detail_data_for_submission(page, page.transfer_detail_cache[777])
    check("★ 未填库位的拆行子行无 SLO 键", "select_LOCATION_OPTIONS" not in payload[1], repr(payload[1]))
    check("★ 普通行有 2 字段 SLO", len(payload[0].get("select_LOCATION_OPTIONS", [])) == 1
          and sorted(payload[0]["select_LOCATION_OPTIONS"][0].keys()) == ["locationId", "locationNo"],
          repr(payload[0].get("select_LOCATION_OPTIONS")))

    print("\n[UI-7] on_location_change：改位 → 6 字段单对象 + loading 标记（且不再二次请求）")
    root2, page2 = make_page()
    page2.transfer_detail_cache[777] = rows_fixture()
    page2.display_detail_data(page2.transfer_detail_cache[777], None, "待上架", 777)
    six = {"enabledStatus": 10031001, "isValid": 10011001, "locationId": 14583,
           "locationNo": "B1-088", "locationType": 90041005, "warehouseId": 11}
    # FakeSession 一旦被请求就抛异常 → 逆向证明此处不再重复 findAllLocationValid
    page2.on_location_change(0, 777, "B1-088", {"realInboundLocationNoId": 14583, "other_data": [six]})
    row = page2.transfer_detail_cache[777][0]
    slo = row.get("select_LOCATION_OPTIONS")
    check("★ 改位后 SLO = 单元素 6 字段对象（不再塞整个匹配列表）",
          isinstance(slo, list) and len(slo) == 1 and len(slo[0]) == 6 and slo[0]["locationNo"] == "B1-088",
          repr(slo))
    check("★ 改位行挂 select_locationOptionLoading=False",
          row.get("select_locationOptionLoading") is False, repr(row.get("select_locationOptionLoading")))
    check("★ 改位后 realInboundLocationNo / Id 已写回",
          row.get("realInboundLocationNo") == "B1-088" and row.get("realInboundLocationNoId") == 14583,
          repr((row.get("realInboundLocationNo"), row.get("realInboundLocationNoId"))))
    check("★ Treeview 第 7 列同步显示新库位",
          page2.transfer_detail_tree.item(page2.detail_item_ids[0], 'values')[6] == "B1-088",
          repr(page2.transfer_detail_tree.item(page2.detail_item_ids[0], 'values')[6]))
    # 改位行经 prepare 后仍保留 6 字段
    out_row = tm.TransferProcessPage.prepare_detail_data_for_submission(
        page2, [page2.transfer_detail_cache[777][0]])[0]
    check("★ 改位行经 prepare 后仍为 6 字段（不降级）",
          len(out_row["select_LOCATION_OPTIONS"][0]) == 6, repr(out_row["select_LOCATION_OPTIONS"]))
    # 未改位的行仍是 2 字段
    out_row2 = tm.TransferProcessPage.prepare_detail_data_for_submission(
        page2, [page2.transfer_detail_cache[777][1]])[0]
    check("★ 未改位行进 prepare 后为 2 字段",
          sorted(out_row2["select_LOCATION_OPTIONS"][0].keys()) == ["locationId", "locationNo"]
          and "select_locationOptionLoading" not in out_row2,
          repr(out_row2["select_LOCATION_OPTIONS"]))
    root2.destroy()

    root.destroy()

    print("\n" + "=" * 60)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  -", f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

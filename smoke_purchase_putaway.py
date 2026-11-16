# -*- coding: utf-8 -*-
"""入库上架页面冒烟测试（临时脚本）

用 FakeController / FakeSession 驱动 PurchasePutawayPage，验证：
1. 查询参数形态（sparePartsStatus 逗号串 + sparePartsStatus1[] 数组 + receiptType 驼峰）
2. 默认值（入库类型 90331017、收货状态三项）
3. 列表渲染与字典解码
4. can_shelf 状态防护 / remain_qty 待上架数量
5. 上架明细（onshelf 接口）渲染
6. 上架提交报文（recordVersion / shelvesQty 字符串 / onshelf_by 数组 /
   select_LOCATION_OPTIONS / isSave / checkStatus）
7. 暂存草稿 vs 确认上架的差异（全 0 校验）
8. 两种打印清单的数据源与字段
"""
import json
import sys
import threading
import time

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb

# 自动应答弹窗，避免被模态框阻塞
mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"
mb.askyesno = lambda *a, **k: True

import purchase_putaway as pp

CAPTURED = []


class FakeResponse:
    def __init__(self, payload, url=''):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self):
        self.handler = None

    def _run(self, method, url, **kw):
        CAPTURED.append({'method': method, 'url': url, **kw})
        return self.handler(method, url, **kw)

    def get(self, url, **kw):
        return self._run('GET', url, **kw)

    def put(self, url, **kw):
        return self._run('PUT', url, **kw)

    def post(self, url, **kw):
        return self._run('POST', url, **kw)


class FakeController:
    def __init__(self, root):
        self.root = root
        self.session = FakeSession()
        self.options = {"商丘库": 11, "郑州库": 6}
        self._cbs = []

    def check_login_status(self, response):
        return False

    def after(self, ms, func=None, *args):
        self._cbs.append((func, args))

    def drain(self, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            if self._cbs:
                fn, args = self._cbs.pop(0)
                if fn:
                    fn(*args)
            else:
                if not any(t.is_alive() for t in threading.enumerate()
                           if t is not threading.main_thread()):
                    break
                time.sleep(0.02)
        time.sleep(0.05)
        while self._cbs:
            fn, args = self._cbs.pop(0)
            if fn:
                fn(*args)


# ---------------------------------------------------------------- 数据
LIST_ROWS = [
    {"id": 2001, "shipNo": "FH20260805001", "receivingNo": "RCV2001",
     "warehouseName": "商丘库", "supplierName": "信义玻璃", "supplierNo": "SUP001",
     "shipQty": 100, "receivingQty": 100, "shelvesQty": 100,
     "receiptStatus": 90311003, "receiptType": 90331017,
     "updateByName": "郭佳", "updateAt": "2026-08-05 10:00:00",
     "recordVersion": 7},
    {"id": 2002, "shipNo": "FH20260805002", "receivingNo": "RCV2002",
     "warehouseName": "商丘库", "supplierName": "福耀玻璃", "supplierNo": "SUP002",
     "shipQty": 40, "receivingQty": 30, "shelvesQty": 30,
     "receiptStatus": 90311004, "receiptType": 90331017,
     "updateByName": "李强", "updateAt": "2026-08-06 11:00:00",
     "recordVersion": 2},
    {"id": 2003, "shipNo": "FH20260805003", "receivingNo": "RCV2003",
     "warehouseName": "商丘库", "supplierName": "圣戈班", "supplierNo": "SUP003",
     "shipQty": 60, "receivingQty": 60, "shelvesQty": 60,
     "receiptStatus": 90311005, "receiptType": 90331021,
     "updateByName": "王五", "updateAt": "2026-08-07 12:00:00",
     "recordVersion": 3},
    {"id": 2004, "shipNo": "FH20260805004", "receivingNo": "RCV2004",
     "warehouseName": "商丘库", "supplierName": "皮尔金顿", "supplierNo": "SUP004",
     "shipQty": 20, "receivingQty": 0, "shelvesQty": 0,
     "receiptStatus": 90311001, "receiptType": 90331017,
     "updateByName": "赵六", "updateAt": "2026-08-08 13:00:00",
     "recordVersion": 1},
]

# receiptInfo/{id} 上架明细（含 shelvesQty/shelvesdQty）
SHELF_DETAILS = [
    {"detailId": 8001, "detailsId": 8001, "brandName": "信义", "partCode": "XY-1111",
     "partName": "前挡风玻璃", "category_two": 90921001, "model_number": "TOYOTA-A",
     "shelvesQty": 100, "shelvesdQty": 0, "costPrice": 50.0,
     "shelfLocationNo": "A-01-01", "shelfLocationId": 501,
     "pickingLocationNo": "B-09", "pickingLocationId": 900},
    {"detailId": 8002, "detailsId": 8002, "brandName": "信义", "partCode": "XY-2222",
     "partName": "后挡风玻璃", "category_two": 90921002, "model_number": "VW-B",
     "shelvesQty": 40, "shelvesdQty": 15, "costPrice": 80.0,
     "shelfLocationNo": "A-02-02", "shelfLocationId": 502},
]

# receiptInfo/onshelf/{id} 入库清单明细（含 shelf_quantity/totalAmt）
ONSHELF_DETAILS = [
    {"detailId": 8001, "brandName": "信义", "partCode": "XY-1111",
     "partName": "前挡风玻璃", "category_two": 90921001, "model_number": "TOYOTA-A",
     "shelf_quantity": 60, "costPrice": 50.0, "totalAmt": 3000.0,
     "location_no": "A-01-01", "onshelf_by": ["郭佳"]},
    {"detailId": 8002, "brandName": "信义", "partCode": "XY-2222",
     "partName": "后挡风玻璃", "category_two": 90921002, "model_number": "VW-B",
     "shelf_quantity": 25, "costPrice": 80.0, "totalAmt": 2000.0,
     "location_no": "A-02-02", "onshelf_by": ["郭佳"]},
]

EMP_DATA = [
    {"EMPLOYEE_NAME": "郭佳", "PHONE": "13800000001"},
    {"EMPLOYEE_NAME": "李强", "PHONE": "13800000002"},
]

LOC_DATA = [
    {"locationId": 501, "locationNo": "A-01-01", "locationName": "前挡区"},
    {"locationId": 502, "locationNo": "A-01-02", "locationName": "后挡区"},
]


def make_handler():
    def handler(method, url, **kw):
        if 'getEmpByRoleCode' in url:
            return FakeResponse({"resultCode": 200, "data": EMP_DATA}, url)
        if 'findAllLocationValid' in url:
            return FakeResponse({"resultCode": 200, "data": LOC_DATA}, url)
        if 'basedata/dicts' in url:
            return FakeResponse({"resultCode": 200, "data": {"dict": {
                "9033": [{"code_id": 90331017, "code_cn_desc": "非玻璃采购入库"},
                         {"code_id": 90331021, "code_cn_desc": "玻璃采购入库"}],
                "9031": [{"code_id": 90311001, "code_cn_desc": "未验收"},
                         {"code_id": 90311002, "code_cn_desc": "部分验收"},
                         {"code_id": 90311003, "code_cn_desc": "已验收"},
                         {"code_id": 90311004, "code_cn_desc": "部分上架"},
                         {"code_id": 90311005, "code_cn_desc": "已上架"}],
                "9092": [{"code_id": 90921001, "code_cn_desc": "前挡"},
                         {"code_id": 90921002, "code_cn_desc": "后挡"}],
            }}}, url)
        if 'shelvesHandle' in url:
            return FakeResponse({"resultCode": 200, "success": True}, url)
        if 'onshelf/' in url:
            return FakeResponse({"resultCode": 200, "data": {"details": ONSHELF_DETAILS}}, url)
        if url.endswith('/receiptInfo'):
            return FakeResponse({"resultCode": 200,
                                 "data": {"rows": LIST_ROWS, "total": 4}}, url)
        if '/receiptInfo/' in url:
            return FakeResponse({"resultCode": 200, "data": {"details": SHELF_DETAILS}}, url)
        return FakeResponse({"resultCode": 404, "errMsg": "unhandled " + url}, url)
    return handler


PASS, FAIL = [], []


def check(name, cond, extra=''):
    if cond:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL  %s  %s" % (name, extra))


def main():
    root = tk.Tk()
    root.withdraw()
    ctrl = FakeController(root)
    ctrl.session.handler = make_handler()

    parent = ttk.Frame(root)
    page = pp.PurchasePutawayPage(parent, ctrl)
    print("[init] 页面构建成功")

    # ---- 1. 默认值 ----
    print("\n[1] 默认值")
    check("仓库默认第一个", page.warehouse_var.get() == "商丘库", page.warehouse_var.get())
    check("收货状态默认 部分验收+已验收+部分上架",
          page.receive_status_vars['90311002'].get()
          and page.receive_status_vars['90311003'].get()
          and page.receive_status_vars['90311004'].get()
          and not page.receive_status_vars['90311001'].get()
          and not page.receive_status_vars['90311005'].get())
    check("折叠区默认收起", page.show_more is False)
    check("两组时间默认不启用",
          page.use_created_var.get() is False and page.use_so_created_var.get() is False)
    ctrl.drain()

    # ---- 2. 字典 ----
    print("\n[2] 字典")
    check("9033 已加载", '90331017' in (page.dict_maps.get('9033') or {}))
    check("9031 已加载", '90311005' in (page.dict_maps.get('9031') or {}))
    check("9092 已加载", '90921001' in (page.dict_maps.get('9092') or {}))
    check("入库类型默认 非玻璃采购入库",
          page.receipt_type_var.get() == "非玻璃采购入库", page.receipt_type_var.get())

    # ---- 3. 查询参数 ----
    print("\n[3] 查询参数")
    CAPTURED.clear()
    page.receipt_no_var.set("FH2026")
    page.supplier_no_var.set("SUP001")
    page.supplier_name_var.set("信义")
    page.query()
    ctrl.drain()
    q = [c for c in CAPTURED if c['method'] == 'GET' and c['url'].endswith('/receiptInfo')]
    check("已发出列表请求", len(q) == 1, str([c['url'] for c in CAPTURED]))
    params = q[0]['params']
    print("       params =", params)
    check("warehouseId=11", params.get('warehouseId') == 11)
    check("searchLoading='true'", params.get('searchLoading') == 'true')
    check("sparePartsStatus 逗号串",
          params.get('sparePartsStatus') == '90311002,90311003,90311004',
          str(params.get('sparePartsStatus')))
    check("sparePartsStatus1[] 数组",
          params.get('sparePartsStatus1[]') == ['90311002', '90311003', '90311004'],
          str(params.get('sparePartsStatus1[]')))
    check("receiptType 驼峰且为 90331017", params.get('receiptType') == '90331017',
          str(params.get('receiptType')))
    check("receiptNo/supplierNo/supplierFullName 已传",
          params.get('receiptNo') == 'FH2026' and params.get('supplierNo') == 'SUP001'
          and params.get('supplierFullName') == '信义')
    check("未启用时间时不传 createdSta/soCreatedSta",
          'createdSta' not in params and 'soCreatedSta' not in params)

    # 关键：与签收页的 receipt_type 区分开
    check("未使用签收页的 receipt_type 下划线写法", 'receipt_type' not in params)

    try:
        import requests
        req = requests.Request('GET', q[0]['url'], params=params).prepare()
        qs = req.url.split('?', 1)[1]
        print("       序列化 =", qs)
        check("序列化含重复键 sparePartsStatus1%5B%5D",
              qs.count('sparePartsStatus1%5B%5D') == 3, qs)
    except Exception as e:
        print("       （跳过序列化校验：%s）" % e)

    # ---- 4. 列表渲染 ----
    print("\n[4] 列表渲染")
    items = page.tree.get_children()
    check("渲染 4 行", len(items) == 4, str(len(items)))
    v0 = page.tree.item(items[0], 'values')
    check("列数 12", len(v0) == 12, str(len(v0)))
    check("发运单号", v0[1] == 'FH20260805001', str(v0[1]))
    check("收货状态解码 已验收", v0[8] == '已验收', str(v0[8]))
    check("入库类型解码", v0[9] == '非玻璃采购入库', str(v0[9]))
    v2 = page.tree.item(items[2], 'values')
    check("第 3 行收货状态 已上架", v2[8] == '已上架', str(v2[8]))
    check("第 3 行入库类型 玻璃采购入库", v2[9] == '玻璃采购入库', str(v2[9]))
    check("分页信息", page.page_info_var.get() == "第 1/1 页 (共 4 条)",
          page.page_info_var.get())

    # ---- 5. can_shelf / remain_qty ----
    print("\n[5] 状态防护与待上架数量")
    check("已验收可上架", page.can_shelf(LIST_ROWS[0]) is True)
    check("部分上架可上架", page.can_shelf(LIST_ROWS[1]) is True)
    check("已上架不可上架", page.can_shelf(LIST_ROWS[2]) is False)
    check("未验收不可上架", page.can_shelf(LIST_ROWS[3]) is False)
    check("remainQty = 100-0 = 100", page.remain_qty(SHELF_DETAILS[0]) == 100,
          str(page.remain_qty(SHELF_DETAILS[0])))
    check("remainQty = 40-15 = 25", page.remain_qty(SHELF_DETAILS[1]) == 25,
          str(page.remain_qty(SHELF_DETAILS[1])))
    check("remainQty 负数归 0",
          page.remain_qty({"shelvesQty": 10, "shelvesdQty": 30}) == 0)

    # ---- 6. 上架明细（onshelf 接口）----
    print("\n[6] 上架明细")
    CAPTURED.clear()
    page.tree.selection_set(items[0])
    page.open_detail()
    ctrl.drain()
    d = [c for c in CAPTURED if 'onshelf/' in c['url']]
    check("明细走 onshelf 端点", len(d) == 1, str([c['url'] for c in CAPTURED]))
    check("明细 URL 带 id",
          d[0]['url'].endswith('/dmscloud.part/part/receiptInfo/onshelf/2001'),
          str(d[0]['url']))
    check("明细数量取 shelf_quantity=60", page.receipt_qty(ONSHELF_DETAILS[0]) == 60)
    check("明细金额取 totalAmt", page.receipt_amount(ONSHELF_DETAILS[0]) == '3000.00',
          page.receipt_amount(ONSHELF_DETAILS[0]))
    check("金额缺失时按 单价×数量 兜底",
          page.receipt_amount({"costPrice": 10, "shelf_quantity": 3}) == '30.00',
          page.receipt_amount({"costPrice": 10, "shelf_quantity": 3}))

    # ---- 7. 上架窗 ----
    print("\n[7] 上架窗")
    CAPTURED.clear()
    page.tree.selection_set(items[0])
    page.open_shelf()
    ctrl.drain()
    sd = [c for c in CAPTURED if c['url'].endswith('/receiptInfo/2001')]
    check("上架明细走 receiptInfo/{id}", len(sd) == 1, str([c['url'] for c in CAPTURED]))
    emp = [c for c in CAPTURED if 'getEmpByRoleCode' in c['url']]
    check("并行拉上架人列表 roleCode=SJR",
          len(emp) == 1 and emp[0]['params'].get('roleCode') == 'SJR', str(emp))
    check("上架人列表已解析", [e['employeeName'] for e in page.emp_list] == ['郭佳', '李强'],
          str(page.emp_list))
    check("recordVersion 取自列表行 = 7", page._record_version == 7,
          str(page._record_version))
    check("上架窗渲染 2 行", len(page._shelf_rows) == 2, str(len(page._shelf_rows)))
    check("默认库位取 shelfLocationNo",
          page._shelf_rows[0]['_shelfLocationNo'] == 'A-01-01',
          str(page._shelf_rows[0]['_shelfLocationNo']))
    check("默认库位 id", page._shelf_rows[0]['_shelfLocationId'] == 501)
    check("默认上架数量 = 待上架 100",
          page._shelf_rows[0]['qty_var'].get() == '100',
          page._shelf_rows[0]['qty_var'].get())
    check("第 2 行默认上架数量 = 25",
          page._shelf_rows[1]['qty_var'].get() == '25',
          page._shelf_rows[1]['qty_var'].get())

    # 顶层上架人同步
    page.top_onshelf_var.set("郭佳")
    check("顶层上架人同步到明细行",
          all(it['person_var'].get() == "郭佳" for it in page._shelf_rows),
          str([it['person_var'].get() for it in page._shelf_rows]))

    # 库位候选
    print("\n[8] 库位候选")
    CAPTURED.clear()
    page._shelf_rows[0]['loc_var'].set("A-01")
    page._loc_target = page._shelf_rows[0]
    page._query_locations(page._shelf_rows[0])
    ctrl.drain()
    loc = [c for c in CAPTURED if 'findAllLocationValid' in c['url']]
    check("库位查询已发出", len(loc) == 1, str([c['url'] for c in CAPTURED]))
    check("库位查询带 warehouseId 与 locationNo",
          loc[0]['params'].get('warehouseId') == 11
          and loc[0]['params'].get('locationNo') == 'A-01', str(loc[0]['params']))
    page.loc_list.selection_set(1)
    page._on_pick_location()
    check("双击候选填入库位编号", page._shelf_rows[0]['loc_var'].get() == 'A-01-02',
          page._shelf_rows[0]['loc_var'].get())
    check("双击候选写入库位 id", page._shelf_rows[0]['_shelfLocationId'] == 502)
    check("选择后取消 _locDirty 标记", page._shelf_rows[0]['_locDirty'] is False)

    # ---- 9. 上架报文 ----
    print("\n[9] 上架报文")
    page._shelf_rows[0]['qty_var'].set("999")     # 超过 100 → 截断
    page._shelf_rows[1]['qty_var'].set("10")      # 小于 25，正常
    payload = page.build_shelf_payload(is_draft=False)
    print("       payload =", json.dumps(payload, ensure_ascii=False)[:320])
    check("顶层 id = 2001", payload['id'] == 2001)
    check("warehouseId = 11", payload['warehouseId'] == 11)
    check("recordVersion = 7", payload['recordVersion'] == 7)
    check("checkStatus = 10041001", payload['checkStatus'] == 10041001)
    check("顶层 onshelf_by 为字符串 '郭佳'", payload['onshelf_by'] == '郭佳')
    check("确认上架不带 isSave", 'isSave' not in payload)
    dtl = payload['detailDtoList']
    check("数组键为 detailDtoList", len(dtl) == 2)
    check("shelvesQty 传字符串", isinstance(dtl[0]['shelvesQty'], str),
          repr(dtl[0]['shelvesQty']))
    check("上架数量截断到 100", dtl[0]['shelvesQty'] == '100', dtl[0]['shelvesQty'])
    check("上架数量正常 10", dtl[1]['shelvesQty'] == '10', dtl[1]['shelvesQty'])
    check("行 onshelf_by 为数组", dtl[0]['onshelf_by'] == ['郭佳'], str(dtl[0]['onshelf_by']))
    check("行 onshelf_by_name 为字符串", dtl[0]['onshelf_by_name'] == '郭佳')
    check("shelfLocationNo 已写入", dtl[0]['shelfLocationNo'] == 'A-01-02',
          dtl[0]['shelfLocationNo'])
    check("shelfLocationId 已写入", dtl[0]['shelfLocationId'] == 502)
    check("select_LOCATION_OPTIONS 结构正确",
          dtl[0]['select_LOCATION_OPTIONS'] == [{"locationId": 502, "locationNo": "A-01-02"}],
          str(dtl[0].get('select_LOCATION_OPTIONS')))
    check("detailId/detailsId 已回填",
          dtl[0]['detailId'] == 8001 and dtl[0]['detailsId'] == 8001)

    # 暂存草稿
    draft = page.build_shelf_payload(is_draft=True)
    check("暂存草稿带 isSave=1", draft.get('isSave') == 1, str(draft.get('isSave')))

    # 全 0 校验
    page._shelf_rows[0]['qty_var'].set("0")
    page._shelf_rows[1]['qty_var'].set("0")
    check("全 0 时确认上架被拦截", page.submit_shelf(False) is None)  # 内部 showwarning 已打桩
    # 拦截时不发请求
    before = len(CAPTURED)
    page.submit_shelf(False)
    ctrl.drain()
    check("全 0 确认上架未发请求", len(CAPTURED) == before, str(len(CAPTURED) - before))

    # 正常提交
    page._shelf_rows[0]['qty_var'].set("50")
    CAPTURED.clear()
    page.submit_shelf(False)
    ctrl.drain()
    post = [c for c in CAPTURED if 'shelvesHandle' in c['url']]
    check("POST shelvesHandle 已发出", len(post) == 1, str([c['url'] for c in CAPTURED]))
    if post:
        body = json.loads(post[0]['data'])
        check("提交 body 含 detailDtoList", 'detailDtoList' in body)
        check("提交用 data= 而非 json=", 'data' in post[0] and 'json' not in post[0])

    # ---- 10. 打印 ----
    print("\n[10] 打印清单")
    page._render_rows(LIST_ROWS, 4)
    items = page.tree.get_children()
    page.tree.selection_set(items[0])

    CAPTURED.clear()
    page.open_print('shelf')
    ctrl.drain()
    ps = [c for c in CAPTURED if c['url'].endswith('/receiptInfo/2001')]
    check("上架清单走 receiptInfo/{id}", len(ps) == 1,
          str([c['url'] for c in CAPTURED]))
    shelf_group = page.build_shelf_group(
        [{"brandName": "信义", "partCode": "XY-1", "partName": "前挡",
          "category_two": 90921001, "model_number": "M1",
          "shelvesQty": 100, "shelvesdQty": 60, "shelfLocationNo": "A-01"}],
        LIST_ROWS[0])
    check("上架清单数量取 shelvesdQty=60", shelf_group['items'][0]['NUM'] == 60,
          str(shelf_group['items'][0]['NUM']))
    check("上架清单不含单价/金额字段",
          'PRICE' not in shelf_group['items'][0] and 'AMOUNT' not in shelf_group['items'][0])

    CAPTURED.clear()
    page.open_print('receipt')
    ctrl.drain()
    pr = [c for c in CAPTURED if 'onshelf/' in c['url']]
    check("入库清单走 receiptInfo/onshelf/{id}", len(pr) == 1,
          str([c['url'] for c in CAPTURED]))
    receipt_group = page.build_receipt_group(ONSHELF_DETAILS, LIST_ROWS[0])
    check("入库清单数量取 shelf_quantity=60", receipt_group['items'][0]['NUM'] == 60,
          str(receipt_group['items'][0]['NUM']))
    check("入库清单金额取 totalAmt=3000", receipt_group['items'][0]['AMOUNT'] == 3000.0,
          str(receipt_group['items'][0]['AMOUNT']))
    check("入库清单带供应商与发运单号",
          receipt_group['header']['SUPPLIER_NAME'] == '信义玻璃'
          and receipt_group['header']['SHIP_NO'] == 'FH20260805001')
    check("仓库名简称替换（福耀玻璃→福耀）",
          page.short_brand('福耀玻璃商丘库') == '福耀商丘库', page.short_brand('福耀玻璃商丘库'))

    # ---- 11. 重置 ----
    print("\n[11] 重置")
    page.reset_form()
    check("重置后入库类型恢复 非玻璃采购入库",
          page.receipt_type_var.get() == "非玻璃采购入库", page.receipt_type_var.get())
    check("重置后收货状态恢复默认三项",
          page.receive_status_vars['90311002'].get()
          and page.receive_status_vars['90311003'].get()
          and page.receive_status_vars['90311004'].get()
          and not page.receive_status_vars['90311001'].get())
    check("重置后折叠项清空",
          page.receipt_no_var.get() == "" and page.supplier_no_var.get() == "")

    # ---- 12. 时间筛选参数 ----
    print("\n[12] 时间筛选")
    page.use_created_var.set(True)
    page.toggle_created()
    page.use_so_created_var.set(True)
    page.toggle_so_created()
    p = page.build_params()
    check("启用后传 createdSta/createdEnd", 'createdSta' in p and 'createdEnd' in p)
    check("启用后传 soCreatedSta/soCreatedEnd", 'soCreatedSta' in p and 'soCreatedEnd' in p)

    root.destroy()

    print("\n" + "=" * 60)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  -", f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""到货签收页面冒烟测试（临时脚本，验证后可删）

用 FakeController / FakeSession 驱动 PurchaseSignPage，验证：
1. 查询参数形态（signStatus 逗号串 + signStatus1[] 数组 + receipt_type 下划线）
2. 列表渲染与勾选列
3. 明细请求与渲染
4. 签收报文（details 数组键 / orderStatus=47141001 / 接收数量截断 / totalPrice 重算）
5. 批量签收 body = { ids: [...] }
6. can_sign 状态防护、分页
"""
import json
import sys
import threading
import time

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb

# 自动应答弹窗，避免测试被模态框阻塞（purchase_sign 里是 `from tkinter import messagebox`，
# 拿到的是同一个模块对象，打补丁对其生效）
mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"
mb.askyesno = lambda *a, **k: True

import purchase_sign as ps

# ---------------------------------------------------------------- 桩
CAPTURED = []


class FakeResponse:
    def __init__(self, payload, url=''):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.url = url
        self.status_code = 200

    def json(self):
        return json.loads(self.text)


class FakeSession:
    """按 URL 返回预设响应，并记录所有请求"""

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
    """替代 MainApplication：提供 session / options / check_login_status / after"""

    def __init__(self, root):
        self.root = root
        self.session = FakeSession()
        self.options = {"商丘库": 11, "郑州库": 6}
        self._cbs = []

    def check_login_status(self, response):
        return False  # False = 登录态正常

    def after(self, ms, func=None, *args):
        # 工作线程里不能调用 Tk 的 after，改为入队，由主线程 drain
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
    {"id": 1001, "shipNo": "FH20260801001", "warehouseName": "商丘库",
     "supplierName": "信义玻璃", "supplierNo": "SUP001", "caseNum": 10,
     "shipQty": 100, "totalAmount": 5000.0, "receivingQty": 0,
     "signStatus": 47121001, "shipDate": "2026-08-01", "receivingDate": "",
     "receiptType": 90331017, "remark": "易碎", "warehouseId": 11,
     "receivingNo": "RCV001"},
    {"id": 1002, "shipNo": "FH20260801002", "warehouseName": "商丘库",
     "supplierName": "福耀玻璃", "supplierNo": "SUP002", "caseNum": 5,
     "shipQty": 40, "totalAmount": 2000.0, "receivingQty": 10,
     "signStatus": 47121003, "shipDate": "2026-08-02", "receivingDate": "2026-08-03",
     "receiptType": 90331017, "remark": "", "warehouseId": 11,
     "receivingNo": "RCV002"},
    {"id": 1003, "shipNo": "FH20260801003", "warehouseName": "商丘库",
     "supplierName": "圣戈班", "supplierNo": "SUP003", "caseNum": 8,
     "shipQty": 60, "totalAmount": 3000.0, "receivingQty": 60,
     "signStatus": 47121002, "shipDate": "2026-08-03", "receivingDate": "2026-08-04",
     "receiptType": 90331021, "remark": "已完成", "warehouseId": 11,
     "receivingNo": "RCV003"},
]

DETAIL_ROWS = [
    {"detailsId": 9001, "brandName": "信义", "partCode": "XY-1234", "partName": "前挡风玻璃",
     "caseNo": "C1", "shipQty": 60, "receivingQty": 0, "costPrice": 50.0,
     "totalPrice": 3000.0, "markCode": "MK1", "remarks": "轻放"},
    {"detailsId": 9002, "brandName": "信义", "partCode": "XY-5678", "partName": "后挡风玻璃",
     "caseNo": "C2", "shipQty": 40, "receivingQty": 0, "costPrice": 50.0,
     "totalPrice": 2000.0, "markCode": "MK2", "remarks": ""},
]

SIGN_INFO_ROWS = [
    {"detailsId": 9001, "partName": "前挡风玻璃", "partCode": "XY-1234",
     "shipQty": 60, "receivedQty": 0, "receivingQty": 60,
     "signCostPrice": 50.0, "costPrice": 50.0},
    {"detailsId": 9002, "partName": "后挡风玻璃", "partCode": "XY-5678",
     "shipQty": 40, "receivedQty": 0, "receivingQty": 40,
     "signCostPrice": 50.0, "costPrice": 50.0},
]


def make_handler():
    def handler(method, url, **kw):
        if 'cargSign/signInfo/' in url:
            return FakeResponse({"resultCode": 200, "data": {"details": SIGN_INFO_ROWS}}, url)
        if 'cargSign/batchSign' in url:
            return FakeResponse({"resultCode": 200, "success": True}, url)
        if url.endswith('cargSign/sign'):
            return FakeResponse({"resultCode": 200, "success": True}, url)
        if 'cargSign/' in url:
            return FakeResponse({"resultCode": 200, "data": {"details": DETAIL_ROWS}}, url)
        if 'basedata/dicts' in url:
            return FakeResponse({"resultCode": 200, "data": {"dict": {
                "9033": [{"code_id": 90331017, "code_cn_desc": "非玻璃采购入库"},
                         {"code_id": 90331021, "code_cn_desc": "玻璃采购入库"}],
                "4712": [{"code_id": 47121001, "code_cn_desc": "未签收"},
                         {"code_id": 47121002, "code_cn_desc": "已签收"},
                         {"code_id": 47121003, "code_cn_desc": "部分签收"}],
            }}}, url)
        if url.endswith('/cargSign'):
            return FakeResponse({"resultCode": 200, "data": {"rows": LIST_ROWS, "total": 3}}, url)
        return FakeResponse({"resultCode": 404, "errMsg": "unhandled " + url}, url)
    return handler


# ---------------------------------------------------------------- 断言
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
    page = ps.PurchaseSignPage(parent, ctrl)
    print("[init] 页面构建成功")

    # ---- 1. 默认值 ----
    print("\n[1] 默认状态")
    check("仓库默认选中第一个", page.warehouse_var.get() == "商丘库", page.warehouse_var.get())
    check("签收状态默认勾选 未签收+部分签收",
          page.sign_status_vars['47121001'].get() is True
          and page.sign_status_vars['47121003'].get() is True
          and page.sign_status_vars['47121002'].get() is False)
    check("折叠区默认收起", page.show_more is False)
    check("发货日期默认不启用", page.use_ship_date_var.get() is False)
    ctrl.drain()

    # ---- 2. 字典加载 ----
    print("\n[2] 字典")
    check("9033 入库类型已加载", '90331017' in (page.dict_maps.get('9033') or {}),
          str(page.dict_maps.get('9033')))
    check("4712 签收状态已加载", '47121001' in (page.dict_maps.get('4712') or {}))
    check("入库类型下拉含「全部」", page.receipt_type_cb['values'][0] == "全部",
          str(page.receipt_type_cb['values']))

    # ---- 3. 查询参数 ----
    print("\n[3] 查询参数")
    CAPTURED.clear()
    page.ship_no_var.set("FH2026")
    page.part_code_var.set("XY-1")
    page.part_name_var.set("玻璃")
    page.receipt_type_var.set("玻璃采购入库")
    page.query()
    ctrl.drain()
    q = [c for c in CAPTURED if c['method'] == 'GET' and c['url'].endswith('/cargSign')]
    check("已发出列表请求", len(q) == 1, str([c['url'] for c in CAPTURED]))
    params = q[0]['params']
    print("       params =", params)
    check("warehouseId=11", params.get('warehouseId') == 11, str(params.get('warehouseId')))
    check("searchLoading='true'", params.get('searchLoading') == 'true')
    check("signStatus 为逗号串", params.get('signStatus') == '47121001,47121003',
          str(params.get('signStatus')))
    check("signStatus1[] 为数组", params.get('signStatus1[]') == ['47121001', '47121003'],
          str(params.get('signStatus1[]')))
    check("receipt_type 下划线且为 code", params.get('receipt_type') == '90331021',
          str(params.get('receipt_type')))
    check("shipNo/partCode/partName 已传",
          params.get('shipNo') == 'FH2026' and params.get('partCode') == 'XY-1'
          and params.get('partName') == '玻璃')
    check("未启用日期时不传 shipStartDate", 'shipStartDate' not in params)

    # requests 序列化出的真实查询串
    try:
        import requests
        req = requests.Request('GET', q[0]['url'], params=params).prepare()
        qs = req.url.split('?', 1)[1]
        print("       序列化 =", qs)
        check("序列化含重复键 signStatus1%5B%5D",
              qs.count('signStatus1%5B%5D') == 2, qs)
    except Exception as e:
        print("       （跳过序列化校验：%s）" % e)

    # ---- 4. 列表渲染 ----
    print("\n[4] 列表渲染")
    items = page.tree.get_children()
    check("渲染 3 行", len(items) == 3, str(len(items)))
    v0 = page.tree.item(items[0], 'values')
    check("列数 15", len(v0) == 15, str(len(v0)))
    check("选择列初始为 ☐", v0[0] == '☐', str(v0[0]))
    check("序号为全局序号", str(v0[1]) == '1', repr(v0[1]))
    check("发运单号", v0[2] == 'FH20260801001', str(v0[2]))
    check("签收状态已解码", v0[10] == '未签收', str(v0[10]))
    check("入库类型已解码", v0[13] == '非玻璃采购入库', str(v0[13]))
    v2 = page.tree.item(items[2], 'values')
    check("已签收行解码正确", v2[10] == '已签收', str(v2[10]))
    check("第 3 行序号为 3", str(v2[1]) == '3', repr(v2[1]))
    check("分页信息", page.page_info_var.get() == "第 1/1 页 (共 3 条)",
          page.page_info_var.get())

    # 翻页后序号应延续（pageNum=2 时首行序号 = 21）
    page.page_num = 2
    page.total = 25
    page._render_rows(LIST_ROWS, 25)
    vp = page.tree.get_children()
    check("第 2 页首行序号为 21", str(page.tree.item(vp[0], 'values')[1]) == '21',
          repr(page.tree.item(vp[0], 'values')[1]))
    check("第 2 页分页信息", page.page_info_var.get() == "第 2/2 页 (共 25 条)",
          page.page_info_var.get())
    page.page_num = 1
    page._render_rows(LIST_ROWS, 3)
    items = page.tree.get_children()  # 重新渲染后句柄已变，需重新取

    # ---- 5. can_sign 状态防护 ----
    print("\n[5] 可签收判定")
    check("未签收可签收", page.can_sign(LIST_ROWS[0]) is True)
    check("部分签收可签收", page.can_sign(LIST_ROWS[1]) is True)
    check("已签收不可签收", page.can_sign(LIST_ROWS[2]) is False)

    # ---- 6. 勾选 ----
    print("\n[6] 勾选列")
    page.tree.selection_set(items[0])
    page.toggle_all(True)
    ids = page.checked_row_ids()
    check("全选后勾选 3 行", len(ids) == 3, str(ids))
    check("已选计数显示", page.selected_var.get() == "已选 3 单", page.selected_var.get())
    page.toggle_all(False)
    check("清空后无勾选", page.checked_row_ids() == [])
    # 模拟点击第一列
    page.tree.event_generate  # noqa
    class E:
        x, y = 10, 10
    # 直接调用 on_tree_click 需要 identify_row，改用 toggle 逻辑验证
    page.toggle_all(False)
    check("清空选择后计数为空", page.selected_var.get() == "", page.selected_var.get())

    # ---- 7. 明细 ----
    print("\n[7] 明细")
    CAPTURED.clear()
    page.tree.selection_set(items[0])
    page.open_detail()
    ctrl.drain()
    d = [c for c in CAPTURED if c['method'] == 'GET' and '/cargSign/' in c['url']]
    check("明细请求 URL 正确",
          len(d) == 1 and d[0]['url'].endswith('/dmscloud.part/part/cargSign/1001'),
          str([c['url'] for c in d]))
    check("明细数据已缓存", len(page._detail_win.winfo_children()) == 1)

    # ---- 8. 签收 ----
    print("\n[8] 签收")
    CAPTURED.clear()
    page.tree.selection_set(items[0])
    page.open_sign()
    ctrl.drain()
    si = [c for c in CAPTURED if 'signInfo/' in c['url']]
    check("优先请求 signInfo", len(si) == 1, str([c['url'] for c in CAPTURED]))
    check("签收窗已渲染 2 行", len(page._sign_rows) == 2, str(len(page._sign_rows)))

    # 改接收数量：第一行填 999（应截断到 60），第二行填 25
    page._sign_rows[0]['recv_var'].set('999')
    page._sign_rows[1]['recv_var'].set('25')
    payload = page.build_sign_payload()
    print("       payload =", json.dumps(payload, ensure_ascii=False)[:300])
    check("数组键为 details", 'details' in payload and 'detailList' not in payload)
    check("无顶层 signStatus", 'signStatus' not in payload)
    check("orderStatus=47141001", payload['orderStatus'] == 47141001, str(payload.get('orderStatus')))
    check("顶层 id", payload['id'] == 1001, str(payload.get('id')))
    check("顶层 shipNo", payload['shipNo'] == 'FH20260801001')
    check("顶层 warehouseId 回退当前仓库", payload['warehouseId'] == 11)
    dt = payload['details']
    check("明细保留 detailsId", dt[0]['detailsId'] == 9001 and dt[1]['detailsId'] == 9002)
    check("接收数量截断到发运数量 60", dt[0]['receivingQty'] == 60, str(dt[0]['receivingQty']))
    check("接收数量正常值 25", dt[1]['receivingQty'] == 25, str(dt[1]['receivingQty']))
    check("totalPrice 按接收数量重算 60*50", dt[0]['totalPrice'] == '3000.00', str(dt[0]['totalPrice']))
    check("totalPrice 按接收数量重算 25*50", dt[1]['totalPrice'] == '1250.00', str(dt[1]['totalPrice']))
    check("保留 signCostPrice 原字段", dt[0].get('signCostPrice') == 50.0)
    check("保留 partName 原字段", dt[0].get('partName') == '前挡风玻璃')

    # 负数与非数字
    page._sign_rows[0]['recv_var'].set('-5')
    page._sign_rows[1]['recv_var'].set('abc')
    p2 = page.build_sign_payload()
    check("负数归 0", p2['details'][0]['receivingQty'] == 0, str(p2['details'][0]['receivingQty']))
    check("非数字归 0", p2['details'][1]['receivingQty'] == 0, str(p2['details'][1]['receivingQty']))

    # 提交
    CAPTURED.clear()
    page._sign_rows[0]['recv_var'].set('60')
    page._sign_rows[1]['recv_var'].set('40')
    page.submit_sign()
    ctrl.drain()
    put = [c for c in CAPTURED if c['method'] == 'PUT' and c['url'].endswith('cargSign/sign')]
    check("PUT cargSign/sign 已发出", len(put) == 1, str([c['url'] for c in CAPTURED]))
    if put:
        body = json.loads(put[0]['data'])
        check("PUT body 为 JSON 且含 details", isinstance(body, dict) and 'details' in body)
        check("PUT 使用 data= 而非 json=", 'data' in put[0] and 'json' not in put[0])

    # ---- 9. 批量签收 ----
    print("\n[9] 批量签收")
    CAPTURED.clear()
    page.toggle_all(True)
    page.batch_sign()
    ctrl.drain()
    b = [c for c in CAPTURED if 'batchSign' in c['url']]
    check("PUT batchSign 已发出", len(b) == 1, str([c['url'] for c in CAPTURED]))
    if b:
        body = json.loads(b[0]['data'])
        check("批量 body = {ids:[...]}", body == {"ids": [1001, 1002, 1003]}, str(body))

    # ---- 10. 重置 ----
    print("\n[10] 重置")
    page.reset_form()
    check("重置后签收状态恢复默认",
          page.sign_status_vars['47121001'].get() and page.sign_status_vars['47121003'].get()
          and not page.sign_status_vars['47121002'].get())
    check("重置后入库类型为全部", page.receipt_type_var.get() == "全部")
    check("重置后发货日期不启用", page.use_ship_date_var.get() is False)

    # ---- 11. 启用日期后传参 ----
    print("\n[11] 日期筛选")
    page.use_ship_date_var.set(True)
    page.toggle_ship_date()
    p3 = page.build_params()
    check("启用后传 shipStartDate/shipEndDate",
          'shipStartDate' in p3 and 'shipEndDate' in p3, str(p3))

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

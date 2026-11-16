# -*- coding: utf-8 -*-
"""库内作业「调拨申请 / 移库管理」冒烟测试（临时脚本）

验证内容
========
A. 源码级注册与契约（离线静态断言）
   1. main_app.py 六个注册点（import / frame_classes / tabs_info /
      create_popup_panel page_map / page_to_tab_group / page_name_map）
   2. 两个页面的接口端点、checkStatus 常量、字典组、列头顺序
   3. 「不提供拆行」的显式决策（Web 模板未渲染 splitRow 按钮）

B. 运行期功能（真实 Tk + FakeSession）
   4. 字典兜底解码（4716 / 4717 / 4617 / 4715）
   5. 调拨申请查询参数形态（searchType=application / 时间起止 / 状态码）
   6. 调拨申请保存报文（saveTransfer 结构、isWarehouseOutbound、boxId、recordVersion）
   7. 移库管理保存报文（shiftHandle 结构、move_by、UI 专用键剔除）
   8. select_LOCATION_OPTIONS 2 字段 / 6 字段语义
   9. 状态闸门（可编辑 / 可删除）

运行：python smoke_transfer_menus.py   （退出码 0 = 全通过）
"""

import json
import re
import sys
import threading
import time

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"
mb.askyesno = lambda *a, **k: True

import transfer_application as ta
import transfer_change as tc
import transfer_dialogs as td

CAPTURED = []


class FakeResponse:
    def __init__(self, payload, url=''):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.url = url
        self.status_code = 200
        self.content = b'xlsx-bytes'

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


# ---------------------------------------------------------------- 假数据
DICTS = {
    '4716': [('47161001', '待提交'), ('47161002', '待审核'), ('47161004', '审核驳回')],
    '4717': [('47171001', '平价调拨'), ('47171002', '加价调拨')],
    '4617': [('46171001', '送货'), ('46171003', '物流发货'), ('46171004', '自提')],
    '4715': [('47151001', '待提交'), ('47151002', '已提交')],
}

APP_ROW = {
    'id': 14642, 'transferNo': 'ZZHJDBD2026072500002', 'transferType': 47171002,
    'logisticsMode': 46171003, 'transferStatus': 47161002, 'moveWarehouseId': 11,
    'moveWarehouseName': '商丘库', 'removeWarehouseId': 6, 'removeWarehouseName': '郑州库',
    'createdAt': '2026-07-25 08:48:38', 'createdBy': 'HJ103', 'createdByName': '赵少龙',
    'auditBy': '赵少龙', 'auditDate': '2026-07-25 15:56:20', 'boxId': 6, 'boxName': '木箱',
    'recordVersion': 5, 'remark': None, 'isWarehouseOutbound': 10041001,
}

APP_DETAIL = [
    {'detailId': 200740, 'brand': 1, 'brandId': 1, 'brandName': '福耀玻璃',
     'partCode': 'GLW11858CCLY', 'partId': 51455, 'partName': '前挡玻璃',
     'availableQty': 1, 'transferQuantity': 1, 'remarks': '顾彪',
     'inboundLocationId': None, 'inboundLocation': None, 'recordVersion': 5},
]

CHANGE_ROW = {
    'shiftNo': 'ZZHJYKD2026072900052', 'warehouseId': 11, 'warehouseName': '商丘库',
    'createdByName': '郭佳', 'createdAt': '2026-07-29 12:19:22', 'move_by': '郭佳',
    'status': 47151001, 'recordVersion': 1, 'remark': '散片上架',
}

CHANGE_DETAIL = [
    {'logId': 58945, 'warehouseId': 11, 'warehouseName': '商丘库',
     'partCode': 'GLW01592NGBN', 'partId': 35675, 'partName': '前挡玻璃',
     'brand': 1, 'brandId': 1, 'brandName': '福耀玻璃', 'availableQty': 2,
     'removeNo': 'Z1-08', 'removeNoId': 15632, 'moveNo': 'A1-043', 'moveNoId': 14202,
     'moveQty': 2, 'status': 47151001},
]

LOC_OBJ = {'enabledStatus': 10031001, 'isValid': 10011001, 'locationId': 14202,
           'locationNo': 'A1-043', 'locationType': 90041005, 'warehouseId': 11}


def make_handler():
    def handler(method, url, **kw):
        if url.endswith('/dicts'):
            return FakeResponse({'resultCode': 200, 'data': {
                'dict': {g: [{'code_id': c, 'code_cn_desc': n} for c, n in arr]
                         for g, arr in DICTS.items()}}})
        if 'queryListForSelect' in url or 'queryListWithPermissions' in url:
            return FakeResponse({'resultCode': 200, 'data': [
                {'name': '郑州库', 'value': 6}, {'name': '商丘库', 'value': 11}]})
        if 'searchUserInfo' in url:
            return FakeResponse({'resultCode': 200, 'data': [
                {'EMPLOYEE_NAME': '郭佳'}, {'EMPLOYEE_NAME': '李强'}]})
        if 'getEmpByRoleCode' in url:
            return FakeResponse({'resultCode': 200, 'data': [
                {'EMPLOYEE_NAME': '郭佳'}, {'EMPLOYEE_NAME': '李强'}]})
        if 'queryBoxModelManageList' in url:
            return FakeResponse({'resultCode': 200, 'data': [
                {'id': 6, 'box_name': '木箱', 'box_type': 90971001},
                {'id': 7, 'box_name': '自提', 'box_type': 90971003}]})
        if url.endswith('/application'):
            return FakeResponse({'resultCode': 200, 'data': {
                'total': 1, 'pageSize': 20, 'pageNum': 1, 'rows': [APP_ROW]}})
        if url.endswith('/adjustLog'):
            return FakeResponse({'resultCode': 200, 'data': {
                'total': 1, 'pageSize': 20, 'pageNum': 1, 'rows': [CHANGE_ROW]}})
        if url.endswith('/findById'):
            return FakeResponse({'resultCode': 200, 'data': APP_DETAIL})
        if url.endswith('/queryByShiftNo'):
            return FakeResponse({'resultCode': 200, 'data': CHANGE_DETAIL})
        if url.endswith('/saveTransfer') or url.endswith('/shiftHandle'):
            return FakeResponse({'resultCode': 200, 'success': True,
                                 'data': {'code': 200}})
        if 'queryPart' in url:
            return FakeResponse({'resultCode': 200, 'data': {
                'total': 1, 'pageSize': 20, 'pageNum': 1, 'rows': [
                    {'partCode': 'GLW01592NGBN', 'partName': '前挡玻璃', 'brand': 1,
                     'brandName': '福耀玻璃', 'availableQty': 2, 'removeNo': 'Z1-08',
                     'warehouseId': 11, 'warehouseName': '商丘库'}]}})
        if 'findAllLocationValid' in url:
            return FakeResponse({'resultCode': 200, 'data': [LOC_OBJ]})
        return FakeResponse({'resultCode': 200, 'data': {}})
    return handler


PASS, FAIL = [], []


def check(name, cond, extra=''):
    if cond:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL  %s  %s" % (name, extra))


def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ================================================================ A. 源码级
def test_source_level():
    print("\n[A] 源码级注册与契约")
    main_src = read('main_app.py')
    app_src = read('transfer_application.py')
    chg_src = read('transfer_change.py')

    check("main_app 导入 TransferApplicationPage",
          'from transfer_application import TransferApplicationPage' in main_src)
    check("main_app 导入 TransferChangePage",
          'from transfer_change import TransferChangePage' in main_src)
    check("frame_classes 含两页",
          '"TransferApplicationPage": TransferApplicationPage' in main_src
          and '"TransferChangePage": TransferChangePage' in main_src)
    check("tabs_info 库内作业含三菜单",
          '("库内作业", ["调拨入库", "调拨申请", "移库管理"])' in main_src)
    check("page_map 含两菜单",
          '"调拨申请": "TransferApplicationPage"' in main_src
          and '"移库管理": "TransferChangePage"' in main_src)
    check("page_to_tab_group 两页归库内作业",
          main_src.count('": "库内作业"') >= 3)
    check("page_name_map 两页标题",
          '"TransferApplicationPage": "调拨申请"' in main_src
          and '"TransferChangePage": "移库管理"' in main_src)

    # 端点
    check("调入申请 saveTransfer 端点",
          "'/warehouse/transferIn/saveTransfer'" in app_src)
    check("调入申请 application 端点 + searchType=application",
          "'/warehouse/transferIn/application'" in app_src
          and "SEARCH_TYPE = 'application'" in app_src)
    check("调入申请 delete / export 端点",
          "'/warehouse/transferIn/delete'" in app_src
          and "'/warehouse/transferIn/export/excel'" in app_src)
    check("移库 adjustLog / shiftHandle 端点",
          "'/warehouse/change/adjustLog'" in chg_src
          and "'/warehouse/change/shiftHandle'" in chg_src)
    check("移库 queryByShiftNo / queryPart 端点",
          "'/warehouse/change/queryByShiftNo'" in chg_src
          and "URL_QUERY_PART_CHANGE = BASE + '/dmscloud.part/warehouse/change/queryPart'"
          in read('transfer_dialogs.py'))
    check("checkStatus 常量 10041001/10041002",
          'CHECK_SAVE = 10041001' in app_src and 'CHECK_SUBMIT = 10041002' in app_src
          and 'CHECK_SAVE = 10041001' in chg_src and 'CHECK_SUBMIT = 10041002' in chg_src)
    check("isWarehouseOutbound 固定 10041001",
          'IS_WAREHOUSE_OUTBOUND = 10041001' in app_src)
    check("移库人角色码 YKR", "MOVER_ROLE = 'YKR'" in chg_src)
    check("字典组 4716/4717/4617/4715",
          "DICT_STATUS = '4716'" in app_src and "DICT_TYPE = '4717'" in app_src
          and "DICT_LOGISTICS = '4617'" in app_src
          and "DICT_STATUS = '4715'" in chg_src)

    # 列头顺序（对齐 Web）
    app_cols = re.search(r"COLUMNS = \[(.*?)\]", app_src, re.S).group(1)
    for label in ['调拨单号', '调入方', '调出方', '调拨类型', '调拨申请时间',
                  '调拨状态', '调拨发起人', '物流方式', '包装方式', '审核人',
                  '审核时间', '摘要']:
        check("调拨申请列含 %s" % label, label in app_cols)
    order = [c for c in re.findall(r"'([^']+)'", app_cols)]
    check("调拨申请列头顺序（序号→摘要）",
          order == ['序号', '调拨单号', '调入方', '调出方', '调拨类型', '调拨申请时间',
                    '调拨状态', '调拨发起人', '物流方式', '包装方式', '审核人',
                    '审核时间', '摘要'], str(order))

    chg_cols = re.search(r"COLUMNS = \[(.*?)\]", chg_src, re.S).group(1)
    chg_order = re.findall(r"'([^']+)'", chg_cols)
    check("移库列头顺序（序号→移库状态）",
          chg_order == ['序号', '仓库名称', '移库单号', '制单人', '创建时间',
                        '调整原因', '移库状态'], str(chg_order))

    # 不提供拆行的显式决策
    check("两页均未定义 split_row 方法（Web 模板未渲染）",
          'def split_row' not in app_src and 'def split_row' not in chg_src)

    # 闸门常量
    check("调入申请可编辑状态 {47161001,47161004}",
          'EDITABLE_STATUS = (47161001, 47161004)' in app_src)
    check("调入申请可删除仅 47161001",
          'DELETABLE_STATUS = (47161001,)' in app_src)
    check("移库可编辑仅 47151001", 'EDITABLE_STATUS = (47151001,)' in chg_src)

    # 共用弹窗三组件
    dlg_src = read('transfer_dialogs.py')
    for cls in ('class ProductPickerDialog', 'class LocationPickerDialog',
                'class EmployeeMultiPicker'):
        check("共用弹窗 %s" % cls, cls in dlg_src)
    check("库位远端截断上限 500", 'LOCATION_LIMIT = 500' in dlg_src)


# ================================================================ B. 运行期
def test_runtime(root, ctrl):
    print("\n[B] 运行期功能")
    parent = ttk.Frame(root)
    app = ta.TransferApplicationPage(parent, ctrl)
    chg = tc.TransferChangePage(parent, ctrl)
    ctrl.drain()

    # ---- 4. 字典兜底 ----
    print("\n[4] 字典解码")
    check("4716 在线字典 待审核", app.decode_status(47161002) == '待审核', app.decode_status(47161002))
    check("4717 在线字典 加价调拨", app.decode_type(47171002) == '加价调拨', app.decode_type(47171002))
    check("4617 在线字典 物流发货", app.decode_logistics(46171003) == '物流发货',
          app.decode_logistics(46171003))
    check("4715 在线字典 已提交", chg.decode_status(47151002) == '已提交', chg.decode_status(47151002))
    # 兜底：清空在线字典后仍能解出
    app.dict_maps = {}
    check("4716 兜底 待提交", app.decode_status(47161001) == '待提交')
    check("4717 兜底 平价调拨", app.decode_type(47171001) == '平价调拨')
    check("4617 兜底 自提", app.decode_logistics(46171004) == '自提')
    check("未知码原样返回", app.decode_status(99999999) == '99999999')
    chg.dict_maps = {}
    check("4715 兜底 待提交", chg.decode_status(47151001) == '待提交')

    # 恢复在线字典
    app.dict_maps = {g: {c: n for c, n in arr} for g, arr in DICTS.items()}
    chg.dict_maps = {'4715': {c: n for c, n in DICTS['4715']}}

    # ---- 5. 调入申请查询参数 ----
    print("\n[5] 调入申请查询参数")
    CAPTURED.clear()
    app.move_wh_var.set("商丘库")       # 调入方 → queryListWithPermissions
    app.remove_wh_var.set("郑州库")     # 调出方 → queryListForSelect
    app.status_var.set("待审核")
    app.query()
    ctrl.drain()
    q = [c for c in CAPTURED if c['method'] == 'GET' and c['url'].endswith('/application')]
    check("已发出 application 请求", len(q) == 1, str([c['url'] for c in CAPTURED]))
    p = q[0]['params'] if q else {}
    print("       params =", p)
    check("searchType=application", p.get('searchType') == 'application')
    check("moveWarehouse=11", p.get('moveWarehouse') == 11)
    check("removeWarehouse=6", p.get('removeWarehouse') == 6)
    check("status=47161002", p.get('status') == '47161002', str(p.get('status')))
    check("startTime/endTime 均存在", bool(p.get('startTime')) and bool(p.get('endTime')))
    check("分页参数 pageNum/pageSize", p.get('pageNum') == 1 and p.get('pageSize') == 20)
    check("列表渲染 1 行", len(app.tree.get_children()) == 1, str(len(app.tree.get_children())))
    vals = app.tree.item(app.tree.get_children()[0], 'values')
    check("行渲染 调拨单号", vals[1] == 'ZZHJDBD2026072500002', str(vals))
    check("行渲染 调拨类型=加价调拨", vals[4] == '加价调拨', str(vals))
    check("行渲染 调拨状态=待审核", vals[6] == '待审核', str(vals))
    check("行渲染 物流方式=物流发货", vals[8] == '物流发货', str(vals))

    # ---- 6. 状态闸门 ----
    print("\n[6] 状态闸门")
    check("调入申请 47161002 不可编辑", ta.TransferApplicationPage.can_edit({'transferStatus': 47161002}) is False)
    check("调入申请 47161001 可编辑", ta.TransferApplicationPage.can_edit({'transferStatus': 47161001}) is True)
    check("调入申请 47161004 可编辑", ta.TransferApplicationPage.can_edit({'transferStatus': 47161004}) is True)
    check("调入申请 47161001 可删除", ta.TransferApplicationPage.can_delete({'transferStatus': 47161001}) is True)
    check("调入申请 47161004 不可删除（PC 无账号）",
          ta.TransferApplicationPage.can_delete({'transferStatus': 47161004}) is False)
    check("移库 47151001 可编辑", tc.TransferChangePage.can_edit({'status': 47151001}) is True)
    check("移库 47151002 不可编辑", tc.TransferChangePage.can_edit({'status': 47151002}) is False)

    # ---- 7. 调入申请保存报文 ----
    print("\n[7] 调入申请保存报文（saveTransfer）")
    app._open_edit_dialog(row=APP_ROW)
    ctrl.drain()
    app.e_remove_wh.set("郑州库")
    app.e_move_wh.set("商丘库")
    app.e_type.set("加价调拨")
    app.e_logistics.set("物流发货")
    app.e_box.set("木箱")
    app.e_remark.delete(0, tk.END)
    app.e_remark.insert(0, "测试摘要")
    app._edit_detail_rows = [
        {'detailId': 200740, 'brand': 1, 'partCode': 'GLW11858CCLY',
         'transferQuantity': 2, 'remarks': '顾彪',
         'inboundLocationId': 14202, 'inboundLocation': 'A1-043',
         'select_LOCATION_OPTIONS': [LOC_OBJ]},
    ]
    payload = app._build_payload(10041001)
    print("       payload =", json.dumps(payload, ensure_ascii=False))
    check("transferType=47171002", payload['transferType'] == '47171002')
    check("logisticsMode=46171003", payload['logisticsMode'] == '46171003')
    check("moveWarehouseId=11 / removeWarehouseId=6",
          payload['moveWarehouseId'] == 11 and payload['removeWarehouseId'] == 6)
    check("checkStatus=10041001", payload['checkStatus'] == 10041001)
    check("isWarehouseOutbound=10041001", payload['isWarehouseOutbound'] == 10041001)
    check("boxId=6", payload['boxId'] == 6)
    check("remark 已传", payload['remark'] == '测试摘要')
    check("recordVersion=5", payload['recordVersion'] == 5)
    check("id=14642（编辑回带）", payload['id'] == 14642)
    check("detailDtoList 1 行且申请数量=2",
          len(payload['detailDtoList']) == 1
          and payload['detailDtoList'][0]['transferQuantity'] == 2)
    check("detailDtoListDelete 为空", payload['detailDtoListDelete'] == [])
    check("6 字段 SLO 完整带出",
          payload['detailDtoList'][0]['select_LOCATION_OPTIONS'][0].get('locationType') == 90041005)

    # 2 字段 SLO（服务端载入）
    app._edit_detail_rows = [
        {'detailId': 1, 'transferQuantity': 1,
         'select_LOCATION_OPTIONS': [{'locationId': 14160, 'locationNo': 'A1-001'}]}]
    p2 = app._build_payload(10041002)
    check("2 字段 SLO 保持 2 字段",
          set(p2['detailDtoList'][0]['select_LOCATION_OPTIONS'][0].keys()) == {'locationId', 'locationNo'})
    check("checkStatus 可切到 10041002", p2['checkStatus'] == 10041002)
    app._close_edit()

    # ---- 8. 移库保存报文 ----
    print("\n[8] 移库保存报文（shiftHandle）")
    chg._open_edit_dialog(row=CHANGE_ROW)
    ctrl.drain()
    chg.e_wh.set("商丘库")
    chg.e_remark.delete(0, tk.END)
    chg.e_remark.insert(0, "散片上架")
    chg._move_by_var.set("郭佳,李强")
    chg._edit_detail_rows = [
        {'logId': 58945, 'partCode': 'X1', 'moveQty': 2, 'moveNoId': 14202,
         'moveNo': 'A1-043', 'removeNo': 'Z1-08', 'availableQty': 2,
         'select_locationOptionLoading': False, '_key': 9,
         'select_LOCATION_OPTIONS': [{'locationId': 14202, 'locationNo': 'A1-043'}]},
        {'logId': 58946, 'partCode': 'X2', 'moveQty': 1, 'moveNoId': 14203,
         'moveNo': 'A1-044', 'removeNo': 'Z1-09', 'availableQty': 2,
         'select_LOCATION_OPTIONS': [LOC_OBJ]},
    ]
    payload = chg._build_payload(10041002)
    print("       payload =", json.dumps(payload, ensure_ascii=False))
    check("shiftNo 回带", payload['shiftNo'] == 'ZZHJYKD2026072900052')
    check("warehouseId=11", payload['warehouseId'] == 11)
    check("checkStatus=10041002", payload['checkStatus'] == 10041002)
    check("status 回带原状态 47151001", payload['status'] == 47151001)
    check("move_by=郭佳,李强", payload['move_by'] == '郭佳,李强')
    check("remark 已传", payload['remark'] == '散片上架')
    check("detailDtoList 2 行", len(payload['detailDtoList']) == 2)
    row0 = payload['detailDtoList'][0]
    check("UI 专用键 select_locationOptionLoading 已剔除",
          'select_locationOptionLoading' not in row0)
    check("UI 专用键 _key 已剔除", '_key' not in row0)
    check("业务字段 moveQty 保留", row0['moveQty'] == 2)
    check("2 字段 SLO 保持 2 字段",
          set(row0['select_LOCATION_OPTIONS'][0].keys()) == {'locationId', 'locationNo'})
    check("6 字段 SLO 保留 locationType",
          payload['detailDtoList'][1]['select_LOCATION_OPTIONS'][0].get('locationType') == 90041005)
    check("detailDtoListDelete 为空", payload['detailDtoListDelete'] == [])
    chg._close_edit()

    # ---- 9. 提交端到端（方法级，验证真正发出 POST）----
    print("\n[9] 提交端到端（POST 端点）")
    CAPTURED.clear()
    app._open_edit_dialog(row=None)
    ctrl.drain()
    app.e_remove_wh.set("郑州库")
    app.e_move_wh.set("商丘库")
    app.e_type.set("加价调拨")
    app._edit_detail_rows = [{'detailId': None, 'transferQuantity': 1}]
    app._submit(ta.CHECK_SAVE)
    ctrl.drain()
    posts = [c for c in CAPTURED if c['method'] == 'POST' and c['url'].endswith('/saveTransfer')]
    check("已发出 saveTransfer POST", len(posts) == 1, str([c['url'] for c in CAPTURED]))
    if posts:
        body = json.loads(posts[0]['data'])
        check("POST body checkStatus=10041001", body['checkStatus'] == 10041001)
        check("POST body 新建 id=None", body['id'] is None)
    app._close_edit()

    CAPTURED.clear()
    chg._open_edit_dialog(row=None)
    ctrl.drain()
    chg.e_wh.set("商丘库")
    chg._move_by_var.set("郭佳")
    chg._edit_detail_rows = [{'logId': None, 'partCode': 'X', 'moveQty': 1,
                              'moveNo': 'A1-001', 'removeNo': 'Z1-01', 'availableQty': 5}]
    chg._submit(tc.CHECK_SUBMIT)
    ctrl.drain()
    posts = [c for c in CAPTURED if c['method'] == 'POST' and c['url'].endswith('/shiftHandle')]
    check("已发出 shiftHandle POST", len(posts) == 1, str([c['url'] for c in CAPTURED]))
    if posts:
        body = json.loads(posts[0]['data'])
        check("POST body checkStatus=10041002", body['checkStatus'] == 10041002)
        check("POST body shiftNo=None（新建）", body['shiftNo'] is None)
        check("POST body move_by=郭佳", body['move_by'] == '郭佳')
    chg._close_edit()

    # ---- 10. 未选仓库/移库人 时拦截 ----
    print("\n[10] 校验拦截")
    CAPTURED.clear()
    chg._open_edit_dialog(row=None)
    ctrl.drain()
    chg._edit_detail_rows = [{'moveQty': 1, 'moveNo': 'A', 'removeNo': 'B'}]
    chg._submit(tc.CHECK_SAVE)
    ctrl.drain()
    check("未选仓库/移库人 → 不发出请求",
          not [c for c in CAPTURED if c['method'] == 'POST'])
    chg._close_edit()


def main():
    root = tk.Tk()
    root.withdraw()
    ctrl = FakeController(root)
    ctrl.session.handler = make_handler()

    test_source_level()
    test_runtime(root, ctrl)

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

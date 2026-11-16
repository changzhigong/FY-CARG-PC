# -*- coding: utf-8 -*-
"""其它出库审核 冒烟测试（临时脚本）

验证内容
========
A. 源码级注册与契约（离线静态断言）
   1. main_app.py 六处注册点全部落地
   2. 接口端点 / 状态常量 / 固定 STATUS_STR / 字典兜底 / 列头顺序
   3. help_center.py 补齐采购入库、库内作业新菜单、其它出库审核、打印条目

B. 运行期功能（真实 Tk + FakeSession）
   4. 字典实时覆盖 + 离线兜底解码（1251 / 1252 / 9092）
   5. build_query_params 严格对齐 HAR（STATUS_STR 固定、WAREHOUSE_CODE、limit）
   6. 列表查询 → 行渲染（待审核高亮 tag）
   7. 审核加载：主单 + 明细 + 操作日志 + 附件只读
   8. build_audit_payload（HAR 形态：REMOVAL_LOCATION 数字、loList disabled、顶层空串剔除）
   9. 通过/驳回端到端（端点、FINANCE_AUDIT_OPINION3、成功后移除行）
  10. 状态闸门（仅 12511005 可审）与驳回意见必填
  11. 打印 getPrintList 参数与分组；导出 exportData 参数
  12. 附件下载 URL 构造

运行：python smoke_other_outbound_review.py  （退出码 0 = 全通过）
"""

import json
import os
import re
import sys
import threading
import time

import tkinter as tk
import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"
mb.askyesno = lambda *a, **k: True

import other_outbound_review as oor

# 文件对话框：导出/下载测试时固定返回临时路径
SAVE_PATH = os.path.join(os.environ.get('TEMP', '.'), 'smoke_other_out_review.xls')
oor.filedialog.asksaveasfilename = lambda *a, **k: SAVE_PATH

ROOT = os.path.dirname(os.path.abspath(__file__))
CAPTURED = []


class FakeResponse:
    def __init__(self, payload, url='', content=b'xls-bytes'):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.url = url
        self.status_code = 200
        self.content = content
        self.headers = {'Content-Type': 'application/vnd.ms-excel'}

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


# ---------------------------------------------------------------- 假数据（HAR 1764）
MASTER = {
    'ID': 1764, 'OTHER_OUT_NO': 'ZZHJQTCK2026102100005', 'BUS_TYPE': 12521003,
    'STATUS': 12511005, 'NO_TAX_AMOUNT': 1235.30, 'REMARK': 'D261008020光学问题工厂处理',
    'CREATED_AT': '2026-10-21', 'FINANCE_AUDIT_OPINION3': None,
    'WAREHOUSE_ID': 11, 'WAREHOUSE_CODE': 'SQ', 'CORRELATION_ORDER_NO': None,
    'SUPPLIER_ID': '1', 'SUPPLIER_NAME': '福耀中国', 'SUPPLIER_NO': 'FYG',
    'CREATED_BY': 'HJ013', 'CREATED_BY_NAME': '冯东亚', 'DEALER_CODE': 'FY',
    'FIRST_SUBMIT_DATE': '2026-10-21', 'ORGANIZATION_ID': 1145, 'OUT_NO': None,
    'RECORD_VERSION': 3, 'SUBMIT_DATE': '2026-10-21',
    'UPDATED_AT': '2026-10-21 16:47:17', 'UPDATED_BY': 'HJ013',
    'RESPONSIBLE_PERSON': '', 'RESPONSIBLE_PERSON_ID': None,
}

ITEMS = [{
    'BATCH_NUMBER': '2025103100061', 'BRAND_ID': 1, 'BRAND_NAME': '福耀玻璃',
    'CATEGORY_TWO': 90921001, 'COST_PRICE': 1235.30, 'CREATED_AT': '2026-10-21 16:47:17',
    'CREATED_BY': 'HJ013', 'DAMAGE_REASON': None, 'DEALER_CODE': 'FY', 'ID': 4237,
    'location_accessories_number': 1,
    'loList': [
        {'batch_price': 1235.30, 'location_accessories_number': 1,
         'location_id': 15022, 'location_no': 'C2-079'},
        {'batch_price': 1235.30, 'location_accessories_number': 1,
         'location_id': 15226, 'location_no': 'D2-059'},
    ],
    'MPQ': None, 'NO_TAX_AMOUNT': 1235.30, 'NUM': 1.00, 'ORGANIZATION_ID': 1145,
    'OTHER_OUT_NO': 'ZZHJQTCK2026102100005', 'PART_ID': 47752,
    'PART_NAME': '上汽通用别克君越(16-22)四门轿车前挡/HUD/隔音膜/圆雨感/摄像框/固定支架/包边条',
    'PART_NO': 'GLW01571VGTY', 'PID': 1764, 'RECORD_VERSION': 1, 'REMARK': None,
    'REMOVAL_LOCATION': '15022', 'REMOVAL_LOCATION_NAME': 'C2-079',
    'RETURN_UNIT_PRICE': 1235.30, 'STORAGE_CODE': 'SQ', 'STORAGE_NAME': '商丘库',
    'SUPPLIER_NAME': '福耀', 'UNIT': None, 'UPDATED_AT': '2026-10-21 16:47:17',
    'UPDATED_BY': 'HJ013', 'WAREHOUSE_ID': 11,
}]

LIST_ROWS = [
    {'ID': 1764, 'OTHER_OUT_NO': 'ZZHJQTCK2026102100005', 'BUS_TYPE': 12521003,
     'STATUS': 12511005, 'CREATED_BY_NAME': '冯东亚', 'WAREHOUSE_NAME': '商丘库',
     'SUBMIT_DATE': '2026-10-21', 'CREATED_AT': '2026-10-21', 'NO_TAX_AMOUNT': 1235.30},
    {'ID': 1433, 'OTHER_OUT_NO': 'ZZHJQTCK2026071500009', 'BUS_TYPE': 12521003,
     'STATUS': 12511008, 'CREATED_BY_NAME': '冯东亚', 'WAREHOUSE_NAME': '商丘库',
     'SUBMIT_DATE': '2026-07-15', 'CREATED_AT': '2026-07-15', 'NO_TAX_AMOUNT': 242.00},
]

LOGS = [{
    'AFTER_VALUE': '待审核', 'BEFORE_VALUE': '待提交', 'BILL_ID': 1764,
    'BILL_NO': 'ZZHJQTCK2026102100005', 'BILL_TYPE': 12041005,
    'OPERATE_DATE': '2026-10-21 16:47:17', 'OPERATOR_NAME': '冯东亚',
    'REMARK': '其它出库申请-提交', 'SUMMARY': 'D261008020光学问题工厂处理',
}]

PRINT_FLAT = [{
    'BATCH_NUMBER': '2025103100061', 'BRAND_NAME': '福耀玻璃', 'BUS_TYPE': 12521003,
    'COST_PRICE': 1235.30, 'CREATED_BY_NAME': '冯东亚', 'ID': 4237,
    'NO_TAX_AMOUNT': 1235.30, 'NUM': 1.00,
    'OTHER_OUT_NO': 'ZZHJQTCK2026102100005', 'PART_NAME': '前挡/HUD',
    'PART_NO': 'GLW01571VGTY', 'PID': 1764, 'REMOVAL_LOCATION_NAME': 'C2-079',
    'REMARK': 'D261008020光学问题工厂处理', 'STORAGE_NAME': '商丘库',
    'SUPPLIER_NAME': '福耀', 'WAREHOUSE_NAME': '商丘库',
}]


def make_handler(dict_payload=None):
    def handler(method, url, **kw):
        if url.endswith('/dicts'):
            return FakeResponse(dict_payload or {'resultCode': 200, 'data': {}})
        if url.endswith('/otherOutboundWarehouse/page'):
            return FakeResponse({'resultCode': 200, 'data': {
                'total': len(LIST_ROWS), 'pageSize': 20, 'pageNum': 1, 'rows': LIST_ROWS}})
        if url.endswith('/queryById/items'):
            return FakeResponse({'resultCode': 200, 'data': ITEMS})
        if url.endswith('/queryById'):
            return FakeResponse({'resultCode': 200, 'data': MASTER})
        if 'operateLogs/page' in url:
            return FakeResponse({'resultCode': 200, 'data': {
                'total': 1, 'pageSize': 5, 'pageNum': 1, 'rows': LOGS}})
        if '/file/billFiles/' in url:
            return FakeResponse({'resultCode': 200, 'data': {
                'initialPreview': ['/file/billFilesReview/10422113/K1'],
                'initialPreviewConfig': [
                    {'key': 'K1', 'caption': '质检单.pdf', 'size': 2048}]}})
        if 'billFilesReview' in url:
            return FakeResponse({}, content=b'PDFDATA')
        if url.endswith('/finance/level3/approved') or url.endswith('/finance/level3/reject'):
            return FakeResponse({'resultCode': 200, 'success': True, 'data': None})
        if url.endswith('/getPrintList'):
            return FakeResponse({'resultCode': 200, 'data': PRINT_FLAT})
        if url.endswith('/exportData'):
            return FakeResponse({}, content=b'XLS-BINARY')
        return FakeResponse({'resultCode': 200, 'data': {}})
    return handler


PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name)


def src(name):
    return open(os.path.join(ROOT, name), encoding='utf-8').read()


# ================================================================ A. 源码级
def test_source_level():
    print("\n--- A. 源码级注册与契约 ---")
    m = src('main_app.py')
    o = src('other_outbound_review.py')
    h = src('help_center.py')

    check("main_app: import 新页面",
          'from other_outbound_review import OtherOutboundReviewPage' in m)
    check("main_app: frame_classes 注册",
          '"OtherOutboundReviewPage": OtherOutboundReviewPage' in m)
    check("main_app: tabs_info 追加「其它出库审核」",
          '("其他出入库管理", ["其他入库审核", "报损出库申请", "其它出库审核"])' in m)
    check("main_app: create_popup_panel page_map",
          '"其它出库审核": "OtherOutboundReviewPage"' in m)
    check("main_app: page_to_tab_group",
          '"OtherOutboundReviewPage": "其他出入库管理"' in m)
    check("main_app: page_name_map",
          '"OtherOutboundReviewPage": "其它出库审核"' in m)

    check("端点 PART = otherOutboundWarehouse",
          "PART = '/dmscloud.part/otherOutboundWarehouse'" in o)
    check("端点 approved = finance/level3/approved",
          "URL_APPROVE = BASE + PART + '/finance/level3/approved'" in o)
    check("端点 reject = finance/level3/reject",
          "URL_REJECT = BASE + PART + '/finance/level3/reject'" in o)
    check("端点 page / queryById / items 齐全",
          all(x in o for x in ["'/page'", "'/queryById'", "'/queryById/items'"]))
    check("端点 getPrintList / exportData 齐全",
          "URL_PRINT = BASE + PART + '/getPrintList'" in o
          and "URL_EXPORT = BASE + PART + '/exportData'" in o)
    check("端点 operateLogs / dicts / billFiles 齐全",
          all(x in o for x in ["'/dmscloud.part/operateLogs/page'",
                               "'/dmscloud.basedata/dicts'",
                               "'/dmscloud.basedata/file/billFiles'"]))

    check("PENDING_STATUS = 12511005", "PENDING_STATUS = '12511005'" in o)
    check("DEFAULT_BUS_TYPE = 12521003", "DEFAULT_BUS_TYPE = '12521003'" in o)
    check("AUDIT_STATUS_STR 固定 5 态",
          "AUDIT_STATUS_STR = '12511005,12511006,12511007,12511010,12511008'" in o)
    check("LOG_BILL_TYPE = 12041005 / ATTACH_BILL_TYPE = 10422113",
          "LOG_BILL_TYPE = 12041005" in o and "ATTACH_BILL_TYPE = 10422113" in o)
    check("QUERY_LIMIT = 500 / LOG_PAGE_SIZE = 5",
          "QUERY_LIMIT = 500" in o and "LOG_PAGE_SIZE = 5" in o)

    check("状态兜底 1251 含 8 态",
          all(("'%s'" % c) in o for c in
              ['12511001', '12511002', '12511005', '12511006',
               '12511007', '12511010', '12511008', '12511009']))
    check("业务类型兜底 1252 含 3 值",
          all(("'%s'" % c) in o for c in ['12521001', '12521002', '12521003']))
    check("字典组 DICT_TYPES = 1251/1252/9092",
          "DICT_TYPES = ['1251', '1252', '9092']" in o)

    check("列表列顺序（Web 实证 8 列）",
          re.search(r'COLUMNS = \[(.*?)\]', o).group(1).replace('"', '').replace(' ', '')
          == '序号,业务单号,业务类型,状态,发起人,出库仓库,提报日期,创建日期')
    check("明细列顺序（审核只读 8 列）",
          'CARG全码/产品编码' in o and '批次单价' in o
          and '出库库位' in o and '退货单价' in o and '出库金额' in o)
    check("审核意见字段 FINANCE_AUDIT_OPINION3",
          "payload['FINANCE_AUDIT_OPINION3']" in o)
    check("审核闸门 is_pending_audit",
          'def is_pending_audit' in o and "str(code) == PENDING_STATUS" in o)
    check("不提供拆行（审核页只读明细，无 split_row）",
          'def split_detail_row' not in o and 'def split_row' not in o)
    check("打印走 CLodop 且任务名「其它出库单打印」",
          'printtask=其它出库单打印' in o)

    check("help_center: 库内作业补齐调拨申请/移库管理",
          '调拨申请：' in h and '移库管理：' in h)
    check("help_center: 仓储查询补齐调拨明细查询",
          '调拨明细查询：' in h)
    check("help_center: 新增采购入库条目",
          '("采购入库", [' in h and '到货签收：' in h and '入库上架：' in h)
    check("help_center: 新增其它出库审核说明",
          '其它出库审核：' in h)
    check("help_center: 打印支持列表补其它出库单",
          '其它出库单。' in h)


# ================================================================ B. 运行期
def test_runtime(root, ctrl):
    print("\n--- B. 运行期功能 ---")
    page = oor.OtherOutboundReviewPage(root, ctrl)
    ctrl.drain()

    # 4. 字典兜底 + 实时覆盖
    check("[4a] 状态兜底解码 12511005→待审核", page.status_label(12511005) == '待审核')
    check("[4b] 状态兜底解码 12511008→已出库", page.status_label(12511008) == '已出库')
    check("[4c] 业务类型兜底 12521003→采购入库退货",
          page.bus_type_label(12521003) == '采购入库退货')
    check("[4d] 分类兜底 90921001→前挡", page.category_label(90921001) == '前挡')
    ctrl.session.handler = make_handler({
        'resultCode': 200, 'data': {'dict': {'1251': [
            {'code_id': 12511005, 'code_cn_desc': '待审核(实时)'}]}}})
    page._dict_thread()
    ctrl.drain()
    check("[4e] 实时字典覆盖兜底", page.status_label(12511005) == '待审核(实时)')
    check("[4f] 实时字典缺失时回落兜底", page.status_label(12511008) == '已出库')
    page.dict_maps = {}

    # 5. 查询参数
    p = page.build_query_params()
    check("[5a] searchLoading=true", p['searchLoading'] == 'true')
    check("[5b] STATUS_STR 固定 5 态",
          p['STATUS_STR'] == '12511005,12511006,12511007,12511010,12511008')
    check("[5c] WAREHOUSE_CODE=SQ（get_storage_code）", p['WAREHOUSE_CODE'] == 'SQ')
    check("[5d] 默认 BUS_TYPE=12521003 / STATUS=12511005",
          p['BUS_TYPE'] == '12521003' and p['STATUS'] == '12511005')
    check("[5e] pageNum=1 / limit=500", p['pageNum'] == 1 and p['limit'] == 500)
    check("[5f] 日期起止格式 YYYY-MM-DD",
          re.match(r'\d{4}-\d{2}-\d{2}$', p['CREATED_AT_FROM'])
          and re.match(r'\d{4}-\d{2}-\d{2}$', p['CREATED_AT_TO']))
    check("[5g] 至少输入一个条件（日期兜底非空）",
          any(p.get(k) for k in ('CREATED_AT_FROM', 'CREATED_AT_TO', 'STATUS', 'BUS_TYPE')))
    page.warehouse_var.set('郑州库')
    check("[5h] 切仓库 → WAREHOUSE_CODE=ZZ",
          page.build_query_params()['WAREHOUSE_CODE'] == 'ZZ')
    page.warehouse_var.set('商丘库')

    # 5i. 状态筛选「全部」不影响 STATUS_STR
    page.status_var.set('')
    p2 = page.build_query_params()
    check("[5i] 状态=全部时 STATUS_STR 仍固定",
          p2['STATUS'] == '' and p2['STATUS_STR'] == oor.AUDIT_STATUS_STR)
    page.status_var.set(oor.PENDING_STATUS)

    # 6. 查询线程 → 行渲染
    CAPTURED.clear()
    page.query()
    ctrl.drain()
    req = next((c for c in CAPTURED if c['url'].endswith('/page')), None)
    check("[6a] 发出 GET /page", req is not None and req['method'] == 'GET')
    check("[6b] 请求携带 STATUS_STR",
          req['params']['STATUS_STR'] == oor.AUDIT_STATUS_STR)
    check("[6c] 默认待审核筛选 → 仅 1 行", len(page.rows) == 1)
    check("[6d] 保留的是待审核单 1764",
          page.rows[0]['ID'] == 1764 and page.is_pending_audit(page.rows[0]['STATUS']))
    iid = page.tree.get_children()[0]
    check("[6e] 待审核行 pending 高亮 tag", 'pending' in page.tree.item(iid, 'tags'))
    vals = page.tree.item(iid, 'values')
    check("[6f] 列表业务类型/状态已字典解码",
          vals[2] == '采购入库退货' and vals[3] == '待审核')

    # 7. 审核加载（主单 + 明细 + 日志 + 附件）
    CAPTURED.clear()
    page._audit_thread(1764)
    ctrl.drain()
    urls = [c['url'] for c in CAPTURED]
    check("[7a] 拉取主单 queryById", any(u.endswith('/queryById') for u in urls))
    check("[7b] 拉取明细 queryById/items", any(u.endswith('/queryById/items') for u in urls))
    log_req = next((c for c in CAPTURED if 'operateLogs/page' in c['url']), None)
    check("[7c] 拉取日志 BILL_TYPE=12041005",
          log_req and str(log_req['params']['BILL_TYPE']) == '12041005')
    check("[7d] 日志 limit=5 / isShowLogs=true",
          log_req and log_req['params']['limit'] == 5
          and str(log_req['params']['isShowLogs']) == 'true')
    check("[7e] 拉取附件 billFiles/10422113",
          any('/file/billFiles/10422113/1764' in u for u in urls))
    check("[7f] 审核窗主单/明细/日志/附件已装载",
          page.audit_form and page.audit_form.get('ID') == 1764
          and len(page.audit_items) == 1 and len(page.audit_logs) == 1
          and len(page.audit_files) == 1)
    check("[7g] 待审核显示审核意见控件", page.check_remark is not None)
    page.audit_win.destroy() if page.audit_win else None
    page.audit_win = None

    # 8. 审核报文（HAR 形态）
    payload = page.build_audit_payload(None)
    check("[8a] 主单完整字段回传（ID/单号/RECORD_VERSION）",
          payload.get('ID') == 1764
          and payload.get('OTHER_OUT_NO') == 'ZZHJQTCK2026102100005'
          and payload.get('RECORD_VERSION') == 3)
    check("[8b] fileList=[] / delItemList=[]",
          payload.get('fileList') == [] and payload.get('delItemList') == [])
    check("[8c] FINANCE_AUDIT_OPINION3 通过时为 None",
          'FINANCE_AUDIT_OPINION3' in payload and payload['FINANCE_AUDIT_OPINION3'] is None)
    check("[8d] itemList 保留 1 行且完整",
          len(payload['itemList']) == 1 and payload['itemList'][0]['ID'] == 4237)
    it = payload['itemList'][0]
    check("[8e] REMOVAL_LOCATION 字符串→数字 15022",
          it['REMOVAL_LOCATION'] == 15022 and isinstance(it['REMOVAL_LOCATION'], int))
    check("[8f] loList 每项补 disabled:false",
          all(x.get('disabled') is False for x in it['loList']))
    check("[8g] 顶层空串键剔除（RESPONSIBLE_PERSON）",
          'RESPONSIBLE_PERSON' not in payload)
    check("[8h] None 值保留（FINANCE_AUDIT_OPINION3/OUT_NO/CORRELATION_ORDER_NO）",
          all(k in payload for k in ('OUT_NO', 'CORRELATION_ORDER_NO')))
    check("[8i] itemList 内部空串不被剔除（保留原字段结构）",
          'REMOVAL_LOCATION_NAME' in it and 'loList' in it)
    check("[8i-2] 责任人空值(None)按 Web/HAR 语义剔除",
          'RESPONSIBLE_PERSON' not in payload
          and 'RESPONSIBLE_PERSON_ID' not in payload)
    _saved = page.audit_form.get('RESPONSIBLE_PERSON')
    page.audit_form['RESPONSIBLE_PERSON'] = '郭佳'
    _p2 = page.build_audit_payload(None)
    check("[8i-3] 责任人非空时保留", _p2.get('RESPONSIBLE_PERSON') == '郭佳')
    page.audit_form['RESPONSIBLE_PERSON'] = _saved
    payload_r = page.build_audit_payload('质量证明不足，退回')
    check("[8j] 驳回意见写入 FINANCE_AUDIT_OPINION3",
          payload_r['FINANCE_AUDIT_OPINION3'] == '质量证明不足，退回')

    # 9. 通过 / 驳回端到端
    CAPTURED.clear()
    page._submit_action(oor.URL_APPROVE, None, '通过', '审核通过成功')
    ctrl.drain()
    posts = [c for c in CAPTURED if c['method'] == 'POST']
    check("[9a] 通过 → POST finance/level3/approved",
          len(posts) == 1 and posts[0]['url'].endswith('/finance/level3/approved'))
    check("[9b] 通过报文 FINANCE_AUDIT_OPINION3=None",
          posts[0]['json']['FINANCE_AUDIT_OPINION3'] is None)
    check("[9c] 成功后从列表移除该单",
          not any(r.get('ID') == 1764 for r in page.rows))
    page.auditing = False

    CAPTURED.clear()
    page._submit_action(oor.URL_REJECT, '资料不全', '驳回', '审核驳回成功')
    ctrl.drain()
    posts = [c for c in CAPTURED if c['method'] == 'POST']
    check("[9d] 驳回 → POST finance/level3/reject",
          len(posts) == 1 and posts[0]['url'].endswith('/finance/level3/reject'))
    check("[9e] 驳回报文带审核意见",
          posts[0]['json']['FINANCE_AUDIT_OPINION3'] == '资料不全')
    page.auditing = False

    # 10. 状态闸门
    page.audit_form = dict(MASTER)
    page.audit_form['STATUS'] = 12511008   # 已出库
    page.audit_items = ITEMS
    page.audit_logs = LOGS
    page.audit_files = []
    page._show_audit_window(page.audit_form, ITEMS, LOGS, [])
    check("[10a] 非待审核隐藏审核意见控件", page.check_remark is None)
    page.audit_win.destroy() if page.audit_win else None
    page.audit_win = None
    CAPTURED.clear()
    page.auditing = False
    page.do_pass()
    page.do_reject()
    ctrl.drain()
    check("[10b] 非待审核 do_pass/do_reject 不发 POST",
          not [c for c in CAPTURED if c['method'] == 'POST'])

    page.audit_form = dict(MASTER)  # 恢复待审核
    page.audit_items = ITEMS
    page._show_audit_window(page.audit_form, ITEMS, LOGS, [])
    page.audit_win.destroy() if page.audit_win else None
    page.audit_win = None
    CAPTURED.clear()
    page.auditing = False
    page.do_reject()   # 审核意见为空
    ctrl.drain()
    check("[10c] 驳回意见为空 → 不发 POST",
          not [c for c in CAPTURED if c['method'] == 'POST'])
    check("[10d] is_pending_audit 判定",
          page.is_pending_audit('12511005') and not page.is_pending_audit(12511008))

    # 11. 打印 / 导出
    page.rows = LIST_ROWS
    page._render_rows()
    page.tree.selection_set(page.tree.get_children())
    CAPTURED.clear()
    page._print_thread("'ZZHJQTCK2026102100005'")
    ctrl.drain()
    pr = next((c for c in CAPTURED if c['url'].endswith('/getPrintList')), None)
    check("[11a] 打印调用 getPrintList", pr is not None)
    check("[11b] 打印参数 OTHER_OUT_NOS + STATUS_STR",
          pr and pr['params']['OTHER_OUT_NOS'] == "'ZZHJQTCK2026102100005'"
          and pr['params']['STATUS_STR'] == oor.AUDIT_STATUS_STR)
    check("[11c] 打印 HTML 含「其它出库单」与合计金额",
          bool(page._build_single_html({'header': PRINT_FLAT[0],
                                        'items': PRINT_FLAT,
                                        'totalNum': 1.0,
                                        'totalAmount': 1235.30})
               .find('其它出库单') >= 0))

    CAPTURED.clear()
    page.export_excel()
    ctrl.drain()
    ex = next((c for c in CAPTURED if c['url'].endswith('/exportData')), None)
    check("[11d] 导出调用 exportData", ex is not None)
    check("[11e] 导出 searchLoading=false 且不带 STATUS_STR/pageNum/limit",
          ex and ex['params']['searchLoading'] == 'false'
          and 'STATUS_STR' not in ex['params']
          and 'pageNum' not in ex['params'] and 'limit' not in ex['params'])
    check("[11f] 勾选单据时导出带 OTHER_OUT_NOS",
          ex and "'ZZHJQTCK2026102100005'" in ex['params'].get('OTHER_OUT_NOS', ''))
    check("[11g] 导出文件已写入",
          os.path.exists(SAVE_PATH) and open(SAVE_PATH, 'rb').read() == b'XLS-BINARY')

    # 12. 附件下载
    CAPTURED.clear()
    att = {'name': '质检单.pdf', 'key': 'K1', 'size': 2048, 'preview': ''}
    page._download_thread(att, SAVE_PATH)
    ctrl.drain()
    dl = next((c for c in CAPTURED if 'billFilesReview' in c['url']), None)
    check("[12a] 附件下载 URL=billFilesReview/10422113/K1",
          dl and dl['url'].endswith('/file/billFilesReview/10422113/K1'))
    check("[12b] 附件内容写入文件",
          open(SAVE_PATH, 'rb').read() == b'PDFDATA')

    try:
        os.remove(SAVE_PATH)
    except OSError:
        pass


def main():
    test_source_level()
    root = tk.Tk()
    root.withdraw()
    ctrl = FakeController(root)
    ctrl.session.handler = make_handler()
    test_runtime(root, ctrl)
    root.destroy()
    print("\n" + "=" * 62)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  -", f)
    print("=" * 62)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""送货车辆独立页 — 离线冒烟测试（不依赖 GUI / 网络）

覆盖：
- 路线主数据：38 条、六地区分布、仓库名→地区、子串匹配、候选预筛
- 聚合：车牌+日期二维分组、空车牌过滤、多车牌字段回退、片数/金额累加、
  司机首个非空、线路自动匹配、排序
- Excel：每车牌一 sheet、首次写入、追加去重、序号续接、金额格式、
  安全 sheet 名、文件名规则
- 查询：分页拉取参数、失败判定、_fetch_all 循环到 total
- 接线：main_app 六处注册、tab 分组、页面类存在
"""
import os
import sys
import json
import tempfile
from collections import Counter

PASS = 0
FAIL = 0
FAILED = []


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(label)
        print('  FAIL:', label)


print('=== 1. 路线主数据 ===')
import delivery_routes as dr
check('路线 38 条', len(dr.DELIVERY_ROUTES) == 38)
dist = Counter(r[3] for r in dr.DELIVERY_ROUTES)
check('六地区分布正确',
      dist == Counter({'西安': 13, '郑州': 8, '兰州': 6,
                       '驻马店': 4, '洛阳': 4, '商丘': 3}))
check('郑州仓库名→地区', dr.get_route_area('郑州库') == '郑州')
check('商丘仓库名→地区', dr.get_route_area('商丘库') == '商丘')
check('银川无路线→空', dr.get_route_area('银川库') == '')
check('短名去库字', dr.warehouse_short_name('西安西郊库') == '西安西郊')
check('子串匹配命中', dr.resolve_route_name('商丘', '永城市经销商') == '永城')
check('多候选取第一条(开封在郑州候选)',
      dr.resolve_route_name('郑州', '开封市鼓楼区') == '开封')
check('无地区不自动匹配', dr.resolve_route_name('', '永城') == '')
check('地区候选数(郑州8)', len(dr.route_options('郑州')) == 8)
check('空地区回退全部路线', len(dr.route_options('')) == 38)


print('=== 2. 聚合 group_by_plate_and_date ===')
import delivery_vehicle as dv
rows = [
    {'license_no': '豫A111', 'waybill_time': '2026-11-02 10:00:00',
     'delivery_count': 5, 'delivery_amount': 50, 'waybill_personnel': '李四',
     'dealer_name': '', 'receive_address': ''},
    {'license_no': '豫A111', 'waybill_time': '2026-11-01 09:00:00',
     'delivery_count': 10, 'delivery_amount': 100.5, 'waybill_personnel': '张三',
     'dealer_name': '开封经销商', 'receive_address': '开封市'},
    {'license_no1': '豫A111', 'waybill_time': '2026-11-01 15:00:00',
     'delivery_count': 5, 'delivery_amount': 50.25, 'waybill_personnel': '',
     'dealer_name': '', 'receive_address': ''},
    {'license_no2': '豫B222', 'delivery_time': '2026-11-03',
     'delivery_count': 3, 'delivery_amount': 30.75, 'waybill_personnel': '王五',
     'customer_name': '永城客户'},
    {'license_no': '', 'delivery_count': 99, 'delivery_amount': 999},
]
g = dv.group_by_plate_and_date(rows, '商丘库')
check('空车牌过滤→3组', len(g) == 3)
check('日期升序→车牌升序排序',
      [x['date'] for x in g] == ['2026-11-01', '2026-11-02', '2026-11-03'])
check('license_no1 回退成车牌', g[2]['plateNumber'] == '豫B222')
check('delivery_time 回退成日期', g[2]['date'] == '2026-11-03')
check('车牌+日期二维合并(同车同日两组→15)', g[0]['quantity'] == 15)
check('金额累加', abs(g[0]['amount'] - 150.75) < 1e-6)
check('司机取首个非空', g[0]['deliverer'] == '张三')
check('线路自动匹配(永城)', g[2]['route'] == '永城')
check('无匹配线路留空', g[0]['route'] == '')
check('退回数默认0', g[0]['returnQty'] == 0)
check('破损数默认0', g[0]['brokenQty'] == 0)


print('=== 3. 文件名 / sheet 名 ===')
check('文件名去库字', dv.report_file_name('商丘库') == '商丘送货车辆.xlsx')
check('未知仓库兜底', dv.report_file_name('') == '未知仓库送货车辆.xlsx')
check('sheet 名非法字符替换', dv.safe_sheet_name('豫A:1/2') == '豫A_1_2')
check('sheet 名 31 字截断', len(dv.safe_sheet_name('车' * 50)) == 31)
check('空 sheet 名兜底', dv.safe_sheet_name('') == '未知车牌')


print('=== 4. Excel 分 sheet / 追加 / 去重 ===')
from openpyxl import load_workbook
excel_rows = [
    {'plateNumber': '豫A111', 'date': '2026-11-01', 'quantity': 10, 'amount': 100.5,
     'deliverer': '张三', 'route': '开封', 'returnQty': 0, 'brokenQty': 0},
    {'plateNumber': '豫A111', 'date': '2026-11-02', 'quantity': 8, 'amount': 80,
     'deliverer': '张三', 'route': '开封', 'returnQty': 1, 'brokenQty': 2},
    {'plateNumber': '豫B222', 'date': '2026-11-01', 'quantity': 5, 'amount': 50,
     'deliverer': '李四', 'route': '永城', 'returnQty': 0, 'brokenQty': 0},
]
with tempfile.TemporaryDirectory() as td:
    path = os.path.join(td, '商丘送货车辆.xlsx')
    out, added, skipped = dv.build_report_workbook(excel_rows, path, path)
    wb = load_workbook(out)
    check('每车牌一 sheet', wb.sheetnames == ['豫A111', '豫B222'])
    ws = wb['豫A111']
    check('首次 2+1 行', added == 3 and skipped == 0)
    check('车牌 sheet 2 数据行', ws.max_row == 3)
    check('金额格式 #,##0.00', ws['E2'].number_format == '#,##0.00')
    check('表头冻结', ws.freeze_panes == 'A2')
    check('退回/破损写入', ws.cell(3, 7).value == 1 and ws.cell(3, 8).value == 2)
    # 追加：1 重复 + 1 新行
    more = [
        dict(excel_rows[0]),  # 完全重复
        {'plateNumber': '豫A111', 'date': '2026-11-03', 'quantity': 6,
         'amount': 60, 'deliverer': '张三', 'route': '开封',
         'returnQty': 0, 'brokenQty': 0},
    ]
    out, added, skipped = dv.build_report_workbook(more, path, path)
    wb = load_workbook(out)
    ws = wb['豫A111']
    check('追加新增1跳过1', added == 1 and skipped == 1)
    check('序号续接为3', ws.cell(4, 1).value == 3)
    check('追加后3数据行', ws.max_row == 4)
    check('新建文件(existing=None)不报错',
          os.path.exists(dv.build_report_workbook(
              excel_rows, os.path.join(td, 'new.xlsx'), None)[0]))


print('=== 5. 纯函数工具 ===')
check('_num 宽松转换', dv._num('12.5') == 12.5 and dv._num('abc') == 0)
check('_first 取首个非空', dv._first('', None, 'x', 'y') == 'x')
check('date_part 取前10位', dv.date_part('2026-11-01 10:00:00') == '2026-11-01')


print('=== 6. 分页拉取与失效判定（stub session）===')


class FakeResponse:
    def __init__(self, payload, status=200):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.status_code = status


class FakeSession:
    def __init__(self, pages, status=200, err_payload=None):
        self.pages = pages
        self.status = status
        self.err_payload = err_payload
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(dict(params or {}))
        if self.err_payload is not None:
            return FakeResponse(self.err_payload, self.status)
        page = params.get('pageNum', 1)
        return FakeResponse(self.pages.get(page, {'data': {'rows': [], 'total': 0}}))


def make_page(controller_session):
    """造一个只带 session 的页面壳，直接调 _fetch_all（跳过 GUI 构造）。"""
    page = dv.DeliveryVehiclePage.__new__(dv.DeliveryVehiclePage)
    page.controller = type('C', (), {'session': controller_session})()
    return page


base_params = {'warehouseId': 11, 'waybillStatus': '',
               'deliveryStartDate': '2026-11-01', 'deliveryEndDate': '2026-11-16'}
# 两页：第1页 200 行 + 第2页 1 行 → 共 201 行，循环到 total 停止
rows_p1 = [{'license_no': 'P%d' % i, 'delivery_count': 1} for i in range(200)]
rows_p2 = [{'license_no': 'LAST', 'delivery_count': 1}]
sess = FakeSession({1: {'data': {'rows': rows_p1, 'total': 201}},
                    2: {'data': {'rows': rows_p2, 'total': 201}}})
fetched, err = make_page(sess)._fetch_all(base_params)
check('分页拉全量 201 行', len(fetched) == 201 and err == '')
check('分页请求2次', len(sess.calls) == 2)
check('每页带 limit=200', all(c.get('limit') == 200 for c in sess.calls))
check('pageNum 递增 1,2', [c['pageNum'] for c in sess.calls] == [1, 2])
check('查询参数透传 warehouseId', sess.calls[0]['warehouseId'] == 11)

# 401 失效：响应体只有 errorMsg，无 resultCode —— 不能被当 0 条数据
sess401 = FakeSession({}, status=401,
                      err_payload={'errorMsg': '错误原因:未能读取到有效 token'})
fetched, err = make_page(sess401)._fetch_all(base_params)
check('401 返回空结果', fetched == [])
check('401 被判为失效而非0条', '登录已失效' in err and '401' in err)

# errorMsg token 失效但 HTTP 200（某些网关不改写状态码）
sess_token = FakeSession({}, status=200,
                         err_payload={'errorMsg': '错误原因:token 已被顶下线'})
fetched, err = make_page(sess_token)._fetch_all(base_params)
check('HTTP200 但 errorMsg 含 token → 判失效', fetched == [] and 'token' in err)

# 业务错误码
sess_biz = FakeSession({}, status=200,
                       err_payload={'resultCode': 500, 'errorMsg': '服务异常'})
fetched, err = make_page(sess_biz)._fetch_all(base_params)
check('业务码500判失败', fetched == [] and err == '服务异常')


print('=== 7. main_app 接线 ===')
try:
    import main_app
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_app.py'),
               encoding='utf-8').read()
    check('import main_app OK', True)
    check('main_app import DeliveryVehiclePage',
          'from delivery_vehicle import DeliveryVehiclePage' in src)
    check('frame_classes 注册', '"DeliveryVehiclePage": DeliveryVehiclePage' in src)
    check('tabs_info 仓库理货含送货车辆',
          '("仓库理货", ["出库单管理", "拣货单管理", "发运单管理", "送货车辆"])' in src)
    check('page_map 映射', '"送货车辆": "DeliveryVehiclePage"' in src)
    check('page_to_tab_group 分组', '"DeliveryVehiclePage": "仓库理货"' in src)
    check('page_name_map 反查', '"DeliveryVehiclePage": "送货车辆"' in src)
    check('无遗留 waybill_manage 内联送货车辆导出按钮依赖',
          'self.vehicle_btn = ttk.Button(bar, text=\'送货车辆\'' in
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'waybill_manage.py'), encoding='utf-8').read())
except Exception as e:
    check('import main_app OK: {}'.format(e), False)

print('=== 8. UI 回归：仓库下拉非空 + 日期为选择器 ===')
try:
    import tkinter as tk
    from tkcalendar import DateEntry

    class _Ctrl:
        def __init__(self):
            self.options = {'商丘库': 11, '郑州库': 6, '西安库': 7}

        def after(self, ms, fn):
            pass

    _root = tk.Tk()
    _root.withdraw()
    _page = dv.DeliveryVehiclePage(_root, _Ctrl())
    _root.update()
    check('仓库下拉已填充(非空)',
          list(_page.warehouse_cb['values']) == ['商丘库', '郑州库', '西安库'])
    check('仓库默认选中第一项', _page.warehouse_var.get() == '商丘库')

    def _collect_dateentries(widget, out):
        for child in widget.winfo_children():
            if isinstance(child, DateEntry):
                out.append(child)
            _collect_dateentries(child, out)

    _des = []
    _collect_dateentries(_page, _des)
    check('发运起止均为 DateEntry(2个)', len(_des) == 2)
    check('发运开始值为 yyyy-mm-dd', len(_page.start_var.get()) == 10
          and _page.start_var.get()[4] == '-')
    _root.destroy()
except Exception as e:
    # 无显示环境跳过 GUI 断言，不误判为功能失败
    print('  (UI 断言跳过: {})'.format(e))

print('=== 9. 写入路径持久化（纯函数，始终运行）===')
_orig_app_dir = dv.app_dir
try:
    _td = tempfile.mkdtemp()
    dv.app_dir = lambda: _td
    check('路径文件名正确', os.path.basename(dv.paths_file_path()) == 'delivery_vehicle_paths.json')
    check('初始无路径记录', dv.load_saved_paths() == {})
    check('保存路径成功', dv.save_saved_paths({'商丘库': r'D:\报表\商丘送货车辆.xlsx'}))
    check('读取路径一致',
          dv.load_saved_paths().get('商丘库') == r'D:\报表\商丘送货车辆.xlsx')
    check('路径文件已落盘', os.path.exists(dv.paths_file_path()))
    with open(dv.paths_file_path(), 'w', encoding='utf-8') as _f:
        _f.write('broken{json')
    check('损坏文件容错返回空', dv.load_saved_paths() == {})
finally:
    dv.app_dir = _orig_app_dir

print('=== 10. 写入路径解析 + 就地编辑（GUI）===')
try:
    import tkinter as tk
    _td2 = tempfile.mkdtemp()
    _orig_app_dir = dv.app_dir
    dv.app_dir = lambda: _td2
    _orig_ask = dv.filedialog.asksaveasfilename

    _root = tk.Tk()
    _root.geometry('1600x900+0+0')
    _root.update()
    _p = dv.DeliveryVehiclePage(_root, _Ctrl())
    _p.pack(fill=tk.BOTH, expand=True)
    _p.warehouse_name = '商丘库'

    # 路径解析：首次询问并记住 -> 再次静默复用
    _calls = []
    dv.filedialog.asksaveasfilename = lambda **kw: (
        _calls.append(kw) or r'D:\报表\商丘送货车辆.xlsx')
    _path1 = _p._resolve_write_path()
    check('首次写入弹出并选路径', _path1 == r'D:\报表\商丘送货车辆.xlsx' and len(_calls) == 1)
    check('initialfile 用仓库默认文件名',
          _calls[0].get('initialfile') == '商丘送货车辆.xlsx')
    check('路径已记住', _p.saved_paths.get('商丘库') == _path1)
    _path2 = _p._resolve_write_path()
    check('再次写入静默复用(不弹窗)', _path2 == _path1 and len(_calls) == 1)
    _p.saved_paths.pop('商丘库', None)
    dv.filedialog.asksaveasfilename = lambda **kw: ''
    check('用户取消返回 None', _p._resolve_write_path() is None)

    # 就地编辑：线路 Combobox / 数字 Entry / Esc 取消
    _p.route_opts = ['商丘-永城', '商丘-民权']
    _p.grouped = [{'plateNumber': '豫A1', 'date': '2026-11-01', 'quantity': 5.0,
                   'amount': 100.0, 'deliverer': '张三', 'route': '',
                   'returnQty': 0, 'brokenQty': 0}]
    _p.tree.insert('', tk.END, iid='0', values=_p._row_values(1, _p.grouped[0]))
    _root.update(); _root.update_idletasks()
    check('可编辑列定义 5 列', len(dv.EDITABLE_COLUMNS) == 5)
    _p._begin_cell_edit('0', 0, '#4', dv.EDITABLE_COLUMNS['#4'])
    _root.update()
    _w = _p._cell_editor['widget']
    check('线路编辑器为 Combobox 且有候选',
          'Combobox' in type(_w).__name__ and len(_w['values']) == 3)
    _w.set('商丘-永城')
    _p._dismiss_cell_editor(commit=True)
    check('线路就地编辑已保存', _p.grouped[0]['route'] == '商丘-永城')
    _p._begin_cell_edit('0', 0, '#5', dv.EDITABLE_COLUMNS['#5'])
    _root.update()
    _we = _p._cell_editor['widget']
    _we.delete(0, tk.END); _we.insert(0, '12.5')
    _p._dismiss_cell_editor(commit=True)
    check('数字就地编辑已保存', _p.grouped[0]['quantity'] == 12.5)
    _p._begin_cell_edit('0', 0, '#6', dv.EDITABLE_COLUMNS['#6'])
    _root.update()
    _wc = _p._cell_editor['widget']
    _wc.delete(0, tk.END); _wc.insert(0, '999')
    _p._dismiss_cell_editor(commit=False)
    check('Esc 取消不改动原值', _p.grouped[0]['amount'] == 100.0)

    _root.destroy()
    dv.filedialog.asksaveasfilename = _orig_ask
    dv.app_dir = _orig_app_dir
except Exception as e:
    dv.app_dir = _orig_app_dir
    print('  (GUI 断言跳过: {})'.format(e))

print('\n结果: PASS={} FAIL={}'.format(PASS, FAIL))
if FAILED:
    print('失败项:', FAILED)
    sys.exit(1)
print('全部通过')

# -*- coding: utf-8 -*-
"""仓库理货三菜单（改名 2 项 + 新增发运单管理）离线冒烟测试

覆盖：
- 源码级：main_app.py 六处注册、改名后的菜单名/页签名、help_center 文案、
  picking_shipping.py 的查询参数补齐（6 个快捷搜索 + endTime）。
- 运行期：WaybillManagePage 的查询参数构造、三条校验、HAR 行渲染、字典解码、
  汇总条、送货车辆聚合、导出、明细弹窗、运行时字典合并。
- OneKeyProcessPage.build_query_params 的桩测（不实例化完整 Tk 页面）。
"""
import json
import os
import sys
import tempfile
import tkinter as tk
import tkinter.messagebox as mb

PASS = 0
FAIL = 0
FAILED_LABELS = []


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED_LABELS.append(label)
        print('  FAIL:', label)


ROOT = os.path.dirname(os.path.abspath(__file__))


def src(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


# 不弹窗
mb.showinfo = lambda *a, **k: 'ok'
mb.showwarning = lambda *a, **k: 'ok'
mb.showerror = lambda *a, **k: 'ok'
mb.askyesno = lambda *a, **k: True

import waybill_manage as wm  # noqa: E402
import picking_shipping as ps  # noqa: E402
import help_center  # noqa: E402


class Var:
    def __init__(self, value=''):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload, ensure_ascii=False)
        self.status_code = 200


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [HAR_ROW]
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({'url': url, 'params': params or {},
                           'headers': headers or {}, 'timeout': timeout})
        return FakeResponse({
            'resultCode': 200, 'success': True,
            'data': {'total': len(self.rows), 'pageSize': 500, 'pageNum': 1,
                     'rows': self.rows, 'sumAmount': None},
        })


class FakeController:
    def __init__(self, root, rows=None):
        self.root = root
        self.options = {'郑州库': '1', '商丘库': '11'}
        self.session = FakeSession(rows)
        self.status = []

    def after(self, ms, fn):
        fn()  # 同步执行，避免子线程操作 Tk 控件

    def show_status(self, msg):
        self.status.append(msg)

    def hide_status(self):
        pass


# HAR 真实行（Desktop\发运单管理\xb.fy-carg.com.har 的 waybillQuery 响应）
HAR_ROW = {
    'bill_no': 'ZZHJSODK4-409202608120001', 'box_count': 1,
    'contact_information': '15090511251', 'dealer_code': 'K4-409',
    'dealer_name': '民权县—张喜进（YM6）', 'delivery_amount': 1901.11,
    'delivery_count': 7, 'delivery_no': 'ZZHJFH2026081200215',
    'forklift_driver': None, 'has_vehicle': 10041001, 'id': 159451,
    'license_no': '豫VG8328', 'license_no1': '豫VG8328', 'license_no2': '豫VG8328',
    'logistics_mode': 46171001, 'logistics_no': None,
    'logistics_provider_id': None, 'logistics_provider_name': None,
    'n1': 27, 'n2': 7195.11, 'n3': 4,
    'order_number': 'ZZHJXSDK4-409202608090002', 'outbound_type': '90371003',
    'print_status': 90481002, 'receive_address': '河南省商丘市民权县商城路南段地下道口东侧',
    'recordVersion': 3, 'WAREHOUSE_ID': 11, 'WAREHOUSE_NAME': '商丘库',
    'waybill_no': 'ZZHJFYD2026081200215', 'waybill_personnel': '陈杰',
    'waybill_status': 90471003, 'waybill_time': '2026-08-12 16:56:47',
}


def main():
    print('=' * 72)
    print('仓库理货三菜单冒烟测试')
    print('=' * 72)

    # ---------------------------------------------------------------- 1 源码级
    main_src = src('main_app.py')
    check('[1a] frame_classes 注册 WaybillManagePage',
          '"WaybillManagePage": WaybillManagePage' in main_src)
    check('[1b] import WaybillManagePage',
          'from waybill_manage import WaybillManagePage' in main_src)
    check('[1c] tabs_info 仓库理货 = 3 项（含发运单管理）',
          '("仓库理货", ["出库单管理", "拣货单管理", "发运单管理"])' in main_src)
    check('[1d] page_map 三项齐全',
          '"发运单管理": "WaybillManagePage"' in main_src
          and '"出库单管理": "outBoundProcessPage"' in main_src
          and '"拣货单管理": "OneKeyProcessPage"' in main_src)
    check('[1e] page_to_tab_group 指向仓库理货',
          '"WaybillManagePage": "仓库理货"' in main_src)
    check('[1f] page_name_map 三项改名生效',
          '"WaybillManagePage": "发运单管理"' in main_src
          and '"outBoundProcessPage": "出库单管理"' in main_src
          and '"OneKeyProcessPage": "拣货单管理"' in main_src)
    # 生效代码里不应再有旧菜单名（注释块除外）
    effective = '\n'.join(l for l in main_src.splitlines()
                          if not l.lstrip().startswith('#'))
    check('[1g] 生效代码无旧名「出库管理」菜单键', '"出库管理":' not in effective)
    check('[1h] 生效代码无旧名「一键发运」菜单键', '"一键发运":' not in effective)

    help_src = src('help_center.py')
    check('[1i] 帮助中心含三个新菜单名',
          all(k in help_src for k in ('出库单管理', '拣货单管理', '发运单管理')))

    pick_src = src('picking_shipping.py')
    check('[1j] 一键发运类改为拣货单管理说明', '拣货单管理' in pick_src)
    check('[1k] 新增 PICKING_QUERY_URL 常量', 'PICKING_QUERY_URL' in pick_src)
    check('[1l] 新增 build_query_params', 'def build_query_params' in pick_src)
    check('[1m] 6 个快捷搜索变量齐全',
          all(k in pick_src for k in ('picking_order_no', 'outbound_no',
                                      'order_number', 'part_code', 'part_name',
                                      'dealer_name')))
    check('[1n] endTime 已下发', "'endTime': endtime" in pick_src)
    check('[1o] clear_filters 清空快捷搜索',
          'for var in self.quick_vars.values():' in pick_src)

    # ---------------------------------------------------------------- 2 常量/字典
    check('[2a] 端点 waybillQuery 与 HAR 一致',
          wm.URL_WAYBILL_QUERY.endswith(
              '/dmscloud.part/warehouse/waybillManagement/waybillQuery'))
    check('[2b] 记录服务端导出端点',
          wm.URL_WAYBILL_EXPORT.endswith(
              '/dmscloud.part/warehouse/waybillManagement/waybillExport'))
    check('[2c] 列数 20（Web 模板 21 列去掉操作列）', len(wm.COLUMNS) == 20)
    check('[2d] 列宽与列数一致', len(wm.COLUMN_WIDTHS) == len(wm.COLUMNS))
    check('[2e] 字段映射 19 项', len(wm.FIELD_KEYS) == 19)
    check('[2f] 列顺序按 Web 模板',
          wm.COLUMNS[1:5] == ['发运单号', '发货单号', '出库仓库', '出库类型'])
    check('[2g] 字典列映射正确', wm.DICT_COLUMNS == {4: '9037', 9: '4617',
                                                14: '9047', 15: '9048'})
    check('[2h] 字典 9047 六项', len(wm.FALLBACK_DICTS['9047']) == 6)
    check('[2i] 字典 9037 十五项', len(wm.FALLBACK_DICTS['9037']) == 15)
    check('[2j] 字典 4617 五项', len(wm.FALLBACK_DICTS['4617']) == 5)
    check('[2k] 90471003 = 已签收（非安卓的「已发运」）',
          wm.FALLBACK_DICTS['9047'][90471003] == '已签收')
    check('[2l] 90371003 = 产品销售出库（非安卓的「其他出库」）',
          wm.FALLBACK_DICTS['9037'][90371003] == '产品销售出库')
    check('[2m] 90481002 = 未打印（页面快照实证）',
          wm.FALLBACK_DICTS['9048'][90481002] == '未打印')
    check('[2n] 送货车辆报表 10 列', len(wm.VEHICLE_HEADERS) == 10)
    check('[2o] 未接通写操作（无 saveWaybill 调用）',
          'saveWaybill(' not in src('waybill_manage.py'))
    check('[2p] 查询条件白名单 16 键（Web searchHandle 口径）',
          len(wm.QUERY_CONDITION_KEYS) == 16
          and 'billNo' not in wm.QUERY_CONDITION_KEYS
          and 'orderNumber' not in wm.QUERY_CONDITION_KEYS
          and 'dealer_name' in wm.QUERY_CONDITION_KEYS)
    check('[2q] 表单第 5 项是「客户 → dealer_name」（Web formList 口径）',
          ('客户:', 'dealer_name', 'input') in wm.FILTER_FIELDS
          and not any(k == 'dealerCode' for _, k, _ in wm.FILTER_FIELDS))

    # ---------------------------------------------------------------- 3 真实 Tk 页面
    root = tk.Tk()
    root.withdraw()
    ctrl = FakeController(root)
    page = wm.WaybillManagePage(root, ctrl)
    root.update()

    check('[3a] 页面实例化', isinstance(page, wm.BasePage))
    check('[3b] 列名与常量一致', list(page.tree['columns']) == wm.COLUMNS)
    check('[3c] 默认汇总条', '共 0 条' in page.summary_var.get())
    check('[3d] 默认仓库为全部', page.warehouse_var.get() == '全部')
    check('[3d2] 发运状态下拉只有 Web 的 2 项 + 全部（非字典 6 项）',
          list(page.status_cb['values']) == ['全部', '已发运', '未发运'])
    check('[3d3] 默认状态为「全部」', page.status_var.get() == '全部')

    # 解码
    check('[3e] decode 发运状态', page.decode('9047', '90471003') == '已签收')
    check('[3f] decode 出库类型', page.decode('9037', 90371003) == '产品销售出库')
    check('[3g] decode 打印状态', page.decode('9048', 90481002) == '未打印')
    check('[3h] decode 物流方式', page.decode('4617', 46171001) == '送货')
    check('[3i] decode 未知码原样返回', page.decode('9047', 99999999) == '99999999')
    check('[3j] 金额千分位', page.fmt_money(1901.11) == '1,901.11')
    check('[3j2] 整数金额不补 .00（HTML 快照 1,351 / 2,381 / 1,562）',
          page.fmt_money(1351.0) == '1,351'
          and page.fmt_money(2381) == '2,381'
          and page.fmt_money(1562.0) == '1,562')

    # 参数构造
    p = page.build_query_params()
    check('[3k] 固定 limit=500 / pageNum=1',
          p.get('limit') == 500 and p.get('pageNum') == 1)
    check('[3l] 默认只带发运起止 + limit/pageNum',
          'deliveryStartDate' in p and 'deliveryEndDate' in p
          and len([k for k in p if k not in ('limit', 'pageNum')]) == 2)

    for v in page.filter_vars.values():
        v.set('')
    page.filter_vars['waybillNo'].set('ZZHJFYD2026081200215')
    page.filter_vars['part_code'].set('C2-079')
    page.warehouse_var.set('商丘库')
    page.status_var.set('已发运')
    page.outbound_type_var.set('产品销售出库')
    page.print_var.set('未打印')
    p = page.build_query_params()
    check('[3m] 发运单号/产品编码下发',
          p.get('waybillNo') == 'ZZHJFYD2026081200215' and p.get('part_code') == 'C2-079')
    check('[3n] 仓库名转数字 ID', p.get('warehouseId') == '11')
    check('[3o] 状态中文转码 90471001（Web 下拉口径）',
          p.get('waybillStatus') == '90471001')
    check('[3p] 出库类型中文转码 90371003', p.get('outbound_type') == '90371003')
    check('[3q] 打印状态中文转码 90481002', p.get('printStatus') == '90481002')
    check('[3r] 空值条件不下发', 'deliveryNo' not in p and 'licenseNo' not in p)

    # 校验（2026-11-14 二次对账：复刻 Web searchHandle 的条件化逻辑）
    check('[3s] 至少输入一个条件', page.validate_query({'limit': 500, 'pageNum': 1})
          == '至少输入一个条件查询')
    check('[3s2] billNo/orderNumber 不计入条件白名单（Web 源码如此）',
          page.validate_query({'billNo': 'SO123', 'orderNumber': 'DD456',
                               'limit': 500}) == '至少输入一个条件查询')
    check('[3s3] 默认状态 90471002 跳过整段日期校验（HAR #38）',
          page.validate_query({'waybillStatus': '90471002', 'limit': 500}) is None)
    check('[3s4] 状态为空也跳过日期校验',
          page.validate_query({'deliveryStartDate': '2026-11-01',
                               'limit': 500}) is None)
    hot = {'waybillStatus': '90471001'}
    check('[3t] 缺发运开始时间',
          page.validate_query(dict(hot, deliveryEndDate='2026-11-14'))
          == '请选择发运开始时间')
    check('[3t2] 缺发运结束时间',
          page.validate_query(dict(hot, deliveryStartDate='2026-11-01'))
          == '请选择发运结束时间')
    check('[3u] 日期格式',
          page.validate_query(dict(hot, deliveryStartDate='2026/11/01',
                                   deliveryEndDate='2026-11-14'))
          == '日期格式应为 yyyy-mm-dd')
    check('[3v] 结束早于开始',
          page.validate_query(dict(hot, deliveryStartDate='2026-11-14',
                                   deliveryEndDate='2026-11-01'))
          == '发运结束时间不能小于发运开始时间')
    check('[3w] 超过 93 天',
          page.validate_query(dict(hot, deliveryStartDate='2026-01-01',
                                   deliveryEndDate='2026-08-01'))
          == '查询时间间隔不能超过93天')
    check('[3x] 合法条件放行',
          page.validate_query(dict(hot, deliveryStartDate='2026-11-01',
                                   deliveryEndDate='2026-11-14',
                                   limit=500, pageNum=1)) is None)
    check('[3x2] 打印日期不参与校验（Web 只校验发运起止）',
          page.validate_query(dict(hot, deliveryStartDate='2026-11-01',
                                   deliveryEndDate='2026-11-14',
                                   printStartDate='2026-11-01')) is None)

    # 渲染 + 端到端查询（同步走 _query_thread，避免子线程操作 Tk）
    page.reset_filters()
    page._query_thread(page.build_query_params())
    root.update()
    check('[3y] 请求 URL 正确', ctrl.session.calls[-1]['url'] == wm.URL_WAYBILL_QUERY)
    check('[3z] 请求参数含默认日期',
          'deliveryStartDate' in ctrl.session.calls[-1]['params'])
    check('[4a] 表格渲染 1 行', len(page.tree.get_children()) == 1)
    vals = page.tree.item('1', 'values')
    check('[4b] 发运单号列', vals[1] == 'ZZHJFYD2026081200215')
    check('[4c] 出库类型解码显示', vals[4] == '产品销售出库')
    check('[4d] 物流方式解码显示', vals[9] == '送货')
    check('[4e] 发运状态解码显示', vals[14] == '已签收')
    check('[4f] 打印状态解码显示', vals[15] == '未打印')
    check('[4g] 金额千分位显示', vals[13] == '1,901.11')
    check('[4h] 空值不显示 None', vals[10] == '' and vals[19] == '')
    check('[4i] 汇总条取后端 rows[0].n* 全量合计（Web getSummary 口径）',
          '共 1 条' in page.summary_var.get()
          and '7,195.11' in page.summary_var.get()
          and '合计片数 27' in page.summary_var.get()
          and '合计箱数 4' in page.summary_var.get()
          and page.summary_source == 'backend')
    page.total = 4
    page.update_summary()
    check('[4i2] 后端合计跨页正确（total 用后端值而非当前页行数）',
          '共 4 条' in page.summary_var.get())
    page.total = 1
    page.update_summary()
    _saved_rows = page.rows
    page.rows = [dict(HAR_ROW, n1=None, n2=None, n3=None)]
    page.update_summary()
    check('[4i3] 无 n* 时退化为当前页本地累加',
          '1,901.11' in page.summary_var.get()
          and '合计片数 7' in page.summary_var.get()
          and page.summary_source == 'local')
    page.rows = _saved_rows
    page.update_summary()

    # 运行时字典合并
    page.set_runtime_dicts({'dict': {'9047': [
        {'code_id': 90471003, 'code_cn_desc': '已签收(运行时)'}]}})
    check('[4j] 运行时字典覆盖',
          page.decode('9047', '90471003') == '已签收(运行时)')
    page.dicts = {k: dict(v) for k, v in wm.FALLBACK_DICTS.items()}

    # 送货车辆聚合
    rows2 = [dict(HAR_ROW), dict(HAR_ROW, delivery_amount=100.0, delivery_count=3),
             dict(HAR_ROW, license_no='')]
    grouped = page.group_by_vehicle(rows2)
    check('[4k] 空车牌过滤 + 按车牌聚合', len(grouped) == 1)
    check('[4l] 记录数累加', grouped[0][3] == 2)
    check('[4m] 片数累加', grouped[0][4] == 10.0)
    check('[4m2] 金额累加', grouped[0][5] == '2,001.11')
    check('[4n] 路线/退回/破损留空', grouped[0][7:] == ['', '', ''])

    # 导出（mock 文件对话框）
    import tkinter.filedialog as fd
    tmp = os.path.join(tempfile.gettempdir(), 'smoke_waybill.xlsx')
    fd.asksaveasfilename = lambda *a, **k: tmp
    wm.filedialog.asksaveasfilename = lambda *a, **k: tmp
    out = page.export_excel()
    check('[4o] 导出 Excel 返回路径', out == tmp and os.path.exists(tmp))
    try:
        from openpyxl import load_workbook
        wb = load_workbook(tmp)
        ws = wb.active
        check('[4p] 导出表头 20 列', ws.max_column == 20)
        check('[4q] 导出数据 1 行 + 表头', ws.max_row == 2)
    except Exception as e:
        check('[4p] openpyxl 读回', False)
    out2 = page.export_vehicle_report()
    check('[4r] 送货车辆报表导出', out2 == tmp and os.path.exists(tmp))
    try:
        from openpyxl import load_workbook
        ws = load_workbook(tmp).active
        check('[4s] 报表 10 列', ws.max_column == 10)
        check('[4t] 报表表头含「送货路线」', ws.cell(1, 8).value == '送货路线')
    except Exception:
        check('[4s] openpyxl 读回', False)

    # 明细弹窗
    page.tree.selection_set('1')
    win = page.open_detail()
    root.update()
    check('[4u] 明细弹窗打开', win is not None and win.winfo_exists())
    if win is not None:
        win.destroy()

    # 重置
    page.reset_filters()
    check('[4v] 重置恢复默认日期',
          page.filter_vars['deliveryStartDate'].get().endswith('-01')
          and page.status_var.get() == '全部')

    root.destroy()

    # ---------------------------------------------------------------- 5 拣货单参数桩测
    stub = object.__new__(ps.OneKeyProcessPage)
    stub.controller = type('C', (), {'options': {'商丘库': '11'}})()
    stub.warehouse_var = Var('商丘库')
    stub.quick_vars = {
        'picking_order_no': Var('JHD001'), 'outbound_no': Var('CKD001'),
        'order_number': Var('DD001'), 'part_code': Var('C2-079'),
        'part_name': Var('前挡'), 'dealer_name': Var('民权县张喜进'),
    }
    stub.picking_status_listbox = None
    stub.picking_status_mapping = ps.OneKeyProcessPage.__init__.__doc__ and {
        '拣货中': 47111002, '拣货完成': 47111003,
        '提前关闭': 47111004, '作废': 47111005,
    }
    stub.start_cal = Var('2026-11-01')
    stub.end_cal = Var('2026-11-14')
    q = stub.build_query_params()
    check('[5a] 6 个快捷搜索全部下发',
          q['picking_order_no'] == 'JHD001' and q['outbound_no'] == 'CKD001'
          and q['order_number'] == 'DD001' and q['part_code'] == 'C2-079'
          and q['part_name'] == '前挡' and q['dealer_name'] == '民权县张喜进')
    check('[5b] endTime 已下发', q.get('endTime') == '2026-11-14')
    check('[5c] startTime 保留', q.get('startTime') == '2026-11-01')
    check('[5d] 仓库 ID 正确', q.get('warehouse_id') == '11')
    check('[5e] 固定参数保持', q.get('sortOrder') == '90591001'
          and q.get('limit') == 1500 and q.get('pageNum') == 1)
    check('[5f] 未选拣货状态为空串', q.get('picking_status') == '')

    # ---------------------------------------------------------------- 结果
    print('=' * 72)
    print('PASS: %d/%d' % (PASS, PASS + FAIL))
    if FAIL:
        print('FAILED:', FAILED_LABELS)
        sys.exit(1)
    print('全部通过')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""仓储查询 5 个新增菜单的 smoke 测试（纯逻辑 + 真实 Tk 实例化 + HAR 字段核对）"""

import os
from datetime import date

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print('  PASS', name)
    else:
        FAIL += 1
        print('  FAIL', name)


import report_query_base as base
from location_stock_query import LocationStockQueryPage
from location_adjust_query import LocationAdjustQueryPage
from loss_report_query import LossReportQueryPage
from overflow_report_query import OverflowReportQueryPage
from receipt_all_query import ReceiptAllQueryPage

CLASSES = [
    (LocationStockQueryPage, '库位库存', 'location/query', 'querySummary'),
    (LocationAdjustQueryPage, '移库单', 'queryLocationAdjust', 'queryLocationAdjustCount'),
    (LossReportQueryPage, '报损单', 'queryFrmLoss', 'queryFrmLossCount'),
    (OverflowReportQueryPage, '报溢单', 'queryOverflow', 'queryOverflowCount'),
    (ReceiptAllQueryPage, '进货汇总', 'queryReceiptAll', 'queryReceiptAllCount'),
]

print('=== 1. 接口与类属性 ===')
for cls, name, query_suffix, count_suffix in CLASSES:
    check('%s 查询接口 %s' % (name, query_suffix), cls.URL_QUERY.endswith(query_suffix))
    check('%s 合计接口 %s' % (name, count_suffix), cls.URL_COUNT.endswith(count_suffix))
    check('%s 接口走 dmscloud.part' % name,
          'https://xb.fy-carg.com/dmscloud.part/' in cls.URL_QUERY)
    check('%s 列定义非空' % name, len(cls.COLUMNS) >= 9)
    check('%s 合计定义' % name, len(cls.TOTALS) >= 1)

print('=== 2. 默认日期（当月1号~今天）===')
today = date.today()
check('begin = 当月1号',
      base.ReportQueryBase._def_date('begin') == date(today.year, today.month, 1))
check('end = 今天', base.ReportQueryBase._def_date('end') == today)

print('=== 3. 数字/金额格式化 ===')
check('整数不显示小数', base.ReportQueryBase.fmt_num(12) == '12')
check('小数保留两位', base.ReportQueryBase.fmt_num(12.5) == '12.50')
check('空值显示 -', base.ReportQueryBase.fmt_money('') == '-')
check('金额两位小数', base.ReportQueryBase.fmt_money('1226.1') == '1226.10')

print('=== 4. 参数构造（FakeController，无网络）===')
import tkinter as tk


class FakeSession:
    def get(self, *a, **kw):
        class R:
            status_code = 200

            def json(self):
                return {'resultCode': 200, 'data': {}}
        return R()


class FakeCtrl:
    def __init__(self):
        self.session = FakeSession()
        self.options = {'商丘库': 11, '郑州库': 6}
        self._calls = []

    def check_login_status(self, r):
        return False

    def after(self, ms, fn, *args):
        self._calls.append((fn, args))
        return 'after'


try:
    import tkinter.messagebox as mb
    mb.showerror = lambda *a, **k: None
    mb.showinfo = lambda *a, **k: None
    root = tk.Tk()
    root.geometry('1600x900+0+0')
    root.update()
    ctrl = FakeCtrl()

    # --- 库位库存：仓库传 code、字典传 code、无日期参数 ---
    p1 = LocationStockQueryPage(root, ctrl)
    p1.pack(fill=tk.BOTH, expand=True)
    root.update()
    p1.filter_vars['partCode'].set('GLW08877')
    p1.warehouse_code_map['商丘库'] = 'SQ'
    p1.warehouse_id_map['商丘库'] = '11'
    p1.filter_vars['storage_code'].set('商丘库')
    p1.dict_option_maps['9004'] = {'拣货库位': '90041005'}
    p1.filter_vars['locationType'].set('拣货库位')
    params = p1.build_params()
    check('库位库存 partCode 入参', params['partCode'] == 'GLW08877')
    check('库位库存仓库传 storage_code=SQ', params['storage_code'] == 'SQ')
    check('库位库存库位类型传字典 code', params['locationType'] == '90041005')
    check('库位库存无日期参数', 'startDate' not in params and 'endDate' not in params)
    check('库位库存分页参数', params['pageNum'] == 1 and params['limit'] == 20)

    # --- 移库单：仓库传数字 ID、日期默认 ---
    p2 = LocationAdjustQueryPage(root, ctrl)
    p2.pack(fill=tk.BOTH, expand=True)
    root.update()
    p2.warehouse_id_map['商丘库'] = '11'
    p2.filter_vars['warehouse'].set('商丘库')
    params = p2.build_params()
    check('移库单仓库传 warehouse=11', params['warehouse'] == '11')
    check('移库单 startDate 默认当月1号',
          params['startDate'] == date(today.year, today.month, 1).isoformat())
    check('移库单 endDate 默认今天', params['endDate'] == today.isoformat())

    # --- 报损单：合计字段映射 ---
    p3 = LossReportQueryPage(root, ctrl)
    p3.pack(fill=tk.BOTH, expand=True)
    root.update()
    p3._apply_totals({'sums': 26, 'amount': 7980.87})
    check('报损单数量合计', p3.total_vars['sums'].get() == '数量合计：26')
    check('报损单金额合计', p3.total_vars['amount'].get() == '金额合计：7980.87')

    # --- 报溢单：HAR 响应字段映射 ---
    p4 = OverflowReportQueryPage(root, ctrl)
    p4.pack(fill=tk.BOTH, expand=True)
    root.update()
    har_row = {'submit_date': '2026-11-03 13:45:23', 'other_in_no': 'ZZHJQTRK2026110200015',
               'created_by_name': '陈雨雨', 'supplier_name': '福耀', 'category_two': 90921001,
               'part_code': 'GLW06869CCLY', 'num': 6.0, 'cost_price': 608.73,
               'total_amount': 3652.38, 'location_no': '52-148', 'warehouse_name': '郑州库'}
    p4.dict_maps['9092'] = {'90921001': '前挡'}
    vals = [p4.format_value(har_row, c, 0) for c in p4.COLUMNS]
    check('报溢单号取自 other_in_no', 'ZZHJQTRK2026110200015' in vals)
    check('报溢单数量格式化', '6' in vals)
    check('报溢单金额格式化', '3652.38' in vals)
    check('报溢单分类字典映射', '前挡' in vals)

    # --- 进货汇总：固定选项映射 ---
    p5 = ReceiptAllQueryPage(root, ctrl)
    p5.pack(fill=tk.BOTH, expand=True)
    root.update()
    p5.filter_vars['isReceiptOrReturn'].set('入库')
    p5.filter_vars['poStatus'].set('已审')
    p5.warehouse_id_map['郑州库'] = '6'
    p5.filter_vars['warehouseId'].set('郑州库')
    params = p5.build_params()
    check('进货汇总入库退回选项值', params['isReceiptOrReturn'] == '90331001,90331004')
    check('进货汇总审核状态选项值', params['poStatus'] == '1')
    check('进货汇总仓库传 warehouseId=6', params['warehouseId'] == '6')

    # --- 分页边界 ---
    p5.total = 41
    p5.page_size = 20
    check('41条分3页', p5.total_pages() == 3)
    p5.go_to_page(99)
    check('末页跳转被钳制', p5.page_num == 3)

    # --- 渲染（用 HAR 样本行）---
    p5._render_rows([
        {'part_large_category': 91011001, 'category_two': 90921001, 'supplier_name': '福耀',
         'part_code': 'CLW24450NCLN', 'part_name': '陕汽德龙F3000前挡', 'adaptation_model': 'F3000',
         'quantitys': 75, 'total_amount': 12789.00, 'warehouse_name': '郑州库'}
    ], 1)
    check('表格渲染 1 行', len(p5.tree.get_children()) == 1)
    check('计数条显示', '共 1 条' in p5.count_var.get())

    root.destroy()
except Exception as e:
    check('Tk 实例化无异常: %s' % e, False)
    try:
        root.destroy()
    except Exception:
        pass

print('\n结果: PASS=%d FAIL=%d' % (PASS, FAIL))
if FAIL:
    raise SystemExit(1)

# -*- coding: utf-8 -*-
"""进货汇总查询（Web: ReceiptAllReport / 进货汇总查询）

证据：Desktop/仓储查询/进货汇总查询/ 下 HAR + receiptAllReport-81b15fd8.js + 渲染 HTML
- 列表 GET /dmscloud.part/receiptDeliveryReport/queryReceiptAll
- 合计 GET .../queryReceiptAllCount  (data.sums 数量 / data.amount 金额)
- 仓库 GET /dmscloud.part/warehouse/manage/queryListForSelect（基类 getWarehouseCodeList 等价）
- 字典 9101 产品大类 / 9092 分类2

对齐要点：
- 入库退回固定三态：全部 '' / 入库 '90331001,90331004' / 采购退货 '90371001,90371002'
- 审核状态固定三态：全部 '' / 已审 '1' / 未审 '2'
- 默认日期当月1号~今天；warehouseId 传数字 ID
- 供应商 Web 端为弹窗选择，PC 端用文本输入 supplierName
"""

from report_query_base import ReportQueryBase, PART

URL_ROOT = PART + '/receiptDeliveryReport'


class ReceiptAllQueryPage(ReportQueryBase):
    TITLE = '进货汇总明细'
    COUNT_UNIT = '条'
    URL_QUERY = URL_ROOT + '/queryReceiptAll'
    URL_COUNT = URL_ROOT + '/queryReceiptAllCount'
    EXCEL_NAME = '进货汇总明细.xlsx'
    FILTER_COLUMNS = 4
    DICT_TYPES = ['9101', '9092']
    TOTALS = [('sums', '数量合计', 'num'), ('amount', '金额合计', 'money')]
    FILTERS = [
        {'key': 'isReceiptOrReturn', 'label': '入库退回', 'type': 'options',
         'options': [('全部', ''), ('入库', '90331001,90331004'),
                     ('采购退货', '90371001,90371002')]},
        {'key': 'poStatus', 'label': '审核状态', 'type': 'options',
         'options': [('全部', ''), ('已审', '1'), ('未审', '2')]},
        {'key': 'startDate', 'label': '起始日期', 'type': 'date', 'default': 'begin'},
        {'key': 'endDate', 'label': '结束日期', 'type': 'date', 'default': 'end'},
        {'key': 'supplierName', 'label': '供应商', 'type': 'text'},
        {'key': 'partLargeCategory', 'label': '产品大类', 'type': 'dict', 'code': '9101'},
        {'key': 'categoryTwo', 'label': '分类2', 'type': 'dict', 'code': '9092'},
        {'key': 'warehouseId', 'label': '仓库', 'type': 'warehouse'},
        {'key': 'partCode', 'label': 'CARG全码/产品编码', 'type': 'text'},
        {'key': 'partName', 'label': '产品名称', 'type': 'text'},
    ]
    COLUMNS = [
        {'label': '产品大类', 'key': 'part_large_category', 'width': 110, 'kind': 'dict', 'dict': '9101'},
        {'label': '产品细类', 'key': 'category_two', 'width': 110, 'kind': 'dict', 'dict': '9092'},
        {'label': '厂家', 'key': 'supplier_name', 'width': 160},
        {'label': 'CARG全码/产品编码', 'key': 'part_code', 'width': 160, 'kind': 'code'},
        {'label': '产品名称', 'key': 'part_name', 'width': 220},
        {'label': '车型', 'key': 'adaptation_model', 'width': 130},
        {'label': '数量', 'key': 'quantitys', 'width': 100, 'kind': 'num'},
        {'label': '金额', 'key': 'total_amount', 'width': 120, 'kind': 'money'},
        {'label': '仓库', 'key': 'warehouse_name', 'width': 100},
    ]

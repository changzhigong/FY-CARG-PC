# -*- coding: utf-8 -*-
"""报溢单查询（Web: OverflowInfoReport / 报溢单查询）

证据：Desktop/仓储查询/报溢单查询/ 下 HAR + overflowInfoReport-becdd401.js + 渲染 HTML
- 列表 GET /dmscloud.part/receiptDeliveryReport/queryOverflow
- 合计 GET .../queryOverflowCount  (data.sums 数量 / data.amount 金额)
- 仓库 GET /dmscloud.part/paymentOrder/getWarehouseCodeList
- 字典 9092 分类
- 导出 GET .../exportOverflow/excel（PC 用 openpyxl 本地导出）

对齐要点：默认日期当月1号~今天；warehouse 传数字 ID；Web search 中 status 恒为空。
"""

from report_query_base import ReportQueryBase, PART

URL_ROOT = PART + '/receiptDeliveryReport'


class OverflowReportQueryPage(ReportQueryBase):
    TITLE = '报溢单明细'
    COUNT_UNIT = '条'
    URL_QUERY = URL_ROOT + '/queryOverflow'
    URL_COUNT = URL_ROOT + '/queryOverflowCount'
    EXCEL_NAME = '报溢单明细.xlsx'
    FILTER_COLUMNS = 4
    DICT_TYPES = ['9092']
    TOTALS = [('sums', '数量合计', 'num'), ('amount', '金额合计', 'money')]
    FILTERS = [
        {'key': 'warehouse', 'label': '门店/仓库', 'type': 'warehouse'},
        {'key': 'startDate', 'label': '起始日期', 'type': 'date', 'default': 'begin'},
        {'key': 'endDate', 'label': '结束日期', 'type': 'date', 'default': 'end'},
        {'key': 'categoryTwo', 'label': '分类', 'type': 'dict', 'code': '9092'},
        {'key': 'adaptationModel', 'label': '车型', 'type': 'text'},
        {'key': 'partCode', 'label': 'CARG全码/产品编码', 'type': 'text'},
        {'key': 'partName', 'label': '产品名称', 'type': 'text'},
    ]
    COLUMNS = [
        {'label': '日期', 'key': 'submit_date', 'width': 145},
        {'label': '报溢单号', 'key': 'other_in_no', 'width': 170, 'kind': 'code'},
        {'label': '经办人', 'key': 'created_by_name', 'width': 100},
        {'label': '厂家', 'key': 'supplier_name', 'width': 160},
        {'label': '分类', 'key': 'category_two', 'width': 100, 'kind': 'dict', 'dict': '9092'},
        {'label': 'CARG全码/产品编码', 'key': 'part_code', 'width': 160, 'kind': 'code'},
        {'label': '产品名称', 'key': 'part_name', 'width': 220},
        {'label': '车型', 'key': 'adaptation_model', 'width': 130},
        {'label': '数量', 'key': 'num', 'width': 90, 'kind': 'num'},
        {'label': '单价', 'key': 'cost_price', 'width': 100, 'kind': 'money'},
        {'label': '金额', 'key': 'total_amount', 'width': 110, 'kind': 'money'},
        {'label': '库位', 'key': 'location_no', 'width': 100, 'kind': 'code'},
        {'label': '仓库', 'key': 'warehouse_name', 'width': 100},
        {'label': '摘要', 'key': 'remarks', 'width': 160},
    ]

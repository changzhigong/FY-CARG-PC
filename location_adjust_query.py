# -*- coding: utf-8 -*-
"""移库单查询（Web: LocationAdjust / 移库单查询）

证据：Desktop/仓储查询/移库单查询/ 下 HAR + locationAdjust-7292fdb7.js + 渲染 HTML
- 列表 GET /dmscloud.part/receiptDeliveryReport/queryLocationAdjust
- 合计 GET .../queryLocationAdjustCount  (data.sums 数量合计)
- 仓库 GET /dmscloud.part/paymentOrder/getWarehouseCodeList
- 导出 GET .../exportLocationAdjust/excel（Web window.location.href；PC 用 openpyxl 本地导出）
- 字典 9092 分类 / 9004 库位类型（表体原/新库位类型）

对齐要点：默认日期当月1号~今天；参数 warehouse 传仓库数字 ID；
Web getSummary 把合计放在「数量」列（第 15 列）。
"""

from report_query_base import ReportQueryBase, PART

URL_ROOT = PART + '/receiptDeliveryReport'


class LocationAdjustQueryPage(ReportQueryBase):
    TITLE = '移库单明细'
    COUNT_UNIT = '条'
    URL_QUERY = URL_ROOT + '/queryLocationAdjust'
    URL_COUNT = URL_ROOT + '/queryLocationAdjustCount'
    EXCEL_NAME = '移库单明细.xlsx'
    FILTER_COLUMNS = 4
    DICT_TYPES = ['9092', '9004']
    TOTALS = [('sums', '数量合计', 'num')]
    FILTERS = [
        {'key': 'startDate', 'label': '起始日期', 'type': 'date', 'default': 'begin'},
        {'key': 'endDate', 'label': '结束日期', 'type': 'date', 'default': 'end'},
        {'key': 'warehouse', 'label': '门店/仓库', 'type': 'warehouse'},
        {'key': 'onshelfBy', 'label': '上架员', 'type': 'text'},
        {'key': 'categoryTwo', 'label': '分类', 'type': 'dict', 'code': '9092'},
        {'key': 'adaptationModel', 'label': '车型', 'type': 'text'},
        {'key': 'partCode', 'label': 'CARG全码/产品编码', 'type': 'text'},
        {'key': 'partName', 'label': '产品名称', 'type': 'text'},
    ]
    COLUMNS = [
        {'label': '日期', 'key': 'created_at', 'width': 145},
        {'label': '移位单号', 'key': 'shift_no', 'width': 170, 'kind': 'code'},
        {'label': '仓库', 'key': 'warehouse_name', 'width': 100},
        {'label': '原库位', 'key': 'remove_no', 'width': 100, 'kind': 'code'},
        {'label': '原库位类型', 'key': 'remove_location_type', 'width': 110, 'kind': 'dict', 'dict': '9004'},
        {'label': '新库位', 'key': 'move_no', 'width': 100, 'kind': 'code'},
        {'label': '新库位类型', 'key': 'move_location_type', 'width': 110, 'kind': 'dict', 'dict': '9004'},
        {'label': '经办人', 'key': 'commit_by', 'width': 100},
        {'label': '上架人员', 'key': 'onshelf_by', 'width': 100},
        {'label': '厂家', 'key': 'supplier_name', 'width': 150},
        {'label': '分类', 'key': 'category_two', 'width': 100, 'kind': 'dict', 'dict': '9092'},
        {'label': 'CARG全码/产品编码', 'key': 'part_code', 'width': 160, 'kind': 'code'},
        {'label': '产品名称', 'key': 'part_name', 'width': 220},
        {'label': '车型', 'key': 'adaptation_model', 'width': 130},
        {'label': '数量', 'key': 'move_quantity', 'width': 90, 'kind': 'num'},
        {'label': '摘要', 'key': 'remark', 'width': 160},
    ]

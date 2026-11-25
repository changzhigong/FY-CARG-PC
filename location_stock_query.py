# -*- coding: utf-8 -*-
"""库位库存查询（Web: InventoryQuery / 库位库存查询）

证据：Desktop/仓储查询/库位库存查询/ 下 HAR + inventory-54d63bb3.js + 渲染 HTML
- 列表 GET /dmscloud.part/warehouse/asicDataQuery/inventoryQuery/location/query
- 合计 GET .../querySummary  (n1 库存数 / n2 冻结数 / n3 可用数 / n4 金额)
- 导出 GET .../exportExcel
- 仓库 GET /dmscloud.part/purchaseMngOem/getStoreList（基类用 getWarehouseCodeList 等价映射）
- 字典 9004 库位类型 / 9100 产品来源 / 9101 产品大类 / 9028 排序类型 / 9092 分类2 / 9090 分类4 / 9096 分类6

对齐要点：本页无日期条件（Web search 对象里 createdAtStart/End 恒为空），
多选字典在 PC 端退化为单选下拉（Tkinter Combobox 无原生多选），传值为单 code。
"""

from report_query_base import ReportQueryBase, PART

URL_ROOT = PART + '/warehouse/asicDataQuery/inventoryQuery/location'


class LocationStockQueryPage(ReportQueryBase):
    TITLE = '库位库存信息'
    COUNT_UNIT = '条'
    URL_QUERY = URL_ROOT + '/query'
    URL_COUNT = URL_ROOT + '/querySummary'
    EXCEL_NAME = '库位库存导出.xlsx'
    FILTER_COLUMNS = 4
    DICT_TYPES = ['9004', '9100', '9101', '9028', '9092', '9090', '9096']
    TOTALS = [
        ('n1', '库存数合计', 'num'),
        ('n2', '冻结数合计', 'num'),
        ('n3', '可用数合计', 'num'),
        ('n4', '金额合计', 'money'),
    ]
    FILTERS = [
        {'key': 'partCode', 'label': 'CARG全码/产品编码', 'type': 'text'},
        {'key': 'partName', 'label': '产品名称', 'type': 'text'},
        {'key': 'storage_code', 'label': '仓库', 'type': 'warehouse',
         'warehouse_value': 'code'},
        {'key': 'locationNo', 'label': '库位', 'type': 'text'},
        {'key': 'locationType', 'label': '库位类型', 'type': 'dict', 'code': '9004'},
        {'key': 'brandName', 'label': '品牌', 'type': 'text'},
        {'key': 'brandCn', 'label': '车辆品牌', 'type': 'text'},
        {'key': 'modelNumber', 'label': '车型', 'type': 'text'},
        {'key': 'modelYear', 'label': '年款', 'type': 'text'},
        {'key': 'productSource', 'label': '产品来源', 'type': 'dict', 'code': '9100'},
        {'key': 'part_large_category', 'label': '产品大类', 'type': 'dict', 'code': '9101'},
        {'key': 'categoryTwo', 'label': '分类2', 'type': 'dict', 'code': '9092'},
        {'key': 'partType', 'label': '分类4', 'type': 'dict', 'code': '9090'},
        {'key': 'categorySix', 'label': '分类6', 'type': 'dict', 'code': '9096'},
        {'key': 'sortType', 'label': '排序类型', 'type': 'dict', 'code': '9028'},
    ]
    COLUMNS = [
        {'label': '仓库', 'key': 'warehouse_name', 'width': 100},
        {'label': '库位', 'key': 'location_no', 'width': 110, 'kind': 'code'},
        {'label': 'CARG全码/产品编码', 'key': 'part_code', 'width': 160, 'kind': 'code'},
        {'label': '产品名称', 'key': 'part_name', 'width': 220},
        {'label': '品牌', 'key': 'brand_name', 'width': 110},
        {'label': '库位库存数', 'key': 'location_accessories_number', 'width': 110, 'kind': 'num'},
        {'label': '冻结数', 'key': 'location_freezing_number', 'width': 90, 'kind': 'num'},
        {'label': '可用数', 'key': 'residue_number', 'width': 90, 'kind': 'num'},
        {'label': '移动平均价', 'key': 'moving_average_price', 'width': 110, 'kind': 'money'},
        {'label': '合计', 'key': 'total_amount', 'width': 110, 'kind': 'money'},
        {'label': '库位类型', 'key': 'location_type', 'width': 100, 'kind': 'dict', 'dict': '9004'},
        {'label': '分类2', 'key': 'category_two', 'width': 100, 'kind': 'dict', 'dict': '9092'},
        {'label': '分类4', 'key': 'part_type', 'width': 100, 'kind': 'dict', 'dict': '9090'},
        {'label': '分类6', 'key': 'category_six', 'width': 100, 'kind': 'dict', 'dict': '9096'},
        {'label': '产品大类', 'key': 'part_large_category', 'width': 100, 'kind': 'dict', 'dict': '9101'},
        {'label': '车辆品牌', 'key': 'brand_cn', 'width': 100},
        {'label': '车型', 'key': 'model_number', 'width': 130},
        {'label': '年款', 'key': 'model_year', 'width': 80},
        {'label': '长', 'key': 'part_length', 'width': 80, 'kind': 'num'},
        {'label': '宽', 'key': 'part_width', 'width': 80, 'kind': 'num'},
        {'label': '中高', 'key': 'part_height', 'width': 80, 'kind': 'num'},
        {'label': '对角', 'key': 'part_diagonal', 'width': 80, 'kind': 'num'},
        {'label': '产品来源', 'key': 'product_source', 'width': 100, 'kind': 'dict', 'dict': '9100'},
    ]

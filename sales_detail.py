# -*- coding: utf-8 -*-
"""销售明细

对齐 fycarg-pda 安卓端 src/views/SalesDetail.vue，接口与业务逻辑保持一致：

- 列表：GET /dmscloud.part/salesProfit/queryDetail
- 合计：GET /dmscloud.part/salesProfit/queryDetailCount
- 导出：GET /dmscloud.part/salesProfit/query/excelDetail（limit=50000, searchLoading=false）

与前面模块的差异（关键坑位）：
1. 仓库参数用 storage_id（数字 ID），取自 warehouse_config.json 的 WAREHOUSE_OPTIONS
   （与装箱明细一致，而非库存冻结的 storage_code）。
2. 字典码表来自 /dmscloud.basedata/dicts（dict[type] = [{code_id, code_cn_desc}]），
   涉及 9101(产品大类) / 9092(分类2) / 9012(客户类型) / 4617(配送方式) /
   1195(管控方式) / 4622(结算方式)；页面初始化时异步拉取，下拉先显示「全部」。
3. 开单人来自 /dcscloud.basedata/.../internalUser；客户区域来自 /dcscloud.basedata/.../queryAreaList；
   线路来自 /dcscloud.basedata/.../queryList；品牌来自 /dmscloud.part/.../brandsdict；
   均异步加载，失败保留「全部」不影响查询。
4. 账单类型（销售出库=1 / 销售退货=2）为页面固定口径，非 dict 7012。
5. 多选字段 line(线路) / dealer_area(客户区域) 同时发送两种形态：
   逗号串（line=62,64）+ 数组形态（line1[]=62&line1[]=64，列表/合计用）；
   导出用 line1=62&line1=64（无 [] 后缀，对齐安卓端 paramsSerializer bracket=false）。
6. 编码序列化：searchLoading 发送字符串 'true'/'false'（非 Python 布尔，避免被序列成 True/False）。
7. 27 列表格；服务端分页 pageNum+limit，每页 20 条；序号为全局序号 (pageNum-1)*20+idx+1。
8. 合计条（笔数 / 数量合计 / 金额合计）来自 queryDetailCount，仅全新查询时刷新。
9. 导出 Excel：后端返回文件流（blob），按用户选择路径保存；若后端返回 JSON 错误则提示。
"""

import json
import threading
from datetime import date

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager

# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

# 接口地址（与安卓端 axios baseURL + path 一致）
URL_QUERY = 'https://xb.fy-carg.com/dmscloud.part/salesProfit/queryDetail'
URL_COUNT = 'https://xb.fy-carg.com/dmscloud.part/salesProfit/queryDetailCount'
URL_EXPORT = 'https://xb.fy-carg.com/dmscloud.part/salesProfit/query/excelDetail'
# 下拉数据源
URL_DICTS = 'https://xb.fy-carg.com/dmscloud.basedata/dicts'
URL_STORE = 'https://xb.fy-carg.com/dmscloud.part/purchaseMngOem/getStoreList'
URL_EMPLOYEE = 'https://xb.fy-carg.com/dcscloud.basedata/basedata/employees/employees/internalUser'
URL_AREA = 'https://xb.fy-carg.com/dcscloud.basedata/DealerData/queryAreaList'
URL_LINE = 'https://xb.fy-carg.com/dcscloud.basedata/transportRoute/queryList'
URL_BRAND = 'https://xb.fy-carg.com/dmscloud.part/vehicleProduct/brandsdict'
URL_DEALER = 'https://xb.fy-carg.com/dmscloud.basedata/DealerData/queryDealer'

# 每页条数（与安卓端 pageSize 保持一致）
PAGE_SIZE = 20

# 字典类型（对齐安卓端 dictOptions 调用）
DICT_TYPES = ['9101', '9092', '9012', '4617', '1195', '4622']
# type -> 中文标签（仅用于下拉占位/注释，实际选项来自接口）
DICT_LABELS = {
    '9101': '产品大类',
    '9092': '分类2',
    '9012': '客户类型',
    '4617': '配送方式',
    '1195': '管控方式',
    '4622': '结算方式',
}
# dict type -> 对应 Combobox 的变量名（用于 build_params 取值）
DICT_VAR_NAMES = {
    '4617': 'logistics_mode_var',
    '9101': 'part_large_category_var',
    '9092': 'category_two_var',
    '9012': 'dealer_type_var',
    '1195': 'funds_type_var',
    '4622': 'sett_method_var',
}

# 账单类型：页面固定口径（非 dict 7012），1=销售出库 / 2=销售退货
BILL_TYPE_OPTIONS = [
    ("全部", ""),
    ("销售出库", "1"),
    ("销售退货", "2"),
]

# 省份：GB/T 2260 省份码（value=region_id），离线可用、与后端值域一致
PROVINCE_OPTIONS = [
    ("北京市", "110000"), ("天津市", "120000"), ("河北省", "130000"), ("山西省", "140000"),
    ("内蒙古自治区", "150000"), ("辽宁省", "210000"), ("吉林省", "220000"), ("黑龙江省", "230000"),
    ("上海市", "310000"), ("江苏省", "320000"), ("浙江省", "330000"), ("安徽省", "340000"),
    ("福建省", "350000"), ("江西省", "360000"), ("山东省", "370000"), ("河南省", "410000"),
    ("湖北省", "420000"), ("湖南省", "430000"), ("广东省", "440000"), ("广西壮族自治区", "450000"),
    ("海南省", "460000"), ("重庆市", "500000"), ("四川省", "510000"), ("贵州省", "520000"),
    ("云南省", "530000"), ("西藏自治区", "540000"), ("陕西省", "610000"), ("甘肃省", "620000"),
    ("青海省", "630000"), ("宁夏回族自治区", "640000"), ("新疆维吾尔自治区", "650000"),
    ("台湾省", "710000"), ("香港特别行政区", "810000"), ("澳门特别行政区", "820000"),
]

# 列表列定义（对齐安卓端表头，27 列，顺序一致）
COLUMNS = ["序号", "销售单号", "账单号", "CARG全码", "产品名称", "产品大类", "分类2",
           "客户名称", "客户类型", "管控方式", "结算方式", "配送方式", "开单员", "品牌",
           "仓库", "库位", "数量", "含税单价", "含税金额", "折扣", "型号", "线路",
           "客户区域", "省份", "部门", "拣货人", "账单日期"]
COLUMN_WIDTHS = [50, 150, 170, 140, 220, 90, 70, 200, 90, 80, 80, 80, 90, 90,
                 80, 90, 70, 90, 100, 70, 150, 90, 90, 80, 90, 80, 150]


class SalesDetailPage(BasePage):
    """销售明细页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 当前页行数据（原始 dict 列表）
        self.total = 0            # 查询总条数
        self.page_num = 1         # 当前页码
        self.page_size = PAGE_SIZE
        self.queried = False      # 是否已执行过查询
        self.loading = False      # 请求进行中（防重入）
        self.exporting = False
        self.summary = {"counts": 0, "sums": 0, "amount": 0}
        # 字典码表：type -> {code: desc}
        self.dict_maps = {}
        # 字典下拉：type -> {desc(显示文本): code}
        self.dict_option_maps = {}
        # 开单人：名称 -> EMPLOYEE_NO
        self.created_by_map = {}
        # 客户区域 / 线路 选项（value->text）与当前多选
        self.area_options = []        # [(text, value)]
        self.area_value_to_text = {}
        self.line_options = []        # [(text, value)]
        self.line_value_to_text = {}
        self.dealer_area_values = []  # 已选区域 value 列表
        self.line_values = []         # 已选线路 value 列表
        # 品牌：名称 -> BRAND_ID
        self.brand_map = {}
        # 客户（经销商）
        self.dealer_code = ""
        self.show_more = False
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        """构建用户界面"""
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main_container)
        self.setup_count_bar(main_container)
        self.setup_data_table(main_container)
        self.setup_summary_bar(main_container)
        self.setup_pagination_controls(main_container)

        # 异步拉取下拉数据源（对齐安卓端 onMounted Promise.all）
        self.load_dicts()
        self.load_created_by()
        self.load_areas()
        self.load_lines()
        self.load_brands()

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        # ---- 常显条件（第 1 行）----
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="账单类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.bill_type_var = tk.StringVar(value="全部")
        self.bill_type_cb = ttk.Combobox(row1, textvariable=self.bill_type_var,
                                         values=[t for t, _ in BILL_TYPE_OPTIONS],
                                         state="readonly", width=10)
        self.bill_type_cb.set("全部")
        self.bill_type_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="开单人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.created_by_var = tk.StringVar(value="全部")
        self.created_by_cb = ttk.Combobox(row1, textvariable=self.created_by_var,
                                          values=["全部"], state="readonly", width=10)
        self.created_by_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="出货开始:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.begin_cal = DateEntry(row1, width=12, date_pattern='yyyy-mm-dd')
        self.begin_cal.set_date(self.def_date('begin'))
        self.begin_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="出货结束:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.end_cal = DateEntry(row1, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT, padx=5)

        # ---- 常显条件（第 2 行）----
        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=5)

        tk.Label(row2, text="客户:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.dealer_name_var = tk.StringVar(value="点击搜索选择")
        self.dealer_btn = tk.Button(row2, textvariable=self.dealer_name_var,
                                    bg="#ffffff", relief=tk.GROOVE, width=18,
                                    anchor="w", command=self.open_dealer_search)
        self.dealer_btn.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="CARG全码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_code_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.part_code_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.part_name_var, width=16).pack(side=tk.LEFT, padx=5)

        # ---- 展开更多条件（默认折叠）----
        self.more_btn = tk.Button(filter_frame, text="展开更多条件 ▼", bg="#f0f0f0",
                                  fg="#1989fa", relief=tk.FLAT, cursor="hand2",
                                  command=self.toggle_more)
        self.more_btn.pack(fill=tk.X)

        self.more_frame = tk.Frame(filter_frame, bg="#f0f0f0")

        m_row1 = tk.Frame(self.more_frame, bg="#f0f0f0")
        m_row1.pack(fill=tk.X, pady=(5, 2))
        tk.Label(m_row1, text="销售单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.sales_order_No_var = tk.StringVar()
        ttk.Entry(m_row1, textvariable=self.sales_order_No_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(m_row1, text="配送方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.logistics_mode_var = tk.StringVar(value="全部")
        self.logistics_mode_cb = ttk.Combobox(m_row1, textvariable=self.logistics_mode_var,
                                             values=["全部"], state="readonly", width=10)
        self.logistics_mode_cb.set("全部")
        self.logistics_mode_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row1, text="产品大类:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_large_category_var = tk.StringVar(value="全部")
        self.part_large_category_cb = ttk.Combobox(m_row1, textvariable=self.part_large_category_var,
                                                  values=["全部"], state="readonly", width=12)
        self.part_large_category_cb.set("全部")
        self.part_large_category_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row1, text="分类2:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.category_two_var = tk.StringVar(value="全部")
        self.category_two_cb = ttk.Combobox(m_row1, textvariable=self.category_two_var,
                                           values=["全部"], state="readonly", width=10)
        self.category_two_cb.set("全部")
        self.category_two_cb.pack(side=tk.LEFT, padx=5)

        m_row2 = tk.Frame(self.more_frame, bg="#f0f0f0")
        m_row2.pack(fill=tk.X, pady=2)
        tk.Label(m_row2, text="客户类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.dealer_type_var = tk.StringVar(value="全部")
        self.dealer_type_cb = ttk.Combobox(m_row2, textvariable=self.dealer_type_var,
                                          values=["全部"], state="readonly", width=10)
        self.dealer_type_cb.set("全部")
        self.dealer_type_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row2, text="客户区域:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.dealer_area_label_var = tk.StringVar(value="全部")
        tk.Button(m_row2, textvariable=self.dealer_area_label_var, bg="#ffffff",
                  relief=tk.GROOVE, width=16, anchor="w",
                  command=lambda: self.open_multi_select(
                      "客户区域", self.area_options, self.area_value_to_text,
                      self.dealer_area_values, self.dealer_area_label_var)).pack(side=tk.LEFT, padx=5)

        tk.Label(m_row2, text="省份:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.province_var = tk.StringVar(value="全部")
        self.province_cb = ttk.Combobox(m_row2, textvariable=self.province_var,
                                        values=["全部"] + [t for t, _ in PROVINCE_OPTIONS],
                                        state="readonly", width=14)
        self.province_cb.set("全部")
        self.province_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row2, text="品牌:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.brand_var = tk.StringVar(value="全部")
        self.brand_cb = ttk.Combobox(m_row2, textvariable=self.brand_var,
                                     values=["全部"], state="readonly", width=12)
        self.brand_cb.set("全部")
        self.brand_cb.pack(side=tk.LEFT, padx=5)

        m_row3 = tk.Frame(self.more_frame, bg="#f0f0f0")
        m_row3.pack(fill=tk.X, pady=2)
        tk.Label(m_row3, text="管控方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.funds_type_var = tk.StringVar(value="全部")
        self.funds_type_cb = ttk.Combobox(m_row3, textvariable=self.funds_type_var,
                                         values=["全部"], state="readonly", width=10)
        self.funds_type_cb.set("全部")
        self.funds_type_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row3, text="结算方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.sett_method_var = tk.StringVar(value="全部")
        self.sett_method_cb = ttk.Combobox(m_row3, textvariable=self.sett_method_var,
                                          values=["全部"], state="readonly", width=10)
        self.sett_method_cb.set("全部")
        self.sett_method_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(m_row3, text="线路:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.line_label_var = tk.StringVar(value="全部")
        tk.Button(m_row3, textvariable=self.line_label_var, bg="#ffffff",
                  relief=tk.GROOVE, width=16, anchor="w",
                  command=lambda: self.open_multi_select(
                      "线路", self.line_options, self.line_value_to_text,
                      self.line_values, self.line_label_var)).pack(side=tk.LEFT, padx=5)

        # ---- 查询 / 重置 / 导出 ----
        btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        btn_row.pack(fill=tk.X, pady=(8, 2))
        self.btn_row = btn_row
        tk.Button(btn_row, text="查询", command=lambda: self.query(True), **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        self.export_btn = tk.Button(btn_row, text="导出 Excel", command=self.export_excel,
                                    bg="#67c23a", fg="white", padx=10, pady=5, bd=0,
                                    activebackground="#5daf34", state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)

    def setup_count_bar(self, parent):
        """查询条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        """构建明细表格"""
        table_frame = tk.LabelFrame(parent, text="销售明细", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("销售单号", "账单号", "产品名称", "客户名称",
                                    "品牌", "型号", "客户区域", "部门", "拣货人",
                                    "账单日期", "CARG全码") else "center"
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.tag_configure("odd", background="#fafafa")
        # 含税金额高亮（对齐安卓端 .amount 样式，整列标红）
        self.tree.tag_configure("amount", foreground="#ee0a24")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tooltip_manager.attach_tooltip(self.tree)

    def setup_summary_bar(self, parent):
        """合计信息条（来自 queryDetailCount：笔数 / 数量合计 / 金额合计）"""
        self.summary_frame = tk.Frame(parent, bg="#f0f0f0")
        self.summary_vars = {}
        items = [("counts", "笔数"), ("sums", "数量合计"), ("amount", "金额合计")]
        for key, label in items:
            var = tk.StringVar(value="-")
            self.summary_vars[key] = var
            item_frame = tk.Frame(self.summary_frame, bg="#ffffff", relief=tk.RIDGE, bd=1)
            item_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            tk.Label(item_frame, text=label, bg="#ffffff", fg="#666666",
                     font=("微软雅黑", 9)).pack(pady=(4, 0))
            fg = "#ee0a24" if key == "amount" else "#323233"
            tk.Label(item_frame, textvariable=var, bg="#ffffff", fg=fg,
                     font=("微软雅黑", 12, "bold")).pack(pady=(0, 4))

    def setup_pagination_controls(self, parent):
        """分页控件（服务端分页，与安卓端 pageNum/limit 一致）"""
        pagination_frame = tk.Frame(parent, bg="#f0f0f0")
        pagination_frame.pack(fill=tk.X, pady=5)

        self.page_info_var = tk.StringVar(value="第 1/1 页")
        tk.Label(pagination_frame, textvariable=self.page_info_var,
                 bg="#f0f0f0").pack(side=tk.LEFT, padx=10)

        btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}
        tk.Button(pagination_frame, text="首页",
                  command=lambda: self.go_to_page(1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="上一页",
                  command=lambda: self.go_to_page(self.page_num - 1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="下一页",
                  command=lambda: self.go_to_page(self.page_num + 1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="尾页",
                  command=lambda: self.go_to_page(self.total_pages), **btn_style).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------ 工具
    @property
    def total_pages(self):
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @staticmethod
    def def_date(kind):
        """起止时间默认值：begin=当月1号，end=今天（对齐安卓端 monthFirstStr/todayStr）"""
        today = date.today()
        if kind == 'begin':
            return date(today.year, today.month, 1)
        return today

    @staticmethod
    def fmt_num(val):
        """数字格式化：整数不显示小数，否则保留两位（对齐安卓端 fmtNum）"""
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    @staticmethod
    def fmt_money(val):
        """金额格式化：非数字显示 '-'，否则两位小数（对齐安卓端 fmtMoney）"""
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return "%.2f" % n

    def _check_response(self, response):
        """检查响应中的登录状态"""
        return not self.controller.check_login_status(response)

    def map_dict(self, type_code, val):
        """字典码表映射：命中返回中文，否则原值；空值返回 '-'（对齐安卓端 mapDict）"""
        if val is None or val == "":
            return "-"
        s = str(val)
        return self.dict_maps.get(type_code, {}).get(s, s)

    def _dict_code(self, type_code):
        """从对应 Combobox 的显示文本反查 code（'全部'/空 -> ''）"""
        var = getattr(self, DICT_VAR_NAMES.get(type_code, ""), None)
        if var is None:
            return ""
        text = var.get()
        if text == "全部" or text == "":
            return ""
        return self.dict_option_maps.get(type_code, {}).get(text, "")

    def _bill_type_value(self):
        text = self.bill_type_var.get()
        for t, v in BILL_TYPE_OPTIONS:
            if t == text:
                return v
        return ""

    def _created_by_value(self):
        text = self.created_by_var.get()
        if text == "全部" or text == "":
            return ""
        return self.created_by_map.get(text, "")

    def _province_value(self):
        text = self.province_var.get()
        if text == "全部" or text == "":
            return ""
        for t, v in PROVINCE_OPTIONS:
            if t == text:
                return v
        return ""

    def _brand_value(self):
        text = self.brand_var.get()
        if text == "全部" or text == "":
            return ""
        return self.brand_map.get(text, "")

    def toggle_more(self):
        """展开/收起更多条件"""
        self.show_more = not self.show_more
        if self.show_more:
            self.more_frame.pack(fill=tk.X, before=self.btn_row)
            self.more_btn.config(text="收起更多条件 ▲")
        else:
            self.more_frame.pack_forget()
            self.more_btn.config(text="展开更多条件 ▼")

    def reset_form(self):
        """重置查询条件（仓库恢复默认第一个，日期恢复月初~今天）"""
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.bill_type_cb.set("全部")
        self.created_by_cb.set("全部")
        self.begin_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.dealer_name_var.set("点击搜索选择")
        self.dealer_code = ""
        self.part_code_var.set("")
        self.part_name_var.set("")
        self.sales_order_No_var.set("")
        for var in (self.logistics_mode_var, self.part_large_category_var,
                    self.category_two_var, self.dealer_type_var, self.funds_type_var,
                    self.sett_method_var):
            var.set("全部")
        self.province_cb.set("全部")
        self.brand_cb.set("全部")
        self.dealer_area_values = []
        self.dealer_area_label_var.set("全部")
        self.line_values = []
        self.line_label_var.set("全部")

    def build_params(self, bracket=True, search_loading='true', page_num=None, size_val=None):
        """构造查询参数（对齐安卓端 buildParams + serializeParams）

        bracket=True  -> 多选用 line1[]/dealer_area1[] 数组形态（列表/合计）
        bracket=False -> 多选用 line1/dealer_area1 无 [] 形态（导出）
        searchLoading 以字符串传递（'true'/'false'），避免被序列成 True/False
        """
        page_num = self.page_num if page_num is None else page_num
        size_val = self.page_size if size_val is None else size_val
        warehouse_name = self.warehouse_var.get()
        storage_id = self.controller.options.get(warehouse_name, "")

        line_values = self.line_values
        area_values = self.dealer_area_values

        p = {
            "searchLoading": search_loading,
            "bill_at_begin": self.begin_cal.get() or "",
            "bill_at_end": self.end_cal.get() or "",
            "bill_type": self._bill_type_value(),
            "dealer_name": "",
            "dealer_code": self.dealer_code,
            "logistics_mode": self._dict_code("4617"),
            "funds_type": self._dict_code("1195"),
            "license_no": "",
            "order_license_no": "",
            "category_two": self._dict_code("9092"),
            "part_large_category": self._dict_code("9101"),
            "part_code": self.part_code_var.get().strip(),
            "part_name": self.part_name_var.get().strip(),
            "dealer_type": self._dict_code("9012"),
            "sales_order_No": self.sales_order_No_var.get().strip(),
            "created_by": self._created_by_value(),
            "storage_id": storage_id,
            "crowdfunding_code": "",
            "promotion_code": "",
            "act_type": "",
            # 多选：逗号串形式
            "line": ",".join(line_values) if line_values else "",
            "dealer_area": ",".join(area_values) if area_values else "",
            "PROVINCE": self._province_value(),
            "brandId": self._brand_value(),
            "location_no": "",
            "sett_method": self._dict_code("4622"),
            "part_type": "",
            "cityId": "",
            "countyId": "",
            "limit": size_val,
            "pageNum": page_num,
        }
        # 多选：数组形态（未选中则不发，对齐安卓端 line1[]/dealer_area1[]）
        if area_values:
            p["dealer_area1[]" if bracket else "dealer_area1"] = list(area_values)
        if line_values:
            p["line1[]" if bracket else "line1"] = list(line_values)
        return p

    # ------------------------------------------------------------------ 查询
    def query(self, reset_page=True):
        """执行查询（reset_page=True 时回到第一页并刷新合计）"""
        if self.loading:
            return
        if reset_page:
            self.page_num = 1

        if not self.begin_cal.get() or not self.end_cal.get():
            messagebox.showwarning("提示", "请选择出货起止日期")
            return

        params = self.build_params(bracket=True, search_loading='true')
        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params, reset_page),
                         daemon=True).start()

    def _query_thread(self, params, fetch_count):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[销售明细-列表] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-列表] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常，请检查网络: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        finally:
            self.loading = False

        if not (data.get("resultCode") == 200 or data.get("code") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("message") or "查询失败"
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return

        d = data.get("data") or {}
        rows = d.get("rows") or []
        total = d.get("total") or data.get("total") or len(rows)
        self.controller.after(0, lambda: self._render_rows(rows, total))

        if fetch_count:
            self.fetch_count()

    def _render_rows(self, rows, total):
        """渲染列表（主线程）"""
        self.rows = rows
        self.total = total
        self.queried = True

        for item in self.tree.get_children():
            self.tree.delete(item)

        base = (self.page_num - 1) * self.page_size
        for idx, row in enumerate(rows):
            bill_date = row.get("bill_date") or ""
            bill_time = row.get("bill_date_time") or ""
            bill_date_disp = (bill_date + (" " + bill_time if bill_time else "")) if bill_date else "-"
            values = (
                base + idx + 1,                                   # 全局序号
                row.get("sales_order_No") or "-",
                row.get("BILL_NO") or "-",
                row.get("part_code") or "-",
                row.get("part_name") or "-",
                self.map_dict("9101", row.get("part_large_category")),
                self.map_dict("9092", row.get("category_two")),
                row.get("DEALER_NAME") or "-",
                self.map_dict("9012", row.get("DEALER_TYPE_CODE")),
                self.map_dict("1195", row.get("FUNDS_TYPE")),
                self.map_dict("4622", row.get("sett_method")),
                self.map_dict("4617", row.get("logistics_mode")),
                row.get("created_by_name") or "-",
                row.get("BRAND_NAME") or "-",
                row.get("storage_name") or row.get("department") or "-",
                row.get("location_no") or "-",
                self.fmt_num(row.get("NUM")),
                self.fmt_money(row.get("IN_TAX_PRICE")),
                self.fmt_money(row.get("IN_TAX_AMOUNT")),
                self.fmt_num(row.get("discount")),
                row.get("model_number") or "-",
                row.get("routeName") or "-",
                row.get("AREA_NAME") or "-",
                row.get("PROVINCE_NAME") or row.get("PROVINCE") or "-",
                row.get("department") or "-",
                row.get("picking_by") or "-",
                bill_date_disp,
            )
            # 含税金额列标红（amount 列索引 18，对应 0-based index 18）
            tags = []
            if idx % 2 == 1:
                tags.append("odd")
            self.tree.insert("", "end", values=values, tags=tuple(tags))

        self.count_var.set(f"共 {total} 条销售明细")
        self.update_page_info()
        self.export_btn.config(state=tk.NORMAL if total else tk.DISABLED)
        if total == 0:
            messagebox.showinfo("查询结果", "无销售明细数据")

    # ------------------------------------------------------------------ 合计
    def fetch_count(self):
        """拉取合计（笔数/数量合计/金额合计），参数与列表一致"""
        params = self.build_params(bracket=True, search_loading='true',
                                   page_num=1, size_val=self.page_size)
        threading.Thread(target=self._count_thread, args=(params,), daemon=True).start()

    def _count_thread(self, params):
        try:
            r = self.controller.session.get(URL_COUNT, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-合计] 请求异常: {e}")
            return

        if not (data.get("resultCode") == 200 or data.get("success")):
            return

        d = data.get("data") or {}
        counts = d.get("counts") or 0
        sums = d.get("sums") or 0
        amount = d.get("amount") or 0
        self.controller.after(0, lambda: self._render_summary(counts, sums, amount))

    def _render_summary(self, counts, sums, amount):
        self.summary = {"counts": counts, "sums": sums, "amount": amount}
        self.summary_vars["counts"].set(str(counts))
        self.summary_vars["sums"].set(self.fmt_num(sums))
        self.summary_vars["amount"].set(self.fmt_money(amount))
        self.summary_frame.pack(fill=tk.X, pady=(5, 0))

    # ------------------------------------------------------------------ 分页
    def update_page_info(self):
        self.page_info_var.set(f"第 {self.page_num}/{self.total_pages} 页 (共 {self.total} 条)")

    def go_to_page(self, page):
        """翻页（服务端分页，重新请求；合计不刷新）"""
        if self.loading:
            return
        try:
            page = int(page)
        except (TypeError, ValueError):
            return
        page = min(max(1, page), self.total_pages)
        if page == self.page_num:
            return
        self.page_num = page
        self.query(reset_page=False)

    # -------------------------------------------------------------- 字典/下拉
    def load_dicts(self):
        threading.Thread(target=self._dicts_thread, daemon=True).start()

    def _dicts_thread(self):
        try:
            r = self.controller.session.get(URL_DICTS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-字典] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        data_obj = data.get("data") or {}
        dict_container = data_obj.get("dict") if isinstance(data_obj, dict) else None
        if not isinstance(dict_container, dict):
            dict_container = {}
        self.dict_maps = {}
        self.dict_option_maps = {}
        for t in DICT_TYPES:
            arr = dict_container.get(t) or []
            code_map = {}
            text_map = {}
            for x in arr:
                if isinstance(x, dict) and x.get("code_id") is not None:
                    code = str(x["code_id"])
                    desc = x.get("code_cn_desc") or code
                    code_map[code] = desc
                    text_map[desc] = code
            self.dict_maps[t] = code_map
            self.dict_option_maps[t] = text_map
        self.controller.after(0, self._refresh_dict_combos)

    def _refresh_dict_combos(self):
        """用拉取的字典刷新各下拉选项（保留「全部」）"""
        mapping = {
            "4617": (self.logistics_mode_var, self.logistics_mode_cb),
            "9101": (self.part_large_category_var, self.part_large_category_cb),
            "9092": (self.category_two_var, self.category_two_cb),
            "9012": (self.dealer_type_var, self.dealer_type_cb),
            "1195": (self.funds_type_var, self.funds_type_cb),
            "4622": (self.sett_method_var, self.sett_method_cb),
        }
        for t, (var, cb) in mapping.items():
            texts = ["全部"] + list(self.dict_option_maps.get(t, {}).keys())
            cb.config(values=texts)
            # 若当前选择已不在新列表中（理论上不会），复位为全部
            if var.get() not in texts:
                var.set("全部")

    def load_created_by(self):
        threading.Thread(target=self._created_by_thread, daemon=True).start()

    def _created_by_thread(self):
        try:
            r = self.controller.session.get(URL_EMPLOYEE, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-开单人] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        lst = (data.get("data") or [])
        if not isinstance(lst, list):
            lst = []
        created_by_map = {}
        for u in lst:
            if isinstance(u, dict) and u.get("EMPLOYEE_NO") is not None:
                name = u.get("EMPLOYEE_NAME") or str(u["EMPLOYEE_NO"])
                created_by_map[name] = u["EMPLOYEE_NO"]
        self.controller.after(0, lambda: self._refresh_created_by(created_by_map))

    def _refresh_created_by(self, created_by_map):
        self.created_by_map = created_by_map
        texts = ["全部"] + list(created_by_map.keys())
        self.created_by_cb.config(values=texts)
        if self.created_by_var.get() not in texts:
            self.created_by_var.set("全部")

    def load_areas(self):
        threading.Thread(target=self._area_thread, daemon=True).start()

    def _area_thread(self):
        try:
            r = self.controller.session.get(URL_AREA, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-客户区域] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        lst = data.get("data") or []
        if not isinstance(lst, list):
            lst = []
        options = []
        v2t = {}
        for a in lst:
            if isinstance(a, dict) and a.get("AREA_ID") is not None:
                text = a.get("AREA_NAME") or str(a["AREA_ID"])
                val = str(a["AREA_ID"])
                options.append((text, val))
                v2t[val] = text
        self.controller.after(0, lambda: self._set_area_options(options, v2t))

    def _set_area_options(self, options, v2t):
        self.area_options = options
        self.area_value_to_text = v2t
        # 清理已失效的选中项
        self.dealer_area_values = [v for v in self.dealer_area_values if v in v2t]
        self._update_multi_label(self.dealer_area_values, self.area_value_to_text,
                                 self.dealer_area_label_var)

    def load_lines(self):
        threading.Thread(target=self._line_thread, daemon=True).start()

    def _line_thread(self):
        try:
            r = self.controller.session.get(URL_LINE, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-线路] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        lst = data.get("data") or []
        if not isinstance(lst, list):
            lst = []
        options = []
        v2t = {}
        for l in lst:
            if isinstance(l, dict) and l.get("id") is not None:
                text = l.get("routeName") or str(l["id"])
                val = str(l["id"])
                options.append((text, val))
                v2t[val] = text
        self.controller.after(0, lambda: self._set_line_options(options, v2t))

    def _set_line_options(self, options, v2t):
        self.line_options = options
        self.line_value_to_text = v2t
        self.line_values = [v for v in self.line_values if v in v2t]
        self._update_multi_label(self.line_values, self.line_value_to_text,
                                 self.line_label_var)

    def load_brands(self):
        threading.Thread(target=self._brand_thread, daemon=True).start()

    def _brand_thread(self):
        try:
            r = self.controller.session.get(URL_BRAND, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[销售明细-品牌] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        lst = data.get("data") or []
        if not isinstance(lst, list):
            lst = []
        brand_map = {}
        for b in lst:
            if isinstance(b, dict) and b.get("BRAND_ID") is not None:
                name = b.get("BRAND_NAME") or str(b["BRAND_ID"])
                brand_map[name] = b["BRAND_ID"]
        self.controller.after(0, lambda: self._refresh_brands(brand_map))

    def _refresh_brands(self, brand_map):
        self.brand_map = brand_map
        texts = ["全部"] + list(brand_map.keys())
        self.brand_cb.config(values=texts)
        if self.brand_var.get() not in texts:
            self.brand_var.set("全部")

    # ---------------------------------------------------- 多选弹层（线路/区域）
    def open_multi_select(self, title, options, value_to_text, selected, label_var):
        """通用多选弹层（线路 / 客户区域共用）"""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("420x520")
        win.transient(self)
        win.grab_set()

        selected_set = set(selected)
        body = tk.Frame(win, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动容器
        canvas = tk.Canvas(body, bg="#ffffff")
        scroll = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#ffffff")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        checks = []
        if not options:
            tk.Label(inner, text="（加载中或无数据）", bg="#ffffff", fg="#c8c9cc").pack(anchor="w", padx=5, pady=5)
        for text, value in options:
            var = tk.BooleanVar(value=(value in selected_set))
            cb = tk.Checkbutton(inner, text=text, variable=var, bg="#ffffff", anchor="w")
            cb.pack(anchor="w", padx=5, pady=2)
            checks.append((value, var))

        def confirm():
            new_sel = [value for value, var in checks if var.get()]
            selected[:] = new_sel
            self._update_multi_label(new_sel, value_to_text, label_var)
            win.destroy()

        btn_frame = tk.Frame(win, bg="#f0f0f0")
        btn_frame.pack(fill=tk.X, pady=8)
        tk.Button(btn_frame, text="确定", command=confirm,
                  bg="#4CAF50", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="取消", command=win.destroy,
                  bg="#e1e1e1", padx=20, pady=5, bd=0).pack(side=tk.RIGHT, padx=20)

    def _update_multi_label(self, selected, value_to_text, label_var):
        if not selected:
            label_var.set("全部")
        else:
            label_var.set("、".join(value_to_text.get(v, v) for v in selected) or "全部")

    # -------------------------------------------------------- 客户搜索弹层
    def open_dealer_search(self):
        win = tk.Toplevel(self)
        win.title("选择客户")
        win.geometry("460x520")
        win.transient(self)
        win.grab_set()

        search_frame = tk.Frame(win, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=10, pady=8)
        kw_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=kw_var, width=22).pack(side=tk.LEFT, padx=5)
        list_state = {"loading": False, "list": []}

        body = tk.Frame(win, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(body, bg="#ffffff")
        scroll = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="#ffffff")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def render_list(items):
            for w in inner.winfo_children():
                w.destroy()
            if not items:
                tk.Label(inner, text="暂无匹配客户", bg="#ffffff", fg="#969799").pack(anchor="w", padx=5, pady=5)
                return
            for d in items:
                name = d.get("dealerName") or ""
                code = d.get("dealerCode") or ""
                item = tk.Frame(inner, bg="#ffffff", relief=tk.GROOVE, bd=1)
                item.pack(fill=tk.X, padx=5, pady=3)
                tk.Label(item, text=name, bg="#ffffff", font=("微软雅黑", 11),
                         anchor="w").pack(anchor="w", padx=8, pady=(4, 0))
                tk.Label(item, text=code, bg="#ffffff", fg="#969799",
                         anchor="w").pack(anchor="w", padx=8, pady=(0, 4))
                item.bind("<Button-1>", lambda e, dd=d: pick(dd))
                for child in item.winfo_children():
                    child.bind("<Button-1>", lambda e, dd=d: pick(dd))

        def pick(d):
            self.dealer_code = d.get("dealerCode") or ""
            self.dealer_name_var.set(d.get("dealerName") or self.dealer_code or "点击搜索选择")
            win.destroy()

        def do_search():
            if list_state["loading"]:
                return
            list_state["loading"] = True
            threading.Thread(target=_search_thread,
                             args=(kw_var.get().strip(),), daemon=True).start()

        def _search_thread(kw):
            try:
                r = self.controller.session.get(URL_DEALER, headers=HEADERS, params={
                    "dealerCode": "", "dealerName": "", "linkMan": "", "linkPhone": "",
                    "address": "", "fuzzy_query": kw, "saleAreaManager": "",
                    "dealerArea": "", "isReceivableShow": 0,
                })
                if not self._check_response(r):
                    list_state["loading"] = False
                    return
                data = json.loads(r.text)
                lst = ((data.get("data") or {}).get("rows")) or []
            except Exception as e:
                print(f"[销售明细-客户搜索] 异常: {e}")
                lst = []
            finally:
                list_state["loading"] = False
            self.controller.after(0, lambda: render_list(lst))

        tk.Button(search_frame, text="搜索", command=do_search,
                  bg="#4CAF50", fg="white", padx=12, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="关闭", command=win.destroy,
                  bg="#e1e1e1", padx=12, pady=4, bd=0).pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------ 导出
    def export_excel(self):
        """导出 Excel（query/excelDetail，limit=50000 取全量，bracket=false）"""
        if self.exporting:
            return
        if not self.begin_cal.get() or not self.end_cal.get():
            messagebox.showwarning("提示", "请选择出货起止日期")
            return

        default_name = f"销售明细_{self.begin_cal.get()}_{self.end_cal.get()}.xlsx".replace("/", "_")
        path = filedialog.asksaveasfilename(
            title="导出销售明细 Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
        if not path:
            return

        self.exporting = True
        self.export_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._export_thread, args=(path,), daemon=True).start()

    def _export_thread(self, path):
        try:
            params = self.build_params(bracket=False, search_loading='false',
                                       page_num=1, size_val=50000)
            r = self.controller.session.get(URL_EXPORT, headers=HEADERS, params=params)
            print(f"[销售明细-导出] {r.url}")
            if not self._check_response(r):
                return

            ct = r.headers.get("Content-Type", "") or ""
            # 后端可能返回 JSON 错误信息（HTTP 200 但 resultCode != 200）
            if "json" in ct.lower():
                try:
                    j = r.json()
                    msg = j.get("errMsg") or j.get("message") or "导出失败"
                except Exception:
                    msg = "导出失败"
                self.controller.after(0, lambda: messagebox.showerror("导出失败", str(msg)))
                return

            with open(path, "wb") as f:
                f.write(r.content)
            self.controller.after(0, lambda: messagebox.showinfo(
                "导出成功", f"文件已保存:\n{path}"))
        except Exception as e:
            print(f"[销售明细-导出] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror(
                "导出失败", f"{e}"))
        finally:
            self.exporting = False
            self.controller.after(0, lambda: self.export_btn.config(
                state=tk.NORMAL if self.total else tk.DISABLED))

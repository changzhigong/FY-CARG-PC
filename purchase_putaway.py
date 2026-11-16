# -*- coding: utf-8 -*-
"""采购入库 — 入库上架

对齐 fycarg-pda 安卓端 src/views/PurchasePutaway.vue + src/service/purchaseInbound.js，
接口与业务逻辑保持一致。

接口（baseURL https://xb.fy-carg.com）：
- 列表        GET  /dmscloud.part/part/receiptInfo
- 上架明细    GET  /dmscloud.part/part/receiptInfo/{id}          （含 shelvesQty/shelvesdQty）
- 入库清单    GET  /dmscloud.part/part/receiptInfo/onshelf/{id}  （含 shelf_quantity/totalAmt）
- 上架提交    POST /dmscloud.part/part/receiptInfo/shelvesHandle
- 上架人      GET  /dcscloud.basedata/basedata/employees/getEmpByRoleCode?roleCode=SJR
- 库位实时    GET  /dmscloud.part/warehouse/transferIn/findAllLocationValid
- 字典        GET  /dmscloud.basedata/dicts

关键业务规则（与安卓端逐条对齐）：
1. 入库类型参数名是 **receiptType**（驼峰），与到货签收页的 receipt_type（下划线）不同，勿混用；
   默认 90331017（非玻璃采购入库）。
2. 收货状态多选同时传两种形态：
   - sparePartsStatus  = 逗号串（如 90311002,90311003,90311004）
   - sparePartsStatus1[] = 数组（requests 对 list 值展开为重复键）
   默认勾选「部分验收 + 已验收 + 部分上架」。
3. 可上架状态：receiptStatus ∈ {90311002 部分验收, 90311003 已验收, 90311004 部分上架}；
   未验收(90311001) 与 已上架(90311005) 禁用。
4. 待上架数量 remainQty = shelvesQty - shelvesdQty（小于 0 归 0）；上架数量不得超过该值。
5. 上架提交报文：
   { id, warehouseId, recordVersion, checkStatus: 10041001, detailDtoList, onshelf_by }
   - recordVersion 只在**列表行**上有（receiptInfo/{id} 明细不含），必须取列表行的值；
   - 明细行：shelfLocationNo / shelfLocationId / shelvesQty 传**字符串** /
     onshelf_by 传**数组** [人] / onshelf_by_name 传字符串；有合法库位 id 时附带
     select_LOCATION_OPTIONS = [{ locationId, locationNo }]；
   - 暂存草稿额外带顶层 isSave: 1（确认上架不带）；
   - 确认上架要求至少一条上架数量 > 0，暂存草稿允许全 0。
6. 打印分两种清单，数据源不同端点：
   - 上架清单：receiptInfo/{id}，数量取 shelvesdQty（已上架数量）；
   - 入库清单：receiptInfo/onshelf/{id}，数量取 shelf_quantity，金额取 totalAmt（该接口专用字段）。

字典组：9033 入库类型 / 9031 收货状态 / 9092 配件分类（category_two）。
接口拉取失败时使用 FALLBACK_DICTS 硬编兜底（与安卓端 FALLBACK 一致）。

与安卓端的交互差异（仅载体差异，逻辑不变）：
- 安卓端每行内嵌「查看 / 上架」按钮；PC 端用按钮栏作用于当前选中行。
- 安卓端库位是输入框 + 浮动建议层；PC 端改为「库位输入框 + 候选列表（双击填入）」，
  同样走 findAllLocationValid 实时查询，并沿用「手输未选则回退已选库位」的防脏数据规则。
- 安卓端打印入口在明细弹层内并需先选清单类型；PC 端在按钮栏直接给「打印上架清单 /
  打印入库清单」两个按钮，均先弹预览再打印。
"""

import json
import threading

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

from base_page import BasePage
from tooltip_manager import tooltip_manager

# ---------------------------------------------------------------- 常量
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

BASE_URL = 'https://xb.fy-carg.com'
URL_LIST = BASE_URL + '/dmscloud.part/part/receiptInfo'
URL_DETAIL = BASE_URL + '/dmscloud.part/part/receiptInfo/{id}'
URL_ONSHELF = BASE_URL + '/dmscloud.part/part/receiptInfo/onshelf/{id}'
URL_SHELVES = BASE_URL + '/dmscloud.part/part/receiptInfo/shelvesHandle'
URL_ONSHELF_PERSONS = BASE_URL + '/dcscloud.basedata/basedata/employees/getEmpByRoleCode'
URL_LOCATIONS = BASE_URL + '/dmscloud.part/warehouse/transferIn/findAllLocationValid'
URL_DICTS = BASE_URL + '/dmscloud.basedata/dicts'

PAGE_SIZE = 20

# 上架提交固定校验状态
CHECK_STATUS = 10041001

# 可上架状态：部分验收 / 已验收 / 部分上架
SHELVABLE_STATUS = (90311002, 90311003, 90311004)

# 默认入库类型：非玻璃采购入库
DEFAULT_RECEIPT_TYPE = '90331017'

# 收货状态选项（字典组 9031）
RECEIVE_STATUS_OPTIONS = [
    ('90311001', '未验收'),
    ('90311002', '部分验收'),
    ('90311003', '已验收'),
    ('90311004', '部分上架'),
    ('90311005', '已上架'),
]
# 默认勾选（对齐安卓端 search.sparePartsStatusList 初始值）
DEFAULT_RECEIVE_STATUS = ('90311002', '90311003', '90311004')

# 字典硬编兜底（与安卓端 FALLBACK 一致）
FALLBACK_DICTS = {
    '9033': {
        '90331017': '非玻璃采购入库',
        '90331021': '玻璃采购入库',
        '90331022': '其它采购入库',
    },
    '9031': {
        '90311001': '未验收',
        '90311002': '部分验收',
        '90311003': '已验收',
        '90311004': '部分上架',
        '90311005': '已上架',
    },
    '9092': {
        '90921001': '前挡',
        '90921002': '后挡',
        '90921003': '边窗',
        '90921004': '其它',
        '90921005': '天窗',
    },
}

# 列表列定义（对齐安卓端表头顺序，供应商拆成两列）
COLUMNS = ['序号', '发运单号', '入库仓库', '供应商', '供应商编号', '发货数量',
           '接收数量', '上架数量', '收货状态', '入库类型', '操作人', '操作时间']
COLUMN_WIDTHS = [50, 160, 90, 150, 100, 80, 80, 80, 90, 130, 80, 140]

# 上架明细列定义（对齐安卓端明细弹层表头）
DETAIL_COLUMNS = ['序号', '品牌', 'CARG全码/编码', '产品名称', '分类', '车型',
                  '数量', '单价', '金额', '库位', '上架人']
DETAIL_WIDTHS = [45, 80, 140, 200, 70, 110, 70, 80, 100, 100, 90]


class PurchasePutawayPage(BasePage):
    """采购入库 — 入库上架页面"""

    def __init__(self, parent, controller):
        self.rows = []
        self.total = 0
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.loading = False
        self.dict_maps = {}
        self.show_more = False
        self.receive_status_vars = {}   # 收货状态多选框 code -> BooleanVar
        self.emp_list = []              # 上架人列表 [{employeeName, phone}]
        self._detail_win = None
        self._shelf_win = None
        self._shelf_rows = []           # 上架弹窗行数据
        self._shelf_header = None       # 上架弹窗对应的列表行
        self._record_version = 0
        self._loc_target = None         # 当前正在编辑库位的行（dict）
        self._loc_timer = None
        self._loc_items = []            # 当前候选库位
        super().__init__(parent, controller)

    # ================================================================ 界面
    def create_widgets(self):
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main_container)
        self.setup_action_bar(main_container)
        self.setup_count_bar(main_container)
        self.setup_data_table(main_container)
        self.setup_pagination_controls(main_container)

        self.load_dicts()

    def setup_filter_panel(self, parent):
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        # ---- 第一行：仓库 + 入库类型 ----
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="入库仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="入库类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.receipt_type_var = tk.StringVar(value="全部")
        self.receipt_type_cb = ttk.Combobox(row1, textvariable=self.receipt_type_var,
                                            values=["全部"], state="readonly", width=16)
        self.receipt_type_cb.pack(side=tk.LEFT, padx=5)

        # ---- 第二行：验收时间（建单）----
        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=2)

        self.use_created_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="按验收时间筛选（建单）", variable=self.use_created_var,
                        command=self.toggle_created).pack(side=tk.LEFT, padx=5)
        tk.Label(row2, text="起:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        self.created_sta_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd',
                                         state="disabled")
        self.created_sta_cal.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="止:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        self.created_end_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd',
                                         state="disabled")
        self.created_end_cal.pack(side=tk.LEFT, padx=2)

        # ---- 第三行：上架时间（入库）----
        row3 = tk.Frame(filter_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=2)

        self.use_so_created_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="按上架时间筛选（入库）", variable=self.use_so_created_var,
                        command=self.toggle_so_created).pack(side=tk.LEFT, padx=5)
        tk.Label(row3, text="起:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        self.so_sta_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd',
                                    state="disabled")
        self.so_sta_cal.pack(side=tk.LEFT, padx=2)
        tk.Label(row3, text="止:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        self.so_end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd',
                                    state="disabled")
        self.so_end_cal.pack(side=tk.LEFT, padx=2)

        # ---- 第四行：收货状态（多选）----
        row4 = tk.Frame(filter_frame, bg="#f0f0f0")
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="收货状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        for code, text in RECEIVE_STATUS_OPTIONS:
            var = tk.BooleanVar(value=(code in DEFAULT_RECEIVE_STATUS))
            self.receive_status_vars[code] = var
            ttk.Checkbutton(row4, text=text, variable=var).pack(side=tk.LEFT, padx=2)

        # ---- 折叠区：发运单号 / 供应商编号 / 供应商名称 ----
        self.more_btn = tk.Button(filter_frame, text="展开发运单号/供应商 ▼",
                                  bg="#f0f0f0", fg="#1989fa", relief=tk.FLAT,
                                  cursor="hand2", command=self.toggle_more)
        self.more_btn.pack(fill=tk.X)

        self.more_frame = tk.Frame(filter_frame, bg="#f0f0f0")
        more_row = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row.pack(fill=tk.X, pady=(5, 2))

        tk.Label(more_row, text="发运单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.receipt_no_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.receipt_no_var, width=18).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row, text="供应商编号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.supplier_no_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.supplier_no_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row, text="供应商名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.supplier_name_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.supplier_name_var, width=18).pack(side=tk.LEFT, padx=5)

        # ---- 查询 / 重置 ----
        self.btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        self.btn_row.pack(fill=tk.X, pady=(8, 2))
        tk.Button(self.btn_row, text="查询", command=self.query,
                  bg="#4CAF50", fg="white", padx=10, pady=5, bd=0,
                  activebackground="#45a049").pack(side=tk.LEFT, padx=5)
        tk.Button(self.btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_action_bar(self, parent):
        bar = tk.Frame(parent, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=(0, 3))

        tk.Button(bar, text="查看明细", command=self.open_detail,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="入库上架", command=self.open_shelf,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="打印上架清单", command=lambda: self.open_print('shelf'),
                  bg="#fa8c16", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="打印入库清单", command=lambda: self.open_print('receipt'),
                  bg="#fa8c16", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Label(bar, text="提示：单击选行；双击行查看明细", bg="#f0f0f0",
                 fg="#666666", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="入库上架列表", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("发运单号", "供应商", "入库仓库", "入库类型") else "center"
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.tag_configure("odd", background="#fafafa")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self.open_detail())
        tooltip_manager.attach_tooltip(self.tree)

    def setup_pagination_controls(self, parent):
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

    # ================================================================ 工具
    @property
    def total_pages(self):
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def current_warehouse_id(self):
        return self.controller.options.get(self.warehouse_var.get(), "")

    @staticmethod
    def fmt_num(val):
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    @staticmethod
    def fmt_money(val):
        try:
            return "%.2f" % float(val or 0)
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def short_brand(text):
        """仓库名简称（对齐安卓端 .replace('福耀玻璃', '福耀')）"""
        return (text or '').replace('福耀玻璃', '福耀')

    @staticmethod
    def to_text(val):
        """onshelf_by 可能是数组也可能是字符串，统一成显示文本"""
        if val is None or val == '':
            return '-'
        if isinstance(val, (list, tuple)):
            return '、'.join(str(x) for x in val if x) or '-'
        return str(val)

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    def _label(self, dict_type, code):
        if code is None or code == "":
            return "-"
        key = str(code)
        live = self.dict_maps.get(dict_type) or {}
        if key in live:
            return live[key]
        fb = FALLBACK_DICTS.get(dict_type) or {}
        return fb.get(key, key)

    def decode_receipt_type(self, code):
        return self._label('9033', code)

    def decode_receive_status(self, code):
        return self._label('9031', code)

    def decode_category(self, code):
        return self._label('9092', code)

    def toggle_more(self):
        self.show_more = not self.show_more
        if self.show_more:
            self.more_frame.pack(fill=tk.X, before=self.btn_row)
            self.more_btn.config(text="收起查询条件 ▲")
        else:
            self.more_frame.pack_forget()
            self.more_btn.config(text="展开发运单号/供应商 ▼")

    def toggle_created(self):
        state = "normal" if self.use_created_var.get() else "disabled"
        self.created_sta_cal.config(state=state)
        self.created_end_cal.config(state=state)

    def toggle_so_created(self):
        state = "normal" if self.use_so_created_var.get() else "disabled"
        self.so_sta_cal.config(state=state)
        self.so_end_cal.config(state=state)

    def reset_form(self):
        """重置（入库类型恢复 90331017，收货状态恢复默认三项）"""
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.receipt_type_var.set(self.decode_receipt_type(DEFAULT_RECEIPT_TYPE))
        for code, _t in RECEIVE_STATUS_OPTIONS:
            self.receive_status_vars[code].set(code in DEFAULT_RECEIVE_STATUS)
        self.use_created_var.set(False)
        self.toggle_created()
        self.use_so_created_var.set(False)
        self.toggle_so_created()
        self.receipt_no_var.set("")
        self.supplier_no_var.set("")
        self.supplier_name_var.set("")

    def current_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.rows):
            return self.rows[idx]
        return None

    # ================================================================ 查询
    def _receipt_type_value(self):
        text = self.receipt_type_var.get()
        if not text or text == "全部":
            return ""
        for code, name in (self.dict_maps.get('9033') or FALLBACK_DICTS['9033']).items():
            if name == text:
                return code
        return text

    def build_params(self):
        """构造查询参数（对齐安卓端 loadList）"""
        selected = [code for code, _t in RECEIVE_STATUS_OPTIONS
                    if self.receive_status_vars[code].get()]
        params = {
            'pageNum': self.page_num,
            'pageSize': self.page_size,
            'warehouseId': self.current_warehouse_id,
            'searchLoading': 'true',
            # 多选字段同时传逗号串与数组两种形态
            'sparePartsStatus': ','.join(selected),
            'sparePartsStatus1[]': list(selected),
        }
        # 注意：本页入库类型参数名是 receiptType（驼峰），到货签收页是 receipt_type
        receipt_type = self._receipt_type_value()
        if receipt_type:
            params['receiptType'] = receipt_type
        if self.receipt_no_var.get().strip():
            params['receiptNo'] = self.receipt_no_var.get().strip()
        if self.supplier_no_var.get().strip():
            params['supplierNo'] = self.supplier_no_var.get().strip()
        if self.supplier_name_var.get().strip():
            params['supplierFullName'] = self.supplier_name_var.get().strip()
        if self.use_created_var.get():
            params['createdSta'] = self.created_sta_cal.get()
            params['createdEnd'] = self.created_end_cal.get()
        if self.use_so_created_var.get():
            params['soCreatedSta'] = self.so_sta_cal.get()
            params['soCreatedEnd'] = self.so_end_cal.get()
        return params

    def query(self, reset_page=True):
        if self.loading:
            return
        if reset_page:
            self.page_num = 1
        if not self.current_warehouse_id:
            messagebox.showwarning("提示", "请先选择入库仓库")
            return

        params = self.build_params()
        self.loading = True
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_LIST, headers=HEADERS, params=params)
            print("[入库上架] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 请求异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "查询异常，请检查网络: %s" % e))
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
        rows = d.get("rows") or d.get("data") or d.get("records") or []
        total = d.get("total") or data.get("total") or len(rows)
        self.controller.after(0, lambda: self._render_rows(rows, total))

    def _render_rows(self, rows, total):
        self.rows = rows
        self.total = total

        for item in self.tree.get_children():
            self.tree.delete(item)

        base = (self.page_num - 1) * self.page_size
        for idx, row in enumerate(rows):
            values = (
                base + idx + 1,
                row.get("shipNo") or "-",
                row.get("warehouseName") or "-",
                row.get("supplierName") or "-",
                row.get("supplierNo") or "-",
                self.fmt_num(row.get("shipQty")),
                self.fmt_num(row.get("receivingQty")),
                self.fmt_num(row.get("shelvesQty")),
                self.decode_receive_status(row.get("receiptStatus")),
                self.decode_receipt_type(row.get("receiptType")),
                row.get("updateByName") or "-",
                row.get("updateAt") or "-",
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        self.count_var.set("共 %d 条收货单" % total)
        self.update_page_info()

    def update_page_info(self):
        self.page_info_var.set("第 %d/%d 页 (共 %d 条)" % (self.page_num, self.total_pages, self.total))

    def go_to_page(self, page):
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

    # ================================================================ 字典 / 上架人
    def load_dicts(self):
        threading.Thread(target=self._dicts_thread, daemon=True).start()

    def _dicts_thread(self):
        try:
            r = self.controller.session.get(URL_DICTS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 字典加载失败，使用硬编兜底: %s" % e)
            return

        d = data.get("data") or {}
        dict_groups = d.get("dict") or {}
        maps = {}
        for group in ('9033', '9031', '9092'):
            arr = dict_groups.get(group) or []
            m = {}
            for x in arr:
                if isinstance(x, dict) and x.get("code_id") is not None:
                    m[str(x.get("code_id"))] = x.get("code_cn_desc")
            if m:
                maps[group] = m
        self.controller.after(0, lambda: self._render_dicts(maps))

    def _render_dicts(self, maps):
        self.dict_maps = maps
        receipt_map = maps.get('9033') or FALLBACK_DICTS['9033']
        self.receipt_type_cb.config(values=["全部"] + list(receipt_map.values()))
        # 默认「非玻璃采购入库」（对齐安卓端 search.receiptType 初始值）
        self.receipt_type_var.set(self.decode_receipt_type(DEFAULT_RECEIPT_TYPE))

    def load_onshelf_persons(self):
        """上架人列表（roleCode=SJR）"""
        try:
            r = self.controller.session.get(URL_ONSHELF_PERSONS, headers=HEADERS,
                                            params={'roleCode': 'SJR'})
            if not self._check_response(r):
                return []
            data = json.loads(r.text) or {}
            arr = data.get("data") or []
            return [{'employeeName': x.get('EMPLOYEE_NAME') or x.get('employeeName') or '',
                     'phone': x.get('PHONE') or x.get('phone') or ''}
                    for x in arr if isinstance(x, dict)]
        except Exception as e:
            print("[入库上架] 上架人列表加载失败: %s" % e)
            return []

    # ================================================================ 明细（上架明细）
    def open_detail(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        row_id = row.get("id")
        if row_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法查看明细")
            return

        win = tk.Toplevel(self)
        win.title("上架明细 - %s" % (row.get("receivingNo") or row.get("shipNo") or ""))
        win.geometry("1120x620")
        self._detail_win = win
        tk.Label(win, text="加载中...", font=("微软雅黑", 10)).pack(pady=20)
        threading.Thread(target=self._detail_thread, args=(row_id, row, win), daemon=True).start()

    def _detail_thread(self, row_id, row, win):
        try:
            r = self.controller.session.get(URL_ONSHELF.format(id=row_id), headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 明细请求异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载明细失败: %s" % e))
            return

        d = data.get("data") or {}
        details = d.get("details") or d.get("data") or d.get("rows") or []
        self.controller.after(0, lambda: self._render_detail(win, row, details))

    def _render_detail(self, win, row, details):
        if not win.winfo_exists():
            return
        for w in win.winfo_children():
            w.destroy()

        top = tk.Frame(win, bg="#f7f8fa")
        top.pack(fill=tk.X, padx=10, pady=8)
        info = [
            ("所属仓库", row.get("warehouseName")),
            ("供应商编号", row.get("supplierNo")),
            ("供应商名称", row.get("supplierName")),
            ("入库类型", self.decode_receipt_type(row.get("receiptType"))),
            ("收货单号", row.get("receivingNo")),
            ("发运单号", row.get("shipNo")),
            ("上架人", (details[0].get("onshelf_by") if details else None)
             or row.get("updateByName")),
        ]
        for i, (label, val) in enumerate(info):
            r, c = divmod(i, 4)
            cell = tk.Frame(top, bg="#f7f8fa")
            cell.grid(row=r, column=c, sticky="w", padx=8, pady=2)
            tk.Label(cell, text="%s：" % label, bg="#f7f8fa", fg="#666666",
                     font=("微软雅黑", 9)).pack(side=tk.LEFT)
            tk.Label(cell, text=self.to_text(val) if label == "上架人" else (val or "-"),
                     bg="#f7f8fa", font=("微软雅黑", 9, "bold")).pack(side=tk.LEFT)

        frame = tk.Frame(win, bg="#f0f0f0")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        tree = ttk.Treeview(frame, columns=DETAIL_COLUMNS, show="headings", height=18)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            tree.heading(col, text=col)
            anchor = "w" if col in ("产品名称", "CARG全码/编码", "车型") else "center"
            tree.column(col, width=width, anchor=anchor)

        for i, d in enumerate(details):
            qty = self.receipt_qty(d)
            tree.insert("", "end", values=(
                i + 1,
                d.get("brandName") or d.get("brand") or "-",
                d.get("partCode") or "-",
                d.get("partName") or "-",
                self.decode_category(d.get("category_two")),
                d.get("model_number") or "-",
                qty,
                self.fmt_money(d.get("costPrice")) if d.get("costPrice") is not None else "-",
                self.receipt_amount(d),
                d.get("shelfLocationNo") or d.get("location_no") or "-",
                self.to_text(d.get("onshelf_by")),
            ))
        if not details:
            tree.insert("", "end", values=("-",) * len(DETAIL_COLUMNS))

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        tooltip_manager.attach_tooltip(tree)

    @staticmethod
    def receipt_qty(d):
        """上架明细数量：shelf_quantity 优先（onshelf 接口字段）"""
        for key in ('shelf_quantity', 'shelvesdQty', 'receivingQty', 'orderQty'):
            if d.get(key) is not None:
                try:
                    return float(d.get(key))
                except (TypeError, ValueError):
                    continue
        return 0

    def receipt_amount(self, d):
        """上架明细金额：totalAmt 优先，缺失按 单价×数量 兜底"""
        if d.get("totalAmt") is not None:
            return self.fmt_money(d.get("totalAmt"))
        try:
            price = float(d.get("costPrice") or 0)
        except (TypeError, ValueError):
            price = 0.0
        return self.fmt_money(price * self.receipt_qty(d))

    # ================================================================ 入库上架
    @staticmethod
    def can_shelf(row):
        """状态防护：部分验收 / 已验收 / 部分上架 可上架"""
        try:
            return int(row.get("receiptStatus")) in SHELVABLE_STATUS
        except (TypeError, ValueError):
            return False

    @staticmethod
    def remain_qty(d):
        """待上架 = shelvesQty - shelvesdQty（小于 0 归 0）"""
        try:
            total = float(d.get("shelvesQty") or 0)
        except (TypeError, ValueError):
            total = 0.0
        try:
            done = float(d.get("shelvesdQty") or 0)
        except (TypeError, ValueError):
            done = 0.0
        r = total - done
        return r if r > 0 else 0

    def open_shelf(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        if not self.can_shelf(row):
            messagebox.showwarning("提示", "仅「部分验收 / 已验收 / 部分上架」的单据可以上架")
            return
        row_id = row.get("id")
        if row_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法上架")
            return

        self._shelf_header = row
        # recordVersion 只在列表行上有，必须在打开上架窗时先取
        self._record_version = row.get("recordVersion") or 0

        win = tk.Toplevel(self)
        win.title("入库上架 - %s" % (row.get("receiptNo") or row.get("shipNo") or ""))
        win.geometry("980x640")
        self._shelf_win = win
        tk.Label(win, text="加载中...", font=("微软雅黑", 10)).pack(pady=20)
        threading.Thread(target=self._shelf_thread, args=(row_id, win), daemon=True).start()

    def _shelf_thread(self, row_id, win):
        try:
            r = self.controller.session.get(URL_DETAIL.format(id=row_id), headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 上架信息加载失败: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载上架信息失败: %s" % e))
            return

        d = data.get("data") or {}
        details = d.get("details") or d.get("data") or d.get("rows") or []
        emps = self.load_onshelf_persons()
        self.controller.after(0, lambda: self._render_shelf(win, details, emps))

    def _render_shelf(self, win, details, emps):
        if not win.winfo_exists():
            return
        for w in win.winfo_children():
            w.destroy()

        self.emp_list = emps or []
        emp_names = [""] + [e["employeeName"] for e in self.emp_list if e["employeeName"]]

        # ---- 顶层上架人 ----
        head = tk.Frame(win, bg="#f0f0f0")
        head.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(head, text="上架人:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.top_onshelf_var = tk.StringVar(value="")
        self.top_onshelf_cb = ttk.Combobox(head, textvariable=self.top_onshelf_var,
                                           values=emp_names, state="readonly", width=14)
        self.top_onshelf_cb.pack(side=tk.LEFT, padx=5)
        tk.Label(head, text="（必选；逐行默认跟随此项，可单独改）", bg="#f0f0f0",
                 fg="#666666", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        # 顶层变更时同步仍为旧值的行
        self._last_top = ""
        self.top_onshelf_var.trace_add("write", self._on_top_onshelf_change)

        # ---- 明细行（可滚动）----
        outer = tk.Frame(win, bg="#f0f0f0")
        outer.pack(fill=tk.BOTH, expand=True, padx=10)
        canvas = tk.Canvas(outer, bg="#f0f0f0", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body = tk.Frame(canvas, bg="#f0f0f0")
        canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        hdr = tk.Frame(body, bg="#f0f0f0")
        hdr.pack(fill=tk.X)
        for text, width in (("产品", 34), ("待上架", 8), ("上架库位", 16),
                            ("上架数量", 10), ("行上架人", 14)):
            tk.Label(hdr, text=text, bg="#f0f0f0", font=("微软雅黑", 9, "bold"),
                     width=width, anchor="w").pack(side=tk.LEFT, padx=3)

        self._shelf_rows = []
        for d in details:
            line = tk.Frame(body, bg="#f0f0f0")
            line.pack(fill=tk.X, pady=2)

            tk.Label(line, text=str(d.get("partName") or d.get("partCode") or "-"),
                     bg="#f0f0f0", width=34, anchor="w").pack(side=tk.LEFT, padx=3)
            remain = self.remain_qty(d)
            tk.Label(line, text=str(int(remain) if remain == int(remain) else remain),
                     bg="#f0f0f0", width=8, anchor="w").pack(side=tk.LEFT, padx=3)

            def_loc_no = d.get("shelfLocationNo") or d.get("pickingLocationNo") or ""
            def_loc_id = d.get("shelfLocationId") or d.get("pickingLocationId")

            loc_var = tk.StringVar(value=def_loc_no)
            loc_entry = ttk.Entry(line, textvariable=loc_var, width=16)
            loc_entry.pack(side=tk.LEFT, padx=3)

            qty_var = tk.StringVar(value=str(int(remain) if remain == int(remain) else remain))
            ttk.Entry(line, textvariable=qty_var, width=10).pack(side=tk.LEFT, padx=3)

            row_person_var = tk.StringVar(value="")
            ttk.Combobox(line, textvariable=row_person_var, values=emp_names,
                         state="readonly", width=12).pack(side=tk.LEFT, padx=3)

            item = {
                "data": d,
                "loc_var": loc_var,
                "qty_var": qty_var,
                "person_var": row_person_var,
                "_shelfLocationNo": def_loc_no,
                "_shelfLocationId": def_loc_id,
                "_locDirty": False,
            }
            self._shelf_rows.append(item)

            # 库位输入：聚焦时记录目标行，按键后防抖查询候选
            loc_entry.bind("<FocusIn>", lambda e, it=item: self._on_loc_focus(it))
            loc_entry.bind("<KeyRelease>", lambda e, it=item: self._on_loc_key(it))

        if not self._shelf_rows:
            tk.Label(body, text="暂无明细", bg="#f0f0f0", fg="#999999").pack(pady=20)

        # ---- 库位候选 ----
        loc_box = tk.LabelFrame(win, text="库位候选（双击填入当前行）", bg="#f0f0f0",
                                font=("微软雅黑", 9, "bold"))
        loc_box.pack(fill=tk.X, padx=10, pady=(6, 0))
        self.loc_list = tk.Listbox(loc_box, height=5)
        self.loc_list.pack(fill=tk.X, padx=5, pady=5)
        self.loc_list.bind("<Double-1>", lambda e: self._on_pick_location())

        # ---- 操作 ----
        actions = tk.Frame(win, bg="#f0f0f0")
        actions.pack(fill=tk.X, padx=10, pady=8)
        self.draft_btn = tk.Button(actions, text="暂存草稿", command=lambda: self.submit_shelf(True),
                                   bg="#2196F3", fg="white", relief=tk.FLAT, padx=14, pady=6)
        self.draft_btn.pack(side=tk.LEFT)
        self.shelf_btn = tk.Button(actions, text="确认上架", command=lambda: self.submit_shelf(False),
                                   bg="#4CAF50", fg="white", relief=tk.FLAT, padx=14, pady=6)
        self.shelf_btn.pack(side=tk.LEFT, padx=8)
        tk.Button(actions, text="取消", command=self._close_shelf_win,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14, pady=6).pack(side=tk.LEFT)

    def _on_top_onshelf_change(self, *_args):
        """顶层上架人变更：同步仍为旧值的明细行"""
        new_val = self.top_onshelf_var.get()
        old = getattr(self, "_last_top", "")
        for it in self._shelf_rows:
            if (it["person_var"].get() or "") == old:
                it["person_var"].set(new_val)
        self._last_top = new_val

    # ---------------------------------------------------------- 库位候选
    def _on_loc_focus(self, item):
        self._loc_target = item

    def _on_loc_key(self, item):
        self._loc_target = item
        item["_locDirty"] = True
        if self._loc_timer:
            try:
                self.after_cancel(self._loc_timer)
            except Exception:
                pass
        self._loc_timer = self.after(400, lambda: self._query_locations(item))

    def _query_locations(self, item):
        kw = (item["loc_var"].get() or "").strip()
        if not kw:
            self.loc_list.delete(0, tk.END)
            return
        # Tk 变量只能在主线程读取，仓库 ID 先取好再传给子线程
        warehouse_id = self.current_warehouse_id
        threading.Thread(target=self._loc_thread, args=(kw, warehouse_id), daemon=True).start()

    def _loc_thread(self, kw, warehouse_id):
        try:
            r = self.controller.session.get(URL_LOCATIONS, headers=HEADERS,
                                            params={'warehouseId': warehouse_id,
                                                    'locationNo': kw})
            if not self._check_response(r):
                return
            data = json.loads(r.text) or {}
            raw = data.get("data") or []
            items = raw if isinstance(raw, list) else (raw.get("data") or [])
        except Exception as e:
            print("[入库上架] 库位查询失败: %s" % e)
            items = []
        self.controller.after(0, lambda: self._render_locations(items))

    def _render_locations(self, items):
        self._loc_items = items or []
        self.loc_list.delete(0, tk.END)
        for it in self._loc_items:
            no = it.get("locationNo") or ""
            name = it.get("locationName") or ""
            self.loc_list.insert(tk.END, "%s%s" % (no, ("（%s）" % name) if name else ""))

    def _on_pick_location(self):
        sel = self.loc_list.curselection()
        if not sel or not self._loc_target:
            return
        idx = sel[0]
        if idx >= len(self._loc_items):
            return
        opt = self._loc_items[idx]
        self._loc_target["loc_var"].set(opt.get("locationNo") or "")
        self._loc_target["_shelfLocationNo"] = opt.get("locationNo") or ""
        self._loc_target["_shelfLocationId"] = opt.get("locationId")
        # 已从候选列表选择，取消「手输未选」标记
        self._loc_target["_locDirty"] = False

    # ---------------------------------------------------------- 提交
    def build_shelf_payload(self, is_draft=False):
        """构造上架报文（对齐安卓端 submitShelf）"""
        header = self._shelf_header or {}
        operator = (self.top_onshelf_var.get() or "").strip()
        if not operator:
            operator = (header.get("updateByName") or "").strip()

        detail_dto_list = []
        for item in self._shelf_rows:
            d = dict(item["data"])
            try:
                qty = float(item["qty_var"].get())
            except (TypeError, ValueError):
                qty = 0.0
            if qty < 0:
                qty = 0.0
            max_qty = self.remain_qty(d)
            if qty > max_qty:
                qty = max_qty
            qty_out = int(qty) if qty == int(qty) else qty

            loc_no = item["_shelfLocationNo"] or item["loc_var"].get() \
                or d.get("pickingLocationNo") or ""
            loc_id = item["_shelfLocationId"] or d.get("shelfLocationId")

            person = (item["person_var"].get() or "").strip() or operator

            row = dict(d)
            row["detailId"] = d.get("detailId") if d.get("detailId") is not None else d.get("detailsId")
            row["detailsId"] = d.get("detailsId") if d.get("detailsId") is not None else d.get("detailId")
            row["shelfLocationNo"] = loc_no
            row["shelfLocationId"] = loc_id
            row["shelvesQty"] = str(qty_out)          # web 以字符串提交
            row["onshelf_by"] = [person] if person else []   # 数组形式
            row["onshelf_by_name"] = person or ""
            if loc_id is not None:
                row["select_LOCATION_OPTIONS"] = [{"locationId": loc_id, "locationNo": loc_no}]
            detail_dto_list.append(row)

        payload = {
            "id": header.get("id"),
            "warehouseId": self.current_warehouse_id,
            "recordVersion": self._record_version,
            "checkStatus": CHECK_STATUS,
            "detailDtoList": detail_dto_list,
            "onshelf_by": operator,                   # 顶层字符串
        }
        if is_draft:
            payload["isSave"] = 1
        return payload

    def submit_shelf(self, is_draft=False):
        if not self._shelf_header:
            messagebox.showwarning("提示", "缺少单据信息，请重新打开上架")
            return
        operator = (self.top_onshelf_var.get() or "").strip()
        if not operator:
            messagebox.showwarning("提示", "请先选择上架人")
            return

        payload = self.build_shelf_payload(is_draft)
        if not is_draft and not any(float(x["shelvesQty"]) > 0 for x in payload["detailDtoList"]):
            messagebox.showwarning("提示", "上架数量不能为全 0")
            return

        for btn in (self.draft_btn, self.shelf_btn):
            btn.config(state="disabled")
        threading.Thread(target=self._shelf_submit_thread,
                         args=(payload, is_draft), daemon=True).start()

    def _shelf_submit_thread(self, payload, is_draft):
        ok_tip = "暂存成功" if is_draft else "上架成功"
        fail_tip = "暂存失败" if is_draft else "上架失败"
        try:
            r = self.controller.session.post(URL_SHELVES, headers=HEADERS,
                                             data=json.dumps(payload, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 提交异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "%s: %s" % (fail_tip, e)))
            self.controller.after(0, self._restore_shelf_btns)
            return

        if data.get("success") or data.get("resultCode") == 200 or data.get("code") == 200:
            self.controller.after(0, lambda: messagebox.showinfo("成功", ok_tip))
            self.controller.after(0, self._close_shelf_win)
            self.controller.after(0, lambda: self.query(reset_page=False))
        else:
            msg = data.get("errMsg") or data.get("message") or fail_tip
            self.controller.after(0, lambda: messagebox.showerror(fail_tip, str(msg)))
            self.controller.after(0, self._restore_shelf_btns)

    def _restore_shelf_btns(self):
        for btn in (getattr(self, "draft_btn", None), getattr(self, "shelf_btn", None)):
            if btn is not None and btn.winfo_exists():
                btn.config(state="normal")

    def _close_shelf_win(self):
        if self._shelf_win and self._shelf_win.winfo_exists():
            self._shelf_win.destroy()
        self._shelf_win = None
        self._shelf_rows = []
        self._shelf_header = None
        self._loc_target = None

    # ================================================================ 打印
    def open_print(self, mode):
        """打印上架清单 / 入库清单（先拉数预览，再打印）"""
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        row_id = row.get("id")
        if row_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法打印")
            return
        url = URL_DETAIL.format(id=row_id) if mode == 'shelf' else URL_ONSHELF.format(id=row_id)
        self.count_var.set("加载打印数据...")
        threading.Thread(target=self._print_thread, args=(url, mode, row), daemon=True).start()

    def _print_thread(self, url, mode, row):
        try:
            r = self.controller.session.get(url, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[入库上架] 打印数据加载失败: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载打印数据失败: %s" % e))
            self.controller.after(0, lambda: self.count_var.set(""))
            return

        d = data.get("data") or {}
        details = d.get("details") or d.get("data") or d.get("rows") or []
        group = (self.build_shelf_group(details, row) if mode == 'shelf'
                 else self.build_receipt_group(details, row))
        self.controller.after(0, lambda: self._show_print_window(mode, group))

    def build_shelf_group(self, details, row):
        """上架清单：数量取 shelvesdQty（已上架数量）"""
        items = []
        for d in details or []:
            try:
                num = float(d.get("shelvesdQty") if d.get("shelvesdQty") is not None
                            else (d.get("orderQty") if d.get("orderQty") is not None
                                  else d.get("receivingQty") or 0))
            except (TypeError, ValueError):
                num = 0
            items.append({
                "BRAND_NAME": d.get("brandName") or d.get("brand") or "",
                "PART_NO": d.get("partCode") or "",
                "PART_NAME": d.get("partName") or "",
                "CATEGORY_TWO": d.get("category_two") if d.get("category_two") is not None else "",
                "MODEL_NUMBER": d.get("model_number") or "",
                "NUM": num,
                "LOCATION": d.get("shelfLocationNo") or d.get("pickingLocationNo") or "",
            })
        return {
            "header": {
                "WAREHOUSE_NAME": self.short_brand(row.get("warehouseName") or self.warehouse_var.get() or ""),
                "DOC_NO": row.get("receivingNo") or row.get("shipNo") or "",
                "OPERATOR": row.get("updateByName") or "",
                "DATE": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
            "items": items,
        }

    def build_receipt_group(self, details, row):
        """入库清单：数量 shelf_quantity，金额 totalAmt"""
        items = []
        for d in details or []:
            qty = self.receipt_qty(d)
            try:
                price = float(d.get("costPrice") or 0)
            except (TypeError, ValueError):
                price = 0.0
            try:
                amount = float(d.get("totalAmt")) if d.get("totalAmt") is not None else price * qty
            except (TypeError, ValueError):
                amount = price * qty
            items.append({
                "BRAND_NAME": d.get("brandName") or d.get("brand") or "",
                "PART_NO": d.get("partCode") or "",
                "PART_NAME": d.get("partName") or "",
                "CATEGORY_TWO": d.get("category_two") if d.get("category_two") is not None else "",
                "MODEL_NUMBER": d.get("model_number") or "",
                "NUM": qty,
                "PRICE": price,
                "AMOUNT": amount,
                "LOCATION": d.get("location_no") or d.get("shelfLocationNo")
                            or d.get("pickingLocationNo") or "",
            })
        return {
            "header": {
                "WAREHOUSE_NAME": self.short_brand(row.get("warehouseName") or self.warehouse_var.get() or ""),
                "SUPPLIER_NAME": row.get("supplierName") or "",
                "SHIP_NO": row.get("shipNo") or "",
                "DOC_NO": row.get("receivingNo") or row.get("shipNo") or "",
                "OPERATOR": row.get("updateByName") or "",
                "DATE": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
            "items": items,
        }

    def _show_print_window(self, mode, group):
        self.count_var.set("共 %d 条收货单" % self.total)
        title = "上架清单" if mode == 'shelf' else "入库清单"
        win = tk.Toplevel(self)
        win.title("%s打印预览" % title)
        win.geometry("900x680")
        win.transient(self)

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="%s打印预览（%d 项）" % (title, len(group["items"])),
                 bg="#f7f8fa", fg="#fa8c16", font=("微软雅黑", 13, "bold")).pack(
            side=tk.LEFT, padx=12, pady=8)

        body = tk.Text(win, wrap=tk.WORD, font=("微软雅黑", 9), bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body.tag_configure("title", font=("微软雅黑", 15, "bold"), justify="center")
        body.tag_configure("h", font=("微软雅黑", 10, "bold"))

        h = group["header"]
        body.insert(tk.END, "\n%s\n" % title, "title")
        if mode == 'shelf':
            body.insert(tk.END, "仓库：%s    单据号：%s    操作人：%s    日期：%s\n" % (
                h.get("WAREHOUSE_NAME") or "-", h.get("DOC_NO") or "-",
                h.get("OPERATOR") or "-", h.get("DATE") or "-"))
            body.insert(tk.END, "品牌 | 零件编号 | 产品名称 | 分类 | 车型 | 数量 | 库位\n", "h")
        else:
            body.insert(tk.END, "仓库：%s    单据号：%s    供应商：%s    发运单号：%s    操作人：%s    日期：%s\n" % (
                h.get("WAREHOUSE_NAME") or "-", h.get("DOC_NO") or "-",
                h.get("SUPPLIER_NAME") or "-", h.get("SHIP_NO") or "-",
                h.get("OPERATOR") or "-", h.get("DATE") or "-"))
            body.insert(tk.END, "品牌 | 零件编号 | 产品名称 | 分类 | 车型 | 数量 | 单价 | 金额 | 库位\n", "h")

        total_num = 0.0
        total_amount = 0.0
        for it in group["items"]:
            total_num += float(it.get("NUM") or 0)
            if mode == 'shelf':
                body.insert(tk.END, "{0} | {1} | {2} | {3} | {4} | {5} | {6}\n".format(
                    it.get("BRAND_NAME") or "", it.get("PART_NO") or "", it.get("PART_NAME") or "",
                    self.decode_category(it.get("CATEGORY_TWO")), it.get("MODEL_NUMBER") or "",
                    it.get("NUM"), it.get("LOCATION") or ""))
            else:
                total_amount += float(it.get("AMOUNT") or 0)
                body.insert(tk.END, "{0} | {1} | {2} | {3} | {4} | {5} | {6:.2f} | {7:.2f} | {8}\n".format(
                    it.get("BRAND_NAME") or "", it.get("PART_NO") or "", it.get("PART_NAME") or "",
                    self.decode_category(it.get("CATEGORY_TWO")), it.get("MODEL_NUMBER") or "",
                    it.get("NUM"), float(it.get("PRICE") or 0), float(it.get("AMOUNT") or 0),
                    it.get("LOCATION") or ""))
        body.insert(tk.END, "合计数量：%s%s\n" % (
            total_num, ("    合计金额：¥{:,.2f}".format(total_amount)) if mode == 'receipt' else ""))
        body.configure(state=tk.DISABLED)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="打 印", command=lambda: self.print_via_clodop(mode, group, win),
                  bg="#fa8c16", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def _build_print_html(self, mode, group):
        h = group["header"]
        title = "上架清单" if mode == 'shelf' else "入库清单"
        rows = ""
        for it in group["items"]:
            if mode == 'shelf':
                rows += (
                    "<tr><td>{0}</td><td style='text-align:center'>{1}</td>"
                    "<td style='text-align:left'>{2}</td><td>{3}</td><td>{4}</td>"
                    "<td>{5}</td><td>{6}</td></tr>".format(
                        it.get("BRAND_NAME") or "", it.get("PART_NO") or "",
                        it.get("PART_NAME") or "", self.decode_category(it.get("CATEGORY_TWO")),
                        it.get("MODEL_NUMBER") or "", it.get("NUM"), it.get("LOCATION") or ""))
            else:
                rows += (
                    "<tr><td>{0}</td><td style='text-align:center'>{1}</td>"
                    "<td style='text-align:left'>{2}</td><td>{3}</td><td>{4}</td>"
                    "<td>{5}</td><td style='text-align:right'>{6:.2f}</td>"
                    "<td style='text-align:right'>{7:.2f}</td><td>{8}</td></tr>".format(
                        it.get("BRAND_NAME") or "", it.get("PART_NO") or "",
                        it.get("PART_NAME") or "", self.decode_category(it.get("CATEGORY_TWO")),
                        it.get("MODEL_NUMBER") or "", it.get("NUM"),
                        float(it.get("PRICE") or 0), float(it.get("AMOUNT") or 0),
                        it.get("LOCATION") or ""))
        if mode == 'shelf':
            head_html = (
                "<div>仓库：%s　单据号：%s　操作人：%s　日期：%s</div>" % (
                    h.get("WAREHOUSE_NAME") or "", h.get("DOC_NO") or "",
                    h.get("OPERATOR") or "", h.get("DATE") or ""))
            th = ("<th>品牌</th><th>零件编号</th><th>产品名称</th><th>分类</th>"
                  "<th>车型</th><th>数量</th><th>库位</th>")
        else:
            head_html = (
                "<div>仓库：%s　单据号：%s　供应商：%s　发运单号：%s　操作人：%s　日期：%s</div>" % (
                    h.get("WAREHOUSE_NAME") or "", h.get("DOC_NO") or "",
                    h.get("SUPPLIER_NAME") or "", h.get("SHIP_NO") or "",
                    h.get("OPERATOR") or "", h.get("DATE") or ""))
            th = ("<th>品牌</th><th>零件编号</th><th>产品名称</th><th>分类</th>"
                  "<th>车型</th><th>数量</th><th>单价</th><th>金额</th><th>库位</th>")
        return (
            "<style>div{width:97%} body{margin:0;padding:0}</style>"
            "<div class='print-page'>"
            "<div class='print-page-title' style='text-align:center;font-size:20px;font-weight:700'>"
            + title + "</div>"
            "<div class='print-page-info' style='font-size:13px'>" + head_html + "</div>"
            "<table border='1' cellspacing='0' style='width:98%;font-size:12px;"
            "border-collapse:collapse;text-align:center'>"
            "<thead><tr>" + th + "</tr></thead><tbody>" + rows + "</tbody></table></div>")

    def print_via_clodop(self, mode, group, win):
        """CLodop WebSocket 打印（复用 other_outbound_apply 的协议）"""
        try:
            import websocket
        except ImportError:
            messagebox.showerror("打印失败", "未安装 websocket 模块，无法连接 CLodop")
            return
        try:
            task_name = "上架清单打印" if mode == 'shelf' else "入库清单打印"
            html_content = self._build_print_html(mode, group)
            now = datetime.now()
            task_id = "PY%02d%02d%02d_1" % (now.hour, now.minute, now.second)
            delim = "\f\f"
            printer_name = "EPSON LQ-630K ESC/P2"
            ws = websocket.create_connection("ws://127.0.0.1:8000/c_webskt/", timeout=10)
            msg = (
                "post:charset=丂{d}"
                "tid={tid}{d}"
                "act=print{d}"
                "browseurl=PYTHON_CLODOP{d}"
                "companyname=用友汽车信息科技（上海）股份有限公司{d}"
                "license=FA9A697F2551BCE81BD852A4EB520525347{d}"
                "licensea=用友汽車信息科技（上海）股份有限公司{d}"
                "licenseb=C66313BD8413BD0174C2CADD29F5380CD92{d}"
                "licensec=Yonyou Auto Information Technology (Shanghai) Co., Ltd.{d}"
                "licensed=941DF3639D9F5679867946141A31424B4E6{d}"
                "top={d}left={d}width={d}height={d}"
                "printtask={task}{d}"
                "printerindex={printer}{d}"
                "orient=1{d}pagewidth=0{d}pageheight=0{d}pagename=A4{d}"
                "printcopies=1{d}itemcount=1{d}"
                "1_type=4{d}1_top=30{d}1_left=3mm{d}1_width=100%{d}1_height=100%{d}"
                "1_content={content}{d}"
                "1_itemstylenames={d}"
                "printmodenames=;left;top;width;height{d}"
                "printstyleclassnames={d}"
            ).format(tid=task_id, task=task_name, printer=printer_name,
                     content=html_content, d=delim)
            ws.send(msg)
            ws.close()
            messagebox.showinfo("成功", "已发送打印任务到 %s" % printer_name)
            win.destroy()
        except Exception as e:
            messagebox.showerror("打印失败",
                                 "CLodop WebSocket打印失败: %s\n\n请确保 CLodop 服务已启动（localhost:8000）" % e)

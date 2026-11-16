# -*- coding: utf-8 -*-
"""出入库流水记录

对齐 fycarg-pda 安卓端 src/views/InventoryRecord.vue，接口与业务逻辑保持一致：

- 查询：GET /dmscloud.part/warehouse/asicDataQuery/inventoryQuery/searchInventoryRecord
  （无独立合计/导出端点，total 取自响应 data.total；安卓端亦无导出）

与前面模块的差异（关键坑位）：
1. 仓库参数用 storage_code（字符串），取自 warehouse_mapping.get_storage_code（与库存冻结一致），
   不是装箱明细的 warehouse_id 数字、也不是销售明细的 storage_id 数字。
2. 双维度切换：group=1 库存维度（18 列）/ group=2 库位库存维度（21 列，多 库位/批次号/批次价）。
   切换维度会重建表格列并重置到第 1 页重新查询（对齐安卓端 switchGroup）。
3. 字典码表来自 /dmscloud.basedata/dicts，涉及 8560(操作类型) / 8561(业务类型)；
   页面初始化异步拉取，下拉先显示「全部」。
4. 操作日期默认今天~今天（对齐安卓端 todayStr，非月初~今天）。
5. 点击行弹出流水明细（列表字段已含全部信息，无需额外接口）。
6. 数字格式化 fmtNum：空/非数 -> '-'，整数不补小数、否则保留两位；fmtMoney 始终两位小数。
7. 服务端分页 pageNum+limit，每页 20 条；序号为全局序号 (pageNum-1)*20+idx+1。

列高亮说明：安卓端「操作前」灰、「操作后」绿、「操作后冻结」红为单格 CSS 着色；ttk.Treeview
不支持单格着色，本端仅保留隔行底色，列语义与字段顺序与安卓端完全一致。
"""

import json
import threading
from datetime import date

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

# 接口地址（与安卓端 axios baseURL + path 一致）
URL_QUERY = 'https://xb.fy-carg.com/dmscloud.part/warehouse/asicDataQuery/inventoryQuery/searchInventoryRecord'
URL_DICTS = 'https://xb.fy-carg.com/dmscloud.basedata/dicts'

# 每页条数（与安卓端 pageSize 保持一致）
PAGE_SIZE = 20

# 字典类型（对齐安卓端 loadDicts）
DICT_TYPES = ['8560', '8561']
DICT_LABELS = {
    '8560': '操作类型',
    '8561': '业务类型',
}
# dict type -> 对应 Combobox 的变量名（用于 build_params 取值）
DICT_VAR_NAMES = {
    '8560': 'operation_type_var',
    '8561': 'business_type_var',
}

# 列定义（两种维度）
# 库存维度（group=1，18 列）
COLUMNS_G1 = ["序号", "类型", "业务类型", "业务单据号", "仓库", "CARG全码/产品编码",
              "产品名称", "品牌编码", "品牌名称", "操作人", "操作日期",
              "操作前库存数量", "操作前冻结数量", "操作前可用数量", "操作数量",
              "操作后库存数量", "操作后冻结数量", "操作后可用数量"]
WIDTHS_G1 = [50, 90, 110, 170, 90, 150, 220, 110, 130, 90, 150,
             100, 100, 100, 90, 110, 100, 100]

# 库位库存维度（group=2，21 列：在「仓库」后插入 库位/批次号/批次价）
COLUMNS_G2 = ["序号", "类型", "业务类型", "业务单据号", "仓库", "库位", "批次号", "批次价",
              "CARG全码/产品编码", "产品名称", "品牌编码", "品牌名称", "操作人", "操作日期",
              "操作前库存数量", "操作前冻结数量", "操作前可用数量", "操作数量",
              "操作后库存数量", "操作后冻结数量", "操作后可用数量"]
WIDTHS_G2 = [50, 90, 110, 170, 90, 90, 110, 90, 150, 220, 110, 130, 90, 150,
             100, 100, 100, 90, 110, 100, 100]

# 右对齐（数字）列
RIGHT_COLS = {"操作前库存数量", "操作前冻结数量", "操作前可用数量", "操作数量",
              "操作后库存数量", "操作后冻结数量", "操作后可用数量", "批次价"}
# 等宽字体（编码类）列
MONO_COLS = {"业务单据号", "CARG全码/产品编码", "品牌编码", "库位", "批次号"}


class InventoryRecordPage(BasePage):
    """出入库流水记录页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 当前页行数据（原始 dict 列表）
        self.total = 0            # 查询总条数
        self.page_num = 1         # 当前页码
        self.page_size = PAGE_SIZE
        self.queried = False      # 是否已执行过查询
        self.loading = False      # 请求进行中（防重入）
        self.active_group = 1     # 1=库存维度 / 2=库位库存维度
        # 字典码表：type -> {code: desc}
        self.dict_maps = {}
        # 字典下拉：type -> {desc(显示文本): code}
        self.dict_option_maps = {}
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        """构建用户界面"""
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_group_tabs(main_container)
        self.setup_filter_panel(main_container)
        self.setup_count_bar(main_container)
        self.setup_data_table(main_container)
        self.setup_pagination_controls(main_container)

        # 异步拉取字典（8560/8561）
        self.load_dicts()

    def setup_group_tabs(self, parent):
        """维度切换：库存维度 / 库位库存维度"""
        tab_frame = tk.Frame(parent, bg="#f0f0f0")
        tab_frame.pack(fill=tk.X, pady=(0, 5))

        self.g1_btn = tk.Button(tab_frame, text="库存维度", width=14,
                                command=lambda: self.toggle_group(1))
        self.g1_btn.pack(side=tk.LEFT, padx=2)
        self.g2_btn = tk.Button(tab_frame, text="库位库存维度", width=14,
                                command=lambda: self.toggle_group(2))
        self.g2_btn.pack(side=tk.LEFT, padx=2)
        self._update_group_tabs()

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="操作类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.operation_type_var = tk.StringVar(value="全部")
        self.operation_type_cb = ttk.Combobox(row1, textvariable=self.operation_type_var,
                                              values=["全部"], state="readonly", width=10)
        self.operation_type_cb.set("全部")
        self.operation_type_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="业务类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.business_type_var = tk.StringVar(value="全部")
        self.business_type_cb = ttk.Combobox(row1, textvariable=self.business_type_var,
                                            values=["全部"], state="readonly", width=10)
        self.business_type_cb.set("全部")
        self.business_type_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="业务单据号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.business_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.business_no_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="CARG全码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_code_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_code_var, width=16).pack(side=tk.LEFT, padx=5)

        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=5)
        tk.Label(row2, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.part_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.part_name_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="品牌编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.brand_code_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.brand_code_var, width=12).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="品牌名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.brand_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.brand_name_var, width=12).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="操作人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.created_by_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.created_by_name_var, width=12).pack(side=tk.LEFT, padx=5)

        row3 = tk.Frame(filter_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=5)
        tk.Label(row3, text="操作日期起:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date())
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row3, text="操作日期止:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date())
        self.end_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row3, text="库位:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.location_no_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.location_no_var, width=12).pack(side=tk.LEFT, padx=5)

        btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        btn_row.pack(fill=tk.X, pady=(8, 2))
        tk.Button(btn_row, text="查询", command=lambda: self.query(True), **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_count_bar(self, parent):
        """查询条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        """构建流水表格（按当前维度初始化列）"""
        table_frame = tk.LabelFrame(parent, text="出入库流水", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=self._current_columns(),
                                show="headings", height=16)
        self._apply_columns_style()
        self._configure_columns()

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
        self.tree.bind("<Double-1>", self.on_row_double_click)

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

    # ------------------------------------------------------------------ 列/维度
    def _current_columns(self):
        return COLUMNS_G1 if self.active_group == 1 else COLUMNS_G2

    def _current_widths(self):
        return WIDTHS_G1 if self.active_group == 1 else WIDTHS_G2

    def _anchor(self, col):
        if col == "序号":
            return "center"
        if col in RIGHT_COLS:
            return "e"
        return "w"

    def _apply_columns_style(self):
        """隔行底色（单格着色在 ttk 不可行，仅保留隔行）"""
        self.tree.tag_configure("odd", background="#fafafa")

    def _configure_columns(self):
        """按当前维度设置表头/列宽/对齐"""
        cols = self._current_columns()
        widths = self._current_widths()
        for col, width in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=self._anchor(col))

    def _apply_group_columns(self, group):
        """切换维度时重建表格列（清除已渲染行）"""
        self.active_group = group
        cols = self._current_columns()
        self.tree["columns"] = cols
        # 清空旧的列宽配置，避免残留
        for child in self.tree.get_children():
            self.tree.delete(child)
        self._configure_columns()

    def _update_group_tabs(self):
        active_bg, active_fg = "#1989fa", "white"
        inactive_bg, inactive_fg = "#f0f0f0", "#323233"
        for btn, g in ((self.g1_btn, 1), (self.g2_btn, 2)):
            if g == self.active_group:
                btn.config(bg=active_bg, fg=active_fg, relief=tk.FLAT)
            else:
                btn.config(bg=inactive_bg, fg=inactive_fg, relief=tk.FLAT)

    def toggle_group(self, group):
        """切换维度（库存/库位库存），重建列并重置到第 1 页重新查询"""
        if group == self.active_group:
            return
        self._apply_group_columns(group)
        self._update_group_tabs()
        self.page_num = 1
        if self.queried:
            self.query(reset_page=False)

    # ------------------------------------------------------------------ 工具
    @property
    def total_pages(self):
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @staticmethod
    def def_date():
        """操作日期默认值：今天（对齐安卓端 todayStr）"""
        return date.today()

    @staticmethod
    def fmt_num(val):
        """数字格式化：整数不显示小数，否则保留两位（对齐安卓端 fmtNum）"""
        if val is None or val == "":
            return "-"
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    @staticmethod
    def fmt_money(val):
        """金额格式化：非数字显示 '-'，否则两位小数（对齐安卓端 fmtMoney）"""
        if val is None or val == "":
            return "-"
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return "%.2f" % n

    def _check_response(self, response):
        """检查响应中的登录状态"""
        return not self.controller.check_login_status(response)

    def map_dict(self, type_code, val):
        """字典码表映射：命中返回中文，否则原值；空值返回 '-'（对齐安卓端 dictLabel）"""
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

    def reset_form(self):
        """重置查询条件（仓库保持当前选择，日期恢复今天~今天）"""
        self.operation_type_cb.set("全部")
        self.business_type_cb.set("全部")
        self.business_no_var.set("")
        self.part_code_var.set("")
        self.part_name_var.set("")
        self.brand_code_var.set("")
        self.brand_name_var.set("")
        self.created_by_name_var.set("")
        self.location_no_var.set("")
        self.start_cal.set_date(self.def_date())
        self.end_cal.set_date(self.def_date())

    def build_params(self):
        """构造查询参数（对齐安卓端 buildParams）"""
        warehouse_name = self.warehouse_var.get()
        storage_code = get_storage_code(warehouse_name)
        return {
            "group": self.active_group,
            "operationType": self._dict_code("8560"),
            "businessType": self._dict_code("8561"),
            "businessNo": self.business_no_var.get().strip(),
            "partCode": self.part_code_var.get().strip(),
            "partName": self.part_name_var.get().strip(),
            "brandCode": self.brand_code_var.get().strip(),
            "brandName": self.brand_name_var.get().strip(),
            "createdByName": self.created_by_name_var.get().strip(),
            "createdAtStart": self.start_cal.get() or "",
            "createdAtEnd": self.end_cal.get() or "",
            "storageCode": storage_code,
            "locationNo": self.location_no_var.get().strip(),
            "pageNum": self.page_num,
            "limit": self.page_size,
        }

    # ------------------------------------------------------------------ 查询
    def query(self, reset_page=True):
        """执行查询"""
        if self.loading:
            return
        if reset_page:
            self.page_num = 1

        params = self.build_params()
        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[出入库流水] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[出入库流水] 请求异常: {e}")
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

    def _render_rows(self, rows, total):
        """渲染列表（主线程）"""
        self.rows = rows
        self.total = total
        self.queried = True

        for item in self.tree.get_children():
            self.tree.delete(item)

        base = (self.page_num - 1) * self.page_size
        for idx, row in enumerate(rows):
            values = self._build_values(row, base + idx + 1)
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        gname = "库存维度" if self.active_group == 1 else "库位库存维度"
        self.count_var.set(f"{gname}流水 共 {total} 条")
        self.update_page_info()
        if total == 0:
            messagebox.showinfo("查询结果", "无流水记录")

    def _build_values(self, row, seq):
        """根据当前维度构造行值元组"""
        if self.active_group == 1:
            return (
                seq,
                self.map_dict("8560", row.get("operation_type")),
                self.map_dict("8561", row.get("business_type")),
                row.get("business_no") or "-",
                row.get("warehouse_name") or "-",
                row.get("part_code") or "-",
                row.get("part_name") or "-",
                row.get("brand_code") or "-",
                row.get("brand_name") or "-",
                row.get("created_by_name") or "-",
                row.get("created_at") or "-",
                self.fmt_num(row.get("inventory_quantity")),
                self.fmt_num(row.get("frozen_inventory")),
                self.fmt_num(row.get("residue_number")),
                self.fmt_num(row.get("operation_quantity")),
                self.fmt_num(row.get("new_inventory_quantity")),
                self.fmt_num(row.get("new_frozen_inventory")),
                self.fmt_num(row.get("new_residue_number")),
            )
        # group=2：库位库存维度
        return (
            seq,
            self.map_dict("8560", row.get("operation_type")),
            self.map_dict("8561", row.get("business_type")),
            row.get("business_no") or "-",
            row.get("warehouse_name") or "-",
            row.get("location_no") or "-",
            row.get("batch") or "-",
            self.fmt_money(row.get("batch_price")),
            row.get("part_code") or "-",
            row.get("part_name") or "-",
            row.get("brand_code") or "-",
            row.get("brand_name") or "-",
            row.get("created_by_name") or "-",
            row.get("created_at") or "-",
            self.fmt_num(row.get("inventory_quantity")),
            self.fmt_num(row.get("frozen_inventory")),
            self.fmt_num(row.get("residue_number")),
            self.fmt_num(row.get("operation_quantity")),
            self.fmt_num(row.get("new_inventory_quantity")),
            self.fmt_num(row.get("new_frozen_inventory")),
            self.fmt_num(row.get("new_residue_number")),
        )

    # ------------------------------------------------------------------ 分页
    def update_page_info(self):
        self.page_info_var.set(f"第 {self.page_num}/{self.total_pages} 页 (共 {self.total} 条)")

    def go_to_page(self, page):
        """翻页（服务端分页，重新请求）"""
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
            print(f"[出入库流水-字典] 拉取失败: {e}")
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
        mapping = {
            "8560": (self.operation_type_var, self.operation_type_cb),
            "8561": (self.business_type_var, self.business_type_cb),
        }
        for t, (var, cb) in mapping.items():
            texts = ["全部"] + list(self.dict_option_maps.get(t, {}).keys())
            cb.config(values=texts)
            if var.get() not in texts:
                var.set("全部")

    # -------------------------------------------------------- 流水明细弹层
    def on_row_double_click(self, event):
        """双击行打开流水明细"""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        index = self.tree.index(row_id)
        if 0 <= index < len(self.rows):
            self.open_detail(self.rows[index])

    def open_detail(self, row):
        """打开流水明细窗口（列表字段已含全部信息，无需额外接口）"""
        win = tk.Toplevel(self)
        win.title("流水明细")
        win.geometry("460x600")
        win.transient(self)
        win.grab_set()

        header = tk.Frame(win, bg="#f7f8fa")
        header.pack(fill=tk.X)
        tk.Label(header, text=row.get("business_no") or "-", bg="#f7f8fa",
                 fg="#1989fa", font=("Consolas", 11)).pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(header, text=row.get("part_name") or "-", bg="#f7f8fa",
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=10, pady=6)

        body = tk.Frame(win, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for key, val in self.detail_lines(row):
            line = tk.Frame(body, bg="#ffffff", relief=tk.GROOVE, bd=1)
            line.pack(fill=tk.X, padx=5, pady=3)
            tk.Label(line, text=key, bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=18, anchor="w").pack(side=tk.LEFT, padx=8, pady=4)
            tk.Label(line, text=str(val), bg="#ffffff", anchor="w",
                     font=("微软雅黑", 10), wraplength=260, justify="left").pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=4)

        tk.Button(win, text="关闭", command=win.destroy,
                  bg="#e1e1e1", padx=20, pady=5, bd=0).pack(pady=10)

    def detail_lines(self, row):
        """明细字段（对齐安卓端 detailLines）"""
        lines = [
            ("仓库", f"{row.get('warehouse_name') or ''}（{row.get('warehouse_code') or ''}）"),
            ("业务单据号", row.get("business_no") or "-"),
            ("业务类型", self.map_dict("8561", row.get("business_type"))),
            ("操作类型", self.map_dict("8560", row.get("operation_type"))),
            ("操作人", row.get("created_by_name") or "-"),
            ("操作日期", row.get("created_at") or "-"),
            ("CARG全码", row.get("part_code") or "-"),
            ("产品名称", row.get("part_name") or "-"),
            ("品牌编码", row.get("brand_code") or "-"),
            ("品牌名称", row.get("brand_name") or "-"),
        ]
        if self.active_group == 2:
            lines.append(("库位", row.get("location_no") or "-"))
            lines.append(("批次号", row.get("batch") or "-"))
            lines.append(("批次价", self.fmt_money(row.get("batch_price"))))
        lines.append(("操作前库存数量", self.fmt_num(row.get("inventory_quantity"))))
        lines.append(("操作前冻结数量", self.fmt_num(row.get("frozen_inventory"))))
        lines.append(("操作前可用数量", self.fmt_num(row.get("residue_number"))))
        lines.append(("操作数量", self.fmt_num(row.get("operation_quantity"))))
        lines.append(("操作后库存数量", self.fmt_num(row.get("new_inventory_quantity"))))
        lines.append(("操作后冻结数量", self.fmt_num(row.get("new_frozen_inventory"))))
        lines.append(("操作后可用数量", self.fmt_num(row.get("new_residue_number"))))
        lines.append(("备注", row.get("notes") or "-"))
        return lines

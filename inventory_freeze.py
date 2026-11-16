# -*- coding: utf-8 -*-
"""库存冻结明细查询

对齐 fycarg-pda 安卓端 src/views/InventoryFreeze.vue，接口与业务逻辑保持一致：

- 主查询：GET /dmscloud.part/warehouse/asicDataQuery/freezeDetailQuery
- 合计：  GET /dmscloud.part/warehouse/asicDataQuery/freezeDetailQuery/pageQuerySummary
- 明细：  GET /dmscloud.part/warehouse/asicDataQuery/freezeDetailQuery/pageQueryOrderDetail

对应安卓端交互：
- 查询条件：仓库 / 单据冻结数大于 / CARG全码(产品编码) / 产品名称，至少一项非空
- 列表 14 列，冻结库存列标红，总可用数 = 总库存 - 冻结库存
- 服务端分页（pageNum + limit，每页 20 条）
- 合计区展示总库存 / 冻结库存 / 销售单冻结 / 总可用数合计
- 点击行查看冻结单据明细（销售单 / SO单 / 出库单 / 拣货单 / 调拨单 五类）
"""

import json
import threading

import tkinter as tk
from tkinter import ttk, messagebox

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import WAREHOUSE_CODE_MAPPING, get_storage_code

# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

# 接口基址（与安卓端 axios baseURL + path 一致）
API_BASE = 'https://xb.fy-carg.com/dmscloud.part/warehouse/asicDataQuery/freezeDetailQuery'
URL_QUERY = API_BASE
URL_SUMMARY = API_BASE + '/pageQuerySummary'
URL_ORDER_DETAIL = API_BASE + '/pageQueryOrderDetail'

# 每页条数（与安卓端 pageSize 保持一致）
PAGE_SIZE = 20

# 列表列定义（对齐安卓端表头）
COLUMNS = ["序号", "仓库", "CARG全码", "产品名称", "品牌", "总库存", "冻结库存",
           "销售单冻结", "SO单冻结", "出库单冻结", "拣货单冻结", "调拨单冻结",
           "总可用数", "运单数量"]
COLUMN_WIDTHS = [50, 80, 170, 260, 120, 80, 80, 90, 80, 90, 90, 90, 80, 80]

# 冻结单据明细分组（顺序与安卓端一致）
DETAIL_SECTIONS = [
    ("销售单冻结", "salesOrder", "SALES_ORDER_FROZEN"),
    ("SO单冻结", "soOrder", "SO_ORDER_FROZEN"),
    ("出库单冻结", "outboundOrder", "OUTBOUND_ORDER_FROZEN"),
    ("拣货单冻结", "pickingOrder", "PICKING_ORDER_FROZEN"),
    ("调拨单冻结", "transferOrder", "TRANSFER_ORDER_FROZEN"),
]


class InventoryFreezePage(BasePage):
    """库存冻结明细查询页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 当前页行数据（原始 dict 列表）
        self.total = 0            # 查询总条数
        self.page_num = 1         # 当前页码
        self.page_size = PAGE_SIZE
        self.queried = False      # 是否已执行过查询
        self.loading = False      # 请求进行中（防重入）
        self.summary = {
            "TOTAL_INVENTORY_ALL": 0,
            "FROZEN_INVENTORY_ALL": 0,
            "SALES_ORDER_FROZEN_ALL": 0,
            "AVAILABLE_ALL": 0,
        }
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

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        # 仓库（下拉，默认第一个仓库，可切"全部"）
        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=["全部"] + warehouses,
                                         state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "全部")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        # 单据冻结数大于
        tk.Label(row1, text="单据冻结数大于:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.freeze_num_var = tk.StringVar(value="0")
        ttk.Entry(row1, textvariable=self.freeze_num_var, width=8).pack(side=tk.LEFT, padx=5)

        # CARG全码 / 产品编码
        tk.Label(row1, text="CARG全码/产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_code_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_code_var, width=20).pack(side=tk.LEFT, padx=5)

        # 产品名称
        tk.Label(row1, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_name_var, width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(row1, text="查询", command=self.query, **btn_style).pack(side=tk.LEFT, padx=(15, 5))
        tk.Button(row1, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_count_bar(self, parent):
        """查询条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        """构建明细表格"""
        table_frame = tk.LabelFrame(parent, text="库存冻结明细", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "center" if col not in ("产品名称", "CARG全码") else "w"
            self.tree.column(col, width=width, anchor=anchor)

        # 冻结库存列标红（对齐安卓端 .frozen 样式）
        self.tree.tag_configure("frozen", foreground="#ee0a24")
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

        # 产品名称列内容较长，附加悬停提示
        tooltip_manager.attach_tooltip(self.tree)
        # 双击行查看冻结单据明细（安卓端为点击行）
        self.tree.bind("<Double-1>", self.on_row_double_click)

    def setup_summary_bar(self, parent):
        """合计信息条（数据来自 pageQuerySummary）"""
        summary_frame = tk.Frame(parent, bg="#f0f0f0")
        summary_frame.pack(fill=tk.X, pady=(5, 0))

        self.summary_vars = {}
        items = [
            ("TOTAL_INVENTORY_ALL", "总库存合计"),
            ("FROZEN_INVENTORY_ALL", "冻结库存合计"),
            ("SALES_ORDER_FROZEN_ALL", "销售单冻结合计"),
            ("AVAILABLE_ALL", "总可用数合计"),
        ]
        for key, label in items:
            var = tk.StringVar(value="0")
            self.summary_vars[key] = var
            item_frame = tk.Frame(summary_frame, bg="#ffffff", relief=tk.RIDGE, bd=1)
            item_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            tk.Label(item_frame, text=label, bg="#ffffff", fg="#666666",
                     font=("微软雅黑", 9)).pack(pady=(4, 0))
            fg = "#ee0a24" if key == "FROZEN_INVENTORY_ALL" else "#323233"
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
    def fmt_num(val):
        """数字格式化：整数不显示小数，否则保留两位（对齐安卓端 fmtNum）"""
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    @staticmethod
    def avail_num(row):
        """总可用数 = 总库存 - 冻结库存（对齐安卓端 availNum）"""
        try:
            total = float(row.get("TOTAL_INVENTORY") or 0)
            frozen = float(row.get("FROZEN_INVENTORY") or 0)
        except (TypeError, ValueError):
            return 0
        return total - frozen

    def _check_response(self, response):
        """检查响应中的登录状态"""
        return not self.controller.check_login_status(response)

    def reset_form(self):
        """重置查询条件"""
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb.set(warehouses[0] if warehouses else "全部")
        self.part_code_var.set("")
        self.part_name_var.set("")
        self.freeze_num_var.set("0")

    def build_params(self):
        """构造查询参数（pageNum + limit，与安卓端 buildParams 一致）"""
        warehouse_name = self.warehouse_var.get()
        storage_code = "" if warehouse_name == "全部" else get_storage_code(warehouse_name)
        try:
            freeze_num = int(float(self.freeze_num_var.get() or 0))
        except ValueError:
            freeze_num = 0
        return {
            "partCode": self.part_code_var.get().strip(),
            "partName": self.part_name_var.get().strip(),
            "storage_code": storage_code,
            "freezeNum": freeze_num,
            "pageNum": self.page_num,
            "limit": self.page_size,
        }

    def build_summary_params(self):
        """合计查询参数（与主查询一致，不含分页）"""
        params = self.build_params()
        params.pop("pageNum", None)
        params.pop("limit", None)
        return params

    # ------------------------------------------------------------------ 查询
    def query(self, reset_page=True):
        """执行查询（reset_page=True 时回到第一页，并重新拉取合计）"""
        if self.loading:
            return
        if reset_page:
            self.page_num = 1

        params = self.build_params()
        # 至少输入一个查询条件（对齐安卓端校验）
        if not params["storage_code"] and not params["partCode"] and not params["partName"]:
            messagebox.showwarning("提示", "请至少输入一个查询条件（仓库/编码/名称）")
            return

        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params, reset_page),
                         daemon=True).start()

    def _query_thread(self, params, fetch_summary):
        """查询线程"""
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[库存冻结查询] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[库存冻结查询] 请求异常: {e}")
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

        if fetch_summary:
            self.fetch_summary()

    def _render_rows(self, rows, total):
        """渲染列表（主线程）"""
        self.rows = rows
        self.total = total
        self.queried = True

        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, row in enumerate(rows):
            values = (
                idx + 1,
                row.get("WAREHOUSE_NAME") or "-",
                row.get("PART_CODE") or "-",
                row.get("PART_NAME") or "-",
                row.get("BRAND_NAME") or "-",
                self.fmt_num(row.get("TOTAL_INVENTORY")),
                self.fmt_num(row.get("FROZEN_INVENTORY")),
                self.fmt_num(row.get("SALES_ORDER_FROZEN")),
                self.fmt_num(row.get("SO_ORDER_FROZEN")),
                self.fmt_num(row.get("OUTBOUND_ORDER_FROZEN")),
                self.fmt_num(row.get("PICKING_ORDER_FROZEN")),
                self.fmt_num(row.get("TRANSFER_ORDER_FROZEN")),
                self.fmt_num(self.avail_num(row)),
                self.fmt_num(row.get("WAYBILL_ORDER_NUM")),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        self.count_var.set(f"共 {total} 条冻结明细")
        self.update_page_info()
        if total == 0:
            messagebox.showinfo("查询结果", "无冻结明细数据")

    def fetch_summary(self):
        """拉取合计数据"""
        params = self.build_summary_params()
        threading.Thread(target=self._summary_thread, args=(params,), daemon=True).start()

    def _summary_thread(self, params):
        try:
            r = self.controller.session.get(URL_SUMMARY, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[库存冻结合计] 请求异常: {e}")
            return

        if not (data.get("resultCode") == 200 or data.get("success")):
            return

        d = data.get("data") or {}
        total_all = d.get("TOTAL_INVENTORY_ALL") or 0
        frozen_all = d.get("FROZEN_INVENTORY_ALL") or 0
        sales_all = d.get("SALES_ORDER_FROZEN_ALL") or 0
        # 总可用数合计 = 总库存合计 - 冻结库存合计（安卓端同逻辑）
        available_all = total_all - frozen_all
        self.controller.after(0, lambda: self._render_summary(
            total_all, frozen_all, sales_all, available_all))

    def _render_summary(self, total_all, frozen_all, sales_all, available_all):
        self.summary["TOTAL_INVENTORY_ALL"] = total_all
        self.summary["FROZEN_INVENTORY_ALL"] = frozen_all
        self.summary["SALES_ORDER_FROZEN_ALL"] = sales_all
        self.summary["AVAILABLE_ALL"] = available_all
        self.summary_vars["TOTAL_INVENTORY_ALL"].set(self.fmt_num(total_all))
        self.summary_vars["FROZEN_INVENTORY_ALL"].set(self.fmt_num(frozen_all))
        self.summary_vars["SALES_ORDER_FROZEN_ALL"].set(self.fmt_num(sales_all))
        self.summary_vars["AVAILABLE_ALL"].set(self.fmt_num(available_all))

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

    # ------------------------------------------------------------------ 明细
    def on_row_double_click(self, event):
        """双击行打开冻结单据明细"""
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        index = self.tree.index(row_id)
        if index < 0 or index >= len(self.rows):
            return
        self.open_detail(self.rows[index])

    def open_detail(self, row):
        """打开冻结单据明细窗口"""
        win = tk.Toplevel(self)
        win.title("冻结单据明细")
        win.geometry("900x620")
        win.transient(self)
        win.grab_set()

        header = tk.Frame(win, bg="#f7f8fa")
        header.pack(fill=tk.X)
        tk.Label(header, text=row.get("PART_CODE") or "-", bg="#f7f8fa", fg="#1989fa",
                 font=("Consolas", 11)).pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(header, text=row.get("PART_NAME") or "-", bg="#f7f8fa",
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=10, pady=6)

        tip = tk.StringVar(value="加载中...")
        tk.Label(win, textvariable=tip, bg="#ffffff", fg="#969799").pack(fill=tk.X, padx=10, pady=4)

        body = tk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        params = {
            "BRAND_ID": row.get("BRAND_ID"),
            "PART_ID": row.get("PART_ID"),
            "WAREHOUSE_ID": row.get("WAREHOUSE_ID"),
        }
        threading.Thread(target=self._detail_thread,
                         args=(params, body, tip, row), daemon=True).start()

    def _detail_thread(self, params, body, tip, row):
        try:
            r = self.controller.session.get(URL_ORDER_DETAIL, headers=HEADERS, params=params)
            print(f"[冻结单据明细] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[冻结单据明细] 请求异常: {e}")
            self.controller.after(0, lambda: tip.set("明细加载失败"))
            return

        d = data.get("data") or {}
        self.controller.after(0, lambda: self._render_detail(body, tip, row, d))

    def _render_detail(self, body, tip, row, data):
        tip.set("")
        for title, key, count_key in DETAIL_SECTIONS:
            section_list = data.get(key) or []

            group = tk.LabelFrame(body, text=f"{title}（{len(section_list)}）",
                                  font=("微软雅黑", 9, "bold"), bg="#ffffff")
            group.pack(fill=tk.X, pady=3)

            if not section_list:
                tk.Label(group, text="无冻结单据", bg="#ffffff", fg="#c8c9cc",
                         font=("微软雅黑", 9)).pack(anchor="w", padx=10, pady=4)
                continue

            cols = ["单据号", "数量", "客户", "开单人", "开单时间"]
            tree = ttk.Treeview(group, columns=cols, show="headings",
                                height=min(len(section_list), 6))
            widths = [200, 80, 220, 120, 160]
            for col, width in zip(cols, widths):
                tree.heading(col, text=col)
                tree.column(col, width=width, anchor="center")
            for order in section_list:
                order_no = (order.get("ORDER_NO") or order.get("SO_NO") or
                            order.get("OUTBOUND_NO") or order.get("TRANSFER_NO") or
                            order.get("PICKING_NO") or "")
                tree.insert("", "end", values=(
                    order_no,
                    order.get("NUM", ""),
                    order.get("CUSTOMER_NAME") or "",
                    order.get("CREATED_BY_NAME") or "",
                    order.get("CREATED_AT") or "",
                ))
            vsb = ttk.Scrollbar(group, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
            vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

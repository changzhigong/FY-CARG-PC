# -*- coding: utf-8 -*-
"""装箱明细查询

对齐 fycarg-pda 安卓端 src/views/PackingDetail.vue，接口与业务逻辑保持一致：

- 主查询：GET /dmscloud.part/warehouse/packing/queryInfoDetail
- 箱子名称选项：GET /dmscloud.part/boxModelManage/queryBoxModelManageList

与「库存冻结明细查询」的两处关键差异：
1. 仓库参数用 warehouse_id（数字 ID），不是 storage_code 字符串；
   取值来自 warehouse_config.json 的 WAREHOUSE_OPTIONS（与出库/调拨模块一致）。
2. 箱子名称（box_name）查询参数传的是 boxModelManage 的 id，不是名称文本；
   选项列表需从 queryBoxModelManageList 异步拉取，拉取失败时保留「全部」不影响查询。

对应安卓端交互：
- 常显条件：出库仓库 / 拣货人 / 装箱人 / 装箱时间起止（默认当月1号 ~ 今天）
- 更多条件（默认折叠）：箱子名称 / 是否发运 / 货箱号 / 备件编号 / 备件名 /
  订单号 / 出库单号 / 拣货单号 / 单据号 / 客户名称
- 出库仓库为必选，未选择时拒绝查询
- 列表 17 列，序号为全局序号 (pageNum-1)*pageSize+idx+1
- 服务端分页（pageNum + limit，每页 20 条）
"""

import json
import threading
from datetime import date

import tkinter as tk
from tkinter import ttk, messagebox
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
URL_QUERY = 'https://xb.fy-carg.com/dmscloud.part/warehouse/packing/queryInfoDetail'
URL_BOX_MODEL = 'https://xb.fy-carg.com/dmscloud.part/boxModelManage/queryBoxModelManageList'

# 每页条数（与安卓端 pageSize 保持一致）
PAGE_SIZE = 20

# 是否发运字典（对齐安卓端 isWaybillOptions）
IS_WAYBILL_OPTIONS = [
    ("全部", ""),
    ("是", "10041001"),
    ("否", "10041002"),
]

# 列表列定义（对齐安卓端表头，顺序一致）
COLUMNS = ["序号", "货箱号", "箱子名称", "备件编号", "备件名", "装箱数量", "库位",
           "装箱时间", "装箱人", "拣货人", "出库单号", "订单号", "拣货单号",
           "单据号", "客户", "是否发运", "仓库"]
COLUMN_WIDTHS = [55, 120, 90, 140, 220, 80, 90, 150, 80, 80,
                 170, 140, 170, 140, 200, 70, 80]


class PackingDetailPage(BasePage):
    """装箱明细查询页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 当前页行数据（原始 dict 列表）
        self.total = 0            # 查询总条数
        self.page_num = 1         # 当前页码
        self.page_size = PAGE_SIZE
        self.queried = False      # 是否已执行过查询
        self.loading = False      # 请求进行中（防重入）
        self.box_model_map = {}   # 箱子名称 -> boxModelManage.id
        self.show_more = False    # 更多条件是否展开（安卓端默认折叠）
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        """构建用户界面"""
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main_container)
        self.setup_count_bar(main_container)
        self.setup_data_table(main_container)
        self.setup_pagination_controls(main_container)

        # 箱子名称选项（异步拉取，失败时保留「全部」）
        self.load_box_models()

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        # ---- 常显条件 ----
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="出库仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="拣货人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.picking_by_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.picking_by_var, width=12).pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="装箱人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.packing_by_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.packing_by_var, width=12).pack(side=tk.LEFT, padx=5)

        # 装箱时间起止（默认：当月1号 ~ 今天，对齐安卓端 getDefDate）
        tk.Label(row1, text="装箱时间起:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.start_cal = DateEntry(row1, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="装箱时间止:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.end_cal = DateEntry(row1, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT, padx=5)

        # ---- 更多条件（默认折叠）----
        self.more_btn = tk.Button(filter_frame, text="展开更多条件 ▼", bg="#f0f0f0",
                                  fg="#1989fa", relief=tk.FLAT, cursor="hand2",
                                  command=self.toggle_more)
        self.more_btn.pack(fill=tk.X)

        self.more_frame = tk.Frame(filter_frame, bg="#f0f0f0")

        more_row1 = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row1.pack(fill=tk.X, pady=(5, 2))
        tk.Label(more_row1, text="箱子名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.box_name_var = tk.StringVar(value="全部")
        self.box_name_cb = ttk.Combobox(more_row1, textvariable=self.box_name_var,
                                        values=["全部"], state="readonly", width=12)
        self.box_name_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="是否发运:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.is_waybill_var = tk.StringVar(value="全部")
        self.is_waybill_cb = ttk.Combobox(
            more_row1, textvariable=self.is_waybill_var,
            values=[t for t, _ in IS_WAYBILL_OPTIONS], state="readonly", width=8)
        self.is_waybill_cb.set("全部")
        self.is_waybill_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="货箱号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.box_no_var = tk.StringVar()
        ttk.Entry(more_row1, textvariable=self.box_no_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="备件编号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_code_var = tk.StringVar()
        ttk.Entry(more_row1, textvariable=self.part_code_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="备件名:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_name_var = tk.StringVar()
        ttk.Entry(more_row1, textvariable=self.part_name_var, width=14).pack(side=tk.LEFT, padx=5)

        more_row2 = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row2.pack(fill=tk.X, pady=2)
        tk.Label(more_row2, text="订单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.order_number_var = tk.StringVar()
        ttk.Entry(more_row2, textvariable=self.order_number_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row2, text="出库单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.outbound_no_var = tk.StringVar()
        ttk.Entry(more_row2, textvariable=self.outbound_no_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row2, text="拣货单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.picking_order_no_var = tk.StringVar()
        ttk.Entry(more_row2, textvariable=self.picking_order_no_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row2, text="单据号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.bill_no_var = tk.StringVar()
        ttk.Entry(more_row2, textvariable=self.bill_no_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row2, text="客户名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.dealer_name_var = tk.StringVar()
        ttk.Entry(more_row2, textvariable=self.dealer_name_var, width=16).pack(side=tk.LEFT, padx=5)

        # ---- 查询 / 重置 ----
        btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        btn_row.pack(fill=tk.X, pady=(8, 2))
        self.btn_row = btn_row
        tk.Button(btn_row, text="查询", command=self.query, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_count_bar(self, parent):
        """查询条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        """构建明细表格"""
        table_frame = tk.LabelFrame(parent, text="装箱明细", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("备件名", "客户", "出库单号", "订单号",
                                    "拣货单号", "单据号", "货箱号") else "center"
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

        # 长文本列附加悬停提示
        tooltip_manager.attach_tooltip(self.tree)

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
        """起止时间默认值：begin=当月1号，end=今天（对齐安卓端 getDefDate）"""
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
    def fmt_waybill(val):
        """是否发运：10041001=是 / 10041002=否（对齐安卓端 fmtWaybill）"""
        s = str(val) if val is not None else ""
        if s == "10041001":
            return "是"
        if s == "10041002":
            return "否"
        return "-"

    def _check_response(self, response):
        """检查响应中的登录状态"""
        return not self.controller.check_login_status(response)

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
        """重置查询条件（仓库恢复默认第一个，时间恢复当月1号~今天）"""
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.picking_by_var.set("")
        self.packing_by_var.set("")
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.box_name_var.set("全部")
        self.is_waybill_cb.set("全部")
        self.box_no_var.set("")
        self.part_code_var.set("")
        self.part_name_var.set("")
        self.order_number_var.set("")
        self.outbound_no_var.set("")
        self.picking_order_no_var.set("")
        self.bill_no_var.set("")
        self.dealer_name_var.set("")

    def build_params(self):
        """构造查询参数（pageNum + limit，与安卓端 buildParams 一致）"""
        warehouse_name = self.warehouse_var.get()
        warehouse_id = self.controller.options.get(warehouse_name, "")
        # 箱子名称：查询参数传 boxModelManage 的 id，非名称文本
        box_name_value = self.box_model_map.get(self.box_name_var.get(), "")
        is_waybill_value = ""
        for text, value in IS_WAYBILL_OPTIONS:
            if text == self.is_waybill_var.get():
                is_waybill_value = value
                break
        return {
            "picking_order_no": self.picking_order_no_var.get().strip(),
            "outbound_no": self.outbound_no_var.get().strip(),
            "order_number": self.order_number_var.get().strip(),
            "bill_no": self.bill_no_var.get().strip(),
            "warehouse_id": warehouse_id,
            "dealer_code": "",
            "dealer_name": self.dealer_name_var.get().strip(),
            "created_start_at": self.start_cal.get() if self.start_cal.get() else "",
            "created_end_at": self.end_cal.get() if self.end_cal.get() else "",
            "box_no": self.box_no_var.get().strip(),
            "part_code": self.part_code_var.get().strip(),
            "part_name": self.part_name_var.get().strip(),
            "picking_by": self.picking_by_var.get().strip(),
            "packing_by": self.packing_by_var.get().strip(),
            "box_name": box_name_value,
            "isWaybill": is_waybill_value,
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
        # 出库仓库必选（对齐安卓端校验）
        if not params["warehouse_id"]:
            messagebox.showwarning("提示", "请先选择出库仓库")
            return

        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        """查询线程"""
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[装箱明细查询] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[装箱明细查询] 请求异常: {e}")
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
            values = (
                base + idx + 1,                       # 全局序号（对齐安卓端）
                row.get("box_no") or "-",
                row.get("box_name") or "-",
                row.get("part_code") or "-",
                row.get("part_name") or "-",
                self.fmt_num(row.get("packing_quantity")),
                row.get("location_no") or "-",
                row.get("created_at") or "-",
                row.get("packing_by") or "-",
                row.get("picking_by") or "-",
                row.get("outbound_no") or "-",
                row.get("order_number") or "-",
                row.get("picking_order_no") or "-",
                row.get("bill_no") or "-",
                row.get("distributor_name") or "-",
                self.fmt_waybill(row.get("isWaybill")),
                row.get("WAREHOUSE_NAME") or "-",
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        self.count_var.set(f"共 {total} 条装箱明细")
        self.update_page_info()
        if total == 0:
            messagebox.showinfo("查询结果", "无装箱明细数据")

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

    # -------------------------------------------------------------- 箱子型号
    def load_box_models(self):
        """拉取箱子型号列表（异步，失败保留「全部」）"""
        threading.Thread(target=self._box_model_thread, daemon=True).start()

    def _box_model_thread(self):
        try:
            r = self.controller.session.get(URL_BOX_MODEL, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[箱子型号] 拉取失败: {e}")
            return

        raw = data.get("data") or []
        items = raw if isinstance(raw, list) else []
        box_model_map = {}
        for it in items:
            if isinstance(it, dict) and it.get("id") is not None:
                box_model_map[str(it.get("box_name"))] = it.get("id")
        self.controller.after(0, lambda: self._render_box_models(box_model_map))

    def _render_box_models(self, box_model_map):
        """更新箱子名称下拉选项"""
        self.box_model_map = box_model_map
        values = ["全部"] + list(box_model_map.keys())
        self.box_name_cb.config(values=values)
        self.box_name_var.set("全部")

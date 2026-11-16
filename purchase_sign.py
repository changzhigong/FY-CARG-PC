# -*- coding: utf-8 -*-
"""采购入库 — 到货签收

对齐 fycarg-pda 安卓端 src/views/PurchaseSign.vue + src/service/purchaseInbound.js，
接口与业务逻辑保持一致：

接口（baseURL https://xb.fy-carg.com）：
- 列表      GET  /dmscloud.part/part/cargSign
- 明细      GET  /dmscloud.part/part/cargSign/{id}
- 签收信息  GET  /dmscloud.part/part/cargSign/signInfo/{id}（含可编辑接收数量）
- 单条签收  PUT  /dmscloud.part/part/cargSign/sign
- 批量签收  PUT  /dmscloud.part/part/cargSign/batchSign
- 字典      GET  /dmscloud.basedata/dicts

关键业务规则（与安卓端逐条对齐）：
1. 查询参数中签收状态同时传两种形态：
   - signStatus  = 逗号串（如 47121001,47121003）
   - signStatus1[] = 数组（requests 对 list 值会展开为重复键，等价于安卓手写序列化）
   入库类型参数名是 receipt_type（下划线），不是驼峰。
2. 默认签收状态勾选「未签收 + 部分签收」（47121001 / 47121003）。
3. 仅 signStatus ∈ {47121001 未签收, 47121003 部分签收} 的单据可签收；已签收禁用。
4. 签收提交数组键为 **details**（不是 detailList），无顶层 signStatus，
   orderStatus 固定常量 47141001（列表行的 orderStatus 是 90341001，两者不同，勿混用）。
5. 逐行保留 signInfo 全字段，仅覆盖 receivingQty 并重算 totalPrice = 接收数量 × 单价
   （单价取 signCostPrice，缺失回退 costPrice），金额按两位小数字符串提交；
   接收数量大于发运数量时截断到发运数量，负数/非法值归 0。
6. 批量签收 body 为 { ids: [...] }，不做数量编辑，直接按发运数量签收。

字典组：
- 9033 入库类型（receiptType）：90331017 非玻璃采购入库 等
- 4712 签收状态（signStatus）：47121001 未签收 / 47121002 已签收 / 47121003 部分签收
接口拉取失败时使用 FALLBACK_DICTS 硬编兜底（与安卓端 FALLBACK 一致）。

与安卓端的交互差异（仅载体差异，逻辑不变）：
- 安卓端每行内嵌「查看 / 签收」按钮；PC 端改为双击行=查看明细，按钮栏的
  「签收」作用于当前选中行，「批量签收」作用于勾选列打勾的行。
- 安卓端发货日期默认为空（不筛选）；PC 端用「按发货日期筛选」复选框控制，
  未勾选时不传 shipStartDate/shipEndDate，保持与安卓端一致的默认行为。
"""

import json
import threading

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

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
URL_LIST = BASE_URL + '/dmscloud.part/part/cargSign'
URL_DETAIL = BASE_URL + '/dmscloud.part/part/cargSign/{id}'
URL_SIGN_INFO = BASE_URL + '/dmscloud.part/part/cargSign/signInfo/{id}'
URL_SIGN = BASE_URL + '/dmscloud.part/part/cargSign/sign'
URL_BATCH_SIGN = BASE_URL + '/dmscloud.part/part/cargSign/batchSign'
URL_DICTS = BASE_URL + '/dmscloud.basedata/dicts'

# 每页条数（与安卓端 pageSize 一致）
PAGE_SIZE = 20

# 签收后提交的固定状态码（注意：不是列表行的 orderStatus 90341001）
SIGN_ORDER_STATUS = 47141001

# 可签收状态：未签收 / 部分签收
SIGNABLE_STATUS = (47121001, 47121003)

# 签收状态选项（字典组 4712）
SIGN_STATUS_OPTIONS = [
    ('47121001', '未签收'),
    ('47121002', '已签收'),
    ('47121003', '部分签收'),
]
# 默认勾选（对齐安卓端 search.signStatusList 初始值）
DEFAULT_SIGN_STATUS = ('47121001', '47121003')

# 字典硬编兜底（与安卓端 FALLBACK 一致）
FALLBACK_DICTS = {
    '9033': {
        '90331017': '非玻璃采购入库',
        '90331021': '玻璃采购入库',
        '90331022': '其它采购入库',
    },
    '4712': {
        '47121001': '未签收',
        '47121002': '已签收',
        '47121003': '部分签收',
    },
}

# 列表列定义（对齐安卓端表头顺序，供应商拆成「供应商 / 供应商编码」两列）
COLUMNS = ['选择', '序号', '发运单号', '收货仓库', '供应商', '供应商编码', '箱数',
           '发货数量', '金额', '接收数量', '签收状态', '发货时间', '收货时间',
           '入库类型', '备注']
COLUMN_WIDTHS = [45, 50, 160, 90, 150, 100, 60, 80, 100, 80, 80,
                 110, 110, 130, 180]

# 明细列定义（对齐安卓端明细弹层表头）
DETAIL_COLUMNS = ['序号', '品牌', 'CARG全码/编码', '产品名称', '箱号', '发运数量',
                  '接收数量', '采购价', '采购金额', '唛头号', '备注']
DETAIL_WIDTHS = [45, 80, 140, 200, 90, 80, 80, 80, 100, 100, 160]


class PurchaseSignPage(BasePage):
    """采购入库 — 到货签收页面"""

    def __init__(self, parent, controller):
        self.rows = []                # 当前页行数据（原始 dict 列表）
        self.total = 0                # 查询总条数
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.loading = False          # 请求进行中（防重入）
        self.dict_maps = {}           # 字典组 -> {code: 名称}
        self.show_more = False        # 折叠区是否展开（安卓端默认收起）
        self.sign_status_vars = {}    # 签收状态多选框变量 code -> BooleanVar
        self._detail_win = None       # 明细弹窗
        self._sign_win = None         # 签收弹窗
        self._sign_rows = []          # 签收弹窗行数据（含 _recv_var）
        self._sign_header = None      # 签收弹窗对应的主单行
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

        # 入库类型选项（异步拉字典）
        self.load_dicts()

    def setup_filter_panel(self, parent):
        """查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        # ---- 第一行：仓库 / 入库类型 / 签收状态（多选）----
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="收货仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
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

        tk.Label(row1, text="签收状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        for code, text in SIGN_STATUS_OPTIONS:
            var = tk.BooleanVar(value=(code in DEFAULT_SIGN_STATUS))
            self.sign_status_vars[code] = var
            ttk.Checkbutton(row1, text=text, variable=var).pack(side=tk.LEFT, padx=2)

        # ---- 第二行：发货日期起止（默认不启用，对齐安卓端默认为空）----
        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=2)

        self.use_ship_date_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="按发货日期筛选", variable=self.use_ship_date_var,
                        command=self.toggle_ship_date).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="发货日期起:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.start_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd',
                                   state="disabled")
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="发货日期止:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.end_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd',
                                 state="disabled")
        self.end_cal.pack(side=tk.LEFT, padx=5)

        # ---- 折叠区：发运单号 / 产品编码 / 产品名称（默认收起）----
        self.more_btn = tk.Button(filter_frame, text="展开发运单号/编码/名称 ▼",
                                  bg="#f0f0f0", fg="#1989fa", relief=tk.FLAT,
                                  cursor="hand2", command=self.toggle_more)
        self.more_btn.pack(fill=tk.X)

        self.more_frame = tk.Frame(filter_frame, bg="#f0f0f0")
        more_row = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row.pack(fill=tk.X, pady=(5, 2))

        tk.Label(more_row, text="发运单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.ship_no_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.ship_no_var, width=18).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row, text="产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_code_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.part_code_var, width=18).pack(side=tk.LEFT, padx=5)

        tk.Label(more_row, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_name_var = tk.StringVar()
        ttk.Entry(more_row, textvariable=self.part_name_var, width=18).pack(side=tk.LEFT, padx=5)

        # ---- 查询 / 重置 ----
        self.btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        self.btn_row.pack(fill=tk.X, pady=(8, 2))
        tk.Button(self.btn_row, text="查询", command=self.query,
                  bg="#4CAF50", fg="white", padx=10, pady=5, bd=0,
                  activebackground="#45a049").pack(side=tk.LEFT, padx=5)
        tk.Button(self.btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_action_bar(self, parent):
        """操作按钮栏（安卓端为行内按钮，PC 端改为按钮栏）"""
        bar = tk.Frame(parent, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=(0, 3))

        tk.Button(bar, text="查看明细", command=self.open_detail,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="签收", command=self.open_sign,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="批量签收", command=self.batch_sign,
                  bg="#fa8c16", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="全选", command=lambda: self.toggle_all(True),
                  bg="#e1e1e1", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="清空选择", command=lambda: self.toggle_all(False),
                  bg="#e1e1e1", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)

        self.selected_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self.selected_var, bg="#f0f0f0",
                 fg="#fa8c16", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10)
        tk.Label(bar, text="提示：单击选行；双击行查看明细；点「选择」列可打勾批量签收",
                 bg="#f0f0f0", fg="#666666", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="到货签收列表", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("发运单号", "供应商", "备注", "入库类型",
                                    "收货仓库") else "center"
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

        # 双击查看明细；单击第 1 列切换勾选
        self.tree.bind("<Double-1>", lambda e: self.open_detail())
        self.tree.bind("<Button-1>", self.on_tree_click)
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
        """当前所选仓库的数字 ID（warehouse_config.json 的 WAREHOUSE_OPTIONS）"""
        return self.controller.options.get(self.warehouse_var.get(), "")

    @staticmethod
    def fmt_num(val):
        """数字格式化：空值 '-'，整数不显示小数，否则保留两位"""
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    def _label(self, dict_type, code):
        """字典解码：接口字典优先，缺失用硬编兜底，都没有则原样返回"""
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

    def decode_sign_status(self, code):
        return self._label('4712', code)

    def toggle_more(self):
        """展开/收起折叠查询条件"""
        self.show_more = not self.show_more
        if self.show_more:
            self.more_frame.pack(fill=tk.X, before=self.btn_row)
            self.more_btn.config(text="收起查询条件 ▲")
        else:
            self.more_frame.pack_forget()
            self.more_btn.config(text="展开发运单号/编码/名称 ▼")

    def toggle_ship_date(self):
        """发货日期起止启用/禁用"""
        state = "normal" if self.use_ship_date_var.get() else "disabled"
        self.start_cal.config(state=state)
        self.end_cal.config(state=state)

    def reset_form(self):
        """重置查询条件（签收状态恢复默认「未签收+部分签收」）"""
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.receipt_type_var.set("全部")
        for code, _text in SIGN_STATUS_OPTIONS:
            self.sign_status_vars[code].set(code in DEFAULT_SIGN_STATUS)
        self.use_ship_date_var.set(False)
        self.toggle_ship_date()
        self.ship_no_var.set("")
        self.part_code_var.set("")
        self.part_name_var.set("")

    # ================================================================ 勾选
    def on_tree_click(self, event):
        """点击「选择」列切换勾选（对齐安卓端 van-checkbox）"""
        rowid = self.tree.identify_row(event.y)
        if not rowid:
            return
        if self.tree.identify_column(event.x) != '#1':
            return
        values = list(self.tree.item(rowid, 'values'))
        values[0] = '☐' if values[0] == '✓' else '✓'
        self.tree.item(rowid, values=values)
        self.refresh_selected_count()

    def toggle_all(self, checked):
        """全选 / 清空选择"""
        mark = '✓' if checked else '☐'
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[0] = mark
            self.tree.item(item, values=values)
        self.refresh_selected_count()

    def refresh_selected_count(self):
        n = sum(1 for it in self.tree.get_children()
                if self.tree.item(it, 'values')[0] == '✓')
        self.selected_var.set("已选 %d 单" % n if n else "")

    def checked_row_ids(self):
        """勾选行的单据 id 列表"""
        ids = []
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] != '✓':
                continue
            idx = self.tree.index(item)
            if 0 <= idx < len(self.rows):
                rid = self.rows[idx].get('id')
                if rid is not None:
                    ids.append(rid)
        return ids

    def current_row(self):
        """当前选中（高亮）行的原始数据"""
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.rows):
            return self.rows[idx]
        return None

    # ================================================================ 查询
    def build_params(self):
        """构造查询参数（对齐安卓端 loadList 的 params）"""
        selected = [code for code, _t in SIGN_STATUS_OPTIONS
                    if self.sign_status_vars[code].get()]
        params = {
            'pageNum': self.page_num,
            'pageSize': self.page_size,
            'warehouseId': self.current_warehouse_id,
            'searchLoading': 'true',
            # 多选字段同时传逗号串与数组两种形态（安卓端 serializeMultiParams 的行为）
            'signStatus': ','.join(selected),
            'signStatus1[]': list(selected),
        }
        # 入库类型：参数名 receipt_type（下划线）
        receipt_type = self._receipt_type_value()
        if receipt_type:
            params['receipt_type'] = receipt_type
        if self.ship_no_var.get().strip():
            params['shipNo'] = self.ship_no_var.get().strip()
        if self.part_code_var.get().strip():
            params['partCode'] = self.part_code_var.get().strip()
        if self.part_name_var.get().strip():
            params['partName'] = self.part_name_var.get().strip()
        if self.use_ship_date_var.get():
            params['shipStartDate'] = self.start_cal.get()
            params['shipEndDate'] = self.end_cal.get()
        return params

    def _receipt_type_value(self):
        """入库类型下拉文本 -> code（「全部」返回空）"""
        text = self.receipt_type_var.get()
        if not text or text == "全部":
            return ""
        for code, name in (self.dict_maps.get('9033') or FALLBACK_DICTS['9033']).items():
            if name == text:
                return code
        return text

    def query(self, reset_page=True):
        """执行查询"""
        if self.loading:
            return
        if reset_page:
            self.page_num = 1
        if not self.current_warehouse_id:
            messagebox.showwarning("提示", "请先选择收货仓库")
            return

        params = self.build_params()
        self.loading = True
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_LIST, headers=HEADERS, params=params)
            print("[到货签收] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[到货签收] 请求异常: %s" % e)
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
        """渲染列表（主线程）"""
        self.rows = rows
        self.total = total

        for item in self.tree.get_children():
            self.tree.delete(item)

        base = (self.page_num - 1) * self.page_size
        for idx, row in enumerate(rows):
            values = (
                '☐',                                            # 选择
                base + idx + 1,                                 # 全局序号
                row.get("shipNo") or "-",
                row.get("warehouseName") or "-",
                row.get("supplierName") or "-",
                row.get("supplierNo") or "-",
                self.fmt_num(row.get("caseNum")),
                self.fmt_num(row.get("shipQty")),
                self.fmt_num(row.get("totalAmount")),
                self.fmt_num(row.get("receivingQty")),
                self.decode_sign_status(row.get("signStatus")),
                row.get("shipDate") or "-",
                row.get("receivingDate") or "-",
                self.decode_receipt_type(row.get("receiptType")),
                row.get("remark") or "-",
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        self.count_var.set("共 %d 条发运单" % total)
        self.update_page_info()
        self.refresh_selected_count()

    # ================================================================ 分页
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

    # ================================================================ 字典
    def load_dicts(self):
        """异步拉取字典组 9033 / 4712（失败保留硬编兜底）"""
        threading.Thread(target=self._dicts_thread, daemon=True).start()

    def _dicts_thread(self):
        try:
            r = self.controller.session.get(URL_DICTS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[到货签收] 字典加载失败，使用硬编兜底: %s" % e)
            return

        d = data.get("data") or {}
        dict_groups = d.get("dict") or {}
        maps = {}
        for group in ('9033', '4712'):
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
        values = ["全部"] + list(receipt_map.values())
        self.receipt_type_cb.config(values=values)
        self.receipt_type_var.set("全部")

    # ================================================================ 明细
    def open_detail(self):
        """查看明细（双击行或按钮）"""
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        row_id = row.get("id")
        if row_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法查看明细")
            return

        win = tk.Toplevel(self)
        win.title("签收明细 - %s" % (row.get("shipNo") or ""))
        win.geometry("1100x520")
        self._detail_win = win

        tk.Label(win, text="加载中...", font=("微软雅黑", 10)).pack(pady=20)
        threading.Thread(target=self._detail_thread, args=(row_id, win), daemon=True).start()

    def _detail_thread(self, row_id, win):
        try:
            r = self.controller.session.get(URL_DETAIL.format(id=row_id), headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[到货签收] 明细请求异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载明细失败: %s" % e))
            return

        d = data.get("data") or {}
        details = d.get("details") or d.get("data") or d.get("rows") or []
        self.controller.after(0, lambda: self._render_detail(win, details))

    def _render_detail(self, win, details):
        if not win.winfo_exists():
            return
        for w in win.winfo_children():
            w.destroy()

        frame = tk.Frame(win, bg="#f0f0f0")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tree = ttk.Treeview(frame, columns=DETAIL_COLUMNS, show="headings", height=18)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            tree.heading(col, text=col)
            anchor = "w" if col in ("产品名称", "备注", "CARG全码/编码") else "center"
            tree.column(col, width=width, anchor=anchor)

        for i, d in enumerate(details):
            tree.insert("", "end", values=(
                i + 1,
                d.get("brandName") or d.get("brand") or "-",
                d.get("partCode") or "-",
                d.get("partName") or "-",
                d.get("caseNo") or "-",
                self.fmt_num(d.get("shipQty")),
                self.fmt_num(d.get("receivingQty")),
                self.fmt_num(d.get("costPrice")),
                self.fmt_num(d.get("totalPrice")),
                d.get("markCode") or "-",
                d.get("remarks") or d.get("remark") or "-",
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

    # ================================================================ 签收
    @staticmethod
    def can_sign(row):
        """状态防护：仅未签收 / 部分签收 可签收"""
        try:
            return int(row.get("signStatus")) in SIGNABLE_STATUS
        except (TypeError, ValueError):
            return False

    def open_sign(self):
        """打开签收窗（可编辑接收数量）"""
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        if not self.can_sign(row):
            messagebox.showwarning("提示", "仅「未签收 / 部分签收」的单据可以签收")
            return
        row_id = row.get("id")
        if row_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法签收")
            return

        self._sign_header = row
        win = tk.Toplevel(self)
        win.title("到货签收 - %s" % (row.get("shipNo") or ""))
        win.geometry("720x520")
        self._sign_win = win
        tk.Label(win, text="加载中...", font=("微软雅黑", 10)).pack(pady=20)
        threading.Thread(target=self._sign_info_thread, args=(row_id, win), daemon=True).start()

    def _sign_info_thread(self, row_id, win):
        """优先用签收信息接口（含可编辑接收数量），失败回退明细接口"""
        data = None
        try:
            r = self.controller.session.get(URL_SIGN_INFO.format(id=row_id), headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text).get("data") or {}
        except Exception as e:
            print("[到货签收] signInfo 失败，回退明细接口: %s" % e)
            try:
                r = self.controller.session.get(URL_DETAIL.format(id=row_id), headers=HEADERS)
                if not self._check_response(r):
                    return
                data = json.loads(r.text).get("data") or {}
            except Exception as e2:
                print("[到货签收] 明细回退也失败: %s" % e2)
                self.controller.after(0, lambda: messagebox.showerror("错误", "加载签收信息失败"))
                return

        details = data.get("details") or data.get("data") or data.get("rows") or []
        self.controller.after(0, lambda: self._render_sign(win, details))

    def _render_sign(self, win, details):
        if not win.winfo_exists():
            return
        for w in win.winfo_children():
            w.destroy()

        head = tk.Frame(win, bg="#f0f0f0")
        head.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(head, text="逐行填写接收数量（不得大于发运数量）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)

        # 滚动区（行多时可滚动）
        outer = tk.Frame(win, bg="#f0f0f0")
        outer.pack(fill=tk.BOTH, expand=True, padx=10)
        canvas = tk.Canvas(outer, bg="#f0f0f0", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body = tk.Frame(canvas, bg="#f0f0f0")
        canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        body.bind("<Configure>", _on_configure)

        # 表头
        hdr = tk.Frame(body, bg="#f0f0f0")
        hdr.pack(fill=tk.X)
        for text, width in (("产品", 34), ("发运数量", 10), ("已接收", 10), ("接收数量", 12)):
            tk.Label(hdr, text=text, bg="#f0f0f0", font=("微软雅黑", 9, "bold"),
                     width=width, anchor="w").pack(side=tk.LEFT, padx=3)

        self._sign_rows = []
        for d in details:
            line = tk.Frame(body, bg="#f0f0f0")
            line.pack(fill=tk.X, pady=2)

            title = "%s" % (d.get("partName") or d.get("partCode") or "-")
            tk.Label(line, text=title, bg="#f0f0f0", width=34, anchor="w").pack(side=tk.LEFT, padx=3)
            ship_qty = d.get("shipQty")
            tk.Label(line, text=str(ship_qty if ship_qty is not None else "-"),
                     bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT, padx=3)
            received = d.get("receivedQty")
            tk.Label(line, text=str(received if received is not None else 0),
                     bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT, padx=3)

            default = d.get("receivingQty")
            if default is None:
                default = d.get("shipQty")
            if default is None:
                default = 0
            var = tk.StringVar(value=str(default))
            ttk.Entry(line, textvariable=var, width=12).pack(side=tk.LEFT, padx=3)

            self._sign_rows.append({"data": d, "recv_var": var})

        if not self._sign_rows:
            tk.Label(body, text="暂无明细", bg="#f0f0f0", fg="#999999").pack(pady=20)

        actions = tk.Frame(win, bg="#f0f0f0")
        actions.pack(fill=tk.X, padx=10, pady=10)
        self.sign_btn = tk.Button(actions, text="确认签收", command=self.submit_sign,
                                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=14, pady=6)
        self.sign_btn.pack(side=tk.LEFT)
        tk.Button(actions, text="取消", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14, pady=6).pack(side=tk.LEFT, padx=8)

    def build_sign_payload(self):
        """构造签收报文（对齐安卓端 submitSign）

        数组键为 details（非 detailList），无顶层 signStatus，orderStatus 固定 47141001。
        """
        header = self._sign_header or {}
        details = []
        for item in self._sign_rows:
            d = dict(item["data"])
            raw = item["recv_var"].get()
            try:
                recv = float(raw)
            except (TypeError, ValueError):
                recv = 0.0
            if recv < 0:
                recv = 0.0
            ship_qty = d.get("shipQty")
            if ship_qty is not None:
                try:
                    if recv > float(ship_qty):
                        recv = float(ship_qty)
                except (TypeError, ValueError):
                    pass
            # 保留整数形态：接收数量通常是整数
            recv_out = int(recv) if recv == int(recv) else recv

            unit = d.get("signCostPrice")
            if unit is None:
                unit = d.get("costPrice")
            try:
                unit = float(unit or 0)
            except (TypeError, ValueError):
                unit = 0.0

            d["detailsId"] = d.get("detailsId")
            d["receivingQty"] = recv_out
            d["totalPrice"] = "%.2f" % (recv * unit)
            details.append(d)

        return {
            "id": header.get("id"),
            "warehouseId": header.get("warehouseId") or self.current_warehouse_id,
            "warehouseName": header.get("warehouseName"),
            "supplierNo": header.get("supplierNo"),
            "supplierName": header.get("supplierName"),
            "shipNo": header.get("shipNo"),
            "receivingNo": header.get("receivingNo"),
            "orderStatus": SIGN_ORDER_STATUS,
            "receiptType": header.get("receiptType"),
            "details": details,
        }

    def submit_sign(self):
        """提交签收"""
        if not self._sign_header:
            messagebox.showwarning("提示", "缺少单据信息，请重新打开签收")
            return
        if not self._sign_rows:
            messagebox.showwarning("提示", "没有可签收的明细")
            return

        # 报文在主线程构造（Tk 变量只能在主线程读取）
        payload = self.build_sign_payload()
        if hasattr(self, "sign_btn"):
            self.sign_btn.config(state="disabled", text="签收中...")
        threading.Thread(target=self._sign_thread, args=(payload,), daemon=True).start()

    def _sign_thread(self, payload):
        try:
            r = self.controller.session.put(URL_SIGN, headers=HEADERS,
                                            data=json.dumps(payload, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[到货签收] 签收异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "签收失败: %s" % e))
            self.controller.after(0, self._restore_sign_btn)
            return

        if data.get("success") or data.get("resultCode") == 200 or data.get("code") == 200:
            self.controller.after(0, lambda: messagebox.showinfo("成功", "签收成功"))
            self.controller.after(0, self._close_sign_win)
            self.controller.after(0, lambda: self.query(reset_page=False))
        else:
            msg = data.get("errMsg") or data.get("message") or "签收失败"
            self.controller.after(0, lambda: messagebox.showerror("签收失败", str(msg)))
            self.controller.after(0, self._restore_sign_btn)

    def _restore_sign_btn(self):
        if hasattr(self, "sign_btn") and self.sign_btn.winfo_exists():
            self.sign_btn.config(state="normal", text="确认签收")

    def _close_sign_win(self):
        if self._sign_win and self._sign_win.winfo_exists():
            self._sign_win.destroy()
        self._sign_win = None
        self._sign_rows = []
        self._sign_header = None

    # ================================================================ 批量签收
    def batch_sign(self):
        """批量签收（勾选行，body = { ids: [...] }）"""
        ids = self.checked_row_ids()
        if not ids:
            messagebox.showwarning("提示", "请先在「选择」列勾选要签收的单据")
            return
        if not messagebox.askyesno("批量签收", "确认签收选中的 %d 个发运单？" % len(ids)):
            return
        threading.Thread(target=self._batch_sign_thread, args=(ids,), daemon=True).start()

    def _batch_sign_thread(self, ids):
        try:
            r = self.controller.session.put(URL_BATCH_SIGN, headers=HEADERS,
                                            data=json.dumps({"ids": ids}, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[到货签收] 批量签收异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "批量签收失败: %s" % e))
            return

        if data.get("success") or data.get("resultCode") == 200 or data.get("code") == 200:
            self.controller.after(0, lambda: messagebox.showinfo("成功", "批量签收成功"))
            self.controller.after(0, lambda: self.toggle_all(False))
            self.controller.after(0, lambda: self.query(reset_page=False))
        else:
            msg = data.get("errMsg") or data.get("message") or "批量签收失败"
            self.controller.after(0, lambda: messagebox.showerror("批量签收失败", str(msg)))

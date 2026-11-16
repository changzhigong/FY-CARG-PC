# -*- coding: utf-8 -*-
"""调拨明细查询

对齐 fycarg-pda 安卓端 src/views/TransferDetailQuery.vue 与 src/service/transferDetail.js，
接口与业务逻辑保持一致：

- 列表：GET /dmscloud.part/receiptDeliveryReport/queryTransfer
- 合计：GET /dmscloud.part/receiptDeliveryReport/queryTransferCount （sums 数量合计 / amount 金额合计）
- 调出方：GET /dmscloud.part/warehouse/manage/queryListForSelect
- 调入方：GET /dmscloud.part/warehouse/manage/queryListWithPermissions
- 包装方式：GET /dmscloud.part/boxModelManage/queryBoxModelManageList
- 字典：GET /dmscloud.basedata/dicts （4716 调拨状态 / 9092 分类 / 4617 物流方式）

与前面模块的关键差异（已逐项对齐安卓端）：
1. 序号为「页面内序号」idx+1（每页从 1 开始），不是全局序号（区别于模块4/5）。
2. 仓库参数用 warehouse_id 数字：调出方 removeWarehouseId / 调入方 moveWarehouseId，
   取值来自 warehouse_config.json 的 WAREHOUSE_OPTIONS（与装箱明细一致）；下拉显示仓库名、传数字 ID。
3. 收货状态固定三态（全部 '' / 未收 '2' / 已收 '1'），非 dicts。
4. 包装方式走专有接口 queryBoxModelManageList（与装箱一致），参数名 boxId 传列表返回的 id。
5. 字典 4716(调拨状态) / 9092(分类) / 4617(物流方式)；页面初始化异步拉取，下拉先「全部」。
6. 创建日期默认 当月1号~今天（对齐安卓端 monthFirstStr~todayStr）。
7. 校验：创建起止日期必填，否则拒绝查询（对齐安卓端 '请选择创建起止日期'）。
8. 合计仅在全新查询（resetPage=True）时刷新，翻页不刷新（对齐安卓端 fetchCount 仅 resetPage 时调用）。
9. 数字列右对齐、编码列等宽字体；金额列标红在 ttk 单格不可行，仅保留隔行底色（与模块5一致）。
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
URL_QUERY = 'https://xb.fy-carg.com/dmscloud.part/receiptDeliveryReport/queryTransfer'
URL_COUNT = 'https://xb.fy-carg.com/dmscloud.part/receiptDeliveryReport/queryTransferCount'
URL_DICTS = 'https://xb.fy-carg.com/dmscloud.basedata/dicts'
URL_WH_OUT = 'https://xb.fy-carg.com/dmscloud.part/warehouse/manage/queryListForSelect'
URL_WH_IN = 'https://xb.fy-carg.com/dmscloud.part/warehouse/manage/queryListWithPermissions'
URL_BOX_MODEL = 'https://xb.fy-carg.com/dmscloud.part/boxModelManage/queryBoxModelManageList'

# 每页条数（与安卓端 pageSize 保持一致）
PAGE_SIZE = 20

# 收货状态：固定三态（非 dicts）
WAYBILL_STATUS_OPTIONS = [
    ("全部", ""),
    ("未收", "2"),
    ("已收", "1"),
]

# 字典类型（对齐安卓端 loadDicts）
DICT_TYPES = ['4716', '9092', '4617']
DICT_LABELS = {
    '4716': '调拨状态',
    '9092': '分类',
    '4617': '物流方式',
}
# dict type -> 对应 Combobox 的变量名（用于 _dict_code 取值）
DICT_VAR_NAMES = {
    '4716': 'transfer_status_var',
    '9092': 'category_two_var',
    '4617': 'logistics_mode_var',
}

# 列表列定义（对齐安卓端表头，顺序一致，共 25 列）
COLUMNS = ["序号", "调拨单号", "调拨状态", "调出仓库", "调入仓库", "品牌", "分类",
           "CARG全码", "产品名称", "车型", "数量", "单价", "金额", "原库位", "新库位",
           "物流方式", "包装方式", "经办人", "理货员", "装箱员", "上架人员", "接收日期",
           "审核人", "审核时间", "备注"]
COLUMN_WIDTHS = [
    50,   # 序号
    150,  # 调拨单号
    100,  # 调拨状态
    90,   # 调出仓库
    90,   # 调入仓库
    110,  # 品牌
    90,   # 分类
    150,  # CARG全码
    200,  # 产品名称
    120,  # 车型
    90,   # 数量
    100,  # 单价
    110,  # 金额
    110,  # 原库位
    110,  # 新库位
    100,  # 物流方式
    100,  # 包装方式
    90,   # 经办人
    90,   # 理货员
    90,   # 装箱员
    90,   # 上架人员
    110,  # 接收日期
    90,   # 审核人
    140,  # 审核时间
    160,  # 备注
]

# 右对齐（数字）列
RIGHT_COLS = {"数量", "单价", "金额"}
# 等宽字体（编码类）列
MONO_COLS = {"调拨单号", "CARG全码", "原库位", "新库位"}


class TransferDetailQueryPage(BasePage):
    """调拨明细查询页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 当前页行数据（原始 dict 列表）
        self.total = 0            # 查询总条数
        self.page_num = 1         # 当前页码
        self.page_size = PAGE_SIZE
        self.queried = False      # 是否已执行过查询
        self.loading = False      # 请求进行中（防重入）
        self.show_more = False    # 更多条件是否展开（安卓端默认折叠）
        # 字典码表：type -> {code: desc}
        self.dict_maps = {}
        # 字典下拉：type -> {desc(显示文本): code}
        self.dict_option_maps = {}
        # 箱子名称 -> boxModelManage.id
        self.box_model_map = {}
        # 合计（数量合计 sums / 金额合计 amount）
        self.sum_sums = None
        self.sum_amount = None
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

        # 异步拉取字典（4716/9092/4617）与包装方式
        self.load_dicts()
        self.load_box_models()

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        warehouses = ["全部"] + list(self.controller.options.keys())

        # ---- 常显条件 ----
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="调拨单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.transfer_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.transfer_no_var, width=16).pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="调出方:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.remove_wh_var = tk.StringVar(value="全部")
        self.remove_wh_cb = ttk.Combobox(row1, textvariable=self.remove_wh_var,
                                        values=warehouses, state="readonly", width=10)
        self.remove_wh_cb.set("全部")
        self.remove_wh_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="调入方:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.move_wh_var = tk.StringVar(value="全部")
        self.move_wh_cb = ttk.Combobox(row1, textvariable=self.move_wh_var,
                                      values=warehouses, state="readonly", width=10)
        self.move_wh_cb.set("全部")
        self.move_wh_cb.pack(side=tk.LEFT, padx=5)

        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=5)
        tk.Label(row2, text="CARG全码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.part_code_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.part_code_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.part_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.part_name_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="创建开始日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.start_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="创建结束日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.end_cal = DateEntry(row2, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT, padx=5)

        # ---- 展开/收起更多条件 ----
        self.more_btn = tk.Button(filter_frame, text="展开更多条件 ▼", bg="#f0f0f0",
                                  fg="#1989fa", relief=tk.FLAT, cursor="hand2",
                                  command=self.toggle_more)
        self.more_btn.pack(fill=tk.X)

        self.more_frame = tk.Frame(filter_frame, bg="#f0f0f0")

        # 更多条件：收货状态 / 调拨状态 / 分类 / 车型
        more_row1 = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row1.pack(fill=tk.X, pady=(5, 2))
        tk.Label(more_row1, text="收货状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.waybill_status_var = tk.StringVar(value="全部")
        self.waybill_status_cb = ttk.Combobox(
            more_row1, textvariable=self.waybill_status_var,
            values=[t for t, _ in WAYBILL_STATUS_OPTIONS], state="readonly", width=10)
        self.waybill_status_cb.set("全部")
        self.waybill_status_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="调拨状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.transfer_status_var = tk.StringVar(value="全部")
        self.transfer_status_cb = ttk.Combobox(more_row1, textvariable=self.transfer_status_var,
                                              values=["全部"], state="readonly", width=10)
        self.transfer_status_cb.set("全部")
        self.transfer_status_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="分类:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.category_two_var = tk.StringVar(value="全部")
        self.category_two_cb = ttk.Combobox(more_row1, textvariable=self.category_two_var,
                                           values=["全部"], state="readonly", width=10)
        self.category_two_cb.set("全部")
        self.category_two_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row1, text="车型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.adaptation_model_var = tk.StringVar()
        ttk.Entry(more_row1, textvariable=self.adaptation_model_var, width=12).pack(side=tk.LEFT, padx=5)

        # 更多条件：物流方式 / 包装方式
        more_row2 = tk.Frame(self.more_frame, bg="#f0f0f0")
        more_row2.pack(fill=tk.X, pady=2)
        tk.Label(more_row2, text="物流方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.logistics_mode_var = tk.StringVar(value="全部")
        self.logistics_mode_cb = ttk.Combobox(more_row2, textvariable=self.logistics_mode_var,
                                             values=["全部"], state="readonly", width=10)
        self.logistics_mode_cb.set("全部")
        self.logistics_mode_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(more_row2, text="包装方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.box_name_var = tk.StringVar(value="全部")
        self.box_name_cb = ttk.Combobox(more_row2, textvariable=self.box_name_var,
                                        values=["全部"], state="readonly", width=12)
        self.box_name_cb.set("全部")
        self.box_name_cb.pack(side=tk.LEFT, padx=5)

        # ---- 查询 / 重置 ----
        btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        btn_row.pack(fill=tk.X, pady=(8, 2))
        self.btn_row = btn_row
        tk.Button(btn_row, text="查询", command=lambda: self.query(True), **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def setup_count_bar(self, parent):
        """查询条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        """构建明细表格（25 列）"""
        table_frame = tk.LabelFrame(parent, text="调拨明细", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            if col in RIGHT_COLS:
                anchor = "e"
            elif col == "序号":
                anchor = "center"
            else:
                anchor = "w"
            self.tree.column(col, width=width, anchor=anchor)
        # 隔行底色
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

        tooltip_manager.attach_tooltip(self.tree)

    def setup_summary_bar(self, parent):
        """合计条：数量合计 / 金额合计（来自 queryTransferCount）"""
        self.summary_frame = tk.Frame(parent, bg="#f0f0f0")
        self.summary_frame.pack(fill=tk.X, pady=(4, 0))
        self.sum_sums_var = tk.StringVar(value="")
        self.sum_amount_var = tk.StringVar(value="")
        tk.Label(self.summary_frame, textvariable=self.sum_sums_var, bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), fg="#323233").pack(side=tk.LEFT, padx=20)
        tk.Label(self.summary_frame, textvariable=self.sum_amount_var, bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), fg="#ee0a24").pack(side=tk.LEFT, padx=20)

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
        """起止日期默认值：begin=当月1号，end=今天（对齐安卓端 monthFirstStr/todayStr）"""
        today = date.today()
        if kind == 'begin':
            return date(today.year, today.month, 1)
        return today

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

    def _wh_id(self, name):
        """仓库名下拉 -> warehouse_id 数字（「全部」/空 -> ''）"""
        if not name or name == "全部":
            return ""
        return str(self.controller.options.get(name, ""))

    def _waybill_value(self):
        """收货状态固定三态反查 value"""
        text = self.waybill_status_var.get()
        for t, v in WAYBILL_STATUS_OPTIONS:
            if t == text:
                return v
        return ""

    def toggle_more(self):
        """展开/收起更多条件（默认折叠，对齐安卓端 showMore）"""
        self.show_more = not self.show_more
        if self.show_more:
            self.more_frame.pack(fill=tk.X, before=self.btn_row)
            self.more_btn.config(text="收起更多条件 ▲")
        else:
            self.more_frame.pack_forget()
            self.more_btn.config(text="展开更多条件 ▼")

    def reset_form(self):
        """重置查询条件（仓库/状态下拉恢复全部，日期恢复当月1号~今天）"""
        self.transfer_no_var.set("")
        self.remove_wh_var.set("全部")
        self.move_wh_var.set("全部")
        self.part_code_var.set("")
        self.part_name_var.set("")
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.waybill_status_var.set("全部")
        self.transfer_status_var.set("全部")
        self.category_two_var.set("全部")
        self.adaptation_model_var.set("")
        self.logistics_mode_var.set("全部")
        self.box_name_var.set("全部")

    def build_params(self):
        """构造查询参数（pageNum + limit，与安卓端 buildParams 逐字一致）"""
        # 包装方式：查询参数传 boxModelManage 的 id，非名称文本
        box_id = self.box_model_map.get(self.box_name_var.get(), "")
        return {
            "transfer_status": self._dict_code("4716"),
            "startDate": self.start_cal.get() if self.start_cal.get() else "",
            "endDate": self.end_cal.get() if self.end_cal.get() else "",
            "waybillStatus": self._waybill_value(),
            "removeWarehouseId": self._wh_id(self.remove_wh_var.get()),
            "moveWarehouseId": self._wh_id(self.move_wh_var.get()),
            "categoryTwo": self._dict_code("9092"),
            "adaptationModel": self.adaptation_model_var.get().strip(),
            "transferNo": self.transfer_no_var.get().strip(),
            "partCode": self.part_code_var.get().strip(),
            "partName": self.part_name_var.get().strip(),
            "logisticsMode": self._dict_code("4617"),
            "boxId": box_id,
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

        # 校验：创建起止日期必填
        if not (self.start_cal.get() and self.end_cal.get()):
            messagebox.showwarning("提示", "请选择创建起止日期")
            return

        params = self.build_params()
        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        # 全新查询时先清空合计，等待合计接口回填
        if reset_page:
            self.sum_sums = None
            self.sum_amount = None
            self._update_summary_labels()
        threading.Thread(target=self._query_thread, args=(params, reset_page), daemon=True).start()

    def _query_thread(self, params, reset_page):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[调拨明细] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[调拨明细] 请求异常: {e}")
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

        # 合计仅在全新查询时刷新（对齐安卓端 fetchCount 仅 resetPage 调用）
        if reset_page:
            self.controller.after(0, self.fetch_count, params)

    def _render_rows(self, rows, total):
        """渲染列表（主线程）—— 序号为页面内 idx+1（对齐安卓端）"""
        self.rows = rows
        self.total = total
        self.queried = True

        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, row in enumerate(rows):
            values = self._build_values(row, idx)
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        self.count_var.set(f"共 {total} 条调拨明细")
        self.update_page_info()
        if total == 0:
            messagebox.showinfo("查询结果", "无调拨明细数据")

    def _build_values(self, row, idx):
        """构造行值元组（字段顺序与安卓端表体一致，25 列）"""
        return (
            idx + 1,                                       # 序号（页面内）
            row.get("transfer_no") or "-",
            self.map_dict("4716", row.get("transfer_status")),
            row.get("remove_warehouse_name") or "-",
            row.get("move_warehouse_name") or "-",
            row.get("brand_name") or "-",
            self.map_dict("9092", row.get("category_two")),
            row.get("part_code") or "-",
            row.get("part_name") or "-",
            row.get("adaptation_model") or "-",
            self.fmt_num(row.get("outbound_quantity")),
            self.fmt_money(row.get("moving_average_price")),
            self.fmt_money(row.get("total_amount")),
            row.get("remove_location_no") or "-",
            row.get("move_location_no") or "-",
            self.map_dict("4617", row.get("logistics_mode")),
            row.get("box_name") or "-",
            row.get("created_by_name") or "-",
            row.get("picking_by") or "-",
            row.get("packing_by") or "-",
            row.get("onshelf_by") or "-",
            row.get("receiving_date") or "-",
            row.get("auditBy") or "-",
            row.get("auditDate") or "-",
            row.get("remarks") or "-",
        )

    # ------------------------------------------------------------------ 合计
    def fetch_count(self, list_params):
        """合计查询（数量合计 sums / 金额合计 amount），参数与列表一致"""
        threading.Thread(target=self._count_thread, args=(list_params,), daemon=True).start()

    def _count_thread(self, list_params):
        try:
            r = self.controller.session.get(URL_COUNT, headers=HEADERS, params=list_params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[调拨明细-合计] 查询失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        d = data.get("data") or {}
        sums = d.get("sums")
        amount = d.get("amount")
        self.controller.after(0, lambda: self._apply_summary(sums, amount))

    def _apply_summary(self, sums, amount):
        self.sum_sums = sums
        self.sum_amount = amount
        self._update_summary_labels()

    def _update_summary_labels(self):
        if self.sum_sums is None and self.sum_amount is None:
            self.sum_sums_var.set("")
            self.sum_amount_var.set("")
        else:
            self.sum_sums_var.set(f"数量合计：{self.fmt_num(self.sum_sums)}")
            self.sum_amount_var.set(f"金额合计：{self.fmt_money(self.sum_amount)}")

    # ------------------------------------------------------------------ 分页
    def update_page_info(self):
        self.page_info_var.set(f"第 {self.page_num}/{self.total_pages} 页 (共 {self.total} 条)")

    def go_to_page(self, page):
        """翻页（服务端分页，重新请求；不刷新合计，对齐安卓端）"""
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
            print(f"[调拨明细-字典] 拉取失败: {e}")
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
            "4716": (self.transfer_status_var, self.transfer_status_cb),
            "9092": (self.category_two_var, self.category_two_cb),
            "4617": (self.logistics_mode_var, self.logistics_mode_cb),
        }
        for t, (var, cb) in mapping.items():
            texts = ["全部"] + list(self.dict_option_maps.get(t, {}).keys())
            cb.config(values=texts)
            if var.get() not in texts:
                var.set("全部")

    def load_box_models(self):
        """拉取包装方式列表（异步，失败保留「全部」）"""
        threading.Thread(target=self._box_model_thread, daemon=True).start()

    def _box_model_thread(self):
        try:
            r = self.controller.session.get(URL_BOX_MODEL, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[调拨明细-包装方式] 拉取失败: {e}")
            return
        raw = data.get("data") or []
        items = raw if isinstance(raw, list) else []
        box_model_map = {}
        for it in items:
            if isinstance(it, dict) and it.get("id") is not None:
                box_model_map[str(it.get("box_name"))] = str(it.get("id"))
        self.controller.after(0, lambda: self._render_box_models(box_model_map))

    def _render_box_models(self, box_model_map):
        """更新包装方式下拉选项（与装箱明细一致）"""
        self.box_model_map = box_model_map
        values = ["全部"] + list(box_model_map.keys())
        self.box_name_cb.config(values=values)
        self.box_name_var.set("全部")

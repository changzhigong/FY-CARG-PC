# -*- coding: utf-8 -*-
"""
其它出入库管理 hub · 菜单1「其他入库审核」OtherInboundReviewPage
-----------------------------------------------------------------
对齐 Android 端 OtherInboundReview.vue / PC web（参考《其它入库审核》audit/addEditDetail）。

状态流转（1249 组，PC 实测）：
  待提交 12491001 --提交--> 待审核 12491002 --审核通过(approved)--> 待入库 12491004
                                   --审核驳回(rejectOtherInbound)--> 审核驳回 12491003
  待入库 12491004 --入库--> 已入库 12491005；已作废 12491006。
  审核按钮仅在 STATUS=12491002（待审核）可用。
业务类型（1250 组，PC excludeCode 12501002/03/05/06/07 后剩两项）：
  12501001 免费赠品入库 / 12501004 客户投诉退货入库（本页默认筛选 12501004）。
明细分类 9092 组、退货原因/异常类型 4811 组。

接口（服务层对齐）：
  列表 GET /dmscloud.part/otherInboundWarehouse/page
  主单 GET .../queryById?id=；明细 GET .../queryById/items?id=
  审核通过 POST .../approved；审核驳回 POST .../rejectOtherInbound（AUDIT_OPINION 必填）
  操作日志 GET /dmscloud.part/operateLogs/page?BILL_ID=&BILL_TYPE=12041004&limit=5&isShowLogs=true
  打印数据 GET .../getPrintList（查询条件 + OTHER_IN_NOS='单号1','单号2'，平铺明细按 OTHER_IN_NO 分组）
  客户搜索 GET /dmscloud.basedata/DealerData/queryDealer
  库位远程搜索 GET /dmscloud.part/warehouse/transferIn/findAllLocation?warehouseId=&locationNo=
  字典 GET /dmscloud.basedata/dicts（1249/1250/9092/4811，失败静默用离线兜底）

审核报文（对齐 PC addEditDetail.saveAction，HAR #145 实测）：
  payload = queryById 完整主单展开 + fileList(主单没有则补 []) + itemList + delItemList=[] + AUDIT_OPINION
  通过 AUDIT_OPINION=null、驳回=意见文本；无 audit_remark 字段。
  明细行 NUM 强制数字、PICKING_LOCATION 兜底 INDICATE_LOCATION、select_LOCATION_OPTIONS 记录所选库位。
金额口径：退货入库(12501004) 行金额 = DISTINCTION_MONEY（缺则 SALE_PRICE_INFO），其余 = NUM*COST_PRICE；
打印行金额 = NUM × COST_PRICE_NEW（缺 COST_PRICE_INFO/COST_PRICE）。
"""
import json
import threading
from datetime import date, timedelta

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}
BASE = 'https://xb.fy-carg.com'
PART = '/dmscloud.part/otherInboundWarehouse'

URL_PAGE = BASE + PART + '/page'
URL_DETAIL = BASE + PART + '/queryById'
URL_ITEMS = BASE + PART + '/queryById/items'
URL_APPROVE = BASE + PART + '/approved'
URL_REJECT = BASE + PART + '/rejectOtherInbound'
URL_PRINT = BASE + PART + '/getPrintList'
URL_LOGS = BASE + '/dmscloud.part/operateLogs/page'
URL_DICT = BASE + '/dmscloud.basedata/dicts'
URL_DEALER = BASE + '/dmscloud.basedata/DealerData/queryDealer'
URL_LOC = BASE + '/dmscloud.part/warehouse/transferIn/findAllLocation'

QUERY_LIMIT = 500
LOG_BILL_TYPE = 12041004
LOG_PAGE_SIZE = 5

# 状态字典 1249 组（离线兜底；运行期被 dicts 覆盖）
STATUS_FALLBACK = {
    '12491001': '待提交', '12491002': '待审核', '12491003': '审核驳回',
    '12491004': '待入库', '12491005': '已入库', '12491006': '已作废',
}
# 业务类型 1250 组
BUS_TYPE_FALLBACK = {'12501001': '免费赠品入库', '12501004': '客户投诉退货入库'}
# 明细分类 9092 组
CATEGORY_FALLBACK = {
    '90921001': '前挡', '90921002': '后挡', '90921003': '边窗', '90921004': '其它',
    '90921005': '天窗', '90921006': '其他',
}
# 退货原因 / 异常类型 4811 组
UNUSUAL_FALLBACK = {
    '48111001': '产品本身质量问题', '48111002': '发货数量/规格不符', '48111003': '发货破损',
    '48111004': '客户报错', '48111005': '运输破损', '48111006': '其他原因',
}
# 字典组
DICT_TYPES = ['1249', '1250', '9092', '4811']

PENDING_STATUS = '12491002'   # 待审核
DEFAULT_BUS_TYPE = '12501004' # 客户投诉退货入库
STATUS_FILTERS = [
    ('全部', ''), ('待审核', '12491002'), ('审核驳回', '12491003'),
    ('待入库', '12491004'), ('已入库', '12491005'), ('已作废', '12491006'),
]
BUS_FILTERS = [('免费赠品', '12501001'), ('客户投诉退货', '12501004')]

COLUMNS = ["序号", "业务单号", "状态", "业务类型", "客户", "发起人", "提报日期", "车牌号"]
COLUMN_WIDTHS = [50, 180, 95, 150, 220, 110, 150, 110]

DETAIL_COLUMNS = ["序号", "产品名称", "产品编码", "分类", "退货原因", "品牌", "销售单价", "数量", "金额", "入库库位"]
DETAIL_WIDTHS = [40, 200, 110, 90, 150, 100, 90, 70, 110, 150]


class OtherInboundReviewPage(BasePage):
    """其它出入库-其他入库审核页面（查询/审核通过/驳回/库位/打印预览）"""

    def __init__(self, parent, controller):
        self.rows = []              # 当前列表（全量，前端按 STATUS 兜底过滤后）
        self.queried = False
        self.loading = False
        self.auditing = False
        self.audit_win = None
        self.audit_form = None      # queryById 完整主单（审核报文权威对象）
        self.audit_items = []       # 明细行（可被库位选择/切换修改）
        self.audit_logs = []
        self.dict_maps = {}         # '1249' -> {code:desc}
        self._item_map = {}         # tree iid -> 明细行 dict（审核窗内）
        self.check_remark = None    # 审核意见控件
        super().__init__(parent, controller)

    # ============================================================ 界面
    def create_widgets(self):
        main = tk.Frame(self.content_frame, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main)
        self.setup_stat_bar(main)
        self.setup_data_table(main)
        self.setup_action_bar(main)

        # 实时字典（失败静默用兜底）——对齐安卓 loadDicts
        threading.Thread(target=self._dict_thread, daemon=True).start()

        # 对齐安卓 onMounted：进入页面自动查询（默认业务类型/状态 + 近10天）
        if self.controller.options:
            self.query()

    def setup_filter_panel(self, parent):
        frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                              font=("微软雅黑", 10, "bold"))
        frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.bind("<<ComboboxSelected>>", lambda e: self.query())
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="业务单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_other_in_no = tk.StringVar()
        ttk.Entry(row1, textvariable=self.var_other_in_no, width=18).pack(side=tk.LEFT)
        tk.Label(row1, text="客户代码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_customer_code = tk.StringVar()
        self.customer_entry = ttk.Entry(row1, textvariable=self.var_customer_code,
                                        state="readonly", width=14)
        self.customer_entry.pack(side=tk.LEFT)
        tk.Button(row1, text="选择", command=self.open_dealer_dialog,
                  bg="#fa8c16", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(row1, text="清除", command=self._clear_customer,
                  bg="#e1e1e1", relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=2)
        self.customer_name_label = tk.Label(row1, text="", bg="#f0f0f0",
                                            fg="#fa8c16", font=("微软雅黑", 9))
        self.customer_name_label.pack(side=tk.LEFT, padx=4)

        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.var_part_code = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_part_code, width=14).pack(side=tk.LEFT)
        tk.Label(row2, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_part_name = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_part_name, width=14).pack(side=tk.LEFT)
        tk.Label(row2, text="车牌号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_plate = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_plate, width=12).pack(side=tk.LEFT)
        tk.Label(row2, text="创建日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.start_cal = DateEntry(row2, width=11, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT)
        tk.Label(row2, text="至", bg="#f0f0f0").pack(side=tk.LEFT, padx=2)
        self.end_cal = DateEntry(row2, width=11, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT)

        row3 = tk.Frame(frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="业务类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.bus_var = tk.StringVar(value=DEFAULT_BUS_TYPE)
        self.bus_buttons = {}
        for label, value in BUS_FILTERS:
            b = tk.Button(row3, text=label, width=12, relief=tk.FLAT,
                          bg="#e1e1e1", fg="#323233",
                          command=lambda v=value: self.change_bus_type(v))
            b.pack(side=tk.LEFT, padx=2)
            self.bus_buttons[value] = b
        self._update_bus_buttons()

        tk.Label(row3, text="状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(16, 5))
        self.status_var = tk.StringVar(value=PENDING_STATUS)
        self.status_buttons = {}
        for label, value in STATUS_FILTERS:
            b = tk.Button(row3, text=label, width=8, relief=tk.FLAT,
                          bg="#e1e1e1", fg="#323233",
                          command=lambda v=value: self.change_status(v))
            b.pack(side=tk.LEFT, padx=2)
            self.status_buttons[value] = b
        self._update_status_buttons()

        row4 = tk.Frame(frame, bg="#f0f0f0")
        row4.pack(fill=tk.X, pady=3)
        tk.Button(row4, text="查 询", command=self.query,
                  bg="#fa8c16", fg="white", padx=16, pady=4, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(row4, text="重 置", command=self.reset_form,
                  bg="#969799", fg="white", padx=16, pady=4, bd=0).pack(side=tk.LEFT, padx=2)

    def setup_stat_bar(self, parent):
        row = tk.Frame(parent, bg="#f0f0f0")
        row.pack(fill=tk.X, pady=(0, 3))
        self.stat_var = tk.StringVar(value="共 0 单")
        tk.Label(row, textvariable=self.stat_var, bg="#f0f0f0",
                 font=("微软雅黑", 11, "bold"), fg="#fa8c16").pack(side=tk.LEFT, padx=10)
        self.sel_var = tk.StringVar(value="已选 0 单")
        tk.Label(row, textvariable=self.sel_var, bg="#f0f0f0",
                 font=("微软雅黑", 10), fg="#646566").pack(side=tk.LEFT, padx=20)
        tk.Button(row, text="刷新", command=self.query,
                  bg="#fa8c16", fg="white", padx=12, pady=2, bd=0).pack(side=tk.RIGHT, padx=5)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="其它入库单列表", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings",
                                 height=15, selectmode="extended")
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w"
            if col in ("序号", "数量"):
                anchor = "center"
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

        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_sel_label())
        self.tree.bind("<Double-1>", lambda e: self.open_audit())
        tooltip_manager.attach_tooltip(self.tree)

    def setup_action_bar(self, parent):
        bar = tk.Frame(parent, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=(4, 2))
        tk.Button(bar, text="打印预览（先勾选/多选单据）", command=self.open_print_selected,
                  bg="#fa8c16", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="取消选择", command=self.clear_selection,
                  bg="#e1e1e1", relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=5)
        tk.Label(bar, text="提示：单击选行（Ctrl/Shift 多选）；双击行打开审核", bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    # ============================================================ 工具
    @staticmethod
    def def_date(kind):
        today = date.today()
        if kind == 'begin':
            return today - timedelta(days=10)
        return today

    @staticmethod
    def fmt_date(d):
        return d.strftime('%Y-%m-%d')

    @staticmethod
    def format_date(s):
        if not s:
            return '-'
        s = str(s).strip().replace('T', ' ')
        return s[:16] if len(s) >= 16 else s

    @staticmethod
    def format_num(val):
        try:
            n = float(val)
            if n != n:  # NaN
                return '-'
            return '{:,.2f}'.format(n)
        except (TypeError, ValueError):
            return '-'

    @staticmethod
    def format_money(val):
        try:
            n = float(val or 0)
        except (TypeError, ValueError):
            n = 0.0
        return '¥{:,.2f}'.format(n)

    def _decode(self, group, code, fallback):
        if code is None or code == '':
            return ''
        s = str(code)
        live = (self.dict_maps.get(group) or {}).get(s)
        if live:
            return live
        return fallback.get(s, s)

    def status_label(self, code):
        return self._decode('1249', code, STATUS_FALLBACK) or '-'

    def bus_type_label(self, code):
        return self._decode('1250', code, BUS_TYPE_FALLBACK) or '-'

    def category_label(self, code):
        return self._decode('9092', code, CATEGORY_FALLBACK) or '-'

    def unusual_label(self, code):
        return self._decode('4811', code, UNUSUAL_FALLBACK) or '-'

    def is_pending_audit(self, code):
        return str(code) == PENDING_STATUS

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    # -------------------------------------------------- 字典加载
    def _dict_thread(self):
        try:
            r = self.controller.session.get(URL_DICT, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他入库审核] 字典加载失败(用兜底): {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        dd = data.get("data") or {}
        dictobj = dd.get("dict") or {}
        maps = {}
        for tp in DICT_TYPES:
            m = {}
            arr = dictobj.get(tp) or []
            if isinstance(arr, list):
                for x in arr:
                    if isinstance(x, dict) and x.get('code_id') is not None:
                        m[str(x['code_id'])] = x.get('code_cn_desc') or ''
            maps[tp] = m
        self.controller.after(0, lambda: setattr(self, 'dict_maps', maps))

    # -------------------------------------------------- 筛选
    def _update_bus_buttons(self):
        cur = self.bus_var.get()
        for value, btn in self.bus_buttons.items():
            if value == cur:
                btn.config(bg="#fa8c16", fg="white")
            else:
                btn.config(bg="#e1e1e1", fg="#323233")

    def _update_status_buttons(self):
        cur = self.status_var.get()
        for value, btn in self.status_buttons.items():
            if value == cur:
                btn.config(bg="#fa8c16", fg="white")
            else:
                btn.config(bg="#e1e1e1", fg="#323233")

    def change_status(self, value):
        self.status_var.set(value)
        self._update_status_buttons()
        self.query()

    def change_bus_type(self, value):
        self.bus_var.set(value)
        self._update_bus_buttons()
        self.query()

    def _clear_customer(self):
        self.var_customer_code.set('')
        self.customer_name_label.config(text='')

    def reset_form(self):
        self.var_other_in_no.set('')
        self._clear_customer()
        self.var_part_code.set('')
        self.var_part_name.set('')
        self.var_plate.set('')
        self.bus_var.set(DEFAULT_BUS_TYPE)
        self.status_var.set(PENDING_STATUS)
        self._update_bus_buttons()
        self._update_status_buttons()
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.query()

    def _selected_rows(self):
        sel = self.tree.selection()
        if not sel:
            return []
        out = []
        for iid in sel:
            idx = self.tree.index(iid)
            if 0 <= idx < len(self.rows):
                out.append(self.rows[idx])
        return out

    def _update_sel_label(self):
        n = len(self.tree.selection())
        self.sel_var.set(f"已选 {n} 单")

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())
        self._update_sel_label()

    # ============================================================ 客户选择
    def open_dealer_dialog(self):
        win = tk.Toplevel(self)
        win.title("选择客户")
        win.geometry("560x520")
        win.transient(self)

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="选择客户", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        box = tk.LabelFrame(win, text="客户搜索", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        box.pack(fill=tk.X, padx=10, pady=5, ipady=4)
        r1 = tk.Frame(box, bg="#f0f0f0")
        r1.pack(fill=tk.X, pady=2)
        tk.Label(r1, text="客户代码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        var_code = tk.StringVar()
        ttk.Entry(r1, textvariable=var_code, width=16).pack(side=tk.LEFT)
        tk.Label(r1, text="客户名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        var_name = tk.StringVar()
        ttk.Entry(r1, textvariable=var_name, width=24).pack(side=tk.LEFT)
        tk.Button(r1, text="查 询", command=lambda: self._search_dealer_thread(win, var_code.get(), var_name.get(), listbox, state),
                  bg="#fa8c16", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=8)
        state = {"rows": [], "sel": None}

        def _on_pick(ev=None):
            i = listbox.curselection()
            if i and 0 <= int(i[0]) < len(state["rows"]):
                state["sel"] = state["rows"][int(i[0])]

        listbox = tk.Listbox(win, font=("微软雅黑", 10), activestyle="dotbox")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        listbox.bind("<<ListboxSelect>>", _on_pick)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="确 定", command=lambda: self._confirm_dealer(win, state),
                  bg="#fa8c16", fg="white", padx=16, pady=4, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关 闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=16, pady=4).pack(side=tk.RIGHT, padx=10)
        # 初始自动搜索（对齐安卓 openDealerDialog → searchDealer）
        self._search_dealer_thread(win, '', '', listbox, state)

    def _search_dealer_thread(self, win, code, name, listbox, state):
        def work():
            rows = []
            try:
                r = self.controller.session.get(URL_DEALER, headers=HEADERS, params={
                    'dealerCode': code or '', 'dealerName': name or '',
                    'pageNum': 1, 'pageSize': 500})
                if self._check_response(r):
                    data = json.loads(r.text)
                    if data.get("resultCode") == 200 or data.get("success"):
                        d = data.get("data") or {}
                        arr = d if isinstance(d, list) else (d.get("rows") or [])
                        rows = arr if isinstance(arr, list) else []
            except Exception as e:
                print(f"[其他入库审核-客户] 异常: {e}")
            self.controller.after(0, lambda: self._render_dealer(win, rows, listbox, state))
        threading.Thread(target=work, daemon=True).start()

    def _render_dealer(self, win, rows, listbox, state):
        state["rows"] = rows
        state["sel"] = None
        listbox.delete(0, tk.END)
        if not rows:
            listbox.insert(tk.END, "未找到客户")
            return
        for d in rows:
            code = d.get('dealerCode') or ''
            short = d.get('dealerShortname') or ''
            nm = d.get('dealerName') or ''
            listbox.insert(tk.END, f"{code}（{short or nm}）  {nm}")

    def _confirm_dealer(self, win, state):
        d = state.get("sel")
        if not d:
            messagebox.showinfo("提示", "请先选择客户", parent=win)
            return
        self.var_customer_code.set(d.get('dealerCode') or '')
        self.customer_name_label.config(text=d.get('dealerName') or '')
        win.destroy()

    # ============================================================ 查询
    def build_query_params(self):
        wh = self.warehouse_var.get()
        return {
            "WAREHOUSE_CODE": get_storage_code(wh),
            "BRAND_ID": '',
            "OTHER_IN_NO": self.var_other_in_no.get() or '',
            "BUS_TYPE": self.bus_var.get() or '',
            "CREATED_AT_FROM": self.fmt_date(self.start_cal.get_date()) if self.start_cal.get() else '',
            "CREATED_AT_TO": self.fmt_date(self.end_cal.get_date()) if self.end_cal.get() else '',
            "STATUS": self.status_var.get() or '',
            "partCode": self.var_part_code.get() or '',
            "partName": self.var_part_name.get() or '',
            "plateNumber": self.var_plate.get() or '',
            "customerCode": self.var_customer_code.get() or '',
            "pageNum": 1,
            "limit": QUERY_LIMIT,
        }

    def query(self):
        if self.loading:
            return
        if not self.warehouse_var.get():
            messagebox.showwarning("提示", "请先选择仓库")
            return
        params = self.build_query_params()
        self.loading = True
        self.queried = False
        self.stat_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_PAGE, headers=HEADERS, params=params)
            print(f"[其他入库审核] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他入库审核] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常: {e}"))
            self.controller.after(0, lambda: self.stat_var.set("共 0 单"))
            return
        finally:
            self.loading = False
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "查询失败"
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            self.controller.after(0, lambda: self.stat_var.set("共 0 单"))
            return
        resp = data.get("data") or {}
        rows = resp.get("rows") if isinstance(resp, dict) else None
        if not isinstance(rows, list):
            rows = resp if isinstance(resp, list) else []
        self.controller.after(0, lambda: self._apply_result(rows))

    def _apply_result(self, rows):
        st = self.status_var.get()
        if st:
            rows = [r for r in rows if str(r.get('STATUS')) == str(st)]
        self.rows = rows
        self.queried = True
        self.clear_selection()
        self._render_rows()
        if not rows:
            messagebox.showinfo("查询结果", "暂无其它入库单")

    def _render_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in enumerate(self.rows):
            customer = ' '.join(x for x in (row.get('CUSTOMER_CODE'), row.get('CUSTOMER_NAME')) if x) or '-'
            values = (
                idx + 1,
                row.get('OTHER_IN_NO') or '-',
                self.status_label(row.get('STATUS')),
                self.bus_type_label(row.get('BUS_TYPE')),
                customer,
                row.get('CREATED_BY_NAME') or '-',
                self.format_date(row.get('SUBMIT_DATE') or row.get('CREATED_AT')),
                row.get('PLATE_NUMBER') or '',
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.stat_var.set("共 {} 单".format(len(self.rows)))

    # ============================================================ 审核
    def open_audit(self):
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("提示", "请先选择一条其它入库单")
            return
        if len(rows) > 1:
            messagebox.showinfo("提示", "请双击选择单条单据进入审核")
            return
        row = rows[0]
        bill_id = row.get('ID')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法审核")
            return
        self.audit_form = None
        self.audit_items = []
        self.audit_logs = []
        threading.Thread(target=self._audit_thread, args=(bill_id,), daemon=True).start()

    def _audit_thread(self, bill_id):
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                data = json.loads(r.text)
                if data.get("resultCode") == 200 or data.get("success"):
                    master = data.get("data") or {}
        except Exception as e:
            print(f"[其他入库审核-主单] 异常: {e}")
        if not master:
            self.controller.after(0, lambda: messagebox.showerror("加载失败", "主单数据加载失败，无法审核"))
            return
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                data = json.loads(r.text)
                if data.get("resultCode") == 200 or data.get("success"):
                    arr = data.get("data") or []
                    items = arr if isinstance(arr, list) else []
        except Exception as e:
            print(f"[其他入库审核-明细] 异常: {e}")
        logs = []
        try:
            r = self.controller.session.get(URL_LOGS, headers=HEADERS, params={
                'BILL_ID': bill_id, 'BILL_TYPE': LOG_BILL_TYPE,
                'limit': LOG_PAGE_SIZE, 'pageNum': 1, 'isShowLogs': True})
            if self._check_response(r):
                data = json.loads(r.text)
                dd = data.get("data") or {}
                if isinstance(dd, dict) and isinstance(dd.get("rows"), list):
                    logs = dd.get("rows")
        except Exception as e:
            print(f"[其他入库审核-日志] 异常: {e}")
        self.controller.after(0, lambda: self._show_audit_window(master, items, logs))

    def _show_audit_window(self, master, items, logs):
        self.audit_form = master
        self.audit_items = items
        self.audit_logs = logs
        win = tk.Toplevel(self)
        win.title("其它入库单审核 - %s" % (master.get('OTHER_IN_NO') or '-'))
        win.geometry("920x780")
        win.transient(self)
        self.audit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="其它入库单审核", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text="状态：%s" % self.status_label(master.get('STATUS')),
                 bg="#f7f8fa", fg="#ee0a24" if str(master.get('STATUS')) in ('12491003', '12491006') else "#323233",
                 font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        # 单据信息（默认折叠）
        info_header = tk.Button(win, text="单据信息 ▼", bg="#f0f0f0", relief=tk.FLAT,
                                anchor="w", font=("微软雅黑", 10, "bold"), command=lambda: self._toggle_info(win, info_header, info_frame))
        info_header.pack(fill=tk.X, padx=10, pady=(6, 0))
        info_frame = tk.Frame(win, bg="#ffffff")
        info_frame.pack(fill=tk.X, padx=10)
        info_frame.pack_forget()  # 默认折叠
        m = master
        for key, val in (("单据号", m.get('OTHER_IN_NO') or '-'),
                         ("业务类型", self.bus_type_label(m.get('BUS_TYPE'))),
                         ("入库仓库", m.get('WAREHOUSE_NAME') or self.warehouse_var.get()),
                         ("客户名称", m.get('CUSTOMER_NAME') or '-'),
                         ("客户代码", m.get('CUSTOMER_CODE') or '-'),
                         ("发起人", m.get('CREATED_BY_NAME') or '-'),
                         ("车牌号", m.get('PLATE_NUMBER') or '-'),
                         ("创建日期", self.format_date(m.get('CREATED_AT'))),
                         ("提报日期", m.get('SUBMIT_DATE') or '-'),
                         ("备注", m.get('REMARK') or '无')):
            line = tk.Frame(info_frame, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text=key + "：", bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=9, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#ffffff", font=("微软雅黑", 10),
                     anchor="w", wraplength=760, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 入库明细标题（含库位切换按钮，仅待审核 + 退货入库关联订单）
        title = tk.Frame(win, bg="#f0f0f0")
        title.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(title, text=f"入库明细（{len(items)}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        pending = self.is_pending_audit(master.get('STATUS'))
        can_switch = pending and str(master.get('BUS_TYPE')) == DEFAULT_BUS_TYPE and bool(master.get('CORRELATION_ORDER_NO'))
        if can_switch:
            tk.Button(title, text="切换指示库位", command=self.switch_indication_location,
                      bg="#fa8c16", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=4)
            tk.Button(title, text="切换销售库位", command=self.switch_sales_location,
                      bg="#969799", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=4)
        if pending:
            tk.Label(title, text="（待审核：双击明细行可选择入库库位）", bg="#f0f0f0",
                     fg="#fa8c16", font=("微软雅黑", 9)).pack(side=tk.RIGHT)

        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dtree = ttk.Treeview(dframe, columns=DETAIL_COLUMNS, show="headings", height=8)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            dtree.heading(col, text=col)
            anchor = "e" if col in ("销售单价", "数量", "金额") else "w"
            dtree.column(col, width=width, anchor=anchor)
        self._item_map = {}
        for idx, d in enumerate(items):
            iid = dtree.insert("", "end", values=(
                idx + 1,
                d.get('PART_NAME') or d.get('PART_NO') or '-',
                d.get('PART_NO') or '-',
                self.category_label(d.get('CATEGORY_TWO')),
                self.unusual_label(d.get('UNUSUAL_TYPE')),
                d.get('BRAND_NAME') or '',
                self.format_num(self._sale_price(d)),
                d.get('NUM') or 0,
                self.format_money(self.detail_amount(d)),
                d.get('PICKING_LOCATION') or d.get('INDICATE_LOCATION') or '',
            ))
            self._item_map[iid] = d
        dsb = ttk.Scrollbar(dframe, orient="vertical", command=dtree.yview)
        dtree.configure(yscrollcommand=dsb.set)
        dtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._audit_dtree = dtree
        if pending:
            dtree.bind("<Double-1>", lambda e: self._on_item_location())

        # 操作日志（默认折叠）
        log_header = tk.Button(win, text=f"操作日志（{len(logs)}） ▼", bg="#f0f0f0",
                               relief=tk.FLAT, anchor="w", font=("微软雅黑", 10, "bold"),
                               command=lambda: self._toggle_logs(win, log_header, log_frame))
        log_header.pack(fill=tk.X, padx=10, pady=(6, 0))
        log_frame = tk.Frame(win, bg="#ffffff")
        log_frame.pack(fill=tk.X, padx=10)
        log_frame.pack_forget()
        for log in logs:
            text = "[{}] {} {} {}".format(
                log.get('OPERATOR_NAME') or '-',
                self.format_date(log.get('OPERATE_DATE') or log.get('CREATED_AT')),
                ('{} → {}'.format(log.get('BEFORE_VALUE'), log.get('AFTER_VALUE'))
                 if log.get('BEFORE_VALUE') or log.get('AFTER_VALUE') else ''),
                ('（%s）' % log['REMARK']) if log.get('REMARK') else '')
            tk.Label(log_frame, text=text, bg="#ffffff", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)

        # 审核意见 / 操作（仅待审核）
        if pending:
            tk.Label(win, text="审核意见（驳回时必填；通过可填可不填）", bg="#f0f0f0",
                     font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 0))
            self.check_remark = tk.Text(win, height=3, font=("微软雅黑", 10))
            self.check_remark.pack(fill=tk.X, padx=10)
            bar = tk.Frame(win, bg="#f0f0f0")
            bar.pack(fill=tk.X, pady=8)
            tk.Button(bar, text="通 过", command=self.do_pass,
                      bg="#07c160", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
            tk.Button(bar, text="驳 回", command=self.do_reject,
                      bg="#ee0a24", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
            tk.Button(bar, text="关 闭", command=win.destroy,
                      bg="#e1e1e1", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.RIGHT, padx=10)
        else:
            bar = tk.Frame(win, bg="#f0f0f0")
            bar.pack(fill=tk.X, pady=10)
            tk.Label(bar, text="当前状态不可审核", bg="#f0f0f0", fg="#969799").pack(side=tk.LEFT, padx=12)
            tk.Button(bar, text="关 闭", command=win.destroy,
                      bg="#e1e1e1", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.RIGHT, padx=10)

    def _toggle_info(self, win, btn, frame):
        if frame.winfo_manager():
            frame.pack_forget()
            btn.config(text="单据信息 ▼")
        else:
            frame.pack(fill=tk.X, padx=10)
            btn.config(text="单据信息 ▲")

    def _toggle_logs(self, win, btn, frame):
        if frame.winfo_manager():
            frame.pack_forget()
            btn.config(text=f"操作日志（{len(self.audit_logs)}） ▼")
        else:
            frame.pack(fill=tk.X, padx=10)
            btn.config(text=f"操作日志（{len(self.audit_logs)}） ▲")

    # -------------------------------------------------- 金额 / 工具
    def _sale_price(self, d):
        """打印/预览销售单价：COST_PRICE_NEW 优先（对齐 PC 打印模板）"""
        return (d.get('COST_PRICE_NEW') if d.get('COST_PRICE_NEW') is not None
                else d.get('COST_PRICE_INFO') if d.get('COST_PRICE_INFO') is not None
                else d.get('COST_PRICE'))

    def detail_amount(self, d):
        """退货入库(12501004) 金额 = DISTINCTION_MONEY，其余 = NUM*COST_PRICE（对齐 PC）"""
        bus = self.audit_form.get('BUS_TYPE') if self.audit_form else (d.get('BUS_TYPE') or '')
        if str(bus) == DEFAULT_BUS_TYPE:
            try:
                return float(d.get('DISTINCTION_MONEY')) if d.get('DISTINCTION_MONEY') is not None else float(d.get('SALE_PRICE_INFO') or 0)
            except (TypeError, ValueError):
                return 0.0
        try:
            return float(d.get('NUM') or 0) * float(d.get('COST_PRICE') or 0)
        except (TypeError, ValueError):
            return 0.0

    # -------------------------------------------------- 库位切换/选择
    def switch_indication_location(self):
        for d in self.audit_items:
            d['PICKING_LOCATION_TEMP'] = d.get('PICKING_LOCATION')
            d['PICKING_LOCATION'] = d.get('INDICATE_LOCATION')
        self._refresh_audit_items()
        messagebox.showinfo("提示", "已切换为指示库位")

    def switch_sales_location(self):
        for d in self.audit_items:
            d['PICKING_LOCATION'] = d.get('PICKING_LOCATION_TEMP') or d.get('PICKING_LOCATION')
        self._refresh_audit_items()
        messagebox.showinfo("提示", "已切换为销售库位")

    def _on_item_location(self):
        sel = self._audit_dtree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先点击一条明细行")
            return
        row = self._item_map.get(sel[0])
        if row is None:
            return
        self.open_location_picker(row)

    def open_location_picker(self, row):
        win = tk.Toplevel(self)
        win.title("选择入库库位")
        win.geometry("480x420")
        win.transient(self)
        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="选择入库库位", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        state = {"rows": [], "sel": None}
        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, padx=10, pady=6)
        tk.Label(bar, text="库位前缀:", bg="#f0f0f0").pack(side=tk.LEFT)
        var_kw = tk.StringVar(value=row.get('PICKING_LOCATION') or '')
        entry = ttk.Entry(bar, textvariable=var_kw, width=20)
        entry.pack(side=tk.LEFT, padx=6)
        tk.Button(bar, text="查 询", command=lambda: self._search_loc_thread(win, var_kw.get(), listbox, state),
                  bg="#fa8c16", fg="white", bd=0, padx=10).pack(side=tk.LEFT)
        listbox = tk.Listbox(win, font=("微软雅黑", 11), activestyle="dotbox")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        def _on_pick(ev=None):
            i = listbox.curselection()
            if i and 0 <= int(i[0]) < len(state["rows"]):
                state["sel"] = state["rows"][int(i[0])]
        listbox.bind("<<ListboxSelect>>", _on_pick)
        foot = tk.Frame(win, bg="#f0f0f0")
        foot.pack(fill=tk.X, pady=6)
        tk.Button(foot, text="确 定", command=lambda: self._confirm_location(win, row, state),
                  bg="#fa8c16", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(foot, text="关 闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14, pady=4).pack(side=tk.RIGHT, padx=10)
        # 已有库位时自动搜索（对齐安卓 openLocationPicker → onLocSearch）
        if var_kw.get():
            self._search_loc_thread(win, var_kw.get(), listbox, state)

    def _search_loc_thread(self, win, kw, listbox, state):
        wh_id = (self.audit_form or {}).get('WAREHOUSE_ID')
        kw = (kw or '').strip()
        if not kw:
            listbox.delete(0, tk.END)
            listbox.insert(tk.END, "请输入库位前缀，如 E2")
            return
        def work():
            rows = []
            try:
                r = self.controller.session.get(URL_LOC, headers=HEADERS,
                                                params={'warehouseId': wh_id, 'locationNo': kw})
                if self._check_response(r):
                    data = json.loads(r.text)
                    if data.get("resultCode") == 200 or data.get("success"):
                        arr = data.get("data") or []
                        rows = arr if isinstance(arr, list) else []
            except Exception as e:
                print(f"[其他入库审核-库位] 异常: {e}")
            self.controller.after(0, lambda: self._render_locations(win, rows, listbox, state))
        threading.Thread(target=work, daemon=True).start()

    def _render_locations(self, win, rows, listbox, state):
        state["rows"] = rows
        state["sel"] = None
        listbox.delete(0, tk.END)
        if not rows:
            listbox.insert(tk.END, "未找到库位，请输入更长的前缀")
            return
        for l in rows:
            listbox.insert(tk.END, l.get('locationNo') or '')

    def _confirm_location(self, win, row, state):
        l = state.get("sel")
        if not l:
            messagebox.showinfo("提示", "请先选择库位", parent=win)
            return
        row['PICKING_LOCATION'] = l.get('locationNo') or ''
        row['select_LOCATION_OPTIONS'] = [l]
        row['select_locationOptionLoading'] = False
        win.destroy()
        self._refresh_audit_items()

    def _refresh_audit_items(self):
        if not hasattr(self, '_audit_dtree'):
            return
        dtree = self._audit_dtree
        for iid, d in self._item_map.items():
            idx = list(self._item_map).index(iid)
            dtree.item(iid, values=(
                idx + 1,
                d.get('PART_NAME') or d.get('PART_NO') or '-',
                d.get('PART_NO') or '-',
                self.category_label(d.get('CATEGORY_TWO')),
                self.unusual_label(d.get('UNUSUAL_TYPE')),
                d.get('BRAND_NAME') or '',
                self.format_num(self._sale_price(d)),
                d.get('NUM') or 0,
                self.format_money(self.detail_amount(d)),
                d.get('PICKING_LOCATION') or d.get('INDICATE_LOCATION') or '',
            ))

    # ============================================================ 审核提交
    def build_audit_payload(self, opinion):
        f = dict(self.audit_form or {})
        item_list = []
        for d in self.audit_items:
            it = dict(d)   # 保留明细行全部字段
            try:
                it['NUM'] = float(d.get('NUM') or 0)
            except (TypeError, ValueError):
                it['NUM'] = 0
            it['PICKING_LOCATION'] = d.get('PICKING_LOCATION') or d.get('INDICATE_LOCATION') or ''
            it['select_locationOptionLoading'] = d.get('select_locationOptionLoading') or False
            it['select_LOCATION_OPTIONS'] = d.get('select_LOCATION_OPTIONS') or []
            item_list.append(it)
        payload = dict(f)
        # 对齐报文：fileList 必传（PC formVo 初始 []，queryById 不回传需补）
        payload['fileList'] = f.get('fileList') or []
        payload['itemList'] = item_list
        payload['delItemList'] = []
        # 通过=null、驳回=意见（对齐报文：通过时 AUDIT_OPINION:null）
        payload['AUDIT_OPINION'] = opinion if opinion else None
        return payload

    def do_pass(self):
        if self.auditing:
            return
        opinion = self.check_remark.get("1.0", "end").strip() if self.check_remark else ''
        f = self.audit_form or {}
        # 对齐 PC：退货入库 + 有关联订单时，明细 BILL_TYPE=70121004 库位不能为空
        if str(f.get('BUS_TYPE')) == DEFAULT_BUS_TYPE and f.get('CORRELATION_ORDER_NO'):
            miss = next((d for d in self.audit_items
                         if str(d.get('BILL_TYPE')) == '70121004'
                         and not (d.get('PICKING_LOCATION') or d.get('INDICATE_LOCATION'))), None)
            if miss:
                messagebox.showwarning("提示", "库位不能为空，请填写!")
                return
        if not messagebox.askyesno("确认通过", f"确认通过单据 {f.get('OTHER_IN_NO') or ''}？通过后进入待入库。"):
            return
        self._submit_action(URL_APPROVE, opinion, "通过", "审核通过成功")

    def do_reject(self):
        if self.auditing:
            return
        opinion = self.check_remark.get("1.0", "end").strip() if self.check_remark else ''
        if not opinion:
            messagebox.showwarning("提示", "驳回必须填写审核意见")
            return
        self._submit_action(URL_REJECT, opinion, "驳回", "审核驳回成功")

    def _submit_action(self, url, opinion, action, ok_message):
        self.auditing = True
        payload = self.build_audit_payload(opinion)
        threading.Thread(target=self._audit_action_thread,
                         args=(url, payload, action, ok_message), daemon=True).start()

    def _audit_action_thread(self, url, payload, action, ok_message):
        try:
            r = self.controller.session.post(url, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他入库审核-{action}] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"{action}失败: {e}"))
            self.controller.after(0, lambda: setattr(self, 'auditing', False))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or f"{action}失败"
            self.controller.after(0, lambda: messagebox.showerror("审核失败", str(msg)))
            self.controller.after(0, lambda: setattr(self, 'auditing', False))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", ok_message))
        self.controller.after(0, lambda: setattr(self, 'auditing', False))
        self.controller.after(0, lambda: self._after_audit_success())

    def _after_audit_success(self):
        fid = (self.audit_form or {}).get('ID')
        if fid is not None:
            self.rows = [r for r in self.rows if str(r.get('ID')) != str(fid)]
        self._render_rows()
        if self.audit_win is not None:
            try:
                self.audit_win.destroy()
            except Exception:
                pass
            self.audit_win = None

    # ============================================================ 打印
    def open_print_selected(self):
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("提示", "请先勾选/多选要打印的单据（Ctrl/Shift 单击多选）")
            return
        nos = ",".join("'%s'" % r['OTHER_IN_NO'] for r in rows if r.get('OTHER_IN_NO'))
        if not nos:
            messagebox.showwarning("提示", "所选单据缺少单号，无法打印")
            return
        self.count_down = rows
        threading.Thread(target=self._print_thread, args=(nos,), daemon=True).start()

    def _print_thread(self, nos):
        params = self.build_query_params()
        params['OTHER_IN_NOS'] = nos
        try:
            r = self.controller.session.get(URL_PRINT, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他入库审核-打印] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"打印数据加载失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "获取打印数据失败"
            self.controller.after(0, lambda: messagebox.showerror("获取失败", str(msg)))
            return
        flat = data.get("data") if isinstance(data.get("data"), list) else []
        groups = []
        for row in flat:
            grp = next((g for g in groups if g['header'].get('OTHER_IN_NO') == row.get('OTHER_IN_NO')), None)
            if not grp:
                grp = {'header': row, 'items': []}
                groups.append(grp)
            grp['items'].append(row)
        for g in groups:
            g['commitBy'] = ''
            tn = 0
            ta = 0.0
            for it in g['items']:
                try:
                    num = float(it.get('NUM') or 0)
                except (TypeError, ValueError):
                    num = 0
                price = self._print_price(it)
                tn += num
                ta += num * price
            g['totalNum'] = tn
            g['totalAmount'] = round(ta, 2)
        if not groups:
            self.controller.after(0, lambda: messagebox.showinfo("提示", "未获取到打印数据"))
            return
        self.controller.after(0, lambda: self._show_print_window(groups))

    @staticmethod
    def _print_price(it):
        try:
            return float(it.get('COST_PRICE_NEW') if it.get('COST_PRICE_NEW') is not None
                         else it.get('COST_PRICE_INFO') if it.get('COST_PRICE_INFO') is not None
                         else it.get('COST_PRICE') or 0)
        except (TypeError, ValueError):
            return 0.0

    def _show_print_window(self, groups):
        win = tk.Toplevel(self)
        win.title("其它入库单打印预览")
        win.geometry("820x720")
        win.transient(self)
        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text=f"打印预览（已选择 {len(groups)} 个单据）", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        body = tk.Text(win, wrap=tk.NONE, font=("微软雅黑", 9), bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body.tag_configure("title", font=("微软雅黑", 15, "bold"), justify="center")
        body.tag_configure("h", font=("微软雅黑", 9, "bold"))
        for g in groups:
            h = g['header']
            body.insert(tk.END, "\n其它入库单\n", "title")
            body.insert(tk.END, f"入库仓库：{h.get('WAREHOUSE_NAME') or ''}    业务类型：{self.bus_type_label(h.get('BUS_TYPE'))}    客户名称：{h.get('CUSTOMER_NAME') or ''}\n")
            body.insert(tk.END, f"开单人：{h.get('CREATED_BY_NAME') or ''}    审核人：{g.get('commitBy') or ''}    单据号：{h.get('OTHER_IN_NO') or ''}\n")
            body.insert(tk.END, f"摘要：{h.get('REMARK') or ''}\n")
            body.insert(tk.END, "品牌 | 产品编码 | 产品名称 | 分类 | 退货原因 | 数量 | 单价 | 入库金额 | 库位\n", "h")
            for it in g['items']:
                amt = (float(it.get('NUM') or 0) * self._print_price(it))
                body.insert(tk.END, f"{self._short_brand(it.get('BRAND_NAME'))} | {it.get('PART_NO') or ''} | "
                                    f"{it.get('PART_NAME') or ''} | {self.category_label(it.get('CATEGORY_TWO'))} | "
                                    f"{self.unusual_label(it.get('UNUSUAL_TYPE'))} | {it.get('NUM') or 0} | "
                                    f"{self.format_num(self._print_price(it))} | {amt:.2f} | "
                                    f"{it.get('PICKING_LOCATION') or it.get('INDICATE_LOCATION') or ''}\n")
            body.insert(tk.END, f"合计数量：{g['totalNum']}    合计金额：{g['totalAmount']:.2f}\n")
            body.insert(tk.END, "─" * 100 + "\n")
        body.configure(state=tk.DISABLED)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="打 印", command=lambda: self.print_via_clodop(groups, win),
                  bg="#fa8c16", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    @staticmethod
    def _short_brand(name):
        if not name:
            return ''
        return str(name).replace('福耀玻璃', '福耀')

    def print_via_clodop(self, groups, win):
        """复用 CLodop WebSocket 协议（对齐 picking_shipping/internal_use）打印其它入库单"""
        try:
            import websocket
        except ImportError:
            messagebox.showerror("打印失败", "未安装 websocket 模块，无法连接 CLodop")
            return
        try:
            html_parts = [self._build_single_html(g) for g in groups]
            now = date.today()
            task_id = f"OI{now.month:02d}{now.day:02d}_1"
            delim = "\f\f"
            printer_name = "EPSON LQ-630K ESC/P2"
            ws = websocket.create_connection("ws://127.0.0.1:8000/c_webskt/", timeout=10)
            for idx, html_content in enumerate(html_parts):
                msg = (
                    f"post:charset=丂{delim}"
                    f"tid={task_id}_{idx}{delim}"
                    f"act=print{delim}"
                    f"browseurl=PYTHON_CLODOP{delim}"
                    f"companyname=用友汽车信息科技（上海）股份有限公司{delim}"
                    f"license=FA9A697F2551BCE81BD852A4EB520525347{delim}"
                    f"licensea=用友汽車信息科技（上海）股份有限公司{delim}"
                    f"licenseb=C66313BD8413BD0174C2CADD29F5380CD92{delim}"
                    f"licensec=Yonyou Auto Information Technology (Shanghai) Co., Ltd.{delim}"
                    f"licensed=941DF3639D9F5679867946141A31424B4E6{delim}"
                    f"top={delim}"
                    f"left={delim}"
                    f"width={delim}"
                    f"height={delim}"
                    f"printtask=其它入库单打印{delim}"
                    f"printerindex={printer_name}{delim}"
                    f"orient=1{delim}"
                    f"pagewidth=0{delim}"
                    f"pageheight=0{delim}"
                    f"pagename=A4{delim}"
                    f"printcopies=1{delim}"
                    f"itemcount=1{delim}"
                    f"1_type=4{delim}"
                    f"1_top=30{delim}"
                    f"1_left=3mm{delim}"
                    f"1_width=100%{delim}"
                    f"1_height=100%{delim}"
                    f"1_content={html_content}{delim}"
                    f"1_itemstylenames={delim}"
                    f"printmodenames=;left;top;width;height{delim}"
                    f"printstyleclassnames={delim}"
                )
                ws.send(msg)
            ws.close()
            messagebox.showinfo("成功", f"已发送 {len(html_parts)} 个打印任务到 {printer_name}")
            win.destroy()
        except Exception as e:
            messagebox.showerror("打印失败", f"CLodop WebSocket打印失败: {e}\n\n请确保 CLodop 服务已启动（localhost:8000）")

    def _build_single_html(self, g):
        h = g['header']
        rows = ""
        for it in g['items']:
            amt = (float(it.get('NUM') or 0) * self._print_price(it))
            rows += (
                f"<tr><td>{self._short_brand(it.get('BRAND_NAME'))}</td>"
                f"<td style='text-align:center'>{it.get('PART_NO') or ''}</td>"
                f"<td style='text-align:left'>{it.get('PART_NAME') or ''}</td>"
                f"<td>{self.category_label(it.get('CATEGORY_TWO'))}</td>"
                f"<td style='text-align:left'>{self.unusual_label(it.get('UNUSUAL_TYPE'))}</td>"
                f"<td>{it.get('NUM') or 0}</td>"
                f"<td>{self.format_num(self._print_price(it))}</td>"
                f"<td>{amt:.2f}</td>"
                f"<td>{it.get('PICKING_LOCATION') or it.get('INDICATE_LOCATION') or ''}</td></tr>"
            )
        return (
            "<style>body{margin:0;padding:0}</style>"
            "<div class='print-page' style='width:97%'>"
            "<div style='text-align:center;font-size:20px;font-weight:700'>其它入库单</div>"
            "<div style='font-size:13px'>"
            f"<div>入库仓库：{h.get('WAREHOUSE_NAME') or ''}　　业务类型：{self.bus_type_label(h.get('BUS_TYPE'))}　　客户名称：{h.get('CUSTOMER_NAME') or ''}</div>"
            f"<div>开单人：{h.get('CREATED_BY_NAME') or ''}　　审核人：{g.get('commitBy') or ''}　　单据号：{h.get('OTHER_IN_NO') or ''}</div>"
            f"<div>摘要：{h.get('REMARK') or ''}</div>"
            "</div>"
            "<table border='1' cellspacing='0' style='width:98%;font-size:12px;border-collapse:collapse;text-align:center'>"
            "<thead><tr><th>品牌</th><th>产品编码</th><th>产品名称</th><th>分类</th><th>退货原因</th>"
            "<th>入库数量</th><th>单价</th><th>入库金额</th><th>入库库位</th></tr></thead>"
            "<tbody>" + rows + "</tbody>"
            f"<tfoot><tr><td colspan='4'/><td colspan='2' style='font-weight:bold'>合计数量：{g['totalNum']}</td>"
            f"<td colspan='2' style='font-weight:bold'>合计金额：{g['totalAmount']:.2f}</td><td/></tr></tfoot>"
            "</table></div>"
        )

# -*- coding: utf-8 -*-
"""
其它出入库管理 hub · 菜单3「其它出库审核」OtherOutboundReviewPage
--------------------------------------------------------------------
对齐 Android 端 OtherOutboundReview.vue + src/service/otherOutboundReview.js
与 PC Web 反编译源码（桌面《其他出库审核》目录）及 HAR 实测报文：
  - financeAuditLevel3-0eb34029.js  → fromData===910107（财务三级审核）
  - index-141b080d.js               → 列表列 / 状态过滤 / 审核与明细入口
  - addEditDetail-d725edb8.js       → 明细列 / saveAction 审核报文
  - xb.fy-carg.com.har              → 单据 1764 / ZZHJQTCK2026102100005 全流程报文

状态流转（1251 组，HAR 实证）：
  待提交 12511001 --提交--> 待仓库处理 12511002 --仓库处理--> 待审核 12511005
  待审核 12511005 --财务三级审核通过(approved)--> 待出库 12511007 --> 已出库 12511008
                  --财务三级审核驳回(reject)--> 审核驳回 12511006（可重新编辑提交）
  其余：部分出库 12511010、已作废 12511009。
  审核按钮仅在 STATUS==12511005（待审核）可用（Web disabled:a.row.STATUS!=12511005）。

业务类型（1252 组）：12521001 报损出库 / 12521002 延保出库 / 12521003 采购入库退货。
  本页默认 12521003（HAR 与安卓 OTHER_OUT_AUDIT_BUS_TYPE_FALLBACK 一致），排除 12521001
  （报损出库由「报损出库申请」/其自身审核流负责，Web formList excludeCode=12521001）。

查询（HAR 实证，fromData=910107）：
  GET /dmscloud.part/otherOutboundWarehouse/page
    ?searchLoading=true&BRAND_ID=&OTHER_OUT_NO=&BUS_TYPE=12521003&STATUS=12511005
     &STATUS_STR=12511005,12511006,12511007,12511010,12511008
     &CREATED_AT_FROM=..&CREATED_AT_TO=..&partCode=&partName=&WAREHOUSE_CODE=SQ
     &pageNum=1&limit=500
  ⚠️ STATUS_STR 是审核页固定下发的状态集合（Web preSearch / 安卓 OTHER_OUT_AUDIT_STATUS_STR），
     后端据此二次过滤，不可省略、不可随筛选变化。
  WAREHOUSE_CODE 取当前仓库编码（get_storage_code），严禁取会话 current_warehouse。

审核报文（HAR #finance/level3/approved 实证）：
  payload = queryById 完整主单展开
          + fileList:[]  + itemList:[明细]  + delItemList:[]
          + FINANCE_AUDIT_OPINION3（通过=null；驳回=意见文本，必填）
  - itemList 每行保留持久化行全部字段；REMOVAL_LOCATION 由 "15022" 字符串转数字 15022；
    loList 每项补 disabled:false（Web addEditDetail 处理，HAR 实证）。
  - 顶层空串键剔除（对齐 PC axios 请求拦截器 / 安卓 stripEmptyTopLevel），None 值保留。

接口清单：
  列表   GET  /dmscloud.part/otherOutboundWarehouse/page
  主单   GET  /dmscloud.part/otherOutboundWarehouse/queryById?id=
  明细   GET  /dmscloud.part/otherOutboundWarehouse/queryById/items?id=
  日志   GET  /dmscloud.part/operateLogs/page?BILL_ID=&BILL_TYPE=12041005&limit=5&isShowLogs=true
  通过   POST /dmscloud.part/otherOutboundWarehouse/finance/level3/approved
  驳回   POST /dmscloud.part/otherOutboundWarehouse/finance/level3/reject
  打印   GET  /dmscloud.part/otherOutboundWarehouse/getPrintList?OTHER_OUT_NOS='..'&STATUS_STR=..
  导出   GET  /dmscloud.part/otherOutboundWarehouse/exportData?（查询条件 + searchLoading=false）
  附件   GET  /dmscloud.basedata/file/billFiles/10422113/{billId}（只读）
  下载   GET  /dmscloud.basedata/file/billFilesReview/10422113/{fileKey}
  字典   GET  /dmscloud.basedata/dicts（1251 状态 / 1252 业务类型 / 9092 分类，失败静默用兜底）

已知口径差异（有证据，不擅自补）：
  1. 审核页明细为只读（Web mode=AUDIT 不渲染库位下拉/破损原因/库位库存数列），
     故本页不提供库位切换、不改明细，仅原样回传（与安卓 buildAuditPayload 一致）。
  2. 打印单价取 COST_PRICE（getPrintList 返回批次成本价；Web 批次单价列同字段）。
  3. 附件在审核态为只读展示（Web optionType="detail"，不上传）。
"""
import json
import threading
from datetime import date, timedelta

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}
BASE = 'https://xb.fy-carg.com'
PART = '/dmscloud.part/otherOutboundWarehouse'

URL_PAGE = BASE + PART + '/page'
URL_DETAIL = BASE + PART + '/queryById'
URL_ITEMS = BASE + PART + '/queryById/items'
URL_APPROVE = BASE + PART + '/finance/level3/approved'
URL_REJECT = BASE + PART + '/finance/level3/reject'
URL_PRINT = BASE + PART + '/getPrintList'
URL_EXPORT = BASE + PART + '/exportData'
URL_LOGS = BASE + '/dmscloud.part/operateLogs/page'
URL_DICT = BASE + '/dmscloud.basedata/dicts'
URL_ATTACH_CFG = BASE + '/dmscloud.basedata/file/billFiles'
URL_ATTACH_REVIEW = BASE + '/dmscloud.basedata/file/billFilesReview'

QUERY_LIMIT = 500
LOG_BILL_TYPE = 12041005
LOG_PAGE_SIZE = 5
ATTACH_BILL_TYPE = 10422113

# 状态字典 1251 组（离线兜底；运行期被 dicts 覆盖）
STATUS_FALLBACK = {
    '12511001': '待提交', '12511002': '待仓库处理', '12511005': '待审核',
    '12511006': '审核驳回', '12511007': '待出库', '12511010': '部分出库',
    '12511008': '已出库', '12511009': '已作废',
}
# 业务类型 1252 组
BUS_TYPE_FALLBACK = {
    '12521001': '报损出库', '12521002': '延保出库', '12521003': '采购入库退货',
}
# 明细分类 9092 组（打印/展示备用）
CATEGORY_FALLBACK = {
    '90921001': '前挡', '90921002': '后挡', '90921003': '边窗',
    '90921004': '其它', '90921005': '天窗',
}
DICT_TYPES = ['1251', '1252', '9092']

PENDING_STATUS = '12511005'       # 待审核（唯一可审核状态）
DEFAULT_BUS_TYPE = '12521003'     # 采购入库退货（HAR / 安卓默认）
# 审核页固定状态集合（Web preSearch fromData=910107 / 安卓 OTHER_OUT_AUDIT_STATUS_STR）
AUDIT_STATUS_STR = '12511005,12511006,12511007,12511010,12511008'

# 状态快捷筛选（对齐安卓 OTHER_OUT_AUDIT_STATUS_FILTERS：STATUS_STR 覆盖 5 态 + 全部）
STATUS_FILTERS = [
    ('全部', ''), ('待审核', '12511005'), ('审核驳回', '12511006'),
    ('待出库', '12511007'), ('部分出库', '12511010'), ('已出库', '12511008'),
]
# 业务类型快捷筛选（排除报损出库 12521001，对齐 Web formList excludeCode）
BUS_FILTERS = [
    ('采购退货', '12521003'), ('延保出库', '12521002'), ('全部', ''),
]

# 列表列（Web index-141b080d.js 实证：序号 + 7 数据列；操作列由双击代替）
COLUMNS = ["序号", "业务单号", "业务类型", "状态", "发起人", "出库仓库", "提报日期", "创建日期"]
COLUMN_WIDTHS = [50, 190, 130, 95, 100, 110, 110, 120]

# 审核窗明细列（Web 明细弹窗 HTML 快照 + addEditDetail.js 实证，只读 8 列）
DETAIL_COLUMNS = ["序号", "CARG全码/产品编码", "产品名称", "批次单价",
                  "出库库位", "出库数量", "退货单价", "出库金额"]
DETAIL_WIDTHS = [45, 165, 300, 95, 110, 80, 95, 105]


class OtherOutboundReviewPage(BasePage):
    """其它出库审核页面（查询 / 明细 / 通过 / 驳回 / 打印 / 导出）"""

    def __init__(self, parent, controller):
        self.rows = []              # 当前列表数据
        self.queried = False
        self.loading = False
        self.auditing = False
        self.audit_win = None
        self.audit_form = None      # queryById 完整主单（审核报文权威对象）
        self.audit_items = []       # queryById/items 明细行（只读）
        self.audit_logs = []        # operateLogs 操作日志
        self.audit_files = []       # 附件（只读）
        self.dict_maps = {}         # '1251' -> {code: desc}
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

        # 实时字典（失败静默用兜底）
        threading.Thread(target=self._dict_thread, daemon=True).start()

        # 对齐安卓 onMounted / Web mounted：进入页面自动查询（默认待审核 + 近3个月）
        if self.controller.options:
            self.query()

    def setup_filter_panel(self, parent):
        frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                              font=("微软雅黑", 10, "bold"))
        frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="出库仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.bind("<<ComboboxSelected>>", lambda e: self.query())
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="业务单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_out_no = tk.StringVar()
        ttk.Entry(row1, textvariable=self.var_out_no, width=22).pack(side=tk.LEFT)

        tk.Label(row1, text="产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_part_code = tk.StringVar()
        ttk.Entry(row1, textvariable=self.var_part_code, width=14).pack(side=tk.LEFT)

        tk.Label(row1, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 2))
        self.var_part_name = tk.StringVar()
        ttk.Entry(row1, textvariable=self.var_part_name, width=14).pack(side=tk.LEFT)

        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="创建日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row2, width=11, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT)
        tk.Label(row2, text="至", bg="#f0f0f0").pack(side=tk.LEFT, padx=3)
        self.end_cal = DateEntry(row2, width=11, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT)
        tk.Label(row2, text="（默认近 3 个月）", bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=8)

        tk.Label(row2, text="业务类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(16, 5))
        self.bus_var = tk.StringVar(value=DEFAULT_BUS_TYPE)
        self.bus_buttons = {}
        for label, value in BUS_FILTERS:
            b = tk.Button(row2, text=label, width=10, relief=tk.FLAT,
                          bg="#e1e1e1", fg="#323233",
                          command=lambda v=value: self.change_bus_type(v))
            b.pack(side=tk.LEFT, padx=2)
            self.bus_buttons[value] = b
        self._update_bus_buttons()

        row3 = tk.Frame(frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(value=PENDING_STATUS)
        self.status_buttons = {}
        for label, value in STATUS_FILTERS:
            b = tk.Button(row3, text=label, width=9, relief=tk.FLAT,
                          bg="#e1e1e1", fg="#323233",
                          command=lambda v=value: self.change_status(v))
            b.pack(side=tk.LEFT, padx=2)
            self.status_buttons[value] = b
        self._update_status_buttons()

        tk.Button(row3, text="查 询", command=self.query,
                  bg="#fa8c16", fg="white", padx=16, pady=3, bd=0).pack(side=tk.LEFT, padx=14)
        tk.Button(row3, text="重 置", command=self.reset_form,
                  bg="#969799", fg="white", padx=14, pady=3, bd=0).pack(side=tk.LEFT, padx=2)

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
        table_frame = tk.LabelFrame(parent, text="其它出库单列表（财务三级审核）", bg="#f0f0f0",
                                    bd=1, relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings",
                                 height=15, selectmode="extended")
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center" if col == "序号" else "w")
        self.tree.tag_configure("odd", background="#fafafa")
        self.tree.tag_configure("pending", background="#fff7e6")

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
        tk.Button(bar, text="审核选中单据", command=self.open_audit,
                  bg="#07c160", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="打印预览（勾选单据）", command=self.open_print_selected,
                  bg="#fa8c16", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="明细导出", command=self.export_excel,
                  bg="#1989fa", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="取消选择", command=self.clear_selection,
                  bg="#e1e1e1", relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=5)
        tk.Label(bar, text="提示：仅「待审核」可审核；双击行查看明细", bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    # ============================================================ 工具
    @staticmethod
    def def_date(kind):
        """Web search 默认 CREATED_AT_FROM = 近 3 个月（setMonth(-3)），止取今天"""
        today = date.today()
        if kind == 'begin':
            return today - timedelta(days=90)
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
            if n != n:
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

    @staticmethod
    def short_brand(name):
        if not name:
            return ''
        return str(name).replace('福耀玻璃', '福耀')

    def _decode(self, group, code, fallback):
        if code is None or code == '':
            return ''
        s = str(code)
        live = (self.dict_maps.get(group) or {}).get(s)
        if live:
            return live
        return fallback.get(s, s)

    def status_label(self, code):
        return self._decode('1251', code, STATUS_FALLBACK) or '-'

    def bus_type_label(self, code):
        return self._decode('1252', code, BUS_TYPE_FALLBACK) or '-'

    def category_label(self, code):
        return self._decode('9092', code, CATEGORY_FALLBACK) or '-'

    def is_pending_audit(self, code):
        return str(code) == PENDING_STATUS

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    # -------------------------------------------------- 字典
    def _dict_thread(self):
        try:
            r = self.controller.session.get(URL_DICT, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其它出库审核] 字典加载失败(用兜底): {e}")
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
            btn.config(bg="#fa8c16", fg="white") if value == cur else btn.config(bg="#e1e1e1", fg="#323233")

    def _update_status_buttons(self):
        cur = self.status_var.get()
        for value, btn in self.status_buttons.items():
            btn.config(bg="#fa8c16", fg="white") if value == cur else btn.config(bg="#e1e1e1", fg="#323233")

    def change_status(self, value):
        self.status_var.set(value)
        self._update_status_buttons()
        self.query()

    def change_bus_type(self, value):
        self.bus_var.set(value)
        self._update_bus_buttons()
        self.query()

    def reset_form(self):
        self.var_out_no.set('')
        self.var_part_code.set('')
        self.var_part_name.set('')
        self.bus_var.set(DEFAULT_BUS_TYPE)
        self.status_var.set(PENDING_STATUS)
        self._update_bus_buttons()
        self._update_status_buttons()
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.query()

    def _selected_rows(self):
        out = []
        for iid in self.tree.selection():
            idx = self.tree.index(iid)
            if 0 <= idx < len(self.rows):
                out.append(self.rows[idx])
        return out

    def _update_sel_label(self):
        self.sel_var.set(f"已选 {len(self.tree.selection())} 单")

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())
        self._update_sel_label()

    # ============================================================ 查询
    def build_query_params(self):
        """严格对齐 HAR：含固定 STATUS_STR、searchLoading、WAREHOUSE_CODE、pageNum/limit"""
        wh = self.warehouse_var.get()
        return {
            "searchLoading": "true",
            "BRAND_ID": '',
            "OTHER_OUT_NO": self.var_out_no.get() or '',
            "BUS_TYPE": self.bus_var.get() or '',
            "STATUS": self.status_var.get() or '',
            "STATUS_STR": AUDIT_STATUS_STR,
            "CREATED_AT_FROM": self.fmt_date(self.start_cal.get_date()) if self.start_cal.get() else '',
            "CREATED_AT_TO": self.fmt_date(self.end_cal.get_date()) if self.end_cal.get() else '',
            "partCode": self.var_part_code.get() or '',
            "partName": self.var_part_name.get() or '',
            "WAREHOUSE_CODE": get_storage_code(wh),
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
            print(f"[其它出库审核] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其它出库审核] 请求异常: {e}")
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
        # 后端已按 STATUS 过滤，前端再兜底一次（对齐安卓 doQuery）
        st = self.status_var.get()
        if st:
            rows = [r for r in rows if str(r.get('STATUS')) == str(st)]
        self.rows = rows
        self.queried = True
        self.clear_selection()
        self._render_rows()
        if not rows:
            messagebox.showinfo("查询结果", "暂无其它出库单")

    def _render_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in enumerate(self.rows):
            values = (
                idx + 1,
                row.get('OTHER_OUT_NO') or '-',
                self.bus_type_label(row.get('BUS_TYPE')),
                self.status_label(row.get('STATUS')),
                row.get('CREATED_BY_NAME') or '-',
                row.get('WAREHOUSE_NAME') or self.warehouse_var.get(),
                self.format_date(row.get('SUBMIT_DATE') or row.get('CREATED_AT')),
                self.format_date(row.get('CREATED_AT')),
            )
            if self.is_pending_audit(row.get('STATUS')):
                tags = ("pending",)
            else:
                tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.stat_var.set("共 {} 单（待审核 {} 单）".format(
            len(self.rows), sum(1 for r in self.rows if self.is_pending_audit(r.get('STATUS')))))

    # ============================================================ 审核
    def open_audit(self):
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("提示", "请先选择一条其它出库单")
            return
        if len(rows) > 1:
            messagebox.showinfo("提示", "请只选择单条单据进入审核")
            return
        row = rows[0]
        bill_id = row.get('ID')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法加载明细")
            return
        self.audit_form = None
        self.audit_items = []
        self.audit_logs = []
        self.audit_files = []
        threading.Thread(target=self._audit_thread, args=(bill_id,), daemon=True).start()

    def _audit_thread(self, bill_id):
        """主单 + 明细 + 操作日志 + 附件（对齐安卓 openAudit / Web getDetailData）"""
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                data = json.loads(r.text)
                if data.get("resultCode") == 200 or data.get("success"):
                    master = data.get("data") or {}
        except Exception as e:
            print(f"[其它出库审核-主单] 异常: {e}")
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
            print(f"[其它出库审核-明细] 异常: {e}")
        logs = []
        try:
            r = self.controller.session.get(URL_LOGS, headers=HEADERS, params={
                'BILL_ID': bill_id, 'BILL_TYPE': LOG_BILL_TYPE,
                'limit': LOG_PAGE_SIZE, 'pageNum': 1, 'isShowLogs': 'true'})
            if self._check_response(r):
                data = json.loads(r.text)
                dd = data.get("data") or {}
                if isinstance(dd, dict) and isinstance(dd.get("rows"), list):
                    logs = dd.get("rows")
        except Exception as e:
            print(f"[其它出库审核-日志] 异常: {e}")
        files = self._fetch_attach_cfg(bill_id)
        self.controller.after(0, lambda: self._show_audit_window(master, items, logs, files))

    def _fetch_attach_cfg(self, bill_id):
        """附件只读配置（对齐 Web optionType='detail' / 报损出库申请 _fetch_attach_cfg）"""
        try:
            url = '{}/{}/{}'.format(URL_ATTACH_CFG, ATTACH_BILL_TYPE, bill_id)
            r = self.controller.session.get(url, headers=HEADERS)
            if not self._check_response(r):
                return []
            data = json.loads(r.text)
            d = data.get('data') or {}
            cfg = d.get('initialPreviewConfig') if isinstance(d, dict) else None
            previews = d.get('initialPreview') if isinstance(d, dict) else None
            out = []
            for i, c in enumerate(cfg if isinstance(cfg, list) else []):
                if not isinstance(c, dict):
                    continue
                key = str(c.get('key') or '')
                name = c.get('caption') or ('附件' + key)
                out.append({
                    'name': name,
                    'key': key,
                    'size': int(c.get('size') or 0),
                    'preview': (previews[i] if isinstance(previews, list) and i < len(previews) else ''),
                })
            return out
        except Exception as e:
            print(f"[其它出库审核-附件] 失败: {e}")
            return []

    def _show_audit_window(self, master, items, logs, files):
        self.audit_form = master
        self.audit_items = items
        self.audit_logs = logs
        self.audit_files = files
        pending = self.is_pending_audit(master.get('STATUS'))
        m = master

        win = tk.Toplevel(self)
        win.title("其它出库单审核 - %s" % (m.get('OTHER_OUT_NO') or '-'))
        win.geometry("980x800")
        win.transient(self)
        self.audit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="其它出库单审核（财务三级）", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text="状态：%s" % self.status_label(m.get('STATUS')),
                 bg="#f7f8fa", fg="#ee0a24" if str(m.get('STATUS')) == '12511006' else "#323233",
                 font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        # 单据信息（默认展开）
        info_header = tk.Button(win, text="单据信息 ▲", bg="#f0f0f0", relief=tk.FLAT,
                                anchor="w", font=("微软雅黑", 10, "bold"),
                                command=lambda: self._toggle_section(info_header, info_frame, "单据信息"))
        info_header.pack(fill=tk.X, padx=10, pady=(6, 0))
        info_frame = tk.Frame(win, bg="#ffffff")
        info_frame.pack(fill=tk.X, padx=10)
        for key, val in (("单据号", m.get('OTHER_OUT_NO') or '-'),
                         ("业务类型", self.bus_type_label(m.get('BUS_TYPE'))),
                         ("出库仓库", m.get('WAREHOUSE_NAME') or self.warehouse_var.get()),
                         ("供应商", m.get('SUPPLIER_NAME') or '-'),
                         ("供应商代码", m.get('SUPPLIER_NO') or '-'),
                         ("发起人", m.get('CREATED_BY_NAME') or '-'),
                         ("无税金额", self.format_money(m.get('NO_TAX_AMOUNT'))),
                         ("创建日期", self.format_date(m.get('CREATED_AT'))),
                         ("提报日期", m.get('SUBMIT_DATE') or '-'),
                         ("关联单号", m.get('CORRELATION_ORDER_NO') or '-'),
                         ("审核意见3", m.get('FINANCE_AUDIT_OPINION3') or '无'),
                         ("备注", m.get('REMARK') or '无')):
            line = tk.Frame(info_frame, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text=key + "：", bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=11, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#ffffff", font=("微软雅黑", 10),
                     anchor="w", wraplength=800, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 出库明细（只读）
        title = tk.Frame(win, bg="#f0f0f0")
        title.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(title, text=f"出库明细（{len(items)}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        total_amount = sum(self._detail_amount(d) for d in items)
        tk.Label(title, text="合计金额：%s" % self.format_money(total_amount), bg="#f0f0f0",
                 fg="#ee0a24", font=("微软雅黑", 10, "bold")).pack(side=tk.RIGHT, padx=6)

        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dtree = ttk.Treeview(dframe, columns=DETAIL_COLUMNS, show="headings", height=8)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            dtree.heading(col, text=col)
            dtree.column(col, width=width,
                         anchor="e" if col in ("批次单价", "出库数量", "退货单价", "出库金额") else "w")
        for idx, d in enumerate(items):
            dtree.insert("", "end", values=(
                idx + 1,
                d.get('PART_NO') or '-',
                d.get('PART_NAME') or '-',
                self.format_num(d.get('COST_PRICE')),
                d.get('REMOVAL_LOCATION_NAME') or d.get('REMOVAL_LOCATION') or '',
                self.format_num(d.get('NUM')),
                self.format_num(d.get('RETURN_UNIT_PRICE')),
                self.format_money(self._detail_amount(d)),
            ))
        dsb = ttk.Scrollbar(dframe, orient="vertical", command=dtree.yview)
        dtree.configure(yscrollcommand=dsb.set)
        dtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)
        tooltip_manager.attach_tooltip(dtree)

        # 操作日志（默认折叠）
        log_header = tk.Button(win, text=f"操作日志（{len(logs)}） ▼", bg="#f0f0f0",
                               relief=tk.FLAT, anchor="w", font=("微软雅黑", 10, "bold"),
                               command=lambda: self._toggle_section(log_header, log_frame,
                                                                    f"操作日志（{len(logs)}）", collapsed=True))
        log_header.pack(fill=tk.X, padx=10, pady=(6, 0))
        log_frame = tk.Frame(win, bg="#ffffff")
        log_frame.pack(fill=tk.X, padx=10)
        log_frame.pack_forget()
        if not logs:
            tk.Label(log_frame, text="无操作日志", bg="#ffffff", fg="#c8c9cc",
                     anchor="w").pack(fill=tk.X)
        for log in logs:
            trans = ''
            if log.get('BEFORE_VALUE') or log.get('AFTER_VALUE'):
                trans = '{} → {}'.format(log.get('BEFORE_VALUE') or '-', log.get('AFTER_VALUE') or '-')
            remark = ('（%s）' % log['REMARK']) if log.get('REMARK') else ''
            summary = ('[%s] ' % log['SUMMARY']) if log.get('SUMMARY') else ''
            tk.Label(log_frame,
                     text="[{}] {} {}{}{}".format(
                         log.get('OPERATOR_NAME') or log.get('OPERATOR') or '-',
                         self.format_date(log.get('OPERATE_DATE') or log.get('CREATED_AT')),
                         summary, trans, remark),
                     bg="#ffffff", anchor="w", font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)

        # 附件（默认折叠，只读）
        file_header = tk.Button(win, text=f"附件（{len(files)}） ▼", bg="#f0f0f0",
                                relief=tk.FLAT, anchor="w", font=("微软雅黑", 10, "bold"),
                                command=lambda: self._toggle_section(file_header, file_frame,
                                                                     f"附件（{len(files)}）", collapsed=True))
        file_header.pack(fill=tk.X, padx=10, pady=(6, 0))
        file_frame = tk.Frame(win, bg="#ffffff")
        file_frame.pack(fill=tk.X, padx=10)
        file_frame.pack_forget()
        if not files:
            tk.Label(file_frame, text="无附件", bg="#ffffff", fg="#c8c9cc", anchor="w").pack(fill=tk.X)
        for f in files:
            line = tk.Frame(file_frame, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text="{}（{}）".format(f.get('name') or '-', self._fmt_size(f.get('size'))),
                     bg="#ffffff", anchor="w", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=4)
            tk.Button(line, text="下载", command=lambda a=f: self.download_attachment(a),
                      bg="#1989fa", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=6)

        # 审核意见 / 操作（仅待审核）
        if pending:
            tk.Label(win, text="审核意见（通过可空；驳回必填，写入 FINANCE_AUDIT_OPINION3）",
                     bg="#f0f0f0", font=("微软雅黑", 10, "bold"), anchor="w").pack(
                fill=tk.X, padx=10, pady=(6, 0))
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
            self.check_remark = None
            bar = tk.Frame(win, bg="#f0f0f0")
            bar.pack(fill=tk.X, pady=10)
            tk.Label(bar, text="当前状态不可审核（仅「待审核」12511005 可审核），此处仅供查看明细",
                     bg="#f0f0f0", fg="#969799").pack(side=tk.LEFT, padx=12)
            tk.Button(bar, text="关 闭", command=win.destroy,
                      bg="#e1e1e1", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.RIGHT, padx=10)

    def _toggle_section(self, btn, frame, label, collapsed=False):
        """折叠/展开；collapsed 仅用于初始文本箭头，实际以 winfo_manager 判定"""
        if frame.winfo_manager():
            frame.pack_forget()
            btn.config(text=f"{label} ▼")
        else:
            frame.pack(fill=tk.X, padx=10)
            btn.config(text=f"{label} ▲")

    @staticmethod
    def _fmt_size(size):
        try:
            n = int(size or 0)
        except (TypeError, ValueError):
            return '0B'
        if n < 1024:
            return '%dB' % n
        if n < 1024 * 1024:
            return '%.1fKB' % (n / 1024.0)
        return '%.1fMB' % (n / 1024.0 / 1024.0)

    def _detail_amount(self, d):
        """出库金额：优先 NO_TAX_AMOUNT（HAR 行级已算好），缺则 NUM*COST_PRICE"""
        v = d.get('NO_TAX_AMOUNT')
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
        try:
            return float(d.get('NUM') or 0) * float(d.get('COST_PRICE') or 0)
        except (TypeError, ValueError):
            return 0.0

    # -------------------------------------------------- 附件下载
    def download_attachment(self, att):
        path = filedialog.asksaveasfilename(title="保存附件", initialfile=att.get('name') or 'attachment')
        if not path:
            return
        threading.Thread(target=self._download_thread, args=(att, path), daemon=True).start()

    def _download_thread(self, att, path):
        file_url = att.get('preview') or ''
        if not file_url:
            file_url = '/file/billFilesReview/{}/{}'.format(ATTACH_BILL_TYPE, att.get('key') or '')
        full = file_url if file_url.startswith('http') else (BASE + '/dmscloud.basedata' + file_url)
        try:
            r = self.controller.session.get(full, headers=HEADERS)
            if not self._check_response(r):
                return
            with open(path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"[其它出库审核-附件下载] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror("下载失败", str(e)))
            return
        self.controller.after(0, lambda: messagebox.showinfo("完成", f"附件已保存到：\n{path}"))

    # ============================================================ 审核提交
    def build_audit_payload(self, opinion):
        """审核报文（HAR #finance/level3/approved 实证）

        queryById 完整主单展开 + fileList:[] + itemList + delItemList:[] + FINANCE_AUDIT_OPINION3。
        itemList：REMOVAL_LOCATION 字符串→数字、loList 每项补 disabled:false（Web 处理，HAR 实证）。
        顶层空串键剔除（对齐 PC axios 拦截器 / 安卓 stripEmptyTopLevel），None 保留。
        """
        f = dict(self.audit_form or {})
        item_list = []
        for d in self.audit_items:
            it = dict(d)
            # REMOVAL_LOCATION: "15022" -> 15022（HAR 提交为数字）
            loc = d.get('REMOVAL_LOCATION')
            if loc not in (None, ''):
                try:
                    it['REMOVAL_LOCATION'] = int(float(loc))
                except (TypeError, ValueError):
                    pass
            # loList 每项补 disabled:false（HAR 实证；Web addEditDetail 打开弹窗时注入）
            lo = d.get('loList')
            if isinstance(lo, list):
                new_lo = []
                for x in lo:
                    if isinstance(x, dict):
                        y = dict(x)
                        y.setdefault('disabled', False)
                        new_lo.append(y)
                    else:
                        new_lo.append(x)
                it['loList'] = new_lo
            item_list.append(it)
        payload = dict(f)
        payload['fileList'] = f.get('fileList') or []
        payload['itemList'] = item_list
        payload['delItemList'] = []
        payload['FINANCE_AUDIT_OPINION3'] = opinion if opinion else None
        # 责任人字段：Web saveInfoFn 在无责任人时置 "" 后由拦截器剔除（HAR approved 报文无此二键）；
        # 有值时原样保留。此处按同一语义剔除空值（None/''）。
        for k in ('RESPONSIBLE_PERSON', 'RESPONSIBLE_PERSON_ID'):
            if k in payload and (payload[k] is None or payload[k] == ''):
                payload.pop(k, None)
        # 顶层空串键剔除（不递归，itemList 内部空串保留）；None 值保留
        return {k: v for k, v in payload.items() if v != ''}

    def opinion_text(self):
        """安全读取审核意见：审核窗被关闭后控件已销毁，避免 TclError"""
        if self.check_remark is None:
            return ''
        try:
            if not self.check_remark.winfo_exists():
                return ''
            return self.check_remark.get("1.0", "end").strip()
        except tk.TclError:
            return ''

    def do_pass(self):
        if self.auditing:
            return
        f = self.audit_form or {}
        if not self.is_pending_audit(f.get('STATUS')):
            messagebox.showwarning("提示", "仅「待审核」单据可通过")
            return
        opinion = self.opinion_text()
        if not messagebox.askyesno("确认通过",
                                   f"确认通过单据 {f.get('OTHER_OUT_NO') or ''}？通过后进入待出库。"):
            return
        self._submit_action(URL_APPROVE, opinion, "通过", "审核通过成功")

    def do_reject(self):
        if self.auditing:
            return
        f = self.audit_form or {}
        if not self.is_pending_audit(f.get('STATUS')):
            messagebox.showwarning("提示", "仅「待审核」单据可驳回")
            return
        opinion = self.opinion_text()
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
                self.controller.after(0, lambda: setattr(self, 'auditing', False))
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其它出库审核-{action}] 异常: {e}")
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
        """从列表移除该单并更新统计（对齐安卓 removeFromList，不重新拉全量）"""
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
        nos = ",".join("'%s'" % r['OTHER_OUT_NO'] for r in rows if r.get('OTHER_OUT_NO'))
        if not nos:
            messagebox.showwarning("提示", "所选单据缺少单号，无法打印")
            return
        threading.Thread(target=self._print_thread, args=(nos,), daemon=True).start()

    def _print_thread(self, nos):
        # HAR 实证：getPrintList 仅 OTHER_OUT_NOS + STATUS_STR 两个参数
        params = {'OTHER_OUT_NOS': nos, 'STATUS_STR': AUDIT_STATUS_STR}
        try:
            r = self.controller.session.get(URL_PRINT, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其它出库审核-打印] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"打印数据加载失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "获取打印数据失败"
            self.controller.after(0, lambda: messagebox.showerror("获取失败", str(msg)))
            return
        flat = data.get("data") if isinstance(data.get("data"), list) else []
        groups = []
        for row in flat:
            grp = next((g for g in groups if g['header'].get('OTHER_OUT_NO') == row.get('OTHER_OUT_NO')), None)
            if not grp:
                grp = {'header': row, 'items': []}
                groups.append(grp)
            grp['items'].append(row)
        for g in groups:
            tn = 0.0
            ta = 0.0
            for it in g['items']:
                try:
                    num = float(it.get('NUM') or 0)
                except (TypeError, ValueError):
                    num = 0.0
                tn += num
                ta += num * self._print_price(it)
            g['totalNum'] = tn
            g['totalAmount'] = round(ta, 2)
        if not groups:
            self.controller.after(0, lambda: messagebox.showinfo("提示", "未获取到打印数据"))
            return
        self.controller.after(0, lambda: self._show_print_window(groups))

    @staticmethod
    def _print_price(it):
        try:
            return float(it.get('COST_PRICE') or 0)
        except (TypeError, ValueError):
            return 0.0

    def _show_print_window(self, groups):
        win = tk.Toplevel(self)
        win.title("其它出库单打印预览")
        win.geometry("900x720")
        win.transient(self)
        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text=f"打印预览（已选择 {len(groups)} 个单据）", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        body = tk.Text(win, wrap=tk.NONE, font=("微软雅黑", 9), bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body.tag_configure("title", font=("微软雅黑", 15, "bold"))
        body.tag_configure("h", font=("微软雅黑", 9, "bold"))
        for g in groups:
            h = g['header']
            body.insert(tk.END, "\n其它出库单\n", "title")
            body.insert(tk.END, f"出库仓库：{h.get('WAREHOUSE_NAME') or ''}    "
                                f"业务类型：{self.bus_type_label(h.get('BUS_TYPE'))}    "
                                f"供应商：{h.get('SUPPLIER_NAME') or ''}\n")
            body.insert(tk.END, f"开单人：{h.get('CREATED_BY_NAME') or ''}    "
                                f"单据号：{h.get('OTHER_OUT_NO') or ''}\n")
            body.insert(tk.END, f"摘要：{h.get('REMARK') or ''}\n")
            body.insert(tk.END, "品牌 | 产品编码 | 产品名称 | 批次单价 | 出库库位 | 出库数量 | 出库金额\n", "h")
            for it in g['items']:
                amt = float(it.get('NUM') or 0) * self._print_price(it)
                body.insert(tk.END, f"{self.short_brand(it.get('BRAND_NAME'))} | {it.get('PART_NO') or ''} | "
                                    f"{it.get('PART_NAME') or ''} | {self.format_num(self._print_price(it))} | "
                                    f"{it.get('REMOVAL_LOCATION_NAME') or ''} | {it.get('NUM') or 0} | {amt:.2f}\n")
            body.insert(tk.END, f"合计数量：{g['totalNum']:g}    合计金额：{g['totalAmount']:.2f}\n")
            body.insert(tk.END, "─" * 110 + "\n")
        body.configure(state=tk.DISABLED)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="打 印", command=lambda: self.print_via_clodop(groups, win),
                  bg="#fa8c16", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def print_via_clodop(self, groups, win):
        """复用 CLodop WebSocket 协议（对齐 other_inbound_review / picking_shipping）"""
        try:
            import websocket
        except ImportError:
            messagebox.showerror("打印失败", "未安装 websocket 模块，无法连接 CLodop")
            return
        try:
            html_parts = [self._build_single_html(g) for g in groups]
            now = date.today()
            task_id = f"OO{now.month:02d}{now.day:02d}_1"
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
                    f"top={delim}left={delim}width={delim}height={delim}"
                    f"printtask=其它出库单打印{delim}"
                    f"printerindex={printer_name}{delim}"
                    f"orient=1{delim}pagewidth=0{delim}pageheight=0{delim}"
                    f"pagename=A4{delim}printcopies=1{delim}itemcount=1{delim}"
                    f"1_type=4{delim}1_top=30{delim}1_left=3mm{delim}"
                    f"1_width=100%{delim}1_height=100%{delim}"
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
            messagebox.showerror("打印失败",
                                 f"CLodop WebSocket打印失败: {e}\n\n请确保 CLodop 服务已启动（localhost:8000）")

    def _build_single_html(self, g):
        h = g['header']
        rows = ""
        for it in g['items']:
            amt = float(it.get('NUM') or 0) * self._print_price(it)
            rows += (
                f"<tr><td>{self.short_brand(it.get('BRAND_NAME'))}</td>"
                f"<td style='text-align:center'>{it.get('PART_NO') or ''}</td>"
                f"<td style='text-align:left'>{it.get('PART_NAME') or ''}</td>"
                f"<td>{self.format_num(self._print_price(it))}</td>"
                f"<td>{it.get('REMOVAL_LOCATION_NAME') or ''}</td>"
                f"<td>{it.get('NUM') or 0}</td>"
                f"<td>{amt:.2f}</td></tr>"
            )
        return (
            "<style>body{margin:0;padding:0}</style>"
            "<div class='print-page' style='width:97%'>"
            "<div style='text-align:center;font-size:20px;font-weight:700'>其它出库单</div>"
            "<div style='font-size:13px'>"
            f"<div>出库仓库：{h.get('WAREHOUSE_NAME') or ''}　　业务类型：{self.bus_type_label(h.get('BUS_TYPE'))}"
            f"　　供应商：{h.get('SUPPLIER_NAME') or ''}</div>"
            f"<div>开单人：{h.get('CREATED_BY_NAME') or ''}　　单据号：{h.get('OTHER_OUT_NO') or ''}</div>"
            f"<div>摘要：{h.get('REMARK') or ''}</div>"
            "</div>"
            "<table border='1' cellspacing='0' style='width:98%;font-size:12px;border-collapse:collapse;text-align:center'>"
            "<thead><tr><th>品牌</th><th>产品编码</th><th>产品名称</th><th>批次单价</th>"
            "<th>出库库位</th><th>出库数量</th><th>出库金额</th></tr></thead>"
            "<tbody>" + rows + "</tbody>"
            f"<tfoot><tr><td colspan='4'/><td colspan='2' style='font-weight:bold'>合计数量：{g['totalNum']:g}</td>"
            f"<td style='font-weight:bold'>合计金额：{g['totalAmount']:.2f}</td></tr></tfoot>"
            "</table></div>"
        )

    # ============================================================ 明细导出
    def export_excel(self):
        """GET exportData 下载 xls（HAR 实证：查询条件 + searchLoading=false + OTHER_OUT_NOS）"""
        path = filedialog.asksaveasfilename(
            title="导出其它出库明细",
            initialfile="其它出库明细_%s.xls" % date.today().strftime('%Y%m%d'),
            defaultextension=".xls",
            filetypes=[("Excel 97-2003", "*.xls"), ("所有文件", "*.*")])
        if not path:
            return
        params = self.build_query_params()
        params['searchLoading'] = 'false'
        params.pop('STATUS_STR', None)     # Web exportFn 不带 STATUS_STR
        params.pop('pageNum', None)
        params.pop('limit', None)
        rows = self._selected_rows()
        if rows:
            params['OTHER_OUT_NOS'] = ",".join("'%s'" % r['OTHER_OUT_NO']
                                               for r in rows if r.get('OTHER_OUT_NO'))
        threading.Thread(target=self._export_thread, args=(params, path), daemon=True).start()

    def _export_thread(self, params, path):
        try:
            r = self.controller.session.get(URL_EXPORT, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            ctype = (r.headers.get('Content-Type') or '').lower()
            if 'json' in ctype:
                data = json.loads(r.text)
                if not (data.get("resultCode") == 200 or data.get("success")):
                    msg = data.get("errMsg") or data.get("msg") or "导出失败"
                    self.controller.after(0, lambda: messagebox.showerror("导出失败", str(msg)))
                    return
            with open(path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"[其它出库审核-导出] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"导出失败: {e}"))
            return
        self.controller.after(0, lambda: messagebox.showinfo("完成", f"明细已导出到：\n{path}"))

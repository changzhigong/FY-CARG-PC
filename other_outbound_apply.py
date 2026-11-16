# -*- coding: utf-8 -*-
"""报损出库申请（其他出入库管理模块 菜单 2/2）

对齐 fycarg-pda 安卓端：
- src/views/OtherOutboundApply.vue（1865 行）
- src/service/otherOutbound.js
- src/config/otherOutbound.js
- 打印模板 utils/lodopPrint.js generateOtherOutboundHtml / printOtherOutboundViaUdp

接口清单（dmscloud.part/otherOutboundWarehouse 为主，dmscloud.basedata 为辅）：
- 列表     GET  /dmscloud.part/otherOutboundWarehouse/page
            ?OTHER_OUT_NO=&BUS_TYPE=12521001&STATUS=&partCode=&partName=&BRAND_ID=
             &WAREHOUSE_CODE=&CREATED_AT_FROM=&CREATED_AT_TO=&pageNum=1&limit=500
- 主单明细 GET  /dmscloud.part/otherOutboundWarehouse/queryById?id=
- 明细行   GET  /dmscloud.part/otherOutboundWarehouse/queryById/items?id=
- 配件搜索 GET  /dmscloud.part/otherOutboundWarehouse/selectParts
            (PART_NO/PART_NAME/STORAGE_NAME/WAREHOUSE_ID/CORRELATION_ORDER_NO/BUS_TYPE)
- 保存新建 POST /dmscloud.part/otherOutboundWarehouse/add    （无 OTHER_OUT_NO）
- 保存编辑 POST /dmscloud.part/otherOutboundWarehouse/edit   （有 OTHER_OUT_NO）
- 提交     POST /dmscloud.part/otherOutboundWarehouse/submit （需 ID + OTHER_OUT_NO）
- 打印数据 GET  /dmscloud.part/otherOutboundWarehouse/getPrintList?OTHER_OUT_NOS='单1','单2'&BUS_TYPE=12521001
- 操作日志 GET  /dmscloud.part/operateLogs/page?BILL_ID=&BILL_TYPE=12041005&limit=5&pageNum=1&isShowLogs=true
- 责任人   GET  /dcscloud.basedata/basedata/employees/employees/internalUser（复用 internalUse）
- 字典     GET  /dmscloud.basedata/dicts（1251 状态 / 9092 分类 / 9969 报损原因，失败静默用兜底）
- 附件上传 POST /dmscloud.basedata/file (multipart，字段 dmsFile) → data.fileUploadId
- 附件配置 GET  /dmscloud.basedata/file/billFiles/10422113/{billId}
- 附件下载 GET  /dmscloud.basedata/file/billFilesReview/10422113/{fileKey}（blob）

关键业务语义（对齐安卓 / HAR 实测）：
1. 状态字典 1251 组：待提交 12511001 / 待仓库处理 12511002 / 待审核 12511005 / 审核驳回 12511006 /
   待出库 12511007 / 部分出库 12511010 / 已出库 12511008 / 已作废 12511009。
   可编辑/可提交 = [12511001, 12511006]（待提交、审核驳回）。无独立草稿态（保存即待提交）。
2. 状态快捷筛选排除 待仓库处理/待出库/部分出库（对齐安卓 OTHER_OUT_STATUS_FILTERS）。
3. ⚠️ 与内部领用不同：本页【没有作废按钮】——安卓 service 仅暴露 add/edit/submit 三个写接口，
   移动端申请页亦不渲染作废（已作废状态仅由 PC 端审核/仓库侧流转产生）。故桌面端不提供作废操作。
4. 保存/提交报文（buildBasePayload 结构，HAR 实证）：
   - 恒带 BRAND_ID=1 / BUS_TYPE=12521001 / DEALER_CODE='FY' / ORGANIZATION_ID（仓库→部门 id，
     复用 internalUse USE_DEPT_MAP）/ WAREHOUSE_CODE+ID+NAME / STATUS（编辑回带原状态 12511006，
     新建默认 12511001）/ NO_TAX_AMOUNT（= Σ COST_PRICE×NUM，round 2）/ itemList / delItemList=[]。
   - add 不带 ID/OTHER_OUT_NO；edit 回带 ID/OTHER_OUT_NO/RECORD_VERSION。
   - submit 需 ID + OTHER_OUT_NO（新建无 id 时先 add 取 id 再 submit，对齐安卓 submitBill）。
   - 明细行固定字段：PART_*/BRAND_*/CATEGORY_TWO/COST_PRICE/NUM/DAMAGE_REASON/
     REMOVAL_LOCATION(+NAME)/AVAILABLE_STOCK_QUANTITY/STORAGE_*/WAREHOUSE_ID/DEALER_CODE/
     SUPPLIER_NAME='福耀'/ORGANIZATION_ID/DR:0/UNIT·MPQ·BATCH_NUMBER·RETURN_UNIT_PRICE·REMARK:null/
     loList/ID(''=新增)/PID(主单id)/OTHER_OUT_NO/RECORD_VERSION/NO_TAX_AMOUNT(行金额)。
   - 保存前校验：责任人必填、至少一条配件、每条须选移出库位与报损原因（对齐安卓 saveDraft/submitBill）。
5. 附件（10422113）：已存附件由 billFiles 配置接口单独拉取（不随 queryById 返回）；
   新增附件先 POST /dmscloud.basedata/file 上传（dmsFile 字段）取 fileUploadId。
   add/edit 报文 fileList = bootstrap-fileinput 草稿结构（新附件 optionType='add'/canDelete=10041001，
   已存 canDelete=10041002）；submit 报文 fileList = submit 结构（canDelete=10041002 统一）。
6. 责任人与制单人身份：Python 端登录仅存 cookies、无 employeeName/employeeId（同报销/内部领用）。
   责任人由用户从内部员工下拉显式选择（employeeId 语义即 RESPONSIBLE_PERSON_ID）；
   CREATED_BY/CREATED_BY_NAME/UPDATED_BY 无身份可填——编辑态沿用主单原值回带，新建态置 ''（后端按登录态生成）。
7. 打印预览：getPrintList 返回平铺明细，按 OTHER_OUT_NO 分组，合计数量 ΣNUM / 合计金额 Σ(NUM×COST_PRICE)；
   打印走 CLodop WebSocket（任务名「报损出库单打印」，复用 picking_shipping 协议）。
"""

import json
import os
import re
import threading
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

# 部门映射：仓库名 → ORGANIZATION_ID（安卓 otherOutbound.js 从 internalUse.js 再导出 USE_DEPT_MAP）
from internal_use_manage import USE_DEPT_MAP

# ---------------------------------------------------------------- 常量 / 接口
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}
BASE = 'https://xb.fy-carg.com'
PART = '/dmscloud.part/otherOutboundWarehouse'

URL_QUERY = BASE + PART + '/page'
URL_DETAIL = BASE + PART + '/queryById'
URL_ITEMS = BASE + PART + '/queryById/items'
URL_PARTS = BASE + PART + '/selectParts'
URL_ADD = BASE + PART + '/add'
URL_EDIT = BASE + PART + '/edit'
URL_SUBMIT = BASE + PART + '/submit'
URL_PRINT = BASE + PART + '/getPrintList'
URL_LOGS = BASE + '/dmscloud.part/operateLogs/page'
URL_DICT = BASE + '/dmscloud.basedata/dicts'
URL_USERS = BASE + '/dcscloud.basedata/basedata/employees/employees/internalUser'
# 附件
URL_FILE_UPLOAD = BASE + '/dmscloud.basedata/file'
URL_ATTACH_CFG = BASE + '/dmscloud.basedata/file/billFiles'
URL_ATTACH_REVIEW = BASE + '/dmscloud.basedata/file/billFilesReview'
URL_ATTACH_DOWNLOAD = BASE + '/dmscloud.basedata/file/billFilesDownload'

QUERY_LIMIT = 500
PAGE_SIZE = 10

# 业务类型（固定 报损出库，1252 组）
BUS_TYPE = 12521001
# 附件单据类型 / 操作日志单据类型（HAR 实测）
ATTACH_BILL_TYPE = 10422113
LOG_BILL_TYPE = 12041005
LOG_PAGE_SIZE = 5

# 默认值（HAR 实测）
DEALER_CODE = 'FY'
DEFAULT_BRAND_ID = 1
DEFAULT_SUPPLIER_NAME = '福耀'
DRAFT_STATUS = 12511001

# 状态字典 1251 组（离线兜底；运行期可被 dicts 1251 覆盖显示）
OUT_STATUS_MAP = {
    12511001: {'label': '待提交', 'editable': True},
    12511002: {'label': '待仓库处理', 'editable': False},
    12511005: {'label': '待审核', 'editable': False},
    12511006: {'label': '审核驳回', 'editable': True},
    12511007: {'label': '待出库', 'editable': False},
    12511010: {'label': '部分出库', 'editable': False},
    12511008: {'label': '已出库', 'editable': False},
    12511009: {'label': '已作废', 'editable': False},
}
OUT_EDITABLE_STATUS = {12511001, 12511006}

# 状态快捷筛选（申请页：排除 待仓库处理/待出库/部分出库）
OUT_STATUS_FILTERS = [
    ('全部', ''), ('待提交', '12511001'), ('待审核', '12511005'),
    ('审核驳回', '12511006'), ('已出库', '12511008'), ('已作废', '12511009'),
]

# 字典组与离线兜底
DICT_TYPES = ['1251', '9092', '9969']
DICT_FALLBACK = {
    '1251': {
        '12511001': '待提交', '12511002': '待仓库处理', '12511005': '待审核',
        '12511006': '审核驳回', '12511007': '待出库', '12511010': '部分出库',
        '12511008': '已出库', '12511009': '已作废',
    },
    '9092': {
        '90921001': '前挡', '90921002': '后挡', '90921003': '边窗',
        '90921004': '其它', '90921005': '天窗', '90921006': '其他',
    },
    '9969': {},  # 报损原因：无离线兜底，完全依赖 dicts 实时接口
}

# 列表列
COLUMNS = ["序号", "报损单号", "状态", "责任人", "出库仓", "备注", "创建时间"]
COLUMN_WIDTHS = [50, 170, 90, 110, 110, 160, 150]

# 附件工具
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
MIME_MAP = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
    'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
    'pdf': 'application/pdf', 'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'txt': 'text/plain', 'zip': 'application/zip', 'rar': 'application/x-rar-compressed',
}


def guess_mime(name):
    ext = (name or '').rsplit('.', 1)[-1].lower() if '.' in (name or '') else ''
    return MIME_MAP.get(ext, 'application/octet-stream')


def is_image_file(name):
    ext = (name or '').rsplit('.', 1)[-1].lower() if '.' in (name or '') else ''
    return ('.' + ext) in IMAGE_EXTS


class OtherOutboundApplyPage(BasePage):
    """报损出库申请页面（查询 / 明细 / 新建编辑 / 保存提交 / 附件 / 打印预览）"""

    def __init__(self, parent, controller):
        self.all_rows = []
        self.filtered_rows = []
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.queried = False
        self.loading = False

        # 筛选条件
        self.filter_status = tk.StringVar(value='')
        self.filter_no = tk.StringVar(value='')
        self.filter_resp = tk.StringVar(value='')

        # 仓库 / 部门解析
        self.wh_name = ''
        self.wh_code = ''
        self.wh_id = None
        self.org_id = None

        # 责任人
        self.internal_users = []
        self.user_names = []
        self.user_map = {}   # name -> {id, phone, orgId, orgName}

        # 字典（1251/9092/9969 实时覆盖）
        self.dict_maps = dict(DICT_FALLBACK)

        # 编辑态
        self.edit_id = ''
        self.edit_mode = 'new'
        self.edit_raw = None          # 主单权威对象（queryById）
        self.edit_other_out_no = ''
        self.edit_record_version = ''
        self.edit_status = ''
        self.edit_wh_name = ''
        self.edit_wh_code = ''
        self.edit_wh_id = None
        self.edit_org_id = None
        self.edit_resp_id = ''
        self.edit_resp_name = ''
        self.edit_remark = ''
        self.edit_items = []          # 报损明细（新增行无 ID）
        self.edit_attachments = []    # {name, key, size, isImage, isNew, preview}
        self.edit_win = None

        # 打印
        self.print_groups = []

        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        main = tk.Frame(self.content_frame, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main)
        self.setup_count_bar(main)
        self.setup_data_table(main)
        self.setup_pagination_controls(main)
        self.setup_action_buttons(main)

        # 初始化数据（异步，失败静默）
        self._load_dict()
        self.load_users()

    def setup_filter_panel(self, parent):
        frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                              font=("微软雅黑", 10, "bold"))
        frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=(5, 2))
        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)
        self.warehouse_cb.bind("<<ComboboxSelected>>", lambda e: self.resolve_warehouse())
        self.resolve_warehouse()
        tk.Label(row1, text="（用于解析出库仓/组织）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=5)

        # 状态快捷标签
        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.status_buttons = {}
        for label, value in OUT_STATUS_FILTERS:
            btn = tk.Button(row2, text=label, width=9, relief=tk.FLAT,
                            bg="#e1e1e1", fg="#323233",
                            command=lambda v=value: self.toggle_status(v))
            btn.pack(side=tk.LEFT, padx=2)
            self.status_buttons[value] = btn
        self._update_status_buttons()

        row3 = tk.Frame(frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=2)
        tk.Label(row3, text="创建日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT, padx=2)
        tk.Label(row3, text="至", bg="#f0f0f0").pack(side=tk.LEFT)
        self.end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT, padx=2)

        row4 = tk.Frame(frame, bg="#f0f0f0")
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="报损单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row4, textvariable=self.filter_no, width=16).pack(side=tk.LEFT, padx=2)
        tk.Label(row4, text="责任人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(row4, textvariable=self.filter_resp, width=12).pack(side=tk.LEFT, padx=2)

        btn_style = {"bg": "#fa8c16", "fg": "white", "padx": 14, "pady": 4,
                     "bd": 0, "activebackground": "#d46b08"}
        tk.Button(row4, text="查询报损单", command=self.query, **btn_style).pack(side=tk.LEFT, padx=12)
        tk.Button(row4, text="重置", command=self.reset_form,
                  bg="#e1e1e1", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="报损出库单列表", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings",
                                 height=13, selectmode="extended")
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "center" if col in ("序号",) else "w"
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

        tooltip_manager.attach_tooltip(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.open_detail())

    def setup_pagination_controls(self, parent):
        pager = tk.Frame(parent, bg="#f0f0f0")
        pager.pack(fill=tk.X, pady=5)
        self.page_info_var = tk.StringVar(value="第 1/1 页")
        tk.Label(pager, textvariable=self.page_info_var, bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}
        tk.Button(pager, text="首页", command=lambda: self.go_page(1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pager, text="上一页", command=lambda: self.go_page(self.page_num - 1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pager, text="下一页", command=lambda: self.go_page(self.page_num + 1), **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(pager, text="尾页", command=lambda: self.go_page(self.total_pages), **btn_style).pack(side=tk.LEFT, padx=2)

    def setup_action_buttons(self, parent):
        bar = tk.Frame(parent, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=(0, 5))
        tk.Button(bar, text="新建报损单", command=lambda: self.open_edit(None),
                  bg="#fa8c16", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="查看明细", command=self.open_detail,
                  bg="#1989fa", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="编辑", command=self.edit_selected,
                  bg="#ff976a", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="清除选择", command=self.clear_selection,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14, pady=4).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="打印预览", command=self.open_print_preview,
                  bg="#07c160", fg="white", padx=14, pady=4, bd=0).pack(side=tk.RIGHT, padx=5)

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def def_date(kind):
        today = date.today()
        if kind == 'begin':
            return date(today.year, today.month, 1)
        return today

    @staticmethod
    def format_money(val):
        try:
            n = float(val or 0)
        except (TypeError, ValueError):
            n = 0.0
        return '¥{:,.2f}'.format(n)

    @staticmethod
    def format_date(s):
        if not s:
            return '-'
        s = str(s).strip().replace('T', ' ')
        return s[:16] if len(s) >= 16 else s

    @staticmethod
    def today_str():
        return date.today().strftime('%Y-%m-%d')

    @staticmethod
    def now_str():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def short_brand(name):
        return (name or '').replace('福耀玻璃', '福耀')

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    # 字典解码：实时 dicts > 离线兜底 > 原码
    def _decode(self, tp, code, fallback=None):
        if code is None or code == '':
            return ''
        live = (self.dict_maps or {}).get(tp) or {}
        if live.get(str(code)):
            return live[str(code)]
        fb = (DICT_FALLBACK.get(tp) or {}) if fallback is None else (fallback or {})
        if fb.get(str(code)):
            return fb[str(code)]
        return str(code)

    def category_label(self, code):
        return self._decode('9092', code) or '-'

    def reason_label(self, code):
        return self._decode('9969', code) or '-'

    # 状态（显示用字典优先，可编辑性用静态映射）
    def out_status_label(self, code):
        if code is None or code == '':
            return '-'
        live = (self.dict_maps or {}).get('1251') or {}
        if live.get(str(code)):
            return live[str(code)]
        return OUT_STATUS_MAP.get(int(code), {}).get('label', str(code))

    @staticmethod
    def out_status_editable(code):
        try:
            return int(code) in OUT_EDITABLE_STATUS
        except (TypeError, ValueError):
            return False

    def _selected_rows(self):
        sel = self.tree.selection()
        if not sel:
            return []
        out = []
        for iid in sel:
            idx = self.tree.index(iid)
            if 0 <= idx < len(self.page_rows):
                out.append(self.page_rows[idx])
        return out

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    def resolve_warehouse(self):
        name = self.warehouse_var.get()
        self.wh_name = name
        self.wh_code = get_storage_code(name) if name else ''
        self.wh_id = self.controller.options.get(name) if name else None
        self.org_id = USE_DEPT_MAP.get(name) if name else None

    # ---------------------------------------------------- 初始化数据（异步）
    def _load_dict(self):
        threading.Thread(target=self._dict_thread, daemon=True).start()

    def _dict_thread(self):
        try:
            r = self.controller.session.get(URL_DICT, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-字典] 加载失败(用兜底): {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        dictobj = ((data.get("data") or {}).get("dict") or {})
        maps = dict(DICT_FALLBACK)
        for tp in DICT_TYPES:
            m = dict(DICT_FALLBACK.get(tp) or {})
            arr = dictobj.get(tp) or []
            if isinstance(arr, list):
                for x in arr:
                    if isinstance(x, dict) and x.get('code_id') is not None:
                        m[str(x['code_id'])] = x.get('code_cn_desc') or ''
            maps[tp] = m
        self.controller.after(0, lambda: setattr(self, 'dict_maps', maps))

    def load_users(self):
        threading.Thread(target=self._user_thread, daemon=True).start()

    def _user_thread(self):
        try:
            r = self.controller.session.get(URL_USERS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-责任人] 加载失败: {e}")
            return
        arr = (data.get('data') or []) if isinstance(data, dict) else []
        items = []
        for u in arr if isinstance(arr, list) else []:
            if not isinstance(u, dict):
                continue
            name = u.get('EMPLOYEE_NAME') or u.get('name') or ''
            if not name:
                continue
            items.append({
                'name': name,
                'id': str(u.get('EMPLOYEE_ID') or u.get('EMP_ID') or u.get('id') or ''),
                'phone': u.get('PHONE') or u.get('phone') or '',
                'orgId': u.get('ORGANIZATION_ID') or '',
                'orgName': u.get('ORG_NAME') or '',
            })
        self.controller.after(0, lambda: self._apply_users(items))

    def _apply_users(self, items):
        self.internal_users = items
        self.user_names = [u['name'] for u in items]
        self.user_map = {u['name']: u for u in items}
        if hasattr(self, 'user_cb') and self.user_cb.winfo_exists():
            self.user_cb.config(values=self.user_names)

    # ------------------------------------------------------------------ 筛选
    def toggle_status(self, value):
        self.filter_status.set('' if self.filter_status.get() == value else value)
        self._update_status_buttons()
        self._apply_filters()

    def _update_status_buttons(self):
        cur = self.filter_status.get()
        for value, btn in self.status_buttons.items():
            if value == cur:
                btn.config(bg="#fa8c16", fg="white")
            else:
                btn.config(bg="#e1e1e1", fg="#323233")

    def _apply_filters(self):
        rows = self.all_rows
        status = self.filter_status.get()
        if status:
            codes = [s.strip() for s in status.split(',') if s.strip()]
            rows = [r for r in rows if str(r.get('STATUS')) in codes]
        no = self.filter_no.get().strip().lower()
        man = self.filter_resp.get().strip().lower()
        if no or man:
            kept = []
            for r in rows:
                bill = str(r.get('OTHER_OUT_NO') or '').lower()
                m = str(r.get('RESPONSIBLE_PERSON') or '').lower()
                if no and no not in bill:
                    continue
                if man and man not in m:
                    continue
                kept.append(r)
            rows = kept
        self.filtered_rows = rows
        self.page_num = 1
        self._render_rows()

    def reset_form(self):
        self.filter_status.set('')
        self._update_status_buttons()
        self.filter_no.set('')
        self.filter_resp.set('')
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.all_rows = []
        self.filtered_rows = []
        self.queried = False
        self.page_num = 1
        self._render_rows()
        self.count_var.set("")

    # ------------------------------------------------------------------ 查询
    def build_query_params(self):
        return {
            "OTHER_OUT_NO": self.filter_no.get() or '',
            "BUS_TYPE": BUS_TYPE,
            "STATUS": self.filter_status.get() or '',
            "partCode": '',
            "partName": '',
            "BRAND_ID": '',
            "WAREHOUSE_CODE": self.wh_code,
            "CREATED_AT_FROM": (self.start_cal.get() + ' 00:00:00') if self.start_cal.get() else '',
            "CREATED_AT_TO": (self.end_cal.get() + ' 23:59:59') if self.end_cal.get() else '',
            "pageNum": 1,
            "limit": QUERY_LIMIT,
        }

    def query(self):
        if self.loading:
            return
        if not self.wh_code:
            messagebox.showwarning("提示", "请先选择仓库")
            return
        params = self.build_query_params()
        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[报损出库申请] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库申请] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        finally:
            self.loading = False

        if not (data.get("resultCode") == 200 or data.get("code") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or data.get("message") or "查询失败"
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return

        resp = data.get("data") or {}
        rows = resp.get("rows") if isinstance(resp, dict) else None
        if not isinstance(rows, list):
            rows = resp if isinstance(resp, list) else []
        self.controller.after(0, lambda: self._apply_query_result(rows))

    def _apply_query_result(self, rows):
        self.all_rows = rows
        self.queried = True
        self._apply_filters()
        if not rows:
            messagebox.showinfo("查询结果", "未查询到报损单")

    # ------------------------------------------------------------------ 渲染
    def _render_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        start = (self.page_num - 1) * self.page_size
        page = self.filtered_rows[start:start + self.page_size]
        self.page_rows = page
        for idx, row in enumerate(page):
            values = (
                start + idx + 1,
                row.get('OTHER_OUT_NO') or '-',
                self.out_status_label(row.get('STATUS')),
                row.get('RESPONSIBLE_PERSON') or '-',
                row.get('WAREHOUSE_NAME') or '-',
                row.get('REMARK') or '-',
                self.format_date(row.get('CREATED_AT')),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        total = len(self.filtered_rows)
        self.count_var.set(f"共 {total} 条报损单")
        self.update_page_info()

    @property
    def total_pages(self):
        return max(1, (len(self.filtered_rows) + self.page_size - 1) // self.page_size)

    @property
    def page_rows(self):
        return getattr(self, '_page_rows', [])

    @page_rows.setter
    def page_rows(self, value):
        self._page_rows = value

    def update_page_info(self):
        self.page_info_var.set(
            f"第 {self.page_num}/{self.total_pages} 页 (共 {len(self.filtered_rows)} 条)")

    def go_page(self, page):
        try:
            page = int(page)
        except (TypeError, ValueError):
            return
        page = min(max(1, page), self.total_pages)
        if page == self.page_num:
            return
        self.page_num = page
        self._render_rows()

    # ------------------------------------------------------------------ 明细
    def open_detail(self):
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("提示", "请先选择一条报损单")
            return
        row = rows[0]
        bill_id = row.get('ID')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法查看明细")
            return
        self.count_var.set("加载明细中...")
        threading.Thread(target=self._detail_thread, args=(bill_id, row), daemon=True).start()

    def _fetch_attach_cfg(self, bill_id):
        """拉取单据附件配置（billFiles）→ (attachments, previews) 失败返回空"""
        try:
            url = '{}/{}/{}'.format(URL_ATTACH_CFG, ATTACH_BILL_TYPE, bill_id)
            r = self.controller.session.get(url, headers=HEADERS)
            if not self._check_response(r):
                return [], []
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-附件配置] 失败: {e}")
            return [], []
        d = data.get('data') or {}
        previews = d.get('initialPreview') if isinstance(d.get('initialPreview'), list) else []
        cfg = d.get('initialPreviewConfig') if isinstance(d.get('initialPreviewConfig'), list) else []
        attachments = []
        for i, c in enumerate(cfg):
            if not isinstance(c, dict):
                continue
            key = str(c.get('key') or '')
            if not key:
                continue
            name = c.get('caption') or ('附件' + key)
            attachments.append({
                'name': name,
                'key': key,
                'size': int(c.get('size') or 0),
                'isImage': is_image_file(name),
                'isNew': False,
                'preview': previews[i] if i < len(previews) else '',
            })
        return attachments, previews

    def _detail_thread(self, bill_id, row):
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                items = (json.loads(r.text).get('data') or [])
                items = items if isinstance(items, list) else []
        except Exception as e:
            print(f"[报损出库-明细] 异常: {e}")
        attachments, _ = self._fetch_attach_cfg(bill_id)
        logs = self._fetch_logs(bill_id)
        p = {
            'id': bill_id,
            'billNo': row.get('OTHER_OUT_NO') or '-',
            'statusCode': row.get('STATUS') or '',
            'respName': row.get('RESPONSIBLE_PERSON') or '-',
            'warehouseName': row.get('WAREHOUSE_NAME') or '-',
            'remark': row.get('REMARK') or '无',
            'items': items,
            'attachments': attachments,
            'logs': logs,
            'row': row,
        }
        self.controller.after(0, lambda: self._show_detail_window(p))

    def _fetch_logs(self, bill_id):
        try:
            r = self.controller.session.get(URL_LOGS, headers=HEADERS, params={
                'BILL_ID': bill_id, 'BILL_TYPE': LOG_BILL_TYPE,
                'limit': LOG_PAGE_SIZE, 'pageNum': 1, 'isShowLogs': True})
            if not self._check_response(r):
                return []
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-日志] 异常: {e}")
            return []
        rows = ((data.get('data') or {}).get('rows') if isinstance(data.get('data'), dict) else None)
        return rows if isinstance(rows, list) else []

    def _show_detail_window(self, p):
        win = tk.Toplevel(self)
        win.title(f"报损出库单明细 - {p['billNo']}")
        win.geometry("760x700")
        win.transient(self)

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="报损出库单明细", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text=f"状态：{self.out_status_label(p['statusCode'])}",
                 bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        info = tk.Frame(win, bg="#ffffff")
        info.pack(fill=tk.X, padx=10, pady=5)
        for key, val in (("单号", p['billNo']),
                         ("责任人", p['respName']),
                         ("出库仓", p['warehouseName']),
                         ("备注", p['remark'])):
            line = tk.Frame(info, bg="#ffffff")
            line.pack(fill=tk.X, pady=2)
            tk.Label(line, text=key + "：", bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=9, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#ffffff", font=("微软雅黑", 10),
                     anchor="w", wraplength=580, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 报损明细
        tk.Label(win, text=f"报损明细（{len(p['items'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dcols = ["序号", "配件", "数量", "分类", "报损原因", "移出库位", "品牌", "单价"]
        dtree = ttk.Treeview(dframe, columns=dcols, show="headings", height=6)
        dwidths = [40, 210, 60, 70, 120, 100, 90, 90]
        for i, col in enumerate(dcols):
            dtree.heading(col, text=col)
            dtree.column(col, width=dwidths[i],
                         anchor="e" if col in ("数量", "单价") else "w")
        for idx, d in enumerate(p['items']):
            dtree.insert("", "end", values=(
                idx + 1,
                d.get('PART_NAME') or d.get('PART_NO') or '-',
                d.get('NUM') or 0,
                self.category_label(d.get('CATEGORY_TWO')),
                self.reason_label(d.get('DAMAGE_REASON')),
                d.get('REMOVAL_LOCATION_NAME') or '-',
                d.get('BRAND_NAME') or '-',
                self.format_money(d.get('COST_PRICE'))))
        dsb = ttk.Scrollbar(dframe, orient="vertical", command=dtree.yview)
        dtree.configure(yscrollcommand=dsb.set)
        dtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 附件（有则逐行可下载）
        tk.Label(win, text=f"附件（{len(p['attachments'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
        aframe = tk.Frame(win, bg="#ffffff")
        aframe.pack(fill=tk.X, padx=10)
        if not p['attachments']:
            tk.Label(aframe, text="无附件", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for a in p['attachments']:
            line = tk.Frame(aframe, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            size = a.get('size') or 0
            tk.Label(line, text=a['name'] + (f"（{self._fmt_size(size)}）" if size else ""),
                     bg="#ffffff", anchor="w").pack(side=tk.LEFT)
            tk.Button(line, text="下载", bg="#1989fa", fg="white", bd=0, width=6,
                      command=lambda at=a: self.download_attachment(at)).pack(side=tk.RIGHT)

        # 操作日志（默认折叠）
        self._log_expanded = False
        logs_frame = tk.Frame(win, bg="#ffffff")
        logs_btn = tk.Button(win, text=f"操作日志（{len(p['logs'])}） ▼", bg="#f0f0f0", relief=tk.FLAT,
                             anchor="w", command=lambda: self._toggle_logs(logs_frame, logs_btn, p['logs']))
        logs_btn.pack(fill=tk.X, padx=10, pady=(8, 0))
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        logs_frame.pack_forget()

        # 底部按钮
        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        editable = self.out_status_editable(p['statusCode'])
        row = p.get('row') or {}
        if editable:
            tk.Button(bar, text="编辑", bg="#fa8c16", fg="white", padx=18, pady=4, bd=0,
                      command=lambda: [win.destroy(), self.open_edit(oo_row_source(row))]).pack(side=tk.LEFT, padx=10)
        else:
            tk.Label(bar, text="当前状态不可编辑", bg="#f0f0f0", fg="#969799").pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=4,
                  command=win.destroy).pack(side=tk.RIGHT, padx=10)

        self.count_var.set(f"共 {len(self.filtered_rows)} 条报损单")

    def _fmt_size(self, size):
        n = int(size or 0)
        if n <= 0:
            return ''
        if n < 1024:
            return str(n) + 'B'
        if n < 1024 * 1024:
            return str(round(n / 1024)) + 'KB'
        return ('%.1fMB' % (n / 1024 / 1024))

    def _toggle_logs(self, frame, btn, logs):
        if self._log_expanded:
            frame.pack_forget()
            btn.config(text=f"操作日志（{len(logs)}） ▼")
            self._log_expanded = False
            return
        for w in frame.winfo_children():
            w.destroy()
        if not logs:
            tk.Label(frame, text="暂无操作日志", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for log in logs:
            flow = ''
            if log.get('BEFORE_VALUE') or log.get('AFTER_VALUE'):
                flow = '[{} → {}] '.format(log.get('BEFORE_VALUE'), log.get('AFTER_VALUE'))
            text = '{}{}{}{}'.format(
                log.get('OPERATOR_NAME') or '-', ' ',
                self.format_date(log.get('OPERATE_DATE')),
                '（%s）' % log['REMARK'] if log.get('REMARK') else '')
            tk.Label(frame, text=flow + text, bg="#ffffff", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        btn.config(text=f"操作日志（{len(logs)}） ▲")
        self._log_expanded = True

    # ------------------------------------------------------------------ 附件
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
            print(f"[报损出库-附件下载] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror("下载失败", str(e)))
            return
        self.controller.after(0, lambda: messagebox.showinfo("完成", f"附件已保存到：\n{path}"))

    # ------------------------------------------------------------------ 编辑
    def edit_selected(self):
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("提示", "请先选择一条报损单")
            return
        row = rows[0]
        if not self.out_status_editable(row.get('STATUS')):
            messagebox.showwarning("提示", "仅「待提交 / 审核驳回」状态可编辑")
            return
        self.open_edit(oo_row_source(row))

    def open_edit(self, source):
        self.edit_id = str(source.get('ID') or '') if source else ''
        self.edit_mode = 'edit' if source else 'new'
        self.edit_raw = None
        self.edit_items = []
        self.edit_attachments = []
        self.edit_other_out_no = (source or {}).get('OTHER_OUT_NO') or ''
        self.edit_record_version = (source or {}).get('RECORD_VERSION') or ''
        self.edit_status = str((source or {}).get('STATUS') or '')
        self.edit_resp_id = str((source or {}).get('RESPONSIBLE_PERSON_ID') or '')
        self.edit_resp_name = (source or {}).get('RESPONSIBLE_PERSON') or ''
        self.edit_remark = (source or {}).get('REMARK') or ''

        name = self.wh_name
        self.edit_wh_name = (source or {}).get('WAREHOUSE_NAME') or name
        self.edit_wh_code = get_storage_code(self.edit_wh_name) if self.edit_wh_name else self.wh_code
        self.edit_wh_id = (source or {}).get('WAREHOUSE_ID') or self.controller.options.get(self.edit_wh_name) or self.wh_id
        self.edit_org_id = USE_DEPT_MAP.get(self.edit_wh_name) or self.org_id

        if self.edit_id:
            self.count_var.set("加载中...")
            threading.Thread(target=self._edit_load_thread, args=(self.edit_id,), daemon=True).start()
        else:
            self._show_edit_window()

    def _edit_load_thread(self, bill_id):
        # 主单权威对象（queryById，取 RECORD_VERSION/STATUS/仓库等回带字段）
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                d = json.loads(r.text).get('data') or {}
                master = d if isinstance(d, dict) else {}
        except Exception as e:
            print(f"[报损出库-编辑主单] 异常: {e}")
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                items = (json.loads(r.text).get('data') or [])
                items = items if isinstance(items, list) else []
        except Exception as e:
            print(f"[报损出库-编辑明细] 异常: {e}")
        attachments, _ = self._fetch_attach_cfg(bill_id)

        self.edit_raw = master
        # 主单覆盖回带（无主单时保持列表行来源值）
        if master:
            self.edit_other_out_no = master.get('OTHER_OUT_NO') or self.edit_other_out_no
            self.edit_record_version = master.get('RECORD_VERSION') or self.edit_record_version
            self.edit_status = str(master.get('STATUS') or self.edit_status or '')
            self.edit_resp_id = str(master.get('RESPONSIBLE_PERSON_ID') or self.edit_resp_id)
            self.edit_resp_name = master.get('RESPONSIBLE_PERSON') or self.edit_resp_name
            self.edit_remark = master.get('REMARK') or self.edit_remark
            self.edit_wh_name = master.get('WAREHOUSE_NAME') or self.edit_wh_name
            self.edit_wh_code = master.get('WAREHOUSE_CODE') or self.edit_wh_code
            self.edit_wh_id = master.get('WAREHOUSE_ID') or self.edit_wh_id
            self.edit_org_id = master.get('ORGANIZATION_ID') or self.edit_org_id

        self.edit_items = [{
            '_orig': d,
            'ID': d.get('ID') if d.get('ID') is not None else '',
            'PART_ID': d.get('PART_ID'), 'PART_NO': d.get('PART_NO'),
            'PART_NAME': d.get('PART_NAME'), 'BRAND_ID': d.get('BRAND_ID'),
            'BRAND_NAME': d.get('BRAND_NAME'), 'CATEGORY_TWO': d.get('CATEGORY_TWO'),
            'COST_PRICE': d.get('COST_PRICE'),
            'NUM': float(d.get('NUM') or 1) if (d.get('NUM') not in (None, '')) else 1,
            'DAMAGE_REASON': d.get('DAMAGE_REASON') or '',
            'REMOVAL_LOCATION': d.get('REMOVAL_LOCATION') or '',
            'REMOVAL_LOCATION_NAME': d.get('REMOVAL_LOCATION_NAME') or '',
            'AVAILABLE_STOCK_QUANTITY': d.get('AVAILABLE_STOCK_QUANTITY'),
            'STORAGE_CODE': d.get('STORAGE_CODE') or self.edit_wh_code,
            'STORAGE_NAME': d.get('STORAGE_NAME') or self.edit_wh_name,
            'WAREHOUSE_ID': d.get('WAREHOUSE_ID'),
            'SUPPLIER_NAME': d.get('SUPPLIER_NAME') or DEFAULT_SUPPLIER_NAME,
            'loList': d.get('loList') if isinstance(d.get('loList'), list) else [],
            'RECORD_VERSION': d.get('RECORD_VERSION') if d.get('RECORD_VERSION') is not None else '',
        } for d in items]
        self.edit_attachments = attachments
        self.controller.after(0, self._show_edit_window)

    def _show_edit_window(self):
        win = tk.Toplevel(self)
        win.title("编辑报损单" if self.edit_id else "新建报损单")
        win.geometry("900x760")
        win.transient(self)
        self.edit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="编辑报损单" if self.edit_id else "新建报损单",
                 bg="#f7f8fa", fg="#fa8c16", font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        if self.edit_id:
            tk.Label(head, text=f"状态：{self.out_status_label(self.edit_status)}",
                     bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        base = tk.LabelFrame(win, text="基本信息", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        base.pack(fill=tk.X, padx=10, pady=5, ipadx=6, ipady=4)

        r1 = tk.Frame(base, bg="#f0f0f0")
        r1.pack(fill=tk.X, pady=2)
        tk.Label(r1, text="出库仓库:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        tk.Label(r1, text=self.edit_wh_name or '-', bg="#f0f0f0",
                 fg="#323233").pack(side=tk.LEFT)
        tk.Label(r1, text=f"（{self.edit_wh_code}）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=4)
        tk.Label(r1, text="  报损单号:", bg="#f0f0f0", width=9, anchor="e").pack(side=tk.LEFT, padx=(20, 0))
        tk.Label(r1, text=self.edit_other_out_no or '（保存后自动生成）',
                 bg="#f0f0f0", fg="#969799" if not self.edit_other_out_no else "#323233").pack(side=tk.LEFT)

        r2 = tk.Frame(base, bg="#f0f0f0")
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text="责任人:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.user_cb = ttk.Combobox(r2, textvariable=tk.StringVar(value=self.edit_resp_name),
                                    values=self.user_names, state="readonly", width=14)
        if self.edit_resp_name in self.user_names:
            self.user_cb.set(self.edit_resp_name)
        self.user_cb.pack(side=tk.LEFT, padx=4)
        self.user_cb.bind("<<ComboboxSelected>>", self._on_edit_user)

        r3 = tk.Frame(base, bg="#f0f0f0")
        r3.pack(fill=tk.X, pady=2)
        tk.Label(r3, text="备注:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_remark_var = tk.StringVar(value=self.edit_remark or '')
        ttk.Entry(r3, textvariable=self.edit_remark_var, width=70).pack(side=tk.LEFT, padx=4)

        # 报损明细
        dhead = tk.Frame(win, bg="#f0f0f0")
        dhead.pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(dhead, text="报损明细", bg="#f0f0f0", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(dhead, text="+ 新增配件", command=self.open_parts_picker,
                  bg="#fa8c16", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=8)
        self.edit_total_var = tk.StringVar(value="")
        tk.Label(dhead, textvariable=self.edit_total_var, bg="#f0f0f0",
                 fg="#fa8c16", font=("微软雅黑", 10, "bold")).pack(side=tk.RIGHT)

        self.items_frame = tk.Frame(win, bg="#ffffff")
        self.items_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        self._render_edit_items()

        # 附件单据
        ahead = tk.Frame(win, bg="#f0f0f0")
        ahead.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(ahead, text="附件单据", bg="#f0f0f0", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(ahead, text="+ 添加附件", command=self.add_attachment,
                  bg="#fa8c16", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=8)
        self.attach_frame = tk.Frame(win, bg="#ffffff")
        self.attach_frame.pack(fill=tk.X, padx=10)
        self._render_edit_attachments()

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        tk.Button(bar, text="保存", command=self.save_draft,
                  bg="#fa8c16", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="提交", command=self.submit_bill,
                  bg="#07c160", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="取消", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def _on_edit_user(self, event=None):
        name = self.user_cb.get()
        u = self.user_map.get(name)
        self.edit_resp_name = name
        if u:
            self.edit_resp_id = u['id']

    # ------------------------------------------------------------ 明细行 UI
    def _render_edit_items(self):
        for w in self.items_frame.winfo_children():
            w.destroy()
        if not self.edit_items:
            tk.Label(self.items_frame, text="请添加报损配件", bg="#ffffff",
                     fg="#c8c9cc").pack(anchor="w", pady=4)
            self._update_edit_total()
            return
        for d in self.edit_items:
            self._render_item_row(d)
        self._update_edit_total()

    def _render_item_row(self, d):
        outer = tk.LabelFrame(self.items_frame, text=d.get('PART_NAME') or d.get('PART_NO') or '(配件)',
                              bg="#f7f8fa", font=("微软雅黑", 9, "bold"))
        outer.pack(fill=tk.X, pady=3)

        line1 = tk.Frame(outer, bg="#f7f8fa")
        line1.pack(fill=tk.X, padx=6, pady=2)
        tk.Label(line1, text="配件编码：" + str(d.get('PART_NO') or '-'),
                 bg="#f7f8fa", fg="#646566").pack(side=tk.LEFT)
        tk.Label(line1, text="单价：" + self.format_money(d.get('COST_PRICE')),
                 bg="#f7f8fa", fg="#646566").pack(side=tk.LEFT, padx=(12, 0))
        tk.Button(line1, text="删", bg="#ee0a24", fg="white", bd=0, width=3,
                  command=lambda dd=d: self.remove_item(dd)).pack(side=tk.RIGHT)

        line2 = tk.Frame(outer, bg="#f7f8fa")
        line2.pack(fill=tk.X, padx=6, pady=2)
        tk.Label(line2, text="数量:", bg="#f7f8fa").pack(side=tk.LEFT)
        num_var = tk.StringVar(value=str(d.get('NUM') or 1))
        num_entry = ttk.Entry(line2, textvariable=num_var, width=8)
        num_entry.pack(side=tk.LEFT, padx=2)

        def on_num(event=None, dd=d, var=num_var):
            try:
                dd['NUM'] = float(var.get() or 0)
            except ValueError:
                dd['NUM'] = 0
            self._update_edit_total()

        num_entry.bind("<KeyRelease>", on_num)

        # 移出库位：优先该行 loList（location_no 显示 / location_id 存储）
        tk.Label(line2, text="移出库位:", bg="#f7f8fa").pack(side=tk.LEFT, padx=(14, 0))
        loc_options = [x.get('location_no') for x in (d.get('loList') or [])
                       if isinstance(x, dict) and x.get('location_no')]
        loc_map = {str(x.get('location_no')): str(x.get('location_id'))
                   for x in (d.get('loList') or []) if isinstance(x, dict)}
        loc_var = tk.StringVar(value=d.get('REMOVAL_LOCATION_NAME') or '')
        loc_cb = ttk.Combobox(line2, textvariable=loc_var,
                              values=loc_options, state="readonly", width=12)
        if d.get('REMOVAL_LOCATION_NAME') in loc_options:
            loc_cb.set(d.get('REMOVAL_LOCATION_NAME'))
        loc_cb.pack(side=tk.LEFT, padx=2)

        def on_loc(event=None, dd=d, var=loc_var, mapping=loc_map):
            no = var.get()
            dd['REMOVAL_LOCATION_NAME'] = no
            dd['REMOVAL_LOCATION'] = mapping.get(no) or no

        loc_cb.bind("<<ComboboxSelected>>", on_loc)

        # 报损原因：9969 组
        tk.Label(line2, text="报损原因:", bg="#f7f8fa").pack(side=tk.LEFT, padx=(14, 0))
        reason_map = (self.dict_maps or {}).get('9969') or {}
        reason_options = list(reason_map.values())
        reason_by_text = {v: k for k, v in reason_map.items()}
        reason_var = tk.StringVar(value=reason_map.get(str(d.get('DAMAGE_REASON') or ''), ''))
        reason_cb = ttk.Combobox(line2, textvariable=reason_var,
                                 values=reason_options, state="readonly", width=12)
        if reason_var.get() not in reason_options and reason_options:
            reason_var.set('')
        reason_cb.pack(side=tk.LEFT, padx=2)

        def on_reason(event=None, dd=d, var=reason_var, rev=reason_by_text):
            dd['DAMAGE_REASON'] = rev.get(var.get()) if var.get() else ''

        reason_cb.bind("<<ComboboxSelected>>", on_reason)

        line3 = tk.Frame(outer, bg="#f7f8fa")
        line3.pack(fill=tk.X, padx=6, pady=(0, 2))
        tk.Label(line3, text="可用库存：" + str(d.get('AVAILABLE_STOCK_QUANTITY') or 0)
                 + " · 分类：" + self.category_label(d.get('CATEGORY_TWO')),
                 bg="#f7f8fa", fg="#969799").pack(side=tk.LEFT)

    def remove_item(self, d):
        # 已存行直接移出列表（delItemList 恒 []，对齐安卓：后端按 itemList 回传差异处理）
        self.edit_items.remove(d)
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_items()

    # ------------------------------------------------------------ 附件 UI
    def _render_edit_attachments(self):
        for w in self.attach_frame.winfo_children():
            w.destroy()
        if not self.edit_attachments:
            tk.Label(self.attach_frame, text="支持图片/文件，提交前自动上传",
                     bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
            return
        for a in self.edit_attachments:
            line = tk.Frame(self.attach_frame, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            size = a.get('size') or 0
            tk.Label(line, text=a['name'] + (f"（{self._fmt_size(size)}）" if size else ""),
                     bg="#ffffff", anchor="w").pack(side=tk.LEFT)
            tk.Button(line, text="删", bg="#ee0a24", fg="white", bd=0, width=3,
                      command=lambda aa=a: self.remove_attachment(aa)).pack(side=tk.RIGHT)

    def add_attachment(self):
        paths = filedialog.askopenfilenames(
            title="选择附件",
            filetypes=[("所有支持", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp;*.pdf;*.doc;*.docx;"
                                   "*.xls;*.xlsx;*.txt;*.zip;*.rar"), ("所有文件", "*.*")])
        if not paths:
            return
        for path in paths:
            threading.Thread(target=self._upload_thread, args=(path,), daemon=True).start()

    def _upload_thread(self, path):
        name = os.path.basename(path)
        try:
            with open(path, 'rb') as f:
                files = {'dmsFile': (name, f, guess_mime(name))}
                r = self.controller.session.post(URL_FILE_UPLOAD, headers=HEADERS, files=files)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-附件上传] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror("上传失败", f"{name}: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "上传失败"
            self.controller.after(0, lambda: messagebox.showerror("上传失败", f"{name}: {msg}"))
            return
        file_id = (data.get("data") or {}).get("fileUploadId")
        if not file_id:
            self.controller.after(0, lambda: messagebox.showerror("上传失败", f"{name}: 未返回 fileUploadId"))
            return
        self.controller.after(0, lambda: self._append_attachment(name, file_id, path))

    def _append_attachment(self, name, file_id, path):
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        self.edit_attachments.append({
            'name': name, 'key': str(file_id), 'size': size,
            'isImage': is_image_file(name), 'isNew': True, 'preview': '',
        })
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_attachments()

    def remove_attachment(self, a):
        self.edit_attachments.remove(a)
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_attachments()

    # ------------------------------------------------------------ 配件选择
    def open_parts_picker(self):
        if not self.edit_wh_id and not self.edit_wh_name:
            messagebox.showwarning("提示", "请先选择出库仓库")
            return
        self.parts_popup = tk.Toplevel(self)
        self.parts_popup.title("选择配件")
        self.parts_popup.geometry("720x580")
        self.parts_popup.transient(self)
        self.parts_kw = tk.StringVar()
        pf = tk.Frame(self.parts_popup)
        pf.pack(fill=tk.X, padx=10, pady=6)
        ttk.Entry(pf, textvariable=self.parts_kw, width=32).pack(side=tk.LEFT, padx=4)
        tk.Button(pf, text="搜索", command=self.search_parts,
                  bg="#fa8c16", fg="white", bd=0, padx=14).pack(side=tk.LEFT, padx=4)
        tk.Label(pf, text="配件编码 / 名称", bg=self.parts_popup.cget('bg'),
                 fg="#969799").pack(side=tk.LEFT, padx=6)

        self.parts_list = tk.Listbox(self.parts_popup, selectmode=tk.EXTENDED)
        self.parts_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        tk.Button(self.parts_popup, text="确认添加",
                  command=self.confirm_parts, bg="#07c160", fg="white", bd=0, padx=16).pack(pady=6)

    def search_parts(self):
        kw = (self.parts_kw.get() or '').strip()
        has_cn = bool(re.search(r'[一-鿿]', kw))
        params = {
            'PART_NO': '' if has_cn else kw,
            'PART_NAME': kw if has_cn else '',
            'STORAGE_NAME': self.edit_wh_name,
            'WAREHOUSE_ID': self.edit_wh_id,
            'CORRELATION_ORDER_NO': '',
            'BUS_TYPE': BUS_TYPE,
        }
        threading.Thread(target=self._parts_thread, args=(params,), daemon=True).start()

    def _parts_thread(self, params):
        try:
            r = self.controller.session.get(URL_PARTS, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-配件] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("搜索失败", str(e)))
            return
        resp = data.get('data') or {}
        rows = resp.get('rows') if isinstance(resp, dict) else None
        rows = rows if isinstance(rows, list) else (resp if isinstance(resp, list) else [])
        self.controller.after(0, lambda: self._apply_parts(rows))

    def _apply_parts(self, rows):
        self.parts_data = rows
        self.parts_list.delete(0, tk.END)
        for p in rows:
            locs = ','.join(str(x.get('location_no')) for x in (p.get('loList') or [])
                            if isinstance(x, dict) and x.get('location_no'))
            line = "{} | {} | {} | 单价 {} | 库存 {} | 库位 {}".format(
                p.get('PART_NAME') or '-', p.get('PART_NO') or '',
                p.get('BRAND_NAME') or '', self.format_money(p.get('COST_PRICE')),
                p.get('AVAILABLE_STOCK_QUANTITY') or 0, locs or '无')
            self.parts_list.insert(tk.END, line)

    def confirm_parts(self):
        sel = self.parts_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "请勾选配件")
            return
        added = 0
        for i in sel:
            if not (0 <= i < len(self.parts_data)):
                continue
            p = self.parts_data[i]
            if any(it.get('PART_ID') == p.get('PART_ID') for it in self.edit_items):
                continue
            self.edit_items.append({
                '_orig': None,
                'ID': '',
                'PART_ID': p.get('PART_ID'), 'PART_NO': p.get('PART_NO'),
                'PART_NAME': p.get('PART_NAME'), 'BRAND_ID': p.get('BRAND_ID'),
                'BRAND_NAME': p.get('BRAND_NAME'), 'CATEGORY_TWO': p.get('CATEGORY_TWO'),
                'COST_PRICE': p.get('COST_PRICE'), 'NUM': 1,
                'DAMAGE_REASON': '',
                'REMOVAL_LOCATION': '', 'REMOVAL_LOCATION_NAME': '',
                'AVAILABLE_STOCK_QUANTITY': p.get('AVAILABLE_STOCK_QUANTITY'),
                'STORAGE_CODE': p.get('STORAGE_CODE') or self.edit_wh_code,
                'STORAGE_NAME': p.get('STORAGE_NAME') or self.edit_wh_name,
                'WAREHOUSE_ID': p.get('WAREHOUSE_ID'),
                'SUPPLIER_NAME': p.get('SUPPLIER_NAME') or DEFAULT_SUPPLIER_NAME,
                'loList': p.get('loList') if isinstance(p.get('loList'), list) else [],
                'RECORD_VERSION': '',
            })
            added += 1
        self.parts_popup.destroy()
        if added:
            self._render_edit_items()

    # ------------------------------------------------------------ 保存/提交
    def _update_edit_total(self):
        total = 0.0
        for d in self.edit_items:
            try:
                total += float(d.get('COST_PRICE') or 0) * float(d.get('NUM') or 0)
            except (TypeError, ValueError):
                pass
        if hasattr(self, 'edit_total_var'):
            self.edit_total_var.set("合计金额：" + self.format_money(total))

    def _current_wh_values(self):
        """编辑/新建使用的仓库三元组（编辑优先主单回带）"""
        if self.edit_mode == 'edit' and self.edit_raw:
            return {
                'code': self.edit_wh_code or self.wh_code,
                'name': self.edit_wh_name or self.wh_name,
                'id': self.edit_wh_id if self.edit_wh_id is not None else self.wh_id,
                'org': self.edit_org_id or self.org_id,
            }
        return {
            'code': self.edit_wh_code or self.wh_code,
            'name': self.edit_wh_name or self.wh_name,
            'id': self.edit_wh_id if self.edit_wh_id is not None else self.wh_id,
            'org': self.edit_org_id or self.org_id,
        }

    def build_item_list(self):
        wh = self._current_wh_values()
        pid = int(self.edit_id) if self.edit_id else ''
        other_no = self.edit_other_out_no or ''
        out = []
        for d in self.edit_items:
            num = float(d.get('NUM') or 0)
            price = float(d.get('COST_PRICE') or 0)
            out.append({
                'PART_ID': d.get('PART_ID'),
                'PART_NO': d.get('PART_NO'),
                'PART_NAME': d.get('PART_NAME'),
                'BRAND_ID': d.get('BRAND_ID'),
                'BRAND_NAME': d.get('BRAND_NAME') or '福耀玻璃',
                'CATEGORY_TWO': d.get('CATEGORY_TWO'),
                'COST_PRICE': price,
                'NUM': num,
                'DAMAGE_REASON': d.get('DAMAGE_REASON') or '',
                'REMOVAL_LOCATION': d.get('REMOVAL_LOCATION') or '',
                'REMOVAL_LOCATION_NAME': d.get('REMOVAL_LOCATION_NAME') or '',
                'AVAILABLE_STOCK_QUANTITY': d.get('AVAILABLE_STOCK_QUANTITY'),
                'STORAGE_CODE': d.get('STORAGE_CODE') or wh['code'],
                'STORAGE_NAME': d.get('STORAGE_NAME') or wh['name'],
                'WAREHOUSE_ID': d.get('WAREHOUSE_ID') or wh['id'],
                'DEALER_CODE': DEALER_CODE,
                'SUPPLIER_NAME': d.get('SUPPLIER_NAME') or DEFAULT_SUPPLIER_NAME,
                'ORGANIZATION_ID': wh['org'] or '',
                'DR': 0,
                'UNIT': None, 'MPQ': None, 'BATCH_NUMBER': None,
                'RETURN_UNIT_PRICE': None, 'REMARK': None,
                'loList': d.get('loList') if isinstance(d.get('loList'), list) else [],
                # 已存明细回带服务器 ID；新增明细送空串
                'ID': d.get('ID') if d.get('ID') not in (None, '') else '',
                'PID': pid,
                'OTHER_OUT_NO': other_no,
                'RECORD_VERSION': d.get('RECORD_VERSION') if d.get('RECORD_VERSION') not in (None, '') else '',
                'NO_TAX_AMOUNT': round(price * num, 2),
            })
        return out

    def build_base_payload(self, status):
        wh = self._current_wh_values()
        items = self.build_item_list()
        no_tax = round(sum(float(it.get('COST_PRICE') or 0) * float(it.get('NUM') or 0)
                           for it in items), 2)
        remark = self.edit_remark_var.get() if hasattr(self, 'edit_remark_var') else self.edit_remark
        base = {
            'BRAND_ID': DEFAULT_BRAND_ID,
            'BUS_TYPE': BUS_TYPE,
            'CREATED_AT': self.today_str(),
            'CREATED_BY': '',
            'CREATED_BY_NAME': '',
            'DEALER_CODE': DEALER_CODE,
            'ORGANIZATION_ID': wh['org'] or '',
            'REMARK': remark,
            'RESPONSIBLE_PERSON': self.edit_resp_name,
            'RESPONSIBLE_PERSON_ID': self.edit_resp_id,
            'STATUS': status,
            'UPDATED_AT': self.now_str(),
            'UPDATED_BY': '',
            'WAREHOUSE_CODE': wh['code'],
            'WAREHOUSE_ID': wh['id'],
            'WAREHOUSE_NAME': wh['name'],
            'NO_TAX_AMOUNT': no_tax,
            'itemList': items,
            'delItemList': [],
        }
        # 编辑态：制单人/创建时间沿用主单原值（桌面无操作人身份，避免覆盖历史）
        if self.edit_raw:
            m = self.edit_raw
            base['CREATED_AT'] = m.get('CREATED_AT') or base['CREATED_AT']
            base['CREATED_BY'] = m.get('CREATED_BY') or ''
            base['CREATED_BY_NAME'] = m.get('CREATED_BY_NAME') or ''
            base['UPDATED_BY'] = m.get('UPDATED_BY') or ''
        return base

    def build_draft_file_list(self):
        """add/edit 报文 fileList（bootstrap-fileinput 草稿结构，对齐安卓 buildDraftFileList）"""
        out = []
        for a in self.edit_attachments:
            size = int(a.get('size') or 0)
            item = {
                'status': 'success',
                'name': a['name'],
                'size': size,
                'sizeKB': '%dKB' % round(size / 1024) if size else '',
                'uid': 'k' + a['key'],
                'url': '',
                'key': a['key'],
                'dealerCode': DEALER_CODE,
                'isValid': 10011001,
                'showZoom': True,
            }
            if a.get('isNew'):
                # 新增附件：optionType=add + canDelete=10041001（对齐 HAR add 报文）
                item['optionType'] = 'add'
                item['canDelete'] = 10041001
                item['response'] = {'resultCode': 200, 'success': True,
                                    'data': {'fileUploadId': a['key']}}
            else:
                # 已存附件：canDelete=10041002、无 optionType
                item['canDelete'] = 10041002
            out.append(item)
        return out

    def build_submit_file_list(self, bill_id):
        """submit 报文 fileList（对齐安卓 buildSubmitFileList）"""
        seg = ATTACH_BILL_TYPE
        out = []
        for a in self.edit_attachments:
            size = int(a.get('size') or 0)
            review_url = '/dmscloud.basedata/file/billFilesReview/{}/{}'.format(seg, a['key'])
            out.append({
                'dealerCode': DEALER_CODE,
                'caption': a['name'],
                'size': size,
                'key': int(a['key']),
                'type': 'image' if a.get('isImage') else 'file',
                'showZoom': True,
                'url': review_url,
                'createdAt': self.now_str(),
                'canDelete': 10041002,
                'isValid': 10011001,
                'description': '',
                'billId': int(bill_id),
                'billType': seg,
                'sizeKB': '%dKB' % round(size / 1024) if size else '',
                'name': a['name'],
                'uuid': review_url,
                'downloadUrl': '/dmscloud.basedata/file/billFilesDownload/{}/{}'.format(seg, a['key']),
            })
        return out

    def _validate(self):
        if not self.edit_wh_name or not self.edit_wh_code:
            messagebox.showwarning("提示", "请先选择出库仓库")
            return False
        if not self.edit_resp_name:
            messagebox.showwarning("提示", "请选择责任人")
            return False
        if not self.edit_items:
            messagebox.showwarning("提示", "请至少添加一条报损配件")
            return False
        for d in self.edit_items:
            if float(d.get('NUM') or 0) <= 0:
                messagebox.showwarning("提示", "配件「%s」数量必须大于 0" % (d.get('PART_NAME') or d.get('PART_NO') or ''))
                return False
            if not d.get('REMOVAL_LOCATION'):
                messagebox.showwarning("提示", "请为每条配件选择移出库位")
                return False
            if not d.get('DAMAGE_REASON'):
                messagebox.showwarning("提示", "请为每条配件选择报损原因")
                return False
        return True

    def save_draft(self):
        if not self._validate():
            return
        status = int(self.edit_status) if self.edit_status else DRAFT_STATUS
        payload = self.build_base_payload(status)
        if self.edit_id:
            payload['ID'] = int(self.edit_id)
            payload['OTHER_OUT_NO'] = self.edit_other_out_no
            payload['RECORD_VERSION'] = self.edit_record_version
        payload['fileList'] = self.build_draft_file_list()
        is_add = not self.edit_id
        self.count_var.set("保存中...")
        threading.Thread(target=self._save_thread, args=(payload, is_add), daemon=True).start()

    def _save_thread(self, payload, is_add):
        try:
            url = URL_ADD if is_add else URL_EDIT
            r = self.controller.session.post(url, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-保存] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"保存失败: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "保存失败"
            self.controller.after(0, lambda: messagebox.showerror("保存失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        # 新建单可能回带 ID（供直接提交）
        d = data.get('data')
        if is_add and isinstance(d, dict):
            self.edit_id = str(d.get('ID') or '')
            self.edit_other_out_no = d.get('OTHER_OUT_NO') or self.edit_other_out_no
            self.edit_record_version = d.get('RECORD_VERSION') if d.get('RECORD_VERSION') is not None else self.edit_record_version
        self.controller.after(0, lambda: messagebox.showinfo("成功", "已保存"))
        self.controller.after(0, self._after_saved)

    def submit_bill(self):
        if not self._validate():
            return
        # 新建单（无 ID）先保存，再尝试提交（对齐安卓 submitBill）
        if not self.edit_id:
            if not messagebox.askyesno("确认提交", "将先保存并提交该报损单，确认？"):
                return
            status = int(self.edit_status) if self.edit_status else DRAFT_STATUS
            # 主线程先构造好报文（build_base_payload 会读 Tk StringVar，不能在子线程执行）
            add_payload = self.build_base_payload(status)
            add_payload['fileList'] = self.build_draft_file_list()
            self.count_var.set("保存并提交中...")
            threading.Thread(target=self._new_submit_worker,
                             args=(add_payload, status), daemon=True).start()
            return
        if not messagebox.askyesno("确认提交", "提交后将进入审核流程，确认提交？"):
            return
        status = int(self.edit_status) if self.edit_status else DRAFT_STATUS
        payload = self.build_base_payload(status)
        payload['ID'] = int(self.edit_id)
        payload['OTHER_OUT_NO'] = self.edit_other_out_no
        payload['RECORD_VERSION'] = self.edit_record_version
        payload['fileList'] = self.build_submit_file_list(self.edit_id)
        self.count_var.set("提交中...")
        threading.Thread(target=self._submit_thread, args=(payload,), daemon=True).start()

    def _new_submit_worker(self, add_payload, status):
        # 步骤1：add（报文已在主线程构造好）
        try:
            r = self.controller.session.post(URL_ADD, headers=HEADERS, json=add_payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-保存] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"保存失败: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "保存失败"
            self.controller.after(0, lambda: messagebox.showerror("保存失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        d = data.get('data') or {}
        bill_id = str(d.get('ID') or '') if isinstance(d, dict) else ''
        other_no = d.get('OTHER_OUT_NO') or '' if isinstance(d, dict) else ''
        if not bill_id or not other_no:
            self.controller.after(0, lambda: messagebox.showinfo(
                "已保存", "单据已保存（未回带单号），请在列表打开该单据后再提交"))
            self.controller.after(0, self._after_saved)
            return
        # 步骤2：submit（基于 add 报文深拷贝，仅改 ID/单号/版本/STATUS/fileList，纯数据不触 Tk）
        try:
            sub = json.loads(json.dumps(add_payload, ensure_ascii=False, default=str))
        except Exception:
            sub = dict(add_payload)
        sub.pop('fileList', None)
        sub['ID'] = int(bill_id)
        sub['OTHER_OUT_NO'] = other_no
        if isinstance(d, dict) and d.get('RECORD_VERSION') is not None:
            sub['RECORD_VERSION'] = d['RECORD_VERSION']
        sub['STATUS'] = status
        sub['fileList'] = self.build_submit_file_list(bill_id)
        try:
            r = self.controller.session.post(URL_SUBMIT, headers=HEADERS, json=sub)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-提交] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"提交失败: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "提交失败"
            self.controller.after(0, lambda: messagebox.showerror("提交失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", "提交成功，已进入审核"))
        self.controller.after(0, self._after_saved)

    def _submit_thread(self, payload):
        try:
            r = self.controller.session.post(URL_SUBMIT, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-提交] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"提交失败: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "提交失败"
            self.controller.after(0, lambda: messagebox.showerror("提交失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", "提交成功，已进入审核"))
        self.controller.after(0, self._after_saved)

    def _after_saved(self):
        if self.edit_win and self.edit_win.winfo_exists():
            self.edit_win.destroy()
        self.query()

    # ------------------------------------------------------------------ 打印
    def open_print_preview(self):
        rows = self.all_rows
        if not rows:
            messagebox.showinfo("提示", "请先查询报损单")
            return
        ids = [str(r['ID']) for r in self._selected_rows()]
        if ids:
            valid = [r for r in rows if str(r['ID']) in ids]
        else:
            # 无勾选：打印当前过滤结果（剔除已作废，对齐其它打印入口）
            valid = [r for r in self.filtered_rows if str(r.get('STATUS')) != '12511009']
        if not valid:
            messagebox.showinfo("提示", "没有可打印的单据（请先勾选，或查询后直接打印）")
            return
        nos = ",".join("'%s'" % r['OTHER_OUT_NO'] for r in valid if r.get('OTHER_OUT_NO'))
        if not nos:
            messagebox.showwarning("提示", "所选单据缺少单号，无法打印")
            return
        self.count_var.set("加载打印数据...")
        threading.Thread(target=self._print_thread, args=(nos,), daemon=True).start()

    def _print_thread(self, nos):
        try:
            r = self.controller.session.get(URL_PRINT, headers=HEADERS,
                                            params={'OTHER_OUT_NOS': nos, 'BUS_TYPE': BUS_TYPE})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报损出库-打印] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"打印数据加载失败: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        flat = (data.get('data') or []) if isinstance(data.get('data'), list) else []
        groups = []
        for row in flat:
            grp = next((g for g in groups if g['header'].get('OTHER_OUT_NO') == row.get('OTHER_OUT_NO')), None)
            if not grp:
                grp = {'header': row, 'items': []}
                groups.append(grp)
            grp['items'].append(row)
        for g in groups:
            num = sum(float(it.get('NUM') or 0) for it in g['items'])
            amount = sum(float(it.get('NUM') or 0) * float(it.get('COST_PRICE') or 0)
                         for it in g['items'])
            g['totalNum'] = num
            g['totalAmount'] = amount
        self.controller.after(0, lambda: self._show_print_window(groups))

    def _show_print_window(self, groups):
        self.count_var.set(f"共 {len(self.filtered_rows)} 条报损单")
        win = tk.Toplevel(self)
        win.title("报损出库单打印预览")
        win.geometry("820x720")
        win.transient(self)
        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text=f"打印预览（{len(groups)} 单）", bg="#f7f8fa", fg="#fa8c16",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        body = tk.Text(win, wrap=tk.WORD, font=("微软雅黑", 9), bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body.tag_configure("title", font=("微软雅黑", 15, "bold"), justify="center")
        body.tag_configure("h", font=("微软雅黑", 10, "bold"))
        for g in groups:
            h = g['header']
            body.insert(tk.END, "\n报损出库单\n", "title")
            body.insert(tk.END, (
                f"出库仓库：{self.short_brand(h.get('WAREHOUSE_NAME') or '')}    业务类型：报损出库    责任人：{h.get('RESPONSIBLE_PERSON') or ''}\n"
                f"开单人：{h.get('CREATED_BY_NAME') or ''}    移出单号：{h.get('OUT_NO') or ''}    单据号：{h.get('OTHER_OUT_NO') or ''}\n"
                f"摘要：{h.get('REMARK') or ''}\n"))
            body.insert(tk.END,
                        "品牌 | 产品编码 | 产品名称 | 分类 | 报损原因 | 出库数量 | 单价 | 出库金额 | 移出库位\n", "h")
            for it in g['items']:
                num = float(it.get('NUM') or 0)
                price = float(it.get('COST_PRICE') or 0)
                body.insert(tk.END, "{0} | {1} | {2} | {3} | {4} | {5} | {6:.2f} | {7:.2f} | {8}\n".format(
                    self.short_brand(it.get('BRAND_NAME') or ''),
                    it.get('PART_NO') or '', it.get('PART_NAME') or '',
                    self.category_label(it.get('CATEGORY_TWO')),
                    self.reason_label(it.get('DAMAGE_REASON')),
                    num, price, num * price,
                    it.get('REMOVAL_LOCATION_NAME') or ''))
            body.insert(tk.END, "合计数量：{0}    合计金额：¥{1:,.2f}\n".format(
                g['totalNum'], g['totalAmount']))
            body.insert(tk.END, "─" * 72 + "\n")
        body.configure(state=tk.DISABLED)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="打 印", command=lambda: self.print_via_clodop(groups, win),
                  bg="#fa8c16", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def print_via_clodop(self, groups, win):
        """复用 CLodop WebSocket 协议（对齐 picking_shipping.py）打印报损出库单"""
        try:
            import websocket
        except ImportError:
            messagebox.showerror("打印失败", "未安装 websocket 模块，无法连接 CLodop")
            return
        try:
            html_parts = []
            for g in groups:
                html_parts.append(self._build_single_html(g))
            now = datetime.now()
            task_id = f"PY{now.hour:02d}{now.minute:02d}{now.second:02d}_1"
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
                    f"printtask=报损出库单打印{delim}"
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

    def _build_single_html(self, group):
        """报损出库单打印 HTML（列对齐安卓 lodopPrint generateOtherOutboundHtml）"""
        h = group['header']
        rows = ""
        for it in group['items']:
            num = float(it.get('NUM') or 0)
            price = float(it.get('COST_PRICE') or 0)
            rows += (
                "<tr>"
                f"<td>{self.short_brand(it.get('BRAND_NAME') or '')}</td>"
                f"<td style='text-align:center'>{it.get('PART_NO') or ''}</td>"
                f"<td style='text-align:left'>{it.get('PART_NAME') or ''}</td>"
                f"<td>{self.category_label(it.get('CATEGORY_TWO'))}</td>"
                f"<td style='text-align:left'>{self.reason_label(it.get('DAMAGE_REASON'))}</td>"
                f"<td>{num}</td>"
                f"<td style='text-align:right'>{price:.2f}</td>"
                f"<td style='text-align:right'>{num * price:.2f}</td>"
                f"<td>{it.get('REMOVAL_LOCATION_NAME') or ''}</td>"
                "</tr>"
            )
        return (
            "<style>div{width:97%} body{margin:0;padding:0}</style>"
            "<div class='print-page'>"
            "<div class='print-page-title' style='text-align:center;font-size:20px;font-weight:700'>报损出库单</div>"
            "<div class='print-page-info' style='font-size:13px'>"
            f"<div>出库仓库：{self.short_brand(h.get('WAREHOUSE_NAME') or '')}　业务类型：报损出库　责任人：{h.get('RESPONSIBLE_PERSON') or ''}</div>"
            f"<div>开单人：{h.get('CREATED_BY_NAME') or ''}　移出单号：{h.get('OUT_NO') or ''}　单据号：{h.get('OTHER_OUT_NO') or ''}</div>"
            f"<div>摘要：{h.get('REMARK') or ''}</div>"
            "</div>"
            "<table border='1' cellspacing='0' style='width:98%;font-size:12px;border-collapse:collapse;text-align:center'>"
            "<thead><tr><th>品牌</th><th>产品编码</th><th>产品名称</th><th>分类</th><th>报损原因</th>"
            "<th>出库数量</th><th>单价</th><th>出库金额</th><th>移出库位</th></tr></thead>"
            "<tbody>" + rows + "</tbody>"
            f"<tfoot><tr><td colspan='4'/><td colspan='2' style='font-weight:bold'>合计数量：{group['totalNum']}</td>"
            f"<td colspan='2' style='font-weight:bold'>合计金额：¥{group['totalAmount']:,.2f}</td><td/></tr></tfoot>"
            "</table></div>"
        )


def oo_row_source(row):
    """列表行 → 编辑接口需要的 source 结构（对齐安卓 openEdit(source)，只挑必要键）"""
    if row is None:
        return {}
    return {
        'ID': row.get('ID'),
        'OTHER_OUT_NO': row.get('OTHER_OUT_NO'),
        'STATUS': row.get('STATUS'),
        'RESPONSIBLE_PERSON': row.get('RESPONSIBLE_PERSON'),
        'RESPONSIBLE_PERSON_ID': row.get('RESPONSIBLE_PERSON_ID'),
        'REMARK': row.get('REMARK'),
        'WAREHOUSE_CODE': row.get('WAREHOUSE_CODE'),
        'WAREHOUSE_NAME': row.get('WAREHOUSE_NAME'),
        'WAREHOUSE_ID': row.get('WAREHOUSE_ID'),
        'RECORD_VERSION': row.get('RECORD_VERSION'),
    }

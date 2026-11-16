# -*- coding: utf-8 -*-
"""内部领用管理（内部领用模块 菜单 1/2）

对齐 fycarg-pda 安卓端：
- src/views/InternalUseManage.vue（1980 行）
- src/service/internalUse.js
- src/config/internalUse.js
- 打印复用本项目的 CLodop WebSocket 机制（picking_shipping.py print_via_clodop）

接口清单（dmscloud.part/internalUse 为主，dcscloud.basedata 为辅）：
- 列表     GET  /dmscloud.part/internalUse/page
- 主单明细 GET  /dmscloud.part/internalUse/queryById?id=
- 明细行   GET  /dmscloud.part/internalUse/queryById/items?id=
- 配件搜索 GET  /dmscloud.part/internalUse/selectParts (PART_NO/PART_NAME/STORAGE_NAME/storage_code)
- 出库库位 GET  /dmscloud.part/internalUse/query/outLocation?STORAGE_CODE=
- 新增     POST /dmscloud.part/internalUse/add
- 编辑     POST /dmscloud.part/internalUse/edit
- 提交     POST /dmscloud.part/internalUse/submit
- 作废     PUT  /dmscloud.part/internalUse/{id}/cancel
- 领用人   GET  /dcscloud.basedata/basedata/employees/employees/internalUser
- 仓库列表 GET  /dmscloud.part/purchaseMngOem/getStoreList
- 打印     GET  /dmscloud.part/internalUse/queryPrintList?USE_NOS='单号1','单号2'
- 操作日志 GET  /dmscloud.part/operateLogs/page?BILL_ID=&BILL_TYPE=12041002&limit=5&pageNum=1&isShowLogs=true

与「报销管理」系列的关键差异：
1. 单据状态字典改用 **1246 组**（待提交/待审核/经理审核通过/经理审核驳回/部门审核通过/部门审核驳回/已作废），
   editable/voidable = [12461001, 12461004, 12461006]（新建/经理驳回/部门驳回）。
2. 列表字段全大写（ID/USE_NO/STATUS/USE_MAN/DEPARTMENT_NAME/WAREHOUSE_NAME/CREATED_AT/REMARK）。
3. 查询参数带 storage_code（仓库码 ZZ/XA…，取自 warehouse_mapping.get_storage_code）、
   ORG_NAME（仓库名）、DEPARTMENT_ID（按仓库映射 1148~1167）、BRAND_ID=''、
   CREATED_AT_FROM/TO（拼接 00:00:00 / 23:59:59）。limit=500，状态由前端过滤。
4. 保存报文（HAR 实证，见 src/config/internalUse.js 头部注释）：
   - 新增(add)：仅 9 个业务字段（DEPARTMENT_ID/NAME、storage_code、USE_MAN/USE_MAN_ID/USE_PHONE、
     REMARK、isDisabledOrgSelect、itemList、delItemList），【不带】STATUS/NO_TAX_AMOUNT/ID/USE_NO。
   - 编辑(save)/提交(submit)：大写 STATUS = 当前状态；以 queryById 主单权威对象为底（带 RECORD_VERSION /
     ORGANIZATION_ID），覆盖用户可改字段，并带 NO_TAX_AMOUNT（= Σ COST_PRICE*USE_NUM）。
   - 新建即提交（submit 且无 id）：现场拼主单，剔除 ID/USE_NO。
5. itemList：编辑态以原始持久化行(_orig)为底保留 ID/PID/RECORD_VERSION/NO_TAX_AMOUNT，仅覆盖 USE_NUM/OUT_LOCATION/loList；
   新增态为简洁结构（含 MOQ/MPQ/UNIT=null, DR:0）。
6. 作废：PUT 路径携带 id；仅 voidable 状态可操作。⚠️ PC 端受 `v-has:auth="internalUse:button:cancel"`
   权限门控（用户账号当前缺该权限，PC 不渲染按钮）；安卓端亦隐藏。本桌面端**无权限体系**，
   按「状态可作废」显式展示作废按钮（与 PC 有权限账号行为对齐），如需禁用待接入权限查询。
7. 打印预览：queryPrintList 按 USE_NO 分组，结构化渲染（对齐 PC/安卓打印模板）；打印走 CLodop WebSocket。
8. ⚠️ **领用人 → 领用部门（DEPARTMENT_ID/NAME）自动带出，部门不可手选**
   （安卓 onUserConfirm，InternalUseManage.vue:1342-1354）：
   - 选择领用人后，USE_MAN / USE_MAN_ID / USE_PHONE 与 DEPARTMENT_ID / DEPARTMENT_NAME
     一并写入，部门取该领用人的 ORG（internalUser 接口的 ORGANIZATION_ID / ORG_NAME）；
   - **无条件覆盖**：领用人无所属组织时部门置空，**不得**用仓库映射值兜底
     （早期实现写成 `u['orgId'] or self.edit_dept_id`，会残留仓库值，与安卓不符）；
   - 新建时部门初始为空（安卓 openEdit:1252-1254），待选领用人后带出；
   - 切换领用仓库**不改变**部门（安卓 onWarehouseConfirm:717 只改 warehouseName）。
9. ⚠️ **DEPARTMENT_ID 与 ORGANIZATION_ID 是两种语义，切勿混用**
   （安卓 buildPayload:1534 / 1563）：
   - DEPARTMENT_ID / DEPARTMENT_NAME → 领用人的所属组织（随领用人变）；
   - ORGANIZATION_ID → 领用仓库映射 USE_DEPT_MAP（随仓库变）；
     仅出现在「新建即提交/编辑」主单里，编辑态沿用主单原值。
   早期实现两者都取 edit_dept_id，导致选过领用人后 ORGANIZATION_ID 被写错。
"""

import json
import threading
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

# ---------------------------------------------------------------- 常量 / 接口
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}
BASE = 'https://xb.fy-carg.com'
PART = '/dmscloud.part/internalUse'

URL_QUERY = BASE + PART + '/page'
URL_DETAIL = BASE + PART + '/queryById'
URL_ITEMS = BASE + PART + '/queryById/items'
URL_PARTS = BASE + PART + '/selectParts'
URL_OUT_LOC = BASE + PART + '/query/outLocation'
URL_ADD = BASE + PART + '/add'
URL_EDIT = BASE + PART + '/edit'
URL_SUBMIT = BASE + PART + '/submit'
# 作废：PUT /dmscloud.part/internalUse/{id}/cancel
URL_CANCEL_TMPL = BASE + PART + '/{id}/cancel'
URL_USERS = BASE + '/dcscloud.basedata/basedata/employees/employees/internalUser'
URL_STORES = BASE + '/dmscloud.part/purchaseMngOem/getStoreList'
URL_PRINT = BASE + PART + '/queryPrintList'
URL_LOGS = BASE + '/dmscloud.part/operateLogs/page'

QUERY_LIMIT = 500
PAGE_SIZE = 10

# 操作日志单据类型（内部领用固定）
LOG_BILL_TYPE = 12041002
LOG_PAGE_SIZE = 5

# 领用单状态字典（1246 组）
USE_STATUS_MAP = {
    12461001: {'label': '待提交', 'editable': True, 'voidable': True},
    12461002: {'label': '待审核', 'editable': False, 'voidable': False},
    12461003: {'label': '经理审核通过', 'editable': False, 'voidable': False},
    12461004: {'label': '经理审核驳回', 'editable': True, 'voidable': True},
    12461005: {'label': '部门审核通过', 'editable': False, 'voidable': False},
    12461006: {'label': '部门审核驳回', 'editable': True, 'voidable': True},
    12461007: {'label': '已作废', 'editable': False, 'voidable': False},
}
USE_EDITABLE_STATUS = [12461001, 12461004, 12461006]
USE_VOIDABLE_STATUS = [12461001, 12461004, 12461006]
USE_CANCELLED_STATUS = 12461007

USE_STATUS_FILTERS = [
    ('全部', ''), ('待提交', '12461001'), ('待审核', '12461002'),
    ('经理审核通过', '12461003'), ('经理审核驳回', '12461004'),
    ('部门审核通过', '12461005'), ('部门审核驳回', '12461006'), ('已作废', '12461007'),
]

# 部门映射：仓库名 → DEPARTMENT_ID/ORGANIZATION_ID（对齐安卓端 USE_DEPT_MAP）
USE_DEPT_MAP = {
    '郑州库': 1148, '西安库': 1149, '兰州库': 1150, '洛阳库': 1151,
    '商丘库': 1152, '驻马店库': 1153, '茶城库': 1154, '雁塔库': 1167,
    '榆林库': 1166, '银川库': 1164, '西安西郊库': 1165,
}

# 审计 / 整单字段默认值（对齐 web 端 addEditDetail 的整单报文）
#
# 事实依据（addEditDetail-262160cf.js + xb.fy-carg.com.har）：
#   saveInfoFn 只做 `t = $.extend({}, this.formVo); t.itemList = ...; t.delItemList = ...`，
#   端点由 clickBtn 决定：!USE_NO && saveBtn → add / USE_NO && saveBtn → edit / submitBtn → submit。
#   即 add、edit、submit 三个端点发的都是「整单」，差异只在 URL 与有无 ID/USE_NO。
#
# web 端 formVo 初始只有 14 个业务字段，不含审计字段；审计字段来自 openDialog 合并进来的 o.row：
#   · 编辑态 row = internalUse/queryById 整单 → 原样回传，UPDATED_AT / RECORD_VERSION 由后端维护
#   · 新建态 addFn() 只传 options、不传 row  → 审计字段本应为空，由后端按登录态生成
#   （HAR 里 add 报文出现 CREATED_AT='2026-06-30 09:46:52' / RECORD_VERSION=5，是组件实例上一次
#    编辑的状态残留脏数据：openDialog 的 $.extend(this.formVo, this.resetFormVo) 只覆盖 resetFormVo
#    那 14 个键、不清除其余键。后端对 add 忽略客户端传入的审计值，故新建一律留空。）
#
# 另：UPDATED_AT / UPDATED_BY / RECORD_VERSION 前端从不自行计算——HAR 中同单三次请求
#   edit(11:57:17) → submit(11:57:28) 递增，均为后端写入后由 queryById 带回再原样回传。
# CREATED_BY / UPDATED_BY 为员工号（如 'HJ011'）；Python 端登录只存 cookie、无 employeeId，
#   故新建时只能留空（同 other_outbound_apply.py 的处理），既有单则原样回传后端已有值。
AUDIT_DEFAULTS = {
    'CREATED_AT': '', 'CREATED_BY': '', 'CREATED_BY_NAME': '',
    'UPDATED_AT': '', 'UPDATED_BY': '', 'UPDATED_BY_NAME': '',
    'RECORD_VERSION': 0, 'DEALER_CODE': 'FY', 'DR': 0,
}

# 列表列
COLUMNS = ["序号", "领用单号", "状态", "领用人", "部门", "出库仓", "创建时间"]
COLUMN_WIDTHS = [50, 170, 90, 100, 110, 110, 150]


class InternalUseManagePage(BasePage):
    """内部领用管理页面（查询/明细/新建编辑/提交/作废/打印预览）"""

    def __init__(self, parent, controller):
        self.all_rows = []
        self.filtered_rows = []
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.queried = False
        self.loading = False

        self.filter_status = tk.StringVar(value='')
        self.filter_use_no = tk.StringVar(value='')
        self.filter_use_man = tk.StringVar(value='')

        # 部门解析（按当前仓库）
        self.dept_id = None
        self.dept_name = ''

        # 领用人
        self.internal_users = []
        self.user_names = []
        self.user_map = {}        # name -> {id, phone, orgId, orgName}

        # 出库库位（全部仓库兜底）
        self.out_locations = []

        # 编辑态
        self.edit_id = ''
        self.edit_mode = 'new'
        self.edit_raw = None
        self.edit_items = []
        self.edit_del_items = []
        self.edit_use_man = ''
        self.edit_use_man_id = ''
        self.edit_use_phone = ''
        self.edit_remark = ''
        # DEPARTMENT_ID/NAME：由「领用人」所属组织带出（不可手选，对齐安卓端 onUserConfirm）
        self.edit_dept_id = None
        self.edit_dept_name = ''
        # ORGANIZATION_ID：由「领用仓库」映射带出（USE_DEPT_MAP），与 DEPARTMENT_ID 是两种语义，
        # 安卓端 getDeptByWarehouse(warehouseName).id，切勿与 edit_dept_id 混用
        self.edit_org_id = None
        self.edit_wh_code = ''
        self.edit_wh_name = ''
        self.edit_win = None

        # 多选打印
        self.selected_ids = []

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

        # 初始化：领用人 / 出库库位
        self.load_users()
        self.load_out_locations()

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
        self.warehouse_cb.bind("<<ComboboxSelected>>", lambda e: self.resolve_dept())
        tk.Label(row1, text="（用于解析部门）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=5)

        # 状态快捷标签
        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.status_buttons = {}
        for label, value in USE_STATUS_FILTERS:
            btn = tk.Button(row2, text=label, width=9, relief=tk.FLAT,
                            bg="#e1e1e1", fg="#323233",
                            command=lambda v=value: self.toggle_status(v))
            btn.pack(side=tk.LEFT, padx=2)
            self.status_buttons[value] = btn
        self._update_status_buttons()

        row3 = tk.Frame(frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=2)
        tk.Label(row3, text="申请日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(self.def_date('begin'))
        self.start_cal.pack(side=tk.LEFT, padx=2)
        tk.Label(row3, text="至", bg="#f0f0f0").pack(side=tk.LEFT)
        self.end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(self.def_date('end'))
        self.end_cal.pack(side=tk.LEFT, padx=2)

        row4 = tk.Frame(frame, bg="#f0f0f0")
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="领用单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row4, textvariable=self.filter_use_no, width=18).pack(side=tk.LEFT, padx=2)
        tk.Label(row4, text="领用人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(row4, textvariable=self.filter_use_man, width=12).pack(side=tk.LEFT, padx=2)

        btn_style = {"bg": "#722ed1", "fg": "white", "padx": 14, "pady": 4,
                     "bd": 0, "activebackground": "#531dab"}
        tk.Button(row4, text="查询领用单", command=self.query, **btn_style).pack(side=tk.LEFT, padx=12)
        tk.Button(row4, text="重置", command=self.reset_form,
                  bg="#e1e1e1", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="内部领用单列表", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=13)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "e" if col == "金额" else ("center" if col in ("序号",) else "w")
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
        tk.Button(bar, text="新建领用单", command=lambda: self.open_edit(None),
                  bg="#722ed1", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="查看明细", command=self.open_detail,
                  bg="#1989fa", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="编辑", command=self.edit_selected,
                  bg="#ff976a", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="作废", command=self.void_selected,
                  bg="#ee0a24", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
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
    def use_status_label(code):
        try:
            return USE_STATUS_MAP.get(int(code), {}).get('label', str(code or '-'))
        except (TypeError, ValueError):
            return str(code or '-')

    @staticmethod
    def use_status_editable(code):
        try:
            return USE_STATUS_MAP.get(int(code), {}).get('editable', False)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def use_status_voidable(code):
        try:
            return USE_STATUS_MAP.get(int(code), {}).get('voidable', False)
        except (TypeError, ValueError):
            return False

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    def _selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.page_rows):
            return self.page_rows[idx]
        return None

    def resolve_dept(self):
        wh = self.warehouse_var.get()
        code = get_storage_code(wh)
        self.dept_id = USE_DEPT_MAP.get(wh)
        self.dept_name = wh

    # ---------------------------------------------------- 初始化数据（异步）
    def load_users(self):
        threading.Thread(target=self._user_thread, daemon=True).start()

    def _user_thread(self):
        try:
            r = self.controller.session.get(URL_USERS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-领用人] 加载失败: {e}")
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
        # 下拉显示文本为「姓名（部门）」：internalUser 返回 90+ 人且含大量非仓库岗
        # （财务部/采购部/客服部/业务部等）与合并账号（如「朱静，寻磊」），
        # 只显示姓名无法区分归属。报文仍传纯姓名（与安卓端一致），此处仅优化展示。
        for u in items:
            u['display'] = '%s（%s）' % (u['name'], u['orgName']) if u.get('orgName') else u['name']
        self.user_names = [u['display'] for u in items]
        self.user_map = {u['display']: u for u in items}
        if hasattr(self, 'user_cb') and self.user_cb.winfo_exists():
            self.user_cb.config(values=self.user_names)
            # 人员列表异步到达时窗口可能已先创建，回填编辑态已有的领用人（按姓名反查显示文本）
            if self.edit_use_man:
                disp = self._user_display(self.edit_use_man)
                if disp:
                    self.user_var.set(disp)

    def _user_display(self, name):
        """按真实姓名取下拉显示文本「姓名（部门）」，列表未加载/无匹配时原样返回"""
        if not name:
            return ''
        for u in self.internal_users:
            if u['name'] == name:
                return u.get('display') or name
        return name

    def load_out_locations(self, code=None):
        sc = code or get_storage_code(self.warehouse_var.get())
        if not sc:
            return
        threading.Thread(target=self._out_loc_thread, args=(sc,), daemon=True).start()

    def _out_loc_thread(self, sc):
        try:
            r = self.controller.session.get(URL_OUT_LOC, headers=HEADERS,
                                            params={'STORAGE_CODE': sc})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-库位] 加载失败: {e}")
            return
        arr = (data.get('data') or []) if isinstance(data, dict) else []
        locs = [l.get('location') for l in (arr if isinstance(arr, list) else [])
                if isinstance(l, dict) and l.get('location')]
        self.controller.after(0, lambda: setattr(self, 'out_locations', locs))

    # ------------------------------------------------------------------ 筛选
    def toggle_status(self, value):
        self.filter_status.set('' if self.filter_status.get() == value else value)
        self._update_status_buttons()
        self._apply_filters()

    def _update_status_buttons(self):
        cur = self.filter_status.get()
        for value, btn in self.status_buttons.items():
            if value == cur:
                btn.config(bg="#722ed1", fg="white")
            else:
                btn.config(bg="#e1e1e1", fg="#323233")

    def _apply_filters(self):
        rows = self.all_rows
        status = self.filter_status.get()
        if status:
            codes = [s.strip() for s in status.split(',') if s.strip()]
            rows = [r for r in rows if str(r.get('STATUS')) in codes]
        no = self.filter_use_no.get().strip().lower()
        man = self.filter_use_man.get().strip().lower()
        if no or man:
            kept = []
            for r in rows:
                bill = str(r.get('USE_NO') or '').lower()
                m = str(r.get('USE_MAN') or '').lower()
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
        self.filter_use_no.set('')
        self.filter_use_man.set('')
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
        wh = self.warehouse_var.get()
        sc = get_storage_code(wh)
        return {
            "USE_NO": self.filter_use_no.get() or '',
            "USE_MAN": self.filter_use_man.get() or '',
            "STATUS": self.filter_status.get() or '',
            "ORG_NAME": wh,
            "DEPARTMENT_ID": self.dept_id or '',
            "storage_code": sc,
            "BRAND_ID": '',
            "CREATED_AT_FROM": (self.start_cal.get() + ' 00:00:00') if self.start_cal.get() else '',
            "CREATED_AT_TO": (self.end_cal.get() + ' 23:59:59') if self.end_cal.get() else '',
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
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[内部领用管理] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用管理] 请求异常: {e}")
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
            messagebox.showinfo("查询结果", "未查询到内部领用单")

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
                row.get('USE_NO') or '-',
                self.use_status_label(row.get('STATUS')),
                row.get('USE_MAN') or '-',
                row.get('DEPARTMENT_NAME') or '-',
                row.get('WAREHOUSE_NAME') or '-',
                self.format_date(row.get('CREATED_AT')),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        total = len(self.filtered_rows)
        self.count_var.set(f"共 {total} 条内部领用单")
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
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条领用单")
            return
        bill_id = row.get('ID')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法查看明细")
            return
        self.count_var.set("加载明细中...")
        threading.Thread(target=self._detail_thread, args=(bill_id, row), daemon=True).start()

    def _detail_thread(self, bill_id, row):
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                master = (json.loads(r.text).get('data') or {})
        except Exception as e:
            print(f"[内部领用-主单] 异常: {e}")
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                items = (json.loads(r.text).get('data') or [])
                items = items if isinstance(items, list) else []
        except Exception as e:
            print(f"[内部领用-明细] 异常: {e}")
        payload = {
            'id': bill_id,
            'useNo': master.get('USE_NO') or row.get('USE_NO') or '',
            'statusCode': str(row.get('STATUS') or master.get('STATUS') or ''),
            'deptName': master.get('DEPARTMENT_NAME') or row.get('DEPARTMENT_NAME') or '',
            'useMan': master.get('USE_MAN') or row.get('USE_MAN') or '',
            'warehouseName': master.get('WAREHOUSE_NAME') or row.get('WAREHOUSE_NAME') or '',
            'remark': master.get('REMARK') or row.get('REMARK') or '',
            'items': items,
        }
        self.controller.after(0, lambda: self._show_detail_window(payload))

    def _show_detail_window(self, p):
        win = tk.Toplevel(self)
        win.title(f"领用单明细 - {p['useNo'] or p['id']}")
        win.geometry("720x680")
        win.transient(self)

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="领用单明细", bg="#f7f8fa", fg="#722ed1",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text=f"状态：{self.use_status_label(p['statusCode'])}",
                 bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        info = tk.Frame(win, bg="#ffffff")
        info.pack(fill=tk.X, padx=10, pady=5)
        for key, val in (("单号", p['useNo'] or '-'),
                         ("部门", p['deptName'] or '-'),
                         ("领用人", p['useMan'] or '-'),
                         ("出库仓", p['warehouseName'] or '-'),
                         ("备注", p['remark'] or '无')):
            line = tk.Frame(info, bg="#ffffff")
            line.pack(fill=tk.X, pady=2)
            tk.Label(line, text=key + "：", bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=9, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#ffffff", font=("微软雅黑", 10),
                     anchor="w", wraplength=560, justify="left").pack(side=tk.LEFT, fill=tk.X)

        tk.Label(win, text=f"领用明细（{len(p['items'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dcols = ["序号", "配件名称", "数量", "库位", "品牌", "单价"]
        dtree = ttk.Treeview(dframe, columns=dcols, show="headings", height=6)
        for i, col in enumerate(dcols):
            dtree.heading(col, text=col)
            dtree.column(col, width=[40, 220, 70, 100, 90, 90][i],
                         anchor="e" if col in ("数量", "单价") else "w")
        for idx, d in enumerate(p['items']):
            dtree.insert("", "end", values=(idx + 1,
                                            d.get('PART_NAME') or d.get('PART_NO') or '-',
                                            d.get('USE_NUM') or 0,
                                            d.get('OUT_LOCATION') or '-',
                                            d.get('BRAND_NAME') or '-',
                                            self.format_money(d.get('COST_PRICE'))))
        dsb = ttk.Scrollbar(dframe, orient="vertical", command=dtree.yview)
        dtree.configure(yscrollcommand=dsb.set)
        dtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 操作日志（默认折叠）
        self._log_expanded = False
        log_frame = tk.Frame(win, bg="#ffffff")
        log_btn = tk.Button(win, text=f"操作日志 ▼", bg="#f0f0f0", relief=tk.FLAT, anchor="w",
                            command=lambda: self._toggle_logs(log_frame, log_btn, p['id']))
        log_btn.pack(fill=tk.X, padx=10, pady=(8, 0))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        log_frame.pack_forget()

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        voidable = self.use_status_voidable(p['statusCode'])
        editable = self.use_status_editable(p['statusCode'])
        if editable:
            tk.Button(bar, text="编辑", bg="#722ed1", fg="white", padx=18, pady=4, bd=0,
                      command=lambda: [win.destroy(), self.open_edit(row_source(p))]).pack(side=tk.LEFT, padx=10)
        if voidable:
            tk.Button(bar, text="作废", bg="#ee0a24", fg="white", padx=18, pady=4, bd=0,
                      command=lambda: [win.destroy(), self.do_void(p['id'])]).pack(side=tk.LEFT, padx=10)
        if not editable and not voidable:
            tk.Label(bar, text="当前状态不可编辑/作废", bg="#f0f0f0", fg="#969799").pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=4,
                  command=win.destroy).pack(side=tk.RIGHT, padx=10)

        self.count_var.set(f"共 {len(self.filtered_rows)} 条内部领用单")

    def _toggle_logs(self, frame, btn, bill_id):
        if self._log_expanded:
            frame.pack_forget()
            btn.config(text="操作日志 ▼")
            self._log_expanded = False
            return
        for w in frame.winfo_children():
            w.destroy()
        threading.Thread(target=self._log_thread, args=(frame, bill_id), daemon=True).start()
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        btn.config(text="操作日志 ▲")
        self._log_expanded = True

    def _log_thread(self, frame, bill_id):
        try:
            r = self.controller.session.get(URL_LOGS, headers=HEADERS, params={
                'BILL_ID': bill_id, 'BILL_TYPE': LOG_BILL_TYPE,
                'limit': LOG_PAGE_SIZE, 'pageNum': 1, 'isShowLogs': True})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-日志] 异常: {e}")
            return
        rows = ((data.get('data') or {}).get('rows') if isinstance(data.get('data'), dict) else None)
        rows = rows if isinstance(rows, list) else []
        self.controller.after(0, lambda: self._render_logs(frame, rows))

    def _render_logs(self, frame, rows):
        if not rows:
            tk.Label(frame, text="无日志", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for log in rows:
            text = "[{}] {} {} {}".format(
                log.get('OPERATOR_NAME') or '-',
                self.format_date(log.get('OPERATE_DATE')),
                ('{} → {}'.format(log.get('BEFORE_VALUE'), log.get('AFTER_VALUE'))
                 if log.get('BEFORE_VALUE') or log.get('AFTER_VALUE') else ''),
                ('（%s）' % log['REMARK']) if log.get('REMARK') else '')
            tk.Label(frame, text=text, bg="#ffffff", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)

    # ------------------------------------------------------------------ 编辑
    def edit_selected(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条领用单")
            return
        if not self.use_status_editable(row.get('STATUS')):
            messagebox.showwarning("提示", "仅「待提交 / 经理审核驳回 / 部门审核驳回」状态可编辑")
            return
        self.open_edit(row_source(row))

    def open_edit(self, source):
        self.edit_id = str(source.get('ID') or '') if source else ''
        self.edit_mode = 'edit' if source else 'new'
        self.edit_raw = None
        self.edit_items = []
        self.edit_del_items = []
        self.edit_use_man = (source or {}).get('USE_MAN') or ''
        self.edit_use_man_id = (source or {}).get('USE_MAN_ID') or ''
        self.edit_use_phone = (source or {}).get('USE_PHONE') or ''
        self.edit_remark = (source or {}).get('REMARK') or ''
        wh = self.warehouse_var.get()
        self.edit_wh_code = get_storage_code(wh)
        self.edit_wh_name = wh
        # ORGANIZATION_ID：按领用仓库映射（USE_DEPT_MAP）
        self.edit_org_id = USE_DEPT_MAP.get(wh)
        # DEPARTMENT_ID/NAME：新建时留空，待选领用人后按其所属组织自动带出（对齐安卓端 openEdit）
        self.edit_dept_id = (source or {}).get('DEPARTMENT_ID') or ''
        self.edit_dept_name = (source or {}).get('DEPARTMENT_NAME') or ''

        if self.edit_id:
            self.count_var.set("加载中...")
            threading.Thread(target=self._edit_thread, args=(self.edit_id,), daemon=True).start()
        else:
            self._show_edit_window()

    def _edit_thread(self, bill_id):
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                master = (json.loads(r.text).get('data') or {})
        except Exception as e:
            print(f"[内部领用-编辑载入] 异常: {e}")
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                items = (json.loads(r.text).get('data') or [])
                items = items if isinstance(items, list) else []
        except Exception as e:
            print(f"[内部领用-编辑明细] 异常: {e}")
        self.edit_raw = master if master else {}
        self.edit_use_man = master.get('USE_MAN') or self.edit_use_man
        self.edit_use_man_id = master.get('USE_MAN_ID') or self.edit_use_man_id
        self.edit_use_phone = master.get('USE_PHONE') or self.edit_use_phone
        self.edit_remark = master.get('REMARK') or self.edit_remark
        self.edit_wh_code = master.get('STORAGE_CODE') or self.edit_wh_code
        self.edit_wh_name = master.get('WAREHOUSE_NAME') or self.edit_wh_name
        self.edit_dept_id = master.get('DEPARTMENT_ID', self.edit_dept_id)
        self.edit_dept_name = master.get('DEPARTMENT_NAME') or self.edit_dept_name
        # ORGANIZATION_ID 归仓：优先主单原值，缺失按领用仓库映射
        self.edit_org_id = master.get('ORGANIZATION_ID') or USE_DEPT_MAP.get(self.edit_wh_name) \
            or self.edit_org_id

        self.edit_items = [{
            '_orig': d,
            'PART_ID': d.get('PART_ID'), 'PART_NO': d.get('PART_NO'),
            'PART_NAME': d.get('PART_NAME'), 'BRAND_ID': d.get('BRAND_ID'),
            'BRAND_NAME': d.get('BRAND_NAME'), 'COST_PRICE': d.get('COST_PRICE'),
            'USE_NUM': d.get('USE_NUM') or 1, 'OUT_LOCATION': d.get('OUT_LOCATION') or '',
            'AVAILABLE_STOCK_QUANTITY': d.get('AVAILABLE_STOCK_QUANTITY'),
            'STORAGE_CODE': d.get('STORAGE_CODE') or self.edit_wh_code,
            'STORAGE_NAME': d.get('STORAGE_NAME') or self.edit_wh_name,
            'WAREHOUSE_ID': d.get('WAREHOUSE_ID'), 'loList': d.get('loList') or [],
        } for d in items]
        if not self.edit_items:
            self.add_item_row()
        self.controller.after(0, self._show_edit_window)

    def add_item_row(self):
        self.edit_items.append({
            '_orig': None, 'PART_ID': None, 'PART_NO': '', 'PART_NAME': '',
            'BRAND_ID': None, 'BRAND_NAME': '', 'COST_PRICE': 0, 'USE_NUM': 1,
            'OUT_LOCATION': '', 'AVAILABLE_STOCK_QUANTITY': 0,
            'STORAGE_CODE': self.edit_wh_code, 'STORAGE_NAME': self.edit_wh_name,
            'WAREHOUSE_ID': None, 'loList': [],
        })

    def remove_item(self, d):
        if d.get('_orig') and d['_orig'].get('ID') is not None:
            self.edit_del_items.append(dict(d['_orig']))
        self.edit_items.remove(d)
        if not self.edit_items:
            self.add_item_row()
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_items()

    def _show_edit_window(self):
        win = tk.Toplevel(self)
        win.title("编辑领用单" if self.edit_id else "新建领用单")
        win.geometry("820x720")
        win.transient(self)
        self.edit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="编辑领用单" if self.edit_id else "新建领用单",
                 bg="#f7f8fa", fg="#722ed1", font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        base = tk.LabelFrame(win, text="基本信息", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        base.pack(fill=tk.X, padx=10, pady=5, ipadx=6, ipady=4)

        r1 = tk.Frame(base, bg="#f0f0f0")
        r1.pack(fill=tk.X, pady=2)
        tk.Label(r1, text="领用仓库:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_wh_var = tk.StringVar(value=self.edit_wh_name or "")
        wh_cb = ttk.Combobox(r1, textvariable=self.edit_wh_var,
                            values=list(self.controller.options.keys()), state="readonly", width=12)
        if self.edit_wh_name in list(self.controller.options.keys()):
            wh_cb.set(self.edit_wh_name)
        wh_cb.pack(side=tk.LEFT, padx=4)
        wh_cb.bind("<<ComboboxSelected>>", self._on_edit_wh)

        tk.Label(r1, text="领用部门:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT, padx=(15, 0))
        # 领用部门为只读展示：选领用人后按其所属组织自动带出，故用 StringVar 以便实时刷新
        self.edit_dept_var = tk.StringVar(value=self.edit_dept_name or "(选领用人自动带出)")
        tk.Label(r1, textvariable=self.edit_dept_var, bg="#f0f0f0",
                 fg="#722ed1").pack(side=tk.LEFT)

        r2 = tk.Frame(base, bg="#f0f0f0")
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text="领用人:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        # 人员列表为异步加载，需保留 StringVar 引用，加载完成后可回填编辑态已有值
        # 显示用「姓名（部门）」，故按姓名反查显示文本；宽度放宽以容纳部门后缀
        self.user_var = tk.StringVar(value=self._user_display(self.edit_use_man))
        self.user_cb = ttk.Combobox(r2, textvariable=self.user_var,
                                    values=self.user_names, state="readonly", width=18)
        self.user_cb.pack(side=tk.LEFT, padx=4)
        self.user_cb.bind("<<ComboboxSelected>>", self._on_edit_user)

        tk.Label(r2, text="联系电话:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT, padx=(15, 0))
        self.edit_phone_var = tk.StringVar(value=self.edit_use_phone or '')
        ttk.Entry(r2, textvariable=self.edit_phone_var, width=14).pack(side=tk.LEFT, padx=4)

        r3 = tk.Frame(base, bg="#f0f0f0")
        r3.pack(fill=tk.X, pady=2)
        tk.Label(r3, text="备注:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_remark_var = tk.StringVar(value=self.edit_remark or '')
        ttk.Entry(r3, textvariable=self.edit_remark_var, width=62).pack(side=tk.LEFT, padx=4)

        dhead = tk.Frame(win, bg="#f0f0f0")
        dhead.pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(dhead, text="领用明细", bg="#f0f0f0", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(dhead, text="+ 添加配件", command=self.open_parts_picker,
                  bg="#722ed1", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=8)
        self.edit_total_var = tk.StringVar(value="")
        tk.Label(dhead, textvariable=self.edit_total_var, bg="#f0f0f0",
                 fg="#722ed1", font=("微软雅黑", 10, "bold")).pack(side=tk.RIGHT)

        self.items_frame = tk.Frame(win, bg="#ffffff")
        self.items_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        self._render_edit_items()

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        tk.Button(bar, text="保存草稿", command=self.save_draft,
                  bg="#722ed1", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="提交", command=self.submit_bill,
                  bg="#07c160", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="取消", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def _on_edit_wh(self, event=None):
        name = self.edit_wh_var.get()
        self.edit_wh_name = name
        self.edit_wh_code = get_storage_code(name)
        # 切换仓库只改 ORGANIZATION_ID（按仓库映射）；
        # DEPARTMENT_ID/NAME 只由「领用人」所属组织决定，切仓库不动（对齐安卓端 onWarehouseConfirm）
        self.edit_org_id = USE_DEPT_MAP.get(name)
        self.load_out_locations(self.edit_wh_code)

    def _on_edit_user(self, event=None):
        """选择领用人：领用人 → 电话 + 领用部门（所属组织）自动带出

        对齐安卓端 onUserConfirm：部门**无条件覆盖**为领用人的 orgId/orgName
        （领用人无组织时置空，不保留仓库映射或其它残留值）。
        """
        # 下拉项是「姓名（部门）」，报文只认纯姓名，必须取 u['name'] 而非显示文本
        text = self.user_cb.get()
        u = self.user_map.get(text)
        self.edit_use_man = u['name'] if u else text
        self.edit_use_man_id = u['id'] if u else ''
        self.edit_use_phone = u['phone'] if u else ''
        self.edit_dept_id = u['orgId'] if u else ''
        self.edit_dept_name = u['orgName'] if u else ''
        self.edit_phone_var.set(self.edit_use_phone)
        # 界面「领用部门」为只读展示，需同步刷新
        if hasattr(self, 'edit_dept_var'):
            self.edit_dept_var.set(self.edit_dept_name or "(选领用人自动带出)")

    def _render_edit_items(self):
        for w in self.items_frame.winfo_children():
            w.destroy()
        for d in self.edit_items:
            row = tk.Frame(self.items_frame, bg="#f7f8fa")
            row.pack(fill=tk.X, pady=2, padx=2)
            tk.Label(row, text=d.get('PART_NAME') or d.get('PART_NO') or '(新配件)',
                     bg="#f7f8fa", width=24, anchor="w").pack(side=tk.LEFT, padx=2)
            amt_var = tk.StringVar(value=str(d.get('USE_NUM') or 0))
            e = ttk.Entry(row, textvariable=amt_var, width=8)
            e.pack(side=tk.LEFT, padx=2)

            def on_amt(event=None, d=d, var=amt_var):
                try:
                    d['USE_NUM'] = float(var.get() or 0)
                except ValueError:
                    d['USE_NUM'] = 0
                self._update_edit_total()

            e.bind("<KeyRelease>", on_amt)
            loc_var = tk.StringVar(value=d.get('OUT_LOCATION') or '')
            loc_cb = ttk.Combobox(row, textvariable=loc_var,
                                 values=self.out_locations or [d.get('OUT_LOCATION') or ''],
                                 width=14)
            loc_cb.pack(side=tk.LEFT, padx=2)

            def on_loc(event=None, d=d, var=loc_var):
                d['OUT_LOCATION'] = var.get()

            loc_cb.bind("<<ComboboxSelected>>", on_loc)
            tk.Button(row, text="删", bg="#ee0a24", fg="white", bd=0, width=3,
                      command=lambda dd=d: self.remove_item(dd)).pack(side=tk.LEFT, padx=2)
        self._update_edit_total()

    def _update_edit_total(self):
        total = 0.0
        for d in self.edit_items:
            try:
                total += float(d.get('COST_PRICE') or 0) * float(d.get('USE_NUM') or 0)
            except (TypeError, ValueError):
                pass
        if hasattr(self, 'edit_total_var'):
            self.edit_total_var.set("合计金额：" + self.format_money(total))

    # 配件搜索
    def open_parts_picker(self):
        if not self.edit_wh_code:
            messagebox.showwarning("提示", "请先选择领用仓库")
            return
        self.parts_popup = tk.Toplevel(self)
        self.parts_popup.title("选择配件")
        self.parts_popup.geometry("680x560")
        self.parts_popup.transient(self)
        self.parts_kw = tk.StringVar()
        pf = tk.Frame(self.parts_popup)
        pf.pack(fill=tk.X, padx=10, pady=6)
        ttk.Entry(pf, textvariable=self.parts_kw, width=30).pack(side=tk.LEFT, padx=4)
        tk.Button(pf, text="搜索", command=self.search_parts,
                  bg="#722ed1", fg="white", bd=0, padx=12).pack(side=tk.LEFT, padx=4)

        self.parts_list = tk.Listbox(self.parts_popup, selectmode=tk.EXTENDED)
        self.parts_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        tk.Button(self.parts_popup, text="确认添加",
                  command=self.confirm_parts, bg="#07c160", fg="white", bd=0, padx=14).pack(pady=6)

    def search_parts(self):
        kw = (self.parts_kw.get() or '').strip()
        has_cn = bool(re.search(r'[一-鿿]', kw))
        sc = self.edit_wh_code
        params = {
            'PART_NO': '' if has_cn else kw,
            'PART_NAME': kw if has_cn else '',
            'STORAGE_NAME': '',
            'storage_code': sc,
        }
        threading.Thread(target=self._parts_thread, args=(params,), daemon=True).start()

    def _parts_thread(self, params):
        try:
            r = self.controller.session.get(URL_PARTS, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-配件] 异常: {e}")
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
            self.parts_list.insert(tk.END, f"{p.get('PART_NAME') or '-'} | {p.get('PART_NO')} | {p.get('BRAND_NAME') or ''}")

    def confirm_parts(self):
        sel = self.parts_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "请勾选配件")
            return
        for i in sel:
            p = self.parts_data[i]
            if any(it.get('PART_ID') == p.get('PART_ID') for it in self.edit_items):
                continue
            self.edit_items.append({
                '_orig': None, 'PART_ID': p.get('PART_ID'), 'PART_NO': p.get('PART_NO'),
                'PART_NAME': p.get('PART_NAME'), 'BRAND_ID': p.get('BRAND_ID'),
                'BRAND_NAME': p.get('BRAND_NAME'), 'COST_PRICE': p.get('COST_PRICE'),
                'USE_NUM': 1, 'OUT_LOCATION': '',
                'AVAILABLE_STOCK_QUANTITY': p.get('AVAILABLE_STOCK_QUANTITY'),
                'STORAGE_CODE': p.get('STORAGE_CODE') or self.edit_wh_code,
                'STORAGE_NAME': p.get('STORAGE_NAME') or self.edit_wh_name,
                'WAREHOUSE_ID': p.get('WAREHOUSE_ID'), 'loList': p.get('loList') or [],
            })
        self.parts_popup.destroy()
        self._render_edit_items()

    # ------------------------------------------------------------ 保存/提交
    def build_item_list(self, is_add):
        out = []
        for d in self.edit_items:
            if not is_add and d.get('_orig'):
                item = dict(d['_orig'])
                item['USE_NUM'] = float(d.get('USE_NUM') or 0)
                item['OUT_LOCATION'] = d.get('OUT_LOCATION') or ''
                item['loList'] = d.get('loList') if isinstance(d.get('loList'), list) and d['loList'] else (d['_orig'].get('loList') or [])
                out.append(item)
            else:
                out.append({
                    'PART_ID': d.get('PART_ID'), 'PART_NO': d.get('PART_NO'),
                    'PART_NAME': d.get('PART_NAME'), 'BRAND_ID': d.get('BRAND_ID'),
                    'BRAND_NAME': d.get('BRAND_NAME'), 'COST_PRICE': d.get('COST_PRICE'),
                    'USE_NUM': float(d.get('USE_NUM') or 0), 'OUT_LOCATION': d.get('OUT_LOCATION') or '',
                    'AVAILABLE_STOCK_QUANTITY': d.get('AVAILABLE_STOCK_QUANTITY'),
                    'STORAGE_CODE': d.get('STORAGE_CODE') or self.edit_wh_code,
                    'STORAGE_NAME': d.get('STORAGE_NAME') or self.edit_wh_name,
                    'WAREHOUSE_ID': d.get('WAREHOUSE_ID'), 'DR': 0,
                    'loList': d.get('loList') or [], 'MOQ': None, 'MPQ': None, 'UNIT': None,
                })
        return out

    def build_payload(self, mode):
        """构造报文，对齐 web 端 addEditDetail.saveInfoFn（依据见 AUDIT_DEFAULTS 处注释）。

        报文内容由「有无 ID/USE_NO」决定，端点由按钮决定：
          · 既有单 → edit（保存）/ submit（提交）：发整单，带 ID/USE_NO 与后端审计字段
          · 新建单 → add（保存）/ submit（新建即提交）：只发 9 个业务字段，不带 ID/USE_NO
        即 add 与「新建即 submit」报文体相同，区别只在端点 URL。
        """
        is_add = (mode == 'add')
        item_list = self.build_item_list(is_add)
        user_fields = {
            'DEPARTMENT_ID': self.edit_dept_id,
            'DEPARTMENT_NAME': self.edit_dept_name,
            'storage_code': self.edit_wh_code,
            'USE_MAN': self.edit_use_man,
            'USE_MAN_ID': self.edit_use_man_id,
            'USE_PHONE': self.edit_use_phone,
            'REMARK': self.edit_remark_var.get() if hasattr(self, 'edit_remark_var') else self.edit_remark,
            'isDisabledOrgSelect': True,
            'itemList': item_list,
            'delItemList': self.edit_del_items,
        }
        # has_id 以 edit_id 为准兜底：queryById 失败时 edit_raw 可能为空，
        # 只认 edit_raw 会把既有单误判成新建，保存时重复走 /add 生成重复单。
        has_id = bool(self.edit_id) or bool(self.edit_raw and self.edit_raw.get('ID') is not None)
        if has_id:
            no_tax = round(sum((float(it.get('COST_PRICE') or 0) * float(it.get('USE_NUM') or 0))
                               for it in item_list), 2)
            current_status = (self.edit_raw or {}).get('STATUS')
            if current_status is None:
                current_status = 12461001      # 兜底「待提交」
            # 既有单：整单原样回传（含后端维护的 CREATED_AT / UPDATED_AT / RECORD_VERSION
            # 与 ORGANIZATION_ID），queryById 若未返回某项则按默认值 / 仓库映射兜底补齐。
            record = dict(self.edit_raw or {})
            if record.get('ID') is None and self.edit_id:
                try:
                    record['ID'] = int(self.edit_id)
                except (TypeError, ValueError):
                    record['ID'] = self.edit_id
            for k, v in AUDIT_DEFAULTS.items():
                if record.get(k) is None or record.get(k) == '':
                    record[k] = v
            if record.get('ORGANIZATION_ID') in (None, ''):
                # ORGANIZATION_ID 归仓：主单原值优先，缺失按「领用仓库」映射兜底
                record['ORGANIZATION_ID'] = self.edit_org_id
            payload = {**record, **user_fields,
                       'NO_TAX_AMOUNT': no_tax, 'STATUS': current_status}
        else:
            # 新建单：只发业务字段，不带 ORGANIZATION_ID / 审计字段 / 整单骨架。
            #
            # web 端新建时 addFn() 只传 options、不传 row，formVo 的基底就是 resetFormVo 的
            # 13 个业务字段，因此 add 与「新建即 submit」实际只发 9 个字段：
            #   DEPARTMENT_ID / DEPARTMENT_NAME / storage_code / USE_MAN / USE_MAN_ID /
            #   USE_PHONE / isDisabledOrgSelect / itemList / delItemList
            # （REMARK 填了才带，空串被 web 端框架层剔除。）
            #
            # HAR 里 add 报文出现的 ORGANIZATION_ID:1152 / CREATED_AT / RECORD_VERSION:5 /
            # WAREHOUSE_NAME / DEALER_CODE / DR / NO_TAX_AMOUNT / STATUS 等，全部是组件实例
            # 上一次编辑的状态残留脏数据（openDialog 的 $.extend(formVo, resetFormVo) 只覆盖
            # resetFormVo 那几个键、不清除其余键），**不是业务构造，不可照抄**。
            # 佐证：addEditDetail 里 ORGANIZATION_ID 全文只出现 1 次，且是领用人的
            # ORGANIZATION_ID 被赋给 formVo.DEPARTMENT_ID，从不给 formVo.ORGANIZATION_ID 赋值；
            # 剥掉残留后 add 报文正好 9 字段，与安卓端 InternalUseManage 的 add 一致。
            # 后端靠 storage_code 识别仓库，审计值由后端按登录态生成。
            payload = dict(user_fields)
        return payload

    def save_draft(self):
        if not self.edit_wh_code:
            messagebox.showwarning("提示", "请选择领用仓库")
            return
        if not self.edit_items:
            messagebox.showwarning("提示", "请至少添加一条领用配件")
            return
        if not self.edit_use_man:
            messagebox.showwarning("提示", "请选择领用人")
            return
        payload = self.build_payload('edit' if self.edit_id else 'add')
        self.count_var.set("保存中...")
        threading.Thread(target=self._save_thread, args=(payload, not self.edit_id), daemon=True).start()

    def submit_bill(self):
        if not self.edit_wh_code:
            messagebox.showwarning("提示", "请选择领用仓库")
            return
        if not self.edit_items:
            messagebox.showwarning("提示", "请至少添加一条领用配件")
            return
        if not self.edit_use_man:
            messagebox.showwarning("提示", "请选择领用人")
            return
        if any(not it.get('OUT_LOCATION') for it in self.edit_items):
            messagebox.showwarning("提示", "请为每条配件选择出库库位")
            return
        if not messagebox.askyesno("确认提交", "提交后将进入部门审核流程，确认提交？"):
            return
        payload = self.build_payload('submit')
        self.count_var.set("提交中...")
        threading.Thread(target=self._submit_thread, args=(payload,), daemon=True).start()

    def _save_thread(self, payload, is_add):
        try:
            url = URL_ADD if is_add else URL_EDIT
            r = self.controller.session.post(url, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-保存] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"保存失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "保存失败"
            self.controller.after(0, lambda: messagebox.showerror("保存失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", "已保存草稿"))
        self.controller.after(0, self._after_saved)

    def _submit_thread(self, payload):
        try:
            r = self.controller.session.post(URL_SUBMIT, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-提交] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"提交失败: {e}"))
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

    # ------------------------------------------------------------------ 作废
    def void_selected(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条领用单")
            return
        if not self.use_status_voidable(row.get('STATUS')):
            messagebox.showwarning("提示", "仅「待提交 / 经理审核驳回 / 部门审核驳回」状态可作废")
            return
        self.do_void(row.get('ID'))

    def do_void(self, bill_id):
        if not messagebox.askyesno("确认作废", "作废后该领用单不可恢复，确认作废？"):
            return
        self.count_var.set("作废中...")
        threading.Thread(target=self._void_thread, args=(bill_id,), daemon=True).start()

    def _void_thread(self, bill_id):
        url = URL_CANCEL_TMPL.format(id=bill_id)
        try:
            r = self.controller.session.put(url, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-作废] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"作废失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "作废失败"
            self.controller.after(0, lambda: messagebox.showerror("作废失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", "作废成功"))
        self.controller.after(0, self.query)

    # ------------------------------------------------------------------ 打印
    def open_print_preview(self):
        rows = [r for r in self.all_rows if str(r.get('STATUS')) != str(USE_CANCELLED_STATUS)]
        if not rows:
            messagebox.showinfo("提示", "请先查询领用单")
            return
        # 多选：勾选优先；无勾选则打印当前过滤结果全部（剔除已作废）
        ids = list(self.selected_ids) if self.selected_ids else [str(r['ID']) for r in rows]
        valid = [r for r in rows if str(r['ID']) in ids]
        if not valid:
            valid = rows
        nos = ",".join("'%s'" % r['USE_NO'] for r in valid if r.get('USE_NO'))
        if not nos:
            messagebox.showwarning("提示", "所选单据缺少单号，无法打印")
            return
        self.count_var.set("加载打印数据...")
        threading.Thread(target=self._print_thread, args=(nos, valid), daemon=True).start()

    def _print_thread(self, nos, valid):
        try:
            r = self.controller.session.get(URL_PRINT, headers=HEADERS, params={'USE_NOS': nos})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-打印] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"打印数据加载失败: {e}"))
            return
        flat = (data.get('data') or []) if isinstance(data.get('data'), list) else []
        groups = []
        for row in flat:
            grp = next((g for g in groups if g['header'].get('USE_NO') == row.get('USE_NO')), None)
            if not grp:
                grp = {'header': row, 'items': []}
                groups.append(grp)
            grp['items'].append(row)
        for g in groups:
            g['totalNum'] = sum(float(it.get('USE_NUM') or 0) for it in g['items'])
        self.controller.after(0, lambda: self._show_print_window(groups))

    def _show_print_window(self, groups):
        self.count_var.set(f"共 {len(self.filtered_rows)} 条内部领用单")
        win = tk.Toplevel(self)
        win.title("内部领用单打印预览")
        win.geometry("760x680")
        win.transient(self)
        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text=f"打印预览（{len(groups)} 单）", bg="#f7f8fa", fg="#722ed1",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        canvas = tk.Canvas(win, bg="#ffffff")
        canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        body = tk.Text(canvas, wrap=tk.WORD, font=("微软雅黑", 9), bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True)
        body.tag_configure("title", font=("微软雅黑", 14, "bold"), justify="center")
        body.tag_configure("h", font=("微软雅黑", 10, "bold"))
        for g in groups:
            h = g['header']
            body.insert(tk.END, "\n内部领用\n", "title")
            info = (f"领用仓库：{h.get('WAREHOUSE_NAME') or h.get('STORAGE_NAME') or ''}    "
                    f"领用部门：{h.get('DEPARTMENT_NAME') or ''}\n"
                    f"单据号：{h.get('USE_NO') or ''}    领用人：{h.get('USE_MAN') or ''}\n"
                    f"领用人电话：{h.get('USE_PHONE') or ''}    摘要：{h.get('REMARK') or ''}\n")
            body.insert(tk.END, info)
            body.insert(tk.END, "品牌 | 产品编码 | 产品名称 | 分类2 | 数量 | 库位\n", "h")
            for it in g['items']:
                body.insert(tk.END, f"{it.get('BRAND_NAME') or ''} | {it.get('PART_NO') or ''} | "
                                    f"{it.get('PART_NAME') or ''} | {it.get('CATEGORY_TWO') or ''} | "
                                    f"{it.get('USE_NUM') or 0} | {it.get('OUT_LOCATION') or ''}\n")
            body.insert(tk.END, f"合计数量：{g['totalNum']}\n")
            body.insert(tk.END, "─" * 60 + "\n")
        body.configure(state=tk.DISABLED)

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=8)
        tk.Button(bar, text="打 印", command=lambda: self.print_via_clodop(groups, win),
                  bg="#722ed1", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def print_via_clodop(self, groups, win):
        """复用 CLodop WebSocket 协议（对齐 picking_shipping.py）打印内部领用单"""
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
                    f"printtask=内部领用单打印{delim}"
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

    @staticmethod
    def _build_single_html(group):
        h = group['header']
        rows = "".join(
            f"<tr><td>{it.get('BRAND_NAME') or ''}</td>"
            f"<td style='text-align:center'>{it.get('PART_NO') or ''}</td>"
            f"<td style='text-align:left'>{it.get('PART_NAME') or ''}</td>"
            f"<td>{it.get('CATEGORY_TWO') or ''}</td>"
            f"<td>{it.get('USE_NUM') or 0}</td>"
            f"<td>{it.get('OUT_LOCATION') or ''}</td></tr>"
            for it in group['items'])
        return (
            "<style>div{width:97%} body{margin:0;padding:0}</style>"
            "<div class='print-page'>"
            "<div class='print-page-title' style='text-align:center;font-size:20px;font-weight:700'>内部领用</div>"
            "<div class='print-page-info' style='font-size:13px'>"
            f"<div>领用仓库：{h.get('WAREHOUSE_NAME') or h.get('STORAGE_NAME') or ''}　领用部门：{h.get('DEPARTMENT_NAME') or ''}　单据号：{h.get('USE_NO') or ''}</div>"
            f"<div>领用人：{h.get('USE_MAN') or ''}　领用人电话：{h.get('USE_PHONE') or ''}</div>"
            f"<div>摘要：{h.get('REMARK') or ''}</div>"
            "</div>"
            "<table border='1' cellspacing='0' style='width:98%;font-size:12px;border-collapse:collapse;text-align:center'>"
            "<thead><tr><th>品牌</th><th>产品编码</th><th>产品名称</th><th>分类2</th><th>领用数量</th><th>出库库位</th></tr></thead>"
            "<tbody>" + rows + "</tbody>"
            f"<tfoot><tr><td colspan='4'/><td colspan='2' style='font-weight:bold'>合计数量：{group['totalNum']}</td></tr></tfoot>"
            "</table></div>"
        )


def row_source(row):
    """明细返回的行（全大写键）转成编辑接口需要的 source 结构"""
    if row is None:
        return {}
    return {
        'ID': row.get('ID'),
        'USE_NO': row.get('USE_NO'),
        'STATUS': row.get('STATUS'),
        'USE_MAN': row.get('USE_MAN'),
        'USE_MAN_ID': row.get('USE_MAN_ID'),
        'USE_PHONE': row.get('USE_PHONE'),
        'REMARK': row.get('REMARK'),
        'STORAGE_CODE': row.get('STORAGE_CODE'),
        'WAREHOUSE_NAME': row.get('WAREHOUSE_NAME'),
        'DEPARTMENT_ID': row.get('DEPARTMENT_ID'),
        'DEPARTMENT_NAME': row.get('DEPARTMENT_NAME'),
    }

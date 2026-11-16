# -*- coding: utf-8 -*-
"""其他支付管理（报销管理模块 菜单 3/3）

对齐 fycarg-pda 安卓端：
- src/views/OtherPayManage.vue
- src/service/otherPay.js   （复用 feeExpense.js 的 CRUD/附件/科目/员工接口，仅新增往来单位查询）
- src/config/otherPay.js    （feeType = 98041002，区别于费用报销 98041001）
- src/service/feeExpense.js / src/config/feeExpense.js （与菜单1 共用的接口与字典）

接口清单（与菜单1「费用报销管理」共用，除往来单位查询外完全一致）：
- 列表   GET  /dmscloud.part/feeExpenseManager/feeExpenseManagerQueryOemInfo
- 明细   GET  /dmscloud.part/feeExpenseManager/feeExpenseManagerDetailData?id=
- 保存   POST /dmscloud.part/feeExpenseManager/feeExpenseManagerSave   (typeOperator '1'草稿 / '2'提交)
- 作废   POST /dmscloud.part/feeExpenseManager/feeExpenseManagerDelete (body {id}，仅草稿)
- 科目   GET  /dmscloud.financeAbutment/accountDefinition/getAccountDefinitionByParams?accountType=FY
- 员工   GET  /dcscloud.basedata/basedata/employees/searchUserInfo
- 组织树 GET  /dcscloud.basedata/company/org/tree
- 附件上传 POST /dmscloud.basedata/file (multipart，字段 dmsFile)
- 附件配置 GET  /dmscloud.basedata/file/billFiles/{billType}/{billId}
- 附件下载 GET  /dmscloud.basedata/file/billFilesReview/{billType}/{fileKey}
- 往来单位 GET  /dmscloud.part/supplierInfo/supplierBase
            ?SUPPLIER_STATUS=10821001&isShowFYG=1&AUDIT_STATUS=88281003[&SUPPLIER_NAME=]

与「费用报销管理（菜单1）」的关键差异：
1. 单据类型 feeType = 98041002（报销为 98041001）；单号前缀 ZZHJFYQT…。
2. 多「往来单位」字段：dealerCode 存 supplier_no（如 G4-004），dealerName 存 supplier_name
   （如 仓库水电费）。来源于 supplierInfo/supplierBase。查询与保存均携带。
3. 与报销相反——保存报文【始终】携带 dealerCode/dealerName（即便编辑态也不置 None）。
   报销模块编辑时置 None 是因为报销单无往来单位概念；本模块往来单位是核心字段。
4. 列表多一列「往来单位」；明细弹窗多一段「支付方式」（payDetailDtoList：
   payBankNo / payBankName / courseInfo / payRemark / payAmount）。
5. 查询额外携带 applyName（制单人显示名）与 created_by（制单人 code），二者并存对齐 HAR。
6. 其余状态字典（9805）/ 日志字典（9806）/ 部门兜底表 / 附件业务类型 与报销完全共用。

身份信息说明（同菜单1）：Python 端登录仅存 cookies，未持久化 employeeName/employeeId。
故申请人由用户从「员工下拉」显式选择；部门由仓库经组织树解析 + 兜底表降级；
往来单位由用户从「供应商下拉」显式选择（dealerCode=supplier_no）。
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

# 复用菜单1（费用报销管理）的全部纯常量与工具函数，避免两处维护
from reimbursement_manage import (
    HEADERS, BASE, PART,
    URL_QUERY, URL_DETAIL, URL_SAVE, URL_VOID,
    URL_ACCOUNT, URL_EMPLOYEE, URL_ORG_TREE, URL_FILE_UPLOAD,
    URL_ATTACH_CFG, URL_ATTACH_FILE,
    ATTACHMENT_BILL_TYPE, ATTACH_VALID, ATTACH_CAN_DELETE,
    QUERY_LIMIT, PAGE_SIZE,
    FEE_STATUS_MAP, FEE_STATUS_FILTERS, FEE_STATUS_DRAFT,
    FEE_LOG_TYPE_MAP, FEE_DEPT_FALLBACK, LOGISTICS_ORG_CODE,
    DETAIL_COLUMNS, DETAIL_WIDTHS,
    MIME_MAP, is_image_file, guess_mime,
)

# 单据类型（固定 其他支付，字典 9804 组）—— 与报销 98041001 严格区分
OTHER_PAY_FEE_TYPE = 98041002

# 往来单位（供应商）接口与固定查询条件（HAR 实测三个参数恒定携带）
URL_SUPPLIER = BASE + '/dmscloud.part/supplierInfo/supplierBase'
SUPPLIER_QUERY = {
    'SUPPLIER_STATUS': 10821001,
    'isShowFYG': 1,
    'AUDIT_STATUS': 88281003,
}
SUPPLIER_PAGE_LIMIT = 500

# 列表列定义（在报销列基础上多一列「往来单位」）
COLUMNS = ["序号", "支付单号", "状态", "申请部门", "往来单位", "申请人", "金额", "申请日期", "费用类型"]
COLUMN_WIDTHS = [50, 170, 90, 120, 140, 90, 120, 150, 130]


class OtherPayManagePage(BasePage):
    """其他支付管理页面（新建 / 编辑 / 提交 / 查询 / 作废 / 往来单位选择）"""

    def __init__(self, parent, controller):
        self.all_rows = []
        self.filtered_rows = []
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.queried = False
        self.loading = False

        # 筛选条件
        self.filter_status = tk.StringVar(value='')
        self.filter_bill_no = tk.StringVar(value='')
        self.filter_apply_name = tk.StringVar(value='')
        self.filter_apply_code = tk.StringVar(value='')
        self.filter_dept_code = tk.StringVar(value='')
        self.filter_dept_name = tk.StringVar(value='')
        self.filter_dealer_code = tk.StringVar(value='')   # supplier_no
        self.filter_dealer_name = tk.StringVar(value='')

        # 部门解析结果
        self.dept_code = ''
        self.dept_name = ''
        self.dept_org_id = None
        self.dept_options = []

        # 科目（费用类型）
        self.accounts = []
        self.account_names = []
        self.account_map = {}

        # 员工
        self.employees = []
        self.employee_names = []
        self.employee_map = {}

        # 往来单位（供应商）
        self.suppliers = []          # [{'name','code','fullName','phone','supplierId'}]
        self.supplier_names = []
        self.supplier_map = {}       # name -> supplier_no

        # 编辑态
        self.edit_id = ''
        self.edit_details = []
        self.edit_attachments = []
        self.edit_detail_deletes = []
        self.edit_attach_deletes = []
        self.edit_apply_name = ''
        self.edit_apply_code = ''
        self.edit_dealer_code = ''   # supplier_no
        self.edit_dealer_name = ''
        self.edit_remark = ''
        self.edit_dept_code = ''
        self.edit_dept_name = ''
        self.edit_dept_org_id = None
        self.edit_win = None

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

        # 异步初始化：组织树、科目、员工、往来单位
        self.load_org_tree()
        self.load_accounts()
        self.load_employees()
        self.load_suppliers()

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
        tk.Label(row1, text="（用于解析申请部门）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=5)

        row2 = tk.Frame(frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.status_buttons = {}
        for label, value in FEE_STATUS_FILTERS:
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

        tk.Label(row3, text="部门:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.dept_var = tk.StringVar(value="全部部门")
        self.dept_cb = ttk.Combobox(row3, textvariable=self.dept_var,
                                    values=["全部部门"], state="readonly", width=12)
        self.dept_cb.pack(side=tk.LEFT, padx=2)
        self.dept_cb.bind("<<ComboboxSelected>>", self.on_dept_selected)

        row4 = tk.Frame(frame, bg="#f0f0f0")
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="支付单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row4, textvariable=self.filter_bill_no, width=18).pack(side=tk.LEFT, padx=2)

        tk.Label(row4, text="往来单位:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.filter_dealer_var = tk.StringVar(value="全部")
        self.filter_dealer_cb = ttk.Combobox(row4, textvariable=self.filter_dealer_var,
                                             values=["全部"], state="readonly", width=14)
        self.filter_dealer_cb.pack(side=tk.LEFT, padx=2)
        self.filter_dealer_cb.bind("<<ComboboxSelected>>", self.on_filter_dealer_selected)

        row5 = tk.Frame(frame, bg="#f0f0f0")
        row5.pack(fill=tk.X, pady=2)
        tk.Label(row5, text="制单人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.apply_var = tk.StringVar()
        self.apply_cb = ttk.Combobox(row5, textvariable=self.apply_var,
                                     values=[], state="readonly", width=12)
        self.apply_cb.pack(side=tk.LEFT, padx=2)
        self.apply_cb.bind("<<ComboboxSelected>>", self.on_apply_selected)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 14, "pady": 4,
                     "bd": 0, "activebackground": "#45a049"}
        tk.Button(row5, text="查询支付单", command=self.query, **btn_style).pack(side=tk.LEFT, padx=12)
        tk.Button(row5, text="重置", command=self.reset_form,
                  bg="#e1e1e1", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="其他支付单列表", bg="#f0f0f0", bd=1,
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
        tk.Button(bar, text="新建支付单", command=lambda: self.open_edit(None),
                  bg="#673ab7", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="查看明细", command=self.open_detail,
                  bg="#1989fa", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="编辑", command=self.edit_selected,
                  bg="#ff976a", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)
        tk.Button(bar, text="作废", command=self.void_selected,
                  bg="#ee0a24", fg="white", padx=14, pady=4, bd=0).pack(side=tk.LEFT, padx=5)

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
    def now_str():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def fee_status_label(code):
        try:
            return FEE_STATUS_MAP.get(int(code), {}).get('label', str(code or '-'))
        except (TypeError, ValueError):
            return str(code or '-')

    @staticmethod
    def fee_log_label(code):
        try:
            return FEE_LOG_TYPE_MAP.get(int(code), str(code or '-'))
        except (TypeError, ValueError):
            return str(code or '-')

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

    def _status_of(self, row):
        return str(row.get('feeExpenseStatus') or '')

    # ---------------------------------------------------- 初始化数据（异步）
    def load_org_tree(self):
        threading.Thread(target=self._org_thread, daemon=True).start()

    def _org_thread(self):
        try:
            r = self.controller.session.get(URL_ORG_TREE, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-组织树] 拉取失败: {e}")
            data = {}
        nodes = (data.get('data') or []) if isinstance(data, dict) else []
        options = []
        resolved = None
        wh = self.warehouse_var.get()
        if isinstance(nodes, list) and nodes:
            logistics = next((n for n in nodes if str(n.get('orgCode')) == LOGISTICS_ORG_CODE), None)
            if logistics:
                for n in nodes:
                    if str(n.get('parentOrgId')) == str(logistics.get('orgId')):
                        options.append({
                            'name': n.get('orgName') or '',
                            'code': n.get('orgCode') or '',
                            'orgId': n.get('orgId'),
                        })
            hit = next((n for n in nodes if str(n.get('orgName')) == wh), None)
            if hit:
                resolved = {
                    'applyDepartmentCode': hit.get('orgCode') or '',
                    'applyOrganizationId': hit.get('orgId'),
                    'applyDepartmentName': hit.get('orgName') or '',
                }
        self.controller.after(0, lambda: self._apply_org(options, resolved))

    def _apply_org(self, options, resolved):
        self.dept_options = options if options else [
            {'name': k, 'code': v['applyDepartmentCode'], 'orgId': v['applyOrganizationId']}
            for k, v in FEE_DEPT_FALLBACK.items()
        ]
        names = ["全部部门"] + [d['name'] for d in self.dept_options]
        self.dept_cb.config(values=names)
        self.resolve_dept(resolved)

    def resolve_dept(self, resolved=None):
        wh = self.warehouse_var.get()
        if not resolved:
            fb = FEE_DEPT_FALLBACK.get(wh)
            if fb:
                resolved = {
                    'applyDepartmentCode': fb['applyDepartmentCode'],
                    'applyOrganizationId': fb['applyOrganizationId'],
                    'applyDepartmentName': wh,
                }
        if resolved:
            self.dept_code = resolved.get('applyDepartmentCode') or ''
            self.dept_name = resolved.get('applyDepartmentName') or wh
            self.dept_org_id = resolved.get('applyOrganizationId')
        else:
            self.dept_code, self.dept_name, self.dept_org_id = '', wh, None
        if self.dept_name in self.dept_cb.cget('values'):
            self.dept_var.set(self.dept_name)
            self.filter_dept_code.set(self.dept_code)
            self.filter_dept_name.set(self.dept_name)
        else:
            self.dept_var.set("全部部门")
            self.filter_dept_code.set('')
            self.filter_dept_name.set('')

    def on_dept_selected(self, event=None):
        name = self.dept_var.get()
        if name == "全部部门":
            self.filter_dept_code.set('')
            self.filter_dept_name.set('')
            return
        hit = next((d for d in self.dept_options if d['name'] == name), None)
        self.filter_dept_code.set(hit['code'] if hit else '')
        self.filter_dept_name.set(name)

    # 往来单位（供应商）下拉
    def on_filter_dealer_selected(self, event=None):
        name = self.filter_dealer_var.get()
        if name == "全部":
            self.filter_dealer_code.set('')
            self.filter_dealer_name.set('')
            return
        self.filter_dealer_code.set(self.supplier_map.get(name, ''))
        self.filter_dealer_name.set(name)

    def load_accounts(self):
        threading.Thread(target=self._account_thread, daemon=True).start()

    def _account_thread(self):
        try:
            r = self.controller.session.get(URL_ACCOUNT, headers=HEADERS,
                                            params={'accountType': 'FY'})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-科目] 拉取失败: {e}")
            return
        arr = (data.get('data') or []) if isinstance(data, dict) else []
        items = []
        for a in arr if isinstance(arr, list) else []:
            if isinstance(a, dict) and a.get('code') is not None:
                items.append({'code': str(a.get('code')),
                              'codeName': a.get('codeName') or str(a.get('code'))})
        self.controller.after(0, lambda: self._apply_accounts(items))

    def _apply_accounts(self, items):
        self.accounts = items
        self.account_names = [a['codeName'] for a in items]
        self.account_map = {a['codeName']: a['code'] for a in items}

    def load_employees(self):
        threading.Thread(target=self._employee_thread, daemon=True).start()

    def _employee_thread(self):
        try:
            r = self.controller.session.get(
                URL_EMPLOYEE, headers=HEADERS,
                params={'keyword': '', 'employeeDataSources': 10451003, 'isOnjob': 10081001})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-员工] 拉取失败: {e}")
            return
        resp = data if isinstance(data, dict) else {}
        raw = resp.get('data') if isinstance(resp.get('data'), list) else (
            resp.get('rows') if isinstance(resp.get('rows'), list) else [])
        items = []
        for e in raw if isinstance(raw, list) else []:
            if not isinstance(e, dict):
                continue
            name = e.get('EMPLOYEE_NAME') or e.get('name') or ''
            code = e.get('USER_CODE') or e.get('value') or e.get('EMPLOYEE_NO') or ''
            if not name:
                continue
            items.append({'name': name, 'code': str(code or ''),
                          'empId': e.get('userId') or e.get('EMPLOYEE_ID') or '',
                          'orgName': e.get('ORG_NAME') or ''})
        self.controller.after(0, lambda: self._apply_employees(items))

    def _apply_employees(self, items):
        self.employees = items
        self.employee_names = [e['name'] for e in items]
        self.employee_map = {e['name']: e['code'] for e in items}
        self.apply_cb.config(values=self.employee_names)

    def on_apply_selected(self, event=None):
        name = self.apply_var.get()
        self.filter_apply_name.set(name)
        self.filter_apply_code.set(self.employee_map.get(name, ''))

    # 往来单位（供应商）查询（本模块特有接口）
    def load_suppliers(self):
        threading.Thread(target=self._supplier_thread, daemon=True).start()

    def _supplier_thread(self):
        try:
            params = dict(SUPPLIER_QUERY)
            params['pageNum'] = 1
            params['limit'] = SUPPLIER_PAGE_LIMIT
            r = self.controller.session.get(URL_SUPPLIER, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-供应商] 拉取失败: {e}")
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            return
        resp = data.get("data") or {}
        rows = resp.get("rows") if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
        items = []
        for s in rows if isinstance(rows, list) else []:
            if not isinstance(s, dict):
                continue
            sno = s.get('supplier_no') or ''
            sname = s.get('supplier_name') or ''
            if not sno or not sname:
                continue
            items.append({
                'name': sname,
                'code': str(sno),
                'fullName': s.get('supplier_full_name') or '',
                'phone': s.get('supplier_phone') or '',
                'supplierId': s.get('supplier_id'),
            })
        self.controller.after(0, lambda: self._apply_suppliers(items))

    def _apply_suppliers(self, items):
        self.suppliers = items
        self.supplier_names = [s['name'] for s in items]
        self.supplier_map = {s['name']: s['code'] for s in items}
        # 查询用往来单位下拉（含「全部」）
        names = ["全部"] + self.supplier_names
        self.filter_dealer_cb.config(values=names)

    # ------------------------------------------------------------------ 筛选
    def toggle_status(self, value):
        self.filter_status.set('' if self.filter_status.get() == value else value)
        self._update_status_buttons()
        self._apply_filters()

    def _update_status_buttons(self):
        cur = self.filter_status.get()
        for value, btn in self.status_buttons.items():
            if value == cur:
                btn.config(bg="#673ab7", fg="white")
            else:
                btn.config(bg="#e1e1e1", fg="#323233")

    def _apply_filters(self):
        rows = self.all_rows
        status = self.filter_status.get()
        if status:
            codes = [s.strip() for s in status.split(',') if s.strip()]
            rows = [r for r in rows if self._status_of(r) in codes]
        no = self.filter_bill_no.get().strip().lower()
        name = self.filter_apply_name.get().strip().lower()
        dealer = self.filter_dealer_name.get().strip().lower()
        if no or name or dealer:
            kept = []
            for r in rows:
                bill = str(r.get('feeExpenseBillNo') or '').lower()
                applier = str(r.get('applyName') or r.get('createdByName') or '').lower()
                unit = str(r.get('dealerName') or '').lower()
                if no and no not in bill:
                    continue
                if name and name not in applier:
                    continue
                if dealer and dealer not in unit:
                    continue
                kept.append(r)
            rows = kept
        self.filtered_rows = rows
        self.page_num = 1
        self._render_rows()

    def reset_form(self):
        self.filter_status.set('')
        self._update_status_buttons()
        self.filter_bill_no.set('')
        self.filter_apply_name.set('')
        self.filter_apply_code.set('')
        self.apply_var.set('')
        self.filter_dealer_code.set('')
        self.filter_dealer_name.set('')
        self.filter_dealer_var.set('全部')
        self.start_cal.set_date(self.def_date('begin'))
        self.end_cal.set_date(self.def_date('end'))
        self.resolve_dept()
        self.all_rows = []
        self.filtered_rows = []
        self.queried = False
        self.page_num = 1
        self._render_rows()
        self.count_var.set("")

    # ------------------------------------------------------------------ 查询
    def build_query_params(self):
        """构造查询参数（对齐安卓端 OtherPayManage.vue doQuery 的 HAR 实测字段）"""
        by_applicant = bool(self.filter_apply_code.get())
        dept_code = self.filter_dept_code.get()
        return {
            "feeType": OTHER_PAY_FEE_TYPE,
            "created_by": self.filter_apply_code.get() or '',
            # 申请人 / 部门互斥（与报销同一契约：created_by=X AND 部门=本仓库会查空）
            "applyDepartmentCode": '' if by_applicant else (dept_code or ''),
            "applyDepartmentName": '' if by_applicant else (self.filter_dept_name.get() if dept_code else ''),
            "applyStartDate": self.start_cal.get() or '',
            "applyEndDate": self.end_cal.get() or '',
            # HAR 实测：以下两项恒为空串，状态与单号由前端过滤
            "feeExpenseStatus": '',
            "feeExpenseBillNo": '',
            "applyName": self.filter_apply_name.get() or '',
            # 往来单位（其他支付特有）
            "dealerCode": self.filter_dealer_code.get() or '',
            "dealerName": self.filter_dealer_name.get() or '',
            "feeExpenseType": '',
            "order": '',
            "sort": '',
            "pageNum": 1,
            "limit": QUERY_LIMIT,
        }

    def query(self):
        if self.loading:
            return
        params = self.build_query_params()
        self.loading = True
        self.queried = False
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[其他支付管理] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付管理] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常，请检查网络: {e}"))
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
            messagebox.showinfo("查询结果", "未查询到其他支付单")

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
                row.get('feeExpenseBillNo') or '-',
                self.fee_status_label(row.get('feeExpenseStatus')),
                row.get('applyDepartmentName') or '-',
                row.get('dealerName') or '-',
                row.get('applyName') or row.get('createdByName') or '-',
                self.format_money(row.get('applyAmountTotal')),
                self.format_date(row.get('createdAt') or row.get('applyStartAt')),
                row.get('feeExpenseTypeStr') or '-',
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)

        total = len(self.filtered_rows)
        self.count_var.set(f"共 {total} 条其他支付单")
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
            messagebox.showinfo("提示", "请先在列表中选择一条其他支付单")
            return
        bill_id = row.get('id')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 id，无法查看明细")
            return
        self.count_var.set("加载明细中...")
        threading.Thread(target=self._detail_thread, args=(bill_id, row), daemon=True).start()

    def _detail_thread(self, bill_id, row):
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-明细] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"明细加载失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "明细加载失败"
            self.controller.after(0, lambda: messagebox.showerror("明细", str(msg)))
            return
        d = data.get("data") or {}
        payload = {
            'id': bill_id,
            'billNo': row.get('feeExpenseBillNo') or '',
            'statusCode': self._status_of(row),
            'deptName': row.get('applyDepartmentName') or '',
            'dealerName': row.get('dealerName') or '',
            'applyName': row.get('applyName') or row.get('createdByName') or '',
            'amountTotal': row.get('applyAmountTotal') or 0,
            'remark': d.get('remark') or row.get('remark') or '',
            'details': d.get('detailDtoList') if isinstance(d.get('detailDtoList'), list) else [],
            'attachments': d.get('attachmentDtoList') if isinstance(d.get('attachmentDtoList'), list) else [],
            'pays': d.get('payDetailDtoList') if isinstance(d.get('payDetailDtoList'), list) else [],
            'logs': d.get('logList') if isinstance(d.get('logList'), list) else [],
        }
        self.controller.after(0, lambda: self._show_detail_window(payload))

    def _show_detail_window(self, p):
        win = tk.Toplevel(self)
        win.title(f"其他支付单明细 - {p['billNo'] or p['id']}")
        win.geometry("760x700")
        win.transient(self)

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="其他支付单明细", bg="#f7f8fa", fg="#673ab7",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text=f"状态：{self.fee_status_label(p['statusCode'])}",
                 bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        info = tk.Frame(win, bg="#ffffff")
        info.pack(fill=tk.X, padx=10, pady=5)
        for key, val in (("单号", p['billNo'] or '-'),
                         ("申请部门", p['deptName'] or '-'),
                         ("往来单位", p['dealerName'] or '-'),
                         ("申请人", p['applyName'] or '-'),
                         ("金额", self.format_money(p['amountTotal'])),
                         ("摘要", p['remark'] or '无')):
            line = tk.Frame(info, bg="#ffffff")
            line.pack(fill=tk.X, pady=2)
            tk.Label(line, text=key + "：", bg="#ffffff", fg="#969799",
                     font=("微软雅黑", 10), width=9, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#ffffff", font=("微软雅黑", 10),
                     anchor="w", wraplength=560, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 费用明细
        tk.Label(win, text=f"费用明细（{len(p['details'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dtree = ttk.Treeview(dframe, columns=DETAIL_COLUMNS, show="headings", height=6)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            dtree.heading(col, text=col)
            dtree.column(col, width=width, anchor="e" if col == "金额" else "w")
        for idx, d in enumerate(p['details']):
            dtree.insert("", "end", values=(idx + 1,
                                            d.get('feeExpenseType') or '-',
                                            self.format_money(d.get('applyAmount')),
                                            d.get('feeRemark') or ''))
        dsb = ttk.Scrollbar(dframe, orient="vertical", command=dtree.yview)
        dtree.configure(yscrollcommand=dsb.set)
        dtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 支付方式（其他支付特有）
        if p['pays']:
            tk.Label(win, text=f"支付方式（{len(p['pays'])}）", bg="#f0f0f0",
                     font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
            pframe = tk.Frame(win, bg="#ffffff")
            pframe.pack(fill=tk.X, padx=10)
            pay_cols = ["序号", "银行卡号", "开户行", "金额", "备注"]
            ptree = ttk.Treeview(pframe, columns=pay_cols, show="headings", height=max(1, len(p['pays'])))
            for i, col in enumerate(pay_cols):
                ptree.heading(col, text=col)
                ptree.column(col, width=[50, 160, 160, 110, 220][i],
                             anchor="e" if col == "金额" else "w")
            for idx, pay in enumerate(p['pays']):
                ptree.insert("", "end", values=(
                    idx + 1,
                    pay.get('payBankNo') or '-',
                    pay.get('payBankName') or '-',
                    self.format_money(pay.get('payAmount')),
                    ((pay.get('courseInfo') or '') + (' · ' + pay.get('payRemark') if pay.get('payRemark') else '')) or ''))
            psb = ttk.Scrollbar(pframe, orient="vertical", command=ptree.yview)
            ptree.configure(yscrollcommand=psb.set)
            ptree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            psb.pack(side=tk.RIGHT, fill=tk.Y)

        # 附件
        tk.Label(win, text=f"附件（{len(p['attachments'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
        aframe = tk.Frame(win, bg="#ffffff")
        aframe.pack(fill=tk.X, padx=10)
        if not p['attachments']:
            tk.Label(aframe, text="无附件", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for a in p['attachments']:
            line = tk.Frame(aframe, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            name = a.get('attachmentName') or ('附件' + str(a.get('attachmentUrl') or ''))
            tk.Label(line, text=name, bg="#ffffff", anchor="w").pack(side=tk.LEFT)
            tk.Button(line, text="下载", bg="#e1e1e1", relief=tk.FLAT,
                      command=lambda at=a: self.download_attachment(at)).pack(side=tk.RIGHT)

        # 操作日志（默认折叠）
        self._log_expanded = False
        log_frame = tk.Frame(win, bg="#ffffff")
        log_btn = tk.Button(win, text=f"操作日志（{len(p['logs'])}） ▼", bg="#f0f0f0",
                            relief=tk.FLAT, anchor="w",
                            command=lambda: self._toggle_logs(log_frame, log_btn, p['logs']))
        log_btn.pack(fill=tk.X, padx=10, pady=(8, 0))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        log_frame.pack_forget()

        # 底部操作
        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        is_draft = (p['statusCode'] == FEE_STATUS_DRAFT)
        if is_draft:
            tk.Button(bar, text="编辑", bg="#673ab7", fg="white", padx=18, pady=4, bd=0,
                      command=lambda: [win.destroy(), self.open_edit(
                          {'id': p['id'],
                           'applyDepartmentCode': p.get('deptCode', ''),
                           'applyDepartmentName': p['deptName'],
                           'dealerCode': p.get('dealerCode') or '',
                           'dealerName': p['dealerName'],
                           'applyName': p['applyName'],
                           'applyUserCode': p.get('applyUserCode') or '',
                           'remark': p['remark']})]).pack(side=tk.LEFT, padx=10)
            tk.Button(bar, text="作废", bg="#ee0a24", fg="white", padx=18, pady=4, bd=0,
                      command=lambda: [win.destroy(), self.do_void(p['id'])]).pack(side=tk.LEFT, padx=10)
        else:
            tk.Label(bar, text="当前状态不可编辑/作废（仅草稿可操作）",
                     bg="#f0f0f0", fg="#969799").pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=4,
                  command=win.destroy).pack(side=tk.RIGHT, padx=10)

        self.count_var.set(f"共 {len(self.filtered_rows)} 条其他支付单")

    def _toggle_logs(self, frame, btn, logs):
        if self._log_expanded:
            frame.pack_forget()
            btn.config(text=btn.cget('text').replace('▲', '▼'))
            self._log_expanded = False
            return
        for w in frame.winfo_children():
            w.destroy()
        if not logs:
            tk.Label(frame, text="无日志", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for log in logs:
            text = "[{}] {} {} {}".format(
                self.fee_log_label(log.get('feeOperatorType')),
                log.get('feeOperatorBy') or '',
                self.format_date(log.get('createdAt')),
                ('（%s）' % log['operatorRemark']) if log.get('operatorRemark') else '')
            tk.Label(frame, text=text, bg="#ffffff", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        btn.config(text=btn.cget('text').replace('▼', '▲'))
        self._log_expanded = True

    # ------------------------------------------------------------------ 编辑
    def edit_selected(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条其他支付单")
            return
        if self._status_of(row) != FEE_STATUS_DRAFT:
            messagebox.showwarning("提示", "仅「新建（草稿）」状态的单据可编辑")
            return
        self.open_edit(row)

    def open_edit(self, source):
        self.edit_id = str(source.get('id') or '') if source else ''
        self.edit_details = []
        self.edit_attachments = []
        self.edit_detail_deletes = []
        self.edit_attach_deletes = []
        self.edit_apply_name = (source or {}).get('applyName') or ''
        self.edit_apply_code = (source or {}).get('applyUserCode') or ''
        self.edit_dealer_code = (source or {}).get('dealerCode') or ''
        self.edit_dealer_name = (source or {}).get('dealerName') or ''
        self.edit_remark = (source or {}).get('remark') or ''
        self.edit_dept_code = (source or {}).get('applyDepartmentCode') or self.dept_code
        self.edit_dept_name = (source or {}).get('applyDepartmentName') or self.dept_name

        if self.edit_id:
            self.count_var.set("加载中...")
            threading.Thread(target=self._edit_thread, args=(self.edit_id,), daemon=True).start()
        else:
            self.add_detail_row()
            self._show_edit_window()

    def _edit_thread(self, bill_id):
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-编辑载入] 异常: {e}")
            data = {}
        d = (data.get('data') or {}) if isinstance(data, dict) else {}
        details = d.get('detailDtoList') if isinstance(d.get('detailDtoList'), list) else []
        atts = d.get('attachmentDtoList') if isinstance(d.get('attachmentDtoList'), list) else []
        meta = {
            'applyName': d.get('applyName') or '',
            'applyUserCode': d.get('applyUserCode') or '',
            'dealerCode': d.get('dealerCode') or '',
            'dealerName': d.get('dealerName') or '',
            'remark': d.get('remark') or '',
            'details': details,
            'attachments': atts,
        }
        self.controller.after(0, lambda: self._apply_edit_data(meta))

    def _apply_edit_data(self, meta):
        if meta['applyName']:
            self.edit_apply_name = meta['applyName']
        if meta['applyUserCode']:
            self.edit_apply_code = meta['applyUserCode']
        if meta['dealerCode']:
            self.edit_dealer_code = meta['dealerCode']
        if meta['dealerName']:
            self.edit_dealer_name = meta['dealerName']
        if meta['remark']:
            self.edit_remark = meta['remark']
        self.edit_details = [{
            'id': d.get('id'),
            'feeExpenseCode': d.get('feeExpenseCode') or '',
            'feeExpenseType': d.get('feeExpenseType') or '',
            'applyAmount': d.get('applyAmount') or 0,
            'feeRemark': d.get('feeRemark') or '',
        } for d in meta['details']]
        self.edit_attachments = [{
            'id': a.get('id'),
            'name': a.get('attachmentName') or ('附件' + str(a.get('attachmentUrl') or '')),
            'attachmentUrl': a.get('attachmentUrl') or '',
            'size': a.get('size') or 0,
            'isValid': a.get('isValid'),
            'canDelete': a.get('canDelete'),
            'invoiceCode': a.get('invoiceCode'),
            'invoiceNumber': a.get('invoiceNumber'),
        } for a in meta['attachments']]
        if not self.edit_details:
            self.add_detail_row()
        self._show_edit_window()

    def add_detail_row(self):
        self.edit_details.append({
            'id': None, 'feeExpenseCode': '', 'feeExpenseType': '',
            'applyAmount': 0, 'feeRemark': ''})

    def remove_detail_row(self, d):
        if d.get('id') is not None:
            self.edit_detail_deletes.append({
                'id': d['id'],
                'feeExpenseCode': d.get('feeExpenseCode') or '',
                'feeExpenseType': d.get('feeExpenseType') or '',
                'applyAmount': float(d.get('applyAmount') or 0),
                'feeRemark': d.get('feeRemark') or '',
                'feeExpenseManagerId': int(self.edit_id) if self.edit_id else None,
            })
        self.edit_details.remove(d)
        if not self.edit_details:
            self.add_detail_row()
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_details()

    def remove_attachment(self, a):
        if a.get('id') is not None:
            self.edit_attach_deletes.append({
                'id': a['id'],
                'attachmentName': a.get('name') or '',
                'attachmentUrl': a.get('attachmentUrl') or '',
                'feeExpenseManagerId': int(self.edit_id) if self.edit_id else None,
                'uploadedName': self.edit_apply_name or '',
                'createdAt': a.get('createdAt') or '',
                'attachmentRemark': None,
                'invoiceCode': None,
                'invoiceNumber': None,
                'isValid': a.get('isValid'),
            })
        self.edit_attachments.remove(a)
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_attachments()

    def _show_edit_window(self):
        win = tk.Toplevel(self)
        win.title("编辑支付单" if self.edit_id else "新建支付单")
        win.geometry("880x740")
        win.transient(self)
        self.edit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="编辑支付单" if self.edit_id else "新建支付单",
                 bg="#f7f8fa", fg="#673ab7",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)

        base = tk.LabelFrame(win, text="基本信息", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        base.pack(fill=tk.X, padx=10, pady=5, ipadx=6, ipady=4)

        r1 = tk.Frame(base, bg="#f0f0f0")
        r1.pack(fill=tk.X, pady=2)
        tk.Label(r1, text="申请部门:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_dept_var = tk.StringVar(value=self.edit_dept_name or "")
        names = [d['name'] for d in self.dept_options] or [self.edit_dept_name]
        dept_cb = ttk.Combobox(r1, textvariable=self.edit_dept_var, values=names,
                               state="readonly", width=14)
        if self.edit_dept_name in names:
            dept_cb.set(self.edit_dept_name)
        dept_cb.pack(side=tk.LEFT, padx=4)
        dept_cb.bind("<<ComboboxSelected>>", self._on_edit_dept)

        # 往来单位（供应商）—— 其他支付核心字段
        tk.Label(r1, text="往来单位:", bg="#f0f0f0", width=8, anchor="w").pack(side=tk.LEFT, padx=(15, 0))
        self.edit_dealer_var = tk.StringVar(value=self.edit_dealer_name)
        dealer_cb = ttk.Combobox(r1, textvariable=self.edit_dealer_var,
                                 values=self.supplier_names, state="readonly", width=16)
        if self.edit_dealer_name in self.supplier_names:
            dealer_cb.set(self.edit_dealer_name)
        dealer_cb.pack(side=tk.LEFT, padx=4)
        dealer_cb.bind("<<ComboboxSelected>>", self._on_edit_dealer)

        r2 = tk.Frame(base, bg="#f0f0f0")
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text="申请人:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_apply_var = tk.StringVar(value=self.edit_apply_name)
        apply_cb = ttk.Combobox(r2, textvariable=self.edit_apply_var,
                                values=self.employee_names, state="readonly", width=14)
        apply_cb.pack(side=tk.LEFT, padx=4)
        apply_cb.bind("<<ComboboxSelected>>", self._on_edit_apply)
        if self.edit_apply_name:
            self.edit_apply_code = self.employee_map.get(self.edit_apply_name, self.edit_apply_code)

        r3 = tk.Frame(base, bg="#f0f0f0")
        r3.pack(fill=tk.X, pady=2)
        tk.Label(r3, text="摘要:", bg="#f0f0f0", width=10, anchor="w").pack(side=tk.LEFT)
        self.edit_remark_var = tk.StringVar(value=getattr(self, 'edit_remark', '') or '')
        ttk.Entry(r3, textvariable=self.edit_remark_var, width=62).pack(side=tk.LEFT, padx=4)

        dhead = tk.Frame(win, bg="#f0f0f0")
        dhead.pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(dhead, text="费用明细", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(dhead, text="+ 添加明细", command=lambda: [self.add_detail_row(),
                                                        self._render_edit_details()],
                  bg="#673ab7", fg="white", bd=0, padx=8).pack(side=tk.LEFT, padx=8)
        self.edit_total_var = tk.StringVar(value="")
        tk.Label(dhead, textvariable=self.edit_total_var, bg="#f0f0f0",
                 fg="#673ab7", font=("微软雅黑", 10, "bold")).pack(side=tk.RIGHT)

        self.details_frame = tk.Frame(win, bg="#ffffff")
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        self._render_edit_details()

        ahead = tk.Frame(win, bg="#f0f0f0")
        ahead.pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(ahead, text="附件", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(ahead, text="添加附件", command=self.add_attachment,
                  bg="#e1e1e1", relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=8)
        self.attach_frame = tk.Frame(win, bg="#ffffff", height=60)
        self.attach_frame.pack(fill=tk.X, padx=10)
        self._render_edit_attachments()

        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        tk.Button(bar, text="保存草稿", command=lambda: self.save(1),
                  bg="#673ab7", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="提交", command=lambda: self.save(2),
                  bg="#07c160", fg="white", padx=18, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="取消", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=18, pady=5).pack(side=tk.RIGHT, padx=10)

    def _on_edit_dept(self, event=None):
        name = self.edit_dept_var.get()
        hit = next((d for d in self.dept_options if d['name'] == name), None)
        if hit:
            self.edit_dept_code = hit['code']
            self.edit_dept_name = hit['name']
            self.edit_dept_org_id = hit.get('orgId')

    def _on_edit_dealer(self, event=None):
        name = self.edit_dealer_var.get()
        self.edit_dealer_name = name
        self.edit_dealer_code = self.supplier_map.get(name, '')

    def _on_edit_apply(self, event=None):
        name = self.edit_apply_var.get()
        self.edit_apply_name = name
        self.edit_apply_code = self.employee_map.get(name, '')

    def _render_edit_details(self):
        for w in self.details_frame.winfo_children():
            w.destroy()
        for d in self.edit_details:
            row = tk.Frame(self.details_frame, bg="#f7f8fa")
            row.pack(fill=tk.X, pady=2, padx=2)

            type_var = tk.StringVar(value=d.get('feeExpenseType') or '')
            cb = ttk.Combobox(row, textvariable=type_var, values=self.account_names,
                              state="readonly", width=20)
            cb.pack(side=tk.LEFT, padx=2)

            def on_type(event=None, d=d, var=type_var):
                name = var.get()
                d['feeExpenseType'] = name
                d['feeExpenseCode'] = self.account_map.get(name, '')

            cb.bind("<<ComboboxSelected>>", on_type)

            amt_var = tk.StringVar(value=str(d.get('applyAmount') or 0))
            e_amt = ttk.Entry(row, textvariable=amt_var, width=10)
            e_amt.pack(side=tk.LEFT, padx=2)

            def on_amt(event=None, d=d, var=amt_var):
                try:
                    d['applyAmount'] = float(var.get() or 0)
                except ValueError:
                    d['applyAmount'] = 0
                self._update_edit_total()

            e_amt.bind("<KeyRelease>", on_amt)

            rem_var = tk.StringVar(value=d.get('feeRemark') or '')
            e_rem = ttk.Entry(row, textvariable=rem_var, width=26)
            e_rem.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

            def on_rem(event=None, d=d, var=rem_var):
                d['feeRemark'] = var.get()

            e_rem.bind("<KeyRelease>", on_rem)

            tk.Button(row, text="删", bg="#ee0a24", fg="white", bd=0, width=3,
                      command=lambda dd=d: self.remove_detail_row(dd)).pack(side=tk.LEFT, padx=2)
        self._update_edit_total()

    def _update_edit_total(self):
        total = sum(float(d.get('applyAmount') or 0) for d in self.edit_details
                    if d.get('feeExpenseCode'))
        if hasattr(self, 'edit_total_var'):
            self.edit_total_var.set("合计金额：" + self.format_money(total))

    def _render_edit_attachments(self):
        for w in self.attach_frame.winfo_children():
            w.destroy()
        if not self.edit_attachments:
            tk.Label(self.attach_frame, text="无附件", bg="#ffffff",
                     fg="#c8c9cc").pack(anchor="w")
        for a in self.edit_attachments:
            line = tk.Frame(self.attach_frame, bg="#ffffff")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text=a.get('name') or '-', bg="#ffffff", anchor="w").pack(side=tk.LEFT)
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
            print(f"[其他支付-附件上传] 失败: {e}")
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
            'id': None, 'name': name, 'attachmentUrl': file_id, 'size': size,
            'isValid': ATTACH_VALID, 'canDelete': ATTACH_CAN_DELETE,
            'invoiceCode': '', 'invoiceNumber': '',
        })
        if self.edit_win and self.edit_win.winfo_exists():
            self._render_edit_attachments()

    # ------------------------------------------------------------ 保存/提交
    def build_payload(self, type_operator):
        """构造保存/提交报文（对齐安卓端 OtherPayManage.vue buildPayload 的 HAR 实测结构）

        与报销模块的关键差异：dealerCode/dealerName【始终】携带（即便编辑态也不置 None）。
        """
        str_op = str(type_operator)
        bill_id = int(self.edit_id) if self.edit_id else None

        details = []
        for d in self.edit_details:
            if not d.get('feeExpenseCode'):
                continue
            if float(d.get('applyAmount') or 0) <= 0:
                continue
            item = {
                'id': d['id'] if d.get('id') is not None else '',
                'feeExpenseCode': d['feeExpenseCode'],
                'feeExpenseType': d.get('feeExpenseType') or '',
                'applyAmount': float(d.get('applyAmount') or 0),
                'feeRemark': d.get('feeRemark') or '',
            }
            if bill_id is not None:
                item['feeExpenseManagerId'] = bill_id
            details.append(item)

        attachments = [self._build_attachment_item(a, bill_id) for a in self.edit_attachments]
        total = sum(d['applyAmount'] for d in details)

        payload = {
            'feeType': OTHER_PAY_FEE_TYPE,
            'typeOperator': str_op,
            'id': bill_id,
            # 往来单位（其他支付核心字段，始终携带）
            'dealerCode': self.edit_dealer_code,
            'dealerName': self.edit_dealer_name,
            'applyDepartmentCode': getattr(self, 'edit_dept_code', '') or '',
            'applyDepartmentName': getattr(self, 'edit_dept_name', '') or '',
            'applyOrganizationId': getattr(self, 'edit_dept_org_id', None),
            'applyName': self.edit_apply_name,
            'applyUserCode': self.edit_apply_code,
            'remark': getattr(self, 'edit_remark_var', None).get()
                      if hasattr(self, 'edit_remark_var') else getattr(self, 'edit_remark', ''),
            'applyAmountTotal': total,
            'detailDtoList': details,
            'detailDtoListDelete': self.edit_detail_deletes,
            'attachmentDtoList': attachments,
            'attachmentDtoListDelete': self.edit_attach_deletes,
        }
        return payload

    def _build_attachment_item(self, a, bill_id):
        name = a.get('name') or ''
        is_img = is_image_file(name)
        size = a.get('size') or 0
        size_kb = '%dKB' % round(size / 1024) if size else ''
        review_url = '{}/{}/{}'.format(URL_ATTACH_FILE, ATTACHMENT_BILL_TYPE,
                                       a.get('attachmentUrl') or '')
        item = {
            'attachmentName': name,
            'attachmentUrl': a.get('attachmentUrl') or '',
            'uploadedName': self.edit_apply_name,
            'createdAt': self.now_str(),
            'isValid': a.get('isValid') if a.get('isValid') is not None else ATTACH_VALID,
            'canDelete': a.get('canDelete') if a.get('canDelete') is not None else ATTACH_CAN_DELETE,
            'invoiceCode': a.get('invoiceCode') if a.get('invoiceCode') is not None else '',
            'invoiceNumber': a.get('invoiceNumber') if a.get('invoiceNumber') is not None else '',
            'optionType': 'update' if a.get('id') is not None else 'add',
        }
        item['id'] = a.get('id') if a.get('id') is not None else None
        if bill_id is not None:
            item['feeExpenseManagerId'] = bill_id
        item['files'] = {
            'status': 'success',
            'name': name,
            'size': size,
            'key': a.get('attachmentUrl') or '',
            'type': 'image' if is_img else 'other',
            'showZoom': is_img,
            'url': review_url,
            'downloadUrl': review_url,
            'uuid': review_url,
            'dealerCode': 'FY',
            'caption': name,
            'description': '',
            'isValid': item['isValid'],
            'canDelete': item['canDelete'],
            'optionType': item['optionType'],
            'sizeKB': size_kb,
            'createdAt': item['createdAt'],
            'billId': a.get('id') if a.get('id') is not None else None,
            'billType': ATTACHMENT_BILL_TYPE,
        }
        return item

    def save(self, type_operator):
        """保存草稿(1) / 提交(2)"""
        # 与安卓端 validateForm 对齐：部门 / 往来单位 / 申请人 / 摘要 / 至少一条有效明细
        if not self.edit_dept_code or not self.edit_dept_name:
            messagebox.showwarning("提示", "请选择申请部门")
            return
        if not self.edit_dealer_code or not self.edit_dealer_name:
            messagebox.showwarning("提示", "请选择往来单位")
            return
        if not self.edit_apply_name or not self.edit_apply_code:
            messagebox.showwarning("提示", "请选择申请人")
            return
        remark = getattr(self, 'edit_remark_var', None).get() if hasattr(self, 'edit_remark_var') else getattr(self, 'edit_remark', '')
        if not str(remark or '').strip():
            messagebox.showwarning("提示", "请输入摘要")
            return
        valid = [d for d in self.edit_details
                 if d.get('feeExpenseCode') and float(d.get('applyAmount') or 0) > 0]
        if not valid:
            messagebox.showwarning("提示", "请至少添加一条有效费用明细（费用科目 + 金额 > 0）")
            return
        if type_operator == 2:
            if not messagebox.askyesno("确认提交", "提交后将进入审核流程，确认提交？"):
                return
        payload = self.build_payload(type_operator)
        self.count_var.set("保存中..." if type_operator == 1 else "提交中...")
        threading.Thread(target=self._save_thread, args=(payload, type_operator), daemon=True).start()

    def _save_thread(self, payload, type_operator):
        try:
            r = self.controller.session.post(URL_SAVE, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-保存] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"保存失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "保存失败"
            self.controller.after(0, lambda: messagebox.showerror("保存失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        ok = "已保存草稿" if type_operator == 1 else "提交成功，已进入审核"
        self.controller.after(0, lambda: messagebox.showinfo("成功", ok))
        self.controller.after(0, self._after_saved)

    def _after_saved(self):
        if self.edit_win and self.edit_win.winfo_exists():
            self.edit_win.destroy()
        self.query()

    # ------------------------------------------------------------------ 作废
    def void_selected(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条其他支付单")
            return
        if self._status_of(row) != FEE_STATUS_DRAFT:
            messagebox.showwarning("提示", "仅「新建（草稿）」状态的单据可作废")
            return
        self.do_void(row.get('id'))

    def do_void(self, bill_id):
        if not messagebox.askyesno("确认作废", "作废后该其他支付单不可恢复，确认作废？"):
            return
        self.count_var.set("作废中...")
        threading.Thread(target=self._void_thread, args=({'id': str(bill_id)},), daemon=True).start()

    def _void_thread(self, body):
        try:
            r = self.controller.session.post(URL_VOID, headers=HEADERS, json=body)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[其他支付-作废] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"作废失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "作废失败"
            self.controller.after(0, lambda: messagebox.showerror("作废失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        self.controller.after(0, lambda: messagebox.showinfo("成功", "作废成功"))
        self.controller.after(0, self.query)

    # ------------------------------------------------------------------ 附件
    def download_attachment(self, attach):
        bill_id = attach.get('id')
        file_key = attach.get('attachmentUrl')
        if not bill_id and not file_key:
            messagebox.showwarning("提示", "附件信息不完整，无法下载")
            return
        default_name = attach.get('attachmentName') or ('附件' + str(file_key or bill_id))
        path = filedialog.asksaveasfilename(title="保存附件", initialfile=default_name)
        if not path:
            return
        threading.Thread(target=self._download_thread,
                         args=(bill_id, file_key, path), daemon=True).start()

    def _download_thread(self, bill_id, file_key, path):
        urls = []
        if bill_id:
            urls.append('{}/{}/{}'.format(URL_ATTACH_CFG, ATTACHMENT_BILL_TYPE, bill_id))
        file_url = ''
        for u in urls:
            try:
                r = self.controller.session.get(u, headers=HEADERS)
                if not self._check_response(r):
                    continue
                data = json.loads(r.text)
                previews = ((data.get('data') or {}).get('initialPreview') or [])
                if previews:
                    file_url = previews[0]
                    break
            except Exception as e:
                print(f"[其他支付-附件配置] 失败: {e}")
        if not file_url and file_key:
            file_url = '/file/billFilesReview/{}/{}'.format(ATTACHMENT_BILL_TYPE, file_key)
        if not file_url:
            self.controller.after(0, lambda: messagebox.showwarning("提示", "附件暂不可下载"))
            return
        full = file_url if file_url.startswith('http') else (BASE + '/dmscloud.basedata' + file_url)
        try:
            r = self.controller.session.get(full, headers=HEADERS)
            if not self._check_response(r):
                return
            with open(path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"[其他支付-附件下载] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror("下载失败", str(e)))
            return
        self.controller.after(0, lambda: messagebox.showinfo("完成", f"附件已保存到：\n{path}"))

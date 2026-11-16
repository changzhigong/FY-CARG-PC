# -*- coding: utf-8 -*-
"""库内作业 — 移库管理

对齐 Web 源（dms_vue-prod，用户提供的反编译 JS）：
- 列表页   ``changedMng/adjustLogSearch/index.vue`` → ``index-3f1a836d.js``
- 编辑弹窗 ``adjustLogSearch/components/editDialog.vue`` → ``editDialog-c90e266a.js``
- 明细弹窗 ``detailDialog.vue`` → ``detailDialog-f43470e2.js``
- 接口桶   ``index-a140512e.js``
并对照安卓端 ``TransferChange.vue`` + ``service/transferChange.js``。

接口清单（baseURL https://xb.fy-carg.com）
========================================
- 列表     GET  /dmscloud.part/warehouse/change/adjustLog
           ?warehouseId&shiftNo&partNo&partName&moveNo&removeNo&createdByName
            &status&startTime&endTime&pageNum&pageSize
- 明细     GET  /dmscloud.part/warehouse/change/queryByShiftNo?shiftNo=
- 保存/提交 POST /dmscloud.part/warehouse/change/shiftHandle
- 导出     GET  /dmscloud.part/warehouse/change/export/excel?<同列表查询参数>
- 仓库     GET  /dmscloud.part/warehouse/manage/queryListWithPermissions
- 移库人   GET  /dcscloud.basedata/basedata/employees/getEmpByRoleCode?roleCode=YKR
- 产品     GET  /dmscloud.part/warehouse/change/queryPart
            ?warehouseId&partNo&partName&isValid=10031001&pageNum&pageSize
- 库位     GET  /dmscloud.part/warehouse/transferIn/findAllLocationValid
- 字典     GET  /dmscloud.basedata/dicts（4715 移库状态）

关键业务规则（逐条对齐 Web 源 / HAR 实测）
========================================
1. 列表返回结构 ``data = {total, pageSize, pageNum, rows:[...]}``；
   行字段（HAR 实测）：``{createdAt, createdBy, createdByName, move_by,
   onshelf_by, organizationId, picking_by, recordVersion, remark, shiftNo,
   status, warehouseId, warehouseName}``。
2. 查询条件：Web ``formList`` 含 仓库/移库单号/编码/名称/移入库位/移出库位/
   制单人/移库状态/调整时间起止。Web 默认 ``createdByName=当前登录人``、
   ``startTime=2个月前``、``endTime=null``。**PC 端登录仅存 cookies、无用户名**
   （同调拨申请），故默认 ``createdByName`` 留空、``endTime`` 取今天，保证
   「调整时间起止」构成有效条件，查询可用。
3. 编辑按钮可用状态：``status == 47151001 待提交``（Web: disabled=status!=47151001）。
   已提交（47151002）不可编辑/删除。
4. 保存/提交报文（Web ``infoSave``）：``{shiftNo, warehouseId, remark,
   checkStatus, status, detailDtoList, detailDtoListDelete, move_by}``；
   ``checkStatus`` 10041001 保存 / 10041002 提交；``status`` 回带原行状态
   （新建为 null）；``move_by`` 为逗号拼接的移库人姓名串。
5. 明细行字段（HAR ``queryByShiftNo`` 实测）：``{availableQty, brand, brandId,
   brandName, createdAt, createdBy, createdByName, logId, moveNo, moveNoId,
   moveQty, organizationId, partCode, partId, partName, picking_by,
   recordVersion, remark, removeNo, removeNoId, shiftNo, status, warehouseId,
   warehouseName}``。编辑时原样回传并叠加用户修改的 ``moveNoId``/``moveNo``/
   ``moveQty``；提交前剔除 UI 专用键 ``select_locationOptionLoading``。
6. ``select_LOCATION_OPTIONS`` 语义（与调拨入库/调拨申请同一条铁律）：
   - 服务端已有移入库位 → ``[{locationId, locationNo}]``（2 字段）；
   - 用户远端搜索新选 → 存 findAllLocationValid 完整对象（6 字段），原样带出。
   移入库位为**单选**，列表恒 1 个元素。
7. 校验（Web ``infoSave`` + 安卓 ``validateDetails``）：
   仓库必填、移库人必填、明细非空；
   每行「移出库位」「移入库位」「移库数量」必填，且移库数量 ≤ 可用数量
   （Web ``qtyValidate`` / 安卓 ``moveQty ≤ availableQty``）。
8. 移库人随仓库变化：Web ``queryYKRInfo`` 在切换仓库时按
   ``warehouseId``（未选仓库时传 -1）重新拉取；PC 端同此行为。
9. 本页编辑弹窗 Web 源定义了 ``splitRow`` 方法，但**模板未渲染拆行按钮**
   （模板扫描证据：editDialog-c90e266a.js 明细列仅
   序号/操作/warehouseName/partCode/partName/brandName/removeNo/moveNoId/
   availableQty/moveQty），故按真相源**不提供拆行**。
"""

import json
import os
import threading
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from base_page import BasePage
from tooltip_manager import tooltip_manager
from transfer_dialogs import (
    HEADERS,
    ProductPickerDialog,
    LocationPickerDialog,
    EmployeeMultiPicker,
    URL_QUERY_PART_CHANGE,
    resp_ok,
    err_msg,
)

# ---------------------------------------------------------------- 接口
BASE = 'https://xb.fy-carg.com'
PART = BASE + '/dmscloud.part'
BASEDATA = BASE + '/dcscloud.basedata'

URL_LIST = PART + '/warehouse/change/adjustLog'
URL_QUERY_BY_NO = PART + '/warehouse/change/queryByShiftNo'
URL_SAVE = PART + '/warehouse/change/shiftHandle'
URL_EXPORT = PART + '/warehouse/change/export/excel'

URL_WH_PERM = PART + '/warehouse/manage/queryListWithPermissions'
URL_DICTS = BASE + '/dmscloud.basedata/dicts'

# ---------------------------------------------------------------- 常量
PAGE_SIZE = 20

CHECK_SAVE = 10041001
CHECK_SUBMIT = 10041002

MOVER_ROLE = 'YKR'          # 移库人角色码
DICT_STATUS = '4715'        # 移库状态

# 字典兜底（HAR /dmscloud.basedata/dicts 实测）
DICT_FALLBACK = {
    DICT_STATUS: {'47151001': '待提交', '47151002': '已提交'},
}

# 可编辑状态（Web: edit 按钮 disabled=status!=47151001）
EDITABLE_STATUS = (47151001,)

# 提交前需剔除的 UI 专用键（对齐 Web normalizeShiftRow）
UI_ONLY_KEYS = ('select_locationOptionLoading', '_key', '_moveInput')

# 列表列（对齐 Web index-3f1a836d.js 表头顺序）
COLUMNS = ['序号', '仓库名称', '移库单号', '制单人', '创建时间', '调整原因', '移库状态']
COLUMN_WIDTHS = [50, 140, 200, 100, 160, 200, 100]

# 编辑弹窗明细列（对齐 Web editDialog 模板）
DETAIL_COLUMNS = ['序号', '仓库名称', 'CARG全码/产品编码', '产品名称', '品牌',
                  '移出库位', '移入库位', '可用数量', '移库数量']
DETAIL_WIDTHS = [45, 100, 160, 280, 100, 110, 110, 90, 90]

# 明细弹窗（只读）列
VIEW_COLUMNS = ['序号', '仓库名称', 'CARG全码/产品编码', '产品名称', '品牌',
                '移出库位', '移入库位', '移库数量']
VIEW_WIDTHS = [45, 100, 160, 300, 100, 120, 120, 100]


class TransferChangePage(BasePage):
    """库内作业 — 移库管理页面"""

    def __init__(self, parent, controller):
        self.rows = []
        self.total = 0
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.loading = False

        self.dict_maps = {}
        self.wh_map = {}          # 仓库 name -> value
        self.movers = []          # 移库人姓名列表（YKR）

        self._edit_win = None
        self._edit_tree = None
        self._edit_detail_rows = []
        self._edit_deleted = []
        self._edit_meta = {}
        self._move_by_var = None

        self._detail_win = None
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

        self.load_dicts()
        self.load_warehouses()

    def setup_filter_panel(self, parent):
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=4)
        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.warehouse_var = tk.StringVar(value="全部")
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=["全部"], state="readonly", width=12)
        self.warehouse_cb.pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="移库单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.shift_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.shift_no_var, width=18).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="CARG全码/产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.part_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_no_var, width=18).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.part_name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_name_var, width=18).pack(side=tk.LEFT, padx=4)

        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="移入库位:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.move_no_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.move_no_var, width=14).pack(side=tk.LEFT, padx=4)
        tk.Label(row2, text="移出库位:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.remove_no_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.remove_no_var, width=14).pack(side=tk.LEFT, padx=4)
        tk.Label(row2, text="制单人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.created_by_var = tk.StringVar()
        self.created_by_cb = ttk.Combobox(row2, textvariable=self.created_by_var,
                                          values=[""], width=16)
        self.created_by_cb.pack(side=tk.LEFT, padx=4)
        tk.Label(row2, text="移库状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.status_var = tk.StringVar(value="全部")
        self.status_cb = ttk.Combobox(row2, textvariable=self.status_var,
                                      values=["全部"], state="readonly", width=12)
        self.status_cb.pack(side=tk.LEFT, padx=4)

        row3 = tk.Frame(filter_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=4)
        tk.Label(row3, text="调整时间:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        month = datetime.now().month - 2
        year = datetime.now().year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        self.start_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(date(year, month, 1))
        self.start_cal.pack(side=tk.LEFT, padx=4)
        tk.Label(row3, text="至", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(date.today())
        self.end_cal.pack(side=tk.LEFT, padx=4)

        btn_row = tk.Frame(filter_frame, bg="#f0f0f0")
        btn_row.pack(fill=tk.X, pady=(6, 2))
        tk.Button(btn_row, text="查询", command=self.query,
                  bg="#4CAF50", fg="white", padx=10, pady=4, bd=0,
                  activebackground="#45a049").pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text="重置", command=self.reset_form,
                  bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=4)

    def setup_action_bar(self, parent):
        bar = tk.Frame(parent, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=(0, 3))
        tk.Button(bar, text="新增移库", command=self.open_new,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="编辑", command=self.open_edit,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="明细", command=self.open_detail,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="导出Excel", command=self.export_excel,
                  bg="#fa8c16", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Label(bar, text="提示：单击选行；双击行查看明细；仅「待提交」可编辑",
                 bg="#f0f0f0", fg="#666666", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="库位调整信息", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("移库单号", "调整原因") else "center"
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.tag_configure("odd", background="#fafafa")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _e: self.open_detail())
        tooltip_manager.attach_tooltip(self.tree)

    def setup_pagination_controls(self, parent):
        pagination_frame = tk.Frame(parent, bg="#f0f0f0")
        pagination_frame.pack(fill=tk.X, pady=5)
        self.page_info_var = tk.StringVar(value="第 1/1 页")
        tk.Label(pagination_frame, textvariable=self.page_info_var,
                 bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}
        tk.Button(pagination_frame, text="首页",
                  command=lambda: self.go_to_page(1), **style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="上一页",
                  command=lambda: self.go_to_page(self.page_num - 1), **style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="下一页",
                  command=lambda: self.go_to_page(self.page_num + 1), **style).pack(side=tk.LEFT, padx=2)
        tk.Button(pagination_frame, text="尾页",
                  command=lambda: self.go_to_page(self.total_pages), **style).pack(side=tk.LEFT, padx=2)

    # ================================================================ 工具
    @property
    def total_pages(self):
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    @staticmethod
    def fmt_num(val):
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return str(int(n)) if n % 1 == 0 else "%.2f" % n

    def _label(self, dict_type, code):
        if code is None or code == "":
            return "-"
        key = str(code)
        live = self.dict_maps.get(dict_type) or {}
        if key in live:
            return live[key]
        return (DICT_FALLBACK.get(dict_type) or {}).get(key, key)

    def decode_status(self, code):
        return self._label(DICT_STATUS, code)

    # ================================================================ 基础数据
    def load_dicts(self):
        threading.Thread(target=self._dicts_thread, daemon=True).start()

    def _dicts_thread(self):
        try:
            r = self.controller.session.get(URL_DICTS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 字典加载失败，用兜底: %s" % e)
            return
        d = data.get('data') or {}
        groups = d.get('dict') or d
        arr = groups.get(DICT_STATUS) or []
        m = {}
        for x in arr if isinstance(arr, list) else []:
            if isinstance(x, dict) and x.get('code_id') is not None:
                m[str(x['code_id'])] = x.get('code_cn_desc') or ''
        if m:
            self.controller.after(0, lambda: self._render_dicts({DICT_STATUS: m}))

    def _render_dicts(self, maps):
        self.dict_maps = maps
        status_map = maps.get(DICT_STATUS) or DICT_FALLBACK[DICT_STATUS]
        self.status_cb.config(values=["全部"] + list(status_map.values()))
        self.status_var.set("全部")

    def load_warehouses(self):
        threading.Thread(target=self._wh_thread, daemon=True).start()

    def _wh_thread(self):
        try:
            r = self.controller.session.get(URL_WH_PERM, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 仓库加载失败: %s" % e)
            return
        arr = data.get('data') or []
        pairs = [(str(x.get('name')), x.get('value')) for x in (arr if isinstance(arr, list) else [])
                 if isinstance(x, dict) and x.get('name') is not None]
        self.controller.after(0, lambda: self._render_warehouses(pairs))

    def _render_warehouses(self, pairs):
        self.wh_map = {name: value for name, value in pairs}
        self.warehouse_cb.config(values=["全部"] + [name for name, _v in pairs])

    # ================================================================ 查询
    def build_params(self):
        params = {'pageNum': self.page_num, 'pageSize': self.page_size}
        if self.warehouse_var.get() and self.warehouse_var.get() != "全部":
            params['warehouseId'] = self.wh_map.get(self.warehouse_var.get(), '')
        for key, var in (('shiftNo', self.shift_no_var), ('partNo', self.part_no_var),
                         ('partName', self.part_name_var), ('moveNo', self.move_no_var),
                         ('removeNo', self.remove_no_var),
                         ('createdByName', self.created_by_var)):
            val = var.get().strip()
            if val:
                params[key] = val
        if self.status_var.get() and self.status_var.get() != "全部":
            params['status'] = self._code_of(DICT_STATUS, self.status_var.get())
        params['startTime'] = self.start_cal.get()
        params['endTime'] = self.end_cal.get()
        return params

    def _code_of(self, dict_type, label):
        live = self.dict_maps.get(dict_type) or DICT_FALLBACK.get(dict_type) or {}
        for code, name in live.items():
            if name == label:
                return code
        return label

    def _validate_search(self, purpose="查询"):
        try:
            d0 = datetime.strptime(self.start_cal.get(), '%Y-%m-%d')
            d1 = datetime.strptime(self.end_cal.get(), '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("提示", "日期格式不正确")
            return False
        if (d1 - d0).days < 0:
            messagebox.showwarning("提示", "调整结束时间不能小于开始时间")
            return False
        return True

    def query(self, reset_page=True):
        if self.loading:
            return
        if reset_page:
            self.page_num = 1
        if not self._validate_search("查询"):
            return
        params = self.build_params()
        self.loading = True
        self.count_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_LIST, headers=HEADERS, params=params)
            print("[移库管理] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 查询异常: %s" % e)
            self.controller.after(0, lambda: self.count_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("错误", "查询异常: %s" % e))
            return
        finally:
            self.loading = False

        if not resp_ok(data):
            msg = err_msg(data, "查询失败")
            self.controller.after(0, lambda: self.count_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            return
        d = data.get('data') or {}
        rows = d.get('rows') or d.get('data') or d.get('records') or []
        total = d.get('total') or len(rows)
        self.controller.after(0, lambda: self._render_rows(rows, total))

    def _render_rows(self, rows, total):
        self.rows = rows
        self.total = total
        for it in self.tree.get_children():
            self.tree.delete(it)
        base = (self.page_num - 1) * self.page_size
        for idx, row in enumerate(rows):
            values = (
                base + idx + 1,
                row.get('warehouseName') or '-',
                row.get('shiftNo') or '-',
                row.get('createdByName') or '-',
                row.get('createdAt') or '-',
                row.get('remark') or '-',
                self.decode_status(row.get('status')),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.count_var.set("共 %d 条移库单" % total)
        self.update_page_info()

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

    def reset_form(self):
        self.warehouse_var.set("全部")
        self.shift_no_var.set("")
        self.part_no_var.set("")
        self.part_name_var.set("")
        self.move_no_var.set("")
        self.remove_no_var.set("")
        self.created_by_var.set("")
        self.status_var.set("全部")
        month = datetime.now().month - 2
        year = datetime.now().year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        self.start_cal.set_date(date(year, month, 1))
        self.end_cal.set_date(date.today())

    def current_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        return self.rows[idx] if 0 <= idx < len(self.rows) else None

    # ================================================================ 状态闸门
    @staticmethod
    def can_edit(row):
        try:
            return int(row.get('status')) in EDITABLE_STATUS
        except (TypeError, ValueError):
            return False

    # ================================================================ 导出
    def export_excel(self):
        if not self._validate_search("导出"):
            return
        params = self.build_params()
        params.pop('pageNum', None)
        params.pop('pageSize', None)
        params['limit'] = 9999999
        path = filedialog.asksaveasfilename(
            title="导出移库管理",
            initialfile="库位调整信息_%s.xlsx" % datetime.now().strftime('%Y%m%d_%H%M'),
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
        if not path:
            return
        self.count_var.set("导出中...")
        threading.Thread(target=self._export_thread, args=(params, path), daemon=True).start()

    def _export_thread(self, params, path):
        try:
            r = self.controller.session.get(URL_EXPORT, headers=HEADERS, params=params)
            if not self._check_response(r):
                return
            if r.status_code != 200 or not r.content:
                raise RuntimeError("HTTP %s，无内容" % r.status_code)
            with open(path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print("[移库管理] 导出异常: %s" % e)
            self.controller.after(0, lambda: self.count_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("错误", "导出失败: %s" % e))
            return
        self.controller.after(0, lambda: self.count_var.set("已导出: %s" % path))
        self.controller.after(0, lambda: messagebox.showinfo("成功", "导出完成:\n%s" % path))
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception:
            pass

    # ================================================================ 新增 / 编辑
    def open_new(self):
        self._open_edit_dialog(row=None)

    def open_edit(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        if not self.can_edit(row):
            messagebox.showwarning("提示", "仅「待提交」状态的移库单可编辑")
            return
        self._open_edit_dialog(row=row)

    def _open_edit_dialog(self, row):
        is_edit = row is not None
        # 仓库基础数据为异步加载，未就绪时下拉为空会导致无法选择，先拦截
        if not self.wh_map:
            messagebox.showwarning("提示", "仓库数据尚未加载完成，请稍后重试")
            return
        self._edit_meta = {
            'is_edit': is_edit,
            'shiftNo': row.get('shiftNo') if is_edit else None,
            'status': row.get('status') if is_edit else None,
            'warehouseId': row.get('warehouseId') if is_edit else None,
            'warehouseName': row.get('warehouseName') if is_edit else None,
            'remark': row.get('remark') if is_edit else None,
            'move_by': row.get('move_by') if is_edit else None,
            'recordVersion': row.get('recordVersion') if is_edit else None,
        }
        self._edit_detail_rows = []
        self._edit_deleted = []

        win = tk.Toplevel(self)
        win.title("编辑移库信息" if is_edit else "新增移库信息")
        win.geometry("1280x660")
        self._edit_win = win
        self._build_edit_dialog(win)
        if is_edit:
            self._load_edit_detail(row.get('shiftNo'))
        # 移库人列表（YKR）：新建时随仓库变化；编辑时按当前仓库
        self._reload_movers()

    def _build_edit_dialog(self, win):
        meta = self._edit_meta
        top = tk.LabelFrame(win, text="移库信息", bg="#f0f0f0",
                            font=("微软雅黑", 10, "bold"))
        top.pack(fill=tk.X, padx=10, pady=(8, 4), ipadx=6, ipady=4)

        tk.Label(top, text="仓库:", bg="#f0f0f0").grid(row=0, column=0, sticky="e", padx=4, pady=6)
        self.e_wh = ttk.Combobox(top, values=list(self.wh_map.keys()),
                                 state="readonly", width=16)
        if meta['is_edit']:
            self.e_wh.config(state="disabled")
        self.e_wh.grid(row=0, column=1, sticky="w", padx=4, pady=6)
        self.e_wh.bind("<<ComboboxSelected>>", lambda _e: self._on_wh_change())

        tk.Label(top, text="移库原因:", bg="#f0f0f0").grid(row=0, column=2, sticky="e", padx=4, pady=6)
        self.e_remark = ttk.Entry(top, width=30)
        self.e_remark.grid(row=0, column=3, sticky="w", padx=4, pady=6)

        tk.Label(top, text="移库人:", bg="#f0f0f0").grid(row=0, column=4, sticky="e", padx=4, pady=6)
        self._move_by_var = tk.StringVar()
        self.e_move_by = ttk.Entry(top, textvariable=self._move_by_var, width=26, state="readonly")
        self.e_move_by.grid(row=0, column=5, sticky="w", padx=4, pady=6)
        tk.Button(top, text="选择", command=self._pick_movers,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=8).grid(row=0, column=6, padx=4)

        tk.Label(top, text="移库单号:", bg="#f0f0f0").grid(row=0, column=7, sticky="e", padx=4, pady=6)
        self.e_shift_no = ttk.Entry(top, width=22)
        self.e_shift_no.insert(0, meta.get('shiftNo') or '系统生成')
        self.e_shift_no.config(state="readonly")
        self.e_shift_no.grid(row=0, column=8, sticky="w", padx=4, pady=6)

        if meta['is_edit']:
            self.e_wh.set(meta.get('warehouseName') or '')
            self.e_remark.insert(0, meta.get('remark') or '')
            self._move_by_var.set(meta.get('move_by') or '')

        # ---- 明细区 ----
        mid = tk.LabelFrame(win, text="移库明细", bg="#f0f0f0",
                            font=("微软雅黑", 10, "bold"))
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        mbar = tk.Frame(mid, bg="#f0f0f0")
        mbar.pack(fill=tk.X, pady=2)
        tk.Button(mbar, text="添加一行", command=self._add_detail_row,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(mbar, text="编辑行", command=self._edit_detail_row,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(mbar, text="删除行", command=self._remove_detail_row,
                  bg="#f5222d", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Label(mbar, text="（移入库位与移库数量必填，移库数量 ≤ 可用数量）", bg="#f0f0f0",
                 fg="#666666", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(mid, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True)
        self._edit_tree = ttk.Treeview(body, columns=DETAIL_COLUMNS, show="headings", height=10)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            self._edit_tree.heading(col, text=col)
            anchor = "w" if col in ("产品名称", "CARG全码/产品编码") else "center"
            self._edit_tree.column(col, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(body, orient="vertical", command=self._edit_tree.yview)
        hsb = ttk.Scrollbar(body, orient="horizontal", command=self._edit_tree.xview)
        self._edit_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._edit_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._edit_tree.bind("<Double-1>", lambda _e: self._edit_detail_row())

        # ---- 底部按钮 ----
        foot = tk.Frame(win, bg="#f0f0f0")
        foot.pack(fill=tk.X, padx=10, pady=8)
        editable = (not meta['is_edit']) or meta.get('status') in EDITABLE_STATUS
        state = "normal" if editable else "disabled"
        self.e_save_btn = tk.Button(foot, text="保存", command=lambda: self._submit(CHECK_SAVE),
                                    bg="#4CAF50", fg="white", relief=tk.FLAT, padx=16, pady=5,
                                    state=state)
        self.e_save_btn.pack(side=tk.LEFT, padx=4)
        self.e_submit_btn = tk.Button(foot, text="提交", command=lambda: self._submit(CHECK_SUBMIT),
                                      bg="#4CAF50", fg="white", relief=tk.FLAT, padx=16, pady=5,
                                      state=state)
        self.e_submit_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(foot, text="返回", command=self._close_edit,
                  bg="#e1e1e1", relief=tk.FLAT, padx=16, pady=5).pack(side=tk.LEFT, padx=4)
        if not editable:
            tk.Label(foot, text="该单据已提交，不可编辑", bg="#f0f0f0",
                     fg="#f5222d").pack(side=tk.LEFT, padx=10)

    # ------------------------------------------------------------ 移库人
    def _current_wh_id(self):
        return self.wh_map.get(self.e_wh.get())

    def _on_wh_change(self):
        """切换仓库 → 明细清空 + 重载移库人（对齐 Web changeWarehouseSelect/queryYKRInfo）。"""
        self._edit_detail_rows = []
        self._render_edit_detail()
        self._reload_movers()

    def _reload_movers(self):
        wh_id = self._current_wh_id()
        param_wh = wh_id if wh_id else -1
        threading.Thread(target=self._movers_thread, args=(param_wh,), daemon=True).start()

    def _movers_thread(self, warehouse_id):
        try:
            r = self.controller.session.get(
                BASE + '/dcscloud.basedata/basedata/employees/getEmpByRoleCode',
                headers=HEADERS, params={'roleCode': MOVER_ROLE, 'warehouseId': warehouse_id})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 移库人加载失败: %s" % e)
            return
        arr = data.get('data') or []
        names = []
        for u in arr if isinstance(arr, list) else []:
            if isinstance(u, dict):
                n = u.get('EMPLOYEE_NAME') or u.get('name')
                if n:
                    names.append(n)
        self.controller.after(0, lambda: setattr(self, 'movers', names))

    def _pick_movers(self):
        preselect = [s.strip() for s in (self._move_by_var.get() or '').split(',') if s.strip()]

        def on_pick(names):
            self._move_by_var.set(','.join(names))

        EmployeeMultiPicker(self._edit_win, self.controller, MOVER_ROLE, on_pick,
                            warehouse_id=self._current_wh_id() or -1,
                            title="选择移库人", preselect=preselect)

    # ------------------------------------------------------------ 明细载入
    def _load_edit_detail(self, shift_no):
        if not shift_no:
            return
        threading.Thread(target=self._load_detail_thread, args=(shift_no,), daemon=True).start()

    def _load_detail_thread(self, shift_no):
        try:
            r = self.controller.session.get(URL_QUERY_BY_NO, headers=HEADERS,
                                            params={'shiftNo': shift_no})
            print("[移库管理] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 明细加载失败: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "明细加载失败: %s" % e))
            return
        arr = data.get('data') or []
        rows = []
        for t in arr if isinstance(arr, list) else []:
            if not isinstance(t, dict):
                continue
            row = dict(t)
            # Web initPage：已有移入库位 → select_LOCATION_OPTIONS 2 字段
            if row.get('moveNo'):
                row['select_LOCATION_OPTIONS'] = [{
                    'locationId': row.get('moveNoId'),
                    'locationNo': row.get('moveNo'),
                }]
            rows.append(row)
        self.controller.after(0, lambda: self._apply_detail_rows(rows))

    def _apply_detail_rows(self, rows):
        self._edit_detail_rows = rows
        self._render_edit_detail()

    def _render_edit_detail(self):
        if self._edit_tree is None or not self._edit_tree.winfo_exists():
            return
        for it in self._edit_tree.get_children():
            self._edit_tree.delete(it)
        for i, row in enumerate(self._edit_detail_rows):
            self._edit_tree.insert("", "end", iid=str(i), values=(
                i + 1,
                row.get('warehouseName') or self.e_wh.get() or '-',
                row.get('partCode') or '-',
                row.get('partName') or '-',
                row.get('brandName') or '-',
                row.get('removeNo') or '-',
                self._move_no_label(row),
                self.fmt_num(row.get('availableQty')),
                self.fmt_num(row.get('moveQty')),
            ))

    def _move_no_label(self, row):
        loc_id = row.get('moveNoId')
        if not loc_id:
            return '-'
        for o in (row.get('select_LOCATION_OPTIONS') or []):
            if o.get('locationId') == loc_id:
                return o.get('locationNo') or row.get('moveNo') or str(loc_id)
        return row.get('moveNo') or str(loc_id)

    def _selected_detail_index(self):
        sel = self._edit_tree.selection() if self._edit_tree else ()
        if not sel:
            return None
        idx = self._edit_tree.index(sel[0])
        return idx if 0 <= idx < len(self._edit_detail_rows) else None

    # ------------------------------------------------------------ 明细增删改
    def _add_detail_row(self):
        wh_id = self._current_wh_id()
        if not wh_id:
            messagebox.showwarning("提示", "请先选择仓库")
            return

        def on_pick(picked):
            existing = {(r.get('partCode'), r.get('brand'), r.get('removeNo'))
                        for r in self._edit_detail_rows}
            added = 0
            for p in picked:
                row = dict(p)
                key = (row.get('partCode'), row.get('brand'), row.get('removeNo'))
                if key in existing:
                    messagebox.showwarning("提示", "%s（库位 %s）已添加，请勿重复添加"
                                           % (row.get('partCode') or '', row.get('removeNo') or '-'))
                    continue
                row.setdefault('warehouseId', wh_id)
                # PC 便捷：默认移库数量 = 可用数量（可编辑）
                if row.get('moveQty') in (None, ''):
                    row['moveQty'] = row.get('availableQty')
                row.setdefault('removeNo', row.get('removeNo') or '')
                row['select_LOCATION_OPTIONS'] = row.get('select_LOCATION_OPTIONS') or []
                self._edit_detail_rows.append(row)
                existing.add(key)
                added += 1
            if added:
                self._render_edit_detail()

        ProductPickerDialog(self._edit_win, self.controller,
                            query_url=URL_QUERY_PART_CHANGE,
                            warehouse_id=wh_id,
                            on_pick=on_pick,
                            title="选择产品（移库仓库）",
                            allow_multi=True)

    def _edit_detail_row(self):
        idx = self._selected_detail_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一行明细")
            return
        row = self._edit_detail_rows[idx]
        win = tk.Toplevel(self._edit_win)
        win.title("编辑明细 - %s" % (row.get('partCode') or ''))
        win.geometry("580x320")
        win.transient(self._edit_win)

        info = tk.LabelFrame(win, text="产品", bg="#f0f0f0")
        info.pack(fill=tk.X, padx=10, pady=8, ipadx=6, ipady=4)
        tk.Label(info, text=row.get('partName') or '-', bg="#f0f0f0",
                 wraplength=540, justify="left").pack(anchor="w", padx=4)
        tk.Label(info, text="编码: %s   品牌: %s   可用数量: %s   移出库位: %s"
                 % (row.get('partCode') or '-', row.get('brandName') or '-',
                    self.fmt_num(row.get('availableQty')), row.get('removeNo') or '-'),
                 bg="#f0f0f0", fg="#666666").pack(anchor="w", padx=4)

        form = tk.Frame(win, bg="#f0f0f0")
        form.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(form, text="移库数量:", bg="#f0f0f0").grid(row=0, column=0, sticky="e", padx=4, pady=8)
        qty_var = tk.StringVar(value='' if row.get('moveQty') in (None, '') else str(row.get('moveQty')))
        ttk.Entry(form, textvariable=qty_var, width=14).grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(form, text="移入库位:", bg="#f0f0f0").grid(row=1, column=0, sticky="e", padx=4, pady=8)
        loc_var = tk.StringVar(value=self._move_no_label(row) if row.get('moveNoId') else '')
        ttk.Entry(form, textvariable=loc_var, width=18, state="readonly").grid(row=1, column=1, sticky="w", padx=4)

        def pick_loc():
            wh_id = self._current_wh_id()
            if not wh_id:
                messagebox.showwarning("提示", "请先选择仓库")
                return

            def on_loc(loc):
                row['moveNoId'] = loc.get('locationId')
                row['moveNo'] = loc.get('locationNo')
                # 远端新选 → 存完整对象（6 字段）
                row['select_LOCATION_OPTIONS'] = [loc]
                loc_var.set(loc.get('locationNo') or '')

            LocationPickerDialog(win, self.controller, wh_id, on_loc,
                                 title="选择移入库位")

        tk.Button(form, text="选择库位", command=pick_loc,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=8).grid(row=1, column=2, padx=6)

        def do_save():
            raw = qty_var.get().strip()
            try:
                qty = int(float(raw))
            except (TypeError, ValueError):
                messagebox.showwarning("提示", "移库数量请输入大于零的数字")
                return
            if qty < 1:
                messagebox.showwarning("提示", "移库数量请输入大于零的数字")
                return
            avail = row.get('availableQty')
            try:
                if avail is not None and qty > int(float(avail)):
                    messagebox.showwarning("提示", "移库数量不能大于可用数量（%s）" % self.fmt_num(avail))
                    return
            except (TypeError, ValueError):
                pass
            row['moveQty'] = qty
            self._render_edit_detail()
            win.destroy()

        foot = tk.Frame(win, bg="#f0f0f0")
        foot.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(foot, text="确定", command=do_save,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=14, pady=4).pack(side=tk.LEFT)
        tk.Button(foot, text="取消", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14, pady=4).pack(side=tk.LEFT, padx=6)

    def _remove_detail_row(self):
        idx = self._selected_detail_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一行明细")
            return
        row = self._edit_detail_rows.pop(idx)
        if row.get('logId'):
            self._edit_deleted.append(row)
        self._render_edit_detail()

    # ------------------------------------------------------------ 提交
    @staticmethod
    def _clean_row(row):
        return {k: v for k, v in row.items() if k not in UI_ONLY_KEYS}

    def _build_payload(self, check_status):
        meta = self._edit_meta
        return {
            'shiftNo': meta.get('shiftNo'),
            'warehouseId': self._current_wh_id(),
            'remark': self.e_remark.get().strip() or None,
            'checkStatus': check_status,
            'status': meta.get('status'),
            'detailDtoList': [self._clean_row(r) for r in self._edit_detail_rows],
            'detailDtoListDelete': [self._clean_row(r) for r in self._edit_deleted],
            'move_by': self._move_by_var.get().strip() or None,
        }

    def _submit(self, check_status):
        if not self._current_wh_id():
            messagebox.showwarning("提示", "请选择仓库")
            return
        if not (self._move_by_var.get() or '').strip():
            messagebox.showwarning("提示", "请选择移库人")
            return
        if not self._edit_detail_rows:
            messagebox.showwarning("提示", "请添加明细")
            return
        for i, row in enumerate(self._edit_detail_rows):
            if not row.get('removeNo'):
                messagebox.showwarning("提示", "第 %d 行移出库位不能为空" % (i + 1))
                return
            if not row.get('moveNo'):
                messagebox.showwarning("提示", "第 %d 行移入库位不能为空" % (i + 1))
                return
            q = row.get('moveQty')
            try:
                qv = int(float(q))
            except (TypeError, ValueError):
                qv = 0
            if qv < 1:
                messagebox.showwarning("提示", "第 %d 行移库数量不能为空且须大于零" % (i + 1))
                return
            avail = row.get('availableQty')
            try:
                if avail is not None and qv > int(float(avail)):
                    messagebox.showwarning("提示", "第 %d 行移库数量不能大于可用数量" % (i + 1))
                    return
            except (TypeError, ValueError):
                pass
            row['moveQty'] = qv

        action = "保存" if check_status == CHECK_SAVE else "提交"
        if not messagebox.askyesno(action, "是否确认%s？" % action):
            return
        payload = self._build_payload(check_status)
        self._set_edit_btns("disabled", "%s中..." % action)
        threading.Thread(target=self._submit_thread, args=(payload, action), daemon=True).start()

    def _set_edit_btns(self, state, text=None):
        for btn, label in ((self.e_save_btn, "保存"), (self.e_submit_btn, "提交")):
            if btn.winfo_exists():
                btn.config(state=state, text=(text or label))

    def _submit_thread(self, payload, action):
        print("[移库管理] %s payload: %s" % (action, json.dumps(payload, ensure_ascii=False)[:800]))
        try:
            r = self.controller.session.post(URL_SAVE, headers=HEADERS,
                                             data=json.dumps(payload, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] %s 异常: %s" % (action, e))
            self.controller.after(0, lambda: messagebox.showerror("错误", "%s失败: %s" % (action, e)))
            self.controller.after(0, lambda: self._set_edit_btns("normal"))
            return
        if resp_ok(data):
            self.controller.after(0, lambda: messagebox.showinfo("成功", "%s成功" % action))
            self.controller.after(0, self._close_edit)
            self.controller.after(0, lambda: self.query(reset_page=False))
        else:
            msg = err_msg(data, "%s失败" % action)
            self.controller.after(0, lambda: messagebox.showerror("%s失败" % action, str(msg)))
            self.controller.after(0, lambda: self._set_edit_btns("normal"))

    def _close_edit(self):
        if self._edit_win and self._edit_win.winfo_exists():
            self._edit_win.destroy()
        self._edit_win = None
        self._edit_detail_rows = []
        self._edit_deleted = []
        self._edit_tree = None
        self._move_by_var = None

    # ================================================================ 明细（只读）
    def open_detail(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        win = tk.Toplevel(self)
        win.title("移库信息 - %s" % (row.get('shiftNo') or ''))
        win.geometry("1100x580")
        self._detail_win = win

        head = tk.LabelFrame(win, text="移库信息", bg="#f0f0f0",
                             font=("微软雅黑", 10, "bold"))
        head.pack(fill=tk.X, padx=10, pady=(8, 4), ipadx=6, ipady=4)
        items = [
            ("移库单号", row.get('shiftNo')), ("仓库", row.get('warehouseName')),
            ("制单人", row.get('createdByName')), ("移库人", row.get('move_by')),
            ("创建时间", row.get('createdAt')),
            ("移库状态", self.decode_status(row.get('status'))),
            ("调整原因", row.get('remark')),
        ]
        for i, (k, v) in enumerate(items):
            tk.Label(head, text="%s:" % k, bg="#f0f0f0", fg="#666666").grid(
                row=i // 4, column=(i % 4) * 2, sticky="e", padx=4, pady=3)
            tk.Label(head, text=str(v if v not in (None, '') else '-'), bg="#f0f0f0").grid(
                row=i // 4, column=(i % 4) * 2 + 1, sticky="w", padx=4, pady=3)

        body = tk.Frame(win, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        tree = ttk.Treeview(body, columns=VIEW_COLUMNS, show="headings", height=14)
        for col, width in zip(VIEW_COLUMNS, VIEW_WIDTHS):
            tree.heading(col, text=col)
            anchor = "w" if col in ("产品名称", "CARG全码/产品编码") else "center"
            tree.column(col, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(body, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        tooltip_manager.attach_tooltip(tree)

        tk.Button(win, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=16, pady=4).pack(pady=8)

        threading.Thread(target=self._detail_thread,
                         args=(row.get('shiftNo'), tree), daemon=True).start()

    def _detail_thread(self, shift_no, tree):
        try:
            r = self.controller.session.get(URL_QUERY_BY_NO, headers=HEADERS,
                                            params={'shiftNo': shift_no})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[移库管理] 明细请求异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载明细失败: %s" % e))
            return
        arr = data.get('data') or []
        self.controller.after(0, lambda: self._render_detail(tree, arr))

    def _render_detail(self, tree, rows):
        if not tree.winfo_exists():
            return
        for i, d in enumerate(rows if isinstance(rows, list) else []):
            if not isinstance(d, dict):
                continue
            tree.insert("", "end", values=(
                i + 1,
                d.get('warehouseName') or '-',
                d.get('partCode') or '-',
                d.get('partName') or '-',
                d.get('brandName') or '-',
                d.get('removeNo') or '-',
                d.get('moveNo') or '-',
                self.fmt_num(d.get('moveQty')),
            ))

# -*- coding: utf-8 -*-
"""库内作业 — 调拨申请（调入申请）

对齐 Web 源（dms_vue-prod，用户提供的反编译 JS）：
- 列表页   ``transferInApplication/index.vue``  → ``index-2643ebf1.js``
- 编辑弹窗 ``transferInApplication/components/editDialog.vue`` → ``editDialog-cc793868.js``
- 明细弹窗 ``detailDialog.vue`` → ``detailDialog-6d7da009.js``
- 接口桶   ``index-b46d22fe.js``
并对照安卓端 ``TransferApplication.vue`` + ``service`` 层。

接口清单（baseURL https://xb.fy-carg.com）
========================================
- 列表     GET  /dmscloud.part/warehouse/transferIn/application
           ?searchType=application&transferNo&partNo&partName&moveWarehouse
            &removeWarehouse&createdByName&status&startTime&endTime&remark
            &pageNum&pageSize
- 明细     GET  /dmscloud.part/warehouse/transferIn/findById?transferId=
- 保存/提交 POST /dmscloud.part/warehouse/transferIn/saveTransfer
- 删除     POST /dmscloud.part/warehouse/transferIn/delete      （body = 整行对象）
- 导出     GET  /dmscloud.part/warehouse/transferIn/export/excel?<同列表查询参数>
- 调出仓库 GET  /dmscloud.part/warehouse/manage/queryListForSelect
- 调入仓库 GET  /dmscloud.part/warehouse/manage/queryListWithPermissions
- 包装方式 GET  /dmscloud.part/boxModelManage/queryBoxModelManageList
- 制单人   GET  /dcscloud.basedata/basedata/employees/searchUserInfo
- 库位搜索 GET  /dmscloud.part/warehouse/transferIn/findAllLocationValid
- 产品搜索 GET  /dmscloud.part/warehouse/transferIn/queryPart
- 字典     GET  /dmscloud.basedata/dicts（4716 状态 / 4717 类型 / 4617 物流）

关键业务规则（逐条对齐 Web 源 / HAR 实测）
========================================
1. ``searchType`` 固定 ``application``（列表）；另有 ``inbound`` 供调拨入库页使用。
2. 列表默认筛选：调拨申请时间起 = 今天往前 2 个月、止 = 今天；制单人默认当前登录人
   （Web ``search.createdByName = userInfo.userName``）。**PC 端登录仅存 cookies、
   无当前用户名**（同报销/内部领用/报损出库），故 PC 端制单人默认留空，需用户自行
   选择——时间起止已构成有效条件，查询不受影响。
3. 校验（Web ``searchHandle``）：起止时间必填、间隔 ≤ 366 天、且至少一个条件非空。
4. 编辑按钮可用状态：``transferStatus ∈ {47161001 待提交, 47161004 审核驳回}``。
   删除按钮可用：``47161001``，或 ``47161004 且 createdBy == 当前用户账号``
   （PC 端无当前账号，故仅对 ``47161001`` 放行，避免越权；见 ``can_delete``）。
5. 保存/提交报文（Web ``infoSave``）：
   ``{id, transferType, logisticsMode, moveWarehouseId, removeWarehouseId, remark,
      checkStatus, isWarehouseOutbound, detailDtoList, detailDtoListDelete, boxId,
      recordVersion}``；``checkStatus`` 10041001 保存 / 10041002 提交；
   ``isWarehouseOutbound`` 固定 10041001。
6. 明细行字段（Web ``initPage`` + HAR findById）：原样回传服务端字段
   （detailId/brand/brandId/brandName/partCode/partId/partName/availableQty/
    removeWarehouseId/recordVersion/remarks 等），并叠加用户编辑：
   ``transferQuantity``（申请数量，≥1）、``remarks``（特别说明）、
   ``inboundLocationId``/``inboundLocation``（入库库位）。
7. ``select_LOCATION_OPTIONS`` 语义（与调拨入库页同一条铁律）：
   - 载入服务端已有库位 → ``[{locationId, locationNo}]``（2 字段）；
   - 用户远端搜索新选 → 存入 findAllLocationValid 返回的完整对象（6 字段），
     提交时原样带出。
   本页入库库位为**单选**，故列表恒为 1 个元素。
8. 唯一性：调入仓库不得等于调出仓库（Web ``infoSave`` 显式校验）。
9. 本页编辑弹窗 Web 源虽定义了 ``splitRow`` 方法，但**模板未渲染拆行按钮**
   （模板扫描证据：editDialog-cc793868.js 明细列仅
   序号/操作/partCode/partName/brandName/availableQty/transferQuantity/
   remarks/inboundLocationId），故按源码真相源**不提供拆行**，避免引入
   Web UI 并不存在的能力。
10. 明细行为空时禁止保存（Web：「请添加明细」）。

与安卓端的差异
============
安卓端 ``TransferApplication.vue`` 的 ``submitCreate`` 未接通（提示「保存功能待接入」）；
本页以 **Web 源**为准接通 saveTransfer，实现完整新增/编辑/保存/提交。
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
    URL_QUERY_PART_TRANSFER_IN,
    resp_ok,
    err_msg,
)

# ---------------------------------------------------------------- 接口
BASE = 'https://xb.fy-carg.com'
PART = BASE + '/dmscloud.part'
BASEDATA = BASE + '/dcscloud.basedata'

URL_LIST = PART + '/warehouse/transferIn/application'
URL_FIND_BY_ID = PART + '/warehouse/transferIn/findById'
URL_SAVE = PART + '/warehouse/transferIn/saveTransfer'
URL_DELETE = PART + '/warehouse/transferIn/delete'
URL_EXPORT = PART + '/warehouse/transferIn/export/excel'

URL_WH_SELECT = PART + '/warehouse/manage/queryListForSelect'
URL_WH_PERM = PART + '/warehouse/manage/queryListWithPermissions'
URL_BOX = PART + '/boxModelManage/queryBoxModelManageList'
URL_USERS = BASEDATA + '/basedata/employees/searchUserInfo'
URL_DICTS = BASE + '/dmscloud.basedata/dicts'

# ---------------------------------------------------------------- 常量
SEARCH_TYPE = 'application'
PAGE_SIZE = 20

CHECK_SAVE = 10041001      # 保存（暂存）
CHECK_SUBMIT = 10041002    # 提交
IS_WAREHOUSE_OUTBOUND = 10041001   # HAR/Web 实测固定值

# 可编辑状态（Web: edit 按钮 disabled 条件取反）
EDITABLE_STATUS = (47161001, 47161004)
# 可删除状态（Web 另加 47161004 且 createdBy==账号；PC 无账号，仅放行 47161001）
DELETABLE_STATUS = (47161001,)

# 字典类型
DICT_STATUS = '4716'    # 调拨状态
DICT_TYPE = '4717'      # 调拨类型
DICT_LOGISTICS = '4617'  # 物流方式

# 字典兜底（HAR 实测 /dmscloud.basedata/dicts 全量）
DICT_FALLBACK = {
    DICT_STATUS: {
        '47161001': '待提交', '47161002': '待审核', '47161003': '审核通过',
        '47161004': '审核驳回', '47161005': '取消调拨', '47161006': '已入库',
        '47161007': '部分入库', '47161008': '待签收', '47161009': '待上架',
    },
    DICT_TYPE: {'47171001': '平价调拨', '47171002': '加价调拨'},
    DICT_LOGISTICS: {
        '46171001': '送货', '46171002': '物流代收', '46171003': '物流发货',
        '46171004': '自提', '46171005': '快递',
    },
}

# 列表列（对齐 Web index-2643ebf1.js 表头顺序）
COLUMNS = ['序号', '调拨单号', '调入方', '调出方', '调拨类型', '调拨申请时间',
           '调拨状态', '调拨发起人', '物流方式', '包装方式', '审核人', '审核时间',
           '摘要']
COLUMN_WIDTHS = [50, 180, 100, 100, 90, 150, 90, 110, 100, 100, 100, 150, 180]

# 编辑弹窗明细列（对齐 Web editDialog 模板）
DETAIL_COLUMNS = ['序号', 'CARG全码/产品编码', '产品名称', '品牌', '可调拨数量',
                  '申请数量', '特别说明', '入库库位']
DETAIL_WIDTHS = [45, 160, 300, 100, 100, 100, 140, 140]

# 明细弹窗（只读）列（对齐 Web detailDialog）
VIEW_COLUMNS = ['序号', 'CARG全码/产品编码', '产品名称', '品牌', '申请数量',
                '特别说明', '入库库位']
VIEW_WIDTHS = [45, 160, 320, 100, 100, 160, 140]


class TransferApplicationPage(BasePage):
    """库内作业 — 调拨申请（调入申请）页面"""

    def __init__(self, parent, controller):
        self.rows = []
        self.total = 0
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.loading = False

        self.dict_maps = {}
        self.move_wh_map = {}      # 调入方 name -> value
        self.remove_wh_map = {}    # 调出方 name -> value
        self.user_names = []
        self.box_list = []         # [{id, box_name, box_type, box_model}]

        # 编辑弹窗状态
        self._edit_win = None
        self._edit_detail_rows = []    # 当前明细行（dict 列表）
        self._edit_deleted = []        # 删除明细累计
        self._edit_meta = {}           # addForm 元信息
        self._edit_tree = None
        self._edit_dirty_labels = {}   # 头部字段展示控件

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
        self.load_users()
        self.load_boxes()

    # ------------------------------------------------------------ 查询条件
    def setup_filter_panel(self, parent):
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=4)
        tk.Label(row1, text="调拨单号:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.transfer_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.transfer_no_var, width=18).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="CARG全码/产品编码:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.part_no_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_no_var, width=18).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.part_name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.part_name_var, width=18).pack(side=tk.LEFT, padx=4)

        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="调入方:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.move_wh_var = tk.StringVar(value="全部")
        self.move_wh_cb = ttk.Combobox(row2, textvariable=self.move_wh_var,
                                       values=["全部"], state="readonly", width=12)
        self.move_wh_cb.pack(side=tk.LEFT, padx=4)
        tk.Label(row2, text="调出方:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.remove_wh_var = tk.StringVar(value="全部")
        self.remove_wh_cb = ttk.Combobox(row2, textvariable=self.remove_wh_var,
                                         values=["全部"], state="readonly", width=12)
        self.remove_wh_cb.pack(side=tk.LEFT, padx=4)
        tk.Label(row2, text="制单人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.created_by_var = tk.StringVar()
        self.created_by_cb = ttk.Combobox(row2, textvariable=self.created_by_var,
                                          values=[""], width=16)
        self.created_by_cb.pack(side=tk.LEFT, padx=4)

        row3 = tk.Frame(filter_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=4)
        tk.Label(row3, text="调拨状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.status_var = tk.StringVar(value="全部")
        self.status_cb = ttk.Combobox(row3, textvariable=self.status_var,
                                      values=["全部"], state="readonly", width=12)
        self.status_cb.pack(side=tk.LEFT, padx=4)
        tk.Label(row3, text="调拨申请时间:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        default_start = datetime.now().replace(day=1)
        # 2 个月前
        month = default_start.month - 2
        year = default_start.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        self.start_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(date(year, month, 1))
        self.start_cal.pack(side=tk.LEFT, padx=4)
        tk.Label(row3, text="至", bg="#f0f0f0").pack(side=tk.LEFT, padx=4)
        self.end_cal = DateEntry(row3, width=12, date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(date.today())
        self.end_cal.pack(side=tk.LEFT, padx=4)
        tk.Label(row3, text="摘要:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 4))
        self.remark_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.remark_var, width=20).pack(side=tk.LEFT, padx=4)

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
        tk.Button(bar, text="新增调拨", command=self.open_new,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="编辑", command=self.open_edit,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="明细", command=self.open_detail,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="删除", command=self.delete_row,
                  bg="#f5222d", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text="导出Excel", command=self.export_excel,
                  bg="#fa8c16", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=3)
        tk.Label(bar, text="提示：单击选行；双击行查看明细", bg="#f0f0f0",
                 fg="#666666", font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=5)

    def setup_count_bar(self, parent):
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="调拨信息", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("调拨单号", "摘要") else "center"
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

    def decode_type(self, code):
        return self._label(DICT_TYPE, code)

    def decode_logistics(self, code):
        return self._label(DICT_LOGISTICS, code)

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
            print("[调拨申请] 字典加载失败，用兜底: %s" % e)
            return
        d = data.get('data') or {}
        groups = d.get('dict') or d
        maps = {}
        for g in (DICT_STATUS, DICT_TYPE, DICT_LOGISTICS):
            arr = groups.get(g) or []
            m = {}
            for x in arr if isinstance(arr, list) else []:
                if isinstance(x, dict) and x.get('code_id') is not None:
                    m[str(x['code_id'])] = x.get('code_cn_desc') or ''
            if m:
                maps[g] = m
        self.controller.after(0, lambda: self._render_dicts(maps))

    def _render_dicts(self, maps):
        self.dict_maps = maps
        status_map = maps.get(DICT_STATUS) or DICT_FALLBACK[DICT_STATUS]
        self.status_cb.config(values=["全部"] + list(status_map.values()))
        self.status_var.set("全部")

    def load_warehouses(self):
        threading.Thread(target=self._wh_thread, args=(URL_WH_SELECT, 'remove'), daemon=True).start()
        threading.Thread(target=self._wh_thread, args=(URL_WH_PERM, 'move'), daemon=True).start()

    def _wh_thread(self, url, kind):
        try:
            r = self.controller.session.get(url, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 仓库加载失败(%s): %s" % (kind, e))
            return
        arr = data.get('data') or []
        pairs = []
        for x in arr if isinstance(arr, list) else []:
            if isinstance(x, dict) and x.get('name') is not None:
                pairs.append((str(x.get('name')), x.get('value')))
        self.controller.after(0, lambda: self._render_warehouses(kind, pairs))

    def _render_warehouses(self, kind, pairs):
        mapping = {name: value for name, value in pairs}
        names = ["全部"] + [name for name, _v in pairs]
        if kind == 'remove':
            self.remove_wh_map = mapping
            self.remove_wh_cb.config(values=names)
        else:
            self.move_wh_map = mapping
            self.move_wh_cb.config(values=names)

    def load_users(self):
        threading.Thread(target=self._users_thread, daemon=True).start()

    def _users_thread(self):
        try:
            r = self.controller.session.get(URL_USERS, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 员工加载失败: %s" % e)
            return
        arr = data.get('data') or []
        names = []
        for u in arr if isinstance(arr, list) else []:
            if isinstance(u, dict):
                n = u.get('EMPLOYEE_NAME') or u.get('name')
                if n:
                    names.append(n)
        self.controller.after(0, lambda: self.created_by_cb.config(values=[""] + names))

    def load_boxes(self):
        threading.Thread(target=self._boxes_thread, daemon=True).start()

    def _boxes_thread(self):
        try:
            r = self.controller.session.get(URL_BOX, headers=HEADERS)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 包装方式加载失败: %s" % e)
            return
        arr = data.get('data') or []
        boxes = [x for x in arr if isinstance(x, dict)] if isinstance(arr, list) else []
        self.controller.after(0, lambda: setattr(self, 'box_list', boxes))

    # ================================================================ 查询
    def build_params(self):
        params = {
            'searchType': SEARCH_TYPE,
            'pageNum': self.page_num,
            'pageSize': self.page_size,
        }
        if self.transfer_no_var.get().strip():
            params['transferNo'] = self.transfer_no_var.get().strip()
        if self.part_no_var.get().strip():
            params['partNo'] = self.part_no_var.get().strip()
        if self.part_name_var.get().strip():
            params['partName'] = self.part_name_var.get().strip()
        if self.move_wh_var.get() and self.move_wh_var.get() != "全部":
            params['moveWarehouse'] = self.move_wh_map.get(self.move_wh_var.get(), '')
        if self.remove_wh_var.get() and self.remove_wh_var.get() != "全部":
            params['removeWarehouse'] = self.remove_wh_map.get(self.remove_wh_var.get(), '')
        if self.created_by_var.get().strip():
            params['createdByName'] = self.created_by_var.get().strip()
        if self.status_var.get() and self.status_var.get() != "全部":
            params['status'] = self._code_of(DICT_STATUS, self.status_var.get())
        params['startTime'] = self.start_cal.get()
        params['endTime'] = self.end_cal.get()
        if self.remark_var.get().strip():
            params['remark'] = self.remark_var.get().strip()
        return params

    def _code_of(self, dict_type, label):
        live = self.dict_maps.get(dict_type) or DICT_FALLBACK.get(dict_type) or {}
        for code, name in live.items():
            if name == label:
                return code
        return label

    def _validate_search(self, purpose="查询"):
        if not self.start_cal.get():
            messagebox.showwarning("提示", "请选择调拨申请开始时间")
            return False
        if not self.end_cal.get():
            messagebox.showwarning("提示", "请选择调拨申请截止时间")
            return False
        try:
            d0 = datetime.strptime(self.start_cal.get(), '%Y-%m-%d')
            d1 = datetime.strptime(self.end_cal.get(), '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("提示", "日期格式不正确")
            return False
        days = (d1 - d0).days
        if days < 0:
            messagebox.showwarning("提示", "调拨申请截止时间不能小于开始时间")
            return False
        if days > 366:
            messagebox.showwarning("提示", "%s时间间隔不能超过 366 天" % purpose)
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
            print("[调拨申请] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 查询异常: %s" % e)
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
                row.get('transferNo') or '-',
                row.get('moveWarehouseName') or '-',
                row.get('removeWarehouseName') or '-',
                self.decode_type(row.get('transferType')),
                row.get('createdAt') or '-',
                self.decode_status(row.get('transferStatus')),
                row.get('createdByName') or '-',
                self.decode_logistics(row.get('logisticsMode')),
                row.get('boxName') or '-',
                row.get('auditBy') or '-',
                row.get('auditDate') or '-',
                row.get('remark') or '-',
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.count_var.set("共 %d 条调拨申请" % total)
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
        self.transfer_no_var.set("")
        self.part_no_var.set("")
        self.part_name_var.set("")
        self.move_wh_var.set("全部")
        self.remove_wh_var.set("全部")
        self.created_by_var.set("")
        self.status_var.set("全部")
        self.remark_var.set("")
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
            return int(row.get('transferStatus')) in EDITABLE_STATUS
        except (TypeError, ValueError):
            return False

    @staticmethod
    def can_delete(row):
        try:
            return int(row.get('transferStatus')) in DELETABLE_STATUS
        except (TypeError, ValueError):
            return False

    # ================================================================ 删除
    def delete_row(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        if not self.can_delete(row):
            messagebox.showwarning("提示", "仅「待提交」状态的调拨申请可以删除")
            return
        if not messagebox.askyesno("删除", "确认删除调拨单 %s ?" % (row.get('transferNo') or '')):
            return
        threading.Thread(target=self._delete_thread, args=(row,), daemon=True).start()

    def _delete_thread(self, row):
        try:
            r = self.controller.session.post(URL_DELETE, headers=HEADERS,
                                             data=json.dumps(row, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 删除异常: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "删除失败: %s" % e))
            return
        if resp_ok(data):
            self.controller.after(0, lambda: messagebox.showinfo("成功", "删除成功"))
            self.controller.after(0, lambda: self.query(reset_page=False))
        else:
            msg = err_msg(data, "删除失败")
            self.controller.after(0, lambda: messagebox.showerror("删除失败", str(msg)))

    # ================================================================ 导出
    def export_excel(self):
        if not self._validate_search("导出"):
            return
        params = self.build_params()
        params.pop('pageNum', None)
        params.pop('pageSize', None)
        params['limit'] = 9999999
        path = filedialog.asksaveasfilename(
            title="导出调拨申请",
            initialfile="调拨申请_%s.xlsx" % datetime.now().strftime('%Y%m%d_%H%M'),
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
            print("[调拨申请] 导出异常: %s" % e)
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
            messagebox.showwarning("提示", "仅「待提交 / 审核驳回」状态可编辑")
            return
        self._open_edit_dialog(row=row)

    def _open_edit_dialog(self, row):
        is_edit = row is not None
        self._edit_meta = {
            'is_edit': is_edit,
            'id': row.get('id') if is_edit else None,
            'transferNo': row.get('transferNo') if is_edit else None,
            'transferType': row.get('transferType') if is_edit else None,
            'logisticsMode': row.get('logisticsMode') if is_edit else None,
            'transferStatus': row.get('transferStatus') if is_edit else None,
            'moveWarehouseId': row.get('moveWarehouseId') if is_edit else None,
            'moveWarehouseName': row.get('moveWarehouseName') if is_edit else None,
            'removeWarehouseId': row.get('removeWarehouseId') if is_edit else None,
            'removeWarehouseName': row.get('removeWarehouseName') if is_edit else None,
            'boxId': row.get('boxId') if is_edit else None,
            'remark': row.get('remark') if is_edit else None,
            'isWarehouseOutbound': (row.get('isWarehouseOutbound') if is_edit
                                    else IS_WAREHOUSE_OUTBOUND),
            'recordVersion': row.get('recordVersion') if is_edit else None,
        }
        self._edit_detail_rows = []
        self._edit_deleted = []

        win = tk.Toplevel(self)
        win.title(("编辑调拨信息" if is_edit else "新增调拨信息"))
        win.geometry("1280x680")
        self._edit_win = win
        self._build_edit_dialog(win)
        if is_edit:
            self._load_edit_detail(row.get('id'))

    def _build_edit_dialog(self, win):
        meta = self._edit_meta
        top = tk.LabelFrame(win, text="调拨信息", bg="#f0f0f0",
                            font=("微软雅黑", 10, "bold"))
        top.pack(fill=tk.X, padx=10, pady=(8, 4), ipadx=6, ipady=4)

        # 调出仓库（queryListForSelect）
        tk.Label(top, text="调出仓库:", bg="#f0f0f0").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.e_remove_wh = ttk.Combobox(top, values=list(self.remove_wh_map.keys()),
                                        state="readonly", width=16)
        if meta['is_edit']:
            self.e_remove_wh.config(state="disabled")
        self.e_remove_wh.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.e_remove_wh.bind("<<ComboboxSelected>>", lambda _e: self._on_remove_wh_change())

        # 调入仓库（queryListWithPermissions）
        tk.Label(top, text="调入仓库:", bg="#f0f0f0").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.e_move_wh = ttk.Combobox(top, values=list(self.move_wh_map.keys()),
                                      state="readonly", width=16)
        if meta['is_edit']:
            self.e_move_wh.config(state="disabled")
        self.e_move_wh.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # 调拨类型（4717）
        tk.Label(top, text="调拨类型:", bg="#f0f0f0").grid(row=0, column=4, sticky="e", padx=4, pady=4)
        type_map = self.dict_maps.get(DICT_TYPE) or DICT_FALLBACK[DICT_TYPE]
        self.e_type = ttk.Combobox(top, values=list(type_map.values()),
                                   state="readonly", width=14)
        self.e_type.grid(row=0, column=5, sticky="w", padx=4, pady=4)

        # 调拨单号（系统生成，只读）
        tk.Label(top, text="调拨单号:", bg="#f0f0f0").grid(row=0, column=6, sticky="e", padx=4, pady=4)
        self.e_transfer_no = ttk.Entry(top, width=22)
        self.e_transfer_no.insert(0, meta.get('transferNo') or '系统生成')
        self.e_transfer_no.config(state="readonly")
        self.e_transfer_no.grid(row=0, column=7, sticky="w", padx=4, pady=4)

        # 物流方式（4617）
        tk.Label(top, text="物流方式:", bg="#f0f0f0").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        logi_map = self.dict_maps.get(DICT_LOGISTICS) or DICT_FALLBACK[DICT_LOGISTICS]
        self.e_logistics = ttk.Combobox(top, values=list(logi_map.values()),
                                        state="readonly", width=16)
        self.e_logistics.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        # 包装方式（boxModelManage）
        tk.Label(top, text="包装方式:", bg="#f0f0f0").grid(row=1, column=2, sticky="e", padx=4, pady=4)
        self.e_box = ttk.Combobox(top, values=[b.get('box_name') or '' for b in self.box_list],
                                  state="readonly", width=16)
        self.e_box.grid(row=1, column=3, sticky="w", padx=4, pady=4)

        # 摘要
        tk.Label(top, text="摘要:", bg="#f0f0f0").grid(row=1, column=4, sticky="e", padx=4, pady=4)
        self.e_remark = ttk.Entry(top, width=34)
        self.e_remark.grid(row=1, column=5, columnspan=3, sticky="w", padx=4, pady=4)

        # 回填
        if meta['is_edit']:
            self.e_remove_wh.set(meta.get('removeWarehouseName') or '')
            self.e_move_wh.set(meta.get('moveWarehouseName') or '')
            self._set_combo_by_code(self.e_type, DICT_TYPE, meta.get('transferType'))
            self._set_combo_by_code(self.e_logistics, DICT_LOGISTICS, meta.get('logisticsMode'))
            box_name = ''
            for b in self.box_list:
                if b.get('id') == meta.get('boxId'):
                    box_name = b.get('box_name') or ''
            self.e_box.set(box_name)
            self.e_remark.insert(0, meta.get('remark') or '')

        # ---- 明细区 ----
        mid = tk.LabelFrame(win, text="调拨明细", bg="#f0f0f0",
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
        tk.Label(mbar, text="（申请数量必填且 ≥1；入库库位可后选）", bg="#f0f0f0",
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
        meta_status = meta.get('transferStatus')
        editable = (not meta['is_edit']) or meta_status in EDITABLE_STATUS
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
            tk.Label(foot, text="该单据当前状态不可编辑", bg="#f0f0f0",
                     fg="#f5222d").pack(side=tk.LEFT, padx=10)

    def _set_combo_by_code(self, combo, dict_type, code):
        if code is None:
            return
        label = self._label(dict_type, code)
        combo.set(label)

    def _on_remove_wh_change(self):
        """切换调出仓库 → 清空明细（对齐 Web changeWarehouseSelect）。"""
        self._edit_detail_rows = []
        self._render_edit_detail()

    # ------------------------------------------------------------ 明细载入
    def _load_edit_detail(self, transfer_id):
        threading.Thread(target=self._load_detail_thread, args=(transfer_id,), daemon=True).start()

    def _load_detail_thread(self, transfer_id):
        try:
            r = self.controller.session.get(URL_FIND_BY_ID, headers=HEADERS,
                                            params={'transferId': transfer_id})
            print("[调拨申请] %s" % r.url)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 明细加载失败: %s" % e)
            self.controller.after(0, lambda: messagebox.showerror("错误", "明细加载失败: %s" % e))
            return
        arr = data.get('data') or []
        rows = []
        for t in arr if isinstance(arr, list) else []:
            if not isinstance(t, dict):
                continue
            row = dict(t)
            # Web initPage：已有入库库位 → select_LOCATION_OPTIONS 2 字段
            if row.get('inboundLocationId'):
                row['select_LOCATION_OPTIONS'] = [{
                    'locationId': row.get('inboundLocationId'),
                    'locationNo': row.get('inboundLocation'),
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
                row.get('partCode') or '-',
                row.get('partName') or '-',
                row.get('brandName') or '-',
                self.fmt_num(row.get('availableQty')),
                self.fmt_num(row.get('transferQuantity')),
                row.get('remarks') or '-',
                self._loc_label(row),
            ))

    def _loc_label(self, row):
        loc_id = row.get('inboundLocationId')
        if not loc_id:
            return '-'
        opts = row.get('select_LOCATION_OPTIONS') or []
        for o in opts:
            if o.get('locationId') == loc_id:
                return o.get('locationNo') or row.get('inboundLocation') or str(loc_id)
        return row.get('inboundLocation') or str(loc_id)

    def _selected_detail_index(self):
        sel = self._edit_tree.selection() if self._edit_tree else ()
        if not sel:
            return None
        idx = self._edit_tree.index(sel[0])
        return idx if 0 <= idx < len(self._edit_detail_rows) else None

    # ------------------------------------------------------------ 明细增删改
    def _add_detail_row(self):
        remove_wh_id = self._current_remove_wh_id()
        if not remove_wh_id:
            messagebox.showwarning("提示", "请先选择调出仓库")
            return

        def on_pick(picked):
            existing = {(r.get('partCode'), r.get('brand'))
                        for r in self._edit_detail_rows}
            added = 0
            for p in picked:
                key = (p.get('partCode'), p.get('brand'))
                if key in existing:
                    messagebox.showwarning("提示", "%s 该配件已添加，请勿重复添加"
                                           % (p.get('partCode') or ''))
                    continue
                row = dict(p)
                # PC 便捷：默认申请数量 = 可调拨数量（可编辑，Web 端留空需手填）
                if row.get('transferQuantity') in (None, ''):
                    row['transferQuantity'] = row.get('availableQty')
                row.setdefault('removeWarehouseId', remove_wh_id)
                row['select_LOCATION_OPTIONS'] = row.get('select_LOCATION_OPTIONS') or []
                self._edit_detail_rows.append(row)
                existing.add(key)
                added += 1
            if added:
                self._render_edit_detail()

        ProductPickerDialog(self._edit_win, self.controller,
                            query_url=URL_QUERY_PART_TRANSFER_IN,
                            warehouse_id=remove_wh_id,
                            on_pick=on_pick,
                            title="选择产品（调出仓库）",
                            allow_multi=True)

    def _edit_detail_row(self):
        idx = self._selected_detail_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一行明细")
            return
        row = self._edit_detail_rows[idx]
        win = tk.Toplevel(self._edit_win)
        win.title("编辑明细 - %s" % (row.get('partCode') or ''))
        win.geometry("560x300")
        win.transient(self._edit_win)

        info = tk.LabelFrame(win, text="产品", bg="#f0f0f0")
        info.pack(fill=tk.X, padx=10, pady=8, ipadx=6, ipady=4)
        tk.Label(info, text=row.get('partName') or '-', bg="#f0f0f0",
                 wraplength=520, justify="left").pack(anchor="w", padx=4)
        tk.Label(info, text="编码: %s   品牌: %s   可调拨: %s"
                 % (row.get('partCode') or '-', row.get('brandName') or '-',
                    self.fmt_num(row.get('availableQty'))),
                 bg="#f0f0f0", fg="#666666").pack(anchor="w", padx=4)

        form = tk.Frame(win, bg="#f0f0f0")
        form.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(form, text="申请数量:", bg="#f0f0f0").grid(row=0, column=0, sticky="e", padx=4, pady=6)
        qty_var = tk.StringVar(value='' if row.get('transferQuantity') in (None, '')
                               else str(row.get('transferQuantity')))
        ttk.Entry(form, textvariable=qty_var, width=14).grid(row=0, column=1, sticky="w", padx=4)
        tk.Label(form, text="特别说明:", bg="#f0f0f0").grid(row=1, column=0, sticky="e", padx=4, pady=6)
        remark_var = tk.StringVar(value=row.get('remarks') or '')
        ttk.Entry(form, textvariable=remark_var, width=34).grid(row=1, column=1, sticky="w", padx=4)

        tk.Label(form, text="入库库位:", bg="#f0f0f0").grid(row=2, column=0, sticky="e", padx=4, pady=6)
        loc_var = tk.StringVar(value=self._loc_label(row) if row.get('inboundLocationId') else '')
        ttk.Entry(form, textvariable=loc_var, width=18, state="readonly").grid(row=2, column=1, sticky="w", padx=4)

        def pick_loc():
            move_wh_id = self._current_move_wh_id()
            if not move_wh_id:
                messagebox.showwarning("提示", "请先选择调入仓库")
                return

            def on_loc(loc):
                row['inboundLocationId'] = loc.get('locationId')
                row['inboundLocation'] = loc.get('locationNo')
                # 远端新选 → 存完整对象（6 字段）
                row['select_LOCATION_OPTIONS'] = [loc]
                loc_var.set(loc.get('locationNo') or '')

            LocationPickerDialog(win, self.controller, move_wh_id, on_loc,
                                 title="选择入库库位（调入仓库）")

        tk.Button(form, text="选择库位", command=pick_loc,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=8).grid(row=2, column=2, padx=6)

        def do_save():
            raw = qty_var.get().strip()
            try:
                qty = int(float(raw))
            except (TypeError, ValueError):
                messagebox.showwarning("提示", "申请数量请输入大于零的数字")
                return
            if qty < 1:
                messagebox.showwarning("提示", "申请数量请输入大于零的数字")
                return
            row['transferQuantity'] = qty
            row['remarks'] = remark_var.get().strip()
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
        if row.get('detailId'):
            self._edit_deleted.append(row)
        self._render_edit_detail()

    # ------------------------------------------------------------ 提交
    def _current_remove_wh_id(self):
        name = self.e_remove_wh.get()
        return self.remove_wh_map.get(name)

    def _current_move_wh_id(self):
        name = self.e_move_wh.get()
        return self.move_wh_map.get(name)

    def _build_payload(self, check_status):
        meta = self._edit_meta
        type_map = self.dict_maps.get(DICT_TYPE) or DICT_FALLBACK[DICT_TYPE]
        logi_map = self.dict_maps.get(DICT_LOGISTICS) or DICT_FALLBACK[DICT_LOGISTICS]
        transfer_type = self._rev_code(type_map, self.e_type.get())
        logistics = self._rev_code(logi_map, self.e_logistics.get())
        box_id = None
        for b in self.box_list:
            if b.get('box_name') == self.e_box.get():
                box_id = b.get('id')
                break
        # 包装方式基础数据异步加载，未命中时回退编辑态原值，避免误清空
        if box_id is None:
            box_id = meta.get('boxId')
        payload = {
            'id': meta.get('id'),
            'transferType': transfer_type,
            'logisticsMode': logistics,
            'moveWarehouseId': self._current_move_wh_id(),
            'removeWarehouseId': self._current_remove_wh_id(),
            'remark': self.e_remark.get().strip() or None,
            'checkStatus': check_status,
            'isWarehouseOutbound': meta.get('isWarehouseOutbound') or IS_WAREHOUSE_OUTBOUND,
            'detailDtoList': [dict(r) for r in self._edit_detail_rows],
            'detailDtoListDelete': [dict(r) for r in self._edit_deleted],
            'boxId': box_id,
            'recordVersion': meta.get('recordVersion'),
        }
        return payload

    @staticmethod
    def _rev_code(dict_map, label):
        for code, name in dict_map.items():
            if name == label:
                return code
        return label or None

    def _submit(self, check_status):
        # 校验（对齐 Web infoSave）
        if not self.e_type.get():
            messagebox.showwarning("提示", "请选择调拨类型")
            return
        remove_id = self._current_remove_wh_id()
        move_id = self._current_move_wh_id()
        if not remove_id:
            messagebox.showwarning("提示", "请选择调出仓库")
            return
        if not move_id:
            messagebox.showwarning("提示", "请选择调入仓库")
            return
        if str(remove_id) == str(move_id):
            messagebox.showwarning("提示", "调入仓库不能与调出仓库相同")
            return
        if not self._edit_detail_rows:
            messagebox.showwarning("提示", "请添加明细")
            return
        for i, row in enumerate(self._edit_detail_rows):
            q = row.get('transferQuantity')
            try:
                qv = int(float(q))
            except (TypeError, ValueError):
                qv = 0
            if qv < 1:
                messagebox.showwarning("提示", "第 %d 行申请数量不能为空且须大于零" % (i + 1))
                return
            row['transferQuantity'] = qv

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
        print("[调拨申请] %s payload: %s" % (action, json.dumps(payload, ensure_ascii=False)[:800]))
        try:
            r = self.controller.session.post(URL_SAVE, headers=HEADERS,
                                             data=json.dumps(payload, ensure_ascii=False))
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] %s 异常: %s" % (action, e))
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

    # ================================================================ 明细（只读）
    def open_detail(self):
        row = self.current_row()
        if not row:
            messagebox.showwarning("提示", "请先选择一行")
            return
        win = tk.Toplevel(self)
        win.title("调拨信息 - %s" % (row.get('transferNo') or ''))
        win.geometry("1100x600")
        self._detail_win = win

        head = tk.LabelFrame(win, text="调拨信息", bg="#f0f0f0",
                             font=("微软雅黑", 10, "bold"))
        head.pack(fill=tk.X, padx=10, pady=(8, 4), ipadx=6, ipady=4)
        items = [
            ("调拨单号", row.get('transferNo')), ("调拨类型", self.decode_type(row.get('transferType'))),
            ("调出仓库", row.get('removeWarehouseName')), ("调入仓库", row.get('moveWarehouseName')),
            ("物流方式", self.decode_logistics(row.get('logisticsMode'))),
            ("包装方式", row.get('boxName')), ("调拨状态", self.decode_status(row.get('transferStatus'))),
            ("发起人", row.get('createdByName')), ("审核人", row.get('auditBy')),
            ("摘要", row.get('remark')),
        ]
        for i, (k, v) in enumerate(items):
            tk.Label(head, text="%s:" % k, bg="#f0f0f0", fg="#666666").grid(
                row=i // 5, column=(i % 5) * 2, sticky="e", padx=4, pady=3)
            tk.Label(head, text=str(v if v not in (None, '') else '-'), bg="#f0f0f0").grid(
                row=i // 5, column=(i % 5) * 2 + 1, sticky="w", padx=4, pady=3)

        body = tk.Frame(win, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        tree = ttk.Treeview(body, columns=VIEW_COLUMNS, show="headings", height=14)
        for col, width in zip(VIEW_COLUMNS, VIEW_WIDTHS):
            tree.heading(col, text=col)
            anchor = "w" if col in ("产品名称", "CARG全码/产品编码", "特别说明") else "center"
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
                         args=(row.get('id'), tree), daemon=True).start()

    def _detail_thread(self, transfer_id, tree):
        try:
            r = self.controller.session.get(URL_FIND_BY_ID, headers=HEADERS,
                                            params={'transferId': transfer_id})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print("[调拨申请] 明细请求异常: %s" % e)
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
                d.get('partCode') or '-',
                d.get('partName') or '-',
                d.get('brandName') or '-',
                self.fmt_num(d.get('transferQuantity')),
                d.get('remarks') or '-',
                d.get('inboundLocation') or '-',
            ))

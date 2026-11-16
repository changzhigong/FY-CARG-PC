# -*- coding: utf-8 -*-
"""仓库理货 — 发运单管理

对齐三方真相源：
1) Web 端页面快照与 HAR：`Desktop\\发运单管理\\发运单管理.html`、
   `Desktop\\发运单管理\\xb.fy-carg.com.har`。HAR 内嵌完整前端 chunk
   （index-ac2688f1.js = WaybillQuery 查询页，shippingManagement-18ded398.js = API barrel，
   edit/detail/waybillPrint = 编辑、明细、打印）。
2) Web 字典权威源：`Desktop\\dicts.json`（/dicts 完整响应）。
3) 安卓端：fycarg-pda `src/views/ShipmentQuery.vue`、`DeliveryVehicle.vue`、
   `src/service/shipment.js`（发运单查询参数与字典映射）。

接口（HAR 实证）：
- 列表  GET  /dmscloud.part/warehouse/waybillManagement/waybillQuery
        参数 warehouseId / waybillStatus / deliveryStartDate / deliveryEndDate /
        limit / pageNum，另支持 Web search 的 billNo、orderNumber、waybillNo、
        deliveryNo、dealerCode、dealerName、dealer_name、outbound_type、
        waybillPersonnel、licenseNo、printStatus、printStartDate、printEndDate、
        part_code、part_name。
        响应 data = {total, pageSize, pageNum, rows, sumAmount}；
        **sumAmount 实测为 null**，但后端在 rows[0] 冗余了全量合计
        n1=总片数 / n2=总金额 / n3=总箱数（其余行均为 null）。
        Web getSummary() 直接取 rows[0].n* 填合计行 a[12]/a[13]/a[14]，
        本页同口径：优先取 rows[0].n*，无该字段时才退化为当前页本地累加。
        （注意：本地累加只能得到「当前页」小计，分页时与 Web 全量合计不等。）
- 仓库  GET  /dmscloud.part//warehouse/manage/queryListForSelect（Web 页面初始化用）
- 服务端导出 GET /dmscloud.part/warehouse/waybillManagement/waybillExport
        （Web 用 window.location.href 拼接 search 全键下载；本页改用本地 openpyxl 导出，
         与 PC 端 bill_query.py 范式一致，避免额外下载会话依赖）

关键业务规则（Web index-ac2688f1.js 实证，2026-11-14 二次对账修订）：
1. 至少输入一个查询条件：Web searchHandle() 的白名单只有 16 个键
   （waybillNo / deliveryNo / dealerCode / dealerName / dealer_name / warehouseId /
   waybillStatus / waybillPersonnel / licenseNo / printStatus / deliveryStartDate /
   deliveryEndDate / printStartDate / printEndDate / part_code / part_name）。
   **billNo、orderNumber 未被计入条件判断**（Web 源码如此），但仍随请求下发。
2. 日期校验是**条件化**的：仅当 waybillStatus 非空且 != 90471002（未发运）时，
   才要求发运起止都填、结束不早于开始、间隔 ≤ 93 天；打印日期不参与校验。
   默认状态 90471002 时整段跳过（HAR #38 首次查询即只带 waybillStatus=90471002、0 条）。
3. 发运状态下拉：Web `excludeCode="90471003,...,90471006"` + `hideBlank:!0,clearable:!1`
   → 实际只有「已发运 90471001」「未发运 90471002」两项，无「请选择」、不可清空，
   默认 90471002。HTML 快照的下拉 DOM 与表头均证实（「待发运/发运中/已作废」全文 0 处）。
   本页按此给 2 项，额外保留「全部」（桌面端便利，对应 HAR #42 的空状态查询），
   默认「全部」；**列表列的解码仍用字典全 6 项**，因为行 waybill_status 是细状态码
   （HAR #41 用 90471001「已发运」查出 4 行，其 waybill_status 均为 90471003「已签收」）。
4. 列表列按 Web 模板顺序，去掉 Web 的「操作」列（改为双击行查看明细）。

有意不实现的功能（证据不足，不擅自构造报文）：
- 「新增发运单」「发运」「销售单打印/预览」：**Web HTML 快照里这些按钮真实存在**
  （按钮组：查询/重置/收起/送货车辆/导出/销售单打印/销售单打印预览/新增发运单/发运），
  但本次 HAR 只采集了查询动作，无 saveWaybill / updateInfo / waybillDetaGroup 报文；
  安卓 ShipmentQuery.vue 也是 onPlaceholder 占位。无响应结构可对齐，故本页为只读查询页。
- 「车牌路线分配」：Web 送货车辆弹窗里有完整 DOM（地区下拉、Excel 导入、下载模板、
  跳过当天已存在的相同路线数据、将第一个路线应用到所有车牌、开始写入），
  HAR 无对应写请求 → 本页只做按车牌聚合导出，路线/退回数/破损数留空。
- Web 有分页控件（5/10/20/50/100/500 条每页、共 N 条），本页固定 limit=500 单页展示。
- 「明细」Web 走 getWaybillDetailList / waybillDetailsQuery，HAR 无对应请求与响应结构；
  本页双击行改为展示该行的完整原始字段 + 解码值，不伪造明细接口。
- 「送货车辆」Web 是页内弹窗（快照 10 列），安卓 DeliveryVehicle.vue 按车牌聚合并导出
  `{仓库}送货车辆.xlsx`；本页按该口径做本地聚合导出，路线/退回数/破损数留空可编辑。

字典（Desktop\\dicts.json 的 code_cn_desc，运行时由 FALLBACK_DICTS 兜底）：
- 9047 发运状态：90471001 已发运 / 90471002 未发运 / 90471003 已签收 /
  90471004 已入库 / 90471005 部分签收 / 90471006 部分入库
- 9048 打印状态：90481001 已打印 / 90481002 未打印
- 9037 出库类型：15 项（90371003 = 产品销售出库）
- 4617 物流方式：46171001 送货 / … / 46171005 快递
注意：安卓 service/shipment.js 的 WAYBILL_STATUS_MAP、PRINT_STATUS_MAP、
OUTBOUND_TYPE_MAP 与 Web 字典/页面快照不一致（如把 90471003 写成「已发运」、
90481002 写成「已打印」），本页一律以 Web dicts.json + HTML 快照为准。
"""

import json
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

from base_page import BasePage
from config_path import config_file_path

BASE_URL = 'https://xb.fy-carg.com'
URL_WAYBILL_QUERY = (
    BASE_URL + '/dmscloud.part/warehouse/waybillManagement/waybillQuery'
)
URL_WAYBILL_EXPORT = (   # 仅记录契约，本页不调用（见模块说明）
    BASE_URL + '/dmscloud.part/warehouse/waybillManagement/waybillExport'
)
URL_WAREHOUSE_LIST = (
    BASE_URL + '/dmscloud.part//warehouse/manage/queryListForSelect'
)

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'),
}

# 列表列（对齐 Web 模板顺序；去掉「操作」列，双击行查看明细）
COLUMNS = [
    '序号', '发运单号', '发货单号', '出库仓库', '出库类型', '客户代码', '客户名称',
    '收货地址', '车牌号', '物流方式', '物流公司名称', '箱数', '片数', '金额',
    '发运状态', '打印状态', '发运时间', '送货人', '联系方式', '物流单号',
]
COLUMN_WIDTHS = [
    50, 170, 170, 90, 130, 90, 170, 230, 90, 90, 120, 60, 60, 100,
    90, 80, 150, 90, 110, 120,
]
# 与 COLUMNS 一一对应（序号单独生成），值为 HAR 行的真实字段名
FIELD_KEYS = [
    'waybill_no', 'delivery_no', 'WAREHOUSE_NAME', 'outbound_type',
    'dealer_code', 'dealer_name', 'receive_address', 'license_no',
    'logistics_mode', 'logistics_provider_name', 'box_count', 'delivery_count',
    'delivery_amount', 'waybill_status', 'print_status', 'waybill_time',
    'waybill_personnel', 'contact_information', 'logistics_no',
]
# 需要字典解码的列：列下标 -> 字典组
DICT_COLUMNS = {4: '9037', 9: '4617', 14: '9047', 15: '9048'}

# Web 字典权威源 Desktop\dicts.json（离线兜底，避免无会话时列显示裸码）
FALLBACK_DICTS = {
    '9047': {
        90471001: '已发运', 90471002: '未发运', 90471003: '已签收',
        90471004: '已入库', 90471005: '部分签收', 90471006: '部分入库',
    },
    '9048': {90481001: '已打印', 90481002: '未打印'},
    '9037': {
        90371001: '普通件采购退货出库', 90371002: '直供件采购退货出库',
        90371003: '产品销售出库', 90371004: '直供件销售出库',
        90371005: '报废出库', 90371006: '内部领用出库',
        90371007: '委外加工出库', 90371008: 'Kit件出库',
        90371009: '总成件拆卸出库', 90371010: '刷机件出库',
        90371011: '盘亏出库', 90371012: '充电桩销售出库',
        90371013: '产品转换出库', 90371014: '调拨出库', 90371015: '绿通出库',
    },
    '4617': {
        46171001: '送货', 46171002: '物流代收', 46171003: '物流发货',
        46171004: '自提', 46171005: '快递',
    },
}

# 查询控件定义：(标签, Web search 键, 类型)，类型 input/date/select
FILTER_FIELDS = [
    ('发运单号:', 'waybillNo', 'input'),
    ('发货单号:', 'deliveryNo', 'input'),
    ('SO单号:', 'billNo', 'input'),
    ('订单号:', 'orderNumber', 'input'),
    # Web formList 第 5 项是「客户 → dealer_name」（只读、点开往来单位弹窗回填），
    # 第 6 项才是「客户名称 → dealerName」；Web 表单没有 dealerCode 控件
    # （该键只存在于 search 对象和条件白名单里，由弹窗内部回填）。
    ('客户:', 'dealer_name', 'input'),
    ('客户名称:', 'dealerName', 'input'),
    ('发运人员:', 'waybillPersonnel', 'input'),
    ('车牌号:', 'licenseNo', 'input'),
    ('CARG全码:', 'part_code', 'input'),
    ('产品名称:', 'part_name', 'input'),
]

# Web searchHandle() 判断「至少输入一个条件」时认的 16 个键。
# 注意 billNo / orderNumber 有表单控件、也会随请求下发，但**不参与**该判断（Web 源码如此）。
QUERY_CONDITION_KEYS = (
    'waybillNo', 'deliveryNo', 'dealerCode', 'dealerName', 'dealer_name',
    'warehouseId', 'waybillStatus', 'waybillPersonnel', 'licenseNo',
    'printStatus', 'deliveryStartDate', 'deliveryEndDate',
    'printStartDate', 'printEndDate', 'part_code', 'part_name',
)

# 送货车辆报表列（Web 发运单管理.html 的「送货车辆」弹窗表头）
VEHICLE_HEADERS = [
    '序号', '车牌号', '日期', '记录数', '片数', '金额',
    '送货人', '送货路线', '退回数', '破损数',
]


class WaybillManagePage(BasePage):
    """发运单管理（只读查询 / 导出 / 送货车辆报表）"""

    def __init__(self, parent, controller):
        self.controller = controller
        self.rows = []                # 当前查询结果原始行
        self.total = 0                # 后端返回的总条数（跨页，对齐 Web「共 N 条」）
        self.summary_source = 'local'  # backend=rows[0].n* 全量合计 / local=当前页累加
        self.row_index = {}           # tree iid -> 原始行
        self.dicts = {k: dict(v) for k, v in FALLBACK_DICTS.items()}
        self.warehouse_options = {}
        self.loading = False
        self.filter_vars = {}
        self.runtime_dicts_loaded = False
        super().__init__(parent, controller)
        self._load_warehouses()

    # ------------------------------------------------------------------ 工具
    def _log(self, *args):
        print('[发运单管理]', *args)

    def _after(self, fn, *args):
        """把 worker 线程结果切回 GUI 线程（controller.after 由主程序提供）"""
        try:
            self.controller.after(0, lambda: fn(*args))
        except Exception:
            # 测试桩可能没有事件循环，直接执行
            try:
                fn(*args)
            except Exception as e:
                self._log('after fallback error:', e)

    def decode(self, group, code):
        """字典码 -> 中文；未命中返回原始值（不吞掉未知码）"""
        if code in (None, ''):
            return ''
        table = self.dicts.get(group, {})
        try:
            key = int(code)
        except (TypeError, ValueError):
            key = code
        return str(table.get(key, code))

    def fmt_money(self, value):
        """千分位金额；Web toThousandFilterByNumber 对整数不补 .00。

        HTML 快照实证：1901.11 → "1,901.11"，1351.0 → "1,351"、2381.0 → "2,381"。
        """
        if value in (None, ''):
            return ''
        try:
            num = float(value)
        except (TypeError, ValueError):
            return str(value)
        if num == int(num):
            return '{:,}'.format(int(num))
        return '{:,.2f}'.format(num)

    def _num(self, value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _warehouse_map(self):
        """仓库名 -> 数字 ID。优先用 controller.options（登录后的仓库权限），
        否则回退 warehouse_config.json 的 WAREHOUSE_OPTIONS。"""
        opts = getattr(self.controller, 'options', None)
        if opts:
            return dict(opts)
        try:
            with open(config_file_path(), encoding='utf-8') as f:
                return dict(json.load(f).get('WAREHOUSE_OPTIONS', {}))
        except Exception:
            return {}

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.content_frame, padding=6)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        self.setup_filter_panel(outer)
        self.setup_action_bar(outer)
        self.setup_data_table(outer)
        self.setup_summary_bar(outer)

    def setup_filter_panel(self, parent):
        box = ttk.LabelFrame(parent, text='查询条件（Web 发运单管理）', padding=6)
        box.grid(row=0, column=0, sticky='ew', pady=(0, 4))

        # 第 1~2 行：文本条件（每行 5 个）
        for line in range(2):
            row = ttk.Frame(box)
            row.pack(fill=tk.X, pady=2)
            for label, key, kind in FILTER_FIELDS[line * 5:(line + 1) * 5]:
                ttk.Label(row, text=label).pack(side=tk.LEFT, padx=(4, 1))
                var = tk.StringVar()
                self.filter_vars[key] = var
                ttk.Entry(row, textvariable=var, width=15).pack(
                    side=tk.LEFT, padx=(0, 8))

        # 第 3 行：下拉 + 日期
        row3 = ttk.Frame(box)
        row3.pack(fill=tk.X, pady=2)

        self.warehouse_map = self._warehouse_map()
        self.warehouse_var = tk.StringVar(value='全部')
        ttk.Label(row3, text='出库仓库:').pack(side=tk.LEFT, padx=(4, 1))
        self.warehouse_cb = ttk.Combobox(
            row3, textvariable=self.warehouse_var, width=11, state='readonly',
            values=['全部'] + list(self.warehouse_map.keys()))
        self.warehouse_cb.pack(side=tk.LEFT, padx=(0, 8))

        self.outbound_type_var = tk.StringVar(value='全部')
        ttk.Label(row3, text='出库类型:').pack(side=tk.LEFT, padx=(4, 1))
        self.outbound_type_cb = ttk.Combobox(
            row3, textvariable=self.outbound_type_var, width=15, state='readonly',
            values=['全部'] + [self.decode('9037', c) for c in self.dicts['9037']])
        self.outbound_type_cb.pack(side=tk.LEFT, padx=(0, 8))

        self.status_var = tk.StringVar(value='全部')
        ttk.Label(row3, text='发运状态:').pack(side=tk.LEFT, padx=(4, 1))
        # Web excludeCode="90471003,90471004,90471005,90471006" 且 hideBlank/clearable 关闭，
        # 下拉实际只有 90471001 已发运 / 90471002 未发运 两项 + 默认 90471002。
        # 本页保留「全部」作桌面便利项（对应 HAR #42 的 waybillStatus= 空查询）。
        # 注意：列表列解码仍用 9047 全 6 项，行状态是细码，与查询用的粗码不同层级。
        self.status_cb = ttk.Combobox(
            row3, textvariable=self.status_var, width=10, state='readonly',
            values=['全部'] + [self.decode('9047', c)
                              for c in (90471001, 90471002)])
        self.status_cb.pack(side=tk.LEFT, padx=(0, 8))

        self.print_var = tk.StringVar(value='全部')
        ttk.Label(row3, text='打印状态:').pack(side=tk.LEFT, padx=(4, 1))
        self.print_cb = ttk.Combobox(
            row3, textvariable=self.print_var, width=9, state='readonly',
            values=['全部'] + [self.decode('9048', c) for c in self.dicts['9048']])
        self.print_cb.pack(side=tk.LEFT, padx=(0, 8))

        # 第 4 行：发运/打印起止日期（默认本月 1 号 ~ 今天，对齐 Web getdefDate）
        row4 = ttk.Frame(box)
        row4.pack(fill=tk.X, pady=2)
        today = datetime.now().date()
        first_day = today.replace(day=1)
        self.date_vars = {}
        for label, key, default in [
            ('发运开始:', 'deliveryStartDate', first_day),
            ('发运结束:', 'deliveryEndDate', today),
            ('打印开始:', 'printStartDate', ''),
            ('打印结束:', 'printEndDate', ''),
        ]:
            ttk.Label(row4, text=label).pack(side=tk.LEFT, padx=(4, 1))
            var = tk.StringVar(value=str(default) if default else '')
            self.date_vars[key] = var
            self.filter_vars[key] = var
            ttk.Entry(row4, textvariable=var, width=12).pack(
                side=tk.LEFT, padx=(0, 8))

    def setup_action_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.grid(row=1, column=0, sticky='ew', pady=(0, 4))

        self.query_btn = ttk.Button(bar, text='查询', command=self.query)
        self.query_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text='重置', command=self.reset_filters).pack(side=tk.LEFT, padx=3)
        self.export_btn = ttk.Button(bar, text='导出 Excel', command=self.export_excel)
        self.export_btn.pack(side=tk.LEFT, padx=3)
        self.vehicle_btn = ttk.Button(bar, text='送货车辆', command=self.export_vehicle_report)
        self.vehicle_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text='查看明细（双击行）', command=self.open_detail).pack(
            side=tk.LEFT, padx=3)

        self.hint_var = tk.StringVar(
            value='只读查询页：Web 有新增发运/发运/销售单打印按钮及车牌路线分配弹窗，'
                  '但本次 HAR 无写请求报文，故未接通')
        ttk.Label(bar, textvariable=self.hint_var, foreground='#888').pack(
            side=tk.LEFT, padx=12)

    def setup_data_table(self, parent):
        box = ttk.LabelFrame(parent, text='发运单列表', padding=4)
        box.grid(row=2, column=0, sticky='nsew', pady=(0, 4))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(box, columns=COLUMNS, show='headings', height=18)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')
        vsb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.bind('<Double-1>', lambda e: self.open_detail())

        # 斑马纹 + 金额列右对齐
        self.tree.tag_configure('odd', background='#F5F8FC')

    def setup_summary_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.grid(row=3, column=0, sticky='ew')
        self.summary_var = tk.StringVar(
            value='共 0 条  |  合计箱数 0  |  合计片数 0  |  合计金额 ¥0')
        ttk.Label(bar, textvariable=self.summary_var,
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------ 字典/仓库
    def set_runtime_dicts(self, dict_map):
        """可选：把会话里拉到的 /dicts 结果合并进来（离线时用 FALLBACK_DICTS）"""
        if not isinstance(dict_map, dict):
            return
        groups = dict_map.get('dict') or dict_map
        for group, items in (groups or {}).items():
            if not isinstance(items, list):
                continue
            table = self.dicts.setdefault(str(group), {})
            for item in items:
                try:
                    table[int(item.get('code_id'))] = item.get('code_cn_desc')
                except (TypeError, ValueError, AttributeError):
                    continue

    def _load_warehouses(self):
        """Web 页面 mounted 会拉 queryListForSelect；PC 已由 controller.options 提供同一映射，
        这里不额外发请求（HAR 中该响应为仓库列表，与 options 等价）。"""
        self.warehouse_options = self._warehouse_map()

    # ------------------------------------------------------------------ 查询
    def _code_of(self, group, label):
        """中文标签 -> 字典码"""
        if label in ('全部', '', None):
            return ''
        for code, name in self.dicts.get(group, {}).items():
            if name == label:
                return str(code)
        return str(label)

    def build_query_params(self):
        """构造 waybillQuery 的 GET 参数。

        只下发非空条件（HAR 实证的空串键可省略），固定 limit=500 / pageNum=1
        与安卓 service/shipment.js 的默认值一致。
        """
        params = {}
        for key, var in self.filter_vars.items():
            value = (var.get() or '').strip()
            if value:
                params[key] = value

        warehouse = self.warehouse_var.get()
        if warehouse and warehouse != '全部':
            params['warehouseId'] = self.warehouse_map.get(warehouse, '')
        code = self._code_of('9037', self.outbound_type_var.get())
        if code:
            params['outbound_type'] = code
        code = self._code_of('9047', self.status_var.get())
        if code:
            params['waybillStatus'] = code
        code = self._code_of('9048', self.print_var.get())
        if code:
            params['printStatus'] = code

        params['limit'] = 500
        params['pageNum'] = 1
        return params

    def validate_query(self, params):
        """复刻 Web searchHandle() 的校验顺序与提示文案。

        1) 「至少一个条件」只认 QUERY_CONDITION_KEYS 这 16 个键；
        2) 日期校验是条件化的：仅当 waybillStatus 非空且 != 90471002（未发运）时触发，
           且只校验发运起止，打印日期不参与（Web 源码：整段 if 包在状态判断里）。
        """
        if not any(str(params.get(k) or '').strip()
                   for k in QUERY_CONDITION_KEYS):
            return '至少输入一个条件查询'

        status = str(params.get('waybillStatus') or '').strip()
        if not status or status == '90471002':
            return None                      # 默认「未发运」跳过整段日期校验

        begin = str(params.get('deliveryStartDate') or '').strip()
        end = str(params.get('deliveryEndDate') or '').strip()
        if not begin:
            return '请选择发运开始时间'
        if not end:
            return '请选择发运结束时间'
        try:
            d1 = datetime.strptime(begin, '%Y-%m-%d').date()
            d2 = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return '日期格式应为 yyyy-mm-dd'   # PC 附加：文本框容错（Web 由日期控件保证）
        if d2 < d1:
            return '发运结束时间不能小于发运开始时间'
        if (d2 - d1).days > 93:
            return '查询时间间隔不能超过93天'
        return None

    def query(self):
        if self.loading:
            return
        params = self.build_query_params()
        error = self.validate_query(params)
        if error:
            messagebox.showwarning('提示', error)
            return None
        self.loading = True
        self._set_busy(True)
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()
        return params

    def _set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in (self.query_btn, self.export_btn, self.vehicle_btn):
            try:
                btn.configure(state=state)
            except Exception:
                pass

    def _query_thread(self, params):
        try:
            response = self.controller.session.get(
                URL_WAYBILL_QUERY, params=params, headers=HEADERS, timeout=30)
            payload = json.loads(response.text) if getattr(response, 'text', None) else {}
            data = payload.get('data') or {}
            rows = data.get('rows') or data.get('dataList') or data.get('records') or []
            total = data.get('total', len(rows))
            self._after(self._render_rows, rows, total)
        except Exception as e:
            self._log('查询失败:', e)
            self._after(self._on_query_error, str(e))

    def _on_query_error(self, message):
        self.loading = False
        self._set_busy(False)
        messagebox.showerror('错误', '查询失败: %s' % message)

    def row_values(self, index, row):
        """把原始行转成表格显示值（按 Web 列顺序 + 字典解码）"""
        values = []
        for col_idx, key in enumerate(FIELD_KEYS, start=1):
            raw = row.get(key, '')
            if col_idx in DICT_COLUMNS:
                value = self.decode(DICT_COLUMNS[col_idx], raw)
            elif key == 'delivery_amount':
                value = self.fmt_money(raw)
            elif raw is None:
                value = ''
            else:
                value = str(raw)
            values.append(value)
        return [str(index)] + values

    def _render_rows(self, rows, total=None):
        self.rows = list(rows or [])
        self.total = total if total is not None else len(self.rows)
        self.row_index.clear()
        try:
            for iid in self.tree.get_children():
                self.tree.delete(iid)
        except Exception:
            pass
        for i, row in enumerate(self.rows, 1):
            iid = str(i)
            self.tree.insert('', tk.END, iid=iid, values=self.row_values(i, row),
                             tags=('odd',) if i % 2 == 0 else ())
            self.row_index[iid] = row
        self.update_summary()
        self.loading = False
        self._set_busy(False)

    def update_summary(self):
        """合计对齐 Web getSummary()：a[12]=n3 箱 / a[13]=n1 片 / a[14]=n2 金额。

        HAR 实证：sumAmount 为 null，但后端只在 rows[0] 冗余了**全量**合计
        （n1=27 / n2=7195.11 / n3=4，其余行全 null），Web 直接取它填合计行。
        优先用该值（分页时正确）；缺失时才退化为当前页本地累加。
        """
        first = self.rows[0] if self.rows else {}
        if first.get('n1') is not None or first.get('n2') is not None \
                or first.get('n3') is not None:
            self.summary_source = 'backend'
            boxes = self._num(first.get('n3'))
            qty = self._num(first.get('n1'))
            amount = self._num(first.get('n2'))
        else:
            self.summary_source = 'local'
            boxes = sum(self._num(r.get('box_count')) for r in self.rows)
            qty = sum(self._num(r.get('delivery_count')) for r in self.rows)
            amount = sum(self._num(r.get('delivery_amount')) for r in self.rows)
        count = self.total if self.total else len(self.rows)
        self.summary_var.set(
            '共 %d 条  |  合计箱数 %g  |  合计片数 %g  |  合计金额 ¥%s' % (
                count, boxes, qty, self.fmt_money(amount)))

    def reset_filters(self):
        for var in self.filter_vars.values():
            var.set('')
        self.warehouse_var.set('全部')
        self.outbound_type_var.set('全部')
        self.status_var.set('全部')
        self.print_var.set('全部')
        today = datetime.now().date()
        self.filter_vars['deliveryStartDate'].set(str(today.replace(day=1)))
        self.filter_vars['deliveryEndDate'].set(str(today))

    # ------------------------------------------------------------------ 明细
    def _selected_row(self):
        try:
            sel = self.tree.selection()
            if not sel:
                return None
            return self.row_index.get(str(sel[0]))
        except Exception:
            return None

    def open_detail(self):
        row = self._selected_row()
        if row is None:
            messagebox.showinfo('提示', '请先双击/选中一行发运单')
            return None
        win = tk.Toplevel(self)
        win.title('发运单明细 — %s' % (row.get('waybill_no') or ''))
        win.geometry('720x520')
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text='Web 明细接口 getWaybillDetailList 无 HAR 报文，此处展示本行完整字段（只读）',
                  foreground='#888').pack(anchor=tk.W, pady=(0, 6))
        cols = ('字段', '原始值', '显示值')
        tree = ttk.Treeview(frame, columns=cols, show='headings', height=20)
        for c, w in zip(cols, (220, 250, 220)):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor='w')
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        key_to_group = {'outbound_type': '9037', 'logistics_mode': '4617',
                        'waybill_status': '9047', 'print_status': '9048'}
        for key in sorted(row.keys()):
            raw = row.get(key)
            shown = (self.decode(key_to_group[key], raw)
                     if key in key_to_group else
                     self.fmt_money(raw) if key == 'delivery_amount' else
                     '' if raw is None else str(raw))
            tree.insert('', tk.END, values=(key, '' if raw is None else str(raw), shown))
        return win

    # ------------------------------------------------------------------ 导出
    def _write_workbook(self, headers, rows, default_name, title):
        """openpyxl 导出（对齐 bill_query.py 的导出范式）"""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        path = filedialog.asksaveasfilename(
            title=title, defaultextension='.xlsx', initialfile=default_name,
            filetypes=[('Excel 文件', '*.xlsx'), ('所有文件', '*.*')])
        if not path:
            return None
        wb = Workbook()
        ws = wb.active
        ws.title = '数据'
        ws.freeze_panes = 'A2'
        ws.append(headers)
        for idx, _ in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(idx)].width = 18
        for cell in ws[1]:
            cell.font = Font(bold=True, size=11, color='FFFFFFFF')
            cell.fill = PatternFill('solid', fgColor='FF409EFF')
            cell.alignment = Alignment(vertical='center', horizontal='center')
        for row in rows:
            ws.append(row)
        wb.save(path)
        return path

    def export_excel(self):
        if not self.rows:
            messagebox.showinfo('提示', '请先查询出数据再导出')
            return None
        data = [self.row_values(i, r) for i, r in enumerate(self.rows, 1)]
        warehouse = self.warehouse_var.get()
        name = '%s发运单%s.xlsx' % (
            '' if warehouse == '全部' else warehouse,
            datetime.now().strftime('%Y%m%d'))
        path = self._write_workbook(COLUMNS, data, name, '导出发运单 Excel')
        if path:
            messagebox.showinfo('完成', '已导出: %s' % path)
        return path

    def group_by_vehicle(self, rows=None):
        """按车牌号聚合送货车辆报表（对齐安卓 DeliveryVehicle.vue 的 groupWaybillByPlate）"""
        rows = self.rows if rows is None else rows
        grouped = {}
        for row in rows:
            plate = str(row.get('license_no') or '').strip()
            if not plate:
                continue
            day = str(row.get('waybill_time') or '')[:10]
            item = grouped.setdefault(plate, {
                'plate': plate, 'date': day, 'count': 0, 'qty': 0.0,
                'amount': 0.0, 'person': str(row.get('waybill_personnel') or ''),
            })
            item['count'] += 1
            item['qty'] += self._num(row.get('delivery_count'))
            item['amount'] += self._num(row.get('delivery_amount'))
            if day and (not item['date'] or day < item['date']):
                item['date'] = day
            if not item['person']:
                item['person'] = str(row.get('waybill_personnel') or '')
        result = []
        for i, item in enumerate(sorted(grouped.values(), key=lambda x: x['plate']), 1):
            result.append([
                i, item['plate'], item['date'], item['count'],
                item['qty'], self.fmt_money(item['amount']),
                item['person'], '', '', '',
            ])
        return result

    def export_vehicle_report(self):
        if not self.rows:
            messagebox.showinfo('提示', '请先查询出数据再生成送货车辆报表')
            return None
        data = self.group_by_vehicle()
        if not data:
            messagebox.showinfo('提示', '无有效送货车辆数据（车牌号为空已过滤）')
            return None
        warehouse = self.warehouse_var.get()
        name = '%s送货车辆.xlsx' % ('' if warehouse == '全部' else warehouse)
        path = self._write_workbook(VEHICLE_HEADERS, data, name, '导出送货车辆报表')
        if path:
            messagebox.showinfo('完成', '已导出: %s' % path)
        return path

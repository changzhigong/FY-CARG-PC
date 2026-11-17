# -*- coding: utf-8 -*-
"""仓库理货 — 送货车辆（独立页，完整对齐 app 端 DeliveryVehicle.vue）

真相源（三方一致，2026-11-17 核实）：
1) 安卓端 fycarg-pda `src/views/DeliveryVehicle.vue`、`src/utils/deliveryReport.js`、
   `src/config/deliveryRoutes.js`、`src/config/warehouses.js`。
2) 浏览器扩展 report-extension `content.js`（生效版，非 model.js）：
   - 唯一后端接口 GET /dmscloud.part/warehouse/waybillManagement/waybillQuery；
   - 路线/地区/模板/写入全部本地逻辑，**无写库接口**（apiBaseUrl 的
     transportRoute/queryList 在 content.js:889-925 被整段注释）。
3) 本 PC 端 waybill_manage.py 的会话/HEADERS 范式（同接口，已按 Web HAR 对齐）。

功能（与 app 端等价）：
- 查询条件：仓库（warehouse_config.json / controller.options）+ 发运状态
  （全部/已发运/未发运，默认全部=不过滤）+ 发运起止日期（默认今天，必填、结束≥开始）。
- 独立分页拉取 waybillQuery（pageSize=200 循环到 total，对齐扩展 content.js:
  524-585；app 用 limit=2000 单页，分页更稳且覆盖 >2000 条场景）。
- 聚合：按【车牌号 + 发运日期】二维分组，过滤空车牌，片数/金额累加，司机取首个非空；
  车牌取 license_no / license_no1 / license_no2，日期取 waybill_time / delivery_time
  前 10 位（deliveryReport.js:119-188）。
- 线路：按仓库地区筛候选，用「经销商 + 收货地址」子串匹配自动预填，可手选覆盖
  （deliveryRoutes.js:74-82、DeliveryVehicle.vue:151-157）。
- 退回数/破损数：接口无此字段，默认 0，可编辑（deliveryReport.js:140、:96-97）。
- 导出：openpyxl 复刻 ExcelJS 逻辑——每个车牌一个 sheet、追加写入（不覆盖）、
  序号按 sheet 内最大值续接、同「日期+线路+片数+金额」跳过、金额格式 #,##0.00、
  表头蓝底白字加粗居中、数据行居中细边框、冻结首行；文件名 {仓库短名}送货车辆.xlsx。

PC 与 app 的唯一差异：app 用 SAF 系统授权绕开安卓分区存储；PC 直接普通文件读写，
无分区存储限制，文件选择用 filedialog。其余逻辑 1:1 对齐。
"""

import json
import os
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from base_page import BasePage
from config_path import config_file_path, app_dir
from delivery_routes import (
    get_route_area, resolve_route_name, route_options, warehouse_short_name,
)

BASE_URL = 'https://xb.fy-carg.com'
URL_WAYBILL_QUERY = (
    BASE_URL + '/dmscloud.part/warehouse/waybillManagement/waybillQuery'
)

# 与 waybill_manage.py 完全一致（同接口，Web HAR 对齐，靠 Cookie 会话鉴权）
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'),
}

PAGE_SIZE = 200  # content.js:531 用 200；循环分页覆盖全量

# 发运状态下拉：Web excludeCode 后仅「已发运/未发运」两项 + app 默认空=不过滤
STATUS_OPTIONS = [
    ('全部', ''),
    ('已发运', '90471001'),
    ('未发运', '90471002'),
]

# 预览/报表列（app deliveryReport.js:35-44 REPORT_COLUMNS，8 列 + 序号）
REPORT_HEADERS = [
    '序号', '出发日期', '线路', '送货片数', '总金额', '司机', '返程退货数', '破损数',
]
# 预览表列 = 序号 + 8 列（与 DeliveryVehicle.vue:74-84 一致）
PREVIEW_COLUMNS = ['序号', '车牌号', '出发日期', '线路', '送货片数',
                   '总金额', '司机', '返程退货数', '破损数']
PREVIEW_WIDTHS = [45, 120, 110, 160, 90, 100, 90, 95, 80]

# Excel 报表样式（app deliveryReport.js）
HEADER_FILL = 'FF409EFF'   # app applyHeaderStyle fgColor FFFFFFFF + 409EFF 底
REPORT_COLUMN_WIDTHS = [6, 14, 16, 12, 14, 12, 12, 10]
AMOUNT_FORMAT = '#,##0.00'


# ---------------------------------------------------------------------- 纯逻辑

def _num(value):
    """宽松数值转换，失败取 0（对齐 JS Number(x) || 0）。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _first(*values):
    """取第一个非空字符串（对齐 JS a || b || c）。"""
    for v in values:
        if v not in (None, ''):
            return v
    return ''


def date_part(dt):
    """日期时间串取 yyyy-mm-dd（对齐 deliveryReport.js:108-111）。"""
    if not dt:
        return ''
    return str(dt)[:10]


def group_by_plate_and_date(rows, warehouse_name):
    """按【车牌号 + 发运日期】聚合，返回可编辑预览行列表。

    对齐 app deliveryReport.js:119-188 groupWaybillByPlate：
    - 车牌取 license_no / license_no1 / license_no2，空车牌过滤
    - 日期取 waybill_time / delivery_time 前 10 位
    - 片数/金额累加，司机取首个非空 waybill_personnel
    - 线路用「经销商+收货地址」子串匹配，命中多条取第一条
    - 退回数/破损数初始化 0（接口无字段）
    - 排序：日期升序 → 车牌升序
    """
    area = get_route_area(warehouse_name)
    grouped = {}
    for row in rows or []:
        plate = str(_first(row.get('license_no'), row.get('license_no1'),
                           row.get('license_no2'))).strip()
        if not plate:
            continue
        day = date_part(_first(row.get('waybill_time'), row.get('delivery_time')))
        key = (plate, day)
        item = grouped.get(key)
        if item is None:
            item = {
                'plateNumber': plate, 'date': day, 'quantity': 0.0, 'amount': 0.0,
                'deliverer': '', 'routes': [], 'returnQty': 0, 'brokenQty': 0,
            }
            grouped[key] = item
        item['quantity'] += _num(row.get('delivery_count'))
        item['amount'] += _num(row.get('delivery_amount'))
        if not item['deliverer']:
            person = _first(row.get('waybill_personnel'))
            if person:
                item['deliverer'] = str(person)

        dealer = str(_first(row.get('dealer_name'), row.get('dealerName'),
                            row.get('customer_name'), row.get('customerName')))
        address = str(_first(row.get('receive_address'), row.get('receiveAddress'),
                             row.get('receiver_address'), row.get('delivery_address'),
                             row.get('address')))
        route = resolve_route_name(area, (dealer + ' ' + address).strip())
        if route and route not in item['routes']:
            item['routes'].append(route)

    result = []
    for key in sorted(grouped.keys(), key=lambda k: (k[1], k[0])):
        item = grouped[key]
        routes = item['routes']
        result.append({
            'plateNumber': item['plateNumber'],
            'date': item['date'],
            'quantity': item['quantity'],
            'amount': item['amount'],
            'deliverer': item['deliverer'],
            'route': routes[0] if routes else '',
            'returnQty': item['returnQty'],
            'brokenQty': item['brokenQty'],
        })
    return result


def safe_sheet_name(name):
    """合法化工作表名：≤31 字符、替换 :\\/?*[]（deliveryReport.js:280-283）。"""
    import re
    cleaned = re.sub(r'[:\\/?*\[\]]', '_', str(name or '')).strip()
    return (cleaned or '未知车牌')[:31]


def report_file_name(warehouse_name):
    """{仓库短名}送货车辆.xlsx（如 商丘送货车辆.xlsx）。"""
    short = warehouse_short_name(warehouse_name) or '未知仓库'
    return '%s送货车辆.xlsx' % short


def _style_sheet_header(ws):
    """仅表头样式（app applyHeaderStyle：蓝底白字加粗居中 + 细边框）。"""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, bottom=thin, right=thin)
    for idx, _ in enumerate(REPORT_HEADERS, 1):
        c = ws.cell(row=1, column=idx)
        c.font = Font(bold=True, size=11, color='FFFFFFFF')
        c.fill = PatternFill('solid', fgColor=HEADER_FILL)
        c.alignment = Alignment(vertical='center', horizontal='center', wrap_text=True)
        c.border = border
    ws.row_dimensions[1].height = 24


def _new_sheet(wb, plate):
    ws = wb.create_sheet(title=safe_sheet_name(plate))
    ws.append(REPORT_HEADERS)
    ws.freeze_panes = 'A2'
    for idx, width in enumerate(REPORT_COLUMN_WIDTHS, 1):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(idx)].width = width
    _style_sheet_header(ws)
    return ws


def _max_serial(ws):
    """当前 sheet 已有最大序号（从 A 列数值取 max）。"""
    max_sn = 0
    for r in range(2, ws.max_row + 1):
        v = ws.cell(row=r, column=1).value
        if isinstance(v, (int, float)) and v > max_sn:
            max_sn = int(v)
    return max_sn


def _row_exists(ws, g):
    """同 sheet 内是否已存在 日期+线路+片数+金额 四元组相同行（跳过重复）。"""
    target = (g['date'], g.get('route') or '',
              round(_num(g['quantity']), 6), round(_num(g['amount']), 6))
    for r in range(2, ws.max_row + 1):
        cur = (ws.cell(row=r, column=2).value or '',
               ws.cell(row=r, column=3).value or '',
               round(_num(ws.cell(row=r, column=4).value), 6),
               round(_num(ws.cell(row=r, column=5).value), 6))
        if cur == target:
            return True
    return False


def _append_row(ws, sn, g):
    """追加一行数据（样式对齐 app addDataRow：金额格式 + 居中细边框）。"""
    from openpyxl.styles import Alignment, Border, Side
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, bottom=thin, right=thin)
    ws.append([
        sn, g['date'], g.get('route') or '',
        _num(g['quantity']), _num(g['amount']), g.get('deliverer') or '',
        int(_num(g.get('returnQty'))) if g.get('returnQty') not in (None, '') else 0,
        int(_num(g.get('brokenQty'))) if g.get('brokenQty') not in (None, '') else 0,
    ])
    r = ws.max_row
    ws.cell(row=r, column=5).number_format = AMOUNT_FORMAT
    for c in range(1, len(REPORT_HEADERS) + 1):
        cell = ws.cell(row=r, column=c)
        cell.border = border
        cell.alignment = Alignment(vertical='center', horizontal='center')


def build_report_workbook(grouped, out_path, existing_path=None):
    """构建/追加送货车辆工作簿（openpyxl 复刻 app buildDeliveryWorkbookBase64）。

    - 每个车牌一个 sheet（名=车牌），不合并单表
    - 已有同名文件：读取后各 sheet 末尾追加，序号续接，重复行跳过
    - 返回 (out_path, appended_count, skipped_count)
    """
    from openpyxl import Workbook, load_workbook

    wb = None
    if existing_path and os.path.exists(existing_path):
        try:
            wb = load_workbook(existing_path)
        except Exception:
            wb = None
    if wb is None:
        wb = Workbook()
        # 去掉默认空 sheet
        for name in list(wb.sheetnames):
            if wb.sheetnames.index(name) == 0 and wb[name].max_row == 1 \
                    and wb[name].max_column == 1 and wb[name]['A1'].value is None:
                wb.remove(wb[name])
    wb.properties.creator = 'FY-CARG-PC'

    by_plate = {}
    for g in grouped:
        by_plate.setdefault(g['plateNumber'], []).append(g)

    appended = skipped = 0
    for plate, items in by_plate.items():
        name = safe_sheet_name(plate)
        if name in wb.sheetnames:
            ws = wb[name]
            is_new = False
            _style_sheet_header(ws)
        else:
            ws = _new_sheet(wb, plate)
            is_new = True
        sn = _max_serial(ws)
        for g in sorted(items, key=lambda x: x['date']):
            if not is_new and _row_exists(ws, g):
                skipped += 1
                continue
            sn += 1
            _append_row(ws, sn, g)
            appended += 1

    parent = os.path.dirname(out_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    wb.save(out_path)
    return out_path, appended, skipped


# ---------------------------------------------------------------------- 页面

class DeliveryVehiclePage(BasePage):
    """送货车辆：独立查询 + 车牌×日期聚合 + 可编辑预览 + 分 sheet 追加导出。"""

    def __init__(self, parent, controller):
        self.controller = controller
        self.grouped = []          # 可编辑预览行（dict 列表）
        self.raw_count = 0
        self.loading = False
        self.writing = False
        self.warehouse_map = {}    # 仓库名 -> 数字 ID
        self.warehouse_name = ''
        self.route_opts = []
        self.last_file = ''
        super().__init__(parent, controller)
        self._load_warehouses()

    # ---------- 工具 ----------
    def _log(self, *args):
        print('[送货车辆]', *args)

    def _after(self, fn, *args):
        try:
            self.controller.after(0, lambda: fn(*args))
        except Exception:
            try:
                fn(*args)
            except Exception as e:
                self._log('after fallback error:', e)

    def _load_warehouses(self):
        opts = getattr(self.controller, 'options', None)
        if opts:
            self.warehouse_map = dict(opts)
        else:
            try:
                with open(config_file_path(), encoding='utf-8') as f:
                    self.warehouse_map = dict(
                        json.load(f).get('WAREHOUSE_OPTIONS', {}))
            except Exception as e:
                self._log('加载仓库配置失败:', e)
                self.warehouse_map = {}

    def _set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in (self.query_btn, self.write_btn, self.reselect_btn):
            try:
                btn.configure(state=state)
            except Exception:
                pass

    # ---------- 界面 ----------
    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.content_frame, padding=6)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        self._build_filter(outer, 0)
        self._build_tip(outer, 1)
        self._build_actions(outer, 2)
        self._build_preview(outer, 3)
        self._build_status(outer, 4)

    def _build_filter(self, outer, row):
        box = ttk.LabelFrame(outer, text='查询条件', padding=6)
        box.grid(row=row, column=0, sticky='ew', pady=(0, 4))
        line = ttk.Frame(box)
        line.pack(fill=tk.X, pady=2)

        ttk.Label(line, text='出库仓库:').pack(side=tk.LEFT, padx=(4, 1))
        self.warehouse_var = tk.StringVar()
        names = list(self.warehouse_map.keys())
        self.warehouse_var.set(names[0] if names else '')
        self.warehouse_cb = ttk.Combobox(
            line, textvariable=self.warehouse_var, width=12, state='readonly',
            values=names)
        self.warehouse_cb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(line, text='发运状态:').pack(side=tk.LEFT, padx=(4, 1))
        self.status_var = tk.StringVar(value='全部')
        status_cb = ttk.Combobox(
            line, textvariable=self.status_var, width=9, state='readonly',
            values=[label for label, _code in STATUS_OPTIONS])
        status_cb.pack(side=tk.LEFT, padx=(0, 10))

        today = str(datetime.now().date())
        ttk.Label(line, text='发运开始:').pack(side=tk.LEFT, padx=(4, 1))
        self.start_var = tk.StringVar(value=today)
        ttk.Entry(line, textvariable=self.start_var, width=12).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Label(line, text='发运结束:').pack(side=tk.LEFT, padx=(4, 1))
        self.end_var = tk.StringVar(value=today)
        ttk.Entry(line, textvariable=self.end_var, width=12).pack(side=tk.LEFT)

    def _build_tip(self, outer, row):
        tip = ('按「车牌号 + 发运日期」汇总片数/金额，每个车牌单独一个 sheet；'
               '双击预览行可编辑 线路/片数/金额/退回数/破损数。'
               '导出为追加写入（同 日期+线路+片数+金额 的行跳过），文件名 {仓库}送货车辆.xlsx。')
        ttk.Label(outer, text=tip, foreground='#409eff', wraplength=900,
                  justify='left').grid(row=row, column=0, sticky='w', pady=(0, 2))

    def _build_actions(self, outer, row):
        bar = ttk.Frame(outer)
        bar.grid(row=row, column=0, sticky='ew', pady=(0, 4))
        self.query_btn = ttk.Button(bar, text='查询生成', command=self.query)
        self.query_btn.pack(side=tk.LEFT, padx=3)
        self.write_btn = ttk.Button(bar, text='追加写入 Excel', command=self.write_report)
        self.write_btn.pack(side=tk.LEFT, padx=3)
        self.reselect_btn = ttk.Button(bar, text='清除文件路径', command=self.clear_file)
        self.reselect_btn.pack(side=tk.LEFT, padx=3)
        self.file_var = tk.StringVar(value='目标文件：{仓库}送货车辆.xlsx（写入时可选）')
        ttk.Label(bar, textvariable=self.file_var, foreground='#888').pack(
            side=tk.LEFT, padx=10)

    def _build_preview(self, outer, row):
        box = ttk.LabelFrame(outer, text='送货车辆预览（双击行编辑）', padding=4)
        box.grid(row=row, column=0, sticky='nsew', pady=(0, 4))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(box, columns=PREVIEW_COLUMNS, show='headings', height=14)
        for col, width in zip(PREVIEW_COLUMNS, PREVIEW_WIDTHS):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')
        vsb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.bind('<Double-1>', self._on_double_click)
        self.row_ids = []

    def _build_status(self, outer, row):
        self.status_text = tk.StringVar(value='')
        ttk.Label(outer, textvariable=self.status_text, foreground='#67c23a').grid(
            row=row, column=0, sticky='w')

    # ---------- 查询 ----------
    def query(self):
        if self.loading:
            return None
        warehouse = self.warehouse_var.get()
        if not warehouse or warehouse not in self.warehouse_map:
            messagebox.showwarning('提示', '请选择出库仓库')
            return None
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        if not start or not end:
            messagebox.showwarning('提示', '请选择发运起止日期')
            return None
        if end < start:
            messagebox.showwarning('提示', '结束日期不能早于开始日期')
            return None
        status_code = dict(STATUS_OPTIONS).get(self.status_var.get(), '')
        params = {
            'warehouseId': self.warehouse_map[warehouse],
            'waybillStatus': status_code,
            'deliveryStartDate': start,
            'deliveryEndDate': end,
        }
        self.loading = True
        self._set_busy(True)
        self.status_text.set('正在拉取发运单...')
        threading.Thread(target=self._query_thread, args=(params, warehouse),
                         daemon=True).start()
        return params

    def _query_thread(self, params, warehouse):
        try:
            rows, err = self._fetch_all(params)
            if err:
                self._after(self._on_query_error, err)
                return
            self._after(self._render_preview, rows, warehouse)
        except Exception as e:
            self._log('查询线程异常:', e)
            self._after(self._on_query_error, str(e))

    def _fetch_all(self, params):
        """分页拉全量 waybillQuery（对齐扩展 content.js:524-585）。"""
        result = []
        page = 1
        total = None
        while True:
            q = dict(params)
            q['limit'] = PAGE_SIZE
            q['pageNum'] = page
            resp = self.controller.session.get(
                URL_WAYBILL_QUERY, params=q, headers=HEADERS, timeout=30)
            payload = json.loads(resp.text) if getattr(resp, 'text', None) else {}

            # 失效/失败判定（三道闸）：
            # 1) HTTP 401/403 —— 会话失效。实测过期 cookie 的响应体只有
            #    {"errorMsg":"错误原因:未能读取到有效 token"}，无 resultCode/code，
            #    若只靠业务码判定会被误当"0 条数据"，必须显式看状态码。
            status = getattr(resp, 'status_code', None)
            if status in (401, 403):
                return result, '登录已失效（HTTP %s），请重新登录' % status
            # 2) 业务错误码（resultCode / code 明确非 200 且非 None）
            rc = payload.get('resultCode')
            code = payload.get('code')
            success = payload.get('success')
            code_bad = ((rc not in (None, 200)) or (code not in (None, 200))
                        or (success is False))
            # 3) 错误消息命中 token/登录失效文案（无业务码时的兜底）。
            #    字段名兼容三种：errorMsg（实测 401 响应用此）、errMsg（app 端读法）、msg。
            err_msg = str(payload.get('errorMsg') or payload.get('errMsg')
                          or payload.get('msg') or '')
            token_bad = any(sig in err_msg for sig in (
                'token', '登录', '未登录', '失效', '过期', '401', '403'))
            if code_bad or (err_msg and token_bad):
                return result, err_msg or '查询失败'
            data = payload.get('data') or {}
            rows = data.get('rows') or data.get('dataList') or data.get('records') or []
            if total is None:
                try:
                    total = int(data.get('total', len(rows)))
                except (TypeError, ValueError):
                    total = len(rows)
            result.extend(rows)
            if len(rows) < PAGE_SIZE or (total is not None and len(result) >= total):
                break
            page += 1
            if page > 1000:  # 安全护栏，避免异常 total 导致死循环
                break
        return result, ''

    def _on_query_error(self, message):
        self.loading = False
        self._set_busy(False)
        self.status_text.set('')
        messagebox.showerror('错误', '查询失败: %s' % message)

    def _render_preview(self, rows, warehouse):
        self.raw_count = len(rows)
        self.warehouse_name = warehouse
        self.grouped = group_by_plate_and_date(rows, warehouse)
        self.route_opts = route_options(get_route_area(warehouse))
        try:
            for iid in self.tree.get_children():
                self.tree.delete(iid)
        except Exception:
            pass
        self.row_ids = []
        for idx, g in enumerate(self.grouped, 1):
            iid = str(idx - 1)
            values = self._row_values(idx, g)
            self.tree.insert('', tk.END, iid=iid, values=values,
                             tags=('odd',) if idx % 2 == 0 else ())
            self.row_ids.append(iid)
        self.tree.tag_configure('odd', background='#fafafa')
        self.file_var.set('目标文件：%s' % report_file_name(warehouse))
        self.status_text.set('匹配发运单 %d 条，有效送货车辆 %d 组'
                             % (self.raw_count, len(self.grouped)))
        self.loading = False
        self._set_busy(False)

    def _row_values(self, idx, g):
        return [
            idx, g['plateNumber'], g['date'], g.get('route') or '',
            _num(g['quantity']), '%.2f' % _num(g['amount']),
            g.get('deliverer') or '',
            int(_num(g.get('returnQty'))) if g.get('returnQty') not in (None, '') else 0,
            int(_num(g.get('brokenQty'))) if g.get('brokenQty') not in (None, '') else 0,
        ]

    # ---------- 双击编辑 ----------
    def _on_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        try:
            idx = int(row_id) + 1
        except ValueError:
            return
        if idx > len(self.grouped):
            return
        self._open_edit_dialog(idx - 1)

    def _open_edit_dialog(self, index):
        g = self.grouped[index]
        dlg = tk.Toplevel(self)
        dlg.title('编辑送货车辆行')
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        fields = {}
        row = 0
        ttk.Label(frm, text='车牌号：%s    日期：%s' % (g['plateNumber'], g['date'])
                  ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(0, 8))
        row += 1
        # 线路：Combobox（按仓库预筛候选，可手选覆盖）
        ttk.Label(frm, text='线路:').grid(row=row, column=0, sticky='w', pady=3)
        route_var = tk.StringVar(value=g.get('route') or '')
        route_cb = ttk.Combobox(frm, textvariable=route_var, width=24,
                                values=[''] + self.route_opts)
        route_cb.grid(row=row, column=1, sticky='w', pady=3)
        fields['route'] = route_var
        row += 1
        for label, key in [('送货片数:', 'quantity'), ('总金额:', 'amount'),
                           ('返程退货数:', 'returnQty'), ('破损数:', 'brokenQty')]:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky='w', pady=3)
            var = tk.StringVar(value=str(g[key]))
            ttk.Entry(frm, textvariable=var, width=20).grid(
                row=row, column=1, sticky='w', pady=3)
            fields[key] = var
            row += 1

        def save():
            try:
                g['route'] = route_var.get().strip()
                g['quantity'] = _num(fields['quantity'].get())
                g['amount'] = _num(fields['amount'].get())
                g['returnQty'] = _num(fields['returnQty'].get())
                g['brokenQty'] = _num(fields['brokenQty'].get())
                for iid in self.tree.get_children():
                    if iid == str(index):
                        self.tree.item(iid, values=self._row_values(index + 1, g))
                        break
                dlg.destroy()
            except Exception as e:
                messagebox.showerror('错误', '保存失败: %s' % e, parent=dlg)

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text='保存', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='取消', command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    # ---------- 导出 ----------
    def clear_file(self):
        self.last_file = ''
        self.status_text.set('已清除目标文件记录')

    def write_report(self):
        if not self.grouped:
            messagebox.showinfo('提示', '请先查询生成报表')
            return None
        if self.writing:
            return None
        default_name = report_file_name(self.warehouse_name)
        initial = os.path.join(app_dir(), default_name)
        path = filedialog.asksaveasfilename(
            title='选择送货车辆 Excel（已存在则追加，不存在则新建）',
            defaultextension='.xlsx',
            initialfile=default_name,
            initialdir=app_dir(),
            filetypes=[('Excel 文件', '*.xlsx'), ('所有文件', '*.*')])
        if not path:
            return None
        self.writing = True
        self._set_busy(True)
        self.status_text.set('正在写入 Excel...')
        threading.Thread(target=self._write_thread,
                         args=(list(self.grouped), path), daemon=True).start()
        return path

    def _write_thread(self, grouped, path):
        try:
            out, appended, skipped = build_report_workbook(grouped, path, path)
            self._after(self._on_write_done, out, appended, skipped)
        except Exception as e:
            self._log('写入线程异常:', e)
            self._after(self._on_write_error, str(e))

    def _on_write_done(self, path, appended, skipped):
        self.writing = False
        self._set_busy(False)
        self.last_file = path
        self.file_var.set('目标文件：%s' % path)
        self.status_text.set('已写入 %d 行，跳过重复 %d 行' % (appended, skipped))

    def _on_write_error(self, message):
        self.writing = False
        self._set_busy(False)
        self.status_text.set('')
        messagebox.showerror('错误', '写入失败: %s' % message)

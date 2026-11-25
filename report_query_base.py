# -*- coding: utf-8 -*-
"""仓储查询报表页通用基类。

对齐 Web 端（HAR + 反混淆 JS）与项目内既有查询页（transfer_detail_query.py /
inventory_record.py）的公共行为：

- 会话：controller.session + controller.check_login_status 统一鉴权
- 筛选：配置驱动的 文本 / 日期(DateEntry) / 仓库 / 字典 / 固定选项 下拉
- 日期默认：当月 1 号 ~ 今天（Web getdefDate('begin'/'end')）
- 表格：服务端分页，pageNum + limit=20；数字列右对齐、编码列等宽
- 合计：独立 Count / Summary 接口，data.sums / data.amount / data.n1~n4
- 导出：openpyxl 本地生成（全量 limit=9999999，对齐 Web exportExcel）

子类只需声明类属性 FILTERS / COLUMNS / URL_QUERY / URL_COUNT 等，
如需特殊参数映射可覆写 build_params / format_value。
"""

import json
import threading
from datetime import date

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from base_page import BasePage

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0'),
}

BASE = 'https://xb.fy-carg.com/dmscloud'
PART = BASE + '.part'
BASEDATA = BASE + '.basedata'

URL_DICTS = BASEDATA + '/dicts'
URL_WAREHOUSE = PART + '/paymentOrder/getWarehouseCodeList'

PAGE_SIZE = 20

# 筛选字段类型：text / date / warehouse / dict / options
#   {'key','label','type', 'param'?, 'default'?, 'code'?, 'options'?, 'warehouse_value'?}
#   warehouse_value: 'id'(默认) / 'code'
# 列定义：
#   {'label','key','width'?, 'kind'?: text/num/money/dict/code, 'dict'?: code}


class ReportQueryBase(BasePage):
    TITLE = '查询'
    COUNT_UNIT = '条'
    URL_QUERY = ''
    URL_COUNT = ''
    FILTERS = []
    COLUMNS = []
    DICT_TYPES = []
    # 合计条：(data key, 显示标签, 格式化类型)；为空则不显示合计条
    TOTALS = [('sums', '数量合计', 'num'), ('amount', '金额合计', 'money')]
    EXCEL_NAME = '查询明细.xlsx'
    FILTER_COLUMNS = 4

    def __init__(self, parent, controller):
        # BasePage.__init__ 会立即调用 create_widgets()，状态必须先初始化
        self.rows = []
        self.total = 0
        self.page_num = 1
        self.page_size = PAGE_SIZE
        self.loading = False
        self.exporting = False
        self.queried = False
        self.filter_vars = {}
        self.date_widgets = {}
        self.combo_widgets = {}
        self.dict_maps = {}          # code -> {code_id(str): desc}
        self.dict_option_maps = {}   # code -> {desc: code_id(str)}
        self.warehouse_names = []
        self.warehouse_id_map = {}   # name -> warehouse_id
        self.warehouse_code_map = {} # name -> warehouse_code
        self.total_values = {}
        super().__init__(parent, controller)

    # -------------------------------------------------------------- 界面构建
    def create_widgets(self):
        outer = ttk.Frame(self.content_frame)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self._build_filter(outer)
        self._build_button_bar(outer)
        self._build_table(outer)
        self._build_summary(outer)
        self._build_pagination(outer)

        # 异步加载字典与仓库（不阻塞界面）
        if self.DICT_TYPES:
            threading.Thread(target=self._load_dicts_thread, daemon=True).start()
        threading.Thread(target=self._load_warehouses_thread, daemon=True).start()

    def _build_filter(self, outer):
        box = ttk.LabelFrame(outer, text='查询条件', padding=6)
        box.pack(fill=tk.X, pady=(0, 5))
        cols = self.FILTER_COLUMNS
        for i, spec in enumerate(self.FILTERS):
            r, c = divmod(i, cols)
            cell = ttk.Frame(box)
            cell.grid(row=r, column=c, sticky='w', padx=(2, 14), pady=3)
            ttk.Label(cell, text=spec['label'] + ':', width=13, anchor='e').pack(side=tk.LEFT)
            key = spec['key']
            kind = spec['type']
            var = tk.StringVar(value='')
            self.filter_vars[key] = var
            if kind == 'date':
                default = spec.get('default', '')
                init = self._def_date('begin' if default == 'begin' else 'end') if default else None
                cal = DateEntry(cell, textvariable=var, width=13, date_pattern='yyyy-mm-dd')
                cal.pack(side=tk.LEFT)
                if init is not None:
                    cal.set_date(init)
                else:
                    cal.delete(0, tk.END)
                self.date_widgets[key] = cal
            elif kind == 'warehouse':
                cb = ttk.Combobox(cell, textvariable=var, width=16, state='readonly',
                                  values=['全部'])
                cb.current(0)
                cb.pack(side=tk.LEFT)
                self.combo_widgets[key] = cb
            elif kind in ('dict', 'options'):
                values = ['全部'] + [x[0] for x in spec.get('options', [])]
                cb = ttk.Combobox(cell, textvariable=var, width=16, state='readonly',
                                  values=values)
                cb.current(0)
                cb.pack(side=tk.LEFT)
                self.combo_widgets[key] = cb
            else:
                ttk.Entry(cell, textvariable=var, width=18).pack(side=tk.LEFT)

    def _build_button_bar(self, outer):
        bar = ttk.Frame(outer)
        bar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(bar, text='查询', command=self.query, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text='重置', command=self.reset_form, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text='导出 Excel', command=self.export_excel, width=12).pack(side=tk.LEFT, padx=2)
        self.count_var = tk.StringVar(value='')
        ttk.Label(bar, textvariable=self.count_var, foreground='#409eff').pack(side=tk.LEFT, padx=12)

    def _build_table(self, outer):
        box = ttk.LabelFrame(outer, text=self.TITLE, padding=4)
        box.pack(fill=tk.BOTH, expand=True)
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        labels = [c['label'] for c in self.COLUMNS]
        widths = [c.get('width', 110) for c in self.COLUMNS]
        self.tree = ttk.Treeview(box, columns=labels, show='headings', height=16)
        for label, width in zip(labels, widths):
            self.tree.heading(label, text=label)
            anchor = 'e' if self._col_kind({'label': label}) in ('num', 'money') else 'center'
            self.tree.column(label, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.tag_configure('odd', background='#fafafa')

    def _build_summary(self, outer):
        if not self.TOTALS:
            return
        bar = ttk.Frame(outer)
        bar.pack(fill=tk.X, pady=(4, 2))
        self.total_vars = {}
        for key, label, kind in self.TOTALS:
            var = tk.StringVar(value=label + '：-')
            self.total_vars[key] = var
            ttk.Label(bar, textvariable=var, foreground='#c0392b',
                      font=('微软雅黑', 9, 'bold')).pack(side=tk.LEFT, padx=14)

    def _build_pagination(self, outer):
        bar = ttk.Frame(outer)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text='首页', command=lambda: self.go_to_page(1), width=7).pack(side=tk.LEFT)
        ttk.Button(bar, text='上一页', command=self.prev_page, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text='下一页', command=self.next_page, width=8).pack(side=tk.LEFT)
        ttk.Button(bar, text='末页', command=lambda: self.go_to_page(self.total_pages()),
                   width=7).pack(side=tk.LEFT, padx=4)
        self.page_var = tk.StringVar(value='1')
        cb = ttk.Combobox(bar, textvariable=self.page_var, width=7, state='readonly')
        cb.pack(side=tk.LEFT, padx=8)
        self.page_combo = cb
        cb.bind('<<ComboboxSelected>>', lambda e: self.go_to_page(self.page_var.get()))
        self.page_info_var = tk.StringVar(value='第 0/0 页 (共 0 条)')
        ttk.Label(bar, textvariable=self.page_info_var).pack(side=tk.LEFT, padx=8)

    # -------------------------------------------------------------- 工具方法
    @staticmethod
    def _def_date(kind):
        today = date.today()
        if kind == 'begin':
            return date(today.year, today.month, 1)
        return today

    @staticmethod
    def fmt_num(val):
        if val is None or val == '':
            return '-'
        try:
            n = float(val)
        except (TypeError, ValueError):
            return str(val)
        return str(int(n)) if n % 1 == 0 else '%.2f' % n

    @staticmethod
    def fmt_money(val):
        if val is None or val == '':
            return '-'
        try:
            return '%.2f' % float(val)
        except (TypeError, ValueError):
            return str(val)

    def _col_kind(self, col):
        return col.get('kind', 'text')

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    def map_dict(self, type_code, val):
        if val is None or val == '':
            return '-'
        s = str(val)
        return self.dict_maps.get(type_code, {}).get(s, s)

    def _filter_value(self, spec):
        """把某个筛选控件的值转成请求参数值。"""
        key = spec['key']
        kind = spec['type']
        raw = self.filter_vars.get(key)
        text = raw.get().strip() if raw is not None else ''
        if kind == 'warehouse':
            if not text or text == '全部':
                return ''
            if spec.get('warehouse_value') == 'code':
                return self.warehouse_code_map.get(text, text)
            return str(self.warehouse_id_map.get(text,
                                                 self.controller.options.get(text, '')))
        if kind == 'dict':
            if not text or text == '全部':
                return ''
            return self.dict_option_maps.get(spec.get('code', ''), {}).get(text, text)
        if kind == 'options':
            if not text or text == '全部':
                return ''
            for display, value in spec.get('options', []):
                if display == text:
                    return value
            return ''
        return text

    def build_params(self, page_num=None, limit=None):
        params = {}
        for spec in self.FILTERS:
            params[spec.get('param', spec['key'])] = self._filter_value(spec)
        params['pageNum'] = self.page_num if page_num is None else page_num
        params['limit'] = self.page_size if limit is None else limit
        return params

    def reset_form(self):
        for spec in self.FILTERS:
            key = spec['key']
            if spec['type'] == 'date' and spec.get('default'):
                self.date_widgets[key].set_date(
                    self._def_date('begin' if spec['default'] == 'begin' else 'end'))
            else:
                self.filter_vars[key].set('')
            cb = self.combo_widgets.get(key)
            if cb is not None:
                cb.current(0)

    def total_pages(self):
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    # -------------------------------------------------------------- 字典/仓库
    def _load_dicts_thread(self):
        try:
            r = self.controller.session.get(URL_DICTS, headers=HEADERS, timeout=20)
            if not self._check_response(r):
                return
            data = r.json()
        except Exception as e:
            print('[%s-字典] 拉取失败: %s' % (self.TITLE, e))
            return
        if not (data.get('resultCode') == 200 or data.get('code') == 200 or data.get('success')):
            return
        obj = data.get('data') or {}
        container = obj.get('dict') if isinstance(obj, dict) else None
        if not isinstance(container, dict):
            container = {}
        code_maps, option_maps = {}, {}
        for t in self.DICT_TYPES:
            cm, om = {}, {}
            for x in container.get(str(t), []) or []:
                if isinstance(x, dict) and x.get('code_id') is not None:
                    code = str(x['code_id'])
                    desc = x.get('code_cn_desc') or x.get('code_en_desc') or code
                    cm[code] = desc
                    om[desc] = code
            code_maps[t] = cm
            option_maps[t] = om
        self.controller.after(0, lambda: self._apply_dicts(code_maps, option_maps))

    def _apply_dicts(self, code_maps, option_maps):
        self.dict_maps = code_maps
        self.dict_option_maps = option_maps
        for spec in self.FILTERS:
            if spec['type'] != 'dict':
                continue
            cb = self.combo_widgets.get(spec['key'])
            if cb is None:
                continue
            opts = ['全部'] + list(option_maps.get(spec.get('code', ''), {}).keys())
            cb.config(values=opts)
            var = self.filter_vars[spec['key']]
            if var.get() not in opts:
                cb.current(0)

    def _load_warehouses_thread(self):
        try:
            r = self.controller.session.get(URL_WAREHOUSE, headers=HEADERS, timeout=20)
            if not self._check_response(r):
                return
            data = r.json()
        except Exception as e:
            print('[%s-仓库] 拉取失败: %s' % (self.TITLE, e))
            return
        if not (data.get('resultCode') == 200 or data.get('success')):
            return
        raw = data.get('data') or []
        if not isinstance(raw, list):
            return
        names, id_map, code_map = [], {}, {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get('warehouse_name')
            if not name:
                continue
            names.append(name)
            if item.get('warehouse_id') is not None:
                id_map[name] = str(item['warehouse_id'])
            if item.get('warehouse_code') is not None:
                code_map[name] = item['warehouse_code']
        self.controller.after(0, lambda: self._apply_warehouses(names, id_map, code_map))

    def _apply_warehouses(self, names, id_map, code_map):
        self.warehouse_names = names
        self.warehouse_id_map = id_map
        self.warehouse_code_map = code_map
        for spec in self.FILTERS:
            if spec['type'] != 'warehouse':
                continue
            cb = self.combo_widgets.get(spec['key'])
            if cb is None:
                continue
            values = ['全部'] + list(names)
            cb.config(values=values)
            var = self.filter_vars[spec['key']]
            if var.get() not in values:
                cb.current(0)

    # -------------------------------------------------------------- 查询/渲染
    def query(self, reset_page=True):
        if self.loading:
            return
        if reset_page:
            self.page_num = 1
        params = self.build_params()
        self.loading = True
        self.count_var.set('查询中...')
        if reset_page:
            self.total_values = {}
            self._update_total_labels()
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(self.URL_QUERY, headers=HEADERS,
                                            params=params, timeout=30)
            print('[%s] %s' % (self.TITLE, r.url))
            if not self._check_response(r):
                return
            data = r.json()
        except Exception as e:
            print('[%s] 请求异常: %s' % (self.TITLE, e))
            self.controller.after(0, lambda: self._query_error('查询异常，请检查网络: %s' % e))
            return
        finally:
            self.loading = False
        if not (data.get('resultCode') == 200 or data.get('code') == 200 or data.get('success')):
            msg = data.get('errMsg') or data.get('errorMsg') or data.get('message') or '查询失败'
            self.controller.after(0, lambda: self._query_error(str(msg)))
            return
        d = data.get('data') or {}
        rows = d.get('rows') or []
        total = d.get('total') or data.get('total') or len(rows)
        self.controller.after(0, lambda: self._render_rows(rows, total))
        if self.URL_COUNT:
            threading.Thread(target=self._count_thread, args=(params,), daemon=True).start()

    def _query_error(self, msg):
        self.count_var.set('')
        messagebox.showerror('查询失败', msg)

    def _render_rows(self, rows, total):
        self.rows = rows
        self.total = total
        self.queried = True
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in enumerate(rows):
            values = [self.format_value(row, col, idx) for col in self.COLUMNS]
            self.tree.insert('', tk.END, values=values,
                             tags=('odd',) if idx % 2 else ())
        self.count_var.set('共 %d %s' % (total, self.COUNT_UNIT))
        self._update_page_info()

    def format_value(self, row, col, idx):
        """单元格显示值；子类可覆写做特殊格式化。"""
        key = col['key']
        val = row.get(key)
        kind = self._col_kind(col)
        if kind == 'num':
            return self.fmt_num(val)
        if kind == 'money':
            return self.fmt_money(val)
        if kind == 'dict':
            return self.map_dict(col.get('dict', ''), val)
        if val is None or val == '':
            return '-'
        return str(val)

    def _count_thread(self, params):
        try:
            r = self.controller.session.get(self.URL_COUNT, headers=HEADERS,
                                            params=params, timeout=30)
            if not self._check_response(r):
                return
            data = r.json()
        except Exception as e:
            print('[%s-合计] 失败: %s' % (self.TITLE, e))
            return
        if not (data.get('resultCode') == 200 or data.get('success')):
            return
        d = data.get('data') or {}
        self.controller.after(0, lambda: self._apply_totals(d))

    def _apply_totals(self, data):
        self.total_values = {k: data.get(k) for k, _, _ in self.TOTALS}
        self._update_total_labels()

    def _update_total_labels(self):
        if not hasattr(self, 'total_vars'):
            return
        for key, label, kind in self.TOTALS:
            val = self.total_values.get(key)
            if val is None:
                text = label + '：-'
            elif kind == 'money':
                text = '%s：%s' % (label, self.fmt_money(val))
            else:
                text = '%s：%s' % (label, self.fmt_num(val))
            self.total_vars[key].set(text)

    # -------------------------------------------------------------- 分页
    def _update_page_info(self):
        pages = self.total_pages()
        self.page_info_var.set('第 %d/%d 页 (共 %d %s)' %
                               (self.page_num, pages, self.total, self.COUNT_UNIT))
        self.page_combo.config(values=[str(i) for i in range(1, pages + 1)])
        self.page_var.set(str(self.page_num))

    def go_to_page(self, page):
        if self.loading:
            return
        try:
            page = int(page)
        except (TypeError, ValueError):
            return
        page = min(max(1, page), self.total_pages())
        if page == self.page_num:
            return
        self.page_num = page
        self.query(reset_page=False)

    def prev_page(self):
        self.go_to_page(self.page_num - 1)

    def next_page(self):
        self.go_to_page(self.page_num + 1)

    # -------------------------------------------------------------- 导出
    def export_excel(self):
        if self.exporting:
            return
        path = filedialog.asksaveasfilename(
            title='导出%s' % self.TITLE,
            defaultextension='.xlsx',
            initialfile=self.EXCEL_NAME,
            filetypes=[('Excel 文件', '*.xlsx'), ('所有文件', '*.*')])
        if not path:
            return
        self.exporting = True
        threading.Thread(target=self._export_thread, args=(path,), daemon=True).start()

    def _export_thread(self, path):
        """导出全量数据（limit=9999999），与 Web exportExcel 行为一致。"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        try:
            params = self.build_params(page_num=1, limit=9999999)
            r = self.controller.session.get(self.URL_QUERY, headers=HEADERS,
                                            params=params, timeout=60)
            if not self._check_response(r):
                return
            data = r.json()
            rows = ((data.get('data') or {}).get('rows') or [])
            wb = Workbook()
            ws = wb.active
            ws.title = self.TITLE
            ws.append([c['label'] for c in self.COLUMNS])
            for cell in ws[1]:
                cell.font = Font(bold=True, color='FFFFFFFF')
                cell.fill = PatternFill('solid', fgColor='FF409EFF')
                cell.alignment = Alignment(horizontal='center', vertical='center')
            for i, col in enumerate(self.COLUMNS, 1):
                ws.column_dimensions[get_column_letter(i)].width = col.get('width', 110)
            for idx, row in enumerate(rows):
                ws.append([self.format_value(row, c, idx) for c in self.COLUMNS])
            if self.TOTALS and self.total_values:
                label = ['合计'] + [''] * (len(self.COLUMNS) - 1)
                for key, _, kind in self.TOTALS:
                    col = self.COLUMNS[-1]
                    if key in self.total_values:
                        label[-1] = (self.fmt_money(self.total_values[key]) if kind == 'money'
                                     else self.fmt_num(self.total_values[key]))
                ws.append(label)
            wb.save(path)
            print('[%s] 导出成功: %s (%d 行)' % (self.TITLE, path, len(rows)))
        except Exception as e:
            print('[%s-导出] 失败: %s' % (self.TITLE, e))
            self.controller.after(0, lambda: messagebox.showerror('导出失败', str(e)))
        finally:
            self.exporting = False

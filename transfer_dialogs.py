# -*- coding: utf-8 -*-
"""库内作业（调拨申请 / 移库管理）PC 端共用弹窗组件

背景
====
Web 端（dms_vue-prod）在明细表格行内内嵌 `el-select` / `el-input` /
`el-upload` 等控件；桌面端 ttk.Treeview 无法内嵌控件，因此把「行内编辑」
映射为三个独立弹窗。三者的**字段名、请求参数、返回结构**逐一对齐 Web 源：

1. ProductPickerDialog  —— 明细「添加一行」
   对齐 Web `partSelect` 组件 + `warehouse/transferIn/queryPart` 、
   `warehouse/change/queryPart`（HAR 实测参数 warehouseId/partNo/partName/
   isValid=10031001/pageNum/pageSize，返回 data.rows）。

2. LocationPickerDialog —— 库位选择
   对齐 Web `el-select remote` + `warehouse/transferIn/findAllLocationValid`
   （参数 warehouseId/locationNo，返回 data=[{locationId,locationNo,...}]）。
   Web 端同一份接口同时服务于「调入申请-入库库位」与「移库管理-移入库位」。

3. EmployeeMultiPicker —— 移库人多选
   对齐 Web `el-select multiple` + `basedata/employees/getEmpByRoleCode`
   （参数 roleCode/warehouseId，返回 data=[{EMPLOYEE_NAME,PHONE}]）。

设计约束
========
- 网络请求一律放在 daemon 线程，UI 更新经 `controller.after(0, ...)` 回主线程
  （与 purchase_sign.py / transfer_manager.py 一致）。
- 组件只负责「选」，不直接改页面状态；统一通过构造时传入的 on_pick 回调回传
  结果，页面自行决定如何落到明细行。
- 组件不吞异常：捕获后打印日志 + 弹窗提示，保证页面不崩。
"""

import json
import threading

import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------- 常量 / 接口
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

BASE = 'https://xb.fy-carg.com'
# 库位远端搜索（调入申请与移库管理共用同一接口）
URL_LOCATION = BASE + '/dmscloud.part/warehouse/transferIn/findAllLocationValid'
# 员工按角色码查询（移库人 roleCode=YKR）
URL_EMP_ROLE = BASE + '/dcscloud.basedata/basedata/employees/getEmpByRoleCode'

# 产品查询接口（两个页面各自不同，由调用方传入）
URL_QUERY_PART_TRANSFER_IN = BASE + '/dmscloud.part/warehouse/transferIn/queryPart'
URL_QUERY_PART_CHANGE = BASE + '/dmscloud.part/warehouse/change/queryPart'

# 有效产品过滤（HAR 实测固定值）
PART_VALID = '10031001'
# 每页条数（对齐 Web BaseTable 默认）
PICKER_PAGE_SIZE = 20
# 库位下拉 Web 端截断上限（splice(0,500)）
LOCATION_LIMIT = 500


# ---------------------------------------------------------------- 工具
def resp_ok(data):
    """统一判定接口成功（与各页面 _check_response 语义一致）。"""
    if not isinstance(data, dict):
        return False
    return bool(data.get('success')) or data.get('resultCode') == 200 or data.get('code') == 200


def err_msg(data, default='请求失败'):
    if isinstance(data, dict):
        return data.get('errMsg') or data.get('errorMsg') or data.get('message') or default
    return default


def _scroll_tree(parent, columns, widths, height=12):
    """生成一个带双向滚动条的 Treeview，返回 (frame, tree)。"""
    frame = tk.Frame(parent, bg="#f0f0f0")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="center")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    return frame, tree


# ================================================================ 1. 产品选择
class ProductPickerDialog:
    """明细「添加一行」——产品选择弹窗（对齐 Web partSelect + queryPart）。

    参数
    ----
    parent       : 父窗口
    controller   : 主控制器（提供 session / after）
    query_url    : queryPart 接口地址（调入申请 / 移库管理各一）
    warehouse_id : 仓库 ID（调入申请=调出仓库，移库管理=当前仓库）
    on_pick      : 选中回调，入参为选中的原始行 dict 列表
    title        : 标题
    allow_multi  : 是否允许多选（默认 True，对齐 Web select-success 批量 push）
    part_no_key  : 产品编码字段名（默认 partCode）
    """

    def __init__(self, parent, controller, query_url, warehouse_id,
                 on_pick, title="选择产品", allow_multi=True,
                 part_no_key="partCode", mode="default"):
        self.controller = controller
        self.query_url = query_url
        self.warehouse_id = warehouse_id
        self.on_pick = on_pick
        self.allow_multi = allow_multi
        self.part_no_key = part_no_key
        self.mode = mode                      # reserved（调用方可留默认）
        self.rows = []
        self.total = 0
        self.page_num = 1
        self.page_size = PICKER_PAGE_SIZE
        self.loading = False

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("980x560")
        self.win.transient(parent)
        self._build()
        # 打开即拉第一页，对齐 Web partSelect mounted 行为
        self.query()

    # ------------------------------------------------------------ UI
    def _build(self):
        top = tk.Frame(self.win, bg="#f0f0f0")
        top.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(top, text="CARG全码/产品编码:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.part_no_var = tk.StringVar()
        e1 = ttk.Entry(top, textvariable=self.part_no_var, width=18)
        e1.pack(side=tk.LEFT, padx=4)
        e1.bind("<Return>", lambda _e: self.query(reset_page=True))

        tk.Label(top, text="产品名称:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(12, 0))
        self.part_name_var = tk.StringVar()
        e2 = ttk.Entry(top, textvariable=self.part_name_var, width=22)
        e2.pack(side=tk.LEFT, padx=4)
        e2.bind("<Return>", lambda _e: self.query(reset_page=True))

        tk.Button(top, text="查询", command=lambda: self.query(reset_page=True),
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=6)

        cols = ['产品编码', '产品名称', '品牌', '可用数量', '库位']
        widths = [150, 380, 110, 80, 120]
        body, self.tree = _scroll_tree(self.win, cols, widths, height=15)
        body.pack(fill=tk.BOTH, expand=True, padx=10)
        if self.allow_multi:
            self.tree.configure(selectmode="extended")
        else:
            self.tree.configure(selectmode="browse")
        self.tree.bind("<Double-1>", lambda _e: self._confirm())

        pager = tk.Frame(self.win, bg="#f0f0f0")
        pager.pack(fill=tk.X, padx=10, pady=8)
        self.info_var = tk.StringVar(value="")
        tk.Label(pager, textvariable=self.info_var, bg="#f0f0f0").pack(side=tk.LEFT)
        btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 6}
        tk.Button(pager, text="上一页", command=lambda: self.go(-1), **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(pager, text="下一页", command=lambda: self.go(1), **btn_style).pack(side=tk.LEFT, padx=3)

        tk.Button(pager, text="添加选中", command=self._confirm,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=12).pack(side=tk.RIGHT, padx=3)
        tk.Button(pager, text="取消", command=self.win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=12).pack(side=tk.RIGHT, padx=3)

    # ------------------------------------------------------------ 数据
    def query(self, reset_page=False):
        if self.loading:
            return
        if reset_page:
            self.page_num = 1
        if not self.warehouse_id:
            messagebox.showwarning("提示", "请先选择仓库")
            return
        params = {
            'warehouseId': self.warehouse_id,
            'partNo': self.part_no_var.get().strip(),
            'partName': self.part_name_var.get().strip(),
            'isValid': PART_VALID,
            'pageNum': self.page_num,
            'pageSize': self.page_size,
        }
        self.loading = True
        self.info_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(self.query_url, headers=HEADERS, params=params)
            print("[产品选择] %s" % r.url)
            data = json.loads(r.text)
        except Exception as e:
            print("[产品选择] 请求异常: %s" % e)
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("错误", "查询异常: %s" % e))
            return
        finally:
            self.loading = False

        if not resp_ok(data):
            msg = err_msg(data, "查询失败")
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            return

        d = data.get('data') or {}
        rows = d.get('rows') or d.get('data') or d.get('records') or []
        total = d.get('total') or len(rows)
        self.controller.after(0, lambda: self._render(rows, total))

    def _render(self, rows, total):
        if not self.win.winfo_exists():
            return
        self.rows = rows
        self.total = total
        for it in self.tree.get_children():
            self.tree.delete(it)
        for row in rows:
            self.tree.insert("", "end", values=(
                row.get('partCode') or '-',
                row.get('partName') or '-',
                row.get('brandName') or row.get('brand') or '-',
                _fmt(row.get('availableQty')),
                row.get('removeNo') or row.get('pickingLocationNo')
                or row.get('locationNo') or row.get('shelfLocationNo') or '-',
            ))
        pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.info_var.set("第 %d/%d 页 (共 %d 条)" % (self.page_num, pages, total))

    def go(self, delta):
        pages = max(1, (self.total + self.page_size - 1) // self.page_size)
        target = min(max(1, self.page_num + delta), pages)
        if target == self.page_num:
            return
        self.page_num = target
        self.query()

    def _confirm(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择产品")
            return
        picked = [self.rows[self.tree.index(it)] for it in sel
                  if 0 <= self.tree.index(it) < len(self.rows)]
        if not picked:
            return
        if self.on_pick:
            self.on_pick(picked)
        self.win.destroy()


# ================================================================ 2. 库位选择
class LocationPickerDialog:
    """库位选择弹窗（对齐 Web el-select remote + findAllLocationValid）。

    参数
    ----
    warehouse_id : 仓库 ID（调入申请=调入仓库，移库管理=当前仓库）
    on_pick      : 回调，入参为选中的库位 dict（含 locationId/locationNo）
    """

    def __init__(self, parent, controller, warehouse_id, on_pick,
                 title="选择库位", current=None, top_n=200):
        self.controller = controller
        self.warehouse_id = warehouse_id
        self.on_pick = on_pick
        self.rows = []
        self.current = current or {}

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("560x520")
        self.win.transient(parent)
        self._build()
        # 预填当前库位编号，若为空则默认拉 A 开头的库位（对齐 Web remote 首次输入）
        if not self.loc_var.get():
            self.loc_var.set(str(self.current.get('locationNo') or ''))
        self.query()

    def _build(self):
        top = tk.Frame(self.win, bg="#f0f0f0")
        top.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(top, text="库位编号:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.loc_var = tk.StringVar(value=str(self.current.get('locationNo') or ''))
        e = ttk.Entry(top, textvariable=self.loc_var, width=24)
        e.pack(side=tk.LEFT, padx=4)
        e.bind("<Return>", lambda _e: self.query())
        e.focus_set()
        tk.Button(top, text="查询", command=self.query,
                  bg="#4CAF50", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=6)

        body, self.tree = _scroll_tree(self.win, ['库位编号', '库位ID'], [260, 120], height=16)
        body.pack(fill=tk.BOTH, expand=True, padx=10)
        self.tree.bind("<Double-1>", lambda _e: self._confirm())

        foot = tk.Frame(self.win, bg="#f0f0f0")
        foot.pack(fill=tk.X, padx=10, pady=8)
        self.info_var = tk.StringVar(value="")
        tk.Label(foot, textvariable=self.info_var, bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(foot, text="确定", command=self._confirm,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=14).pack(side=tk.RIGHT, padx=3)
        tk.Button(foot, text="取消", command=self.win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14).pack(side=tk.RIGHT, padx=3)

    def query(self):
        if not self.warehouse_id:
            messagebox.showwarning("提示", "请先选择仓库")
            return
        keyword = self.loc_var.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入库位编号关键字")
            return
        self.info_var.set("查询中...")
        threading.Thread(target=self._thread, args=(keyword,), daemon=True).start()

    def _thread(self, keyword):
        try:
            r = self.controller.session.get(
                URL_LOCATION, headers=HEADERS,
                params={'warehouseId': self.warehouse_id, 'locationNo': keyword})
            print("[库位选择] %s" % r.url)
            data = json.loads(r.text)
        except Exception as e:
            print("[库位选择] 请求异常: %s" % e)
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("错误", "查询异常: %s" % e))
            return

        if not resp_ok(data):
            msg = err_msg(data, "查询失败")
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            return
        rows = data.get('data') or []
        if not isinstance(rows, list):
            rows = []
        # Web 端 splice(0,500) 截断
        self.controller.after(0, lambda: self._render(rows[:LOCATION_LIMIT]))

    def _render(self, rows):
        if not self.win.winfo_exists():
            return
        self.rows = rows
        for it in self.tree.get_children():
            self.tree.delete(it)
        for row in rows:
            self.tree.insert("", "end", values=(
                row.get('locationNo') or '-',
                row.get('locationId') or '-',
            ))
        self.info_var.set("共 %d 个库位" % len(rows))

    def _confirm(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择库位")
            return
        idx = self.tree.index(sel[0])
        if not (0 <= idx < len(self.rows)):
            return
        if self.on_pick:
            self.on_pick(self.rows[idx])
        self.win.destroy()


# ================================================================ 3. 移库人多选
class EmployeeMultiPicker:
    """移库人多选弹窗（对齐 Web el-select multiple + getEmpByRoleCode）。

    参数
    ----
    role_code    : 角色码（移库人 YKR；本模块另可传 JHR 拣货人 / SJR 上架人）
    warehouse_id : 可选，仓库 ID（Web 端移库人随仓库变化，传 -1 表示全部）
    on_pick      : 回调，入参为选中的姓名列表
    """

    def __init__(self, parent, controller, role_code, on_pick,
                 warehouse_id=None, title="选择移库人", preselect=None):
        self.controller = controller
        self.role_code = role_code
        self.warehouse_id = warehouse_id
        self.on_pick = on_pick
        self.preselect = set(preselect or [])
        self.names = []

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("420x520")
        self.win.transient(parent)
        self._build()
        self.load()

    def _build(self):
        tk.Label(self.win, text="可多选（Ctrl/Shift 点选）", bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(anchor="w", padx=10, pady=(8, 2))
        body = tk.Frame(self.win, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True, padx=10)
        self.listbox = tk.Listbox(body, selectmode=tk.EXTENDED, height=18)
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vsb.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        foot = tk.Frame(self.win, bg="#f0f0f0")
        foot.pack(fill=tk.X, padx=10, pady=8)
        self.info_var = tk.StringVar(value="加载中...")
        tk.Label(foot, textvariable=self.info_var, bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(foot, text="确定", command=self._confirm,
                  bg="#2196F3", fg="white", relief=tk.FLAT, padx=14).pack(side=tk.RIGHT, padx=3)
        tk.Button(foot, text="取消", command=self.win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=14).pack(side=tk.RIGHT, padx=3)

    def load(self):
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        params = {'roleCode': self.role_code}
        if self.warehouse_id is not None:
            params['warehouseId'] = self.warehouse_id
        try:
            r = self.controller.session.get(URL_EMP_ROLE, headers=HEADERS, params=params)
            print("[移库人] %s" % r.url)
            data = json.loads(r.text)
        except Exception as e:
            print("[移库人] 请求异常: %s" % e)
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("错误", "加载失败: %s" % e))
            return

        if not resp_ok(data):
            msg = err_msg(data, "加载失败")
            self.controller.after(0, lambda: self.info_var.set(""))
            self.controller.after(0, lambda: messagebox.showerror("加载失败", str(msg)))
            return
        arr = data.get('data') or []
        names = []
        for u in arr if isinstance(arr, list) else []:
            if isinstance(u, dict):
                n = u.get('EMPLOYEE_NAME') or u.get('name')
                if n:
                    names.append(n)
        self.controller.after(0, lambda: self._render(names))

    def _render(self, names):
        if not self.win.winfo_exists():
            return
        self.names = names
        self.listbox.delete(0, tk.END)
        for i, n in enumerate(names):
            self.listbox.insert(tk.END, n)
            if n in self.preselect:
                self.listbox.selection_set(i)
        self.info_var.set("共 %d 人" % len(names))

    def _confirm(self):
        picked = [self.names[i] for i in self.listbox.curselection()
                  if 0 <= i < len(self.names)]
        if self.on_pick:
            self.on_pick(picked)
        self.win.destroy()


# ================================================================ 工具
def _fmt(val):
    """数字格式化：空值 '-'，整数不显示小数，否则两位。"""
    try:
        n = float(val)
    except (TypeError, ValueError):
        return "-"
    return str(int(n)) if n % 1 == 0 else "%.2f" % n

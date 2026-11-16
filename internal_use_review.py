# -*- coding: utf-8 -*-
"""
内部领用 · 菜单2「部门审核」InternalUseReviewPage
--------------------------------------------------
对齐 Android 端 InternalUseReview.vue（部门审核，菜单 MENU_ID 501505）。

工作流（1246 组，HAR 实证）：
  新建 12461001 --提交--> 待审核 12461002 --部门通过--> 部门审核通过 12461005
  （后续经理环节 12461003/12461004 不在本页）；部门驳回 --> 部门审核驳回 12461006（退回领用人可改再提）。

查询待审（对齐安卓 doQuery）：
  GET /dmscloud.part/internalUse/page?STATUS=12461002&ORG_NAME={仓}&storage_code={code}&
     DEPARTMENT_ID=&BRAND_ID=&CREATED_AT_FROM=&CREATED_AT_TO=&isDept=1&pageNum=1&limit=500
  前端再按 STATUS==12461002 兜底过滤。

审核报文（⚠️ 大小写 STATUS 语义，HAR #92 实证，勿改）：
  - 大写 STATUS = 当前状态（待审核 12461002），来自 queryById 主单权威对象原样带回；
  - 小写 status  = 目标状态（通过 12461005 / 驳回 12461006），追加在报文末尾；
  - 主单以 queryById 返回的完整对象展开（含 RECORD_VERSION/NO_TAX_AMOUNT/时间字段…），
    明细行保留持久化行全部字段，仅覆盖 USE_NUM / OUT_LOCATION / loList；
  - 驳回必须带顶层 checkRemark（审核意见）。
  - 端点：通过 POST /dmscloud.part/internalUse/manager/approved；驳回 POST .../manager/reject。
  - 审核日志由后端在审核 POST 成功后自动生成，前端不构造（与 PC 一致）。

本页桌面实现要点：
  - 仓库下拉 + 自动查询本仓待审（对齐安卓 onMounted）；「待我审核：N 单」统计 + 刷新。
  - 双击/审核按钮打开审核窗：主单信息 + 领用明细 + 操作日志（operateLogs/page,
    BILL_TYPE=12041002, limit=5, isShowLogs=true）+ 审核意见（驳回必填）。
  - 通过/驳回成功即从列表移除并更新统计，不重新拉全量。
"""
import json
import threading

import tkinter as tk
from tkinter import ttk, messagebox

from base_page import BasePage
from tooltip_manager import tooltip_manager
from warehouse_mapping import get_storage_code

from internal_use_manage import (
    HEADERS, BASE, PART,
    URL_DETAIL, URL_ITEMS, URL_LOGS,
    LOG_BILL_TYPE, LOG_PAGE_SIZE, QUERY_LIMIT,
    COLUMNS, COLUMN_WIDTHS,          # 列表列（与菜单1一致）
    InternalUseManagePage,           # 复用静态格式化/状态辅助
)

# 本页接口
URL_QUERY = BASE + PART + '/page'
URL_APPROVE = BASE + PART + '/manager/approved'
URL_REJECT = BASE + PART + '/manager/reject'

# 部门审核目标状态（小写 status 字段）
AUDIT_PASS_STATUS = 12461005    # 部门审核通过
AUDIT_REJECT_STATUS = 12461006  # 部门审核驳回
# 本页待审状态（待部门审核）
DEPT_PENDING_STATUS = 12461002

# 明细列（审核窗内展示）
DETAIL_COLUMNS = ["序号", "配件名称", "数量", "库位", "品牌", "单价"]
DETAIL_WIDTHS = [50, 240, 70, 110, 100, 100]


class InternalUseReviewPage(BasePage):
    """内部领用-部门审核页面（待审列表 / 通过 / 驳回）"""

    def __init__(self, parent, controller):
        self.pending_rows = []      # 待审列表（STATUS==12461002）
        self.queried = False
        self.loading = False
        self.auditing = False       # 审核请求进行中
        self.audit_id = ''
        self.audit_win = None
        self.audit_raw = None       # queryById 完整主单（构造审核报文的权威对象）
        self.audit_items = []       # queryById/items 明细行
        self.check_remark = None    # 审核意见控件
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        main = tk.Frame(self.content_frame, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_header(main)
        self.setup_data_table(main)

        # 对齐安卓 onMounted：进入页面自动查询待审
        if self.controller.options:
            self.query()

    def setup_header(self, parent):
        frame = tk.LabelFrame(parent, text="待审领用单（部门审核）", bg="#f0f0f0",
                              font=("微软雅黑", 10, "bold"))
        frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=6)

        row = tk.Frame(frame, bg="#f0f0f0")
        row.pack(fill=tk.X)

        tk.Label(row, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)
        tk.Label(row, text="（本仓库待部门审核领用单）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=5)

        self.stat_var = tk.StringVar(value="待我审核：-")
        tk.Label(row, textvariable=self.stat_var, bg="#f0f0f0",
                 font=("微软雅黑", 11, "bold"), fg="#07c160").pack(side=tk.LEFT, padx=20)

        tk.Button(row, text="刷新", command=self.query,
                  bg="#07c160", fg="white", padx=14, pady=3, bd=0).pack(side=tk.RIGHT, padx=5)

        tk.Label(frame, text="双击单据行打开审核", bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 9)).pack(anchor="w", padx=5)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="领用单审核", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "e" if col == "金额" else ("center" if col == "序号" else "w")
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
        self.tree.bind("<Double-1>", lambda e: self.open_audit())

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def format_money(val):
        return InternalUseManagePage.format_money(val)

    @staticmethod
    def format_date(s):
        return InternalUseManagePage.format_date(s)

    @staticmethod
    def use_status_label(code):
        return InternalUseManagePage.use_status_label(code)

    def _check_response(self, response):
        return not self.controller.check_login_status(response)

    def _selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.pending_rows):
            return self.pending_rows[idx]
        return None

    # ------------------------------------------------------------------ 查询
    def build_query_params(self):
        """待部门审核查询（对齐安卓 doQuery：isDept=1，其余筛选恒空）"""
        wh = self.warehouse_var.get()
        return {
            "USE_NO": '',
            "USE_MAN": '',
            "STATUS": str(DEPT_PENDING_STATUS),
            "ORG_NAME": wh,
            "DEPARTMENT_ID": '',
            "storage_code": get_storage_code(wh),
            "BRAND_ID": '',
            "CREATED_AT_FROM": '',
            "CREATED_AT_TO": '',
            "isDept": 1,
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
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[内部领用-部门审核] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-部门审核] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常，请检查网络: {e}"))
            self.controller.after(0, lambda: self.stat_var.set("待我审核：-"))
            return
        finally:
            self.loading = False

        if not (data.get("resultCode") == 200 or data.get("code") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or data.get("message") or "查询失败"
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            self.controller.after(0, lambda: self.stat_var.set("待我审核：-"))
            return

        resp = data.get("data") or {}
        rows = resp.get("rows") if isinstance(resp, dict) else None
        if not isinstance(rows, list):
            rows = resp if isinstance(resp, list) else []
        self.controller.after(0, lambda: self._apply_result(rows))

    def _apply_result(self, rows):
        # 仅保留待部门审核状态（后端已按 STATUS 过滤，前端再兜底一次）
        self.pending_rows = [r for r in rows
                             if str(r.get('STATUS')) == str(DEPT_PENDING_STATUS)]
        self.queried = True
        self._render_rows()
        if not self.pending_rows:
            messagebox.showinfo("内部领用-部门审核", "暂无待审领用单")

    def _render_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in enumerate(self.pending_rows):
            values = (
                idx + 1,
                row.get('USE_NO') or '-',
                self.use_status_label(row.get('STATUS')),
                row.get('USE_MAN') or '-',
                row.get('DEPARTMENT_NAME') or '-',
                row.get('WAREHOUSE_NAME') or '-',
                self.format_date(row.get('CREATED_AT')),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.stat_var.set("待我审核：{} 单".format(len(self.pending_rows)))

    # ------------------------------------------------------------------ 审核
    def open_audit(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条待审领用单")
            return
        bill_id = row.get('ID')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 ID，无法审核")
            return
        self.audit_id = str(bill_id)
        self.audit_raw = None
        self.audit_items = []
        threading.Thread(target=self._audit_thread, args=(bill_id, row), daemon=True).start()

    def _audit_thread(self, bill_id, row):
        """加载主单 + 明细 + 操作日志（对齐安卓：主单/明细并行拉完后再拉日志）"""
        master = {}
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                d = json.loads(r.text)
                if d.get("resultCode") == 200 or d.get("success"):
                    master = d.get("data") or {}
        except Exception as e:
            print(f"[内部领用-部门审核-主单] 异常: {e}")
        items = []
        try:
            r = self.controller.session.get(URL_ITEMS, headers=HEADERS, params={'id': bill_id})
            if self._check_response(r):
                d = json.loads(r.text)
                if d.get("resultCode") == 200 or d.get("success"):
                    arr = d.get("data") or []
                    items = arr if isinstance(arr, list) else []
        except Exception as e:
            print(f"[内部领用-部门审核-明细] 异常: {e}")
        if not master:
            self.controller.after(0, lambda: messagebox.showerror("加载失败", "主单数据加载失败，无法审核"))
            return
        logs = []
        try:
            r = self.controller.session.get(URL_LOGS, headers=HEADERS, params={
                'BILL_ID': bill_id, 'BILL_TYPE': LOG_BILL_TYPE,
                'limit': LOG_PAGE_SIZE, 'pageNum': 1, 'isShowLogs': True})
            if self._check_response(r):
                d = json.loads(r.text)
                dd = d.get("data") or {}
                logs = dd.get("rows") if isinstance(dd, dict) and isinstance(dd.get("rows"), list) else []
        except Exception as e:
            print(f"[内部领用-部门审核-日志] 异常: {e}")
        payload = {
            'id': str(bill_id),
            'master': master,
            'items': items,
            'logs': logs,
        }
        self.controller.after(0, lambda: self._show_audit_window(payload))

    def _show_audit_window(self, p):
        win = tk.Toplevel(self)
        win.title("领用单审核 - %s" % (p['master'].get('USE_NO') or p['id']))
        win.geometry("760x760")
        win.transient(self)
        self.audit_win = win
        self.audit_raw = p['master']
        self.audit_items = p['items']
        m = p['master']

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="领用单审核", bg="#f7f8fa", fg="#722ed1",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text="状态：%s" % self.use_status_label(m.get('STATUS')),
                 bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        # 基本信息
        info = tk.LabelFrame(win, text="基本信息", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        info.pack(fill=tk.X, padx=10, pady=5, ipadx=6, ipady=4)
        for key, val in (("单号", m.get('USE_NO') or '-'),
                         ("部门", m.get('DEPARTMENT_NAME') or '-'),
                         ("领用人", m.get('USE_MAN') or '-'),
                         ("领用人电话", m.get('USE_PHONE') or '-'),
                         ("出库仓", m.get('WAREHOUSE_NAME') or '-'),
                         ("备注", m.get('REMARK') or '无')):
            line = tk.Frame(info, bg="#f0f0f0")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text=key + "：", bg="#f0f0f0", fg="#969799",
                     font=("微软雅黑", 10), width=10, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#f0f0f0", font=("微软雅黑", 10),
                     anchor="w", wraplength=600, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 领用明细
        tk.Label(win, text=f"领用明细（{len(p['items'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dtree = ttk.Treeview(dframe, columns=DETAIL_COLUMNS, show="headings", height=5)
        for col, width in zip(DETAIL_COLUMNS, DETAIL_WIDTHS):
            dtree.heading(col, text=col)
            anchor = "e" if col in ("数量", "单价") else "w"
            dtree.column(col, width=width, anchor=anchor)
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

        # 操作日志（默认展开，对齐 PC logs 组件 is-active）
        self._render_audit_logs(win, p['logs'])

        # 审核意见
        tk.Label(win, text="审核意见（驳回时必填）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
        self.check_remark = tk.Text(win, height=3, font=("微软雅黑", 10))
        self.check_remark.pack(fill=tk.X, padx=10)

        # 操作按钮
        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        tk.Button(bar, text="通 过", command=self.do_pass,
                  bg="#07c160", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="驳 回", command=self.do_reject,
                  bg="#ee0a24", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.RIGHT, padx=10)

    def _render_audit_logs(self, win, logs):
        lf = tk.LabelFrame(win, text=f"操作日志（{len(logs)}）", bg="#f0f0f0",
                           font=("微软雅黑", 10, "bold"))
        lf.pack(fill=tk.X, padx=10, pady=(6, 2), ipadx=6, ipady=3)
        if not logs:
            tk.Label(lf, text="无日志", bg="#f0f0f0", fg="#c8c9cc").pack(anchor="w")
            return
        # 后端 BEFORE_VALUE/AFTER_VALUE 已是中文状态名，原样展示不二次翻译
        for log in logs:
            operator = log.get('OPERATOR_NAME') or log.get('OPERATOR') or '-'
            when = self.format_date(log.get('OPERATE_DATE') or log.get('CREATED_AT'))
            trans = ''
            if log.get('BEFORE_VALUE') or log.get('AFTER_VALUE'):
                trans = '{} → {}'.format(log.get('BEFORE_VALUE') or '-', log.get('AFTER_VALUE') or '-')
            remark = ('（%s）' % log['REMARK']) if log.get('REMARK') else ''
            summary = ('[%s] ' % log['SUMMARY']) if log.get('SUMMARY') else ''
            text = "[{}] {} {}{}{}".format(operator, when, summary, trans, remark)
            tk.Label(lf, text=text, bg="#f0f0f0", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)

    def build_audit_payload(self, target_status, remark=None):
        """审核报文（⚠️ 大小写 STATUS 语义，HAR #92：大写=当前态，小写 status=目标态）"""
        master = dict(self.audit_raw or {})
        item_list = []
        for d in self.audit_items:
            it = dict(d)   # 保留持久化行全部字段（ID/PID/RECORD_VERSION/…）
            it['USE_NUM'] = d.get('USE_NUM')
            it['OUT_LOCATION'] = d.get('OUT_LOCATION') or ''
            it['loList'] = (d.get('loList') if isinstance(d.get('loList'), list) and d['loList'] else [])
            item_list.append(it)
        payload = dict(master)               # 完整主单权威对象展开
        payload['itemList'] = item_list
        payload['delItemList'] = []
        payload['status'] = target_status    # 小写 status = 目标状态（HAR 末位追加）
        if remark:
            payload['checkRemark'] = remark
        return payload

    def do_pass(self):
        if self.auditing:
            return
        if not messagebox.askyesno("确认通过", "确认通过此领用单？通过后进入经理审核。"):
            return
        self._submit_action(URL_APPROVE, AUDIT_PASS_STATUS, None, "通过", "已审核通过")

    def do_reject(self):
        if self.auditing:
            return
        remark = self.check_remark.get("1.0", "end").strip() if self.check_remark else ''
        if not remark:
            messagebox.showwarning("提示", "驳回必须填写审核意见")
            return
        if not messagebox.askyesno("确认驳回", "确认驳回此领用单并退回领用人？"):
            return
        self._submit_action(URL_REJECT, AUDIT_REJECT_STATUS, remark, "驳回", "已驳回，退回领用人")

    def _submit_action(self, url, target_status, remark, action, ok_message):
        self.auditing = True
        payload = self.build_audit_payload(target_status, remark)
        threading.Thread(target=self._audit_action_thread,
                         args=(url, payload, action, ok_message), daemon=True).start()

    def _audit_action_thread(self, url, payload, action, ok_message):
        try:
            r = self.controller.session.post(url, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[内部领用-部门审核-{action}] 异常: {e}")
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
        bid = self.audit_id
        self.pending_rows = [r for r in self.pending_rows
                             if str(r.get('ID')) != str(bid)]
        self._render_rows()
        if self.audit_win is not None:
            try:
                self.audit_win.destroy()
            except Exception:
                pass
            self.audit_win = None

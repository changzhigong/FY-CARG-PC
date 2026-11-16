# -*- coding: utf-8 -*-
"""报销审核（报销管理模块 菜单 2/3）

对齐 fycarg-pda 安卓端 src/views/ReimbursementReview.vue：
- src/service/feeExpense.js（checkFeeExpense）
- src/config/feeExpense.js（CHECK_PASS / CHECK_REJECT）

接口：
- 待审列表 GET  /dmscloud.part/feeExpenseManager/feeExpenseManagerQueryOemInfo
              （参数 **checkType=1** = 待我审核，其余筛选字段全部为空串）
- 单据明细 GET  /dmscloud.part/feeExpenseManager/feeExpenseManagerDetailData?id=
- 审核     POST /dmscloud.part/feeExpenseManager/feeExpenseManagerCheck
- 附件下载 GET  /dmscloud.basedata/file/billFilesReview/{billType}/{fileKey}

与「报销管理（菜单1）」的关键差异：
1. 查询参数固定带 **checkType=1**（待我审核），且 created_by / 部门 / 日期 / 状态 / 单号
   全部为空串 —— 审核池由后端按当前审核人权限返回，前端不再按仓库或部门过滤。
2. 前端仅保留「待审」状态：98051002（分管审批）/ 98051003（会计核对）。
   菜单1 是拉全量后由用户筛选状态，本菜单只关心这两个待审态。
3. **无分页**：安卓端审核页直接列出全部待审单（列表通常很短），本端同样不分页。
4. 审核报文固定：typeOperator="3"、payDetailDtoList=[]、payDetailDtoListDelete=[]、
   payCheckType=0；通过 checkStatus=11241002（不传意见），驳回 checkStatus=11241003
   **且 checkRemark 必填**（安卓端 doReject 有非空校验）。
5. 审核成功后仅从本地列表移除该单并关窗，**不重新查询**（对齐安卓端 removeFromList）。
6. 附件下载走 billFilesReview（isReview=true），与菜单1 一致。

说明（与安卓端的两处有意差异，均为 PC 端安全性增强）：
- 通过 / 驳回操作前增加二次确认（安卓端无确认弹窗，直接提交）。
- 页面初始化自动查询（对齐安卓端 onMounted 的 await doQuery()）。
"""

import json
import os
import threading

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from base_page import BasePage
from tooltip_manager import tooltip_manager

from reimbursement_manage import (
    HEADERS, BASE, PART,
    URL_QUERY, URL_DETAIL, URL_ATTACH_CFG, URL_ATTACH_FILE,
    FEE_TYPE, ATTACHMENT_BILL_TYPE,
    CHECK_PASS, CHECK_REJECT,
    QUERY_LIMIT,
    FEE_LOG_TYPE_MAP,
    ReimbursementManagePage,
)

# 审核接口
URL_CHECK = BASE + PART + '/feeExpenseManagerCheck'

# 待审状态：分管审批 / 会计核对
PENDING_STATUS = ('98051002', '98051003')

# 列表列定义（对齐安卓端审核卡片字段）
COLUMNS = ["序号", "报销单号", "状态", "申请部门", "申请人", "金额", "提交日期"]
COLUMN_WIDTHS = [50, 180, 110, 140, 100, 130, 160]

# 明细列
DETAIL_COLUMNS = ["序号", "费用类型", "金额", "备注"]
DETAIL_WIDTHS = [50, 180, 120, 300]


class ReimbursementReviewPage(BasePage):
    """报销审核页面（待审单据 / 通过 / 驳回）"""

    def __init__(self, parent, controller):
        self.pending_rows = []      # 待审单据列表（已过滤）
        self.queried = False
        self.loading = False
        self.auditing = False
        self.audit_id = ''
        self.audit_win = None
        self.check_remark = None    # 审核意见输入控件（Text）
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        main = tk.Frame(self.content_frame, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_header(main)
        self.setup_data_table(main)

        # 对齐安卓端 onMounted：进入页面自动查询待审
        self.query()

    def setup_header(self, parent):
        frame = tk.LabelFrame(parent, text="待审报销单", bg="#f0f0f0",
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
        tk.Label(row, text="（仅显示，审核池不按仓库过滤）", bg="#f0f0f0",
                 fg="#969799").pack(side=tk.LEFT, padx=5)

        self.stat_var = tk.StringVar(value="待我审核：-")
        tk.Label(row, textvariable=self.stat_var, bg="#f0f0f0",
                 font=("微软雅黑", 11, "bold"), fg="#07c160").pack(side=tk.LEFT, padx=20)

        tk.Button(row, text="刷新", command=self.query,
                  bg="#07c160", fg="white", padx=14, pady=3, bd=0).pack(side=tk.RIGHT, padx=5)

        tk.Label(frame, text="双击单据行打开审核", bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 9)).pack(anchor="w", padx=5)

    def setup_data_table(self, parent):
        table_frame = tk.LabelFrame(parent, text="报销单审核", bg="#f0f0f0", bd=1,
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
        return ReimbursementManagePage.format_money(val)

    @staticmethod
    def format_date(s):
        return ReimbursementManagePage.format_date(s)

    @staticmethod
    def fee_status_label(code):
        return ReimbursementManagePage.fee_status_label(code)

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
        if 0 <= idx < len(self.pending_rows):
            return self.pending_rows[idx]
        return None

    # ------------------------------------------------------------------ 查询
    def build_query_params(self):
        """待审查询参数（checkType=1，其余筛选字段恒为空串）"""
        return {
            "feeType": FEE_TYPE,
            "checkType": 1,
            "created_by": '',
            "applyDepartmentCode": '',
            "applyDepartmentName": '',
            "applyStartDate": '',
            "applyEndDate": '',
            "feeExpenseStatus": '',
            "feeExpenseBillNo": '',
            "applyName": '',
            "dealerCode": '',
            "dealerName": '',
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
        self.stat_var.set("查询中...")
        threading.Thread(target=self._query_thread, args=(params,), daemon=True).start()

    def _query_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=HEADERS, params=params)
            print(f"[报销审核] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报销审核] 请求异常: {e}")
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
        # 仅保留待审状态 98051002 / 98051003
        self.pending_rows = [r for r in rows
                             if str(r.get('feeExpenseStatus')) in PENDING_STATUS]
        self.queried = True
        self._render_rows()
        if not self.pending_rows:
            messagebox.showinfo("报销审核", "暂无待审报销单")

    def _render_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in enumerate(self.pending_rows):
            values = (
                idx + 1,
                row.get('feeExpenseBillNo') or '-',
                self.fee_status_label(row.get('feeExpenseStatus')),
                row.get('applyDepartmentName') or '-',
                row.get('applyName') or row.get('createdByName') or '-',
                self.format_money(row.get('applyAmountTotal')),
                self.format_date(row.get('applyStartAt') or row.get('createdAt')),
            )
            tags = ("odd",) if idx % 2 == 1 else ()
            self.tree.insert("", "end", values=values, tags=tags)
        self.stat_var.set("待我审核：{} 单".format(len(self.pending_rows)))

    # ------------------------------------------------------------------ 审核
    def open_audit(self):
        row = self._selected_row()
        if not row:
            messagebox.showinfo("提示", "请先选择一条待审报销单")
            return
        bill_id = row.get('id')
        if bill_id is None:
            messagebox.showwarning("提示", "该行缺少单据 id，无法审核")
            return
        self.audit_id = str(bill_id)
        threading.Thread(target=self._audit_thread, args=(bill_id, row), daemon=True).start()

    def _audit_thread(self, bill_id, row):
        try:
            r = self.controller.session.get(URL_DETAIL, headers=HEADERS, params={'id': bill_id})
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报销审核-明细] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"加载单据失败: {e}"))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or "加载失败"
            self.controller.after(0, lambda: messagebox.showerror("明细", str(msg)))
            return
        d = data.get("data") or {}
        payload = {
            'id': str(bill_id),
            'billNo': row.get('feeExpenseBillNo') or '',
            'statusCode': str(row.get('feeExpenseStatus') or ''),
            'deptName': row.get('applyDepartmentName') or '',
            'applyName': row.get('applyName') or row.get('createdByName') or '',
            'amountTotal': row.get('applyAmountTotal') or 0,
            'remark': d.get('remark') or row.get('remark') or '',
            'details': d.get('detailDtoList') if isinstance(d.get('detailDtoList'), list) else [],
            'attachments': d.get('attachmentDtoList') if isinstance(d.get('attachmentDtoList'), list) else [],
            'logs': d.get('logList') if isinstance(d.get('logList'), list) else [],
        }
        self.controller.after(0, lambda: self._show_audit_window(payload))

    def _show_audit_window(self, p):
        win = tk.Toplevel(self)
        win.title(f"报销单审核 - {p['billNo'] or p['id']}")
        win.geometry("760x720")
        win.transient(self)
        self.audit_win = win

        head = tk.Frame(win, bg="#f7f8fa")
        head.pack(fill=tk.X)
        tk.Label(head, text="报销单审核", bg="#f7f8fa", fg="#07c160",
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(head, text=f"状态：{self.fee_status_label(p['statusCode'])}",
                 bg="#f7f8fa", fg="#ee0a24", font=("微软雅黑", 11)).pack(side=tk.RIGHT, padx=12)

        # 基本信息（只读）
        info = tk.LabelFrame(win, text="基本信息", bg="#f0f0f0", font=("微软雅黑", 10, "bold"))
        info.pack(fill=tk.X, padx=10, pady=5, ipadx=6, ipady=4)
        for key, val in (("单号", p['billNo'] or '-'),
                         ("申请部门", p['deptName'] or '-'),
                         ("申请人", p['applyName'] or '-'),
                         ("金额", self.format_money(p['amountTotal'])),
                         ("备注", p['remark'] or '无')):
            line = tk.Frame(info, bg="#f0f0f0")
            line.pack(fill=tk.X, pady=1)
            tk.Label(line, text=key + "：", bg="#f0f0f0", fg="#969799",
                     font=("微软雅黑", 10), width=9, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=str(val), bg="#f0f0f0", font=("微软雅黑", 10),
                     anchor="w", wraplength=600, justify="left").pack(side=tk.LEFT, fill=tk.X)

        # 费用明细
        tk.Label(win, text=f"费用明细（{len(p['details'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
        dframe = tk.Frame(win)
        dframe.pack(fill=tk.BOTH, expand=True, padx=10)
        dtree = ttk.Treeview(dframe, columns=DETAIL_COLUMNS, show="headings", height=5)
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

        # 附件
        tk.Label(win, text=f"附件（{len(p['attachments'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
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

        # 操作日志（审核页默认展开，不折叠）
        tk.Label(win, text=f"操作日志（{len(p['logs'])}）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
        lframe = tk.Frame(win, bg="#ffffff", height=70)
        lframe.pack(fill=tk.X, padx=10)
        if not p['logs']:
            tk.Label(lframe, text="无日志", bg="#ffffff", fg="#c8c9cc").pack(anchor="w")
        for log in p['logs']:
            text = "[{}] {} {} {}".format(
                self.fee_log_label(log.get('feeOperatorType')),
                log.get('feeOperatorBy') or '',
                self.format_date(log.get('createdAt')),
                ('（%s）' % log['operatorRemark']) if log.get('operatorRemark') else '')
            tk.Label(lframe, text=text, bg="#ffffff", anchor="w",
                     font=("微软雅黑", 9), fg="#646566").pack(fill=tk.X)

        # 审核意见
        tk.Label(win, text="审核意见（驳回时必填）", bg="#f0f0f0",
                 font=("微软雅黑", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(6, 2))
        self.check_remark = tk.Text(win, height=4, font=("微软雅黑", 10))
        self.check_remark.pack(fill=tk.X, padx=10)

        # 操作按钮
        bar = tk.Frame(win, bg="#f0f0f0")
        bar.pack(fill=tk.X, pady=10)
        tk.Button(bar, text="通过", command=self.do_pass,
                  bg="#07c160", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="驳回", command=self.do_reject,
                  bg="#ee0a24", fg="white", padx=20, pady=5, bd=0).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="关闭", command=win.destroy,
                  bg="#e1e1e1", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.RIGHT, padx=10)

    def build_check_payload(self, check_status, remark=None):
        """审核报文（对齐安卓端 doPass / doReject 的 HAR 实测结构）"""
        payload = {
            'id': int(self.audit_id) if str(self.audit_id).isdigit() else self.audit_id,
            'checkStatus': check_status,
            'typeOperator': "3",
            'payDetailDtoList': [],
            'payDetailDtoListDelete': [],
            'payCheckType': 0,
        }
        # 通过不传意见；驳回必须带 checkRemark
        if remark:
            payload['checkRemark'] = remark
        return payload

    def do_pass(self):
        if self.auditing:
            return
        if not messagebox.askyesno("确认通过", "确认审核通过该报销单？"):
            return
        self._submit(CHECK_PASS, None, "通过")

    def do_reject(self):
        if self.auditing:
            return
        remark = self.check_remark.get("1.0", "end").strip() if self.check_remark else ''
        if not remark:
            messagebox.showwarning("提示", "驳回必须填写审核意见")
            return
        if not messagebox.askyesno("确认驳回", "确认驳回该报销单并退回申请人？"):
            return
        self._submit(CHECK_REJECT, remark, "驳回")

    def _submit(self, check_status, remark, action):
        self.auditing = True
        payload = self.build_check_payload(check_status, remark)
        threading.Thread(target=self._check_thread, args=(payload, action), daemon=True).start()

    def _check_thread(self, payload, action):
        try:
            r = self.controller.session.post(URL_CHECK, headers=HEADERS, json=payload)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[报销审核-提交] 异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"{action}失败: {e}"))
            self.controller.after(0, lambda: setattr(self, 'auditing', False))
            return
        if not (data.get("resultCode") == 200 or data.get("success")):
            msg = data.get("errMsg") or data.get("msg") or f"{action}失败"
            self.controller.after(0, lambda: messagebox.showerror("审核失败", str(msg)))
            self.controller.after(0, lambda: setattr(self, 'auditing', False))
            return
        self.controller.after(0, lambda: self._after_checked(payload.get('id'), action))

    def _after_checked(self, bill_id, action):
        self.auditing = False
        messagebox.showinfo("成功", "已审核通过" if action == "通过" else "已驳回，退回申请人")
        # 对齐安卓端 removeFromList：仅本地移除，不重新查询
        self.remove_from_list(bill_id)
        if self.audit_win and self.audit_win.winfo_exists():
            self.audit_win.destroy()
            self.audit_win = None

    def remove_from_list(self, bill_id):
        self.pending_rows = [r for r in self.pending_rows
                             if str(r.get('id')) != str(bill_id)]
        self._render_rows()

    # ------------------------------------------------------------------ 附件
    def download_attachment(self, attach):
        """下载附件（审核页走 billFilesReview）"""
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
        file_url = ''
        if bill_id:
            try:
                r = self.controller.session.get(
                    '{}/{}/{}'.format(URL_ATTACH_CFG, ATTACHMENT_BILL_TYPE, bill_id),
                    headers=HEADERS)
                if self._check_response(r):
                    data = json.loads(r.text)
                    previews = ((data.get('data') or {}).get('initialPreview') or [])
                    if previews:
                        file_url = previews[0]
            except Exception as e:
                print(f"[报销审核-附件配置] 失败: {e}")
        if not file_url and file_key:
            # 审核页回退固定用 billFilesReview（isReview=true）
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
            print(f"[报销审核-附件下载] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror("下载失败", str(e)))
            return
        self.controller.after(0, lambda: messagebox.showinfo("完成", f"附件已保存到：\n{path}"))

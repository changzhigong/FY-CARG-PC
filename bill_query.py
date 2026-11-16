# -*- coding: utf-8 -*-
"""账单查询

对齐 fycarg-pda 安卓端 src/views/BillQuery.vue，接口与业务逻辑保持一致：

- 列表：GET /dmscloud.part/partBill/partBillQueryOemInfo
- 汇总：GET /dmscloud.part/partBill/getBillTotalData（与列表并发请求）

与前面两个模块的差异：
1. 请求需额外携带 tenantCode: 10770000 请求头（安卓端 axios 显式传入）。
2. 查询条件只有「日期（单日）」，仓库为当前仓库；PC 端提供仓库下拉便于切换。
3. 一次取全量（pageNum=1, limit=2000），无分页；结果按拣货单号升序排序，
   无拣货单号的排在最前面。
4. 含 8 张字典码表映射（结算方式 / 物流方式 / 资金类型 / 客户类型 /
   账单类型 / 订单类型 / 开票状态 / 核销状态）。
5. 支持导出 Excel（12 列精简版 + 合计行），文件名「{仓库名}{日期}.xlsx」。
"""

import json
import os
import threading
from datetime import date
from functools import cmp_to_key

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from base_page import BasePage
from tooltip_manager import tooltip_manager

# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

# 账单接口需额外携带 tenantCode（对齐安卓端 axios headers）
BILL_HEADERS = dict(HEADERS, tenantCode='10770000')

URL_QUERY = 'https://xb.fy-carg.com/dmscloud.part/partBill/partBillQueryOemInfo'
URL_TOTAL = 'https://xb.fy-carg.com/dmscloud.part/partBill/getBillTotalData'

# 一次取全量（安卓端 limit=2000）
PAGE_SIZE = 2000

# ── 字典码表（对齐安卓端 const MAP）──
SETT_MAP = {          # 结算方式 type:4622
    '46221001': '现结', '46221002': '月结',
    '46221003': '挂账', '46221004': '到付',
}
LOGISTICS_MAP = {     # 物流方式 type:4617
    '46171001': '送货', '46171002': '物流代收', '46171003': '物流发货',
    '46171004': '自提', '46171005': '快递',
}
FUND_TYPE_MAP = {     # 资金类型 type:1195
    '11951001': '额度', '11951002': '挂账', '11951003': '现金',
}
ORG_TYPE_MAP = {      # 客户类型 type:1247
    '12471001': '客户', '12471002': '服务站', '12471003': '供应商',
    '12471004': '物流公司', '12471005': '保险公司', '12471006': '其他',
}
BILL_TYPE_MAP = {     # 账单类型 type:7012
    '70121001': '备件销售退货', '70121002': '备件销售',
    '70121003': '备件销售退货(含税)', '70121004': '备件销售出库',
}
ORDER_TYPE_MAP = {    # 订单类型 type:1710
    '17101001': '普通订单', '17101002': '紧急订单',
}
INVOICE_STATUS_MAP = {  # 开票状态 type:1258
    '12581001': '未开票', '12581002': '已开票', '12581003': '部分开票',
}
WRITEOFF_MAP = {      # 核销状态 type:7014
    '70141001': '未核销', '70141002': '部分核销', '70141003': '已核销',
}

# 列表列定义（对齐安卓端表头，28 列）
COLUMNS = ["序号", "客户代码", "客户名称", "交易仓库", "客户类型", "门店订单号",
           "账单号", "发货单号", "账单生成日期", "资金类型", "不含税金额", "税率",
           "税额", "含税金额", "账单类型", "订单类型", "退货账单", "开票状态",
           "核销状态", "结算方式", "物流单号", "拣货单号", "发票号", "电子发票",
           "开票日期", "物流方式", "订单制单人", "账单到期日"]
COLUMN_WIDTHS = [50, 110, 200, 90, 80, 150, 170, 170, 150, 80, 100, 60, 90, 100,
                 130, 90, 80, 80, 80, 80, 140, 160, 120, 70, 110, 90, 100, 110]

# 导出列定义（12 列精简版，对齐安卓端 doExport）
EXPORT_HEADERS = ["序号", "客户代码", "客户名称", "账单号", "账单生成日期", "资金类型",
                  "含税金额", "账单类型", "是否退货账单", "拣货单号", "物流方式", "订单制单人"]
EXPORT_WIDTHS = [6, 10, 22, 22, 14, 10, 14, 14, 12, 22, 10, 10]


class BillQueryPage(BasePage):
    """账单查询页面"""

    def __init__(self, parent, controller):
        self.rows = []            # 账单列表（原始 dict，已排序）
        self.summary = None       # 汇总：n1 不含税 / n2 税额 / n3 含税
        self.queried = False
        self.loading = False
        self.exporting = False
        super().__init__(parent, controller)

    # ------------------------------------------------------------------ 界面
    def create_widgets(self):
        """构建用户界面"""
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_filter_panel(main_container)
        self.setup_summary_bar(main_container)
        self.setup_data_table(main_container)
        self.setup_count_bar(main_container)

    def setup_filter_panel(self, parent):
        """构建查询条件面板"""
        filter_frame = tk.LabelFrame(parent, text="查询条件", bg="#f0f0f0",
                                     font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)

        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5,
                     "bd": 0, "activebackground": "#45a049"}

        # 日期（单日，默认今天 —— 安卓端 todayStr）
        tk.Label(row1, text="日期:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.date_cal = DateEntry(row1, width=12, date_pattern='yyyy-mm-dd')
        self.date_cal.set_date(date.today())
        self.date_cal.pack(side=tk.LEFT, padx=5)

        # 仓库（安卓端为当前登录仓库，PC 端提供下拉便于切换）
        tk.Label(row1, text="仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(15, 5))
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                         values=warehouses, state="readonly", width=10)
        self.warehouse_cb.set(warehouses[0] if warehouses else "")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)

        self.query_btn = tk.Button(row1, text="查询账单", command=self.query, **btn_style)
        self.query_btn.pack(side=tk.LEFT, padx=(15, 5))

        self.export_btn = tk.Button(row1, text="导出 Excel", command=self.export_excel,
                                    bg="#67c23a", fg="white", padx=10, pady=5, bd=0,
                                    activebackground="#5daf34", state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)

    def setup_summary_bar(self, parent):
        """汇总条：不含税合计 / 税额 / 含税合计"""
        self.summary_var = tk.StringVar(value="")
        self.summary_frame = tk.Frame(parent, bg="#f0f9eb")
        tk.Label(self.summary_frame, textvariable=self.summary_var, bg="#f0f9eb",
                 fg="#333333", font=("微软雅黑", 10)).pack(padx=10, pady=6)

    def setup_data_table(self, parent):
        """构建账单表格"""
        table_frame = tk.LabelFrame(parent, text="账单明细", bg="#f0f0f0", bd=1,
                                    relief=tk.SOLID, font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col, width in zip(COLUMNS, COLUMN_WIDTHS):
            self.tree.heading(col, text=col)
            anchor = "w" if col in ("客户名称", "门店订单号", "账单号", "发货单号",
                                    "订单制单人") else "center"
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.tag_configure("odd", background="#fafafa")
        # 含税金额高亮（对齐安卓端 .amount 样式）
        self.tree.tag_configure("amount", foreground="#e6a23c")
        # 拣货单号绿色（对齐安卓端 .picking-no）
        self.tree.tag_configure("picking", foreground="#07c160")

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

    def setup_count_bar(self, parent):
        """记录条数提示"""
        self.count_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.count_var, bg="#f0f0f0",
                 font=("微软雅黑", 9), fg="#666666").pack(fill=tk.X)

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def fmt_money(val):
        """金额格式化：非数字显示 '-'，否则两位小数（对齐安卓端 fmtMoney）"""
        try:
            n = float(val)
        except (TypeError, ValueError):
            return "-"
        return "%.2f" % n

    @staticmethod
    def _map_code(mapping, val):
        """通用码表映射：命中返回中文，否则原值；空值返回 '-'（对齐安卓端 mapXxx）"""
        if val is None or val == "":
            return "-"
        s = str(val)
        return mapping.get(s, s)

    @staticmethod
    def map_is_return(val):
        """是否退货账单：10041001/1/true/是 → 是，其余（含空）→ 否"""
        if val is None or val == "" or val == 0:
            return "否"
        s = str(val)
        if s in ("10041001", "1", "true", "是"):
            return "是"
        return "否"

    @staticmethod
    def sort_by_picking_no(rows):
        """按拣货单号升序，无拣货单号的排在最前面（对齐安卓端 sortByPickingNo）"""
        def cmp(a, b):
            av = str(a.get("pickingOrderNo") or "").strip()
            bv = str(b.get("pickingOrderNo") or "").strip()
            if not av and not bv:
                return 0
            if not av:
                return -1
            if not bv:
                return 1
            try:
                an, bn = float(av), float(bv)
                return (an > bn) - (an < bn)
            except ValueError:
                return (av > bv) - (av < bv)
        return sorted(rows, key=cmp_to_key(cmp))

    def _check_response(self, response):
        """检查响应中的登录状态"""
        return not self.controller.check_login_status(response)

    def build_params(self):
        """构造查询参数（对齐安卓端 doQuery 的 params）"""
        warehouse_name = self.warehouse_var.get()
        warehouse_id = self.controller.options.get(warehouse_name, "")
        day = self.date_cal.get() or ""
        return {
            "generationstartdate": day,
            "generationenddate": day,
            "warehouseName": warehouse_name,
            "warehouseId": warehouse_id,
            "isLogisticsPartBill": "10041002",
            "pageNum": 1,
            "limit": PAGE_SIZE,
            "sort": "",
            "order": "",
            "searchLoading": "false",
        }

    # ------------------------------------------------------------------ 查询
    def query(self):
        """执行查询（列表 + 汇总并发，对齐安卓端 Promise.all）"""
        if self.loading:
            return
        if not self.date_cal.get():
            messagebox.showwarning("提示", "请选择日期")
            return

        params = self.build_params()
        self.loading = True
        self.queried = False
        self.rows = []
        self.summary = None
        self.count_var.set("查询中...")
        self.export_btn.config(state=tk.DISABLED)
        self.summary_frame.pack_forget()

        threading.Thread(target=self._query_list_thread, args=(params,), daemon=True).start()
        threading.Thread(target=self._query_total_thread, args=(params,), daemon=True).start()

    def _query_list_thread(self, params):
        try:
            r = self.controller.session.get(URL_QUERY, headers=BILL_HEADERS, params=params)
            print(f"[账单查询-列表] {r.url}")
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[账单查询-列表] 请求异常: {e}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"查询异常，请检查网络: {e}"))
            self.controller.after(0, lambda: self.count_var.set(""))
            return
        finally:
            self.loading = False

        if not (data.get("resultCode") == 200 or data.get("code") == 200):
            msg = data.get("errMsg") or data.get("msg") or "查询失败"
            self.controller.after(0, lambda: messagebox.showerror("查询失败", str(msg)))
            self.controller.after(0, lambda: self.count_var.set(""))
            return

        d = data.get("data") or {}
        raw_rows = d.get("rows") or d.get("records") or d.get("list") or []
        if raw_rows:
            print("[账单查询] API返回字段名:", list(raw_rows[0].keys()))
        rows = self.sort_by_picking_no(raw_rows)
        self.controller.after(0, lambda: self._render_rows(rows))

    def _query_total_thread(self, params):
        try:
            r = self.controller.session.get(URL_TOTAL, headers=BILL_HEADERS, params=params)
            if not self._check_response(r):
                return
            data = json.loads(r.text)
        except Exception as e:
            print(f"[账单查询-汇总] 请求异常: {e}")
            return

        if not (data.get("resultCode") == 200 or data.get("code") == 200):
            return

        d = data.get("data") or {}
        self.controller.after(0, lambda: self._render_summary(d))

    def _render_rows(self, rows):
        """渲染列表（主线程）"""
        self.rows = rows
        self.queried = True

        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, row in enumerate(rows):
            values = (
                idx + 1,
                row.get("dealerCode") or "-",
                row.get("dealerName") or "-",
                row.get("warehouseName") or self.warehouse_var.get() or "-",
                self._map_code(ORG_TYPE_MAP, row.get("orgType")),
                row.get("businessNo") or "-",
                row.get("billNo") or "-",
                row.get("deliveryNo") or "-",
                row.get("createdAt") or "-",
                self._map_code(FUND_TYPE_MAP, row.get("fundsType")),
                self.fmt_money(row.get("noTaxAmount")),
                "-" if row.get("taxRate") is None else row.get("taxRate"),
                self.fmt_money(row.get("taxAmount")),
                self.fmt_money(row.get("inTaxAmount")),
                self._map_code(BILL_TYPE_MAP, row.get("billType")),
                self._map_code(ORDER_TYPE_MAP, row.get("salesOrderType")),
                self.map_is_return(row.get("isReturn")),
                self._map_code(INVOICE_STATUS_MAP, row.get("gtcInvoiceStatus")),
                self._map_code(WRITEOFF_MAP, row.get("writeoffStatus")),
                self._map_code(SETT_MAP, row.get("settMethod")),
                row.get("logisticsNo") or "",
                row.get("pickingOrderNo") or "-",
                row.get("invoiceNo") or "",
                "查看" if row.get("invoiceUrl") else "",
                row.get("invoiceDate") or "",
                self._map_code(LOGISTICS_MAP, row.get("logistics_mode")),
                row.get("created_by_name") or "-",
                row.get("expireDate") or "-",
            )
            tags = ["odd"] if idx % 2 == 1 else []
            self.tree.insert("", "end", values=values, tags=tuple(tags))

        self.count_var.set(f"共 {len(rows)} 条账单记录")
        if rows:
            self.export_btn.config(state=tk.NORMAL)
        if not rows:
            messagebox.showinfo("查询结果", "当日无账单数据")

    def _render_summary(self, data):
        """渲染汇总条"""
        n1 = float(data.get("n1") or 0)
        n2 = float(data.get("n2") or 0)
        n3 = float(data.get("n3") or 0)
        self.summary = {"n1": "%.2f" % n1, "n2": "%.2f" % n2, "n3": "%.2f" % n3}
        self.summary_var.set(
            f"不含税合计: ¥{self.summary['n1']}   |   税额: ¥{self.summary['n2']}   |   含税合计: ¥{self.summary['n3']}")
        self.summary_frame.pack(fill=tk.X, pady=(0, 5))

    # ------------------------------------------------------------------ 导出
    def export_excel(self):
        """导出 Excel（12 列精简版 + 合计行，对齐安卓端 doExport）"""
        if not self.rows or self.exporting:
            return

        warehouse_name = self.warehouse_var.get()
        default_name = f"{warehouse_name}{self.date_cal.get()}.xlsx".replace("/", "_")
        path = filedialog.asksaveasfilename(
            title="导出账单 Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
        if not path:
            return

        self.exporting = True
        self.export_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._export_thread, args=(path,), daemon=True).start()

    def _export_thread(self, path):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "账单数据"
            ws.freeze_panes = "A2"   # 冻结表头（对齐安卓端 views frozen ySplit:1）

            thin = Side(style="thin")
            medium = Side(style="medium")
            thin_border = Border(top=thin, left=thin, bottom=thin, right=thin)

            ws.append(EXPORT_HEADERS)
            ws.row_dimensions[1].height = 24
            for idx, width in enumerate(EXPORT_WIDTHS, 1):
                ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = width
            header_row = ws[1]
            for cell in header_row:
                cell.font = Font(bold=True, size=11, color="FFFFFFFF")
                cell.fill = PatternFill("solid", fgColor="FF409EFF")
                cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
                cell.border = Border(top=thin, left=thin, bottom=medium, right=thin)

            for i, r in enumerate(self.rows, 1):
                ws.append([
                    i,
                    r.get("dealerCode") or "",
                    r.get("dealerName") or "",
                    r.get("billNo") or "",
                    r.get("createdAt") or "",
                    self._map_code(FUND_TYPE_MAP, r.get("fundsType")),
                    float(r.get("inTaxAmount") or 0),
                    self._map_code(BILL_TYPE_MAP, r.get("billType")),
                    self.map_is_return(r.get("isReturn")),
                    r.get("pickingOrderNo") or "",
                    self._map_code(LOGISTICS_MAP, r.get("logistics_mode")),
                    r.get("created_by_name") or "",
                ])
                row = ws[ws.max_row]
                ws.cell(row=ws.max_row, column=7).number_format = "#,##0.00"   # 第 7 列含税金额
                for cell in row:
                    cell.border = thin_border

            # 合计行
            if self.summary:
                ws.append(["合计", "", "", "", "", "", float(self.summary["n3"] or 0),
                           "", "", "", "", ""])
                sum_row = ws[ws.max_row]
                for cell in sum_row:
                    cell.font = Font(bold=True, size=11)
                    cell.fill = PatternFill("solid", fgColor="FFFFF7E6")
                    cell.border = Border(top=medium, left=thin, bottom=medium, right=thin)
                ws.cell(row=ws.max_row, column=7).number_format = "#,##0.00"

            wb.save(path)
            self.controller.after(0, lambda: messagebox.showinfo(
                "导出成功", f"文件已保存:\n{path}"))
        except Exception as e:
            print(f"[账单导出] 失败: {e}")
            self.controller.after(0, lambda: messagebox.showerror(
                "导出失败", f"{e}"))
        finally:
            self.exporting = False
            self.controller.after(0, lambda: self.export_btn.config(state=tk.NORMAL))

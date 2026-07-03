import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import os
import json
import threading
from datetime import datetime
from base_page import BasePage

# ── 结算方式映射（type:4622）──
SETT_MAP = {'46221001': '现结', '46221002': '月结', '46221003': '挂账', '46221004': '到付'}
# ── 物流方式映射（type:4617）──
LOGISTICS_MAP = {'46171001': '送货', '46171002': '物流代收', '46171003': '物流发货', '46171004': '自提', '46171005': '快递'}
# ── 资金类型映射（type:1195）──
FUND_TYPE_MAP = {'11951001': '额度', '11951002': '挂账', '11951003': '现金'}
# ── 客户类型映射（type:1247）──
ORG_TYPE_MAP = {'12471001': '客户', '12471002': '服务站', '12471003': '供应商', '12471004': '物流公司', '12471005': '保险公司', '12471006': '其他'}
# ── 账单类型映射（type:7012）──
BILL_TYPE_MAP = {'70121001': '备件销售退货', '70121002': '备件销售', '70121003': '备件销售退货(含税)', '70121004': '备件销售出库'}
# ── 订单类型映射（type:1710）──
ORDER_TYPE_MAP = {'17101001': '普通订单', '17101002': '紧急订单'}
# ── 开票状态映射（type:1258）──
INVOICE_STATUS_MAP = {'12581001': '未开票', '12581002': '已开票', '12581003': '部分开票'}
# ── 核销状态映射（type:7014）──
WRITEOFF_MAP = {'70141001': '未核销', '70141002': '部分核销', '70141003': '已核销'}


def fmt_money(val):
    """金额格式化，保留两位小数"""
    try:
        n = float(val)
        return f"{n:.2f}"
    except (ValueError, TypeError):
        return "-"


def map_settlement(val):
    return SETT_MAP.get(str(val), val or "-")


def map_logistics(val):
    return LOGISTICS_MAP.get(str(val), val or "-")


def map_fund_type(val):
    if not val and val != 0:
        return "-"
    return FUND_TYPE_MAP.get(str(val), str(val))


def map_org_type(val):
    return ORG_TYPE_MAP.get(str(val), val or "-")


def map_bill_type(val):
    return BILL_TYPE_MAP.get(str(val), val or "-")


def map_order_type(val):
    return ORDER_TYPE_MAP.get(str(val), val or "-")


def map_invoice_status(val):
    if not val and val != 0:
        return "-"
    return INVOICE_STATUS_MAP.get(str(val), str(val))


def map_writeoff(val):
    if not val and val != 0:
        return "-"
    return WRITEOFF_MAP.get(str(val), str(val))


def map_is_return(val):
    if not val and val != 0:
        return "否"
    s = str(val)
    if s in ("10041001", "1", "true", "是"):
        return "是"
    return "否"


class ExcelDataProcessPage(BasePage):
    """财务日报页面 —— 对齐 Claw 项目账单查询功能"""

    # 28 列表格列定义（列名, 字段key, 宽度, 对齐方式）
    COLUMNS = [
        ("序号",         "seq_no",          50,  "center"),
        ("客户代码",     "dealerCode",      90,  "w"),
        ("客户名称",     "dealerName",      160, "w"),
        ("交易仓库",     "warehouseName",   100, "w"),
        ("客户类型",     "org_type_text",   80,  "center"),
        ("门店订单号",   "businessNo",      130, "w"),
        ("账单号",       "billNo",          140, "w"),
        ("发货单号",     "deliveryNo",      130, "w"),
        ("账单生成日期", "createdAt",       100, "center"),
        ("资金类型",     "fund_type_text",  70,  "center"),
        ("不含税金额",   "noTaxAmount",     100, "e"),
        ("税率",         "taxRate",         60,  "center"),
        ("税额",         "taxAmount",       100, "e"),
        ("含税金额",     "inTaxAmount",     100, "e"),
        ("账单类型",     "bill_type_text",  120, "center"),
        ("订单类型",     "order_type_text", 80,  "center"),
        ("退货账单",     "is_return_text",  70,  "center"),
        ("开票状态",     "invoice_status",  80,  "center"),
        ("核销状态",     "writeoff_status", 80,  "center"),
        ("结算方式",     "sett_method",     70,  "center"),
        ("物流单号",     "logisticsNo",     130, "w"),
        ("拣货单号",     "pickingOrderNo",  130, "w"),
        ("发票号",       "invoiceNo",       140, "w"),
        ("电子发票",     "invoiceUrl",      80,  "center"),
        ("开票日期",     "invoiceDate",     100, "center"),
        ("物流方式",     "logistics_text",  80,  "center"),
        ("订单制单人",   "created_by_name", 80,  "w"),
        ("账单到期日",   "expireDate",      100, "center"),
    ]

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller
        self.bill_data = []       # 查询结果数据
        self.summary_data = None  # 汇总数据 {n1, n2, n3}

    def create_widgets(self):
        """创建界面组件"""
        # ── 筛选区域 ──
        filter_frame = ttk.LabelFrame(self.content_frame, text="查询条件")
        filter_frame.pack(pady=5, fill="x", padx=10)

        row1 = ttk.Frame(filter_frame)
        row1.pack(pady=5, fill="x", padx=10)
        ttk.Label(row1, text="日期:").pack(side=tk.LEFT, padx=5)
        self.date_entry = DateEntry(row1, date_pattern='yyyy-mm-dd')
        self.date_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="仓库:").pack(side=tk.LEFT, padx=(15, 5))
        self.warehouse_combo = ttk.Combobox(row1, values=list(self.controller.options.keys()), width=12)
        self.warehouse_combo.current(0)
        self.warehouse_combo.pack(side=tk.LEFT, padx=5)

        # 按钮行
        btn_row = ttk.Frame(row1)
        btn_row.pack(side=tk.LEFT, padx=(15, 0))
        ttk.Button(btn_row, text="查询账单", command=self._do_query).pack(side=tk.LEFT, padx=3)
        self.export_btn = ttk.Button(btn_row, text="导出 Excel", command=self._do_export, state="disabled")
        self.export_btn.pack(side=tk.LEFT, padx=3)

        # ── 汇总区域 ──
        self.summary_frame = ttk.LabelFrame(self.content_frame, text="汇总统计")
        self.summary_frame.pack(pady=3, fill="x", padx=10)
        self.summary_labels = {}
        for label, key in [("不含税合计:", "n1"), ("税额合计:", "n2"), ("含税合计:", "n3")]:
            f = ttk.Frame(self.summary_frame)
            f.pack(side=tk.LEFT, padx=15, pady=3)
            ttk.Label(f, text=label, font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
            var = tk.StringVar(value="-")
            ttk.Label(f, textvariable=var, font=("微软雅黑", 10), foreground="#e6a23c").pack(side=tk.LEFT)
            self.summary_labels[key] = var

        # ── 表格区域 ──
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(pady=5, fill="both", expand=True, padx=5)

        # TreeView（只显示关键列作为ID列）
        self.tree = ttk.Treeview(table_frame, columns=[c[1] for c in self.COLUMNS], show="headings", selectmode="browse")
        for col_def in self.COLUMNS:
            col_key = col_def[1]
            col_name = col_def[0]
            col_width = col_def[2]
            col_anchor = col_def[3]
            self.tree.heading(col_key, text=col_name)
            self.tree.column(col_key, width=col_width, anchor=col_anchor, minwidth=40)

        # 滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill="both", expand=True)

        # ── 计数状态行 ──
        self.count_var = tk.StringVar(value="共 0 条账单记录")
        ttk.Label(self.content_frame, textvariable=self.count_var, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X, padx=10)

        # ── 状态栏 ──
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.content_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def _do_query(self):
        """查询账单数据（对齐 Claw 项目 doQuery）"""
        warehouse_name = self.warehouse_combo.get()
        warehouse_id = self.controller.options.get(warehouse_name, "")
        date = self.date_entry.get()

        if not date:
            messagebox.showwarning("警告", "请选择日期")
            return

        # 在新线程中执行，避免界面冻结
        self.status_var.set("正在查询...")
        self.export_btn.configure(state="disabled")
        threading.Thread(target=self._query_thread, args=(warehouse_id, warehouse_name, date), daemon=True).start()

    def _query_thread(self, warehouse_id, warehouse_name, date):
        """后台线程执行查询"""
        try:
            params = {
                "generationstartdate": date,
                "generationenddate": date,
                "warehouseName": warehouse_name,
                "warehouseId": str(warehouse_id) if warehouse_id else "",
                "isLogisticsPartBill": "10041002",
                "pageNum": 1,
                "limit": 2000,
                "sort": "",
                "order": "",
                "searchLoading": "false",
            }

            headers = {
                **self.controller.session.headers,
                "tenantCode": "10770000",
            }

            # 并发查询：账单列表 + 汇总数据
            list_url = "https://xb.fy-carg.com/dmscloud.part/partBill/partBillQueryOemInfo"
            total_url = "https://xb.fy-carg.com/dmscloud.part/partBill/getBillTotalData"

            list_res = self.controller.session.get(list_url, params=params, headers=headers)
            total_res = self.controller.session.get(total_url, params=params, headers=headers)

            # 检查登录状态
            if not hasattr(self.controller, '_check_response') or self.controller._check_response(list_res):
                list_json = list_res.json()
                total_json = total_res.json()

                list_data = list_json.get("data", {}) if list_json.get("resultCode") == 200 or list_json.get("code") == 200 else {}
                raw_rows = list_data.get("rows") or list_data.get("records") or list_data.get("list") or []

                total_data = total_json.get("data", {}) if total_json.get("resultCode") == 200 or total_json.get("code") == 200 else {}

                # 在主线程更新 UI
                self.controller.after(0, lambda: self._update_table(raw_rows, total_data, warehouse_name))
            else:
                self.controller.after(0, lambda: self.status_var.set("登录已过期，请重新登录"))

        except Exception as e:
            self.controller.after(0, lambda: self._query_error(str(e)))

    def _update_table(self, raw_rows, total_data, warehouse_name):
        """更新表格和汇总（主线程）"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.bill_data = []
        self.summary_data = None

        if not raw_rows:
            self.status_var.set("当日无账单数据")
            self.count_var.set("共 0 条账单记录")
            self.export_btn.configure(state="disabled")
            # 清空汇总
            for k in self.summary_labels:
                self.summary_labels[k].set("-")
            return

        # 填充数据行
        for idx, r in enumerate(raw_rows):
            row_values = (
                idx + 1,                                   # 序号
                r.get("dealerCode", "-"),                  # 客户代码
                r.get("dealerName", "-"),                  # 客户名称
                r.get("warehouseName", warehouse_name),    # 交易仓库
                map_org_type(r.get("orgType")),            # 客户类型
                r.get("businessNo", "-"),                  # 门店订单号
                r.get("billNo", "-"),                      # 账单号
                r.get("deliveryNo", "-"),                  # 发货单号
                r.get("createdAt", "-"),                   # 账单生成日期
                map_fund_type(r.get("fundsType")),         # 资金类型
                fmt_money(r.get("noTaxAmount", 0)),        # 不含税金额
                r.get("taxRate", "-"),                     # 税率
                fmt_money(r.get("taxAmount", 0)),          # 税额
                fmt_money(r.get("inTaxAmount", 0)),        # 含税金额
                map_bill_type(r.get("billType")),          # 账单类型
                map_order_type(r.get("salesOrderType")),   # 订单类型
                map_is_return(r.get("isReturn")),          # 退货账单
                map_invoice_status(r.get("gtcInvoiceStatus")), # 开票状态
                map_writeoff(r.get("writeoffStatus")),     # 核销状态
                map_settlement(r.get("settMethod")),       # 结算方式
                r.get("logisticsNo", "") or "-",           # 物流单号
                r.get("pickingOrderNo", "-"),              # 拣货单号
                r.get("invoiceNo", "") or "-",             # 发票号
                "查看" if r.get("invoiceUrl") else "-",    # 电子发票
                r.get("invoiceDate", "") or "-",           # 开票日期
                map_logistics(r.get("logistics_mode")),    # 物流方式
                r.get("created_by_name", "-"),             # 订单制单人
                r.get("expireDate", "-"),                  # 账单到期日
            )
            self.tree.insert("", tk.END, values=row_values)
            self.bill_data.append(r)

        # 更新汇总
        if total_data:
            self.summary_data = {
                "n1": fmt_money(total_data.get("n1", 0)),
                "n2": fmt_money(total_data.get("n2", 0)),
                "n3": fmt_money(total_data.get("n3", 0)),
            }
            for k in self.summary_labels:
                self.summary_labels[k].set(self.summary_data.get(k, "-"))
        else:
            for k in self.summary_labels:
                self.summary_labels[k].set("-")

        self.count_var.set(f"共 {len(raw_rows)} 条账单记录")
        self.status_var.set("查询完成")
        self.export_btn.configure(state="normal")

    def _query_error(self, msg):
        """查询出错处理"""
        self.status_var.set(f"查询失败: {msg}")
        self.export_btn.configure(state="disabled")
        messagebox.showerror("查询失败", f"查询账单失败:\n{msg}")

    def _do_export(self):
        """导出 Excel 到桌面（对齐 Claw 项目 doExport）"""
        if not self.bill_data:
            messagebox.showwarning("警告", "没有可导出的数据，请先查询")
            return

        try:
            warehouse_name = self.warehouse_combo.get()
            date = self.date_entry.get()

            # 桌面路径
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = warehouse_name.replace("/", "_").replace("\\", "_").replace(":", "_")
            file_name = f"{safe_name}{date}.xlsx"
            file_path = os.path.join(desktop, file_name)

            self.status_var.set("正在导出 Excel...")
            self.update()

            # 在新线程中执行导出，避免界面冻结
            threading.Thread(
                target=self._export_thread,
                args=(file_path, warehouse_name, date),
                daemon=True
            ).start()

        except Exception as e:
            self.status_var.set(f"导出失败: {str(e)}")
            messagebox.showerror("错误", f"导出 Excel 失败:\n{str(e)}")

    def _export_thread(self, file_path, warehouse_name, date):
        """后台线程执行 Excel 导出"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import (
                Border, Side, PatternFill, Font, Alignment, numbers
            )
            from openpyxl.utils import get_column_letter

            wb = Workbook()
            ws = wb.active
            ws.title = "账单数据"

            # ── 导出列定义（12列精简版，对齐 Claw）──
            export_cols = [
                ("序号",         6,  "center"),
                ("客户代码",     10, "left"),
                ("客户名称",     22, "left"),
                ("账单号",       22, "left"),
                ("账单生成日期", 14, "center"),
                ("资金类型",     10, "center"),
                ("含税金额",     14, "right"),
                ("账单类型",     14, "center"),
                ("是否退货账单", 12, "center"),
                ("拣货单号",     22, "left"),
                ("物流方式",     10, "center"),
                ("订单制单人",   10, "left"),
            ]

            # 表头样式
            header_fill = PatternFill(start_color="409EFF", end_color="409EFF", fill_type="solid")
            header_font = Font(bold=True, size=11, color="FFFFFF", name="微软雅黑")
            header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
            thin_border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin")
            )
            medium_bottom = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="medium")
            )

            # 写入表头
            for ci, (col_name, col_width, col_align) in enumerate(export_cols, 1):
                cell = ws.cell(row=1, column=ci, value=col_name)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = medium_bottom
                ws.column_dimensions[get_column_letter(ci)].width = col_width

            ws.row_dimensions[1].height = 24

            # 写入数据行
            row_num = 2
            for i, r in enumerate(self.bill_data):
                values = [
                    i + 1,
                    r.get("dealerCode", ""),
                    r.get("dealerName", ""),
                    r.get("billNo", ""),
                    r.get("createdAt", ""),
                    map_fund_type(r.get("fundsType")),
                    float(r.get("inTaxAmount", 0) or 0),
                    map_bill_type(r.get("billType")),
                    map_is_return(r.get("isReturn")),
                    r.get("pickingOrderNo", ""),
                    map_logistics(r.get("logistics_mode")),
                    r.get("created_by_name", ""),
                ]
                for ci, val in enumerate(values, 1):
                    cell = ws.cell(row=row_num, column=ci, value=val)
                    cell.border = thin_border
                    if ci == 7:  # 含税金额列
                        cell.number_format = '#,##0.00'
                row_num += 1

            # 汇总行
            if self.summary_data:
                sum_fill = PatternFill(start_color="FFF7E6", end_color="FFF7E6", fill_type="solid")
                sum_font = Font(bold=True, name="微软雅黑")
                # 合计标签
                cell = ws.cell(row=row_num, column=1, value="合计")
                cell.font = sum_font; cell.fill = sum_fill; cell.border = thin_border
                for ci in range(2, 7):
                    c = ws.cell(row=row_num, column=ci, value="")
                    c.fill = sum_fill; c.border = thin_border
                # 含税金额汇总
                cell = ws.cell(row=row_num, column=7, value=float(self.summary_data.get("n3", 0)))
                cell.font = sum_font; cell.fill = sum_fill; cell.border = thin_border
                cell.number_format = '#,##0.00'
                for ci in range(8, 13):
                    c = ws.cell(row=row_num, column=ci, value="")
                    c.fill = sum_fill; c.border = thin_border

            # 冻结首行
            ws.freeze_panes = "A2"

            # 保存
            wb.save(file_path)

            self.controller.after(0, lambda: self._export_done(file_path))
        except Exception as e:
            self.controller.after(0, lambda: self._export_error(str(e)))

    def _export_done(self, file_path):
        """导出完成回调"""
        self.status_var.set(f"导出完成: {os.path.basename(file_path)}")
        messagebox.showinfo("导出完成", f"Excel 文件已保存到桌面:\n{file_path}")

    def _export_error(self, msg):
        """导出失败回调"""
        self.status_var.set(f"导出失败: {msg}")
        messagebox.showerror("导出失败", f"导出 Excel 失败:\n{msg}")

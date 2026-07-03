import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import json
import threading
import openpyxl
from openpyxl.styles import PatternFill, Font, NamedStyle, Alignment, Border, Side
from openpyxl.worksheet.page import PageMargins
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import TableColumn
from openpyxl.styles.borders import Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
import os
import win32com.client
import pythoncom
import subprocess
import platform
from collections import defaultdict
from copy import deepcopy
from typing import Union, Optional, Dict, Tuple, Any
from base_page import BasePage


# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}


class TransferProcessPage(BasePage):
    """调拨入库页面"""
    def __init__(self, parent, controller):
        self.original_data = []  # 存储原始数据
        self.filtered_data = []  # 存储筛选后的数据
        self.selected_items = set()  # 存储选中的项
        self.transfer_detail_cache = {}  # 缓存子节点数据
        self.inboundLog_cache = {}
        # 定义调拨类型映射关系
        self.transfer_type_mapping = {
            "平价调拨": 47171001,
            "加价调拨": 47171002
        }

        # 定义调拨状态映射关系
        self.transfer_status_mapping = {
            "待签收": 47161008,
            "待上架": 47161009,
            "已入库": 47161006
        }
        # 添加分类代码映射字典
        self.CATEGORY_MAPPING = {
            90921001: "前挡",
            90921002: "后挡",
            90921003: "边窗",
            90921004: "其它",
            90921005: "天窗",
        }
        
        # 添加仓库映射字典
        self.WAREHOUSE_MAPPING = {
            "郑州库": {"storage_code": "ZZ", "warehouseId": 6},
            "西安库": {"storage_code": "XA", "warehouseId": 7},
            "兰州库": {"storage_code": "LZ", "warehouseId": 8},
            "驻马店库": {"storage_code": "ZMD", "warehouseId": 9},
            "茶城库": {"storage_code": "CC", "warehouseId": 10},
            "商丘库": {"storage_code": "SQ", "warehouseId": 11},
            "洛阳库": {"storage_code": "LY", "warehouseId": 12},
            "雁塔库": {"storage_code": "YT", "warehouseId": 13},
            "西宁库": {"storage_code": "XN", "warehouseId": 14},
            "榆林库": {"storage_code": "YL", "warehouseId":15},
            "银川库": {"storage_code": "YC", "warehouseId": 16},
            "西安西郊库": {"storage_code": "XA-XJ", "warehouseId": 18}
        }
        # 初始化筛选条件
        self.filtered_data = self.original_data.copy()
        self.filtered_data_all = self.original_data.copy()  # 初始化分页所需的数据
        # 新增分页相关属性
        self.current_page = 1
        self.page_size = 10  # 每页显示200条
        self.total_pages = 1
        # 初始化分页信息变量
        self.page_info_var = tk.StringVar()  # 新增这一行
        # 初始化编辑组件列表
        self.location_entries = []  # 存储实际入库库位的输入框
        self.quantity_spins = []   # 存储实际入库数量的调节钮
        self.quantity_vars = []    # 存储数量变量，防止被回收
        self.detail_item_ids = []  # 存储详情Treeview的行ID

        super().__init__(parent, controller)

    def _check_response(self, response):
        """检查响应中的登录状态"""
        # 如果controller.check_login_status返回True，说明用户已被登出
        # 我们应该返回False，表示不应该继续当前操作
        return not self.controller.check_login_status(response)

    def parse_and_convert_json(self, data):
        """解析JSON数据，并将状态代码转换为文本"""
        try:
            if isinstance(data, dict) and 'data' in data and 'rows' in data['data']:
                orders = data['data']['rows']
            else:
                orders = data  # 已经是列表格式
            
            # 遍历所有订单 替换所有代码映射的文本
            for order in orders:
                # 调拨类型转换
                transfer_type_code = order.get("transferType", "")
                for text, code in self.transfer_type_mapping.items():
                    if code == transfer_type_code:
                        order["transferType"] = text
                        break
                
                # 调拨状态转换
                transfer_status_code = order.get("transferStatus", "")
                for text, code in self.transfer_status_mapping.items():
                    if code == transfer_status_code:
                        order["transferStatus"] = text
                        break

            return orders
        except Exception as e:
            messagebox.showerror("错误", f"数据解析失败: {str(e)}")
            return []

    def create_widgets(self):
        """构建用户界面"""
        # 主容器
        main_container = tk.Frame(self.content_frame, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 顶部筛选面板
        self.setup_filter_panel(main_container)
        
        # 中间数据表格
        self.setup_data_table(main_container)

    def setup_filter_panel(self, parent):
        """构建筛选控制面板"""
        filter_frame = tk.LabelFrame(parent, text="筛选条件", bg="#f0f0f0", 
                                   font=("微软雅黑", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)
        
        # 第一行筛选条件
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)
        # 按钮样式
        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        # 调拨类型筛选
        tk.Label(row1, text="调拨类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.transfer_type_var = tk.StringVar(value="全部")
        type_options = ["全部", "平价调拨", "加价调拨"]
        for option in type_options:
            tk.Radiobutton(row1, text=option, variable=self.transfer_type_var,
                         value=option, command=self.apply_filters,
                         bg="#f0f0f0").pack(side=tk.LEFT, padx=5)

        # 调拨状态下拉框
        tk.Label(row1, text="调拨状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.transfer_status_var = tk.StringVar()
        transfer_statuses = list(self.transfer_status_mapping.keys())
        self.transfer_status_cb = ttk.Combobox(row1, textvariable=self.transfer_status_var,
                                       values=["全部"] + transfer_statuses, state="readonly",width=8)
        self.transfer_status_cb.set("全部")
        self.transfer_status_cb.pack(side=tk.LEFT, padx=5)
        # 调入仓库下拉框
        tk.Label(row1, text="调入仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.movewarehouse_var = tk.StringVar()
        movewarehouses = list(self.controller.options.keys())
        self.movewarehouse_cb = ttk.Combobox(row1, textvariable=self.movewarehouse_var,
                                       values=["全部"] + movewarehouses, state="readonly",width=8)
        self.movewarehouse_cb.set("全部")
        self.movewarehouse_cb.pack(side=tk.LEFT, padx=5)
        # 调出仓库下拉框
        tk.Label(row1, text="调出仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.removewarehouse_var = tk.StringVar()
        removewarehouses = list(self.controller.options.keys())
        self.removewarehouse_cb = ttk.Combobox(row1, textvariable=self.removewarehouse_var,
                                       values=["全部"] + removewarehouses, state="readonly",width=8)
        self.removewarehouse_cb.set("全部")
        self.removewarehouse_cb.pack(side=tk.LEFT, padx=5)
        # 调拨日期选择
        tk.Label(row1, text="调拨起始日期:").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row1, width=10, date_pattern='yyyy-mm-dd')
        # 默认不设置日期，使其为空
        self.start_cal.delete(0, tk.END)
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="调拨结束日期:").pack(side=tk.LEFT, padx=5)
        self.end_cal = DateEntry(row1, width=10, date_pattern='yyyy-mm-dd')
        # 默认不设置日期，使其为空
        self.end_cal.delete(0, tk.END)
        self.end_cal.pack(side=tk.LEFT, padx=5)

         # 调拨单号
        tk.Label(row1, text="调拨单号:").pack(side=tk.LEFT, padx=(5,5))
        self.transfer_no_var = tk.StringVar()
        transfer_no_entry = ttk.Entry(row1,  textvariable=self.transfer_no_var, width=15)
        transfer_no_entry.pack(side=tk.LEFT, padx=5)
        
        # 产品编码
        tk.Label(row1, text="产品编码:").pack(side=tk.LEFT, padx=(5,5))
        self.part_no_var = tk.StringVar()
        part_no_entry = ttk.Entry(row1,  textvariable=self.part_no_var, width=15)
        part_no_entry.pack(side=tk.LEFT, padx=5)
        
        # 产品名称
        tk.Label(row1, text="产品名称:").pack(side=tk.LEFT, padx=(5,5))
        self.part_name_var = tk.StringVar()
        part_name_entry = ttk.Entry(row1,  textvariable=self.part_name_var, width=15)
        part_name_entry.pack(side=tk.LEFT, padx=5) 

        tk.Button(row1, text="查询", command=self.transfer_query, **btn_style).pack(side=tk.LEFT, padx=5)

        # 清除筛选按钮
        tk.Button(row1, text="重置", command=self.clear_filters,
                 bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=20)

##        # 第二行筛选条件
##        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
##        row2.pack(fill=tk.X, pady=5)
##         # 调拨单号
##        tk.Label(row2, text="调拨单号:").pack(side=tk.LEFT, padx=(5,5))
##        self.transfer_no_var = tk.StringVar()
##        transfer_no_entry = ttk.Entry(row2,  textvariable=self.transfer_no_var, width=20)
##        transfer_no_entry.pack(side=tk.LEFT, padx=5)
##        
##        # 产品编码
##        tk.Label(row2, text="产品编码:").pack(side=tk.LEFT, padx=(5,5))
##        self.part_no_var = tk.StringVar()
##        part_no_entry = ttk.Entry(row2,  textvariable=self.part_no_var, width=20)
##        part_no_entry.pack(side=tk.LEFT, padx=5)
##        
##        # 产品名称
##        tk.Label(row2, text="产品名称:").pack(side=tk.LEFT, padx=(5,5))
##        self.part_name_var = tk.StringVar()
##        part_name_entry = ttk.Entry(row2,  textvariable=self.part_name_var, width=20)
##        part_name_entry.pack(side=tk.LEFT, padx=5)  

    def transfer_query(self):
        """查询调拨单"""
        movewarehouse_name = self.movewarehouse_var.get()
        removewarehouse_name = self.removewarehouse_var.get()
        transferNo = self.transfer_no_var.get()
        partNo = self.part_no_var.get()
        partName = self.part_name_var.get()
        # 如果选择"全部"，则将值设为空字符串
        if movewarehouse_name == "全部":
            movewarehouse_id = ""
        else:
            movewarehouse_id = self.controller.options.get(movewarehouse_name)
            
        if removewarehouse_name == "全部":
            removewarehouse_id = ""
        else:
            removewarehouse_id = self.controller.options.get(removewarehouse_name)
            
        # 获取日期值，如果为空则设为空字符串
        starttime = self.start_cal.get() if self.start_cal.get() else ""
        endtime = self.end_cal.get() if self.end_cal.get() else ""
        # 获取调拨状态
        transfer_status_text = self.transfer_status_var.get()
        transfer_type_text = self.transfer_type_var.get()
        
        # 如果选择"全部"，则将值设为空字符串，否则使用映射的数字代码
        if transfer_status_text == "全部":
            transfer_status = ""
        else:
            transfer_status = self.transfer_status_mapping.get(transfer_status_text)
            
        if transfer_type_text == "全部":
            transfer_type = ""
        else:
            transfer_type = self.transfer_type_mapping.get(transfer_type_text)
            
        print(f"调拨状态: {transfer_status_text} -> {transfer_status}")
        # 添加分页参数到API请求中
        transfer_query_url=f'https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/application?transferType={transfer_type}&searchType=inbound&startTime={starttime}&endTime={endtime}&transferNo={transferNo}&partNo={partNo}&partName={partName}&removeWarehouse={removewarehouse_id}&moveWarehouse={movewarehouse_id}&createdByName=&status={transfer_status}&limit=500&pageNum=1'
        print(transfer_query_url)
        r = self.controller.session.get(transfer_query_url,headers=HEADERS)

        # 检查登录状态
        if not self._check_response(r):
            return

        data=json.loads(r.text)
        self.transfer_data=json.loads(r.text)
        origindata=deepcopy(self.transfer_data)
        print(self.transfer_data)

        # 在新查询前彻底清空详情视图与编辑控件
        try:
            # 销毁所有现有的编辑控件
            for entry in getattr(self, 'location_entries', []):
                if hasattr(entry, 'entry') and entry.entry.winfo_exists():
                    entry.entry.destroy()
            
            for spin in getattr(self, 'quantity_spins', []):
                if spin.winfo_exists():
                    spin.destroy()
            
            # 清空列表
            self.detail_item_ids = []
            self.location_entries = []
            self.quantity_spins = []
            self.quantity_vars = []
        except Exception as e:
            print(f"清理编辑控件时出错: {e}")

        try:
            if hasattr(self, "transfer_detail_tree"):
                for _iid in self.transfer_detail_tree.get_children():
                    self.transfer_detail_tree.delete(_iid)
        except Exception:
            pass
        try:
            if hasattr(self, "transfer_detail_cache"):
                self.transfer_detail_cache.clear()
            if hasattr(self, "inboundLog_cache"):
                self.inboundLog_cache.clear()
        except Exception:
            pass

        # 调用 refresh_data 并传递 data
        self.refresh_data(origindata)

    def apply_filters(self):
        """应用所有筛选条件"""
        # self.transfer_detail_cache = {}  # 缓存子节点数据
        # self.inboundLog_cache = {}
        # 直接使用原始数据，不需要复杂筛选
        self.filtered_data = self.original_data
        self.filtered_data_all = self.original_data  # 设置分页所需的数据
        
        # 计算总页数
        self.total_pages = max(1, (len(self.filtered_data_all) + self.page_size - 1) // self.page_size)
        
        # 重置到第一页
        self.current_page = 1
        self.refresh_table()
        
    def clear_filters(self):
        """清除所有筛选条件"""
        self.transfer_type_var.set("全部")
        self.transfer_status_var.set("全部")
        
        # 清空日期选择器
        self.start_cal.delete(0, tk.END)
        self.end_cal.delete(0, tk.END)
        
        # 重置调入仓库和调出仓库
        self.movewarehouse_var.set("全部")
        self.removewarehouse_var.set("全部")
        
        self.apply_filters()

    def setup_data_table(self, parent):
        """构建数据表格"""
        # 表格容器
        table_frame = tk.LabelFrame(parent, text="调拨单查询", bg="#f0f0f0",  bd=1, relief=tk.SOLID,
                                   font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=False)
        
        # 表格标题
        columns = [
            "选择","序号", "调拨单号", "拣货单号","调入方","调出方","调拨类型", "调拨状态","调拨申请时间","调拨发起人","审核人", "审核时间"
        ]
        
        # 创建Treeview
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        
        # 配置列
        col_widths = [40,40, 180, 180, 80,80, 80, 80, 150, 80, 80, 150]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")
        
        # 添加垂直滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # 添加水平滚动条
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        # 创建底部控制框架并使用grid布局
        bottom_frame = tk.Frame(parent, bg="#f0f0f0")
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        # 在底部框架中创建分页和操作按钮区域
        action_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        action_frame.grid(row=0, column=0, sticky="e", padx=10, pady=5)

        pagination_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        pagination_frame.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        bottom_frame.grid_columnconfigure(1, weight=1)  # 让操作按钮区域占据剩余空间
        # 调用分页和操作按钮设置方法，传递对应的框架
        self.setup_pagination_controls(pagination_frame)
        self.setup_action_buttons(action_frame)

        # 添加详情容器
        self.detail_container = tk.LabelFrame(parent, text="调拨单明细", bg="#f0f0f0",  bd=1, relief=tk.SUNKEN,
                                   font=("微软雅黑", 10, "bold"))
        self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
        
        # 创建详情Treeview
        self.detail_columns = [
            "序号","品牌", "CARG全码/产品编码", "产品名称", "入库指示库位","待入库数量", "实际入库库位","入库数量", "销售价", "加价率", "特别说明"
        ]
        self.transfer_detail_tree = ttk.Treeview(self.detail_container, columns=self.detail_columns,
                                      show="headings", height=15)

        # 配置详情列
        detail_col_widths = [50, 100, 150, 300, 80, 80, 120, 80, 80, 80, 150]
        for col, width in zip(self.detail_columns, detail_col_widths):
            self.transfer_detail_tree.heading(col, text=col)
            self.transfer_detail_tree.column(col, width=width, anchor="center")
        
        # 添加滚动条
        detail_vsb = ttk.Scrollbar(self.detail_container, orient="vertical", command=self.transfer_detail_tree.yview)
        detail_hsb = ttk.Scrollbar(self.detail_container, orient="horizontal", command=self.transfer_detail_tree.xview)
        self.transfer_detail_tree.configure(yscrollcommand=detail_vsb.set, xscrollcommand=detail_hsb.set)
        
        # 布局详情Treeview
        self.transfer_detail_tree.grid(row=0, column=0, sticky="nsew")
        detail_vsb.grid(row=0, column=1, sticky="ns")
        detail_hsb.grid(row=1, column=0, sticky="ew")
        
        self.detail_container.grid_rowconfigure(0, weight=1)
        self.detail_container.grid_columnconfigure(0, weight=1)

        # 添加按钮和上架人下拉框
        button_frame = tk.Frame(parent, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=5)
        

        
        # 上架人多选下拉框
        tk.Label(button_frame, text="上架人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        self.onshelf_frame = ttk.Frame(button_frame)
        self.onshelf_frame.pack(side=tk.LEFT, padx=(0, 20))
        self.onshelf_listbox = tk.Listbox(self.onshelf_frame, selectmode=tk.MULTIPLE, height=4, exportselection=False)
        self.onshelf_scrollbar = ttk.Scrollbar(self.onshelf_frame, orient=tk.VERTICAL, command=self.onshelf_listbox.yview)
        self.onshelf_listbox.configure(yscrollcommand=self.onshelf_scrollbar.set)
        self.onshelf_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.onshelf_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮样式
        button_style = {"bg": "#673AB7", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        
        # 暂存按钮
        self.temp_storage_btn = tk.Button(button_frame, text="暂存", command=self.temp_storage, **button_style)
        self.temp_storage_btn.pack(side=tk.LEFT, padx=10)
        
        # 入库按钮
        self.transfer_in_btn = tk.Button(button_frame, text="入库", command=self.transfer_in, **button_style)
        self.transfer_in_btn.pack(side=tk.LEFT, padx=10)
        
        # 初始化上架人列表
        self.load_onshelf_persons()        
        # 绑定单击事件
        self.tree.bind("<Button-1>", self.on_click)
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        # 存储复选框状态的字典
        self.checkbox_states = {}
        # # 初始化缓存和状态
        # self.transfer_detail_cache = {}  # 存储已获取的详细信息 

        # 初始化编辑控件相关变量
        self.detail_item_ids = []  # 存储详情Treeview的行ID
        self.location_entries = []  # 存储实际入库库位的输入框
        self.quantity_spins = []   # 存储实际入库数量的调节钮
        self.quantity_vars = []    # 存储数量变量，防止被回收

        
        # 绑定事件，确保编辑控件跟随滚动
        self.transfer_detail_tree.bind('<Motion>', self.position_detail_widgets)
        self.transfer_detail_tree.bind('<ButtonPress-1>', self.position_detail_widgets)
        self.transfer_detail_tree.bind('<MouseWheel>', self.position_detail_widgets)
        self.transfer_detail_tree.bind('<Leave>', self.position_detail_widgets)
        self.transfer_detail_tree.bind('<Map>', self.position_detail_widgets)

        # 初始化数据
        self.refresh_table()

    # def on_treeview_click(self, event):
    #     """处理Treeview的点击事件，实现复选框功能"""
    #     # 获取点击位置
    #     rowid = self.tree.identify_row(event.y)
    #     column = self.tree.identify_column(event.x)
        
    #     # 确保点击的是第一列（选择列）
    #     if rowid and column == '#1':
    #         # 获取当前行的值
    #         current_values = self.tree.item(rowid, 'values')
            
    #         # 切换复选框状态
    #         if current_values[0] == '☐':
    #             new_value = '✓'
    #         else:
    #             new_value = '☐'
            
    #         # 更新显示的值
    #         new_values = list(current_values)
    #         new_values[0] = new_value
    #         self.tree.item(rowid, values=new_values)
            
    #         # 更新复选框状态字典
    #         self.checkbox_states[rowid] = (new_value == '✓')
            
    #         # 更新选中项集合
    #         order_id = rowid  # 使用行ID作为订单标识
    #         if new_value == '✓':
    #             self.selected_items.add(order_id)
    #         else:
    #             if order_id in self.selected_items:
    #                 self.selected_items.remove(order_id)

# ... existing code ...
    def update_button_states(self):
        """更新按钮状态"""
        # 检查是否有选中的项
        selected_items = self.tree.selection()
        
        if selected_items:
            # 有选中项时启用按钮
            self.temp_storage_btn.config(state=tk.NORMAL)
            self.transfer_in_btn.config(state=tk.NORMAL)
        else:
            # 没有选中项时禁用按钮
            self.temp_storage_btn.config(state=tk.DISABLED)
            self.transfer_in_btn.config(state=tk.DISABLED)
    
    def on_treeview_click(self, event):
        """处理Treeview的点击事件，实现复选框功能"""
        # 获取点击位置
        rowid = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        # 确保点击的是第一列（选择列）
        if rowid and column == '#1':
            # 获取当前行的值
            current_values = self.tree.item(rowid, 'values')
            
            # 切换复选框状态
            if current_values[0] == '☐':
                new_value = '✓'
            else:
                new_value = '☐'
            
            # 更新显示的值
            new_values = list(current_values)
            new_values[0] = new_value
            self.tree.item(rowid, values=new_values)
            
            # 更新复选框状态字典
            self.checkbox_states[rowid] = (new_value == '✓')
            
            # 更新选中项集合
            order_id = rowid  # 使用行ID作为订单标识
            if new_value == '✓':
                self.selected_items.add(order_id)
            else:
                if order_id in self.selected_items:
                    self.selected_items.remove(order_id)
            
            # 更新按钮状态
            self.update_button_states()
        elif rowid:
            # 点击其他列时，选中该行
            self.tree.selection_set(rowid)
            # 确保该项在视图中可见
            self.tree.see(rowid)
            # 更新按钮状态
            self.update_button_states()
# ... existing code ...

    # def on_click(self, event):
    #     """处理节点展开事件"""
    #     item = self.tree.identify_row(event.y)
    #     if not item:
    #         return
    #     column = self.tree.identify_column(event.x)
    #     if column == '#1':
    #         return self.on_treeview_click(event)
            
    #     # 直接使用行的iid作为调拨单ID
    #     transfer_id = item
        
    #     # 获取调拨单号和其他信息
    #     values = self.tree.item(item, "values")
    #     transfer_no = values[2]  # 调拨单号在第2列
            
    #     # 调试信息：验证iid是否正确
    #     print(f"行iid: {item}, 类型: {type(item)}")
    #     print(f"调拨单号: {transfer_no}, 调拨单ID: {transfer_id}")
    #     print(f"行数据验证: {self.tree.item(item) == self.tree.item(transfer_id)}")
        
    #     transfer_status = values[7]  # 调拨状态在第8列
    #     print(f"调拨状态: {transfer_status}")
        
    #     # 检查缓存
    #     if transfer_id in self.transfer_detail_cache and (transfer_status == "待签收" or transfer_status == "待上架"):
    #         transfer_detail_data = self.transfer_detail_cache[transfer_id]
    #         inboundLog_data = None
    #         self.display_detail_data(transfer_detail_data, inboundLog_data,transfer_status,transfer_id)
    #         return
    #     elif transfer_id in self.inboundLog_cache and transfer_id in self.transfer_detail_cache and transfer_status == "已入库":
    #         inboundLog_data = self.inboundLog_cache[transfer_id]
    #         transfer_detail_data = self.transfer_detail_cache[transfer_id]
    #         self.display_detail_data(transfer_detail_data,inboundLog_data, transfer_status,transfer_id)
    #         return
    #     else:
    #         pass

    #     # 发送GET请求获取详细信息
    #     detail_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail?transferId={transfer_id}"
    #     inboundLog_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundLog?transferId={transfer_id}"
    #     if transfer_status == "待上架" or transfer_status == "待签收":
    #         response = self.controller.session.get(detail_url, headers=HEADERS)
    #         # 检查登录状态
    #         if not self._check_response(response):
    #             return
    #         # 修改此处：添加对响应数据结构的检查
    #         response_data = response.json()
    #         if 'data' not in response_data:
    #             messagebox.showerror("错误", f"获取调拨单详情失败: {response_data.get('message', '未知错误')}")
    #             return
    #         transfer_detail_data = response_data['data']
    #         inboundLog_data = None
    #         # 存入缓存
    #         self.transfer_detail_cache[transfer_id] = transfer_detail_data
    #         self.display_detail_data(transfer_detail_data,inboundLog_data,transfer_status,transfer_id)
    #     elif transfer_status == "已入库":
    #         response = self.controller.session.get(detail_url, headers=HEADERS)
    #         respo = self.controller.session.get(inboundLog_url, headers=HEADERS)
    #         # 检查登录状态
    #         if not self._check_response(response) or not self._check_response(respo):
    #             return
    #         # 修改此处：同样添加对响应数据结构的检查
    #         response_data = response.json()
    #         print(response_data)
    #         respo_data = respo.json()
    #         print(respo_data)
    #         if 'data' not in response_data:
    #             messagebox.showerror("错误", f"获取调拨单详情失败: {response_data.get('message', '未知错误')}")
    #             return
                
    #         if 'data' not in respo_data:
    #             messagebox.showerror("错误", f"获取入库日志失败: {respo_data.get('message', '未知错误')}")
    #             return
                
    #         transfer_detail_data = response_data['data']
    #         inboundLog_data = respo_data['data']
    #         # 存入缓存
    #         self.transfer_detail_cache[transfer_id] = transfer_detail_data
    #         self.inboundLog_cache[transfer_id] = inboundLog_data
    #         self.display_detail_data(transfer_detail_data,inboundLog_data,transfer_status,transfer_id)
    #     else:
    #         print("无效的调拨状态")
# ... existing code ...
    def on_tree_select(self, event=None):
        """处理Treeview选择事件"""
        self.update_button_states()
    
    def on_click(self, event):
        """处理节点展开事件"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        column = self.tree.identify_column(event.x)
        if column == '#1':
            return self.on_treeview_click(event)
            
        # 直接使用行的iid作为调拨单ID
        transfer_id = item
        
        # 获取调拨单号和其他信息
        values = self.tree.item(item, "values")
        transfer_no = values[2]  # 调拨单号在第2列
            
        # 调试信息：验证iid是否正确
        print(f"行iid: {item}, 类型: {type(item)}")
        print(f"调拨单号: {transfer_no}, 调拨单ID: {transfer_id}")
        print(f"行数据验证: {self.tree.item(item) == self.tree.item(transfer_id)}")
        
        transfer_status = values[7]  # 调拨状态在第8列
        print(f"调拨状态: {transfer_status}")
        
        # 更新按钮状态
        self.update_button_states()
        
        # 检查缓存
        if transfer_id in self.transfer_detail_cache and (transfer_status == "待签收" or transfer_status == "待上架"):
            transfer_detail_data = self.transfer_detail_cache[transfer_id]
            inboundLog_data = None
            self.display_detail_data(transfer_detail_data, inboundLog_data,transfer_status,transfer_id)
            return
        elif transfer_id in self.inboundLog_cache and transfer_id in self.transfer_detail_cache and transfer_status == "已入库":
            inboundLog_data = self.inboundLog_cache[transfer_id]
            transfer_detail_data = self.transfer_detail_cache[transfer_id]
            self.display_detail_data(transfer_detail_data,inboundLog_data, transfer_status,transfer_id)
            return
        else:
            pass

        # 发送GET请求获取详细信息
        detail_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail?transferId={transfer_id}"
        inboundLog_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundLog?transferId={transfer_id}"
        if transfer_status == "待上架" or transfer_status == "待签收":
            response = self.controller.session.get(detail_url, headers=HEADERS)
            # 检查登录状态
            if not self._check_response(response):
                return
            # 修改此处：添加对响应数据结构的检查
            response_data = response.json()
            if 'data' not in response_data:
                messagebox.showerror("错误", f"获取调拨单详情失败: {response_data.get('message', '未知错误')}")
                return
            transfer_detail_data = response_data['data']
            inboundLog_data = None
            # 存入缓存
            self.transfer_detail_cache[transfer_id] = transfer_detail_data
            self.display_detail_data(transfer_detail_data,inboundLog_data,transfer_status,transfer_id)
        elif transfer_status == "已入库":
            response = self.controller.session.get(detail_url, headers=HEADERS)
            respo = self.controller.session.get(inboundLog_url, headers=HEADERS)
            # 检查登录状态
            if not self._check_response(response) or not self._check_response(respo):
                return
            # 修改此处：同样添加对响应数据结构的检查
            response_data = response.json()
            print(response_data)
            respo_data = respo.json()
            print(respo_data)
            if 'data' not in response_data:
                messagebox.showerror("错误", f"获取调拨单详情失败: {response_data.get('message', '未知错误')}")
                return
                
            if 'data' not in respo_data:
                messagebox.showerror("错误", f"获取入库日志失败: {respo_data.get('message', '未知错误')}")
                return
                
            transfer_detail_data = response_data['data']
            inboundLog_data = respo_data['data']
            # 存入缓存
            self.transfer_detail_cache[transfer_id] = transfer_detail_data
            self.inboundLog_cache[transfer_id] = inboundLog_data
            self.display_detail_data(transfer_detail_data,inboundLog_data,transfer_status,transfer_id)
        else:
            print("无效的调拨状态")
# ... existing code ...
               
    # ==================== 各仓库库位集合生成函数 ====================
    
    def generate_storage_locations_set_for_sq(self, max_level, maxnum):
        """生成商丘库所有库位集合 - 格式: A1-001"""
        locations_set = set()
        rack_config = {
            'A': 112,
            'B': 104,
            'C': 104,
            'D': 104,
            'E': maxnum
        }
        for rack, max_num in rack_config.items():
            for level in range(1, max_level):
                for num in range(1, max_num + 1):
                    locations_set.add(f"{rack}{level}-{num:03d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_zz(self):
        """生成郑州库所有库位集合"""
        locations_set = set()
        # 散片库位：50-59排和61-68排，每排90个库位，分2层
        scattered_racks = list(range(50, 60)) + list(range(61, 69))
        for rack in scattered_racks:
            for level in range(1, 3):
                for slot in range(1, 91):
                    locations_set.add(f"{rack}-{level}{slot:02d}")
        # 高架整箱货位
        high_rack_config = [
            (10, 28, 12, 5),   # 10-28排：每排12个库位，5层
            (29, 36, 4, 5),    # 29-36排：每排4个库位，5层
            (40, 43, 28, 3),   # 40-43排：每排28个库位，3层
        ]
        for start, end, slots, levels in high_rack_config:
            for rack in range(start, end + 1):
                for level in range(1, levels + 1):
                    for slot in range(1, slots + 1):
                        locations_set.add(f"G{rack:02d}{level}-{slot:02d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_xa(self):
        """生成西安库/西安西郊库所有库位集合 - 格式: 211-152"""
        locations_set = set()
        # 散片库位：21-25排，每排152个，2层
        for rack in range(21, 26):
            for level in range(1, 3):
                for slot in range(1, 153):
                    locations_set.add(f"{rack}{level}-{slot:03d}")
        # 散片库位：33-37排，每排136个，2层
        for rack in range(33, 38):
            for level in range(1, 3):
                for slot in range(1, 137):
                    locations_set.add(f"{rack}{level}-{slot:03d}")
        # 高架整箱货位
        high_rack_config = [
            (40, 52, 19, 5),   # 40-52排：每排19个，5层
            (53, 54, 12, 5),   # 53-54排：每排12个，5层
            (55, 55, 12, 1),   # 55排：12个，1层
            (60, 60, 20, 1),   # 60排：20个，1层
        ]
        for start, end, slots, levels in high_rack_config:
            for rack in range(start, end + 1):
                for level in range(1, levels + 1):
                    for slot in range(1, slots + 1):
                        locations_set.add(f"{rack}{level}-{slot:03d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_lz(self):
        """生成兰州库所有库位集合"""
        locations_set = set()
        # 散片库位配置：(排号, 层数, 库位数, 格式, 补零位数)
        scattered_config = [
            ('M41', 2, 136, '{rack}{level}-{slot}', 3),
            ('M42', 2, 160, '{rack}{level}-{slot}', 3),
            ('M43', 2, 160, '{rack}{level}-{slot}', 3),
            ('M6', 2, 170, '{rack}{level}-{slot}', 3),
            ('M7', 2, 150, '{rack}{level}-{slot}', 3),
            ('M8', 2, 140, '{rack}{level}-{slot}', 3),
            ('M90', 2, 152, '{rack}{level}-{slot}', 3),
            ('M91', 2, 160, '{rack}{level}-{slot}', 3),
            ('MG8', 2, 95, '{rack}{level}-{slot}', 2),
            ('MA01', 2, 8, '{rack}-{level}-{slot}', 2),
            ('MA02', 2, 8, '{rack}-{level}-{slot}', 2),
            ('MA03', 2, 12, '{rack}-{level}-{slot}', 2),
            ('MA04', 2, 12, '{rack}-{level}-{slot}', 2),
            ('MA05', 2, 12, '{rack}-{level}-{slot}', 2),
            ('MD01', 3, 19, '{rack}-{level}-{slot}', 2),
            ('MD02', 3, 19, '{rack}-{level}-{slot}', 2),
            ('MD03', 3, 19, '{rack}-{level}-{slot}', 2),
            ('MD04', 3, 19, '{rack}-{level}-{slot}', 2),
            ('MD05', 3, 19, '{rack}-{level}-{slot}', 2),
            ('MD06', 3, 19, '{rack}-{level}-{slot}', 2),
        ]
        for rack, levels, slots, fmt, pad in scattered_config:
            for level in range(1, levels + 1):
                for slot in range(1, slots + 1):
                    slot_str = str(slot).zfill(pad)
                    loc = fmt.format(rack=rack, level=level, slot=slot_str)
                    locations_set.add(loc)
        # 高架整箱货位
        high_config = [
            ('M1', 'M3', 30, 3, '{rack}{level}-{slot}', 3),
            ('M4', 'M5', 12, 3, '{rack}{level}-{slot}', 3),
            ('MG1', 'MG7', 20, 3, '{rack}{level}-{slot}', 2),
        ]
        for start, end, slots, levels, fmt, pad in high_config:
            prefix = ''.join(c for c in start if not c.isdigit())
            start_num = int(''.join(c for c in start if c.isdigit()))
            end_num = int(''.join(c for c in end if c.isdigit()))
            for num in range(start_num, end_num + 1):
                rack = prefix + str(num)
                for level in range(1, levels + 1):
                    for slot in range(1, slots + 1):
                        slot_str = str(slot).zfill(pad)
                        loc = fmt.format(rack=rack, level=level, slot=slot_str)
                        locations_set.add(loc)
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_zmd(self):
        """生成驻马店库所有库位集合 - 格式: 101-001"""
        locations_set = set()
        rack_config = [
            (10, 140, 2),   # 10排：140个，2层
            (11, 215, 2),   # 11排：215个，2层
            (12, 176, 2),   # 12排：176个，2层
        ]
        for rack, slots, levels in rack_config:
            for level in range(1, levels + 1):
                for slot in range(1, slots + 1):
                    locations_set.add(f"{rack}{level}-{slot:03d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_ly(self):
        """生成洛阳库所有库位集合 - 格式: 1-001 (不分层)"""
        locations_set = set()
        rack_config = [
            (1, 2, 136),    # 1-2排：每排136个
            (4, 5, 80),     # 4-5排：每排80个
            (7, 8, 88),     # 7-8排：每排88个
            (10, 11, 80),   # 10-11排：每排80个
        ]
        for start, end, slots in rack_config:
            for rack in range(start, end + 1):
                for slot in range(1, slots + 1):
                    locations_set.add(f"{rack}-{slot:03d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_yl(self):
        """生成榆林库所有库位集合 - 格式: 101-001"""
        locations_set = set()
        for rack in range(10, 16):  # 10-15排
            for level in range(1, 3):
                for slot in range(1, 111):
                    locations_set.add(f"{rack}{level}-{slot:03d}")
        return sorted(locations_set)
    
    def generate_storage_locations_set_for_yc(self):
        """生成银川库所有库位集合 - 格式: 111-001"""
        locations_set = set()
        for rack in range(11, 17):  # 11-16排
            for level in range(1, 3):
                for slot in range(1, 111):
                    locations_set.add(f"{rack}{level}-{slot:03d}")
        return sorted(locations_set)

    class AutoCompleteEntry:
        """自动完成输入框类"""
        def __init__(self, parent,  row_idx, transfer_id, on_change_callback, is_editable=True, warehouse_id=None):
            self.parent = parent
            # self.all_locations = all_locations
            self.row_idx = row_idx
            self.transfer_id = transfer_id
            self.on_change_callback = on_change_callback
            self.is_editable = is_editable
            self.warehouse_id = warehouse_id  # 添加仓库ID参数
            self.current_selection = -1
            self.selected_value = ""     # 记录已选择的值
            self.initial_value = ""  # 添加这行来存储初始值
            self.user_selected = False  # 标记用户是否主动选择项
            self.after_id = None  # 用于延迟请求的ID
            self.last_query = ""  # 记录上一次查询的内容
            self.debounce_time = 200  # 延迟时间（毫秒）
            self.location_data = {}  # 存储库位相关数据，包括realInboundLocationNoId
            # 尝试获取controller引用
            self.controller = None
            self.matches = []
            widget = parent
            while widget is not None:
                if hasattr(widget, 'controller'):
                    self.controller = widget.controller
                    break
                widget = getattr(widget, 'master', None) or getattr(widget, 'parent', None)

            # 创建Entry
            self.entry = ttk.Entry(parent, state='normal' if is_editable else 'disabled')
            self.listbox = None
            self.listbox_window = None
            self.listbox_visible = False
           
            # 绑定事件
            self.entry.bind('<KeyRelease>', self.on_keyrelease)
            self.entry.bind('<FocusIn>', self.on_focus_in)
            self.entry.bind('<FocusOut>', self.on_focus_out)
            self.entry.bind('<Up>', self.on_arrow_key)
            self.entry.bind('<Down>', self.on_arrow_key)
            self.entry.bind('<Return>', self.on_return)
            self.entry.bind('<Escape>', self.on_escape)

        def set_value(self, value):
            """设置初始值（修复禁用状态下无法赋值的问题）"""
            self.is_initializing = True    
            # 1. 保存当前状态（可能是normal或disabled）
            current_state = self.entry.cget('state')
            try:
                # 2. 临时切换为normal，允许修改值
                self.entry.config(state='normal')
                # 3. 清空并插入新值
                self.entry.delete(0, tk.END)
                self.entry.insert(0, value if value else "")
                
                # 保存初始值和选中项
                self.initial_value = value or ""
                self.selected_value = value or ""
                if value:
                    self.current_selection = 0
                else:
                    self.current_selection = -1
            except Exception as e:
                # 打印错误日志（可选）
                print(f"设置值失败: {e}")
            finally:
                # 4. 恢复原来的状态（disabled或normal）
                self.entry.config(state=current_state)
            
            # 延迟清除初始化标志
            self.parent.after(100, self._clear_initializing_flag)        

        def _clear_initializing_flag(self):
            """清除初始化标志"""
            self.is_initializing = False

        def get_value(self):
            """获取当前值"""
            return self.entry.get()
        
        def place(self, x, y, width, height):
            """定位控件"""
            # 确保坐标和尺寸有效
            x = max(0, int(x))
            y = max(0, int(y))
            width = max(1, int(width))
            height = max(1, int(height))
            
            self.entry.place(x=x, y=y, width=width, height=height)
            # 确保Entry控件可见
            self.entry.lift()
            self.entry.update_idletasks()

        def on_keyrelease(self, event):
            """按键释放事件 - 实时过滤"""
            if not self.is_editable:
                return
            if self.is_initializing:
                return
            if event.keysym in ['Up', 'Down', 'Return']:
                return
                
            value = self.entry.get()
            # self.filter_and_show_matches(value)
            # 取消之前的延迟请求
            if self.after_id:
                self.parent.after_cancel(self.after_id)
            
            # 设置新的延迟请求
            self.after_id = self.parent.after(self.debounce_time, lambda: self.filter_and_show_matches(value))        
        # def filter_and_show_matches(self, pattern):
        #     """过滤并显示匹配项"""
        #     if not pattern:
        #         self.hide_listbox()
        #         return
                
        #     # 前缀匹配
        #     matches = [loc for loc in self.all_locations 
        #               if loc.lower().startswith(pattern.lower())]
            
        #     if matches:
        #         self.show_listbox(matches)#[:30])
        #         self.current_selection = 0
        #         if self.listbox:
        #             self.listbox.selection_set(0)
        #     else:
        #         self.hide_listbox()
        # def filter_and_show_matches(self, pattern):
        #     """过滤并显示匹配项"""
        #     if not pattern:
        #         self.hide_listbox()
        #         return
                
        #     # 如果有仓库ID，则通过HTTP请求获取匹配的库位
        #     if self.warehouse_id:
        #         try:
        #             # 发送HTTP GET请求获取匹配的库位
        #             url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/findAllLocationValid"
        #             params = {
        #                 "warehouseId": self.warehouse_id,
        #                 "locationNo": pattern
        #             }
        #             # 使用controller的session来保持登录状态
        #             response = self.parent.master.controller.session.get(url, params=params, headers=HEADERS)
        #             response.raise_for_status()
        #             result = response.json()
                    
        #             # 再次检查输入框中的内容是否与请求时的内容一致
        #             # 防止因延迟返回的结果覆盖了用户后续输入的内容
        #             current_input = self.entry.get()
        #             if current_input != pattern:
        #                 # 用户已经输入了新的内容，忽略这次过期的响应
        #                 return
                    
        #             # 从响应中提取库位列表
        #             if result.get('data'):
        #                 matches = [item['locationNo'] for item in result['data']]
        #             else:
        #                 matches = []
        #         except Exception as e:
        #             print(f"获取库位数据失败: {e}")
        #             # 出错时回退到本地匹配
        #             matches = [loc for loc in self.all_locations 
        #                       if loc.lower().startswith(pattern.lower())]
        #     else:
        #         # 没有仓库ID时使用本地匹配
        #         matches = [loc for loc in self.all_locations 
        #                   if loc.lower().startswith(pattern.lower())]
            
        #     if matches:
        #         self.show_listbox(matches)
        #         self.current_selection = 0
        #         if self.listbox:
        #             self.listbox.selection_set(0)
        #     else:
        #         self.hide_listbox()

# ... existing code ...
        def filter_and_show_matches(self, pattern):
            """过滤并显示匹配项"""

                
            # 如果有仓库ID，则通过HTTP请求获取匹配的库位
            if self.warehouse_id:
                try:
                    # 发送HTTP GET请求获取匹配的库位
                    url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/findAllLocationValid"
                    params = {
                        "warehouseId": self.warehouse_id,
                        "locationNo": pattern
                    }
                    # 使用controller的session来保持登录状态
                    # 修复：通过正确的途径获取controller
                    # controller = None
                    # widget = self.parent
                    # while widget is not None:
                    #     if hasattr(widget, 'controller'):
                    #         controller = widget.controller
                    #         break
                    #     widget = getattr(widget, 'master', None) or getattr(widget, 'parent', None)
                    
                    if self.controller is None:
                        # 如果找不到controller，不进行本地匹配，直接返回
                        self.hide_listbox()
                        return
                    
                    response = self.controller.session.get(url, params=params, headers=HEADERS)

                    response.raise_for_status()
                    result = response.json()
                    
                    # 再次检查输入框中的内容是否与请求时的内容一致
                    # 防止因延迟返回的结果覆盖了用户后续输入的内容
                    current_input = self.entry.get()
                    if current_input != pattern:
                        # 用户已经输入了新的内容，忽略这次过期的响应
                        return
                    
                    # 从响应中提取库位列表和相关数据
                    if result.get('data'):

                        # 清空之前的数据
                        self.location_data = {}
                        self.matches = []  # 清空之前的匹配结果                        
                        for item in result['data']:
                            location_no = item['locationNo']
                            print(location_no)
                            self.matches.append(location_no)
                            # 保存库位相关数据，包括realInboundLocationNoId
                            self.location_data[location_no] = {
                                'realInboundLocationNoId': item.get('locationId'),
                                'other_data': [item]  # 保存其他可能需要的数据
                            }
                    else:
                        self.matches = []
                except Exception as e:
                    print(f"获取库位数据失败: {e}")
                    # 出错时清空location_data
                    self.matches = []
                    self.location_data = {}
            else:
                # 没有仓库ID时不进行匹配
                self.matches = []
                self.location_data = {}
            
            if self.matches:
                self.show_listbox(self.matches)
                self.current_selection = 0
                if self.listbox:
                    self.listbox.selection_set(0)
            else:
                self.hide_listbox()
# ... existing code ...

        # def on_listbox_click(self, event):
        #     """Listbox单击事件"""
        #     # 获取点击的项
        #     if self.listbox:
        #         # 获取鼠标点击位置的项
        #         index = self.listbox.nearest(event.y)
        #         if index >= 0:
        #             self.current_selection = index
        #             self.listbox.selection_clear(0, tk.END)
        #             self.listbox.selection_set(index)
        #             self.listbox.activate(index)
        #             # 添加这行来更新显示
        #             self.select_current_item()
        #             self.user_selected = True  # 用户点击选择

        def show_listbox(self, items):
            """显示Listbox"""
            # 如果已经有listbox窗口，先销毁
            if self.listbox_window and self.listbox_window.winfo_exists():
                self.listbox_window.destroy()
            
            # 创建顶层窗口用于Listbox
            self.listbox_window = tk.Toplevel(self.parent)
            self.listbox_window.wm_overrideredirect(True)
            self.listbox_window.wm_transient(self.parent)
            # 设置窗口属性，确保显示在最前面
            self.listbox_window.wm_attributes("-topmost", True)            
            # 计算位置（在Entry下方）
            try:
                entry_x = self.entry.winfo_rootx()
                entry_y = self.entry.winfo_rooty()
                entry_width = self.entry.winfo_width()
                entry_height = self.entry.winfo_height()
                
                listbox_x = entry_x
                listbox_y = entry_y + entry_height
                
                self.listbox_window.geometry(f"{entry_width}x120+{listbox_x}+{listbox_y}")
            except tk.TclError:
                # 如果获取位置失败，使用默认位置
                self.listbox_window.geometry("200x120")
            
            # 创建Listbox
            self.listbox = tk.Listbox(self.listbox_window, height=6)
            scrollbar = tk.Scrollbar(self.listbox_window, orient=tk.VERTICAL)
            self.listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=self.listbox.yview)
            
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 添加匹配项
            for item in items:  # 限制显示数量以提高性能
                self.listbox.insert(tk.END, item)
            
            # 绑定事件
            self.listbox.bind('<Double-Button-1>', self.on_listbox_select)
            self.listbox.bind('<Button-1>', self.on_listbox_select)
            self.listbox.bind('<Return>', self.on_listbox_select)
            self.listbox.bind('<Escape>', self.on_escape)
            self.listbox.bind('<FocusOut>', self.on_listbox_focus_out)
            
            self.listbox_visible = True
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            # 确保窗口显示在最前面
            self.listbox_window.lift()

# ... existing code ...
        def hide_listbox(self):
            """隐藏Listbox"""
            try:
                if self.listbox_window and self.listbox_window.winfo_exists():
                    self.listbox_window.destroy()
            except tk.TclError:
                pass
            self.listbox_visible = False
            # 不要在这里重置current_selection，因为validate_and_hide还需要使用它
            # self.current_selection = -1
# ... existing code ...
        
        def on_focus_in(self, event):
            """获得焦点时显示匹配项"""
            if not self.is_editable:
                return
            if self.is_initializing:
                return
            # 获取当前输入框的值
            current_value = self.entry.get()
            # 显示匹配项，但不清空输入框
            self.filter_and_show_matches(current_value)     

        def on_focus_out(self, event):
            if not self.is_editable:
                return
            if self.is_initializing:
                return

            """失去焦点时验证输入并隐藏Listbox"""
            # 如果是初始化过程中的焦点变化，不进行验证
            if getattr(self, 'is_initializing', False):
                # self.is_initializing = False
                return
            # 延迟执行以允许其他事件处理
            self.parent.after(100, self.validate_and_hide)
        
        # def validate_and_hide(self):
        #     """验证输入并隐藏Listbox"""
        #     if getattr(self, 'is_initializing', False):
        #         # 初始化阶段不验证，直接返回
        #         self.is_initializing = False
        #         return

        #     # 获取当前输入
        #     current_input = self.entry.get().strip()            
        #     # 如果有选中项，则使用选中项的值
        #     # if self.current_selection >= 0 and self.listbox and self.listbox_visible:
        #     # 只有当用户主动选择（点击或按回车）时才验证输入
        #     if self.user_selected:
        #         try:
        #             selected = self.listbox.get(self.current_selection)
        #             self.selected_value = selected
        #             self.entry.delete(0, tk.END)
        #             self.entry.insert(0, selected)
        #         except tk.TclError:
        #             pass
        #     else:
        #         # 检查当前输入是否有效
        #         if current_input and current_input in self.all_locations:
        #             # 输入有效，保留当前输入
        #             self.selected_value = current_input
        #         else:
        #             # 输入无效或为空，恢复到初始值
        #             self.entry.delete(0, tk.END)
        #             # 恢复到初始值（即current_location）
        #             if hasattr(self, 'initial_value'):
        #                 self.entry.insert(0, self.initial_value)
        #                 self.selected_value = self.initial_value
            
        #     # 只有在隐藏列表框时才重置current_selection
        #     if not self.listbox_visible:
        #         self.current_selection = -1
        #     self.hide_listbox()
        #     # 只有在值发生变化时才触发回调
        #     if self.selected_value != self.initial_value:
        #         self.on_change_callback(self.row_idx, self.transfer_id)      
        #     # 重置用户选择标记
        #     self.user_selected = False
        # def validate_and_hide(self):
        #     """验证输入并隐藏Listbox"""
        #     if getattr(self, 'is_initializing', False):
        #         # 初始化阶段不验证，直接返回
        #         self.is_initializing = False
        #         return
            
        #     # 只有当用户主动选择（点击或按回车）时才验证输入
        #     print(self.user_selected)
        #     if self.user_selected:
        #         # 用户已经选择了有效选项，直接使用选择的值
        #         print(self.current_selection)
        #         if self.current_selection >= 0 and self.listbox and self.listbox_visible:
        #             try:
        #                 selected = self.listbox.get(self.current_selection)
        #                 print(selected)
        #                 self.selected_value = selected
        #                 self.entry.delete(0, tk.END)
        #                 self.entry.insert(0, selected)
        #             except tk.TclError:
        #                 pass
        #         else:
        #             print("没有选择")
        #     else:
        #         # 用户没有从列表中选择，检查手动输入的值
        #         current_input = self.entry.get().strip()
        #         print(current_input)
        #         # 检查当前输入是否有效
        #         if current_input and current_input in self.all_locations:
        #             # 输入有效，保留当前输入
        #             self.selected_value = current_input
        #         else:
        #             # 输入无效或为空，恢复到初始值
        #             self.entry.delete(0, tk.END)
        #             # 恢复到初始值（即current_location）
        #             if hasattr(self, 'initial_value'):
        #                 self.entry.insert(0, self.initial_value)
        #                 self.selected_value = self.initial_value
                
        #         # 只有在值发生变化时才触发回调
        #         if self.selected_value != self.initial_value:
        #             print(self.selected_value)
        #             print(self.initial_value)
        #             self.on_change_callback(self.row_idx, self.transfer_id)
                
        #     # 重置用户选择标记
        #     self.user_selected = False
            
        #     # 隐藏列表框
        #     self.hide_listbox()
# ... existing code ...
        def validate_and_hide(self):
            """验证输入并隐藏Listbox"""
            if getattr(self, 'is_initializing', False):
                # 初始化阶段不验证，直接返回
                self.is_initializing = False
                return
            
            # 只有当用户主动选择（点击或按回车）时才验证输入
            print(self.user_selected)
            if self.user_selected:
                # 用户已经选择了有效选项，直接使用选择的值
                print(self.current_selection)
                if self.current_selection >= 0 and self.listbox and self.listbox_visible:
                    try:
                        selected = self.listbox.get(self.current_selection)
                        print(selected)
                        self.selected_value = selected
                        self.entry.delete(0, tk.END)
                        self.entry.insert(0, selected)
                        # 更新初始值为当前选中的值，防止再次点击时恢复到旧值
                        self.initial_value = selected
                        # # 触发回调
                        # self.on_change_callback(self.row_idx, self.transfer_id)
                    except tk.TclError:
                        pass
                else:
                    print("没有选择")
            else:
                # 用户没有从列表中选择，检查手动输入的值
                current_input = self.entry.get().strip()
                print(current_input)
                # 检查当前输入是否有效
                if current_input and current_input in self.matches:
                    # 输入有效，保留当前输入
                    self.selected_value = current_input
                else:
                    # 输入无效或为空，恢复到初始值
                    self.entry.delete(0, tk.END)
                    # 恢复到初始值（即current_location）
                    if hasattr(self, 'initial_value'):
                        self.entry.insert(0, self.initial_value)
                        self.selected_value = self.initial_value
                
            # 只有在值发生变化时才触发回调
            if self.selected_value != self.initial_value:
                print(self.selected_value)
                print(self.initial_value)
                selected_data = self.location_data.get(self.selected_value, {})
                self.on_change_callback(self.row_idx, self.transfer_id, self.selected_value, selected_data)
                
            # 重置用户选择标记
            self.user_selected = False
            
            # 隐藏列表框并重置current_selection
            self.hide_listbox()
            self.current_selection = -1
# ... existing code ...
        def on_listbox_focus_out(self, event):
            """Listbox失去焦点时隐藏"""
            self.hide_listbox()
        
        def on_arrow_key(self, event):
            """上下键导航"""
            if not self.is_editable:
                return
            if self.is_initializing:
                return
            if not self.listbox_visible or not self.listbox:
                return
                
            if event.keysym == 'Up':
                self.current_selection = max(0, self.current_selection - 1)
            elif event.keysym == 'Down':
                self.current_selection = min(self.listbox.size() - 1, self.current_selection + 1)
            
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_selection)
            self.listbox.see(self.current_selection)
            return "break"
        
        def on_return(self, event):
            """回车键选择"""
            if not self.is_editable:
                return
            if self.is_initializing:
                return
            if self.listbox_visible and self.current_selection >= 0 and self.listbox:
                self.select_current_item()
                return "break"
            elif self.listbox_visible and self.listbox:
                # 如果没有选择项但有listbox显示，选择第一项
                self.current_selection = 0
                self.select_current_item()
                self.user_selected = True  # 用户按回车选择
                return "break"
        
        def on_escape(self, event):
            """ESC键隐藏Listbox"""
            if not self.is_editable:
                return
            if self.is_initializing:
                return
            if self.listbox_visible:
                self.hide_listbox()
                self.entry.focus_set()
            return "break"
        
        # def on_listbox_select(self, event):
        #     """Listbox选择事件"""
        #     # 获取当前选择的索引
        #     selection = self.listbox.curselection()
        #     if selection:
        #         self.current_selection = selection[0]
        #     self.select_current_item()
        #     self.user_selected = True  # 用户按回车选择
# ... existing code ...
        def on_listbox_select(self, event):
            """Listbox选择事件（单击、双击或回车）"""
            if self.listbox:
                # 处理单击选择
                if event.type in (tk.EventType.ButtonPress, tk.EventType.ButtonRelease):
                    index = self.listbox.nearest(event.y)
                    if index >= 0:
                        self.current_selection = index
                        print("单击选择")
                        print(self.current_selection)
                        self.listbox.selection_clear(0, tk.END)
                        self.listbox.selection_set(index)
                        self.listbox.activate(index)
                        # 立即选择当前项
                        self.select_current_item()
                        self.user_selected = True
                        # return "break"  # 阻止事件继续传播
                else:
                    # 处理双击或回车选择
                    selection = self.listbox.curselection()
                    print("双击回车")
                    print(selection)
                    if selection:
                        self.current_selection = selection[0]
                        # 立即选择当前项
                        self.select_current_item()
                        self.user_selected = True
                        # return "break"
# ... existing code ...     
        # def select_current_item(self):
        #     """选择当前项"""
        #     print("选择当前项")
        #     print(self.current_selection)
        #     if self.current_selection >= 0 and self.listbox:
        #         try:
        #             selected = self.listbox.get(self.current_selection)
        #             self.entry.delete(0, tk.END)
        #             self.entry.insert(0, selected)
        #             self.hide_listbox()
                    
        #             # 触发位置改变回调
        #             self.on_change_callback(self.row_idx, self.transfer_id)
        #             self.entry.focus_set()
        #         except tk.TclError:
        #             pass
# ... existing code ...
        def select_current_item(self):
            """选择当前项"""
            print("选择当前项")
            print(self.current_selection)
            if self.current_selection >= 0 and self.listbox:
                try:
                    selected = self.listbox.get(self.current_selection)
                    self.entry.delete(0, tk.END)
                    self.entry.insert(0, selected)
                    self.hide_listbox()
                    
                    # 触发位置改变回调，传递选中的库位和相关数据
                    selected_data = self.location_data.get(selected, {})
                    self.on_change_callback(self.row_idx, self.transfer_id, selected, selected_data)
                    self.entry.focus_set()
                    # 更新初始值为当前选中的值，防止再次点击时恢复到旧值
                    self.initial_value = selected
                    self.selected_value = selected
                except tk.TclError:
                    pass
# ... existing code ...
    # def display_detail_data(self, detail_data,transfer_status,transfer_id):
    #     """显示详情数据"""
    #     # 清空详情Treeview
    #     self.transfer_detail_tree.delete(*self.transfer_detail_tree.get_children())

    #     # 清空编辑控件 - 更严格的清理逻辑
    #     for entry in self.location_entries:
    #         try:
    #             if hasattr(entry, 'listbox_window') and entry.listbox_window and entry.listbox_window.winfo_exists():
    #                 entry.listbox_window.destroy()
    #             if hasattr(entry, 'entry') and entry.entry.winfo_exists():
    #                 entry.entry.destroy()
    #             elif hasattr(entry, 'destroy') and entry.winfo_exists():
    #                 entry.destroy()
    #         except (tk.TclError, AttributeError):
    #             # 控件可能已被销毁，忽略错误
    #             pass
                
    #     for spin in self.quantity_spins:
    #         try:
    #             if spin.winfo_exists():
    #                 spin.destroy()
    #         except tk.TclError:
    #             # 控件可能已被销毁，忽略错误
    #             pass
        
    #     # 强制垃圾回收，确保控件被完全清理
    #     import gc
    #     gc.collect()
        
    #     # 重新初始化列表
    #     self.location_entries = []  # 改为存储AutoCompleteEntry对象
    #     self.quantity_spins = []
    #     self.quantity_vars = []
    #     self.detail_item_ids = []
    #     self.all_locations=self.generate_storage_locations_set(max_level=4,maxnum=72)

    #     # 设置交替行标签
    #     self.transfer_detail_tree.tag_configure('oddrow', background='#E5E5E5')
    #     self.transfer_detail_tree.tag_configure('evenrow', background='#FFFFFF')        

    #     # 填充商品数据
    #     for i, item_data in enumerate(detail_data, 1):
    #         tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
    #         # 获取当前行的库位选项
    #         outbound_Quantity = item_data.get("outboundQuantity",0)
    #         current_location = item_data.get("realInboundLocationNo", "")
    #         current_quantity = item_data.get("inboundQuantity", 0)

    #         # 判断调拨状态是否允许交互
    #         is_editable = (transfer_status == "待上架")

    #         item_id = self.transfer_detail_tree.insert("", "end", values=(
    #             i,
    #             item_data.get("brandName",""),
    #             item_data.get("partCode", ""),
    #             item_data.get("partName", ""),
    #             item_data.get("shelfLocationNo", ""),
    #             item_data.get("waitInboundQty",0),
    #             current_location,
    #             current_quantity,
    #             item_data.get("salesPrice",""),
    #             item_data.get("priceIncreaseRate",""),
    #             item_data.get("remarks","")
    #         ),iid = item_data.get("detailId"),tags=tags)

    #         self.detail_item_ids.append(item_id)

    #         # 创建实际入库库位自动完成输入框
    #         location_entry = self.AutoCompleteEntry(
    #             self.transfer_detail_tree,
    #             self.all_locations,
    #             i-1,  # row_idx
    #             transfer_id,
    #             self.on_location_change,  # 回调函数
    #             is_editable
    #         )
            
    #         # 设置初始值
    #         location_entry.set_value(current_location)
    #         # 确保Entry控件正确更新显示
    #         location_entry.entry.update_idletasks()            
    #         self.location_entries.append(location_entry)
            
    #         # 创建实际入库数量调节钮
    #         var = tk.StringVar(value=str(current_quantity))
    #         var.trace_add('write', lambda *_, idx=i-1, v=var: self.on_quantity_change(idx,transfer_id, v))
            
    #         spin = tk.Spinbox(
    #             self.transfer_detail_tree,
    #             from_=0,
    #             to=outbound_Quantity,
    #             width=5,
    #             bg='lightyellow',
    #             textvariable=var,
    #             state='normal' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         spin.delete(0, tk.END)
    #         spin.insert(0, current_quantity)
            
    #         spin.bind("<FocusOut>", lambda e, idx=i-1: self.on_quantity_change(idx,transfer_id))
    #         spin.bind("<Return>", lambda e, idx=i-1: self.on_quantity_change(idx,transfer_id))
            
    #         self.quantity_spins.append(spin)
    #         self.quantity_vars.append(var)
            
    #     print(self.detail_item_ids)
        
    #     # 确保Treeview完成渲染后再进行布局
    #     self.transfer_detail_tree.update_idletasks()
        
    #     self.position_detail_widgets()

    #     # 显示详情容器
    #     self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
    def display_detail_data(self, detail_data,inboundLog_data,transfer_status,transfer_id):
        """显示详情数据"""
        # 清空详情Treeview
        self.transfer_detail_tree.delete(*self.transfer_detail_tree.get_children())

        # 清空编辑控件 - 更严格的清理逻辑
        for entry in self.location_entries:
            try:
                if hasattr(entry, 'listbox_window') and entry.listbox_window and entry.listbox_window.winfo_exists():
                    entry.listbox_window.destroy()
                if hasattr(entry, 'entry') and entry.entry.winfo_exists():
                    entry.entry.destroy()
                elif hasattr(entry, 'destroy') and entry.winfo_exists():
                    entry.destroy()
            except (tk.TclError, AttributeError):
                # 控件可能已被销毁，忽略错误
                pass
                
        for spin in self.quantity_spins:
            try:
                if spin.winfo_exists():
                    spin.destroy()
            except tk.TclError:
                # 控件可能已被销毁，忽略错误
                pass
        
        # 强制垃圾回收，确保控件被完全清理
        import gc
        gc.collect()
        
        # 重新初始化列表
        self.location_entries = []  # 改为存储AutoCompleteEntry对象
        self.quantity_spins = []
        self.quantity_vars = []
        self.detail_item_ids = []
        # self.all_locations=self.generate_storage_locations_set_for_sq(max_level=4,maxnum=72)

        # 设置交替行标签
        self.transfer_detail_tree.tag_configure('oddrow', background='#E5E5E5')
        self.transfer_detail_tree.tag_configure('evenrow', background='#FFFFFF')        
        # 配置汇总行的样式
        self.transfer_detail_tree.tag_configure('summary', background='#f0f0f0', font=('Arial', 13, 'bold'))

        # 初始化汇总变量
        total_wait_inbound_qty = 0
        total_inbound_qty = 0

        # 获取调入仓库ID，用于传递给自动完成输入框
        movewarehouse_id = None
        # 从原始数据中查找调入仓库ID
        for record in self.original_data:
            if str(record.get("id")) == str(transfer_id):
                movewarehouse_id = record.get("moveWarehouseId")
                break

        # 填充商品数据
        for i, (item_data, log_data) in enumerate(zip(detail_data, inboundLog_data if inboundLog_data else [{}] * len(detail_data)), 1):
            tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
            # 获取当前行的库位选项
            outbound_Quantity = item_data.get("outboundQuantity",0)

            # 累加数量用于汇总
            wait_inbound_qty = item_data.get("waitInboundQty", 0) or 0
            if transfer_status == "待上架" or transfer_status == "待签收":
                inbound_qty = item_data.get("inboundQuantity", 0) or 0
                current_location = item_data.get("realInboundLocationNo", "")
                # current_quantity = item_data.get("inboundQuantity", 0)
            elif transfer_status == "已入库":
                inbound_qty = log_data.get("transferQuantity", 0) or 0
                current_location = log_data.get("realInboundLocationNo", "")
            else:
                inbound_qty = 0
                current_location = ""
            
            total_wait_inbound_qty += wait_inbound_qty
            total_inbound_qty += inbound_qty

            # 判断调拨状态是否允许交互
            is_editable = (transfer_status == "待上架")

            item_id = self.transfer_detail_tree.insert("", "end", values=(
                i,
                item_data.get("brandName",""),
                item_data.get("partCode", ""),
                item_data.get("partName", ""),
                item_data.get("shelfLocationNo", ""),
                wait_inbound_qty,
                current_location,
                inbound_qty,
                item_data.get("salesPrice",""),
                item_data.get("priceIncreaseRate",""),
                item_data.get("remarks","")
            ),iid = item_data.get("detailId"),tags=tags)

            self.detail_item_ids.append(item_id)

            # 创建实际入库库位自动完成输入框
            location_entry = self.AutoCompleteEntry(
                self.transfer_detail_tree,
                # self.all_locations,
                i-1,  # row_idx
                transfer_id,
                self.on_location_change,  # 回调函数
                is_editable,
                warehouse_id=movewarehouse_id  # 传递仓库ID，用于获取有效库位

            )
            
            # 设置初始值
            location_entry.set_value(current_location)
            # 确保Entry控件正确更新显示
            location_entry.entry.update_idletasks()            
            self.location_entries.append(location_entry)
            
            # 创建实际入库数量调节钮
            var = tk.StringVar(value=str(inbound_qty))
            var.trace_add('write', lambda *_, idx=i-1, v=var: self.on_quantity_change(idx,transfer_id, v))
            
            spin = tk.Spinbox(
                self.transfer_detail_tree,
                from_=0,
                to=outbound_Quantity,
                width=5,
                bg='lightyellow',
                textvariable=var,
                state='normal' if is_editable else 'disabled'  # 动态设置状态
            )
            spin.delete(0, tk.END)
            spin.insert(0, inbound_qty)
            
            spin.bind("<FocusOut>", lambda e, idx=i-1: self.on_quantity_change(idx,transfer_id))
            spin.bind("<Return>", lambda e, idx=i-1: self.on_quantity_change(idx,transfer_id))
            
            self.quantity_spins.append(spin)
            self.quantity_vars.append(var)
            
        # 插入汇总行
        self.transfer_detail_tree.insert("", "end", values=(
            "合计",
            "", "", "", "",
            total_wait_inbound_qty,
            "",
            total_inbound_qty,
            "", "", ""
        ), tags=("summary",))

        print(self.detail_item_ids)
        
        # 确保Treeview完成渲染后再进行布局
        self.transfer_detail_tree.update_idletasks()
        
        self.position_detail_widgets()

        # 显示详情容器
        self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
    def position_detail_widgets(self, event=None):
        """将编辑控件定位到对应单元格"""
##        print(f"DEBUG: Positioning {len(self.location_entries)} location entries")
        
        # 确保所有列表长度一致且正确匹配
        n = min(len(self.detail_item_ids), len(self.location_entries), len(self.quantity_spins))
        
        for i in range(n):
            try:
                # 获取当前行的item_id
                item_id = self.detail_item_ids[i]
##                print(f"DEBUG: Row {i} - item_id: {item_id}")                
        
                # 验证控件索引与行索引匹配
                if i >= len(self.location_entries) or i >= len(self.quantity_spins):
                    continue
                    
                # 实际入库库位列 (第7列，索引为7)
                bbox_location = self.transfer_detail_tree.bbox(item_id, '#7')
                
                if bbox_location and bbox_location != (0, 0, 0, 0):
                    x, y, width, height = bbox_location
                    # 添加小偏移避免边框重叠
                    x += 1
                    y += 1
                    width = max(width - 2, 1)
                    height = max(height - 2, 1)
                    
                    # 确保控件存在且有效
                    if i < len(self.location_entries) and hasattr(self.location_entries[i], 'place'):
                        self.location_entries[i].place(
                            x=x, y=y, width=width, height=height
                        )
                        # 确保Entry控件显示正确的值
                        self.location_entries[i].entry.update_idletasks()
                else:
                    # 如果AutoCompleteEntry有entry属性，隐藏它
                    if i < len(self.location_entries) and hasattr(self.location_entries[i], 'entry'):
                        self.location_entries[i].entry.place_forget()
                
                # 实际入库数量列 (第8列，索引为8)
                bbox_quantity = self.transfer_detail_tree.bbox(item_id, '#8')
                
                if bbox_quantity and bbox_quantity != (0, 0, 0, 0):
                    x, y, width, height = bbox_quantity
                    # 添加小偏移避免边框重叠
                    x += 1
                    y += 1
                    width = max(width - 2, 1)
                    height = max(height - 2, 1)
                    
                    # 确保控件存在且有效
                    if i < len(self.quantity_spins):
                        self.quantity_spins[i].place(
                            x=x, y=y, width=width, height=height
                        )
                else:
                    if i < len(self.quantity_spins):
                        self.quantity_spins[i].place_forget()

            except tk.TclError as e:
                # item 被删除或不可见
                pass
            except IndexError as e:
                # 索引不匹配，跳过此控件
                continue

    # def on_location_change(self, row_idx,transfer_id):
    #     """实际入库库位修改时更新Treeview"""
    #     # 从对应的自动完成输入框中获取当前选中的库位
    #     if row_idx < len(self.location_entries):
    #         actual_location = self.location_entries[row_idx].get_value()
    #         item_id = self.detail_item_ids[row_idx]
    #         current_values = list(self.transfer_detail_tree.item(item_id, 'values'))
    #         current_values[6] = actual_location  # 第7列是实际拣货库位（存储实际库位）
    #         self.transfer_detail_tree.item(item_id, values=current_values)
            
    #         # 更新缓存中的数据
    #         if transfer_id in self.transfer_detail_cache:
    #             for i, item in enumerate(self.transfer_detail_cache[transfer_id]):
    #                 if i == row_idx:
    #                     item["realInboundLocationNo"] = actual_location
    #                     break
# # ... existing code ...
#     def on_location_change(self, row_idx, transfer_id, location_no=None, location_data=None):
#         """实际入库库位修改时更新Treeview"""
#         # 从对应的自动完成输入框中获取当前选中的库位
#         if row_idx < len(self.location_entries):
#             if location_no is None:
#                 # 如果没有传入location_no，则从entry获取
#                 actual_location = self.location_entries[row_idx].get_value()
#             else:
#                 # 使用传入的location_no
#                 actual_location = location_no
                
#             item_id = self.detail_item_ids[row_idx]
#             current_values = list(self.transfer_detail_tree.item(item_id, 'values'))
#             current_values[6] = actual_location  # 第7列是实际拣货库位（存储实际库位）
#             self.transfer_detail_tree.item(item_id, values=current_values)
            
#             # 更新缓存中的数据
#             if transfer_id in self.transfer_detail_cache:
#                 for i, item in enumerate(self.transfer_detail_cache[transfer_id]):
#                     if i == row_idx:
#                         item["realInboundLocationNo"] = actual_location
#                         # 如果有传入的location_data，则更新realInboundLocationNoId
#                         if location_data and 'realInboundLocationNoId' in location_data:
#                             item["realInboundLocationNoId"] = location_data['realInboundLocationNoId']
#                         break
# # ... existing code ...

# ... existing code ...
    def on_location_change(self, row_idx, transfer_id, location_no=None, location_data=None):
        """实际入库库位修改时更新Treeview"""
        # 从对应的自动完成输入框中获取当前选中的库位
        if row_idx < len(self.location_entries):
            if location_no is None:
                # 如果没有传入location_no，则从entry获取
                actual_location = self.location_entries[row_idx].get_value()
            else:
                # 使用传入的location_no
                actual_location = location_no
                
            item_id = self.detail_item_ids[row_idx]
            current_values = list(self.transfer_detail_tree.item(item_id, 'values'))
            current_values[6] = actual_location  # 第7列是实际拣货库位（存储实际库位）
            self.transfer_detail_tree.item(item_id, values=current_values)
            
            # 更新缓存中的数据
            if transfer_id in self.transfer_detail_cache:
                for i, item in enumerate(self.transfer_detail_cache[transfer_id]):
                    if i == row_idx:
                        item["realInboundLocationNo"] = actual_location
                        # 如果有传入的location_data，则更新realInboundLocationNoId
                        if location_data and 'realInboundLocationNoId' in location_data:
                            item["realInboundLocationNoId"] = location_data['realInboundLocationNoId']
                        
                        # 库位改变时添加select_LOCATION_OPTIONS和select_locationOptionLoading字段
                        if location_no is not None:  # 说明是通过选择触发的改变
                            if location_data and 'other_data' in location_data:
                                # 获取仓库ID
                                movewarehouse_id = None
                                # 从原始数据中查找调入仓库ID
                                for record in self.original_data:
                                    if str(record.get("id")) == str(transfer_id):
                                        movewarehouse_id = record.get("moveWarehouseId")
                                        break
                                # 发送HTTP GET请求获取匹配的库位
                                url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/findAllLocationValid"
                                params = {
                                    "warehouseId": movewarehouse_id,
                                    "locationNo": location_no
                                }
                                # 使用controller的session来保持登录状态
                                # 修复：通过正确的途径获取controller
                                controller = None
                                widget = self
                                while widget is not None:
                                    if hasattr(widget, 'controller'):
                                        controller = widget.controller
                                        break
                                    widget = getattr(widget, 'master', None) or getattr(widget, 'parent', None)
                                
                                if controller is None:
                                    return
                                
                                response = controller.session.get(url, params=params, headers=HEADERS)

                                response.raise_for_status()
                                result = response.json()

                                # 库位改变时，select_LOCATION_OPTIONS包含所有信息
                                item["select_LOCATION_OPTIONS"] = result['data']
                            elif actual_location:  # 只有当库位不为空时才添加
                                # 库位改变时，如果没有完整数据，则至少包含locationNo和id
                                item["select_LOCATION_OPTIONS"] = [{
                                    "locationNo": actual_location,
                                    "locationId": location_data.get('realInboundLocationNoId', '') if location_data else ''
                                }]
                            # 库位改变时才添加select_locationOptionLoading字段
                            item["select_locationOptionLoading"] = False
                        break
# ... existing code ...
# ... existing code ...
    def update_summary_row(self, transfer_id):
        """更新汇总行数据"""
        try:
            # 获取所有数据行的实际入库数量
            total_inbound_qty = 0
            children = self.transfer_detail_tree.get_children()
            
            # 遍历所有子项，跳过汇总行
            for child in children:
                values = self.transfer_detail_tree.item(child, 'values')
                # 检查是否为数据行（不是汇总行）
                if values and len(values) > 0 and str(values[0]) != "合计":
                    try:
                        # 第8列是实际入库数量
                        if len(values) > 7:
                            qty = int(values[7]) if values[7] else 0
                            total_inbound_qty += qty
                    except (ValueError, IndexError):
                        pass
            
            # 查找并更新汇总行
            for child in children:
                values = self.transfer_detail_tree.item(child, 'values')
                if values and len(values) > 0 and str(values[0]) == "合计":
                    # 更新汇总行的入库数量
                    new_values = list(values)
                    if len(new_values) > 7:
                        new_values[7] = str(total_inbound_qty)
                        self.transfer_detail_tree.item(child, values=new_values)
                    break
                    
        except Exception as e:
            print(f"更新汇总行失败: {e}")
# ... existing code ...
    # def on_quantity_change(self, row_idx, transfer_id,var=None):
    #     """实际入库数量修改时验证并更新"""
    #     try:
    #         raw_value = var.get() if var else self.quantity_spins[row_idx].get()
            
    #         if not raw_value.isdigit():
    #             return  # 静默忽略非法输入
            
    #         new_val = int(raw_value)
    #         if new_val < 0:
    #             new_val = 0
    #             var.set(new_val)  # 同步回Spinbox显示
            
    #         # 更新Treeview
    #         item_id = self.detail_item_ids[row_idx]
    #         current_values = list(self.transfer_detail_tree.item(item_id, 'values'))
    #         current_values[7] = new_val  # 第8列是实际入库数量
    #         self.transfer_detail_tree.item(item_id, values=current_values)
            
    #         # 更新缓存中的数据
    #         transfer_id = transfer_id
    #         if transfer_id in self.transfer_detail_cache:
    #             for i, item in enumerate(self.transfer_detail_cache[transfer_id]):
    #                 if i == row_idx:
    #                     item["inboundQuantity"] = new_val
    #                     break
                        
    #     except ValueError:
    #         # 恢复Spinbox显示为当前Treeview值
    #         item_id = self.detail_item_ids[row_idx]
    #         current_values = self.transfer_detail_tree.item(item_id, 'values')
    #         self.quantity_spins[row_idx].delete(0, tk.END)
    #         self.quantity_spins[row_idx].insert(0, current_values[8])
# ... existing code ...
    def on_quantity_change(self, row_idx, transfer_id, var=None):
        """实际入库数量修改时验证并更新"""
        try:
            # 读取输入
            if var is not None:
                raw_value = var.get()
            else:
                raw_value = self.quantity_spins[row_idx].get()

            # 非数字直接忽略（允许空/中间态）
            if raw_value is None or not str(raw_value).isdigit():
                return

            # 归一化到非负整数
            new_val = max(0, int(raw_value))
            if var is not None:
                try:
                    var.set(str(new_val))
                except Exception:
                    pass

            current_values = []

            # 更新Treeview
            if 0 <= row_idx < len(self.detail_item_ids):
                item_id = self.detail_item_ids[row_idx]
                try:
                    current_values = list(self.transfer_detail_tree.item(item_id, 'values'))
                except tk.TclError:
                    current_values = []

                if len(current_values) > 7:
                    current_values[7] = str(new_val)  # 第8列是实际入库数量
                    try:
                        self.transfer_detail_tree.item(item_id, values=current_values)
                    except tk.TclError:
                        pass

                # 更新缓存，仅当能取到拣货单号时
                if transfer_id and transfer_id in self.transfer_detail_cache:
                    if row_idx < len(self.transfer_detail_cache[transfer_id]):
                        self.transfer_detail_cache[transfer_id][row_idx]["inboundQuantity"] = new_val
                        
                # 更新汇总行的实际入库数量和
                self.update_summary_row(transfer_id)

        except Exception:
            # 异常时尽量回退到当前Treeview值
            try:
                if 0 <= row_idx < len(self.detail_item_ids):
                    item_id = self.detail_item_ids[row_idx]
                    current_values = self.transfer_detail_tree.item(item_id, 'values')
                    if len(current_values) > 8:
                        self.quantity_spins[row_idx].delete(0, tk.END)
                        self.quantity_spins[row_idx].insert(0, current_values[8])
            except Exception:
                pass
# ... existing code ...
    def refresh_table(self):
        """刷新表格数据（增加分页逻辑）"""
        # 计算当前页的数据范围
        start_index = (self.current_page - 1) * self.page_size
        end_index = min(start_index + self.page_size, len(self.filtered_data_all))
        
        # 获取当前页的数据
        self.current_page_data = self.filtered_data_all[start_index:end_index]
        
        """刷新表格数据"""
        # 清除Treeview中的数据
        self.tree.delete(*self.tree.get_children())
        self.checkbox_states = {}  # 清除复选框状态
        self.selected_items = set()  # 清除选中项
        # 设置交替行标签
        self.tree.tag_configure('oddrow', background='#F5F5F5')
        self.tree.tag_configure('evenrow', background='#FFFFFF')   

        
        # 在Treeview中插入数据
        for i,order in enumerate(self.current_page_data,1):
            tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
            values = (
                '☐',  # 复选框占位
                f"{start_index + i}",  # 序号
                order.get("transferNo", ""),
                order.get("pickingOrderNo", ""),
                order.get("moveWarehouseName", ""),
                order.get("removeWarehouseName", ""),
                order.get("transferType",""),
                order.get("transferStatus",""),
                order.get("createdAt", ""),
                order.get("createdByName", ""),
                order.get("auditBy", ""),
                order.get("auditDate", "")
            )
            print(order.get("id",0))
            self.tree.insert("", "end", values=values, iid=order.get("id",0),tags=tags)  # 使用调拨单ID作为行ID
        # 更新分页信息
        self.update_page_info()

    def update_page_info(self):
        """更新分页信息显示"""
        self.page_info_var.set(f"第 {self.current_page}/{self.total_pages} 页 (共 {len(self.filtered_data_all)} 条)")

    def go_to_page(self, page):
        """跳转到指定页码"""
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.refresh_table()

    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_table()

    def go_to_last_page(self):
        """跳转到最后一页"""
        self.go_to_page(self.total_pages)

    def jump_to_page(self):
        """跳转到用户输入的页码"""
        try:
            page = int(self.page_entry.get())
            self.go_to_page(page)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的页码数字")

    def setup_pagination_controls(self, parent):
        
        # 分页信息标签
        page_label = tk.Label(parent, textvariable=self.page_info_var, bg="#f0f0f0")
        page_label.pack(side=tk.LEFT, padx=10)
        
        # 分页按钮
        btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}

        tk.Button(parent, text="首页", 
                 command=lambda: self.go_to_page(1), **btn_style).pack(side=tk.LEFT, padx=2)
        
        tk.Button(parent, text="上一页", 
                 command=self.go_to_prev_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
        tk.Button(parent, text="下一页", 
                 command=self.go_to_next_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
        tk.Button(parent, text="尾页", 
                 command=self.go_to_last_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # 页码输入框
        tk.Label(parent, text="跳转到:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 0))
        self.page_entry = tk.Entry(parent, width=5)
        self.page_entry.pack(side=tk.LEFT, padx=2)
        
        tk.Button(parent, text="跳转", 
                 command=self.jump_to_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # 初始化分页信息
        self.update_page_info()

    def setup_action_buttons(self, parent):
        
        # 按钮样式
        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        
        # 按钮组
        buttons = [
            ("全选", self.select_all),
            ("全不选", self.deselect_all),
            ("反选", self.toggle_selection)
        ]
        
        for text, cmd in buttons:
            tk.Button(parent, text=text, command=cmd, **btn_style).pack(side=tk.LEFT, padx=5)
      # 添加批量签收和生成/打印调拨单按钮
        btn_style_special = {"bg": "#673AB7", "fg": "white", "padx": 10, "pady": 5, 
                           "bd": 0, "activebackground": "#5E35B1"}
        
        tk.Button(parent, text="批量签收", command=self.batch_sign_transfers_ui, 
                **btn_style_special).pack(side=tk.LEFT, padx=20)
        
        tk.Button(parent, text="生成打印调拨单", command=self.generate_transfer_list_ui, 
                **btn_style_special).pack(side=tk.LEFT, padx=5)
        
        tk.Button(parent, text="调拨单打印预览", command=self.print_preview,
                **btn_style_special).pack(side=tk.LEFT, padx=5)

    def select_all(self):
        """全选"""
        for order in self.current_page_data:
            order_id = order.get("transferNo")
            self.selected_items.add(order_id)
        
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            self.tree.item(item, values=('✓',) + self.tree.item(item, 'values')[1:])

    def deselect_all(self):
        """全不选"""
        self.selected_items.clear()
        
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            self.tree.item(item, values=('☐',) + self.tree.item(item, 'values')[1:])

    # def toggle_selection(self):
    #     """反选"""
    #     all_order_ids = set(order.get("transferNo") for order in self.current_page_data)
    #     new_selected_items = all_order_ids - self.selected_items
        
    #     # 更新选中项集合
    #     self.selected_items = new_selected_items
        
    #     # 更新Treeview中的复选框显示
    #     for item in self.tree.get_children():
    #         order_id = item
    #         if order_id in self.selected_items:
    #             self.tree.item(item, values=('✓',) + self.tree.item(item, 'values')[1:])
    #         else:
    #             self.tree.item(item, values=('☐',) + self.tree.item(item, 'values')[1:])
    def toggle_selection(self):
        """反选"""
        # 获取当前页面所有项
        all_items = self.tree.get_children()
        
        # 获取当前选中的项
        currently_selected = set()
        for item in all_items:
            if self.tree.item(item, 'values')[0] == '✓':
                currently_selected.add(item)
        
        # 计算需要选中的项（当前未选中的项）
        items_to_select = set(all_items) - currently_selected
        
        # 更新selected_items集合
        # 首先清除当前页面所有项的记录
        for item in all_items:
            order_no = self.tree.item(item, 'values')[1]  # transferNo在第2列
            self.selected_items.discard(order_no)
        
        # 添加需要选中的项到selected_items集合
        for item in items_to_select:
            order_no = self.tree.item(item, 'values')[1]  # transferNo在第2列
            self.selected_items.add(order_no)
        
        # 更新Treeview中的复选框显示
        for item in all_items:
            order_no = self.tree.item(item, 'values')[1]  # transferNo在第2列
            if order_no in self.selected_items:
                self.tree.item(item, values=('✓',) + self.tree.item(item, 'values')[1:])
            else:
                self.tree.item(item, values=('☐',) + self.tree.item(item, 'values')[1:])
    def refresh_data(self,data):

        # 先检查返回的数据是否有错误信息
        try:
            if isinstance(data, dict) and 'errorMsg' in data and data['errorMsg']:
                if '错误原因:token 已被顶下线' in data['errorMsg']:
                    # 显示下线提示
                    messagebox.showerror("登录状态异常", "您的账号已在其他地方登录，当前会话已失效。\n即将返回登录界面。")
                    
                    # 关闭主窗口
                    self.controller.root.destroy()
                    
                    # 重新打开登录窗口
                    from login_app import LoginApp
                    login_root = tk.Tk()
                    login_app = LoginApp(login_root)
                    login_root.mainloop()
                    return
        except Exception:
            pass

        """加载数据"""
        self.original_data = self.parse_and_convert_json(data)
        self.apply_filters()


# ... existing code ...
    def load_onshelf_persons(self):
        """加载上架人列表"""
        try:
            url = "https://xb.fy-carg.com/dcscloud.basedata//basedata/employees/getEmpByRoleCode?roleCode=SJR"
            response = self.controller.session.get(url, headers=HEADERS)
            
            # 检查登录状态
            if not self._check_response(response):
                return
                
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    self.onshelf_listbox.delete(0, tk.END)
                    for employee in data["data"]:
                        employee_name = employee.get("EMPLOYEE_NAME", "")
                        if employee_name:
                            self.onshelf_listbox.insert(tk.END, employee_name)
        except Exception as e:
            print(f"加载上架人列表失败: {e}")

    def print_preview(self):
        """调拨单打印预览 - 获取选中行并打开预览窗口"""
        # 从 treeview 中获取用户已选择的调拨单号
        transfer_nos = []
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == '✓':  # 检查是否选中
                transfer_no = self.tree.item(item, 'values')[2]  # 调拨单号在第2列
                if transfer_no:
                    transfer_nos.append(transfer_no)
        
        if not transfer_nos:
            messagebox.showwarning("警告", "请至少选择一条调拨单记录")
            return
        
        # 获取当前选择的调入仓库名称
        move_warehouse_name = self.movewarehouse_var.get()
        if move_warehouse_name == "全部":
            move_warehouse_name = ""
        
        # 打开打印预览窗口
        TransferPrintPreviewWindow(self.winfo_toplevel(), transfer_nos, self, move_warehouse_name)

    def get_selected_onshelf_persons(self):
        """获取选中的上架人"""
        selected_indices = self.onshelf_listbox.curselection()
        selected_persons = [self.onshelf_listbox.get(i) for i in selected_indices]
        return ",".join(selected_persons) if selected_persons else ""

#     def temp_storage(self):
#         """暂存功能"""
#         # 获取选中的调拨单
#         selected_items = self.tree.selection()
#         if not selected_items:
#             messagebox.showwarning("警告", "请先选择一条调拨单记录")
#             return
            
#         # 获取选中的调拨单信息
#         item = selected_items[0]
#         values = self.tree.item(item, 'values')
        
#         # 获取调拨单ID和详情
#         transfer_id = item
#         transfer_no = values[2]  # 调拨单号
#         movewarehouse_id = values[4]  # 调入方
#         removewarehouse_id = values[5]  # 调出方
#         transfer_type_text = values[6]  # 调拨类型
        
#         # 获取上架人
#         onshelf_by = self.get_selected_onshelf_persons() or ""
#         # if not onshelf_by:
#         #     messagebox.showwarning("警告", "请至少选择一个上架人")
#         #     return
            
#         # 获取调拨类型代码
#         transfer_type = self.transfer_type_mapping.get(transfer_type_text, "")
        
#         # 获取详情数据
#         if transfer_id not in self.transfer_detail_cache:
#             messagebox.showwarning("警告", "未找到调拨单详情数据")
#             return
            
#         detail_data = self.transfer_detail_cache[transfer_id]
        
#         # 构造POST数据
#         post_data = {
#             "detailDtoListDelete": [],
#             "id": int(transfer_id),
#             "moveWarehouseId": movewarehouse_id,
#             "onshelf_by": onshelf_by,
#             "removeWarehouseId": removewarehouse_id,
#             "transferNo": transfer_no,
#             "transferType": transfer_type,
#             "checkStatus": 10041001,
#             "detailDtoList": detail_data
#         }
        
#         # 发送POST请求
#         url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/tempStorage"
#         try:
#             response = self.controller.session.post(url, headers=HEADERS, data=json.dumps(post_data))
            
#             # 检查登录状态
#             if not self._check_response(response):
#                 return
                
#             if response.status_code == 200:
#                 result = response.json()
#                 if result.get("success"):
#                     messagebox.showinfo("成功", "暂存成功")
#                 else:
#                     messagebox.showerror("失败", f"暂存失败: {result.get('message', '未知错误')}")
#             else:
#                 messagebox.showerror("错误", f"请求失败，状态码: {response.status_code}")
#         except Exception as e:
#             messagebox.showerror("错误", f"请求异常: {str(e)}")

#     def transfer_in(self):
#         """入库功能"""
#         # 获取选中的调拨单
#         selected_items = self.tree.selection()
#         if not selected_items:
#             messagebox.showwarning("警告", "请先选择一条调拨单记录")
#             return
            
#         # 获取选中的调拨单信息
#         item = selected_items[0]
#         values = self.tree.item(item, 'values')
        
#         # 获取调拨单ID和详情
#         transfer_id = item
#         transfer_no = values[2]  # 调拨单号
#         movewarehouse_id = values[4]  # 调入方
#         removewarehouse_id = values[5]  # 调出方
#         transfer_type_text = values[6]  # 调拨类型
        
#         # 获取上架人
#         onshelf_by = self.get_selected_onshelf_persons() or ""
#         # if not onshelf_by:
#         #     messagebox.showwarning("警告", "请至少选择一个上架人")
#         #     return
            
#         # 获取调拨类型代码
#         transfer_type = self.transfer_type_mapping.get(transfer_type_text, "")
        
#         # 获取详情数据
#         if transfer_id not in self.transfer_detail_cache:
#             messagebox.showwarning("警告", "未找到调拨单详情数据")
#             return
            
#         detail_data = self.transfer_detail_cache[transfer_id]
        
#         # 构造POST数据
#         post_data = {
#             "detailDtoListDelete": [],
#             "id": int(transfer_id),
#             "moveWarehouseId": movewarehouse_id,
#             "onshelf_by": onshelf_by,
#             "removeWarehouseId": removewarehouse_id,
#             "transferNo": transfer_no,
#             "transferType": transfer_type,
#             "checkStatus": 10041001,
#             "detailDtoList": detail_data
#         }
        
#         # 发送POST请求
#         url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/transferInbound"
#         try:
#             response = self.controller.session.post(url, headers=HEADERS, data=json.dumps(post_data))
            
#             # 检查登录状态
#             if not self._check_response(response):
#                 return
                
#             if response.status_code == 200:
#                 result = response.json()
#                 if result.get("success"):
#                     messagebox.showinfo("成功", "入库成功")
#                     # 刷新数据
#                     self.transfer_query()
#                 else:
#                     messagebox.showerror("失败", f"入库失败: {result.get('message', '未知错误')}")
#             else:
#                 messagebox.showerror("错误", f"请求失败，状态码: {response.status_code}")
#         except Exception as e:
#             messagebox.showerror("错误", f"请求异常: {str(e)}")
# # ... existing code ...
# ... existing code ...
    def prepare_detail_data_for_submission(self, detail_data):
        """为提交准备详情数据，确保所有必要字段都存在"""
        for item in detail_data:
            
            # 确保select_LOCATION_OPTIONS字段存在
            if "select_LOCATION_OPTIONS" not in item:
                # 如果realInboundLocationNo存在，创建包含该信息的字典
                real_location = item.get("realInboundLocationNo")
                real_location_id = item.get("realInboundLocationNoId")
                if real_location:  # 只有当库位不为空时才添加
                    # 默认情况下，select_LOCATION_OPTIONS只包含locationNo和id字段
                    item["select_LOCATION_OPTIONS"] = [{
                        "locationNo": real_location,
                        "locationId": real_location_id
                    }]
                else:
                    # 如果没有库位信息，也添加一个空的select_LOCATION_OPTIONS
                    return
            else:
                # 如果select_LOCATION_OPTIONS字段已存在，确保其包含locationNo和id字段
                if "locationNo" not in item["select_LOCATION_OPTIONS"][0]:
                    item["select_LOCATION_OPTIONS"][0]["locationNo"] = item.get("realInboundLocationNo")
                if "locationId" not in item["select_LOCATION_OPTIONS"][0]:
                    item["select_LOCATION_OPTIONS"][0]["locationId"] = item.get("realInboundLocationNoId")
            # select_locationOptionLoading字段只在库位改变时才有，所以这里不添加
        
        return detail_data
# ... existing code ...
    def temp_storage(self):
        """暂存功能"""
        # 获取选中的调拨单
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择一条调拨单记录")
            return
            
        # 获取选中的调拨单信息
        item = selected_items[0]
        values = self.tree.item(item, 'values')
        
        # 检查调拨状态，只有"待上架"状态才能进行暂存操作
        transfer_status = values[7]  # 调拨状态在第8列
        if transfer_status != "待上架":
            messagebox.showwarning("警告", "只有状态为'待上架'的调拨单才能进行暂存操作")
            return
        
        # 获取调拨单ID和详情
        transfer_id = item
        transfer_no = values[2]  # 调拨单号
        movewarehouse_name = values[4]  # 调入方名称
        removewarehouse_name = values[5]  # 调出方名称
        
        # 通过映射字典获取仓库ID
        movewarehouse_id = self.WAREHOUSE_MAPPING.get(movewarehouse_name, {}).get("warehouseId")
        removewarehouse_id = self.WAREHOUSE_MAPPING.get(removewarehouse_name, {}).get("warehouseId")
        
        # 如果映射字典中没有找到，尝试在原始数据中查找
        if movewarehouse_id is None or removewarehouse_id is None:
            for record in self.original_data:
                if str(record.get("id")) == str(transfer_id):
                    # 获取调拨单详情数据
                    if movewarehouse_id is None:
                        movewarehouse_id = record.get("moveWarehouseId")
                    if removewarehouse_id is None:
                        removewarehouse_id = record.get("removeWarehouseId")
                    break
        
        transfer_type_text = values[6]  # 调拨类型
        
        # 获取上架人
        onshelf_by = self.get_selected_onshelf_persons()
        if not onshelf_by:
            messagebox.showwarning("警告", "请至少选择一个上架人")
            return
            
        # 获取调拨类型代码
        transfer_type = self.transfer_type_mapping.get(transfer_type_text, "")
        
        # 获取详情数据
        if transfer_id not in self.transfer_detail_cache:
            messagebox.showwarning("警告", "未找到调拨单详情数据")
            return
            
        detail_data = self.transfer_detail_cache[transfer_id]
        # 准备详情数据，确保所有必要字段都存在
        detail_data = self.prepare_detail_data_for_submission(detail_data)
        
        # 获取乐观锁 recordVersion（取自查询数据 header 中的 recordVersion 字段）
        record_version = ""
        try:
            record_version = self.transfer_data.get("header", {}).get("recordVersion", "")
        except Exception:
            record_version = ""
        
        # 构造POST数据
        post_data = {
            "detailDtoListDelete": [],
            "id": int(transfer_id),
            "moveWarehouseId": movewarehouse_id,
            "onshelf_by": onshelf_by,
            "recordVersion": record_version,
            "removeWarehouseId": removewarehouse_id,
            "transferNo": transfer_no,
            "transferType": transfer_type,
            "checkStatus": 10041001,
            "detailDtoList": detail_data
        }
        
        # 发送POST请求
        url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/tempStorage"
        try:
            #response = self.controller.session.post(url, headers=HEADERS, data=json.dumps(post_data))
            print(json.dumps(post_data,indent=4,ensure_ascii=False,sort_keys=True))
            # # 检查登录状态
            # if not self._check_response(response):
            #     return
                
            # if response.status_code == 200:
            #     result = response.json()
            #     if result.get("success"):
            #         messagebox.showinfo("成功", "暂存成功")
            #     else:
            #         messagebox.showerror("失败", f"暂存失败: {result.get('message', '未知错误')}")
            # else:
            #     messagebox.showerror("错误", f"请求失败，状态码: {response.status_code}")
        except Exception as e:
            messagebox.showerror("错误", f"请求异常: {str(e)}")
# ... existing code ...
# ... existing code ...
    def transfer_in(self):
        """入库功能"""
        # 获取选中的调拨单
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择一条调拨单记录")
            return
            
        # 获取选中的调拨单信息
        item = selected_items[0]
        values = self.tree.item(item, 'values')
        
        # 检查调拨状态，只有"待上架"状态才能进行入库操作
        transfer_status = values[7]  # 调拨状态在第8列
        if transfer_status != "待上架":
            messagebox.showwarning("警告", "只有状态为'待上架'的调拨单才能进行入库操作")
            return
        
        # 获取调拨单ID和详情
        transfer_id = item
        transfer_no = values[2]  # 调拨单号
        movewarehouse_name = values[4]  # 调入方名称
        removewarehouse_name = values[5]  # 调出方名称
        
        # 通过映射字典获取仓库ID
        movewarehouse_id = self.WAREHOUSE_MAPPING.get(movewarehouse_name, {}).get("warehouseId")
        removewarehouse_id = self.WAREHOUSE_MAPPING.get(removewarehouse_name, {}).get("warehouseId")
        
        # 如果映射字典中没有找到，尝试在原始数据中查找
        if movewarehouse_id is None or removewarehouse_id is None:
            for record in self.original_data:
                if str(record.get("id", "")) == str(transfer_id):
                    if movewarehouse_id is None:
                        movewarehouse_id = record.get("moveWarehouseId")
                    if removewarehouse_id is None:
                        removewarehouse_id = record.get("removeWarehouseId")
                    break
        
        transfer_type_text = values[6]  # 调拨类型
        
        # 获取上架人
        onshelf_by = self.get_selected_onshelf_persons()
        if not onshelf_by:
            messagebox.showwarning("警告", "请至少选择一个上架人")
            return
            
        # 获取调拨类型代码
        transfer_type = self.transfer_type_mapping.get(transfer_type_text, "")
        
        # 获取详情数据
        if transfer_id not in self.transfer_detail_cache:
            messagebox.showwarning("警告", "未找到调拨单详情数据")
            return
            
        detail_data = self.transfer_detail_cache[transfer_id]

        # 检查实际入库库位是否为空
        empty_location_items = []
        for i, item in enumerate(detail_data):
            real_inbound_location = item.get("realInboundLocationNo", "") or item.get("inboundLocationNo", "")
            if not real_inbound_location:
                # 获取产品信息用于提示
                part_code = item.get("partCode", f"第{i+1}项")
                part_name = item.get("partName", "")
                empty_location_items.append(f"{part_code} {part_name}")
        
        if empty_location_items:
            messagebox.showwarning("警告", f"以下产品的实际入库库位为空，不能执行暂存操作：\n" + "\n".join(empty_location_items))
            return

        # 准备详情数据，确保所有必要字段都存在
        detail_data = self.prepare_detail_data_for_submission(detail_data)
        
        # 获取乐观锁 recordVersion（取自查询数据 header 中的 recordVersion 字段）
        record_version = ""
        try:
            record_version = self.transfer_data.get("header", {}).get("recordVersion", "")
        except Exception:
            record_version = ""
             
        # 构造POST数据
        post_data = {
            "detailDtoListDelete": [],
            "id": int(transfer_id),
            "moveWarehouseId": movewarehouse_id,
            "onshelf_by": onshelf_by,
            "recordVersion": record_version,
            "removeWarehouseId": removewarehouse_id,
            "transferNo": transfer_no,
            "transferType": transfer_type,
            "checkStatus": 10041001,
            "detailDtoList": detail_data
        }
        
        # 发送POST请求
        url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/transferInbound"
        try:
            #response = self.controller.session.post(url, headers=HEADERS, data=json.dumps(post_data))
            print(json.dumps(post_data,indent=4,ensure_ascii=False,sort_keys=True))
            # # 检查登录状态
            # if not self._check_response(response):
            #     return
                
            # if response.status_code == 200:
            #     result = response.json()
            #     if result.get("success"):
            #         messagebox.showinfo("成功", "入库成功")
            #         # 刷新数据
            #         self.transfer_query()
            #     else:
            #         messagebox.showerror("失败", f"入库失败: {result.get('message', '未知错误')}")
            # else:
            #     messagebox.showerror("错误", f"请求失败，状态码: {response.status_code}")
        except Exception as e:
            messagebox.showerror("错误", f"请求异常: {str(e)}")
# ... existing code ...
    # 4. 添加批量签收UI函数
    def batch_sign_transfers_ui(self):
        """批量签收调拨单UI入口"""
        # 检查是否有选中的调拨单
        if not self.selected_items:
            messagebox.showwarning("警告", "请至少选择一条调拨单记录")
            return
            
        # 确认是否要批量签收
        if not messagebox.askyesno("确认", "确定要批量签收选中的调拨单吗？"):
            return
            
        # 获取选中的调拨单ID和单号
        transfer_ids = []
        transfer_nos = []
        
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == '✓':  # 检查是否选中
                transfer_id = item  # 行ID就是调拨单ID
                transfer_no = self.tree.item(item, 'values')[2]  # 调拨单号在第2列
                transfer_ids.append(transfer_id)
                transfer_nos.append(transfer_no)
                
        if not transfer_ids:
            messagebox.showwarning("警告", "未找到有效的调拨单ID")
            return
            
        # 在新线程中执行签收操作，避免界面冻结
        threading.Thread(target=self._batch_sign_in_thread, 
                        args=(transfer_ids, transfer_nos)).start()
    
    # 5. 添加批量签收线程函数
    def _batch_sign_in_thread(self, transfer_ids, transfer_nos):
        """在线程中执行批量签收操作"""
        try:
            
            # 执行批量签收
            success, message = self.batch_sign_transfers(transfer_ids, transfer_nos)
            
            # 处理签收结果
            if success:
                self.controller.after(0, lambda: (self.transfer_status_var.set("待上架"), self.transfer_query(), self._sign_complete(f"签收成功: {message}")))
            else:
                self.controller.after(0, lambda: self._sign_complete(f"签收结果: {message}"))
                
        except Exception as e:
            self.controller.after(0, lambda: self._sign_complete(f"签收失败: {str(e)}"))
    
    # 6. 添加签收完成处理函数
    def _sign_complete(self, message):
        """签收完成后的处理"""
        self.controller.hide_status()
        
        # 根据消息内容显示不同类型的对话框
        if "成功" in message:
            messagebox.showinfo("签收完成", message)
            # 刷新数据
            # self.transfer_query()
        elif "未查询到" in message:
            messagebox.showwarning("提示", message)
        else:
            messagebox.showerror("签收结果", message)
    
    # 7. 添加批量签收函数
    def batch_sign_transfers(self, transfer_ids, transfer_nos):
        """批量签收调拨单"""
        if not transfer_ids or not transfer_nos or len(transfer_ids) != len(transfer_nos):
            print("没有可签收的调拨单或数据不匹配")
            return False, "没有可签收的调拨单或数据不匹配"
        
        sign_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/Sign"
        success_count = 0
        failed_count = 0
        error_messages = []
        
        for transfer_id, transfer_no in zip(transfer_ids, transfer_nos):
            data = {
                "transferId": transfer_id,
                "billNo": transfer_no
            }
            
            try:
                response = self.controller.session.post(sign_url, headers=HEADERS, data=json.dumps(data))


                # 检查登录状态
                if not self._check_response(response):
                    return
                response.raise_for_status()
                result = response.json()                
                if result.get('resultCode') == 200 and result.get('success') == True:
                    success_count += 1
                    print(f"调拨单 {transfer_no} 签收成功")
                else:
                    failed_count += 1
                    error_message = f"调拨单 {transfer_no} 签收失败: {result.get('errMsg', '未知错误')}"
                    error_messages.append(error_message)
                    print(error_message)
                    
            except Exception as e:
                failed_count += 1
                error_message = f"调拨单 {transfer_no} 签收异常: {str(e)}"
                error_messages.append(error_message)
                print(error_message)
        
        # 构建结果消息
        if success_count > 0 and failed_count == 0:
            result_message = f"所有调拨单签收成功，共 {success_count} 个"
            return True, result_message
        elif success_count > 0 and failed_count > 0:
            result_message = f"部分调拨单签收成功，成功 {success_count} 个，失败 {failed_count} 个"
            if error_messages:
                result_message += f"失败原因: {'; '.join(error_messages[:3])}"
                if len(error_messages) > 3:
                    result_message += "..."
            return False, result_message
        else:
            result_message = f"所有调拨单签收失败，共 {failed_count} 个"
            if error_messages:
                result_message += f"失败原因: {'; '.join(error_messages[:3])}"
                if len(error_messages) > 3:
                    result_message += "..."
            return False, result_message
    
    # 8. 添加生成调拨单UI函数
    def generate_transfer_list_ui(self):
        """生成打印调拨单UI入口"""
        # 获取当前筛选条件
        move_warehouse = self.movewarehouse_var.get()
        remove_warehouse = self.removewarehouse_var.get()
        start_time = self.start_cal.get() if self.start_cal.get() else ""
        end_time = self.end_cal.get() if self.end_cal.get() else ""
        status = self.transfer_status_var.get()
        transfer_no = self.transfer_no_var.get()
        part_no = self.part_no_var.get()
        part_name = self.part_name_var.get()
        
        # 验证必填字段
        if not move_warehouse and not remove_warehouse and not transfer_no and not part_no and not part_name:
            messagebox.showerror("错误", "请至少选择调入仓库/调出仓库或输入调拨单号/产品编码/产品名称")
            return
        
        # 验证日期
        if start_time and end_time:
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d')
                end_dt = datetime.strptime(end_time, '%Y-%m-%d')
                if start_dt > end_dt:
                    messagebox.showerror("错误", "开始日期不能晚于结束日期")
                    return
            except ValueError:
                messagebox.showerror("错误", "日期格式不正确")
                return
        
        # 在新线程中执行生成操作，避免界面冻结
        self.controller.show_status("正在准备生成调拨单...")
        
        thread = threading.Thread(target=self._generate_in_thread, 
                                args=(move_warehouse, remove_warehouse, start_time, end_time, 
                                     status, transfer_no, part_no, part_name))
        thread.daemon = True
        thread.start()
    
    # 9. 添加生成调拨单线程函数
    def _generate_in_thread(self, move_warehouse, remove_warehouse, start_time, end_time, 
                          status, transfer_no="", part_no="", part_name=""):
        try:
            self.controller.show_status("正在生成调拨单...")
            
            # 执行生成调拨单
            filename = self.create_workbook(move_warehouse, remove_warehouse, start_time, end_time, 
                                         status, transfer_no, part_no, part_name)
            
            if filename:
                self.controller.after(0, lambda: self._generation_complete(f"生成成功: {filename}"))
            else:
                self.controller.after(0, lambda: self._generation_complete("生成失败: 未查询到数据或发生错误"))
                
        except Exception as e:
            self.controller.after(0, lambda: self._generation_complete(f"生成失败: {str(e)}"))

    # 10. 添加生成完成处理函数
    def _generation_complete(self, message):
        """生成完成后的处理"""
        self.controller.hide_status()
        
        if "成功" in message:
            # 提取文件名并尝试打印
            try:
                filename = message.split(": ")[1] if ": " in message else ""
                if filename and os.path.exists(filename):
                    # 使用独立线程处理打印确认，避免阻塞
                    confirm_thread = threading.Thread(target=self._handle_print_confirmation, args=(filename,))
                    confirm_thread.daemon = True
                    confirm_thread.start()
            except Exception as print_err:
                print(f"打印过程中发生错误: {print_err}")
                self.controller.after(0, lambda: messagebox.showerror("错误", f"打印过程中发生错误: {print_err}"))
            
            # 在主线程中显示完成信息
            self.controller.after(0, lambda: messagebox.showinfo("完成", message))
        else:
            self.controller.after(0, lambda: messagebox.showerror("错误", message))
    
    def _handle_print_confirmation(self, filename):
        """在独立线程中处理打印确认"""
        # 使用after方法在主线程中显示对话框
        result = []
        lock = threading.Lock()
        event = threading.Event()
        
        def ask_confirmation():
            try:
                answer = messagebox.askyesno("打印确认", f"是否打印文件 {os.path.basename(filename)}？")
                with lock:
                    result.append(answer)
            finally:
                event.set()
        
        # 在主线程中执行对话框显示
        self.controller.after(0, ask_confirmation)
        event.wait()  # 等待用户响应
        
        with lock:
            if result and result[0]:  # 用户确认打印
                print("正在尝试打印文件...")
                self.controller.after(0, lambda: self.controller.show_status("正在打印文件，请稍候..."))
                
                # 在新线程中执行打印操作
                print_thread = threading.Thread(target=self._print_in_thread, args=(filename,))
                print_thread.daemon = True
                print_thread.start()
            else:
                print("用户取消了打印操作") 

    # 添加一个新方法用于在线程中执行打印
    def _print_in_thread(self, filename):
        try:
            print_result = self.print_excel_file(filename)
            if print_result:
                print("文件已成功发送到打印机")
                self.controller.after(0, lambda: messagebox.showinfo("打印状态", "文件已成功发送到打印机"))
            else:
                print("文件打印失败")
                self.controller.after(0, lambda: messagebox.showerror("打印状态", "文件打印失败"))
        except Exception as print_err:
            print(f"打印过程中发生错误: {print_err}")
            self.controller.after(0, lambda: messagebox.showerror("错误", f"打印过程中发生错误: {print_err}"))
    
    # 11. 添加获取调拨单明细函数
    def get_transfer_detail(self, transferNos):
        """批量获取调拨单明细"""
        if not isinstance(transferNos, list):
            transferNos = [transferNos]
            
        PrintDetail_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/getPrintList"
        params = {
            'searchType': 'inbound',
            'createdByName': '',
            'transferNos': ",".join(f"'{x}'" for x in transferNos)
        }

        try:
            response = self.controller.session.get(PrintDetail_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"查询调拨单{transferNos}明细失败: {e}")
            return None
    
    # 12. 添加查询库存函数
    def query_inventory(self, storage_code="SQ", page_num=1, page_size=500, **kwargs):
        """通用库存查询函数"""
        inventory_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/asicDataQuery/inventoryQuery/location/query"
        
        # 基本参数
        params = {
            'storage_code': storage_code,
            'limit': str(page_size),
            'pageNum': str(page_num)
        }
        
        # 添加其他参数
        for key, value in kwargs.items():
            if value is not None:
                params[key] = value
        
        try:
            response = self.controller.session.get(inventory_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return
            response.raise_for_status()
            return response.json()
        except Exception as e:
            param_info = ', '.join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
            print(f"查询库存失败 [{param_info}]: {e}")
            return None
    
    # 13. 添加查询所有库存函数
    def query_all_inventory(self, storage_code="SQ", **kwargs):
        """查询所有库存数据，自动处理分页"""
        page_num = 1
        page_size = 500
        all_rows = []
        total_pages = 1
        
        while page_num <= total_pages:
            result = self.query_inventory(storage_code, page_num, page_size, **kwargs)
            
            if not result or 'data' not in result:
                break
                
            # 提取当前页数据
            if 'rows' in result['data']:
                all_rows.extend(result['data']['rows'])
            
            # 计算总页数
            if page_num == 1 and 'total' in result['data']:
                total_count = result['data']['total']
                total_pages = (total_count + page_size - 1) // page_size
            
            page_num += 1
        
        # 构造合并后的结果
        merged_result = {'data': {'rows': all_rows}}
        if result and 'data' in result and 'total' in result['data']:
            merged_result['data']['total'] = result['data']['total']
        
        return merged_result
    
    # 14. 添加查询销售明细函数
    def query_order_by_code(self, item_code, storage_id=11):
        """构造销售明细查询URL并获取销售明细数据"""
        now = datetime.now()
        starttime = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        endtime = now.strftime('%Y-%m-%d')
        inventoryQuery_url = "https://xb.fy-carg.com/dmscloud.part/salesProfit/queryDetail"
        params = {
            "bill_at_begin": starttime,
            "bill_at_end": endtime,
            "part_code": item_code,
            "storage_id": storage_id,
            "limit": 50,
            "pageNum": "1",
        }
        try:
            response = self.controller.session.get(inventoryQuery_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return

            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"查询{item_code}销售明细失败: {e}")
            return None
    
    # 15. 添加获取最近销售库位函数
    def get_recent_sale_location(self, response):
        """获取最近销售库位信息"""
        # 获取销售明细列表
        sales_list = response.get('data', {}).get('rows', [])
        if not sales_list:
            return "无销售记录"
        recent_record = max(
            (r for r in sales_list if r.get('bill_date')),
            key=lambda x: x['bill_date'],
            default=None
        )
        if not recent_record:
            return "无有效记录"
        return f"{recent_record.get('location_no', '未知库位')}【{int(recent_record.get('NUM', 0))}】\n{recent_record.get('bill_date', '未知日期')}"
    
    # 16. 添加自动调整行高函数
    def auto_adjust_rows(self, ws):
        """自动调整Excel行高"""
        DEFAULT_ROW_HEIGHT = 16
        
        # 获取所有合并单元格的行号
        merged_rows = set()
        for merged_range in ws.merged_cells.ranges:
            for row in range(merged_range.min_row, merged_range.max_row + 1):
                merged_rows.add(row)
        
        for row in ws.iter_rows():
            row_num = row[0].row
            
            # 跳过标题行和合并单元格所在行
            if row_num in (1, 2, 3) or row_num in merged_rows:
                continue
                
            # 获取所有非空单元格的文本长度
            text_lengths = []
            for cell in row:
                if cell.value is not None and str(cell.value).strip():
                    text_lengths.append(len(str(cell.value)))
                    
            # 如果没有有效内容，设置默认行高
            if not text_lengths:
                ws.row_dimensions[row_num].height = DEFAULT_ROW_HEIGHT
                continue
                
            # 计算最大字符数和所需行数
            max_chars = max(text_lengths)
            lines_split = max(
                len(str(cell.value).split('\n')) 
                for cell in row
            )
            lines_chars = round((max_chars // 16) + 1)  # 每行大约16个字符
            lines = max(lines_split, lines_chars)
            new_height = max(DEFAULT_ROW_HEIGHT, lines * DEFAULT_ROW_HEIGHT)
            ws.row_dimensions[row_num].height = new_height
    
    # 17. 添加获取所有库存数据函数
    def get_all_stock_data(self, storage_code="SQ"):
        """获取指定仓库的所有库存数据"""
        return self.query_all_inventory(storage_code=storage_code)
    
    # 18. 添加构建库存索引函数
    def build_stock_indices(self, stock_data):
        """构建库存数据的索引结构（只保留必要字段）"""
        location_index = defaultdict(list)
        part_code_index = defaultdict(list)
        
        if stock_data and 'data' in stock_data and 'rows' in stock_data['data']:
            for item in stock_data['data']['rows']:
                # 只保留必要的字段
                simplified_item = {
                    'part_code': item.get('part_code'),
                    'location_accessories_number': item.get('location_accessories_number'),
                    'location_no': item.get('location_no')
                }
                
                # 按库位索引
                location_no = simplified_item.get('location_no')
                if location_no:
                    location_index[location_no].append(simplified_item)
                
                # 按产品编码索引
                part_code = simplified_item.get('part_code')
                if part_code:
                    part_code_index[part_code].append(simplified_item)
        
        return {
            'location': dict(location_index),
            'part_code': dict(part_code_index)
        }
    
    # 19. 添加查找空库位函数
    def find_empty_locations(self, storage_code):
        """查找空库位 - 根据仓库代码选择对应的库位生成方法"""
        # 根据仓库代码选择对应的库位生成方法
        if storage_code == 'SQ':
            all_locations = self.generate_storage_locations_set_for_sq(3, 56)
        elif storage_code == 'ZZ':
            all_locations = self.generate_storage_locations_set_for_zz()
        elif storage_code in ('XA', 'XA-XJ'):
            all_locations = self.generate_storage_locations_set_for_xa()
        elif storage_code == 'LZ':
            all_locations = self.generate_storage_locations_set_for_lz()
        elif storage_code == 'ZMD':
            all_locations = self.generate_storage_locations_set_for_zmd()
        elif storage_code == 'LY':
            all_locations = self.generate_storage_locations_set_for_ly()
        elif storage_code == 'YL':
            all_locations = self.generate_storage_locations_set_for_yl()
        elif storage_code == 'YC':
            all_locations = self.generate_storage_locations_set_for_yc()
        else:
            # CC/YT/XN 等未专门配置的仓库，默认使用商丘库逻辑
            all_locations = self.generate_storage_locations_set_for_sq(3, 56)
        
        # 从系统获取已占用的库位集合
        occupied_locations = self.get_occupied_locations_from_erp(storage_code)
        
        # 使用集合差集操作计算空库位
        empty_locations_set = set(all_locations) - occupied_locations
        
        # 转换为排序后的列表
        empty_locations = sorted(empty_locations_set)
        
        return empty_locations
    
    # 20. 添加获取已占用库位函数
    def get_occupied_locations_from_erp(self, storage_code="SQ"):
        """从ERP系统获取已占用的库位集合"""
        # 使用通用查询函数，查询分类为前挡的库存
        json_data = self.query_all_inventory(storage_code=storage_code, categoryTwo='90921001')
        
        if json_data and 'data' in json_data and 'rows' in json_data['data']:
            localno_list = set(item['location_no'] for item in json_data['data']['rows'])
            return localno_list
        return set()

    def inboundDetail_query(self, transferId: int):
        """构造调拨明细查询URL并获取调拨明细数据"""
        inboundDetail_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail"
        params = {
            'transferId': transferId
        }
        try:
            response = self.controller.session.get(inboundDetail_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"查询调拨明细失败: {e}")
            return None

    # 21. 添加创建Excel工作簿函数
    def create_workbook(self, move_warehouse_name="", remove_warehouse_name="", start_time="", 
                      end_time="", status_name="", transfer_no="", part_no="", part_name=""):
        """创建Excel工作簿并填充数据"""
        try:
            # 获取仓库ID和状态代码
            move_warehouse_id = ""
            remove_warehouse_id = ""
            
            if move_warehouse_name != "全部" and move_warehouse_name:
                move_warehouse_id = self.controller.options.get(move_warehouse_name, "")
                
            if remove_warehouse_name != "全部" and remove_warehouse_name:
                remove_warehouse_id = self.controller.options.get(remove_warehouse_name, "")
            
            storage_code = self.WAREHOUSE_MAPPING.get(move_warehouse_name, {}).get("storage_code", "SQ")
            status_code = self.transfer_status_mapping.get(status_name, "") if status_name != "全部" else ""
            
                
            # 从treeview中获取用户已选择的调拨单ID和调拨单号
            transferIds = []
            transferNos = []
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == '✓':  # 检查是否选中
                    transfer_id = item  # 行ID就是调拨单ID
                    transfer_no = self.tree.item(item, 'values')[2]  # 调拨单号在第2列
                    transferIds.append(transfer_id)
                    transferNos.append(transfer_no)
            
            if not transferIds:
                messagebox.showwarning("警告", "请至少选择一条调拨单记录")
                return None
            
            # 获取所有库存数据并创建索引
            all_stock_data = self.get_all_stock_data(storage_code)
            stock_indices = self.build_stock_indices(all_stock_data)
            
            # 查找空库位
            empty_locations = self.find_empty_locations(storage_code)
            
            # 创建工作簿
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "调拨清单"
            
            # 创建隐藏工作表存储空库位数据
            hidden_ws = wb.create_sheet("空库位数据")
            hidden_ws.sheet_state = 'hidden'  # 隐藏工作表
            
            # 将空库位数据写入隐藏表的A列
            for i, location in enumerate(empty_locations, 1):
                hidden_ws.cell(row=i, column=1, value=location)
            
            # 设置打印标题行
            ws.print_title_rows = '4:4'
            ws.print_options.horizontalCentered = True
            
            # 批量查询所有调拨单明细
            all_detail_data = self.get_transfer_detail(transferNos)
            if not all_detail_data or 'data' not in all_detail_data:
                print("未查询到调拨单明细数据")
                return None
            
            # 按调拨单号分组数据
            transfer_details = {}
            for item in all_detail_data['data']:
                transfer_no = item.get('transferNo')
                if transfer_no not in transfer_details:
                    transfer_details[transfer_no] = []
                transfer_details[transfer_no].append(item)
                
            # 定义表头
            headers_str = ["品牌", "产品名称", "分类", "产品编码", "入库\n库位",
                          "入库\n数量", "指示\n库位", "调拨前\n库存数", "3月内最近\n出库信息"]
            
            current_row = 1
            
            # 添加标题行
            ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
            title_cell = ws.cell(row=current_row, column=1, value="调拨清单")
            title_cell.font = Font(bold=True, size=20)
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[current_row].height = 30
            current_row += 1
            
            # 处理每个调拨单
            for transferNo, transferId in zip(transferNos, transferIds):
                # 获取当前调拨单的数据
                detail_data = {'data': transfer_details.get(transferNo, [])}
                if not detail_data['data']:
                    continue
                    
                shelf_data = self.inboundDetail_query(transferId)
                
                # 添加空行分隔
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                cell=ws.cell(row=current_row, column=1, 
                                value="·················································")
                current_row += 1
                # 添加调拨单分隔信息
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                transfer_data = detail_data['data'][0] if len(detail_data['data']) > 0 else {}
                remove_warehouse = transfer_data.get('removeWarehouseName', '')
                move_warehouse = transfer_data.get('moveWarehouseName', '')
                info_cell = ws.cell(row=current_row, column=1, 
                                value=f"↓↓调出仓库: {remove_warehouse} | 调入仓库: {move_warehouse} | 调拨单号: {transferNo}↓↓")
                info_cell.font = Font(bold=True, size=13)
                info_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 20
                current_row += 1
                # 如果是第一个调拨单，添加表头
                if current_row == 4:
                    # 添加表头
                    for col, header in enumerate(headers_str, 1):
                        ws.cell(row=current_row, column=col, value=header)
                    header_font = Font(bold=True, color="FF0000")
                    header_fill = PatternFill("solid", fgColor="F0F0F0")
                    center_align = Alignment(wrap_text=True, horizontal="center", vertical="center")
                    for cell in ws[current_row]:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = center_align
                    current_row += 1
                
                ws.freeze_panes = "A5"
                
                # 填充数据
                for item1,item2 in zip(detail_data['data'],shelf_data['data']):
                    inboundQuantity = item1.get('inboundQuantity', 0)
                    cell_alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
                    # 判断入库数量为0时，设置删除线格式
                    if inboundQuantity == 0:
                        data_font = Font(bold=True, size=11, strike=True)  # 添加删除线格式
                    else:
                        data_font = Font(bold=True,size=11)  # 设置11号字体
                    
                    # 基础信息
                    cell = ws.cell(row=current_row, column=1, value=item1.get('brandName', ''))
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    cell = ws.cell(row=current_row, column=2, value=item1.get('partName', ''))
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    # 分类转换
                    category_code = item1.get('categoryTwo', '')
                    category_name = self.CATEGORY_MAPPING.get(category_code, category_code)
                    cell = ws.cell(row=current_row, column=3, value=category_name)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    item_code = item1.get('partCode', '')
                    cell = ws.cell(row=current_row, column=4, value=item_code)
                    cell.alignment = cell_alignment
                    cell.font = data_font

                    inboundLocationNo: str = item1.get('inboundLocationNo', '')
                    if inboundLocationNo:
                        # 使用索引查询库位信息
                        location_items = stock_indices['location'].get(inboundLocationNo, [])
                        total_qty = sum(int(item.get('location_accessories_number', 0)) for item in location_items)
                        # if total_qty >= 0:
                        summary_info = f'【{total_qty}】'
                        cell = ws.cell(row=current_row, column=5, value=f'{inboundLocationNo}\n{summary_info}')
                    else:
                        cell = ws.cell(row=current_row, column=5, value="")
                        # 为单元格添加数据有效性下拉选项（使用外部引用）
                        if empty_locations:
                            # 创建数据验证规则，引用隐藏表中的A列数据
                            dv = DataValidation(type="list", formula1="=空库位数据!$A$1:$A$" + str(len(empty_locations)), allow_blank=True)
                            dv.add(cell)
                            ws.add_data_validation(dv)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    cell = ws.cell(row=current_row, column=6, value=inboundQuantity)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    shelfLocationNo: str = item2.get('shelfLocationNo','')
                    if shelfLocationNo:
                        # 使用索引查询库位信息
                        location_items = stock_indices['location'].get(shelfLocationNo, [])
                        total_qty = sum(int(item.get('location_accessories_number', 0)) for item in location_items)
                        if total_qty >= 0:
                            shelf_info = f'【{total_qty}】'
                            cell = ws.cell(row=current_row, column=7, value=f'{shelfLocationNo}\n{shelf_info}')
                    else:
                        cell = ws.cell(row=current_row, column=7, value=shelfLocationNo)
                    cell.alignment = cell_alignment
                    cell.font = data_font

                    # 补充库存和销售信息
                    if item_code:
                        # 库存信息
                        stock_data =stock_indices['part_code'].get(item_code, [])
                        # print(stock_data)
                        if stock_data:
                            locations = []
                            quantities = []
                            for loc in stock_data:
                                locations.append(loc.get('location_no', ''))
                                quantities.append(str(loc.get('location_accessories_number', 0)))
                            if locations and quantities:
                                cell = ws.cell(row=current_row, column=8, value=f"{'\n'.join(locations)}\n【{','.join(quantities)}】")
                                cell.alignment = cell_alignment
                                cell.font = data_font
                        # 销售信息
                        storage_id: int = self.WAREHOUSE_MAPPING.get(move_warehouse_name, {}).get("warehouseId", 11)
                        order_data = self.query_order_by_code(item_code, storage_id)
                        recent_sale = self.get_recent_sale_location(order_data) if order_data else "没有记录"
                        sale_info: str = f"{recent_sale}\n{item2.get('remarks', '')}"
                        cell = ws.cell(row=current_row, column=9, value=sale_info)
                        cell.alignment = cell_alignment
                        cell.font = data_font               
                    current_row += 1
                # 添加调拨单合计行
                if len(detail_data['data']) > 0:
                    ws.cell(row=current_row, column=5, value="合计:").font = Font(bold=True,size =12)
                    ws.cell(row=current_row, column=5).alignment = Alignment(horizontal="right")
                    total_qty = sum(float(item.get('inboundQuantity', 0)) for item in detail_data['data'])
                    ws.cell(row=current_row, column=6, value=total_qty).font = Font(bold=True,size = 12)
                    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="center", vertical="center")
                    current_row += 1
                # 添加调拨单分隔信息
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                transfer_data = detail_data['data'][0] if len(detail_data['data']) > 0 else {}
                remove_warehouse = transfer_data.get('removeWarehouseName', '')
                move_warehouse = transfer_data.get('moveWarehouseName', '')
                info_cell = ws.cell(row=current_row, column=1, 
                                value=f"↑↑调出仓库: {remove_warehouse} | 调入仓库: {move_warehouse} | 调拨单号: {transferNo}↑↑")
                info_cell.font = Font(bold=True, size=13)
                info_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 30
                current_row += 1

                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                ws.cell(row=current_row, column=1, value=str(empty_locations)).font = Font(bold=True,size = 11)
                ws.cell(row=current_row, column=1).alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 50
                current_row += 1
            # 设置边框
            thin_border = Side(border_style="thin", color="000000")
            border = Border(left=thin_border, right=thin_border, 
                        top=thin_border, bottom=thin_border)
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row,
                                min_col=1, max_col=len(headers_str)):
                for cell in row:
                    cell.border = border
            
            # 设置列宽
            column_widths = {
                "A": 9,   # 品牌
                "B": 26,  # 产品名称
                "C": 5,   # 分类
                "D": 14,  # 产品编码
                "E": 8, # 入库库位
                "F": 7.5, # 入库数量
                "G": 8, # 指示库位
                "H": 8, # 之前库存及数量
                "I": 15   # 最近90天出库库位及日期
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            self.auto_adjust_rows(ws)
            
            # 设置页面格式
            ws.page_setup.paperSize = 1  # A4纸张 (210mm × 297mm)
            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
            ws.print_options.horizontalCentered = True
            margin_in_inch = 8 / 25.4
            ws.page_margins = PageMargins(left=0.15, right=0.15,
                                        top=margin_in_inch, bottom=margin_in_inch,
                                        header=0.3, footer=0.3)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')

            # 生成文件名（不带时间戳用于检查重复）
            condition_str = ""
            if move_warehouse_name:
                condition_str += f"_{move_warehouse_name}"
            if status_name:
                condition_str += f"_{status_name}"
            if start_time:
                condition_str += f"_{start_time.replace('-', '')}"
            if end_time:
                condition_str += f"_{end_time.replace('-', '')}"
            
            base_filename = f"调拨清单{condition_str}"
            
            # 检查最近30分钟内是否已生成相同条件的文件
            import glob
            
            # 查找匹配的现有文件
            pattern = f"{base_filename}_*.xlsx"
            existing_files = glob.glob(pattern)
            
            # 检查是否有最近30分钟内生成的相同文件
            current_time = datetime.now()
            for existing_file in existing_files:
                # 提取文件名中的时间戳
                try:
                    # 文件名格式: 调拨清单[条件]_YYYYMMDD_HHMM.xlsx
                    parts = existing_file.split('_')
                    if len(parts) >= 2:
                        # 假设时间戳是最后两个部分
                        time_part = parts[-2] + "_" + parts[-1].replace('.xlsx', '')  # YYYYMMDD_HHMM
                        file_time = datetime.strptime(time_part, '%Y%m%d_%H%M')
                        
                        # 如果文件是最近30分钟内生成的，则直接返回该文件
                        if current_time - file_time <= timedelta(minutes=1):
                            print(f"找到最近生成的相同文件: {existing_file}")
                            return existing_file
                except (ValueError, IndexError):
                    # 解析时间戳失败，跳过该文件
                    continue
            
            # 生成带时间戳的新文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"{base_filename}_{timestamp}.xlsx"
            wb.save(filename)
            print(f"处理完成，文件已保存为: {filename}")
            
            return filename

        except Exception as e:
            print(f"生成Excel文件时发生错误: {e}")
            return None

    def _print_with_com(self, app_name, filename):
        """通用的COM对象打印方法（静默 + 打印触发即成功，避免重复打印）"""
        printed = False
        app = None
        workbook = None
        try:
            pythoncom.CoInitialize()

            # 统一WPS容错：当请求WPS时依次尝试两个ProgID，失败则回退Excel
            if app_name in ("WPS.Application", "KWPS.Application"):
                for wps_name in ("WPS.Application", "KWPS.Application"):
                    try:
                        app = win32com.client.Dispatch(wps_name)
                        break
                    except:
                        continue
                if app is None:
                    app = win32com.client.Dispatch("Excel.Application")
            else:
                app = win32com.client.Dispatch(app_name)

            # 静默设置（尽量不弹窗/不刷新）
            try:
                app.Visible = False
            except:
                pass
            try:
                app.DisplayAlerts = False
            except:
                pass
            try:
                app.ScreenUpdating = False
            except:
                pass

            workbook = app.Workbooks.Open(os.path.abspath(filename))
            # 后台打印：优先使用Background参数
            try:
                workbook.PrintOut(Background=True)
            except TypeError:
                workbook.PrintOut()

            printed = True
            return True  # 一旦提交到打印队列即判定成功，避免后续兜底再次触发打印

        except Exception as e:
            # 已提交打印则返回True，避免系统打印或其他COM重试造成重复
            return True if printed else False
        finally:
            # 清理放到finally，吞掉异常，避免影响返回值
            try:
                if workbook is not None:
                    workbook.Close(SaveChanges=False)
            except:
                pass
            try:
                if app is not None:
                    app.Quit()
            except:
                pass
            try:
                pythoncom.CoUninitialize()
            except:
                pass

    def _print_with_system_command(self, filename):
        """使用系统默认命令打印文件（Windows尽量静默，不弹终端窗口）"""
        try:
            system = platform.system()

            if system == "Windows":
                # 使用CREATE_NO_WINDOW抑制控制台窗口；加-NoProfile降低干扰
                CREATE_NO_WINDOW = 0x08000000
                ps_cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f'Start-Process -FilePath "{filename}" -Verb Print -WindowStyle Hidden -PassThru | Wait-Process'
                ]
                result = subprocess.run(
                    ps_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=CREATE_NO_WINDOW
                )
                return result.returncode == 0

            elif system == "Darwin":  # macOS
                result = subprocess.run(["lp", filename], capture_output=True, text=True, timeout=60)
                return result.returncode == 0

            else:  # Linux/其他
                result = subprocess.run(["lp", filename], capture_output=True, text=True, timeout=60)
                return result.returncode == 0

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def print_excel_file(self, filename):
        """
        先顺序尝试所有可用的COM对象打印，全部失败后再尝试系统默认命令。
        
        参数:
        - filename: 要打印的Excel文件路径
        
        返回:
        - 布尔值，表示打印是否成功
        """
        # 优先顺序尝试所有COM对象（静默 + 已触发即成功的策略由 _print_with_com 保证）
        for app_name in ["WPS.Application", "KWPS.Application", "Excel.Application"]:
            try:
                if self._print_with_com(app_name, filename):
                    return True
            except Exception:
                # 吞掉单个COM异常，继续尝试下一个
                pass
        
        # 所有COM对象都失败后，再尝试系统默认命令打印（Windows静默）
        if self._print_with_system_command(filename):
            return True
        
        return False

    def open_shipping_window(self):
        """处理选中订单"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请至少选择一条记录")
            return
        
        # 获取选中项的订单数据
        selected_orders = [order for order in self.filtered_data if order.get("transferNo") in self.selected_items]
        # 显示处理信息
        messagebox.showinfo("提示", f"将处理{len(selected_orders)}条订单记录")
        processed_order_ids = set(order.get("transferNo") for order in selected_orders)
        """打开一键发运窗口"""
        ShippingWindow(self, processed_order_ids)        
        messagebox.showinfo("成功", f"已成功处理{len(selected_orders)}条订单记录")        
        # 重新应用筛选条件
        self.picking_query()


class TransferPrintPreviewWindow:
    """调拨单打印预览窗口 - 展示调入清单HTML预览并通过WebSocket打印"""
    
    # 分类代码映射
    CATEGORY_TWO_MAP = {
        90921001: "前挡", 90921002: "后挡", 90921003: "边窗",
        90921004: "其它", 90921005: "天窗"
    }
    
    def __init__(self, parent, transfer_nos, controller=None, move_warehouse_name=""):
        self.parent = parent
        self.controller = controller  # TransferProcessPage 实例
        # 从 TransferProcessPage 的 controller (MainApplication) 获取 session
        self.session = controller.controller.session if controller and controller.controller else None
        self.transfer_nos = transfer_nos
        self.move_warehouse_name = move_warehouse_name
        self.print_data = []  # 分组后的打印数据
        
        # 仓库映射 - 用于获取 storage_code 和 warehouseId
        self.WAREHOUSE_MAPPING = {
            "郑州库": {"storage_code": "ZZ", "warehouseId": 6},
            "西安库": {"storage_code": "XA", "warehouseId": 7},
            "兰州库": {"storage_code": "LZ", "warehouseId": 8},
            "驻马店库": {"storage_code": "ZMD", "warehouseId": 9},
            "茶城库": {"storage_code": "CC", "warehouseId": 10},
            "商丘库": {"storage_code": "SQ", "warehouseId": 11},
            "洛阳库": {"storage_code": "LY", "warehouseId": 12},
            "雁塔库": {"storage_code": "YT", "warehouseId": 13},
            "西宁库": {"storage_code": "XN", "warehouseId": 14},
            "榆林库": {"storage_code": "YL", "warehouseId": 15},
            "银川库": {"storage_code": "YC", "warehouseId": 16},
            "西安西郊库": {"storage_code": "XA-XJ", "warehouseId": 18}
        }
        
        # 获取仓库信息
        warehouse_info = self.WAREHOUSE_MAPPING.get(move_warehouse_name, {"storage_code": "SQ", "warehouseId": 11})
        self.storage_code = warehouse_info["storage_code"]
        self.warehouseId = warehouse_info["warehouseId"]
        
        # 筛选状态变量
        self.is_urgent_var = tk.BooleanVar(value=False)
        self.is_only_remark_var = tk.BooleanVar(value=False)
        self.show_empty_locations_var = tk.BooleanVar(value=False)
        self._empty_locations_cache = None  # 空库位数据缓存
        self._html_cache = None  # 上次生成的 HTML 缓存（用于过滤刷新）
        
        # 创建顶层窗口
        self.window = tk.Toplevel(parent)
        self.window.title("调入清单打印预览")
        self.window.geometry("900x700")
        self.window.minsize(600, 400)
        
        # 主框架
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部按钮区
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(btn_frame, text=f"已选 {len(transfer_nos)} 个调拨单", 
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=5)
        
        btn_style = {"bg": "#673AB7", "fg": "white", "padx": 15, "pady": 5, 
                     "bd": 0, "activebackground": "#45a049", "font": ("微软雅黑", 10)}
        
        tk.Button(btn_frame, text="关闭", 
                  command=self.window.destroy,
                  bg="#f44336", fg="white", padx=15, pady=5, 
                  bd=0, font=("微软雅黑", 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="打印", 
                  command=self.print_via_clodop, **btn_style).pack(side=tk.RIGHT, padx=5)
        
        # 筛选复选框区
        filter_frame = tk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(filter_frame, text="筛选：", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        cb_style = {"font": ("微软雅黑", 9), "selectcolor": "#673AB7"}
        
        self.cb_urgent = tk.Checkbutton(filter_frame, text="急用", variable=self.is_urgent_var,
                                         command=self._on_filter_changed, **cb_style)
        self.cb_urgent.pack(side=tk.LEFT, padx=3)
        
        self.cb_only_remark = tk.Checkbutton(filter_frame, text="仅备注", variable=self.is_only_remark_var,
                                              command=self._on_filter_changed, **cb_style)
        self.cb_only_remark.pack(side=tk.LEFT, padx=3)
        
        self.cb_empty_locations = tk.Checkbutton(filter_frame, text="前档空库位清单", 
                                                   variable=self.show_empty_locations_var,
                                                   command=self._on_filter_changed, **cb_style)
        self.cb_empty_locations.pack(side=tk.LEFT, padx=3)
        
        # HTML预览区域
        self.preview_container = tk.Frame(main_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True)
        
        # 加载数据
        self._load_data()
    
    def _render_preview(self, html_content):
        """将HTML渲染到预览区域 - 使用 tkinterweb HtmlFrame"""
        for widget in self.preview_container.winfo_children():
            widget.destroy()
        
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; padding:10px; font-family:'微软雅黑',sans-serif; font-size:12px; background:#fff; }}
table {{ border-collapse:collapse; width:100%; }}
td {{ padding:2px 4px; }}
</style></head>
<body>{html_content}</body></html>"""
        
        try:
            from tkinterweb import HtmlFrame
            self.html_frame = HtmlFrame(self.preview_container)
            self.html_frame.load_html(full_html)
            self.html_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            return
        except ImportError:
            pass
        
        label = tk.Label(self.preview_container,
                        text="打印预览需要 tkinterweb 库\n\n请运行：pip install tkinterweb\n\n安装后重启程序即可在窗口内预览",
                        font=("微软雅黑", 12), justify=tk.CENTER,
                        bg="white", fg="#333333")
        label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def _on_filter_changed(self):
        """当任意筛选复选框状态变化时调用 - 统一刷新预览"""
        show_empty = self.show_empty_locations_var.get()
        
        # 前档空库位勾选时，禁用/恢复其他复选框
        if show_empty:
            self.cb_urgent.config(state=tk.DISABLED)
            self.cb_only_remark.config(state=tk.DISABLED)
        else:
            self.cb_urgent.config(state=tk.NORMAL)
            self.cb_only_remark.config(state=tk.NORMAL)
        
        self._refresh_preview()
    
    def _refresh_preview(self):
        """根据当前筛选状态重新生成 HTML 并刷新预览"""
        show_empty = self.show_empty_locations_var.get()
        
        if show_empty:
            # 前档空库位清单 - 替代视图
            html_content = self._build_empty_locations_html()
        else:
            is_urgent = self.is_urgent_var.get()
            is_only_remark = self.is_only_remark_var.get()
            html_content = self._build_html(is_urgent=is_urgent, is_only_remark=is_only_remark)
        
        self._render_preview(html_content)
    
    def _load_data(self):
        """加载打印数据并渲染预览 - 遵循 Content.js formatPrintData + generatePrintHTML 逻辑"""
        try:
            loading_label = tk.Label(self.preview_container, 
                                     text="⏳ 正在获取打印数据...", 
                                     font=("微软雅黑", 10), bg="white")
            loading_label.pack(pady=20)
            self.window.update()
            
            # 构建 getPrintList URL
            nos_str = ",".join([f"'{no}'" for no in self.transfer_nos])
            url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/getPrintList?transferNos={nos_str}"
            
            if self.session:
                resp = self.session.get(url, timeout=15)
            else:
                import requests
                resp = requests.get(url, timeout=15, headers=HEADERS)
            
            if resp.status_code != 200:
                self._render_preview(f"❌ HTTP错误: {resp.status_code}")
                return
            
            data_list = resp.json().get("data", [])
            if not isinstance(data_list, list) or len(data_list) == 0:
                self._render_preview("❌ 未获取到打印数据")
                return
            
            # 更新loading提示
            for widget in self.preview_container.winfo_children():
                widget.destroy()
            loading_label = tk.Label(self.preview_container, 
                                     text="⏳ 正在获取调拨明细...", 
                                     font=("微软雅黑", 10), bg="white")
            loading_label.pack(pady=20)
            self.window.update()
            
            # 获取每个调拨单的明细数据（备注、指示库位）- 遵循 Content.js inboundDetail_query
            detail_cache = {}
            for item in data_list:
                transfer_id = item.get("transferId") or item.get("id")
                if transfer_id and transfer_id not in detail_cache:
                    try:
                        detail_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail?transferId={transfer_id}"
                        if self.session:
                            detail_resp = self.session.get(detail_url, timeout=10)
                        else:
                            import requests
                            detail_resp = requests.get(detail_url, timeout=10, headers=HEADERS)
                        if detail_resp.status_code == 200:
                            detail_data = detail_resp.json().get("data", [])
                            detail_cache[transfer_id] = detail_data if isinstance(detail_data, list) else []
                        else:
                            detail_cache[transfer_id] = []
                    except Exception as e:
                        print(f"获取调拨明细失败 transferId={transfer_id}: {e}")
                        detail_cache[transfer_id] = []
            
            # 更新loading提示 - 获取库存数据
            for widget in self.preview_container.winfo_children():
                widget.destroy()
            loading_label = tk.Label(self.preview_container, 
                                     text="⏳ 正在获取库存数据...", 
                                     font=("微软雅黑", 10), bg="white")
            loading_label.pack(pady=20)
            self.window.update()
            
            # 获取库存数据并构建索引 - 遵循 Content.js get_all_stock_data + build_stock_indices
            all_stock_data = self.controller.get_all_stock_data(self.storage_code)
            stock_indices = self.controller.build_stock_indices(all_stock_data)
            
            # 更新loading提示 - 获取销售数据
            for widget in self.preview_container.winfo_children():
                widget.destroy()
            loading_label = tk.Label(self.preview_container, 
                                     text="⏳ 正在获取销售数据...", 
                                     font=("微软雅黑", 10), bg="white")
            loading_label.pack(pady=20)
            self.window.update()
            
            # 数据分组（同时查询每个 item 的销售数据）- 遵循 Content.js generatePrintHTML 逻辑
            self._group_data(data_list, detail_cache, stock_indices)
            
            # 生成HTML并显示
            html = self._build_html()
            self._render_preview(html)
            
        except Exception as e:
            self._render_preview(f"❌ 加载失败: {e}")
    
    def _group_data(self, data_list, detail_cache, stock_indices):
        """按 transferNo 分组，合并明细备注/指示库位/库存/销售信息 - 遵循 Content.js generatePrintHTML 逻辑"""
        groups = {}
        for item in data_list:
            transfer_no = item.get("transferNo", "")
            if transfer_no not in groups:
                groups[transfer_no] = {"items": [], "header": item}
            groups[transfer_no]["items"].append(item)
        
        for transfer_no, group in groups.items():
            items = group["items"]
            header = dict(group["header"])
            
            # 获取明细数据
            transfer_id = header.get("transferId") or header.get("id")
            detail_data = detail_cache.get(transfer_id, [])
            
            total_num = 0
            total_amount = 0.0
            
            # 处理每个 item - 遵循 Content.js generatePrintHTML 中对每个 item 的处理
            processed_items = []
            for item in items:
                quantity = int(item.get("inboundQuantity", 0) or 0)
                price = float(item.get("salesPrice", 0) or 0)
                rate = float(item.get("priceIncreaseRate", 1) or 1)
                amount = quantity * price * rate
                
                total_num += quantity
                total_amount += amount
                
                # 匹配明细数据中的备注和指示库位 - 遵循 Content.js detailItem.remarks / detailItem.shelfLocationNo
                detail_id = item.get("detailId")
                remark = ""
                shelf_location_no = ""
                if detail_id and detail_data:
                    for detail in detail_data:
                        if detail.get("detailId") == detail_id:
                            remark = detail.get("remarks", "") or ""
                            shelf_location_no = detail.get("shelfLocationNo", "") or ""
                            break
                
                # 格式化品牌名（>3字截取前2字）- 遵循 Content.js formattedBrandName
                brand_name = item.get("brandName", "") or ""
                if len(brand_name) > 3:
                    brand_name = brand_name[:2]
                
                part_code = item.get("partCode", "") or ""
                
                # ===== 入库库位显示：库位号 + 【库存数量】 - 遵循 Content.js inboundLocationDisplay =====
                inbound_location_no = item.get("inboundLocationNo", "") or ""
                inbound_location_display = ""
                if inbound_location_no:
                    location_stock = stock_indices['location'].get(inbound_location_no, [])
                    stock_qty = sum(loc.get('location_accessories_number', 0) or 0 for loc in location_stock)
                    inbound_location_display = f"{inbound_location_no}\n【{stock_qty}】"
                
                # ===== 指示库位显示：库位号 + 【库存数量】 - 遵循 Content.js shelfLocationDisplay =====
                shelf_location_display = ""
                if shelf_location_no:
                    shelf_stock = stock_indices['location'].get(shelf_location_no, [])
                    shelf_qty = sum(loc.get('location_accessories_number', 0) or 0 for loc in shelf_stock)
                    shelf_location_display = f"{shelf_location_no}\n【{shelf_qty}】"
                
                # ===== 调拨前库存数：所有库位【数量,数量】- 遵循 Content.js prestockvalue =====
                prestockvalue = ""
                if part_code:
                    stock_data = stock_indices['part_code'].get(part_code, [])
                    if stock_data and len(stock_data) > 0:
                        locations = []
                        quantities = []
                        for loc in stock_data:
                            locations.append(loc.get('location_no', '') or '')
                            quantities.append(str(loc.get('location_accessories_number', 0) or 0))
                        if locations and quantities:
                            prestockvalue = f"{chr(10).join(locations)}\n【{','.join(quantities)}】"
                
                # ===== 3月内最近出库信息 - 遵循 Content.js query_order_by_code + get_recent_sale_location =====
                recent_sale_info = ""
                if part_code:
                    order_data = self.controller.query_order_by_code(part_code, self.warehouseId)
                    recent_sale_info = self.controller.get_recent_sale_location(order_data) if order_data else "没有记录"
                
                processed_items.append({
                    "brandName": brand_name,
                    "partName": item.get("partName", "") or "",
                    "categoryTwo": item.get("categoryTwo", ""),
                    "partCode": part_code,
                    "inboundLocationNo": inbound_location_no,
                    "inboundLocationDisplay": inbound_location_display,
                    "inboundQuantity": quantity,
                    "salesPrice": price,
                    "priceIncreaseRate": rate,
                    "amount": amount,
                    "remark": remark,
                    "shelfLocationNo": shelf_location_no,
                    "shelfLocationDisplay": shelf_location_display,
                    "prestockvalue": prestockvalue,
                    "recentSaleInfo": recent_sale_info
                })
            
            header["totalNum"] = total_num
            header["totalAmount"] = f"{total_amount:.2f}"
            
            self.print_data.append({"header": header, "items": processed_items})
    
    def _get_category_name(self, code):
        """获取分类名称"""
        return self.CATEGORY_TWO_MAP.get(code, str(code))
    
    def _get_short_transfer_no(self, transfer_no):
        """截取调拨单号后7位"""
##        if transfer_no and len(transfer_no) > 7:
##            return transfer_no[-7:]
        return transfer_no or ""
    
    def _build_html(self, is_urgent=False, is_only_remark=False):
        """构建调入清单打印HTML - 遵循 Content.js generatePrintHTML 表头和数据列逻辑
        
        Args:
            is_urgent: 急用模式 - 只保留 remark 非空的明细行，空组跳过
            is_only_remark: 仅备注模式 - 隐藏指示库位/调拨前库存数/3月内最近出库信息三列
        """
        current_date = datetime.now().strftime("%Y/%m/%d %H:%M")
        html_parts = []
        
        for idx, group in enumerate(self.print_data):
            header = group["header"]
            items = group["items"]
            
            # 急用过滤：只保留备注非空的行
            if is_urgent:
                items = [item for item in items if item.get("remark", "").strip()]
            
            # 如果过滤后没有明细行，跳过整个调拨单
            if not items:
                continue
            
            # 重新计算合计数量（急用过滤后可能变化）
            total_num = sum(int(item.get("inboundQuantity", 0) or 0) for item in items)
            
            # 表头信息
            remove_warehouse = header.get("removeWarehouseName", "") or ""
            move_warehouse = header.get("moveWarehouseName", "") or ""
            transfer_no = self._get_short_transfer_no(header.get("transferNo", ""))
            created_by = header.get("createdByName", "") or ""
            onshelf_by = header.get("onshelf_by", "") or ""
            head_remark = header.get("headRemark", "") or ""
            
            # 构建分组HTML - 列宽参考 Content.js
            # 完整模式(10列): 品牌5% 产品名称28% 分类5% 产品编码15% 入库库位7% 入库数量5% 指示库位7% 调拨前库存数7% 最近出库14% 备注7%
            # 仅备注模式(7列): 品牌5% 产品名称35% 分类5% 产品编码18% 入库库位10% 入库数量7% 备注20%
            group_html = f"""
    <div id="transferPrintDiv{idx}" style="font-family:'微软雅黑';color:#000000;page-break-after:always;">
    <div style="width:100%;margin:0 auto;text-align:center;">
    <span style="font-size:25px;font-weight:bold;">调入清单</span>
    </div>
    <div style="width:100%;margin:0;text-align:left;">
    <table style="margin:0 auto;font-size:15px;width:98%;" align="center" valign="middle">
    <tr>
    <td style="vertical-align:top;text-align:left;width:33%;">调出仓库：{remove_warehouse}</td>
    <td style="vertical-align:top;text-align:left;width:33%;">调入仓库：{move_warehouse}</td>
    <td style="vertical-align:top;text-align:left;width:35%;">单 据 号：{transfer_no}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;">开 单 人：{created_by}</td>
    <td style="vertical-align:top;text-align:left;">上 架 人：{onshelf_by}</td>
    <td style="vertical-align:top;text-align:left;">摘　　要：{head_remark}</td>
    </tr>
    </table>
    <table style="width:100%;margin:0 auto;font-size:14px;vertical-align:middle;text-align:center;
    border:1px solid #000000;border-collapse:collapse;" align="center" valign="middle">
    <tr>
    <td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">品牌</td>
    <td style="width:{'35%' if is_only_remark else '28%'};display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">产品名称</td>
    <td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">分类</td>
    <td style="width:{'18%' if is_only_remark else '15%'};display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;white-space:pre-line;">产品编码</td>
    <td style="width:{'10%' if is_only_remark else '7%'};display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;white-space:pre-line;">入库<br/>库位</td>
    <td style="width:{'7%' if is_only_remark else '5%'};display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">入库<br/>数量</td>"""
            
            if not is_only_remark:
                group_html += """
    <td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;white-space:pre-line;">指示<br/>库位</td>
    <td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;white-space:pre-line;">调拨前<br/>库存数</td>
    <td style="width:14%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;white-space:pre-line;">3月内最近<br/>出库信息</td>"""
            
            group_html += """
    <td style="width:{'20%' if is_only_remark else '7%'};display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">备注</td>
    </tr>"""
            
            # 产品明细行
            for item in items:
                brand = item.get("brandName", "")
                part_name = item.get("partName", "")
                category = self._get_category_name(item.get("categoryTwo", ""))
                part_code = item.get("partCode", "")
                inbound_location_display = item.get("inboundLocationDisplay", "")
                quantity = item.get("inboundQuantity", 0)
                remark = item.get("remark", "")
                
                # 入库数量为0时添加删除线样式
                row_class = 'class="strike-through"' if quantity == 0 else ''
                
                if is_only_remark:
                    # 仅备注模式：7列
                    group_html += f"""
    <tr {row_class}>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {brand} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_name} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {category} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_code} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {inbound_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {quantity} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {remark} </td>
    </tr>"""
                else:
                    shelf_location_display = item.get("shelfLocationDisplay", "")
                    prestockvalue = item.get("prestockvalue", "")
                    recent_sale_info = item.get("recentSaleInfo", "")
                    
                    group_html += f"""
    <tr {row_class}>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {brand} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_name} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {category} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_code} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {inbound_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {quantity} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {shelf_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {prestockvalue} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {recent_sale_info} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {remark} </td>
    </tr>"""
            
            # 合计行 - 根据模式调整 colspan
            if is_only_remark:
                # 7列：品牌+产品名称(2) + 分类+产品编码(2) + 入库库位(1) + 合计数量(1) + 备注(1)
                group_html += f"""
    <tr>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="1">合计数量：</td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="1"> {total_num} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="1"></td>
    </tr>"""
            else:
                # 10列
                group_html += f"""
    <tr>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="1">合计数量：</td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="1"> {total_num} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="4"></td>
    </tr>"""
            
            group_html += """
    </table>
    </div>
    </div>"""
            
            html_parts.append(group_html)
        
        return "\n".join(html_parts)
    
    def print_via_clodop(self):
        """通过WebSocket连接CLodop 直接打印到针式打印机 - 遵循当前筛选状态"""
        import websocket
        
        # 读取当前筛选状态
        show_empty = self.show_empty_locations_var.get()
        is_urgent = self.is_urgent_var.get()
        is_only_remark = self.is_only_remark_var.get()
        
        try:
            html_parts = []
            html_head = '<style>div { width: 97%; } body { margin: 0; padding: 0; } .strike-through { text-decoration: line-through; }</style>\n'
            
            if show_empty:
                # 前档空库位清单 - 单一页面
                html_parts.append(html_head + self._build_empty_locations_html())
            else:
                # 调拨单打印 - 遍历分组，应用筛选
                for idx, group in enumerate(self.print_data):
                    # 急用过滤
                    items = group["items"]
                    if is_urgent:
                        items = [item for item in items if item.get("remark", "").strip()]
                    if not items:
                        continue  # 跳过空组
                    
                    # 构建过滤后的临时 group
                    filtered_group = {"header": group["header"], "items": items}
                    html_parts.append(html_head + self._build_single_html(
                        idx, filtered_group, is_urgent=False, is_only_remark=is_only_remark
                    ))
            
            if not html_parts:
                messagebox.showwarning("警告", "当前筛选条件下没有可打印的数据")
                return
            
            # 生成唯一TASKID
            now = datetime.now()
            task_id = f"DB{now.hour:02d}{now.minute:02d}{now.second:02d}_1"
            
            # CLodop WebSocket协议消息格式
            delim = "\f\f"
            printer_name = "EPSON LQ-630K ESC/P2"
            
            # 连接WebSocket并发送每个打印任务
            ws = websocket.create_connection("ws://127.0.0.1:8000/c_webskt/", timeout=10)
            
            for idx, html_content in enumerate(html_parts):
                msg = (
                    f"post:charset=丂{delim}"
                    f"tid={task_id}_{idx}{delim}"
                    f"act=print{delim}"
                    f"browseurl=PYTHON_CLODOP{delim}"
                    f"companyname=用友汽车信息科技（上海）股份有限公司{delim}"
                    f"license=FA9A697F2551BCE81BD852A4EB520525347{delim}"
                    f"licensea=用友汽車信息科技（上海）股份有限公司{delim}"
                    f"licenseb=C66313BD8413BD0174C2CADD29F5380CD92{delim}"
                    f"licensec=Yonyou Auto Information Technology (Shanghai) Co., Ltd.{delim}"
                    f"licensed=941DF3639D9F5679867946141A31424B4E6{delim}"
                    f"top={delim}"
                    f"left={delim}"
                    f"width={delim}"
                    f"height={delim}"
                    f"printtask=调入清单打印{delim}"
                    f"printerindex={printer_name}{delim}"
                    f"orient=3{delim}"
                    f"pagewidth=220mm{delim}"
                    f"pageheight=15mm{delim}"
                    f"pagename={delim}"
                    f"printcopies=1{delim}"
                    f"itemcount=1{delim}"
                    f"1_type=4{delim}"
                    f"1_top=30{delim}"
                    f"1_left=3mm{delim}"
                    f"1_width=100%{delim}"
                    f"1_height=100%{delim}"
                    f"1_content={html_content}{delim}"
                    f"1_itemstylenames={delim}"
                    f"printmodenames=;left;top;width;height{delim}"
                    f"printstyleclassnames={delim}"
                )
                
                ws.send(msg)
            
            ws.close()
            
            # 打印成功后关闭预览窗口
            self.window.destroy()
            
        except ImportError:
            messagebox.showerror("错误", "缺少 websocket-client 库\n\n请运行：pip install websocket-client")
        except Exception as e:
            messagebox.showerror("打印失败", f"打印出错: {e}")
    
    def _build_single_html(self, idx, group, is_urgent=False, is_only_remark=False):
        """为单个调拨单构建完整HTML（用于CLodop打印）- 遵循 Content.js generatePrintHTML
        
        Args:
            idx: 索引
            group: 调拨单数据 {"header": ..., "items": [...]}
            is_urgent: 急用模式 - 只保留 remark 非空的明细行
            is_only_remark: 仅备注模式 - 隐藏指示库位/调拨前库存数/3月内最近出库信息三列
        """
        header = group["header"]
        items = group["items"]
        
        # 急用过滤
        if is_urgent:
            items = [item for item in items if item.get("remark", "").strip()]
        
        # 重新计算合计
        total_num = sum(int(item.get("inboundQuantity", 0) or 0) for item in items)
        
        current_date = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        remove_warehouse = header.get("removeWarehouseName", "") or ""
        move_warehouse = header.get("moveWarehouseName", "") or ""
        transfer_no = self._get_short_transfer_no(header.get("transferNo", ""))
        created_by = header.get("createdByName", "") or ""
        onshelf_by = header.get("onshelf_by", "") or ""
        head_remark = header.get("headRemark", "") or ""
        
        rows_html = ""
        for item in items:
            brand = item.get("brandName", "")
            part_name = item.get("partName", "")
            category = self._get_category_name(item.get("categoryTwo", ""))
            part_code = item.get("partCode", "")
            inbound_location_display = item.get("inboundLocationDisplay", "")
            quantity = item.get("inboundQuantity", 0)
            remark = item.get("remark", "")
            row_class = 'class="strike-through"' if quantity == 0 else ''
            
            if is_only_remark:
                # 仅备注模式：7列
                rows_html += f"""
    <tr {row_class}>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {brand} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_name} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {category} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_code} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {inbound_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {quantity} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {remark} </td>
    </tr>"""
            else:
                shelf_location_display = item.get("shelfLocationDisplay", "")
                prestockvalue = item.get("prestockvalue", "")
                recent_sale_info = item.get("recentSaleInfo", "")
                
                rows_html += f"""
    <tr {row_class}>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {brand} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_name} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {category} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {part_code} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {inbound_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {quantity} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {shelf_location_display} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {prestockvalue} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {recent_sale_info} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;white-space:pre-line;"> {remark} </td>
    </tr>"""
        
        # 构建表头
        if is_only_remark:
            header_row = """<tr>
<td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">品牌</td>
<td style="width:35%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">产品名称</td>
<td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">分类</td>
<td style="width:18%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">产品编码</td>
<td style="width:10%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">入库<br/>库位</td>
<td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">入库<br/>数量</td>
<td style="width:20%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">备注</td>
</tr>"""
            # 7列合计行
            footer_row = f"""<tr>
<td colspan="2" style="border:1px solid #000000;"></td>
<td colspan="2" style="border:1px solid #000000;"></td>
<td colspan="1" style="border:1px solid #000000;">合计数量：</td>
<td colspan="1" style="border:1px solid #000000;"> {total_num} </td>
<td colspan="1" style="border:1px solid #000000;"></td>
</tr>"""
        else:
            header_row = """<tr>
<td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">品牌</td>
<td style="width:28%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">产品名称</td>
<td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">分类</td>
<td style="width:15%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">产品编码</td>
<td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">入库<br/>库位</td>
<td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">入库<br/>数量</td>
<td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">指示<br/>库位</td>
<td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">调拨前<br/>库存数</td>
<td style="width:14%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;white-space:pre-line;">3月内最近<br/>出库信息</td>
<td style="width:7%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;">备注</td>
</tr>"""
            # 10列合计行
            footer_row = f"""<tr>
<td colspan="2" style="border:1px solid #000000;"></td>
<td colspan="2" style="border:1px solid #000000;"></td>
<td colspan="1" style="border:1px solid #000000;">合计数量：</td>
<td colspan="1" style="border:1px solid #000000;"> {total_num} </td>
<td colspan="4" style="border:1px solid #000000;"></td>
</tr>"""
        
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; padding:0; font-family:'微软雅黑',sans-serif; }}
table {{ border-collapse:collapse; }}
td {{ padding:2px 4px; }}
</style></head>
<body>
<div id="transferPrintDiv{idx}" style="font-family:'微软雅黑';color:#000000;">
<div style="width:100%;margin:0 auto;text-align:center;">
<span style="font-size:25px;font-weight:bold;">调入清单</span>
</div>
<div style="width:100%;margin:0;text-align:left;">
<table style="margin:0 auto;font-size:15px;width:98%;" align="center" valign="middle">
<tr>
<td style="vertical-align:top;text-align:left;width:33%;">调出仓库：{remove_warehouse}</td>
<td style="vertical-align:top;text-align:left;width:33%;">调入仓库：{move_warehouse}</td>
<td style="vertical-align:top;text-align:left;width:35%;">单 据 号：{transfer_no}</td>
</tr>
<tr>
<td style="vertical-align:top;text-align:left;">开 单 人：{created_by}</td>
<td style="vertical-align:top;text-align:left;">上 架 人：{onshelf_by}</td>
<td style="vertical-align:top;text-align:left;">摘　　要：{head_remark}</td>
</tr>
</table>
<table style="width:100%;margin:0 auto;font-size:14px;vertical-align:middle;text-align:center;
border:1px solid #000000;border-collapse:collapse;" align="center" valign="middle">
{header_row}
{rows_html}
{footer_row}
</table>
</div>
</div>
</body></html>"""
    
    def _build_empty_locations_html(self):
        """生成前档空库位清单 HTML - 遵循 Content.js generateEmptyLocationsHTML"""
        # 使用缓存避免重复请求
        if self._empty_locations_cache is None:
            try:
                self._empty_locations_cache = self.controller.find_empty_locations(self.storage_code)
            except Exception as e:
                return f"<p>❌ 获取空库位数据失败: {e}</p>"
        
        empty_locations = self._empty_locations_cache
        if not empty_locations:
            return f"<p style='text-align:center;padding:40px;'>当前仓库 ({self.move_warehouse_name}) 没有前档空库位</p>"
        
        # 仓库名称映射
        warehouse_name_map = {
            'SQ': '商丘库', 'ZZ': '郑州库', 'XA': '西安库', 'LZ': '兰州库',
            'ZMD': '驻马店库', 'CC': '茶城库', 'LY': '洛阳库', 'YT': '雁塔库',
            'XN': '西宁库', 'YL': '榆林库', 'YC': '银川库', 'XA-XJ': '西安西郊库'
        }
        warehouse_name = warehouse_name_map.get(self.storage_code, self.move_warehouse_name)
        
        # 按排号分组 - 根据仓库格式提取排号
        locations_by_rack = {}
        for location in empty_locations:
            rack = self._extract_rack(location, self.storage_code)
            if rack not in locations_by_rack:
                locations_by_rack[rack] = []
            locations_by_rack[rack].append(location)
        
        sorted_racks = sorted(locations_by_rack.keys())
        
        current_time = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        html = f"""<div id="emptyLocationsPrintDiv" style="font-family:微软雅黑; color: rgb(0, 0, 0);">
    <div style="width: 100%; margin: 0px auto; text-align: center;">
    <span style="font-size: 25px; font-weight: bold;">{warehouse_name} - 前档空库位清单</span>
    </div>
    <div style="width: 100%; margin: 10px 0; text-align: center;">
    <span style="font-size: 16px; font-weight: bold;">空库位总数量：{len(empty_locations)}个</span>
    </div>
    <div style="width: 100%; margin: 0px;">
    <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 12px; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
    <tbody>"""
        
        for rack in sorted_racks:
            rack_locations = sorted(locations_by_rack[rack])
            # 每行显示12个库位
            chunk_size = 12
            chunks = [rack_locations[i:i+chunk_size] for i in range(0, len(rack_locations), chunk_size)]
            
            html += f"""
    <tr>
    <td style="width: 15%; display: table-cell; vertical-align: middle; height: 25px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse; font-weight: bold; background-color: #f5f5f5; padding: 5px;">
    排号：{rack}（{len(rack_locations)}个）
    </td>
    <td style="border: 1px solid rgb(0, 0, 0); border-collapse: collapse; padding: 5px;">"""
            
            for ci, chunk in enumerate(chunks):
                html += f"""
    <div style="margin-bottom: {'5px' if ci < len(chunks) - 1 else '0'}; line-height: 1.4;">
    {', '.join(chunk)}
    </div>"""
            
            html += """
    </td>
    </tr>"""
        
        html += f"""
    </tbody>
    </table>
    </div>
    <div style="width: 100%; margin: 10px 0; text-align: right;">
    <span style="font-size: 12px;">生成时间：{current_time}</span>
    </div>
    </div>"""
        
        return html
    
    def _extract_rack(self, location, storage_code):
        """根据仓库代码从库位编号中提取排号 - 遵循 Content.js 逻辑"""
        if storage_code == 'LY':
            # 洛阳库格式：排号-库位号（如：1-001）
            return location.split('-')[0]
        elif storage_code == 'LZ':
            # 兰州库特殊格式
            if '-' in location:
                parts = location.split('-')
                return parts[0]  # 如 MA01-1-01 → MA01
            else:
                # 取字母前缀，如 M411-001 → M4
                return ''.join(c for c in location if not c.isdigit())
        elif storage_code == 'ZZ':
            # 郑州库格式：50-101 或 G101-01
            if location.startswith('G'):
                # 高架货位 G101-01 → G10
                return 'G' + location[1:].split('-')[0][:2]
            else:
                # 散片库位 50-101 → 50
                return location.split('-')[0]
        elif storage_code in ('XA', 'XA-XJ', 'ZMD', 'YL', 'YC', 'SQ'):
            # 格式：排号层数-库位号（如：101-001 → 1, 211-152 → 2）
            # 取第一个 '-' 之前去掉最后一位数字
            first_part = location.split('-')[0]
            return first_part[:-1] if len(first_part) > 1 else first_part
        else:
            # 默认：取第一个 '-' 之前的非数字部分
            first_part = location.split('-')[0] if '-' in location else location
            return first_part[:-1] if len(first_part) > 1 else first_part

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from copy import deepcopy
import json
import requests
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


class outBoundProcessPage(BasePage):
    """拣货单生成页面"""
    def __init__(self, parent, controller):
        self.original_data = []  # 存储原始数据
        self.filtered_data = []  # 存储筛选后的数据
        self.selected_items = set()  # 存储选中的项
        self.detail_cache = {}  # 缓存子节点数据
        self.parent=parent
        # 定义出库状态映射关系
        self.outbound_status_mapping = {
            "未出库" : 90381001,
            "部分出库" : 90381002,
            "已出库" : 90381003,
        }

        #定义出库类型映射关系
        self.outbound_type_mapping = {
            "产品销售出库" : 90371003,
            "调拨出库" : 90371014,
            "内部领用出库" : 90371006,
            "盘亏出库":90371011,
            "报废出库":90371005,
            "产品转换出库":90371013,
            "绿通出库":90371015,
            "普通件采购退货出库":90371001
        }

        # 定义物流方式映射关系
        self.logistics_mode_mapping = {
            "送货": 46171001,
            "物流代收": 46171002,
            "物流发货":46171003,
            "自提":46171004,
            "快递":46171005
        }
        # 定义拣货状态映射关系
        self.picking_status_mapping = {
            "未开始":47111001,
            "拣货中": 47111002,
            "拣货完成": 47111003,
            "提前关闭":47111004,
            "作废":47111005
        }

        self.filtered_data = self.original_data.copy()        
        # 新增分页相关属性
        self.current_page = 1
        self.page_size = 10  # 每页显示200条
        self.total_pages = 1
        self.filtered_data_all = []  # 存储所有筛选后的数据
        # 初始化分页信息变量
        self.page_info_var = tk.StringVar()  # 新增这一行
        # 预先定义UI变量，避免类型检查错误
        self.outbound_status_var = tk.StringVar()
        self.outboundtype_var = tk.StringVar()
        self.logistics_var = tk.StringVar()
        self.picking_var = tk.StringVar()
        self.warehouse_var = tk.StringVar()
        super().__init__(parent, controller)

    def _check_response(self, response):
        """检查响应中的登录状态"""
        # 如果controller.check_login_status返回True，说明用户已被登出
        # 我们应该返回False，表示不应该继续当前操作
        return not self.controller.check_login_status(response)

    def parse_and_convert_json(self, data):
        """解析JSON数据，并将状态代码转换为文本"""
        try:
            # 处理不同的API响应格式
            if isinstance(data, dict):
                if 'data' in data and 'rows' in data['data']:
                    orders = data['data']['rows']
                elif 'rows' in data:
                    orders = data['rows']
                elif 'list' in data:
                    orders = data['list']
                else:
                    # 如果data是字典但不是列表格式，将其转换为列表
                    orders = [data] if data else []
            else:
                orders = data  # 已经是列表格式
            
            # 确保orders是列表
            if not isinstance(orders, list):
                orders = [orders] if orders else []
            
            # 遍历所有订单 替换所有代码映射的文本
            for order in orders:
                # 出库状态转换
                outbound_status_code = order.get("outbound_status", "")
                for text, code in self.outbound_status_mapping.items():
                    if code == outbound_status_code:
                        order["outbound_status"] = text
                        break

            for order in orders:
                # 出库类型转换
                outbound_type_code = order.get("outbound_type", "")
                for text, code in self.outbound_type_mapping.items():
                    if code == outbound_type_code:
                        order["outbound_type"] = text
                        break
                
                # 物流方式转换
                logistics_mode_code = order.get("logistics_mode", "")
                for text, code in self.logistics_mode_mapping.items():
                    if code == logistics_mode_code:
                        order["logistics_mode"] = text
                        break
                
                # 拣货状态转换
                picking_status_code = order.get("picking_status", "")
                for text, code in self.picking_status_mapping.items():
                    if code == picking_status_code:
                        order["picking_status"] = text
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
        filter_frame.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=5)
        
        # 第一行筛选条件
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5)
        # 按钮样式
        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        # 出库状态筛选
        tk.Label(row1, text="出库状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.outbound_status_var = tk.StringVar()
        outbounds = list(self.outbound_status_mapping.keys())
        self.outbound_cb = ttk.Combobox(row1, textvariable=self.outbound_status_var,
                                       values=["全部"] + outbounds, state="readonly",width=10)
        self.outbound_cb.set("全部")
        self.outbound_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.outbound_cb.pack(side=tk.LEFT, padx=5)

        # 出库类型下拉框
        tk.Label(row1, text="出库类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.outboundtype_var = tk.StringVar()
        outboundtypes = list(self.outbound_type_mapping.keys())
        self.outboundtype_cb = ttk.Combobox(row1, textvariable=self.outboundtype_var,
                                       values=["全部"] + outboundtypes, state="readonly",width=10)
        self.outboundtype_cb.set("全部")
        self.outboundtype_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.outboundtype_cb.pack(side=tk.LEFT, padx=5)

        # 拣货状态下拉框
        tk.Label(row1, text="拣货状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.picking_var = tk.StringVar()
##        pickings = sorted({order["picking_status"] for order in self.original_data})
        pickings = list(self.picking_status_mapping.keys())
        self.picking_cb = ttk.Combobox(row1, textvariable=self.picking_var,
                                       values=["全部"] + pickings, state="readonly",width=10)
        self.picking_cb.set("全部")
        self.picking_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.picking_cb.pack(side=tk.LEFT, padx=5)
        # 出库仓库下拉框
        tk.Label(row1, text="出库仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                       values=["全部"] + warehouses, state="readonly",width=10)
        self.warehouse_cb.set("全部")
##        self.warehouse_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)        

        
        # 物流方式下拉框
        tk.Label(row1, text="物流方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.logistics_var = tk.StringVar()
##        logisticses = sorted({order["logistics_mode"] for order in self.original_data})
        logisticses = list(self.logistics_mode_mapping.keys())
        self.logistics_cb = ttk.Combobox(row1, textvariable=self.logistics_var,
                                       values=["全部"] + logisticses, state="readonly",width=10)
        self.logistics_cb.set("全部")
        self.logistics_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.logistics_cb.pack(side=tk.LEFT, padx=5)

        # 日期选择
        # 计算当前日期往前数10天的日期
        current_date = datetime.now()
        before_7_days = current_date - timedelta(days=7)
        tk.Label(row1, text="起始日期:").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row1,width=10,date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(before_7_days)
##        self.start_cal.set_date(datetime.today().replace(day=1).strftime('%Y-%m-%d'))
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="结束日期:").pack(side=tk.LEFT, padx=5)
        self.end_cal = DateEntry(row1, width=10,date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(None)        
        self.end_cal.pack(side=tk.LEFT, padx=5)
##        self.end_cal.delete(0, tk.END)

        query_btn = tk.Button(row1, text="查询", command=self.outbound_query)
        query_btn.configure(**btn_style)
        query_btn.pack(side=tk.LEFT, padx=5)

        # 清除筛选按钮
        clear_btn = tk.Button(row1, text="清除筛选", command=self.clear_filters, bg="#4CAF50")
        clear_btn.configure(relief="flat")
        clear_btn.pack(side=tk.LEFT, padx=60)

##        # 第二行筛选条件
##        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
##        row2.pack(fill=tk.X, pady=5)

    def outbound_query(self):
        """查询出库单"""
        warehouse_name = self.warehouse_var.get()
        warehouse_id = self.controller.options.get(warehouse_name,"")
        starttime = self.start_cal.get()
        if self.outboundtype_var.get() == "全部":
            outbound_type_code = ""
        else:
            outbound_type_code = self.outboundtype_var.get()
        outbound_query_url=f'https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/issueOrderDetails?outboundStatus=90381001,90381002&outboundType={outbound_type_code}&pickingStatus=47111001,47111002&logistics_mode=&outboundStartTime={starttime}&warehouse_id={warehouse_id}&created_by=&line='
        r = self.controller.session.get(outbound_query_url,headers=HEADERS)

        # 检查登录状态
        if not self._check_response(r):
            return

        self.data=json.loads(r.text)
        origindata=deepcopy(self.data)
        print(self.data)
        # 在新查询前清空详情视图与缓存
        try:
            if hasattr(self, "outbound_detail_tree"):
                for _iid in self.outbound_detail_tree.get_children():
                    self.outbound_detail_tree.delete(_iid)
        except Exception:
            pass
        try:
            if hasattr(self, "detail_cache"):
                self.detail_cache.clear()
        except Exception:
            pass

        # 调用 refresh_data 并传递 data
        self.refresh_data(origindata)

    def apply_filters(self):
        """应用所有筛选条件"""
        # 当筛选条件变化时清理缓存
        self.detail_cache = {}
##        warehouse = self.warehouse_var.get()
        logistics = self.logistics_var.get()
        picking = self.picking_var.get()
        outbound = self.outbound_status_var.get()
        outbound_type = self.outboundtype_var.get()
        # 获取当前选择的出库状态对应的数字代码
        selected_outbound = self.outbound_status_var.get()
        
        self.filtered_data = [
            order for order in self.original_data
            if (self.outbound_status_var.get() == "全部" or order["outbound_status"] == selected_outbound)
            and (picking == "全部" or order["picking_status"] == picking)
            and (outbound_type == "全部" or order["outbound_type"] == outbound_type)
            and (logistics == "全部" or order["logistics_mode"] == logistics)
        ]

        # 存储所有筛选结果
        self.filtered_data_all = self.filtered_data
        
        # 计算总页数
        self.total_pages = max(1, (len(self.filtered_data_all) + self.page_size - 1) // self.page_size)
        
        # 重置到第一页
        self.current_page = 1
        self.refresh_table()
        
    def clear_filters(self):
        """清除所有筛选条件"""
        self.outbound_status_var.set("全部")
        self.outboundtype_var.set("全部")
        self.logistics_var.set("全部")
        self.picking_var.set("全部")
        
        self.apply_filters()

    def setup_data_table(self, parent):
        """构建数据表格"""
        # 表格容器
        table_frame = tk.LabelFrame(parent, text="出库单查询", bg="#f0f0f0",  bd=1, relief=tk.SOLID,
                                   font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=False)
        
        # 表格标题
        columns = [
            "序号","选择","客户名称","出库仓库", "出库指示时间","摘要","订单数量","取消数量","出库数量","出库状态","拣货状态",  "so订单号", "订单号","出库单号","出库类型", 
            "客户代码", "收货地址", "物流方式",  "货物类型",
            "制单人"
        ]
        
        
        # 创建Treeview
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)#修改20250803
        
        # 配置主列
        col_widths = [40,40,120,60,120,100,60,60,60,60,60,190,190,150,80,60,120,60,60,60]
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
        
        table_frame.grid_rowconfigure(0, weight=0)
        table_frame.grid_columnconfigure(0, weight=1)

        # 创建底部控制框架并使用grid布局
        bottom_frame = tk.Frame(parent, bg="#f0f0f0")
        bottom_frame.pack(fill=tk.X, pady=(15, 0))
        # 在底部框架中创建分页和操作按钮区域
        action_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        action_frame.grid(row=0, column=0, sticky="e", padx=10, pady=5)

        pagination_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        pagination_frame.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        bottom_frame.grid_columnconfigure(1, weight=1)  # 让操作按钮区域占据剩余空间
        # 调用分页和操作按钮设置方法，传递对应的框架
        self.setup_pagination_controls(pagination_frame)
        self.setup_action_buttons(action_frame)


        # # 添加详情容器
        # self.detail_container = tk.LabelFrame(parent, text="出库单明细", bg="#f0f0f0",  bd=1, relief=tk.SUNKEN,
        #                            font=("微软雅黑", 10, "bold"))
        # self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
        
        # # 创建详情Treeview
        # self.detail_columns = ["序号", "CARG全码/产品编码", "产品名称", "品牌", "指示拣货库位",
        #                        "库位属性", "订单数量", "取消数量", "出库数量", "出库批次",
        #                        "最后修改人", "最后修改时间"]
        # self.outbound_detail_tree = ttk.Treeview(self.detail_container, columns=self.detail_columns, 
        #                               show="headings", height=15)
        
        # # 配置详情列
        # detail_col_widths = [20, 100, 300, 60, 60, 60, 60, 60, 60, 80, 60, 100]
        # for col, width in zip(self.detail_columns, detail_col_widths):
        #     self.outbound_detail_tree.heading(col, text=col)
        #     self.outbound_detail_tree.column(col, width=width, anchor="center")
        
        # # 添加滚动条
        # detail_vsb = ttk.Scrollbar(self.detail_container, orient="vertical", command=self.outbound_detail_tree.yview)
        # detail_hsb = ttk.Scrollbar(self.detail_container, orient="horizontal", command=self.outbound_detail_tree.xview)
        # self.outbound_detail_tree.configure(yscrollcommand=detail_vsb.set, xscrollcommand=detail_hsb.set)
        
        # # 布局详情Treeview
        # self.outbound_detail_tree.grid(row=0, column=0, sticky="nsew")
        # detail_vsb.grid(row=0, column=1, sticky="ns")
        # detail_hsb.grid(row=1, column=0, sticky="ew")
        
        # self.detail_container.grid_rowconfigure(0, weight=0)
        # self.detail_container.grid_columnconfigure(0, weight=1)        

        
##        # 初始隐藏详情容器
##        self.detail_container.pack_forget()
        
        # 绑定点击事件到选择列，实现复选框功能
##        self.tree.bind("<Button-3>", self.on_treeview_click)
        # 绑定双击事件
        self.tree.bind("<Button-1>", self.on_double_click)
##        self.tree.bind("<<TreeviewOpen>>", self.on_expand)  # 添加20250803 绑定展开事件
        # 存储复选框状态的字典
        self.checkbox_states = {}
        # 初始化缓存和状态
        self.detail_cache = {}  # 存储已获取的详细信息       
        # 初始化数据
        self.refresh_table()
        # 为Treeview添加tooltip功能
        tooltip_manager.attach_tooltip(self.tree)
    def on_treeview_click(self, event):
        """处理Treeview的点击事件，实现复选框功能"""
        # 获取点击位置
        rowid = self.tree.identify_row(event.y)
        print("rowid")
        print(rowid)
        column = self.tree.identify_column(event.x)
        print("column")
        print(column)
        # 确保点击的是第一列（选择列）
        if rowid and column == '#2':
            # 获取当前行的值
            current_values = self.tree.item(rowid, 'values')
            
            # 切换复选框状态
            if current_values[1] == '☐':
                new_value = '✓'
            else:
                new_value = '☐'
            
            # 更新显示的值
            new_values = list(current_values)
            new_values[1] = new_value
            self.tree.item(rowid, values=new_values)
            
            # 更新复选框状态字典
            self.checkbox_states[rowid] = (new_value == '✓')
            
            # 更新选中项集合
##            order_id = rowid  # 使用行ID作为订单标识
            
            order_id=current_values[13]#修改20250721
            print(order_id)
            if new_value == '✓':
                self.selected_items.add(order_id)
            else:
                if order_id in self.selected_items:
                    self.selected_items.remove(order_id)

    # def on_double_click(self, event):
    #     """处理节点展开事件"""
    #     item = self.tree.identify_row(event.y)
    #     if not item:
    #         return
    #     column = self.tree.identify_column(event.x)
    #     if column == '#2':
    #         return self.on_treeview_click(event)
    #     # 获取出库单号
    #     outbound_no = item  # 行ID就是出库单号
        
    #     # 检查缓存
    #     if outbound_no in self.detail_cache:
    #         detail_data = self.detail_cache[outbound_no]
    #         self.display_detail_data(detail_data)
    #         return

    #     try:
    #         # 获取出库单ID
    #         outbounddata = self.data['data']['rows']
    #         indexed_id = {d["outbound_no"]:d["id"] for d in outbounddata}
    #         outbound_id = indexed_id[outbound_no]
            
    #         # 发送GET请求获取详细信息
    #         detail_url = f"https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/queryDetailList?id={outbound_id}"
    #         response = self.controller.session.get(detail_url, headers=HEADERS)

    #         # 检查登录状态
    #         if not self._check_response(response):
    #             return

    #         if response.status_code == 200:
    #             detail_data = response.json()['data']
    #             # 存入缓存
    #             self.detail_cache[outbound_no] = detail_data
    #             self.display_detail_data(detail_data)
                
    #     except Exception as e:
    #         print(f"获取详细信息失败: {e}")

# ... existing code ...
    def on_double_click(self, event):
        """处理节点展开事件"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        column = self.tree.identify_column(event.x)
        if column == '#2':
            return self.on_treeview_click(event)
        # 获取出库单号
        outbound_no = item  # 行ID就是出库单号
        
        # 检查缓存
        if outbound_no in self.detail_cache:
            detail_data = self.detail_cache[outbound_no]
            self.display_detail_data(detail_data)
            return

        try:
            # 获取出库单ID
            outbounddata = self.data['data']['rows']
            indexed_id = {d["outbound_no"]:d["id"] for d in outbounddata}
            outbound_id = indexed_id[outbound_no]
            
            # 发送GET请求获取详细信息
            detail_url = f"https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/queryDetailList?id={outbound_id}"
            response = self.controller.session.get(detail_url, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return

            if response.status_code == 200:
                detail_data = response.json()['data']
                # 存入缓存
                self.detail_cache[outbound_no] = detail_data
                self.display_detail_data(self.parent,detail_data)
                
        except Exception as e:
            print(f"获取详细信息失败: {e}")
# ... existing code ...

    # def display_detail_data(self, detail_data):
    #     """显示详情数据"""
    #     # 清空详情Treeview
    #     self.outbound_detail_tree.delete(*self.outbound_detail_tree.get_children())
        
    #     # 填充商品数据
    #     for i, item_data in enumerate(detail_data, 1):
    #         location_type_map = {90041001:"拣货库位",90041002:"暂存库位",90041003:"捡存一体",90041004:"冻结库位",90041005:"散片库位",90041006:"整箱库位",90041007:"质量问题库位"}
    #         location_type = location_type_map.get(item_data.get("location_type", ""), "")
            
    #         self.outbound_detail_tree.insert("", "end", values=(
    #             i,
    #             item_data.get("part_code", ""),
    #             item_data.get("part_name", ""),
    #             item_data.get("BRAND_NAME", ""),
    #             item_data.get("location_no", ""),
    #             location_type,
    #             item_data.get("order_quantity", ""),
    #             item_data.get("canceled_num", 0),
    #             item_data.get("outbound_quantity", ""),
    #             item_data.get("out_storage_batch", ""),
    #             item_data.get("updated_by_name", ""),
    #             item_data.get("updated_at", "")
    #         ))
        
    #     # 显示详情容器
    #     self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
    # def display_detail_data(self, detail_data):
    #     """显示详情数据"""
    #     # 清空详情Treeview
    #     self.outbound_detail_tree.delete(*self.outbound_detail_tree.get_children())
        
    #     # 初始化汇总变量
    #     total_order_quantity = 0
    #     total_canceled_num = 0
    #     total_outbound_quantity = 0
        
    #     # 填充商品数据
    #     for i, item_data in enumerate(detail_data, 1):
    #         location_type_map = {90041001:"拣货库位",90041002:"暂存库位",90041003:"捡存一体",90041004:"冻结库位",90041005:"散片库位",90041006:"整箱库位",90041007:"质量问题库位"}
    #         location_type = location_type_map.get(item_data.get("location_type", ""), "")
            
    #         # 累加数量用于汇总
    #         order_quantity = item_data.get("order_quantity", 0) or 0
    #         canceled_num = item_data.get("canceled_num", 0) or 0
    #         outbound_quantity = item_data.get("outbound_quantity", 0) or 0
            
    #         total_order_quantity += order_quantity
    #         total_canceled_num += canceled_num
    #         total_outbound_quantity += outbound_quantity
            
    #         self.outbound_detail_tree.insert("", "end", values=(
    #             i,
    #             item_data.get("part_code", ""),
    #             item_data.get("part_name", ""),
    #             item_data.get("BRAND_NAME", ""),
    #             item_data.get("location_no", ""),
    #             location_type,
    #             order_quantity,
    #             canceled_num,
    #             outbound_quantity,
    #             item_data.get("out_storage_batch", ""),
    #             item_data.get("updated_by_name", ""),
    #             item_data.get("updated_at", "")
    #         ))
        
    #     # 插入汇总行
    #     self.outbound_detail_tree.insert("", "end", values=(
    #         "合计",
    #         "", "", "", "", "",
    #         total_order_quantity,
    #         total_canceled_num,
    #         total_outbound_quantity,
    #         "", "", ""
    #     ), tags=("summary",))
        
    #     # 配置汇总行的样式（可选）
    #     self.outbound_detail_tree.tag_configure("summary", background="#f0f0f0", font=("Arial", 13, "bold"))
        
    #     # 显示详情容器
    #     self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
# ... existing code ...
    def display_detail_data(self, parent,detail_data):
        """显示详情数据（弹窗方式）"""
        # 创建弹窗
        detail_window = tk.Toplevel(parent)
        detail_window.title("出库单明细")
        detail_window.geometry("1500x800")
        detail_window.transient(parent)  # 设置为临时窗口
        detail_window.grab_set()  # 模态窗口，阻止与其他窗口交互
        
        # 居中显示
        detail_window.update_idletasks()
        x = (detail_window.winfo_screenwidth() // 2) - (1500 // 2)
        y = (detail_window.winfo_screenheight() // 2) - (800 // 2)
        detail_window.geometry(f"1500x800+{x}+{y}")
        
        # 创建详情容器
        detail_container = tk.LabelFrame(detail_window, text="出库单明细", bd=1, relief=tk.SUNKEN,
                                       font=("微软雅黑", 10, "bold"))
        detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建详情Treeview
        detail_columns = ["序号", "CARG全码/产品编码", "产品名称", "品牌", "指示拣货库位",
                         "库位属性", "订单数量", "取消数量", "出库数量", "出库批次",
                         "最后修改人", "最后修改时间"]
        detail_tree = ttk.Treeview(detail_container, columns=detail_columns, show="headings", height=20)
        
        # 配置详情列
        detail_col_widths = [20, 100, 300, 60, 60, 60, 60, 60, 60, 80, 60, 100]
        for col, width in zip(detail_columns, detail_col_widths):
            detail_tree.heading(col, text=col)
            detail_tree.column(col, width=width, anchor="center")
        
        # 添加滚动条
        detail_vsb = ttk.Scrollbar(detail_container, orient="vertical", command=detail_tree.yview)
        detail_hsb = ttk.Scrollbar(detail_container, orient="horizontal", command=detail_tree.xview)
        detail_tree.configure(yscrollcommand=detail_vsb.set, xscrollcommand=detail_hsb.set)
        
        # 布局详情Treeview
        detail_tree.grid(row=0, column=0, sticky="nsew")
        detail_vsb.grid(row=0, column=1, sticky="ns")
        detail_hsb.grid(row=1, column=0, sticky="ew")
        
        detail_container.grid_rowconfigure(0, weight=1)
        detail_container.grid_columnconfigure(0, weight=1)
        
        # 初始化汇总变量
        total_order_quantity = 0
        total_canceled_num = 0
        total_outbound_quantity = 0
        
        # 填充商品数据
        for i, item_data in enumerate(detail_data, 1):
            location_type_map = {90041001:"拣货库位",90041002:"暂存库位",90041003:"捡存一体",90041004:"冻结库位",90041005:"散片库位",90041006:"整箱库位",90041007:"质量问题库位"}
            location_type = location_type_map.get(item_data.get("location_type", ""), "")
            
            # 累加数量用于汇总
            order_quantity = item_data.get("order_quantity", 0) or 0
            canceled_num = item_data.get("canceled_num", 0) or 0
            outbound_quantity = item_data.get("outbound_quantity", 0) or 0
            
            total_order_quantity += order_quantity
            total_canceled_num += canceled_num
            total_outbound_quantity += outbound_quantity
            
            detail_tree.insert("", "end", values=(
                i,
                item_data.get("part_code", ""),
                item_data.get("part_name", ""),
                item_data.get("BRAND_NAME", ""),
                item_data.get("location_no", ""),
                location_type,
                order_quantity,
                canceled_num,
                outbound_quantity,
                item_data.get("out_storage_batch", ""),
                item_data.get("updated_by_name", ""),
                item_data.get("updated_at", "")
            ))
        
        # 插入汇总行
        detail_tree.insert("", "end", values=(
            "合计",
            "", "", "", "", "",
            total_order_quantity,
            total_canceled_num,
            total_outbound_quantity,
            "", "", ""
        ), tags=("summary",))
        
        # 配置汇总行的样式（可选）
        detail_tree.tag_configure("summary", background="#f0f0f0", font=("Arial", 13, "bold"))
        # 为详情Treeview添加tooltip功能
        tooltip_manager.attach_tooltip(detail_tree)        
        # 添加关闭按钮
        button_frame = tk.Frame(detail_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        close_btn = tk.Button(button_frame, text="关闭", command=detail_window.destroy,
                             bg="#4CAF50", fg="white", padx=10, pady=5, bd=0)
        close_btn.pack(side=tk.RIGHT)
        
        # 窗口关闭事件处理
        detail_window.protocol("WM_DELETE_WINDOW", detail_window.destroy)
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
        for index,order in enumerate(self.current_page_data,start=1):
            tags = ('evenrow',) if index % 2 == 0 else ('oddrow',)
            values = (
                index,#序号
                '☐',  # 复选框占位
                order.get("dealer_name", ""),
                order.get("WAREHOUSE_NAME", ""),
                order.get("created_at", ""),
                order.get("remark", ""),
                order.get("order_quantity", 0),
                order.get("canceled_num", 0),
                order.get("outbound_quantity", 0),
                order.get("outbound_status", ""),
                order.get("picking_status", ""),
                order.get("bill_no",""),
                order.get("order_number", ""),
                order.get("outbound_no", ""),
                order.get("outbound_type", ""),
                order.get("dealer_code",""),
                order.get("delivery_address",""),
                order.get("logistics_mode",""),
                order.get("goods_type",""),
                order.get("created_by","")

            )
            self.tree.insert("", "end", values=values, iid=order.get("outbound_no", order.get("outboundNo", "")),tags=tags)  # 使用出库单号作为行ID
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
        tk.Button(
            parent,
            text="生成拣货单",
            command=self.generate_picking_order,
            padx=10,
            pady=5,
            bd=0,
            bg="#673AB7",
            fg="white",
            activebackground="#45a049"
        ).pack(side=tk.LEFT, padx=10)
        # 初始化分页信息
        self.update_page_info()

    def setup_action_buttons(self, parent):
        
        # 按钮样式
        btn_style = {"bg": "#4CAF50", "fg": "white", "activebackground": "#45a049"}
        
        # 按钮组
        buttons = [
            ("全选", self.select_all),
            ("全不选", self.deselect_all),
            ("反选", self.toggle_selection)
        ]
        
        for text, cmd in buttons:
            btn = tk.Button(parent, text=text, command=cmd, padx=10, pady=5, bd=0)
            btn.configure(**btn_style)
            btn.pack(side=tk.LEFT, padx=5)
        # 按钮样式
##        btn_style1 = {"bg": "#673AB7", "fg": "white", "padx": 10, "pady": 5, 
##                    "bd": 0, "activebackground": "#45a049"}
##        tk.Button(btn_frame, text="生成拣货单", command=self.generate_picking_order, **btn_style1).pack(side=tk.LEFT, padx=10)

    def select_all(self):
        """全选"""
        for order in self.current_page_data:
            order_id = order.get("outbound_no")
            self.selected_items.add(order_id)
        
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            vals = self.tree.item(item, 'values')
            vals_list = list(vals) if isinstance(vals, (list, tuple)) else [vals]
            if vals_list:
                vals_list[1] = '✓'
            else:
                vals_list = ['✓']
            self.tree.item(item, values=tuple(vals_list))

    def deselect_all(self):
        """全不选"""
        self.selected_items.clear()
        
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            vals = self.tree.item(item, 'values')
            vals_list = list(vals) if isinstance(vals, (list, tuple)) else [vals]
            if vals_list:
                vals_list[1] = '☐'
            else:
                vals_list = ['☐']
            self.tree.item(item, values=tuple(vals_list))

    def toggle_selection(self):
        """反选"""
        all_order_ids = set(order.get("outbound_no") for order in self.current_page_data)
        new_selected_items = all_order_ids - self.selected_items
        
        # 更新选中项集合
        self.selected_items = new_selected_items
        
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            print("以下childitem")
            print(item)
            order_id = item
##            order_id = self.tree.item(item, 'iid')#修改20250731
            if order_id in self.selected_items:
                vals = self.tree.item(item, 'values')
                vals_list = list(vals) if isinstance(vals, (list, tuple)) else [vals]
                if vals_list:
                    vals_list[1] = '✓'
                else:
                    vals_list = ['✓']
                self.tree.item(item, values=tuple(vals_list))
            else:
                vals = self.tree.item(item, 'values')
                vals_list = list(vals) if isinstance(vals, (list, tuple)) else [vals]
                if vals_list:
                    vals_list[1] = '☐'
                else:
                    vals_list = ['☐']
                self.tree.item(item, values=tuple(vals_list))

    def refresh_data(self,data):
        """加载数据"""

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

        self.original_data = self.parse_and_convert_json(data)
        # 直接应用筛选条件（不需要制单人Checkbuttons）
        self.apply_filters()

    def generate_postdata(self,dict_list, target_key, target_values):
        # 构建键值到字典的映射（假设键值唯一）
        value_to_dict = {d[target_key]: d for d in dict_list if target_key in d}
        
        # 返回匹配的字典列表
        return [value_to_dict[val] for val in target_values if val in value_to_dict]

    def generate_picking_order(self):
        generate_url="https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/generatePickingList"
        outbound_data = self.data
        print("********self.data********")
        print(outbound_data)
        """处理选中订单"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请至少选择一条记录")
            return
        
        # 获取选中项的订单数据
        selected_orders = [order for order in self.filtered_data if order.get("outbound_no") in self.selected_items]
        print("********selected_orders********")
        print(selected_orders)
        # 显示处理信息
        if not messagebox.askyesno("确认", f"将处理{len(selected_orders)}条订单记录，是否生成拣货单？"):
            return
        processed_outbound_orders = list(order.get("outbound_no") for order in selected_orders)
        print(processed_outbound_orders)
        """生成拣货单"""
        postdata= self.generate_postdata(outbound_data['data']['rows'],"outbound_no",processed_outbound_orders)
        print(postdata)
        try:
            response=self.controller.session.post(generate_url,headers=HEADERS,data=json.dumps(postdata))
            
            # 检查登录状态
            if not self._check_response(response):
                return

            response.raise_for_status()  # 检查HTTP错误
            
            data = response.json()
            
            if 'success' in data and data['success'] == True:
                messagebox.showinfo("成功", f"已成功处理{len(selected_orders)}条订单记录")
            else:
                if 'errorMsg' in data and not data['errorMsg'] == None:
                    messagebox.showerror("出错了", data['errorMsg']) 

                
        except requests.exceptions.RequestException as e:
            return False, f"请求异常: {str(e)}"
        except json.JSONDecodeError:
            return False, "响应不是有效的JSON格式"    
        # 重新应用筛选条件
        self.outbound_query()


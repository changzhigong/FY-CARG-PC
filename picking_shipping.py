import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import threading
from datetime import datetime, timedelta
from tkcalendar import DateEntry
from base_page import BasePage
from copy import deepcopy
from tooltip_manager import tooltip_manager
# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}
def load_config(file_path):
    """从JSON文件加载配置"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 从文件加载配置
loaded_config = load_config("warehouse_config.json")

# 获取原始字典结构
WAREHOUSE_OPTIONS = loaded_config["WAREHOUSE_OPTIONS"]
DRIVER_OPTIONS = loaded_config["DRIVER_OPTIONS"]
warehouse_data = loaded_config["warehouse_data"]
driver_data = loaded_config["driver_data"]
warehouse_vehicle_data = loaded_config["warehouse_vehicle_data"]

class OneKeyProcessPage(BasePage):
    """一键发运处理页面"""
    def __init__(self, parent, controller):
        # 定义打印状态映射关系
        self.print_status_mapping = {
            "已打印": 90481001,
            "未打印": 90481002
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
            "拣货中": 47111002,
            "拣货完成": 47111003,
            "提前关闭":47111004,
            "作废":47111005
        }
        self.original_data = []  # 存储原始数据
        self.filtered_data = []  # 存储筛选后的数据
        self.selected_items = set()  # 存储选中的项
        self.picking_detail_cache = {}  # 缓存子节点数据
        # 加载数据
        self.filtered_data = self.original_data.copy()        
        # 新增分页相关属性
        self.current_page = 1
        self.page_size = 20  # 每页显示200条
        self.total_pages = 1
        self.filtered_data_all = []  # 存储所有筛选后的数据
        # 可选的每页显示条数
        self.page_size_options = [5, 10, 20, 50, 100, 500]
        # 初始化分页信息变量
        self.page_info_var = tk.StringVar()  # 新增这一行
        self.print_status_var =tk.StringVar()
        self.action_controls_enabled: bool = False
        self.picking_status_listbox: tk.Listbox | None = None
        self.picking_status_scrollbar: ttk.Scrollbar | None = None
        self.controller = controller
        self.parent = parent
        super().__init__(parent, controller)

    def _check_response(self, response):
        # """检查响应中的登录状态"""
        # if self.controller.check_login_status(response):
        #     return False  # 已被登出
        # return True  # 正常状态            
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
                # 打印状态转换
                print_status_code = order.get("print_status", "")
                for text, code in self.print_status_mapping.items():
                    if code == print_status_code:
                        order["print_status"] = text
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
        filter_frame.pack(fill=tk.X, pady=(0, 5), ipadx=10, ipady=5)
        
        # 第一行筛选条件
        row1 = tk.Frame(filter_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=3)
        # 按钮样式
        btn_style = {"bg": "#4CAF50", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        # 打印状态筛选
        tk.Label(row1, text="打印状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.print_status_var = tk.StringVar(value="全部")
        status_options = ["全部", "已打印", "未打印"]
        for option in status_options:
            tk.Radiobutton(row1, text=option, variable=self.print_status_var,
                         value=option, command=self.apply_filters,
                         bg="#f0f0f0").pack(side=tk.LEFT, padx=5)

        # 拣货状态多选框
        tk.Label(row1, text="拣货状态:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))

        # 创建列表框和滚动条
        self.picking_status_listbox = tk.Listbox(row1, selectmode=tk.SINGLE,bg="#4CAF50",relief=tk.SUNKEN, width = 10, height= 2,exportselection=False)
        self.picking_status_scrollbar = ttk.Scrollbar(row1, orient=tk.VERTICAL, command=self.picking_status_listbox.yview)
        self.picking_status_listbox.configure(yscrollcommand=self.picking_status_scrollbar.set)
        
        self.picking_status_listbox.pack(side=tk.LEFT, fill=tk.X, expand=False)
        self.picking_status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 更新拣货状态列表框
        self.picking_status_listbox.delete(0, tk.END)
        for status in self.picking_status_mapping.keys():
            self.picking_status_listbox.insert(tk.END, status)

        # 出库仓库下拉框
        tk.Label(row1, text="出库仓库:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.warehouse_var = tk.StringVar()
        warehouses = list(self.controller.options.keys())
        self.warehouse_cb = ttk.Combobox(row1, textvariable=self.warehouse_var,
                                       values=["全部"] + warehouses, state="readonly",width=10)
        self.warehouse_cb.set("全部")
        self.warehouse_cb.pack(side=tk.LEFT, padx=5)        

        # 物流方式下拉框
        tk.Label(row1, text="物流方式:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(5,5))
        self.logistics_var = tk.StringVar()
        logisticses = list(self.logistics_mode_mapping.keys())
        self.logistics_cb = ttk.Combobox(row1, textvariable=self.logistics_var,
                                       values=["全部"] + logisticses, state="readonly",width=10)
        self.logistics_cb.set("全部")
        self.logistics_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.logistics_cb.pack(side=tk.LEFT, padx=5)

        # 日期选择
        # 计算当前日期往前数一周的日期
        current_date = datetime.now()
        before_7_days = current_date - timedelta(days=7)
        tk.Label(row1, text="起始日期:").pack(side=tk.LEFT, padx=5)
        self.start_cal = DateEntry(row1,width=10,date_pattern='yyyy-mm-dd')
        self.start_cal.set_date(before_7_days)
        self.start_cal.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="结束日期:").pack(side=tk.LEFT, padx=5)
        self.end_cal = DateEntry(row1, width=10,date_pattern='yyyy-mm-dd')
        self.end_cal.set_date(None)        
        self.end_cal.pack(side=tk.LEFT, padx=5)

        tk.Button(row1, text="查询", command=self.picking_query, **btn_style).pack(side=tk.LEFT, padx=5)

        # 清除筛选按钮
        tk.Button(row1, text="清除筛选", command=self.clear_filters,
                 bg="#4CAF50", relief=tk.FLAT).pack(side=tk.LEFT, padx=60)

##        # 第二行筛选条件
##        row2 = tk.Frame(filter_frame, bg="#f0f0f0")
##        row2.pack(fill=tk.X, pady=5)

    def _set_widget_enabled(self, widget, enable: bool):
        try:
            if hasattr(widget, "state"):
                try:
                    if enable:
                        widget.state(["!disabled"])
                    else:
                        widget.state(["disabled"])
                    return
                except Exception:
                    pass
            if hasattr(widget, "configure"):
                widget.configure(state=(tk.NORMAL if enable else tk.DISABLED))
        except Exception:
            try:
                if hasattr(widget, "configure"):
                    widget.configure(state=tk.DISABLED)
            except Exception:
                pass

    def picking_query(self):
        """查询拣货单"""
        warehouse_name = self.warehouse_var.get()
        warehouse_id = self.controller.options.get(warehouse_name,"")
        starttime = self.start_cal.get()

        # 获取拣货状态（多选）
        picking_status_by_indices = self.picking_status_listbox.curselection()
        print(picking_status_by_indices)
        if len(picking_status_by_indices)==0:
            picking_status =""
        else:
            picking_status = ",".join(["%s" % self.picking_status_mapping[self.picking_status_listbox.get(i)] for i in picking_status_by_indices])
        print(picking_status)
        headers = {'Referer': "https://xb.fy-carg.com/"}
        picking_query_url=f'https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/pickingListQueryNew?picking_order_no=&outbound_no=&order_number=&warehouse_id={warehouse_id}&dealer_code=&dealer_name=&dealerName=&packageStatus=&print_status=&created_by=&logistics_mode=&sortOrder=90591001&part_code=&part_name=&picking_status={picking_status}&startTime={starttime}&salesman=&line=&limit=1500&pageNum=1&outboundType=&location_area=&outboundStatus=&orderTypeStr='
        r = self.controller.session.get(picking_query_url,headers=headers) 

        # 检查登录状态
        if not self._check_response(r):
            return

        data=json.loads(r.text)
        self.picking_data=json.loads(r.text)
        origindata=deepcopy(self.picking_data)
        print(self.picking_data)

        # 在新查询前彻底清空详情视图与编辑控件
        try:
            # 销毁所有现有的编辑控件
            for combo in getattr(self, 'location_combos', []):
                if combo.winfo_exists():
                    combo.destroy()
            
            for spin in getattr(self, 'quantity_spins', []):
                if spin.winfo_exists():
                    spin.destroy()
            
            for combo in getattr(self, 'reason_combos', []):
                if combo.winfo_exists():
                    combo.destroy()
            
            # 清空列表
            self.detail_item_ids = []
            self.location_combos = []
            self.quantity_spins = []
            self.quantity_vars = []
            self.reason_combos = []
        except Exception as e:
            print(f"清理编辑控件时出错: {e}")

        try:
            if hasattr(self, "picking_detail_tree"):
                for _iid in self.picking_detail_tree.get_children():
                    self.picking_detail_tree.delete(_iid)
        except Exception:
            pass
        try:
            if hasattr(self, "picking_detail_cache"):
                self.picking_detail_cache.clear()
        except Exception:
            pass

        
        # 调用 refresh_data 并传递 data
        self.refresh_data(origindata)

    def apply_filters(self):
        """应用所有筛选条件"""
        self.picking_detail_cache = {}  # 缓存子节点数据
        logistics = self.logistics_var.get()
        # 获取当前选择的打印状态对应的数字代码
        selected_print_status = self.print_status_var.get()
        
        self.filtered_data = [
            order for order in self.original_data
            if (self.print_status_var.get() == "全部" or order["print_status"] == selected_print_status)
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
        self.print_status_var.set("全部")
        self.warehouse_var.set("全部")
        self.logistics_var.set("全部")
        # 修复：检查 self.picking_status_listbox 是否为 None
        if self.picking_status_listbox is not None:
            self.picking_status_listbox.selection_clear(0, tk.END)
        
        self.apply_filters()

    def setup_data_table(self, parent):
        """构建数据表格"""
        # 表格容器
        table_frame = tk.LabelFrame(parent, text="拣货单查询", bg="#f0f0f0",  bd=1, relief=tk.SOLID,
                                   font=("微软雅黑", 10, "bold"))
        table_frame.pack(fill=tk.BOTH, expand=False)

        
        # 表格标题
        columns = [
            "序号","选择","拣货状态", "打印状态", "拣货单号", "计划拣货数量","取消数量","实际拣货数量","单据总金额","摘要","拣货人", "出库单号","客户名称",
            "客户代码", "收货地址", "物流方式", "物流代收公司","出库仓库", "制单人",
             "拣货单生成时间"
        ]
        
        # 创建Treeview
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        
        # 配置列
        col_widths = [50,50, 60, 60, 150,100, 60, 60, 100, 140, 60, 180, 150, 80, 150, 80, 80, 80, 100, 120]
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
        # self.detail_container = tk.LabelFrame(parent, text="拣货单明细", bg="#f0f0f0",  bd=1, relief=tk.SUNKEN,
        #                            font=("微软雅黑", 10, "bold"))
        # self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
        
        # # 创建详情Treeview
        # self.detail_columns = ["序号","品牌", "CARG全码/产品编码", "产品名称",  "指示拣货库位",
        #                        "计划拣货数", "取消数", "实际拣货库位", "实际拣货数量","拣货差异原因","拣货单号","出库单号","订单号",
        #                        "客户代码", "客户名称","货物类型"]
        # self.picking_detail_tree = ttk.Treeview(self.detail_container, columns=self.detail_columns,
        #                               show="headings", height=15)

        # # 配置详情列
        # detail_col_widths = [50, 80, 150, 300, 80, 80, 80, 100, 80, 80, 180, 180,180, 80, 120, 60]
        # for col, width in zip(self.detail_columns, detail_col_widths):
        #     self.picking_detail_tree.heading(col, text=col)
        #     self.picking_detail_tree.column(col, width=width, anchor="center")
        
        # # 添加滚动条
        # detail_vsb = ttk.Scrollbar(self.detail_container, orient="vertical", command=self.picking_detail_tree.yview)
        # detail_hsb = ttk.Scrollbar(self.detail_container, orient="horizontal", command=self.picking_detail_tree.xview)
        # self.picking_detail_tree.configure(yscrollcommand=detail_vsb.set, xscrollcommand=detail_hsb.set)
        
        # # 布局详情Treeview
        # self.picking_detail_tree.grid(row=0, column=0, sticky="nsew")
        # detail_vsb.grid(row=0, column=1, sticky="ns")
        # detail_hsb.grid(row=1, column=0, sticky="ew")
        
        # self.detail_container.grid_rowconfigure(0, weight=0)
        # self.detail_container.grid_columnconfigure(0, weight=1)


        # # 拣货人（多选）下拉框区域，参考 2943-2954
        # tk.Label(parent, text="拣货人:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 2))
        # self.picking_frame = ttk.Frame(parent)
        # self.picking_frame.pack(side=tk.LEFT, padx=(0, 10))
        # self.picking_listbox = tk.Listbox(self.picking_frame, selectmode=tk.SINGLE, height=3, exportselection=False)
        # self.picking_scrollbar = ttk.Scrollbar(self.picking_frame, orient=tk.VERTICAL, command=self.picking_listbox.yview)
        # self.picking_listbox.configure(yscrollcommand=self.picking_scrollbar.set)
        # self.picking_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # self.picking_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 仓库变化时更新拣货人列表（参考 3085-3092）
        # var = getattr(self, "warehouse_var", None)
        # # 创建按钮时初始状态为禁用
        # self.Picking_isSave = tk.Button(parent, text="暂存", command=self.is_Save, state='disabled', **button_style)
        # self.Picking_isSave.pack(side=tk.LEFT, padx=10)
        # self.Picking_complete = tk.Button(parent, text="拣货完成", command=self.picking_complete, state='disabled', **button_style)
        # self.Picking_complete.pack(side=tk.LEFT, padx=10)
        
        # 初始更新交互状态
        try:
            self._update_action_controls_state()
        except Exception:
            pass
        
        # 绑定 tree 选择事件，确保选择和详情加载后更新
        try:
            self.tree.bind("<<TreeviewSelect>>", self._update_action_controls_state)
            self.tree.bind("<ButtonRelease-1>", lambda e: self.after(500, self._update_action_controls_state()))
        except Exception:
            pass
        
        # 绑定双击事件
        self.tree.bind("<Button-1>", self.on_left_click)
        # 存储复选框状态的字典
        self.checkbox_states = {}
        # 初始化缓存和状态
        self.picking_detail_cache = {}  # 存储已获取的详细信息 

        # # 初始化编辑控件相关变量
        # self.detail_item_ids = []  # 存储详情Treeview的行ID
        # self.location_combos = []  # 存储实际拣货库位的下拉框
        # self.quantity_spins = []   # 存储实际拣货数量的调节钮
        # self.reason_combos = []    # 存储拣货差异原因的下拉框
        # self.quantity_vars = []    # 存储数量变量，防止被回收
        
        # 拣货差异原因选项和映射
        self.reason_options = ['', '库存差异', '库存不良', '整箱差异', '拣货破损', '客户取消']

        
        # # 绑定事件，确保编辑控件跟随滚动
        # self.picking_detail_tree.bind('<Motion>', self.position_detail_widgets)
        # self.picking_detail_tree.bind('<ButtonPress-1>', self.position_detail_widgets)
        # self.picking_detail_tree.bind('<MouseWheel>', self.position_detail_widgets)
        # self.picking_detail_tree.bind('<Leave>', self.position_detail_widgets)
        # self.picking_detail_tree.bind('<Map>', self.position_detail_widgets)

        # 初始化数据
        self.refresh_table()
        # 为Treeview添加tooltip功能
        tooltip_manager.attach_tooltip(self.tree)
    # def update_picking_listbox_by_warehouse(self):
    #     """根据仓库名称更新拣货人列表，参考 3085-3092"""
    #     # 交互条件守卫：不可交互则清空并返回
    #     try:
    #         can_edit = getattr(self, "action_controls_enabled", None)
    #         if can_edit is None:
    #             can_edit = False
    #             if hasattr(self, "tree") and self.tree.selection():
    #                 item_id = self.tree.selection()[0]
    #                 values = self.tree.item(item_id, "values") or []
    #                 # 原判断：任意列包含"拣货中"即视为允许交互
    #                 # can_edit = any(str(v) == "拣货中" for v in values)
    #                 # 新判断：精确检查"拣货状态"列是否为"拣货中"（该列为第二列）
    #                 pick_status = values[1] if len(values) > 1 else ""
    #                 can_edit = (str(pick_status) == "拣货中")
    #         if not can_edit:
    #             if hasattr(self, "picking_listbox") and self.picking_listbox:
    #                 self.picking_listbox.delete(0, tk.END)
    #             return
    #     except Exception:
    #         if hasattr(self, "picking_listbox") and self.picking_listbox:
    #             self.picking_listbox.delete(0, tk.END)
    #         return
    #     try:
    #         warehouse_name = self.warehouse_var.get() if hasattr(self, "warehouse_var") else ""
    #     except Exception:
    #         warehouse_name = ""
    #     # 从可用数据源获取人员列表，优先使用类属性 self.warehouse_data，否则尝试全局 warehouse_data
    #     data_source =warehouse_data

    #     personnel_lists = data_source.get(warehouse_name, [[], [], [], []])

    #     # 获取拣货人列表，优先使用 personnel_lists[0]，否则使用空列表
    #     picking_by_list = personnel_lists[0] if isinstance(personnel_lists, (list, tuple)) and len(personnel_lists) > 0 else []
    #     # 更新拣货人列表框
    #     if hasattr(self, "picking_listbox") and self.picking_listbox:
    #         self.picking_listbox.delete(0, tk.END)
    #         for name in picking_by_list:
    #             self.picking_listbox.insert(tk.END, name)

# ... existing code ...
    def update_picking_listbox_by_warehouse(self):
        # 交互条件守卫：不可交互则清空并返回
        try:
            can_edit = getattr(self, "action_controls_enabled", None)
            if can_edit is None:
                can_edit = False
                if hasattr(self, "tree") and self.tree.selection():
                    item_id = self.tree.selection()[0]
                    values = self.tree.item(item_id, "values") or []
                    # 原判断：任意列包含"拣货中"即视为允许交互
                    # can_edit = any(str(v) == "拣货中" for v in values)
                    # 新判断：精确检查"拣货状态"列是否为"拣货中"（该列为第二列）
                    pick_status = values[2] if len(values) > 2 else ""  # 修复索引为2（第三列是拣货状态）
                    can_edit = (str(pick_status) == "拣货中")
            # 在弹窗中不需要检查action_controls_enabled，因为可能还未设置
            # 只要仓库信息有效就应该更新列表
        except Exception:
            pass
            
        try:
            warehouse_name = self.warehouse_var.get() if hasattr(self, "warehouse_var") else ""
        except Exception:
            warehouse_name = ""
            
        # 从可用数据源获取人员列表，优先使用类属性 self.warehouse_data，否则尝试全局 warehouse_data
        data_source = warehouse_data

        personnel_lists = data_source.get(warehouse_name, [[], [], [], []])

        # 获取拣货人列表，优先使用 personnel_lists[0]，否则使用空列表
        picking_by_list = personnel_lists[0] if isinstance(personnel_lists, (list, tuple)) and len(personnel_lists) > 0 else []
        # 更新拣货人列表框
        if hasattr(self, "picking_listbox") and self.picking_listbox:
            self.picking_listbox.delete(0, tk.END)
            for name in picking_by_list:
                self.picking_listbox.insert(tk.END, name)
# ... existing code ...

    # def is_Save(self):
    #     """暂存：提交拣货数据到指定接口，包含 dataList 和 picking_by"""
    #     # 检查当前选中的订单是否处于"拣货中"状态
    #     selected_items = self.tree.selection()
    #     for item in selected_items:
    #         values = self.tree.item(item, 'values')
    #         # 拣货状态在第3列(索引为2)
    #         if len(values) <= 2 or values[2] != "拣货中":
    #             messagebox.showwarning("警告", "只有状态为'拣货中'的订单才能进行暂存操作")
    #             return
    #     # 添加确认弹窗
    #     if not messagebox.askyesno("确认暂存", "确定要执行暂存操作吗？"):
    #         return
    #     # 获取拣货人（多选）
    #     picking_by = ""
    #     if hasattr(self, "picking_listbox") and self.picking_listbox:
    #         try:
    #             indices = self.picking_listbox.curselection()
    #             picking_by = ",".join([self.picking_listbox.get(i) for i in indices])
    #         except Exception:
    #             picking_by = ""

    #     # 获取拣货单详情数据 detail_data
    #     # 优先从当前选中拣货单的缓存中取；按项目已有命名尝试 self.picking_detail_cache
    #     detail_data = None
    #     try:
    #         # 从主表 Tree 选中项获取拣货单号；若无选中则使用焦点项
    #         picking_order_no = None
    #         try:
    #             sel = self.tree.selection()
    #             if sel:
    #                 picking_order_no = sel[0]
    #             else:
    #                 picking_order_no = self.tree.focus()
    #         except Exception:
    #             picking_order_no = None
    #         if picking_order_no and hasattr(self, "picking_detail_cache"):
    #             detail_data = self.picking_detail_cache.get(picking_order_no)
    #         if detail_data is None:
    #             try:
    #                 # 这里尝试用当前界面的选中单据键获取，若无则取任意已加载的详情
    #                 selected_keys = list(self.picking_detail_cache.keys())
    #                 if selected_keys:
    #                     detail_data = self.picking_detail_cache.get(selected_keys[0])
    #             except Exception:
    #                 detail_data = None
    #     except Exception:
    #         pass
    #     print(detail_data)
    #     if detail_data is None:
    #         # 如果未获取到详情，提示并中止
    #         try:
    #             messagebox.showwarning("提示", "未找到拣货单详情数据，无法暂存提交。")
    #         except Exception:
    #             pass
    #         return

    #     payload = {
    #         "dataList": detail_data,
    #         "picking_by": picking_by or "",
    #         "isSave":1
    #     }
    #     print(payload)

    #     url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"

    #     #调用项目统一 POST 方法（占位名：self.request_post），请替换为你实际封装方法
    #     try:
    #         resp = self.controller.session.post(url, json=payload,headers=HEADERS)
    #     except Exception:
    #         resp = None

    #     # 检查登录状态
    #     if not self._check_response(resp):
    #         return

    #     # 简单反馈
    #     try:
    #         if resp and resp.status_code == 200:
    #             # HTTP请求成功，检查业务状态码
    #             resp_data = resp.json()
    #             if resp_data.get("resultCode") == 200:
    #                 messagebox.showinfo("成功", "暂存成功")
    #                 # 暂存成功后，失效缓存并刷新详情数据
    #                 try:
    #                     # 获取当前拣货单号
    #                     sel = self.tree.selection()
    #                     if sel:
    #                         picking_order_no = sel[0]

    #                     else:
    #                         picking_order_no = self.tree.focus()
    #                     if picking_order_no:
    #                         # 失效旧缓存
    #                         if hasattr(self, "picking_detail_cache"):
    #                             self.picking_detail_cache.pop(picking_order_no, None)
    #                         # 拉取最新详情
    #                         detail_url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/getPrintPickingList?picking_order_no={picking_order_no}"
    #                         resp_detail = self.controller.session.get(detail_url, headers=HEADERS)
    #                         if resp_detail.status_code == 200:
    #                             new_detail = resp_detail.json().get("data", [])
    #                             # 写回缓存
    #                             if hasattr(self, "picking_detail_cache"):
    #                                 self.picking_detail_cache[picking_order_no] = new_detail
    #                             # 获取当前行的拣货状态用于展示
    #                             picking_status = ""
    #                             try:
    #                                 picking_status = self.tree.item(picking_order_no, "values")[1]
    #                             except Exception:
    #                                 picking_status = ""
    #                             # 刷新详情视图
    #                             self.display_detail_data(new_detail, picking_status)
    #                 except Exception:
    #                     pass
    #             else:
    #                 # 业务逻辑失败
    #                 messagebox.showerror("失败", f"暂存失败：{resp_data.get('resultCode', '无响应')}")
    #         else:
    #             # HTTP请求失败
    #             messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
    #     except Exception:
    #         pass

    # def picking_complete(self):
    #     """暂存：提交拣货数据到指定接口，包含 dataList 和 picking_by"""
    #     # 检查当前选中的订单是否处于"拣货中"状态
    #     selected_items = self.tree.selection()
    #     for item in selected_items:
    #         values = self.tree.item(item, 'values')
    #         # 拣货状态在第3列(索引为2)
    #         if len(values) <= 2 or values[2] != "拣货中":
    #             messagebox.showwarning("警告", "只有状态为'拣货中'的订单才能进行拣货完成操作")
    #             return
    #     # 添加确认弹窗
    #     if not messagebox.askyesno("确认拣货完成", "确定要执行拣货完成操作吗？此操作不可逆。"):
    #         return
    #     # 获取拣货人（多选）
    #     picking_by = ""
    #     if hasattr(self, "picking_listbox") and self.picking_listbox:
    #         try:
    #             indices = self.picking_listbox.curselection()
    #             picking_by = ",".join([self.picking_listbox.get(i) for i in indices])
    #         except Exception:
    #             picking_by = ""

    #     # 获取拣货单详情数据 detail_data
    #     # 优先从当前选中拣货单的缓存中取；按项目已有命名尝试 self.picking_detail_cache 
    #     detail_data = None
    #     try:
    #         # 从主表 Tree 选中项获取拣货单号；若无选中则使用焦点项
    #         picking_order_no = None
    #         try:
    #             sel = self.tree.selection()
    #             if sel:
    #                 picking_order_no = sel[0]
    #             else:
    #                 picking_order_no = self.tree.focus()
    #         except Exception:
    #             picking_order_no = None
    #         if picking_order_no and hasattr(self, "picking_detail_cache"):
    #             detail_data = self.picking_detail_cache.get(picking_order_no)
    #         if detail_data is None:
    #             try:
    #                 # 这里尝试用当前界面的选中单据键获取，若无则取任意已加载的详情
    #                 selected_keys = list(self.picking_detail_cache.keys())
    #                 if selected_keys:
    #                     detail_data = self.picking_detail_cache.get(selected_keys[0])
    #             except Exception:
    #                 detail_data = None
    #     except Exception:
    #         pass
    #     print(detail_data)

    #     if detail_data is None:
    #         # 如果未获取到详情，提示并中止
    #         try:
    #             messagebox.showwarning("提示", "未找到拣货单详情数据，无法拣货完成。")
    #         except Exception:
    #             pass
    #         return

    #     payload = {
    #         "dataList": detail_data,
    #         "picking_by": picking_by or "",
    #         "picking_status":47111003
    #     }

    #     url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"

    #     # 调用项目统一 POST 方法（占位名：self.request_post），请替换为你实际封装方法
    #     try:
    #         resp = self.controller.session.post(url, json=payload,headers=HEADERS)
    #     except Exception:
    #         resp = None

    #     # 检查登录状态
    #     if not self._check_response(resp):
    #         return

    #     # 简单反馈
    #     try:
    #         if resp and resp.status_code == 200:
    #             # HTTP请求成功，检查业务状态码
    #             resp_data = resp.json()
    #             if resp_data.get("resultCode") == 200:
    #                 messagebox.showinfo("成功", "拣货完成")

    #                 # 清空详情Treeview
    #                 try:
    #                     if hasattr(self, "picking_detail_tree") and self.picking_detail_tree:
    #                         self.picking_detail_tree.delete(*self.picking_detail_tree.get_children())
    #                 except Exception as e:
    #                     print(f"清空详情Treeview失败: {e}")
                    
    #                 # 清空编辑控件
    #                 try:
    #                     if hasattr(self, "location_combos"):
    #                         for combo in self.location_combos:
    #                             combo.destroy()
    #                         self.location_combos = []
    #                     if hasattr(self, "quantity_spins"):
    #                         for spin in self.quantity_spins:
    #                             spin.destroy()
    #                         self.quantity_spins = []
    #                 except Exception as e:
    #                     print(f"清空编辑控件失败: {e}")

    #                 # 成功后使对应拣货单的详情缓存失效，避免读取过期数据
    #                 try:
    #                     # 从主表 Tree 选中项或焦点项获取拣货单号
    #                     picking_order_no = None
    #                     try:
    #                         sel = self.tree.selection() if hasattr(self, "tree") else []
    #                         if sel:
    #                             picking_order_no = sel[0]
    #                         else:
    #                             picking_order_no = self.tree.focus() if hasattr(self, "tree") else None
    #                     except Exception:
    #                         picking_order_no = None
    #                     if hasattr(self, "picking_detail_cache") and picking_order_no:
    #                         self.picking_detail_cache.pop(picking_order_no, None)
    #                 except Exception:
    #                     pass

    #                 # 拣货完成后重新查询数据，刷新界面显示
    #                 try:
    #                     self.picking_query()
    #                 except Exception as e:
    #                     print(f"重新查询数据失败: {e}")
    #                     # 即使查询失败也不影响主要功能

    #             else:
    #                 # 业务逻辑失败
    #                 messagebox.showerror("失败", f"拣货失败：{resp_data.get('resultCode', '无响应')}")
    #         else:
    #             # HTTP请求失败
    #             messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
    #     except Exception:
    #         pass

    def picking_save_popup(self, detail_data, picking_listbox, popup_window, detail_tree):
        # """弹窗中的暂存操作"""
        # # 获取选中的拣货人
        # picking_by = ""
        # try:
        #     indices = picking_listbox.curselection()
        #     picking_by = ",".join([picking_listbox.get(i) for i in indices])
        # except Exception:
        #     picking_by = ""
        
        # # 更新detail_data中的数据
        # updated_detail_data = self._update_detail_data_from_treeview(detail_data, detail_tree)
        # print(json.dumps(updated_detail_data,ensure_ascii=False,indent = 4,sort_keys=True))
        # # 构造提交数据
        # payload = {
        #     "dataList": updated_detail_data,
        #     "picking_by": picking_by or "",
        #     "isSave": 1
        # }
        
        # url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"
        
        # try:
        #     print(json.dumps(payload,ensure_ascii=False,indent = 4,sort_keys=True))
        #     resp = self.controller.session.post(url, json=payload, headers=HEADERS)
            
        #     # 检查登录状态
        #     if not self._check_response(resp):
        #         return

        #     if resp and resp.status_code == 200:
        #         resp_data = resp.json()
        #         if resp_data.get("resultCode") == 200:
        #             messagebox.showinfo("成功", "暂存成功")
        #             popup_window.destroy()
        #             # 刷新主界面数据
        #             self.picking_query()
        #         else:
        #             messagebox.showerror("失败", f"暂存失败：{resp_data.get('message', '未知错误')}")
        #     else:
        #         messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
        # except Exception as e:
        #     messagebox.showerror("错误", f"发生异常：{str(e)}")
# ... existing code ...
        """弹窗中的暂存操作"""
        # 添加确认弹窗
        if not messagebox.askyesno("确认暂存", "确定要执行暂存操作吗？"):
            return
            
        # 获取选中的拣货人
        picking_by = ""
        try:
            indices = picking_listbox.curselection()
            picking_by = ",".join([picking_listbox.get(i) for i in indices])
        except Exception:
            picking_by = ""
        
        # 更新detail_data中的数据
        updated_detail_data = self._update_detail_data_from_treeview(detail_data, detail_tree)
        
        # 构造提交数据
        payload = {
            "dataList": updated_detail_data,
            "picking_by": picking_by or "",
            "isSave": 1
        }
        
        url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"
        
        try:
            resp = self.controller.session.post(url, json=payload, headers=HEADERS)
            
            # 检查登录状态
            if not self._check_response(resp):
                popup_window.destroy()  # 确保在登录状态异常时关闭弹窗
                return

            if resp and resp.status_code == 200:
                resp_data = resp.json()
                if resp_data.get("resultCode") == 200:
                    messagebox.showinfo("成功", "暂存成功")
                    # 失效旧缓存，保持数据一致性
                    try:
                        if hasattr(self, "tree") and self.tree.selection():
                            picking_order_no = self.tree.selection()[0]
                            if hasattr(self, "picking_detail_cache"):
                                self.picking_detail_cache.pop(picking_order_no, None)
                    except Exception:
                        pass
                    popup_window.destroy()
                    # 刷新主界面数据
                    self.picking_query()
                else:
                    messagebox.showerror("失败", f"暂存失败：{resp_data.get('message', '未知错误')}")
                    popup_window.destroy()  # 失败时也关闭弹窗
            else:
                messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
                popup_window.destroy()  # 失败时也关闭弹窗
        except Exception as e:
            messagebox.showerror("错误", f"发生异常：{str(e)}")
            popup_window.destroy()  # 异常时也关闭弹窗
# ... existing code ...            
    def picking_complete_popup(self, detail_data, picking_listbox, popup_window, detail_tree):
        # """弹窗中的拣货完成操作"""
        # # 添加确认弹窗
        # if not messagebox.askyesno("确认拣货完成", "确定要执行拣货完成操作吗？此操作不可逆。"):
        #     return
            
        # # 获取选中的拣货人
        # picking_by = ""
        # try:
        #     indices = picking_listbox.curselection()
        #     picking_by = ",".join([picking_listbox.get(i) for i in indices])
        # except Exception:
        #     picking_by = ""
        
        # # 更新detail_data中的数据
        # updated_detail_data = self._update_detail_data_from_treeview(detail_data, detail_tree)
        
        # # 构造提交数据
        # payload = {
        #     "dataList": updated_detail_data,
        #     "picking_by": picking_by or "",
        #     "picking_status": 47111003  # 拣货完成状态
        # }
        # print(json.dumps(payload,ensure_ascii=False,indent = 4,sort_keys=True))        
        # url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"
        
        # try:
        #     resp = self.controller.session.post(url, json=payload, headers=HEADERS)
            
        #     # 检查登录状态
        #     if not self._check_response(resp):
        #         return

        #     if resp and resp.status_code == 200:
        #         resp_data = resp.json()
        #         if resp_data.get("resultCode") == 200:
        #             messagebox.showinfo("成功", "拣货完成")
        #             popup_window.destroy()
        #             # 刷新主界面数据
        #             self.picking_query()
        #         else:
        #             messagebox.showerror("失败", f"拣货完成失败：{resp_data.get('message', '未知错误')}")
        #     else:
        #         messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
        # except Exception as e:
        #     messagebox.showerror("错误", f"发生异常：{str(e)}")
# ... existing code ...
        """弹窗中的拣货完成操作"""
        # 添加确认弹窗
        if not messagebox.askyesno("确认拣货完成", "确定要执行拣货完成操作吗？此操作不可逆。"):
            return
            
        # 获取选中的拣货人
        picking_by = ""
        try:
            indices = picking_listbox.curselection()
            picking_by = ",".join([picking_listbox.get(i) for i in indices])
        except Exception:
            picking_by = ""
        
        # 更新detail_data中的数据
        updated_detail_data = self._update_detail_data_from_treeview(detail_data, detail_tree)
        
        # 构造提交数据
        payload = {
            "dataList": updated_detail_data,
            "picking_by": picking_by or "",
            "picking_status": 47111003  # 拣货完成状态
        }
        
        url = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"
        
        try:
            resp = self.controller.session.post(url, json=payload, headers=HEADERS)
            
            # 检查登录状态
            if not self._check_response(resp):
                popup_window.destroy()  # 确保在登录状态异常时关闭弹窗
                return

            if resp and resp.status_code == 200:
                resp_data = resp.json()
                if resp_data.get("resultCode") == 200:
                    messagebox.showinfo("成功", "拣货完成")
                    # 失效旧缓存，保持数据一致性
                    try:
                        if hasattr(self, "tree") and self.tree.selection():
                            picking_order_no = self.tree.selection()[0]
                            if hasattr(self, "picking_detail_cache"):
                                self.picking_detail_cache.pop(picking_order_no, None)
                    except Exception:
                        pass
                    popup_window.destroy()
                    # 刷新主界面数据
                    self.picking_query()
                else:
                    messagebox.showerror("失败", f"拣货完成失败：{resp_data.get('message', '未知错误')}")
                    popup_window.destroy()  # 失败时也关闭弹窗
            else:
                messagebox.showerror("失败", f"请求失败：{getattr(resp, 'status_code', '无响应')}")
                popup_window.destroy()  # 失败时也关闭弹窗
        except Exception as e:
            messagebox.showerror("错误", f"发生异常：{str(e)}")
            popup_window.destroy()  # 异常时也关闭弹窗
# ... existing code ...
    def _update_detail_data_from_treeview(self, detail_data, detail_tree):
        """从Treeview中更新detail_data"""
        updated_data = []
        children = detail_tree.get_children()
        
        # 遍历所有数据行（排除汇总行）
        data_children = [child for child in children if detail_tree.item(child, "values")[0] != "合计"]
        
        for i, child in enumerate(data_children):
            if i < len(detail_data):
                # 复制原始数据
                item_data = detail_data[i].copy()
                values = detail_tree.item(child, "values")
                
                # 更新相关字段
                if len(values) > 7:
                    item_data["location_no"] = values[7]  # 实际拣货库位
                if len(values) > 8:
                    item_data["pick_num"] = values[8]  # 实际拣货数量
                if len(values) > 9:
                    item_data["before_closed_reason"] = values[9]  # 拣货差异原因
                    
                updated_data.append(item_data)
        
        return updated_data

    def load_and_display_picking_detail(self, picking_order_no, picking_status):
        """统一的详情加载与展示逻辑，带缓存 + 并发保护"""
        if not picking_order_no:
            return
        # 懒初始化并发保护集合
        if not hasattr(self, "_loading_set"):
            self._loading_set = set()
        try:
            # 1) 缓存命中
            if picking_order_no in self.picking_detail_cache:
                picking_detail_data = self.picking_detail_cache[picking_order_no]
                if picking_detail_data is not None:
                    self.display_detail_data(self.parent,picking_detail_data, picking_status)
                return

            # 2) 并发保护：正在加载则直接返回
            if picking_order_no in self._loading_set:
                return
            self._loading_set.add(picking_order_no)

            # 3) 未命中，请求详情
            detail_url = (
                f"https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/"
                f"getPrintPickingList?picking_order_no={picking_order_no}"
            )
            response = self.controller.session.get(detail_url, headers=HEADERS)
            print(response.json())
            # 检查登录状态
            if not self._check_response(response):
                return

            if response.status_code == 200:
                picking_detail_data = response.json().get('data')
                if picking_detail_data is not None:
                    self.picking_detail_cache[picking_order_no] = picking_detail_data
                    self.display_detail_data(self.parent,picking_detail_data, picking_status)
        except Exception:
            # 详情加载失败时静默忽略，不影响勾选/选择操作
            pass
        finally:
            # 清理并发保护状态
            try:
                self._loading_set.discard(picking_order_no)
            except Exception:
                pass

    def on_treeview_click(self, event):
        """仅处理第一列复选框切换（不弹出详情页）"""
        # 获取点击位置
        rowid = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not rowid:
            return

        # 仅当第一列（选择列）才处理复选框
        if column != '#2':
            return

        # 获取当前行的值
        current_values = self.tree.item(rowid, 'values')
        if not current_values:
            return

        # 切换复选框状态
        new_value = '✓' if current_values[1] == '☐' else '☐'
        new_values = list(current_values)
        new_values[1] = new_value
        self.tree.item(rowid, values=new_values)

        # 更新复选框状态字典
        self.checkbox_states[rowid] = (new_value == '✓')

        # 更新选中项集合
        if new_value == '✓':
            self.selected_items.add(rowid)
        else:
            self.selected_items.discard(rowid)

    def on_left_click(self, event):
        """左键点击：非第一列时加载详情；第一列交由 on_treeview_click 处理"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        column = self.tree.identify_column(event.x)

        # 第一列交给复选框处理，避免重复触发
        if column == '#2':
            return self.on_treeview_click(event)

        # 非第一列：加载并展示详情（统一方法）
        values = self.tree.item(item, "values")
        picking_status = values[2] if values and len(values) > 2 else None
        self.load_and_display_picking_detail(item, picking_status)

    # def display_detail_data(self, detail_data,picking_status):
    #     """显示详情数据"""
    #     # 清空详情Treeview
    #     self.picking_detail_tree.delete(*self.picking_detail_tree.get_children())

    #     # 清空编辑控件
    #     for combo in self.location_combos:
    #         combo.destroy()
    #     for spin in self.quantity_spins:
    #         spin.destroy()
    #     for combo in self.reason_combos:
    #         combo.destroy()
        
    #     self.location_combos = []
    #     self.quantity_spins = []
    #     self.reason_combos = []
    #     self.quantity_vars = []
    #     self.detail_item_ids = []

    #     # 设置交替行标签
    #     self.picking_detail_tree.tag_configure('oddrow', background='#E5E5E5')
    #     self.picking_detail_tree.tag_configure('evenrow', background='#FFFFFF')        

    #     # 填充商品数据
    #     for i, item_data in enumerate(detail_data, 1):
    #         tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
    #         # 获取当前行的库位选项
    #         current_location = item_data.get("location_no", "")
    #         order_quantity = item_data.get("order_num",0)
    #         current_quantity = item_data.get("pick_num", "")
    #         current_reason = item_data.get("before_closed_reason") if item_data.get("before_closed_reason") else ''

    #         # 判断拣货状态是否允许交互
    #         # 原始逻辑：
    #         is_editable:bool = (picking_status == "拣货中")
    #         # 同步到交互标志，供守卫使用，确保首次详情显示即可识别为可交互
    #         self.action_controls_enabled = is_editable
    #         try:
    #             self._set_widget_enabled(self.Picking_isSave, is_editable)
    #             self._set_widget_enabled(self.Picking_complete, is_editable)
    #         except Exception:
    #             if hasattr(self, "Picking_isSave"):
    #                 self.Picking_isSave.configure(state=("normal" if is_editable else "disabled"))
    #             if hasattr(self, "Picking_complete"):
    #                 self.Picking_complete.configure(state=("normal" if is_editable else "disabled"))

    #         item_id = self.picking_detail_tree.insert("", "end", values=(
    #             i,
    #             item_data.get("brand_name",""),
    #             item_data.get("part_code", ""),
    #             item_data.get("part_name", ""),
    #             item_data.get("location_no1", ""),
    #             item_data.get("order_num",0),
    #             item_data.get("cancel_num", 0),
    #             current_location,
    #             current_quantity,
    #             current_reason,
    #             item_data.get("picking_order_no",""),
    #             item_data.get("outbound_no",""),
    #             item_data.get("order_number",""),
    #             item_data.get("DEALER_CODE",""),
    #             item_data.get("DEALER_NAME", ""),
    #             item_data.get("goods_type", "")
    #         ), iid = item_data.get("id",0),tags=tags)

    #         self.detail_item_ids.append(item_id)

    #         # 创建实际拣货库位下拉框
    #         # 获取库位和数量的连接字符串作为显示选项
    #         display_options = []
    #         location_mapping = {}  # 存储显示文本到实际库位的映射
            
    #         for location_info in item_data.get("loList", []):
    #             # 假设每个库位都有对应的数量信息，这里需要根据实际情况调整
    #             # 如果没有直接的数量信息，可以使用默认值或从其他地方获取
    #             quantity = location_info["quantity"]  # 这里需要根据实际情况获取数量
    #             location = location_info["locationNo"]
    #             display_text = f"{location} ({quantity})"  # 显示文本：库位 (数量)
    #             display_options.append(display_text)
    #             location_mapping[display_text] = location  # 映射：显示文本 -> 实际库位
            
    #         # 创建实际拣货库位下拉框
    #         location_combo = ttk.Combobox(
    #             self.picking_detail_tree,
    #             values=display_options,
    #             state='readonly' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         location_combo.set(current_location)

    #         # 存储映射关系供回调使用
    #         location_combo.location_mapping = location_mapping  # type: ignore
            
    #         location_combo.bind("<<ComboboxSelected>>", 
    #                            lambda e, idx=i-1: self.on_location_change(idx))
    #         self.location_combos.append(location_combo)
            
    #         # 创建实际拣货数量调节钮
    #         var = tk.StringVar(value=str(current_quantity))
    #         var.trace_add('write', lambda *_, idx=i-1, v=var: self.on_quantity_change(idx, v))
            
    #         spin = tk.Spinbox(
    #             self.picking_detail_tree,
    #             from_=0,
    #             to=order_quantity,
    #             width=5,
    #             bg='lightyellow',
    #             textvariable=var,
    #             state='normal' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         spin.delete(0, tk.END)
    #         spin.insert(0, current_quantity)
            
    #         spin.bind("<FocusOut>", lambda e, idx=i-1: self.on_quantity_change(idx))
    #         spin.bind("<Return>", lambda e, idx=i-1: self.on_quantity_change(idx))
            
    #         self.quantity_spins.append(spin)
    #         self.quantity_vars.append(var)
            
    #         # 创建拣货差异原因下拉框
    #         reason_combo = ttk.Combobox(
    #             self.picking_detail_tree,
    #             values=self.reason_options,
    #             state='readonly' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         reason_combo.set(str(current_reason) if current_reason is not None else '')
    #         reason_combo.bind("<<ComboboxSelected>>", 
    #                          lambda e, idx=i-1: self.on_reason_change(idx))
    #         self.reason_combos.append(reason_combo)
    #     print(self.detail_item_ids)
    #     # 初始布局编辑控件
    #     self.position_detail_widgets()

    #     # 显示详情容器
    #     self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
    #     # self._update_action_controls_state()
    #     # 详情显示完成后再根据交互条件更新拣货人列表
    #     self.update_picking_listbox_by_warehouse()
    #     self._auto_set_picking_by_from_detail_data(detail_data)
    # def display_detail_data(self, detail_data,picking_status):
    #     """显示详情数据"""
    #     # 清空详情Treeview
    #     self.picking_detail_tree.delete(*self.picking_detail_tree.get_children())

    #     # 清空编辑控件
    #     for combo in self.location_combos:
    #         combo.destroy()
    #     for spin in self.quantity_spins:
    #         spin.destroy()
    #     for combo in self.reason_combos:
    #         combo.destroy()
        
    #     self.location_combos = []
    #     self.quantity_spins = []
    #     self.reason_combos = []
    #     self.quantity_vars = []
    #     self.detail_item_ids = []

    #     # 设置交替行标签
    #     self.picking_detail_tree.tag_configure('oddrow', background='#E5E5E5')
    #     self.picking_detail_tree.tag_configure('evenrow', background='#FFFFFF')        
    #     # 配置汇总行的样式
    #     self.picking_detail_tree.tag_configure('summary', background='#f0f0f0', font=('Arial', 13, 'bold'))

    #     # 初始化汇总变量
    #     total_order_num = 0
    #     total_cancel_num = 0
    #     total_pick_num = 0

    #     # 填充商品数据
    #     for i, item_data in enumerate(detail_data, 1):
    #         tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
    #         # 获取当前行的库位选项
    #         current_location = item_data.get("location_no", "")
    #         order_quantity = item_data.get("order_num",0)
    #         current_quantity = item_data.get("pick_num", "")
    #         current_reason = item_data.get("before_closed_reason") if item_data.get("before_closed_reason") else ''

    #         # 累加数量用于汇总
    #         order_num = item_data.get("order_num", 0) or 0
    #         cancel_num = item_data.get("cancel_num", 0) or 0
    #         pick_num = int(item_data.get("pick_num", "")) or 0
            
    #         total_order_num += order_num
    #         total_cancel_num += cancel_num
    #         total_pick_num += pick_num

    #         # 判断拣货状态是否允许交互
    #         # 原始逻辑：
    #         is_editable:bool = (picking_status == "拣货中")
    #         # 同步到交互标志，供守卫使用，确保首次详情显示即可识别为可交互
    #         self.action_controls_enabled = is_editable
    #         try:
    #             self._set_widget_enabled(self.Picking_isSave, is_editable)
    #             self._set_widget_enabled(self.Picking_complete, is_editable)
    #         except Exception:
    #             if hasattr(self, "Picking_isSave"):
    #                 self.Picking_isSave.configure(state=("normal" if is_editable else "disabled"))
    #             if hasattr(self, "Picking_complete"):
    #                 self.Picking_complete.configure(state=("normal" if is_editable else "disabled"))

    #         item_id = self.picking_detail_tree.insert("", "end", values=(
    #             i,
    #             item_data.get("brand_name",""),
    #             item_data.get("part_code", ""),
    #             item_data.get("part_name", ""),
    #             item_data.get("location_no1", ""),
    #             order_num,
    #             cancel_num,
    #             current_location,
    #             pick_num,
    #             current_reason,
    #             item_data.get("picking_order_no",""),
    #             item_data.get("outbound_no",""),
    #             item_data.get("order_number",""),
    #             item_data.get("DEALER_CODE",""),
    #             item_data.get("DEALER_NAME", ""),
    #             item_data.get("goods_type", "")
    #         ), iid = item_data.get("id",0),tags=tags)

    #         self.detail_item_ids.append(item_id)

    #         # 创建实际拣货库位下拉框
    #         # 获取库位和数量的连接字符串作为显示选项
    #         display_options = []
    #         location_mapping = {}  # 存储显示文本到实际库位的映射
            
    #         for location_info in item_data.get("loList", []):
    #             # 假设每个库位都有对应的数量信息，这里需要根据实际情况调整
    #             # 如果没有直接的数量信息，可以使用默认值或从其他地方获取
    #             quantity = location_info["quantity"]  # 这里需要根据实际情况获取数量
    #             location = location_info["locationNo"]
    #             display_text = f"{location} ({quantity})"  # 显示文本：库位 (数量)
    #             display_options.append(display_text)
    #             location_mapping[display_text] = location  # 映射：显示文本 -> 实际库位
            
    #         # 创建实际拣货库位下拉框
    #         location_combo = ttk.Combobox(
    #             self.picking_detail_tree,
    #             values=display_options,
    #             state='readonly' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         location_combo.set(current_location)

    #         # 存储映射关系供回调使用
    #         location_combo.location_mapping = location_mapping  # type: ignore
            
    #         location_combo.bind("<<ComboboxSelected>>", 
    #                            lambda e, idx=i-1: self.on_location_change(idx))
    #         self.location_combos.append(location_combo)
            
    #         # 创建实际拣货数量调节钮
    #         var = tk.StringVar(value=str(current_quantity))
    #         var.trace_add('write', lambda *_, idx=i-1, v=var: self.on_quantity_change(idx, v))
            
    #         spin = tk.Spinbox(
    #             self.picking_detail_tree,
    #             from_=0,
    #             to=order_quantity,
    #             width=5,
    #             bg='lightyellow',
    #             textvariable=var,
    #             state='normal' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         spin.delete(0, tk.END)
    #         spin.insert(0, current_quantity)
            
    #         spin.bind("<FocusOut>", lambda e, idx=i-1: self.on_quantity_change(idx))
    #         spin.bind("<Return>", lambda e, idx=i-1: self.on_quantity_change(idx))
            
    #         self.quantity_spins.append(spin)
    #         self.quantity_vars.append(var)
            
    #         # 创建拣货差异原因下拉框
    #         reason_combo = ttk.Combobox(
    #             self.picking_detail_tree,
    #             values=self.reason_options,
    #             state='readonly' if is_editable else 'disabled'  # 动态设置状态
    #         )
    #         reason_combo.set(str(current_reason) if current_reason is not None else '')
    #         reason_combo.bind("<<ComboboxSelected>>", 
    #                          lambda e, idx=i-1: self.on_reason_change(idx))
    #         self.reason_combos.append(reason_combo)
        
    #     # 插入汇总行（不在detail_item_ids中，避免影响控件定位）
    #     self.picking_detail_tree.insert("", "end", values=(
    #         "合计",
    #         "", "", "", "",
    #         total_order_num,
    #         total_cancel_num,
    #         "",
    #         total_pick_num,
    #         "", "", "", "", "", "", ""
    #     ), tags=("summary",))

    #     print(self.detail_item_ids)
    #     # 初始布局编辑控件
    #     self.position_detail_widgets()

    #     # 显示详情容器
    #     self.detail_container.pack(fill=tk.BOTH, expand=False, pady=(5,0))
    #     # self._update_action_controls_state()
    #     # 详情显示完成后再根据交互条件更新拣货人列表
    #     self.update_picking_listbox_by_warehouse()
    #     self._auto_set_picking_by_from_detail_data(detail_data)

# ... existing code ...
    def display_detail_data(self, parent,data,picking_status):
        """显示详情数据（弹窗方式）"""
        # 创建弹窗
        detail_window = tk.Toplevel(parent)
        detail_window.title("拣货单明细")
        detail_window.geometry("1800x900")
        detail_window.transient(parent)  # 设置为临时窗口
        detail_window.grab_set()  # 模态窗口，阻止与其他窗口交互
        
        # 居中显示
        detail_window.update_idletasks()
        x = (detail_window.winfo_screenwidth() // 2) - (1800 // 2)
        y = (detail_window.winfo_screenheight() // 2) - (900 // 2)
        detail_window.geometry(f"1800x900+{x}+{y}")
        
        # 创建详情容器
        detail_container = tk.LabelFrame(detail_window, text="拣货单明细", bd=1, relief=tk.SUNKEN,
                                       font=("微软雅黑", 10, "bold"))
        detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建详情Treeview
        detail_columns = ["序号","品牌", "CARG全码/产品编码", "产品名称",  "指示拣货库位",
                         "计划拣货数", "取消数", "实际拣货库位", "实际拣货数量","拣货差异原因","拣货单号","出库单号","订单号",
                         "客户代码", "客户名称","货物类型"]
        detail_tree = ttk.Treeview(detail_container, columns=detail_columns, show="headings", height=25)
        
        # 配置详情列
        detail_col_widths = [50, 80, 120, 180, 80, 80, 80, 100, 80, 80, 180, 180,180, 80, 120, 60]
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
        
        # 初始化编辑控件相关变量（弹窗内使用）
        location_combos_popup = []  # 存储实际拣货库位的下拉框
        quantity_spins_popup = []   # 存储实际拣货数量的调节钮
        reason_combos_popup = []    # 存储拣货差异原因的下拉框
        quantity_vars_popup = []    # 存储数量变量，防止被回收
        detail_item_ids_popup = []  # 存储详情Treeview的行ID
        
        # 设置交替行标签
        detail_tree.tag_configure('oddrow', background='#E5E5E5')
        detail_tree.tag_configure('evenrow', background='#FFFFFF')        
        # 配置汇总行的样式
        detail_tree.tag_configure('summary', background='#f0f0f0', font=('Arial', 13, 'bold'))

        # 初始化汇总变量
        total_order_num = 0
        total_cancel_num = 0
        total_pick_num = 0

        # 填充商品数据
        for i, item_data in enumerate(data, 1):
            tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
            # 获取当前行的库位选项
            current_location = item_data.get("location_no", "")
            order_quantity = item_data.get("order_num",0)
            current_quantity = item_data.get("pick_num", "")
            current_reason = item_data.get("before_closed_reason") if item_data.get("before_closed_reason") else ''

            # 累加数量用于汇总
            order_num = item_data.get("order_num", 0) or 0
            cancel_num = item_data.get("cancel_num", 0) or 0
            pick_num = int(item_data.get("pick_num", "")) or 0
            
            total_order_num += order_num
            total_cancel_num += cancel_num
            total_pick_num += pick_num

            # 判断拣货状态是否允许交互
            # 原始逻辑：
            is_editable:bool = (picking_status == "拣货中")
            # 同步到交互标志，供守卫使用，确保首次详情显示即可识别为可交互
            # 注意：在弹窗中，我们不需要同步到主界面的按钮状态

            item_id = detail_tree.insert("", "end", values=(
                i,
                item_data.get("brand_name",""),
                item_data.get("part_code", ""),
                item_data.get("part_name", ""),
                item_data.get("location_no1", ""),
                order_num,
                cancel_num,
                current_location,
                pick_num,
                current_reason,
                item_data.get("picking_order_no",""),
                item_data.get("outbound_no",""),
                item_data.get("order_number",""),
                item_data.get("DEALER_CODE",""),
                item_data.get("DEALER_NAME", ""),
                item_data.get("goods_type", "")
            ), iid = item_data.get("id",0),tags=tags)

            detail_item_ids_popup.append(item_id)

            # 创建实际拣货库位下拉框
            # 获取库位和数量的连接字符串作为显示选项
            display_options = []
            location_mapping = {}  # 存储显示文本到实际库位的映射
            
            for location_info in item_data.get("loList", []):
                # 假设每个库位都有对应的数量信息，这里需要根据实际情况调整
                # 如果没有直接的数量信息，可以使用默认值或从其他地方获取
                quantity = location_info["quantity"]  # 这里需要根据实际情况获取数量
                location = location_info["locationNo"]
                display_text = f"{location} ({quantity})"  # 显示文本：库位 (数量)
                display_options.append(display_text)
                location_mapping[display_text] = location  # 映射：显示文本 -> 实际库位
            
            # 创建实际拣货库位下拉框
            location_combo = ttk.Combobox(
                detail_tree,
                values=display_options,
                state='readonly' if is_editable else 'disabled'  # 动态设置状态
            )
            location_combo.set(current_location)

            # 存储映射关系供回调使用
            location_combo.location_mapping = location_mapping  # type: ignore
            
            location_combo.bind("<<ComboboxSelected>>", 
                               lambda e, idx=i-1: self.on_location_change_popup(idx, location_combos_popup, detail_tree, detail_item_ids_popup))
            location_combos_popup.append(location_combo)
            
            # 创建实际拣货数量调节钮
            var = tk.StringVar(value=str(current_quantity))
            var.trace_add('write', lambda *_, idx=i-1, v=var: self.on_quantity_change_popup(idx, v, quantity_spins_popup, detail_tree, detail_item_ids_popup))
            
            spin = tk.Spinbox(
                detail_tree,
                from_=0,
                to=order_quantity,
                width=5,
                bg='lightyellow',
                textvariable=var,
                state='normal' if is_editable else 'disabled'  # 动态设置状态
            )
            spin.delete(0, tk.END)
            spin.insert(0, current_quantity)
            
            spin.bind("<FocusOut>", lambda e, idx=i-1: self.on_quantity_change_popup(idx, None, quantity_spins_popup, detail_tree, detail_item_ids_popup))
            spin.bind("<Return>", lambda e, idx=i-1: self.on_quantity_change_popup(idx, None, quantity_spins_popup, detail_tree, detail_item_ids_popup))
            
            quantity_spins_popup.append(spin)
            quantity_vars_popup.append(var)
            
            # 创建拣货差异原因下拉框
            reason_combo = ttk.Combobox(
                detail_tree,
                values=self.reason_options,
                state='readonly' if is_editable else 'disabled'  # 动态设置状态
            )
            reason_combo.set(str(current_reason) if current_reason is not None else '')
            reason_combo.bind("<<ComboboxSelected>>", 
                             lambda e, idx=i-1: self.on_reason_change_popup(idx, reason_combos_popup, detail_tree, detail_item_ids_popup))
            reason_combos_popup.append(reason_combo)
        
        # 插入汇总行（不在detail_item_ids中，避免影响控件定位）
        detail_tree.insert("", "end", values=(
            "合计",
            "", "", "", "",
            total_order_num,
            total_cancel_num,
            "",
            total_pick_num,
            "", "", "", "", "", "", ""
        ), tags=("summary",))
        
        # 添加定位编辑控件的方法（弹窗内使用）
        def position_detail_widgets_popup(event=None):
            """将编辑控件定位到对应单元格（弹窗内使用）"""
            # 确保所有列表长度一致
            n = len(detail_item_ids_popup)
            for i in range(n):
                # 检查其他列表是否有足够的元素
                if i >= len(location_combos_popup) or i >= len(quantity_spins_popup) or i >= len(reason_combos_popup):
                    continue
                try:
                    # 实际拣货库位列 (第8列，索引为8)
                    bbox_location = detail_tree.bbox(detail_item_ids_popup[i], '#8')
                    if bbox_location:
                        x, y, width, height = bbox_location
                        location_combos_popup[i].place(x=x, y=y, width=width, height=height)
                    else:
                        location_combos_popup[i].place_forget()
                    
                    # 实际拣货数量列 (第9列，索引为9)
                    bbox_quantity = detail_tree.bbox(detail_item_ids_popup[i], '#9')
                    if bbox_quantity:
                        x, y, width, height = bbox_quantity
                        quantity_spins_popup[i].place(x=x, y=y, width=width, height=height)
                    else:
                        quantity_spins_popup[i].place_forget()
                    
                    # 拣货差异原因列 (第10列，索引为10)
                    bbox_reason = detail_tree.bbox(detail_item_ids_popup[i], '#10')
                    if bbox_reason:
                        x, y, width, height = bbox_reason
                        reason_combos_popup[i].place(x=x, y=y, width=width, height=height)
                    else:
                        reason_combos_popup[i].place_forget()
                except tk.TclError:
                    # item 被删除或不可见
                    pass

        # 绑定事件确保编辑控件跟随滚动和变化（弹窗内使用）
        detail_tree.bind('<Motion>', position_detail_widgets_popup)
        detail_tree.bind('<ButtonPress-1>', position_detail_widgets_popup)
        detail_tree.bind('<MouseWheel>', position_detail_widgets_popup)
        detail_tree.bind('<Leave>', position_detail_widgets_popup)
        detail_tree.bind('<Map>', position_detail_widgets_popup)

        # 初始布局编辑控件
        detail_tree.bind('<Configure>', position_detail_widgets_popup)
        # 添加窗口大小变化的绑定
        detail_window.bind('<Configure>', position_detail_widgets_popup)

        detail_window.after(100, position_detail_widgets_popup)  # 稍后执行以确保Treeview已正确布局
        
        # 创建操作按钮框架
        action_frame = tk.Frame(detail_window)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建拣货人选择列表框
        picking_frame = tk.Frame(action_frame)
        picking_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(picking_frame, text="拣货人:").pack(anchor=tk.W)
        
        # 创建列表框和滚动条
        listbox_frame = tk.Frame(picking_frame)
        listbox_frame.pack()
        
        self.picking_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED, height=4)
        self.listbox_scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.picking_listbox.yview)
        self.picking_listbox.config(yscrollcommand=self.listbox_scrollbar.set)
        
        self.picking_listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        self.listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # 调用update_picking_listbox_by_warehouse方法更新拣货人列表
        self.update_picking_listbox_by_warehouse() 
            # 自动选择与详情数据中相同的拣货人
        self._auto_set_picking_by_from_detail_data_in_popup(data, self.picking_listbox)
        
        # 创建按钮框架
        button_frame = tk.Frame(action_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # 创建暂存和拣货完成按钮
        save_btn = tk.Button(button_frame, text="暂存", command=lambda: self.picking_save_popup(
            data, self.picking_listbox, detail_window, detail_tree, location_combos_popup, 
            quantity_spins_popup, reason_combos_popup),
                             bg="#4CAF50", fg="white", padx=10, pady=5, bd=0)
        # 根据拣货状态设置按钮状态
        if picking_status != "拣货中":
            save_btn.configure(state="disabled")
        save_btn.pack(side=tk.LEFT, padx=5)
        
        complete_btn = tk.Button(button_frame, text="拣货完成", command=lambda: self.picking_complete_popup(
            data, self.picking_listbox, detail_window, detail_tree, location_combos_popup, 
            quantity_spins_popup, reason_combos_popup),
                                 bg="#2196F3", fg="white", padx=10, pady=5, bd=0)
        # 根据拣货状态设置按钮状态
        if picking_status != "拣货中":
            complete_btn.configure(state="disabled")
        complete_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = tk.Button(button_frame, text="关闭", command=detail_window.destroy,
                             bg="#f44336", fg="white", padx=10, pady=5, bd=0)
        close_btn.pack(side=tk.LEFT, padx=5)
        
        # 为详情Treeview添加tooltip功能
        tooltip_manager.attach_tooltip(detail_tree)
        
        # 窗口关闭事件处理
        detail_window.protocol("WM_DELETE_WINDOW", detail_window.destroy)
# ... existing code ...

    # def _auto_set_picking_by_from_detail_data(self, detail_data):
    #     """根据详情数据中的picking_by字段自动设置拣货人选项"""
    #     if not detail_data or not hasattr(self, "picking_listbox"):
    #         return
        
    #     # 从详情数据中提取picking_by字段（取第一个有效值）
    #     picking_by_value = ""
    #     for item_data in detail_data:
    #         picking_by = item_data.get("picking_by", "")
    #         if picking_by:
    #             picking_by_value = picking_by
    #             break
        
    #     # 清空当前选中状态
    #     self.picking_listbox.selection_clear(0, tk.END)
        
    #     if not picking_by_value:
    #         # 如果picking_by为空，保持清空状态
    #         return
        
    #     # 分割拣货人字符串（支持多个拣货人用逗号分隔）
    #     picking_names = [name.strip() for name in picking_by_value.split(",") if name.strip()]
        
    #     # 获取列表框中的所有选项
    #     all_items = self.picking_listbox.get(0, tk.END)
        
    #     # 自动匹配并选中对应的拣货人
    #     for name in picking_names:
    #         if name in all_items:
    #             index = all_items.index(name)
    #             self.picking_listbox.selection_set(index)

    # def position_detail_widgets(self, event=None):
    #     """将编辑控件定位到对应单元格"""
    #     # 确保所有列表长度一致
    #     n = len(self.detail_item_ids)
    #     for i in range(n):
    #         # 检查其他列表是否有足够的元素
    #         if i >= len(self.location_combos) or i >= len(self.quantity_spins) or i >= len(self.reason_combos):
    #             continue
    #         try:
    #             # 实际拣货库位列 (第8列，索引为8)
    #             bbox_location = self.picking_detail_tree.bbox(self.detail_item_ids[i], '#8')
    #             if bbox_location:
    #                 x, y, width, height = bbox_location
    #                 self.location_combos[i].place(
    #                     x=x, y=y, width=width, height=height
    #                 )
    #             else:
    #                 self.location_combos[i].place_forget()
                
    #             # 实际拣货数量列 (第9列，索引为9)
    #             bbox_quantity = self.picking_detail_tree.bbox(self.detail_item_ids[i], '#9')
    #             if bbox_quantity:
    #                 x, y, width, height = bbox_quantity
    #                 self.quantity_spins[i].place(
    #                     x=x, y=y, width=width, height=height
    #                 )
    #             else:
    #                 self.quantity_spins[i].place_forget()
                
    #             # 拣货差异原因列 (第10列，索引为10)
    #             bbox_reason = self.picking_detail_tree.bbox(self.detail_item_ids[i], '#10')
    #             if bbox_reason:
    #                 x, y, width, height = bbox_reason
    #                 self.reason_combos[i].place(
    #                     x=x, y=y, width=width, height=height
    #                 )
    #             else:
    #                 self.reason_combos[i].place_forget()
                    
    #         except tk.TclError:
    #             # item 被删除或不可见
    #             pass

    def _auto_set_picking_by_from_detail_data_in_popup(self, detail_data, popup_listbox):
        """在弹窗中根据详情数据自动设置拣货人选项"""
        if not detail_data:
            return
        
        # 从详情数据中提取picking_by字段（取第一个有效值）
        picking_by_value = ""
        for item_data in detail_data:
            picking_by = item_data.get("picking_by", "")
            if picking_by:
                picking_by_value = picking_by
                break
        
        if not picking_by_value:
            return
        
        # 分割拣货人字符串（支持多个拣货人用逗号分隔）
        picking_names = [name.strip() for name in picking_by_value.split(",") if name.strip()]
        
        # 获取列表框中的所有选项
        all_items = popup_listbox.get(0, tk.END)
        
        # 自动匹配并选中对应的拣货人
        for name in picking_names:
            if name in all_items:
                index = all_items.index(name)
                popup_listbox.selection_set(index)

    def clear_editing_controls(self):
        """清空编辑控件"""
        # 清空编辑控件
        for combo in self.location_combos:
            combo.destroy()
        for spin in self.quantity_spins:
            spin.destroy()
        for combo in self.reason_combos:
            combo.destroy()
        
        self.location_combos = []
        self.quantity_spins = []
        self.reason_combos = []
        self.quantity_vars = []
        self.detail_item_ids = []

#     def on_location_change(self, row_idx):
#         """实际拣货库位修改时更新Treeview"""
#         # 获取选中的显示文本
#         display_text = ""
#         try:
#             display_text = self.location_combos[row_idx].get()
#         except Exception:
#             pass

#         # 获取对应的实际库位值（若无映射则回退为显示文本本身）
#         actual_location = ""
#         try:
#             mapping = getattr(self.location_combos[row_idx], "location_mapping", {}) or {}
#             actual_location = mapping.get(display_text, display_text)
#         except Exception:
#             actual_location = display_text

#         # 行存在性检查
#         if row_idx >= len(self.detail_item_ids):
#             return

#         # 更新Treeview中第7列（实际拣货库位）
#         item_id = self.detail_item_ids[row_idx]
#         try:
#             current_values = list(self.picking_detail_tree.item(item_id, 'values'))
#         except tk.TclError:
#             current_values = []
#         if len(current_values) > 7:
#             current_values[7] = actual_location
#             try:
#                 self.picking_detail_tree.item(item_id, values=current_values)
#             except tk.TclError:
#                 pass

#         # 更新缓存中的数据
#         picking_order_no = current_values[10] if len(current_values) > 10 else ""
#         if picking_order_no and picking_order_no in self.picking_detail_cache:
#             if row_idx < len(self.picking_detail_cache[picking_order_no]):
#                 self.picking_detail_cache[picking_order_no][row_idx]["location_no"] = actual_location

#         # 同步下拉显示
#         try:
#             self.location_combos[row_idx].set(actual_location)
#         except Exception:
#             pass

#     def on_quantity_change(self, row_idx, var=None):
#         """实际拣货数量修改时验证并更新"""
#         try:
#             # 读取输入
#             if var is not None:
#                 raw_value = var.get()
#             else:
#                 raw_value = self.quantity_spins[row_idx].get()

#             # 非数字直接忽略（允许空/中间态）
#             if raw_value is None or not str(raw_value).isdigit():
#                 return

#             # 归一化到非负整数
#             new_val = max(0, int(raw_value))
#             if var is not None:
#                 try:
#                     var.set(str(new_val))
#                 except Exception:
#                     pass

#             current_values = []

#             # 更新Treeview
#             if 0 <= row_idx < len(self.detail_item_ids):
#                 item_id = self.detail_item_ids[row_idx]
#                 try:
#                     current_values = list(self.picking_detail_tree.item(item_id, 'values'))
#                 except tk.TclError:
#                     current_values = []

#                 if len(current_values) > 8:
#                     current_values[8] = str(new_val)  # 第8列是实际拣货数量
#                     try:
#                         self.picking_detail_tree.item(item_id, values=current_values)
#                     except tk.TclError:
#                         pass

#                 # 更新缓存，仅当能取到拣货单号时
#                 picking_order_no = current_values[10] if len(current_values) > 10 else ""
#                 if picking_order_no and picking_order_no in self.picking_detail_cache:
#                     if row_idx < len(self.picking_detail_cache[picking_order_no]):
#                         self.picking_detail_cache[picking_order_no][row_idx]["pick_num"] = str(new_val)
#                 self.update_summary_row()
#         except Exception:
#             # 异常时尽量回退到当前Treeview值
#             try:
#                 if 0 <= row_idx < len(self.detail_item_ids):
#                     item_id = self.detail_item_ids[row_idx]
#                     current_values = self.picking_detail_tree.item(item_id, 'values')
#                     if len(current_values) > 8:
#                         self.quantity_spins[row_idx].delete(0, tk.END)
#                         self.quantity_spins[row_idx].insert(0, current_values[8])
#             except Exception:
#                 pass
# # ... existing code ...
#     def update_summary_row(self):
#         """更新汇总行数据"""
#         try:
#             # 获取所有数据行的实际拣货数量
#             total_pick_qty = 0
#             children = self.picking_detail_tree.get_children()
            
#             # 遍历所有子项，跳过汇总行
#             for child in children:
#                 values = self.picking_detail_tree.item(child, 'values')
#                 # 检查是否为数据行（不是汇总行）
#                 if values and len(values) > 0 and str(values[0]) != "合计":
#                     try:
#                         # 第9列是实际拣货数量
#                         if len(values) > 8:
#                             qty = int(values[8]) if values[8] else 0
#                             total_pick_qty += qty
#                     except (ValueError, IndexError):
#                         pass
            
#             # 查找并更新汇总行
#             for child in children:
#                 values = self.picking_detail_tree.item(child, 'values')
#                 if values and len(values) > 0 and str(values[0]) == "合计":
#                     # 更新汇总行的拣货数量
#                     new_values = list(values)
#                     if len(new_values) > 8:
#                         new_values[8] = str(total_pick_qty)
#                         self.picking_detail_tree.item(child, values=new_values)
#                     break
                    
#         except Exception as e:
#             print(f"更新汇总行失败: {e}")
# # ... existing code ...
#     def on_reason_change(self, row_idx):
#         """拣货差异原因修改时更新Treeview"""
#         reason_text = self.reason_combos[row_idx].get()
        
#         item_id = self.detail_item_ids[row_idx]
#         current_values = list(self.picking_detail_tree.item(item_id, 'values'))
#         current_values[9] = reason_text  # 第9列是拣货差异原因（显示文本）
#         self.picking_detail_tree.item(item_id, values=current_values)
        
#         picking_order_no = current_values[10] if len(current_values) > 10 else ""
#         if picking_order_no and picking_order_no in self.picking_detail_cache:
#             if row_idx < len(self.picking_detail_cache[picking_order_no]):
#                 self.picking_detail_cache[picking_order_no][row_idx]["before_closed_reason"] = reason_text
# ... existing code ...
    def on_location_change_popup(self, row_idx, location_combos, detail_tree, detail_item_ids):
        """实际拣货库位修改时更新Treeview（弹窗内使用）"""
        # 获取选中的显示文本
        display_text = ""
        try:
            display_text = location_combos[row_idx].get()
        except Exception:
            pass

        # 获取对应的实际库位值（若无映射则回退为显示文本本身）
        actual_location = ""
        try:
            mapping = getattr(location_combos[row_idx], "location_mapping", {}) or {}
            actual_location = mapping.get(display_text, display_text)
        except Exception:
            actual_location = display_text

        # 行存在性检查
        if row_idx >= len(detail_item_ids):
            return

        # 更新Treeview中第8列（实际拣货库位）
        item_id = detail_item_ids[row_idx]
        try:
            current_values = list(detail_tree.item(item_id, 'values'))
        except tk.TclError:
            current_values = []
        if len(current_values) > 7:
            current_values[7] = actual_location
            try:
                detail_tree.item(item_id, values=current_values)
            except tk.TclError:
                pass

        # 更新缓存中的数据
        picking_order_no = current_values[10] if len(current_values) > 10 else ""
        if picking_order_no and picking_order_no in self.picking_detail_cache:
            if row_idx < len(self.picking_detail_cache[picking_order_no]):
                self.picking_detail_cache[picking_order_no][row_idx]["location_no"] = actual_location

        # 同步下拉显示
        try:
            location_combos[row_idx].set(actual_location)
        except Exception:
            pass

    def on_quantity_change_popup(self, row_idx, var, quantity_spins, detail_tree, detail_item_ids):
        """实际拣货数量修改时验证并更新（弹窗内使用）"""
        try:
            # 读取输入
            if var is not None:
                raw_value = var.get()
            else:
                raw_value = quantity_spins[row_idx].get()

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
            if 0 <= row_idx < len(detail_item_ids):
                item_id = detail_item_ids[row_idx]
                try:
                    current_values = list(detail_tree.item(item_id, 'values'))
                except tk.TclError:
                    current_values = []

                if len(current_values) > 8:
                    current_values[8] = str(new_val)  # 第9列是实际拣货数量
                    try:
                        detail_tree.item(item_id, values=current_values)
                    except tk.TclError:
                        pass

                # 更新缓存，仅当能取到拣货单号时
                picking_order_no = current_values[10] if len(current_values) > 10 else ""
                if picking_order_no and picking_order_no in self.picking_detail_cache:
                    if row_idx < len(self.picking_detail_cache[picking_order_no]):
                        self.picking_detail_cache[picking_order_no][row_idx]["pick_num"] = str(new_val)
                self.update_summary_row_popup(detail_tree)
        except Exception:
            # 异常时尽量回退到当前Treeview值
            try:
                if 0 <= row_idx < len(detail_item_ids):
                    item_id = detail_item_ids[row_idx]
                    current_values = detail_tree.item(item_id, 'values')
                    if len(current_values) > 8:
                        quantity_spins[row_idx].delete(0, tk.END)
                        quantity_spins[row_idx].insert(0, current_values[8])
            except Exception:
                pass

    def update_summary_row_popup(self, detail_tree):
        """更新汇总行数据（弹窗内使用）"""
        try:
            # 获取所有数据行的实际拣货数量
            total_pick_qty = 0
            children = detail_tree.get_children()
            
            # 遍历所有子项，跳过汇总行
            for child in children:
                values = detail_tree.item(child, 'values')
                # 检查是否为数据行（不是汇总行）
                if values and len(values) > 0 and str(values[0]) != "合计":
                    try:
                        # 第9列是实际拣货数量
                        if len(values) > 8:
                            qty = int(values[8]) if values[8] else 0
                            total_pick_qty += qty
                    except (ValueError, IndexError):
                        pass
            
            # 查找并更新汇总行
            for child in children:
                values = detail_tree.item(child, 'values')
                if values and len(values) > 0 and str(values[0]) == "合计":
                    # 更新汇总行的拣货数量
                    new_values = list(values)
                    if len(new_values) > 8:
                        new_values[8] = str(total_pick_qty)
                        detail_tree.item(child, values=new_values)
                    break
                    
        except Exception as e:
            print(f"更新汇总行失败: {e}")

    def on_reason_change_popup(self, row_idx, reason_combos, detail_tree, detail_item_ids):
        """拣货差异原因修改时更新Treeview（弹窗内使用）"""
        reason_text = reason_combos[row_idx].get()
        
        item_id = detail_item_ids[row_idx]
        current_values = list(detail_tree.item(item_id, 'values'))
        current_values[9] = reason_text  # 第10列是拣货差异原因（显示文本）
        detail_tree.item(item_id, values=current_values)
        
        picking_order_no = current_values[10] if len(current_values) > 10 else ""
        if picking_order_no and picking_order_no in self.picking_detail_cache:
            if row_idx < len(self.picking_detail_cache[picking_order_no]):
                self.picking_detail_cache[picking_order_no][row_idx]["before_closed_reason"] = reason_text
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
        self.tree.tag_configure('oddrow', background='#D5D5D5')
        self.tree.tag_configure('evenrow', background='#FFFFFF')   

        
        # 在Treeview中插入数据
        for i,order in enumerate(self.current_page_data,1):
            tags = ('evenrow',) if i % 2 == 0 else ('oddrow',)
            values = (
                f"{start_index + i}",  # 序号                
                '☐',  # 复选框占位
                order.get("picking_status", ""),
                order.get("print_status", ""),
                order.get("picking_order_no", ""),
                order.get("out_num", 0),
                order.get("cancel_num",0),
                order.get("pick_num",0),
                f"{order.get('totalAmount', 0):.2f}",
                order.get("remark", ""),
                order.get("picking_by", ""),
                order.get("outbound_no", ""),
                order.get("DEALER_NAME", ""),
                order.get("DEALER_CODE", ""),
                order.get("receive_address", ""),
                order.get("logistics_mode", ""),
                order.get("logistics_company",""),
                order.get("WAREHOUSE_NAME", ""),
                order.get("created_by", ""),
                order.get("created_at", "")
            )
            self.tree.insert("", "end", values=values, iid=order.get("picking_order_no"),tags=tags)  # 使用拣货单号作为行ID
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

    # def setup_pagination_controls(self, parent):
        
    #     # 分页信息标签
    #     page_label = tk.Label(parent, textvariable=self.page_info_var, bg="#f0f0f0")
    #     page_label.pack(side=tk.LEFT, padx=10)
        
    #     # 分页按钮
    #     btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}
        
    #     tk.Button(parent, text="首页", 
    #              command=lambda: self.go_to_page(1), **btn_style).pack(side=tk.LEFT, padx=2)
        
    #     tk.Button(parent,text="上一页", 
    #              command=self.go_to_prev_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
    #     tk.Button(parent, text="下一页", 
    #              command=self.go_to_next_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
    #     tk.Button(parent, text="尾页", 
    #              command=self.go_to_last_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
    #     # 页码输入框
    #     tk.Label(parent, text="跳转到:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 0))
    #     self.page_entry = tk.Entry(parent, width=5)
    #     self.page_entry.pack(side=tk.LEFT, padx=2)
        
    #     tk.Button(parent, text="跳转", 
    #              command=self.jump_to_page, **btn_style).pack(side=tk.LEFT, padx=2)
        
    #     # 初始化分页信息
    #     self.update_page_info()

# ... existing code ...
    def setup_pagination_controls(self, parent):
        # 分页信息标签
        page_label = tk.Label(parent, textvariable=self.page_info_var, bg="#f0f0f0")
        page_label.pack(side=tk.LEFT, padx=10)
        
        # 每页显示条数下拉框
        page_size_frame = tk.Frame(parent, bg="#f0f0f0")
        page_size_frame.pack(side=tk.LEFT, padx=10)
        
        # tk.Label(page_size_frame, text="每页显示:", bg="#f0f0f0").pack(side=tk.LEFT)
        
        self.page_size_var = tk.StringVar(value=str(self.page_size))
        self.page_size_cb = ttk.Combobox(
            page_size_frame, 
            textvariable=self.page_size_var, 
            values=[str(size) for size in self.page_size_options],
            state="readonly",
            width=5
        )
        self.page_size_cb.pack(side=tk.LEFT, padx=5)
        self.page_size_cb.bind("<<ComboboxSelected>>", self.on_page_size_change)
        
        tk.Label(page_size_frame, text="条/页", bg="#f0f0f0").pack(side=tk.LEFT)
        
        # 分页按钮
        btn_style = {"bg": "#e1e1e1", "relief": tk.FLAT, "width": 8}
        
        tk.Button(parent, text="首页", 
                 command=lambda: self.go_to_page(1), **btn_style).pack(side=tk.LEFT, padx=2)
        
        tk.Button(parent,text="上一页", 
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
        
    def on_page_size_change(self, event=None):
        """当每页显示条数改变时"""
        try:
            new_page_size = int(self.page_size_var.get())
            if new_page_size != self.page_size:
                self.page_size = new_page_size
                # 重置到第一页并刷新显示
                self.current_page = 1
                # 重新计算总页数
                self.total_pages = max(1, (len(self.filtered_data_all) + self.page_size - 1) // self.page_size)
                self.refresh_table()
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
# ... existing code ...

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
        # 按钮样式
        btn_style1 = {"bg": "#673AB7", "fg": "white", "padx": 10, "pady": 5, 
                    "bd": 0, "activebackground": "#45a049"}
        tk.Button(parent, text="批量一键发运", command=self.open_shipping_window, **btn_style1).pack(side=tk.LEFT, padx=10)
        tk.Button(parent, text="打印预览", command=self.open_print_preview, **btn_style1).pack(side=tk.LEFT, padx=10)

    def select_all(self):
        """全选"""
        for order in self.current_page_data:
            order_id = order.get("picking_order_no")
            self.selected_items.add(order_id)
        
        # # 更新Treeview中的复选框显示
        # for item in self.tree.get_children():
        #     self.tree.item(item, values=('✓',) + self.tree.item(item, 'values')[1:])
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[1] = '✓'  # 复选框在第二列
            self.tree.item(item, values=values)
    def deselect_all(self):
        """全不选"""
        self.selected_items.clear()
        
        # 更新Treeview中的复选框显示
        # for item in self.tree.get_children():
        #     self.tree.item(item, values=('☐',) + self.tree.item(item, 'values')[1:])
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[1] = '☐'  # 复选框在第二列
            self.tree.item(item, values=values)

    def toggle_selection(self):
        """反选"""
        all_order_ids = set(order.get("picking_order_no") for order in self.current_page_data)
        new_selected_items = all_order_ids - self.selected_items
        
        # 更新选中项集合
        self.selected_items = new_selected_items
        
        # 更新Treeview中的复选框显示
        # for item in self.tree.get_children():
        #     order_id = item
        #     if order_id in self.selected_items:
        #         self.tree.item(item, values=('✓',) + self.tree.item(item, 'values')[1:])
        #     else:
        #         self.tree.item(item, values=('☐',) + self.tree.item(item, 'values')[1:])
        # 更新Treeview中的复选框显示
        for item in self.tree.get_children():
            order_id = item
            values = list(self.tree.item(item, 'values'))
            if order_id in self.selected_items:
                values[1] = '✓'  # 复选框在第二列
            else:
                values[1] = '☐'  # 复选框在第二列
            self.tree.item(item, values=values)

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

    def _update_action_controls_state(self, event=None):
        """更新操作按钮的交互状态"""
        try:
            # 检查是否有详情数据
            has_detail_data = False
            if hasattr(self, 'picking_detail_tree') and self.picking_detail_tree:
                # 检查详情树是否有数据
                has_detail_data = len(self.picking_detail_tree.get_children()) > 0
            
            # 检查是否有选中的拣货单
            has_selected_picking = False
            if hasattr(self, 'tree') and self.tree:
                selected_items = self.tree.selection()
                has_selected_picking = len(selected_items) > 0
                    # 检查选中的拣货单是否都处于"拣货中"状态
            all_selected_picking = True
            if hasattr(self, 'tree') and self.tree:
                selected_items = self.tree.selection()
                for item in selected_items:
                    values = self.tree.item(item, 'values')
                    # 拣货状态在第3列(索引为2)
                    if len(values) > 2 and values[2] != "拣货中":
                        all_selected_picking = False
                        break

            # 按钮应该在详情数据加载完成且有选中项时才可用
            buttons_enabled = has_detail_data and has_selected_picking  and all_selected_picking
            
            # 更新按钮状态
            if hasattr(self, 'Picking_isSave'):
                self.Picking_isSave.config(state='normal' if buttons_enabled else 'disabled')
            
            if hasattr(self, 'Picking_complete'):
                self.Picking_complete.config(state='normal' if buttons_enabled else 'disabled')
                
        except Exception as e:
            # 出错时默认禁用按钮以确保安全
            if hasattr(self, 'Picking_isSave'):
                self.Picking_isSave.config(state='disabled')
            if hasattr(self, 'Picking_complete'):
                self.Picking_complete.config(state='disabled')

    def open_shipping_window(self):
        """处理选中订单"""
        selected_items = self.tree.selection()

        if not self.selected_items:
            messagebox.showwarning("警告", "请至少选择一条记录")
            return
        # 检查所有选中的订单是否都处于"拣货中"状态
        for item in selected_items:
            values = self.tree.item(item, 'values')
            # 拣货状态在第3列(索引为2)
            if len(values) <= 2 or values[2] != "拣货中":
                messagebox.showwarning("警告", "只有状态为'拣货中'的订单才能进行一键发运操作")
                return        
        # 获取选中项的订单数据
        selected_orders = [order for order in self.filtered_data if order.get("picking_order_no") in self.selected_items]
        # 显示处理信息
        if not messagebox.askyesno("确认", f"将处理{len(selected_orders)}条订单记录，是否一键发运？"):
            return

        processed_picking_orders = set(order.get("picking_order_no") for order in selected_orders)
        # 获取当前选中的仓库
        current_warehouse = self.warehouse_var.get()
        """打开一键发运窗口"""
        shipping_window = ShippingWindow(self, warehouse_data, driver_data, warehouse_vehicle_data,processed_picking_orders, controller=self.controller,default_warehouse=current_warehouse)
        
        # 设置窗口关闭回调，清空编辑控件
        shipping_window.window.protocol("WM_DELETE_WINDOW", self.clear_editing_controls)

    def open_print_preview(self):
        """打开打印预览窗口 - 支持单选/多选拣货单"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先勾选需要打印预览的拣货单")
            return
        
        picking_order_nos = list(self.selected_items)
        PrintPreviewWindow(self, picking_order_nos, controller=self.controller)


class ShippingWindow:
    def __init__(self, parent,warehouse_data, driver_data, warehouse_vehicle_data,processed_picking_orders,controller, default_warehouse=None):
        """
        初始化一键发运窗口
        
        参数:
        parent: 父窗口
        warehouse_data: 仓库数据，格式为 {仓库名: {"人员": [拣货人列表, 装箱人列表, 叉车司机列表, 送货人列表]}}
        driver_data: 送货人员联系方式数据，格式为 {送货人员名: 联系方式}
        warehouse_vehicle_data: 仓库车牌号数据，格式为 {仓库名: [车牌号列表]}
        """
        self.parent = parent
        self.controller = controller if controller else parent.controller  # 从parent获取
        self.warehouse_data = warehouse_data
        self.driver_data = driver_data
        self.warehouse_vehicle_data = warehouse_vehicle_data
        self.processed_picking_orders = processed_picking_orders
        self.default_warehouse = default_warehouse

        
        # 仓库名称与编号的映射
        self.warehouse_code_map = {
            "郑州库": 6,
            "西安库": 7,
            "兰州库":8,
            "驻马店库":9,
            "茶城库":10,
            "商丘库":11,
            "洛阳库":12,
            "雁塔库":13,
            "西宁库":14,
            "榆林库":15,
            "银川库":16,
            "西安西郊库":18,
            # 可以继续添加其他仓库的映射
        }
        
        # 物流方式与代码的映射
        self.logistics_code_map = {
            "送货": 46171001,
            "物流代收": 46171002,
            "物流发货":46171003,
            "自提":46171004,
            "快递":46171005
        }

        # 箱子名称与代码的映射
        self.box_model_map = {
            "木箱":{
                "box_model": "MX",
                "box_type": 90971001,
                "id": 6,
            },
            "自提":{
                "box_model": "ZT",
                "box_type": 90971003,
                "id": 7,
            },
            "纸皮包装":{
                "box_model": "ZPBZ",
                "box_type": 90971004,
                "id": 8,
            },
            "送货":{
                "box_model": "SH",
                "box_type": 90971003,
                "id": 9,
            }
        }
        
        # 创建顶层窗口
        self.window = tk.Toplevel(parent)
        self.root = parent
        self.window.title("一键发运")
        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # 获取窗口宽度和高度
        window_width = 600
        window_height = 600
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        # 设置窗口位置
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.minsize(400, 600)   # 设置最小尺寸
        self.window.transient(parent)  # 设置为父窗口的子窗口
        self.window.grab_set()  # 模态对话框
        
        # 创建变量来存储选择的值
        self.warehouse_var = tk.StringVar()
        self.box_name_var = tk.StringVar()
        self.logistics_mode_var = tk.StringVar()
        self.forklift_driver_var = tk.StringVar()
        self.has_vehicle_var = tk.IntVar()  # 改为IntVar，用于存储10041001或10041002
        self.license_no_var = tk.StringVar()
        self.waybill_personnel_var = tk.StringVar()
        self.contact_information_var = tk.StringVar()
        self.delivery_route_var = tk.StringVar()  # 新增送货线路变量
        
        # 当前仓库对应的送货人列表和车牌号列表
        self.current_delivery_list = []
        self.current_vehicle_list = []  # 添加此行，初始化车牌号列表变量

        
        # 创建界面
        self.setup_ui()

        # 先初始化下拉框选项
        self.update_warehouse_options()
        
        # 再设置按钮样式（确保变量有默认值）
        self.has_vehicle_var.set(10041002)  # 设置默认值
        self.update_button_styles()

        
        # 绑定事件
        self.warehouse_var.trace("w", self.on_warehouse_changed)
   
    def set_has_vehicle_yes(self):
        """设置是否自有车辆为'是'，返回值10041001"""
        self.has_vehicle_var.set(10041001)
        self.update_license_no_input()  # 更新车牌号输入方式
        self.update_waybill_personnel_input()  # 更新送货人输入方式
        self.update_button_styles()  # 更新按钮样式    
    def set_has_vehicle_no(self):
        """设置是否自有车辆为'否'，返回值10041002"""
        self.has_vehicle_var.set(10041002)
        self.update_license_no_input()  # 更新车牌号输入方式
        self.update_waybill_personnel_input()  # 更新送货人输入方式
        self.update_button_styles()  # 更新按钮样式
        
    def setup_ui(self):
        """设置数据收集界面"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 仓库选择 (必填)
        ttk.Label(main_frame, text="出库仓库:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.warehouse_cb = ttk.Combobox(main_frame, textvariable=self.warehouse_var, state="readonly")
        self.warehouse_cb.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 拣货人 (可选项) - 改为多选列表框
        ttk.Label(main_frame, text="拣货人:").grid(row=0, column=2, sticky=tk.W, pady=5)
        self.picking_frame = ttk.Frame(main_frame)
        self.picking_frame.grid(row=0, column=3, sticky=tk.W+tk.E, pady=5)

        # 创建列表框和滚动条
        self.picking_listbox = tk.Listbox(self.picking_frame, selectmode=tk.MULTIPLE, height=3,exportselection=False)
        self.picking_scrollbar = ttk.Scrollbar(self.picking_frame, orient=tk.VERTICAL, command=self.picking_listbox.yview)
        self.picking_listbox.configure(yscrollcommand=self.picking_scrollbar.set)
        
        self.picking_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.picking_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 箱子名称 (必填)
        ttk.Label(main_frame, text="箱子名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.box_name_cb = ttk.Combobox(main_frame, textvariable=self.box_name_var, state="readonly")
        self.box_name_cb['values'] = ["木箱", "自提", "纸皮包装", "送货"]
        self.box_name_cb.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 物流方式 (可选项，必填)
        ttk.Label(main_frame, text="物流方式:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.logistics_mode_cb = ttk.Combobox(main_frame, textvariable=self.logistics_mode_var, state="readonly")
        self.logistics_mode_cb['values'] = ["送货", "物流代收", "物流发货", "自提","快递"]
        self.logistics_mode_cb.grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)

        # 物流公司 (仅当“物流方式”=“物流代收”可选；可为空)
        ttk.Label(main_frame, text="物流公司:").grid(row=2, column=2, sticky=tk.W, pady=5)
        self.logistics_company_var = tk.StringVar()
        self.logistics_company_id_map = {
            "贰仟家汽车新服务有限公司(卡号116546)": 1436
        }
        self.logistics_company_cb = ttk.Combobox(
            main_frame,
            textvariable=self.logistics_company_var,
            state="disabled"
        )
        self.logistics_company_cb['values'] = ["", "贰仟家汽车新服务有限公司(卡号116546)"]
        self.logistics_company_cb.grid(row=2, column=3, sticky=tk.W+tk.E, pady=5)

        # 当物流方式为“物流代收”时启用物流公司选择，否则禁用并清空
        def _toggle_logistics_company_state():
            mode = self.logistics_mode_var.get()
            if mode == "物流代收":
                self.logistics_company_cb.config(state="readonly")
            else:
                self.logistics_company_var.set("")
                self.logistics_company_cb.config(state="disabled")

        self.logistics_mode_cb.bind("<<ComboboxSelected>>", lambda e: _toggle_logistics_company_state())
        _toggle_logistics_company_state()
        
        # 装箱人 (可选项) - 改为多选列表框
        ttk.Label(main_frame, text="装箱人:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.packing_frame = ttk.Frame(main_frame)
        self.packing_frame.grid(row=3, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 创建列表框和滚动条
        self.packing_listbox = tk.Listbox(self.packing_frame, selectmode=tk.MULTIPLE, height=3,exportselection=False)
        self.packing_scrollbar = ttk.Scrollbar(self.packing_frame, orient=tk.VERTICAL, command=self.packing_listbox.yview)
        self.packing_listbox.configure(yscrollcommand=self.packing_scrollbar.set)
        
        self.packing_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.packing_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 叉车司机 (可选项)
        ttk.Label(main_frame, text="叉车司机:").grid(row=3, column=2, sticky=tk.W, pady=5)
        self.forklift_driver_cb = ttk.Combobox(main_frame, textvariable=self.forklift_driver_var, state="readonly")
        self.forklift_driver_cb.grid(row=3, column=3, sticky=tk.W+tk.E, pady=5)
        
        # 是否自有车辆 (必填) - 改为两个按钮
        ttk.Label(main_frame, text="是否自有车辆:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.vehicle_button_frame = tk.Frame(main_frame)
        self.vehicle_button_frame.grid(row=4, column=1, sticky=tk.W, pady=5)
        self.yes_button = tk.Button(self.vehicle_button_frame, text="是", command=self.set_has_vehicle_yes)
        self.yes_button.pack(side=tk.LEFT, padx=5)
        self.no_button = tk.Button(self.vehicle_button_frame, text="否", command=self.set_has_vehicle_no)
        self.no_button.pack(side=tk.LEFT, padx=5)
        
        # 车牌号 (根据是否自有车辆动态切换输入方式)
        ttk.Label(main_frame, text="车牌号:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.license_no_container = tk.Frame(main_frame)
        self.license_no_container.grid(row=5, column=1, sticky=tk.W+tk.E, pady=5)
        self.update_license_no_input()  # 初始化车牌号输入方式
         # 送货线路 (新增)
        ttk.Label(main_frame, text="送货线路:").grid(row=5, column=2, sticky=tk.W, pady=5)
        self.delivery_route_var = tk.StringVar()
        self.delivery_route_cb = ttk.Combobox(main_frame, textvariable=self.delivery_route_var, state="readonly")
        self.delivery_route_cb.grid(row=5, column=3, sticky=tk.W+tk.E, pady=5)       
        # 送货人 (根据是否自有车辆动态切换输入方式)
        ttk.Label(main_frame, text="送货人:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.waybill_personnel_container = tk.Frame(main_frame)
        self.waybill_personnel_container.grid(row=6, column=1, sticky=tk.W+tk.E, pady=5)
        self.update_waybill_personnel_input()  # 初始化送货人输入方式
        
        # 联系方式 (独立输入，不再自动关联到送货人)
        ttk.Label(main_frame, text="联系方式:").grid(row=6, column=2, sticky=tk.W, pady=5)
        self.contact_information_entry = ttk.Entry(main_frame, textvariable=self.contact_information_var)
        self.contact_information_entry.grid(row=6, column=3,sticky=tk.W+tk.E, pady=5)
        
        # 添加统计信息标签
        self.stats_frame = ttk.Frame(main_frame)
        self.stats_frame.grid(row=8, column=0, columnspan=4, sticky=tk.EW, pady=10)
        
        # 初始化统计变量
        self.order_count_var = tk.StringVar(value="订单数量: 0")
        self.total_quantity_var = tk.StringVar(value="货物数量: 0")
        self.total_amount_var = tk.StringVar(value="单据金额: 0.00")
        
        # 创建标签
        self.order_count_label = ttk.Label(self.stats_frame, textvariable=self.order_count_var)
        self.order_count_label.pack(side=tk.LEFT, padx=10)
        
        self.total_quantity_label = ttk.Label(self.stats_frame, textvariable=self.total_quantity_var)
        self.total_quantity_label.pack(side=tk.LEFT, padx=10)
        
        self.total_amount_label = ttk.Label(self.stats_frame, textvariable=self.total_amount_var)
        self.total_amount_label.pack(side=tk.LEFT, padx=10)
        
        # 在按钮创建部分，确保按钮可见
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=4, sticky=tk.EW, pady=20)

        # 使用更明显的按钮样式并居中显示
        # 创建一个内部框架用于居中按钮
        button_container = ttk.Frame(button_frame)
        button_container.pack(expand=True)
        
        confirm_btn = ttk.Button(button_container, text="确认发运", command=self.confirm_shipping)
        confirm_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = ttk.Button(button_container, text="取消", command=self.window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)


        
        # 配置网格权重，使列可以随窗口调整大小
        main_frame.columnconfigure(1, weight=1)
        # # 添加调试：确保窗口正确显示
        # print("ShippingWindow UI setup completed")
        # print(f"Button frame children: {button_frame.winfo_children()}")   
        # 初始化送货线路选项
        self.init_delivery_routes()
        # 初始化统计数据
        self.update_statistics()

    def init_delivery_routes(self):
        """初始化送货线路下拉选项"""
        try:
            # 从指定URL获取送货线路数据
            url = "https://xb.fy-carg.com/dcscloud.basedata/transportRoute/queryList"
            response = self.controller.session.get(url, headers=HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    # 提取routeName字段作为选项
                    route_names = [route.get("routeName", "") for route in data["data"] if route.get("routeName")]
                    self.delivery_route_cb['values'] = ["请选择"] + route_names
                    self.delivery_route_var.set("")  # 默认值为空
        except Exception as e:
            print(f"获取送货线路数据失败: {e}")

    def update_statistics(self):
        """更新统计数据"""
        try:
            # 订单数量
            order_count = len(self.processed_picking_orders) if self.processed_picking_orders else 0
            self.order_count_var.set(f"本次处理订单数量: {order_count}")
            
            # 货物数量和单据金额从主窗口的tree中获取
            total_quantity = 0
            total_amount = 0.0
            
            # 遍历所有处理的拣货单，从主窗口的tree中获取信息
            for picking_order_no in self.processed_picking_orders:
                try:
                    # 从主窗口的tree中获取该拣货单的信息
                    if hasattr(self.parent, 'tree') and picking_order_no in self.parent.tree.get_children():
                        values = self.parent.tree.item(picking_order_no, 'values')
                        if values and len(values) > 8:
                            # 计划拣货数量在第6列(索引5)
                            quantity = values[5] if values[5] not in [None, ''] else 0
                            total_quantity += int(quantity)
                            
                            # 单据总金额在第9列(索引8)
                            amount = values[8] if values[8] not in [None, ''] else 0
                            total_amount += float(amount)
                except Exception as e:
                    print(f"获取拣货单 {picking_order_no} 详情失败: {e}")
            
            self.total_quantity_var.set(f"计划拣货数量: {total_quantity}")
            self.total_amount_var.set(f"单据总金额: {total_amount:.2f}")
        except Exception as e:
            print(f"更新统计数据失败: {e}")


    def update_button_styles(self):
        """更新按钮样式，突出显示选中的按钮"""
        current_value = self.has_vehicle_var.get()
        
        # 重置两个按钮的样式
        self.yes_button.config(bg='SystemButtonFace', fg='black')
        self.no_button.config(bg='SystemButtonFace', fg='black')
        
        # 根据当前值设置选中按钮的样式
        if current_value == 10041001:  # 是
            self.yes_button.config(bg='#4CAF50', fg='white')
        elif current_value == 10041002:  # 否
            self.no_button.config(bg='#4CAF50', fg='white')


    
    def update_warehouse_options(self):
        """更新仓库下拉框选项"""
        warehouse_names = list(self.warehouse_data.keys())
        self.warehouse_cb['values'] = warehouse_names
        # 如果有默认仓库，自动设置
        if self.default_warehouse and self.default_warehouse != "全部":
            self.warehouse_var.set(self.default_warehouse)
        else:
            self.warehouse_var.set(warehouse_names[0])  # 设置默认值为第一个仓库
        # 初始状态更新
        self.on_warehouse_changed()
    
    def on_warehouse_changed(self, *args):
        """当仓库选择变化时更新相关字段选项"""
        warehouse_name = self.warehouse_var.get()

        
        if not warehouse_name:
            # 仓库未选择，清空所有相关选项
            self.picking_listbox.delete(0, tk.END)
            self.packing_listbox.delete(0, tk.END)
            
            self.forklift_driver_cb['values'] = []
            self.forklift_driver_var.set('')
            
            # 清空送货人相关选项
            self.current_delivery_list = []
            self.update_waybill_personnel_input()  # 使用更新方法来设置送货人选项
            
            # 清空已选择的值
            self.box_name_var.set('')
            self.logistics_mode_var.set('')
            self.waybill_personnel_var.set('')
            self.contact_information_var.set('')  # 清空联系方式
            
            # 清空车牌号列表
            self.current_vehicle_list = []  # 添加此行，清空车牌号列表
            self.update_license_no_input()  # 更新车牌号输入方式
            return
        
        # 获取该仓库对应的人员列表
        personnel_lists = self.warehouse_data.get(warehouse_name, [[], [], [], []])
        picking_by_list, packing_by_list, forklift_driver_list, waybill_personnel_list = personnel_lists

        # 更新拣货人列表框
        self.picking_listbox.delete(0, tk.END)
        for name in picking_by_list:
            self.picking_listbox.insert(tk.END, name)
        
        # 更新装箱人列表框
        self.packing_listbox.delete(0, tk.END)
        for name in packing_by_list:
            self.packing_listbox.insert(tk.END, name)

        
        self.forklift_driver_cb['values'] = forklift_driver_list
        self.forklift_driver_var.set('')  # 默认值为空，不再设置"请选择"

        
        # 保存当前仓库的送货人列表
        self.current_delivery_list = waybill_personnel_list
        
        # 获取该仓库对应的车牌号列表
        self.current_vehicle_list = self.warehouse_vehicle_data.get(warehouse_name, [])  # 修复：将值赋给self.current_vehicle_list
        
        
        # 更新车牌号和送货人显示状态
        self.update_license_no_input()
        self.update_waybill_personnel_input()
    
    def update_license_no_input(self):
        """更新车牌号输入方式"""
        # 清除车牌号容器中的所有控件
        for widget in self.license_no_container.winfo_children():
            widget.destroy()
        
        # 根据是否自有车辆选择，设置车牌号输入方式
        if self.has_vehicle_var.get() == 10041001:  # 如果选择"是"（自有车辆）
            # 车牌号使用下拉框
            self.license_no_cb = ttk.Combobox(self.license_no_container, textvariable=self.license_no_var, state="readonly")
            self.license_no_cb['values'] = ["请选择"] + self.current_vehicle_list  # 增加"请选择"选项
            self.license_no_var.set('')  # 默认值设置为空字符串，而不是"请选择"
            self.license_no_cb.pack(fill=tk.X, padx=5)
        else:  # 如果选择"否"（非自有车辆）
            # 车牌号使用输入框
            self.license_no_entry = ttk.Entry(self.license_no_container, textvariable=self.license_no_var)
            self.license_no_var.set('')  # 设置为空字符串
            self.license_no_entry.pack(fill=tk.X, padx=5)
    
    def update_waybill_personnel_input(self):
        """更新送货人输入方式"""
        # 清除送货人容器中的所有控件
        for widget in self.waybill_personnel_container.winfo_children():
            widget.destroy()
        
        # 根据是否自有车辆选择，设置送货人输入方式
        if self.has_vehicle_var.get() == 10041001:  # 如果选择"是"（自有车辆）
            # 送货人使用下拉框(关联到仓库的送货人员)
            if self.current_delivery_list:  # 如果有送货人列表
                self.waybill_personnel_cb = ttk.Combobox(
                    self.waybill_personnel_container, 
                    textvariable=self.waybill_personnel_var, 
                    state="readonly"
                )
                self.waybill_personnel_cb['values'] = ["请选择"] + self.current_delivery_list
                self.waybill_personnel_cb.pack(fill=tk.X, padx=5)
                
                # 绑定选择事件
                self.waybill_personnel_cb.bind(
                    "<<ComboboxSelected>>", 
                    self.on_waybill_personnel_selected
                )
            else:  # 如果没有送货人列表
                self.waybill_personnel_entry = ttk.Entry(
                    self.waybill_personnel_container, 
                    textvariable=self.waybill_personnel_var
                )
                self.waybill_personnel_entry.pack(fill=tk.X, padx=5)
                self.waybill_personnel_entry.bind(
                    "<KeyRelease>", 
                    self.on_waybill_personnel_changed
                )
        else:  # 如果选择"否"（非自有车辆）
            self.waybill_personnel_entry = ttk.Entry(
                self.waybill_personnel_container, 
                textvariable=self.waybill_personnel_var
            )
            self.waybill_personnel_var.set('')  # 设置为空字符串
            self.waybill_personnel_entry.pack(fill=tk.X, padx=5)
            self.waybill_personnel_entry.bind(
                "<KeyRelease>", 
                self.on_waybill_personnel_changed
            )
        
        # 初始化联系方式为空
        self.contact_information_var.set('')

    def on_waybill_personnel_selected(self, event=None):
        """当送货人选择变化时更新联系方式"""
        selected_person = self.waybill_personnel_var.get()
        if selected_person and selected_person != "请选择":
            # 从driver_data中获取联系方式
            contact = self.driver_data.get(selected_person, "")
            self.contact_information_var.set(contact)
        else:
            self.contact_information_var.set('')

    def on_waybill_personnel_changed(self, event=None):
        """当手动输入送货人时尝试匹配联系方式"""
            
        name = self.waybill_personnel_var.get()
        if name:
            # 尝试在driver_data中查找匹配的联系方式
            for driver, contact in self.driver_data.items():
                if name in driver:  # 部分匹配
                    self.contact_information_var.set(contact)
                    return
            # 如果没有找到匹配的，清空联系方式
            self.contact_information_var.set('')
    
    def confirm_shipping(self):
        """确认发运，收集表单数据"""
        # 获取仓库代码
        warehouse_name = self.warehouse_var.get()
        warehouse_code = self.warehouse_code_map.get(warehouse_name, "")  # 获取仓库代码
        
        # 获取物流方式代码
        logistics_mode = self.logistics_mode_var.get()
        logistics_code = self.logistics_code_map.get(logistics_mode, "")  # 获取物流方式代码
        # 获取物流公司代码
        logistics_company = self.logistics_company_var.get()
        logistics_company_id = self.logistics_company_id_map.get(self.logistics_company_var.get())  # 获取物流公司代码
        # 获取箱子名称代码
        box_name = self.box_name_var.get()
        box_info = self.box_model_map.get(box_name, {})  # 获取箱子相关信息
        

        # 获取拣货人（多选）
        picking_by_indices = self.picking_listbox.curselection()
        print(picking_by_indices)
        if len(picking_by_indices)==0:
            picking_by =None
        else:
            picking_by = ",".join([self.picking_listbox.get(i) for i in picking_by_indices])

        
        # 获取装箱人（多选）
        packing_by_indices = self.packing_listbox.curselection()
        print(packing_by_indices)
        packing_by = [self.packing_listbox.get(i) for i in packing_by_indices]
        if len(packing_by_indices)==0:
            packingBy = None
        else:
            packingBy = ",".join([self.packing_listbox.get(i) for i in packing_by_indices])



        if self.license_no_var.get()=='':
            license_no = None
        else:
            license_no = self.license_no_var.get()

        if self.waybill_personnel_var.get()=='':
            waybill_personnel = None
        else:
            waybill_personnel = self.waybill_personnel_var.get()



        forklift_driver = self.forklift_driver_var.get()

        if self.logistics_company_var.get()=='':
            logistics_company_id = None
        else:
            logistics_company_id = self.logistics_company_id_map.get(self.logistics_company_var.get())

        if self.contact_information_var.get()=='':
            contact_information = None
        else:
            contact_information = self.contact_information_var.get()
        
        # 收集所有字段的值
        shipping_data = {
            "picking_status" : 47111003,
            "picking_by" : picking_by,
            "dataList" : [],
            "packingData" : {
                "box_type" :box_info.get("id",""),
                "packing_by" : packing_by,
                "forklift_driver" : forklift_driver,
                "has_vehicle" : self.has_vehicle_var.get(),  # 返回10041001或10041002
                "license_no1" : license_no,
                "license_no2" : "",
                "waybill_personnel" : waybill_personnel,
                "contact_information" : contact_information,
                "box_type1" :box_info.get("box_type",""),
                "box_model" : box_info.get("box_model",""),
                "box_price" :0,
                "logistics_mode" : logistics_code,# 添加物流方式代码
                 "logistics_company_id" :logistics_company_id,
                "packingBy" :packingBy,
                "license_no" : license_no
                }
        }
        update_data = {
            "logistics_mode" :logistics_code,        
            "logistics_company_id" : logistics_company_id,   
            "dataList" : []
        }
        # 验证必填字段"warehouse_name",,"license_no", "waybill_personnel"
        required_fields = [ "box_model", "has_vehicle", "logistics_mode"]

        missing_fields = []
        
        # 检查仓库是否填写
        if not warehouse_name:
            missing_fields.append("出库仓库")
        
        # 检查箱子名称是否填写
        if not box_name:
            missing_fields.append("箱子名称")
        
        # 检查物流方式是否填写
        if not logistics_mode:
            missing_fields.append("物流方式")
        
        # 检查是否自有车辆是否填写
        if not self.has_vehicle_var.get():
            missing_fields.append("是否自有车辆")
 

##        # 只有自有车辆时才需要车牌号和送货人
        if self.has_vehicle_var.get() == 10041001 and logistics_code == 46171001:  # 自有车辆
            
            # 检查送货人是否填写
            waybill_personnel = self.waybill_personnel_var.get()
            if not waybill_personnel or waybill_personnel == "请选择":
                missing_fields.append("送货人")
        
        if missing_fields:
            messagebox.showwarning("警告", f"以下字段为必填项: {', '.join(missing_fields)}")
            return

        
        # 实际发运逻辑：对每个拣货单单独发运
        try:
            success = 0
            failed = []
            url_post = "https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking"
            picking_update_url="https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/updateLogisticsMode"

            for picking_order_no in self.processed_picking_orders:
                try:
                    url_get = f"https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/getPrintPickingList?picking_order_no={picking_order_no}"
                    resp = self.controller.session.get(url_get, timeout=10,headers=HEADERS)

                    # 检查登录状态
                    if not self.parent._check_response(resp):
                        return

                    if resp.status_code != 200:
                        failed.append((picking_order_no, f"GET HTTP {resp.status_code}"))
                        continue
                    dataList = resp.json().get("data")
                    print(dataList)
                    if not isinstance(dataList, list):
                        failed.append((picking_order_no, "GET 返回dataList非列表"))
                        continue

                    # 针对当前拣货单设置 dataList 后单独提交
                    update_data["dataList"] = dataList
                    print(json.dumps(update_data,indent=4,ensure_ascii=False,sort_keys=True))
                    post_resp = self.controller.session.post(picking_update_url, json=update_data, headers=HEADERS, timeout=15)
                    shipping_data["dataList"] = dataList

                    # 动态计算 picking_status（参考 inject.js 逻辑）
                    # 状态码: 47111002=拣货中, 47111003=拣货完成, 47111004=提前关闭, 47111005=作废
                    picking_status = 47111003  # 默认：拣货完成
                    total_picked = 0
                    for item in dataList:
                        pick_num = int(item.get("pick_num", 0) or 0)
                        total_picked += pick_num
                        # 期望数量：优先使用 split_num，其次 out_num
                        expected_qty = int(item.get("split_num") or item.get("out_num") or 0)
                        if pick_num != expected_qty:
                            picking_status = 47111004  # 提前关闭
                    if total_picked == 0:
                        picking_status = 47111005  # 作废
                    shipping_data["picking_status"] = picking_status

                    print(json.dumps(shipping_data,indent=4,ensure_ascii=False,sort_keys=True))
                    post_resp = self.controller.session.post(url_post, json=shipping_data, headers=HEADERS, timeout=15)

                    if post_resp.status_code != 200:
                        failed.append((picking_order_no, f"POST HTTP {post_resp.status_code}"))
                        continue
                    # 尝试解析返回
                    try:
                        _ = post_resp.json()
                    except Exception:
                        pass
                    success += 1
                except Exception as e_inner:
                    failed.append((picking_order_no, f"异常: {e_inner}"))
                    continue

            # 汇总提示
            if failed:
                fail_msg = "; ".join([f"{no}:{reason}" for no, reason in failed[:10]])
                more = "" if len(failed) <= 10 else f" 等共{len(failed)}条"
                messagebox.showwarning("部分失败", f"成功 {success} 条，失败 {len(failed)} 条。失败示例: {fail_msg}{more}")
            else:
                messagebox.showinfo("成功", f"已成功发运 {success} 条拣货单")
                # 发运成功后清空详情区域
                if hasattr(self, 'picking_detail_tree'):
                    self.picking_detail_tree.delete(*self.picking_detail_tree.get_children())
                    # 清空编辑控件
                    for combo in getattr(self, 'location_combos', []):
                        try:
                            combo.destroy()
                        except:
                            pass
                    for spin in getattr(self, 'quantity_spins', []):
                        try:
                            spin.destroy()
                        except:
                            pass
                    for combo in getattr(self, 'reason_combos', []):
                        try:
                            combo.destroy()
                        except:
                            pass
                    
                    # 重置相关列表
                    self.location_combos = []
                    self.quantity_spins = []
                    self.reason_combos = []
                    self.quantity_vars = []
                    self.detail_item_ids = []
                
                # 发运成功后重新查询拣货单
                if hasattr(self.parent, 'picking_query'):
                    self.parent.picking_query()
            # 结束后关闭窗口
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"发运流程发生异常: {e}")
            return


class PrintPreviewWindow:
    """打印预览窗口 - 展示拣货单HTML预览并通过WebSocket打印"""
    
    # 分类代码映射
    CATEGORY_TWO_MAP = {
        90921001: "前挡", 90921002: "后挡", 90921003: "侧窗",
        90921004: "门玻", 90921005: "天窗", 90921006: "角窗",
        90921007: "后悬窗", 90921008: "后视镜", 90921009: "其他"
    }
    
    # 物流方式映射
    LOGISTICS_MODE_MAP = {
        46171001: "送货", 46171002: "物流代收", 46171003: "物流发货",
        46171004: "自提", 46171005: "快递"
    }
    
    # 包装方式映射
    PACKING_METHOD_MAP = {
        90971001: "木箱", 90971002: "纸皮包装", 90971003: "自提", 90971004: "送货"
    }
    
    # 结算方式映射
    SETT_METHOD_MAP = {
        46221001: "现结", 46221002: "月结", 46221003: "挂账"
    }
    
    def __init__(self, parent, picking_order_nos, controller=None):
        self.parent = parent
        self.controller = controller
        self.picking_order_nos = picking_order_nos
        self.print_data = []  # 分组后的打印数据
        
        # 创建顶层窗口
        self.window = tk.Toplevel(parent)
        self.window.title("打印预览")
        self.window.geometry("900x700")
        self.window.minsize(600, 400)
        
        # 主框架
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部按钮区
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(btn_frame, text=f"已选 {len(picking_order_nos)} 个拣货单", 
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=5)
        
        btn_style = {"bg": "#673AB7", "fg": "white", "padx": 15, "pady": 5, 
                     "bd": 0, "activebackground": "#45a049", "font": ("微软雅黑", 10)}
        
        tk.Button(btn_frame, text="关闭", 
                  command=self.window.destroy,
                  bg="#f44336", fg="white", padx=15, pady=5, 
                  bd=0, font=("微软雅黑", 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="打印", 
                  command=self.print_via_clodop, **btn_style).pack(side=tk.RIGHT, padx=5)

        
        # HTML预览区域 - 使用 tkinterweb HtmlFrame（自带滚动条，支持table/CSS）
        self.preview_container = tk.Frame(main_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True)
        
        # 保存引用
        self.preview_canvas = None  # 不再使用Canvas
        self.preview_inner = None   # 将由 _render_preview 创建 HtmlFrame
        self.preview_text = None
        
        # 加载数据
        self._load_data()
    
    def _render_preview(self, html_content):
        """将HTML渲染到预览区域 - 使用 tkinterweb HtmlFrame 内嵌渲染表格布局"""
        # 清空预览容器
        for widget in self.preview_container.winfo_children():
            widget.destroy()
        
        # 构建完整HTML文档（tkinterweb 需要完整HTML结构）
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin:0; padding:10px; font-family:'微软雅黑',sans-serif; font-size:12px; background:#fff; }}
table {{ border-collapse:collapse; width:100%; }}
td {{ padding:2px 4px; }}
</style></head>
<body>{html_content}</body></html>"""
        
        try:
            # 使用 tkinterweb 的 HtmlFrame（自带滚动条，支持table/CSS布局）
            from tkinterweb import HtmlFrame
            self.html_frame = HtmlFrame(self.preview_container)
            self.html_frame.load_html(full_html)
            self.html_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            return
        except ImportError:
            pass
        
        # 回退：提示安装 tkinterweb
        label = tk.Label(self.preview_container,
                        text="打印预览需要 tkinterweb 库\n\n请运行：pip install tkinterweb\n\n安装后重启程序即可在窗口内预览",
                        font=("微软雅黑", 12), justify=tk.CENTER,
                        bg="white", fg="#333333")
        label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def _load_data(self):
        """加载打印数据并渲染预览"""
        try:
            loading_label = tk.Label(self.preview_container, 
                                     text="⏳ 正在获取打印数据...", 
                                     font=("微软雅黑", 10), bg="white")
            loading_label.pack(pady=20)
            self.window.update()
            
            # 构建URL并获取数据
            nos_str = ",".join([f"'{no}'" for no in self.picking_order_nos])
            url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/getPrintPickingList?picking_order_nos={nos_str}&picking_order_no="
            
            session = self.controller.session if self.controller else None
            if session:
                resp = session.get(url, timeout=15)
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
            
            # 数据分组
            self._group_data(data_list)
            
            # 生成HTML并显示
            html = self._build_html()
            self._render_preview(html)
            
        except Exception as e:
            self._render_preview(f"❌ 加载失败: {e}")
    
    def _group_data(self, data_list):
        """按 picking_order_no 分组，计算合计，收集item_ids用于打印统计"""
        groups = {}
        for item in data_list:
            order_no = item.get("picking_order_no", "")
            if order_no not in groups:
                groups[order_no] = {"items": [], "header": item}
            groups[order_no]["items"].append(item)
        
        for order_no, group in groups.items():
            items = group["items"]
            header = dict(group["header"])
            
            total_num = 0
            total_price = 0.0
            cashiers = []
            item_ids = []  # 收集id用于打印次数统计
            
            for item in items:
                pick_num = int(item.get("pick_num", 0) or 0)
                audit_price = float(item.get("audit_price", 0) or 0)
                total_num += pick_num
                total_price += pick_num * audit_price
                by_name = item.get("created_by_name", "")
                if by_name and by_name not in cashiers:
                    cashiers.append(by_name)
                item_id = item.get("id")
                if item_id:
                    item_ids.append(item_id)
            
            header["totalNum"] = total_num
            header["totalPrice"] = total_price
            header["cashier"] = ",".join(cashiers)
            header["item_ids"] = item_ids
            
            self.print_data.append({"header": header, "items": items})
    
    def _get_category_name(self, code):
        """获取分类名称"""
        return self.CATEGORY_TWO_MAP.get(code, str(code))
    
    def _build_html(self):
        """构建打印HTML"""
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        html_parts = []
        
        for idx, group in enumerate(self.print_data):
            header = group["header"]
            items = group["items"]
            
            # 品牌名简化
            brand_name = header.get("brand_name", "").replace("福耀玻璃", "福耀")
            
            # 物流模式名称
            logistics_code = header.get("logistics_mode", "")
            logistics_name = self.LOGISTICS_MODE_MAP.get(logistics_code, str(logistics_code))
            
            # 包装方式名称
            pack_code = header.get("packing_method", "")
            pack_name = self.PACKING_METHOD_MAP.get(pack_code, str(pack_code))
            
            # 结算方式名称
            sett_code = header.get("sett_method", "")
            sett_name = self.SETT_METHOD_MAP.get(sett_code, str(sett_code))
            
            # 出库类型
            outbound_type = header.get("outbound_type", 90371003)
            doc_type = "郑州晖锦调拨清单" if outbound_type == 90371014 else "郑州晖锦销售清单"
            
            # 构建每个分组的HTML
            group_html = f"""
    <div id="pickingPrintDiv{idx}" style="font-family:'微软雅黑';color:#000000;page-break-after:always;">
    <div style="width:100%;margin:0 auto;text-align:center;">
    <span style="font-size:25px;font-weight:bold;">{doc_type}</span>
    </div>
    <div style="width:100%;margin:0;text-align:left;">
    <table style="margin:0 auto;font-size:16px;width:96%;" align="center" valign="middle">
    <tr>
    <td style="vertical-align:top;text-align:left;width:35%;" colspan="4">客户名称：{header.get("DEALER_NAME", "")}</td>
    <td style="vertical-align:top;text-align:left;width:20%;" colspan="2">联 系 人：{header.get("linkman", "")}</td>
    <td style="vertical-align:top;text-align:left;width:35%;" colspan="2">单　　号：{header.get("picking_order_no", "")}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">客户地址：{header.get("receive_address", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">电　　话：{header.get("phone", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">打　　印：{current_date}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">出库仓库：{header.get("WAREHOUSE_NAME", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">物流公司：{header.get("logistics_company", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">物流电话：{header.get("logistics_phone", "")}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">配送方式：{logistics_name}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">包装方式：{pack_name}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">结算方式：{sett_name}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="8">摘　　要：{header.get("remark") or ""}</td>
    </tr>
    </table>
    <table style="width:98%;margin:0 auto;font-size:15px;vertical-align:middle;text-align:center;
    border:1px solid #000000;border-collapse:collapse;" align="center" valign="middle">
    <tr>
    <td style="width:8%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">品牌</td>
    <td style="width:31%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">产品名称</td>
    <td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">分类</td>
    <td style="width:17%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">产品编号</td>
    <td style="width:13%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">库位</td>
    <td style="width:5%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">数量</td>
    <td style="width:10%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">单价</td>
    <td style="width:9%;display:table-cell;vertical-align:middle;height:20px;border:1px solid #000000;border-collapse:collapse;">金额</td>
    </tr>"""
            
            # 产品明细行
            for item in items:
                i_brand = item.get("brand_name", "").replace("福耀玻璃", "福耀")
                i_part_name = item.get("part_name", "")
                i_category = self._get_category_name(item.get("category_two", ""))
                i_part_code = item.get("part_code", "")
                i_location = item.get("location_no", "")
                i_pick_num = item.get("pick_num", "0")
                i_audit_price = float(item.get("audit_price", 0) or 0)
                i_amount = int(item.get("pick_num", 0) or 0) * i_audit_price
                
                group_html += f"""
    <tr>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_brand} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_part_name} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_category} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_part_code} </td>
    <td style="text-align:left;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_location} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_pick_num} </td>
    <td style="text-align:right;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_audit_price:.2f} </td>
    <td style="text-align:right;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;"> {i_amount:.2f} </td>
    </tr>"""
            
            # 汇总行与签名区
            group_html += f"""
    <tr>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="3"> 合计数量：{header.get("totalNum", 0)} </td>
    <td style="text-align:center;display:table-cell;word-wrap:break-word;word-break:break-all;vertical-align:middle;border:1px solid #000000;" colspan="3"> 合计金额：{header.get("totalPrice", 0):.2f} </td>
    </tr>
    </table>
    <table style="width:96%;margin:0 auto;font-size:15px;" align="center" valign="middle">
    <tr>
    <td style="width:25%;text-align:left;">开单人：{header.get("cashier") or ""}</td>
    <td style="width:25%;text-align:left;">拣货人：{header.get("picking_by") or ""}</td>
    <td style="width:15%;text-align:left;">装箱人：{header.get("packing_by") or ""}</td>
    <td style="width:15%;text-align:right;">客户签字：</td>
    <td style="width:15%;text-align:left;border-bottom:1px solid #000;"></td>
    <td style="width:10%;text-align:left;">重({header.get("printNum", 1)})</td>
    </tr>
    </table>
    </div>
    </div>"""
            
            html_parts.append(group_html)
        
        return "\n".join(html_parts)
    
    def print_via_clodop(self):
        """通过WebSocket连接CLodop (localhost:8000) 直接打印到EPSON针式打印机，并上报打印次数"""
        import websocket
        
        if not self.print_data:
            messagebox.showwarning("警告", "没有可打印的数据")
            return
        
        try:
            # 收集所有item_id用于打印统计
            all_item_ids = []
            for group in self.print_data:
                ids = group["header"].get("item_ids", [])
                all_item_ids.extend(ids)
            
            # 去重
            seen = set()
            unique_item_ids = []
            for iid in all_item_ids:
                if iid not in seen:
                    seen.add(iid)
                    unique_item_ids.append(iid)
            
            # 生成HTML内容（带打印样式）
            html_parts = []
            # 添加全局样式
            html_head = '<style>div { width: 97%; } body { margin: 0; padding: 0; }</style>\n'
            
            for idx, group in enumerate(self.print_data):
                html_parts.append(
                    html_head + 
                    self._build_single_html(idx, group)
                )
            
            # 生成唯一TASKID
            now = datetime.now()
            task_id = f"PY{now.hour:02d}{now.minute:02d}{now.second:02d}_1"
            
            # CLodop WebSocket协议消息格式
            delim = "\f\f"  # CLodop分隔符
            printer_name = "EPSON LQ-630K ESC/P2"
            
            # 是否调拨单（使用连续纸设置）
            first_header = self.print_data[0].get("header", {})
            outbound_type = first_header.get("outbound_type", 90371003)
            
            if outbound_type == 90371014:
                orient = "1"
                pagewidth = "0"
                pageheight = "0"
                pagename = "A4"
            else:
                orient = "3"
                pagewidth = "220mm"
                pageheight = "15mm"
                pagename = ""
            
            # 连接WebSocket并发送每个打印任务
            ws = websocket.create_connection("ws://127.0.0.1:8000/c_webskt/", timeout=10)
            
            for idx, html_content in enumerate(html_parts):
                if outbound_type == 90371014:
                    html_content = html_content.replace('div { width: 97%; }', 'div { width: 97%} ')
                
                # 发送原始HTML内容（CLodop协议中1_content不需要URL编码）
                
                # 构建协议消息
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
                    f"printtask=拣货单打印{delim}"
                    f"printerindex={printer_name}{delim}"
                    f"orient={orient}{delim}"
                    f"pagewidth={pagewidth}{delim}"
                    f"pageheight={pageheight}{delim}"
                    f"pagename={pagename}{delim}"
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
            
            # 打印成功后，发起POST请求统计打印次数
            print_count_msg = ""
            if unique_item_ids:
                try:
                    payload = [{"id": iid} for iid in unique_item_ids]
                    print_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/print"
                    session = self.controller.session if self.controller else None
                    if session:
                        resp = session.post(print_url, json=payload, timeout=15)
                    else:
                        import requests
                        resp = requests.post(print_url, json=payload, timeout=15, headers=HEADERS)
                    
                    if resp.status_code == 200:
                        print_count_msg = f"\n打印次数已上报（{len(unique_item_ids)}条记录）"
                    else:
                        print_count_msg = f"\n打印次数上报失败: HTTP {resp.status_code}"
                except Exception as stat_e:
                    print_count_msg = f"\n打印次数上报异常: {stat_e}"
            # 更新预览中的打印次数显示（重新加载数据刷新printNum）
            self._refresh_print_num()            
            # 打印成功后关闭预览窗口
            self.window.destroy()
            
            # 注释掉统计信息弹窗，打印后不再弹出提示
            # messagebox.showinfo("成功", f"已发送 {len(html_parts)} 个打印任务到 EPSON LQ-630K ESC/P2{print_count_msg}")
            
        except Exception as e:
            messagebox.showerror("打印失败", f"CLodop WebSocket打印失败: {e}\n\n请确保 CLodop 服务已启动（localhost:8000）")
    
    def _refresh_print_num(self):
        """打印后重新获取数据，更新预览中的 printNum 显示"""
        try:
            nos_str = ",".join([f"'{no}'" for no in self.picking_order_nos])
            url = f"https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/getPrintPickingList?picking_order_nos={nos_str}&picking_order_no="
            
            session = self.controller.session if self.controller else None
            if session:
                resp = session.get(url, timeout=15)
            else:
                import requests
                resp = requests.get(url, timeout=15, headers=HEADERS)
            
            if resp.status_code != 200:
                return
            
            data_list = resp.json().get("data", [])
            if not isinstance(data_list, list) or len(data_list) == 0:
                return
            
            # 提取新的 printNum
            for group in self.print_data:
                order_no = group["header"].get("picking_order_no", "")
                # 从新数据中找对应订单的printNum
                for item in data_list:
                    if item.get("picking_order_no") == order_no:
                        group["header"]["printNum"] = item.get("printNum", group["header"].get("printNum", 1))
                        break
            
            # 重新渲染HTML预览
            html = self._build_html()
            self._render_preview(html)
            
        except Exception as e:
            pass  # 静默失败，不影响打印流程
    
    def _build_single_html(self, idx, group):
        """构建单个打印分组的HTML"""
        header = group["header"]
        items = group["items"]
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        brand_name = header.get("brand_name", "").replace("福耀玻璃", "福耀")
        logistics_name = self.LOGISTICS_MODE_MAP.get(header.get("logistics_mode", ""), "")
        pack_name = self.PACKING_METHOD_MAP.get(header.get("packing_method", ""), "")
        sett_name = self.SETT_METHOD_MAP.get(header.get("sett_method", ""), "")
        outbound_type = header.get("outbound_type", 90371003)
        doc_type = "郑州晖锦调拨清单" if outbound_type == 90371014 else "郑州晖锦销售清单"
        
        html = f"""    <div id="pickingPrintDiv{idx}" style="font-family:'微软雅黑';color:#000000;">
    <div style="width:100%;margin:0 auto;text-align:center;">
    <span style="font-size:25px;font-weight:bold;">{doc_type}</span>
    </div>
    <div style="width:100%;margin:0;text-align:left;">
    <table style="margin:0 auto;font-size:16px;width:96%;" align="center" valign="middle">
    <tr>
    <td style="vertical-align:top;text-align:left;width:35%;" colspan="4">客户名称：{header.get("DEALER_NAME", "")}</td>
    <td style="vertical-align:top;text-align:left;width:20%;" colspan="2">联 系 人：{header.get("linkman", "")}</td>
    <td style="vertical-align:top;text-align:left;width:35%;" colspan="2">单　　号：{header.get("picking_order_no", "")}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">客户地址：{header.get("receive_address", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">电　　话：{header.get("phone", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">打　　印：{current_date}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">出库仓库：{header.get("WAREHOUSE_NAME", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">物流公司：{header.get("logistics_company", "")}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">物流电话：{header.get("logistics_phone", "")}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="4">配送方式：{logistics_name}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">包装方式：{pack_name}</td>
    <td style="vertical-align:top;text-align:left;" colspan="2">结算方式：{sett_name}</td>
    </tr>
    <tr>
    <td style="vertical-align:top;text-align:left;" colspan="8">摘　　要：{header.get("remark") or ""}</td>
    </tr>
    </table>
    <table style="width:98%;margin:0 auto;font-size:15px;vertical-align:middle;text-align:center;
    border:1px solid #000000;border-collapse:collapse;" align="center" valign="middle">
    <tr>
    <td style="width:8%;border:1px solid #000000;">品牌</td>
    <td style="width:31%;border:1px solid #000000;">产品名称</td>
    <td style="width:5%;border:1px solid #000000;">分类</td>
    <td style="width:17%;border:1px solid #000000;">产品编号</td>
    <td style="width:13%;border:1px solid #000000;">库位</td>
    <td style="width:5%;border:1px solid #000000;">数量</td>
    <td style="width:10%;border:1px solid #000000;">单价</td>
    <td style="width:9%;border:1px solid #000000;">金额</td>
    </tr>"""
        
        for item in items:
            i_brand = item.get("brand_name", "").replace("福耀玻璃", "福耀")
            i_part_name = item.get("part_name", "")
            i_category = self._get_category_name(item.get("category_two", ""))
            i_part_code = item.get("part_code", "")
            i_location = item.get("location_no", "")
            i_pick_num = item.get("pick_num", "0")
            i_audit_price = float(item.get("audit_price", 0) or 0)
            i_amount = int(item.get("pick_num", 0) or 0) * i_audit_price
            
            html += f"""
    <tr>
    <td style="text-align:center;border:1px solid #000000;"> {i_brand} </td>
    <td style="text-align:left;border:1px solid #000000;"> {i_part_name} </td>
    <td style="text-align:center;border:1px solid #000000;"> {i_category} </td>
    <td style="text-align:left;border:1px solid #000000;"> {i_part_code} </td>
    <td style="text-align:left;border:1px solid #000000;"> {i_location} </td>
    <td style="text-align:center;border:1px solid #000000;"> {i_pick_num} </td>
    <td style="text-align:right;border:1px solid #000000;"> {i_audit_price:.2f} </td>
    <td style="text-align:right;border:1px solid #000000;"> {i_amount:.2f} </td>
    </tr>"""
        
        html += f"""
    <tr>
    <td style="text-align:center;border:1px solid #000000;" colspan="2"></td>
    <td style="text-align:center;border:1px solid #000000;" colspan="3"> 合计数量：{header.get("totalNum", 0)} </td>
    <td style="text-align:center;border:1px solid #000000;" colspan="3"> 合计金额：{header.get("totalPrice", 0):.2f} </td>
    </tr>
    </table>
    <table style="width:96%;margin:0 auto;font-size:15px;" align="center" valign="middle">
    <tr>
    <td style="width:25%;text-align:left;">开单人：{header.get("cashier") or ""}</td>
    <td style="width:25%;text-align:left;">拣货人：{header.get("picking_by") or ""}</td>
    <td style="width:15%;text-align:left;">装箱人：{header.get("packing_by") or ""}</td>
    <td style="width:15%;text-align:right;">客户签字：</td>
    <td style="width:15%;text-align:left;border-bottom:1px solid #000;"></td>
    <td style="width:10%;text-align:left;">重({header.get("printNum", 1)})</td>
    </tr>
    </table>
    </div>
    </div>"""
        
        return html


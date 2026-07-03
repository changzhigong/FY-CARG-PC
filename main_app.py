import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
from datetime import datetime
import json

from home_page import HomePage
from excel_data_processor import ExcelDataProcessPage
from deliver_report import DeliverReportProcessPage
from outbound_manager import outBoundProcessPage
from picking_shipping import OneKeyProcessPage
from transfer_manager import TransferProcessPage
from config_manager import ConfigPage



class MainApplication:
    """主应用程序框架"""
    # def __init__(self, root, session=None):
    #     self.root = root
    #     self.root.title("郑州晖锦汽车配件有限公司")
    #     self.root.geometry("1920x1000")
    #     self.root.attributes("-alpha", 0.95)
    #     # 统一管理session
    #     self.session = session if session else requests.Session()
        
    #     # 从配置文件加载选项
    #     try:
    #         with open("warehouse_config.json", "r", encoding="utf-8") as f:
    #             config = json.load(f)
    #             self.options = config["WAREHOUSE_OPTIONS"]
    #     except Exception as e:
    #         print(f"加载配置文件失败: {e}")
    #         self.options = {}

    #     self.headers = {
    #         'Accept': 'application/json, text/plain, */*',
    #         'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    #         'content-type': 'application/json;charset=UTF-8',
    #         'Refer': 'https://xb.fy-carg.com/',
    #         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
    #     }

    #     self.create_menu()
    #     style = ttk.Style()

    #     # 设置 Treeview 的字体样式
    #     style.configure("Treeview", 
    #                    font=('Arial', 12),  # 字体和大小
    #                    rowheight=25,        # 行高
    #                    background="#FFFFFF", # 背景色
    #                    foreground="#1E90FF", # 文字颜色
    #                    fieldbackground="#FFFFFF")  # 字段背景色
        
    #     # 设置表头的字体样式
    #     style.configure("Treeview.Heading", 
    #                    font=('Arial', 12),  # 粗体
    #                    background="#E0E0E0",        # 背景色
    #                    foreground="#673AB7")        # 文字颜色

    #     style.map('Treeview', 
    #              background=[('selected', '#4A6984')],  # 选中行颜色
    #              foreground=[('selected', 'white')])     # 选中行文字颜色
        
    #     style.configure('Transparent.TFrame', background='systemTransparent')
    #     # 页面容器
    #     self.container = ttk.Frame(self.root, style='Transparent.TFrame')
    #     self.container.pack(side="top", fill="both",expand=True)
    #     self.container.grid_rowconfigure(0, weight=1)
    #     self.container.grid_columnconfigure(0, weight=1)

    #     # 初始化页面 - 使用延迟加载
    #     self.frames = {}
    #     self.frame_classes = {
    #         "HomePage": HomePage,
    #         "ExcelDataProcessPage": ExcelDataProcessPage,
    #         "DeliverReportProcessPage": DeliverReportProcessPage,
    #         "outBoundProcessPage": outBoundProcessPage,
    #         "OneKeyProcessPage": OneKeyProcessPage,
    #         "TransferProcessPage": TransferProcessPage,
    #         "ConfigPage": ConfigPage
    #     }
        
    #     # 首先只创建首页，其他页面延迟加载
    #     self.frames["HomePage"] = HomePage(self.container, self)
    #     self.frames["HomePage"].grid(row=0, column=0, sticky="nsew")
        
    #     # 隐藏其他页面，但不创建它们
    #     for page_name in self.frame_classes.keys():
    #         if page_name != "HomePage":
    #             self.frames[page_name] = None
        
    #     # 显示首页
    #     self.show_frame("HomePage")
    
    #     # 添加状态栏
    #     self.create_status_bar()
    #     # 用于跟踪时间更新的after调用
    #     self.time_update_id = None
    def __init__(self, root, session=None):
        self.root = root
        self.root.title("郑州晖锦汽车配件有限公司")
        self.root.geometry("1920x1000")
        self.root.attributes("-alpha", 0.95)
        # 统一管理session
        self.session = session if session else requests.Session()
        
        # 从配置文件加载选项
        try:
            with open("warehouse_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                self.options = config["WAREHOUSE_OPTIONS"]
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.options = {}

        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'application/json;charset=UTF-8',
            'Refer': 'https://xb.fy-carg.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
        }
        self.create_menu()
        # 页面容器
        style = ttk.Style()
        style.configure('Transparent.TFrame', background='systemTransparent')
        self.container = ttk.Frame(self.root, style='Transparent.TFrame')
        self.container.pack(side="top", fill="both",expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # 初始化页面 - 使用延迟加载
        self.frames = {}
        self.frame_classes = {
            "HomePage": HomePage,
            "ExcelDataProcessPage": ExcelDataProcessPage,
            "DeliverReportProcessPage": DeliverReportProcessPage,
            "outBoundProcessPage": outBoundProcessPage,
            "OneKeyProcessPage": OneKeyProcessPage,
            "TransferProcessPage": TransferProcessPage,
            "ConfigPage": ConfigPage
        }
        
        # 首先只创建首页，其他页面延迟加载
        self.frames["HomePage"] = HomePage(self.container, self)
        self.frames["HomePage"].grid(row=0, column=0, sticky="nsew")
        
        # 隐藏其他页面，但不创建它们
        for page_name in self.frame_classes.keys():
            if page_name != "HomePage":
                self.frames[page_name] = None
        


        # 设置 Treeview 的字体样式
        style.configure("Treeview", 
                       font=('Arial', 12),  # 字体和大小
                       rowheight=25,        # 行高
                       background="#FFFFFF", # 背景色
                       foreground="#1E90FF", # 文字颜色
                       fieldbackground="#FFFFFF")  # 字段背景色
        
        # 设置表头的字体样式
        style.configure("Treeview.Heading", 
                       font=('Arial', 12),  # 粗体
                       background="#E0E0E0",        # 背景色
                       foreground="#673AB7")        # 文字颜色

        style.map('Treeview', 
                 background=[('selected', '#4A6984')],  # 选中行颜色
                 foreground=[('selected', 'white')])     # 选中行文字颜色

        # 显示首页
        self.show_frame("HomePage")
    
        # 添加状态栏
        self.create_status_bar()
        # 用于跟踪时间更新的after调用
        self.time_update_id = None
    def check_login_status(self, response):
        """
        检查登录状态，如果token被顶下线则处理登出
        """
        try:
            if response and hasattr(response, 'text') and response.text:
                data = response.json()
                error_msg = data.get('errorMsg', '')
                if '错误原因:token 已被顶下线' in error_msg:
                    # 显示下线提示
                    messagebox.showerror("登录状态异常", "您的账号已在其他地方登录，当前会话已失效。\n即将返回登录界面。")
                    
                    # 关闭主窗口
                    self.root.destroy()
                    
                    # 重新打开登录窗口
                    from login_app import LoginApp
                    login_root = tk.Tk()
                    login_app = LoginApp(login_root)
                    login_root.mainloop()
                    return True
        except Exception as e:
            # 解析响应出错，但不影响主流程
            pass
        return False

    # def create_menu(self):
    #     tab_control = ttk.Notebook(self.root, style="Custom.TNotebook")
        
    #     # 创建选项卡页（实际为占位Frame，保持原有页面切换逻辑）
    #     home_tab = ttk.Frame(tab_control)
    #     report_tab = ttk.Frame(tab_control)
    #     finance_tab = ttk.Frame(tab_control)
    #     outBound_tab = ttk.Frame(tab_control)
    #     onekey_tab = ttk.Frame(tab_control)
    #     Transfer_tab = ttk.Frame(tab_control)
    #     config_tab = ttk.Frame(tab_control)
        
    #     tab_control.add(home_tab, text="首页")
    #     tab_control.add(report_tab, text="送货日报") 
    #     tab_control.add(finance_tab, text="财务日报")
    #     tab_control.add(outBound_tab, text="出库管理")
    #     tab_control.add(onekey_tab, text="一键发运")
    #     tab_control.add(Transfer_tab, text="调拨入库")
    #     tab_control.add(config_tab, text="配置管理")
    #     tab_control.pack(expand=0, fill=tk.BOTH, padx=5, pady=5)

    #     # 自定义标签页样式
    #     style = ttk.Style()
    #     style.configure("Custom.TNotebook", background="#E5E5E5", borderwidth=0)
    #     style.configure("Custom.TNotebook.Tab", 
    #                     background="#1E90FF", 
    #                     foreground="#bdc3c7", 
    #                     padding=[20, 5],
    #                     font=("Arial", 10, "bold"))
    #     style.map("Custom.TNotebook.Tab", 
    #               background=[("selected", "#1E90FF")],
    #               foreground=[("selected", "#1E90FF")])        
        
    #     # 绑定选项卡切换事件
    #     tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
    #     # 配置页访问控制状态
    #     self._config_unlocked = False
        
    def _get_config_password(self):
        """读取配置页面密码，优先从文件config_password.txt；否则使用默认"""
        try:
            with open("config_password.txt", "r", encoding="utf-8") as f:
                val = f.read().strip()
                return val if val else "admin123"
        except Exception:
            return "admin123"

    # def on_tab_change(self, event):
    #     """处理选项卡切换事件"""
    #     tab_control = event.widget
    #     selected = tab_control.tab(tab_control.select(), "text")
        
    #     # 离开配置页后自动加锁
    #     if selected != "配置管理":
    #         self._config_unlocked = False

    #     # 配置页访问密码验证
    #     if selected == "配置管理" and not getattr(self, "_config_unlocked", False):
    #         pwd = simpledialog.askstring("安全验证", "请输入配置页面密码：", show="*")
    #         if pwd is None:
    #             # 用户取消，回到首页
    #             tab_control.select(0)
    #             return
    #         if pwd != self._get_config_password():
    #             messagebox.showerror("权限错误", "密码不正确，无法进入配置页面")
    #             tab_control.select(0)
    #             return
    #         self._config_unlocked = True
        
    #     page_map = {
    #         "首页": "HomePage",
    #         "送货日报": "DeliverReportProcessPage",
    #         "财务日报": "ExcelDataProcessPage",
    #         "出库管理":"outBoundProcessPage",
    #         "一键发运":"OneKeyProcessPage",
    #         "调拨入库":"TransferProcessPage",
    #         "配置管理":"ConfigPage"
    #     }
        
    #     page_name = page_map[selected]
    #     self.show_frame(page_name)

    # def create_menu(self):
    #     tab_control = ttk.Notebook(self.root, style="Custom.TNotebook")
        
    #     # 创建选项卡页
    #     home_tab = ttk.Frame(tab_control)
    #     quick_access_tab = ttk.Frame(tab_control)
    #     warehouse_tab = ttk.Frame(tab_control)
    #     internal_ops_tab = ttk.Frame(tab_control)
    #     config_tab = ttk.Frame(tab_control)
        
    #     tab_control.add(home_tab, text="首页")
    #     tab_control.add(quick_access_tab, text="快捷操作")
    #     tab_control.add(warehouse_tab, text="仓库理货")
    #     tab_control.add(internal_ops_tab, text="库内作业")
    #     tab_control.add(config_tab, text="配置管理")
    #     tab_control.pack(expand=0, fill=tk.BOTH, padx=5, pady=5)

    #     # 在快捷操作标签页中添加按钮
    #     quick_access_frame = ttk.LabelFrame(quick_access_tab, text="日常操作", padding=10)
    #     quick_access_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    #     ttk.Button(quick_access_frame, text="送货日报", 
    #               command=lambda: self.show_frame("DeliverReportProcessPage")).pack(fill=tk.X, pady=5)
    #     ttk.Button(quick_access_frame, text="财务日报", 
    #               command=lambda: self.show_frame("ExcelDataProcessPage")).pack(fill=tk.X, pady=5)
        
    #     # 在仓库理货标签页中添加按钮
    #     warehouse_frame = ttk.LabelFrame(warehouse_tab, text="出库管理", padding=10)
    #     warehouse_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    #     ttk.Button(warehouse_frame, text="出库管理", 
    #               command=lambda: self.show_frame("outBoundProcessPage")).pack(fill=tk.X, pady=5)
    #     ttk.Button(warehouse_frame, text="一键发运", 
    #               command=lambda: self.show_frame("OneKeyProcessPage")).pack(fill=tk.X, pady=5)
        
    #     # 在库内作业标签页中添加按钮
    #     internal_ops_frame = ttk.LabelFrame(internal_ops_tab, text="调拨作业", padding=10)
    #     internal_ops_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    #     ttk.Button(internal_ops_frame, text="调拨入库", 
    #               command=lambda: self.show_frame("TransferProcessPage")).pack(fill=tk.X, pady=5)
        
    #     # 自定义标签页样式
    #     style = ttk.Style()
    #     style.configure("Custom.TNotebook", background="#E5E5E5", borderwidth=0)
    #     style.configure("Custom.TNotebook.Tab", 
    #                     background="#1E90FF", 
    #                     foreground="#bdc3c7", 
    #                     padding=[20, 5],
    #                     font=("Arial", 10, "bold"))
    #     style.map("Custom.TNotebook.Tab", 
    #               background=[("selected", "#1E90FF")],
    #               foreground=[("selected", "#1E90FF")])        
        
    #     # 绑定选项卡切换事件
    #     tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
    #     # 配置页访问控制状态
    #     self._config_unlocked = False

    # def create_menu(self):
    #     tab_control = ttk.Notebook(self.root, style="Custom.TNotebook")
        
    #     # 创建选项卡页
    #     home_tab = ttk.Frame(tab_control)
    #     quick_access_tab = ttk.Frame(tab_control)
    #     warehouse_tab = ttk.Frame(tab_control)
    #     internal_ops_tab = ttk.Frame(tab_control)
    #     config_tab = ttk.Frame(tab_control)
        
    #     tab_control.add(home_tab, text="首页")
    #     tab_control.add(quick_access_tab, text="快捷操作")
    #     tab_control.add(warehouse_tab, text="仓库理货")
    #     tab_control.add(internal_ops_tab, text="库内作业")
    #     tab_control.add(config_tab, text="配置管理")
    #     tab_control.pack(expand=0, fill=tk.BOTH, padx=5, pady=5)

    #     # 在快捷操作标签页中添加按钮
    #     quick_access_frame = ttk.Frame(quick_access_tab)
    #     quick_access_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
    #     ttk.Label(quick_access_frame, text="日常操作", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
    #     button_frame1 = ttk.Frame(quick_access_frame)
    #     button_frame1.pack()
        
    #     ttk.Button(button_frame1, text="送货日报", 
    #               command=lambda: self.show_frame("DeliverReportProcessPage"),
    #               width=20).pack(side=tk.LEFT, padx=5)
    #     ttk.Button(button_frame1, text="财务日报", 
    #               command=lambda: self.show_frame("ExcelDataProcessPage"),
    #               width=20).pack(side=tk.LEFT, padx=5)
        
    #     # 在仓库理货标签页中添加按钮
    #     warehouse_frame = ttk.Frame(warehouse_tab)
    #     warehouse_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
    #     ttk.Label(warehouse_frame, text="出库管理", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
    #     button_frame2 = ttk.Frame(warehouse_frame)
    #     button_frame2.pack()
        
    #     ttk.Button(button_frame2, text="出库管理", 
    #               command=lambda: self.show_frame("outBoundProcessPage"),
    #               width=20).pack(side=tk.LEFT, padx=5)
    #     ttk.Button(button_frame2, text="一键发运", 
    #               command=lambda: self.show_frame("OneKeyProcessPage"),
    #               width=20).pack(side=tk.LEFT, padx=5)
        
    #     # 在库内作业标签页中添加按钮
    #     internal_ops_frame = ttk.Frame(internal_ops_tab)
    #     internal_ops_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
    #     ttk.Label(internal_ops_frame, text="调拨作业", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
    #     button_frame3 = ttk.Frame(internal_ops_frame)
    #     button_frame3.pack()
        
    #     ttk.Button(button_frame3, text="调拨入库", 
    #               command=lambda: self.show_frame("TransferProcessPage"),
    #               width=20).pack(side=tk.LEFT, padx=5)
        
    #     # 自定义标签页样式
    #     style = ttk.Style()
    #     style.configure("Custom.TNotebook", background="#E5E5E5", borderwidth=0)
    #     style.configure("Custom.TNotebook.Tab", 
    #                     background="#1E90FF", 
    #                     foreground="#bdc3c7", 
    #                     padding=[20, 5],
    #                     font=("Arial", 10, "bold"))
    #     style.map("Custom.TNotebook.Tab", 
    #               background=[("selected", "#1E90FF")],
    #               foreground=[("selected", "#1E90FF")])        
        
    #     # 绑定选项卡切换事件
    #     tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)
    #     # 配置页访问控制状态
    #     self._config_unlocked = False


    # def create_menu(self):
    #     # 创建顶部的选项卡按钮
    #     tab_frame = ttk.Frame(self.root)
    #     tab_frame.pack(fill=tk.X, padx=5, pady=5)
        
    #     # 创建选项卡样式
    #     style = ttk.Style()
    #     style.configure("Tab.TButton", 
    #                    background="#1E90FF", 
    #                    foreground="#bdc3c7", 
    #                    padding=[20, 5],
    #                    font=("Arial", 10, "bold"))
    #     style.map("Tab.TButton", 
    #              background=[("selected", "#1E90FF")],
    #              foreground=[("selected", "#1E90FF")])
        
    #     # 创建选项卡按钮
    #     self.tab_buttons = {}
    #     self.tab_panels = {}
        
    #     tabs_info = [
    #         ("首页", []),
    #         ("快捷操作", ["送货日报", "财务日报"]),
    #         ("仓库理货", ["出库管理", "一键发运"]),
    #         ("库内作业", ["调拨入库"]),
    #         ("配置管理", [])
    #     ]
        
    #     for i, (tab_name, buttons) in enumerate(tabs_info):
    #         btn = ttk.Button(tab_frame, text=tab_name, style="Tab.TButton")
    #         btn.pack(side=tk.LEFT, padx=2)
    #         self.tab_buttons[tab_name] = btn
            
    #         # 为有子按钮的选项卡创建弹出面板
    #         if buttons:
    #             panel = self.create_popup_panel(tab_name, buttons)
    #             self.tab_panels[tab_name] = panel
                
    #             # 绑定点击事件
    #             btn.bind("<Button-1>", lambda e, name=tab_name: self.toggle_panel(name))
    #         else:
    #             # 为没有子按钮的选项卡直接绑定功能
    #             if tab_name == "首页":
    #                 btn.config(command=lambda: self.show_frame("HomePage"))
    #             elif tab_name == "配置管理":
    #                 btn.config(command=self.open_config_page)
        
    #     # 创建配置页访问控制状态
    #     self._config_unlocked = False
    def create_menu(self):
        # 创建顶部的选项卡按钮
        tab_frame = ttk.Frame(self.root)
        tab_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建选项卡样式
        style = ttk.Style()
        style.configure("Tab.TButton", 
                       background="#1E90FF", 
                       foreground="#bdc3c7", 
                       padding=[20, 5],
                       font=("Arial", 10, "bold"))
        style.map("Tab.TButton", 
                 background=[("selected", "#1E90FF")],
                 foreground=[("selected", "#1E90FF")])
        
        # 创建高亮样式
        style.configure("Active.Tab.TButton", 
                       background="white",  # 更亮的蓝色
                       foreground="#4682B4", 
                       padding=[20, 5],
                       font=("Arial", 11, "bold"))
        style.map("Active.Tab.TButton", 
                 background=[("selected", "white")],
                 foreground=[("selected", "#4682B4")])
        
        # 创建选项卡按钮
        self.tab_buttons = {}
        self.tab_panels = {}
        
        tabs_info = [
            ("首页", []),
            ("快捷操作", ["送货日报", "财务日报"]),
            ("仓库理货", ["出库管理", "一键发运"]),
            ("库内作业", ["调拨入库"]),
            ("配置管理", [])
        ]
        
        for i, (tab_name, buttons) in enumerate(tabs_info):
            btn = ttk.Button(tab_frame, text=tab_name, style="Tab.TButton")
            btn.pack(side=tk.LEFT, padx=2)
            self.tab_buttons[tab_name] = btn
            
            # 为有子按钮的选项卡创建弹出面板
            if buttons:
                panel = self.create_popup_panel(tab_name, buttons)
                self.tab_panels[tab_name] = panel
                
                # 绑定鼠标进入和离开事件
                btn.bind("<Enter>", lambda e, name=tab_name: self.show_panel(name))
                btn.bind("<Leave>", lambda e, name=tab_name: self.schedule_hide_panel(name))
                panel.bind("<Enter>", lambda e, name=tab_name: self.cancel_hide_panel(name))
                panel.bind("<Leave>", lambda e, name=tab_name: self.schedule_hide_panel(name))
            else:
                # 为没有子按钮的选项卡直接绑定功能
                if tab_name == "首页":
                    btn.config(command=lambda: self.show_frame("HomePage"))
                elif tab_name == "配置管理":
                    btn.config(command=self.open_config_page)
        
        # 创建配置页访问控制状态
        self._config_unlocked = False
        
        # 用于延迟隐藏面板的定时器
        self._hide_panel_timer = None

    def show_panel(self, tab_name):
        """显示弹出面板"""
        # 取消之前的隐藏定时器
        if self._hide_panel_timer:
            self.root.after_cancel(self._hide_panel_timer)
            self._hide_panel_timer = None
            
        # 隐藏所有面板
        self.hide_all_panels()
        
        # 显示点击的面板
        if tab_name in self.tab_panels:
            panel = self.tab_panels[tab_name]
            btn = self.tab_buttons[tab_name]
            
            # 获取按钮位置
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height()
            
            # 定位并显示面板
            panel.geometry(f"+{x}+{y}")
            panel.deiconify()
            panel.lift()
    
    def schedule_hide_panel(self, tab_name):
        """延迟隐藏面板"""
        if self._hide_panel_timer:
            self.root.after_cancel(self._hide_panel_timer)
        self._hide_panel_timer = self.root.after(300, self.hide_all_panels)  # 300ms后隐藏
        
    def cancel_hide_panel(self, tab_name):
        """取消隐藏面板的计划"""
        if self._hide_panel_timer:
            self.root.after_cancel(self._hide_panel_timer)
            self._hide_panel_timer = None
    def hide_all_panels(self):
        """隐藏所有弹出面板"""
        for panel in self.tab_panels.values():
            panel.withdraw()
            
        # 清除定时器
        if self._hide_panel_timer:
            self.root.after_cancel(self._hide_panel_timer)
            self._hide_panel_timer = None

    def create_popup_panel(self, tab_name, buttons):
        """创建弹出面板"""
        panel = tk.Toplevel(self.root)
        panel.withdraw()  # 初始隐藏
        panel.overrideredirect(True)  # 无边框窗口
        panel.configure(bg="#f0f0f0", relief="raised", bd=1)
        
        # 添加按钮到面板
        for button_text in buttons:
            page_map = {
                "送货日报": "DeliverReportProcessPage",
                "财务日报": "ExcelDataProcessPage",
                "出库管理": "outBoundProcessPage",
                "一键发运": "OneKeyProcessPage",
                "调拨入库": "TransferProcessPage"
            }
            
            # if button_text in page_map:
            #     btn = ttk.Button(panel, 
            #                    text=button_text,
            #                    command=lambda page=page_map[button_text]: self.show_frame(page),
            #                    width=15)
            #     btn.pack(fill=tk.X, padx=5, pady=2)
            if button_text in page_map:
                # 传递tab_name和button_text给lambda函数
                btn = ttk.Button(panel, 
                               text=button_text,
                               command=lambda t=tab_name, b=button_text, p=page_map[button_text]: self.select_submenu(t, b, p),
                               width=15)
                btn.pack(fill=tk.X, padx=5, pady=2)        
        return panel
    def select_submenu(self, tab_name, button_text, page_name):
        """选择子菜单项"""
        # 隐藏所有面板
        self.hide_all_panels()
        
        # 更新选项卡按钮的文本
        if tab_name in self.tab_buttons:
            # 保存原始文本，方便恢复
            if not hasattr(self, '_original_tab_names'):
                self._original_tab_names = {}
            if tab_name not in self._original_tab_names:
                self._original_tab_names[tab_name] = tab_name
                
            self.tab_buttons[tab_name].config(text=button_text)
            # 高亮显示当前选项卡
            self.highlight_active_tab(tab_name)        
        # 显示对应的页面
        self.show_frame(page_name)
    # def toggle_panel(self, tab_name):
    #     """切换弹出面板的显示/隐藏"""
    #     # 隐藏所有面板
    #     self.hide_all_panels()
        
    #     # 如果点击的是当前显示的面板对应的选项卡，则隐藏它
    #     if hasattr(self, '_current_panel') and self._current_panel == tab_name:
    #         delattr(self, '_current_panel')
    #         return
            
    #     # 显示点击的面板
    #     if tab_name in self.tab_panels:
    #         panel = self.tab_panels[tab_name]
    #         btn = self.tab_buttons[tab_name]
            
    #         # 获取按钮位置
    #         x = btn.winfo_rootx()
    #         y = btn.winfo_rooty() + btn.winfo_height()
            
    #         # 定位并显示面板
    #         panel.geometry(f"+{x}+{y}")
    #         panel.deiconify()
    #         panel.lift()
            
    #         # 记录当前显示的面板
    #         self._current_panel = tab_name
            
    #         # 点击其他地方隐藏面板
    #         self._root_click_funcid = self.root.bind("<Button-1>", self.on_root_click, add="+")
    
    # def hide_all_panels(self):
    #     """隐藏所有弹出面板"""
    #     for panel in self.tab_panels.values():
    #         panel.withdraw()
            
    #     # 解除绑定
    #     try:
    #         if hasattr(self, '_root_click_funcid'):
    #             self.root.unbind("<Button-1>", self._root_click_funcid)
    #             delattr(self, '_root_click_funcid')
    #     except tk.TclError:
    #         pass
    
    # def on_root_click(self, event):
    #     """处理根窗口点击事件，用于隐藏面板"""
    #     # 检查点击是否在面板或按钮上
    #     x, y = event.x_root, event.y_root
        
    #     clicked_on_panel = False
    #     if hasattr(self, '_current_panel'):
    #         panel = self.tab_panels[self._current_panel]
    #         panel_x = panel.winfo_rootx()
    #         panel_y = panel.winfo_rooty()
    #         panel_width = panel.winfo_width()
    #         panel_height = panel.winfo_height()
            
    #         if (panel_x <= x <= panel_x + panel_width and 
    #             panel_y <= y <= panel_y + panel_height):
    #             clicked_on_panel = True
        
    #     clicked_on_button = False
    #     for btn in self.tab_buttons.values():
    #         btn_x = btn.winfo_rootx()
    #         btn_y = btn.winfo_rooty()
    #         btn_width = btn.winfo_width()
    #         btn_height = btn.winfo_height()
            
    #         if (btn_x <= x <= btn_x + btn_width and 
    #             btn_y <= y <= btn_y + btn_height):
    #             clicked_on_button = True
        
    #     # 如果点击在面板或按钮之外的地方，隐藏面板
    #     if not clicked_on_panel and not clicked_on_button:
    #         self.hide_all_panels()
    #         if hasattr(self, '_current_panel'):
    #             delattr(self, '_current_panel')
    
    def open_config_page(self):
        """打开配置页面（带密码验证）"""
        if not getattr(self, "_config_unlocked", False):
            pwd = simpledialog.askstring("安全验证", "请输入配置页面密码：", show="*")
            if pwd is None:
                return
            if pwd != self._get_config_password():
                messagebox.showerror("权限错误", "密码不正确，无法进入配置页面")
                return
            self._config_unlocked = True
        
        self.show_frame("ConfigPage")


    # def on_tab_change(self, event):
    #     """处理选项卡切换事件"""
    #     tab_control = event.widget
    #     selected = tab_control.tab(tab_control.select(), "text")
        
    #     # 离开配置页后自动加锁
    #     if selected != "配置管理":
    #         self._config_unlocked = False

    #     # 配置页访问密码验证
    #     if selected == "配置管理" and not getattr(self, "_config_unlocked", False):
    #         pwd = simpledialog.askstring("安全验证", "请输入配置页面密码：", show="*")
    #         if pwd is None:
    #             # 用户取消，回到首页
    #             tab_control.select(0)
    #             return
    #         if pwd != self._get_config_password():
    #             messagebox.showerror("权限错误", "密码不正确，无法进入配置页面")
    #             tab_control.select(0)
    #             return
    #         self._config_unlocked = True
        
    #     # 对于非按钮标签页，仍然需要映射到相应的页面
    #     page_map = {
    #         "首页": "HomePage",
    #         "配置管理":"ConfigPage"
    #     }
        
    #     if selected in page_map:
    #         page_name = page_map[selected]
    #         self.show_frame(page_name)


    # def show_frame(self, page_name):
    #     """显示指定页面"""
    #     # 延迟加载页面
    #     if self.frames[page_name] is None:
    #         frame_class = self.frame_classes[page_name]
    #         frame = frame_class(self.container, self)
    #         self.frames[page_name] = frame
    #         frame.grid(row=0, column=0, sticky="nsew")
    #         frame.grid_remove()  # 隐藏页面直到需要显示
        
    #     frame = self.frames[page_name]
    #     frame.grid()
    #     frame.tkraise()
    #     # 如果离开配置页面，则重置配置页面的解锁状态
    #     if page_name != "ConfigPage":
    #         self._config_unlocked = False


        
    def show_frame(self, page_name):
        """显示指定页面"""
        # 延迟加载页面
        if self.frames[page_name] is None:
            frame_class = self.frame_classes[page_name]
            frame = frame_class(self.container, self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_remove()  # 隐藏页面直到需要显示
        
        frame = self.frames[page_name]
        frame.grid()
        frame.tkraise()
        
        # 如果离开配置页面，则重置配置页面的解锁状态
        if page_name != "ConfigPage":
            self._config_unlocked = False
            
        # 更新选项卡文字显示
        self.update_tab_names(page_name)
            
    def update_tab_names(self, current_page):
        """根据当前页面更新选项卡文字"""
        # 定义页面到选项卡组的映射
        page_to_tab_group = {
            "DeliverReportProcessPage": "快捷操作",
            "ExcelDataProcessPage": "快捷操作",
            "outBoundProcessPage": "仓库理货",
            "OneKeyProcessPage": "仓库理货",
            "TransferProcessPage": "库内作业"
        }
        
        # 获取当前页面所属的选项卡组
        current_page_group = page_to_tab_group.get(current_page)
        
        # 如果当前页面属于某个功能组
        if current_page_group:
            # 找到对应的选项卡并更新文字
            for tab_name, original_name in self._original_tab_names.items():
                if original_name == current_page_group:
                    # 这是当前页面所属的选项卡，显示页面名称
                    page_name_map = {
                        "DeliverReportProcessPage": "送货日报",
                        "ExcelDataProcessPage": "财务日报", 
                        "outBoundProcessPage": "出库管理",
                        "OneKeyProcessPage": "一键发运",
                        "TransferProcessPage": "调拨入库"
                    }
                    if current_page in page_name_map:
                        self.tab_buttons[tab_name].config(text=page_name_map[current_page])
                    # 高亮显示当前活动选项卡
                    self.highlight_active_tab(tab_name)
                else:
                    # 其他选项卡恢复原始文字
                    self.tab_buttons[tab_name].config(text=original_name)
        else:
            # 如果是首页或配置页面，则恢复所有选项卡的原始文字
            self.restore_tab_names()
            # 根据页面类型高亮对应的选项卡
            if current_page == "HomePage":
                self.highlight_active_tab("首页")
            elif current_page == "ConfigPage":
                self.highlight_active_tab("配置管理")


    def highlight_active_tab(self, active_tab_name):
        """高亮显示当前活动选项卡"""
        # 重置所有选项卡样式
        for tab_name, btn in self.tab_buttons.items():
            if tab_name == active_tab_name:
                # 高亮显示当前选项卡
                btn.config(style="Active.Tab.TButton")
            else:
                # 恢复其他选项卡样式
                btn.config(style="Tab.TButton")
                
    #     # 配置高亮样式
    #     style = ttk.Style()
    #     style.configure("Active.Tab.TButton", 
    #                    background="#4682B4",  # 更亮的蓝色
    #                    foreground="white", 
    #                    padding=[20, 5],
    #                    font=("Arial", 10, "bold"))
    #     style.map("Active.Tab.TButton", 
    #              background=[("selected", "#4682B4")],
    #              foreground=[("selected", "white")])            
    def restore_tab_names(self):
        """恢复选项卡按钮的原始文本"""
        if hasattr(self, '_original_tab_names'):
            for tab_name, original_name in self._original_tab_names.items():
                if tab_name in self.tab_buttons:
                    self.tab_buttons[tab_name].config(text=original_name)

    def create_status_bar(self):
        """创建状态栏"""
        status_bar = tk.Frame(self.root, bg="#34495e", height=25)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 左侧状态信息
        tk.Label(
            status_bar, 
            text="准备就绪", 
            font=("Arial", 9), 
            bg="#34495e", 
            fg="#ecf0f1",
            padx=10
        ).pack(side=tk.LEFT)
        
        # 右侧状态信息
        tk.Label(
            status_bar, 
            text="版权所有违者必究", 
            font=("Arial", 9), 
            bg="#34495e", 
            fg="#bdc3c7",
            padx=10
        ).pack(side=tk.RIGHT)
        
        # 时间显示
        self.time_label = tk.Label(
            status_bar, 
            text="", 
            font=("Arial", 9), 
            bg="#34495e", 
            fg="#bdc3c7",
            padx=10
        )
        self.time_label.pack(side=tk.RIGHT)
        self.update_time()
    
    def update_time(self):
        """更新状态栏时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        # 保存after调用的ID，以便在退出时取消
        self.time_update_id = self.root.after(1000, self.update_time)
    
    def show_status(self, message):
        """显示状态栏消息"""
        # 查找状态栏中的左侧标签（第一个子组件）
        status_bar = self.root.winfo_children()[-1]  # 状态栏是root的最后一个子组件
        if isinstance(status_bar, tk.Frame) and status_bar.winfo_children():
            status_label = status_bar.winfo_children()[0]  # 左侧标签是第一个子组件
            if isinstance(status_label, tk.Label):
                status_label.config(text=message)
    
    def hide_status(self):
        """隐藏状态栏消息（恢复默认状态）"""
        self.show_status("准备就绪")
        
    def after(self, ms, func=None):
        """转发after方法到root窗口对象"""
        return self.root.after(ms, func)

    def destroy(self):
        """重写destroy方法以正确清理资源"""
        try:
            # 取消时间更新的after调用
            if self.time_update_id:
                self.root.after_cancel(self.time_update_id)
        except Exception:
            # 如果已经销毁或出错，忽略
            pass
        
        try:
            # 销毁主窗口
            self.root.destroy()
        except Exception:
            # 如果已经销毁，忽略
            pass
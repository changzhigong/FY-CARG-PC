import tkinter as tk
from tkinter import ttk

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("多页面程序框架")
        self.geometry("800x600")
        
        # 创建菜单系统
        self.create_menu()
        
        # 创建页面容器
        self.container = ttk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # 初始化页面字典
        self.frames = {}
        
        # 创建所有页面
        for F in (HomePage, SettingsPage, AboutPage):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        # 显示初始页面
        self.show_frame("HomePage")

    def create_menu(self):
        # 创建主菜单栏
        menubar = tk.Menu(self)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="主页", command=lambda: self.show_frame("HomePage"))
        view_menu.add_command(label="设置", command=lambda: self.show_frame("SettingsPage"))
        menubar.add_cascade(label="视图", menu=view_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=lambda: self.show_frame("AboutPage"))
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.config(menu=menubar)

    def show_frame(self, page_name):
        """显示指定页面"""
        frame = self.frames[page_name]
        frame.tkraise()

class BasePage(ttk.Frame):
    """页面基类"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.create_widgets()
        
    def create_widgets(self):
        """需要子类实现"""
        raise NotImplementedError

class HomePage(BasePage):
    def create_widgets(self):
        label = ttk.Label(self, text="主页", font=('Arial', 18))
        label.pack(pady=20)
        
        btn = ttk.Button(self, text="去设置页",
                        command=lambda: self.controller.show_frame("SettingsPage"))
        btn.pack()

class SettingsPage(BasePage):
    def create_widgets(self):
        label = ttk.Label(self, text="设置页面", font=('Arial', 18))
        label.pack(pady=20)
        
        # 示例设置控件
        self.var = tk.BooleanVar()
        check = ttk.Checkbutton(self, text="示例选项", variable=self.var)
        check.pack(pady=10)
        
        btn = ttk.Button(self, text="返回主页",
                        command=lambda: self.controller.show_frame("HomePage"))
        btn.pack()

class AboutPage(BasePage):
    def create_widgets(self):
        label = ttk.Label(self, text="关于我们", font=('Arial', 18))
        label.pack(pady=20)
        
        text = tk.Text(self, height=10)
        text.insert(tk.END, "这是一个多页面程序示例\n版本：1.0.0")
        text.pack(pady=10)
        text.config(state=tk.DISABLED)
        
        btn = ttk.Button(self, text="关闭",
                        command=lambda: self.controller.show_frame("HomePage"))
        btn.pack()

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()

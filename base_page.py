import tkinter as tk
from tkinter import ttk


class BasePage(ttk.Frame):
    """页面基类"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # 创建内容容器
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        # 创建页面内容
        self.create_widgets()        
    def create_widgets(self):
        """创建页面组件 - 子类必须重写此方法"""
        # 空实现，子类需要重写
        pass

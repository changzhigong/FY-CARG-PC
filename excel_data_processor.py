import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import shutil
import pyperclip
import os
from data_processor import DataFetcher, ExcelProcessor
from base_page import BasePage


class ExcelDataProcessPage(BasePage):
    """Excel数据处理页面"""
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller
        

    def create_widgets(self):
        """创建界面组件"""
        # 日期选择区
        date_frame = ttk.LabelFrame(self.content_frame, text="选择日期")
        date_frame.pack(pady=10, fill="x", padx=10)
        
        ttk.Label(date_frame, text="日期:").grid(row=0, column=0, padx=5)
        self.date_entry = DateEntry(date_frame, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1)
        
        # 仓库选择区
        warehouse_frame = ttk.LabelFrame(self.content_frame, text="选择仓库")
        warehouse_frame.pack(pady=10, fill="x", padx=10)
        
        self.warehouse_combo = ttk.Combobox(warehouse_frame, values=list(self.controller.options.keys()))
        self.warehouse_combo.current(0)
        self.warehouse_combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 操作按钮区
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="下载并处理", command=self._download_and_process).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="返回首页", command=lambda: self.controller.show_frame("HomePage")).pack(side=tk.RIGHT, padx=10)
        # 状态显示区
        self.status_var = tk.StringVar(value="")
        status_bar = ttk.Label(self.content_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _download_and_process(self):
        """从服务器下载数据"""
        try:
            warehouse_name = self.warehouse_combo.get()
            warehouse_id = self.controller.options[warehouse_name]
            date = self.date_entry.get()
            
            self.status_var.set(f"正在从服务器下载{warehouse_name}数据...")
            self.update()
            
            # 使用DataFetcher类获取数据
            fetcher = DataFetcher(self.controller.session)
            data = fetcher.fetch_data(warehouse_id, date)
            
            # 保存原始文件
            file_prefix = f"{warehouse_name}{date}"
            xls_path = f"{file_prefix}.xls"
            with open(xls_path, 'wb') as f:
                f.write(data)
            
            self.status_var.set(f"数据下载完成: {xls_path}")
        except Exception as e:
            self.status_var.set(f"下载失败: {str(e)}")
            messagebox.showerror("错误", f"数据下载失败: {str(e)}")

        """处理Excel文件"""
        try:
            warehouse_name = self.warehouse_combo.get()
            date = self.date_entry.get()
            
            # 查找最新的xls文件
            file_prefix = f"{warehouse_name}{date}"
            xls_path = f"{file_prefix}.xls"
            xlsx_path = f"{file_prefix}.xlsx"
            
            if not os.path.exists(xls_path):
                raise FileNotFoundError(f"找不到文件: {xls_path}")
            
            self.status_var.set(f"正在处理Excel文件: {xls_path}...")
            self.update()
            
            # 使用ExcelProcessor处理文件
            ExcelProcessor.convert_xls_to_xlsx(xls_path, xlsx_path)
            ExcelProcessor.process_workbook(xlsx_path)
            
            # 复制到默认下载路径
            dest_path = os.path.join("D:/Downloads/", os.path.basename(xlsx_path))
            shutil.copy(xlsx_path, dest_path)
            # 清理临时文件
            os.remove(xls_path)

            # 复制路径到剪贴板
            pyperclip.copy(dest_path)
            
            self.status_var.set(f"处理完成，文件已保存至: {dest_path}")
            messagebox.showinfo("完成", f"Excel文件处理完成!\n保存路径: {dest_path}")
        except Exception as e:
            self.status_var.set(f"处理失败: {str(e)}")
            messagebox.showerror("错误", f"Excel处理失败: {str(e)}")

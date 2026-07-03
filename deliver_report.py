import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from collections import defaultdict
from datetime import datetime, date
from tkcalendar import DateEntry
import json
import os
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import TableColumn
from openpyxl.styles.borders import Border, Side
from openpyxl.styles import PatternFill, Font, NamedStyle, Alignment, Border, Side
from openpyxl import load_workbook
import requests
from ctypes import create_unicode_buffer, windll
from typing import Union
from copy import copy,deepcopy
from base_page import BasePage

# 常量定义
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json;charset=UTF-8',
    'Refer': 'https://xb.fy-carg.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
}

class DeliverReportProcessPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller
    def create_widgets(self):
        # 日期选择组件
        date_frame = ttk.LabelFrame(self.content_frame, text="日期范围选择")
        date_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(date_frame, text="起始日期:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_cal = DateEntry(date_frame, date_pattern='yyyy-mm-dd')
        self.start_cal.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        tk.Label(date_frame, text="结束日期:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_cal = DateEntry(date_frame, date_pattern='yyyy-mm-dd')
        self.end_cal.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 仓库选择
        warehouse_frame = ttk.LabelFrame(self.content_frame, text="仓库选择")
        warehouse_frame.pack(fill=tk.X, pady=10)
        
##        tk.Label(warehouse_frame, text="选择仓库:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.combo = ttk.Combobox(
            warehouse_frame, 
            values=list(self.controller.options.keys())
        )
        self.combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        self.combo.current(0)

        # 处理按钮
        def process_data_callback():
            """数据处理按钮回调函数"""
            try:
                start = self.start_cal.get()
                end = self.end_cal.get()
                selected_warehouse = self.combo.get()
                selected_id = self.controller.options[selected_warehouse]  # 直接使用self.options
                
                # 显示处理状态
                status_var.set(f"正在处理 {selected_warehouse} {start} 至 {end} 的数据...")
                self.update()
                
                output_path = self.process_data(start, end, selected_id)
                messagebox.showinfo("完成", f"数据处理完成\n保存路径: {output_path}")
##                status_var.set(f"数据处理完成,保存路径: {output_path}")
                # 更新状态
                status_var.set("数据处理完成")
            except Exception as e:
                messagebox.showerror("错误", f"处理失败: {str(e)}")
                status_var.set("处理失败")

        # 状态栏
        status_var = tk.StringVar(value="")
        status_bar = ttk.Label(
            self.content_frame, 
            textvariable=status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 操作按钮区
        butn_frame = ttk.Frame(self.content_frame)
        butn_frame.pack(pady=15)
        
        # 处理按钮
        process_button = ttk.Button(
            butn_frame, 
            text="开始处理", 
            command=process_data_callback,
            width=20
        )
        process_button.pack(side=tk.LEFT,padx=10)
        ttk.Button(butn_frame, text="返回首页", command=lambda: self.controller.show_frame("HomePage")).pack(side=tk.RIGHT,padx=10)

    def get_Driver_value(self, input_date: Union[str, datetime.date]) -> str:
        if isinstance(input_date, str):
            input_date = datetime.strptime(input_date, '%Y-%m-%d').date()
        return ["永城", "柘城", "民权", "永城", "柘城", "民权", "周日休息"][input_date.weekday()]


    def get_weekday_value(self, input_date: Union[str, datetime.date]) -> str:
        if isinstance(input_date, str):
            input_date = datetime.strptime(input_date, '%Y-%m-%d').date()
        return ["永城", "柘城", "民权", "永城", "柘城", "民权", "周日休息"][input_date.weekday()]

    def process_data(self, startdate: str, enddate: str, selected_id: int):
        """完整数据处理流程"""
        # 查询数据
        query_url = (
            f'https://xb.fy-carg.com/dmscloud.part/salesProfitGlass/queryDetail?'
            f'bill_at_begin={startdate}&bill_at_end={enddate}&bill_type=&dealer_name=&'
            f'dealer_code=&logistics_mode=46171001&funds_type=&license_no=&category_two=&'
            f'part_large_category=91011001&part_code=&part_name=&dealer_type=&created_by=&'
            f'storage_id={selected_id}&crowdfunding_code=&promotion_code=&act_type=&line=&'
            f'dealer_area=&limit=500&pageNum=1'
        )
        
        try:
            response = self.controller.session.get(query_url, headers=HEADERS)
            response.raise_for_status()
            
            # 保存临时数据
            with open('temp_data.json', 'wb') as f:
                f.write(response.content)
                
            # 构建文件路径
            buf = create_unicode_buffer(260)
            windll.shell32.SHGetFolderPathW(0, 5, 0, 0, buf)
            base_path = f"{buf.value}/WXWork/1688855801452093/WeDrive/郑州晖锦汽车配件/5、物流部门/9、车辆送货管理".replace("\\", "/")
            excel_path = f"{base_path}/{next(k for k,v in self.controller.options.items() if v == selected_id)[:-1]}送货车辆.xlsx"
##            excel_path = f"{next(k for k,v in self.options.items() if v == selected_id)[:-1]}送货车辆.xlsx"
            # 处理Excel
            df = self._process_json_to_excel('temp_data.json', excel_path)
            self._append_to_excel(excel_path, df)
            
            os.remove('temp_data.json')
            return excel_path
        except Exception as e:
            print(f"数据处理失败: {str(e)}")
            raise

    def _process_json_to_excel(self, json_path: str, excel_path: str) -> pd.DataFrame:
        """JSON数据处理逻辑"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)['data']['rows']
        
        daily_sum = defaultdict(lambda: {'NUM': 0, 'IN_TAX_AMOUNT': 0.0})
        
        for item in data:
            date_str = item['bill_date']
            daily_sum[date_str]['NUM'] += int(item['NUM'])
            daily_sum[date_str]['IN_TAX_AMOUNT'] += float(item['IN_TAX_AMOUNT'])
        wb = load_workbook(excel_path)
        ws = wb.active
        max_row = ws.max_row
        records = []
        for i, (date_str, sums) in enumerate(daily_sum.items(), 1):
            records.append({
                'SN': max_row+i-1,
                'Date': date_str,
                'Route': self.get_weekday_value(date_str),
                'Sum1': sums['NUM'],
                'Sum2': sums['IN_TAX_AMOUNT'],
                'Driver': '陈杰',
                'Other1': '',
                'Other2': ''
            })
        
        return pd.DataFrame(records)

    def _append_to_excel(self, excel_path: str, df: pd.DataFrame) -> None:
        """带样式的Excel追加"""
        book = load_workbook(excel_path)
        sheet = book.active
        
        # 获取样式模板
        style_row = 2 if sheet.max_row >=2 else 1
        style_template = [
            {attr: copy(getattr(sheet.cell(row=style_row, column=j), attr)) 
             for attr in ('font', 'fill', 'border', 'alignment', 'number_format')}
            for j in range(1, sheet.max_column + 1)
        ]
        
        # 追加数据
        for idx, row in df.iterrows():
            new_row = sheet.max_row + 1
            for col_idx, value in enumerate(row, 1):
                cell = sheet.cell(row=new_row, column=col_idx, value=value)
                if col_idx-1 < len(style_template):
                    for attr, val in style_template[col_idx-1].items():
                        setattr(cell, attr, val)
        
        book.save(excel_path)

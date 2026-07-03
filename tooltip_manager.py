import tkinter as tk
from tkinter import ttk


class TreeviewTooltipManager:
    """全局Treeview Tooltip管理器"""
    def __init__(self):
        self.current_tooltip = None
    
    def attach_tooltip(self, treeview):
        """为Treeview附加tooltip功能"""
        treeview.bind("<Motion>", lambda e: self.on_treeview_motion(e, treeview))
        treeview.bind("<Leave>", self.on_treeview_leave)
    
    def on_treeview_motion(self, event, treeview):
        """处理Treeview中的鼠标移动事件"""
        # 获取鼠标位置的项目和列
        row_id = treeview.identify_row(event.y)
        column_id = treeview.identify_column(event.x)
        
        # 如果有现有的tooltip，先销毁它
        if self.current_tooltip:
            self.hide_tooltip()
            
        # 如果鼠标在有效的单元格上
        if row_id and column_id:
            # 获取单元格的值
            try:
                item_values = treeview.item(row_id, 'values')
                col_num = int(column_id[1:]) - 1  # 转换为0基索引
                
                # 确保索引有效
                if 0 <= col_num < len(item_values):
                    cell_value = item_values[col_num]
                    
                    # 只有当内容不为空且超出了显示范围时才显示tooltip
                    if cell_value and str(cell_value).strip():
                        # 创建新的tooltip
                        self.show_tooltip(treeview, event, str(cell_value))
            except Exception:
                # 忽略任何错误，避免因为索引等问题导致异常
                pass
    
    def on_treeview_leave(self, event=None):
        """鼠标离开Treeview时隐藏tooltip"""
        self.hide_tooltip()
    
    def show_tooltip(self, widget, event, text):
        """显示tooltip"""
        x = event.x_root + 10
        y = event.y_root + 10

        # 创建提示窗口
        self.current_tooltip = tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.configure(bg="#ffffe0")

        label = tk.Label(tw, text=text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("微软雅黑", "9", "normal"))
        label.pack(ipadx=1, ipady=1)
    
    def hide_tooltip(self):
        """隐藏tooltip"""
        if self.current_tooltip:
            self.current_tooltip.destroy()
            self.current_tooltip = None

# 创建全局的Treeview Tooltip管理器实例
tooltip_manager = TreeviewTooltipManager()
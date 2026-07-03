import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from base_page import BasePage
from typing import Any
import requests
from io import BytesIO

class HomePage(BasePage):
    """首页"""
    """首页"""
    _image_refs: list[Any]

    def __init__(self, parent, controller):
        self._image_refs = []
        super().__init__(parent, controller)

    def create_widgets(self):
        # 从在线URL获取图片
        url = "https://xb.fy-carg.com/png/file-read-2224-d9173f6b.png"
        
        try:
            # 发送GET请求获取图片数据
            response = requests.get(url)
            response.raise_for_status()  # 如果请求失败会抛出异常
            
            # 将获取的数据转换为BytesIO对象，然后由PIL打开
            image_data = BytesIO(response.content)
            image = Image.open(image_data)
            
            photo = ImageTk.PhotoImage(image)
            
            # 创建Label用于显示图片，放在content_frame中而不是self上
            background_label = ttk.Label(self.content_frame, image=photo)
            # 保持对photo的引用，防止被垃圾回收
            self._image_refs.append(photo)
            background_label.place(x=0, y=0, relwidth=1, relheight=1)
            
        except requests.exceptions.RequestException as e:
            print(f"加载图片失败: {e}")
            # 这里可以添加加载失败时的备用处理

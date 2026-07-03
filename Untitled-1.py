#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket登录状态监控模块
负责建立WebSocket连接并监控登录状态
"""

import websocket
import threading
import json
import time
import logging
from tkinter import messagebox
import tkinter as tk

class WebSocketMonitor:
    """WebSocket登录状态监控器"""
    
    def __init__(self, session, base_url="https://xb.fy-carg.com"):
        self.session = session
        self.base_url = base_url
        self.ws_url = self._get_ws_url()
        self.ws = None
        self.is_connected = False
        self.is_monitoring = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 重连延迟秒数
        
        # 状态回调函数
        self.on_status_change = None
        self.on_connection_lost = None
        
        # 线程控制
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        self._setup_logging()
    
    def _get_ws_url(self):
        """获取WebSocket URL"""
        # 根据您的API结构，这里需要确定WebSocket端点
        # 假设WebSocket端点为 /dmscloud/websocket
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"{ws_url}/dmscloud/websocket"
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("WebSocketMonitor")
    
    def start_monitoring(self, on_status_change=None, on_connection_lost=None):
        """开始监控登录状态"""
        self.on_status_change = on_status_change
        self.on_connection_lost = on_connection_lost
        
        if self.is_monitoring:
            self.logger.warning("监控已经在运行中")
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.logger.info("WebSocket监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.ws:
            self.ws.close()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("WebSocket监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring and not self.stop_event.is_set():
            try:
                if not self.is_connected:
                    self._connect_websocket()
                
                # 保持连接活跃
                if self.is_connected:
                    self._send_heartbeat()
                
                # 等待一段时间后再次检查
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {str(e)}")
                self._handle_connection_error()
    
    def _connect_websocket(self):
        """建立WebSocket连接"""
        try:
            # 获取cookies用于认证
            cookies = self.session.cookies.get_dict()
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                header={
                    "Cookie": cookie_header,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            # 启动WebSocket连接（非阻塞）
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 等待连接建立
            for _ in range(30):  # 最多等待30秒
                if self.is_connected or self.stop_event.is_set():
                    break
                time.sleep(1)
            
            if self.is_connected:
                self.reconnect_attempts = 0
                self.logger.info("WebSocket连接建立成功")
            else:
                raise Exception("WebSocket连接超时")
                
        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {str(e)}")
            self._handle_connection_error()
    
    def _on_open(self, ws):
        """WebSocket连接打开回调"""
        self.is_connected = True
        self.logger.info("WebSocket连接已打开")
        
        # 发送认证消息（如果需要）
        self._send_auth_message()
    
    def _on_message(self, ws, message):
        """WebSocket消息接收回调"""
        try:
            data = json.loads(message)
            self.logger.debug(f"收到WebSocket消息: {data}")
            
            # 处理状态码信息
            if "status" in data:
                status_code = data.get("status")
                self._handle_status_code(status_code)
            
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析WebSocket消息: {message}")
    
    def _on_error(self, ws, error):
        """WebSocket错误回调"""
        self.logger.error(f"WebSocket错误: {str(error)}")
        self.is_connected = False
        self._handle_connection_error()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭回调"""
        self.logger.info(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.is_connected = False
        self._handle_connection_lost()
    
    def _send_auth_message(self):
        """发送认证消息"""
        try:
            auth_message = {
                "type": "auth",
                "token": self._get_auth_token(),
                "timestamp": int(time.time())
            }
            self.ws.send(json.dumps(auth_message))
            self.logger.debug("认证消息已发送")
        except Exception as e:
            self.logger.error(f"发送认证消息失败: {str(e)}")
    
    def _send_heartbeat(self):
        """发送心跳包"""
        try:
            heartbeat = {
                "type": "heartbeat",
                "timestamp": int(time.time())
            }
            self.ws.send(json.dumps(heartbeat))
            self.logger.debug("心跳包已发送")
        except Exception as e:
            self.logger.error(f"发送心跳包失败: {str(e)}")
            self.is_connected = False
    
    def _get_auth_token(self):
        """获取认证token"""
        # 从session中提取认证信息
        # 这里需要根据您的认证机制实现
        return "auth_token_placeholder"
    
    def _handle_status_code(self, status_code):
        """处理状态码"""
        if status_code == 101:
            # 登录状态保持正常
            if self.on_status_change:
                self.on_status_change("connected", "登录状态正常")
        else:
            # 登录状态异常
            self.logger.warning(f"登录状态异常，状态码: {status_code}")
            if self.on_status_change:
                self.on_status_change("disconnected", f"登录状态异常: {status_code}")
            
            # 触发下线处理
            self._handle_user_logged_out()
    
    def _handle_user_logged_out(self):
        """处理用户下线"""
        self.logger.warning("检测到用户已下线")
        
        # 在主线程中显示下线提示
        if tk._default_root:  # 检查Tkinter根窗口是否存在
            tk._default_root.after(0, self._show_logout_message)
        
        # 停止监控
        self.stop_monitoring()
    
    def _show_logout_message(self):
        """显示下线提示消息"""
        try:
            messagebox.showerror(
                "登录状态异常", 
                "检测到您的登录已下线，窗口将自动关闭。\n请重新登录系统。",
                parent=tk._default_root
            )
            
            # 延迟关闭窗口，让用户看到消息
            tk._default_root.after(1000, self._close_application)
            
        except Exception as e:
            self.logger.error(f"显示下线消息失败: {str(e)}")
    
    def _close_application(self):
        """关闭应用程序"""
        try:
            if tk._default_root:
                tk._default_root.quit()
                tk._default_root.destroy()
        except Exception as e:
            self.logger.error(f"关闭应用程序失败: {str(e)}")
    
    def _handle_connection_error(self):
        """处理连接错误"""
        self.is_connected = False
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * self.reconnect_attempts
            self.logger.info(f"将在{delay}秒后尝试重连 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            # 延迟重连
            threading.Timer(delay, self._attempt_reconnect).start()
        else:
            self.logger.error("达到最大重连次数，停止重连")
            self._handle_connection_lost()
    
    def _attempt_reconnect(self):
        """尝试重连"""
        if self.is_monitoring and not self.stop_event.is_set():
            self.logger.info("尝试重新连接WebSocket")
            self._connect_websocket()
    
    def _handle_connection_lost(self):
        """处理连接丢失"""
        self.logger.warning("WebSocket连接已丢失")
        
        if self.on_connection_lost:
            self.on_connection_lost()
        
        # 如果连接丢失但监控仍在继续，尝试重新建立连接
        if self.is_monitoring:
            self._handle_connection_error()

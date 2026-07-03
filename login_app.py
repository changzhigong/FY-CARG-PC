import tkinter as tk
from tkinter import ttk, messagebox
import requests
from http import cookiejar
from cryptography.fernet import Fernet
import json
import os
from datetime import datetime
from PIL import Image, ImageTk
import io
import sys
import traceback


class SecureStorage:
    """安全存储处理类"""
    def __init__(self):
        self.key_file = 'secret.key'
        self.data_file = 'user_config.json'
        self._ensure_key_exists()

    def _ensure_key_exists(self):
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)

    def _get_cipher(self):
        with open(self.key_file, 'rb') as f:
            return Fernet(f.read())

    def save_credentials(self, username, password, remember):
        try:
            data = {
                'remember': remember,
                'username': username if remember else '',
                'password': self._get_cipher().encrypt(password.encode()).decode() if remember else ''
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f)
            print(f"[INFO] 凭证已保存: {username}")
        except Exception as e:
            print(f"[ERROR] 保存凭证失败 - 错误信息: {str(e)}")
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            raise

    def load_credentials(self):
        try:
            if not os.path.exists(self.data_file):
                return None, None, False

            with open(self.data_file, 'r') as f:
                data = json.load(f)

            password = ''
            if data['remember'] and data['password']:
                password = self._get_cipher().decrypt(data['password'].encode()).decode()

            print(f"[INFO] 凭证已加载: {data['username'] if data['username'] else '无用户名'}")
            return data['username'], password, data['remember']
        except Exception as e:
            print(f"[ERROR] 加载凭证失败 - 错误信息: {str(e)}")
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            return None, None, False


class LoginApp:
    """登录系统主类"""
    def __init__(self, root):
        self.root = root


        self.storage = SecureStorage()
        # 登录状态标志
        self.login_success = False        
        # 创建新的session
        self.session = requests.Session()
        # 创建cookies jar
        self.cookie_jar = cookiejar.LWPCookieJar(filename='cookies')
        # 尝试加载cookies，如果不存在则创建新的
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
            print("[INFO] Cookies加载成功")
        except Exception as e:
            print(f"[WARNING] 加载cookies失败: {e}")
        # 将cookie jar设置到session
        self.session.cookies = self.cookie_jar  # type: ignore
        
        self.login_attempts = 0
        self.max_attempts = 3

        # 网站接口配置
        self.login_api_url = "https://xb.fy-carg.com/dmscloud.basedata/login"
        self.captcha_url = "https://xb.fy-carg.com/dmscloud.basedata/login/code?key=1"
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
        }

        # 配置ttk样式
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f5f5f5")
        self.style.configure("TLabel", background="#f5f5f5", font=("微软雅黑", 10))
        self.style.configure("TButton", 
                           font=("微软雅黑", 10), 
                           padding=5,
                           relief="flat",
                           background="#4a90e2",
                           foreground="white")
        self.style.map("TButton",
                      background=[("active", "#3a7bc8")])
        self.style.configure("TRadiobutton", font=("微软雅黑", 10))
        self.style.configure("TEntry", font=("微软雅黑", 10))

        # # 先隐藏窗口，在窗口配置完成后再显示
        # self.root.withdraw()

        self._center_window()        
        self._create_widgets()
        self._load_credentials()
        # 延迟加载验证码，确保GUI组件已创建
        self.root.after(50, self._refresh_captcha)
    def _center_window(self):
        self.root.title("安全登录系统")
        self.root.configure(bg="#f5f5f5")
        # """将窗口居中显示"""
        # self.root.update_idletasks()
        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # 获取窗口宽度和高度
        window_width = 400
        window_height = 400
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # # 显示窗口
        # self.root.deiconify()
        # 设置窗口置顶
        self.root.wm_attributes("-topmost", True)
        # 可选：在窗口获得焦点后取消置顶
        self.root.after(1000, lambda: self.root.wm_attributes("-topmost", False))
    def _create_widgets(self):
        """创建登录界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, 
                 text="系统登录", 
                 font=("微软雅黑", 16, "bold"),
                 foreground="#333").pack(pady=15)

        # 输入区域框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.BOTH,pady=10)


        # 用户名
        ttk.Label(input_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(input_frame, width=25)
        self.username_entry.grid(row=0, column=1, pady=5, padx=10)

        # 密码
        ttk.Label(input_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(input_frame, show="●", width=25)
        self.password_entry.grid(row=1, column=1, pady=5, padx=10)

        # 记住密码
        self.remember_var = tk.BooleanVar()
        ttk.Checkbutton(input_frame, 
                       text="记住密码", 
                       variable=self.remember_var).grid(row=2, columnspan=2, pady=5)

        # 验证码区域
        captcha_frame = ttk.Frame(input_frame)
        captcha_frame.grid(row=3, columnspan=2, pady=10)
        ttk.Label(captcha_frame, text="验证码:").pack(side=tk.LEFT)
        self.captcha_entry = ttk.Entry(captcha_frame, width=10)
        self.captcha_entry.pack(side=tk.LEFT, padx=5)
        self.captcha_label = ttk.Label(captcha_frame)
        self.captcha_label.pack(side=tk.LEFT)
        ttk.Button(captcha_frame, 
                  text="刷新", 
                  command=self._refresh_captcha, 
                  width=5).pack(side=tk.LEFT, padx=5)

        # 登录按钮
        ttk.Button(main_frame, 
                  text="登 录", 
                  command=self._perform_login, 
                  style="TButton",
                  width=15).pack(pady=20)
        
        # 绑定回车键
        self.root.bind('<Return>', lambda event: self._perform_login())

    def _load_credentials(self):
        """加载存储的凭证"""
        print("[INFO] 开始加载存储的凭证")
        username, password, remember = self.storage.load_credentials()
        if username:
            print(f"[INFO] 加载用户名: {username}")
            self.username_entry.insert(0, username)
        if password:
            print("[INFO] 加载密码")
            self.password_entry.insert(0, password)
        self.remember_var.set(remember)
        print(f"[INFO] 记住密码选项: {remember}")

    def _refresh_captcha(self):
        """刷新验证码图片"""
        print("[INFO] 开始刷新验证码")
        try:
            # 检查窗口是否仍然存在
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                print("[INFO] 窗口已关闭，取消刷新验证码")
                return
            print(f"[INFO] 请求验证码URL: {self.captcha_url}")
            response = self.session.get(self.captcha_url, headers=self.headers)
            print(f"[INFO] 验证码请求状态码: {response.status_code}")
            img = Image.open(io.BytesIO(response.content)).resize((100, 30), resample=Image.Resampling.LANCZOS)
            self.captcha_img = ImageTk.PhotoImage(img)
            # 检查Label是否仍然存在再配置
            if hasattr(self, 'captcha_label') and self.captcha_label.winfo_exists():
                self.captcha_label.config(image=self.captcha_img)
                print("[INFO] 验证码图片已刷新并显示")
            else:
                print("[WARNING] 验证码Label不存在，可能窗口已关闭")
        except Exception as e:
            print(f"[ERROR] 验证码加载失败 - 错误信息: {str(e)}")
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            # 避免在没有GUI环境时报错
            # messagebox.showerror("错误", f"验证码加载失败: {str(e)}")

    def _perform_login(self):
        """执行登录操作"""
        print("[INFO] 开始执行登录操作")
        if self.login_attempts >= self.max_attempts:
            print(f"[ERROR] 登录尝试次数过多: {self.login_attempts} >= {self.max_attempts}")
            messagebox.showerror("错误", "登录尝试次数过多，请稍后再试")
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        captcha = self.captcha_entry.get().strip()
        
        print(f"[INFO] 用户输入 - 用户名: {username}, 验证码: {captcha}")

        # 基本验证
        if not all([username, password, captcha]):
            print("[ERROR] 登录表单填写不完整")
            messagebox.showerror("错误", "所有字段必须填写")
            return

        try:
            # 验证验证码
            print("[INFO] 开始验证验证码")
            verify_url = f'https://xb.fy-carg.com/dmscloud.basedata/login/verifyCode/{captcha}'
            print(f"[INFO] 验证码验证URL: {verify_url}")
            verify_res = self.session.get(verify_url, headers=self.headers)
            print(f"[INFO] 验证码验证响应状态: {verify_res.status_code}")
            print(f"[INFO] 验证码验证响应内容: {verify_res.text}")
            
            if not verify_res.json().get('success'):
                print("[ERROR] 验证码验证失败")
                raise ValueError("验证码错误")

            # 执行登录
            print("[INFO] 验证码验证通过，开始执行登录")
            login_data = {
                "username": username,
                "password": password,
                "verificationCode": captcha,
                "deviceModel": "Windows",
                "deviceType": 99991001,
                "platformForwarding": 10041002
            }
            
            print(f"[INFO] 登录请求URL: {self.login_api_url}")
            print(f"[INFO] 登录请求数据: {login_data}")
            response = self.session.post(self.login_api_url, 
                                      headers=self.headers, 
                                      json=login_data)
            print(f"[INFO] 登录响应状态码: {response.status_code}")
            print(f"[INFO] 登录响应内容: {response.text}")

            if response.status_code == 200 and response.json().get('success'):
                print("[INFO] 登录成功")
                self.storage.save_credentials(username, password, self.remember_var.get())
                #保存cookies以备后续使用
                try:
                    self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
                    print("[INFO] Cookies保存成功")
                except Exception as e:
                    print(f"[WARNING] 保存cookies失败: {e}")
                # 设置登录成功的标志
                self.login_success =True

                # 取消所有待执行的定时任务
                for after_id in self.root.tk.call('after', 'info'):
                    self.root.after_cancel(after_id)

                self.root.destroy()
                
                # # 登录成功后，创建主窗口和MainApp实例
                # print("[INFO] 启动主应用程序")
                # from main_app import MainApplication
                # main_root = tk.Tk()  # 这是主应用程序的根窗口
                # main_root.state('zoomed')
                # app_main = MainApplication(main_root, self.session)
                # # 调用main_root.mainloop()启动主应用程序的事件循环
                # # main_root是Tk实例，具有mainloop()方法
                # try:
                #     app_main.root.mainloop()
                # except Exception as e:
                #     print(f"[ERROR] 主应用程序运行出错: {e}")
                # finally:
                #     # 确保正确清理资源
                #     try:
                #         app_main.destroy()
                #     except Exception:
                #         # 如果app_main已经销毁或出错，忽略
                #         pass
            else:
                error_msg = response.json().get('errorMsg', '未知错误')
                print(f"[ERROR] 登录失败 - 错误信息: {error_msg}")
                raise ValueError(error_msg)

        except Exception as e:
            self.login_attempts += 1
            print(f"[ERROR] 登录过程中发生异常 - 错误信息: {str(e)}")
            print(f"[ERROR] 错误详情: {traceback.format_exc()}")
            messagebox.showerror("登录失败", str(e))
            # 只有在登录窗口仍然存在时才刷新验证码
            if self.root.winfo_exists():
                self._refresh_captcha()
            print(f"[INFO] 登录尝试次数: {self.login_attempts}")
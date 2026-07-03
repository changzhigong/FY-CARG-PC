import tkinter as tk
from login_app import LoginApp
# # from main_app import MainApplication
# # # def main():
# # #     """应用程序主入口"""
# # #     # 创建登录窗口
# # #     login_root = tk.Tk()
# # #     login_app = LoginApp(login_root)
# # #     login_root.mainloop()
    
# # #     # 登录窗口关闭后，如果需要可以在这里处理其他逻辑
# # #     # 例如检查是否登录成功，然后决定是否启动主应用程序
# # def main():
# #     """应用程序主入口"""
# #     while True:
# #         # 创建登录窗口
# #         login_root = tk.Tk()
# #         login_app = LoginApp(login_root)
# #         login_root.mainloop()
        
# #         # 检查是否有会话信息，如果有则启动主应用程序
# #         if hasattr(login_app, 'session') and login_app.session:
# #             # 创建主应用程序窗口
# #             main_root = tk.Tk()
# #             main_app = MainApplication(main_root, login_app.session)
# #             main_root.mainloop()
# #         else:
# #             # 如果没有会话信息，退出程序
# #             break
# def main():
#     """应用程序主入口"""
#     while True:
#         # 创建登录窗口
#         login_root = tk.Tk()
#         login_app = LoginApp(login_root)
#         login_root.mainloop()
        
#         # 登录窗口关闭后，检查是否登录成功
#         if hasattr(login_app, 'login_success') and login_app.login_success:
#             # 登录成功，启动主应用程序
#             from main_app import MainApplication
#             main_root = tk.Tk()
#             main_app = MainApplication(main_root, login_app.session)
#             main_root.state('zoomed')
#             main_root.mainloop()
#         else:
#             # 用户关闭了登录窗口或登录失败退出，结束程序
#             break
def main():
    """应用程序主入口"""
    while True:
        # 创建登录窗口
        login_root = tk.Tk()
        login_app = LoginApp(login_root)
        login_root.mainloop()
        
        # 登录窗口关闭后，检查是否登录成功
        if hasattr(login_app, 'login_success') and login_app.login_success:
            # 登录成功，启动主应用程序
            from main_app import MainApplication
            main_root = tk.Tk()
            main_app = MainApplication(main_root, login_app.session)
            main_root.state('zoomed')
            try:
                main_root.mainloop()
            except Exception as e:
                print(f"[ERROR] 主应用程序运行出错: {e}")
            finally:
                # 确保正确清理资源
                try:
                    main_app.destroy()
                except Exception:
                    # 如果main_app已经销毁或出错，忽略
                    pass
        else:
            # 用户关闭了登录窗口或登录失败退出，结束程序
            break
if __name__ == "__main__":
    main()

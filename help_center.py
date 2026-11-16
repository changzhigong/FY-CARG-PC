# -*- coding: utf-8 -*-
"""帮助中心（关于软件 / 检查更新 / 使用帮助）

对齐 fycarg-pda 安卓端 src/views/HelpPage.vue 的信息架构：
- 关于软件：应用名 / 副标题 / 版本号 / 单位 / 联系方式 / 版权
- 检查更新：当前版本 + 「检查更新」按钮；发现新版本时展示版本号、更新内容与下载按钮。
  更新逻辑与安卓同款（GitHub Releases API，见 update_checker.py），仅发布仓库与安装包资产不同。
  下载在软件内完成（见 update_downloader.py）：桌面落地、断点续传、进度/取消，
  不调用系统浏览器；UI 更新一律 controller.after(0, ...) 回主线程。
- 使用帮助：按桌面端实际菜单（快捷操作 / 仓库理货 / 库内作业 / 仓储查询 / 报销管理 /
  内部领用 / 其他出入库管理 / 采购入库 / 打印）整理的可折叠条目。

本页无登录会话依赖；检查更新走公开 GitHub API（不用 dms 会话/Header）。
"""

import os
import threading
import webbrowser

import tkinter as tk
from tkinter import ttk, messagebox

from base_page import BasePage
from app_version import (APP_NAME, APP_SUBTITLE, APP_VERSION, APP_BUILD_DATE,
                         APP_COMPANY, APP_AUTHOR, APP_CONTACT, APP_GITHUB,
                         APP_COPYRIGHT, get_version_string)
from update_checker import (clear_update_cache, check_for_update,
                            _load_config_repo)
from update_downloader import (default_download_dir, safe_filename,
                               download_file, launch_installer, reveal_in_folder)

# 使用帮助条目：(标题, [段落…])  —— 对齐桌面端已上线的菜单集合
HELP_SECTIONS = [
    ("首页与登录", [
        "双击桌面图标启动后先登录 dms 账号；登录态失效（被顶下线）会提示并退回登录窗。",
        "首页用于日常跳转；顶部标签栏即各业务模块，悬停弹出子菜单。",
    ]),
    ("快捷操作", [
        "送货日报：按仓库与日期生成送货清单 Excel。",
        "财务日报：汇总出库/费用类财务日报数据。",
    ]),
    ("仓库理货", [
        "出库单管理（原「出库管理」）：查询出库单、查看明细、生成拣货单。",
        "拣货单管理（原「一键发运」）：拣货单查询（支持拣货单号 / 出库单号 / 订单号 / "
        "产品编码 / 产品名称 / 客户名称快捷搜索、发运起止日期），拣货保存与完成、"
        "批量一键发运、打印预览。",
        "发运单管理：按发运单号 / 发货单号 / 客户 / 仓库 / 出库类型 / 发运状态 / "
        "打印状态 / 发运起止日期 / 产品等查询发运单，双击行看完整字段，"
        "导出 Excel 与「{仓库}送货车辆.xlsx」报表；为只读查询页，"
        "新增发运 / 发运 / 打印在安卓端仍是占位且 HAR 无保存报文，故未接通。",
    ]),
    ("库内作业", [
        "调拨入库：录入实际入库库位/数量（可拆行、部分入库），暂存或入库；支持签收与打印。",
        "调拨申请：新建/编辑调拨申请单（选调出调入仓、配件、申请数量、入库库位），保存或提交，可删除/导出。",
        "移库管理：新建移库单（移库人、移入库位、移库数量），保存或提交，可查看移库记录。",
    ]),
    ("仓储查询", [
        "库存冻结查询：按仓库/商品查询冻结明细。",
        "装箱明细查询：按仓库/货箱/备件查询装箱明细。",
        "账单查询：按日期查询账单及开票/核销状态，可导出 Excel。",
        "销售明细：按多条件查询备件销售明细。",
        "出入库流水记录：按仓库/单据号/备件查询出入库流水。",
        "调拨明细查询：按调出/调入方、状态、日期查询调拨明细。",
    ]),
    ("报销管理", [
        "报销管理：填写费用明细（类型、金额、备注、往来单位/供应商），保存草稿或提交审批；可上传附件。",
        "报销审核：查看待我审核单据，通过/驳回，查看审批轨迹。",
        "其他支付管理：非报销类的付款申请，流程同报销管理。",
    ]),
    ("内部领用", [
        "内部领用：新建/编辑领用单，添加明细（产品、数量、移出库位），保存、提交或作废。",
        "部门审核：查看待我审核的领用单，通过/驳回并填审核意见，查看审批轨迹。",
    ]),
    ("其他出入库管理", [
        "其他入库审核：审核其他入库单（免费赠品、客户投诉退货等），可打印预览、填入库库位后通过/驳回。",
        "报损出库申请：填报损出库单（选配件、移出库位、报损原因、附件），保存或提交，仅待提交/审核驳回可改。",
        "其它出库审核：财务三级审核其它出库单（默认采购退货出库），查主单/明细/操作日志/附件，通过或驳回；仅「待审核」可审，驳回须填审核意见。支持打印预览与明细导出。",
    ]),
    ("采购入库", [
        "到货签收：按采购发运单签收，支持批量签收与明细查看。",
        "入库上架：采购入库单分配上架库位、录入实际入库数量后提交上架。",
    ]),
    ("打印功能", [
        "本机打印：需在电脑启动 CLodop（localhost:8000），默认打印机 EPSON LQ-630K，A4/连续纸。",
        "移动端打印：PDA 与电脑同一局域网，电脑端运行 LodopUdpBridge 打印桥后即可在 PDA 发起打印。",
        "支持打印：拣货单、调拨单/上架单、内部领用单、其他入库单、报损出库单、其它出库单。",
    ]),
    ("配置管理", [
        "首次使用请在「配置管理」里维护仓库与员工选项，页面需输入配置密码。",
    ]),
    ("关于更新", [
        "检查更新通过 GitHub Releases 对比版本号，发现新版本后跳浏览器下载 Windows 安装包。",
        "建议定期检查更新以获取最新修复与功能。",
    ]),
]


class HelpCenterPage(BasePage):
    """帮助中心页面（关于软件 / 检查更新 / 使用帮助）"""

    def __init__(self, parent, controller):
        self.checking = False
        self.has_update = False
        self.release_info = None
        self.latest_version = ''
        self.downloading = False
        self.download_cancel = None   # threading.Event，置位取消下载
        self._help_expanded = {}   # 条目名 -> bool
        super().__init__(parent, controller)

    # ---------------------------------------------------------------- 界面
    def create_widgets(self):
        outer = tk.Frame(self.content_frame, bg="#f0f0f0")
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.canvas = tk.Canvas(outer, bg="#f0f0f0", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body = tk.Frame(self.canvas, bg="#f0f0f0")
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        # 鼠标滚轮
        self.canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

        self._build_about(self.body)
        self._build_update(self.body)
        self._build_help(self.body)

    def _on_wheel(self, event):
        # 页面被隐藏（grid_remove 切到其它页）时不再滚动，避免全局滚轮串扰其它页面
        try:
            if not self.winfo_viewable():
                return
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        except tk.TclError:
            pass

    # ---------------------------------------------- 关于软件
    def _build_about(self, parent):
        card = tk.Frame(parent, bg="#ffffff", highlightthickness=0)
        card.pack(fill=tk.X, padx=10, pady=(10, 8))
        info = tk.Frame(card, bg="#ffffff")
        info.pack(padx=16, pady=16)
        tk.Label(info, text=APP_NAME, bg="#ffffff", fg="#323233",
                 font=("微软雅黑", 20, "bold")).pack()
        tk.Label(info, text=APP_SUBTITLE, bg="#ffffff", fg="#969799",
                 font=("微软雅黑", 10)).pack(pady=(2, 6))
        tk.Label(info, text=get_version_string(), bg="#ffffff", fg="#fa8c16",
                 font=("微软雅黑", 11, "bold")).pack()
        tk.Label(info, text=APP_COMPANY, bg="#ffffff", fg="#646566",
                 font=("微软雅黑", 10)).pack(pady=(4, 0))
        tk.Label(info, text="GitHub: {} ｜ 联系: {}".format(APP_GITHUB, APP_CONTACT),
                 bg="#ffffff", fg="#969799", font=("微软雅黑", 9)).pack(pady=(2, 0))
        tk.Label(info, text=APP_COPYRIGHT, bg="#ffffff", fg="#c8c9cc",
                 font=("微软雅黑", 8)).pack(pady=(6, 0))

    # ---------------------------------------------- 检查更新
    def _build_update(self, parent):
        box = tk.LabelFrame(parent, text="更新", bg="#f0f0f0",
                            font=("微软雅黑", 10, "bold"))
        box.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=4)

        row1 = tk.Frame(box, bg="#f0f0f0")
        row1.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(row1, text="当前版本：", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Label(row1, text=get_version_string(), bg="#f0f0f0",
                 fg="#1989fa", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(row1, text="检查更新", bg="#f0f0f0",
                 fg="#646566", font=("微软雅黑", 9)).pack(side=tk.RIGHT)

        row2 = tk.Frame(box, bg="#f0f0f0")
        row2.pack(fill=tk.X, padx=10, pady=(0, 2))
        self.check_btn = tk.Button(row2, text="检查更新", command=self.do_check_update,
                                   bg="#fa8c16", fg="white", padx=18, pady=5, bd=0,
                                   font=("微软雅黑", 10, "bold"))
        self.check_btn.pack(side=tk.LEFT, pady=2)
        self.repo_hint_var = tk.StringVar(value="版本来源：GitHub Releases（{}）".format(
            _load_config_repo()))
        tk.Label(row2, textvariable=self.repo_hint_var, bg="#f0f0f0",
                 fg="#969799", font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=12)

        # 检查结果区（动态重建）
        self.result_frame = tk.Frame(box, bg="#f0f0f0")
        self.result_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

    def _clear_result(self):
        for w in self.result_frame.winfo_children():
            w.destroy()

    def do_check_update(self):
        if self.checking or self.downloading:
            return
        self.checking = True
        self.check_btn.config(text="检查中…", state=tk.DISABLED)
        self._clear_result()
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        clear_update_cache()
        result = check_for_update()
        self.controller.after(0, lambda: self._apply_result(result))

    def _apply_result(self, result):
        self.checking = False
        self.check_btn.config(text="检查更新", state=tk.NORMAL)
        if result.get('error'):
            err = result['error']
            hint = ''
            if '404' in str(err):
                hint = ("\n\n提示：未找到 changzhigong/FY-CARG-PC 的 Release（404）。\n"
                        "可能是网络不可达，或该仓库暂无 Release/已设为私有；\n"
                        "若仓库恢复私有，可在 user_config.json 配置 \"update_token\" "
                        "或设置环境变量 FYCARG_UPDATE_TOKEN 后重试。")
            messagebox.showerror(
                "检查更新失败",
                "请检查网络后重试。\n\n原因：{}{}".format(err, hint))
            return
        if not result.get('hasUpdate'):
            messagebox.showinfo("检查更新", "已是最新版本")
            return
        release = result.get('releaseInfo') or {}
        self.release_info = release
        self.latest_version = result.get('latestVersion') or ''
        self._clear_result()
        box = tk.Frame(self.result_frame, bg="#ecf5ff")
        box.pack(fill=tk.X, pady=4)
        tk.Label(box, text="发现新版本 {}，建议立即更新".format(self.latest_version),
                 bg="#ecf5ff", fg="#1989fa", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
        if release.get('body'):
            tk.Label(box, text="{} 更新内容".format(self.latest_version),
                     bg="#ecf5ff", fg="#646566", font=("微软雅黑", 9, "bold")).pack(anchor="w", padx=8)
            tk.Label(box, text=release['body'], bg="#ecf5ff", fg="#646566",
                     font=("微软雅黑", 9), justify="left", wraplength=820,
                     anchor="w").pack(anchor="w", padx=14)
        line = tk.Frame(box, bg="#ecf5ff")
        line.pack(fill=tk.X, padx=8, pady=(4, 6))
        asset_url = release.get('assetUrl') or ''
        if asset_url:
            self.download_btn = tk.Button(line, text="下载并安装最新版本", bg="#ee0a24", fg="white",
                                          bd=0, padx=12, pady=3,
                                          command=lambda: self.start_download(release))
            self.download_btn.pack(side=tk.LEFT)
            size_mb = (release.get('assetSize') or 0) / 1024.0 / 1024.0
            hint = '软件内直接下载到桌面，支持断点续传'
            if size_mb >= 0.1:
                hint += '（约 {:.1f} MB）'.format(size_mb)
            tk.Label(line, text=hint, bg="#ecf5ff", fg="#969799",
                     font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=8)
            # 备用入口：无内置下载器能力时仍可从浏览器 manual 下载
            tk.Button(line, text="用浏览器下载", bg="#ecf5ff", fg="#1989fa",
                      bd=0, font=("微软雅黑", 8),
                      command=lambda: self.open_release(release)).pack(side=tk.RIGHT)
        else:
            tk.Button(line, text="前往 GitHub 发布页", bg="#ee0a24", fg="white",
                      bd=0, padx=12, pady=3,
                      command=lambda: self.open_release(release)).pack(side=tk.LEFT)
            tk.Label(line, text="该版本暂未附带 Windows 安装包资产，将打开发布页",
                     bg="#ecf5ff", fg="#969799", font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=8)

        # 下载进度区（动态重建）
        self.progress_frame = tk.Frame(box, bg="#ecf5ff")
        self.progress_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

    # ---------------------------------------------- 应用内下载
    def start_download(self, release):
        """在软件内下载安装包（后台线程 + 主线程回调 UI）"""
        if self.downloading:
            return
        url = release.get('assetUrl') or ''
        if not url:
            messagebox.showinfo("提示", "该版本暂无安装包下载地址")
            return
        filename = safe_filename(release.get('assetName'),
                                 fallback='FY-CARG-PC-v{}.exe'.format(
                                     (release.get('version') or 'update').lstrip('v')))
        dest_path = os.path.join(default_download_dir(), filename)

        self.downloading = True
        self.download_cancel = threading.Event()
        if getattr(self, 'download_btn', None) is not None:
            try:
                self.download_btn.config(state=tk.DISABLED)
            except tk.TclError:
                pass
        self._clear_progress()
        self._render_progress(dest_path)

        threading.Thread(target=self._download_thread,
                         args=(url, dest_path, int(release.get('assetSize') or 0)),
                         daemon=True).start()

    def _clear_progress(self):
        frame = getattr(self, 'progress_frame', None)
        if frame is None:
            return
        try:
            for w in frame.winfo_children():
                w.destroy()
        except tk.TclError:
            pass

    def _render_progress(self, dest_path):
        """在进度区渲染进度条 / 百分比 / 取消按钮"""
        self._clear_progress()
        frame = self.progress_frame
        self.pb_var = tk.DoubleVar(value=0)
        self.progress_label_var = tk.StringVar(value="准备下载：{}".format(os.path.basename(dest_path)))
        tk.Label(frame, textvariable=self.progress_label_var, bg="#ecf5ff",
                 fg="#646566", font=("微软雅黑", 9)).pack(anchor="w", pady=(2, 2))
        self.pb = ttk.Progressbar(frame, variable=self.pb_var, maximum=100, length=420)
        self.pb.pack(side=tk.LEFT, pady=(0, 4))
        self.cancel_btn = tk.Button(frame, text="取消", bg="#ffffff", fg="#646566",
                                    bd=0, font=("微软雅黑", 9),
                                    command=self.cancel_download)
        self.cancel_btn.pack(side=tk.LEFT, padx=8, pady=(0, 4))

    def _on_progress(self, downloaded, total, percent, resumed):
        """下载线程调用：只发信号，UI 更新切回主线程"""
        self.controller.after(0, lambda: self._apply_progress(downloaded, total, percent, resumed))

    def _apply_progress(self, downloaded, total, percent, resumed):
        try:
            if self.pb_var is not None:
                self.pb_var.set(percent)
            tag = '（断点续传）' if resumed else ''
            if total:
                self.progress_label_var.set(
                    "下载中{tag}：{:.1f} / {:.1f} MB  ({:.0f}%)".format(
                        tag, downloaded / 1048576.0, total / 1048576.0, percent))
            else:
                self.progress_label_var.set("下载中{tag}：{:.1f} MB".format(
                    tag, downloaded / 1048576.0))
        except (tk.TclError, AttributeError):
            pass

    def _download_thread(self, url, dest_path, expected_size):
        try:
            result = download_file(
                url, dest_path, expected_size=expected_size,
                on_progress=self._on_progress, cancel_event=self.download_cancel)
        except Exception as e:
            result = {'ok': False, 'error': str(e), 'path': dest_path,
                      'downloaded': 0, 'total': expected_size}
        self.controller.after(0, lambda: self._download_done(result))

    def _download_done(self, result):
        self.downloading = False
        if getattr(self, 'download_btn', None) is not None:
            try:
                self.download_btn.config(state=tk.NORMAL)
            except tk.TclError:
                pass
        path = result.get('path') or ''
        if result.get('ok'):
            self._clear_progress()
            tk.Label(self.progress_frame, text="✓ 已下载到：{}".format(path),
                     bg="#ecf5ff", fg="#07c160", font=("微软雅黑", 9),
                     wraplength=760, justify="left").pack(anchor="w")
            answer = messagebox.askyesno(
                "下载完成",
                "安装包已下载到：\n{}\n\n是否立即安装？\n"
                "（将启动安装程序，安装过程中本程序可关闭）".format(path))
            if answer:
                ok, err = launch_installer(path)
                if not ok:
                    messagebox.showerror("启动安装失败", err)
            else:
                ok, err = reveal_in_folder(path)
                if not ok:
                    messagebox.showinfo("提示", "安装包位置：\n{}".format(path))
        else:
            err = result.get('error') or '未知错误'
            if '取消' in err:
                self._clear_progress()
                tk.Label(self.progress_frame, text="已取消下载（断点已保留，下次可续传）",
                         bg="#ecf5ff", fg="#969799", font=("微软雅黑", 9)).pack(anchor="w")
            else:
                self._clear_progress()
                tk.Label(self.progress_frame, text="下载失败：{}".format(err),
                         bg="#ecf5ff", fg="#ee0a24", font=("微软雅黑", 9),
                         wraplength=760, justify="left").pack(anchor="w")
                tk.Button(self.progress_frame, text="重试", bg="#ffffff", fg="#1989fa",
                          bd=0, font=("微软雅黑", 9),
                          command=lambda: self.start_download(self.release_info or {})).pack(anchor="w")
                tk.Button(self.progress_frame, text="用浏览器下载", bg="#ffffff", fg="#969799",
                          bd=0, font=("微软雅黑", 8),
                          command=lambda: self.open_release(self.release_info or {})).pack(anchor="w")

    def cancel_download(self):
        if self.download_cancel is not None:
            self.download_cancel.set()
        try:
            if getattr(self, 'cancel_btn', None) is not None:
                self.cancel_btn.config(state=tk.DISABLED, text="取消中…")
        except tk.TclError:
            pass

    def open_release(self, release):
        """备用入口：用系统浏览器打开发布页或安装包直链"""
        url = release.get('assetUrl') or release.get('htmlUrl') or ''
        if not url:
            messagebox.showinfo("提示", "暂无可用的下载地址")
            return
        try:
            webbrowser.open(url)
            messagebox.showinfo("已打开", "已在浏览器打开：\n" + url)
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    # ---------------------------------------------- 使用帮助
    def _build_help(self, parent):
        box = tk.LabelFrame(parent, text="使用帮助", bg="#f0f0f0",
                            font=("微软雅黑", 10, "bold"))
        box.pack(fill=tk.X, padx=10, pady=(0, 10), ipady=4)
        self._help_rows = {}
        for title, paras in HELP_SECTIONS:
            self._help_expanded[title] = False
            row = tk.Frame(box, bg="#ffffff")
            row.pack(fill=tk.X, padx=8, pady=2)
            toggle = tk.Button(
                row, text="▶  {}".format(title), command=lambda t=title: self._toggle_help(t),
                bg="#ffffff", fg="#323233", anchor="w", relief=tk.FLAT,
                font=("微软雅黑", 10, "bold"), padx=6)
            toggle.pack(fill=tk.X)
            holder = tk.Frame(row, bg="#ffffff")
            holder.pack_forget()
            row._holder = holder
            row._toggle = toggle
            self._help_rows[title] = row

    def _toggle_help(self, title):
        row = self._help_rows.get(title)
        if row is None:
            return
        holder = row._holder
        toggle = row._toggle
        expanded = self._help_expanded.get(title, False)
        self._help_expanded[title] = not expanded
        if expanded:
            for w in holder.winfo_children():
                w.destroy()
            holder.pack_forget()
            toggle.config(text="▶  {}".format(title))
        else:
            for para in dict(HELP_SECTIONS)[title]:
                tk.Label(holder, text="• " + para, bg="#ffffff",
                         fg="#666666", font=("微软雅黑", 9), justify="left",
                         anchor="w", wraplength=920).pack(fill=tk.X, padx=18, pady=1)
            holder.pack(fill=tk.X, after=toggle)
            toggle.config(text="▼  {}".format(title))

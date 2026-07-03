import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from base_page import BasePage
# WebSocket配置
WEBSOCKET_CONFIG = {
    "heartbeat_interval": 30,  # 心跳间隔(秒)
    "reconnect_delay": 5,      # 重连延迟(秒)
    "max_reconnect_attempts": 5,
    "connection_timeout": 10   # 连接超时(秒)
}


class ConfigPage(BasePage):
    """配置管理页面：可视化编辑 warehouse_config.json"""
    def __init__(self, parent, controller):
        self.loaded_config = None
        super().__init__(parent, controller)
        self.controller = controller

    def create_widgets(self):
        # 读取全局已加载配置
        try:
            from main_app import loaded_config
            self.loaded_config = loaded_config or {}
        except ImportError:
            # 兜底读取文件
            self.loaded_config = self.load_config("warehouse_config.json") or {}

        # 顶部：选择仓库
        top_frame = ttk.LabelFrame(self.content_frame, text="仓库选择")
        top_frame.pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(top_frame, text="仓库名称").pack(side=tk.LEFT, padx=6)
        warehouses = list(self.loaded_config.get("WAREHOUSE_OPTIONS", {}).keys())
        self.warehouse_var = tk.StringVar(value=warehouses[0] if warehouses else "")
        self.warehouse_cb = ttk.Combobox(top_frame, textvariable=self.warehouse_var, values=warehouses, state="readonly", width=20)
        self.warehouse_cb.pack(side=tk.LEFT, padx=6)
        ttk.Button(top_frame, text="载入该仓库", command=self.load_selected_warehouse).pack(side=tk.LEFT, padx=6)

        # 分区：基础配置（WAREHOUSE_OPTIONS + DRIVER_OPTIONS）
        base_frame = ttk.LabelFrame(self.content_frame, text="仓库基础配置")
        base_frame.pack(fill=tk.X, padx=10, pady=8)

        # 仓库编码
        ttk.Label(base_frame, text="仓库编码(WAREHOUSE_OPTIONS)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.wh_code_var = tk.StringVar()
        self.wh_code_entry = ttk.Entry(base_frame, textvariable=self.wh_code_var, width=15)
        self.wh_code_entry.grid(row=0, column=1, sticky="w", padx=6, pady=6)

        # 司机选项 DRIVER_OPTIONS（单司机或多司机，使用逗号分隔）
        ttk.Label(base_frame, text="司机(单/多，逗号分隔)").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.driver_options_text = tk.Text(base_frame, height=3, width=40)
        self.driver_options_text.grid(row=1, column=1, sticky="w", padx=6, pady=6)

        # 分区：人员配置（warehouse_data，按4组，每行用逗号分隔）
        people_frame = ttk.LabelFrame(self.content_frame, text="人员配置（warehouse_data）")
        people_frame.pack(fill=tk.BOTH, padx=10, pady=8)
        ttk.Label(people_frame, text="四组人员，每行一组，成员用逗号分隔").pack(anchor="w", padx=6, pady=3)
        self.warehouse_people_text = tk.Text(people_frame, height=8)
        self.warehouse_people_text.pack(fill=tk.BOTH, padx=6, pady=6)

        # 分区：车辆配置（warehouse_vehicle_data：每行一个车牌或"自提"）
        vehicle_frame = ttk.LabelFrame(self.content_frame, text="车辆配置（warehouse_vehicle_data）")
        vehicle_frame.pack(fill=tk.BOTH, padx=10, pady=8)
        ttk.Label(vehicle_frame, text="每行一个车辆编号或'自提'").pack(anchor="w", padx=6, pady=3)
        self.warehouse_vehicle_text = tk.Text(vehicle_frame, height=6)
        self.warehouse_vehicle_text.pack(fill=tk.BOTH, padx=6, pady=6)

        # 分区：司机电话（driver_data：每行"姓名,手机号"）
        driver_frame = ttk.LabelFrame(self.content_frame, text="司机电话（driver_data，全局）")
        driver_frame.pack(fill=tk.BOTH, padx=10, pady=8)
        ttk.Label(driver_frame, text="每行格式：姓名,手机号").pack(anchor="w", padx=6, pady=3)
        self.driver_data_text = tk.Text(driver_frame, height=8)
        self.driver_data_text.pack(fill=tk.BOTH, padx=6, pady=6)

        # 操作按钮
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="载入全局司机电话", command=self.load_driver_data_global).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="保存当前仓库配置", command=self.save_current_warehouse).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="保存全部配置", command=self.save_all_config).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="锁定配置页", command=self.lock_config_page).pack(side=tk.RIGHT, padx=6)

        # 初始加载当前选中的仓库
        self.load_selected_warehouse()
        self.load_driver_data_global()

    # 载入选中仓库数据到UI
    def load_selected_warehouse(self):
        wh = self.warehouse_var.get()
        cfg = self.loaded_config or {}

        # 仓库编码
        wh_code = str(cfg.get("WAREHOUSE_OPTIONS", {}).get(wh, ""))
        self.wh_code_var.set(wh_code)

        # DRIVER_OPTIONS：可能是字符串或列表
        drv_opt = cfg.get("DRIVER_OPTIONS", {}).get(wh, "")
        if isinstance(drv_opt, list):
            drv_str = ",".join(drv_opt)
        else:
            drv_str = str(drv_opt) if drv_opt else ""
        self.driver_options_text.delete("1.0", tk.END)
        self.driver_options_text.insert(tk.END, drv_str)

        # warehouse_data：四组列表
        groups = cfg.get("warehouse_data", {}).get(wh, [])
        lines = []
        for i in range(4):
            group = groups[i] if i < len(groups) else []
            lines.append(",".join(group))
        self.warehouse_people_text.delete("1.0", tk.END)
        self.warehouse_people_text.insert(tk.END, "\n".join(lines))

        # warehouse_vehicle_data：每行一个
        vehicles = cfg.get("warehouse_vehicle_data", {}).get(wh, [])
        self.warehouse_vehicle_text.delete("1.0", tk.END)
        self.warehouse_vehicle_text.insert(tk.END, "\n".join(vehicles))

    # 载入全局司机电话到UI
    def load_driver_data_global(self):
        drv_data = (self.loaded_config or {}).get("driver_data", {})
        lines = [f"{name},{phone}" for name, phone in drv_data.items()]
        self.driver_data_text.delete("1.0", tk.END)
        self.driver_data_text.insert(tk.END, "\n".join(lines))

    # 保存仅当前仓库相关配置
    def save_current_warehouse(self):
        wh = self.warehouse_var.get()
        cfg = self.loaded_config or {}

        # 仓库编码
        code_text = self.wh_code_var.get().strip()
        if code_text:
            try:
                cfg.setdefault("WAREHOUSE_OPTIONS", {})[wh] = int(code_text)
            except ValueError:
                messagebox.showerror("错误", "仓库编码必须为整数")
                return

        # DRIVER_OPTIONS
        drv_text = self.driver_options_text.get("1.0", tk.END).strip()
        if drv_text:
            if "," in drv_text:
                cfg.setdefault("DRIVER_OPTIONS", {})[wh] = [x.strip() for x in drv_text.split(",") if x.strip()]
            else:
                cfg.setdefault("DRIVER_OPTIONS", {})[wh] = drv_text

        # warehouse_data 四行
        people_text = self.warehouse_people_text.get("1.0", tk.END).strip()
        groups_lines = people_text.splitlines()
        new_groups = []
        for i in range(4):
            line = groups_lines[i] if i < len(groups_lines) else ""
            new_groups.append([x.strip() for x in line.split(",") if x.strip()])
        cfg.setdefault("warehouse_data", {})[wh] = new_groups

        # 车辆
        vehicle_text = self.warehouse_vehicle_text.get("1.0", tk.END).strip()
        vehicles = [x.strip() for x in vehicle_text.splitlines() if x.strip()]
        cfg.setdefault("warehouse_vehicle_data", {})[wh] = vehicles

        # 写回文件
        self._write_config_to_file(cfg)
        messagebox.showinfo("成功", f"已保存仓库[{wh}]相关配置")

    # 保存全局司机电话
    def save_all_config(self):
        cfg = self.loaded_config or {}

        # 更新全局 driver_data
        lines = self.driver_data_text.get("1.0", tk.END).strip().splitlines()
        new_driver_data = {}
        for line in lines:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2:
                messagebox.showerror("错误", f"司机电话行格式不正确：{line}（应为 姓名,手机号）")
                return
            name, phone = parts
            new_driver_data[name] = phone
        cfg["driver_data"] = new_driver_data

        # 同步当前仓库的基础/人员/车辆（避免遗漏）
        self.save_current_warehouse()

        # 再次写回（确保 driver_data 覆盖）
        self._write_config_to_file(cfg)
        messagebox.showinfo("成功", "已保存全部配置")

    def lock_config_page(self):
        """手动锁定配置页并返回首页内容"""
        try:
            # 重置访问状态
            self.controller._config_unlocked = False
        except Exception:
            pass
        # 返回首页内容显示（不切换标签，但内容切至首页）
        try:
            self.controller.show_frame("HomePage")
            messagebox.showinfo("已锁定", "配置页面已锁定，需重新输入密码方可进入。")
        except Exception as e:
            messagebox.showinfo("已锁定", "配置页面已锁定。")

    def _write_config_to_file(self, cfg):
        try:
            with open("warehouse_config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("写入失败", str(e))

    @staticmethod
    def load_config(file_path):
        """从JSON文件加载配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

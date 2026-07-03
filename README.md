# FY-CARG-PC

富阳 ERP 仓库管理桌面客户端 —— 针对汽车配件行业的多仓库协同管理工具。

## 概述

基于 Python Tkinter 构建的 Windows 桌面应用，对接 `xb.fy-carg.com` 后端 ERP 系统，为**郑州晖锦汽车配件有限公司**提供以下核心业务能力：

- 多仓库（10 个）出库管理与拣货
- 一键发运（拣货 → 发货一体化）
- 跨仓库调拨入库
- 送货日报 / 财务日报 Excel 导出
- 司机、车辆、人员配置管理

## 技术栈

| 领域 | 技术 |
|------|------|
| GUI | Tkinter + ttk（主题化组件） |
| HTTP | `requests` + `LWPCookieJar`（Cookie 持久化） |
| 加密 | `cryptography.fernet`（凭证安全存储） |
| Excel | `openpyxl`（读写.xlsx）、`xlrd`（兼容.xls） |
| 数据处理 | `pandas` |
| 图像 | `Pillow`（验证码渲染、首页图片） |
| WebSocket | `websocket-client`（登录状态监控，开发中） |

## 项目结构

```
FY-CARG-PC/
├── main.py                 # 程序入口，登录 → 主窗口流程控制
├── login_app.py            # 登录模块（验证码、凭证加密、Cookie 持久化）
├── main_app.py             # 主框架（菜单栏、页面路由、状态栏、Token 过期检测）
├── base_page.py            # 页面基类（统一布局容器）
│
├── home_page.py            # 首页（仪表盘）
├── outbound_manager.py     # 出库管理（拣货单生成与打印预览）
├── picking_shipping.py     # 一键发运（拣货 + 发货流程）
├── transfer_manager.py     # 调拨入库（跨仓库调拨作业）
├── deliver_report.py       # 送货日报（Excel 报表生成）
├── excel_data_processor.py # 财务日报（财务数据处理与导出）
├── config_manager.py       # 配置管理（仓库 / 司机 / 车辆 webGUI 编辑）
│
├── data_processor.py       # 数据获取与 Excel 处理工具类
├── tooltip_manager.py      # Treeview 控件悬停提示管理器
│
├── warehouse_config.json   # 仓库配置文件（仓库编码、司机、车辆信息）
├── user_config.json        # 用户凭证（加密存储，自动生成）
├── secret.key              # 加密密钥（自动生成）
│
├── test_websocket_monitor.py # WebSocket 监控模块单元测试
├── test.bat                # 启动脚本
│
└── .gitignore              # Git 忽略规则
```

## 功能模块

### 1. 登录系统

- 用户名 + 密码 + 图形验证码登录
- 验证码自动刷新，支持点击刷新
- 记住密码（Fernet 对称加密存储）
- Cookie 持久化（LWPCookieJar），减少重复登录
- Token 被顶下线自动检测与重登录

### 2. 首页

- 展示公司品牌图片
- 欢迎仪表盘

### 3. 出库管理

- 按仓库、日期范围查询待出库订单
- TreeView 表格展示，支持多选、悬停详情
- 拣货单生成与打印预览
- 出库状态动态计算与颜色标记

### 4. 一键发运

- 拣货单生成 → 发货确认一条龙
- 自动对接司机分配
- 批量操作支持

### 5. 调拨入库

- 跨仓库物料调拨申请
- 调拨入库确认
- Excel 调拨单导出（含格式化）

### 6. 送货日报

- 按日期 + 仓库查询送货数据
- 自动生成格式化 Excel 报表
- 支持多仓库汇总

### 7. 财务日报

- 按日期拉取各仓库财务数据
- Excel 自动格式化（合并单元格、样式、公式）
- 一键复制粘贴支持

### 8. 配置管理

- 密码保护的配置页面（默认密码：`admin123`，可在 `config_password.txt` 自定义）
- 可视化编辑仓库选项（名称/编码）
- 仓库人员分组管理（业务员、仓管、备货员、司机）
- 司机联系方式管理
- 仓库车辆配置

## 仓库清单

| 仓库名称 | 编码 | 所在城市 |
|----------|------|----------|
| 商丘库 | SQ | 商丘 |
| 郑州库 | ZZ | 郑州 |
| 西安库 | XA | 西安 |
| 兰州库 | LZ | 兰州 |
| 驻马店库 | ZMD | 驻马店 |
| 洛阳库 | LY | 洛阳 |
| 银川库 | YC | 银川 |
| 榆林库 | YL | 榆林 |
| 茶城库 | CC | （茶城） |
| 西安西郊库 | XAXJ | 西安 |

## 运行环境

### 系统要求

- Windows 10 / 11
- Python 3.8+
- 网络连接（需访问 `xb.fy-carg.com`）

### 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install requests cryptography Pillow pandas openpyxl xlrd tkcalendar websocket-client pyperclip
```

### 启动

```bash
python main.py
```

或双击 `test.bat`。

## 开发说明

### 添加新页面

1. 在 `base_page.py` 基类上创建新页面类
2. 在 `main_app.py` 的 `frame_classes` 字典中注册
3. 如需加入菜单，在 `create_menu()` 中添加对应选项

### API 约定

- 基础 URL：`https://xb.fy-carg.com/dmscloud.xxx/`
- 鉴权：登录后 Session Cookie 自动携带
- 分页：默认 `limit=500`，通过 `data.total` 判断是否还有更多数据

### 凭证安全

- 用户密码使用 Fernet 对称加密，密钥存储在 `secret.key`
- 生产环境建议将 `secret.key` 和 `config_password.txt` 加入 `.gitignore`

## License

内部使用工具，版权所有。

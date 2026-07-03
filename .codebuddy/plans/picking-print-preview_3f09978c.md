---
name: picking-print-preview
overview: 在拣货管理页面添加打印预览按钮，支持单选/多选拣货单，调用getPrintPickingList API获取数据，渲染HTML预览，并通过WebSocket连接CLodop(localhost:8000)直接打印到爱普生针式打印机。
todos:
  - id: add-print-preview-button
    content: 在 setup_action_buttons 方法中"批量一键发运"按钮旁边添加"打印预览"按钮
    status: completed
  - id: implement-open-preview-method
    content: 实现 open_print_preview 方法：校验选中项、调用 getPrintPickingList API 获取数据
    status: completed
    dependencies:
      - add-print-preview-button
  - id: implement-data-grouping-logic
    content: 实现数据分组逻辑：按 picking_order_no 分组、计算合计数量/金额、合并开单人
    status: completed
    dependencies:
      - implement-open-preview-method
  - id: build-html-template
    content: 构建 HTML 模板生成方法：客户信息区 + 产品明细表 + 汇总行 + 签名区
    status: completed
    dependencies:
      - implement-data-grouping-logic
  - id: create-preview-window
    content: 创建 PrintPreviewWindow Toplevel 类：展示 HTML 预览内容和打印按钮
    status: completed
    dependencies:
      - build-html-template
  - id: implement-clodop-websocket-print
    content: 实现 CLodop WebSocket 打印功能：连接 localhost:8000，构造协议消息，发送打印任务
    status: completed
    dependencies:
      - create-preview-window
---

## 产品概述

在拣货管理页面（picking_shipping.py）新增"打印预览"功能按钮，支持单选或多选拣货单，发起 GET 请求获取打印数据，在独立窗口中渲染 HTML 预览表格，并通过 WebSocket 连接本地 CLodop 打印服务（localhost:8000）直接后台打印到 EPSON LQ-630K 针式打印机。

## 核心功能

- 在"批量一键发运"按钮旁边增加"打印预览"按钮，按钮样式统一
- 支持勾选一个或多个拣货单（复用 self.selected_items），未选择时弹窗提示
- 调用 getPrintPickingList API 获取拣货单明细数据（picking_order_nos 参数逗号分隔并加引号）
- 在 Tkinter Toplevel 窗口中渲染 HTML 打印预览，按拣货单号分组展示表格
- 表格列：品牌、产品名称、分类、产品编号、库位、数量、单价、金额
- 底部汇总行：合计数量、合计金额、开单人、拣货人、装箱人、客户签字区域
- 通过 WebSocket 连接 ws://127.0.0.1:8000/c_webskt/，按 CLodop 协议序列化 HTML 内容并直接发送打印
- 打印目标为针式打印机 EPSON LQ-630K，使用连续纸尺寸（220mm x 15mm）
- 预览窗口提供"打印"按钮直接触发后台打印，无需浏览器

## 技术栈选择

- **GUI 框架**: Tkinter（与现有项目一致）
- **HTTP 请求**: requests.Session（复用 self.controller.session）
- **WebSocket**: websocket-client 库
- **HTML 渲染**: Python 字符串模板拼接 + Tkinter Label/Text 控件显示
- **打印协议**: CLodop WebSocket 协议

## 实现方案

### 总体策略

在 `OneKeyProcessPage` 类中新增 `open_print_preview` 方法作为按钮回调，创建 `PrintPreviewWindow` 类（Toplevel 窗口），内部调用 API 获取数据后渲染 HTML 表格并展示。打印功能通过 Python `websocket` 库连接 localhost:8000 的 CLodop 服务，按 CLodop WebSocket 协议构造消息发送。

### CLodop WebSocket 协议实现

CLodop WebSocket 消息格式基于 `CLodopfuncs.js` 中 `wsDoPostDatas` 和 `createPostDataString` 方法：

**分隔符**: `\f\f` (两个换页符)

**消息结构**:

```
post:charset=丂\f\f
tid=TASKID\f\f
act=print\f\f
browseurl=PYTHON\f\f
top=\f\f
left=\f\f
width=\f\f
height=\f\f
printtask=拣货单打印\f\f
printerindex=EPSON LQ-630K ESC/P2\f\f
orient=1\f\f
pagewidth=220mm\f\f
pageheight=15mm\f\f
pagename=连续纸01\f\f
printcopies=1\f\f
itemcount=1\f\f
1_type=4\f\f
1_top=0\f\f
1_left=0\f\f
1_width=100%\f\f
1_height=100%\f\f
1_content=<url_encoded_html>\f\f
1_itemstylenames=\f\f
printmodenames=\f\f
printstyleclassnames=\f\f
```

- TASKID 使用时间戳生成
- HTML 内容需要 URL 编码（quote）
- 打印机名称为 "EPSON LQ-630K ESC/P2"
- 针式打印机使用连续纸：pagewidth=220mm, pageheight=15mm
- ADD_PRINT_HTM 对应的 type=4

### HTML 模板结构

参考 `componentsPrint-93df05b7.js` 的 Vue 模板 render 函数：

1. 顶部标题栏：logo 图片 + 公司简称 + 单据类型（销售清单/调拨清单）
2. 客户信息区：客户名称、联系人、单号、客户地址、电话、打印时间、出库仓库、物流公司、物流电话、配送方式、包装方式、结算方式、摘要
3. 产品明细表（border 表格）：品牌 | 产品名称 | 分类 | 产品编号 | 库位 | 数量 | 单价 | 金额
4. 汇总行：合计数量、合计金额
5. 底部签名区：开单人、拣货人、装箱人、客户签字、重(N)

## 实现细节

### 核心目录结构

```
c:/Users/Administrator/Desktop/test/
├── picking_shipping.py    # [MODIFY] 新增打印预览按钮、回调方法、PrintPreviewWindow 类
```

### 新增代码结构

#### 1. OneKeyProcessPage 类扩展

- 第2372行后：添加"打印预览"按钮 `tk.Button(parent, text="打印预览", command=self.open_print_preview, **btn_style1)`
- 新增方法 `open_print_preview(self)`：校验选中项、调用 API、创建 PrintPreviewWindow

#### 2. PrintPreviewWindow 类（新建在 ShippingWindow 类之前或之后）

- `__init__`: 接收父窗口、dataList、session 引用
- 创建 Toplevel 窗口，显示 HTML 预览内容
- 提供"打印"按钮触发 WebSocket 打印
- 方法：`build_html()` 生成打印 HTML、`print_via_clodop()` WebSocket 打印

#### 3. 关键依赖

- `import websocket` 用于 WebSocket 连接
- `from urllib.parse import quote` 用于 URL 编码 HTML 内容
- `import time`, `import hashlib` 用于生成 TASKID

### 数据分组逻辑

dataList 按 `picking_order_no` 分组：

- 第一项设置分组头信息（DEALER_NAME, linkman, phone, receive_address, WAREHOUSE_NAME, logistics_mode, packing_method, sett_method, remark, picking_by, created_by_name）
- 计算 `totalNum = sum(pick_num)`, `totalPrice = sum(pick_num * audit_price)`
- 合并 cashier（created_by_name 去重拼接）

### 分类映射

```python
CATEGORY_TWO_MAP = {
    90921001: "前挡",
    90921002: "后挡", 
    90921003: "侧窗",
    # ... 按需扩展
}
```

### 品牌处理

品牌"福耀玻璃"替换为"福耀"。

### 性能考量

- WebSocket 连接一次性建立，发送完毕后关闭
- HTML 内容较大时确保 URL 编码正确
- 预览窗口使用 Tkinter Text 控件显示 HTML（或使用简单表格控件展示纯文本预览）

### 日志与错误处理

- GET 请求失败时弹出错误提示
- WebSocket 连接失败时提示用户检查 CLodop 服务是否运行
- 无选中项时弹出警告
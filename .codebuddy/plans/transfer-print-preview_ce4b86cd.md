---
name: transfer-print-preview
overview: 在 transfer_manager.py 中实现调拨单打印预览功能：创建 TransferPrintPreviewWindow 类，替换占位的 print_preview 方法，使用 getPrintList API 获取打印数据，用 tkinterweb HtmlFrame 渲染 HTML 预览，支持 CLodop 打印。
todos:
  - id: add-preview-class
    content: 在 transfer_manager.py 中添加 TransferPrintPreviewWindow 类，包含 __init__（Toplevel窗口+按钮+预览容器）和 _render_preview（HtmlFrame渲染）方法
    status: completed
  - id: add-load-data
    content: 实现 _load_data 方法：调用 transferIn/getPrintList API 获取打印数据，对每个调拨单调用 inboundDetail_query 获取备注/指示库位
    status: completed
    dependencies:
      - add-preview-class
  - id: add-group-build-html
    content: 实现 _group_data（按transferNo分组+计算合计）和 _build_html（生成调入清单HTML表格）方法
    status: completed
    dependencies:
      - add-load-data
  - id: add-clodop-print
    content: 实现 print_via_clodop 方法，通过 WebSocket 连接 CLodop 发送打印任务（参考 picking_shipping.py）
    status: completed
    dependencies:
      - add-group-build-html
  - id: replace-button-handler
    content: 替换 TransferProcessPage.print_preview 占位方法，获取选中行 transferNos 并创建 TransferPrintPreviewWindow
    status: completed
    dependencies:
      - add-preview-class
---

## 用户需求

在 transfer_manager.py 调拨管理页面中，将"调拨单打印预览"按钮（第450行）的占位方法替换为真实的打印预览功能，参考 picking_shipping.py 的 PrintPreviewWindow 类和 Content.js 的调拨打印逻辑。

## 核心功能

- 点击"调拨单打印预览"按钮后，打开打印预览窗口
- 预览窗口使用 tkinterweb HtmlFrame 内嵌渲染 HTML 表格，支持完整的 table/CSS 布局
- 表格内容按调拨单号分组，每组显示：表头信息（调出仓库、调入仓库、单据号、开单人、上架人、摘要）+ 数据行（品牌、产品名称、分类、产品编码、入库库位、入库数量、备注）
- 通过 CLodop WebSocket 直接发送打印任务到针式打印机
- 数据通过 API `transferIn/getPrintList` 获取，并合并 `inboundDetail` 获取备注和指示库位

## 技术方案

### 实现策略

在 transfer_manager.py 中添加一个新的 `TransferPrintPreviewWindow` 类（独立顶层类，非内部类），完全参照 picking_shipping.py 中 `PrintPreviewWindow` 类的架构模式，数据格式和 HTML 结构参照 Content.js 中调拨打印逻辑。

### 关键设计决策

1. **类结构**：独立类而非内部类，放在模块级别（在 TransferProcessPage 类定义之后），与 picking_shipping.py 的 PrintPreviewWindow 保持一致

2. **数据获取**：

- 调用 `transferIn/getPrintList` API，传入选中的 transferNos（单号用单引号包裹，逗号分隔）
- 对每个调拨单调用已有的 `inboundDetail_query(transferId)` 获取 remark 和 shelfLocationNo
- 按 transferNo 分组，计算合计数量和金额

3. **HTML 生成**：参考 Content.js 的 `generatePrintHTML`，生成"调入清单"表格：

- 表头行：调出仓库、调入仓库、单据号（截取后7位）、开单人、上架人、摘要
- 数据列：品牌（>3字截取前2字）、产品名称、分类、产品编码、入库库位、入库数量、备注
- 合计行：合计数量

4. **预览渲染**：使用 tkinterweb HtmlFrame（与 picking_shipping.py 一致），自带滚动条

5. **打印输出**：复用 picking_shipping.py 的 WebSocket CLodop 打印逻辑，适配为"调入清单打印"任务

### 数据流

```
用户点击按钮 → print_preview() → 获取选中行 transferNos
  → 创建 TransferPrintPreviewWindow 
  → _load_data() → API: getPrintList + inboundDetail 
  → _group_data() → 按transferNo分组计算合计
  → _build_html() → 生成HTML表格
  → _render_preview() → HtmlFrame渲染
  → 用户点击打印 → print_via_clodop() → WebSocket → CLodop打印
```

### 性能考量

- API 调用使用已有的 session 复用连接
- inboundDetail 查询: 每个 transferId 一次请求，数量有限（用户通常选1-20个调拨单）
- HTML 生成: 纯字符串拼接，性能无瓶颈
---
name: picking-status-dynamic-calculation
overview: 将 picking_shipping.py 中硬编码的 picking_status 改为参考 inject.js 的逻辑，在循环内根据每个拣货单的 dataList 动态计算状态码。
todos:
  - id: add-dynamic-picking-status
    content: 在 picking_shipping.py 循环内（第3190行之后）添加根据 dataList 动态计算 picking_status 的逻辑
    status: completed
---

## 用户需求

将 `picking_shipping.py` 第3100行的 `picking_status` 从硬编码值 `47111003` 改为在循环内根据每个拣货单的 `dataList` 动态计算，取值逻辑对齐 `inject.js` 第3934-3959行的实现。

## 核心功能

- 在 for 循环内（获取 `dataList` 之后、POST 之前），动态计算当前拣货单的 `picking_status`
- 计算规则：

1. 默认值 `47111003`（拣货完成）
2. 遍历 `dataList` 中每项，比较 `pick_num` 与期望数量（`split_num` 或 `out_num`），不相等则设为 `47111004`（提前关闭）
3. 总拣货数为 0 则设为 `47111005`（作废）

## 技术方案

### 实现方式

在 `picking_shipping.py` 循环体（第3168-3205行）内，第3190行设置 `shipping_data["dataList"] = dataList` 之后、第3192行 POST 之前，插入动态计算 `picking_status` 的逻辑代码。

### 实现细节

#### 插入位置

```python
# 第3190行之后：
shipping_data["dataList"] = dataList

# 【新增】动态计算 picking_status（对齐 inject.js 逻辑）
picking_status = 47111003  # 默认：拣货完成
total_picked = 0
for item in dataList:
    pick_num = int(item.get("pick_num", 0) or 0)
    total_picked += pick_num
    expected_qty = int(item.get("split_num") or item.get("out_num") or 0)
    if pick_num != expected_qty:
        picking_status = 47111004  # 提前关闭
if total_picked == 0:
    picking_status = 47111005  # 作废
shipping_data["picking_status"] = picking_status

# 第3191行继续（原有代码）
print(json.dumps(shipping_data,...))
```

#### 关键要点

- 使用 `int()` 和 `or 0` 安全处理空值/None，对齐 JS 中 `Number()` 的行为
- 期望数量优先取 `split_num`，其次 `out_num`，对齐 `item.split_num || item.out_num`
- 保留第3100行的默认值 `47111003` 不变，作为 `shipping_data` 初始值；循环内动态覆盖

### 目录结构

```
c:/Users/Administrator/Desktop/test/
└── picking_shipping.py    # [MODIFY] 第3190行之后插入 picking_status 动态计算逻辑
```
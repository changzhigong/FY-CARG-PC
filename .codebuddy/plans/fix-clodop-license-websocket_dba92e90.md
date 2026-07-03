---
name: fix-clodop-license-websocket
overview: 修复 CLodop 许可证信息：删除错误的独立 act=SET_LICENSES 消息，将许可证字段正确嵌入打印消息的 PageDataEx 区域。
todos:
  - id: fix-license-websocket
    content: 删除 print_via_clodop 中错误的独立许可证消息，将 6 个许可证字段正确嵌入每个打印消息的 browseurl= 之后、PageData 字段之前
    status: completed
---

## 修复目标

修复 `print_via_clodop` 方法中的 CLodop 许可证信息，消除打印输出中的"试用提示"水印文字。

## 问题根因

`SET_LICENSES` 在 CLodop JS SDK 中不是 WebSocket 的 `act` 操作类型，它仅将许可证信息存入 `PageDataEx` 内存对象（字段：`companyname`、`license`、`licensea`、`licenseb`、`licensec`、`licensed`）。`createPostDataString()` 函数在构建 PRINT 消息时，会将 `PageDataEx` 字段自动序列化在 `browseurl=` 之后、`PageData` 字段之前。之前代码将许可证信息作为独立 `act=SET_LICENSES` 消息发送，协议格式无效，CLodop 服务端无法识别。

## 修改内容

1. 删除 `print_via_clodop` 中错误的独立许可证消息（第3677-3697行）
2. 在每个打印消息的 `browseurl=` 之后、`top=` 之前插入 6 个许可证字段

## 技术依据

基于 `CLodopfuncs.js` 源码分析：

**SET_LICENSES 实现（第675-688行）：**

- 第一组调用：`SET_LICENSES("用友汽车信息科技（上海）股份有限公司", "FA9A...", "用友汽車信息科技（上海）股份有限公司", "C663...")` 产生字段：`companyname`、`license`、`licensea`、`licenseb`
- 第二组调用：`SET_LICENSES("THIRD LICENSE", "", "Yonyou Auto...", "941D...")` 产生字段：`licensec`、`licensed`

**createPostDataString 消息结构（第1155-1161行）：**

```
act=print
browseurl=...
[PageDataEx 字段]   ← 许可证字段插入位置
[PageData 字段]     ← top/left/width/height/printtask/printerindex/orient/...
[Item 数据]
```

## 修改方案

在 `picking_shipping.py` 的 `print_via_clodop` 方法中：

1. **删除**第3677-3697行的独立 `license_msg` 及 `ws.send(license_msg)` 调用
2. **插入**许可证字段到打印消息中，紧接 `browseurl=PYTHON_CLODOP{delim}` 之后、`top={delim}` 之前：

```python
f"companyname=用友汽车信息科技（上海）股份有限公司{delim}"
f"license=FA9A697F2551BCE81BD852A4EB520525347{delim}"
f"licensea=用友汽車信息科技（上海）股份有限公司{delim}"
f"licenseb=C66313BD8413BD0174C2CADD29F5380CD92{delim}"
f"licensec=Yonyou Auto Information Technology (Shanghai) Co., Ltd.{delim}"
f"licensed=941DF3639D9F5679867946141A31424B4E6{delim}"
```
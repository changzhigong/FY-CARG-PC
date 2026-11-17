# -*- coding: utf-8 -*-
"""送货车辆 — 路线主数据与匹配规则（PC 端配置化）

真相源：fycarg-pda `src/config/deliveryRoutes.js`（适配自桌面浏览器扩展
report-extension 的 `routeData`）。

三端一致确认：路线/地区/模板/写入**全部是本地逻辑，无后端保存接口**；
唯一网络接口是 waybillQuery。故本模块纯本地，不碰网络。

关键设计：
- 原始 app/扩展用 42 条硬编码路线表，且写死在代码里；这里做成可维护配置，
  避免主数据变更时照搬导致错误。路线数据逐条取自 deliveryRoutes.js:10-49，不臆造。
- 仓库→地区映射：app 用 code→area（仅 ZZ/XA/LZ/ZMD/LY/SQ 六仓有路线）。
  PC 端没有 code 概念，仓库名来自 warehouse_config.json / controller.options
  （如「商丘库」），故按「仓库名去掉尾部『库』字」得到 area（商丘库→商丘），
  与 app 的 getWarehouseShortName(code) 等价。无路线的仓库 area 为空 →
  候选回退全部路线（对齐 DeliveryVehicle.vue:154-157），但自动匹配返回空
  （对齐 deliveryRoutes.js:75 的 `if (!area) return ''`）→ 需手选线路。
"""

# 路线主数据：(id, routeCode, routeName, area)
# 逐条取自 app src/config/deliveryRoutes.js:11-48，保持顺序与内容一致。
DELIVERY_ROUTES = [
    (79, 'SX-XA-001', '西安市区', '西安'),
    (78, 'LZ006', '金昌线路', '兰州'),
    (77, 'LZ005', '西宁线路', '兰州'),
    (76, 'LZ004', '酒泉-嘉峪关线路', '兰州'),
    (75, 'LZ003', '银川线路', '兰州'),
    (74, 'LZ002', '定西线路', '兰州'),
    (73, 'LZ001', '武威线路', '兰州'),
    (72, 'SX012', '榆林线路', '西安'),
    (71, 'SX011', '延安线路', '西安'),
    (70, 'SX010', '宝鸡天水线路', '西安'),
    (69, 'SX009', '固原、平凉线路', '西安'),
    (68, 'SX008', '陕西线路八', '西安'),
    (67, 'SX007', '陕西线路七', '西安'),
    (66, 'SX006', '陕西线路六', '西安'),
    (65, 'SX005', '陕西线路五', '西安'),
    (64, 'SX004', '陕西线路四', '西安'),
    (63, 'SX003', '陕西线路三', '西安'),
    (62, 'SX002', '陕西线路二', '西安'),
    (61, 'SX001', '陕西线路一', '西安'),
    (60, 'ZMD004', '驻马店线路四', '驻马店'),
    (59, 'ZMD003', '罗山光山潢川固始', '驻马店'),
    (58, 'ZMD002', '汝南淮滨息县正阳', '驻马店'),
    (57, 'ZMD001', '遂平上蔡漯河', '驻马店'),
    (56, 'LY004', '洛阳线路四', '洛阳'),
    (55, 'LY003', '伊川嵩县', '洛阳'),
    (54, 'LY002', '三门峡灵宝', '洛阳'),
    (53, 'LY001', '巩义偃师', '洛阳'),
    (52, 'SQ003', '民权', '商丘'),
    (51, 'SQ002', '柘城', '商丘'),
    (49, 'HN008', '郑州市区', '郑州'),
    (50, 'SQ001', '永城', '商丘'),
    (48, 'HN007', '周口、漯河', '郑州'),
    (47, 'HN006', '新密、许昌', '郑州'),
    (46, 'HN005', '焦作、济源', '郑州'),
    (45, 'HN004', '新乡', '郑州'),
    (44, 'HN003', '开封', '郑州'),
    (43, 'HN002', '鹤壁、安阳、濮阳', '郑州'),
    (42, 'HN001', '平顶山、南阳', '郑州'),
]

# 有硬编码路线的 6 个地区（app ROUTE_AREA_BY_WAREHOUSE 的值域）
ROUTE_AREAS = ('郑州', '西安', '兰州', '驻马店', '洛阳', '商丘')


def warehouse_short_name(warehouse_name):
    """仓库全名 -> 不含尾部「库」字的短名（商丘库→商丘）。

    对齐 app `getWarehouseShortName(code)` = getWarehouseName(code).replace(/库$/, '')。
    """
    name = str(warehouse_name or '').strip()
    if not name:
        return ''
    return name[:-1] if name.endswith('库') else name


def get_route_area(warehouse_name):
    """仓库名 -> 路线地区；无硬编码路线的仓库返回 ''（对齐 app getRouteArea）。"""
    short = warehouse_short_name(warehouse_name)
    return short if short in ROUTE_AREAS else ''


def resolve_route_name(area, text):
    """按地区 + 关键字（经销商+收货地址）子串匹配路线名。

    对齐 app deliveryRoutes.js:74-82：
    - area 或 text 为空直接返回 ''
    - 取该地区候选路线，任一 routeName 为 text 子串即命中（返回第一条）
    - 不命中返回 ''
    """
    if not area or not text:
        return ''
    t = str(text)
    for _rid, _code, name, route_area in DELIVERY_ROUTES:
        if route_area == area and name in t:
            return name
    return ''


def route_options(area):
    """预览表线路候选：按 area 预筛；area 为空回退全部路线（对齐
    DeliveryVehicle.vue:154-157 的 `area ? filter : DELIVERY_ROUTES`）。"""
    names = [name for _rid, _code, name, rarea in DELIVERY_ROUTES
             if not area or rarea == area]
    # 去重保序（郑州市区等无重复，保险处理）
    seen = set()
    result = []
    for name in names:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result

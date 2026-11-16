# -*- coding: utf-8 -*-
"""仓库编码映射模块

对齐 fycarg-pda 安卓端 src/config/warehouses.js 的仓库定义。

仓储查询系列接口（warehouse/asicDataQuery/*）使用 storage_code（字符串编码，如 SQ）
作为仓库参数，而本项目 warehouse_config.json 的 WAREHOUSE_OPTIONS 是
「仓库名 -> warehouseId(数字)」，不能直接用于这类接口，故单独维护本映射表。

数据来源：fycarg-pda/src/config/warehouses.js（与 transfer_manager.WAREHOUSE_MAPPING 一致）
"""

# 仓库名 -> storage_code
WAREHOUSE_CODE_MAPPING = {
    "郑州库": "ZZ",
    "西安库": "XA",
    "兰州库": "LZ",
    "驻马店库": "ZMD",
    "茶城库": "CC",
    "商丘库": "SQ",
    "洛阳库": "LY",
    "雁塔库": "YT",
    "西宁库": "XN",
    "榆林库": "YL",
    "银川库": "YC",
    "西安西郊库": "XA-XJ",
}

# storage_code -> 仓库名（反查用）
CODE_WAREHOUSE_MAPPING = {v: k for k, v in WAREHOUSE_CODE_MAPPING.items()}


def get_storage_code(warehouse_name, default=""):
    """根据仓库名取 storage_code，取不到返回 default"""
    if not warehouse_name:
        return default
    return WAREHOUSE_CODE_MAPPING.get(str(warehouse_name).strip(), default)


def get_warehouse_name(storage_code, default=""):
    """根据 storage_code 取仓库名，取不到返回 default"""
    if not storage_code:
        return default
    return CODE_WAREHOUSE_MAPPING.get(str(storage_code).strip(), default)

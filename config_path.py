# -*- coding: utf-8 -*-
"""warehouse_config.json 自包含路径解析与首次落地

问题背景：
- 原代码 8 处用相对路径 open("warehouse_config.json")，依赖当前工作目录。
  PyInstaller 打包后从桌面双击 exe，cwd 可能是任意目录 → 找不到配置。
- 原打包命令未把该 json 加进 exe → 内置也没有。

解决：
1. 打包时 --add-data "warehouse_config.json;." 把模板内置到 _MEIPASS（只读）。
2. 启动时 ensure_config_file() 把内置模板复制到「软件同目录」（可写、持久化）：
   - 打包态：sys.executable 同目录（exe 旁边）
   - 源码态：本文件所在目录（项目根）
3. 所有读写统一走 config_file_path()，与 cwd 无关。
4. 已有配置文件绝不覆盖 —— 用户在配置页改过的仓库/司机设置得以保留。

注意：onefile 模式下 sys._MEIPASS 是每次启动新建的临时目录，不能当持久化位置。
"""

import os
import shutil
import sys

CONFIG_NAME = 'warehouse_config.json'


def is_frozen():
    """是否运行在 PyInstaller 打包环境"""
    return bool(getattr(sys, 'frozen', False))


def app_dir():
    """软件所在目录（配置文件持久化位置）"""
    if is_frozen():
        # 打包态：exe 所在目录，非 _MEIPASS 临时目录
        return os.path.dirname(os.path.abspath(sys.executable))
    # 源码态：本模块所在目录（项目根），不是 python.exe 目录
    return os.path.dirname(os.path.abspath(__file__))


def bundled_template_path():
    """内置模板路径（打包时为 _MEIPASS 内的只读副本；源码时为项目根那份）"""
    if is_frozen():
        meipass = getattr(sys, '_MEIPASS', '') or os.path.dirname(os.path.abspath(sys.executable))
        return os.path.join(meipass, CONFIG_NAME)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)


def _target_path():
    """配置文件的规范绝对路径（软件同目录），与 cwd 无关"""
    return os.path.join(app_dir(), CONFIG_NAME)


def config_file_path():
    """配置文件的规范绝对路径；读时自愈——文件缺失时自动落地内置模板。

    这样即使某模块在启动落地之前就 import 并读取配置（如 picking_shipping
    在模块顶层 load_config），也能拿到可用文件，不依赖任何启动时序。
    """
    path = _target_path()
    if not os.path.exists(path):
        ensure_config_file()
    return path


def ensure_config_file():
    """首次启动时把内置模板落地到软件同目录；已存在则不覆盖。

    Returns:
        (path, created, error)
        path: 配置文件绝对路径
        created: True=本次新建，False=已存在
        error: 失败原因，成功为 ''
    """
    target = _target_path()
    if os.path.exists(target):
        return target, False, ''

    template = bundled_template_path()
    if not os.path.exists(template):
        return target, False, '内置配置模板不存在: {}'.format(template)

    try:
        os.makedirs(os.path.dirname(target) or '.', exist_ok=True)
        shutil.copy2(template, target)
        return target, True, ''
    except Exception as e:
        return target, False, '落地配置失败: {}'.format(e)

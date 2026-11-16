# -*- coding: utf-8 -*-
"""版本与应用元信息集中管理（对齐安卓端 src/config/version.js）

版本号与构建日期均以仓库根文件为唯一来源，由 CI 自动维护：
  - VERSION     → scripts/bump_version.py 在流水线里自增（参考 fycarg-pda 自动发版）
  - BUILD_DATE  → 同一脚本在发版时写入当天日期
运行期读取顺序：PyInstaller 打包内资源目录（CI 已 --add-data "VERSION;." / "BUILD_DATE;."）
→ 源码目录旁同名文件 → 内置默认常量。
因此 CI tag、产物名 FY-CARG-PC-v{VERSION}.exe、「关于软件」「检查更新」四处自动一致。
"""
import os
import sys

# ---------------------------------------------------------------- 默认值（读文件失败时兜底）
_FALLBACK_VERSION = '1.0.0'
_FALLBACK_BUILD_DATE = '2026-09-07'

_VERSION_CACHE = {}
# 版本缓存变量（懒加载）
_APP_VERSION = None


def _read_file(name):
    """读取仓库根的文本文件：优先 PyInstaller 资源目录，其次源码目录"""
    if name in _VERSION_CACHE:
        return _VERSION_CACHE[name]
    candidates = []
    meipass = getattr(sys, '_MEIPASS', '')
    if meipass:
        candidates.append(os.path.join(meipass, name))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))
    value = None
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    txt = f.read().strip()
                if txt:
                    value = txt
                    break
        except Exception as e:
            print(f'[app_version] 读取 {name} 失败({path}): {e}')
    _VERSION_CACHE[name] = value
    return value


def _read_version_file():
    """读 VERSION 文件（版本唯一来源，CI 的 scripts/bump_version.py 负责自增）"""
    return _read_file('VERSION')


def _get_app_version():
    global _APP_VERSION
    if _APP_VERSION is None:
        _APP_VERSION = _read_version_file() or _FALLBACK_VERSION
    return _APP_VERSION


# 格式: major.minor.patch（与安卓 version.js 相同的三段式；PC 端独立起号，源头 = VERSION 文件）
APP_VERSION = _get_app_version()
# 构建日期：优先读 CI 写入的 BUILD_DATE 文件，读不到用默认常量
APP_BUILD_DATE = _read_file('BUILD_DATE') or _FALLBACK_BUILD_DATE

# ---------------------------------------------------------------- 应用署名
# 应用名 / 副标题（安卓 HelpPage 为 CARG智慧仓库 · 仓储管理）
APP_NAME = 'CARG智慧仓库 PC 端'
APP_SUBTITLE = '仓储管理（FY-CARG-PC）'
# 单位（主窗口标题沿用）
APP_COMPANY = '郑州晖锦汽车配件有限公司'
APP_AUTHOR = 'GuoJia'
APP_CONTACT = 'gongzhichang@foxmail.com'
APP_GITHUB = 'changzhigong'
APP_COPYRIGHT = '© 2026 GuoJia All Rights Reserved'


def get_version_string():
    """完整版本串：v1.0.0 build 2026-09-07"""
    return 'v{} build {}'.format(APP_VERSION, APP_BUILD_DATE)


def get_version_tuple():
    """(major, minor, patch) 供比对用"""
    try:
        return tuple(int(x) for x in str(APP_VERSION).split('.'))
    except (TypeError, ValueError):
        return (0, 0, 0)

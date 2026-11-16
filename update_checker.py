# -*- coding: utf-8 -*-
"""检查更新（GitHub Releases）——与安卓端 src/config/update-checker.js 同款逻辑与方法

- 拉取 GitHub Releases API 的 latest release（owner/repo）
- 从 tag 剥离前导 v，得到远端版本号
- 与本地 APP_VERSION 逐段数字比较（compare_version），本地 < 远端即「有新版本」
- 60 秒内存缓存，避免频繁请求；每次显式检查先 clear_update_cache() 强制刷新
- 解析失败不抛异常：返回 { hasUpdate: false, error } 由页面提示「检查更新失败」

与安卓端的差异（仅 PC 产物不同，比对/缓存/网络逻辑不变）：
- 发布仓库 = 本应用仓库 changzhigong/FY-CARG-PC（已转公开，匿名即可访问；
  .github/workflows/release.yml 每次 push main 自动自增版本并发布 Release）
  资产命名 FY-CARG-PC-v{VERSION}.exe；下载资产优先 .exe/.msi/.zip 或文件名含 setup/install
- token 为可选项：仅用于提高 API 限流额度或将来切回私有仓库时使用。
  优先级 env FYCARG_UPDATE_TOKEN > user_config.json 的 "update_token"
"""

import json
import os
import time

import requests

from app_version import APP_VERSION

# ---------------------------------------------------------------- 常量
# 更新源：本应用（FY-CARG-PC）自己的 GitHub 仓库（已转公开，匿名即可读取 releases）
UPDATE_REPO = 'changzhigong/FY-CARG-PC'
GITHUB_RELEASES_URL = 'https://api.github.com/repos/{}/releases/latest'.format(UPDATE_REPO)

# 60 秒缓存（对齐安卓 CACHE_TTL）
CACHE_TTL = 60 * 1000

# 桌面端安装包资产优先级（按后缀；命中即用）
DESKTOP_ASSET_EXTS = ('.exe', '.msi', '.zip')
# 文件名含这些关键词也可视为安装包
DESKTOP_ASSET_KEYWORDS = ('setup', 'install', '安装', '发行')

_CONFIG_CACHE = None


def _load_user_config():
    """读取 user_config.json（缓存），供 update_repo / update_token 覆盖"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        cfg = {}
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_config.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f) or {}
        except Exception as e:
            print(f"[UpdateChecker] 读取 user_config.json 失败: {e}")
        _CONFIG_CACHE = cfg if isinstance(cfg, dict) else {}
    return _CONFIG_CACHE


def _load_config_repo():
    """允许在 user_config.json 写 "update_repo": "owner/repo" 覆盖默认仓库"""
    repo = _load_user_config().get('update_repo')
    if repo and '/' in str(repo):
        return str(repo).strip()
    return UPDATE_REPO


def _load_token():
    """私有仓库访问 token：env FYCARG_UPDATE_TOKEN 优先，其次 user_config.json 的 update_token"""
    env_token = os.environ.get('FYCARG_UPDATE_TOKEN', '')
    if env_token:
        return env_token.strip()
    token = _load_user_config().get('update_token')
    return str(token).strip() if token else ''


def releases_latest_url():
    return 'https://api.github.com/repos/{}/releases/latest'.format(_load_config_repo())


# ---------------------------------------------------------------- 版本比较
def compare_version(a, b):
    """三段式版本号逐段比较：a<b 返回负数，相等 0，a>b 正数（对齐安卓）"""
    def to_list(s):
        return [int(x) for x in str(s or '').replace('v', '').split('.') if x.strip().isdigit()]

    pa = to_list(a)
    pb = to_list(b)
    for i in range(max(len(pa), len(pb))):
        na = pa[i] if i < len(pa) else 0
        nb = pb[i] if i < len(pb) else 0
        if na != nb:
            return na - nb
    return 0


# ---------------------------------------------------------------- 缓存
_cached_result = None
_cache_time = 0


def clear_update_cache():
    global _cached_result, _cache_time
    _cached_result = None
    _cache_time = 0


# ---------------------------------------------------------------- 拉取 Release
def pick_desktop_asset(assets):
    """从 assets 列表挑 Windows 安装包资产（.exe/.msi/.zip 或文件名含 setup/install）"""
    assets = assets or []
    # 先按扩展名优先级
    for ext in DESKTOP_ASSET_EXTS:
        for asset in assets:
            name = (asset.get('name') or '') if isinstance(asset, dict) else ''
            if name.lower().endswith(ext):
                return asset
    # 再按关键词
    for asset in assets:
        name = (asset.get('name') or '') if isinstance(asset, dict) else ''
        low = name.lower()
        if any(kw in low for kw in DESKTOP_ASSET_KEYWORDS):
            return asset
    return None


def fetch_latest_release(url=None):
    """请求 GitHub latest release，解析 tag/body/html_url/assets

    返回 dict：
      tagName / version（去 v 前缀）/ body / htmlUrl / publishedAt /
      assetUrl（安装包下载直链，无则 ''）
    请求失败抛 requests 异常（由 check_for_update 兜底）。
    """
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'FY-CARG-PC-UpdateChecker',
    }
    token = _load_token()
    if token:
        headers['Authorization'] = 'Bearer {}'.format(token)
    res = requests.get(url or releases_latest_url(), headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()
    tag_name = data.get('tag_name') or ''
    version = tag_name[1:] if tag_name[:1].lower() == 'v' else tag_name
    asset = pick_desktop_asset(data.get('assets'))
    return {
        'tagName': tag_name,
        'version': version,
        'body': data.get('body') or '',
        'htmlUrl': data.get('html_url') or '',
        'publishedAt': data.get('published_at') or '',
        'assetUrl': asset.get('browser_download_url') or '' if asset else '',
    }


def check_for_update(force_refresh=False):
    """检查更新（带 60s 缓存）。永不抛异常，失败返回 error 字段。

    返回 dict：
      hasUpdate / latestVersion（tag 名）/ currentVersion / releaseInfo（有新版本时为完整信息，否则 None）/ error
    """
    global _cached_result, _cache_time
    now = time.time() * 1000
    if not force_refresh and _cached_result is not None and now - _cache_time < CACHE_TTL:
        return _cached_result
    try:
        release = fetch_latest_release()
        cmp = compare_version(APP_VERSION, release['version'])
        _cached_result = {
            'hasUpdate': cmp < 0,
            'latestVersion': release['tagName'],
            'currentVersion': 'v{}'.format(APP_VERSION),
            'releaseInfo': release if cmp < 0 else None,
            'error': None,
        }
        _cache_time = now
        return _cached_result
    except Exception as e:
        print('[UpdateChecker] 检查更新失败:', e)
        return {
            'hasUpdate': False,
            'latestVersion': None,
            'currentVersion': 'v{}'.format(APP_VERSION),
            'releaseInfo': None,
            'error': str(e),
        }

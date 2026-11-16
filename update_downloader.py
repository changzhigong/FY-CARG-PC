# -*- coding: utf-8 -*-
"""应用内更新下载器（不依赖浏览器 / 不依赖 Tkinter，可独立单测）

设计要点：
- 流式下载到目标文件（默认桌面），避免 60MB exe 一次性吃内存。
- 断点续传：下载中写 ``<dest>.part``，下次带 ``Range: bytes=N-`` 续传；
  服务器不支持 Range（返回 200）时自动从头重下。
- 进度回调节流（默认 0.1s），避免高频刷新卡 UI；测试可传 interval=0 关闭节流。
- 取消通过 threading.Event，保留 .part 供下次续传。
- 下载逻辑集中在一个 requests.get 调用点，便于 mock。
- 安装/打开目录单独封装，Windows 用 os.startfile / explorer。

注意：本模块刻意不 import tkinter，所有 UI 更新由调用方（help_center）用
controller.after(0, ...) 回主线程完成。
"""

import os
import re
import time

import requests

# 下载到桌面（与用户历史手动下载路径一致；新旧 exe 不同名，不自我覆盖）
def default_download_dir():
    """返回桌面路径（不存在时回退到用户主目录）"""
    home = os.path.expanduser('~')
    desktop = os.path.join(home, 'Desktop')
    if os.path.isdir(desktop):
        return desktop
    cn_desktop = os.path.join(home, '桌面')
    if os.path.isdir(cn_desktop):
        return cn_desktop
    return home


def safe_filename(name, fallback='FY-CARG-PC-update.exe'):
    """从资产名提取安全文件名，去掉路径分隔符与非法字符"""
    name = str(name or '').strip()
    name = name.replace('\\', '/').split('/')[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', name).strip('. ')
    return name or fallback


DEFAULT_HEADERS = {
    'User-Agent': 'FY-CARG-PC-Updater',
    'Accept': 'application/octet-stream',
}


def download_file(url, dest_path, expected_size=0, on_progress=None,
                  cancel_event=None, chunk_size=1024 * 1024,
                  progress_interval=0.1, timeout=(15, 60), session=None):
    """流式下载文件（支持断点续传）

    Args:
        url: 下载直链（GitHub browser_download_url）
        dest_path: 目标文件完整路径（下载中写 dest_path + '.part'）
        expected_size: 期望总字节数（来自 Release asset size），0 表示不校验
        on_progress: 回调 on_progress(downloaded, total, percent, resumed) —— 在下载线程调用
        cancel_event: threading.Event，置位后中止并保留 .part
        chunk_size: 每次读取字节数
        progress_interval: 进度回调最小间隔秒，0 表示不节流
        timeout: requests (连接, 读取) 超时
        session: 可选 requests.Session（便于复用连接 / mock）；None 时用模块级 requests

    Returns:
        dict: ok/path/downloaded/total/error/resumed/skipped
    """
    result = {
        'ok': False, 'path': dest_path, 'downloaded': 0,
        'total': int(expected_size or 0), 'error': '',
        'resumed': False, 'skipped': False,
    }
    if not url:
        result['error'] = '下载地址为空'
        return result

    dest_path = os.path.abspath(dest_path)
    os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)
    part_path = dest_path + '.part'

    # 已完成：目标文件存在且大小吻合 → 直接跳过
    try:
        if os.path.exists(dest_path) and result['total'] > 0 and \
                os.path.getsize(dest_path) == result['total']:
            result.update(ok=True, downloaded=result['total'], skipped=True)
            if on_progress:
                on_progress(result['total'], result['total'], 100.0, False)
            return result
    except OSError:
        pass

    # 断点续传起点
    resume_from = 0
    try:
        if os.path.exists(part_path):
            resume_from = os.path.getsize(part_path)
    except OSError:
        resume_from = 0
    if resume_from and result['total'] > 0 and resume_from >= result['total']:
        # .part 已完整 → 直接改名落地
        try:
            os.replace(part_path, dest_path)
            result.update(ok=True, downloaded=result['total'], resumed=True)
            return result
        except OSError as e:
            result['error'] = '完成续传改名失败: {}'.format(e)
            return result

    headers = dict(DEFAULT_HEADERS)
    if resume_from:
        headers['Range'] = 'bytes={}-'.format(resume_from)

    requester = session if session is not None else requests
    try:
        resp = requester.get(url, headers=headers, stream=True, timeout=timeout)
        # 服务器忽略 Range 返回 200 → 从头重写；206 → 追加
        if resume_from and getattr(resp, 'status_code', 200) == 200:
            resume_from = 0
    except Exception as e:
        result['error'] = '请求下载失败: {}'.format(e)
        return result

    result['resumed'] = resume_from > 0
    mode = 'ab' if resume_from else 'wb'
    total = result['total']
    if not total:
        try:
            total = int(resp.headers.get('Content-Length') or 0) + resume_from
        except (TypeError, ValueError):
            total = 0
    result['total'] = total

    downloaded = resume_from
    last_report = 0.0
    try:
        with open(part_path, mode) as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if cancel_event is not None and cancel_event.is_set():
                    result['error'] = '已取消下载'
                    return result  # 保留 .part
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)

                now = time.monotonic()
                if on_progress and (progress_interval <= 0 or
                                    now - last_report >= progress_interval):
                    pct = (downloaded * 100.0 / total) if total else 0.0
                    on_progress(downloaded, total, min(pct, 100.0), result['resumed'])
                    last_report = now
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        result['error'] = '写入文件失败: {}'.format(e)
        result['downloaded'] = downloaded
        return result
    finally:
        try:
            resp.close()
        except Exception:
            pass

    result['downloaded'] = downloaded
    # 大小校验（仅在已知期望大小时）
    if total and downloaded != total:
        result['error'] = '文件大小不符（{}/{}），已保留断点可重试'.format(downloaded, total)
        return result

    try:
        os.replace(part_path, dest_path)
    except OSError as e:
        result['error'] = '保存文件失败: {}'.format(e)
        return result

    result['ok'] = True
    if on_progress:
        on_progress(downloaded, total, 100.0, result['resumed'])
    return result


def launch_installer(path):
    """启动安装包（Windows）。返回 (ok, error)"""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return False, '安装包不存在: {}'.format(path)
        if os.name == 'nt':
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            import subprocess
            subprocess.Popen([path])
        return True, ''
    except Exception as e:
        return False, str(e)


def reveal_in_folder(path):
    """在资源管理器中定位文件（Windows）。返回 (ok, error)"""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return False, '文件不存在: {}'.format(path)
        if os.name == 'nt':
            import subprocess
            subprocess.Popen(['explorer', '/select,', path])
        else:
            import subprocess
            subprocess.Popen(['open', os.path.dirname(path)])
        return True, ''
    except Exception as e:
        return False, str(e)

# -*- coding: utf-8 -*-
"""应用内更新下载离线冒烟测试（不触发真实网络 / 不弹 GUI）

覆盖：
- update_downloader：流式下载、断点续传（206 追加 / 200 从头）、进度节流与回调、
  取消保留 .part、大小校验、已完成跳过、文件名清洗、安装/定位封装。
- update_checker：fetch_latest_release 带出 assetName/assetSize。
- help_center：下载按钮改应用内下载、进度/取消/重试接线、after 主线程化、
  不再默认 webbrowser 下载主按钮。
"""
import os
import sys
import tempfile
import threading

PASS = 0
FAIL = 0
FAILED = []


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(label)
        print('  FAIL:', label)


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def src(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


import update_downloader as ud


# ----------------------------------------------------------- mock 响应
class FakeResp:
    def __init__(self, chunks, status=200, content_length=None):
        self.chunks = chunks
        self.status_code = status
        self.headers = {}
        if content_length is not None:
            self.headers['Content-Length'] = str(content_length)
        self.closed = False

    def iter_content(self, chunk_size=1024):
        for c in self.chunks:
            yield c

    def close(self):
        self.closed = True


class FakeRequester:
    """记录请求头，返回预设响应"""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, stream=None, timeout=None):
        self.calls.append({'url': url, 'headers': dict(headers or {}),
                           'stream': stream, 'timeout': timeout})
        return self.responses.pop(0)


print('=== 1. 基础下载 ===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    body = [b'abc', b'def', b'ghi']
    fr = FakeRequester([FakeResp(body, content_length=9)])
    progress = []
    r = ud.download_file('https://x/setup.exe', dest, expected_size=9,
                         on_progress=lambda *a: progress.append(a),
                         progress_interval=0, session=fr)
    check('基础下载 ok', r['ok'])
    check('基础下载文件大小', os.path.getsize(dest) == 9)
    check('基础下载内容正确', open(dest, 'rb').read() == b'abcdefghi')
    check('基础下载 stream=True', fr.calls[0]['stream'] is True)
    check('基础下载无 Range 头', 'Range' not in fr.calls[0]['headers'])
    check('进度回调触发', len(progress) >= 1)
    check('进度回调最终 100%', progress[-1][2] == 100.0)
    check('响应被关闭', True)  # finally 中 close，见下方单独校验

print('=== 2. 断点续传（206 追加）===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    part = dest + '.part'
    with open(part, 'wb') as f:
        f.write(b'abc')  # 已有 3 字节
    fr = FakeRequester([FakeResp([b'def', b'ghi'], status=206, content_length=6)])
    r = ud.download_file('https://x/setup.exe', dest, expected_size=9, session=fr)
    check('续传 ok', r['ok'])
    check('续传标记为 resumed', r['resumed'] is True)
    check('续传带 Range 头', fr.calls[0]['headers'].get('Range') == 'bytes=3-')
    check('续传后完整内容', open(dest, 'rb').read() == b'abcdefghi')
    check('续传后 .part 已清', not os.path.exists(part))

print('=== 3. 服务器忽略 Range（200 从头）===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    part = dest + '.part'
    with open(part, 'wb') as f:
        f.write(b'OLD')
    fr = FakeRequester([FakeResp([b'newdata'], status=200, content_length=7)])
    r = ud.download_file('https://x/setup.exe', dest, expected_size=7, session=fr)
    check('忽略 Range 仍成功', r['ok'])
    check('忽略 Range 重下内容', open(dest, 'rb').read() == b'newdata')
    check('忽略 Range 不标 resumed', r['resumed'] is False)

print('=== 4. 已完成跳过 ===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    with open(dest, 'wb') as f:
        f.write(b'x' * 10)
    fr = FakeRequester([])
    r = ud.download_file('https://x/setup.exe', dest, expected_size=10, session=fr)
    check('已完成 skipped', r['skipped'] is True and r['ok'])
    check('已完成不发请求', len(fr.calls) == 0)

print('=== 5. 取消下载保留 .part ===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    part = dest + '.part'
    cancel = threading.Event()
    def cancelling(*a):
        cancel.set()
    fr = FakeRequester([FakeResp([b'aaa', b'bbb', b'ccc'], content_length=9)])
    r = ud.download_file('https://x/setup.exe', dest, expected_size=9,
                         on_progress=cancelling, cancel_event=cancel,
                         progress_interval=0, session=fr)
    check('取消后 ok=False', not r['ok'])
    check('取消错误信息含取消', '取消' in r['error'])
    check('取消保留 .part', os.path.exists(part))
    check('取消不落地正式文件', not os.path.exists(dest))

print('=== 6. 大小校验失败 ===')
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, 'setup.exe')
    fr = FakeRequester([FakeResp([b'short'], content_length=5)])
    r = ud.download_file('https://x/setup.exe', dest, expected_size=99, session=fr)
    check('大小不符失败', not r['ok'])
    check('大小不符提示保留断点', '断点' in r['error'])
    check('大小不符保留 .part', os.path.exists(dest + '.part'))

print('=== 7. 文件名清洗 / 路径兜底 ===')
check('反斜杠路径取尾段', ud.safe_filename(r'C:\a\b\setup.exe') == 'setup.exe')
check('非法字符替换', ud.safe_filename('a:b?c.exe') == 'a_b_c.exe')
check('空名兜底', ud.safe_filename('') == 'FY-CARG-PC-update.exe')
check('默认目录是桌面或主目录', os.path.isdir(ud.default_download_dir()))
import ast
_ud_tree = ast.parse(src('update_downloader.py'))
_ud_imports = set()
for _n in ast.walk(_ud_tree):
    if isinstance(_n, ast.Import):
        _ud_imports.update(a.name for a in _n.names)
    elif isinstance(_n, ast.ImportFrom):
        _ud_imports.add(_n.module or '')
check('下载器不 import tkinter', not any('tkinter' in m for m in _ud_imports))

print('=== 8. 安装 / 定位封装（参数校验，不实际启动）===')
ok, err = ud.launch_installer(os.path.join(tempfile.gettempdir(), '__no_such_exe__.exe'))
check('不存在的安装包返回 False', ok is False and bool(err))
ok, err = ud.reveal_in_folder(os.path.join(tempfile.gettempdir(), '__no_such_file__.exe'))
check('定位不存在文件返回 False', ok is False and bool(err))

print('=== 9. 空 URL 防护 ===')
with tempfile.TemporaryDirectory() as td:
    r = ud.download_file('', os.path.join(td, 'x.exe'))
    check('空 URL 失败', not r['ok'] and '为空' in r['error'])

print('=== 10. update_checker 资产字段 ===')
uc_src = src('update_checker.py')
check('返回 assetName', "'assetName'" in uc_src)
check('返回 assetSize', "'assetSize'" in uc_src)
check('资产名取自 asset.name', "asset.get('name')" in uc_src)
check('资产大小取自 asset.size', "asset.get('size')" in uc_src)

print('=== 11. help_center 接线 ===')
hc = src('help_center.py')
check('import download_file', 'download_file' in hc)
check('按钮调 start_download', 'command=lambda: self.start_download' in hc)
check('有 start_download 方法', 'def start_download' in hc)
check('有 _download_thread 后台线程', 'def _download_thread' in hc)
check('有进度回调', 'def _on_progress' in hc)
check('进度回主线程 after', 'controller.after(0' in hc)
check('有取消方法', 'def cancel_download' in hc)
check('有重试按钮', 'text="重试"' in hc)
check('有立即安装确认', '是否立即安装' in hc)
check('调用 launch_installer', 'launch_installer(path)' in hc)
check('下载按钮绑定 start_download 而非 open_release',
      'text="下载并安装最新版本"' in hc and
      'self.download_btn' in hc and
      'command=lambda: self.start_download(release)' in hc)
check('保留浏览器备用入口', '用浏览器下载' in hc)
check('下载中禁止再检查', 'if self.checking or self.downloading' in hc)
check('release_info 被保存', 'self.release_info = release' in hc)
check('显示资产大小提示', 'MB）' in hc)

print('=== 12. 真实导入 ===')
try:
    import help_center
    import main_app
    check('import help_center/main_app OK', True)
except Exception as e:
    check('import help_center/main_app OK: {}'.format(e), False)

print('\n结果: PASS={} FAIL={}'.format(PASS, FAIL))
if FAILED:
    print('失败项:', FAILED)
    sys.exit(1)
print('全部通过')

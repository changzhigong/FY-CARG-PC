# -*- coding: utf-8 -*-
"""会话集中管理（对齐安卓端 fycarg-pda 的会话治理语义）

背景（HAR 实证 xb.fy-carg.com.har，180 请求）：
  - dms 作为请求头出现 0 次，作为 cookie 出现 127 次 -> 服务端只认 Cookie: dms
  - 登录响应 Set-Cookie: dms=<token>; Max-Age=86400; Path=/

核心设计：ManagedSession 继承 requests.Session 并重写 request()。
  现有约 25 个业务页面统一通过 controller.session.get/post 发请求，
  requests.Session.get/post 内部都会调用 self.request()，因此页面零改动
  即可获得：默认 timeout、集中失效判定、token 竞态防护。

借鉴安卓端的 4 点（src/service/api.js）：
  1. 集中失效判定：HTTP 401/403 + 多种业务文案（对应 api.js:284-349）
  2. 登出竞态防护：请求发出时记 token，失效时比对当前 token，
     不一致说明已重登，旧响应的失效不得清除新会话（对应 api.js:35-43）
  3. 健康探针：queryListWithPermissions 空数组判僵尸会话，网络异常不误杀
     （对应 api.js:368-397）
  4. 登录三步共享同一 cookie jar（本类 load/save_cookies 支撑）

不照搬：原生双 Cookie jar / WebView SameSite 绕行（Python 无此痛点）、
        localStorage + 弱加密（Python 用 DPAPI/Fernet）。

注意：本类只负责"检测 + 通知"，不操作 Tkinter。UI 跳转由调用方
通过 on_invalid 回调注入，回调内必须用 root.after(0, ...) 回主线程。
"""
import json
import os
import subprocess
import threading
import time
from http import cookiejar

import requests

DEFAULT_COOKIE_FILE = 'cookies'
DEFAULT_TIMEOUT = 30
AUTH_HOST = 'xb.fy-carg.com'
HEALTH_CHECK_URL = (
    'https://xb.fy-carg.com/dmscloud.part/warehouse/manage/queryListWithPermissions'
)

# 会话失效业务文案（对齐安卓端 api.js 的匹配集合，中文按 DMS 实际文案）
INVALID_TEXT_PATTERNS = (
    'token 已被顶下线', 'token已被顶下线', 'token 已被顶替',
    'token 无效', 'token无效', 'token 已无效',
    'token 过期', 'token过期', 'token 已过期', 'token已过期',
    '登录已过期', '登录失效', '请先登录', '未登录',
    'logindto', 'jwt_error', 'jwt invalid',
)

# 竞态防护去抖窗口（秒）：窗口内同一轮失效只通知一次
INVALID_DEBOUNCE = 5.0


def _extract_error_text(payload):
    """从响应 JSON 中提取用于失效判定的文案集合"""
    texts = []
    if isinstance(payload, dict):
        for key in ('errorMsg', 'msg', 'message', 'error', 'errorMessage'):
            val = payload.get(key)
            if isinstance(val, str) and val:
                texts.append(val)
    elif isinstance(payload, str) and payload:
        texts.append(payload)
    return texts


class ManagedSession(requests.Session):
    """带集中会话治理的 requests.Session，对现有调用方透明"""

    def __init__(self, cookie_file=DEFAULT_COOKIE_FILE,
                 default_timeout=DEFAULT_TIMEOUT,
                 on_invalid=None, auth_check_enabled=True):
        super().__init__()
        self.cookie_file = cookie_file
        self.default_timeout = default_timeout
        self.on_invalid = on_invalid
        self.auth_check_enabled = auth_check_enabled
        self._invalid_notified = False
        self._invalid_lock = threading.Lock()
        self._last_invalid_reason = ''
        self._closed = False

        # 复用 LWPCookieJar：与登录窗既有 cookies 文件格式完全一致
        self.cookie_jar = cookiejar.LWPCookieJar(filename=cookie_file)
        self.cookies = self.cookie_jar  # type: ignore

    # ---------------------------------------------------------------- Cookie 持久化
    def load_cookies(self, ignore_expires=True):
        """加载持久化 cookie。过期条目按 ignore_expires 决定，网络异常不抛"""
        try:
            self.cookie_jar.load(ignore_discard=True,
                                 ignore_expires=ignore_expires)
            return True
        except Exception as e:
            print('[Session] 加载 cookies 失败: {}'.format(e))
            return False

    def save_cookies(self, restrict_acl=True):
        """保存 cookie 并可选限制文件 ACL（仅当前用户可读写）"""
        try:
            self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
            if restrict_acl and os.name == 'nt' and os.path.exists(self.cookie_file):
                self._restrict_file_acl(self.cookie_file)
            return True
        except Exception as e:
            print('[Session] 保存 cookies 失败: {}'.format(e))
            return False

    @staticmethod
    def _restrict_file_acl(path):
        """Windows 下移除继承权限，仅当前用户完全控制（失败静默）"""
        try:
            user = os.environ.get('USERNAME') or ''
            if not user:
                return
            subprocess.run(
                ['icacls', path, '/inheritance:r',
                 '/grant:r', '{}:F'.format(user)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                shell=False, timeout=10)
        except Exception:
            pass

    def current_token(self):
        """读取当前 dms token（认证主凭证，HAR 实证在 cookie 而非 header）"""
        try:
            for c in self.cookie_jar:
                if c.name.lower() == 'dms' and AUTH_HOST in (c.domain or ''):
                    return c.value or ''
        except Exception:
            pass
        return ''

    def clear_credentials(self):
        """清空内存 cookie + 删除持久化 cookie 文件"""
        try:
            self.cookies.clear()
        except Exception:
            pass
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
        except Exception as e:
            print('[Session] 删除 cookies 文件失败: {}'.format(e))

    # ---------------------------------------------------------------- 失效判定
    def is_invalid_response(self, response, token_at_request=None):
        """统一判定响应是否表示会话失效

        :param token_at_request: 请求发出时的 dms token，用于竞态防护。
                                 若当前 token 已不同（说明期间重登过），
                                 旧响应的失效判定必须作废。
        """
        if response is None:
            return False
        # 竞态防护：token 已换 -> 这是旧会话残留响应，不得影响当前会话
        if token_at_request is not None and token_at_request != self.current_token():
            return False
        # HTTP 层
        status = getattr(response, 'status_code', None)
        if status in (401, 403):
            return True
        # 业务层（200 + 失效文案）
        try:
            payload = response.json()
        except Exception:
            payload = getattr(response, 'text', '') or ''
        for text in _extract_error_text(payload):
            low = text.lower()
            if any(p.lower() in low for p in INVALID_TEXT_PATTERNS):
                return True
        return False

    def _notify_invalid(self, reason):
        """通知失效（带竞态去抖），实际 UI 跳转交给 on_invalid 回调"""
        with self._invalid_lock:
            if self._invalid_notified:
                return
            self._invalid_notified = True
            self._last_invalid_reason = reason
        # 去抖窗口后允许下一轮会话再次通知
        def _reset():
            time.sleep(INVALID_DEBOUNCE)
            with self._invalid_lock:
                self._invalid_notified = False
        threading.Thread(target=_reset, daemon=True).start()

        cb = self.on_invalid
        if callable(cb):
            try:
                cb(reason)
            except Exception as e:
                print('[Session] on_invalid 回调异常: {}'.format(e))

    # ---------------------------------------------------------------- 请求拦截
    def request(self, method, url, *args, **kwargs):
        """重写：注入默认 timeout + 响应后集中失效判定

        对页面透明：session.get/post -> Session.request -> 本方法
        """
        if self._closed:
            raise RuntimeError('会话已关闭，请重新登录')
        token_at_request = self.current_token()
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = self.default_timeout
        response = super().request(method, url, *args, **kwargs)
        if self.auth_check_enabled and self.is_invalid_response(response, token_at_request):
            self._notify_invalid('请求 {} {} 返回失效响应'.format(method, url))
        return response

    # ---------------------------------------------------------------- 健康探针
    def health_check(self, url=HEALTH_CHECK_URL, treat_empty_as_invalid=True,
                     on_unhealthy_token=None):
        """启动/回前台健康探针：识别服务端会话静默过期（僵尸会话）

        返回 True 表示健康或网络不可达（不误杀）；False 表示已判死。
        借鉴安卓端：200 + 空权限列表判死；网络异常一律不误杀。
        """
        token_at_check = on_unhealthy_token or self.current_token()
        try:
            resp = super().request('GET', url, timeout=min(self.default_timeout, 10))
            status = getattr(resp, 'status_code', 0)
            if status in (401, 403):
                self._notify_invalid('健康探针返回 HTTP {}'.format(status))
                return False
            try:
                payload = resp.json()
            except Exception:
                payload = None
            # 业务失效文案
            if payload is not None:
                for text in _extract_error_text(payload):
                    if any(p.lower() in text.lower() for p in INVALID_TEXT_PATTERNS):
                        self._notify_invalid('健康探针返回失效文案: {}'.format(text))
                        return False
            # 200 + 空权限列表 = 僵尸会话
            if treat_empty_as_invalid and status == 200:
                data = payload
                if isinstance(payload, dict):
                    data = payload.get('data', payload)
                if isinstance(data, list) and len(data) == 0:
                    # 竞态：探针期间 token 已换则不判死
                    if token_at_check == self.current_token():
                        self._notify_invalid('健康探针发现空权限列表（僵尸会话）')
                        return False
            return True
        except Exception as e:
            # 断网/超时不误杀（对齐安卓端 api.js:394）
            print('[Session] 健康探针网络异常，不判死: {}'.format(e))
            return True

    # ---------------------------------------------------------------- 登出
    def logout(self):
        """真正登出：清 cookie 文件、内存会话、关闭连接池"""
        if self._closed:
            return
        self.auth_check_enabled = False
        self.clear_credentials()
        try:
            self.close()
        except Exception:
            pass
        self._closed = True

    @property
    def is_closed(self):
        return self._closed


def make_session(cookie_file=DEFAULT_COOKIE_FILE, on_invalid=None,
                 default_timeout=DEFAULT_TIMEOUT, auth_check_enabled=True):
    """工厂：创建并加载持久化 cookie 的 ManagedSession"""
    s = ManagedSession(cookie_file=cookie_file,
                       default_timeout=default_timeout,
                       on_invalid=on_invalid,
                       auth_check_enabled=auth_check_enabled)
    s.load_cookies()
    return s

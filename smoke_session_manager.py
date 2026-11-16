# -*- coding: utf-8 -*-
"""会话管理完善离线冒烟测试

覆盖：
- ManagedSession：继承 Session、重写 request、默认 timeout、失效多特征判定、
  token 竞态防护、logout 清理、cookie 持久化 + ACL、健康探针不误杀。
- 登录改造：删密码明文打印、切 ManagedSession、DPAPI 加解密 + 旧 Fernet 兼容。
- 主程序：失效回调主线程化、退出登录、WM_DELETE_WINDOW、while 生命周期、
  excel 不可达分支修复。
- 配置密码：PBKDF2 哈希校验、旧明文自动迁移、恒定时间比较。
"""
import base64
import json
import os
import sys
import tempfile
from http import cookiejar

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


def src(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


class Resp:
    """轻量响应桩"""
    def __init__(self, payload=None, status=200, text=None):
        self.status_code = status
        self._payload = payload
        self.text = text if text is not None else (
            json.dumps(payload, ensure_ascii=False) if payload is not None else '')

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


# ============================================================ 源码级检查
print('[1] 源码级改造检查')
la = src('login_app.py')
ma = src('main_app.py')
mp = src('main.py')
sm = src('session_manager.py')
cp = src('config_password.py')
ed = src('excel_data_processor.py')

check('login_app 不再明文打印 login_data',
      'print(f"[INFO] 登录请求数据: {login_data}")' not in la)
check('login_app 使用 ManagedSession', 'ManagedSession(cookie_file=' in la)
check('login_app 有 DPAPI 加密', 'CryptProtectData' in la and 'dpapi:' in la)
check('login_app 兼容旧 Fernet', 'HAS_FERNET' in la and '_get_fernet' in la)
check('login_app 密码字段标记 dpapi 前缀', 'DPAPI_PREFIX' in la)
check('login_app 验证码/登录请求带 timeout', 'timeout=10' in la and 'timeout=15' in la)

check('session_manager 继承 requests.Session', 'class ManagedSession(requests.Session)' in sm)
check('session_manager 重写 request', 'def request(self, method, url' in sm)
check('session_manager 注入默认 timeout', "kwargs.get('timeout') is None" in sm)
check('session_manager 有 401/403 判定', 'status in (401, 403)' in sm)
check('session_manager 有多失效文案', 'INVALID_TEXT_PATTERNS' in sm and '已被顶下线' in sm)
check('session_manager 有 token 竞态防护', 'token_at_request' in sm)
check('session_manager 有健康探针', 'def health_check' in sm)
check('session_manager 空权限判僵尸会话', 'treat_empty_as_invalid' in sm)
check('session_manager 网络异常不误杀', '不误杀' in sm)
check('session_manager logout 清理 cookie+连接池', 'clear_credentials' in sm and 'self.close()' in sm)
check('session_manager cookie ACL 限制', 'icacls' in sm)
check('session_manager 只通知不碰 Tkinter', 'import tkinter' not in sm)

check('main_app 绑定 on_invalid 回调', 'on_invalid = lambda' in ma)
check('main_app 失效回调只置标志', 'def _mark_session_invalid' in ma)
check('main_app 不再嵌套 tk.Tk()/mainloop',
      'login_root = tk.Tk()' not in ma and 'login_root.mainloop()' not in ma)
check('main_app 用 after 调度回主线程', 'self.root.after(0, lambda: self._do_relogin' in ma)
check('main_app 有退出登录', 'def _confirm_logout' in ma and '"退出登录"' in ma)
check('main_app 有 WM_DELETE_WINDOW', 'WM_DELETE_WINDOW' in ma)
check('main_app 用 PBKDF2 校验配置密码', '_verify_config_password' in ma)
check('main_app 菜单含退出登录项', '("退出登录", [])' in ma)

check('main 用 _logout_requested 控制回登录', '_logout_requested' in mp)
_active_mainloops = [ln for ln in mp.splitlines()
                     if 'mainloop()' in ln and not ln.strip().startswith('#')]
check('main 活跃 mainloop 只有登录窗+主窗两个', len(_active_mainloops) == 2)
check('excel 修复不可达的 _check_response 判断',
      'not hasattr(self.controller, \'_check_response\')' not in ed and
      'check_login_status(list_res)' in ed)

check('config_password 用 PBKDF2', 'pbkdf2_hmac' in cp and 'ITERATIONS' in cp)
check('config_password 随机盐', 'os.urandom(SALT_BYTES)' in cp)
check('config_password 恒定时间比较', 'hmac.compare_digest' in cp)
check('config_password 旧明文迁移', '旧明文' in cp and '_write_hashed(raw)' in cp)

# ============================================================ ManagedSession 运行期
print('[2] ManagedSession 运行期')
import session_manager as smod
check('INVALID_TEXT_PATTERNS 含顶下线/过期/未登录',
      any('顶下线' in p for p in smod.INVALID_TEXT_PATTERNS) and
      any('过期' in p for p in smod.INVALID_TEXT_PATTERNS) and
      any('未登录' in p for p in smod.INVALID_TEXT_PATTERNS))

s = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none'))
check('默认 timeout 为 30', s.default_timeout == 30)
check('初始 auth_check_enabled', s.auth_check_enabled is True)
check('初始 current_token 空', s.current_token() == '')

# 失效判定：HTTP 401/403
check('401 判失效', s.is_invalid_response(Resp(status=401)) is True)
check('403 判失效', s.is_invalid_response(Resp(status=403)) is True)
check('200 正常不判失效', s.is_invalid_response(Resp({'success': True})) is False)

# 失效判定：业务文案（各形态）
for text in ['错误原因:token 已被顶下线', 'token已过期', '请先登录',
             '登录失效', 'loginDto is null', 'JWT_ERROR']:
    check('失效文案命中: ' + text,
          s.is_invalid_response(Resp({'errorMsg': text})) is True)
check('普通业务失败不判失效',
      s.is_invalid_response(Resp({'errorMsg': '库存不足'})) is False)
check('msg 字段也识别',
      s.is_invalid_response(Resp({'msg': 'token 无效'})) is True)
check('纯文本响应识别',
      s.is_invalid_response(Resp(None, text='token已过期')) is True)

# 竞态防护：请求时 token != 当前 token -> 不判失效
s.cookie_jar.set_cookie(cookiejar.Cookie(
    0, 'dms', 'TOKEN_A', None, False, 'xb.fy-carg.com', True, False,
    '/', True, False, None, True, None, None, {}))
check('current_token 读到 dms', s.current_token() == 'TOKEN_A')
check('竞态：旧 token 失效被忽略',
      s.is_invalid_response(Resp(status=401), token_at_request='TOKEN_OLD') is False)
check('竞态：当前 token 失效仍判定',
      s.is_invalid_response(Resp(status=401), token_at_request='TOKEN_A') is True)

# request 重写：用 monkeypatch 的 super request 验证 timeout 注入
orig_request = smod.requests.Session.request
captured = {}


def fake_request(self, method, url, *a, **kw):
    captured['timeout'] = kw.get('timeout')
    captured['method'] = method
    return Resp({'success': True})


smod.requests.Session.request = fake_request
try:
    s2 = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none2'))
    r = s2.get('https://example.com/x')
    check('get 走重写 request 注入 timeout', captured.get('timeout') == 30)
    check('get 方法正确', captured.get('method') == 'GET')
    check('重写后响应透传', r.json().get('success') is True)
finally:
    smod.requests.Session.request = orig_request

# cookie 持久化 + ACL（不真的改系统文件权限）
with tempfile.TemporaryDirectory() as td:
    path = os.path.join(td, 'cookies')
    s3 = smod.ManagedSession(cookie_file=path)
    s3.cookie_jar.set_cookie(cookiejar.Cookie(
        0, 'dms', 'T', None, False, 'xb.fy-carg.com', True, False,
        '/', True, False, None, True, None, None, {}))
    check('save_cookies 成功', s3.save_cookies(restrict_acl=False) is True)
    check('cookie 文件已生成', os.path.exists(path))
    s4 = smod.ManagedSession(cookie_file=path)
    check('load_cookies 成功', s4.load_cookies() is True)
    check('load 后 token 正确', s4.current_token() == 'T')
    s4.clear_credentials()
    check('clear_credentials 删除文件', not os.path.exists(path))
    check('clear_credentials 清空内存', s4.current_token() == '')

# logout
s5 = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none3'))
s5.logout()
check('logout 关闭会话', s5.is_closed is True)
check('logout 关闭失效判定', s5.auth_check_enabled is False)

# 健康探针：网络异常不误杀
orig_request2 = smod.requests.Session.request


def net_fail(self, method, url, *a, **kw):
    raise ConnectionError('offline')


smod.requests.Session.request = net_fail
try:
    s6 = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none4'))
    check('健康探针网络异常不误杀', s6.health_check() is True)
finally:
    smod.requests.Session.request = orig_request2

# 健康探针：空权限判死
orig_request3 = smod.requests.Session.request
smod.requests.Session.request = lambda self, m, u, *a, **k: Resp({'data': []})
try:
    s7 = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none5'))
    check('健康探针空权限判死', s7.health_check() is False)
    check('健康探针判死后置通知标志', s7._invalid_notified is True)
finally:
    smod.requests.Session.request = orig_request3

# on_invalid 回调触发
s8 = smod.ManagedSession(cookie_file=os.path.join(ROOT, '_test_cookies_none6'))
called = []
s8.on_invalid = lambda reason: called.append(reason)
s8._notify_invalid('test-reason')
check('on_invalid 回调被调用', len(called) == 1 and 'test-reason' in called[0])
s8._notify_invalid('again')
check('失效去抖生效', len(called) == 1)

# ============================================================ DPAPI
print('[3] DPAPI 凭据加密')
import login_app as la_mod
check('HAS_DPAPI 为真', la_mod.HAS_DPAPI is True)

st = la_mod.SecureStorage()
enc = st._encrypt('Test@1234')
check('DPAPI 密文带前缀', enc.startswith('dpapi:'))
check('DPAPI 解密正确', st._decrypt(enc) == 'Test@1234')
check('DPAPI 密文不泄露明文', 'Test@1234' not in enc)

# 旧 Fernet 密文兼容
fernet = None
try:
    from cryptography.fernet import Fernet
    fernet = Fernet
except ImportError:
    pass
if fernet:
    old_token = fernet.generate_key()
    old_cipher = fernet(old_token)
    old_enc = old_cipher.encrypt('OldPass'.encode()).decode()
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        keyfile = os.path.join(td, 'secret.key')
        with open(keyfile, 'wb') as f:
            f.write(old_token)
        st2 = la_mod.SecureStorage()
        st2.key_file = keyfile
        check('旧 Fernet 密文兼容读取', st2._decrypt(old_enc) == 'OldPass')

# ============================================================ 配置密码
print('[4] 配置密码 PBKDF2')
import config_password as cfg
import tempfile as tf
orig_file = cfg.PASSWORD_FILE
try:
    with tf.TemporaryDirectory() as td:
        p = os.path.join(td, 'config_password.txt')
        cfg.PASSWORD_FILE = p
        # 初始无文件 -> 默认密码 admin123 被写入哈希
        check('默认密码校验通过', cfg.verify_config_password('admin123') is True)
        check('默认密码已迁移为哈希', cfg._read_raw().startswith('pbkdf2$'))
        check('错误密码被拒', cfg.verify_config_password('wrong') is False)
        # 旧明文迁移
        with open(p, 'w', encoding='utf-8') as f:
            f.write('495103')
        check('旧明文校验通过', cfg.verify_config_password('495103') is True)
        check('旧明文自动迁移', cfg._read_raw().startswith('pbkdf2$'))
        check('迁移后新格式仍可校验', cfg.verify_config_password('495103') is True)
        # 哈希格式损坏
        with open(p, 'w', encoding='utf-8') as f:
            f.write('pbkdf2$bad$bad$1000')
        check('损坏哈希格式拒绝', cfg.verify_config_password('495103') is False)
finally:
    cfg.PASSWORD_FILE = orig_file

# ============================================================ 汇总
print('\n' + '=' * 50)
print('PASS={} FAIL={}'.format(PASS, FAIL))
if FAILED:
    print('失败项:')
    for f in FAILED:
        print('  -', f)
sys.exit(1 if FAIL else 0)

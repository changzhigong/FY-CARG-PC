# -*- coding: utf-8 -*-
"""配置页访问密码（PBKDF2-HMAC-SHA256 + 随机盐，文件落在软件同目录）

历史问题：
- PASSWORD_FILE 原为相对路径 'config_password.txt'。打包后从桌面双击 exe，
  cwd 不是软件目录 → 读不到真实密码文件 → 误判"没设密码"，用默认 admin123
  生成哈希写到 cwd（桌面），导致用户输原来的密码也进不去。
  现在改为 config_path.app_dir() 拼绝对路径，与 warehouse_config.json 同策略。

密码生命周期：
- has_password()：是否已有有效密码（PBKDF2 哈希或旧明文）。无 → 首次进入引导设置。
- set_password(new)：首次设置（无需旧密码），写哈希。
- change_password(old, new)：校验旧密码后改密。
- verify_config_password(input)：校验，兼容旧明文并自动迁移为哈希。

对外 API：has_password / set_password / change_password / verify_config_password
"""
import hashlib
import hmac
import os

from config_path import app_dir

PASSWORD_FILE = os.path.join(app_dir(), 'config_password.txt')
PREFIX = 'pbkdf2'
ITERATIONS = 200000
SALT_BYTES = 16


def _read_raw():
    try:
        with open(PASSWORD_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def _hash(password, salt_bytes, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'),
                               salt_bytes, iterations)


def _is_hashed(raw):
    return raw.startswith(PREFIX + '$')


def _parse_hashed(raw):
    """返回 (salt_bytes, hash_bytes, iterations)，格式非法返回 None"""
    try:
        parts = raw.split('$')
        if len(parts) != 4 or parts[0] != PREFIX:
            return None
        salt = bytes.fromhex(parts[1])
        digest = bytes.fromhex(parts[2])
        iterations = int(parts[3])
        if not salt or not digest or iterations <= 0:
            return None
        return salt, digest, iterations
    except Exception:
        return None


def _write_hashed(password):
    """把密码以 PBKDF2 哈希写回软件同目录，限制 ACL（失败不阻断）"""
    salt = os.urandom(SALT_BYTES)
    digest = _hash(password, salt)
    raw = '{}${}${}${}'.format(PREFIX, salt.hex(), digest.hex(), ITERATIONS)
    try:
        os.makedirs(os.path.dirname(PASSWORD_FILE) or '.', exist_ok=True)
        with open(PASSWORD_FILE, 'w', encoding='utf-8') as f:
            f.write(raw)
    except Exception as e:
        print('[ConfigPwd] 写入哈希失败: {}'.format(e))
        return False
    try:
        if os.name == 'nt':
            import subprocess
            user = os.environ.get('USERNAME') or ''
            if user:
                subprocess.run(
                    ['icacls', PASSWORD_FILE, '/inheritance:r',
                     '/grant:r', '{}:F'.format(user)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=10)
    except Exception:
        pass
    return True


def has_password():
    """是否已有有效密码。False → 首次进入应引导用户自己设置"""
    raw = _read_raw()
    if not raw:
        return False
    if _is_hashed(raw):
        return _parse_hashed(raw) is not None
    # 旧明文视为已设置（保留历史兼容，用户可用原密码登录后改密）
    return True


def set_password(new_password):
    """首次设置密码（无需旧密码）。空密码不允许。返回 (ok, error)"""
    if new_password is None or not str(new_password).strip():
        return False, '密码不能为空'
    return _write_hashed(new_password), ''


def change_password(old_password, new_password):
    """校验旧密码后修改密码。返回 (ok, error)"""
    if not has_password():
        return False, '当前未设置密码'
    if not verify_config_password(old_password):
        return False, '原密码不正确'
    if new_password is None or not str(new_password).strip():
        return False, '新密码不能为空'
    if not _write_hashed(new_password):
        return False, '写入新密码失败'
    return True, ''


def verify_config_password(input_pwd):
    """校验密码；旧明文格式校验成功后自动迁移为哈希"""
    if input_pwd is None:
        return False
    raw = _read_raw()
    if not raw:
        # 无密码文件时不再默认放行 —— 由 has_password() 引导首次设置，
        # 这里保守拒绝，避免绕过首次设置流程。
        return False

    if _is_hashed(raw):
        parsed = _parse_hashed(raw)
        if not parsed:
            return False
        salt, digest, iterations = parsed
        candidate = _hash(input_pwd, salt, iterations)
        return hmac.compare_digest(candidate, digest)

    # 旧明文：恒定时间比较后迁移
    ok = hmac.compare_digest(str(input_pwd), raw)
    if ok:
        _write_hashed(raw)
    return ok

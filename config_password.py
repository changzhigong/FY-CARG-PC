# -*- coding: utf-8 -*-
"""配置页访问密码校验（PBKDF2-HMAC-SHA256 + 随机盐）

历史：config_password.txt 明文存放（如 "495103"），任何可读目录者都能拿到。
现在：文件改为 "pbkdf2$<salt_hex>$<hash_hex>" 格式；首次读取若为旧明文，
校验通过后自动迁移为哈希（保持用户无需手工改密的平滑升级）。

对外只暴露 verify_config_password(input_pwd) -> bool。
"""
import hashlib
import hmac
import os

PASSWORD_FILE = 'config_password.txt'
DEFAULT_PASSWORD = 'admin123'
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
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
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
    """把密码以 PBKDF2 哈希写回文件，限制文件访问（失败不阻断）"""
    salt = os.urandom(SALT_BYTES)
    digest = _hash(password, salt)
    raw = '{}${}${}${}'.format(PREFIX, salt.hex(), digest.hex(), ITERATIONS)
    try:
        with open(PASSWORD_FILE, 'w', encoding='utf-8') as f:
            f.write(raw)
    except Exception as e:
        print('[ConfigPwd] 写入哈希失败: {}'.format(e))
        return False
    # Windows 下限制 ACL，仅当前用户可读写
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


def verify_config_password(input_pwd):
    """校验配置页密码；旧明文格式校验成功后自动迁移为哈希"""
    if input_pwd is None:
        return False
    raw = _read_raw()
    if not raw:
        raw = DEFAULT_PASSWORD
        _write_hashed(raw)

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

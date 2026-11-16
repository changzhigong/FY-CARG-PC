# -*- coding: utf-8 -*-
"""配置页密码首次设置 / 改密 离线冒烟测试

覆盖：
- 密码文件绝对路径（软件同目录，cwd 无关）
- has_password 首次 False / 设置后 True
- set_password 首次设置、空密码拒绝
- change_password 校验旧密码、旧密码错误拒绝、成功改密
- verify_config_password 哈希校验、旧明文自动迁移
- 历史相对路径 bug 不再存在（不再用默认 admin123 兜底）
- main_app / config_manager 接线：首次引导、页内改密按钮
"""
import os
import sys
import tempfile

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


import config_password as cpwd
import config_path as cpath

print('=== 1. 绝对路径（软件同目录）===')
check('PASSWORD_FILE 是绝对路径', os.path.isabs(cpwd.PASSWORD_FILE))
check('PASSWORD_FILE 在 app_dir 下',
      os.path.dirname(cpwd.PASSWORD_FILE) == cpath.app_dir())
check('PASSWORD_FILE 文件名正确',
      os.path.basename(cpwd.PASSWORD_FILE) == 'config_password.txt')
check('源码里无相对路径字面量',
      "PASSWORD_FILE = 'config_password.txt'" not in src('config_password.py'))
check('不再有默认 admin123 常量',
      'DEFAULT_PASSWORD' not in src('config_password.py'))

print('=== 2. 首次设置流程 ===')
orig_file = cpwd.PASSWORD_FILE
with tempfile.TemporaryDirectory() as td:
    cpwd.PASSWORD_FILE = os.path.join(td, 'config_password.txt')
    check('首次无密码 has_password=False', cpwd.has_password() is False)
    check('首次 verify 任意密码都失败', cpwd.verify_config_password('admin123') is False)
    check('空密码设置被拒', cpwd.set_password('')[0] is False)
    ok, err = cpwd.set_password('MyNewPass2026')
    check('首次设置成功', ok is True and err == '')
    check('设置后 has_password=True', cpwd.has_password() is True)
    check('新密码可校验通过', cpwd.verify_config_password('MyNewPass2026') is True)
    check('错误密码被拒', cpwd.verify_config_password('495103') is False)
    with open(cpwd.PASSWORD_FILE, encoding='utf-8') as f:
        check('落地为 PBKDF2 哈希', f.read().strip().startswith('pbkdf2$'))

print('=== 3. 改密流程 ===')
with tempfile.TemporaryDirectory() as td:
    cpwd.PASSWORD_FILE = os.path.join(td, 'config_password.txt')
    cpwd.set_password('old_password')
    ok, err = cpwd.change_password('wrong_old', 'new_password')
    check('旧密码错误改密被拒', ok is False and '不正确' in err)
    check('改密失败后原密码仍有效', cpwd.verify_config_password('old_password') is True)
    ok, err = cpwd.change_password('old_password', 'new_password')
    check('正确改密成功', ok is True and err == '')
    check('改后新密码有效', cpwd.verify_config_password('new_password') is True)
    check('改后旧密码失效', cpwd.verify_config_password('old_password') is False)
    ok, err = cpwd.change_password('new_password', '')
    check('空新密码改密被拒', ok is False)

print('=== 4. 旧明文兼容与迁移 ===')
with tempfile.TemporaryDirectory() as td:
    cpwd.PASSWORD_FILE = os.path.join(td, 'config_password.txt')
    with open(cpwd.PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write('495103')
    check('旧明文视为已设置', cpwd.has_password() is True)
    check('旧明文密码校验通过', cpwd.verify_config_password('495103') is True)
    with open(cpwd.PASSWORD_FILE, encoding='utf-8') as f:
        check('旧明文校验后自动迁移哈希', f.read().strip().startswith('pbkdf2$'))
    check('迁移后仍可校验', cpwd.verify_config_password('495103') is True)

print('=== 5. cwd 无关性 ===')
orig_cwd = os.getcwd()
with tempfile.TemporaryDirectory() as td:
    cpwd.PASSWORD_FILE = os.path.join(td, 'pwd.txt')
    cpwd.set_password('CwdIndependent')
    os.chdir(td)
    try:
        check('切换 cwd 后校验仍通过',
              cpwd.verify_config_password('CwdIndependent') is True)
    finally:
        os.chdir(orig_cwd)
cpwd.PASSWORD_FILE = orig_file

print('=== 6. main_app 首次引导接线 ===')
ma = src('main_app.py')
check('open_config_page 检查 has_password', 'has_password()' in ma)
check('首次调用 set_password', 'set_password(pwd)' in ma)
check('首次提示文案', '首次设置' in ma)
check('两次确认提示', '请再次输入新密码以确认' in ma)
check('保留原校验', '_verify_config_password(pwd)' in ma)

print('=== 7. config_manager 页内改密接线 ===')
cm = src('config_manager.py')
check('有 change_password 方法', 'def change_password(self)' in cm)
check('操作区有修改密码按钮', 'text="修改密码"' in cm)
check('调用底层 change_password', 'change_password as do_change' in cm)
check('校验原密码输入', 'old_var' in cm and 'new_var' in cm and 'confirm_var' in cm)

print('=== 8. 遗留文件已清理 ===')
check('项目目录无明文密码文件（走首次设置）',
      not os.path.exists(os.path.join(ROOT, 'config_password.txt')))

print('=== 9. 真实导入 ===')
try:
    import config_manager
    import main_app
    check('import config_manager/main_app OK', True)
except Exception as e:
    check('import config_manager/main_app OK: {}'.format(e), False)

print('\n结果: PASS={} FAIL={}'.format(PASS, FAIL))
if FAILED:
    print('失败项:', FAILED)
    sys.exit(1)
print('全部通过')

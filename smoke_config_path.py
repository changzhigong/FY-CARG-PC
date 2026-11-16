# -*- coding: utf-8 -*-
"""warehouse_config.json 自包含配置路径离线冒烟测试

覆盖：
- config_path：app_dir 源码/打包两种模式、config_file_path 绝对路径与 cwd 无关、
  首次落地复制内置模板、已有文件不覆盖、读时自愈、落地失败不抛异常。
- 打包配置：release.yml 含 --add-data warehouse_config.json。
- 业务模块接线：main_app / picking_shipping / config_manager / waybill_manage 全用绝对路径。
- main.py 启动时显式落地。
"""
import ast
import json
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


import config_path as cp

print('=== 1. 源码模式路径 ===')
check('源码模式 is_frozen=False', cp.is_frozen() is False)
check('app_dir = 项目根', os.path.samefile(cp.app_dir(), ROOT))
check('config_file_path 绝对路径', os.path.isabs(cp.config_file_path()))
check('config_file_path 指向项目根/wcfg',
      cp.config_file_path() == os.path.join(ROOT, 'warehouse_config.json'))
check('实际配置文件存在', os.path.exists(cp.config_file_path()))

print('=== 2. cwd 无关性 ===')
orig_cwd = os.getcwd()
td = tempfile.mkdtemp()
os.chdir(td)
try:
    check('切换 cwd 后路径不变',
          cp.config_file_path() == os.path.join(ROOT, 'warehouse_config.json'))
    check('切换 cwd 仍能读到配置', os.path.exists(cp.config_file_path()))
finally:
    os.chdir(orig_cwd)   # 必须先切出，否则 Windows 下无法删除该目录
    try:
        os.rmdir(td)
    except OSError:
        pass

print('=== 3. 打包模式落地到 exe 同目录 ===')
import importlib
# 用临时目录模拟 exe 目录 + _MEIPASS
with tempfile.TemporaryDirectory() as exe_dir, tempfile.TemporaryDirectory() as bundle_dir:
    template = os.path.join(bundle_dir, 'warehouse_config.json')
    with open(template, 'w', encoding='utf-8') as f:
        json.dump({'WAREHOUSE_OPTIONS': {'测试库': 99}}, f, ensure_ascii=False)

    saved_frozen = getattr(sys, 'frozen', None)
    saved_meipass = getattr(sys, '_MEIPASS', None)
    saved_exe = sys.executable
    try:
        sys.frozen = True
        sys._MEIPASS = bundle_dir
        sys.executable = os.path.join(exe_dir, 'FY-CARG-PC.exe')
        importlib.reload(cp)

        check('打包模式 is_frozen=True', cp.is_frozen() is True)
        check('app_dir = exe 同目录', cp.app_dir() == exe_dir)
        check('内置模板路径在 _MEIPASS',
              cp.bundled_template_path() == template)
        expected = os.path.join(exe_dir, 'warehouse_config.json')
        # 首次落地（必须在任何 config_file_path 调用之前，否则读时自愈已抢先落地）
        path, created, err = cp.ensure_config_file()
        check('首次落地成功', created is True and err == '')
        check('落地到 exe 同目录', os.path.exists(expected))
        with open(expected, encoding='utf-8') as f:
            check('落地内容来自内置模板',
                  json.load(f)['WAREHOUSE_OPTIONS']['测试库'] == 99)
        check('配置路径指向 exe 同目录', cp.config_file_path() == expected)

        # 已有文件不覆盖
        with open(expected, 'w', encoding='utf-8') as f:
            json.dump({'WAREHOUSE_OPTIONS': {'用户改的库': 1}}, f)
        path2, created2, err2 = cp.ensure_config_file()
        check('已存在不重复落地', created2 is False and err2 == '')
        with open(expected, encoding='utf-8') as f:
            check('用户修改未被覆盖',
                  '用户改的库' in json.load(f)['WAREHOUSE_OPTIONS'])

        # 读时自愈：删掉目标后调 config_file_path 应自动重建
        os.remove(expected)
        p3 = cp.config_file_path()
        check('读时自愈重建文件', os.path.exists(p3))
    finally:
        # 恢复 sys 状态，reload 回源码模式
        if saved_frozen is None:
            if hasattr(sys, 'frozen'):
                del sys.frozen
        else:
            sys.frozen = saved_frozen
        if saved_meipass is None:
            if hasattr(sys, '_MEIPASS'):
                del sys._MEIPASS
        else:
            sys._MEIPASS = saved_meipass
        sys.executable = saved_exe
        importlib.reload(cp)

print('=== 4. 落地失败不抛异常 ===')
with tempfile.TemporaryDirectory() as exe_dir:
    saved_frozen = getattr(sys, 'frozen', None)
    saved_exe = sys.executable
    try:
        sys.frozen = True
        sys.executable = os.path.join(exe_dir, 'app.exe')
        importlib.reload(cp)
        # 模板也不存在（_MEIPASS 指向空目录）
        saved_meipass = getattr(sys, '_MEIPASS', None)
        sys._MEIPASS = os.path.join(exe_dir, 'nonexist')
        path, created, err = cp.ensure_config_file()
        check('模板缺失返回 error 不抛异常', created is False and '不存在' in err)
        if saved_meipass is None:
            if hasattr(sys, '_MEIPASS'):
                del sys._MEIPASS
        else:
            sys._MEIPASS = saved_meipass
    finally:
        if saved_frozen is None:
            if hasattr(sys, 'frozen'):
                del sys.frozen
        else:
            sys.frozen = saved_frozen
        sys.executable = saved_exe
        importlib.reload(cp)

print('=== 5. release.yml 打包资源 ===')
yml = src(os.path.join('.github', 'workflows', 'release.yml'))
check('add-data 内置配置模板', '--add-data "warehouse_config.json;."' in yml)

print('=== 6. 业务模块接线（绝对路径）===')
for fname in ('main_app.py', 'picking_shipping.py', 'config_manager.py',
              'waybill_manage.py'):
    code = src(fname)
    check('{} import config_path'.format(fname),
          'from config_path import' in code)
    # AST 精确检查 open() 调用的首参，避免注释/文档字符串误伤
    _tree = ast.parse(code)
    _bad_open = False
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Name) and \
                _n.func.id == 'open' and _n.args:
            _arg = _n.args[0]
            if isinstance(_arg, ast.Constant) and 'warehouse_config.json' in str(_arg.value):
                _bad_open = True
    check('{} 无相对路径 open'.format(fname), not _bad_open)

print('=== 7. main.py 启动落地 ===')
mp = src('main.py')
check('main.py import ensure_config_file', 'from config_path import ensure_config_file' in mp)
# 取最后一个 def main(): 后的活跃代码（前面注释里有多个）
_main_body = mp[mp.rfind('def main():'):]
check('main() 调用 ensure_config_file', 'ensure_config_file()' in _main_body)

print('=== 8. 真实导入 ===')
try:
    import main_app
    check('import main_app OK', True)
except Exception as e:
    check('import main_app OK: {}'.format(e), False)

print('\n结果: PASS={} FAIL={}'.format(PASS, FAIL))
if FAILED:
    print('失败项:', FAILED)
    sys.exit(1)
print('全部通过')

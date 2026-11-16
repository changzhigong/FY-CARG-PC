# -*- coding: utf-8 -*-
"""版本自增脚本（自动发版流水线用）

参考 fycarg-pda/.github/workflows/release.yml 的自动发版思路，适配本仓库：
本仓库**没有独立分发仓库**，Release/tag 就在 changzhigong/FY-CARG-PC 自身，
所以「当前版本」直接从本仓库的 latest release 取（失败依次回退 git tag、VERSION 文件）。

行为：
  1. 解析当前版本（GitHub latest release tag → 本地 git tag v* → VERSION 文件）
  2. 按 --bump（patch/minor/major，默认 patch）自增
  3. 写回 VERSION 与 BUILD_DATE 两个文件（--dry-run 时不写）
  4. 输出 old/new（GITHUB_OUTPUT 存在时按 Actions 格式输出，供后续步骤引用）

用法：
  python scripts/bump_version.py --dry-run                  # 只看下一个版本号
  python scripts/bump_version.py --bump minor                # 次版本 +1（x.Y+1.0）
  python scripts/bump_version.py                             # 补丁 +1（默认）
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date

# Windows runner 默认 stdout 编码为 cp1252，print 中文会抛 UnicodeEncodeError
# （2026-11-16 首次发版实测失败点）。强制 UTF-8，确保 CI 日志中文正常输出。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

VERSION_FILE = 'VERSION'
BUILD_DATE_FILE = 'BUILD_DATE'
DEFAULT_REPO = 'changzhigong/FY-CARG-PC'
TAG_RE = re.compile(r'^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$')


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_local_version():
    """回退来源：VERSION 文件"""
    path = os.path.join(repo_root(), VERSION_FILE)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            ver = f.read().strip()
        if ver:
            return ver
    except OSError:
        pass
    return None


def parse_version(text):
    m = TAG_RE.match((text or '').strip())
    if not m:
        return None
    return (int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0))


def fetch_latest_release_version(repo, token=''):
    """从 GitHub latest release 取版本号（公开仓库无需 token）"""
    import urllib.request
    url = 'https://api.github.com/repos/{}/releases/latest'.format(repo)
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'FY-CARG-PC-bump-version',
    })
    if token:
        req.add_header('Authorization', 'Bearer {}'.format(token))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return (data.get('tag_name') or '').strip() or None
    except Exception as e:
        print('[bump] GitHub latest release 获取失败: {}'.format(e))
        return None


def fetch_latest_git_tag():
    """回退来源：本地/远端 git tag v* 中最大的版本号"""
    try:
        out = subprocess.check_output(
            ['git', 'tag', '--list', 'v*'], cwd=repo_root(),
            stderr=subprocess.DEVNULL).decode('utf-8', 'ignore')
    except Exception as e:
        print('[bump] git tag 读取失败: {}'.format(e))
        return None
    vers = [parse_version(t) for t in out.split()]
    vers = [v for v in vers if v]
    if not vers:
        return None
    return '.'.join(str(x) for x in max(vers))


def current_version(repo, token=''):
    tag = fetch_latest_release_version(repo, token)
    if tag and parse_version(tag):
        print('[bump] 当前版本来源: GitHub latest release ({})'.format(tag))
        return tag.lstrip('vV')
    tag = fetch_latest_git_tag()
    if tag:
        print('[bump] 当前版本来源: git tag (v{})'.format(tag))
        return str(tag).lstrip('vV')
    local = read_local_version()
    print('[bump] 当前版本来源: {} 文件 ({})'.format(VERSION_FILE, local))
    return local or '0.0.0'


def bump_version(version, level):
    parts = parse_version(version) or (0, 0, 0)
    major, minor, patch = parts
    if level == 'major':
        return '{}.{}.{}'.format(major + 1, 0, 0)
    if level == 'minor':
        return '{}.{}.{}'.format(major, minor + 1, 0)
    return '{}.{}.{}'.format(major, minor, patch + 1)


def write_files(new_version, build_date, dry_run=False):
    if dry_run:
        print('[bump] dry-run: 不写入文件')
        return
    root = repo_root()
    with open(os.path.join(root, VERSION_FILE), 'w', encoding='utf-8') as f:
        f.write(new_version + '\n')
    with open(os.path.join(root, BUILD_DATE_FILE), 'w', encoding='utf-8') as f:
        f.write(build_date + '\n')
    print('[bump] 已写入 {} = {} / {} = {}'.format(
        VERSION_FILE, new_version, BUILD_DATE_FILE, build_date))


def emit_outputs(old_version, new_version):
    """GITHUB_OUTPUT（Actions）与标准输出双写"""
    pairs = [('old', old_version), ('new', new_version)]
    out_file = os.environ.get('GITHUB_OUTPUT')
    if out_file:
        with open(out_file, 'a', encoding='utf-8') as f:
            for k, v in pairs:
                f.write('{}={}\n'.format(k, v))
    for k, v in pairs:
        print('{}={}'.format(k, v))


def main(argv=None):
    ap = argparse.ArgumentParser(description='自动版本自增')
    ap.add_argument('--bump', choices=['patch', 'minor', 'major'], default='patch',
                    help='自增级别，默认 patch')
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY') or DEFAULT_REPO,
                    help='owner/repo，默认取环境变量 GITHUB_REPOSITORY 或 ' + DEFAULT_REPO)
    ap.add_argument('--token', default=os.environ.get('GITHUB_TOKEN')
                    or os.environ.get('FYCARG_UPDATE_TOKEN') or '',
                    help='可选，私有仓库/提额用 GitHub token')
    ap.add_argument('--dry-run', action='store_true', help='只计算不写文件')
    args = ap.parse_args(argv)

    old = (current_version(args.repo, args.token) or '0.0.0').lstrip('vV')
    if parse_version(old) is None:
        print('[bump] 无法解析当前版本: {}'.format(old))
        return 1
    new = bump_version(old, args.bump)
    build_date = date.today().strftime('%Y-%m-%d')
    print('[bump] {} ({}) → {} ({})'.format(old, args.bump, new,
                                            'dry-run' if args.dry_run else 'write'))
    write_files(new, build_date, dry_run=args.dry_run)
    emit_outputs(old, new)
    return 0


if __name__ == '__main__':
    sys.exit(main())

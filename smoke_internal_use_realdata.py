# -*- coding: utf-8 -*-
"""用 internalUser 真实接口报文验证「领用人 → 领用部门」解析与带出

数据来源：GET https://xb.fy-carg.com/dcscloud.basedata//basedata/employees/employees/internalUser
（2026-09-08 实测，resultCode=200，data 为数组，字段 EMPLOYEE_NAME / EMPLOYEE_ID / EMP_ID /
 PHONE / ORG_NAME / ORGANIZATION_ID）

验证要点：
1. 解析字段与安卓端一致（name/id/phone/orgId/orgName）
2. 仓库岗：领用人 ORGANIZATION_ID 与 USE_DEPT_MAP 相同（故旧 bug 不易暴露）
3. 职能岗（财务/采购/客服等）与顶级组织：DEPARTMENT_ID 必须取领用人组织，
   ORGANIZATION_ID 必须取仓库映射 —— 两者不同源，正是本次修复的关键
"""
import sys
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: "ok"
mb.showerror = lambda *a, **k: "ok"
mb.showwarning = lambda *a, **k: "ok"

import internal_use_manage as m

PASS, FAIL = [], []


def check(name, cond, extra=''):
    if cond:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL  %s  %s" % (name, extra))


# 真实报文抽样（覆盖仓库岗 / 职能岗 / 顶级组织 / 合并账号）
RAW_SAMPLE = [
    {"EMPLOYEE_NAME": "郑州晖锦_系统管理员", "EMP_ID": 1, "EMPLOYEE_ID": 1,
     "ORG_NAME": "郑州晖锦", "ORGANIZATION_ID": 1, "PHONE": "13800000000"},
    {"EMPLOYEE_NAME": "郭佳", "EMP_ID": 1191, "EMPLOYEE_ID": 1191,
     "ORG_NAME": "商丘库", "ORGANIZATION_ID": 1152, "PHONE": "13523495103"},
    {"EMPLOYEE_NAME": "司林林", "EMP_ID": 1208, "EMPLOYEE_ID": 1208,
     "ORG_NAME": "郑州库", "ORGANIZATION_ID": 1148, "PHONE": "18595440845"},
    {"EMPLOYEE_NAME": "韩飞宇", "EMP_ID": 1189, "EMPLOYEE_ID": 1189,
     "ORG_NAME": "西安库", "ORGANIZATION_ID": 1149, "PHONE": "18846035737"},
    {"EMPLOYEE_NAME": "范江飞", "EMP_ID": 1185, "EMPLOYEE_ID": 1185,
     "ORG_NAME": "财务部", "ORGANIZATION_ID": 1143, "PHONE": "15837427917"},
    {"EMPLOYEE_NAME": "游文华", "EMP_ID": 1183, "EMPLOYEE_ID": 1183,
     "ORG_NAME": "采购部", "ORGANIZATION_ID": 1145, "PHONE": "15609310333"},
    {"EMPLOYEE_NAME": "常静", "EMP_ID": 1199, "EMPLOYEE_ID": 1199,
     "ORG_NAME": "客服部", "ORGANIZATION_ID": 1157, "PHONE": "18706882365"},
    {"EMPLOYEE_NAME": "李振东", "EMP_ID": 1184, "EMPLOYEE_ID": 1184,
     "ORG_NAME": "物流部", "ORGANIZATION_ID": 1147, "PHONE": "18392137873"},
    {"EMPLOYEE_NAME": "高军安", "EMP_ID": 1252, "EMPLOYEE_ID": 1252,
     "ORG_NAME": "榆林库", "ORGANIZATION_ID": 1166, "PHONE": "13474399506"},
    {"EMPLOYEE_NAME": "王俭", "EMP_ID": 1265, "EMPLOYEE_ID": 1265,
     "ORG_NAME": "银川库", "ORGANIZATION_ID": 1164, "PHONE": "13309577715"},
    {"EMPLOYEE_NAME": "朱静，寻磊", "EMP_ID": 1281, "EMPLOYEE_ID": 1281,
     "ORG_NAME": "西安库", "ORGANIZATION_ID": 1149, "PHONE": "13696847046"},
]


def parse_users(arr):
    """复刻 internal_use_manage._user_thread 的解析逻辑"""
    items = []
    for u in arr:
        if not isinstance(u, dict):
            continue
        name = u.get('EMPLOYEE_NAME') or u.get('name') or ''
        if not name:
            continue
        items.append({
            'name': name,
            'id': str(u.get('EMPLOYEE_ID') or u.get('EMP_ID') or u.get('id') or ''),
            'phone': u.get('PHONE') or u.get('phone') or '',
            'orgId': u.get('ORGANIZATION_ID') or '',
            'orgName': u.get('ORG_NAME') or '',
        })
    return items


class FakeController:
    def __init__(self):
        self.session = None
        self.options = {"商丘库": 11, "郑州库": 6, "西安库": 7}

    def check_login_status(self, r):
        return False

    def after(self, ms, func=None, *a):
        if func:
            func(*a)


def main():
    root = tk.Tk()
    root.withdraw()
    ctrl = FakeController()
    page = m.InternalUseManagePage(ttk.Frame(root), ctrl)

    print("\n[1] 真实报文解析")
    users = parse_users(RAW_SAMPLE)
    check("全部 11 条均解析出姓名", len(users) == 11, str(len(users)))
    gj = next(u for u in users if u['name'] == '郭佳')
    check("郭佳 id = 1191（EMPLOYEE_ID）", gj['id'] == '1191', gj['id'])
    check("郭佳 phone = 13523495103", gj['phone'] == '13523495103', gj['phone'])
    check("郭佳 orgId = 1152（ORGANIZATION_ID）", gj['orgId'] == 1152, repr(gj['orgId']))
    check("郭佳 orgName = 商丘库（ORG_NAME）", gj['orgName'] == '商丘库', gj['orgName'])
    admin = users[0]
    check("系统管理员 orgId = 1（顶级组织）", admin['orgId'] == 1, repr(admin['orgId']))
    hb = next(u for u in users if u['name'] == '范江飞')
    check("范江飞为职能岗 财务部 1143", hb['orgId'] == 1143 and hb['orgName'] == '财务部')

    page._apply_users(users)

    def pick(name):
        """模拟下拉选中：按姓名取显示文本再 set，然后触发选择回调"""
        page.user_cb.set(page._user_display(name))
        page._on_edit_user()

    print("\n[2] 仓库岗：领用人组织 == 仓库映射（旧 bug 不易暴露的场景）")
    page.warehouse_var.set("商丘库")
    page.open_edit(None)
    check("ORGANIZATION_ID = 商丘库映射 1152", page.edit_org_id == 1152, repr(page.edit_org_id))
    pick("郭佳")
    check("DEPARTMENT_ID = 1152", page.edit_dept_id == 1152, repr(page.edit_dept_id))
    check("DEPARTMENT_NAME = 商丘库", page.edit_dept_name == '商丘库')
    check("此时 DEPARTMENT_ID 与 ORGANIZATION_ID 恰好相同（1152）",
          page.edit_dept_id == page.edit_org_id)

    print("\n[3] 职能岗：两者必须不同源（旧 bug 会写错的场景）")
    pick("范江飞")
    check("DEPARTMENT_ID = 领用人组织 1143（财务部）", page.edit_dept_id == 1143,
          repr(page.edit_dept_id))
    check("DEPARTMENT_NAME = 财务部", page.edit_dept_name == '财务部')
    check("ORGANIZATION_ID 仍为仓库映射 1152（不被领用人污染）",
          page.edit_org_id == 1152, repr(page.edit_org_id))
    check("★ DEPARTMENT_ID ≠ ORGANIZATION_ID（旧实现此二者会相等）",
          page.edit_dept_id != page.edit_org_id,
          "dept=%s org=%s" % (page.edit_dept_id, page.edit_org_id))

    print("\n[4] 顶级组织（郑州晖锦 id=1）")
    pick("郑州晖锦_系统管理员")
    check("DEPARTMENT_ID = 1", page.edit_dept_id == 1, repr(page.edit_dept_id))
    check("DEPARTMENT_NAME = 郑州晖锦", page.edit_dept_name == '郑州晖锦')
    check("ORGANIZATION_ID 仍为 1152", page.edit_org_id == 1152, repr(page.edit_org_id))

    print("\n[5] 提交报文（新建即提交，职能岗）")
    pick("游文华")                      # 采购部 1145
    page.edit_items = [{'_orig': None, 'PART_ID': 'P1', 'PART_NO': 'XY-1',
                        'PART_NAME': '玻璃', 'BRAND_ID': 1, 'BRAND_NAME': '信义',
                        'COST_PRICE': 10, 'USE_NUM': 2, 'OUT_LOCATION': 'A-01',
                        'AVAILABLE_STOCK_QUANTITY': 99, 'STORAGE_CODE': 'SQ',
                        'STORAGE_NAME': '商丘库', 'WAREHOUSE_ID': 11, 'loList': []}]
    page.edit_remark_var.set("真实数据验证")
    page.edit_raw = {}
    p = page.build_payload('submit')
    print("       DEPARTMENT_ID=%s(%s)  ORGANIZATION_ID=%s  USE_MAN=%s" % (
        p.get('DEPARTMENT_ID'), p.get('DEPARTMENT_NAME'),
        p.get('ORGANIZATION_ID'), p.get('USE_MAN')))
    check("DEPARTMENT_ID = 采购部 1145", p.get('DEPARTMENT_ID') == 1145)
    check("DEPARTMENT_NAME = 采购部", p.get('DEPARTMENT_NAME') == '采购部')
    # 新建单不带 ORGANIZATION_ID：web 端 resetFormVo 无此字段，HAR add 报文里的是残留脏数据。
    # 页面状态 edit_org_id 仍为仓库映射 1152，只用于既有单（edit_raw 缺该字段时兜底）。
    check("新建不带 ORGANIZATION_ID（web 端 resetFormVo 无此字段）",
          'ORGANIZATION_ID' not in p, repr(p.get('ORGANIZATION_ID')))
    check("★ DEPARTMENT_ID=1145 不被仓库映射 1152 污染（两者不同源）",
          p.get('DEPARTMENT_ID') == 1145 and page.edit_org_id == 1152,
          "DEPARTMENT_ID=%r edit_org_id=%r" % (p.get('DEPARTMENT_ID'), page.edit_org_id))
    check("USE_MAN_ID = 1183", p.get('USE_MAN_ID') == '1183')
    check("USE_PHONE = 15609310333", p.get('USE_PHONE') == '15609310333')
    # 下拉显示带部门后缀，但报文必须是纯姓名，不能把「姓名（部门）」写进 USE_MAN
    check("★ USE_MAN 为纯姓名（不含部门后缀）", p.get('USE_MAN') == '游文华',
          repr(p.get('USE_MAN')))

    print("\n[5b] 下拉显示文本")
    check("郭佳 → 郭佳（商丘库）", page._user_display('郭佳') == '郭佳（商丘库）',
          page._user_display('郭佳'))
    check("范江飞 → 范江飞（财务部）", page._user_display('范江飞') == '范江飞（财务部）',
          page._user_display('范江飞'))
    check("顶级组织也带出", page._user_display('郑州晖锦_系统管理员') == '郑州晖锦_系统管理员（郑州晖锦）',
          page._user_display('郑州晖锦_系统管理员'))
    check("未知名原样返回", page._user_display('不存在的人') == '不存在的人')
    check("下拉选项全部为显示文本",
          all('（' in d or not u.get('orgName') for d, u in zip(page.user_names, users)))

    print("\n[6] 重名/合并账号不影响匹配")
    pick("朱静，寻磊")
    check("合并账号名可正常带出部门 西安库 1149",
          page.edit_dept_id == 1149 and page.edit_dept_name == '西安库',
          "%s / %s" % (page.edit_dept_id, page.edit_dept_name))

    print("\n[7] 编辑态开窗：下拉按姓名回填显示文本")
    page.edit_use_man = '郭佳'
    page.edit_use_man_id = '1191'
    page.edit_use_phone = '13523495103'
    page.edit_dept_id = 1152
    page.edit_dept_name = '商丘库'
    page._show_edit_window()
    check("下拉显示 郭佳（商丘库）", page.user_var.get() == '郭佳（商丘库）',
          page.user_var.get())
    check("部门展示同步为 商丘库", page.edit_dept_var.get() == '商丘库',
          page.edit_dept_var.get())
    # 不重选领用人直接保存，报文应保持主单原值（安卓 editPopup 亦不重算）
    p2 = page.build_payload('edit')
    check("未重选领用人时 USE_MAN 仍为纯姓名", p2.get('USE_MAN') == '郭佳',
          repr(p2.get('USE_MAN')))
    check("未重选领用人时 DEPARTMENT_ID 保持 1152", p2.get('DEPARTMENT_ID') == 1152,
          repr(p2.get('DEPARTMENT_ID')))

    root.destroy()
    print("\n" + "=" * 60)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  -", f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

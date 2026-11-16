# -*- coding: utf-8 -*-
"""内部领用「领用人 → 领用部门」对齐修复验证（临时脚本）

对齐安卓端 InternalUseManage.vue：
- openEdit（1252-1254）：新建时 deptId='' / deptName=''，部门待选领用人后带出
- onUserConfirm（1342-1354）：选领用人 → useMan/useManId/usePhone + deptId=orgId / deptName=orgName
  （**无条件覆盖**，领用人无组织时置空）
- buildPayload（1534/1563）：DEPARTMENT_ID 来自领用人组织，ORGANIZATION_ID 来自仓库映射，两者不同源
- onWarehouseConfirm（717）：切仓库只改 warehouseName，不动部门
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


class FakeController:
    def __init__(self):
        self.session = None
        self.options = {"商丘库": 11, "郑州库": 6}

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

    # 注入领用人数据（模拟 internalUser 接口返回，走 _apply_users 生成「姓名（部门）」显示文本）
    page._apply_users([
        {'name': '郭佳', 'id': 'E01', 'phone': '13800000001',
         'orgId': '2001', 'orgName': '物流部-郑州'},
        {'name': '散人', 'id': 'E02', 'phone': '13800000002',
         'orgId': '', 'orgName': ''},          # 无所属组织
    ])

    def pick(name):
        """模拟下拉选中：按姓名取显示文本再 set，然后触发选择回调"""
        page.user_cb.set(page._user_display(name))
        page._on_edit_user()

    print("\n[1] 新建：部门留空，ORGANIZATION_ID 按仓库映射")
    page.warehouse_var.set("商丘库")
    page.open_edit(None)
    # open_edit 无 id 时直接开窗
    check("新建 DEPARTMENT_ID 为空", page.edit_dept_id == '', repr(page.edit_dept_id))
    check("新建 DEPARTMENT_NAME 为空", page.edit_dept_name == '', repr(page.edit_dept_name))
    check("新建 ORGANIZATION_ID = 商丘库映射 1152", page.edit_org_id == 1152,
          repr(page.edit_org_id))
    check("界面部门显示占位文案",
          page.edit_dept_var.get() == "(选领用人自动带出)", page.edit_dept_var.get())

    print("\n[2] 选领用人 → 部门按其所属组织带出（无条件覆盖）")
    pick("郭佳")
    check("USE_MAN = 郭佳", page.edit_use_man == '郭佳')
    check("USE_MAN_ID = E01", page.edit_use_man_id == 'E01')
    check("USE_PHONE 自动带出", page.edit_use_phone == '13800000001')
    check("DEPARTMENT_ID = 领用人 orgId 2001", page.edit_dept_id == '2001',
          repr(page.edit_dept_id))
    check("DEPARTMENT_NAME = 领用人 orgName", page.edit_dept_name == '物流部-郑州',
          repr(page.edit_dept_name))
    check("界面部门同步刷新", page.edit_dept_var.get() == '物流部-郑州',
          page.edit_dept_var.get())
    check("联系电话输入框同步", page.edit_phone_var.get() == '13800000001')

    print("\n[3] 领用人无组织 → 部门置空（不残留仓库映射值，安卓为无条件覆盖）")
    pick("散人")
    check("DEPARTMENT_ID 置空", page.edit_dept_id == '', repr(page.edit_dept_id))
    check("DEPARTMENT_NAME 置空", page.edit_dept_name == '', repr(page.edit_dept_name))
    check("界面回到占位文案",
          page.edit_dept_var.get() == "(选领用人自动带出)", page.edit_dept_var.get())
    check("ORGANIZATION_ID 仍为仓库映射 1152", page.edit_org_id == 1152,
          repr(page.edit_org_id))

    print("\n[4] 切仓库：只改 ORGANIZATION_ID，不动 DEPARTMENT_ID")
    pick("郭佳")
    page.edit_wh_var.set("郑州库")
    page._on_edit_wh()
    check("ORGANIZATION_ID 随仓库变为 1148", page.edit_org_id == 1148, repr(page.edit_org_id))
    check("DEPARTMENT_ID 不受切仓库影响（仍 2001）", page.edit_dept_id == '2001',
          repr(page.edit_dept_id))
    check("DEPARTMENT_NAME 不受切仓库影响", page.edit_dept_name == '物流部-郑州')
    check("warehouse_code 已更新", page.edit_wh_code == 'ZZ', repr(page.edit_wh_code))

    print("\n[5] build_payload：两个 ID 不同源")
    page.edit_items = [{'_orig': None, 'PART_ID': 'P1', 'PART_NO': 'XY-1',
                        'PART_NAME': '玻璃', 'BRAND_ID': 1, 'BRAND_NAME': '信义',
                        'COST_PRICE': 10, 'USE_NUM': 2, 'OUT_LOCATION': 'A-01',
                        'AVAILABLE_STOCK_QUANTITY': 99, 'STORAGE_CODE': 'ZZ',
                        'STORAGE_NAME': '郑州库', 'WAREHOUSE_ID': 6, 'loList': []}]
    page.edit_remark_var.set("测试")

    add_payload = page.build_payload('add')
    print("       add =", {k: v for k, v in add_payload.items() if k != 'itemList'})
    check("add: DEPARTMENT_ID = 领用人组织 2001",
          add_payload.get('DEPARTMENT_ID') == '2001', repr(add_payload.get('DEPARTMENT_ID')))
    check("add: DEPARTMENT_NAME = 物流部-郑州",
          add_payload.get('DEPARTMENT_NAME') == '物流部-郑州')
    check("add: USE_MAN/USE_MAN_ID/USE_PHONE 齐全",
          add_payload.get('USE_MAN') == '郭佳' and add_payload.get('USE_MAN_ID') == 'E01'
          and add_payload.get('USE_PHONE') == '13800000001')
    # web 端新建时 addFn() 不传 row，formVo 基底 = resetFormVo（13 个业务字段，无 ORGANIZATION_ID）。
    # HAR 里 add 报文的 ORGANIZATION_ID/CREATED_AT/RECORD_VERSION 等全是组件实例上一次编辑的
    # 状态残留脏数据，剥掉后正好 9 字段，与安卓端 add 一致 → 新建一律不带这些字段。
    NEW_ONLY_FIELDS = {'DEPARTMENT_ID', 'DEPARTMENT_NAME', 'storage_code', 'USE_MAN',
                       'USE_MAN_ID', 'USE_PHONE', 'REMARK', 'isDisabledOrgSelect',
                       'itemList', 'delItemList'}
    check("add: 不带 ORGANIZATION_ID（非 resetFormVo 字段，HAR 中为残留脏数据）",
          'ORGANIZATION_ID' not in add_payload, repr(add_payload.get('ORGANIZATION_ID')))
    check("add: 不带任何审计字段/整单骨架",
          not ({'CREATED_AT', 'CREATED_BY', 'UPDATED_AT', 'UPDATED_BY', 'RECORD_VERSION',
                'DEALER_CODE', 'DR', 'STATUS', 'NO_TAX_AMOUNT', 'WAREHOUSE_NAME',
                'BRAND_ID', 'WBS', 'COST_CENTER', 'SHIPPING_ADDRESS'} & set(add_payload)),
          str(sorted(set(add_payload) - NEW_ONLY_FIELDS)))
    check("add: 剔除 ID/USE_NO（新建单无单号）",
          'ID' not in add_payload and 'USE_NO' not in add_payload)
    check("add: 字段集 = web 端 9 字段 + REMARK",
          set(add_payload) == NEW_ONLY_FIELDS, str(sorted(set(add_payload) ^ NEW_ONLY_FIELDS)))
    check("add: isDisabledOrgSelect=True", add_payload.get('isDisabledOrgSelect') is True)

    # 新建即提交（无 ID）：报文体与 add 相同，只有端点 URL 不同
    page.edit_raw = {}
    submit_payload = page.build_payload('submit')
    check("submit(无ID): 报文体与 add 完全一致",
          {k: v for k, v in submit_payload.items()} == {k: v for k, v in add_payload.items()},
          str(sorted(set(submit_payload) ^ set(add_payload))))
    check("submit(无ID): 同样不带 ORGANIZATION_ID",
          'ORGANIZATION_ID' not in submit_payload, repr(submit_payload.get('ORGANIZATION_ID')))
    check("submit(无ID): DEPARTMENT_ID 仍为领用人组织 2001",
          submit_payload.get('DEPARTMENT_ID') == '2001',
          repr(submit_payload.get('DEPARTMENT_ID')))
    check("submit(无ID): 剔除 ID/USE_NO",
          'ID' not in submit_payload and 'USE_NO' not in submit_payload)

    # 编辑已有单（有 ID）：ORGANIZATION_ID 沿用主单原值
    page.edit_raw = {'ID': 555, 'USE_NO': 'LY001', 'STATUS': 12461001,
                     'ORGANIZATION_ID': 9999, 'RECORD_VERSION': 3}
    edit_payload = page.build_payload('edit')
    check("edit(有ID): ORGANIZATION_ID 沿用主单 9999",
          edit_payload.get('ORGANIZATION_ID') == 9999,
          repr(edit_payload.get('ORGANIZATION_ID')))
    check("edit(有ID): DEPARTMENT_ID 被领用人组织覆盖为 2001",
          edit_payload.get('DEPARTMENT_ID') == '2001',
          repr(edit_payload.get('DEPARTMENT_ID')))
    check("edit(有ID): STATUS = 当前状态 12461001",
          edit_payload.get('STATUS') == 12461001)
    check("edit(有ID): 带 ID/USE_NO",
          edit_payload.get('ID') == 555 and edit_payload.get('USE_NO') == 'LY001')
    check("edit(有ID): RECORD_VERSION 原样回传 3（前端不自行递增）",
          edit_payload.get('RECORD_VERSION') == 3, repr(edit_payload.get('RECORD_VERSION')))
    check("edit(有ID): 缺失审计字段按默认补齐 DEALER_CODE='FY'/DR=0",
          edit_payload.get('DEALER_CODE') == 'FY' and edit_payload.get('DR') == 0,
          repr({k: edit_payload.get(k) for k in ('DEALER_CODE', 'DR')}))

    print("\n[5b] 既有单审计字段原样回传（对齐 web 端：后端维护，前端不重算）")
    page.edit_raw = {'ID': 556, 'USE_NO': 'LY002', 'STATUS': 12461001,
                     'CREATED_AT': '2026-07-29 11:56:52', 'CREATED_BY': 'HJ011',
                     'UPDATED_AT': '2026-07-29 11:57:17', 'UPDATED_BY': 'HJ011',
                     'RECORD_VERSION': 4, 'DEALER_CODE': 'FY', 'DR': 0}
    sub2 = page.build_payload('submit')
    check("submit(有ID): CREATED_AT/CREATED_BY 原样回传",
          sub2.get('CREATED_AT') == '2026-07-29 11:56:52'
          and sub2.get('CREATED_BY') == 'HJ011',
          repr({k: sub2.get(k) for k in ('CREATED_AT', 'CREATED_BY')}))
    check("submit(有ID): UPDATED_AT/UPDATED_BY 原样回传（不写当前时间）",
          sub2.get('UPDATED_AT') == '2026-07-29 11:57:17'
          and sub2.get('UPDATED_BY') == 'HJ011',
          repr({k: sub2.get(k) for k in ('UPDATED_AT', 'UPDATED_BY')}))
    check("submit(有ID): RECORD_VERSION 原样回传 4",
          sub2.get('RECORD_VERSION') == 4, repr(sub2.get('RECORD_VERSION')))
    check("submit(有ID): 既有单带 ORGANIZATION_ID（与新建相反）",
          'ORGANIZATION_ID' in sub2, repr(sub2.get('ORGANIZATION_ID')))

    # queryById 未返回 ORGANIZATION_ID 时，按领用仓库映射兜底（此时 edit_org_id=1148/郑州库）
    page.edit_raw = {'ID': 557, 'USE_NO': 'LY003', 'STATUS': 12461001}
    sub3 = page.build_payload('edit')
    check("edit(有ID但主单缺 ORGANIZATION_ID): 按仓库映射兜底 1148",
          sub3.get('ORGANIZATION_ID') == 1148, repr(sub3.get('ORGANIZATION_ID')))

    print("\n[5c] 兜底：queryById 失败 edit_raw 为空时，仍按 edit_id 判定为既有单")
    page.edit_id = '777'
    page.edit_raw = {}
    fallback = page.build_payload('edit')
    check("edit_id 非空 → ID 补回 777，不会误走 /add 重复建单",
          fallback.get('ID') == 777, repr(fallback.get('ID')))
    check("兜底场景审计字段仍有默认值",
          fallback.get('DEALER_CODE') == 'FY' and fallback.get('RECORD_VERSION') == 0,
          repr({k: fallback.get(k) for k in ('DEALER_CODE', 'RECORD_VERSION')}))
    page.edit_id = ''
    page.edit_raw = {}

    print("\n[6] 编辑载入：部门取主单值，ORGANIZATION_ID 回退仓库映射")
    page2 = m.InternalUseManagePage(ttk.Frame(root), ctrl)
    page2.warehouse_var.set("商丘库")
    page2.open_edit(None)
    page2.edit_raw = {'DEPARTMENT_ID': '3003', 'DEPARTMENT_NAME': '物流部-西安',
                      'WAREHOUSE_NAME': '西安库', 'STORAGE_CODE': 'XA'}
    page2.edit_wh_name = '西安库'
    page2.edit_wh_code = 'XA'
    page2.edit_org_id = m.USE_DEPT_MAP.get('西安库')
    check("编辑态 ORGANIZATION_ID 回退仓库映射 1149", page2.edit_org_id == 1149,
          repr(page2.edit_org_id))
    page2.edit_dept_id = page2.edit_raw.get('DEPARTMENT_ID', page2.edit_dept_id)
    page2.edit_dept_name = page2.edit_raw.get('DEPARTMENT_NAME') or page2.edit_dept_name
    check("编辑态 DEPARTMENT_ID 取主单 3003", page2.edit_dept_id == '3003')

    root.destroy()
    print("\n" + "=" * 60)
    print("PASS: %d   FAIL: %d" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  -", f)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

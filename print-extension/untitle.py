    
    # 11. 添加获取调拨单明细函数
    def get_transfer_detail(self, transferNos):
        """批量获取调拨单明细"""
        if not isinstance(transferNos, list):
            transferNos = [transferNos]
            
        PrintDetail_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/getPrintList"
        params = {
            'searchType': 'inbound',
            'createdByName': '',
            'transferNos': ",".join(f"'{x}'" for x in transferNos)
        }

        try:
            response = self.controller.session.get(PrintDetail_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"查询调拨单{transferNos}明细失败: {e}")
            return None
    
    # 12. 添加查询库存函数
    def query_inventory(self, storage_code="SQ", page_num=1, page_size=500, **kwargs):
        """通用库存查询函数"""
        inventory_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/asicDataQuery/inventoryQuery/location/query"
        
        # 基本参数
        params = {
            'storage_code': storage_code,
            'limit': str(page_size),
            'pageNum': str(page_num)
        }
        
        # 添加其他参数
        for key, value in kwargs.items():
            if value is not None:
                params[key] = value
        
        try:
            response = self.controller.session.get(inventory_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return
            response.raise_for_status()
            return response.json()
        except Exception as e:
            param_info = ', '.join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
            print(f"查询库存失败 [{param_info}]: {e}")
            return None
    
    # 13. 添加查询所有库存函数
    def query_all_inventory(self, storage_code="SQ", **kwargs):
        """查询所有库存数据，自动处理分页"""
        page_num = 1
        page_size = 500
        all_rows = []
        total_pages = 1
        
        while page_num <= total_pages:
            result = self.query_inventory(storage_code, page_num, page_size, **kwargs)
            
            if not result or 'data' not in result:
                break
                
            # 提取当前页数据
            if 'rows' in result['data']:
                all_rows.extend(result['data']['rows'])
            
            # 计算总页数
            if page_num == 1 and 'total' in result['data']:
                total_count = result['data']['total']
                total_pages = (total_count + page_size - 1) // page_size
            
            page_num += 1
        
        # 构造合并后的结果
        merged_result = {'data': {'rows': all_rows}}
        if result and 'data' in result and 'total' in result['data']:
            merged_result['data']['total'] = result['data']['total']
        
        return merged_result
    
    # 14. 添加查询销售明细函数
    def query_order_by_code(self, item_code, storage_id=11):
        """构造销售明细查询URL并获取销售明细数据"""
        now = datetime.now()
        starttime = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        endtime = now.strftime('%Y-%m-%d')
        inventoryQuery_url = "https://xb.fy-carg.com/dmscloud.part/salesProfit/queryDetail"
        params = {
            "bill_at_begin": starttime,
            "bill_at_end": endtime,
            "part_code": item_code,
            "storage_id": storage_id,
            "limit": 50,
            "pageNum": "1",
        }
        try:
            response = self.controller.session.get(inventoryQuery_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return

            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"查询{item_code}销售明细失败: {e}")
            return None
    
    # 15. 添加获取最近销售库位函数
    def get_recent_sale_location(self, response):
        """获取最近销售库位信息"""
        # 获取销售明细列表
        sales_list = response.get('data', {}).get('rows', [])
        if not sales_list:
            return "无销售记录"
        recent_record = max(
            (r for r in sales_list if r.get('bill_date')),
            key=lambda x: x['bill_date'],
            default=None
        )
        if not recent_record:
            return "无有效记录"
        return f"{recent_record.get('location_no', '未知库位')}【{int(recent_record.get('NUM', 0))}】\n{recent_record.get('bill_date', '未知日期')}"
    
    
    # 17. 添加获取所有库存数据函数
    def get_all_stock_data(self, storage_code="SQ"):
        """获取指定仓库的所有库存数据"""
        return self.query_all_inventory(storage_code=storage_code)
    
    # 18. 添加构建库存索引函数
    def build_stock_indices(self, stock_data):
        """构建库存数据的索引结构（只保留必要字段）"""
        location_index = defaultdict(list)
        part_code_index = defaultdict(list)
        
        if stock_data and 'data' in stock_data and 'rows' in stock_data['data']:
            for item in stock_data['data']['rows']:
                # 只保留必要的字段
                simplified_item = {
                    'part_code': item.get('part_code'),
                    'location_accessories_number': item.get('location_accessories_number'),
                    'location_no': item.get('location_no')
                }
                
                # 按库位索引
                location_no = simplified_item.get('location_no')
                if location_no:
                    location_index[location_no].append(simplified_item)
                
                # 按产品编码索引
                part_code = simplified_item.get('part_code')
                if part_code:
                    part_code_index[part_code].append(simplified_item)
        
        return {
            'location': dict(location_index),
            'part_code': dict(part_code_index)
        }
    
    # 19. 添加查找空库位函数
    def find_empty_locations(self, storage_code):
        """查找空库位"""
        # 生成所有库位集合
        all_locations = self.generate_storage_locations_set(max_level=3,maxnum=56)
        
        # 从系统获取已占用的库位集合
        occupied_locations = self.get_occupied_locations_from_erp(storage_code)
        
        # 使用集合差集操作计算空库位
        empty_locations_set = set(all_locations) - occupied_locations
        
        # 转换为排序后的列表
        empty_locations = sorted(empty_locations_set)
        
        return empty_locations
    
    # 20. 添加获取已占用库位函数
    def get_occupied_locations_from_erp(self, storage_code="SQ"):
        """从ERP系统获取已占用的库位集合"""
        # 使用通用查询函数，查询分类为前挡的库存
        json_data = self.query_all_inventory(storage_code=storage_code, categoryTwo='90921001')
        
        if json_data and 'data' in json_data and 'rows' in json_data['data']:
            localno_list = set(item['location_no'] for item in json_data['data']['rows'])
            return localno_list
        return set()

    def inboundDetail_query(self, transferId: int):
        """构造调拨明细查询URL并获取调拨明细数据"""
        inboundDetail_Query_url = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail"
        params = {
            'transferId': transferId
        }
        try:
            response = self.controller.session.get(inboundDetail_Query_url, params=params, headers=HEADERS)

            # 检查登录状态
            if not self._check_response(response):
                return

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"查询调拨明细失败: {e}")
            return None

    # 21. 添加创建Excel工作簿函数
    def create_workbook(self, move_warehouse_name="", remove_warehouse_name="", start_time="", 
                      end_time="", status_name="", transfer_no="", part_no="", part_name=""):
        """创建Excel工作簿并填充数据"""
        try:
            # 获取仓库ID和状态代码
            move_warehouse_id = ""
            remove_warehouse_id = ""
            
            if move_warehouse_name != "全部" and move_warehouse_name:
                move_warehouse_id = self.controller.options.get(move_warehouse_name, "")
                
            if remove_warehouse_name != "全部" and remove_warehouse_name:
                remove_warehouse_id = self.controller.options.get(remove_warehouse_name, "")
            
            storage_code = self.WAREHOUSE_MAPPING.get(move_warehouse_name, {}).get("storage_code", "SQ")
            status_code = self.transfer_status_mapping.get(status_name, "") if status_name != "全部" else ""
            
                
            # 从treeview中获取用户已选择的调拨单ID和调拨单号
            transferIds = []
            transferNos = []
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == '✓':  # 检查是否选中
                    transfer_id = item  # 行ID就是调拨单ID
                    transfer_no = self.tree.item(item, 'values')[2]  # 调拨单号在第2列
                    transferIds.append(transfer_id)
                    transferNos.append(transfer_no)
            
            if not transferIds:
                messagebox.showwarning("警告", "请至少选择一条调拨单记录")
                return None
            
            # 获取所有库存数据并创建索引
            all_stock_data = self.get_all_stock_data(storage_code)
            stock_indices = self.build_stock_indices(all_stock_data)
            
            # 查找空库位
            empty_locations = self.find_empty_locations(storage_code)
            
            # 创建工作簿
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "调拨清单"
            
            # 创建隐藏工作表存储空库位数据
            hidden_ws = wb.create_sheet("空库位数据")
            hidden_ws.sheet_state = 'hidden'  # 隐藏工作表
            
            # 将空库位数据写入隐藏表的A列
            for i, location in enumerate(empty_locations, 1):
                hidden_ws.cell(row=i, column=1, value=location)
            
            # 设置打印标题行
            ws.print_title_rows = '4:4'
            ws.print_options.horizontalCentered = True
            
            # 批量查询所有调拨单明细
            all_detail_data = self.get_transfer_detail(transferNos)
            if not all_detail_data or 'data' not in all_detail_data:
                print("未查询到调拨单明细数据")
                return None
            
            # 按调拨单号分组数据
            transfer_details = {}
            for item in all_detail_data['data']:
                transfer_no = item.get('transferNo')
                if transfer_no not in transfer_details:
                    transfer_details[transfer_no] = []
                transfer_details[transfer_no].append(item)
                
            # 定义表头
            headers_str = ["品牌", "产品名称", "分类", "产品编码", "入库\n库位",
                          "入库\n数量", "指示\n库位", "调拨前\n库存数", "3月内最近\n出库信息"]
            
            current_row = 1
            
            # 添加标题行
            ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
            title_cell = ws.cell(row=current_row, column=1, value="调拨清单")
            title_cell.font = Font(bold=True, size=20)
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[current_row].height = 30
            current_row += 1
            
            # 处理每个调拨单
            for transferNo, transferId in zip(transferNos, transferIds):
                # 获取当前调拨单的数据
                detail_data = {'data': transfer_details.get(transferNo, [])}
                if not detail_data['data']:
                    continue
                    
                shelf_data = self.inboundDetail_query(transferId)
                
                # 添加空行分隔
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                cell=ws.cell(row=current_row, column=1, 
                                value="·················································")
                current_row += 1
                # 添加调拨单分隔信息
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                transfer_data = detail_data['data'][0] if len(detail_data['data']) > 0 else {}
                remove_warehouse = transfer_data.get('removeWarehouseName', '')
                move_warehouse = transfer_data.get('moveWarehouseName', '')
                info_cell = ws.cell(row=current_row, column=1, 
                                value=f"↓↓调出仓库: {remove_warehouse} | 调入仓库: {move_warehouse} | 调拨单号: {transferNo}↓↓")
                info_cell.font = Font(bold=True, size=13)
                info_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 20
                current_row += 1
                # 如果是第一个调拨单，添加表头
                if current_row == 4:
                    # 添加表头
                    for col, header in enumerate(headers_str, 1):
                        ws.cell(row=current_row, column=col, value=header)
                    header_font = Font(bold=True, color="FF0000")
                    header_fill = PatternFill("solid", fgColor="F0F0F0")
                    center_align = Alignment(wrap_text=True, horizontal="center", vertical="center")
                    for cell in ws[current_row]:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = center_align
                    current_row += 1
                
                ws.freeze_panes = "A5"
                
                # 填充数据
                for item1,item2 in zip(detail_data['data'],shelf_data['data']):
                    inboundQuantity = item1.get('inboundQuantity', 0)
                    cell_alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
                    # 判断入库数量为0时，设置删除线格式
                    if inboundQuantity == 0:
                        data_font = Font(bold=True, size=11, strike=True)  # 添加删除线格式
                    else:
                        data_font = Font(bold=True,size=11)  # 设置11号字体
                    
                    # 基础信息
                    cell = ws.cell(row=current_row, column=1, value=item1.get('brandName', ''))
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    cell = ws.cell(row=current_row, column=2, value=item1.get('partName', ''))
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    # 分类转换
                    category_code = item1.get('categoryTwo', '')
                    category_name = self.CATEGORY_MAPPING.get(category_code, category_code)
                    cell = ws.cell(row=current_row, column=3, value=category_name)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    item_code = item1.get('partCode', '')
                    cell = ws.cell(row=current_row, column=4, value=item_code)
                    cell.alignment = cell_alignment
                    cell.font = data_font

                    inboundLocationNo: str = item1.get('inboundLocationNo', '')
                    if inboundLocationNo:
                        # 使用索引查询库位信息
                        location_items = stock_indices['location'].get(inboundLocationNo, [])
                        total_qty = sum(int(item.get('location_accessories_number', 0)) for item in location_items)
                        # if total_qty >= 0:
                        summary_info = f'【{total_qty}】'
                        cell = ws.cell(row=current_row, column=5, value=f'{inboundLocationNo}\n{summary_info}')
                    else:
                        cell = ws.cell(row=current_row, column=5, value="")
                        # 为单元格添加数据有效性下拉选项（使用外部引用）
                        if empty_locations:
                            # 创建数据验证规则，引用隐藏表中的A列数据
                            dv = DataValidation(type="list", formula1="=空库位数据!$A$1:$A$" + str(len(empty_locations)), allow_blank=True)
                            dv.add(cell)
                            ws.add_data_validation(dv)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    cell = ws.cell(row=current_row, column=6, value=inboundQuantity)
                    cell.alignment = cell_alignment
                    cell.font = data_font
                    
                    shelfLocationNo: str = item2.get('shelfLocationNo','')
                    if shelfLocationNo:
                        # 使用索引查询库位信息
                        location_items = stock_indices['location'].get(shelfLocationNo, [])
                        total_qty = sum(int(item.get('location_accessories_number', 0)) for item in location_items)
                        if total_qty >= 0:
                            shelf_info = f'【{total_qty}】'
                            cell = ws.cell(row=current_row, column=7, value=f'{shelfLocationNo}\n{shelf_info}')
                    else:
                        cell = ws.cell(row=current_row, column=7, value=shelfLocationNo)
                    cell.alignment = cell_alignment
                    cell.font = data_font

                    # 补充库存和销售信息
                    if item_code:
                        # 库存信息
                        stock_data =stock_indices['part_code'].get(item_code, [])
                        # print(stock_data)
                        if stock_data:
                            locations = []
                            quantities = []
                            for loc in stock_data:
                                locations.append(loc.get('location_no', ''))
                                quantities.append(str(loc.get('location_accessories_number', 0)))
                            if locations and quantities:
                                cell = ws.cell(row=current_row, column=8, value=f"{'\n'.join(locations)}\n【{','.join(quantities)}】")
                                cell.alignment = cell_alignment
                                cell.font = data_font
                        # 销售信息
                        storage_id: int = self.WAREHOUSE_MAPPING.get(move_warehouse_name, {}).get("warehouseId", 11)
                        order_data = self.query_order_by_code(item_code, storage_id)
                        recent_sale = self.get_recent_sale_location(order_data) if order_data else "没有记录"
                        sale_info: str = f"{recent_sale}\n{item2.get('remarks', '')}"
                        cell = ws.cell(row=current_row, column=9, value=sale_info)
                        cell.alignment = cell_alignment
                        cell.font = data_font               
                    current_row += 1
                # 添加调拨单合计行
                if len(detail_data['data']) > 0:
                    ws.cell(row=current_row, column=5, value="合计:").font = Font(bold=True,size =12)
                    ws.cell(row=current_row, column=5).alignment = Alignment(horizontal="right")
                    total_qty = sum(float(item.get('inboundQuantity', 0)) for item in detail_data['data'])
                    ws.cell(row=current_row, column=6, value=total_qty).font = Font(bold=True,size = 12)
                    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="center", vertical="center")
                    current_row += 1
                # 添加调拨单分隔信息
                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                transfer_data = detail_data['data'][0] if len(detail_data['data']) > 0 else {}
                remove_warehouse = transfer_data.get('removeWarehouseName', '')
                move_warehouse = transfer_data.get('moveWarehouseName', '')
                info_cell = ws.cell(row=current_row, column=1, 
                                value=f"↑↑调出仓库: {remove_warehouse} | 调入仓库: {move_warehouse} | 调拨单号: {transferNo}↑↑")
                info_cell.font = Font(bold=True, size=13)
                info_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 30
                current_row += 1

                ws.merge_cells(start_row=current_row, end_row=current_row, start_column=1, end_column=len(headers_str))
                ws.cell(row=current_row, column=1, value=str(empty_locations)).font = Font(bold=True,size = 11)
                ws.cell(row=current_row, column=1).alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
                ws.row_dimensions[current_row].height = 50
                current_row += 1
            # 设置边框
            thin_border = Side(border_style="thin", color="000000")
            border = Border(left=thin_border, right=thin_border, 
                        top=thin_border, bottom=thin_border)
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row,
                                min_col=1, max_col=len(headers_str)):
                for cell in row:
                    cell.border = border
            
            # 设置列宽
            column_widths = {
                "A": 9,   # 品牌
                "B": 26,  # 产品名称
                "C": 5,   # 分类
                "D": 14,  # 产品编码
                "E": 8, # 入库库位
                "F": 7.5, # 入库数量
                "G": 8, # 指示库位
                "H": 8, # 之前库存及数量
                "I": 15   # 最近90天出库库位及日期
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            self.auto_adjust_rows(ws)
            
            # 设置页面格式
            ws.page_setup.paperSize = 1  # A4纸张 (210mm × 297mm)
            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
            ws.print_options.horizontalCentered = True
            margin_in_inch = 8 / 25.4
            ws.page_margins = PageMargins(left=0.15, right=0.15,
                                        top=margin_in_inch, bottom=margin_in_inch,
                                        header=0.3, footer=0.3)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')

            # 生成文件名（不带时间戳用于检查重复）
            condition_str = ""
            if move_warehouse_name:
                condition_str += f"_{move_warehouse_name}"
            if status_name:
                condition_str += f"_{status_name}"
            if start_time:
                condition_str += f"_{start_time.replace('-', '')}"
            if end_time:
                condition_str += f"_{end_time.replace('-', '')}"
            
            base_filename = f"调拨清单{condition_str}"
            
            # 检查最近30分钟内是否已生成相同条件的文件
            import glob
            
            # 查找匹配的现有文件
            pattern = f"{base_filename}_*.xlsx"
            existing_files = glob.glob(pattern)
            
            # 检查是否有最近30分钟内生成的相同文件
            current_time = datetime.now()
            for existing_file in existing_files:
                # 提取文件名中的时间戳
                try:
                    # 文件名格式: 调拨清单[条件]_YYYYMMDD_HHMM.xlsx
                    parts = existing_file.split('_')
                    if len(parts) >= 2:
                        # 假设时间戳是最后两个部分
                        time_part = parts[-2] + "_" + parts[-1].replace('.xlsx', '')  # YYYYMMDD_HHMM
                        file_time = datetime.strptime(time_part, '%Y%m%d_%H%M')
                        
                        # 如果文件是最近30分钟内生成的，则直接返回该文件
                        if current_time - file_time <= timedelta(minutes=30):
                            print(f"找到最近生成的相同文件: {existing_file}")
                            return existing_file
                except (ValueError, IndexError):
                    # 解析时间戳失败，跳过该文件
                    continue
            
            # 生成带时间戳的新文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"{base_filename}_{timestamp}.xlsx"
            wb.save(filename)
            print(f"处理完成，文件已保存为: {filename}")
            
            return filename

        except Exception as e:
            print(f"生成Excel文件时发生错误: {e}")
            return None

// 调拨单打印扩展 - Content Script

// 全局变量
// CLodop 打印控件的本地实现
let checkInterval = null;
let observer = null;
let printExtensionInitialized = false;
let currentTransferNos = [];


function isAdjustLogPage() {
  return new Promise((resolve) => {
    setTimeout(() => {
      try {
        const currentUrl = window.location.href;
        const pageTitle = document.title;

        if (
          (currentUrl.includes('/part/warehouse/transferInbound/index') &&
            currentUrl.includes('menuId=501304')) &&
          pageTitle.includes('调拨入库')
        ) {
          resolve(true);
        } else {
          resolve(false);
        }
      } catch (error) {
        console.error('页面检测失败:', error);
        resolve(false);
      }
    }, 500); // 延迟 500毫秒检测
  });
}

// 修改 injectPrintButton 为异步函数
async function injectPrintButton() {
  try {
    // 延迟 1 秒后再次检测页面
    await new Promise(resolve => setTimeout(resolve, 1000));
    const isTargetPage = await isAdjustLogPage();
    const currentUrl = window.location.href;
    const pageTitle = document.title;
    if (!isTargetPage) return;
    if (!isTargetPage) {
      // 如果不是目标页面，移除已注入的按钮（如果存在）
      const existingBtn = document.getElementById('custom-print-preview-btn');
      if (existingBtn) {
        existingBtn.remove();
        console.log('检测到非调拨页面，已移除打印按钮');
      }
      return;
    }
    // 避免重复注入
    if (document.getElementById('custom-print-preview-btn')) {
      return;
    }

    if (!currentUrl.includes('/part/warehouse/transferInbound/index?menuId=501304')||!pageTitle.includes('调拨入库')) {
      return;
    }

    console.log('正在注入调拨单打印按钮...');

    // 多个可能的选择器
    const selectors = [
      '.tableHead .btnGroup .el-button-group',
      '.tableHead .el-button-group',
      '.btnGroup .el-button-group',
      '.el-button-group',
      '.tableHead > div:last-child .el-button-group'
    ];

    let btnGroup = null;
    for (const selector of selectors) {
      btnGroup = document.querySelector(selector);
      if (btnGroup && btnGroup.children.length > 0) {
        break;
      }
    }

    if (!btnGroup) {
      console.log('未找到按钮组，等待页面加载...');
      return;
    }
    
    // 创建专用打印预览按钮
    const printBtn = document.createElement('button');
    printBtn.className = 'el-button el-button--primary el-button--mini';
    printBtn.innerHTML = '<i class="el-icon-printer"></i> 调拨专用打印预览';
    printBtn.style.cssText = `
      margin-left: 10px;
    `;
    printBtn.id = 'custom-print-preview-btn';
    
    // 添加data属性以匹配Vue生成的元素
    const vueElements = document.querySelectorAll('[data-v-fe00d540]');
    if (vueElements.length > 0) {
      printBtn.setAttribute('data-v-fe00d540', '');
    }

    
    printBtn.addEventListener('click', handleCustomPrint);
    
    // 查找合适的位置插入（在打印按钮和打印预览按钮之间）
    const buttons = btnGroup.querySelectorAll('button');
    let insertPositionFound = false;
    
    for (let i = 0; i < buttons.length - 1; i++) {
      const currentBtn = buttons[i];
      const nextBtn = buttons[i + 1];
      const currentText = currentBtn.textContent.trim();
      const nextText = nextBtn.textContent.trim();
      
      // 查找"打印"按钮和"打印预览"按钮的组合
      if (currentText === '打印' && nextText === '打印预览') {
        // 在打印按钮后插入
        currentBtn.insertAdjacentElement('afterend', printBtn);
        insertPositionFound = true;
        break;
      }
    }
    
    // 如果没有找到预期的按钮组合，使用备选方案
    if (!insertPositionFound) {
      // 查找打印按钮
      const printButton = Array.from(buttons).find(btn => btn.textContent.trim() === '打印');
      if (printButton) {
        // 在打印按钮后插入
        printButton.insertAdjacentElement('afterend', printBtn);
      } else {
        // 查找打印预览按钮
        const previewButton = Array.from(buttons).find(btn => btn.textContent.trim() === '打印预览');
        if (previewButton) {
          // 在打印预览按钮前插入
          previewButton.insertAdjacentElement('beforebegin', printBtn);
        } else {
          // 备选方案：添加到最后
          const lastButton = btnGroup.lastElementChild;
          if (lastButton) {
            lastButton.insertAdjacentElement('afterend', printBtn);
          } else {
            btnGroup.appendChild(printBtn);
          }
        }
      }
    }
    
    console.log('调拨单打印按钮注入成功');
    printExtensionInitialized = true;
  } catch (error) {
    console.error('注入打印按钮失败:', error);
  }
}


// 获取选中的调拨单行
function getSelectedRows() {
  const selectedRows = [];
  
  try {
    // 方法1: 通过复选框获取选中的行
    const checkboxes = document.querySelectorAll('.el-table__body .el-checkbox__original:checked');
    
    checkboxes.forEach(checkbox => {
      const row = checkbox.closest('tr');
      if (row && !selectedRows.includes(row)) {
        selectedRows.push(row);
      }
    });
    
    console.log(`通过复选框找到 ${selectedRows.length} 个选中的行`);
    
    // 方法2: 如果没有选中的复选框，检查是否有当前选中的行（高亮行）
    if (selectedRows.length === 0) {
      const highlightedRows = document.querySelectorAll('.el-table__body tr.current-row');
      highlightedRows.forEach(row => {
        if (!selectedRows.includes(row)) {
          selectedRows.push(row);
        }
      });
      console.log(`通过高亮行找到 ${highlightedRows.length} 个选中的行`);
    }
    
    return selectedRows;
  } catch (error) {
    console.error('获取选中行失败:', error);
    return [];
  }
}

// 从行中提取调拨单号
function extractTransferNo(row) {
  try {
    // 根据提供的HTML结构，调拨单号在第4列（el-table_1_column_4）
    const transferNoCell = row.querySelector('.el-table_1_column_4 .cell');
    if (transferNoCell) {
      const transferNo = transferNoCell.textContent.trim();
      // 验证调拨单号格式
      if (transferNo && transferNo.startsWith('ZZHJDBD')) {
        return transferNo;
      }
    }
    
    // 备用方法：检查所有单元格
    const cells = row.querySelectorAll('.cell');
    for (let cell of cells) {
      const text = cell.textContent.trim();
      if (text && text.startsWith('ZZHJDBD')) {
        return text;
      }
    }
    
    console.warn('未能从行中提取调拨单号');
    return null;
  } catch (error) {
    console.error('提取调拨单号失败:', error);
    return null;
  }
}

// 获取选中的调拨单号
function getSelectedTransferNos() {
  const selectedRows = getSelectedRows();
  const transferNos = [];
  
  selectedRows.forEach(row => {
    const transferNo = extractTransferNo(row);
    if (transferNo && !transferNos.includes(transferNo)) {
      transferNos.push(transferNo);
    }
  });
  
  console.log(`选中的调拨单号: ${transferNos}`);
  return transferNos;
}


function getSearchParams() {
  const params = {
    searchType: 'inbound'
  };

  // 映射关系
  const transfer_type_mapping = {
    "平价调拨": 47171001,
    "加价调拨": 47171002
  };

  const WAREHOUSE_MAPPING = {
    "郑州库": { "storage_code": "ZZ", "warehouseId": 6 },
    "西安库": { "storage_code": "XA", "warehouseId": 7 },
    "兰州库": { "storage_code": "LZ", "warehouseId": 8 },
    "驻马店库": { "storage_code": "ZMD", "warehouseId": 9 },
    "茶城库": { "storage_code": "CC", "warehouseId": 10 },
    "商丘库": { "storage_code": "SQ", "warehouseId": 11 },
    "洛阳库": { "storage_code": "LY", "warehouseId": 12 },
    "雁塔库": { "storage_code": "YT", "warehouseId": 13 },
    "西宁库": { "storage_code": "XN", "warehouseId": 14 },
    "榆林库": { "storage_code": "YL", "warehouseId": 15 },
    "银川库": { "storage_code": "YC", "warehouseId": 16 },
    "西安西郊库": { "storage_code": "XA-XJ", "warehouseId": 18 }
  };

  const transfer_status_mapping = {
    "待签收": 47161008,
    "待上架": 47161009,
    "已入库": 47161006
  };

  try {
    // 调拨单号
    const transferNoInput = document.querySelector('input[placeholder="调拨单号"]');
    params.transferNo = transferNoInput?.value.trim() || '';

    // CARG全码/产品编码
    const partNoInput = document.querySelector('input[placeholder="CARG全码/产品编码"]');
    params.partNo = partNoInput?.value.trim() || '';

    // 产品名称
    const partNameInput = document.querySelector('input[placeholder="产品名称"]');
    params.partName = partNameInput?.value.trim() || '';

    // 调拨申请时间
    const startTimeInput = document.querySelector('input[placeholder="调拨申请时间"]');
    params.startTime = startTimeInput?.value.trim() || '';

    // 至
    const endTimeInput = document.querySelector('input[placeholder="至"]');
    params.endTime = endTimeInput?.value.trim() || '';

    // 拣货单号
    const pickingOrderNoInput = document.querySelector('input[placeholder="拣货单号"]');
    params.pickingOrderNo = pickingOrderNoInput?.value.trim() || '';

    // 调拨类型
    const transferTypeLabel = Array.from(document.querySelectorAll('label')).find(label => 
      label.textContent.trim() === '调拨类型'
    );
    const transferTypeInput = transferTypeLabel?.nextElementSibling?.querySelector('input.el-input__inner');
    const transferTypeValue = transferTypeInput?.value.trim() || '';
    console.log('调拨类型输入框:', transferTypeInput, '值:', transferTypeValue);
    if (transferTypeValue === "请选择") {
      params.transferType = '';
    } else {
      params.transferType = transfer_type_mapping[transferTypeValue] || transferTypeValue;
    }

    // 调入方
    const moveWarehouseLabel = Array.from(document.querySelectorAll('label')).find(label => 
      label.textContent.trim() === '调入方'
    );
    const moveWarehouseInput = moveWarehouseLabel?.nextElementSibling?.querySelector('input.el-input__inner');
    const moveWarehouseValue = moveWarehouseInput?.value.trim() || '';
    console.log('调入方输入框:', moveWarehouseInput, '值:', moveWarehouseValue);
    if (moveWarehouseValue === "请选择"|| !moveWarehouseValue) {
      params.moveWarehouse = '';
    } else {
      const mappedWarehouse = WAREHOUSE_MAPPING[moveWarehouseValue];
      if (mappedWarehouse) {
        params.moveWarehouse = mappedWarehouse.warehouseId;
      } else {
        console.warn(`调入方映射失败: 未找到键 "${moveWarehouseValue}"`);
        params.moveWarehouse = '';
      }
    }

    // 调出方
    const removeWarehouseLabel = Array.from(document.querySelectorAll('label')).find(label =>
      label.textContent.trim() === '调出方'
    );
    const removeWarehouseInput = removeWarehouseLabel?.nextElementSibling?.querySelector('input.el-input__inner');
    const removeWarehouseValue = removeWarehouseInput?.value.trim() || '';
    console.log('调出方输入框:', removeWarehouseInput, '值:', removeWarehouseValue);

    if (removeWarehouseValue === "请选择" || !removeWarehouseValue) {
      params.removeWarehouse = '';
    } else {
      const mappedWarehouse = WAREHOUSE_MAPPING[removeWarehouseValue];
      if (mappedWarehouse) {
        params.removeWarehouse = mappedWarehouse.warehouseId;
      } else {
        console.warn(`调出方映射失败: 未找到键 "${removeWarehouseValue}"`);
        params.removeWarehouse = '';
      }
    }


    // 调拨状态
    const statusLabel = Array.from(document.querySelectorAll('label')).find(label => 
      label.textContent.trim() === '调拨状态'
    );
    const statusInput = statusLabel?.nextElementSibling?.querySelector('input.el-input__inner');
    const statusValue = statusInput?.value.trim() || '';
    console.log('调拨状态输入框:', statusInput, '值:', statusValue);
    if (statusValue === "请选择") {
      params.status = '';
    } else {
      const mappedStatus = transfer_status_mapping[statusValue];
      if (mappedStatus) {
        params.status = mappedStatus;
      } else {
        console.warn(`调拨状态映射失败: 未找到键 "${statusValue}"`);
        params.status = '';
      }
    }

    // 制单人
    const createdByNameLabel = Array.from(document.querySelectorAll('label')).find(label => 
      label.textContent.trim() === '制单人'
    );
    const createdByNameInput = createdByNameLabel?.nextElementSibling?.querySelector('input.el-input__inner');
    const createdByNameValue = createdByNameInput?.value.trim() || '';
    console.log('制单人输入框:', createdByNameInput, '值:', createdByNameValue);
    if (createdByNameValue === "请选择") {
      params.createdByName = '';
    } else {
      params.createdByName = createdByNameValue;
    }


    console.log('提取的搜索参数:', params);
    return params;
  } catch (error) {
    console.error('获取搜索参数失败:', error);
    return params;
  }
}


// 构建API URL
function buildApiUrl(transferNos, searchParams) {
  try {
    const baseUrl = 'https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/getPrintList';
    const params = new URLSearchParams();
    
    // 添加搜索参数
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        params.append(key, value);
      }
    });
    
    // 格式化调拨单号（按照原系统的格式）
    const formattedNos = transferNos.map(no => `'${no}'`).join(',');
    params.append('transferNos', formattedNos);
    
    const apiUrl = `${baseUrl}?${params.toString()}`;
    console.log('构建的API URL:', apiUrl);
    return apiUrl;
  } catch (error) {
    console.error('构建API URL失败:', error);
    throw error;
  }
}

// 检查CLodop是否可用 - 使用事件监听器
function isClodopAvailable() {
  return new Promise((resolve) => {
    // 创建唯一的事件ID
    const eventId = 'clodop_check_' + Date.now();
    
    // 监听来自页面的消息
    const messageHandler = (event) => {
      if (event.data.type === 'CLODOP_CHECK_RESULT' && event.data.id === eventId) {
        window.removeEventListener('message', messageHandler);
        resolve(event.data.available);
      }
    };
    
    window.addEventListener('message', messageHandler);
    
    // 创建一个iframe来执行检查（绕过CSP）
    const iframe = document.createElement('iframe');
    iframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
    iframe.srcdoc = `
      <script>
        // 在iframe中检查CLodop可用性
        const available = !!(window.parent.CLODOP || window.parent.getLodop);
        window.parent.postMessage({
          type: 'CLODOP_CHECK_RESULT',
          id: '${eventId}',
          available: available
        }, '*');
      </script>
    `;

    document.body.appendChild(iframe);

    // 超时处理
    setTimeout(() => {
      window.removeEventListener('message', messageHandler);
      if (iframe.parentNode) {
        document.body.removeChild(iframe);
      }
      resolve(false);
    }, 3000);
  });
}



// 处理打印请求
async function handleCustomPrint(event) {
  event.preventDefault();
  event.stopPropagation();

  try {
    // 检查CLodop是否可用
    const clodopAvailable = await isClodopAvailable();
    if (!clodopAvailable) {
      showMessage('CLodop打印控件未加载，请刷新页面或检查CLodop安装', 'error');
      return;
    }

    console.log('开始处理打印请求...');

    // 获取选中的调拨单号
    const transferNos = getSelectedTransferNos();
    if (transferNos.length === 0) {
      showMessage('请先选择需要打印的调拨单', 'warning');
      return;
    }
    
    console.log(`选中了 ${transferNos.length} 个调拨单:`, transferNos);
    
    // 获取搜索参数
    const searchParams = getSearchParams();
    
    // 构建API URL
    const apiUrl = buildApiUrl(transferNos, searchParams);
    
    // 显示加载提示
    showMessage('正在获取打印数据...', 'info');
    
    // 获取打印数据
    const responseData = await fetchPrintData(apiUrl);
    
    if (!responseData || !responseData.success) {
      showMessage(responseData?.errMsg || '获取数据失败', 'error');
      return;
    }
    
    const printData = responseData.data || [];
    if (printData.length === 0) {
      showMessage('没有获取到打印数据', 'warning');
      return;
    }
    
    console.log(`获取到 ${printData.length} 条打印数据`);
    
    // 显示打印预览
    showPrintPreview(printData, transferNos, searchParams);
    
  } catch (error) {
    console.error('打印处理失败:', error);
    showMessage('打印处理失败: ' + error.message, 'error');
  }
}


// 获取打印数据
async function fetchPrintData(apiUrl) {
  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('API响应数据:', data);

    return data;
  } catch (error) {
    console.error('获取打印数据失败:', error);
    throw error;
  }
}

// 显示消息提示
function showMessage(message, type = 'info') {
  // 使用Element UI风格的提示
  const messageDiv = document.createElement('div');
  messageDiv.className = `el-message el-message--${type}`;
  messageDiv.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 999999;
    padding: 15px 20px;
    background-color: ${type === 'error' ? '#fef0f0' :
      type === 'warning' ? '#fdf6ec' :
        type === 'success' ? '#f0f9eb' : '#edf2fc'};
    border: 1px solid ${type === 'error' ? '#fde2e2' :
      type === 'warning' ? '#faecd8' :
        type === 'success' ? '#e1f3d8' : '#e4e7ed'};
    border-radius: 4px;
    color: ${type === 'error' ? '#f56c6c' :
      type === 'warning' ? '#e6a23c' :
        type === 'success' ? '#67c23a' : '#909399'};
    font-size: 14px;
  `;
  
  messageDiv.innerHTML = `
    <i class="el-message__icon el-icon-${type === 'error' ? 'error' : 
                                          type === 'warning' ? 'warning' : 
                                          type === 'success' ? 'success' : 'info'}"></i>
    <p class="el-message__content">${message}</p>
  `;
  
  document.body.appendChild(messageDiv);
  
  // 3秒后自动移除
  setTimeout(() => {
    if (messageDiv.parentNode) {
      messageDiv.parentNode.removeChild(messageDiv);
    }
  }, 3000);
}


/**
 * 查询库存数据
 * @param {string} storage_code - 仓库代码，默认为 "SQ"
 * @param {number} page_num - 页码，默认为 1
 * @param {number} page_size - 每页大小，默认为 500
 * @param {Object} kwargs - 其他查询参数
 * @returns {Promise<Object|null>} - 返回查询结果或 null（失败时）
 */
async function query_inventory(storage_code = "SQ", page_num = 1, page_size = 500, kwargs = {}) {
  const baseUrl = "https://xb.fy-carg.com/dmscloud.part/warehouse/asicDataQuery/inventoryQuery/location/query";
  
  // 构造查询参数
  const params = new URLSearchParams();
  params.append('storage_code', storage_code);
  params.append('limit', page_size);
  params.append('pageNum', page_num);

  // 添加其他参数（kwargs）
  Object.entries(kwargs).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      params.append(key, value);
    }
  });

  // 拼接完整的 URL
  const apiUrl = `${baseUrl}?${params.toString()}`;

  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('库存查询结果:', data);
    return data;
  } catch (error) {
    console.error('查询库存失败:', error);
    return null;
  }
}


/**
 * 查询所有库存数据，自动处理分页
 * @param {string} storage_code - 仓库代码，默认为 "SQ"
 * @param {Object} kwargs - 其他查询参数
 * @returns {Promise<Object|null>} - 返回合并后的查询结果或 null（失败时）
 */
async function query_all_inventory(storage_code = "SQ", kwargs = {}) {
  let page_num = 1;
  const page_size = 500;
  let all_rows = [];
  let total_pages = 1;

  while (page_num <= total_pages) {
    const result = await query_inventory(storage_code, page_num, page_size, kwargs);

    if (!result || !result.data) {
      break;
    }

    // 提取当前页数据
    if (result.data.rows) {
      all_rows = all_rows.concat(result.data.rows);
    }

    // 计算总页数
    if (page_num === 1 && result.data.total) {
      const total_count = result.data.total;
      total_pages = Math.ceil(total_count / page_size);
    }

    page_num++;
  }

  // 构造合并后的结果
  const merged_result = {
    data: {
      rows: all_rows,
      total: all_rows.length
    }
  };

  return merged_result;
}


/**
  * 根据产品编码查询销售明细数据
  * @param {string} item_code - 产品编码
  * @param {number} storage_id - 仓库ID，默认为 11
  * @returns {Promise<Object|null>} - 返回查询结果或 null（失败时）
  */
async function query_order_by_code(item_code, storage_id = 11) {
  const baseUrl = "https://xb.fy-carg.com/dmscloud.part/salesProfit/queryDetail";

  // 构造查询参数
  const now = new Date();
  const starttime = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const endtime = now.toISOString().split('T')[0];

  const params = new URLSearchParams();
  params.append('bill_at_begin', starttime);
  params.append('bill_at_end', endtime);
  params.append('part_code', item_code);
  params.append('storage_id', storage_id);
  params.append('limit', '50');
  params.append('pageNum', '1');

  // 拼接完整的 URL
  const apiUrl = `${baseUrl}?${params.toString()}`;

  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('销售明细查询结果:', data);
    return data;
  } catch (error) {
    console.error('查询销售明细失败:', error);
    return null;
  }
}


/**
 * 获取最近销售库位信息
 * @param {Object} response - 销售明细查询结果
 * @returns {string} - 返回最近销售记录的库位信息，格式为 "库位【数量】\n日期"
 */
function get_recent_sale_location(response) {
  if (!response || !response.data || !response.data.rows) {
    return "无销售记录";
  }

  const sales_list = response.data.rows;
  const recent_record = sales_list.reduce((latest, record) => {
    if (!record.bill_date) return latest;
    if (!latest || new Date(record.bill_date) > new Date(latest.bill_date)) {
      return record;
    }
    return latest;
  }, null);

  if (!recent_record) {
    return "无有效记录";
  }

  return `${recent_record.location_no || '未知库位'}【${recent_record.NUM || 0}】\n${recent_record.bill_date || '未知日期'}`;
}

/**
 * 获取指定仓库的所有库存数据
 * @param {string} storage_code - 仓库代码，默认为 "SQ"
 * @returns {Promise<Object|null>} - 返回所有库存数据或 null（失败时）
 */
async function get_all_stock_data(storage_code = "SQ") {
  return await query_all_inventory(storage_code);
}


// /**
//  * 查找空库位
//  * @param {string} storage_code - 仓库代码
//  * @returns {Promise<Array<string>>} - 返回空库位列表
//  */
// async function find_empty_locations(storage_code) {
//   // 生成所有库位集合（需根据实际逻辑实现）
//   const all_locations = generate_storage_locations_set_for_sq(3,56);

//   // 获取已占用的库位集合
//   const occupied_locations = await get_occupied_locations_from_erp(storage_code);

//   // 计算空库位
//   const empty_locations = all_locations.filter(location => !occupied_locations.has(location));

//   return empty_locations;
// }

/**
 * 查找空库位
 * @param {string} storage_code - 仓库代码
 * @returns {Promise<Array<string>>} - 返回空库位列表
 */
async function find_empty_locations(storage_code) {
  // 根据仓库代码选择对应的库位生成方法
  let all_locations;

  switch (storage_code) {
    case 'SQ': // 商丘库
      all_locations = generate_storage_locations_set_for_sq(3, 56);
      break;
    case 'ZZ': // 郑州库
      all_locations = generate_storage_locations_set_for_zz();
      break;
    case 'XA': // 西安库
    case 'XA-XJ': // 西安西郊库
      all_locations = generate_storage_locations_set_for_xa();
      break;
    case 'LZ': // 兰州库
      all_locations = generate_storage_locations_set_for_lz();
      break;
    case 'ZMD': // 驻马店库
      all_locations = generate_storage_locations_set_for_zmd();
      break;
    // case 'CC': // 茶城库
    //   all_locations = generate_storage_locations_set_for_sq(3, 56);
    //   break;
    case 'LY': // 洛阳库
      all_locations = generate_storage_locations_set_for_ly();
      break;
    // case 'YT': // 雁塔库
    //   all_locations = generate_storage_locations_set_for_sq(3, 56);
    //   break;
    // case 'XN': // 西宁库
    //   all_locations = generate_storage_locations_set_for_sq(3, 56);
    //   break;
    case 'YL': // 榆林库
      all_locations = generate_storage_locations_set_for_yl();
      break;
    case 'YC': // 银川库
      all_locations = generate_storage_locations_set_for_yc();
      break;
    default:
      // 默认使用商丘库的逻辑
      all_locations = generate_storage_locations_set_for_sq(3, 56);
      break;
  }

  // 获取已占用的库位集合
  const occupied_locations = await get_occupied_locations_from_erp(storage_code);

  // 计算空库位
  const empty_locations = all_locations.filter(location => !occupied_locations.has(location));

  return empty_locations;
}


/**
 * 从ERP系统获取已占用的库位集合
 * @param {string} storage_code - 仓库代码，默认为 "SQ"
 * @returns {Promise<Set<string>>} - 返回已占用的库位集合
 */
async function get_occupied_locations_from_erp(storage_code = "SQ") {
  const json_data = await query_all_inventory(storage_code, { });
  //const json_data = await query_all_inventory(storage_code, { categoryTwo: '90921001' });
  if (json_data && json_data.data && json_data.data.rows) {
    const localno_list = new Set(json_data.data.rows.map(item => item.location_no));
    return localno_list;
  }

  return new Set();
}

    /**
     * 生成郑州库所有库位集合
     * @returns {Array<string>} - 返回所有库位列表（已排序）
     */
    function generate_storage_locations_set_for_zz() {
        const locations_set = new Set();
        
        // 散片库位配置
        // 50-59排和61-68排，每排90个库位，分2层
        const scattered_racks = [
            // 50-59排
            ...Array.from({length: 10}, (_, i) => 50 + i),
            // 61-68排  
            ...Array.from({length: 8}, (_, i) => 61 + i)
        ];
        
        // 高架整箱货位配置
        const high_rack_config = [
            // 10-28排：每排12个库位，5层
            { start: 10, end: 28, slots: 12, levels: 5 },
            // 29-36排：每排4个库位，5层
            { start: 29, end: 36, slots: 4, levels: 5 },
            // 40-43排：每排28个库位，3层
            { start: 40, end: 43, slots: 28, levels: 3 }
        ];
        
        // 生成散片库位
        for (const rack of scattered_racks) {
            for (let level = 1; level <= 2; level++) {
                for (let slot = 1; slot <= 90; slot++) {
                    // 格式：排号-层数库位号（如：50-101）
                    const location = `${rack}-${level}${slot.toString().padStart(2, '0')}`;
                    locations_set.add(location);
                }
            }
        }
        
        // 生成高架整箱货位
        for (const config of high_rack_config) {
            for (let rack = config.start; rack <= config.end; rack++) {
                for (let level = 1; level <= config.levels; level++) {
                    for (let slot = 1; slot <= config.slots; slot++) {
                        // 格式：G排号层数-库位号（如：G101-01）
                        const rackStr = rack.toString().padStart(2, '0');
                        const slotStr = slot.toString().padStart(2, '0');
                        const location = `G${rackStr}${level}-${slotStr}`;
                        locations_set.add(location);
                    }
                }
            }
        }
        
        // 转换为数组并排序
        return Array.from(locations_set).sort();
    }

/**
 * 生成西安库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_xa() {
  const locations_set = new Set();

  // 散片库位配置
  // 21-25排，每排152个库位001-152，分2层
  const scattered_racks_21_25 = Array.from({ length: 5 }, (_, i) => 21 + i);

  // 33-37排，每排136个库位001-136，分2层
  const scattered_racks_33_37 = Array.from({ length: 5 }, (_, i) => 33 + i);

  // 高架整箱货位配置
  const high_rack_config = [
    // 40-52排：每排19个库位001-019，5层
    { start: 40, end: 52, slots: 19, levels: 5 },
    // 53-54排：每排12个库位001-012，5层
    { start: 53, end: 54, slots: 12, levels: 5 },
    // 55排：12个库位001-012，1层
    { start: 55, end: 55, slots: 12, levels: 1 },
    // 60排：20个库位001-020，1层
    { start: 60, end: 60, slots: 20, levels: 1 }
  ];

  // 生成21-25排散片库位
  for (const rack of scattered_racks_21_25) {
    for (let level = 1; level <= 2; level++) {
      for (let slot = 1; slot <= 152; slot++) {
        // 格式：排号层数-库位号（如：211-152）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${rack}${level}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 生成33-37排散片库位
  for (const rack of scattered_racks_33_37) {
    for (let level = 1; level <= 2; level++) {
      for (let slot = 1; slot <= 136; slot++) {
        // 格式：排号层数-库位号（如：331-136）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${rack}${level}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 生成高架整箱货位
  for (const config of high_rack_config) {
    for (let rack = config.start; rack <= config.end; rack++) {
      for (let level = 1; level <= config.levels; level++) {
        for (let slot = 1; slot <= config.slots; slot++) {
          // 格式：排号层数-库位号（如：401-001）
          const slotStr = slot.toString().padStart(3, '0');
          const location = `${rack}${level}-${slotStr}`;
          locations_set.add(location);
        }
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}

/**
 * 生成兰州库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_lz() {
  const locations_set = new Set();

  // 散片库位配置
  const scattered_rack_config = [
    // M41排：每排136个库位001-136，分2层
    { rack: 'M41', levels: 2, slots: 136, format: '${rack}${level}-${slotStr}' },
    // M42-M43排：每排160个库位001-160，分2层
    { rack: 'M42', levels: 2, slots: 160, format: '${rack}${level}-${slotStr}' },
    { rack: 'M43', levels: 2, slots: 160, format: '${rack}${level}-${slotStr}' },
    // M6排：每排170个库位001-170，分2层
    { rack: 'M6', levels: 2, slots: 170, format: '${rack}${level}-${slotStr}' },
    // M7排：每排150个库位001-150，分2层
    { rack: 'M7', levels: 2, slots: 150, format: '${rack}${level}-${slotStr}' },
    // M8排：每排140个库位001-140，分2层
    { rack: 'M8', levels: 2, slots: 140, format: '${rack}${level}-${slotStr}' },
    // M90排：152个库位001-152，分2层
    { rack: 'M90', levels: 2, slots: 152, format: '${rack}${level}-${slotStr}' },
    // M91排：160个库位001-160，分2层
    { rack: 'M91', levels: 2, slots: 160, format: '${rack}${level}-${slotStr}' },
    // MG8排：95个库位01-95，分2层
    { rack: 'MG8', levels: 2, slots: 95, format: '${rack}${level}-${slotStr}', slotPadding: 2 },
    // MA01-MA02排：8个库位，2层，格式：排号-层数-库位号
    { rack: 'MA01', levels: 2, slots: 8, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MA02', levels: 2, slots: 8, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    // MA03-MA05排：12个库位，2层，格式：排号-层数-库位号
    { rack: 'MA03', levels: 2, slots: 12, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MA04', levels: 2, slots: 12, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MA05', levels: 2, slots: 12, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    // MD01-MD06排：19个库位，3层，格式：排号-层数-库位号
    { rack: 'MD01', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MD02', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MD03', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MD04', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MD05', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 },
    { rack: 'MD06', levels: 3, slots: 19, format: '${rack}-${level}-${slotStr}', slotPadding: 2 }
  ];

  // 高架整箱货位配置
  const high_rack_config = [
    // M1-M3排：每排30个库位001-030，3层
    { start: 'M1', end: 'M3', slots: 30, levels: 3, format: '${rack}${level}-${slotStr}' },
    // M4-M5排：每排12个库位001-012，3层
    { start: 'M4', end: 'M5', slots: 12, levels: 3, format: '${rack}${level}-${slotStr}' },
    // MG1-MG7排：每排20个库位01-20，3层
    { start: 'MG1', end: 'MG7', slots: 20, levels: 3, format: '${rack}${level}-${slotStr}', slotPadding: 2 }
  ];

  // 生成散片库位
  for (const config of scattered_rack_config) {
    const slotPadding = config.slotPadding || 3; // 默认3位数字

    for (let level = 1; level <= config.levels; level++) {
      for (let slot = 1; slot <= config.slots; slot++) {
        const slotStr = slot.toString().padStart(slotPadding, '0');
        const location = eval('`' + config.format + '`');
        locations_set.add(location);
      }
    }
  }

  // 生成高架整箱货位
  for (const config of high_rack_config) {
    const rackStart = parseInt(config.start.replace(/[^\d]/g, ''));
    const rackEnd = parseInt(config.end.replace(/[^\d]/g, ''));
    const rackPrefix = config.start.replace(/\d+/g, '');
    const slotPadding = config.slotPadding || 3;

    for (let rackNum = rackStart; rackNum <= rackEnd; rackNum++) {
      const rack = rackPrefix + rackNum;

      for (let level = 1; level <= config.levels; level++) {
        for (let slot = 1; slot <= config.slots; slot++) {
          const slotStr = slot.toString().padStart(slotPadding, '0');
          const location = eval('`' + config.format + '`');
          locations_set.add(location);
        }
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}



/**
 * 生成所有库位集合（优化版本）
 * @param {number} max_level - 最大层数
 * @param {number} maxnum - E排的最大库位数
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_sq(max_level, maxnum) {
    const locations_set = new Set();
    
    // 定义各排的配置：排号 -> 每层库位数
    const rack_config = {
        'A': 112,  // A排每层112个库位
        'B': 104,  // B排每层104个库位
        'C': 104,  // C排每层104个库位
        'D': 104,  // D排每层104个库位
        'E': maxnum // E排每层maxnum个库位
    };
    
    // 在一个循环中生成所有库位
    for (const [rack, max_num] of Object.entries(rack_config)) {
        for (let level = 1; level < max_level; level++) {
            for (let num = 1; num <= max_num; num++) {
                locations_set.add(`${rack}${level}-${num.toString().padStart(3, '0')}`);
            }
        }
    }
    
    // 转换为数组并排序
    return Array.from(locations_set).sort();
}

/**
 * 生成银川库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_yc() {
  const locations_set = new Set();

  // 银川库配置：11-16排，每排110个库位001-110，分2层
  const racks = Array.from({ length: 6 }, (_, i) => 11 + i); // 11-16排

  // 生成所有库位
  for (const rack of racks) {
    for (let level = 1; level <= 2; level++) {
      for (let slot = 1; slot <= 110; slot++) {
        // 格式：排号层数-库位号（如：111-001）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${rack}${level}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}

/**
 * 生成榆林库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_yl() {
  const locations_set = new Set();

  // 榆林库配置：10-15排，每排110个库位001-110，分2层
  const racks = Array.from({ length: 6 }, (_, i) => 10 + i); // 10-15排

  // 生成所有库位
  for (const rack of racks) {
    for (let level = 1; level <= 2; level++) {
      for (let slot = 1; slot <= 110; slot++) {
        // 格式：排号层数-库位号（如：101-001）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${rack}${level}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}

/**
 * 生成驻马店库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_zmd() {
  const locations_set = new Set();

  // 驻马店库配置：10-12排，每排不同数量的库位，分2层
  const rack_config = [
    // 10排：140个库位001-140，分2层
    { rack: 10, slots: 140, levels: 2 },
    // 11排：215个库位001-215，分2层
    { rack: 11, slots: 215, levels: 2 },
    // 12排：176个库位001-176，分2层
    { rack: 12, slots: 176, levels: 2 }
  ];

  // 生成所有库位
  for (const config of rack_config) {
    for (let level = 1; level <= config.levels; level++) {
      for (let slot = 1; slot <= config.slots; slot++) {
        // 格式：排号层数-库位号（如：101-001）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${config.rack}${level}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}

/**
 * 生成洛阳库所有库位集合
 * @returns {Array<string>} - 返回所有库位列表（已排序）
 */
function generate_storage_locations_set_for_ly() {
  const locations_set = new Set();

  // 洛阳库配置：不同排的库位数量不同，不分层
  const rack_config = [
    // 1-2排：每排136个库位001-136，不分层
    { start: 1, end: 2, slots: 136 },
    // 4-5排：每排80个库位001-080，不分层
    { start: 4, end: 5, slots: 80 },
    // 7-8排：每排88个库位001-088，不分层
    { start: 7, end: 8, slots: 88 },
    // 10-11排：每排80个库位001-080，不分层
    { start: 10, end: 11, slots: 80 }
  ];

  // 生成所有库位
  for (const config of rack_config) {
    for (let rack = config.start; rack <= config.end; rack++) {
      for (let slot = 1; slot <= config.slots; slot++) {
        // 格式：排号-库位号（如：1-001）
        const slotStr = slot.toString().padStart(3, '0');
        const location = `${rack}-${slotStr}`;
        locations_set.add(location);
      }
    }
  }

  // 转换为数组并排序
  return Array.from(locations_set).sort();
}

// /**
//  * 生成空库位预览页面HTML
//  * @param {Array<string>} empty_locations - 空库位列表
//  * @param {string} storage_code - 仓库代码
//  * @returns {string} - 返回空库位预览页面的HTML
//  */
// function generateEmptyLocationsHTML(empty_locations, storage_code) {
//   // 按排号分组
//   const locationsByRack = {};

//   empty_locations.forEach(location => {
//     // 提取排号（根据不同的仓库格式处理）
//     let rack;
//     if (storage_code === 'LY') {
//       // 洛阳库格式：排号-库位号（如：1-001）
//       rack = location.split('-')[0];
//     } else if (storage_code === 'LZ') {
//       // 兰州库特殊格式处理
//       if (location.includes('-')) {
//         const parts = location.split('-');
//         rack = parts[0]; // 如 MA01-1-01 中的 MA01
//       } else {
//         rack = location.replace(/\d/g, ''); // 如 M411-001 中的 M4
//       }
//     } else {
//       // 其他仓库格式：排号层数-库位号（如：101-001）
//       rack = location.substring(0, location.indexOf('-') - 1); // 如 101-001 中的 1
//     }

//     if (!locationsByRack[rack]) {
//       locationsByRack[rack] = [];
//     }
//     locationsByRack[rack].push(location);
//   }
//   );

//   // 按排号排序
//   const sortedRacks = Object.keys(locationsByRack).sort();

//   let emptyLocationsHTML = '';

//   sortedRacks.forEach(rack => {
//     const rackLocations = locationsByRack[rack].sort();

//     emptyLocationsHTML += `
//       <div id="emptyLocationsPrintDiv" style="page-break-before: always;">
//         <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
//           <div style="width: 100%; margin: 0px auto; text-align: center;">
//             <span style="font-size: 25px; font-weight: bold;">${getWarehouseName(storage_code)} - 前档空库位清单</span>
//           </div>
//           <div style="width: 100%; margin: 10px 0; text-align: center;">
//             <span style="font-size: 16px; font-weight: bold;">排号：${rack}（共${rackLocations.length}个空库位）</span>
//           </div>
//           <div style="width: 100%; margin: 0px;">
//             <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 14px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
//               <tbody>
//                 <tr>
//                   <td style="width: 10%; display: table-cell; vertical-align: middle; height: 25px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse; font-weight: bold;">序号</td>
//                   <td style="width: 45%; display: table-cell; vertical-align: middle; height: 25px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse; font-weight: bold;">库位编号</td>
//                   <td style="width: 45%; display: table-cell; vertical-align: middle; height: 25px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse; font-weight: bold;">状态</td>
//                 </tr>
//     `;

//     // 每页显示20个库位
//     const pageSize = 20;
//     for (let page = 0; page < Math.ceil(rackLocations.length / pageSize); page++) {
//       const startIndex = page * pageSize;
//       const endIndex = Math.min(startIndex + pageSize, rackLocations.length);
//       const pageLocations = rackLocations.slice(startIndex, endIndex);

//       if (page > 0) {
//         emptyLocationsHTML += `
//           <div style="page-break-before: always;">
//             <div style="width: 100%; margin: 10px 0; text-align: center;">
//               <span style="font-size: 16px; font-weight: bold;">排号：${rack}（续）</span>
//             </div>
//         `;
//       }

//       pageLocations.forEach((location, index) => {
//         const serialNumber = startIndex + index + 1;
//         emptyLocationsHTML += `
//                 <tr>
//                   <td style="border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${serialNumber}</td>
//                   <td style="border: 1px solid rgb(0, 0, 0); border-collapse: collapse; white-space: pre-line;">${location}</td>
//                   <td style="border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">空库位</td>
//                 </tr>
//         `;
//       });

//       if (page > 0) {
//         emptyLocationsHTML += `</div>`;
//       }
//     }

//     emptyLocationsHTML += `
//               </tbody>
//             </table>
//           </div>
//           <div style="width: 100%; margin: 10px 0; text-align: right;">
//             <span style="font-size: 12px;">生成时间：${getCurrentTime()}</span>
//           </div>
//         </div>
//       </div>
//     `;
//   });

//   return emptyLocationsHTML;
// }

/**
 * 生成空库位预览页面HTML（按行显示版）
 * @param {Array<string>} empty_locations - 空库位列表
 * @param {string} storage_code - 仓库代码
 * @returns {string} - 返回空库位预览页面的HTML
 */
function generateEmptyLocationsHTML(empty_locations, storage_code) {
  // 按排号分组
  const locationsByRack = {};

  empty_locations.forEach(location => {
    // 提取排号（根据不同的仓库格式处理）
    let rack;
    if (storage_code === 'LY') {
      // 洛阳库格式：排号-库位号（如：1-001）
      rack = location.split('-')[0];
    } else if (storage_code === 'LZ') {
      // 兰州库特殊格式处理
      if (location.includes('-')) {
        const parts = location.split('-');
        rack = parts[0]; // 如 MA01-1-01 中的 MA01
      } else {
        rack = location.replace(/\d/g, ''); // 如 M411-001 中的 M4
      }
    } else {
      // 其他仓库格式：排号层数-库位号（如：101-001）
      rack = location.substring(0, location.indexOf('-') - 1); // 如 101-001 中的 1
    }

    if (!locationsByRack[rack]) {
      locationsByRack[rack] = [];
    }
    locationsByRack[rack].push(location);
  });

  // 按排号排序
  const sortedRacks = Object.keys(locationsByRack).sort();

  let emptyLocationsHTML = '';

  // 为所有排创建一个表格
  emptyLocationsHTML += `
    <div id="emptyLocationsPrintDiv">
      <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
        <div style="width: 100%; margin: 0px auto; text-align: center;">
          <span style="font-size: 25px; font-weight: bold;">${getWarehouseName(storage_code)} - 前档空库位清单</span>
        </div>
        <div style="width: 100%; margin: 10px 0; text-align: center;">
          <span style="font-size: 16px; font-weight: bold;">空库位总数量：${empty_locations.length}个</span>
        </div>
        <div style="width: 100%; margin: 0px;">
          <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 12px; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
            <tbody>
  `;

  // 每排占一行
  sortedRacks.forEach(rack => {
    const rackLocations = locationsByRack[rack].sort();
    // 将库位用逗号分隔，每行显示15个（充分利用宽度）
    const chunkSize = 12;
    const locationChunks = [];
    for (let i = 0; i < rackLocations.length; i += chunkSize) {
      locationChunks.push(rackLocations.slice(i, i + chunkSize));
    }

    emptyLocationsHTML += `
              <tr>
                <td style="width: 15%; display: table-cell; vertical-align: middle; height: 25px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse; font-weight: bold; background-color: #f5f5f5; padding: 5px;">
                  排号：${rack}（${rackLocations.length}个）
                </td>
                <td style="border: 1px solid rgb(0, 0, 0); border-collapse: collapse; padding: 5px;">
                  ${locationChunks.map((chunk, chunkIndex) => `
                    <div style="margin-bottom: ${chunkIndex < locationChunks.length - 1 ? '5px' : '0'}; line-height: 1.4;">
                      ${chunk.join(', ')}
                    </div>
                  `).join('')}
                </td>
              </tr>
    `;
  });

  emptyLocationsHTML += `
            </tbody>
          </table>
        </div>
        <div style="width: 100%; margin: 10px 0; text-align: right;">
          <span style="font-size: 12px;">生成时间：${getCurrentTime()}</span>
        </div>
      </div>
    </div>
  `;

  return emptyLocationsHTML;
}



/**
 * 根据仓库代码获取仓库名称
 * @param {string} storage_code - 仓库代码
 * @returns {string} - 返回仓库名称
 */
function getWarehouseName(storage_code) {
  const warehouseMap = {
    'SQ': '商丘库',
    'ZZ': '郑州库',
    'XA': '西安库',
    'XA-XJ': '西安西郊库',
    'LZ': '兰州库',
    'ZMD': '驻马店库',
    'CC': '茶城库',
    'LY': '洛阳库',
    'YT': '雁塔库',
    'XN': '西宁库',
    'YL': '榆林库',
    'YC': '银川库'
  };
  return warehouseMap[storage_code] || storage_code;
}


/**
 * 查询调拨明细数据
 * @param {number} transferId - 调拨单ID
 * @returns {Promise<Object|null>} - 返回调拨明细数据或 null（失败时）
 */
async function inboundDetail_query(transferId) {
  const baseUrl = "https://xb.fy-carg.com/dmscloud.part/warehouse/transferIn/inboundDetail";

  // 使用 URLSearchParams 构造查询字符串
  const params = new URLSearchParams();
  params.append('transferId', transferId);

  // 拼接完整的 URL
  const apiUrl = `${baseUrl}?${params.toString()}`;

  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('调拨明细查询结果:', data);
    return data;
  } catch (error) {
    console.error('查询调拨明细失败:', error);
    return null;
  }
}



async function formatPrintData(rawData) {
  // 如果 rawData 无效，返回空数组
  if (!rawData || !Array.isArray(rawData)) {
    console.error('无效的打印数据:', rawData);
    return [];
  }

  const groupedData = groupDataByTransferNo(rawData);
  const formattedGroups = [];

  // 获取当前用户信息
  const currentUser = '当前用户'; // 实际应从用户信息获取
  const currentTime = getCurrentTime();

  // 获取所有调拨单的 transferId 和 detail_data
  const transferDetails = {};
  for (const [transferNo, items] of Object.entries(groupedData)) {
    if (items.length === 0) continue;

    // 获取当前调拨单的 transferId
    const transferId = items[0].transferId || items[0].id;
    console.log(transferId)
    if (!transferDetails[transferId]) {
      try {
        const response = await inboundDetail_query(transferId);
        console.log(response)
        if (response && response.data) {
          transferDetails[transferId] = response.data;
        }
      } catch (error) {
        console.error(`获取调拨单 ${transferNo} 的明细数据失败:`, error);
        transferDetails[transferId] = [];
      }
    }
  }

  // 处理每个调拨单组
  for (const [transferNo, items] of Object.entries(groupedData)) {
    if (items.length === 0) continue;

    // 按调拨单号排序，确保同一调拨单的数据在一起
    items.sort((a, b) => {
      if (a.partCode && b.partCode) {
        return a.partCode.localeCompare(b.partCode);
      }
      return 0;
    });

    // 获取当前调拨单的 transferId 和 detail_data
    const transferId = items[0].transferId || items[0].id;
    const detail_data = transferDetails[transferId] || [];

    // 计算总数和总金额
    let totalQuantity = 0;
    let totalAmount = 0;

    // 处理每个 item，合并 remark
    const processedItems = items.map(item => {
      const quantity = parseInt(item.inboundQuantity) || 0;
      const price = parseFloat(item.salesPrice) || 0;
      const rate = parseFloat(item.priceIncreaseRate) || 1;

      totalQuantity += quantity;
      totalAmount += quantity * price * rate;

      // 匹配 detail_data 中的 remark
      const detailItem = detail_data.find(detail => detail.detailId === item.detailId);
      const remark = detailItem ? detailItem.remarks : '';
      const shelfLocationNo = detailItem ? detailItem.shelfLocationNo : '';
      // 格式化 brandName：如果大于3个字符，取前2个字符
      let formattedBrandName = item.brandName || '';
      if (formattedBrandName && formattedBrandName.length > 3) {
        formattedBrandName = formattedBrandName.substring(0, 2);
      }
      
      return {
        ...item,
        brandName: formattedBrandName, // 使用格式化后的品牌名
        remark: remark,
        shelfLocationNo: shelfLocationNo
      };
    });

    // 添加分组信息
    const group = {
      transferNo: transferNo,
      items: processedItems,
      headerInfo: {
        ...items[0], // 使用第一个项目作为头部信息
        userName: currentUser,
        currentDate: currentTime,
        totalNum: totalQuantity,
        totalAmount: totalAmount.toFixed(2)
      }
    };

    formattedGroups.push(group);
  }

  console.log(`格式化后的数据: ${formattedGroups.length} 个调拨单`);
  return formattedGroups;
}



// 按照调拨单号分组数据
function groupDataByTransferNo(data) {
  const groups = {};

  data.forEach(item => {
    const transferNo = item.transferNo;
    if (!groups[transferNo]) {
      groups[transferNo] = [];
    }
    groups[transferNo].push(item);
  });

  return groups;
}

// 获取当前时间
function getCurrentTime() {
  const date = new Date();
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}/${month}/${day} ${hours}:${minutes}`;
}

// 获取分类名称（基于分类代码）
function getCategoryName(categoryCode) {
  const categoryMap = {
    '90921001': '前挡',
    '90921002': '后挡',
    '90921003': '边窗',
    '90921004': '其它',
    '90921005': '天窗'
  };

  return categoryMap[categoryCode] || categoryCode || '';
}

// 在文件适当位置添加这个函数
function getShortTransferNo(transferNo) {
  if (!transferNo) return '';
  return transferNo.length > 7 ? transferNo.substring(7) : transferNo;
}

// 数字格式化（千分位，保留2位小数）
function formatNumber(num) {
  if (num === null || num === undefined) return '0.00';

  const n = parseFloat(num);
  if (isNaN(n)) return '0.00';

  // 保留2位小数
  const fixedNum = n.toFixed(2);

  // 添加千分位
  return fixedNum.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
// 生成随机 z-index 值（范围：3000-4000）
function getRandomZIndex() {
  return Math.floor(Math.random() * 1000) + 3000; // 3000-3999
}
// 显示打印预览

// async function showPrintPreview(printData, transferNos,searchParams) {


//   try {
//   // 格式化数据
//     const formattedData = await formatPrintData(printData);
//     // const searchParams = getSearchParams();
//     // 检查 formattedData 是否为数组
//     if (!Array.isArray(formattedData)) {
//         throw new Error('格式化后的数据不是数组');
//       }
//       // 创建与系统类似的预览对话框
//       const dialogWrapper = document.createElement('div');
//       dialogWrapper.className = 'el-dialog__wrapper';
//       dialogWrapper.style.cssText = `z-index: ${getRandomZIndex()};`;

//       const dialog = document.createElement('div');
//       dialog.className = 'el-dialog';
//       dialog.setAttribute('role', 'dialog');
//       dialog.setAttribute('aria-modal', 'true');
//       dialog.setAttribute('aria-label', `调入清单打印预览-(已选择${transferNos.length}个单据)`);
//       dialog.style.cssText = 'margin-top: 15vh; width: 80%;';

//       // 对话框头部
//       const dialogHeader = document.createElement('div');
//       dialogHeader.className = 'el-dialog__header';
//       dialogHeader.innerHTML = `<span class="el-dialog__title">调入清单打印预览-(已选择${transferNos.length}个单据)</span>
//         <button type="button" aria-label="Close" class="el-dialog__headerbtn">
//           <i class="el-dialog__close el-icon el-icon-close"></i>
//         </button>`;

//       // 对话框主体
//       const dialogBody = document.createElement('div');
//       dialogBody.className = 'el-dialog__body';

//       // 打印机选择区域
//       const printerSelect = document.createElement('div');
//       printerSelect.style.cssText = 'margin-bottom: 20px;';
//       printerSelect.innerHTML = '<span style="font-weight: bold;">选择打印机:</span>';

//       const selectContainer = document.createElement('div');
//       selectContainer.className = 'el-select el-select--small';
//       selectContainer.style.cssText = 'width: 300px; margin-top: 10px;';

//       // 输入框
//       const selectInput = document.createElement('div');
//       selectInput.className = 'el-input el-input--small el-input--suffix';
//       selectInput.innerHTML = `
//         <input type="text" readonly="readonly" autocomplete="off" placeholder="点击选择打印机" 
//               class="el-input__inner" id="printerInput">
//         <span class="el-input__suffix">
//           <span class="el-input__suffix-inner">
//             <i class="el-select__caret el-input__icon el-icon-arrow-up"></i>
//           </span>
//         </span>
//       `;

//       // 下拉选项容器
//       const dropdown = document.createElement('div');
//       dropdown.className = 'el-select-dropdown el-popper';
//       dropdown.style.cssText = 'display: none; min-width: 300px; max-height: 200px; overflow-y: auto;';

//       const dropdownContent = document.createElement('div');
//       dropdownContent.className = 'el-scrollbar';
//       dropdownContent.innerHTML = `
//         <div class="el-select-dropdown__wrap el-scrollbar__wrap" style="margin-bottom: -12px; margin-right: -12px;">
//           <ul class="el-scrollbar__view el-select-dropdown__list" id="printerList">
//             <li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>
//           </ul>
//         </div>
//       `;

//       dropdown.appendChild(dropdownContent);
//       selectContainer.appendChild(selectInput);
//       selectContainer.appendChild(dropdown);
//       printerSelect.appendChild(selectContainer);

//       // 当前选中的打印机
//       let selectedPrinter = null;

//       // 加载打印机列表
//       async function loadPrinterList() {
//         try {
//           const printerList = document.getElementById('printerList');

//           // 清除之前的加载状态
//           printerList.innerHTML = '<li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>';

//           // 使用iframe获取打印机列表（绕过CSP）
//           const printerIframe = document.createElement('iframe');
//           printerIframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
//           printerIframe.srcdoc = `
//         <script>
//           try {
//             const LODOP = window.parent.CLODOP || window.parent.getLodop();
//             if (LODOP) {
//               const printerCount = LODOP.GET_PRINTER_COUNT();
//               const printers = [];
//               let defaultPrinterIndex = -1;
              
//               // 尝试多种方法确定默认打印机
              
//               // 方法2: 如果上面失败，尝试找到包含"默认"字样的打印机
//               for (let i = 0; i < printerCount; i++) {
//                 const printerName = LODOP.GET_PRINTER_NAME(i);
//                 printers.push({
//                   index: i,
//                   name: printerName,
//                   isDefault: i === defaultPrinterIndex
//                 });
                
//                 // 如果还没有找到默认打印机，尝试根据名称判断
//                 if (defaultPrinterIndex === -1) {
//                   if (printerName.toLowerCase().includes('default') || 
//                       printerName.includes('默认') ||
//                       printerName.toLowerCase().includes('epson') || // 常见的默认打印机
//                       printerName.toLowerCase().includes('hp') ||
//                       printerName.toLowerCase().includes('canon')) {
//                     defaultPrinterIndex = i;
//                   }
//                 }
//               }
              
//               // 方法3: 如果仍然没有找到，使用第一个打印机
//               if (defaultPrinterIndex === -1 && printers.length > 0) {
//                 defaultPrinterIndex = 0;
//               }
              
//               window.parent.postMessage({
//                 type: 'PRINTER_LIST_LOADED',
//                 printers: printers,
//                 defaultPrinterIndex: defaultPrinterIndex
//               }, '*');
//             } else {
//               window.parent.postMessage({
//                 type: 'PRINTER_LIST_ERROR',
//                 error: 'CLodop未初始化'
//               }, '*');
//             }
//           } catch (error) {
//             window.parent.postMessage({
//               type: 'PRINTER_LIST_ERROR',
//               error: error.message
//             }, '*');
//           }
//         </script>
//       `;

//           document.body.appendChild(printerIframe);

//           // 创建唯一的事件ID，避免重复监听
//           const eventId = 'printer_list_' + Date.now();

//           // 监听打印机列表加载完成
//           const messageHandler = (event) => {
//             // 只处理当前会话的事件
//             if (event.data.type === 'PRINTER_LIST_LOADED' || event.data.type === 'PRINTER_LIST_ERROR') {
//               window.removeEventListener('message', messageHandler);

//               if (printerIframe.parentNode) {
//                 document.body.removeChild(printerIframe);
//               }

//               if (event.data.type === 'PRINTER_LIST_LOADED') {
//                 const printers = event.data.printers;
//                 const defaultPrinterIndex = event.data.defaultPrinterIndex;
//                 printerList.innerHTML = '';

//                 if (printers.length === 0) {
//                   printerList.innerHTML = '<li class="el-select-dropdown__item"><span>未找到可用打印机</span></li>';
//                 } else {
//                   printers.forEach((printer, index) => {
//                     const item = document.createElement('li');
//                     item.className = 'el-select-dropdown__item';

//                     // 默认选择系统默认打印机
//                     if (defaultPrinterIndex !== -1 && printer.index === defaultPrinterIndex) {
//                       item.classList.add('selected');
//                       selectedPrinter = printer;
//                       document.getElementById('printerInput').value = printer.name;
//                       item.innerHTML = `<span>${printer.name} (默认)</span>`;
//                     } else {
//                       item.innerHTML = `<span>${printer.name}</span>`;
//                     }

//                     item.dataset.index = printer.index;
//                     item.dataset.name = printer.name;

//                     item.addEventListener('click', () => {
//                       // 移除之前选中的样式
//                       document.querySelectorAll('.el-select-dropdown__item.selected').forEach(el => {
//                         el.classList.remove('selected');
//                       });

//                       // 添加选中样式
//                       item.classList.add('selected');

//                       // 更新输入框显示
//                       document.getElementById('printerInput').value = printer.name;

//                       // 更新选中的打印机
//                       selectedPrinter = printer;

//                       // 隐藏下拉菜单
//                       dropdown.style.display = 'none';
//                     });

//                     printerList.appendChild(item);
//                   });
//                 }
//               } else {
//                 printerList.innerHTML = `<li class="el-select-dropdown__item"><span>加载打印机失败: ${event.data.error}</span></li>`;
//               }

//               // 清除超时定时器
//               clearTimeout(timeoutId);
//             }
//           };

//           window.addEventListener('message', messageHandler);

//           // 超时处理
//           const timeoutId = setTimeout(() => {
//             window.removeEventListener('message', messageHandler);
//             if (printerIframe.parentNode) {
//               document.body.removeChild(printerIframe);
//             }
//             printerList.innerHTML = '<li class="el-select-dropdown__item"><span>加载超时，请检查CLodop</span></li>';
//           }, 5000);

//         } catch (error) {
//           console.error('加载打印机列表失败:', error);
//           document.getElementById('printerList').innerHTML = '<li class="el-select-dropdown__item"><span>加载失败</span></li>';
//         }
//       }

//       // 下拉菜单显示/隐藏控制
//       const inputField = selectInput.querySelector('input');
//       const dropdownIcon = selectInput.querySelector('.el-select__caret');

//       function toggleDropdown() {
//         if (dropdown.style.display === 'none') {
//           dropdown.style.display = 'block';
//           dropdownIcon.classList.remove('el-icon-arrow-up');
//           dropdownIcon.classList.add('el-icon-arrow-down');
//         } else {
//           dropdown.style.display = 'none';
//           dropdownIcon.classList.remove('el-icon-arrow-down');
//           dropdownIcon.classList.add('el-icon-arrow-up');
//         }
//       }

//       inputField.addEventListener('click', toggleDropdown);
//       dropdownIcon.addEventListener('click', toggleDropdown);

//       // 点击外部关闭下拉菜单
//       document.addEventListener('click', (event) => {
//         if (!selectContainer.contains(event.target)) {
//           dropdown.style.display = 'none';
//           dropdownIcon.classList.remove('el-icon-arrow-down');
//           dropdownIcon.classList.add('el-icon-arrow-up');
//         }
//       });

//       // // 添加“加价调拨”开关按钮
//       // const priceToggleContainer = document.createElement('div');
//       // priceToggleContainer.style.cssText = 'margin-bottom: 20px; display: flex; align-items: center;';

//       // const priceToggleLabel = document.createElement('span');
//       // priceToggleLabel.style.cssText = 'font-weight: bold; margin-right: 10px;';
//       // priceToggleLabel.textContent = '加价调拨:';

//       // const priceToggle = document.createElement('input');
//       // priceToggle.type = 'checkbox';
//       // priceToggle.id = 'priceToggle';
//       // priceToggle.style.cssText = 'margin-right: 5px;';

//       // priceToggleContainer.appendChild(priceToggleLabel);
//       // priceToggleContainer.appendChild(priceToggle);

//       // // 添加"急用"复选框
//       // const urgentToggleContainer = document.createElement('div');
//       // urgentToggleContainer.style.cssText = 'margin-bottom: 20px; display: flex; align-items: center;';

//       // const urgentToggleLabel = document.createElement('span');
//       // urgentToggleLabel.style.cssText = 'font-weight: bold; margin-right: 10px;';
//       // urgentToggleLabel.textContent = '急用:';

//       // const urgentToggle = document.createElement('input');
//       // urgentToggle.type = 'checkbox';
//       // urgentToggle.id = 'urgentToggle';
//       // urgentToggle.style.cssText = 'margin-right: 5px;';

//       // urgentToggleContainer.appendChild(urgentToggleLabel);
//       // urgentToggleContainer.appendChild(urgentToggle);

//       // // // 按钮区域
//       // // const buttonContainer = document.createElement('div');
//       // // buttonContainer.style.cssText = 'text-align: center; margin-top: 20px;';
//       // // buttonContainer.innerHTML = `
//       // //   <button type="button" class="el-button el-button--default el-button--small">
//       // //     <span>返　回</span>
//       // //   </button>
//       // //   <button type="button" class="el-button el-button--primary el-button--small">
//       // //     <span>打　印</span>
//       // //   </button>
//       // // `;

//     // 将三个复选框放在同一行
//     const toggleContainer = document.createElement('div');
//     toggleContainer.style.cssText = 'margin-bottom: 20px; display: flex; align-items: center; gap: 20px;';

//     // 添加"加价调拨"开关按钮
//     const priceToggleContainer = document.createElement('div');
//     priceToggleContainer.style.cssText = 'display: flex; align-items: center;';

//     const priceToggleLabel = document.createElement('span');
//     priceToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
//     priceToggleLabel.textContent = '加价调拨:';

//     const priceToggle = document.createElement('input');
//     priceToggle.type = 'checkbox';
//     priceToggle.id = 'priceToggle';
//     priceToggle.style.cssText = 'margin-right: 5px;';

//     priceToggleContainer.appendChild(priceToggleLabel);
//     priceToggleContainer.appendChild(priceToggle);
//     toggleContainer.appendChild(priceToggleContainer);

//     // 添加"仅备注"复选框
//     const onlyRemarkToggleContainer = document.createElement('div');
//     onlyRemarkToggleContainer.style.cssText = 'display: flex; align-items: center;';

//     const onlyRemarkToggleLabel = document.createElement('span');
//     onlyRemarkToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
//     onlyRemarkToggleLabel.textContent = '仅备注:';

//     const onlyRemarkToggle = document.createElement('input');
//     onlyRemarkToggle.type = 'checkbox';
//     onlyRemarkToggle.id = 'onlyRemarkToggle';
//     onlyRemarkToggle.style.cssText = 'margin-right: 5px;';

//     onlyRemarkToggleContainer.appendChild(onlyRemarkToggleLabel);
//     onlyRemarkToggleContainer.appendChild(onlyRemarkToggle);
//     toggleContainer.appendChild(onlyRemarkToggleContainer);

//     // 添加"急用"复选框
//     const urgentToggleContainer = document.createElement('div');
//     urgentToggleContainer.style.cssText = 'display: flex; align-items: center;';

//     const urgentToggleLabel = document.createElement('span');
//     urgentToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
//     urgentToggleLabel.textContent = '急用:';

//     const urgentToggle = document.createElement('input');
//     urgentToggle.type = 'checkbox';
//     urgentToggle.id = 'urgentToggle';
//     urgentToggle.style.cssText = 'margin-right: 5px;';

//     urgentToggleContainer.appendChild(urgentToggleLabel);
//     urgentToggleContainer.appendChild(urgentToggle);
//     toggleContainer.appendChild(urgentToggleContainer);

//     // 添加"前档空库位"复选框
//     const emptyLocationToggleContainer = document.createElement('div');
//     emptyLocationToggleContainer.style.cssText = 'display: flex; align-items: center; margin-left: 15px;';

//     const emptyLocationToggleLabel = document.createElement('span');
//     emptyLocationToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
//     emptyLocationToggleLabel.textContent = '前档空库位:';

//     const emptyLocationToggle = document.createElement('input');
//     emptyLocationToggle.type = 'checkbox';
//     emptyLocationToggle.id = 'emptyLocationToggle';
//     emptyLocationToggle.style.cssText = 'margin-right: 5px;';

//     emptyLocationToggleContainer.appendChild(emptyLocationToggleLabel);
//     emptyLocationToggleContainer.appendChild(emptyLocationToggle);
//     toggleContainer.appendChild(emptyLocationToggleContainer);

//       // 按钮区域
//       const buttonContainer = document.createElement('div');
//       buttonContainer.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 20px;';
//       buttonContainer.innerHTML = `
//       <button type="button" class="el-button el-button--default el-button--small">
//         <span>返　回</span>
//       </button>
//       <button type="button" class="el-button el-button--primary el-button--small">
//         <span>打　印</span>
//       </button>
//       <div class="el-dropdown" style="display: inline-block; margin-left: 10px;">
//         <button type="button" class="el-button el-button--success el-button--small" id="exportButton">
//           <span>导　出</span>
//           <i class="el-icon-arrow-down el-icon--right"></i>
//         </button>
//         <ul class="el-dropdown-menu el-popper" style="display: none; min-width: 120px; position: absolute; z-index: 9999; background-color: #fff; border: 1px solid #ebeef5; border-radius: 4px; box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);">
//           <li class="el-dropdown-menu__item" data-type="excel" style="list-style: none; line-height: 36px; padding: 0 20px; margin: 0; font-size: 14px; color: #606266; cursor: pointer;">
//             <i class="el-icon-document"></i> Excel格式
//           </li>
//           <li class="el-dropdown-menu__item" data-type="pdf" style="list-style: none; line-height: 36px; padding: 0 20px; margin: 0; font-size: 14px; color: #606266; cursor: pointer;">
//             <i class="el-icon-document"></i> PDF格式
//           </li>
//         </ul>
//       </div>
//       `;

//       // 打印预览内容区域
//       const printPreviewDiv = document.createElement('div');
//       printPreviewDiv.id = 'printPreviewDiv';

//       /**
//        * 根据仓库名称获取仓库代码和仓库ID
//        * @param {string} warehouseName - 仓库名称
//        * @returns {Object} - 返回仓库代码和仓库ID
//        */
//       function getWarehouseInfo(warehouseName) {
//         const WAREHOUSE_MAPPING = {
//           "郑州库": { "storage_code": "ZZ", "warehouseId": 6 },
//           "西安库": { "storage_code": "XA", "warehouseId": 7 },
//           "兰州库": { "storage_code": "LZ", "warehouseId": 8 },
//           "驻马店库": { "storage_code": "ZMD", "warehouseId": 9 },
//           "茶城库": { "storage_code": "CC", "warehouseId": 10 },
//           "商丘库": { "storage_code": "SQ", "warehouseId": 11 },
//           "洛阳库": { "storage_code": "LY", "warehouseId": 12 },
//           "雁塔库": { "storage_code": "YT", "warehouseId": 13 },
//           "西宁库": { "storage_code": "XN", "warehouseId": 14 },
//           "榆林库": { "storage_code": "YL", "warehouseId": 15 },
//           "银川库": { "storage_code": "YC", "warehouseId": 16 },
//           "西安西郊库": { "storage_code": "XA-XJ", "warehouseId": 18 }
//         };
//         return WAREHOUSE_MAPPING[warehouseName] || { storage_code: "SQ", warehouseId: 11 };
//       }


//       /**
//        * 构建库存数据的索引结构
//        * @param {Object} stock_data - 库存数据
//        * @returns {Object} - 返回按库位和产品编码索引的数据
//        */
//       function build_stock_indices(stock_data) {
//         const location_index = {};
//         const part_code_index = {};

//         if (stock_data && stock_data.data && stock_data.data.rows) {
//           stock_data.data.rows.forEach(item => {
//             // 简化数据
//             const simplified_item = {
//               part_code: item.part_code,
//               location_accessories_number: item.location_accessories_number,
//               location_no: item.location_no
//             };

//             // 按库位索引
//             if (simplified_item.location_no) {
//               if (!location_index[simplified_item.location_no]) {
//                 location_index[simplified_item.location_no] = [];
//               }
//               location_index[simplified_item.location_no].push(simplified_item);
//             }

//             // 按产品编码索引
//             if (simplified_item.part_code) {
//               if (!part_code_index[simplified_item.part_code]) {
//                 part_code_index[simplified_item.part_code] = [];
//               }
//               part_code_index[simplified_item.part_code].push(simplified_item);
//             }
//           });
//         }

//         return {
//           location: location_index,
//           part_code: part_code_index
//         };
//       }

//       async function generatePrintHTML(isPriceTransfer, isUrgent, isOnlyRemark,searchParams, showEmptyLocations) {
//         let printHTML = '';
//         // const searchParams = getSearchParams();
//         const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
//         const storage_code = warehouseInfo.storage_code;
//         const warehouseId = warehouseInfo.warehouseId;

//         const empty_locations = await find_empty_locations(storage_code)
//         const all_stock_data = await get_all_stock_data(storage_code);
//         const stock_indices = build_stock_indices(all_stock_data);

//         // 如果启用前档空库位显示，生成空库位预览页面
//         let emptyLocationsHTML = '';
//         if (showEmptyLocations && empty_locations.length > 0) {
//           emptyLocationsHTML = generateEmptyLocationsHTML(empty_locations, storage_code);
//         }

//         // 使用 Promise.all 处理异步操作
//         const formattedDataPromises = formattedData.map(async (group, groupIndex) => {
//           const header = group.headerInfo;
//           let items = group.items;
//           const transferType = header.transferType;
//           // const isPriceTransfer = transferType === 47171002 || transferType === '47171002';
//           // 如果启用了"急用"筛选，只显示有备注的条目
//           if (isUrgent) {
//             items = items.filter(item => item.remark && item.remark.trim() !== '');
//           }
//           // 如果筛选后items为空，返回空字符串，跳过这个调拨单
//           if (items.length === 0) {
//             return '';
//           }
    
//           // // 处理每个 item 的异步操作
//           // const itemsHTML = await Promise.all(
//           //   items.map(async (item, index) => {
//           //     const quantity = parseInt(item.inboundQuantity) || 0;
//           //     const price = parseFloat(item.salesPrice) || 0;
//           //     const rate = parseFloat(item.priceIncreaseRate) || 1;
//           //     const amount = (quantity * price * rate).toFixed(2);

//           //     // 获取库位库存数量
//           //     const inboundLocationNo = item.inboundLocationNo;
//           //     const locationStock = stock_indices.location[inboundLocationNo] || [];
//           //     const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
//           //     // 入库库位显示逻辑
//           //     const inboundLocationDisplay = inboundLocationNo ? `${inboundLocationNo}\n【${stockQty}】` : '';

//           //     // 获取指示库位库存数量
//           //     const shelfLocationNo = item.shelfLocationNo;
//           //     const shelfLocationNostock = stock_indices.location[shelfLocationNo] || [];
//           //     const shelfQty = shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
//           //     // 指示库位显示逻辑
//           //     const shelfLocationDisplay = shelfLocationNo ? `${shelfLocationNo}\n【${shelfQty}】` : '';

//           //     // 获取调拨前库存数
//           //     const partCode = item.partCode;
//           //     let prestockvalue = ''; // 初始化为空字符串
//           //     if (partCode) {
//           //       const stock_data = stock_indices['part_code'][partCode] || [];
//           //       if (stock_data && stock_data.length > 0) {
//           //           const locations = [];
//           //           const quantities = [];
//           //           for (const loc of stock_data) {
//           //               locations.push(loc['location_no'] || '');
//           //               quantities.push(String(loc['location_accessories_number'] || 0));
//           //           }
//           //           if (locations.length > 0 && quantities.length > 0) {
//           //               prestockvalue = `${locations.join('\n')}\n【${quantities.join(',')}】`;
//           //           }
//           //       }
//           //     }
//           //     // const preTransferStock = stock_indices.part_code[partCode] || [];
//           //     // const preTransferQty = preTransferStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);

//           //     // 获取3月内最近出库信息
//           //     const orderData = await query_order_by_code(partCode, warehouseId);
//           //     const recentSaleInfo =`${get_recent_sale_location(orderData)}`;
//           //     // 判断是否添加入库数量为0的删除线样式
//           //     const rowClass = quantity === 0 ? 'class="strike-through"' : '';
//           //     return `
//           //   <tr ${rowClass}>
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
//           //     <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.partCode || ''}</td>
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${inboundLocationDisplay}</td>
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
//           //     ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${shelfLocationDisplay}</td>` : ''}
//           //     ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${prestockvalue || ''}</td>` : ''}
//           //     ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${recentSaleInfo}</td>` : ''}
//           //     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.remark || ''}</td>
//           //     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
//           //     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
//           //     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
//           //   </tr>
//           // `;
//           //   })
//           // );

//           // 处理每个 item 的异步操作
//           const itemsHTML = await Promise.all(
//             items.map(async (item, index) => {
//               const quantity = parseInt(item.inboundQuantity) || 0;
//               const price = parseFloat(item.salesPrice) || 0;
//               const rate = parseFloat(item.priceIncreaseRate) || 1;
//               const amount = (quantity * price * rate).toFixed(2);

//               // 获取库位库存数量（入库库位需要始终获取，因为即使仅备注也需要显示）
//               const inboundLocationNo = item.inboundLocationNo;
//               const locationStock = stock_indices.location[inboundLocationNo] || [];
//               const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
//               // 入库库位显示逻辑
//               const inboundLocationDisplay = inboundLocationNo ? `${inboundLocationNo}\n【${stockQty}】` : '';

//               // 当不是"仅备注"模式时，才获取指示库位、调拨前库存数和3月内最近出库信息
//               let shelfLocationDisplay = '';
//               let prestockvalue = '';
//               let recentSaleInfo = '';

//               if (!isOnlyRemark) {
//                 // 获取指示库位库存数量
//                 const shelfLocationNo = item.shelfLocationNo;
//                 const shelfLocationNostock = stock_indices.location[shelfLocationNo] || [];
//                 const shelfQty = shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
//                 shelfLocationDisplay = shelfLocationNo ? `${shelfLocationNo}\n【${shelfQty}】` : '';

//                 // 获取调拨前库存数
//                 const partCode = item.partCode;
//                 if (partCode) {
//                   const stock_data = stock_indices['part_code'][partCode] || [];
//                   if (stock_data && stock_data.length > 0) {
//                     const locations = [];
//                     const quantities = [];
//                     for (const loc of stock_data) {
//                       locations.push(loc['location_no'] || '');
//                       quantities.push(String(loc['location_accessories_number'] || 0));
//                     }
//                     if (locations.length > 0 && quantities.length > 0) {
//                       prestockvalue = `${locations.join('\n')}\n【${quantities.join(',')}】`;
//                     }
//                   }
//                 }

//                 // 获取3月内最近出库信息（只有非仅备注模式才发起网络请求）
//                 const orderData = await query_order_by_code(partCode, warehouseId);
//                 recentSaleInfo = get_recent_sale_location(orderData);
//               }

//               // 判断是否添加入库数量为0的删除线样式
//               const rowClass = quantity === 0 ? 'class="strike-through"' : '';
//               return `
//       <tr ${rowClass}>
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
//         <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.partCode || ''}</td>
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${inboundLocationDisplay}</td>
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
//         ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${shelfLocationDisplay}</td>` : ''}
//         ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${prestockvalue || ''}</td>` : ''}
//         ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${recentSaleInfo}</td>` : ''}
//         <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.remark || ''}</td>
//         ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
//         ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
//         ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
//       </tr>
//     `;
//             })
//           );


//           // 生成每个调拨单的 HTML
//           return `
//           <div id="transferPrintDiv${groupIndex}" index="${groupIndex}">
//             <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
//               <div style="width: 100%; margin: 0px auto; text-align: center;">
//                 <span style="font-size: 25px; font-weight: bold;">调入清单</span>
//               </div>
//               <div style="width: 100%; margin: 0px; text-align: left;">
//                 <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 98%;">
//                   <tbody>
//                     <tr>
//                       <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
//                       <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
//                       <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${getShortTransferNo(header.transferNo) || ''}</td>
//                     </tr>
//                     <tr>
//                       <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
//                       <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
//                       <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
//                     </tr>
//                   </tbody>
//                 </table>
//                 <table align="center" valign="middle" style="width: 100%; margin: 0px auto; font-size: 14px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
//                   <tbody>
//                     <tr>
//                       <td style="width: ${!isOnlyRemark ? '5' : '8'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
//                       <td style="width: ${!isOnlyRemark ? '28' : '38'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
//                       <td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
//                       <td style="width: ${!isOnlyRemark ? '15' : '20'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">产品编码</td>
//                       <td style="width: ${!isOnlyRemark ? '7' : '10'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n库位</td>
//                       <td style="width: ${!isOnlyRemark ? '5' : '8'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n数量</td>
//                       ${!isOnlyRemark ? `<td style="width: 7%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">指示\n库位</td>` : ''}
//                       ${!isOnlyRemark ? `<td style="width: 7%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">调拨前\n库存数</td>` : ''}
//                       ${!isOnlyRemark ? `<td style="width: 14%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">3月内最近\n出库信息</td>` : ''}
//                       <td style="width: ${!isOnlyRemark ? '7' : '11'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">备注</td>
//                       ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
//                       ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
//                       ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
//                     </tr>
//                     ${itemsHTML.join('')}
//                     <tr style="text-align: center;">
//                       <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
//                       <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
//                       <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
//                       <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
//                       <td colspan="${!isOnlyRemark ? '4' : '1'}" style="border: 1px solid rgb(0, 0, 0);"></td>
//                       ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
//                     </tr>
//                   </tbody>
//                 </table>
//               </div>
//             </div>
//           </div>
//         `;
//         });

//         // 等待所有调拨单的 HTML 生成完成
//         const formattedDataHTML = await Promise.all(formattedDataPromises);
//         // 过滤掉空字符串（即items为空的调拨单）
//         printHTML = formattedDataHTML.filter(html => html !== '').join('');

//         // 如果启用了前档空库位显示，在最后添加空库位预览页面
//         if (showEmptyLocations && emptyLocationsHTML) {
//           printHTML += emptyLocationsHTML;
//         }

//         // 在生成打印 HTML 的顶层添加样式
//         const style = `
//           <style>
//             .strike-through {
//               text-decoration: line-through;
//               color: #999; /* 可选：让删除线行的颜色变浅 */
//             }
//           </style>
//         `;
//         // 在最终打印 HTML 中包含样式
//         printHTML = style + printHTML;
//         return printHTML;
//       }


//       // // 异步调用
//       // generatePrintHTML(false,false)
//       //   .then(html => {
//       //     printPreviewDiv.innerHTML = html;
//       //   })
//       //   .catch(error => {
//       //     console.error('生成打印内容失败:', error);
//       //     showMessage('生成打印内容失败: ' + error.message, 'error');
//       //   });
//       // 修复初始调用部分（第1534行附近）
//       // 异步调用
//       (async () => {
//         try {
//           const html = await generatePrintHTML(false, false, false,searchParams,false); // 初始三个复选框都不选中
//           printPreviewDiv.innerHTML = html;
//         } catch (error) {
//           console.error('生成打印内容失败:', error);
//           showMessage('生成打印内容失败: ' + error.message, 'error');
//         }
//       })();

//       // // 监听价格开关状态变化
//       // priceToggle.addEventListener('change', (event) => {
//       //   const isChecked = event.target.checked;
//       //   printPreviewDiv.innerHTML = generatePrintHTML(isChecked);
//       // });
//       // // 监听价格开关状态变化
//       // priceToggle.addEventListener('change', async (event) => {
//       //   const isChecked = event.target.checked;
//       //   generatePrintHTML(isChecked)
//       //     .then(html => {
//       //       printPreviewDiv.innerHTML = html;
//       //     })
//       //     .catch(error => {
//       //       console.error('生成打印内容失败:', error);
//       //       showMessage('生成打印内容失败: ' + error.message, 'error');
//       //     });
//       // });
//       // 3. 修改按钮事件监听部分（约1530行）

//       // 修复事件监听部分（第1564行附近）
//       // 监听价格开关状态变化
//       priceToggle.addEventListener('change', async (event) => {
//         try {
//           const isPriceChecked = event.target.checked;
//           const isUrgentChecked = urgentToggle.checked; // 获取急用复选框状态
//           const isOnlyRemarkChecked = onlyRemarkToggle.checked;
//           const isEmptyLocationChecked = event.target.checked;
//           const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked,searchParams,isEmptyLocationChecked);
//           printPreviewDiv.innerHTML = html;
//         } catch (error) {
//           console.error('生成打印内容失败:', error);
//           showMessage('生成打印内容失败: ' + error.message, 'error');
//         }
//       });

//       // 监听急用复选框状态变化
//       urgentToggle.addEventListener('change', async (event) => {
//         try {
//           const isPriceChecked = priceToggle.checked; // 获取价格复选框状态
//           const isUrgentChecked = event.target.checked;
//           const isOnlyRemarkChecked = onlyRemarkToggle.checked;
//           const isEmptyLocationChecked = event.target.checked;
//           const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked,searchParams,isEmptyLocationChecked);
//           printPreviewDiv.innerHTML = html;
//         } catch (error) {
//           console.error('生成打印内容失败:', error);
//           showMessage('生成打印内容失败: ' + error.message, 'error');
//         }
//       });

//       // 监听"仅备注"复选框状态变化
//       onlyRemarkToggle.addEventListener('change', async (event) => {
//         try {
//           const isPriceChecked = priceToggle.checked; // 获取价格复选框状态
//           const isUrgentChecked = urgentToggle.checked;
//           const isOnlyRemarkChecked = event.target.checked;
//           const isEmptyLocationChecked = event.target.checked;
//           const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked,searchParams,isEmptyLocationChecked);
//           printPreviewDiv.innerHTML = html;
//         } catch (error) {
//           console.error('生成打印内容失败:', error);
//           showMessage('生成打印内容失败: ' + error.message, 'error');
//         }
//       });

//       // 监听前档空库位开关状态变化
//       emptyLocationToggle.addEventListener('change', async (event) => {
//         try {
//           const isPriceChecked = priceToggle.checked;
//           const isUrgentChecked = urgentToggle.checked;
//           const isOnlyRemarkChecked = onlyRemarkToggle.checked;
//           const isEmptyLocationChecked = event.target.checked;

//           const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked, searchParams, isEmptyLocationChecked);
//           printPreviewDiv.innerHTML = html;
//         } catch (error) {
//           console.error('生成打印内容失败:', error);
//           showMessage('生成打印内容失败: ' + error.message, 'error');
//         }
//       });


//       // 组装对话框
//       dialogBody.appendChild(printerSelect);
//       dialogBody.appendChild(toggleContainer);
//       dialogBody.appendChild(buttonContainer);
//       dialogBody.appendChild(printPreviewDiv);

//       dialog.appendChild(dialogHeader);
//       dialog.appendChild(dialogBody);
//       dialogWrapper.appendChild(dialog);

//       document.body.appendChild(dialogWrapper);

//       // 添加事件监听器
//       const closeButton = dialogHeader.querySelector('.el-dialog__headerbtn');
//       const returnButton = buttonContainer.querySelector('.el-button--default');
//       const printButton = buttonContainer.querySelector('.el-button--primary');




//       // 设置导出功能事件
//       setupExportEvents(buttonContainer, priceToggle, urgentToggle, searchParams, formattedData);


//       // // 处理导出类型选择
//       // exportDropdown.querySelectorAll('.el-dropdown-menu__item').forEach(item => {
//       //   item.addEventListener('click', async (event) => {
//       //     event.stopPropagation();
//       //     const exportType = event.currentTarget.dataset.type;

//       //     try {
//       //       const isPriceTransfer = priceToggle.checked;
//       //       const isUrgent = urgentToggle.checked;

//       //       // 获取导出数据
//       //       const exportData = await generateExportData(isPriceTransfer, isUrgent);

//       //       if (exportData.length === 0) {
//       //         showMessage('没有可导出的数据', 'warning');
//       //         return;
//       //       }

//       //       // 生成文件名
//       //       const fileName = generateFileName(isUrgent);

//       //       if (exportType === 'excel') {
//       //         exportToExcel(exportData, fileName);
//       //       } else if (exportType === 'pdf') {
//       //         exportToPDF(exportData, fileName);
//       //       }

//       //       showMessage(`导出成功: ${fileName}`, 'success');
//       //       exportDropdown.style.display = 'none';
//       //     } catch (error) {
//       //       console.error('导出失败:', error);
//       //       showMessage('导出失败: ' + error.message, 'error');
//       //     }
//       //   });
//       // });

//       // 关闭对话框
//       const closeDialog = () => {
//         if (dialogWrapper.parentNode) {
//           dialogWrapper.parentNode.removeChild(dialogWrapper);
//         }
//       };

//       closeButton.addEventListener('click', closeDialog);
//       returnButton.addEventListener('click', closeDialog);

//       // 打印功能
//       printButton.addEventListener('click', async () => {
//         try {
//           if (!selectedPrinter) {
//             showMessage('请先选择打印机', 'warning');
//             return;
//           }

//           // 直接打印预览内容
//           await printDirect(printPreviewDiv.innerHTML, selectedPrinter.name);

//           // 显示成功消息
//           showMessage(`打印任务已发送到打印机: ${selectedPrinter.name}`, 'success');
//           // 打印成功后自动关闭预览对话框
//           closeDialog();
//         } catch (error) {
//           console.error('打印失败:', error);
//           showMessage('打印失败: ' + error.message, 'error');
//         }
//       });


//       // 加载打印机列表
//       setTimeout(loadPrinterList, 100);

//     } catch (error) {
//       console.error('打开打印预览失败:', error);
//       showMessage('打开打印预览失败: ' + error.message, 'error');
//     }

// 显示打印预览
async function showPrintPreview(printData, transferNos, searchParams) {

    try {
      // 格式化数据
      const formattedData = await formatPrintData(printData);

      // 检查 formattedData 是否为数组
      if (!Array.isArray(formattedData)) {
        throw new Error('格式化后的数据不是数组');
      }

      // ===== 新增：缓存变量 =====
      const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
      const storage_code = warehouseInfo.storage_code;
      const warehouseId = warehouseInfo.warehouseId;

      // 使用空对象标记"未加载"状态
      let cachedEmptyLocations = []; // 空库位缓存
      let cachedStockData = null;     // 库存数据缓存
      let cachedStockIndices = null;   // 库存索引缓存
      let cachedSaleInfo = {};       // 销售信息缓存（按产品编码索引）
      // ===== 缓存变量结束 =====

      // 创建与系统类似的预览对话框
      const dialogWrapper = document.createElement('div');
      dialogWrapper.className = 'el-dialog__wrapper';
      dialogWrapper.style.cssText = `z-index: ${getRandomZIndex()};`;

      const dialog = document.createElement('div');
      dialog.className = 'el-dialog';
      dialog.setAttribute('role', 'dialog');
      dialog.setAttribute('aria-modal', 'true');
      dialog.setAttribute('aria-label', `调入清单打印预览-(已选择${transferNos.length}个单据)`);
      dialog.style.cssText = 'margin-top: 15vh; width: 80%;';

      // 对话框头部
      const dialogHeader = document.createElement('div');
      dialogHeader.className = 'el-dialog__header';
      dialogHeader.innerHTML = `<span class="el-dialog__title">调入清单打印预览-(已选择${transferNos.length}个单据)</span>
        <button type="button" aria-label="Close" class="el-dialog__headerbtn">
          <i class="el-dialog__close el-icon el-icon-close"></i>
        </button>`;

      // 对话框主体
      const dialogBody = document.createElement('div');
      dialogBody.className = 'el-dialog__body';

      // 打印机选择区域
      const printerSelect = document.createElement('div');
      printerSelect.style.cssText = 'margin-bottom: 20px;';
      printerSelect.innerHTML = '<span style="font-weight: bold;">选择打印机:</span>';

      const selectContainer = document.createElement('div');
      selectContainer.className = 'el-select el-select--small';
      selectContainer.style.cssText = 'width: 300px; margin-top: 10px;';

      // 输入框
      const selectInput = document.createElement('div');
      selectInput.className = 'el-input el-input--small el-input--suffix';
      selectInput.innerHTML = `
        <input type="text" readonly="readonly" autocomplete="off" placeholder="点击选择打印机" 
              class="el-input__inner" id="printerInput">
        <span class="el-input__suffix">
          <span class="el-input__suffix-inner">
            <i class="el-select__caret el-input__icon el-icon-arrow-up"></i>
          </span>
        </span>
      `;

      // 下拉选项容器
      const dropdown = document.createElement('div');
      dropdown.className = 'el-select-dropdown el-popper';
      dropdown.style.cssText = 'display: none; min-width: 300px; max-height: 200px; overflow-y: auto;';

      const dropdownContent = document.createElement('div');
      dropdownContent.className = 'el-scrollbar';
      dropdownContent.innerHTML = `
        <div class="el-select-dropdown__wrap el-scrollbar__wrap" style="margin-bottom: -12px; margin-right: -12px;">
          <ul class="el-scrollbar__view el-select-dropdown__list" id="printerList">
            <li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>
          </ul>
        </div>
      `;

      dropdown.appendChild(dropdownContent);
      selectContainer.appendChild(selectInput);
      selectContainer.appendChild(dropdown);
      printerSelect.appendChild(selectContainer);

      // 当前选中的打印机
      let selectedPrinter = null;

      // 加载打印机列表
      async function loadPrinterList() {
        try {
          const printerList = document.getElementById('printerList');

          // 清除之前的加载状态
          printerList.innerHTML = '<li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>';

          // 使用iframe获取打印机列表（绕过CSP）
          const printerIframe = document.createElement('iframe');
          printerIframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
          printerIframe.srcdoc = `
          <script>
            try {
              const LODOP = window.parent.CLODOP || window.parent.getLodop();
              if (LODOP) {
                const printerCount = LODOP.GET_PRINTER_COUNT();
                const printers = [];
                let defaultPrinterIndex = -1;
                
                // 尝试多种方法确定默认打印机
                
                // 方法2: 如果上面失败，尝试找到包含"默认"字样的打印机
                for (let i = 0; i < printerCount; i++) {
                  const printerName = LODOP.GET_PRINTER_NAME(i);
                  printers.push({
                    index: i,
                    name: printerName,
                    isDefault: i === defaultPrinterIndex
                  });
                  
                  // 如果还没有找到默认打印机，尝试根据名称判断
                  if (defaultPrinterIndex === -1) {
                    if (printerName.toLowerCase().includes('default') || 
                        printerName.includes('默认') ||
                        printerName.toLowerCase().includes('epson') || // 常见的默认打印机
                        printerName.toLowerCase().includes('hp') ||
                        printerName.toLowerCase().includes('canon')) {
                      defaultPrinterIndex = i;
                    }
                  }
                }
                
                // 方法3: 如果仍然没有找到，使用第一个打印机
                if (defaultPrinterIndex === -1 && printers.length > 0) {
                  defaultPrinterIndex = 0;
                }
                
                window.parent.postMessage({
                  type: 'PRINTER_LIST_LOADED',
                  printers: printers,
                  defaultPrinterIndex: defaultPrinterIndex
                }, '*');
              } else {
                window.parent.postMessage({
                  type: 'PRINTER_LIST_ERROR',
                  error: 'CLodop未初始化'
                }, '*');
              }
            } catch (error) {
              window.parent.postMessage({
                type: 'PRINTER_LIST_ERROR',
                error: error.message
              }, '*');
            }
          </script>
        `;

          document.body.appendChild(printerIframe);

          // 创建唯一的事件ID，避免重复监听
          const eventId = 'printer_list_' + Date.now();

          // 监听打印机列表加载完成
          const messageHandler = (event) => {
            // 只处理当前会话的事件
            if (event.data.type === 'PRINTER_LIST_LOADED' || event.data.type === 'PRINTER_LIST_ERROR') {
              window.removeEventListener('message', messageHandler);

              if (printerIframe.parentNode) {
                document.body.removeChild(printerIframe);
              }

              if (event.data.type === 'PRINTER_LIST_LOADED') {
                const printers = event.data.printers;
                const defaultPrinterIndex = event.data.defaultPrinterIndex;
                printerList.innerHTML = '';

                if (printers.length === 0) {
                  printerList.innerHTML = '<li class="el-select-dropdown__item"><span>未找到可用打印机</span></li>';
                } else {
                  printers.forEach((printer, index) => {
                    const item = document.createElement('li');
                    item.className = 'el-select-dropdown__item';

                    // 默认选择系统默认打印机
                    if (defaultPrinterIndex !== -1 && printer.index === defaultPrinterIndex) {
                      item.classList.add('selected');
                      selectedPrinter = printer;
                      document.getElementById('printerInput').value = printer.name;
                      item.innerHTML = `<span>${printer.name} (默认)</span>`;
                    } else {
                      item.innerHTML = `<span>${printer.name}</span>`;
                    }

                    item.dataset.index = printer.index;
                    item.dataset.name = printer.name;

                    item.addEventListener('click', () => {
                      // 移除之前选中的样式
                      document.querySelectorAll('.el-select-dropdown__item.selected').forEach(el => {
                        el.classList.remove('selected');
                      });

                      // 添加选中样式
                      item.classList.add('selected');

                      // 更新输入框显示
                      document.getElementById('printerInput').value = printer.name;

                      // 更新选中的打印机
                      selectedPrinter = printer;

                      // 隐藏下拉菜单
                      dropdown.style.display = 'none';
                    });

                    printerList.appendChild(item);
                  });
                }
              } else {
                printerList.innerHTML = `<li class="el-select-dropdown__item"><span>加载打印机失败: ${event.data.error}</span></li>`;
              }

              // 清除超时定时器
              clearTimeout(timeoutId);
            }
          };

          window.addEventListener('message', messageHandler);

          // 超时处理
          const timeoutId = setTimeout(() => {
            window.removeEventListener('message', messageHandler);
            if (printerIframe.parentNode) {
              document.body.removeChild(printerIframe);
            }
            printerList.innerHTML = '<li class="el-select-dropdown__item"><span>加载超时，请检查CLodop</span></li>';
          }, 5000);

        } catch (error) {
          console.error('加载打印机列表失败:', error);
          document.getElementById('printerList').innerHTML = '<li class="el-select-dropdown__item"><span>加载失败</span></li>';
        }
      }

      // 下拉菜单显示/隐藏控制
      const inputField = selectInput.querySelector('input');
      const dropdownIcon = selectInput.querySelector('.el-select__caret');

      function toggleDropdown() {
        if (dropdown.style.display === 'none') {
          dropdown.style.display = 'block';
          dropdownIcon.classList.remove('el-icon-arrow-up');
          dropdownIcon.classList.add('el-icon-arrow-down');
        } else {
          dropdown.style.display = 'none';
          dropdownIcon.classList.remove('el-icon-arrow-down');
          dropdownIcon.classList.add('el-icon-arrow-up');
        }
      }

      inputField.addEventListener('click', toggleDropdown);
      dropdownIcon.addEventListener('click', toggleDropdown);

      // 点击外部关闭下拉菜单
      document.addEventListener('click', (event) => {
        if (!selectContainer.contains(event.target)) {
          dropdown.style.display = 'none';
          dropdownIcon.classList.remove('el-icon-arrow-down');
          dropdownIcon.classList.add('el-icon-arrow-up');
        }
      });

      // 将三个复选框放在同一行
      const toggleContainer = document.createElement('div');
      toggleContainer.style.cssText = 'margin-bottom: 20px; display: flex; align-items: center; gap: 20px;';

      // 添加"加价调拨"开关按钮
      const priceToggleContainer = document.createElement('div');
      priceToggleContainer.style.cssText = 'display: flex; align-items: center;';

      const priceToggleLabel = document.createElement('span');
      priceToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
      priceToggleLabel.textContent = '加价调拨:';

      const priceToggle = document.createElement('input');
      priceToggle.type = 'checkbox';
      priceToggle.id = 'priceToggle';
      priceToggle.style.cssText = 'margin-right: 5px;';

      priceToggleContainer.appendChild(priceToggleLabel);
      priceToggleContainer.appendChild(priceToggle);
      toggleContainer.appendChild(priceToggleContainer);

      // 添加"仅备注"复选框
      const onlyRemarkToggleContainer = document.createElement('div');
      onlyRemarkToggleContainer.style.cssText = 'display: flex; align-items: center;';

      const onlyRemarkToggleLabel = document.createElement('span');
      onlyRemarkToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
      onlyRemarkToggleLabel.textContent = '仅备注:';

      const onlyRemarkToggle = document.createElement('input');
      onlyRemarkToggle.type = 'checkbox';
      onlyRemarkToggle.id = 'onlyRemarkToggle';
      onlyRemarkToggle.checked = true; // 默认选中"仅备注"
      onlyRemarkToggle.style.cssText = 'margin-right: 5px;';

      onlyRemarkToggleContainer.appendChild(onlyRemarkToggleLabel);
      onlyRemarkToggleContainer.appendChild(onlyRemarkToggle);
      toggleContainer.appendChild(onlyRemarkToggleContainer);

      // 添加"急用"复选框
      const urgentToggleContainer = document.createElement('div');
      urgentToggleContainer.style.cssText = 'display: flex; align-items: center;';

      const urgentToggleLabel = document.createElement('span');
      urgentToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
      urgentToggleLabel.textContent = '急用:';

      const urgentToggle = document.createElement('input');
      urgentToggle.type = 'checkbox';
      urgentToggle.id = 'urgentToggle';
      urgentToggle.style.cssText = 'margin-right: 5px;';

      urgentToggleContainer.appendChild(urgentToggleLabel);
      urgentToggleContainer.appendChild(urgentToggle);
      toggleContainer.appendChild(urgentToggleContainer);

      // 添加"前档空库位"复选框
      const emptyLocationToggleContainer = document.createElement('div');
      emptyLocationToggleContainer.style.cssText = 'display: flex; align-items: center; margin-left: 15px;';

      const emptyLocationToggleLabel = document.createElement('span');
      emptyLocationToggleLabel.style.cssText = 'font-weight: bold; margin-right: 5px;';
      emptyLocationToggleLabel.textContent = '前档空库位:';

      const emptyLocationToggle = document.createElement('input');
      emptyLocationToggle.type = 'checkbox';
      emptyLocationToggle.id = 'emptyLocationToggle';
      emptyLocationToggle.style.cssText = 'margin-right: 5px;';

      emptyLocationToggleContainer.appendChild(emptyLocationToggleLabel);
      emptyLocationToggleContainer.appendChild(emptyLocationToggle);
      toggleContainer.appendChild(emptyLocationToggleContainer);

      // 按钮区域
      const buttonContainer = document.createElement('div');
      buttonContainer.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 20px;';
      buttonContainer.innerHTML = `
      <button type="button" class="el-button el-button--default el-button--small">
        <span>返　回</span>
      </button>
      <button type="button" class="el-button el-button--primary el-button--small">
        <span>打　印</span>
      </button>
      <div class="el-dropdown" style="display: inline-block; margin-left: 10px;">
        <button type="button" class="el-button el-button--success el-button--small" id="exportButton">
          <span>导　出</span>
          <i class="el-icon-arrow-down el-icon--right"></i>
        </button>
        <ul class="el-dropdown-menu el-popper" style="display: none; min-width: 120px; position: absolute; z-index: 9999; background-color: #fff; border: 1px solid #ebeef5; border-radius: 4px; box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);">
          <li class="el-dropdown-menu__item" data-type="excel" style="list-style: none; line-height: 36px; padding: 0 20px; margin: 0; font-size: 14px; color: #606266; cursor: pointer;">
            <i class="el-icon-document"></i> Excel格式
          </li>
          <li class="el-dropdown-menu__item" data-type="pdf" style="list-style: none; line-height: 36px; padding: 0 20px; margin: 0; font-size: 14px; color: #606266; cursor: pointer;">
            <i class="el-icon-document"></i> PDF格式
          </li>
        </ul>
      </div>
      `;

      // 打印预览内容区域
      const printPreviewDiv = document.createElement('div');
      printPreviewDiv.id = 'printPreviewDiv';

      /**
       * 根据仓库名称获取仓库代码和仓库ID
       * @param {string} warehouseName - 仓库名称
       * @returns {Object} - 返回仓库代码和仓库ID
       */
      function getWarehouseInfo(warehouseName) {
        const WAREHOUSE_MAPPING = {
          "郑州库": { "storage_code": "ZZ", "warehouseId": 6 },
          "西安库": { "storage_code": "XA", "warehouseId": 7 },
          "兰州库": { "storage_code": "LZ", "warehouseId": 8 },
          "驻马店库": { "storage_code": "ZMD", "warehouseId": 9 },
          "茶城库": { "storage_code": "CC", "warehouseId": 10 },
          "商丘库": { "storage_code": "SQ", "warehouseId": 11 },
          "洛阳库": { "storage_code": "LY", "warehouseId": 12 },
          "雁塔库": { "storage_code": "YT", "warehouseId": 13 },
          "西宁库": { "storage_code": "XN", "warehouseId": 14 },
          "榆林库": { "storage_code": "YL", "warehouseId": 15 },
          "银川库": { "storage_code": "YC", "warehouseId": 16 },
          "西安西郊库": { "storage_code": "XA-XJ", "warehouseId": 18 }
        };
        return WAREHOUSE_MAPPING[warehouseName] || { storage_code: "SQ", warehouseId: 11 };
      }


      /**
       * 构建库存数据的索引结构
       * @param {Object} stock_data - 库存数据
       * @returns {Object} - 返回按库位和产品编码索引的数据
       */
      function build_stock_indices(stock_data) {
        const location_index = {};
        const part_code_index = {};

        if (stock_data && stock_data.data && stock_data.data.rows) {
          stock_data.data.rows.forEach(item => {
            // 简化数据
            const simplified_item = {
              part_code: item.part_code,
              location_accessories_number: item.location_accessories_number,
              location_no: item.location_no
            };

            // 按库位索引
            if (simplified_item.location_no) {
              if (!location_index[simplified_item.location_no]) {
                location_index[simplified_item.location_no] = [];
              }
              location_index[simplified_item.location_no].push(simplified_item);
            }

            // 按产品编码索引
            if (simplified_item.part_code) {
              if (!part_code_index[simplified_item.part_code]) {
                part_code_index[simplified_item.part_code] = [];
              }
              part_code_index[simplified_item.part_code].push(simplified_item);
            }
          });
        }

        return {
          location: location_index,
          part_code: part_code_index
        };
      }

      // ===== 修改后的 generatePrintHTML 函数，使用缓存 =====
      async function generatePrintHTML(isPriceTransfer, isUrgent, isOnlyRemark, showEmptyLocations) {
        let printHTML = '';

        // ===== 使用缓存避免重复请求 =====
        // 只有当缓存不存在或为空时才加载数据
        if (!cachedStockData || !cachedStockData.data) {
          console.log('缓存未命中，加载库存数据...');
          cachedStockData = await get_all_stock_data(storage_code);
          cachedStockIndices = build_stock_indices(cachedStockData);
        } else {
          console.log('缓存命中，使用已缓存的库存数据');
        }

        // 只有当启用前档空库位且缓存不存在时才加载
        if (showEmptyLocations && (!cachedEmptyLocations || cachedEmptyLocations.length === 0)) {
          console.log('前档空库位未缓存，加载中...');
          cachedEmptyLocations = await find_empty_locations(storage_code);
        } else {
          console.log('使用已缓存的空库位数据');
        }

        const stock_indices = cachedStockIndices;
        const empty_locations = cachedEmptyLocations;
        // ===== 缓存逻辑结束 =====

        // 如果启用前档空库位显示，生成空库位预览页面
        let emptyLocationsHTML = '';
        if (showEmptyLocations && empty_locations && empty_locations.length > 0) {
          emptyLocationsHTML = generateEmptyLocationsHTML(empty_locations, storage_code);
        }

        // 使用 Promise.all 处理异步操作
        const formattedDataPromises = formattedData.map(async (group, groupIndex) => {
          const header = group.headerInfo;
          let items = group.items;
          const transferType = header.transferType;

          // 如果启用了"急用"筛选，只显示有备注的条目
          if (isUrgent) {
            items = items.filter(item => item.remark && item.remark.trim() !== '');
          }

          // 如果筛选后items为空，返回空字符串，跳过这个调拨单
          if (items.length === 0) {
            return '';
          }

          // 处理每个 item 的异步操作
          const itemsHTML = await Promise.all(
            items.map(async (item, index) => {
              const quantity = parseInt(item.inboundQuantity) || 0;
              const price = parseFloat(item.salesPrice) || 0;
              const rate = parseFloat(item.priceIncreaseRate) || 1;
              const amount = (quantity * price * rate).toFixed(2);

              // 获取库位库存数量（入库库位需要始终获取，因为即使仅备注也需要显示）
              const inboundLocationNo = item.inboundLocationNo;
              const locationStock = stock_indices.location[inboundLocationNo] || [];
              const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
              // 入库库位显示逻辑
              const inboundLocationDisplay = inboundLocationNo ? `${inboundLocationNo}\n【${stockQty}】` : '';

              // 当不是"仅备注"模式时，才获取指示库位、调拨前库存数和3月内最近出库信息
              let shelfLocationDisplay = '';
              let prestockvalue = '';
              let recentSaleInfo = '';

              if (!isOnlyRemark) {
                // 获取指示库位库存数量
                const shelfLocationNo = item.shelfLocationNo;
                const shelfLocationNostock = stock_indices.location[shelfLocationNo] || [];
                const shelfQty = shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
                shelfLocationDisplay = shelfLocationNo ? `${shelfLocationNo}\n【${shelfQty}】` : '';

                // 获取调拨前库存数
                const partCode = item.partCode;
                if (partCode) {
                  const stock_data = stock_indices['part_code'][partCode] || [];
                  if (stock_data && stock_data.length > 0) {
                    const locations = [];
                    const quantities = [];
                    for (const loc of stock_data) {
                      locations.push(loc['location_no'] || '');
                      quantities.push(String(loc['location_accessories_number'] || 0));
                    }
                    if (locations.length > 0 && quantities.length > 0) {
                      prestockvalue = `${locations.join('\n')}\n【${quantities.join(',')}】`;
                    }
                  }
                }

                // 获取3月内最近出库信息（使用缓存）
                if (partCode) {
                  // 检查缓存
                  if (!cachedSaleInfo[partCode]) {
                    console.log(`销售信息未缓存，查询产品编码: ${partCode}`);
                    const orderData = await query_order_by_code(partCode, warehouseId);
                    cachedSaleInfo[partCode] = get_recent_sale_location(orderData);
                  } else {
                    console.log(`销售信息缓存命中，产品编码: ${partCode}`);
                  }
                  recentSaleInfo = cachedSaleInfo[partCode];
                }
              }

              // 判断是否添加入库数量为0的删除线样式
              const rowClass = quantity === 0 ? 'class="strike-through"' : '';

              return `
                <tr ${rowClass}>
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
                  <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.partCode || ''}</td>
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${inboundLocationDisplay}</td>
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
                  ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${shelfLocationDisplay}</td>` : ''}
                  ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${prestockvalue || ''}</td>` : ''}
                  ${!isOnlyRemark ? `<td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${recentSaleInfo}</td>` : ''}
                  <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.remark || ''}</td>
                  ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
                  ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
                  ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
                </tr>
              `;
            })
          );

          // 生成每个调拨单的 HTML
          return `
            <div id="transferPrintDiv${groupIndex}" index="${groupIndex}">
              <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
                <div style="width: 100%; margin: 0px auto; text-align: center;">
                  <span style="font-size: 25px; font-weight: bold;">调入清单</span>
                </div>
                <div style="width: 100%; margin: 0px; text-align: left;">
                  <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 98%;">
                    <tbody>
                      <tr>
                        <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
                        <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
                        <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${getShortTransferNo(header.transferNo) || ''}</td>
                      </tr>
                      <tr>
                        <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
                        <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
                        <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
                      </tr>
                    </tbody>
                  </table>
                  <table align="center" valign="middle" style="width: 100%; margin: 0px auto; font-size: 14px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
                    <tbody>
                      <tr>
                        <td style="width: ${!isOnlyRemark ? '5' : '8'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
                        <td style="width: ${!isOnlyRemark ? '28' : '38'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
                        <td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
                        <td style="width: ${!isOnlyRemark ? '15' : '20'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">产品编码</td>
                        <td style="width: ${!isOnlyRemark ? '7' : '10'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n库位</td>
                        <td style="width: ${!isOnlyRemark ? '5' : '8'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n数量</td>
                        ${!isOnlyRemark ? `<td style="width: 7%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">指示\n库位</td>` : ''}
                        ${!isOnlyRemark ? `<td style="width: 7%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">调拨前\n库存数</td>` : ''}
                        ${!isOnlyRemark ? `<td style="width: 14%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">3月内最近\n出库信息</td>` : ''}
                        <td style="width: ${!isOnlyRemark ? '7' : '11'}%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">备注</td>
                        ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
                        ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
                        ${isPriceTransfer ? '<td style="width: 5%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
                      </tr>
                      ${itemsHTML.join('')}
                      <tr style="text-align: center;">
                        <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
                        <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
                        <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
                        <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
                        <td colspan="${!isOnlyRemark ? '4' : '1'}" style="border: 1px solid rgb(0, 0, 0);"></td>
                        ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          `;
        });

        // 等待所有调拨单的 HTML 生成完成
        const formattedDataHTML = await Promise.all(formattedDataPromises);
        // 过滤掉空字符串（即items为空的调拨单）
        printHTML = formattedDataHTML.filter(html => html !== '').join('');

        // 如果启用了前档空库位显示，在最后添加空库位预览页面
        if (showEmptyLocations && emptyLocationsHTML) {
          printHTML += emptyLocationsHTML;
        }

        // 在生成打印 HTML 的顶层添加样式
        const style = `
          <style>
            .strike-through {
              text-decoration: line-through;
              color: #999; /* 可选：让删除线行的颜色变浅 */
            }
          </style>
        `;
        // 在最终打印 HTML 中包含样式
        printHTML = style + printHTML;
        return printHTML;
      }

      // 异步调用
      (async () => {
        try {
          const html = await generatePrintHTML(false, false, true, false); // 初始"仅备注"复选框选中
          printPreviewDiv.innerHTML = html;
        } catch (error) {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        }
      })();

      // 监听价格开关状态变化
      priceToggle.addEventListener('change', async (event) => {
        try {
          const isPriceChecked = event.target.checked;
          const isUrgentChecked = urgentToggle.checked;
          const isOnlyRemarkChecked = onlyRemarkToggle.checked;
          const isEmptyLocationChecked = emptyLocationToggle.checked;
          const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked, isEmptyLocationChecked);
          printPreviewDiv.innerHTML = html;
        } catch (error) {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        }
      });

      // 监听急用复选框状态变化
      urgentToggle.addEventListener('change', async (event) => {
        try {
          const isPriceChecked = priceToggle.checked;
          const isUrgentChecked = event.target.checked;
          const isOnlyRemarkChecked = onlyRemarkToggle.checked;
          const isEmptyLocationChecked = emptyLocationToggle.checked;
          const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked, isEmptyLocationChecked);
          printPreviewDiv.innerHTML = html;
        } catch (error) {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        }
      });

      // 监听"仅备注"复选框状态变化
      onlyRemarkToggle.addEventListener('change', async (event) => {
        try {
          const isPriceChecked = priceToggle.checked;
          const isUrgentChecked = urgentToggle.checked;
          const isOnlyRemarkChecked = event.target.checked;
          const isEmptyLocationChecked = emptyLocationToggle.checked;
          const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked, isEmptyLocationChecked);
          printPreviewDiv.innerHTML = html;
        } catch (error) {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        }
      });

      // 监听前档空库位开关状态变化
      emptyLocationToggle.addEventListener('change', async (event) => {
        try {
          const isPriceChecked = priceToggle.checked;
          const isUrgentChecked = urgentToggle.checked;
          const isOnlyRemarkChecked = onlyRemarkToggle.checked;
          const isEmptyLocationChecked = event.target.checked;
          const html = await generatePrintHTML(isPriceChecked, isUrgentChecked, isOnlyRemarkChecked, isEmptyLocationChecked);
          printPreviewDiv.innerHTML = html;
        } catch (error) {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        }
      });

      // 组装对话框
      dialogBody.appendChild(printerSelect);
      dialogBody.appendChild(toggleContainer);
      dialogBody.appendChild(buttonContainer);
      dialogBody.appendChild(printPreviewDiv);

      dialog.appendChild(dialogHeader);
      dialog.appendChild(dialogBody);
      dialogWrapper.appendChild(dialog);

      document.body.appendChild(dialogWrapper);

      // 添加事件监听器
      const closeButton = dialogHeader.querySelector('.el-dialog__headerbtn');
      const returnButton = buttonContainer.querySelector('.el-button--default');
      const printButton = buttonContainer.querySelector('.el-button--primary');

      // 设置导出功能事件
      setupExportEvents(buttonContainer, priceToggle, urgentToggle,onlyRemarkToggle, searchParams, formattedData, cachedStockIndices, cachedSaleInfo, warehouseId);

      // 关闭对话框
      const closeDialog = () => {
        if (dialogWrapper.parentNode) {
          dialogWrapper.parentNode.removeChild(dialogWrapper);
        }
      };

      closeButton.addEventListener('click', closeDialog);
      returnButton.addEventListener('click', closeDialog);

      // 打印功能
      printButton.addEventListener('click', async () => {
        try {
          if (!selectedPrinter) {
            showMessage('请先选择打印机', 'warning');
            return;
          }

          // 直接打印预览内容
          await printDirect(printPreviewDiv.innerHTML, selectedPrinter.name);

          // 显示成功消息
          showMessage(`打印任务已发送到打印机: ${selectedPrinter.name}`, 'success');
          // 打印成功后自动关闭预览对话框
          closeDialog();
        } catch (error) {
          console.error('打印失败:', error);
          showMessage('打印失败: ' + error.message, 'error');
        }
      });

      // 加载打印机列表
      setTimeout(loadPrinterList, 100);

    } catch (error) {
      console.error('打开打印预览失败:', error);
      showMessage('打开打印预览失败: ' + error.message, 'error');
    }



    // // 设置导出功能事件
    // function setupExportEvents(buttonContainer, priceToggle, urgentToggle, searchParams,formattedData) {
    //   const exportButton = buttonContainer.querySelector('#exportButton');
    //   const exportDropdown = buttonContainer.querySelector('.el-dropdown-menu');

    //   // 显示/隐藏导出下拉菜单
    //   exportButton.addEventListener('click', (event) => {
    //     event.stopPropagation();
    //     exportDropdown.style.display = exportDropdown.style.display === 'none' ? 'block' : 'none';
    //   });

    //   // 点击其他地方关闭下拉菜单
    //   document.addEventListener('click', () => {
    //     exportDropdown.style.display = 'none';
    //   });

    //   // 处理导出类型选择
    //   exportDropdown.querySelectorAll('.el-dropdown-menu__item').forEach(item => {
    //     item.addEventListener('click', async (event) => {
    //       event.stopPropagation();
    //       const exportType = event.currentTarget.dataset.type;

    //       try {
    //         const isPriceTransfer = priceToggle.checked;
    //         const isUrgent = urgentToggle.checked;
    //         // const isOnlyRemark = onlyRemarkToggle.checked;
    //         // 获取导出数据
    //         const exportData = await generateExportData(isPriceTransfer, isUrgent, searchParams,formattedData);

    //         if (exportData.length === 0) {
    //           showMessage('没有可导出的数据', 'warning');
    //           return;
    //         }

    //         // 生成文件名
    //         const fileName = generateFileName(isUrgent,searchParams);

    //         // 直接在内容脚本中处理导出
    //         if (exportType === 'excel') {
    //           await exportToExcelInContentScript(exportData, fileName);
    //           showMessage(`导出成功: ${fileName}`, 'success');
    //         } else if (exportType === 'pdf') {
    //           // 使用Canvas渲染方法导出PDF
    //           await exportToPDFWithCanvas(exportData, fileName);
    //           showMessage(`导出成功: ${fileName}`, 'success');
    //         }

    //         exportDropdown.style.display = 'none';
    //       } catch (error) {
    //         console.error('导出失败:', error);
    //         showMessage('导出失败: ' + error.message, 'error');
    //       }
    //     });
    //   });

    // }

    // // 生成导出数据的函数
    // async function generateExportData(isPriceTransfer, isUrgent,searchParams,formattedData) {
    //   // const searchParams = getSearchParams();
    //   const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
    //   const storage_code = warehouseInfo.storage_code;
    //   const warehouseId = warehouseInfo.warehouseId;

    //   const all_stock_data = await get_all_stock_data(storage_code);
    //   const stock_indices = build_stock_indices(all_stock_data);

    //   const exportData = [];

    //   // 使用 for...of 循环处理异步操作，避免混合 Promise.map 和 for...of
    //   for (const group of formattedData) {
    //     const header = group.headerInfo;
    //     let items = group.items;

    //     // 如果启用了"急用"筛选，只显示有备注的条目
    //     if (isUrgent) {
    //       items = items.filter(item => item.remark && item.remark.trim() !== '');
    //     }

    //     // 如果筛选后items为空，跳过这个调拨单
    //     if (items.length === 0) {
    //       continue;
    //     }

    //     // 处理每个 item 的数据
    //     for (const item of items) {
    //       const quantity = parseInt(item.inboundQuantity) || 0;
    //       const price = parseFloat(item.salesPrice) || 0;
    //       const rate = parseFloat(item.priceIncreaseRate) || 1;
    //       const amount = (quantity * price * rate).toFixed(2);

    //       // 获取库位库存数量
    //       const inboundLocationNo = item.inboundLocationNo;
    //       const locationStock = stock_indices.location[inboundLocationNo] || [];
    //       const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
    //       const inboundLocationDisplay = inboundLocationNo ? `${inboundLocationNo}【${stockQty}】` : '';

    //       // 获取指示库位库存数量
    //       const shelfLocationNo = item.shelfLocationNo;
    //       const shelfLocationNostock = stock_indices.location[shelfLocationNo] || [];
    //       const shelfQty = shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
    //       const shelfLocationDisplay = shelfLocationNo ? `${shelfLocationNo}【${shelfQty}】` : '';

    //       // 获取调拨前库存数
    //       const partCode = item.partCode;
    //       let prestockvalue = '';
    //       if (partCode) {
    //         const stock_data = stock_indices['part_code'][partCode] || [];
    //         if (stock_data && stock_data.length > 0) {
    //           const locations = [];
    //           const quantities = [];
    //           for (const loc of stock_data) {
    //             locations.push(loc['location_no'] || '');
    //             quantities.push(String(loc['location_accessories_number'] || 0));
    //           }
    //           if (locations.length > 0 && quantities.length > 0) {
    //             prestockvalue = `${locations.join('\n')}【${quantities.join(',')}】`;
    //           }
    //         }
    //       }

    //       // 获取3月内最近出库信息
    //       const orderData = await query_order_by_code(partCode, warehouseId);
    //       const recentSaleInfo = get_recent_sale_location(orderData);

    //       // 创建导出行数据
    //       const row = {
    //         调拨单号: getShortTransferNo(header.transferNo) || '',
    //         品牌: item.brandName || '',
    //         产品名称: item.partName || '',
    //         分类: getCategoryName(item.categoryTwo),
    //         产品编码: item.partCode || '',
    //         入库库位: inboundLocationDisplay,
    //         入库数量: quantity,
    //         指示库位: shelfLocationDisplay,
    //         调拨前库存数: prestockvalue,
    //         三月内最近出库信息: recentSaleInfo,
    //         备注: item.remark || ''
    //       };
          
    //       // 如果是加价调拨，添加价格信息
    //       if (isPriceTransfer) {
    //         row.成本价 = price;
    //         row.加价率 = rate;
    //         row.金额 = amount;
    //       }
          
    //       exportData.push(row);
    //     }
    //   }
      
    //   return exportData;
    // }

    // 修改函数定义（第 3363 行）
    function setupExportEvents(buttonContainer, priceToggle, urgentToggle, onlyRemarkToggle, searchParams, formattedData, cachedStockIndices, cachedSaleInfo, warehouseId) {
      const exportButton = buttonContainer.querySelector('#exportButton');
      const exportDropdown = buttonContainer.querySelector('.el-dropdown-menu');

      // 显示/隐藏导出下拉菜单
      exportButton.addEventListener('click', (event) => {
        event.stopPropagation();
        exportDropdown.style.display = exportDropdown.style.display === 'none' ? 'block' : 'none';
      });

      // 点击其他地方关闭下拉菜单
      document.addEventListener('click', () => {
        exportDropdown.style.display = 'none';
      });

      // 处理导出类型选择
      exportDropdown.querySelectorAll('.el-dropdown-menu__item').forEach(item => {
        item.addEventListener('click', async (event) => {
          event.stopPropagation();
          const exportType = event.currentTarget.dataset.type;

          try {
            const isPriceTransfer = priceToggle.checked;
            const isUrgent = urgentToggle.checked;
            const isOnlyRemark = onlyRemarkToggle.checked;  // 使用 onlyRemarkToggle
            // 获取导出数据，传递所有缓存参数
            const exportData = await generateExportData(isPriceTransfer, isUrgent, isOnlyRemark, searchParams, formattedData, cachedStockIndices, cachedSaleInfo, warehouseId);

            if (exportData.length === 0) {
              showMessage('没有可导出的数据', 'warning');
              return;
            }

            // 生成文件名
            const fileName = generateFileName(isUrgent, searchParams);

            // 直接在内容脚本中处理导出
            if (exportType === 'excel') {
              await exportToExcelInContentScript(exportData, fileName);
              showMessage(`导出成功: ${fileName}`, 'success');
            } else if (exportType === 'pdf') {
              // 使用Canvas渲染方法导出PDF
              await exportToPDFWithCanvas(exportData, fileName);
              showMessage(`导出成功: ${fileName}`, 'success');
            }

            exportDropdown.style.display = 'none';
          } catch (error) {
            console.error('导出失败:', error);
            showMessage('导出失败: ' + error.message, 'error');
          }
        });
      });
    }

    // 修改 generateExportData 函数定义（第 3420 行）
    async function generateExportData(isPriceTransfer, isUrgent, isOnlyRemark, searchParams, formattedData, cachedStockIndices, cachedSaleInfo, warehouseId) {
      const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
      const storage_code = warehouseInfo.storage_code;
      // warehouseId 从参数获取，而不是从 warehouseInfo
      // const warehouseId = warehouseInfo.warehouseId;

      // 使用缓存的库存数据
      if (!cachedStockIndices) {
        const all_stock_data = await get_all_stock_data(storage_code);
        cachedStockIndices = build_stock_indices(all_stock_data);
      }
      const stock_indices = cachedStockIndices;

      const exportData = [];

      // 使用 for...of 循环处理异步操作，避免混合 Promise.map 和 for...of
      for (const group of formattedData) {
        const header = group.headerInfo;
        let items = group.items;

        // 如果启用了"急用"筛选，只显示有备注的条目
        if (isUrgent) {
          items = items.filter(item => item.remark && item.remark.trim() !== '');
        }

        // 如果筛选后items为空，跳过这个调拨单
        if (items.length === 0) {
          continue;
        }

        // 处理每个 item 的数据
        for (const item of items) {
          const quantity = parseInt(item.inboundQuantity) || 0;
          const price = parseFloat(item.salesPrice) || 0;
          const rate = parseFloat(item.priceIncreaseRate) || 1;
          const amount = (quantity * price * rate).toFixed(2);

          // 如果不是仅备注模式，获取库存和销售信息
          let inboundLocationDisplay = '';
          let shelfLocationDisplay = '';
          let prestockvalue = '';
          let recentSaleInfo = '';
          // 获取库位库存数量
          const inboundLocationNo = item.inboundLocationNo;
          const locationStock = stock_indices.location[inboundLocationNo] || [];
          const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
          inboundLocationDisplay = inboundLocationNo ? `${inboundLocationNo}【${stockQty}】` : '';
          if (!isOnlyRemark) {


            // 获取指示库位库存数量
            const shelfLocationNo = item.shelfLocationNo;
            const shelfLocationNostock = stock_indices.location[shelfLocationNo] || [];
            const shelfQty = shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
            shelfLocationDisplay = shelfLocationNo ? `${shelfLocationNo}【${shelfQty}】` : '';

            // 获取调拨前库存数
            const partCode = item.partCode;
            if (partCode) {
              const stock_data = stock_indices['part_code'][partCode] || [];
              if (stock_data && stock_data.length > 0) {
                const locations = [];
                const quantities = [];
                for (const loc of stock_data) {
                  locations.push(loc['location_no'] || '');
                  quantities.push(String(loc['location_accessories_number'] || 0));
                }
                if (locations.length > 0 && quantities.length > 0) {
                  prestockvalue = `${locations.join('\n')}【${quantities.join(',')}】`;
                }
              }
            }

            // 获取3月内最近出库信息（使用缓存）
            // const partCode = item.partCode;
            if (!cachedSaleInfo[partCode]) {
              const orderData = await query_order_by_code(partCode, warehouseId);
              cachedSaleInfo[partCode] = get_recent_sale_location(orderData);
            }
            recentSaleInfo = cachedSaleInfo[partCode] || '无销售记录';
          }

          // 创建导出行数据
          const row = {
            调拨单号: header.transferNo || '',
            品牌: item.brandName || '',
            产品名称: item.partName || '',
            分类: getCategoryName(item.categoryTwo),
            产品编码: item.partCode || '',
            入库库位: inboundLocationDisplay,
            入库数量: quantity

          };



          // 如果不是仅备注模式，添加库存和销售信息列
          if (!isOnlyRemark) {
            row.指示库位 = shelfLocationDisplay;
            row.调拨前库存数 = prestockvalue;
            row.三月内最近出库信息 = recentSaleInfo;
          }
          // 如果是加价调拨，添加价格信息
          if (isPriceTransfer) {
            row.成本价 = price;
            row.加价率 = rate;
            row.金额 = amount;
          }
          row.备注 = item.remark || '';
          exportData.push(row);
        }
      }

      return exportData;
    }


    // 生成文件名的函数
    function generateFileName(isUrgent,searchParams) {
      // 添加调试信息
      console.log('generateFileName 中的 searchParams:', searchParams);
      console.log('startTime:', searchParams.startTime);
      console.log('endTime:', searchParams.endTime);
      const startTime = searchParams.startTime || '';
      let endTime = searchParams.endTime || '';
      
      // 如果 endTime 为空，设置为今天的日期
      if (!endTime) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        endTime = `${year}-${month}-${day}`;
        console.log('endTime 为空，设置为今天日期:', endTime);
      }

      // 格式化时间字符串
      const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return dateStr.replace(/-/g, '').substring(0, 8); // 去掉横线，只保留年月日
      };

      const dateRange = startTime && endTime
        ? `(${formatDate(startTime)}-${formatDate(endTime)})`
        : '';

      const prefix = isUrgent ? '急用调拨' : '所有调拨';
      return `${prefix}${dateRange}`;
    }

    // // 在内容脚本中导出Excel的函数
    // async function exportToExcelInContentScript(data, fileName) {
    //   // 检查XLSX库是否已加载
    //   if (typeof XLSX === 'undefined') {
    //     throw new Error('Excel导出库未加载，请刷新页面重试');
    //   }
      
    //   try {
    //     // 创建工作簿
    //     const wb = XLSX.utils.book_new();
        
    //     // 创建工作表
    //     const ws = XLSX.utils.json_to_sheet(data);
        
    //     // 设置列宽
    //     const colWidths = Object.keys(data[0] || {}).map(() => ({ wch: 15 }));
    //     ws['!cols'] = colWidths;
        
    //     // 添加工作表到工作簿
    //     XLSX.utils.book_append_sheet(wb, ws, fileName);
        
    //     // 下载文件
    //     XLSX.writeFile(wb, `${fileName}.xlsx`);
    //   } catch (error) {
    //     console.error('Excel导出失败:', error);
    //     throw error;
    //   }
    // }

    // // 在内容脚本中导出Excel的函数 - 使用HTML表格方式
    // async function exportToExcelInContentScript(data, fileName) {
    //   if (!data || data.length === 0) {
    //     throw new Error('没有可导出的数据');
    //   }

    //   try {
    //     // 获取表头
    //     const headers = Object.keys(data[0]);
        
    //     // 构建HTML表格
    //     let html = `
    //       <html xmlns:o="urn:schemas-microsoft-com:office:office" 
    //             xmlns:x="urn:schemas-microsoft-com:office:excel"
    //             xmlns="http://www.w3.org/TR/REC-html40">
    //       <head>
    //         <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    //         <meta http-equiv="Content-Disposition" content="attachment; filename=${fileName}.xls">
    //         <style>
    //           table {
    //             border-collapse: collapse;
    //             mso-displayed-decimal-separator: "\\.";
    //             mso-displayed-thousand-separator: "\\,";
    //           }
    //           td, th {
    //             border: 1px solid #000000;
    //             padding: 2px 4px;
    //             font-family: Arial, sans-serif;
    //             font-size: 12px;
    //             white-space: normal;
    //             mso-number-format: \@;
    //           }
    //           th {
    //             background-color: #428BCA;
    //             color: #FFFFFF;
    //             font-weight: bold;
    //             text-align: center;
    //             vertical-align: middle;
    //           }
    //           /* 列宽设置 */
    //           .col-0 { width: 90px; }  /* 调拨单号 */
    //           .col-1 { width: 50px; }  /* 品牌 */
    //           .col-2 { width: 200px; } /* 产品名称 - 需要换行 */
    //           .col-3 { width: 50px; }  /* 分类 */
    //           .col-4 { width: 120px; } /* 产品编码 */
    //           .col-5 { width: 50px; }  /* 入库库位 */
    //           .col-6 { width: 25px; }  /* 入库数量 */
    //           .col-7 { width: 50px; }  /* 指示库位 */
    //           .col-8 { width: 75px; }  /* 调拨前库存数 - 需要换行 */
    //           .col-9 { width: 100px; } /* 3月内最近出库信息 - 需要换行 */
    //           .col-10 { width: 50px; } /* 备注 - 需要换行 */
    //           /* 所有单元格居中对齐 */
    //           td {
    //             text-align: center;
    //             vertical-align: middle;
    //           }
    //         </style>
    //       </head>
    //       <body>
    //         <table>
    //           <thead>
    //             <tr>
    //     `;

    //     // 添加表头
    //     headers.forEach((header, index) => {
    //       html += `<th class="col-${index}">${header}</th>`;
    //     });
    //     html += `</tr></thead><tbody>`;

    //     // 添加数据行
    //     data.forEach(row => {
    //       html += '<tr>';
    //       headers.forEach((header, index) => {
    //         let cellValue = row[header] || '';
            
    //         // 处理字符串值，将换行符替换为<br>标签
    //         if (typeof cellValue === 'string') {
    //           // 将\n换行符替换为<br>标签，Excel能正确识别
    //           cellValue = cellValue.replace(/\n/g, '<br>');
    //           cellValue = cellValue.replace(/\\n/g, '<br>');
    //         }
            
    //         html += `<td class="col-${index}">${cellValue}</td>`;
    //       });
    //       html += '</tr>';
    //     });

    //     html += `
    //           </tbody>
    //         </table>
    //       </body>
    //       </html>
    //     `;

    //     // 方法1：使用.data URL下载（推荐）
    //     const encodedHtml = encodeURIComponent(html);
    //     const dataUrl = `data:application/vnd.ms-excel;charset=utf-8,${encodedHtml}`;
        
    //     // 创建下载链接
    //     const link = document.createElement('a');
    //     link.href = dataUrl;
    //     link.download = `${fileName}.xls`;
    //     link.style.display = 'none';
        
    //     // 触发下载
    //     document.body.appendChild(link);
    //     link.click();
    //     document.body.removeChild(link);
        
    //     console.log(`Excel导出成功: ${fileName}.xls`);
    //   } catch (error) {
    //     console.error('Excel导出失败:', error);
    //     throw error;
    //   }
    // }

    // 在内容脚本中导出Excel的函数 - 使用ExcelJS库
    async function exportToExcelInContentScript(data, fileName) {
      // 检查ExcelJS库是否已加载
      if (typeof ExcelJS === 'undefined') {
        throw new Error('ExcelJS 库未加载，请刷新页面重试');
      }

      if (!data || data.length === 0) {
        throw new Error('没有可导出的数据');
      }

      try {
        // 获取表头
        const headers = Object.keys(data[0]);

        // 创建工作簿
        const workbook = new ExcelJS.Workbook();
        workbook.creator = 'ERP打印扩展';
        workbook.created = new Date();
        workbook.modified = new Date();

        // 创建工作表
        const worksheet = workbook.addWorksheet(fileName);

        // 预处理数据：确保所有字段都是字符串，避免科学计数法
        const processedData = data.map(row => {
          const processedRow = {};
          headers.forEach(header => {
            let value = row[header];

            // 将数值转换为字符串，避免科学计数法
            if (typeof value === 'number') {
              processedRow[header] = value.toString();
            } else if (value === null || value === undefined) {
              processedRow[header] = '';
            } else {
              processedRow[header] = String(value);
            }
          });
          return processedRow;
        });

        // 添加表头行
        const headerRow = worksheet.addRow(headers);
        
        // 设置表头样式
        headerRow.eachCell((cell, colNumber) => {
          cell.font = {
            bold: true,
            size: 11,
            color: { argb: 'FFFFFF' }
          };
          cell.fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: '4F81BD' } // 蓝色背景
          };
          cell.alignment = {
            vertical: 'middle',
            horizontal: 'center',
            wrapText: true
          };
          cell.border = {
            top: { style: 'thin' },
            left: { style: 'thin' },
            bottom: { style: 'thin' },
            right: { style: 'thin' }
          };
        });

        // 设置表头行高
        headerRow.height = 25;

        // 添加数据行
        processedData.forEach(row => {
          const rowData = headers.map(header => row[header] || '');
          const dataRow = worksheet.addRow(rowData);
          
          // 设置数据行基本样式
          dataRow.eachCell((cell, colNumber) => {
            cell.alignment = {
              vertical: 'middle',
              horizontal: 'center'
            };
            cell.border = {
              top: { style: 'thin' },
              left: { style: 'thin' },
              bottom: { style: 'thin' },
              right: { style: 'thin' }
            };
          });
        });

        // // 设置列宽 - ExcelJS的列宽单位与XLSX不同，1个字符大约等于1.2个宽度单位
        // const colWidths = [
        //   { width: 16 },   // 调拨单号 (13 * 1.2 ≈ 16)
        //   { width: 6 },    // 品牌 (5 * 1.2 ≈ 6)
        //   { width: 36 },   // 产品名称 (30 * 1.2 ≈ 36)
        //   { width: 6 },    // 分类 (5 * 1.2 ≈ 6)
        //   { width: 16 },   // 产品编码 (14 * 1.2 ≈ 16)
        //   { width: 8 },   // 入库库位 (6 * 1.2 ≈ 10)
        //   { width: 6 },    // 入库数量 (5 * 1.2 ≈ 6)
        //   { width: 8 },  // 指示库位 (6 * 1.2 ≈ 8.4)
        //   { width: 8 },   // 调拨前库存数 (8 * 1.2 ≈ 10)
        //   { width: 12 },   // 3月内最近出库信息 (10 * 1.2 ≈ 17)
        //   { width: 8 }    // 备注 (7 * 1.2 ≈ 8)
        // ];

        // // 应用列宽
        // colWidths.forEach((widthObj, index) => {
        //   const column = worksheet.getColumn(index + 1);
        //   column.width = widthObj.width;
        // });
        // // 定义需要自动换行的列索引（1-based）
        // const wrapTextColumns = [3, 6, 8, 9, 10, 11]; // 产品名称、调拨前库存数、3月内最近出库信息、备注

        // // 设置需要换行的列的样式
        // wrapTextColumns.forEach(colIndex => {
        //   const column = worksheet.getColumn(colIndex);
          
        //   // 设置列对齐方式和自动换行
        //   column.alignment = { 
        //     vertical: 'middle', 
        //     horizontal: 'center',
        //     wrapText: true 
        //   };
          
        //   // // 设置列宽稍微大一些以便换行显示
        //   // column.width = Math.max(column.width || 0, 20);
          
        //   // 遍历该列的所有单元格，确保包含换行符的单元格正确设置
        //   column.eachCell((cell, rowNumber) => {
        //     if (cell.value && typeof cell.value === 'string' && cell.value.includes('\n')) {
        //       cell.alignment = { 
        //         vertical: 'middle', 
        //         horizontal: 'center',
        //         wrapText: true 
        //       };
        //     }
        //   });
        // });
        // 修改 Excel 导出函数中的列宽计算（第 3962-3981 行）

        // 根据实际列数动态计算列宽
        const colWidths = headers.map((header, index) => {
          // 根据列名设置默认列宽
          const widthMap = {
            '调拨单号': 16,
            '品牌': 6,
            '产品名称': 36,
            '分类': 6,
            '产品编码': 16,
            '入库库位': 8,
            '入库数量': 6,
            '指示库位': 8,
            '调拨前库存数': 8,
            '三月内最近出库信息': 12,
            '备注': 8,
            '成本价': 12,
            '加价率': 8,
            '金额': 12
          };

          return { width: widthMap[header] || 10 };
        });

        // 应用列宽
        colWidths.forEach((widthObj, index) => {
          const column = worksheet.getColumn(index + 1);
          column.width = widthObj.width;
        });




        // 根据实际列名设置自动换行（第 3984-4010 行）

        // 定义需要自动换行的列名
        const wrapTextColumnNames = ['产品名称', '入库库位', '指示库位', '调拨前库存数', '三月内最近出库信息', '备注'];

        // 找出需要换行的列的实际索引
        const wrapTextColumns = wrapTextColumnNames
          .filter(colName => headers.includes(colName))
          .map(colName => headers.indexOf(colName) + 1); // 转换为 1-based 索引

        // 设置需要换行的列的样式
        wrapTextColumns.forEach(colIndex => {
          const column = worksheet.getColumn(colIndex);
          column.alignment = {
            vertical: 'middle',
            horizontal: 'center',
            wrapText: true
          };

          // 遍历该列的所有单元格，确保包含换行符的单元格正确设置
          column.eachCell((cell, rowNumber) => {
            if (cell.value && typeof cell.value === 'string' && cell.value.includes('\n')) {
              cell.alignment = {
                vertical: 'middle',
                horizontal: 'center',
                wrapText: true
              };
            }
          });
        });



        // 如果有价格信息列，添加相应的列宽
        if (processedData.length > 0 && processedData[0].成本价 !== undefined) {
          // 成本价列
          const costPriceCol = worksheet.columnCount + 1;
          worksheet.getColumn(costPriceCol).width = 12; // 成本价
          worksheet.getColumn(costPriceCol + 1).width = 8.4; // 加价率
          worksheet.getColumn(costPriceCol + 2).width = 12; // 金额
          
          // 设置这些列的对齐方式
          for (let i = costPriceCol; i <= costPriceCol + 2; i++) {
            const column = worksheet.getColumn(i);
            column.alignment = { vertical: 'middle', horizontal: 'right' };
          }
        }

        // 设置所有行的默认行高，对于包含换行符的行，自动调整行高
        worksheet.eachRow((row, rowNumber) => {
          if (rowNumber > 1) { // 跳过表头行
            let maxLines = 1;
            
            // 检查该行中需要换行的列，计算最大行数
            wrapTextColumns.forEach(colIndex => {
              const cell = row.getCell(colIndex);
              if (cell.value && typeof cell.value === 'string') {
                const lines = cell.value.split('\n').length;
                if (lines > maxLines) {
                  maxLines = lines;
                }
              }
            });
            
            // 根据最大行数设置行高（每行大约20像素）
            if (maxLines > 1) {
              row.height = 30 * maxLines;
            } else {
              row.height = 30;
            }
          }
        });

        // 生成Excel文件
        const buffer = await workbook.xlsx.writeBuffer();
        
        // 创建Blob
        const blob = new Blob([buffer], { 
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
        });

        // 创建下载链接
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.href = url;
        link.download = `${fileName}.xlsx`;
        link.style.display = 'none';

        // 触发下载
        document.body.appendChild(link);
        link.click();

        // 清理
        setTimeout(() => {
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }, 100);

        console.log(`Excel导出成功: ${fileName}.xlsx`);
        showMessage(`导出成功: ${fileName}.xlsx`, 'success');

      } catch (error) {
        console.error('Excel导出失败:', error);
        throw error;
      }
    }








  // // 在内容脚本中使用Canvas渲染导出PDF
  // async function exportToPDFWithCanvas(data, fileName) {
  //   try {
  //     // 检查必要的库是否已加载
  //     if (typeof XLSX === 'undefined') {
  //       throw new Error('Excel导出库未加载，请刷新页面重试');
  //     }

  //     if (typeof html2canvas === 'undefined') {
  //       throw new Error('html2canvas库未加载，请刷新页面重试');
  //     }

  //     // 创建HTML表格
  //     const htmlContent = createHTMLTableForPDF(data, fileName);

  //     // 创建临时容器
  //     const tempContainer = document.createElement('div');
  //     tempContainer.style.cssText = `
  //     position: fixed;
  //     top: -10000px;
  //     left: -10000px;
  //     width: 210mm;
  //     padding: 20px;
  //     background: white;
  //     font-family: Arial, "Microsoft YaHei", sans-serif;
  //     font-size: 12px;
  //     z-index: -1000;
  //   `;
  //     tempContainer.innerHTML = htmlContent;
  //     document.body.appendChild(tempContainer);

  //     try {
  //       // 使用html2canvas渲染HTML内容
  //       const canvas = await html2canvas(tempContainer, {
  //         scale: 1.2, // 提高图像质量
  //         useCORS: true,
  //         allowTaint: true,
  //         logging: false,  // 关闭日志输出减少内存占用
  //         backgroundColor: '#ffffff',
  //         width: tempContainer.scrollWidth,
  //         height: tempContainer.scrollHeight
  //       });

  //       // 创建PDF
  //       if (typeof window.jspdf === 'undefined') {
  //         throw new Error('PDF导出库未加载，请刷新页面重试');
  //       }


  //       const { jsPDF } = window.jspdf;
  //       const imgData = canvas.toDataURL('image/jpeg', 0.7);

  //       // 计算PDF尺寸
  //       const imgWidth = 210; // letter宽度(mm)
  //       const pageHeight = 290; // letter高度(mm)
  //       const imgHeight = (canvas.height * imgWidth) / canvas.width;
  //       let heightLeft = imgHeight;
  //       let position = 0;


  //       // 创建PDF，纵向letter
  //       const pdf = new jsPDF('p', 'mm', 'letter');

  //       // 添加图像到PDF
  //       pdf.addImage(imgData, 'jpeg', 0, position, imgWidth, imgHeight);
  //       heightLeft -= pageHeight;

  //       // 如果内容超过一页，添加更多页面
  //       while (heightLeft >= 0) {
  //         position = heightLeft - imgHeight;
  //         pdf.addPage();
  //         pdf.addImage(imgData, 'jpeg', 0, position, imgWidth, imgHeight);
  //         heightLeft -= pageHeight;
  //       }

  //       // 保存PDF
  //       pdf.save(`${fileName}.pdf`);

  //     } finally {
  //       // 清理临时容器
  //       document.body.removeChild(tempContainer);
  //     }

  //   } catch (error) {
  //     console.error('Canvas渲染PDF失败:', error);
  //     // 如果Canvas渲染失败，回退到HTML导出
  //     exportToHTMLInContentScript(data, fileName);
  //   }
  // }

  // 在内容脚本中使用Canvas渲染导出PDF
  async function exportToPDFWithCanvas(data, fileName) {
    try {
      // 检查必要的库是否已加载
      if (typeof XLSX === 'undefined') {
        throw new Error('Excel导出库未加载，请刷新页面重试');
      }

      if (typeof html2canvas === 'undefined') {
        throw new Error('html2canvas库未加载，请刷新页面重试');
      }

      // 创建PDF
      if (typeof window.jspdf === 'undefined') {
        throw new Error('PDF导出库未加载，请刷新页面重试');
      }

      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF('p', 'mm', 'letter'); // 纵向letter

      // 获取表头
      const headers = Object.keys(data[0] || {});
      const colCount = headers.length;

      // 计算列宽
      const pageWidth = 210; // A4页面宽度减去边距
      const minColWidth = 25; // 最小列宽
      const colWidth = Math.max(pageWidth / colCount, minColWidth);

      // 创建临时容器
      const tempContainer = document.createElement('div');
      tempContainer.style.cssText = `
        position: fixed;
        top: -10000px;
        left: -10000px;
        width: 210mm;
        background: white;
        font-family: Arial, "Microsoft YaHei", sans-serif;
        font-size: 12px;
        z-index: -1000;
      `;
      document.body.appendChild(tempContainer);

      // 添加标题
      const titleDiv = document.createElement('div');
      titleDiv.style.cssText = `
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 5px;
      `;
      titleDiv.textContent = fileName;
      tempContainer.appendChild(titleDiv);

      // 智能分页处理
      let currentPageRows = [];
      let allPagesData = [];
      const pageHeight = 250; // 每页可用高度(mm)
      const rowHeightEstimate = 15; // 估计每行高度
      const headerHeight = 30; // 标题和表头高度
      const maxRowsPerPage = Math.floor((pageHeight - headerHeight) / rowHeightEstimate);

      // 分组处理数据
      let currentTransferNo = '';
      let groupStartIndex = 0;

      for (let i = 0; i < data.length; i++) {
        const row = data[i];

        // 检查是否是新的调拨单
        if (row.调拨单号 !== currentTransferNo) {
          // 如果当前页已有数据且遇到新的调拨单，检查是否需要分页
          if (currentPageRows.length > 0) {
            const newGroupRows = [];
            let j = i;

            // 计算新调拨单有多少行
            while (j < data.length && data[j].调拨单号 === row.调拨单号) {
              newGroupRows.push(data[j]);
              j++;
            }

            // 如果当前页加上新调拨单会超过最大行数，则分页
            if (currentPageRows.length + newGroupRows.length > maxRowsPerPage) {
              allPagesData.push([...currentPageRows]);
                currentPageRows = [];
              }
            }

            currentTransferNo = row.调拨单号;
          }

          currentPageRows.push(row);

          // 如果当前页达到最大行数，则分页
          if (currentPageRows.length >= maxRowsPerPage) {
            allPagesData.push([...currentPageRows]);
            currentPageRows = [];
            currentTransferNo = ''; // 重置，确保下一个调拨单可以从新页开始
          }
        }

        // 添加最后一页的数据
        if (currentPageRows.length > 0) {
          allPagesData.push(currentPageRows);
        }

        // 为每页生成表格并渲染
        for (let pageIndex = 0; pageIndex < allPagesData.length; pageIndex++) {
          const pageData = allPagesData[pageIndex];

          // 清空临时容器
          while (tempContainer.firstChild) {
            tempContainer.removeChild(tempContainer.firstChild);
          }

          // 重新添加标题（每页都显示）
          const pageTitle = document.createElement('div');
          pageTitle.style.cssText = `
          text-align: center;
          font-size: 18px;
          font-weight: bold;
          margin-bottom: 15px;
        `;
          pageTitle.textContent = `${fileName} - 第${pageIndex + 1}页`;
          tempContainer.appendChild(pageTitle);

          // 创建表格
          const table = document.createElement('table');
          table.style.cssText = `
          border-collapse: collapse;
          width: 100%;
          font-size: 12px;
          margin-bottom: 10px;
        `;

          // 添加表头
          const thead = document.createElement('thead');
          const headerRow = document.createElement('tr');
          headerRow.style.cssText = 'background-color: #428bca; color: white; font-weight: bold;';

          headers.forEach(header => {
            const th = document.createElement('th');
            th.style.cssText = 'border: 1px solid #000; padding: 8px; text-align: center;';
            th.textContent = header;
            headerRow.appendChild(th);
          });

          thead.appendChild(headerRow);
          table.appendChild(thead);

          // 添加表体
          const tbody = document.createElement('tbody');
          pageData.forEach((row, index) => {
            const tr = document.createElement('tr');
            // 斑马纹
            tr.style.cssText = index % 2 === 0 ? 'background-color: #ffffff;' : 'background-color: #f9f9f9;';

            headers.forEach(header => {
              const td = document.createElement('td');
              td.style.cssText = 'border: 1px solid #000; padding: 5px; text-align: center; vertical-align: top;';

              let value = String(row[header] || '');
              // 处理换行符
              if (value.includes('\n')) {
                value = value.replace(/\n/g, '<br>');
              }

              td.innerHTML = value;
              tr.appendChild(td);
            });

            tbody.appendChild(tr);
          });

          table.appendChild(tbody);
          tempContainer.appendChild(table);

          // 添加页脚
          const footer = document.createElement('div');
          footer.style.cssText = `
          margin-top: 20px;
          text-align: right;
          font-size: 10px;
          color: #666;
        `;
          footer.textContent = `生成时间: ${new Date().toLocaleString()}`;
          tempContainer.appendChild(footer);

          // 渲染当前页
          try {
            const canvas = await html2canvas(tempContainer, {
              scale: 1.5, // 提高图像质量
              useCORS: true,
              allowTaint: true,
              logging: false,  // 关闭日志输出减少内存占用
              backgroundColor: '#ffffff',
              width: tempContainer.scrollWidth,
              height: tempContainer.scrollHeight
            });

            // 转换为图像
            const imgData = canvas.toDataURL('image/jpeg', 0.9);
            const imgWidth = 190; // 页面宽度(mm)
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            // 如果不是第一页，添加新页
            if (pageIndex > 0) {
              pdf.addPage();
            }

            // 添加图像到PDF，确保完整显示
            pdf.addImage(imgData, 'jpeg', 10, 10, imgWidth, Math.min(imgHeight, pageHeight));

          } catch (canvasError) {
            console.error(`渲染第${pageIndex + 1}页失败:`, canvasError);
            // 如果当前页渲染失败，跳过该页但继续处理其他页
            continue;
          }
        }

        // 保存PDF
        pdf.save(`${fileName}.pdf`);

      } catch (error) {
        console.error('Canvas渲染PDF失败:', error);
        // 如果Canvas渲染失败，回退到HTML导出
        exportToHTMLInContentScript(data, fileName);
      } finally {
        // 清理临时容器
        try {
          if (typeof tempContainer !== 'undefined' && document.body.contains(tempContainer)) {
            document.body.removeChild(tempContainer);
          }
        } catch (cleanupError) {
          console.error('清理临时容器失败:', cleanupError);
        } 
      }
    } 


    // // 创建用于PDF的HTML表格
    // function createHTMLTableForPDF(data, fileName) {
    //   // 获取表头
    //   const headers = Object.keys(data[0] || {});

    //   // 创建表格HTML
    //   let tableHTML = `
    //   <div style="font-family: Arial, 'Microsoft YaHei', sans-serif; margin-bottom: 20px;">
    //     <h2 style="text-align: center; margin-bottom: 20px; font-size: 18px;">${fileName}</h2>
    //     <table style="border-collapse: collapse; width: 100%; font-size: 12px;">
    // `;

    //   // 添加表头
    //   tableHTML += '<thead><tr style="background-color: #428bca; color: white; font-weight: bold;">';
    //   headers.forEach(header => {
    //     tableHTML += `<th style="border: 1px solid #000; padding: 8px; text-align: center;">${header}</th>`;
    //   });
    //   tableHTML += '</tr></thead>';

    //   // 添加表体
    //   tableHTML += '<tbody>';
    //   data.forEach((row, index) => {
    //     // 斑马纹
    //     const rowStyle = index % 2 === 0 ? 'background-color: #ffffff;' : 'background-color: #f9f9f9;';
    //     tableHTML += `<tr style="${rowStyle}">`;
    //     headers.forEach(header => {
    //       let value = String(row[header] || '');
    //       // 处理换行符
    //       if (value.includes('\n')) {
    //         value = value.replace(/\n/g, '<br>');
    //       }
    //       tableHTML += `<td style="border: 1px solid #000; padding: 5px; text-align: center; vertical-align: top;">${value}</td>`;
    //     });
    //     tableHTML += '</tr>';
    //   });
    //   tableHTML += '</tbody></table>';

    //   // 添加页脚
    //   tableHTML += `
    //   <div style="margin-top: 20px; text-align: right; font-size: 10px; color: #666;">
    //     生成时间: ${new Date().toLocaleString()}
    //   </div>
    //   </div>
    // `;

    //   return tableHTML;
    // }


    // // 在内容脚本中导出PDF的函数
    // async function exportToPDFInContentScript(data, fileName) {
    //   // 检查jsPDF库是否已加载
    //   if (typeof window.jspdf === 'undefined') {
    //     throw new Error('PDF导出库未加载，请刷新页面重试');
    //   }
      
    //   try {
    //     const { jsPDF } = window.jspdf;
    //     const doc = new jsPDF('l', 'mm', 'a4'); // 横向A4
        
    //     // 获取表头
    //     const headers = Object.keys(data[0] || {});
    //     const colCount = headers.length;
    //     const colWidth = 200 / colCount; // 200mm是A4横向的大致宽度
        
    //     // 设置字体
    //     doc.setFont('helvetica');
        
    //     // 添加表头
    //     let yPosition = 20;
    //     headers.forEach((header, index) => {
    //       const xPosition = 10 + (index * colWidth);
    //       doc.text(header, xPosition, yPosition);
    //     });
        
    //     // 添加数据行
    //     yPosition += 10;
    //     data.forEach((row, rowIndex) => {
    //       // 检查是否需要新页
    //       if (yPosition > 280) {
    //         doc.addPage();
    //         yPosition = 20;
            
    //         // 重新添加表头
    //         headers.forEach((header, index) => {
    //           const xPosition = 10 + (index * colWidth);
    //           doc.text(header, xPosition, yPosition);
    //         });
    //         yPosition += 10;
    //       }
          
    //       // 添加数据
    //       headers.forEach((header, index) => {
    //         const xPosition = 10 + (index * colWidth);
    //         const cellText = String(row[header] || '').substring(0, 25); // 限制文本长度
    //         doc.text(cellText, xPosition, yPosition);
    //       });
    //       yPosition += 8;
    //     });
        
    //     // 保存文件
    //     doc.save(`${fileName}.pdf`);
    //   } catch (error) {
    //     console.error('PDF导出失败:', error);
    //     // 如果jsPDF失败，回退到HTML格式
    //     exportToHTMLInContentScript(data, fileName);
    //   }
    // }

    // 在内容脚本中导出HTML的函数（作为PDF导出的备选方案）
    function exportToHTMLInContentScript(data, fileName) {
      // 获取表头
      const headers = Object.keys(data[0] || {});
      
        // 创建表格HTML
        let tableHTML = '<table style="border-collapse: collapse; width: 100%;">';

        // 添加表头
        tableHTML += '<thead><tr>';
        headers.forEach(header => {
          tableHTML += `<th style="border: 1px solid #000; padding: 5px; text-align: center;">${header}</th>`;
        });
        tableHTML += '</tr></thead>';

        // 添加表体
        tableHTML += '<tbody>';
        data.forEach(row => {
          tableHTML += '<tr>';
          headers.forEach(header => {
            const value = row[header] || '';
            tableHTML += `<td style="border: 1px solid #000; padding: 5px; text-align: center;">${value}</td>`;
          });
          tableHTML += '</tr>';
        });
        tableHTML += '</tbody></table>';

        // 创建完整的HTML内容
        const htmlContent = `
        <html>
          <head>
            <title>${fileName}</title>
            <style>
              @page { size: A4 landscape; }
              body { margin: 10mm; font-family: Arial, sans-serif; }
              h1 { text-align: center; margin-bottom: 20px; }
              table { width: 100%; border-collapse: collapse; }
              /* 添加斑马纹 */
              tr:nth-child(even) { background-color: #f2f2f2; }
              /* 打印样式 */
              @media print {
                body { margin: 5mm; }
                .no-print { display: none; }
              }
            </style>
          </head>
          <body>
            <h1>${fileName}</h1>
            <div class="no-print" style="margin-bottom: 20px; text-align: center;">
              <button onclick="window.print()">打印此页面</button>
              <button onclick="window.close()">关闭</button>
            </div>
            ${tableHTML}
            <script>
              // 自动打印提示
              window.onload = function() {
                console.log('页面加载完成，可以使用浏览器的打印功能保存为PDF');
              };
            </script>
          </body>
        </html>
      `;

        // 创建Blob对象
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const dataUrl = URL.createObjectURL(blob);

        // 创建一个隐藏的下载链接
        const downloadLink = document.createElement('a');
        downloadLink.href = dataUrl;
        downloadLink.download = `${fileName}.html`;
        downloadLink.style.display = 'none';
        document.body.appendChild(downloadLink);
        downloadLink.click();

        // 清理
        setTimeout(() => {
          document.body.removeChild(downloadLink);
          URL.revokeObjectURL(dataUrl);
        }, 1000);
      }
}




// 直接打印函数 - 使用iframe执行
async function printDirect(htmlContent, printerName) {
  return new Promise((resolve, reject) => {
    // 创建唯一的事件ID
    const eventId = 'print_execute_' + Date.now();

    // 监听来自页面的消息
    const messageHandler = (event) => {
      if (event.data.type === 'PRINT_RESULT' && event.data.id === eventId) {
        window.removeEventListener('message', messageHandler);
        if (iframe.parentNode) {
          document.body.removeChild(iframe);
        }

        if (event.data.success) {
          resolve(event.data.message);
        } else {
          reject(new Error(event.data.error));
        }
      }
    };

    window.addEventListener('message', messageHandler);

    // 创建一个iframe来执行打印（绕过CSP）
    const iframe = document.createElement('iframe');
    iframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
    iframe.srcdoc = `
      <!DOCTYPE html>
      <html>
      <head>
        <script>
          try {
            // 在iframe中获取CLodop对象
            const LODOP = window.parent.CLODOP || window.parent.getLodop();
            
            if (!LODOP) {
              throw new Error('CLodop 打印控件未初始化，请确保网站已加载CLodopfuncs.js');
            }
            
            // 初始化打印任务
            LODOP.SET_LICENSES("\u7528\u53CB\u6C7D\u8F66\u4FE1\u606F\u79D1\u6280\uFF08\u4E0A\u6D77\uFF09\u80A1\u4EFD\u6709\u9650\u516C\u53F8", "FA9A697F2551BCE81BD852A4EB520525347", "\u7528\u53CB\u6C7D\u8ECA\u4FE1\u606F\u79D1\u6280\uFF08\u4E0A\u6D77\uFF09\u80A1\u4EFD\u6709\u9650\u516C\u53F8", "C66313BD8413BD0174C2CADD29F5380CD92");
            LODOP.PRINT_INIT('调拨单打印');
            
            // 设置打印机
            if ('${printerName}') {
              // 根据打印机名称设置打印机索引
              const printerCount = LODOP.GET_PRINTER_COUNT();
              for (let i = 0; i < printerCount; i++) {
                const name = LODOP.GET_PRINTER_NAME(i);
                if (name === '${printerName}') {
                  LODOP.SET_PRINTER_INDEX(i);
                  break;
                }
              }
            }
            // 如果是PDF虚拟打印机，禁用canvas绘制
            if ('${printerName}'.toLowerCase().includes('pdf')) {
              LODOP.SET_PRINT_MODE('PRINT_DEFAULTPDF', true);
              LODOP.SET_PRINT_MODE('CANVAS_DISABLED', true);
            }            
            // 设置页面大小为信纸纵向
            LODOP.SET_PRINT_PAGESIZE(1, 0, 0, 'Letter');
            
            // 添加打印内容
            LODOP.ADD_PRINT_HTM(0, 0, '100%', '100%', \`${htmlContent.replace(/`/g, '\\`')}\`);
            //LODOP.SET_PRINT_STYLEA(0, "MarginBottom", "15mm"); // 调整下边距
            // 直接发送到打印机，不显示预览
            LODOP.PRINT();
            
            // 发送成功消息
            window.parent.postMessage({
              type: 'PRINT_RESULT',
              id: '${eventId}',
              success: true,
              message: '打印任务已发送到打印机: ${printerName}'
            }, '*');
            
          } catch (error) {
            // 发送错误消息
            window.parent.postMessage({
              type: 'PRINT_RESULT',
              id: '${eventId}',
              success: false,
              error: error.message
            }, '*');
          }
        </script>
      </head>
      <body></body>
      </html>
    `;

    document.body.appendChild(iframe);

    // 超时处理
    setTimeout(() => {
      window.removeEventListener('message', messageHandler);
      if (iframe.parentNode) {
        document.body.removeChild(iframe);
      }
      reject(new Error('打印操作超时'));
    }, 10000);
  });
}



function cleanupPrintExtension() {
  if (observer) {
    observer.disconnect();
  }
  if (checkInterval) {
    clearInterval(checkInterval);
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange);
  printExtensionInitialized = false;
}




// 单独定义 visibilitychange 处理函数
async function handleVisibilityChange() {
  if (!document.hidden) {
    try {
      const isTargetPage = await isAdjustLogPage();
      const btn = document.getElementById('custom-print-preview-btn');

      if (!isTargetPage && btn) {
        btn.remove();
        console.log('用户切换回非调拨页面，已移除打印按钮');
      } else if (isTargetPage && !btn) {
        await injectPrintButton();
      }
    } catch (error) {
      console.error('页面可见性变化检测失败:', error);
    }
  }
}
// 初始化函数
async function initPrintExtension() {
  if (printExtensionInitialized) return;
  printExtensionInitialized = true;
  // 监听页面内容变化（适用于SPA路由切换）
  observer = new MutationObserver(async () => {
    try {
      const isTargetPage = await isAdjustLogPage();
      const btn = document.getElementById('custom-print-preview-btn');

      if (!isTargetPage && btn) {
        btn.remove();
        console.log('检测到页面切换为非调拨页面，已移除打印按钮');
      } else if (isTargetPage && !btn) {
        await injectPrintButton();
      }
    } catch (error) {
      console.error('页面切换检测失败:', error);
    }
  });

  // 监听文档的子树变化（包括动态加载的内容）
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // 设置周期性检查
  checkInterval = setInterval(async () => {
    try {
      const isTargetPage = await isAdjustLogPage();
      const btn = document.getElementById('custom-print-preview-btn');

      if (isTargetPage && !btn) {
        await injectPrintButton();
      } else if (!isTargetPage) {
        clearInterval(checkInterval);
        printExtensionInitialized = false;
      }
    } catch (error) {
      console.error('周期性检查失败:', error);
    }
  }, 5000);

  // 初始化 visibilitychange 事件监听
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // 监听页面卸载事件
  window.addEventListener('unload', cleanupPrintExtension);

  // 4. 首次检测页面状态
  try {
    const isTargetPage = await isAdjustLogPage();
    if (isTargetPage) {
      await injectPrintButton();
    }
  } catch (error) {
    console.error('初始化检测失败:', error);
  }
  // 清理逻辑
  window.cleanupPrintExtension = () => {
    clearInterval(checkInterval);
    printExtensionInitialized = false;
  };

  console.log('调拨单打印扩展初始化完成');
}

// 页面加载后启动
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPrintExtension);
} else {
  initPrintExtension();
}
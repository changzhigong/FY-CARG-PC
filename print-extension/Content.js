// 调拨单打印扩展 - Content Script

// 调拨单打印扩展 - Content Script

// 全局变量
// CLodop 打印控件的本地实现

let printExtensionInitialized = false;
let currentTransferNos = [];



// // 检测是否在调拨单页面
// function isAdjustLogPage() {
//   try {
//     // 方法1: 精确匹配路由
//     const currentUrl = window.location.href;
//     if (currentUrl.includes('/part/warehouse/transferInbound/index') && 
//         currentUrl.includes('menuId=501304')) {
//       return true;
//     }

//     return false;
//   } catch (error) {
//     console.error('页面检测失败:', error);
//     return false;
//   }
// }

function isAdjustLogPage() {
  return new Promise((resolve) => {
    setTimeout(() => {
      try {
        const currentUrl = window.location.href;
        const pageTitle = document.title;
        const transferTable = document.querySelector('.el-table')?.textContent;

        if (
          (currentUrl.includes('/part/warehouse/transferInbound/index') &&
            currentUrl.includes('menuId=501304')) ||
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
    }, 1000); // 延迟 1 秒检测
  });
}

// 修改 injectPrintButton 为异步函数
async function injectPrintButton() {
  try {
    const isTargetPage = await isAdjustLogPage();
    const currentUrl = window.location.href;   
    if (!isTargetPage) return;
    // 避免重复注入
    if (document.getElementById('custom-print-preview-btn')) {
      return;
    }
    // if (!currentUrl.includes('/part/warehouse/transferInbound/index') && 
    //     currentUrl.includes('menuId=501304')) {
    //   return;
    // }
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
    printBtn.innerHTML = '<i class="el-icon-printer"></i> 专用打印预览';
    printBtn.style.cssText = `
      margin-left: 10px;
      background-color: #67c23a !important;
      border-color: #67c23a !important;
    `;
    printBtn.id = 'custom-print-preview-btn';
    
    // 添加data属性以匹配Vue生成的元素
    const vueElements = document.querySelectorAll('[data-v-fe00d540]');
    if (vueElements.length > 0) {
      printBtn.setAttribute('data-v-fe00d540', '');
    }
    
    // 添加鼠标悬停效果
    printBtn.addEventListener('mouseenter', () => {
      printBtn.style.backgroundColor = '#5daf34 !important';
      printBtn.style.borderColor = '#5daf34 !important';
    });
    
    printBtn.addEventListener('mouseleave', () => {
      printBtn.style.backgroundColor = '#67c23a !important';
      printBtn.style.borderColor = '#67c23a !important';
    });
    
    printBtn.addEventListener('click', handleCustomPrint);
    
    // 查找合适的位置插入（在批量签收按钮后）
    const batchReceiveBtn = btnGroup.querySelector('#batch-receive-btn');
    if (batchReceiveBtn) {
      batchReceiveBtn.insertAdjacentElement('afterend', printBtn);
    } else {
      // 查找最后一个按钮
      const lastButton = btnGroup.lastElementChild;
      if (lastButton) {
        lastButton.insertAdjacentElement('afterend', printBtn);
      } else {
        btnGroup.appendChild(printBtn);
      }
    }
    
    console.log('调拨单打印按钮注入成功');
    printExtensionInitialized = true;
  } catch (error) {
    console.error('注入打印按钮失败:', error);
  }
}


// // 注入打印按钮
// function injectPrintButton() {
//   try {
//     if (!isAdjustLogPage()) return;

//     // 避免重复注入
//     if (document.getElementById('custom-print-preview-btn')) {
//       return;
//     }
//     if (currentUrl.includes('/part/warehouse/transferInbound/index') && 
//         currentUrl.includes('menuId=501304')) {
//       return
//     }
//     console.log('正在注入调拨单打印按钮...');

//     // 多个可能的选择器
//     const selectors = [
//       '.tableHead .btnGroup .el-button-group',
//       '.tableHead .el-button-group',
//       '.btnGroup .el-button-group',
//       '.el-button-group',
//       '.tableHead > div:last-child .el-button-group'
//     ];

//     let btnGroup = null;
//     for (const selector of selectors) {
//       btnGroup = document.querySelector(selector);
//       if (btnGroup && btnGroup.children.length > 0) {
//         break;
//       }
//     }

//     if (!btnGroup) {
//       console.log('未找到按钮组，等待页面加载...');
//       return;
//     }
    
//     // 创建专用打印预览按钮
//     const printBtn = document.createElement('button');
//     printBtn.className = 'el-button el-button--primary el-button--mini';
//     printBtn.innerHTML = '<i class="el-icon-printer"></i> 专用打印预览';
//     printBtn.style.cssText = `
//       margin-left: 10px;
//       background-color: #67c23a !important;
//       border-color: #67c23a !important;
//     `;
//     printBtn.id = 'custom-print-preview-btn';
    
//     // 添加data属性以匹配Vue生成的元素
//     const vueElements = document.querySelectorAll('[data-v-fe00d540]');
//     if (vueElements.length > 0) {
//       printBtn.setAttribute('data-v-fe00d540', '');
//     }
    
//     // 添加鼠标悬停效果
//     printBtn.addEventListener('mouseenter', () => {
//       printBtn.style.backgroundColor = '#5daf34 !important';
//       printBtn.style.borderColor = '#5daf34 !important';
//     });
    
//     printBtn.addEventListener('mouseleave', () => {
//       printBtn.style.backgroundColor = '#67c23a !important';
//       printBtn.style.borderColor = '#67c23a !important';
//     });
    
//     printBtn.addEventListener('click', handleCustomPrint);
    
//     // 查找合适的位置插入（在批量签收按钮后）
//     const batchReceiveBtn = btnGroup.querySelector('#batch-receive-btn');
//     if (batchReceiveBtn) {
//       batchReceiveBtn.insertAdjacentElement('afterend', printBtn);
//     } else {
//       // 查找最后一个按钮
//       const lastButton = btnGroup.lastElementChild;
//       if (lastButton) {
//         lastButton.insertAdjacentElement('afterend', printBtn);
//       } else {
//         btnGroup.appendChild(printBtn);
//       }
//     }
    
//     console.log('调拨单打印按钮注入成功');
//     printExtensionInitialized = true;
    
//   } catch (error) {
//     console.error('注入打印按钮失败:', error);
//   }
// }

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

// // 获取搜索表单参数
// function getSearchParams() {
//   const params = {
//     searchType: 'inbound'
//   };
  
//   try {
//     // 获取页面上可能存在的搜索参数
//     const searchForm = document.querySelector('.searchForm');
//     if (searchForm) {
//       // 尝试从表单中获取值
//       const inputs = searchForm.querySelectorAll('input, select, .el-input__inner');
//       inputs.forEach(input => {
//         try {
//           const name = input.name || input.getAttribute('v-model') || input.id || input.getAttribute('data-model');
//           if (name && input.value) {
//             // 提取属性名（移除search.前缀）
//             const paramName = name.replace('search.', '');
//             params[paramName] = input.value;
//           }
//         } catch (e) {
//           // 忽略单个input的解析错误
//         }
//       });
//     }
//     // 尝试从URL参数中获取
//     const urlParams = new URLSearchParams(window.location.search);
//     for (const [key, value] of urlParams) {
//       if (value) {
//         params[key] = value;
//       }
//     }
    
//     // 设置默认值
//     if (!params.moveWarehouse) params.moveWarehouse = '';
//     if (!params.createdByName) params.createdByName = '';
//     if (!params.status) params.status = '';
    
//     console.log('搜索参数:', params);
//     return params;
//   } catch (error) {
//     console.error('获取搜索参数失败:', error);
//     return params;
//   }
// }
// // 获取搜索表单参数
// function getSearchParams() {
//   const params = {
//     searchType: 'inbound'
//   };

//   try {
//     // 获取搜索表单
//     const searchForm = document.querySelector('.searchform');
//     if (!searchForm) {
//       console.log('未找到搜索表单');
//       return params;
//     }

//     // 提取表单中的输入元素
//     const inputs = searchForm.querySelectorAll('input, select, .el-input__inner');

//     inputs.forEach(input => {
//       try {
//         // 获取输入元素的name或placeholder作为参数名
//         let paramName = input.name;
//         if (!paramName) {
//           // 如果没有name属性，尝试从placeholder中提取
//           const placeholder = input.placeholder;
//           if (placeholder) {
//             paramName = placeholder.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '');
//           }
//         }

//         // 如果仍然没有paramName，跳过
//         if (!paramName) return;

//         // 获取输入值
//         let value = input.value;

//         // 处理特殊字段
//         if (paramName === '调拨申请时间') {
//           paramName = 'startTime';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         } else if (input.type === 'checkbox' || input.type === 'radio') {
//           // 处理复选框和单选框
//           value = input.checked ? input.value : '';
//         }
//         if (paramName === '至') {
//           paramName = 'endTime';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         } else if (input.type === 'checkbox' || input.type === 'radio') {
//           // 处理复选框和单选框
//           value = input.checked ? input.value : '';
//         }

//         if (paramName === '产品名称') {
//           paramName = 'partName';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         } 
//         if (paramName === 'CARG全码/产品编码') {
//           paramName = 'partNo';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         } 
//         if (paramName === '调拨单号') {
//           paramName = 'transferNos';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         }

//         if (paramName === '拣货单号') {
//           paramName = 'pickingOrderNo';
//           // 日期字段可能需要额外处理
//           value = input.value.trim();
//         }

//         // 如果值不为空，添加到params
//         if (value && value.trim() !== '') {
//           params[paramName] = value.trim();
//         }
//       } catch (e) {
//         console.error(`提取参数失败: ${e.message}`);
//       }
//     });



//     console.log('提取的搜索参数:', params);
//     return params;
//   } catch (error) {
//     console.error('获取搜索参数失败:', error);
//     return params;
//   }
// }




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
    showPrintPreview(printData, transferNos);
    
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

// // 格式化数据
// function formatPrintData(rawData) {
//   const groupedData = groupDataByTransferNo(rawData);
//   const formattedGroups = [];

//   // 获取当前用户信息
//   const currentUser = '当前用户'; // 实际应从用户信息获取
//   const currentTime = getCurrentTime();

//   // 处理每个调拨单组
//   Object.entries(groupedData).forEach(([transferNo, items]) => {
//     if (items.length === 0) return;

//     // 按调拨单号排序，确保同一调拨单的数据在一起
//     items.sort((a, b) => {
//       if (a.partCode && b.partCode) {
//         return a.partCode.localeCompare(b.partCode);
//       }
//       return 0;
//     });

//     // 计算总数和总金额
//     let totalQuantity = 0;
//     let totalAmount = 0;

//     items.forEach(item => {
//       const quantity = parseInt(item.inboundQuantity) || 0;
//       const price = parseFloat(item.salesPrice) || 0;
//       const rate = parseFloat(item.priceIncreaseRate) || 1;

//       totalQuantity += quantity;
//       totalAmount += quantity * price * rate;
//     });

//     // 添加分组信息
//     const group = {
//       transferNo: transferNo,
//       items: items,
//       headerInfo: {
//         ...items[0], // 使用第一个项目作为头部信息
//         userName: currentUser,
//         currentDate: currentTime,
//         totalNum: totalQuantity,
//         totalAmount: totalAmount.toFixed(2)
//       }
//     };

//     formattedGroups.push(group);
//   });

//   console.log(`格式化后的数据: ${formattedGroups.length} 个调拨单`);
//   return formattedGroups;
// }

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


/**
 * 查找空库位
 * @param {string} storage_code - 仓库代码
 * @returns {Promise<Array<string>>} - 返回空库位列表
 */
async function find_empty_locations(storage_code) {
  // 生成所有库位集合（需根据实际逻辑实现）
  const all_locations = generate_storage_locations_set();

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
  const json_data = await query_all_inventory(storage_code, { categoryTwo: '90921001' });

  if (json_data && json_data.data && json_data.data.rows) {
    const localno_list = new Set(json_data.data.rows.map(item => item.location_no));
    return localno_list;
  }

  return new Set();
}



/**
 * 生成所有库位集合
 * @returns {Array<string>} - 返回所有库位列表
 */
function generate_storage_locations_set() {
  // 根据实际逻辑生成库位列表
  const all_locations = [];
  // 示例：生成从 A01 到 A56 的库位
  for (let i = 1; i <= 56; i++) {
    all_locations.push(`A${i.toString().padStart(2, '0')}`);
  }
  return all_locations;
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


// async function formatPrintData(rawData) {
//   const groupedData = groupDataByTransferNo(rawData);
//   const formattedGroups = [];

//   // 获取当前用户信息
//   const currentUser = '当前用户'; // 实际应从用户信息获取
//   const currentTime = getCurrentTime();

//   // 处理每个调拨单组
//   for (const [transferNo, items] of Object.entries(groupedData)) {
//     if (items.length === 0) continue;

//     // 按调拨单号排序，确保同一调拨单的数据在一起
//     items.sort((a, b) => {
//       if (a.partCode && b.partCode) {
//         return a.partCode.localeCompare(b.partCode);
//       }
//       return 0;
//     });

//     // 获取当前调拨单的 transferId
//     const transferId = items[0].transferId || items[0].id;

//     // 调用 inboundDetail_query 获取 detail_data
//     let detail_data = [];
//     try {
//       const response = await inboundDetail_query(transferId);
//       if (response && response.data) {
//         detail_data = response.data;
//       }
//     } catch (error) {
//       console.error(`获取调拨单 ${transferNo} 的明细数据失败:`, error);
//     }

//     // 计算总数和总金额
//     let totalQuantity = 0;
//     let totalAmount = 0;

//     // 处理每个 item，合并 remark
//     const processedItems = items.map(item => {
//       const quantity = parseInt(item.inboundQuantity) || 0;
//       const price = parseFloat(item.salesPrice) || 0;
//       const rate = parseFloat(item.priceIncreaseRate) || 1;

//       totalQuantity += quantity;
//       totalAmount += quantity * price * rate;

//       // 匹配 detail_data 中的 remark
//       const detailItem = detail_data.find(detail => detail.detailId === item.detailId);
//       const remark = detailItem ? detailItem.remark : '';
//       const shelfLocationNo = detailItem ? detailItem.shelfLocationNo : '';
//       return {
//         ...item,
//         remark: remark,
//         shelfLocationNo: shelfLocationNo
//       };
//     });

//     // 添加分组信息
//     const group = {
//       transferNo: transferNo,
//       items: processedItems,
//       headerInfo: {
//         ...items[0], // 使用第一个项目作为头部信息
//         userName: currentUser,
//         currentDate: currentTime,
//         totalNum: totalQuantity,
//         totalAmount: totalAmount.toFixed(2)
//       }
//     };

//     formattedGroups.push(group);
//   }

//   console.log(`格式化后的数据: ${formattedGroups.length} 个调拨单`);
//   return formattedGroups;
// }

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
      return {
        ...item,
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
// // 显示打印预览
// function showPrintPreview(printData, transferNos) {
//   try {
//     // 格式化数据
//     const formattedData = formatPrintData(printData);

//     // 创建与系统类似的预览对话框
//     const dialogWrapper = document.createElement('div');
//     dialogWrapper.className = 'el-dialog__wrapper';
//     dialogWrapper.style.cssText = `z-index: ${getRandomZIndex()};`; // 动态设置 z-index

//     const dialog = document.createElement('div');
//     dialog.className = 'el-dialog';
//     dialog.setAttribute('role', 'dialog');
//     dialog.setAttribute('aria-modal', 'true');
//     dialog.setAttribute('aria-label', `调入清单打印预览-(已选择${transferNos.length}个单据)`);
//     dialog.style.cssText = 'margin-top: 15vh; width: 80%;';

//     // 对话框头部
//     const dialogHeader = document.createElement('div');
//     dialogHeader.className = 'el-dialog__header';
//     dialogHeader.innerHTML = `<span class="el-dialog__title">调入清单打印预览-(已选择${transferNos.length}个单据)</span>
//       <button type="button" aria-label="Close" class="el-dialog__headerbtn">
//         <i class="el-dialog__close el-icon el-icon-close"></i>
//       </button>`;

//     // 对话框主体
//     const dialogBody = document.createElement('div');
//     dialogBody.className = 'el-dialog__body';

//     // 打印机选择区域
//     const printerSelect = document.createElement('div');
//     printerSelect.style.cssText = 'margin-bottom: 20px;';
//     printerSelect.innerHTML = '<span style="font-weight: bold;">选择打印机:</span>';

//     const selectContainer = document.createElement('div');
//     selectContainer.className = 'el-select el-select--small';
//     selectContainer.style.cssText = 'width: 300px; margin-top: 10px;';

//     // 输入框
//     const selectInput = document.createElement('div');
//     selectInput.className = 'el-input el-input--small el-input--suffix';
//     selectInput.innerHTML = `
//       <input type="text" readonly="readonly" autocomplete="off" placeholder="点击选择打印机" 
//              class="el-input__inner" id="printerInput">
//       <span class="el-input__suffix">
//         <span class="el-input__suffix-inner">
//           <i class="el-select__caret el-input__icon el-icon-arrow-up"></i>
//         </span>
//       </span>
//     `;

//     // 下拉选项容器
//     const dropdown = document.createElement('div');
//     dropdown.className = 'el-select-dropdown el-popper';
//     dropdown.style.cssText = 'display: none; min-width: 300px; max-height: 200px; overflow-y: auto;';

//     const dropdownContent = document.createElement('div');
//     dropdownContent.className = 'el-scrollbar';
//     dropdownContent.innerHTML = `
//       <div class="el-select-dropdown__wrap el-scrollbar__wrap" style="margin-bottom: -12px; margin-right: -12px;">
//         <ul class="el-scrollbar__view el-select-dropdown__list" id="printerList">
//           <li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>
//         </ul>
//       </div>
//     `;

//     dropdown.appendChild(dropdownContent);
//     selectContainer.appendChild(selectInput);
//     selectContainer.appendChild(dropdown);
//     printerSelect.appendChild(selectContainer);

//     // 当前选中的打印机
//     let selectedPrinter = null;

//     // 加载打印机列表
//     async function loadPrinterList() {
//       try {
//         const printerList = document.getElementById('printerList');

//         // 清除之前的加载状态
//         printerList.innerHTML = '<li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>';

//         // 使用iframe获取打印机列表（绕过CSP）
//         const printerIframe = document.createElement('iframe');
//         printerIframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
//         printerIframe.srcdoc = `
//       <script>
//         try {
//           const LODOP = window.parent.CLODOP || window.parent.getLodop();
//           if (LODOP) {
//             const printerCount = LODOP.GET_PRINTER_COUNT();
//             const printers = [];
//             let defaultPrinterIndex = -1;
            
//             // 尝试多种方法确定默认打印机
            
//             // 方法2: 如果上面失败，尝试找到包含"默认"字样的打印机
//             for (let i = 0; i < printerCount; i++) {
//               const printerName = LODOP.GET_PRINTER_NAME(i);
//               printers.push({
//                 index: i,
//                 name: printerName,
//                 isDefault: i === defaultPrinterIndex
//               });
              
//               // 如果还没有找到默认打印机，尝试根据名称判断
//               if (defaultPrinterIndex === -1) {
//                 if (printerName.toLowerCase().includes('default') || 
//                     printerName.includes('默认') ||
//                     printerName.toLowerCase().includes('epson') || // 常见的默认打印机
//                     printerName.toLowerCase().includes('hp') ||
//                     printerName.toLowerCase().includes('canon')) {
//                   defaultPrinterIndex = i;
//                 }
//               }
//             }
            
//             // 方法3: 如果仍然没有找到，使用第一个打印机
//             if (defaultPrinterIndex === -1 && printers.length > 0) {
//               defaultPrinterIndex = 0;
//             }
            
//             window.parent.postMessage({
//               type: 'PRINTER_LIST_LOADED',
//               printers: printers,
//               defaultPrinterIndex: defaultPrinterIndex
//             }, '*');
//           } else {
//             window.parent.postMessage({
//               type: 'PRINTER_LIST_ERROR',
//               error: 'CLodop未初始化'
//             }, '*');
//           }
//         } catch (error) {
//           window.parent.postMessage({
//             type: 'PRINTER_LIST_ERROR',
//             error: error.message
//           }, '*');
//         }
//       </script>
//     `;

//         document.body.appendChild(printerIframe);

//         // 创建唯一的事件ID，避免重复监听
//         const eventId = 'printer_list_' + Date.now();

//         // 监听打印机列表加载完成
//         const messageHandler = (event) => {
//           // 只处理当前会话的事件
//           if (event.data.type === 'PRINTER_LIST_LOADED' || event.data.type === 'PRINTER_LIST_ERROR') {
//             window.removeEventListener('message', messageHandler);

//             if (printerIframe.parentNode) {
//               document.body.removeChild(printerIframe);
//             }

//             if (event.data.type === 'PRINTER_LIST_LOADED') {
//               const printers = event.data.printers;
//               const defaultPrinterIndex = event.data.defaultPrinterIndex;
//               printerList.innerHTML = '';

//               if (printers.length === 0) {
//                 printerList.innerHTML = '<li class="el-select-dropdown__item"><span>未找到可用打印机</span></li>';
//               } else {
//                 printers.forEach((printer, index) => {
//                   const item = document.createElement('li');
//                   item.className = 'el-select-dropdown__item';

//                   // 默认选择系统默认打印机
//                   if (defaultPrinterIndex !== -1 && printer.index === defaultPrinterIndex) {
//                     item.classList.add('selected');
//                     selectedPrinter = printer;
//                     document.getElementById('printerInput').value = printer.name;
//                     item.innerHTML = `<span>${printer.name} (默认)</span>`;
//                   } else {
//                     item.innerHTML = `<span>${printer.name}</span>`;
//                   }

//                   item.dataset.index = printer.index;
//                   item.dataset.name = printer.name;

//                   item.addEventListener('click', () => {
//                     // 移除之前选中的样式
//                     document.querySelectorAll('.el-select-dropdown__item.selected').forEach(el => {
//                       el.classList.remove('selected');
//                     });

//                     // 添加选中样式
//                     item.classList.add('selected');

//                     // 更新输入框显示
//                     document.getElementById('printerInput').value = printer.name;

//                     // 更新选中的打印机
//                     selectedPrinter = printer;

//                     // 隐藏下拉菜单
//                     dropdown.style.display = 'none';
//                   });

//                   printerList.appendChild(item);
//                 });
//               }
//             } else {
//               printerList.innerHTML = `<li class="el-select-dropdown__item"><span>加载打印机失败: ${event.data.error}</span></li>`;
//             }

//             // 清除超时定时器
//             clearTimeout(timeoutId);
//           }
//         };

//         window.addEventListener('message', messageHandler);

//         // 超时处理
//         const timeoutId = setTimeout(() => {
//           window.removeEventListener('message', messageHandler);
//           if (printerIframe.parentNode) {
//             document.body.removeChild(printerIframe);
//           }
//           printerList.innerHTML = '<li class="el-select-dropdown__item"><span>加载超时，请检查CLodop</span></li>';
//         }, 5000);

//       } catch (error) {
//         console.error('加载打印机列表失败:', error);
//         document.getElementById('printerList').innerHTML = '<li class="el-select-dropdown__item"><span>加载失败</span></li>';
//       }
//     }


//     // 下拉菜单显示/隐藏控制
//     const inputField = selectInput.querySelector('input');
//     const dropdownIcon = selectInput.querySelector('.el-select__caret');

//     function toggleDropdown() {
//       if (dropdown.style.display === 'none') {
//         dropdown.style.display = 'block';
//         dropdownIcon.classList.remove('el-icon-arrow-up');
//         dropdownIcon.classList.add('el-icon-arrow-down');
//       } else {
//         dropdown.style.display = 'none';
//         dropdownIcon.classList.remove('el-icon-arrow-down');
//         dropdownIcon.classList.add('el-icon-arrow-up');
//       }
//     }

//     inputField.addEventListener('click', toggleDropdown);
//     dropdownIcon.addEventListener('click', toggleDropdown);

//     // 点击外部关闭下拉菜单
//     document.addEventListener('click', (event) => {
//       if (!selectContainer.contains(event.target)) {
//         dropdown.style.display = 'none';
//         dropdownIcon.classList.remove('el-icon-arrow-down');
//         dropdownIcon.classList.add('el-icon-arrow-up');
//       }
//     });

//     // 按钮区域
//     const buttonContainer = document.createElement('div');
//     buttonContainer.style.cssText = 'text-align: center; margin-top: 20px;';
//     buttonContainer.innerHTML = `
//       <button type="button" class="el-button el-button--default el-button--small">
//         <span>返　回</span>
//       </button>
//       <button type="button" class="el-button el-button--primary el-button--small">
//         <span>打　印</span>
//       </button>
//     `;

//     // 打印预览内容区域
//     const printPreviewDiv = document.createElement('div');
//     printPreviewDiv.id = 'printPreviewDiv';

//     // ... 其余代码保持不变（生成打印内容的部分）

//     // 生成打印内容
//     let printHTML = '';
//     formattedData.forEach((group, groupIndex) => {
//       const header = group.headerInfo;
//       const items = group.items;
//       const transferType = header.transferType;
//       const isPriceTransfer = transferType === 47171002 || transferType === '47171002';

//       printHTML += `
//         <div id="transferPrintDiv${groupIndex}" index="${groupIndex}">
//           <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
//             <div style="width: 100%; margin: 0px auto; text-align: center;">
//               <span style="font-size: 25px; font-weight: bold;">调入清单</span>
//             </div>
//             <div style="width: 100%; margin: 0px; text-align: left;">
//               <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 96%;">
//                 <tbody>
//                   <tr>
//                     <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
//                     <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
//                     <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${header.transferNo || ''}</td>
//                   </tr>
//                   <tr>
//                     <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
//                     <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
//                     <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
//                   </tr>
//                 </tbody>
//               </table>
//               <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
//                 <tbody>
//                   <tr>
//                     <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
//                     <td style="width: 25%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
//                     <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
//                     <td style="width: 13%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品编码</td>
//                     <td style="width: 15%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库库位</td>
//                     <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库数量</td>
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
//                   </tr>
//       `;

//       items.forEach((item, index) => {
//         const quantity = parseInt(item.inboundQuantity) || 0;
//         const price = parseFloat(item.salesPrice) || 0;
//         const rate = parseFloat(item.priceIncreaseRate) || 1;
//         const amount = (quantity * price * rate).toFixed(2);

//         printHTML += `
//                   <tr>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
//                     <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partCode || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.inboundLocationNo || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
//                   </tr>
//         `;
//       });

//       // 汇总行
//       printHTML += `
//                   <tr style="text-align: center;">
//                     <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
//                     <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
//                     <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
//                     <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
//                     ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
//                   </tr>
//                 </tbody>
//               </table>
//             </div>
//           </div>
//         </div>
//       `;
//     });

//     printPreviewDiv.innerHTML = printHTML;

//     // 组装对话框
//     dialogBody.appendChild(printerSelect);
//     dialogBody.appendChild(buttonContainer);
//     dialogBody.appendChild(printPreviewDiv);

//     dialog.appendChild(dialogHeader);
//     dialog.appendChild(dialogBody);
//     dialogWrapper.appendChild(dialog);

//     document.body.appendChild(dialogWrapper);

//     // 添加事件监听器
//     const closeButton = dialogHeader.querySelector('.el-dialog__headerbtn');
//     const returnButton = buttonContainer.querySelector('.el-button--default');
//     const printButton = buttonContainer.querySelector('.el-button--primary');

//     // 关闭对话框
//     const closeDialog = () => {
//       if (dialogWrapper.parentNode) {
//         dialogWrapper.parentNode.removeChild(dialogWrapper);
//       }
//     };

//     closeButton.addEventListener('click', closeDialog);
//     returnButton.addEventListener('click', closeDialog);

//     // 打印功能
//     printButton.addEventListener('click', async () => {
//       try {
//         if (!selectedPrinter) {
//           showMessage('请先选择打印机', 'warning');
//           return;
//         }

//         // 直接打印预览内容
//         await printDirect(printPreviewDiv.innerHTML, selectedPrinter.name);

//         // 显示成功消息
//         showMessage(`打印任务已发送到打印机: ${selectedPrinter.name}`, 'success');
//         // 打印成功后自动关闭预览对话框
//         closeDialog();
//       } catch (error) {
//         console.error('打印失败:', error);
//         showMessage('打印失败: ' + error.message, 'error');
//       }
//     });

//     // 加载打印机列表
//     setTimeout(loadPrinterList, 100);

//     // ... 其余代码（ESC键关闭、遮罩层关闭等）保持不变

//   } catch (error) {
//     console.error('打开打印预览失败:', error);
//     showMessage('打开打印预览失败: ' + error.message, 'error');
//   }
// }

async function showPrintPreview(printData, transferNos) {
  try {
    // 格式化数据
    const formattedData=await formatPrintData(printData);
    // 检查 formattedData 是否为数组
    if (!Array.isArray(formattedData)) {
      throw new Error('格式化后的数据不是数组');
    }
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

    // 添加“加价调拨”开关按钮
    const priceToggleContainer = document.createElement('div');
    priceToggleContainer.style.cssText = 'margin-bottom: 20px; display: flex; align-items: center;';

    const priceToggleLabel = document.createElement('span');
    priceToggleLabel.style.cssText = 'font-weight: bold; margin-right: 10px;';
    priceToggleLabel.textContent = '加价调拨:';

    const priceToggle = document.createElement('input');
    priceToggle.type = 'checkbox';
    priceToggle.id = 'priceToggle';
    priceToggle.style.cssText = 'margin-right: 5px;';

    priceToggleContainer.appendChild(priceToggleLabel);
    priceToggleContainer.appendChild(priceToggle);

    // 按钮区域
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'text-align: center; margin-top: 20px;';
    buttonContainer.innerHTML = `
      <button type="button" class="el-button el-button--default el-button--small">
        <span>返　回</span>
      </button>
      <button type="button" class="el-button el-button--primary el-button--small">
        <span>打　印</span>
      </button>
    `;

    // 打印预览内容区域
    const printPreviewDiv = document.createElement('div');
    printPreviewDiv.id = 'printPreviewDiv';

    // // 生成打印内容
    // function generatePrintHTML(isPriceTransfer) {
    //   let printHTML = '';
    //   formattedData.forEach((group, groupIndex) => {
    //     const header = group.headerInfo;
    //     const items = group.items;

    //     printHTML += `
    //   <div id="transferPrintDiv${groupIndex}" index="${groupIndex}">
    //     <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
    //       <div style="width: 100%; margin: 0px auto; text-align: center;">
    //         <span style="font-size: 25px; font-weight: bold;">调入清单</span>
    //       </div>
    //       <div style="width: 100%; margin: 0px; text-align: left;">
    //         <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 96%;">
    //           <tbody>
    //             <tr>
    //               <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
    //               <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
    //               <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${header.transferNo || ''}</td>
    //             </tr>
    //             <tr>
    //               <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
    //               <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
    //               <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
    //             </tr>
    //           </tbody>
    //         </table>
    //         <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
    //           <tbody>
    //             <tr>
    //               <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
    //               <td style="width: 25%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
    //               <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
    //               <td style="width: 13%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品编码</td>
    //               <td style="width: 15%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库库位</td>
    //               <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库数量</td>
    //               ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
    //               ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
    //               ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
    //             </tr>
    // `;

    //     items.forEach((item, index) => {
    //       const quantity = parseInt(item.inboundQuantity) || 0;
    //       const price = parseFloat(item.salesPrice) || 0;
    //       const rate = parseFloat(item.priceIncreaseRate) || 1;
    //       const amount = (quantity * price * rate).toFixed(2);

    //       printHTML += `
    //             <tr>
    //               <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
    //               <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
    //               <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
    //               <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partCode || ''}</td>
    //               <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.inboundLocationNo || ''}</td>
    //               <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
    //               ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
    //               ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
    //               ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
    //             </tr>
    //   `;
    //     });

    //     // 汇总行
    //     printHTML += `
    //             <tr style="text-align: center;">
    //               <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
    //               <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
    //               <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
    //               <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
    //               ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
    //             </tr>
    //           </tbody>
    //         </table>
    //       </div>
    //     </div>
    //   </div>
    // `;
    //   });
    //   return printHTML;
    // }






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

    // async function generatePrintHTML(isPriceTransfer) {
    //   let printHTML = '';
    //   const searchParams = getSearchParams();
    //   const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
    //   const storage_code = warehouseInfo.storage_code;
    //   const warehouseId = warehouseInfo.warehouseId;

    //   // 获取所有库存数据并构建索引
    //   const all_stock_data = await get_all_stock_data(storage_code);
    //   const stock_indices = build_stock_indices(all_stock_data);

    //   formattedData.forEach((group, groupIndex) => {
    //     const header = group.headerInfo;
    //     const items = group.items;
    //     const transferType = header.transferType;
    //     const isPriceTransfer = transferType === 47171002 || transferType === '47171002';

    //     printHTML += `
    //         <div id="transferPrintDiv${groupIndex}" index="${groupIndex}">
    //             <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
    //                 <div style="width: 100%; margin: 0px auto; text-align: center;">
    //                     <span style="font-size: 25px; font-weight: bold;">调入清单</span>
    //                 </div>
    //                 <div style="width: 100%; margin: 0px; text-align: left;">
    //                     <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 96%;">
    //                         <tbody>
    //                             <tr>
    //                                 <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
    //                                 <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
    //                                 <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${header.transferNo || ''}</td>
    //                             </tr>
    //                             <tr>
    //                                 <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
    //                                 <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
    //                                 <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
    //                             </tr>
    //                         </tbody>
    //                     </table>
    //                     <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
    //                         <tbody>
    //                             <tr>
    //                                 <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
    //                                 <td style="width: 22%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
    //                                 <td style="width: 6%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
    //                                 <td style="width: 12%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品编码</td>
    //                                 <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库库位</td>
    //                                 <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库数量</td>
    //                                 <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">指示库位</td>
    //                                 <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">调拨前库存数</td>
    //                                 <td style="width: 15%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">3月内最近出库信息</td>
    //                                 ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
    //                                 ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
    //                                 ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
    //                                 </tr>
    //     `;

    //     items.forEach(async (item, index) => {
    //       const quantity = parseInt(item.inboundQuantity) || 0;
    //       const price = parseFloat(item.salesPrice) || 0;
    //       const rate = parseFloat(item.priceIncreaseRate) || 1;
    //       const amount = (quantity * price * rate).toFixed(2);

    //       // 获取库位库存数量
    //       const inboundLocationNo = item.inboundLocationNo;
    //       const locationStock = stock_indices.location[inboundLocationNo] || [];
    //       const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);

    //       // 获取调拨前库存数
    //       const partCode = item.partCode;
    //       const preTransferStock = stock_indices.part_code[partCode] || [];
    //       const preTransferQty = preTransferStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);

    //       // 获取3月内最近出库信息
    //       const orderData = await query_order_by_code(partCode, warehouseId);
    //       const recentSaleInfo = get_recent_sale_location(orderData);

    //       printHTML += `
    //                         <tr>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
    //                             <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partCode || ''}</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${inboundLocationNo || ''}【${stockQty}】</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.shelfLocationNo || ''}【${preTransferQty}】</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${preTransferQty}</td>
    //                             <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${recentSaleInfo}</td>
    //                             ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
    //                             ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
    //                             ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
    //                             </tr>
    //         `;
    //     });

    //     // 汇总行
    //     printHTML += `
    //                         <tr style="text-align: center;">
    //                             <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
    //                             <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
    //                             <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
    //                             <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
    //                             <td colspan="3" style="border: 1px solid rgb(0, 0, 0);"></td>
    //                             ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
    //                         </tr>
    //                     </tbody>
    //                 </table>
    //             </div>
    //         </div>
    //     </div>
    //     `;
    //   });

    //   return printHTML;
    // }


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

    async function generatePrintHTML(isPriceTransfer) {
      let printHTML = '';
      const searchParams = getSearchParams();
      const warehouseInfo = getWarehouseInfo(searchParams.moveWarehouseName);
      const storage_code = warehouseInfo.storage_code;
      const warehouseId = warehouseInfo.warehouseId;

      const all_stock_data = await get_all_stock_data(storage_code);
      const stock_indices = build_stock_indices(all_stock_data);

      // 使用 Promise.all 处理异步操作
      const formattedDataPromises = formattedData.map(async (group, groupIndex) => {
        const header = group.headerInfo;
        const items = group.items;
        const transferType = header.transferType;
        // const isPriceTransfer = transferType === 47171002 || transferType === '47171002';

        // 处理每个 item 的异步操作
        const itemsHTML = await Promise.all(
          items.map(async (item, index) => {
            const quantity = parseInt(item.inboundQuantity) || 0;
            const price = parseFloat(item.salesPrice) || 0;
            const rate = parseFloat(item.priceIncreaseRate) || 1;
            const amount = (quantity * price * rate).toFixed(2);

            // 获取库位库存数量
            const inboundLocationNo = item.inboundLocationNo;
            const locationStock = stock_indices.location[inboundLocationNo] || [];
            const stockQty = locationStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
            // 获取指示库位库存数量
            const shelfLocationNo=item.shelfLocationNo;
            const shelfLocationNostock=stock_indices.location[shelfLocationNo] || [];
            const shelfQty= shelfLocationNostock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);
            // 获取调拨前库存数
            const partCode = item.partCode;
            let prestockvalue = ''; // 初始化为空字符串
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
            // const preTransferStock = stock_indices.part_code[partCode] || [];
            // const preTransferQty = preTransferStock.reduce((sum, loc) => sum + (loc.location_accessories_number || 0), 0);

            // 获取3月内最近出库信息
            const orderData = await query_order_by_code(partCode, warehouseId);
            const recentSaleInfo =`${get_recent_sale_location(orderData)}\n ${item.remark || ''}`;

            return `
          <tr>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
            <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.partCode || ''}</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${inboundLocationNo || ''}\n【${stockQty}】</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${item.shelfLocationNo || ''}\n【${shelfQty}】</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${prestockvalue || ''}</td>
            <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">${recentSaleInfo}</td>
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
              <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 96%;">
                <tbody>
                  <tr>
                    <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
                    <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
                    <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${header.transferNo || ''}</td>
                  </tr>
                  <tr>
                    <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
                    <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
                    <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
                  </tr>
                </tbody>
              </table>
              <table align="center" valign="middle" style="width: 100%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
                <tbody>
                  <tr>
                    <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
                    <td style="width: 25%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
                    <td style="width: 6%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
                    <td style="width: 16%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">产品编码</td>
                    <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n库位</td>
                    <td style="width: 6%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">入库\n数量</td>
                    <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">指示\n库位</td>
                    <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">调拨前\n库存数</td>
                    <td style="width: 12%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;white-space: pre-line;">3月内最近\n出库信息</td>
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
                    <td colspan="3" style="border: 1px solid rgb(0, 0, 0);"></td>
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
      printHTML = formattedDataHTML.join('');

      return printHTML;
    }


    // 异步调用
    generatePrintHTML(false)
      .then(html => {
        printPreviewDiv.innerHTML = html;
      })
      .catch(error => {
        console.error('生成打印内容失败:', error);
        showMessage('生成打印内容失败: ' + error.message, 'error');
      });

    // // 监听价格开关状态变化
    // priceToggle.addEventListener('change', (event) => {
    //   const isChecked = event.target.checked;
    //   printPreviewDiv.innerHTML = generatePrintHTML(isChecked);
    // });
    // 监听价格开关状态变化
    priceToggle.addEventListener('change', async (event) => {
      const isChecked = event.target.checked;
      generatePrintHTML(isChecked)
        .then(html => {
          printPreviewDiv.innerHTML = html;
        })
        .catch(error => {
          console.error('生成打印内容失败:', error);
          showMessage('生成打印内容失败: ' + error.message, 'error');
        });
    });
    // 组装对话框
    dialogBody.appendChild(printerSelect);
    dialogBody.appendChild(priceToggleContainer); // 添加开关按钮
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
}


// function showPrintPreview(printData, transferNos) {
//   try {
//     const formattedData = formatPrintData(printData);
//     const dialogWrapper = document.createElement('div');
//     dialogWrapper.className = 'el-dialog__wrapper';
//     dialogWrapper.style.cssText = `z-index: ${getRandomZIndex()};`;

//     const dialog = document.createElement('div');
//     dialog.className = 'el-dialog';
//     dialog.setAttribute('role', 'dialog');
//     dialog.setAttribute('aria-modal', 'true');
//     dialog.setAttribute('aria-label', `调入清单打印预览-(已选择${transferNos.length}个单据)`);
//     dialog.style.cssText = 'margin-top: 15vh; width: 80%;';

//     // 对话框头部
//     const dialogHeader = document.createElement('div');
//     dialogHeader.className = 'el-dialog__header';
//     dialogHeader.innerHTML = `<span class="el-dialog__title">调入清单打印预览-(已选择${transferNos.length}个单据)</span>
//       <button type="button" aria-label="Close" class="el-dialog__headerbtn">
//         <i class="el-dialog__close el-icon el-icon-close"></i>
//       </button>`;

//     // 对话框主体
//     const dialogBody = document.createElement('div');
//     dialogBody.className = 'el-dialog__body';

//     // 打印机选择区域
//     const printerSelect = document.createElement('div');
//     printerSelect.style.cssText = 'margin-bottom: 20px;';
//     printerSelect.innerHTML = '<span style="font-weight: bold;">选择打印机:</span>';

//     const selectContainer = document.createElement('div');
//     selectContainer.className = 'el-select el-select--small';
//     selectContainer.style.cssText = 'width: 300px; margin-top: 10px;';

//     // 输入框
//     const selectInput = document.createElement('div');
//     selectInput.className = 'el-input el-input--small el-input--suffix';
//     selectInput.innerHTML = `
//       <input type="text" readonly="readonly" autocomplete="off" placeholder="点击选择打印机" 
//              class="el-input__inner" id="printerInput">
//       <span class="el-input__suffix">
//         <span class="el-input__suffix-inner">
//           <i class="el-select__caret el-input__icon el-icon-arrow-up"></i>
//         </span>
//       </span>
//     `;

//     // 下拉选项容器
//     const dropdown = document.createElement('div');
//     dropdown.className = 'el-select-dropdown el-popper';
//     dropdown.style.cssText = 'display: none; min-width: 300px; max-height: 200px; overflow-y: auto;';

//     const dropdownContent = document.createElement('div');
//     dropdownContent.className = 'el-scrollbar';
//     dropdownContent.innerHTML = `
//       <div class="el-select-dropdown__wrap el-scrollbar__wrap" style="margin-bottom: -12px; margin-right: -12px;">
//         <ul class="el-scrollbar__view el-select-dropdown__list" id="printerList">
//           <li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>
//         </ul>
//       </div>
//     `;

//     dropdown.appendChild(dropdownContent);
//     selectContainer.appendChild(selectInput);
//     selectContainer.appendChild(dropdown);
//     printerSelect.appendChild(selectContainer);

//     // 当前选中的打印机
//     let selectedPrinter = null;

//     // 加载打印机列表
//     async function loadPrinterList() {
//       try {
//         const printerList = document.getElementById('printerList');

//         // 清除之前的加载状态
//         printerList.innerHTML = '<li class="el-select-dropdown__item"><span>正在加载打印机列表...</span></li>';

//         // 使用iframe获取打印机列表（绕过CSP）
//         const printerIframe = document.createElement('iframe');
//         printerIframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
//         printerIframe.srcdoc = `
//       <script>
//         try {
//           const LODOP = window.parent.CLODOP || window.parent.getLodop();
//           if (LODOP) {
//             const printerCount = LODOP.GET_PRINTER_COUNT();
//             const printers = [];
//             let defaultPrinterIndex = -1;
            
//             // 尝试多种方法确定默认打印机
            
//             // 方法2: 如果上面失败，尝试找到包含"默认"字样的打印机
//             for (let i = 0; i < printerCount; i++) {
//               const printerName = LODOP.GET_PRINTER_NAME(i);
//               printers.push({
//                 index: i,
//                 name: printerName,
//                 isDefault: i === defaultPrinterIndex
//               });
              
//               // 如果还没有找到默认打印机，尝试根据名称判断
//               if (defaultPrinterIndex === -1) {
//                 if (printerName.toLowerCase().includes('default') || 
//                     printerName.includes('默认') ||
//                     printerName.toLowerCase().includes('epson') || // 常见的默认打印机
//                     printerName.toLowerCase().includes('hp') ||
//                     printerName.toLowerCase().includes('canon')) {
//                   defaultPrinterIndex = i;
//                 }
//               }
//             }
            
//             // 方法3: 如果仍然没有找到，使用第一个打印机
//             if (defaultPrinterIndex === -1 && printers.length > 0) {
//               defaultPrinterIndex = 0;
//             }
            
//             window.parent.postMessage({
//               type: 'PRINTER_LIST_LOADED',
//               printers: printers,
//               defaultPrinterIndex: defaultPrinterIndex
//             }, '*');
//           } else {
//             window.parent.postMessage({
//               type: 'PRINTER_LIST_ERROR',
//               error: 'CLodop未初始化'
//             }, '*');
//           }
//         } catch (error) {
//           window.parent.postMessage({
//             type: 'PRINTER_LIST_ERROR',
//             error: error.message
//           }, '*');
//         }
//       </script>
//     `;

//         document.body.appendChild(printerIframe);

//         // 创建唯一的事件ID，避免重复监听
//         const eventId = 'printer_list_' + Date.now();

//         // 监听打印机列表加载完成
//         const messageHandler = (event) => {
//           // 只处理当前会话的事件
//           if (event.data.type === 'PRINTER_LIST_LOADED' || event.data.type === 'PRINTER_LIST_ERROR') {
//             window.removeEventListener('message', messageHandler);

//             if (printerIframe.parentNode) {
//               document.body.removeChild(printerIframe);
//             }

//             if (event.data.type === 'PRINTER_LIST_LOADED') {
//               const printers = event.data.printers;
//               const defaultPrinterIndex = event.data.defaultPrinterIndex;
//               printerList.innerHTML = '';

//               if (printers.length === 0) {
//                 printerList.innerHTML = '<li class="el-select-dropdown__item"><span>未找到可用打印机</span></li>';
//               } else {
//                 printers.forEach((printer, index) => {
//                   const item = document.createElement('li');
//                   item.className = 'el-select-dropdown__item';

//                   // 默认选择系统默认打印机
//                   if (defaultPrinterIndex !== -1 && printer.index === defaultPrinterIndex) {
//                     item.classList.add('selected');
//                     selectedPrinter = printer;
//                     document.getElementById('printerInput').value = printer.name;
//                     item.innerHTML = `<span>${printer.name} (默认)</span>`;
//                   } else {
//                     item.innerHTML = `<span>${printer.name}</span>`;
//                   }

//                   item.dataset.index = printer.index;
//                   item.dataset.name = printer.name;

//                   item.addEventListener('click', () => {
//                     // 移除之前选中的样式
//                     document.querySelectorAll('.el-select-dropdown__item.selected').forEach(el => {
//                       el.classList.remove('selected');
//                     });

//                     // 添加选中样式
//                     item.classList.add('selected');

//                     // 更新输入框显示
//                     document.getElementById('printerInput').value = printer.name;

//                     // 更新选中的打印机
//                     selectedPrinter = printer;

//                     // 隐藏下拉菜单
//                     dropdown.style.display = 'none';
//                   });

//                   printerList.appendChild(item);
//                 });
//               }
//             } else {
//               printerList.innerHTML = `<li class="el-select-dropdown__item"><span>加载打印机失败: ${event.data.error}</span></li>`;
//             }

//             // 清除超时定时器
//             clearTimeout(timeoutId);
//           }
//         };

//         window.addEventListener('message', messageHandler);

//         // 超时处理
//         const timeoutId = setTimeout(() => {
//           window.removeEventListener('message', messageHandler);
//           if (printerIframe.parentNode) {
//             document.body.removeChild(printerIframe);
//           }
//           printerList.innerHTML = '<li class="el-select-dropdown__item"><span>加载超时，请检查CLodop</span></li>';
//         }, 5000);

//       } catch (error) {
//         console.error('加载打印机列表失败:', error);
//         document.getElementById('printerList').innerHTML = '<li class="el-select-dropdown__item"><span>加载失败</span></li>';
//       }
//     }


//     // 下拉菜单显示/隐藏控制
//     const inputField = selectInput.querySelector('input');
//     const dropdownIcon = selectInput.querySelector('.el-select__caret');

//     function toggleDropdown() {
//       if (dropdown.style.display === 'none') {
//         dropdown.style.display = 'block';
//         dropdownIcon.classList.remove('el-icon-arrow-up');
//         dropdownIcon.classList.add('el-icon-arrow-down');
//       } else {
//         dropdown.style.display = 'none';
//         dropdownIcon.classList.remove('el-icon-arrow-down');
//         dropdownIcon.classList.add('el-icon-arrow-up');
//       }
//     }

//     inputField.addEventListener('click', toggleDropdown);
//     dropdownIcon.addEventListener('click', toggleDropdown);

//     // 点击外部关闭下拉菜单
//     document.addEventListener('click', (event) => {
//       if (!selectContainer.contains(event.target)) {
//         dropdown.style.display = 'none';
//         dropdownIcon.classList.remove('el-icon-arrow-down');
//         dropdownIcon.classList.add('el-icon-arrow-up');
//       }
//     });

//     // 按钮区域
//     const buttonContainer = document.createElement('div');
//     buttonContainer.style.cssText = 'text-align: center; margin-top: 20px;';
//     buttonContainer.innerHTML = `
//       <button type="button" class="el-button el-button--default el-button--small">
//         <span>返　回</span>
//       </button>
//       <button type="button" class="el-button el-button--primary el-button--small">
//         <span>打　印</span>
//       </button>
//     `;

//     // 打印预览内容区域
//     const printPreviewDiv = document.createElement('div');
//     printPreviewDiv.id = 'printPreviewDiv';

//     // 生成打印内容时，确保每个调拨单的内容独立
//     let printHTML = '';
//     formattedData.forEach((group, groupIndex) => {
//       const header = group.headerInfo;
//       const items = group.items;
//       const transferType = header.transferType;
//       const isPriceTransfer = transferType === 47171002 || transferType === '47171002';

//       printHTML += `
//         <div id="transferPrintDiv${groupIndex}" index="${group.transferNo}">
//           <div style="font-family: 微软雅黑; color: rgb(0, 0, 0);">
//             <div style="width: 100%; margin: 0px auto; text-align: center;">
//               <span style="font-size: 25px; font-weight: bold;">调入清单</span>
//             </div>
//             <div style="width: 100%; margin: 0px; text-align: left;">
//               <table align="center" valign="middle" style="margin: 0px auto; font-size: 15px; width: 96%;">
//                 <tbody>
//                   <tr>
//                     <td style="width: 33%; vertical-align: top; text-align: left;">调出仓库：${header.removeWarehouseName || ''}</td>
//                     <td style="width: 33%; vertical-align: top; text-align: left;">调入仓库：${header.moveWarehouseName || ''}</td>
//                     <td style="width: 35%; vertical-align: top; text-align: left;">单 据 号：${header.transferNo || ''}</td>
//                   </tr>
//                   <tr>
//                     <td style="vertical-align: top; text-align: left;">开 单 人：${header.createdByName || ''}</td>
//                     <td style="vertical-align: top; text-align: left;">上 架 人：${header.onshelf_by || ''}</td>
//                     <td style="vertical-align: top; text-align: left;">摘 要：${header.headRemark || ''}</td>
//                   </tr>
//                 </tbody>
//               </table>
//               <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
//                 <tbody>
//                   <tr>
//                     <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
//                     <td style="width: 25%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
//                     <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
//                     <td style="width: 13%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品编码</td>
//                     <td style="width: 15%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库库位</td>
//                     <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库数量</td>
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
//                     ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
//                   </tr>
//     `;

//       items.forEach((item, index) => {
//         const quantity = parseInt(item.inboundQuantity) || 0;
//         const price = parseFloat(item.salesPrice) || 0;
//         const rate = parseFloat(item.priceIncreaseRate) || 1;
//         const amount = (quantity * price * rate).toFixed(2);

//         printHTML += `
//                   <tr>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
//                     <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partCode || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.inboundLocationNo || ''}</td>
//                     <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
//                     ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
//                   </tr>
//         `;
//       });

//       // 汇总行
//       printHTML += `
//                   <tr style="text-align: center;">
//                     <td colspan="3" style="border: 1px solid rgb(0, 0, 0);"></td>
//                     <td colspan="3" style="border: 1px solid rgb(0, 0, 0);"></td>
//                     <td colspan="${isPriceTransfer ? '3' : '1'}" style="border: 1px solid rgb(0, 0, 0);">合计数量：${formatNumber(header.totalNum)}</td>
//                     ${isPriceTransfer ? `<td colspan="2" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
//                   </tr>
//       `;
//       printHTML += `
//                 </tbody>
//               </table>
//             </div>
//           </div>
//         </div>
//       `;
//     });

//     printPreviewDiv.innerHTML = printHTML;

//     // 组装对话框
//     dialogBody.appendChild(printerSelect);
//     dialogBody.appendChild(buttonContainer);
//     dialogBody.appendChild(printPreviewDiv);

//     dialog.appendChild(dialogHeader);
//     dialog.appendChild(dialogBody);
//     dialogWrapper.appendChild(dialog);

//     document.body.appendChild(dialogWrapper);

//     // 添加事件监听器
//     const closeButton = dialogHeader.querySelector('.el-dialog__headerbtn');
//     const returnButton = buttonContainer.querySelector('.el-button--default');
//     const printButton = buttonContainer.querySelector('.el-button--primary');

//     // 关闭对话框
//     const closeDialog = () => {
//       if (dialogWrapper.parentNode) {
//         dialogWrapper.parentNode.removeChild(dialogWrapper);
//       }
//     };

//     closeButton.addEventListener('click', closeDialog);
//     returnButton.addEventListener('click', closeDialog);

//     // 打印功能
//     printButton.addEventListener('click', async () => {
//       try {
//         if (!selectedPrinter) {
//           showMessage('请先选择打印机', 'warning');
//           return;
//         }

//         // 直接打印预览内容
//         await printDirect(printPreviewDiv.innerHTML, selectedPrinter.name);

//         // 显示成功消息
//         showMessage(`打印任务已发送到打印机: ${selectedPrinter.name}`, 'success');
//         // 打印成功后自动关闭预览对话框
//         closeDialog();
//       } catch (error) {
//         console.error('打印失败:', error);
//         showMessage('打印失败: ' + error.message, 'error');
//       }
//     });

//     // 加载打印机列表
//     setTimeout(loadPrinterList, 100);
//   } catch (error) {
//     console.error('打开打印预览失败:', error);
//     showMessage('打开打印预览失败: ' + error.message, 'error');
//   }
// }



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


// async function printDirect(htmlContent, printerName) {
//   return new Promise((resolve, reject) => {
//     const eventId = 'print_execute_' + Date.now();

//     const messageHandler = (event) => {
//       if (event.data.type === 'PRINT_RESULT' && event.data.id === eventId) {
//         window.removeEventListener('message', messageHandler);
//         if (iframe.parentNode) document.body.removeChild(iframe);
//         event.data.success ? resolve(event.data.message) : reject(new Error(event.data.error));
//       }
//     };

//     window.addEventListener('message', messageHandler);

//     const iframe = document.createElement('iframe');
//     iframe.style.cssText = 'position: absolute; left: -9999px; top: -9999px; width: 0; height: 0;';
//     iframe.srcdoc = `
//       <!DOCTYPE html>
//       <html>
//       <head>
//         <script>
//           try {
//             const LODOP = window.parent.CLODOP || window.parent.getLodop();
//             if (!LODOP) throw new Error('CLodop 打印控件未初始化');

//             // 初始化打印任务
//             LODOP.PRINT_INIT('调拨单打印');

//             // 设置打印机
//             if ('${printerName}') {
//               const printerCount = LODOP.GET_PRINTER_COUNT();
//               for (let i = 0; i < printerCount; i++) {
//                 const name = LODOP.GET_PRINTER_NAME(i);
//                 if (name === '${printerName}') {
//                   LODOP.SET_PRINTER_INDEX(i);
//                   break;
//                 }
//               }
//             }

//             // 处理 PDF 虚拟打印机
//             if ('${printerName}'.toLowerCase().includes('pdf')) {
//               LODOP.SET_PRINT_MODE('PRINT_DEFAULTPDF', true);
//               LODOP.SET_PRINT_MODE('CANVAS_DISABLED', true);
//             }

//             // 解析 HTML 内容，按调拨单号分页
//             const parser = new DOMParser();
//             const doc = parser.parseFromString(\`${htmlContent.replace(/`/g, '\\`')}\`, 'text/html');
//             const transferDivs = doc.querySelectorAll('[id^="transferPrintDiv"]');

//             // 为每个调拨单生成独立的打印任务
//             transferDivs.forEach((div, index) => {
//               const transferNo = div.getAttribute('index');
//               LODOP.PRINT_INIT(\`调拨单打印 - \${transferNo}\`);
//               LODOP.ADD_PRINT_HTM(0, 0, '100%', '100%', div.outerHTML);
//               LODOP.SET_PRINT_PAGESIZE(1, 0, 0, 'Letter');
//               LODOP.SET_PRINT_STYLEA(0, "MarginBottom", "15mm"); // 调整下边距
//               LODOP.PRINT();
//             });

//             window.parent.postMessage({
//               type: 'PRINT_RESULT',
//               id: '${eventId}',
//               success: true,
//               message: '打印任务已发送到打印机: ${printerName}'
//             }, '*');
//           } catch (error) {
//             window.parent.postMessage({
//               type: 'PRINT_RESULT',
//               id: '${eventId}',
//               success: false,
//               error: error.message
//             }, '*');
//           }
//         </script>
//       </head>
//       <body></body>
//       </html>
//     `;

//     document.body.appendChild(iframe);

//     setTimeout(() => {
//       window.removeEventListener('message', messageHandler);
//       if (iframe.parentNode) document.body.removeChild(iframe);
//       reject(new Error('打印操作超时'));
//     }, 10000);
//   });
// }


// 初始化函数
function initPrintExtension() {
  if (printExtensionInitialized) return;

  console.log('初始化调拨单打印扩展...');

  // 立即尝试注入
  injectPrintButton();

  // 设置周期性检查
  const checkInterval = setInterval(() => {
    if (isAdjustLogPage() && !document.getElementById('custom-print-preview-btn')) {
      injectPrintButton();
    } else if (!isAdjustLogPage()) {
      clearInterval(checkInterval);
      printExtensionInitialized = false;
    }
  }, 2000);

  // 监听DOM变化
  const observer = new MutationObserver((mutations) => {
    if (isAdjustLogPage() && !document.getElementById('custom-print-preview-btn')) {
      injectPrintButton();
      observer.disconnect(); // 检测到目标页面后停止监听      
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true
  });

  // 监听页面可见性变化（SPA路由变化）
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      setTimeout(injectPrintButton, 500);
    }
  });

  console.log('调拨单打印扩展初始化完成');
}

// 页面加载后启动
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPrintExtension);
} else {
  initPrintExtension();
}
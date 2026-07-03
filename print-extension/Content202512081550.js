// 调拨单打印扩展 - Content Script

// 调拨单打印扩展 - Content Script

// 全局变量
// CLodop 打印控件的本地实现

let printExtensionInitialized = false;
let currentTransferNos = [];



// 检测是否在调拨单页面
function isAdjustLogPage() {
  try {
    // 方法1: 精确匹配路由
    const currentUrl = window.location.href;
    if (currentUrl.includes('/part/warehouse/transferInbound/index') && 
        currentUrl.includes('menuId=501304')) {
      return true;
    }

    // 方法2: 检查特定页面元素（备用）
    const tableTitle = document.querySelector('.tabletitle');
    if (tableTitle && tableTitle.textContent.includes('调拨信息')) {
      return true;
    }

    // 方法3: 检查页面内容（备用）
    const hasTransferTable = document.querySelector('table')?.textContent?.includes('调拨单号') ||
                            document.querySelector('table')?.textContent?.includes('调入方');

    if (hasTransferTable) return true;

    // 方法4: 检查页面标题（备用）
    const pageTitle = document.title;
    if (pageTitle.includes('调拨') || pageTitle.includes('Transfer')) {
      return true;
    }

    return false;
  } catch (error) {
    console.error('页面检测失败:', error);
    return false;
  }
}


// 注入打印按钮
function injectPrintButton() {
  try {
    if (!isAdjustLogPage()) return;

    // 避免重复注入
    if (document.getElementById('custom-print-preview-btn')) {
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
// 获取搜索表单参数
function getSearchParams() {
  const params = {
    searchType: 'inbound'
  };

  try {
    // 获取搜索表单
    const searchForm = document.querySelector('.searchform');
    if (!searchForm) {
      console.log('未找到搜索表单');
      return params;
    }

    // 提取表单中的输入元素
    const inputs = searchForm.querySelectorAll('input, select, .el-input__inner');

    inputs.forEach(input => {
      try {
        // 获取输入元素的name或placeholder作为参数名
        let paramName = input.name;
        if (!paramName) {
          // 如果没有name属性，尝试从placeholder中提取
          const placeholder = input.placeholder;
          if (placeholder) {
            paramName = placeholder.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '');
          }
        }

        // 如果仍然没有paramName，跳过
        if (!paramName) return;

        // 获取输入值
        let value = input.value;

        // 处理特殊字段
        if (paramName === '调拨申请时间' || paramName === '至') {
          // 日期字段可能需要额外处理
          value = input.value.trim();
        } else if (input.type === 'checkbox' || input.type === 'radio') {
          // 处理复选框和单选框
          value = input.checked ? input.value : '';
        }

        // 如果值不为空，添加到params
        if (value && value.trim() !== '') {
          params[paramName] = value.trim();
        }
      } catch (e) {
        console.error(`提取参数失败: ${e.message}`);
      }
    });

    // 处理特定字段（如调拨类型、调入方、调出方等）
    const transferTypeInput = searchForm.querySelector('input[placeholder="调拨类型"]');
    if (transferTypeInput && transferTypeInput.value) {
      params.transferType = transferTypeInput.value;
    }

    const transferNoInput = searchForm.querySelector('input[placeholder="调拨单号"]');
    if (transferNoInput && transferNoInput.value) {
      params.transferNo = transferNoInput.value;
    }

    const partNoInput = searchForm.querySelector('input[placeholder="CARG全码/产品编码"]');
    if (partNoInput && partNoInput.value) {
      params.partNo = partNoInput.value;
    }

    const partNameInput = searchForm.querySelector('input[placeholder="产品名称"]');
    if (partNameInput && partNameInput.value) {
      params.partName = partNameInput.value;
    }

    const moveWarehouseInput = searchForm.querySelector('input[placeholder="调入方"]');
    if (moveWarehouseInput && moveWarehouseInput.value) {
      params.moveWarehouse = moveWarehouseInput.value;
    }

    const removeWarehouseInput = searchForm.querySelector('input[placeholder="调出方"]');
    if (removeWarehouseInput && removeWarehouseInput.value) {
      params.removeWarehouse = removeWarehouseInput.value;
    }

    const createdByNameInput = searchForm.querySelector('input[placeholder="制单人"]');
    if (createdByNameInput && createdByNameInput.value) {
      params.createdByName = createdByNameInput.value;
    }

    const statusInput = searchForm.querySelector('input[placeholder="调拨状态"]');
    if (statusInput && statusInput.value) {
      params.status = statusInput.value;
    }

    const pickingOrderNoInput = searchForm.querySelector('input[placeholder="拣货单号"]');
    if (pickingOrderNoInput && pickingOrderNoInput.value) {
      params.pickingOrderNo = pickingOrderNoInput.value;
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

// 格式化数据
function formatPrintData(rawData) {
  const groupedData = groupDataByTransferNo(rawData);
  const formattedGroups = [];

  // 获取当前用户信息
  const currentUser = '当前用户'; // 实际应从用户信息获取
  const currentTime = getCurrentTime();

  // 处理每个调拨单组
  Object.entries(groupedData).forEach(([transferNo, items]) => {
    if (items.length === 0) return;

    // 按调拨单号排序，确保同一调拨单的数据在一起
    items.sort((a, b) => {
      if (a.partCode && b.partCode) {
        return a.partCode.localeCompare(b.partCode);
      }
      return 0;
    });

    // 计算总数和总金额
    let totalQuantity = 0;
    let totalAmount = 0;

    items.forEach(item => {
      const quantity = parseInt(item.inboundQuantity) || 0;
      const price = parseFloat(item.salesPrice) || 0;
      const rate = parseFloat(item.priceIncreaseRate) || 1;

      totalQuantity += quantity;
      totalAmount += quantity * price * rate;
    });

    // 添加分组信息
    const group = {
      transferNo: transferNo,
      items: items,
      headerInfo: {
        ...items[0], // 使用第一个项目作为头部信息
        userName: currentUser,
        currentDate: currentTime,
        totalNum: totalQuantity,
        totalAmount: totalAmount.toFixed(2)
      }
    };

    formattedGroups.push(group);
  });

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
    '90921003': '门玻璃',
    '90921004': '天窗',
    '90921005': '三角'
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
// 显示打印预览
function showPrintPreview(printData, transferNos) {
  try {
    // 格式化数据
    const formattedData = formatPrintData(printData);

    // 创建与系统类似的预览对话框
    const dialogWrapper = document.createElement('div');
    dialogWrapper.className = 'el-dialog__wrapper';
    dialogWrapper.style.cssText = `z-index: ${getRandomZIndex()};`; // 动态设置 z-index

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

    // ... 其余代码保持不变（生成打印内容的部分）

    // 生成打印内容
    let printHTML = '';
    formattedData.forEach((group, groupIndex) => {
      const header = group.headerInfo;
      const items = group.items;
      const transferType = header.transferType;
      const isPriceTransfer = transferType === 47171002 || transferType === '47171002';

      printHTML += `
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
              <table align="center" valign="middle" style="width: 98%; margin: 0px auto; font-size: 15px; vertical-align: middle; text-align: center; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">
                <tbody>
                  <tr>
                    <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">品牌</td>
                    <td style="width: 25%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品名称</td>
                    <td style="width: 8%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">分类</td>
                    <td style="width: 13%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">产品编码</td>
                    <td style="width: 15%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库库位</td>
                    <td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">入库数量</td>
                    ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">成本价 </td>' : ''}
                    ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">加价率 </td>' : ''}
                    ${isPriceTransfer ? '<td style="width: 10%; display: table-cell; vertical-align: middle; height: 20px; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">金额 </td>' : ''}
                  </tr>
      `;

      items.forEach((item, index) => {
        const quantity = parseInt(item.inboundQuantity) || 0;
        const price = parseFloat(item.salesPrice) || 0;
        const rate = parseFloat(item.priceIncreaseRate) || 1;
        const amount = (quantity * price * rate).toFixed(2);

        printHTML += `
                  <tr>
                    <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.brandName || ''}</td>
                    <td style="text-align: left; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partName || ''}</td>
                    <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${getCategoryName(item.categoryTwo)}</td>
                    <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.partCode || ''}</td>
                    <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${item.inboundLocationNo || ''}</td>
                    <td style="text-align: center; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${quantity}</td>
                    ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(price)}</td>` : ''}
                    ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(rate)}</td>` : ''}
                    ${isPriceTransfer ? `<td style="text-align: right; display: table-cell; overflow-wrap: break-word; word-break: break-all; vertical-align: middle; border: 1px solid rgb(0, 0, 0); border-collapse: collapse;">${formatNumber(amount)}</td>` : ''}
                  </tr>
        `;
      });

      // 汇总行
      printHTML += `
                  <tr style="text-align: center;">
                    <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
                    <td colspan="2" style="border: 1px solid rgb(0, 0, 0);"></td>
                    <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">合计数量：</td>
                    <td colspan="1" style="border: 1px solid rgb(0, 0, 0);">${formatNumber(header.totalNum)}</td>
                    ${isPriceTransfer ? `<td colspan="3" style="border: 1px solid rgb(0, 0, 0);">合计金额：${formatNumber(header.totalAmount)}</td>` : ''}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    });

    printPreviewDiv.innerHTML = printHTML;

    // 组装对话框
    dialogBody.appendChild(printerSelect);
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

    // ... 其余代码（ESC键关闭、遮罩层关闭等）保持不变

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
            LODOP.SET_PRINT_STYLEA(0, "MarginBottom", "15mm"); // 调整下边距
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
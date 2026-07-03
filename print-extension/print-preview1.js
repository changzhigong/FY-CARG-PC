// 解析URL参数
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const data = params.get('data');
    const transferNos = params.get('transferNos');
    
    return {
        data: data ? JSON.parse(decodeURIComponent(data)) : [],
        transferNos: transferNos ? JSON.parse(decodeURIComponent(transferNos)) : []
    };
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

// 生成打印HTML
function generatePrintHTML(printData) {
  let html = '';
  
  printData.forEach((group, groupIndex) => {
    const header = group.headerInfo;
    const items = group.items;
    const transferType = header.transferType;
    const isPriceTransfer = transferType === 47171002 || transferType === '47171002';
    
    html += `
      <div class="print-page" id="print-page-${groupIndex}">
        <div class="print-header">
          <h2>调拨清单</h2>
        </div>
        
        <div class="header-info">
          <table class="info-table">
            <tr>
              <td style="width: 33%; text-align: left;">
                <strong>调出仓库：</strong>${header.removeWarehouseName || ''}
              </td>
              <td style="width: 33%; text-align: left;">
                <strong>调入仓库：</strong>${header.moveWarehouseName || ''}
              </td>
              <td style="width: 34%; text-align: left;">
                <strong>单据号：</strong>${header.transferNo || ''}
              </td>
            </tr>
            <tr>
              <td style="text-align: left;">
                <strong>开单人：</strong>${header.createdByName || ''}
              </td>
              <td style="text-align: left;">
                <strong>上架人：</strong>${header.onshelf_by || ''}
              </td>
              <td style="text-align: left;">
                <strong>摘要：</strong>${header.headRemark || ''}
              </td>
            </tr>
          </table>
        </div>
        
        <table class="print-table">
          <thead>
            <tr>
              <th style="width: 10%;">品牌</th>
              <th style="width: 25%;">产品名称</th>
              <th style="width: 8%;">分类</th>
              <th style="width: 13%;">产品编码</th>
              <th style="width: 15%;">入库库位</th>
              <th style="width: 10%;">入库数量</th>
              ${isPriceTransfer ? '<th style="width: 10%;">成本价</th>' : ''}
              ${isPriceTransfer ? '<th style="width: 10%;">加价率</th>' : ''}
              ${isPriceTransfer ? '<th style="width: 10%;">金额</th>' : ''}
            </tr>
          </thead>
          <tbody>
    `;
    
    items.forEach((item, index) => {
      const quantity = parseInt(item.inboundQuantity) || 0;
      const price = parseFloat(item.salesPrice) || 0;
      const rate = parseFloat(item.priceIncreaseRate) || 1;
      const amount = (quantity * price * rate).toFixed(2);
      
      html += `
            <tr>
              <td>${item.brandName || ''}</td>
              <td style="text-align: left;">${item.partName || ''}</td>
              <td>${getCategoryName(item.categoryTwo)}</td>
              <td>${item.partCode || ''}</td>
              <td>${item.inboundLocationNo || ''}</td>
              <td>${quantity}</td>
              ${isPriceTransfer ? `<td style="text-align: right;">${formatNumber(price)}</td>` : ''}
              ${isPriceTransfer ? `<td style="text-align: right;">${formatNumber(rate)}</td>` : ''}
              ${isPriceTransfer ? `<td style="text-align: right;">${formatNumber(amount)}</td>` : ''}
            </tr>
      `;
    });
    
    // 汇总行
    const colspan = isPriceTransfer ? '3' : '0';
    html += `
          </tbody>
          <tfoot>
            <tr class="summary-row">
              <td colspan="${isPriceTransfer ? '6' : '5'}"></td>
              <td colspan="${colspan}">
                <strong>合计数量：</strong>${formatNumber(header.totalNum)}
                ${isPriceTransfer ? `<br><strong>合计金额：</strong>${formatNumber(header.totalAmount)}` : ''}
              </td>
            </tr>
          </tfoot>
        </table>
        
        <div class="print-footer">
          <div>打印人：${header.userName || ''}</div>
          <div>打印时间：${header.currentDate || ''}</div>
        </div>
      </div>
    `;
  });
  
  return html;
}

// 获取分类名称（基于分类代码）
function getCategoryName(categoryCode) {
  const categoryMap = {
    '90921001': '前挡',
    '90921002': '后挡',
    '90921003': '门玻璃',
    '90921004': '天窗',
    '90921005': '角窗'
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

// 主函数 - 修改初始化部分
async function main() {
  const { data, transferNos } = getUrlParams();
  
  if (!data || data.length === 0) {
    document.getElementById('print-content').innerHTML = '<p style="text-align:center;padding:50px;">没有打印数据</p>';
    return;
  }
  
  // 格式化数据（按调拨单号分组）
  const printData = formatPrintData(data);
  
  // 生成HTML
  const printHTML = generatePrintHTML(printData);
  document.getElementById('print-content').innerHTML = printHTML;
  
  // 更新标题显示选中的调拨单数量
  const titleElement = document.querySelector('.print-header h2');
  if (titleElement) {
    titleElement.textContent = `调拨清单 (${printData.length}个调拨单)`;
  }
  
  // 初始化打印机选择
  try {
    const LODOP = await initCLodop();
    const printers = await getPrinterList(LODOP);
    
    const select = document.getElementById('printer-select');
    select.innerHTML = '';
    
    printers.forEach(printer => {
      const option = document.createElement('option');
      option.value = printer.value;
      option.textContent = printer.label;
      select.appendChild(option);
    });
    
    // 设置默认打印机
    const defaultPrinter = LODOP.GET_PRINTER_NAME(-1);
    const defaultOption = Array.from(select.options).find(
      opt => opt.textContent === defaultPrinter
    );
    if (defaultOption) {
      select.value = defaultOption.value;
    }
    
  } catch (error) {
    console.error('打印机初始化失败:', error);
    const select = document.getElementById('printer-select');
    select.innerHTML = '<option value="">无法获取打印机列表</option>';
  }
  
// 绑定按钮事件
document.getElementById('btn-close').addEventListener('click', () => {
    // 尝试多种关闭方式
  try {
    // 方式1：发送消息给父窗口
    window.parent.postMessage('close-print-preview', '*');
  } catch (error) {
    console.error('关闭预览窗口失败:', error);
    // 最后的备用方式
    window.close();
  }
});


  document.getElementById('btn-print').addEventListener('click', () => {
    const printerIndex = parseInt(document.getElementById('printer-select').value) || 0;
    doPrint(printerIndex);
  });
  
  console.log(`打印预览已加载: ${printData.length} 个调拨单`);
}

// 初始化CLodop打印
function initCLodop() {
  return new Promise((resolve, reject) => {
    try {
      // 直接使用本地的CLodop实现
      const LODOP = getLodop();
      if (LODOP) {
        resolve(LODOP);
      } else {
        reject(new Error('无法初始化打印控件'));
      }
    } catch (error) {
      reject(error);
    }
  });
}


// 获取打印机列表
async function getPrinterList(LODOP) {
    const printerList = [];
    const printerCount = LODOP.GET_PRINTER_COUNT();
    
    for (let i = 0; i < printerCount; i++) {
        const name = LODOP.GET_PRINTER_NAME(i);
        printerList.push({
            label: name,
            value: i
        });
    }
    
    return printerList;
}
// 打印函数 - 按调拨单分页打印
async function doPrint(printerIndex) {
  try {
    const LODOP = await initCLodop();
    
    if (!LODOP) {
      alert('CLodop打印控件未安装或未启动');
      return;
    }
    
    // 获取所有打印页面
    const pages = document.querySelectorAll('.print-page');
    
    // 初始化打印任务
    LODOP.PRINT_INIT('调拨单打印');
    
    // 设置打印机索引
    if (printerIndex !== undefined && printerIndex !== null) {
        LODOP.SET_PRINTER_INDEX(printerIndex);
    }
    
    // 设置页面大小
    LODOP.SET_PRINT_PAGESIZE(1, 0, 0, 'A4'); // 1-纵向打印，2-横向打印
    
    // 为每个页面添加打印内容
    pages.forEach((page, index) => {
      // 获取页面的HTML内容
      const pageHTML = page.outerHTML;
      
      // 设置打印区域
      if (index === 0) {
        // 第一页，添加整个页面内容
        LODOP.ADD_PRINT_HTM(10, 10, "100%", "100%", pageHTML);
      } else {
        // 后续页面，先创建新页面再添加内容
        LODOP.NEWPAGE();
        LODOP.ADD_PRINT_HTM(10, 10, "100%", "100%", pageHTML);
      }
    });
    
    // 直接打印，不显示预览
    LODOP.PRINT();
    
    console.log(`已发送 ${pages.length} 个调拨单到打印机`);
    
    // 显示成功消息
    showMessage(`成功发送 ${pages.length} 个调拨单到打印机`, 'success');

  } catch (error) {
    console.error('打印失败:', error);
    showMessage('打印失败: ' + error.message, 'error');
  }
}

// 添加消息提示函数
function showMessage(message, type = 'info') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `print-message print-message--${type}`;
  messageDiv.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    padding: 10px 20px;
    background-color: ${type === 'error' ? '#fef0f0' :
      type === 'success' ? '#f0f9eb' : '#edf2fc'};
    border: 1px solid ${type === 'error' ? '#fde2e2' :
      type === 'success' ? '#e1f3d8' : '#e4e7ed'};
    border-radius: 4px;
    color: ${type === 'error' ? '#f56c6c' :
      type === 'success' ? '#67c23a' : '#909399'};
    font-size: 14px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  `;

  messageDiv.innerHTML = message;
  document.body.appendChild(messageDiv);

  // 3秒后自动移除
  setTimeout(() => {
    if (messageDiv.parentNode) {
      messageDiv.parentNode.removeChild(messageDiv);
    }
  }, 3000);
}




// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', main);
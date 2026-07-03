// popup.js
document.addEventListener('DOMContentLoaded', function() {
    const statusDiv = document.getElementById('status');
    const refreshBtn = document.getElementById('refresh');
    
    // 检查当前页面状态
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const currentTab = tabs[0];
        if (currentTab.url.includes('xb.fy-carg.com')) {
            statusDiv.textContent = '已连接到ERP系统';
            statusDiv.className = 'status online';
        } else {
            statusDiv.textContent = '请在ERP系统页面使用';
            statusDiv.className = 'status offline';
        }
    });
    
    // 刷新按钮
    refreshBtn.addEventListener('click', function() {
        chrome.tabs.reload();
        window.close();
    });
});
(function() {
    'use strict';

    // 硬编码的拣货人和装箱人数据
    const HARD_CODED_EMPLOYEES = {
        6: {  // 郑州库
            pickers: [
                { name: "司林林", phone: "" },
                { name: "杜志航", phone: "" },
                { name: "连培几", phone: "" },
                { name: "闫慧超", phone: "" },
                { name: "滑明浩", phone: "" },
                { name: "化昌宁", phone: "" },
                { name: "闫中伟", phone: "" },
                { name: "闫英杰", phone: "" },
                { name: "吕超俊", phone: "" },
                { name: "闫风强", phone: "" },
                { name: "朱水仓", phone: "" },
                { name: "安现华", phone: "" },
                { name: "吕超永", phone: "" },
                { name: "吕超凡", phone: "" },
                { name: "吕瑞鹏", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "司林林", phone: "" },
                { name: "杜志航", phone: "" },
                { name: "连培几", phone: "" },
                { name: "闫慧超", phone: "" },
                { name: "滑明浩", phone: "" },
                { name: "化昌宁", phone: "" },
                { name: "闫中伟", phone: "" },
                { name: "闫英杰", phone: "" },
                { name: "吕超俊", phone: "" },
                { name: "闫风强", phone: "" },
                { name: "朱水仓", phone: "" },
                { name: "吕超永", phone: "" },
                { name: "吕超凡", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        7: {  // 西安库
            pickers: [
                { name: "李文强", phone: "" },
                { name: "高养国", phone: "" },
                { name: "朱静", phone: "" },
                { name: "党磊磊", phone: "" },
                { name: "许波", phone: "" },
                { name: "常平军", phone: "" },
                { name: "唐小峰", phone: "" },
                { name: "寻磊", phone: "" },
                { name: "徐平安", phone: "" },
                { name: "宋永飞", phone: "" },
                { name: "马爵前", phone: "" },
                { name: "高军安", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "李文强", phone: "" },
                { name: "高养国", phone: "" },
                { name: "朱静", phone: "" },
                { name: "党磊磊", phone: "" },
                { name: "许波", phone: "" },
                { name: "常平军", phone: "" },
                { name: "唐小峰", phone: "" },
                { name: "寻磊", phone: "" },
                { name: "徐平安", phone: "" },
                { name: "宋永飞", phone: "" },
                { name: "马爵前", phone: "" },
                { name: "高军安", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        8: {  // 兰州库
            pickers: [
                { name: "张增勇", phone: "" },
                { name: "魏孔德", phone: "" },
                { name: "杨世荣", phone: "" },
                { name: "王会勇", phone: "" },
                { name: "李亚红", phone: "" },
                { name: "张晶", phone: "" },
                { name: "陶正斌", phone: "" },
                { name: "李兴鹏", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "张增勇", phone: "" },
                { name: "魏孔德", phone: "" },
                { name: "杨世荣", phone: "" },
                { name: "王会勇", phone: "" },
                { name: "李亚红", phone: "" },
                { name: "张晶", phone: "" },
                { name: "陶正斌", phone: "" },
                { name: "李兴鹏", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        11: {  // 商丘库
            pickers: [
                { name: "郭佳", phone: "" },
                { name: "陈杰", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "郭佳", phone: "" },
                { name: "陈杰", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        9: {  // 驻马店库
            pickers: [
                { name: "曹小威", phone: "" },
                { name: "戚登阔", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "曹小威", phone: "" },
                { name: "戚登阔", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        12: {  // 洛阳库
            pickers: [
                { name: "理流通", phone: "" },
                { name: "李景现", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "理流通", phone: "" },
                { name: "李景现", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        16: {  // 银川库
            pickers: [
                { name: "洪建华", phone: "" },
                { name: "王俭", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "洪建华", phone: "" },
                { name: "王俭", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        10: {  // 茶城库
            pickers: [
                { name: "冯东亚", phone: "" },
                { name: "韦坚", phone: "" },
                { name: "陈雨雨", phone: "" },
                { name: "郎帅帅", phone: "" },
                { name: "张亮亮", phone: "" },
                { name: "田兴", phone: "" },
                { name: "代鹏程", phone: "" },
                { name: "朱水仓", phone: "" },
                { name: "安现华", phone: "" },
                { name: "吕超永", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "陈雨雨", phone: "" },
                { name: "郎帅帅", phone: "" },
                { name: "朱水仓", phone: "" },
                { name: "吕超永", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        },
        18: {  // 西安西郊库
            pickers: [
                { name: "李文强", phone: "" },
                { name: "宋永飞", phone: "" }
            ],
            packers: [
                { name: "李文强", phone: "" },
                { name: "宋永飞", phone: "" }
            ]
        },
        15: {  // 榆林库
            pickers: [
                { name: "司睿峰", phone: "" },
                { name: "高君安", phone: "" },
                { name: "公共账号", phone: "" }
            ],
            packers: [
                { name: "司睿峰", phone: "" },
                { name: "高君安", phone: "" },
                { name: "公共账号", phone: "" }
            ]
        }
    };

    const GM = {
        xmlhttpRequest: function(details) {
            return new Promise((resolve, reject) => {
                const requestId = Date.now() + Math.random();
                
                const responseHandler = function(event) {
                    if (event.source !== window) return;
                    if (event.data.type === 'ERP_AUTOMATION_RESPONSE' && event.data.requestId === requestId) {
                        window.removeEventListener('message', responseHandler);
                        
                        if (event.data.error) {
                            if (details.onerror) details.onerror(event.data.error);
                            reject(event.data.error);
                        } else {
                            const response = {
                                responseText: event.data.data,
                                status: event.data.status || 200,
                                finalUrl: details.url
                            };
                            if (details.onload) details.onload(response);
                            resolve(response);
                        }
                    }
                };
                
                window.addEventListener('message', responseHandler);
                
                window.postMessage({
                    type: 'ERP_AUTOMATION_REQUEST',
                    action: 'GM_xmlhttpRequest',
                    requestId: requestId,
                    url: details.url,
                    method: details.method,
                    headers: details.headers,
                    data: details.data
                }, '*');
            });
        },
        
        setValue: function(key, value) {
            window.postMessage({
                type: 'ERP_AUTOMATION_REQUEST',
                action: 'GM_setValue',
                key: key,
                value: value
            }, '*');
        },
        
        getValue: function(key, defaultValue) {
            return new Promise((resolve) => {
                const requestId = Date.now() + Math.random();
                
                const responseHandler = function(event) {
                    if (event.source !== window) return;
                    if (event.data.type === 'ERP_AUTOMATION_RESPONSE' && event.data.requestId === requestId) {
                        window.removeEventListener('message', responseHandler);
                        resolve(event.data.data !== undefined ? event.data.data : defaultValue);
                    }
                };
                
                window.addEventListener('message', responseHandler);
                
                window.postMessage({
                    type: 'ERP_AUTOMATION_REQUEST',
                    action: 'GM_getValue',
                    requestId: requestId,
                    key: key
                }, '*');
            });
        },

        notification: function (details) {
            try {
                window.postMessage({
                    type: 'ERP_AUTOMATION_REQUEST',
                    action: 'GM_notification',
                    title: details.title,
                    text: details.text
                }, '*');
            } catch (error) {
                console.error('发送通知请求时出错:', error);
                console.log(`[通知] ${details.title || 'ERP自动化'}: ${details.text}`);
            }
        },
        
        addStyle: function(css) {
            const style = document.createElement('style');
            style.textContent = css;
            document.head.appendChild(style);
        }
    };
    window.GM_xmlhttpRequest = GM.xmlhttpRequest;
    window.GM_setValue = GM.setValue;
    window.GM_getValue = GM.getValue;
    window.GM_notification = GM.notification;
    window.GM_addStyle = GM.addStyle;

    
    /**
     * 自定义模态框类 - 替代原生 confirm()
     * 支持完整数据显示，无字符数限制
     */
    class CustomModal {
        constructor(title, content) {
            this.title = title;
            this.content = content;
            this.promise = null;
            this.modal = null;
            this.overlay = null;
            this.createModal();
        }

        createModal() {
            // 创建遮罩层
            this.overlay = document.createElement('div');
            this.overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                z-index: 999999;
                display: none;
                align-items: center;
                justify-content: center;
            `;

            // 创建模态框容器
            this.modal = document.createElement('div');
            this.modal.style.cssText = `
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                max-width: 900px;
                max-height: 80vh;
                width: 90vw;
                display: flex;
                flex-direction: column;
                animation: modalFadeIn 0.3s ease-out;
            `;

            // 创建标题栏
            const header = document.createElement('div');
            header.style.cssText = `
                padding: 16px 20px;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 8px 8px 0 0;
                color: white;
            `;
            header.innerHTML = `
                <h2 style="margin: 0; font-size: 18px; font-weight: 600;">${this.title}</h2>
                <button id="modal-close-x" style="
                    background: none;
                    border: none;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    padding: 0;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: background 0.2s;
                ">&times;</button>
            `;

            // 创建内容区域
            const contentArea = document.createElement('div');
            contentArea.style.cssText = `
                padding: 20px;
                overflow-y: auto;
                max-height: calc(80vh - 120px);
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.6;
                color: #1f2937;
                word-wrap: break-word;
                white-space: pre-wrap;
            `;
            contentArea.innerHTML = this.content;

            // 创建按钮区域
            const footer = document.createElement('div');
            footer.style.cssText = `
                padding: 16px 20px;
                border-top: 1px solid #e5e7eb;
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                background: #f8f9fa;
                border-radius: 0 0 8px 8px;
            `;

            const cancelBtn = document.createElement('button');
            cancelBtn.id = 'modal-cancel-btn';
            cancelBtn.textContent = '取消';
            cancelBtn.style.cssText = `
                padding: 10px 24px;
                font-size: 14px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                background: white;
                color: #6b7280;
                border: 1px solid #d1d5db;
            `;
            cancelBtn.onmouseover = () => {
                cancelBtn.style.backgroundColor = '#f3f4f6';
                cancelBtn.style.color = 'white';
            };
            cancelBtn.onmouseout = () => {
                cancelBtn.style.backgroundColor = 'white';
                cancelBtn.style.color = '#6b7280';
            };

            const confirmBtn = document.createElement('button');
            confirmBtn.id = 'modal-confirm-btn';
            confirmBtn.textContent = '确认';
            confirmBtn.style.cssText = `
                padding: 10px 24px;
                font-size: 14px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: 500;
            `;
            confirmBtn.onmouseover = () => {
                confirmBtn.style.transform = 'translateY(-2px)';
                confirmBtn.style.boxShadow = '0 6px 12px rgba(102, 126, 234, 0.4)';
            };
            confirmBtn.onmouseout = () => {
                confirmBtn.style.transform = 'translateY(0)';
                confirmBtn.style.boxShadow = '0 4px 6px rgba(102, 126, 234, 0.3)';
            };

            footer.appendChild(cancelBtn);
            footer.appendChild(confirmBtn);
            this.modal.appendChild(header);
            this.modal.appendChild(contentArea);
            this.modal.appendChild(footer);

            // 添加动画样式
            const style = document.createElement('style');
            style.textContent = `
                @keyframes modalFadeIn {
                    from {
                        opacity: 0;
                        transform: scale(0.9);
                    }
                    to {
                        opacity: 1;
                        transform: scale(1);
                    }
                }
                @keyframes modalFadeOut {
                    from {
                        opacity: 1;
                        transform: scale(1);
                    }
                    to {
                        opacity: 0;
                        transform: scale(0.9);
                    }
                }
                /* 滚动条样式 */
                .modal-container::-webkit-scrollbar {
                    width: 8px;
                }
                .modal-container::-webkit-scrollbar-track {
                    background: #f1f1f1;
                }
                .modal-container::-webkit-scrollbar-thumb {
                    background: #c1c1c1;
                    border-radius: 4px;
                }
                .modal-container::-webkit-scrollbar-thumb:hover {
                    background: #a8a29e;
                }
            `;
            document.head.appendChild(style);

            // 将模态框添加到遮罩层
            this.overlay.appendChild(this.modal);
            // 将遮罩层添加到document.body
            document.body.appendChild(this.overlay);

            // 延迟绑定事件监听器，确保 DOM 元素已完全插入
            setTimeout(() => {
                // 绑定事件
                this.overlay.addEventListener('click', (e) => {
                    if (e.target === this.overlay) {
                        this.cancel();
                    }
                });

                const closeXBtn = document.getElementById('modal-close-x');
                if (closeXBtn) {
                    closeXBtn.addEventListener('click', () => {
                        this.cancel();
                    });
                }

                const cancelBtn = document.getElementById('modal-cancel-btn');
                if (cancelBtn) {
                    cancelBtn.addEventListener('click', () => {
                        this.cancel();
                    });
                }

                const confirmBtn = document.getElementById('modal-confirm-btn');
                if (confirmBtn) {
                    confirmBtn.addEventListener('click', () => {
                        this.confirm();
                    });
                }

                // 保存keydown事件处理器引用
                this.keydownHandler = (e) => {
                    if (e.key === 'Escape') {
                        this.cancel();
                    }
                };
                document.addEventListener('keydown', this.keydownHandler);
            }, 10);
        }

        show() {
            this.promise = new Promise((resolve) => {
                this.resolve = resolve;
            });
            this.overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            return this.promise;
        }

        hide() {
            this.modal.style.animation = 'modalFadeOut 0.2s ease-out forwards';
            setTimeout(() => {
                this.overlay.style.display = 'none';
                this.overlay.remove();
                this.modal.remove();
                document.body.style.overflow = '';
                // 移除keydown事件监听器，防止内存泄漏
                if (this.keydownHandler) {
                    document.removeEventListener('keydown', this.keydownHandler);
                    this.keydownHandler = null;
                }
            }, 200);
        }

        confirm() {
            this.hide();
            if (this.resolve) {
                this.resolve(true);
            }
        }

        cancel() {
            this.hide();
            if (this.resolve) {
                this.resolve(false);
            }
        }
    }

    class StableVueERPAutomation {
        constructor() {
            this.isRunning = false;
            this.currentPage = 'unknown';
            this.observer = null;
            this.panelInjected = false;
            this.lastInjectionTime = 0;
            this.keyboardHandler = null;
            this.panelState = 'normal';
            this.batchInfoWindow = null;
            this.batchProcessing = false;
            this.currentBatchIndex = 0;
            this.selectedOrders = [];
            this.batchSettings = {};
            this.transferInButtonInjected = false; // 添加调拨入库按钮注入状态
            this.apiData = {
                pickers: [],
                packers: [],
                boxes: [],
                vehicles: [],
                drivers: [],
                warehouses: [] // 添加仓库数据
            };
            this.pageButtonInjected = false;
            this.lastButtonCheckTime = 0;
            this.pageButtonLock = false;
            this.transferInButtonLock = false;
            this.init();
        }
        init() {
            console.log('🚀 稳定的Vue ERP自动化系统开始初始化');
            this.waitForStableVueApp().then(() => {
                console.log('✅ Vue应用已稳定加载');
                this.startStableAutomation();
            }).catch((error) => {
                console.log('⚠️ Vue应用等待超时，尝试直接启动:', error);
                this.startStableAutomation();
            });
            this.setupStableRouterListener();
        }
        waitForStableVueApp() {
            return new Promise((resolve, reject) => {
                const maxWaitTime = 15000; // 延长等待时间
                const startTime = Date.now();
                let stableCount = 0;
                const requiredStableCount = 3; // 需要连续稳定3次

                const checkStability = () => {
                    const hasVueApp = document.querySelector('#app') ||
                                     document.querySelector('[data-vue-app]') ||
                                     document.querySelector('[v-if], [v-for], [v-model]');

                    if (hasVueApp) {
                        stableCount++;
                        console.log(`✅ Vue应用稳定检测 ${stableCount}/${requiredStableCount}`);
                    } else {
                        stableCount = 0;
                    }

                    if (stableCount >= requiredStableCount) {
                        resolve();
                        return;
                    }

                    if (Date.now() - startTime > maxWaitTime) {
                        reject(new Error('Vue应用稳定检测超时'));
                        return;
                    }
                    setTimeout(checkStability, 1000);
                };

                checkStability();
            });
        }
        // setupStableRouterListener() {
        //     let lastRoute = window.location.href;
        //     const isTargetPage = (url) => {
        //         const isPickingPage = url.includes('/part/warehouse/outboundManagement/pickingListQuery/') && 
        //                             url.includes('menuId=501202');
        //         const isTransferInPage = url.includes('/part/warehouse/transferInbound/index') && 
        //                                 url.includes('menuId=501304');
                
        //         return {
        //             isPickingPage,
        //             isTransferInPage,
        //             isAnyTargetPage: isPickingPage || isTransferInPage
        //         };
        //     };           
        //     const handleRouteChange = () => {
        //         const newRoute = window.location.href;
        //         if (lastRoute !== newRoute) {
        //             const lastPageType = isTargetPage(lastRoute);
        //             const currentPageType = isTargetPage(newRoute);
        //             if (!lastPageType.isPickingPage && currentPageType.isPickingPage) {
        //                 console.log('🔄 检测到从其他页面切换到拣货管理页面，执行检测');
        //                 setTimeout(() => {
        //                     this.detectCurrentPage();
        //                     this.injectControlPanel();
        //                     this.injectPageBatchButton();
        //                 }, 500);
        //             } else if (lastPageType.isPickingPage && !currentPageType.isPickingPage) {
        //                 console.log('🔄 从拣货管理页面切换到其他页面，清理状态');
        //                 this.cleanupPickingPage();
        //             }
        //             if (!lastPageType.isTransferInPage && currentPageType.isTransferInPage) {
        //                 console.log('🔄 检测到从其他页面切换到调拨入库页面，执行检测');
        //                 setTimeout(() => {
        //                     this.detectCurrentPage();  // 使用统一的页面检测方法
        //                     this.injectControlPanel();  // 添加这行，注入控制面板
        //                     this.injectTransferInBatchButton();
        //                 }, 500);
        //             } else if (lastPageType.isTransferInPage && !currentPageType.isTransferInPage) {
        //                 console.log('🔄 从调拨入库页面切换到其他页面，清理状态');
        //                 this.cleanupTransferInPage();
        //             }
                    
        //             lastRoute = newRoute;
        //         }
        //     };  
        //     window.addEventListener('hashchange', handleRouteChange);
        //     window.addEventListener('popstate', handleRouteChange);
        //     this.observeSimpleRouteChanges(handleRouteChange);
        //     setTimeout(() => {
        //         handleRouteChange();
        //     }, 1000);
        // }

        setupStableRouterListener() {
            let lastRoute = window.location.href;
            const isTargetPage = (url) => {
                const isPickingPage = url.includes('/part/warehouse/outboundManagement/pickingListQuery/') && 
                                    url.includes('menuId=501202');
                const isTransferInPage = url.includes('/part/warehouse/transferInbound/index') && 
                                        url.includes('menuId=501304');
                
                return {
                    isPickingPage,
                    isTransferInPage,
                    isAnyTargetPage: isPickingPage || isTransferInPage
                };
            };           
            const handleRouteChange = () => {
                const newRoute = window.location.href;
                if (lastRoute !== newRoute) {
                    console.log('🔄 检测到路由变化:', { from: lastRoute, to: newRoute });
                    const lastPageType = isTargetPage(lastRoute);
                    const currentPageType = isTargetPage(newRoute);
                    
                    if (!lastPageType.isPickingPage && currentPageType.isPickingPage) {
                        console.log('🔄 检测到从其他页面切换到拣货管理页面，执行检测');
                        setTimeout(() => {
                            this.detectCurrentPage();
                            this.injectControlPanel();
                            this.injectPageBatchButton();
                        }, 500);
                    } else if (lastPageType.isPickingPage && !currentPageType.isPickingPage) {
                        console.log('🔄 从拣货管理页面切换到其他页面，清理状态');
                        this.cleanupPickingPage();
                    }
                    
                    if (!lastPageType.isTransferInPage && currentPageType.isTransferInPage) {
                        console.log('🔄 检测到从其他页面切换到调拨入库页面，执行检测');
                        setTimeout(() => {
                            this.detectCurrentPage();  // 使用统一的页面检测方法
                            this.injectControlPanel();  // 添加这行，注入控制面板
                            this.injectTransferInBatchButton();
                        }, 500);
                    } else if (lastPageType.isTransferInPage && !currentPageType.isTransferInPage) {
                        console.log('🔄 从调拨入库页面切换到其他页面，清理状态');
                        this.cleanupTransferInPage();
                    }
                    
                    lastRoute = newRoute;
                } else {
                    // 即使URL没有变化，也要检查页面类型是否发生变化
                    this.detectCurrentPage();
                    this.injectControlPanel();
                }
            };  
            
            // 增强路由监听
            window.addEventListener('hashchange', handleRouteChange);
            window.addEventListener('popstate', handleRouteChange);
            
            // // 增强pushState和replaceState的监听
            // const originalPushState = history.pushState;
            // const originalReplaceState = history.replaceState;
            
            // history.pushState = function() {
            //     originalPushState.apply(history, arguments);
            //     setTimeout(handleRouteChange, 0);
            // };
            
            // history.replaceState = function() {
            //     originalReplaceState.apply(history, arguments);
            //     setTimeout(handleRouteChange, 0);
            // };
            
            // 保持原有的简单路由变化检查
            this.observeSimpleRouteChanges(handleRouteChange);
            
            // 页面加载完成后立即检测一次
            setTimeout(() => {
                handleRouteChange();
            }, 1000);
        }

        // setupStableRouterListener() {
        //     let lastRoute = window.location.href;
        //     const isTargetPage = (url) => {
        //         const isPickingPage = url.includes('/part/warehouse/outboundManagement/pickingListQuery/') && 
        //                             url.includes('menuId=501202');
        //         const isTransferInPage = url.includes('/part/warehouse/transferInbound/index') && 
        //                                 url.includes('menuId=501304');
                
        //         return {
        //             isPickingPage,
        //             isTransferInPage,
        //             isAnyTargetPage: isPickingPage || isTransferInPage
        //         };
        //     };    
            
        //     const handleRouteChange = () => {
        //         // 批量处理期间完全禁用路由检测
        //         if (this.batchProcessing) {
        //             return;
        //         }
                
        //         const newRoute = window.location.href;
        //         const lastPageType = isTargetPage(lastRoute);
        //         const currentPageType = isTargetPage(newRoute);
                
        //         if (lastRoute !== newRoute) {
        //             console.log('🔄 检测到路由变化:', { from: lastRoute, to: newRoute });
                    
        //             if (!lastPageType.isPickingPage && currentPageType.isPickingPage) {
        //                 console.log('🔄 检测到从其他页面切换到拣货管理页面，执行检测');
        //                 setTimeout(() => {
        //                     this.detectCurrentPage();
        //                     this.injectControlPanel();
        //                     this.injectPageBatchButton();
        //                 }, 500);
        //             } else if (lastPageType.isPickingPage && !currentPageType.isPickingPage) {
        //                 console.log('🔄 从拣货管理页面切换到其他页面，清理状态');
        //                 this.cleanupPickingPage();
        //             }
                    
        //             if (!lastPageType.isTransferInPage && currentPageType.isTransferInPage) {
        //                 console.log('🔄 检测到从其他页面切换到调拨入库页面，执行检测');
        //                 setTimeout(() => {
        //                     this.detectCurrentPage();
        //                     this.injectControlPanel();
        //                     this.injectTransferInBatchButton();
        //                 }, 500);
        //             } else if (lastPageType.isTransferInPage && !currentPageType.isTransferInPage) {
        //                 console.log('🔄 从调拨入库页面切换到其他页面，清理状态');
        //                 this.cleanupTransferInPage();
        //             }
                    
        //             lastRoute = newRoute;
        //         }
        //     };  
            
        //     // 使用更轻量级的路由监听方式，避免重写原生方法
        //     window.addEventListener('hashchange', handleRouteChange);
        //     window.addEventListener('popstate', handleRouteChange);
            
        //     // 不再重写 pushState 和 replaceState，改用定时检查的方式
        //     this.routeCheckInterval = setInterval(() => {
        //         // 批量处理期间不检查路由
        //         if (this.batchProcessing) {
        //             return;
        //         }
                
        //         const currentRoute = window.location.href;
        //         if (lastRoute !== currentRoute) {
        //             lastRoute = currentRoute;
        //             handleRouteChange();
        //         }
        //     }, 1000); // 每秒检查一次
            
        //     // 页面加载完成后立即检测一次
        //     setTimeout(() => {
        //         handleRouteChange();
        //     }, 1000);
        // }

        observeSimpleRouteChanges(handleRouteChange) {
            let lastUrl = window.location.href;
            const checkInterval = setInterval(() => {
                const currentUrl = window.location.href;
                if (currentUrl !== lastUrl) {
                    lastUrl = currentUrl;
                    console.log('🔄 检测到SPA路由变化');
                    handleRouteChange();
                }
            }, 1000);
            this.routeCheckInterval = checkInterval;
        }

        cleanupTransferInPage() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (panel) {
                panel.remove();
                this.panelInjected = false;
            }
            const batchButton = document.getElementById('batch-receive-btn');
            if (batchButton) {
                batchButton.remove();
                this.transferInButtonInjected = false;
            }
            this.currentPage = 'unknown';
            
            console.log('✅ 调拨入库页面相关资源已清理');
        }

        // cleanupTransferInPage() {
        //     // 清理定时器
        //     if (this.routeCheckInterval) {
        //         clearInterval(this.routeCheckInterval);
        //         this.routeCheckInterval = null;
        //     }
            
        //     // 断开DOM观察器
        //     if (this.observer) {
        //         this.observer.disconnect();
        //         this.observer = null;
        //     }
            
        //     const panel = document.getElementById('stable-erp-automation-panel');
        //     if (panel) {
        //         panel.remove();
        //         this.panelInjected = false;
        //     }
        //     const batchButton = document.getElementById('batch-receive-btn');
        //     if (batchButton) {
        //         batchButton.remove();
        //         this.transferInButtonInjected = false;
        //     }
        //     this.currentPage = 'unknown';
            
        //     console.log('✅ 调拨入库页面相关资源已清理');
        // }

        // injectTransferInBatchButton() {
        //     if (this.transferInButtonLock) {
        //         console.log('ℹ️ 调拨入库页面按钮注入正在执行中，跳过重复执行');
        //         return;
        //     }
        //     this.transferInButtonLock = true;
        //     try {
        //         if (this.transferInButtonInjected || document.getElementById('batch-receive-btn')) {
        //             console.log('✅ 批量签收按钮已存在，跳过注入');
        //             return;
        //         }
        //         if (!location.href.includes('/part/warehouse/transferInbound/index') || 
        //             !location.href.includes('menuId=501304')) {
        //             return;
        //         }
        //         const btnGroup = document.querySelector('.tableHead .btnGroup .el-button-group');
        //         if (!btnGroup) {
        //             console.log('❌ 未找到按钮组容器，等待重试');
        //             setTimeout(() => this.injectTransferInBatchButton(), 1000);
        //             return;
        //         }
        //         const batchReceiveButton = document.createElement('button');
        //         batchReceiveButton.id = 'batch-receive-btn';
        //         batchReceiveButton.type = 'button';
        //         batchReceiveButton.className = 'el-button el-button--primary el-button--mini';
        //         batchReceiveButton.innerHTML = '<i class="el-icon-check"></i><span>批量签收</span>';
        //         batchReceiveButton.addEventListener('click', () => {
        //             this.handleBatchReceive();
        //         });
        //         const printPreviewButton = btnGroup.querySelector('button:last-child');
        //         if (printPreviewButton) {
        //             btnGroup.insertBefore(batchReceiveButton, printPreviewButton.nextSibling);
        //             this.transferInButtonInjected = true;
        //             console.log('✅ 批量签收按钮已注入到打印预览按钮后面');
        //         } else {
        //             btnGroup.appendChild(batchReceiveButton);
        //             this.transferInButtonInjected = true;
        //             console.log('✅ 批量签收按钮已注入到按钮组末尾');
        //         }
        //     } catch (error) {
        //         console.error('注入批量签收按钮时出错:', error);            
        //     } finally {
        //         setTimeout(() => {
        //             this.transferInButtonLock = false;
        //         }, 1000);
        //     }
        // }

        // 在injectTransferInBatchButton方法中添加月结批量入库按钮
        injectTransferInBatchButton() {
            if (this.transferInButtonLock) {
                console.log('ℹ️ 调拨入库页面按钮注入正在执行中，跳过重复执行');
                return;
            }
            this.transferInButtonLock = true;
            try {
                // 检查是否已经注入了按钮（任何一个存在就认为已注入）
                const batchReceiveButtonExists = document.getElementById('batch-receive-btn');
                const monthlyBatchStoreInButtonExists = document.getElementById('monthly-batch-store-in-btn');
                
                if (batchReceiveButtonExists && monthlyBatchStoreInButtonExists) {
                    console.log('✅ 调拨入库页面按钮已存在，跳过注入');
                    this.transferInButtonInjected = true;
                    return;
                }
                
                // 如果只有一个按钮存在，也认为有问题，重新注入
                if (batchReceiveButtonExists || monthlyBatchStoreInButtonExists) {
                    console.log('⚠️ 检测到按钮状态不一致，重新注入所有按钮');
                    if (batchReceiveButtonExists) {
                        batchReceiveButtonExists.remove();
                    }
                    if (monthlyBatchStoreInButtonExists) {
                        monthlyBatchStoreInButtonExists.remove();
                    }
                }
                if (!location.href.includes('/part/warehouse/transferInbound/index') || 
                    !location.href.includes('menuId=501304')) {
                    return;
                }
                const btnGroup = document.querySelector('.tableHead .btnGroup .el-button-group');
                if (!btnGroup) {
                    console.log('❌ 未找到按钮组容器，等待重试');
                    setTimeout(() => this.injectTransferInBatchButton(), 1000);
                    return;
                }
                
                // 批量签收按钮
                const batchReceiveButton = document.createElement('button');
                batchReceiveButton.id = 'batch-receive-btn';
                batchReceiveButton.type = 'button';
                batchReceiveButton.className = 'el-button el-button--primary el-button--mini';
                batchReceiveButton.innerHTML = '<i class="el-icon-check"></i><span>批量签收</span>';
                batchReceiveButton.addEventListener('click', () => {
                    this.handleBatchReceive();
                });
                
                // 月结批量入库按钮
                const monthlyBatchStoreInButton = document.createElement('button');
                monthlyBatchStoreInButton.id = 'monthly-batch-store-in-btn';
                monthlyBatchStoreInButton.type = 'button';
                monthlyBatchStoreInButton.className = 'el-button el-button--success el-button--mini';
                monthlyBatchStoreInButton.innerHTML = '<i class="el-icon-shopping-bag-1"></i><span>月结批量入库</span>';
                monthlyBatchStoreInButton.addEventListener('click', () => {
                    this.handleMonthlyBatchStoreIn();
                });
                
                const printPreviewButton = btnGroup.querySelector('button:last-child');
                if (printPreviewButton) {
                    btnGroup.insertBefore(batchReceiveButton, printPreviewButton.nextSibling);
                    btnGroup.insertBefore(monthlyBatchStoreInButton, batchReceiveButton.nextSibling);
                    this.transferInButtonInjected = true;
                    console.log('✅ 批量签收和月结批量入库按钮已注入到打印预览按钮后面');
                } else {
                    btnGroup.appendChild(batchReceiveButton);
                    btnGroup.appendChild(monthlyBatchStoreInButton);
                    this.transferInButtonInjected = true;
                    console.log('✅ 批量签收和月结批量入库按钮已注入到按钮组末尾');
                }
            } catch (error) {
                console.error('注入调拨入库页面按钮时出错:', error);            
            } finally {
                setTimeout(() => {
                    this.transferInButtonLock = false;
                }, 1000);
            }
        }

        // 实现月结批量入库逻辑
        async handleMonthlyBatchStoreIn() {
            try {
                // 检查是否为月末最后一天
                if (!this.isLastDayOfMonth()) {
                    const confirmContinue = confirm('当前日期不是月末最后一天，确定要执行月结批量入库操作吗？\n点击"确定"继续，点击"取消"中止操作。');
                    if (!confirmContinue) {
                        this.updateStatus('月结批量入库操作已取消', 'waiting');
                        return;
                    }
                }
                console.log('🔄 开始月结批量入库流程');
                this.updateStatus('正在处理月结批量入库...', 'running');
                
                // 获取待上架的调拨单
                const selectedOrders = await this.getMonthlyStoreInOrders();
                
                if (!selectedOrders || selectedOrders.length === 0) {
                    this.updateStatus('未找到待上架的调拨单', 'error');
                    GM_notification({
                        title: '月结批量入库',
                        text: '未找到待上架的调拨单'
                    });
                    return;
                }
                
                console.log(`✅ 找到 ${selectedOrders.length} 个待上架的调拨单`);
                let successCount = 0;
                let failCount = 0;
                
                for (let i = 0; i < selectedOrders.length; i++) {
                    const order = selectedOrders[i];
                    try {
                        console.log(`🔄 开始处理第 ${i + 1}/${selectedOrders.length} 个调拨单: ${order.transferNumber}`);
                        await this.processMonthlyStoreIn(order);
                        successCount++;
                        console.log(`✅ 调拨单 ${order.transferNumber} 月结入库成功`);
                    } catch (error) {
                        failCount++;
                        console.error(`❌ 调拨单 ${order.transferNumber} 月结入库失败:`, error);
                    }
                }
                
                this.updateStatus(`月结批量入库完成: 成功 ${successCount} 个，失败 ${failCount} 个`, 'normal');
                GM_notification({
                    title: '月结批量入库完成',
                    text: `成功 ${successCount} 个，失败 ${failCount} 个`
                });
                
            } catch (error) {
                console.error('❌ 月结批量入库过程中出错:', error);
                this.updateStatus(`月结批量入库失败: ${error.message}`, 'error');
                GM_notification({
                    title: '月结批量入库失败',
                    text: error.message
                });
            }
        }

        // 获取待上架的调拨单
        async getMonthlyStoreInOrders() {
            console.log('🔍 获取待上架的调拨单...');
            
            const selectedOrders = [];
            const table = document.querySelector('.el-table__body') ||
                        document.querySelector('.el-table') ||
                        document.querySelector('table');
            
            if (!table) {
                console.error('❌ 未找到调拨单表格');
                throw new Error('未找到调拨单表格');
            }
            
            const rows = table.querySelectorAll('tbody tr');
            console.log(`找到 ${rows.length} 行数据`);
            
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const checkbox = row.querySelector('.el-checkbox input[type="checkbox"]');
                const cells = row.querySelectorAll('td');
                const status = cells[9]?.textContent?.trim();
                
                // 只选择待上架状态的调拨单
                if (status === '待上架' && checkbox && checkbox.checked) {
                    const orderInfo = this.extractTransferOrderInfoFromRow(row, i);
                    if (orderInfo && orderInfo.storeInButton) {
                        selectedOrders.push(orderInfo);
                        console.log(`✅ 添加待上架的调拨单: ${orderInfo.transferNumber}`);
                    }
                }
            }
            
            console.log(`✅ 找到 ${selectedOrders.length} 个待上架的调拨单`);
            
            if (selectedOrders.length === 0) {
                throw new Error('未找到待上架的调拨单，请确保已选择状态为"待上架"的调拨单');
            }
            
            return selectedOrders;
        }

        // 处理单个调拨单的月结入库
        async processMonthlyStoreIn(order) {
            console.log(`🔍 处理调拨单 ${order.transferNumber} 的月结入库`);
            
            // 点击入库按钮
            await this.clickStoreInButton(order.storeInButton);
            await this.delay(1000); // 等待详情页面加载
            
            // 处理详情页面
            await this.handleStoreInDetailPage();
            await this.delay(1000); // 等待详情页面处理完成
        }

        // 点击入库按钮
        async clickStoreInButton(button) {
            if (!button) {
                throw new Error('未找到入库按钮');
            }
            if (button.disabled) {
                throw new Error('入库按钮不可用');
            }
            
            console.log('🔍 点击入库按钮');
            button.click();
            await this.delay(100);
        }

        // 处理入库详情页面
        async handleStoreInDetailPage() {
            console.log('🔍 处理入库详情页面');
            
            // 等待详情页面加载完成
            await this.waitForDetailPageLoad();
            
            // 填写库位填充信息
            await this.fillLocationInfo();
            
            // 点击确认按钮
            await this.clickConfirmLocationButton();
            // 选择上架人
            await this.selectOnShelfPerson();
            //点击返回按钮
            await this.clickReturnButtonInTransferInPage();
            await this.delay(300);
            // 点击入库按钮
            // await this.clickStoreInConfirmButton();
        }

        // 等待详情页面加载
        async waitForDetailPageLoad() {
            console.log('⏳ 等待详情页面加载...');
            const maxWaitTime = 5000;
            const startTime = Date.now();
            
            while (Date.now() - startTime < maxWaitTime) {
                const locationInput = document.querySelector('.el-select.search-input.el-select--small input[placeholder="请输入入库库位"]');
                const confirmButton = document.querySelector('.el-button-group button.el-button--primary');
                
                if (locationInput && confirmButton) {
                    console.log('✅ 详情页面加载完成');
                    return;
                }
                await this.delay(200);
            }
            
            throw new Error('详情页面加载超时');
        }

        // // 填写库位填充信息
        // async fillLocationInfo() {
        //     console.log('🔍 填写库位填充信息');
            
        //     // 找到库位填充输入框
        //     const locationInput = document.querySelector('.el-select.search-input.el-select--small input[placeholder="请输入入库库位"]');
        //     if (!locationInput) {
        //         throw new Error('未找到库位填充输入框');
        //     }
            
        //     // 输入"月结调拨未到"
        //     locationInput.value = '月结调拨未到';
        //     locationInput.dispatchEvent(new Event('input', { bubbles: true }));
            
        //     console.log('✅ 已填写库位填充信息: 月结调拨未到');
        //     await this.delay(500);
        // }
        // 填写库位填充信息
        async fillLocationInfo() {
            console.log('🔍 填写库位填充信息');
            
            // 更准确地定位库位填充输入框
            const locationInputContainer = document.querySelector('.tableHead .btnGroup .el-select.search-input');
            if (!locationInputContainer) {
                throw new Error('未找到库位填充区域');
            }
            
            const locationInput = locationInputContainer.querySelector('input[placeholder="请输入入库库位"]');
            if (!locationInput) {
                throw new Error('未找到库位填充输入框');
            }
            
            // 点击输入框以激活下拉菜单
            locationInput.click();
            await this.delay(300);
            
            // 输入"月结调拨未到"
            locationInput.value = '月结调拨未到';
            locationInput.dispatchEvent(new Event('input', { bubbles: true }));
            locationInput.dispatchEvent(new Event('change', { bubbles: true }));
            await this.delay(500);
            
            // 查找并点击下拉菜单中的匹配选项
            const dropdown = document.querySelector('.el-select-dropdown:not([style*="display: none"])');
            if (dropdown) {
                const options = dropdown.querySelectorAll('.el-select-dropdown__item');
                let targetOption = null;
                
                // 查找匹配的选项
                for (let option of options) {
                    const optionText = option.textContent?.trim();
                    if (optionText.includes('月结调拨未到')) {
                        targetOption = option;
                        break;
                    }
                }
                
                // 如果没找到精确匹配，尝试查找包含关键词的选项
                if (!targetOption) {
                    for (let option of options) {
                        const optionText = option.textContent?.trim();
                        if (optionText.includes('月结') || optionText.includes('未到')) {
                            targetOption = option;
                            console.log(`✅ 找到近似匹配选项: "${optionText}"`);
                            break;
                        }
                    }
                }
                
                if (targetOption) {
                    targetOption.click();
                    console.log('✅ 已选择下拉菜单中的选项');
                    await this.delay(300);
                } else {
                    console.log('⚠️ 未找到匹配的下拉选项，尝试直接输入');
                    // 如果没有找到匹配选项，则直接失焦以确认输入
                    locationInput.blur();
                }
            } else {
                console.log('⚠️ 未找到下拉菜单，尝试直接输入');
                // 如果没有下拉菜单，则直接失焦以确认输入
                locationInput.blur();
            }
            
            console.log('✅ 已填写库位填充信息: 月结调拨未到');
            await this.delay(500);
        }
        // 点击确认库位按钮
        async clickConfirmLocationButton() {
            console.log('🔍 点击确认库位按钮');
            
            // 更准确地定位确认按钮，基于库位填充区域内的按钮
            const locationSection = document.querySelector('.tableHead .btnGroup .el-select.search-input');
            if (!locationSection) {
                throw new Error('未找到库位填充区域');
            }
            
            // 在库位填充区域内查找确认按钮
            const confirmButton = locationSection.nextElementSibling?.querySelector('button');
            if (!confirmButton) {
                throw new Error('未找到确认按钮');
            }
            
            const buttonText = confirmButton.textContent?.trim();
            if (buttonText === '确认') {
                confirmButton.click();
                console.log('✅ 已点击确认按钮');
                await this.delay(1000); // 等待确认操作完成
            } else {
                console.log(`⚠️ 确认按钮文本为"${buttonText}"，跳过点击`);
                throw new Error(`确认按钮文本不匹配: "${buttonText}"`);
            }
        }

        // 选择上架人
        async selectOnShelfPerson() {
            console.log('🔍 选择上架人');
            
            try {
                // 查找上架人标签
                const onShelfLabel = Array.from(document.querySelectorAll('.el-form-item__label'))
                    .find(label => label.textContent && label.textContent.includes('上架人'));
                
                if (!onShelfLabel) {
                    console.log('⚠️ 未找到上架人标签');
                    return;
                }
                
                // 获取上架人表单项
                const onShelfFormItem = onShelfLabel.closest('.el-form-item');
                if (!onShelfFormItem) {
                    console.log('⚠️ 未找到上架人表单项');
                    return;
                }
                
                // 查找上架人下拉框
                const onShelfSelect = onShelfFormItem.querySelector('.el-select');
                if (!onShelfSelect) {
                    console.log('⚠️ 未找到上架人下拉框');
                    return;
                }
                
                // 点击上架人下拉框
                onShelfSelect.click();
                await this.delay(300);
                
                // 查找展开的下拉菜单
                const dropdowns = document.querySelectorAll('.el-select-dropdown');
                let targetDropdown = null;
                
                for (let dropdown of dropdowns) {
                    const style = window.getComputedStyle(dropdown);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        targetDropdown = dropdown;
                        break;
                    }
                }
                
                if (!targetDropdown) {
                    console.log('⚠️ 未找到展开的上架人下拉菜单');
                    return;
                }
                
                // 查找选项
                const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
                let publicAccountOption = null;
                
                // 查找"公共账号"选项
                for (let option of options) {
                    const optionText = option.textContent?.trim();
                    if (optionText.includes('公共账号')) {
                        publicAccountOption = option;
                        break;
                    }
                }
                
                // 如果没找到"公共账号"，则选择第一个选项
                if (!publicAccountOption && options.length > 0) {
                    publicAccountOption = options[0];
                    console.log(`⚠️ 未找到"公共账号"选项，选择第一个选项: ${publicAccountOption.textContent?.trim()}`);
                }
                
                if (publicAccountOption) {
                    publicAccountOption.click();
                    console.log(`✅ 已选择上架人: ${publicAccountOption.textContent?.trim()}`);
                    await this.delay(200);
                } else {
                    console.log('⚠️ 上架人下拉菜单中没有可用选项');
                }
                
                // 隐藏下拉菜单
                targetDropdown.style.display = 'none';
                await this.delay(100);
                
            } catch (error) {
                console.error('选择上架人时出错:', error);
            }
        }
        async clickReturnButtonInTransferInPage() {
            console.log('🔍 查找并点击调拨入库页面返回按钮');
            
            // 首先尝试在对话框底部查找返回按钮
            const dialogFooters = document.querySelectorAll('.dialog-footer');
            for (const footer of dialogFooters) {
                const buttons = footer.querySelectorAll('button');
                for (const button of buttons) {
                    const text = button.textContent?.trim();
                    if (text && text.includes('返回')) {
                        console.log('✅ 在对话框底部找到返回按钮，准备点击');
                        button.click();
                        console.log('✅ 点击了返回按钮');
                        await this.delay(500);
                        return true;
                    }
                }
            }
            
            // 如果在对话框底部没找到，尝试在其他地方查找
            const buttons = document.querySelectorAll('.el-button');
            for (const button of buttons) {
                const text = button.textContent?.trim();
                const hasReturnText = text && (text.includes('返回'));

                if (hasReturnText) {
                    console.log('✅ 找到带图标的返回按钮，准备点击');
                    button.click();
                    console.log('✅ 点击了返回按钮');
                    await this.delay(500);
                    return true;
                }
            }
            
            // 最后尝试仅通过文本内容查找
            for (const button of buttons) {
                const text = button.textContent?.trim();
                if (text && text.includes('返回')) {
                    console.log('✅ 通过文本找到返回按钮，准备点击');
                    button.click();
                    console.log('✅ 点击了返回按钮');
                    await this.delay(500);
                    return true;
                }
            }

            console.log('❌ 未找到返回按钮');
            return false;
        }
        // 点击入库 按钮
        async clickStoreInConfirmButton() {
            console.log('🔍 点击入库确认按钮');
            
            // 查找入库按钮（在对话框底部）
            const storeInButtons = document.querySelectorAll('.dialog-footer button.el-button--primary');
            for (let button of storeInButtons) {
                const buttonText = button.textContent?.trim();
                if (buttonText === '入库') {
                    button.click();
                    console.log('✅ 已点击入库按钮');
                    await this.delay(1500); // 等待入库操作完成
                    return;
                }
            }
            
            // 如果上面的方法找不到，尝试另一种方式
            const footer = document.querySelector('.el-dialog__footer');
            if (footer) {
                const buttons = footer.querySelectorAll('button');
                for (let button of buttons) {
                    const buttonText = button.textContent?.trim();
                    if (buttonText.includes('入库')) {
                        button.click();
                        console.log('✅ 已点击入库按钮');
                        await this.delay(1500);
                        return;
                    }
                }
            }
            
            throw new Error('未找到入库确认按钮');
        }
        async handleBatchReceive() {
            try {
                console.log('🔄 开始批量签收流程');
                this.updateStatus('正在处理批量签收...', 'running');
                const selectedOrders = await this.getSelectedTransferOrders();
                
                if (!selectedOrders || selectedOrders.length === 0) {
                    this.updateStatus('未找到选中的调拨单', 'error');
                    GM_notification({
                        title: '批量签收',
                        text: '请先选择要签收的调拨单'
                    });
                    return;
                }
                
                console.log(`✅ 找到 ${selectedOrders.length} 个选中的调拨单`);
                let successCount = 0;
                let failCount = 0;
                
                for (let i = 0; i < selectedOrders.length; i++) {
                    const order = selectedOrders[i];
                    try {
                        console.log(`🔄 开始处理第 ${i + 1}/${selectedOrders.length} 个调拨单: ${order.transferNumber}`);
                        await this.clickReceiveButton(order.receiveButton);
                        await this.delay(500);
                        await this.handleReceiveConfirmDialog();
                        await this.delay(500);
                        
                        successCount++;
                        console.log(`✅ 调拨单 ${order.transferNumber} 签收成功`);
                    } catch (error) {
                        failCount++;
                        console.error(`❌ 调拨单 ${order.transferNumber} 签收失败:`, error);
                    }
                }
                this.updateStatus(`批量签收完成: 成功 ${successCount} 个，失败 ${failCount} 个`, 'normal');
                GM_notification({
                    title: '批量签收完成',
                    text: `成功 ${successCount} 个，失败 ${failCount} 个`
                });
                
            } catch (error) {
                console.error('❌ 批量签收过程中出错:', error);
                this.updateStatus(`批量签收失败: ${error.message}`, 'error');
                GM_notification({
                    title: '批量签收失败',
                    text: error.message
                });
            }
        }
        async getSelectedTransferOrders() {
            console.log('🔍 获取选中的调拨单...');
            
            const selectedOrders = [];
            const table = document.querySelector('.el-table__body') ||
                        document.querySelector('.el-table') ||
                        document.querySelector('table');
            
            if (!table) {
                console.error('❌ 未找到调拨单表格');
                throw new Error('未找到调拨单表格');
            }
            const rows = table.querySelectorAll('tbody tr');
            console.log(`找到 ${rows.length} 行数据`);
            
            let selectedCount = 0;
            
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const checkbox = row.querySelector('.el-checkbox input[type="checkbox"]');
                if (checkbox && checkbox.checked) {
                    selectedCount++;
                    const orderInfo = this.extractTransferOrderInfoFromRow(row, i);
                    if (orderInfo && orderInfo.receiveButton) {
                        selectedOrders.push(orderInfo);
                        console.log(`✅ 添加选中的调拨单: ${orderInfo.transferNumber}`);
                    } else {
                        console.log(`⚠️ 调拨单信息不完整，跳过: 行 ${i + 1}`);
                    }
                }
            }
            
            console.log(`✅ 找到 ${selectedOrders.length} 个有效的选中调拨单（共 ${selectedCount} 个选中的行）`);
            
            if (selectedOrders.length === 0) {
                throw new Error('未找到有效的选中调拨单，请确保已选择调拨单且调拨单有签收按钮');
            }
            
            return selectedOrders;
        }
        // extractTransferOrderInfoFromRow(row, index) {
        //     try {
        //         const cells = row.querySelectorAll('td');
        //         console.log(`🔍 分析第 ${index + 1} 行，共 ${cells.length} 个单元格`);
                
        //         const orderInfo = {
        //             index: index,
        //             rowElement: row,
        //             checkbox: row.querySelector('.el-checkbox input[type="checkbox"]'),
        //             transferNumber: cells[3]?.textContent?.trim() || `调拨单-${index + 1}`,
        //             receiveButton: this.findReceiveButtonInRow(cells[2])
        //         };
                
        //         console.log(`✅ 提取调拨单信息: ${orderInfo.transferNumber}`, {
        //             hasCheckbox: !!orderInfo.checkbox,
        //             hasReceiveButton: !!orderInfo.receiveButton,
        //             checkboxChecked: orderInfo.checkbox?.checked
        //         });
                
        //         return orderInfo;
        //     } catch (error) {
        //         console.error('提取调拨单信息失败:', error);
        //         return null;
        //     }
        // }
        // 在extractTransferOrderInfoFromRow方法中添加入库按钮识别
        extractTransferOrderInfoFromRow(row, index) {
            try {
                const cells = row.querySelectorAll('td');
                console.log(`🔍 分析第 ${index + 1} 行，共 ${cells.length} 个单元格`);
                
                const orderInfo = {
                    index: index,
                    rowElement: row,
                    checkbox: row.querySelector('.el-checkbox input[type="checkbox"]'),
                    transferNumber: cells[3]?.textContent?.trim() || `调拨单-${index + 1}`,
                    receiveButton: this.findReceiveButtonInRow(cells[2]),
                    storeInButton: this.findStoreInButtonInRow(cells[2]), // 添加入库按钮
                    status: cells[9]?.textContent?.trim() // 获取状态信息
                };
                
                console.log(`✅ 提取调拨单信息: ${orderInfo.transferNumber}`, {
                    hasCheckbox: !!orderInfo.checkbox,
                    hasReceiveButton: !!orderInfo.receiveButton,
                    hasStoreInButton: !!orderInfo.storeInButton,
                    status: orderInfo.status,
                    checkboxChecked: orderInfo.checkbox?.checked
                });
                
                return orderInfo;
            } catch (error) {
                console.error('提取调拨单信息失败:', error);
                return null;
            }
        }

        // 查找入库按钮
        findStoreInButtonInRow(cell) {
            if (!cell) return null;
            const buttons = cell.querySelectorAll('.el-button');
            console.log(`🔍 在单元格中找到 ${buttons.length} 个按钮`);
            
            for (let button of buttons) {
                const buttonText = button.querySelector('span')?.textContent?.trim();
                if (buttonText === '入库') {
                    console.log('✅ 找到入库按钮');
                    return button;
                }
            }
            
            console.log('❌ 未找到入库按钮');
            return null;
        }
        findReceiveButtonInRow(cell) {
            if (!cell) return null;
            const buttons = cell.querySelectorAll('.el-button');
            console.log(`🔍 在单元格中找到 ${buttons.length} 个按钮`);
            
            for (let button of buttons) {
                const buttonText = button.querySelector('span')?.textContent?.trim();
                if (buttonText === '签收') {
                    console.log('✅ 找到签收按钮');
                    return button;
                }
            }
            
            console.log('❌ 未找到签收按钮');
            return null;
        }
        async clickReceiveButton(button) {
            if (!button) {
                throw new Error('未找到签收按钮');
            }
            if (button.disabled) {
                throw new Error('签收按钮不可用');
            }
            
            console.log('🔍 点击签收按钮');
            button.click();
            await this.delay(100);
        }
        async handleReceiveConfirmDialog() {
            console.log('🔍 检查签收确认对话框');
            await this.delay(300);
            const confirmButton = document.querySelector('.el-message-box__btns .el-button--primary') ||
                                document.querySelector('.el-dialog__footer .el-button--primary') ||
                                document.querySelector('button.el-button--primary');
            
            if (confirmButton) {
                const buttonText = confirmButton.textContent?.trim();
                console.log(`🔍 找到确认按钮: "${buttonText}"`);
                
                if (buttonText === '确定' || buttonText === '确认') {
                    console.log('✅ 点击确认按钮');
                    confirmButton.click();
                    await this.delay(300);
                }
            } else {
                console.log('ℹ️ 未找到确认对话框，可能不需要确认');
            }
        }
        // 在类中添加优化后的delay方法
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, Math.min(ms, 500))); // 限制最大等待时间
        }
        updateStatus(message, status = 'normal') {
            const statusElement = document.getElementById('automationStatus');
            if (statusElement) {
                statusElement.textContent = message;
                statusElement.className = `status-indicator status-${status}`;
            }
            console.log(`${status.toUpperCase()}: ${message}`);
        }
        cleanupPickingPage() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (panel) {
                panel.remove();
                this.panelInjected = false;
            }
            const pageButton = document.getElementById('page-batch-shipping-btn');
            if (pageButton) {
                pageButton.remove();
                this.pageButtonInjected = false;
            }
            this.currentPage = 'unknown';
            this.queryConditionsSetupCompleted = false;
            this.settingUpQueryConditions = false;

            console.log('✅ 拣货页面相关资源已清理');
        }

        // cleanupPickingPage() {
        //     // 清理定时器
        //     if (this.routeCheckInterval) {
        //         clearInterval(this.routeCheckInterval);
        //         this.routeCheckInterval = null;
        //     }
            
        //     // 断开DOM观察器
        //     if (this.observer) {
        //         this.observer.disconnect();
        //         this.observer = null;
        //     }
            
        //     const panel = document.getElementById('stable-erp-automation-panel');
        //     if (panel) {
        //         panel.remove();
        //         this.panelInjected = false;
        //     }
        //     const pageButton = document.getElementById('page-batch-shipping-btn');
        //     if (pageButton) {
        //         pageButton.remove();
        //         this.pageButtonInjected = false;
        //     }
        //     this.currentPage = 'unknown';
        //     this.queryConditionsSetupCompleted = false;
        //     this.settingUpQueryConditions = false;

        //     console.log('✅ 拣货页面相关资源已清理');
        // }

        // detectCurrentPage() {
        //     const url = window.location.href.toLowerCase();
        //     const title = document.title.toLowerCase();
        //     const bodyText = document.body.innerText.toLowerCase();

        //     console.log('🔍 增强页面检测:');
        //     console.log('URL:', url);
        //     console.log('Title:', title);
        //     console.log('Body Text Length:', bodyText.length);
        //     this.currentPage = 'unknown';
        //     const PICKING_PAGE_PATTERN = /\/part\/warehouse\/outboundManagement\/pickingListQuery\/index2\?menuId=501202/i;
        //     const TRANSFER_IN_PAGE_PATTERN = /\/part\/warehouse\/transferInbound\/index\?menuId=501304/i;

        //     if (PICKING_PAGE_PATTERN.test(url)) {
        //         this.currentPage = 'picking';
        //         console.log('✅ 检测到拣货页面（基于精确URL匹配）');
        //     } else if (TRANSFER_IN_PAGE_PATTERN.test(url)) {
        //         this.currentPage = 'transferIn';
        //         console.log('✅ 检测到调拨入库页面（基于精确URL匹配）');
        //     } else {
        //         this.currentPage = 'unknown';
        //         console.log('❓ 未知页面类型');
        //     }
        //     this.executePageSpecificInit();

        //     return this.currentPage;
        // }

        detectCurrentPage() {
            const url = window.location.href;
            const lowerUrl = url.toLowerCase();
            
            console.log('🔍 增强页面检测:');
            console.log('URL:', url);
            
            this.currentPage = 'unknown';
            
            // 更宽松的匹配规则
            const isPickingPage = lowerUrl.includes('pickinglistquery') && lowerUrl.includes('menuid=501202');
            const isTransferInPage = lowerUrl.includes('transferinbound') && lowerUrl.includes('menuid=501304');

            if (isPickingPage) {
                this.currentPage = 'picking';
                console.log('✅ 检测到拣货页面');
            } else if (isTransferInPage) {
                this.currentPage = 'transferIn';
                console.log('✅ 检测到调拨入库页面');
            } else {
                this.currentPage = 'unknown';
                console.log('❓ 未知页面类型');
            }
            
            this.executePageSpecificInit();
            return this.currentPage;
        }

        executePageSpecificInit() {
            switch (this.currentPage) {
                case 'picking':
                    setTimeout(() => this.autoInitPickingPage(), 1000);
                    break;
                case 'transferIn':
                    setTimeout(() => this.autoInitTransferInPage(), 1000);
                    break;
            }
        }
        autoInitPickingPage() {
            console.log('🔄 自动初始化拣货页面功能');
            this.updateStatus('拣货页面已就绪，可进行拣货操作', 'waiting');
            this.queryConditionsSetupCompleted = false;
            this.settingUpQueryConditions = false;
            this.waitForEssentialElements().then(() => {
                this.injectPageBatchButton();
            }).catch(() => {
                this.injectPageBatchButton();
            });
        }
        async waitForEssentialElements() {
            console.log('⏳ 等待必要的页面元素加载完成...');
            const maxWaitTime = 10000; // 最大等待8秒
            const startTime = Date.now();
            
            return new Promise((resolve, reject) => {
                const checkElements = () => {
                    const appElement = document.querySelector('#app');
                    const formElement = document.querySelector('.el-form');
                    const tableElement = document.querySelector('.el-table');
                    
                    if (appElement && formElement && tableElement) {
                        console.log('✅ 必要的页面元素已加载完成');
                        resolve();
                    } else if (Date.now() - startTime > maxWaitTime) {
                        console.log('⚠️ 等待必要元素超时');
                        reject(new Error('等待必要元素超时'));
                    } else {
                        setTimeout(checkElements, 300);
                    }
                };
                
                checkElements();
            });
        }
        autoInitTransferInPage() {
            console.log('🔄 自动初始化调拨入库页面功能');
            this.updateStatus('调拨入库页面已就绪，可进行批量签收操作', 'waiting');
            this.waitForTransferInElements().then(() => {
                this.injectTransferInBatchButton();
            }).catch(() => {
                this.injectTransferInBatchButton();
            });
        }
        async waitForTransferInElements() {
            console.log('⏳ 等待调拨入库页面元素加载完成...');
            const maxWaitTime = 10000; // 最大等待10秒
            const startTime = Date.now();

            return new Promise((resolve, reject) => {
                const checkElements = () => {
                    const appElement = document.querySelector('#app');
                    const formElement = document.querySelector('.searchform') || document.querySelector('.el-form');
                    const tableElement = document.querySelector('.el-table');
                    const buttonGroupElement = document.querySelector('.btnGroup') || document.querySelector('.el-button-group');

                    if (appElement && formElement && tableElement && buttonGroupElement) {
                        console.log('✅ 调拨入库页面必要元素已加载完成');
                        resolve();
                    } else if (Date.now() - startTime > maxWaitTime) {
                        console.log('⚠️ 等待调拨入库页面元素超时');
                        reject(new Error('等待调拨入库页面元素超时'));
                    } else {
                        setTimeout(checkElements, 300);
                    }
                };

                checkElements();
            });
        }
        startStableAutomation() {
            this.detectCurrentPage();
            this.injectControlPanel();
            this.setupKeyboardListeners();
            this.setupStableDOMObserver();
        }
        setupStableDOMObserver() {
            let domChangeTimer;
            let changeCount = 0;

            this.observer = new MutationObserver((mutations) => {
                clearTimeout(domChangeTimer);
                const hasSignificantChange = mutations.some(mutation => {
                    if (mutation.type === 'childList') {
                        return Array.from(mutation.addedNodes).some(node =>
                            node.nodeType === 1 &&
                            (node.tagName === 'TABLE' ||
                             node.tagName === 'FORM' ||
                             node.tagName === 'DIV' && node.className &&
                             (node.className.includes('table') ||
                              node.className.includes('form') ||
                              node.className.includes('container'))
                            )
                        );
                    }
                    return false;
                });

                if (hasSignificantChange) {
                    changeCount++;
                    console.log(`🔄 检测到重要DOM变化 (#${changeCount})`);
                    domChangeTimer = setTimeout(() => {
                        const existingPanel = document.getElementById('stable-erp-automation-panel');
                        if (!existingPanel) {
                            console.log('🔧 面板丢失，重新注入');
                            this.panelInjected = false;
                            this.injectControlPanel();
                        } else {
                            console.log('✅ 面板仍然存在，无需操作');
                        }
                        this.handlePageSpecificButtonCheck();

                        changeCount = 0;
                    }, 3000); // 等待3秒确保DOM稳定


                }
            });
            const appContainer = document.querySelector('#app') ||
                                document.querySelector('.app-container') ||
                                document.querySelector('.main-content') ||
                                document.body;

            if (appContainer) {
                this.observer.observe(appContainer, {
                    childList: true,
                    subtree: true,
                    attributes: false, // 不观察属性变化
                    characterData: false // 不观察文本变化
                });
                console.log('🔍 启动有限的DOM观察器');
            }
        }

        // setupStableDOMObserver() {
        //     let domChangeTimer;
        //     let changeCount = 0;

        //     this.observer = new MutationObserver((mutations) => {
        //         clearTimeout(domChangeTimer);
        //         const hasSignificantChange = mutations.some(mutation => {
        //             if (mutation.type === 'childList') {
        //                 return Array.from(mutation.addedNodes).some(node =>
        //                     node.nodeType === 1 &&
        //                     (node.tagName === 'TABLE' ||
        //                      node.tagName === 'FORM' ||
        //                      node.tagName === 'DIV' && node.className &&
        //                      (node.className.includes('table') ||
        //                       node.className.includes('form') ||
        //                       node.className.includes('container'))
        //                     )
        //                 );
        //             }
        //             return false;
        //         });

        //         if (hasSignificantChange) {
        //             changeCount++;
        //             console.log(`🔄 检测到重要DOM变化 (#${changeCount})`);
        //             domChangeTimer = setTimeout(() => {
        //                 // 检查面板是否存在
        //                 const existingPanel = document.getElementById('stable-erp-automation-panel');
        //                 if (!existingPanel) {
        //                     console.log('🔧 面板丢失，重新注入');
        //                     this.panelInjected = false;
        //                     this.injectControlPanel();
        //                 } else {
        //                     // 面板存在，检查内容是否需要更新
        //                     this.handlePageSpecificButtonCheck();
        //                 }

        //                 changeCount = 0;
        //             }, 1000); // 缩短等待时间以提高响应速度
        //         }
        //     });
            
        //     const appContainer = document.querySelector('#app') ||
        //                         document.querySelector('.app-container') ||
        //                         document.querySelector('.main-content') ||
        //                         document.body;

        //     if (appContainer) {
        //         this.observer.observe(appContainer, {
        //             childList: true,
        //             subtree: true,
        //             attributes: false,
        //             characterData: false
        //         });
        //         console.log('🔍 启动增强的DOM观察器');
        //     }
        // }

        // setupStableDOMObserver() {
        //     // 批量处理期间完全禁用DOM观察器
        //     if (this.batchProcessing) {
        //         return;
        //     }
            
        //     // 减少DOM观察器的监控范围，只监控关键区域
        //     let domChangeTimer;

        //     this.observer = new MutationObserver((mutations) => {
        //         // 批量处理期间不执行DOM观察
        //         if (this.batchProcessing) {
        //             return;
        //         }
                
        //         clearTimeout(domChangeTimer);
                
        //         // 只关注可能导致面板丢失的重大变化
        //         const hasMajorChange = mutations.some(mutation => {
        //             if (mutation.type === 'childList' && mutation.removedNodes.length > 0) {
        //                 return Array.from(mutation.removedNodes).some(node => {
        //                     // 检查是否移除了我们的面板
        //                     if (node.id === 'stable-erp-automation-panel') {
        //                         return true;
        //                     }
                            
        //                     // 检查是否移除了关键容器
        //                     if (node.className && typeof node.className === 'string' && 
        //                         (node.className.includes('app') || node.className.includes('container'))) {
        //                         return true;
        //                     }
                            
        //                     return false;
        //                 });
        //             }
        //             return false;
        //         });

        //         if (hasMajorChange) {
        //             console.log(`🔄 检测到重大DOM变化`);
        //             domChangeTimer = setTimeout(() => {
        //                 // 只在面板确实丢失时才重新注入
        //                 const existingPanel = document.getElementById('stable-erp-automation-panel');
        //                 if (!existingPanel) {
        //                     console.log('🔧 面板丢失，重新注入');
        //                     this.panelInjected = false;
        //                     this.injectControlPanel();
        //                 }
        //             }, 1000);
        //         }
        //     });
            
        //     // 只观察body元素的直接子元素变化，减少性能影响
        //     const appContainer = document.body;

        //     if (appContainer) {
        //         this.observer.observe(appContainer, {
        //             childList: true,  // 只监控直接子元素
        //             subtree: false,   // 不监控子孙元素
        //             attributes: false,
        //             characterData: false
        //         });
        //         console.log('🔍 启动轻量级DOM观察器');
        //     }
        // }

        handlePageSpecificButtonCheck() {
            if (this.currentPage === 'picking') {
                this.handlePickingPageButtonCheck();
            } else if (this.currentPage === 'transferIn') {
                this.handleTransferInPageButtonCheck();
            }
        }
        handlePickingPageButtonCheck() {
            const existingPageButton = document.getElementById('page-batch-shipping-btn');
            if (!existingPageButton) {
                console.log('🔧 拣货页面按钮丢失，重新注入');
                this.pageButtonInjected = false;
                this.queryConditionsSetupCompleted = false;
                this.settingUpQueryConditions = false;
                this.injectPageBatchButtonFallback();
            }
        }
        handleTransferInPageButtonCheck() {
            const existingTransferButton = document.getElementById('batch-receive-btn');
            if (!existingTransferButton) {
                console.log('🔧 调拨入库页面按钮丢失，重新注入');
                this.transferInButtonInjected = false;
                this.injectTransferInBatchButton();
            }
        }
        async fetchWarehouses() {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: 'https://xb.fy-carg.com/dmscloud.part//warehouse/manage/queryListForSelect',
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                this.apiData.warehouses = data.data.map(item => ({
                                    name: item.name,
                                    value: item.value,
                                    address: item.address
                                }));
                                resolve(this.apiData.warehouses);
                            } else {
                                reject(new Error('获取仓库数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        async fetchPickers(warehouseId = '11') {

            // 优先检查硬编码数据
            const warehouseIdNum = parseInt(warehouseId);
            if (HARD_CODED_EMPLOYEES[warehouseIdNum] && 
                HARD_CODED_EMPLOYEES[warehouseIdNum].pickers.length > 0) {
                console.log(`✅ 使用仓库${warehouseId}的硬编码拣货人数据`);
                this.apiData.pickers = HARD_CODED_EMPLOYEES[warehouseIdNum].pickers;
                return this.apiData.pickers;
            }
            
            // 如果硬编码数据不存在，调用API

            // 如果硬编码数据不存在，调用API
            // return new Promise((resolve, reject) => {
            //     GM_xmlhttpRequest({
            //         method: 'GET',
            //         url: `https://xb.fy-carg.com/dcscloud.basedata//basedata/employees/getEmpByRoleCode?roleCode=JHR&warehouseId=${warehouseId}`,
            //         onload: (response) => {
            //             try {
            //                 const data = JSON.parse(response.responseText);
            //                 if (data.success && data.data) {
            //                     this.apiData.pickers = data.data.map(item => ({
            //                         name: item.EMPLOYEE_NAME,
            //                         phone: item.PHONE
            //                     }));
            //                     resolve(this.apiData.pickers);
            //                 } else {
            //                     reject(new Error('获取拣货人数据失败'));
            //                 }
            //             } catch (error) {
            //                 reject(error);
            //             }
            //         },
            //         onerror: (error) => {
            //             reject(error);
            //         }
            //     });
            // });
        }
        async fetchPackers(warehouseId = '11') {

            // 优先检查硬编码数据
            const warehouseIdNum = parseInt(warehouseId);
            if (HARD_CODED_EMPLOYEES[warehouseIdNum] && 
                HARD_CODED_EMPLOYEES[warehouseIdNum].packers.length > 0) {
                console.log(`✅ 使用仓库${warehouseId}的硬编码装箱人数据`);
                this.apiData.packers = HARD_CODED_EMPLOYEES[warehouseIdNum].packers;
                return this.apiData.packers;
            }
            
            // 如果硬编码数据不存在，调用API

            // 如果硬编码数据不存在，调用API
            // return new Promise((resolve, reject) => {
            //     GM_xmlhttpRequest({
            //         method: 'GET',
            //         url: `https://xb.fy-carg.com/dcscloud.basedata//basedata/employees/getEmpByRoleCode?roleCode=ZXR&warehouseId=${warehouseId}`,
            //         onload: (response) => {
            //             try {
            //                 const data = JSON.parse(response.responseText);
            //                 if (data.success && data.data) {
            //                     this.apiData.packers = data.data.map(item => ({
            //                         name: item.EMPLOYEE_NAME,
            //                         phone: item.PHONE
            //                     }));
            //                     resolve(this.apiData.packers);
            //                 } else {
            //                     reject(new Error('获取装箱人数据失败'));
            //                 }
            //             } catch (error) {
            //                 reject(error);
            //             }
            //         },
            //         onerror: (error) => {
            //             reject(error);
            //         }
            //     });
            // });
        }
        async fetchBoxes() {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: 'https://xb.fy-carg.com/dmscloud.part//boxModelManage/queryBoxModelManageList',
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                this.apiData.boxes = data.data.map(item => ({
                                    model: item.box_model,
                                    name: item.box_name,
                                    type: item.box_type,
                                    id: item.id
                                }));
                                resolve(this.apiData.boxes);
                            } else {
                                reject(new Error('获取箱子数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        async fetchVehicles(warehouseId = '11') {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: `https://xb.fy-carg.com/dmscloud.part//ownVehicle/manage/queryListForSelect?warehouse_id=${warehouseId}`,
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                this.apiData.vehicles = data.data.map(item => ({
                                    name: item.name,
                                    value: item.value
                                }));
                                resolve(this.apiData.vehicles);
                            } else {
                                reject(new Error('获取车辆数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        async fetchDrivers() {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: `https://xb.fy-carg.com/dcscloud.basedata//basedata/employees/getEmpByRoleCode?roleCode=Logistics_driver`,
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                this.apiData.drivers = data.data.map(item => ({
                                    name: item.EMPLOYEE_NAME,
                                    phone: item.PHONE
                                }));
                                resolve(this.apiData.drivers);
                            } else {
                                reject(new Error('获取送货人数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        async fetchLogisticsCompanies() {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: 'https://xb.fy-carg.com/dcscloud.basedata/DealerData/getLogCompangList?logistics=logisticsCompanys',
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                this.apiData.logisticsCompanies = data.data.map(item => ({
                                    id: item.DEALER_ID,
                                    name: item.DEALER_NAME
                                }));
                                resolve(this.apiData.logisticsCompanies);
                            } else {
                                reject(new Error('获取物流公司数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        async loadAllAPIData() {
            this.updateStatus('正在加载配置数据...', 'running');

            try {
                await Promise.all([
                    this.fetchWarehouses(), // 先获取仓库数据
                    this.fetchPickers(),
                    this.fetchPackers(),
                    this.fetchBoxes(),
                    this.fetchVehicles(),
                    this.fetchDrivers(),
                    this.fetchLogisticsCompanies() // 添加获取物流公司数据
                ]);

                console.log('✅ 所有API数据加载完成:', this.apiData);
                return true;
            } catch (error) {
                console.error('❌ 加载API数据失败:', error);
                this.updateStatus(`加载配置数据失败: ${error.message}`, 'error');
                return false;
            }
        }
        injectControlPanel() {
            const now = Date.now();
            // if (this.panelInjected && (now - this.lastInjectionTime < 5000)) {
            //     console.log('⏸️ 跳过重复注入');
            //     return;
            // }
            const existingPanel = document.getElementById('stable-erp-automation-panel');
            if (existingPanel) {
                existingPanel.remove();
            }

            const panel = document.createElement('div');
            panel.id = 'stable-erp-automation-panel';
            panel.className = `automation-panel ${this.panelState === 'minimized' ? 'minimized' : this.panelState === 'collapsed' ? 'collapsed' : ''}`;
            // 重新检测当前页面类型
            this.detectCurrentPage();
            let panelContent = '';
            switch (this.currentPage) {
                case 'picking':
                    panelContent = this.getPickingPanelContent();
                    break;
                case 'transferIn':
                    panelContent = this.getTransferInPanelContent();
                    break;
                default:
                    panelContent = this.getGeneralPanelContent();
            }


            panel.innerHTML = panelContent;
            const insertionPoint = document.body;
            if (insertionPoint) {
                insertionPoint.appendChild(panel);
                this.panelInjected = true;
                this.lastInjectionTime = now;
                console.log('✅ 自动化控制面板已稳定注入');
                this.bindPanelEvents();
                this.makePanelDraggable();
            } else {
                console.error('❌ 找不到插入点');
            }
        }
        injectPageBatchButton() {
            if (this.pageButtonLock) {
                console.log('ℹ️ 按钮注入正在执行中，跳过重复执行');
                return;
            }
            this.pageButtonLock = true;
            try {
            if (this.queryConditionsSetupCompleted) {
                console.log('ℹ️ 查询条件已设置完成，直接注入按钮');
                this.injectPageBatchButtonFallback();
                return;
            }
            if (this.settingUpQueryConditions) {
                console.log('ℹ️ 正在设置查询条件，跳过重复执行');
                return;
            }
            this.settingUpQueryConditions = true;            
            this.setupQueryConditions().then(() => {
                this.injectPageBatchButtonFallback();
            }).catch(error => {
                console.error('设置查询条件时出错:', error);
                this.settingUpQueryConditions = false;
                this.queryConditionsSetupCompleted = false;
                this.injectPageBatchButtonFallback();
            });
            } finally {
                setTimeout(() => {
                    this.pageButtonLock = false;
                }, 1000);
            }
        }
        injectPageBatchButtonFallback() {
            const existingButton = document.getElementById('page-batch-shipping-btn');
            if (existingButton) {
                console.log('✅ 页面批量按钮已存在，跳过注入');
                this.pageButtonInjected = true;
                return;
            }
            if (!location.href.includes('/part/warehouse/outboundManagement/pickingListQuery/')) {
                return; // 如果不是目标页面，直接退出，不执行后续代码
            }
            if (this.pageButtonInjected || document.getElementById('page-batch-shipping-btn')) {
                return;
            }
            const formActions = document.querySelector('.el-form div[style*="text-align: center"]') ||
                            document.querySelector('.el-form .form-actions');
            if (!formActions) {
                console.log('❌ 未找到表单底部按钮区域，等待重试');
                setTimeout(() => {
                    this.pageButtonInjected = false;
                    this.injectPageBatchButtonFallback();
                }, 2000);
                return;
            }
            const batchButton = document.createElement('button');
            batchButton.id = 'page-batch-shipping-btn';
            batchButton.className = 'el-button el-button--primary el-button--mini page-batch-shipping-btn batch-operation-button';
            batchButton.innerHTML = '<i class="el-icon-ship"></i><span>批量一键发运</span>';
            batchButton.type = 'button';
            batchButton.setAttribute('data-batch-operation', 'true'); // 添加特殊标识
            batchButton.addEventListener('click', () => {
                this.handleBatchShipping();
            });
            formActions.appendChild(batchButton);

            this.pageButtonInjected = true;
            this.settingUpQueryConditions = false; // 重置标志位
            console.log('✅ 页面批量一键发运按钮已正确注入到表单底部按钮区域（备用方法）');
        }
        async setupQueryConditions() {
            try {
                console.log('🔍 开始设置查询条件');
                const hasData = this.checkPickingListHasData();
                if (hasData) {
                    console.log('ℹ️ 拣货单列表已有数据，跳过查询条件设置，只执行查询操作');
                    try {
                        console.log('🔍 点击查询按钮刷新数据');
                        await this.clickSearchButton();
                        await this.delay(500);
                    } catch (error) {
                        console.error('点击查询按钮时出错:', error);
                        this.queryConditionsSetupCompleted = false;
                        throw error;
                    }
                    
                    console.log('✅ 查询操作完成');
                    this.queryConditionsSetupCompleted = true;
                    return;
                }
                console.log('ℹ️ 拣货单列表无数据，需要设置查询条件');
                const expandButton = document.querySelector('.el-button.searchDA.el-button--text.el-button--mini');
                if (expandButton) {
                    const spanText = expandButton.querySelector('span')?.textContent?.trim();
                    console.log(`🔍 展开按钮文本: "${spanText}"`);
                    if (spanText === '展开') {
                        console.log('✅ 点击展开按钮');
                        expandButton.click();
                        await this.delay(300); // 等待展开动画完成
                    } else {
                        console.log(`ℹ️ 展开按钮状态为"${spanText}"，跳过点击`);
                    }
                } else {
                    console.log('⚠️ 未找到展开按钮');
                }
                await this.waitForFormElements();
                try {
                    const warehouses = await this.fetchWarehousesForQuery();
                    if (warehouses && warehouses.length > 0) {
                        const warehouseName = warehouses[0].name;
                        console.log(`📦 设置出货仓库为: ${warehouseName}`);
                        await this.setWarehouse(warehouseName);
                    }
                } catch (error) {
                    console.error('获取或设置仓库信息时出错:', error);
                    this.queryConditionsSetupCompleted = false;
                    throw error; // 重新抛出错误，让上层处理
                }
                try {
                    console.log('🧹 清除制单人选项');
                    const createdResult = await this.clearSelectField('created_byM');
                    if (!createdResult) {
                        console.log('⚠️ 清除制单人选项可能未完全成功');
                    }
                } catch (error) {
                    console.error('清除制单人选项时出错:', error);
                    this.queryConditionsSetupCompleted = false;
                    throw error;
                }
                try {
                    console.log('🧹 清除业务员选项');
                    const salesResult = await this.clearSelectField('salesmanM');
                    if (!salesResult) {
                        console.log('⚠️ 清除业务员选项可能未完全成功');
                    }
                } catch (error) {
                    console.error('清除业务员选项时出错:', error);
                    this.queryConditionsSetupCompleted = false;
                    throw error;
                }
                try {
                    console.log('🔍 点击查询按钮');
                    await this.clickSearchButton();
                    await this.delay(500);
                } catch (error) {
                    console.error('点击查询按钮时出错:', error);
                    this.queryConditionsSetupCompleted = false;
                    throw error;
                }
                const searchButtons = Array.from(document.querySelectorAll('.el-button'));
                for (let button of searchButtons) {
                    const text = button.textContent?.trim();
                    if (text && (text.includes('查询') || text.includes('搜索') || text.includes('Search'))) {
                        button.removeEventListener('click', this.searchButtonHandler);
                        this.searchButtonHandler = async () => {
                            console.log('🔍 用户点击了查询按钮');
                            setTimeout(() => {
                                this.pageButtonInjected = false;
                                this.injectPageBatchButtonFallback();
                            }, 1000); // 等待2秒确保查询完成
                        };
                        button.addEventListener('click', this.searchButtonHandler);
                        break;
                    }
                }
                console.log('✅ 查询条件设置完成');
                this.queryConditionsSetupCompleted = true;
            } catch (error) {
                console.error('设置查询条件时出错:', error);
                this.queryConditionsSetupCompleted = false;
                this.settingUpQueryConditions = false;
                throw error; // 重新抛出错误，让上层处理
            } finally {
                setTimeout(() => {
                    this.settingUpQueryConditions = false;
                }, 5000);
            }
        }
        async waitForFormElements() {
            console.log('⏳ 等待表单元素加载完成');
            const maxWaitTime = 3000;
            const startTime = Date.now();

            while (Date.now() - startTime < maxWaitTime) {
                const createdByLabel = Array.from(document.querySelectorAll('.el-form-item__label'))
                    .find(label => label.textContent && label.textContent.trim() === '制单人');
                const salesmanLabel = Array.from(document.querySelectorAll('.el-form-item__label'))
                    .find(label => label.textContent && label.textContent.trim() === '业务员');
                const warehouseLabel = Array.from(document.querySelectorAll('.el-form-item__label'))
                    .find(label => label.textContent && label.textContent.trim() === '出货仓库');

                if (createdByLabel && salesmanLabel && warehouseLabel) {
                    console.log('✅ 表单元素已加载完成');
                    await this.delay(300);
                    return;
                }

                await this.delay(200);
            }

            console.log('⚠️ 等待表单元素超时，继续执行');
        }
        async fetchWarehousesForQuery() {
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: 'https://xb.fy-carg.com/dmscloud.part//warehouse/manage/queryListWithPermissions',
                    onload: (response) => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (data.success && data.data) {
                                console.log('✅ 获取仓库信息成功:', data.data);
                                resolve(data.data);
                            } else {
                                reject(new Error('获取仓库数据失败'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
        }
        checkPickingListHasData() {
            console.log('🔍 开始检查拣货单列表是否有数据');
            const table = document.querySelector('.el-table__body') ||
                        document.querySelector('.el-table') ||
                        document.querySelector('table');
            
            if (!table) {
                console.log('❌ 未找到拣货单表格');
                return false;
            }
            const rows = table.querySelectorAll('tbody tr');
            console.log(`找到 ${rows.length} 行数据`);
            
            if (rows.length === 0) {
                console.log('❌ 拣货单列表为空，没有数据行');
                return false;
            }
            let hasValidData = false;
            let validOrderCount = 0;
            
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                let pickingNumber = null;
                const pickingNumberCell = row.querySelector('.el-table_1_column_5 .cell');
                if (pickingNumberCell) {
                    pickingNumber = pickingNumberCell.textContent.trim();
                }
                if (!pickingNumber || pickingNumber === '-') {
                    const cells = row.querySelectorAll('td');
                    for (const cell of cells) {
                        const cellText = cell.textContent.trim();
                        if (cellText && cellText !== '-' && cellText.length > 5 &&
                            /^[A-Za-z0-9]+$/.test(cellText)) {
                            pickingNumber = cellText;
                            break;
                        }
                    }
                }
                if (pickingNumber && pickingNumber !== '-' && pickingNumber.length > 5) {
                    console.log(`✅ 发现有效的拣货单号: ${pickingNumber} (行 ${i + 1})`);
                    hasValidData = true;
                    validOrderCount++;
                    break;
                }
            }

            if (hasValidData) {
                console.log(`✅ 拣货单列表有数据，共找到 ${validOrderCount} 个有效订单`);
                return true;
            } else {
                console.log('❌ 拣货单列表没有有效数据');
                if (rows.length > 0) {
                    console.log('第一行内容:', rows[0].innerText.substring(0, 100) + '...');
                    console.log('第一行HTML结构:', rows[0].innerHTML.substring(0, 200) + '...');
                }
                return false;
            }
        }
        async setWarehouse(warehouseName) {
            const warehouseLabel = Array.from(document.querySelectorAll('.el-form-item__label'))
                .find(label => label.textContent && label.textContent.trim() === '出货仓库');

            if (!warehouseLabel) {
                console.log('❌ 未找到出货仓库标签');
                return;
            }

            const formItem = warehouseLabel.closest('.el-form-item');
            if (!formItem) {
                console.log('❌ 未找到出货仓库表单项');
                return;
            }

            const select = formItem.querySelector('.el-select');
            if (!select) {
                console.log('❌ 未找到出货仓库下拉框');
                return;
            }
            select.click();
            await this.delay(300);
            const dropdowns = document.querySelectorAll('.el-select-dropdown');
            let targetDropdown = null;

            for (let dropdown of dropdowns) {
                const style = window.getComputedStyle(dropdown);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    targetDropdown = dropdown;
                    break;
                }
            }

            if (!targetDropdown) {
                console.log('❌ 未找到展开的下拉菜单');
                return;
            }
            const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
            let found = false;

            for (let option of options) {
                const optionText = option.textContent?.trim();
                if (optionText === warehouseName) {
                    console.log(`✅ 找到匹配的仓库选项: ${warehouseName}`);
                    option.click();
                    found = true;
                    break;
                }
            }

            if (!found) {
                console.log(`⚠️ 未找到匹配的仓库选项: ${warehouseName}`);
                if (options.length > 0) {
                    options[0].click();
                    console.log('✅ 选择第一个仓库选项作为备选');
                }
            }
            targetDropdown.style.display = 'none';
            await this.delay(200);
        }
        async clearSelectField(fieldId) {
            console.log(`🔍 开始清除字段: ${fieldId}`);
            let labelText = '';
            switch (fieldId) {
                case 'created_byM':
                    labelText = '制单人';
                    break;
                case 'salesmanM':
                    labelText = '业务员';
                    break;
                default:
                    labelText = fieldId;
            }
            let label = null;
            const maxWaitTime = 3000;
            const startTime = Date.now();
            
            while (Date.now() - startTime < maxWaitTime) {
                label = Array.from(document.querySelectorAll('.el-form-item__label'))
                    .find(label => label.textContent && label.textContent.trim() === labelText);
                
                if (label) {
                    break;
                }
                
                await this.delay(100);
            }
            
            if (!label) {
                console.log(`❌ 未找到字段标签: ${labelText}`);
                return;
            }

            const formItem = label.closest('.el-form-item');
            if (!formItem) {
                console.log(`❌ 未找到表单项: ${labelText}`);
                return;
            }

            const select = formItem.querySelector('.el-select');
            if (!select) {
                console.log(`❌ 未找到下拉框: ${labelText}`);
                return;
            }
            const input = formItem.querySelector('.el-input__inner');
            if (!input) {
                console.log(`❌ 未找到输入框: ${labelText}`);
                return;
            }
            
            // 对于多选下拉框，需要检查是否有标签，而不是 input.value
            const tagsContainer = formItem.querySelector('.el-select__tags');
            let hasTags = false;
            let tags = [];

            if (tagsContainer) {
                tags = Array.from(tagsContainer.querySelectorAll('.el-tag')).filter(tag => {
                    return tag.style.display !== 'none';
                });
                hasTags = tags.length > 0;
            }

            // 读取 input.value 用于日志记录（多选框中这个值通常是空的）
            let inputValue = input.value;

            console.log(`📋 字段 ${labelText} - input值: "${inputValue}", 标签数量: ${tags.length}`);

            // 如果没有标签，说明已经是空的
            if (!hasTags) {
                console.log(`ℹ️ 字段 ${labelText} 已经是空的（无选中标签），无需清除`);
                return;
            }

            console.log(`📋 字段 ${labelText} 当前选中的标签:`, tags.map(tag => tag.textContent?.trim()));

            // 清除已选中的标签
            for (const tag of tags) {
                const closeIcon = tag.querySelector('.el-tag__close');
                if (closeIcon) {
                    closeIcon.click();
                    console.log(`✅ 已清除标签: ${tag.textContent?.trim()}`);
                    await this.delay(100);
                }
            }
            
            console.log(`✅ 字段 ${labelText} 已清除完成`);
            // select.click();
            // await this.delay(300);
            // const dropdowns = document.querySelectorAll('.el-select-dropdown');
            // let targetDropdown = null;
            // for (let dropdown of dropdowns) {
            //     const style = window.getComputedStyle(dropdown);
            //     if (style.display !== 'none' && style.visibility !== 'hidden') {
            //         const selectRect = select.getBoundingClientRect();
            //         const dropdownRect = dropdown.getBoundingClientRect();
            //         const isBelowSelect = Math.abs(dropdownRect.top - selectRect.bottom) < 50;
            //         const isHorizontallyAligned = Math.abs(dropdownRect.left - selectRect.left) < 50;
                    
            //         if (isBelowSelect && isHorizontallyAligned) {
            //             targetDropdown = dropdown;
            //             console.log(`✅ 通过位置关联找到正确的下拉菜单: ${labelText}`);
            //             break;
            //         }
            //     }
            // }
            // if (!targetDropdown) {
            //     console.log('🔄 尝试通过z-index查找最新展开的下拉菜单');
            //     const visibleDropdowns = Array.from(dropdowns).filter(dropdown => {
            //         const style = window.getComputedStyle(dropdown);
            //         return style.display !== 'none' && style.visibility !== 'hidden';
            //     }).sort((a, b) => {
            //         return (parseInt(b.style.zIndex) || 0) - (parseInt(a.style.zIndex) || 0);
            //     });
            //     if (visibleDropdowns.length > 0) {
            //         targetDropdown = visibleDropdowns[0];
            //         console.log('✅ 通过z-index找到最新展开的下拉菜单');
            //     }
            // }
            // if (!targetDropdown) {
            //     console.log('🔄 尝试通过data属性关联查找下拉菜单');
            //     const selectId = select.getAttribute('id') || select.querySelector('input')?.getAttribute('id');
                
            //     if (selectId) {
            //         for (let dropdown of dropdowns) {
            //             const reference = dropdown.getAttribute('data-popper-reference');
            //             const style = window.getComputedStyle(dropdown);
                        
            //             if (reference && reference.includes(selectId) && 
            //                 style.display !== 'none' && style.visibility !== 'hidden') {
            //                 targetDropdown = dropdown;
            //                 console.log(`✅ 通过data属性找到关联的下拉菜单: ${labelText}`);
            //                 break;
            //             }
            //         }
            //     }
            // }

            // if (!targetDropdown) {
            //     console.log(`❌ 未找到与${labelText}关联的展开下拉菜单`);
            //     await this.delay(100);
            //     return false;
            // }
            // const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
            // let found = false;

            // for (let option of options) {
            //     const optionText = option.textContent?.trim();
            //     if (optionText === '请选择') {
            //         console.log(`✅ 找到"请选择"选项: ${labelText}`);
            //         option.click();
            //         found = true;
            //         break;
            //     }
            // }

            // if (!found) {
            //     console.log(`⚠️ 未找到"请选择"选项: ${labelText}`);
            //     if (options.length > 0) {
            //         options[0].click();
            //         console.log(`✅ 点击第一个选项来重置: ${labelText}`);
            //     }
            // }
            // await this.delay(200);
            // targetDropdown.style.display = 'none';
            // await this.delay(100);
            // const newValue = input.value;
            // console.log(`📋 字段 ${labelText} 清除后值: "${newValue}"`);
            return true;
        }
        async clickSearchButton() {
            const searchButtons = Array.from(document.querySelectorAll('.el-button'));
            let searchButton = null;

            for (let button of searchButtons) {
                const text = button.textContent?.trim();
                if (text && (text.includes('查询') || text.includes('搜索') || text.includes('Search'))) {
                    searchButton = button;
                    break;
                }
            }

            if (!searchButton) {
                console.log('❌ 未找到查询按钮');
                return;
            }

            searchButton.click();
            await this.delay(200); // 等待查询结果加载
        }
        async handleBatchShipping() {
            if (this.isRunning) {
                this.updateStatus('系统繁忙，请稍候...', 'waiting');
                return;
            }

            this.isRunning = true;

            try {
                await this.batchCompletePicking();
            } catch (error) {
                this.updateStatus(`错误: ${error.message}`, 'error');
                console.error('自动化错误:', error);
            } finally {
                this.isRunning = false;
            }
        }
        makePanelDraggable() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (!panel) return;

            const header = panel.querySelector('.automation-panel-header');
            if (!header) return;

            let isDragging = false;
            let startX = 0;
            let startY = 0;
            let initialBottom = 0;
            let initialRight = 0;
            let animationFrameId = null;
            header.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return;
                
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                const viewWidth = window.innerWidth;
                const viewHeight = window.innerHeight;
                const rect = panel.getBoundingClientRect();
                initialBottom = viewHeight - rect.bottom;
                initialRight = viewWidth - rect.right;
                 panel.classList.add('dragging');
                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
                e.preventDefault();
            });
            function handleMouseMove(e) {
                if (!isDragging) return;
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                }
              
                animationFrameId = requestAnimationFrame(() => {
                    panel.style.bottom = (initialBottom - deltaY) + 'px';
                    panel.style.right = (initialRight - deltaX) + 'px';
                    panel.style.left = 'auto';
                    panel.style.top = 'auto';
                });
            }
            function handleMouseUp() {
                if (!isDragging) return;
                
                isDragging = false;
                header.style.cursor = 'move';
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
                panel.classList.remove('dragging');
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                    animationFrameId = null;
                }
            }
        }
        toggleCollapse() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (!panel) return;
            panel.classList.add('state-transition', 'collapsing');

            if (this.panelState === 'collapsed') {
                panel.classList.remove('collapsed');
                this.panelState = 'normal';
            } else {
                panel.classList.add('collapsed');
                this.panelState = 'collapsed';
                if (panel.style.left !== 'auto') {
                    const rect = panel.getBoundingClientRect();
                    const viewWidth = window.innerWidth;
                    const viewHeight = window.innerHeight;
                    panel.style.bottom = (viewHeight - rect.bottom) + 'px';
                    panel.style.right = (viewWidth - rect.right) + 'px';
                    panel.style.left = 'auto';
                    panel.style.top = 'auto';
                }
                if (this.panelState === 'minimized') {
                    panel.classList.remove('minimized');
                }
            }
            setTimeout(() => {
                panel.classList.remove('state-transition', 'collapsing');
            }, 50);
        }
        toggleMinimize() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (!panel) return;
            panel.classList.add('state-transition', 'minimizing');

            if (this.panelState === 'minimized') {
                panel.classList.remove('minimized');
                this.panelState = 'normal';
            } else {
                panel.classList.add('minimized');
                this.panelState = 'minimized';
                if (panel.style.left !== 'auto') {
                    const rect = panel.getBoundingClientRect();
                    const viewWidth = window.innerWidth;
                    const viewHeight = window.innerHeight;
                    panel.style.bottom = (viewHeight - rect.bottom) + 'px';
                    panel.style.right = (viewWidth - rect.right) + 'px';
                    panel.style.left = 'auto';
                    panel.style.top = 'auto';
                }
                if (this.panelState === 'collapsed') {
                    panel.classList.remove('collapsed');
                }
            }
            setTimeout(() => {
                panel.classList.remove('state-transition', 'minimizing');
            }, 50);
        }


        closePanel() {
            const panel = document.getElementById('stable-erp-automation-panel');
            if (panel) {
                panel.remove();
                this.panelInjected = false;
            }
        }

        getGeneralPanelContent() {
            return `
                <div class="automation-panel-header">
                    <div class="automation-panel-title">🤖 ERP自动化v3.6</div>
                    <div class="automation-panel-controls">
                        <button class="panel-control-btn minimize-btn collapse" title="最小化"></button>
                        <button class="panel-control-btn collapse-btn" title="折叠"></button>
                        <button class="panel-control-btn close-btn" title="关闭"></button>
                    </div>
                </div>
                <div class="automation-panel-content">
                    <div style="margin-bottom: 10px;">
                        <button class="automation-btn" data-action="refreshDetection">
                            重新检测页面
                        </button>
                        <!--<button class="automation-btn secondary" data-action="debugInfo">-->
                        <!--    调试信息-->
                        <!--</button>-->
                    </div>
                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;">
                        <div>📋 当前检测:</div>
                        <div>• 页面类型: ${this.currentPage}</div>
                        <div>• URL: ${window.location.href.substring(0, 30)}...</div>
                    </div>
                    <div class="status-indicator status-waiting" id="automationStatus">
                        等待页面检测...
                    </div>
                    <div style="margin-top: 10px; font-size: 10px; color: #999; text-align: center;">
                        增强版页面检测 | 快捷键: Ctrl+Shift+R
                    </div>
                    <!-- 添加一行空白 -->
                    <div style="height: 10px;"></div>

                    <!-- 添加分割线 -->
                    <hr style="border: none; border-top: 1px solid #eee; margin: 5px 0;">
                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;text-align: right;">
                        By 郭佳
                    </div>
                </div>
            `;
        }
        getTransferInPanelContent() {
            return `
                <div class="automation-panel-header">
                    <div class="automation-panel-title">🤖 ERP自动化v3.6-调拨入库</div>
                    <div class="automation-panel-controls">
                        <button class="panel-control-btn minimize-btn collapse" title="最小化"></button>
                        <button class="panel-control-btn collapse-btn" title="折叠"></button>
                        <button class="panel-control-btn close-btn" title="关闭"></button>
                    </div>
                </div>
                <div class="automation-panel-content">
                    <div style="margin-bottom: 10px;">
                        <div class="button-group">
                            <button class="automation-btn" data-action="batchReceive">
                                <i class="el-icon-check"></i> 批量签收
                            </button>
                            <button class="automation-btn success" data-action="monthlyBatchStoreIn">
                                <i class="el-icon-shopping-bag-1"></i> 月结批量入库
                            </button>
                            <button class="automation-btn secondary" data-action="refreshDetection">
                                <i class="el-icon-refresh"></i> 重新检测页面
                            </button>
                        </div>
                    </div>
                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;">
                        <div class="info-section">
                            <h4>操作说明</h4>
                            <ul>
                                <li>批量签收调拨单</li>
                                <li>月末调拨未到批量入库操作</li>
                            </ul>
                        </div>
                    </div>
                    <div class="status-indicator status-waiting" id="automationStatus">
                        等待操作...
                    </div>
                    <div style="margin-top: 10px; font-size: 10px; color: #999; text-align: center;">
                        调拨入库页面 | 快捷键: Ctrl+Shift+R
                    </div>

                    <!-- 添加分割线 -->
                    <hr style="border: none; border-top: 1px solid #eee; margin: 5px 0;">
                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;text-align: right;">
                        By 郭佳
                    </div>
                </div>
            `;
        }
        getPickingPanelContent() {
            return `
                <div class="automation-panel-header">
                    <div class="automation-panel-title">🤖 ERP自动化v3.6-拣货管理</div>
                    <div class="automation-panel-controls">
                        <button class="panel-control-btn minimize-btn collapse" title="最小化"></button>
                        <button class="panel-control-btn collapse-btn" title="折叠"></button>
                        <button class="panel-control-btn close-btn" title="关闭"></button>
                    </div>
                </div>
                <div class="automation-panel-content">
                    <div style="margin-bottom: 10px;">
                        <button class="automation-btn success" data-action="batchCompletePicking">
                            批量一键发运
                        </button>
                        <button class="automation-btn info" data-action="refreshDetection">
                            重新检测页面
                        </button>
                    </div>
                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;">
                        <div>📋 功能说明:</div>
                        <div>• 批量一键发运: 批量处理选中的拣货单</div>
                        <div>• 重新检测: 刷新页面检测结果</div>
                    </div>
                    <div class="status-indicator status-waiting" id="automationStatus">
                        就绪 - 拣货管理页面
                    </div>
                    <div style="margin-top: 10px; font-size: 10px; color: #999; text-align: center;">
                        增强批量功能
                    </div>
                    <!-- 添加一行空白 -->
                    <div style="height: 10px;"></div>

                    <!-- 添加分割线 -->
                    <hr style="border: none; border-top: 1px solid #eee; margin: 5px 0;">

                    <div style="margin-bottom: 10px; font-size: 12px; color: #666;text-align: right;">
                        By 郭佳
                    </div>
                </div>
            `;
        }
        bindPanelEvents() {
    
            const panel = document.getElementById('stable-erp-automation-panel');
            if (!panel) return;
            const buttons = panel.querySelectorAll('[data-action]');
            buttons.forEach(btn => {
                btn.replaceWith(btn.cloneNode(true));
            });
            const newButtons = panel.querySelectorAll('[data-action]');
            newButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const action = e.target.getAttribute('data-action');
                    this.executeAction(action);
                });
            });
            const minimizeBtn = panel.querySelector('.minimize-btn');
            const collapseBtn = panel.querySelector('.collapse-btn');
            const closeBtn = panel.querySelector('.close-btn');

            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleMinimize();
                    minimizeBtn.classList.toggle('collapse');
                    minimizeBtn.classList.toggle('expand');
                });
            }

            if (collapseBtn) {
                collapseBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleCollapse();
                });
            }

            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.closePanel();
                });
            }        
        }
        async executeAction(action) {
            if (this.isRunning) {
                this.updateStatus('系统繁忙，请稍候...', 'waiting');
                return;
            }

            this.isRunning = true;

            try {
                switch(action) {
                    case 'batchCompletePicking':
                        await this.batchCompletePicking();
                        break;
                    case 'batchReceive':
                        await this.handleBatchReceive();
                        break;
                    case 'monthlyBatchStoreIn':
                        await this.handleMonthlyBatchStoreIn();
                        break;
                    case 'refreshDetection':
                        await this.refreshPageDetection();
                        break;
                    // case 'debugInfo':
                    //     this.showDebugInfo();
                    //     break;
                }
            } catch (error) {
                this.updateStatus(`错误: ${error.message}`, 'error');
                console.error('自动化错误:', error);
            } finally {
                this.isRunning = false;
            }
        }
        async batchCompletePicking() {
            this.updateStatus('准备批量一键发运操作...', 'running');

            try {
                const selectedOrders = await this.getSelectedPickingOrders();
                if (selectedOrders.length === 0) {
                    this.updateStatus('请先选择要处理的拣货单', 'error');
                    return;
                }
                this.selectedOrders = selectedOrders; // 添加这一行
                const dataLoaded = await this.loadAllAPIData();
                if (!dataLoaded) {
                    this.updateStatus('加载配置数据失败，请重试', 'error');
                    return;
                }
                await this.showBatchInfoWindow(selectedOrders);

            } catch (error) {
                this.updateStatus(`批量操作准备失败: ${error.message}`, 'error');
                console.error('批量操作错误:', error);
            }
        }
        async showBatchInfoWindow(selectedOrders) {
            this.closeBatchInfoWindow();
            const overlay = document.createElement('div');
            overlay.className = 'batch-operation-overlay';
            const window = document.createElement('div');
            window.className = 'batch-operation-panel';
            window.innerHTML = this.getBatchInfoWindowContent(selectedOrders);

            document.body.appendChild(overlay);
            document.body.appendChild(window);

            this.batchInfoWindow = window;
            const warehouseIdInput = window.querySelector('#batch-warehouse-id');
            if (warehouseIdInput && warehouseIdInput.value) {
                const warehouseId = warehouseIdInput.value;
                try {
                    await Promise.all([
                        this.fetchPickers(warehouseId),
                        this.fetchPackers(warehouseId),
                        this.fetchVehicles(warehouseId),
                        this.fetchDrivers()
                    ]);
                    const pickerSelect = window.querySelector('#batch-picker-select');
                    const packerSelect = window.querySelector('#batch-packer-select');
                    const vehicleSelect = window.querySelector('#batch-vehicle-number');
                    const driverSelect = window.querySelector('#batch-driver-select');

                    if (pickerSelect) {
                        const currentValue = pickerSelect.value;
                        pickerSelect.innerHTML = '<option value="">请选择拣货人</option>' +
                            this.apiData.pickers.map(picker =>
                                `<option value="${picker.name}">${picker.name}</option>`
                            ).join('');
                        if (currentValue && this.apiData.pickers.some(p => p.name === currentValue)) {
                            pickerSelect.value = currentValue;
                        }
                    }

                    if (packerSelect) {
                        const currentValue = packerSelect.value;
                        packerSelect.innerHTML = '<option value="">请选择装箱人</option>' +
                            this.apiData.packers.map(packer =>
                                `<option value="${packer.name}">${packer.name}</option>`
                            ).join('');
                        if (currentValue && this.apiData.packers.some(p => p.name === currentValue)) {
                            packerSelect.value = currentValue;
                        }
                    }

                    if (vehicleSelect) {
                        const currentValue = vehicleSelect.value;
                        vehicleSelect.innerHTML = '<option value="">请选择车牌号</option>' +
                            this.apiData.vehicles.map(vehicle =>
                                `<option value="${vehicle.value}">${vehicle.name}</option>`
                            ).join('');
                        if (currentValue && this.apiData.vehicles.some(v => v.value == currentValue)) {
                            vehicleSelect.value = currentValue;
                        }
                    }

                    if (driverSelect) {
                        const currentValue = driverSelect.value;
                        driverSelect.innerHTML = '<option value="">请选择送货人</option>' +
                            this.apiData.drivers.map(driver =>
                                `<option value="${driver.name}">${driver.name}</option>`
                            ).join('');
                        if (currentValue && this.apiData.drivers.some(d => d.name === currentValue)) {
                            driverSelect.value = currentValue;
                        }
                    }

                    console.log(`✅ 已根据匹配的仓库ID ${warehouseId} 更新相关数据`);
                } catch (error) {
                    console.error('根据匹配仓库更新数据失败:', error);
                }
            }
            this.bindBatchWindowEvents();

            this.updateStatus('请填写批量操作信息', 'waiting');
        }
        getBatchInfoWindowContent(selectedOrders) {
            const logisticsOptions = ['送货', '物流代收', '物流发货', '自提', '快递'];
            let currentWarehouseName = '';
            const warehouseSelect = document.querySelector('.el-form-item__label[for="warehouse_id"]');
            if (warehouseSelect) {
                const formItem = warehouseSelect.closest('.el-form-item');
                if (formItem) {
                    const input = formItem.querySelector('.el-input__inner');
                    if (input) {
                        currentWarehouseName = input.value;
                    }
                }
            }
            let matchedWarehouseId = '';
            if (currentWarehouseName) {
                const matchedWarehouse = this.apiData.warehouses.find(w => w.name === currentWarehouseName);
                if (matchedWarehouse) {
                    matchedWarehouseId = matchedWarehouse.value;
                }
            }

            return `
                <div class="batch-operation-header">
                    <div class="batch-operation-title">🚀 批量一键发运信息配置</div>
                    <button class="batch-operation-close" title="关闭">×</button>
                </div>

                <div class="batch-selected-count">
                    📋 已选择 <strong>${selectedOrders.length}</strong> 个拣货单
                </div>

                <div style="margin-bottom: 15px; padding: 8px; background: #fff3cd; border-radius: 4px; font-size: 12px; color: #856404;">
                    💡 <strong>说明：</strong>只有<strong style="color: #d63384;">拣货人</strong>是必填项，其他字段可根据需要选填
                </div>

                <div class="batch-section">
                    <div class="batch-section-title">基础信息</div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <!-- 隐藏出货仓库字段，但仍保留功能 -->
                        <input type="hidden" id="batch-warehouse-select" value="${currentWarehouseName}">
                        <input type="hidden" id="batch-warehouse-id" value="${matchedWarehouseId}">

                        <div class="batch-form-group">
                            <label class="batch-form-label">拣货人 <span style="color: red;">*</span></label>
                            <select class="batch-form-select" id="batch-picker-select" multiple size="4">
                                <option value="">请选择拣货人（可多选）</option>
                                ${this.apiData.pickers.map(picker =>
                                    `<option value="${picker.name}">${picker.name}</option>`
                                ).join('')}
                            </select>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">点击选择选项，再次点击取消选择</div>
                        </div>

                        <div class="batch-form-group">
                            <label class="batch-form-label">装箱人 <span style="color: #666; font-size: 12px;">(可选)</span></label>
                            <select class="batch-form-select" id="batch-packer-select" multiple size="4">
                                <option value="">请选择装箱人（可多选）</option>
                                ${this.apiData.packers.map(packer =>
                                    `<option value="${packer.name}">${packer.name}</option>`
                                ).join('')}
                            </select>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">点击选择选项，再次点击取消选择</div>
                        </div>

                    </div>
                </div>

                <div class="batch-section">
                    <div class="batch-section-title">包装信息</div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="batch-form-group">
                            <label class="batch-form-label">箱子名称 <span style="color: #666; font-size: 12px;">(可选)</span></label>
                            <select class="batch-form-select" id="batch-box-type">
                                <option value="">请选择箱子类型</option>
                                ${this.apiData.boxes.map(box =>
                                    `<option value="${box.name}">${box.name}</option>`
                                ).join('')}
                            </select>
                        </div>

                        <div class="batch-form-group">
                            <label class="batch-form-label">物流方式 <span style="color: #666; font-size: 12px;">(可选)</span></label>
                            <select class="batch-form-select" id="batch-logistics-type">
                                <option value="">请选择物流方式</option>
                                ${logisticsOptions.map(option =>
                                    `<option value="${option}">${option}</option>`
                                ).join('')}
                            </select>
                        </div>
                        
                        <div class="batch-form-group" id="logistics-company-field" style="display: none;">
                            <label class="batch-form-label">物流公司 <span style="color: #666; font-size: 12px;">(物流代收时必填)</span></label>
                            <select class="batch-form-select" id="batch-logistics-company">
                                <option value="">请选择物流公司</option>
                                ${this.apiData.logisticsCompanies.map(company =>
                                    `<option value="${company.name}">${company.name}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                </div>

                <div class="batch-section">
                    <div class="batch-section-title">运输信息 <span style="color: #666; font-size: 12px;">(可选)</span></div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="batch-form-group">
                            <label class="batch-form-label">是否自有车辆</label>
                            <div style="display: flex; gap: 20px; margin-top: 5px;">
                                <label style="display: flex; align-items: center;">
                                    <input type="radio" name="own-vehicle" value="是" id="own-vehicle-yes">
                                    <span style="margin-left: 5px;">是</span>
                                </label>
                                <label style="display: flex; align-items: center;">
                                    <input type="radio" name="own-vehicle" value="否" id="own-vehicle-no" checked>
                                    <span style="margin-left: 5px;">否</span>
                                </label>
                            </div>
                        </div>
                    </div>
                    
                    <div class="batch-conditional-fields" id="vehicle-fields" style="display: none; margin-top: 15px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="batch-form-group">
                                <label class="batch-form-label">车牌号 <span style="color: #666; font-size: 12px;">(可选)</span></label>
                                <select class="batch-form-select" id="batch-vehicle-number">
                                    <option value="">请选择车牌号</option>
                                    ${this.apiData.vehicles.map(vehicle =>
                                        `<option value="${vehicle.value}">${vehicle.name}</option>`
                                    ).join('')}
                                </select>
                            </div>

                            <div class="batch-form-group">
                                <label class="batch-form-label">送货人 <span style="color: #666; font-size: 12px;">(可选)</span></label>
                                <select class="batch-form-select" id="batch-driver-select">
                                    <option value="">请选择送货人</option>
                                    ${this.apiData.drivers.map(driver =>
                                        `<option value="${driver.name}">${driver.name}</option>`
                                    ).join('')}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="batch-progress-container" id="batch-progress-container">
                    <div class="batch-progress-text" id="batch-progress-text">准备开始处理...</div>
                    <div class="batch-progress-bar">
                        <div class="batch-progress-fill" id="batch-progress-fill"></div>
                    </div>
                </div>

                <div class="batch-operation-buttons">
                    <button class="batch-operation-btn batch-operation-cancel" id="batch-cancel-btn">取消</button>
                    <button class="batch-operation-btn batch-operation-confirm" id="batch-confirm-btn">慢处理</button>
                    <button class="batch-operation-btn batch-operation-confirm" id="batch-confirm-btn-2">快处理</button>
                </div>
            `;
        }
        bindBatchWindowEvents() {
            if (!this.batchInfoWindow) return;
            const closeBtn = this.batchInfoWindow.querySelector('.batch-operation-close');
            const cancelBtn = this.batchInfoWindow.querySelector('#batch-cancel-btn');
            const confirmBtn = this.batchInfoWindow.querySelector('#batch-confirm-btn');
            const confirmBtn2 = this.batchInfoWindow.querySelector('#batch-confirm-btn-2');
            const overlay = document.querySelector('.batch-operation-overlay');

            const closeWindow = () => {
                this.closeBatchInfoWindow(true);
            };

            if (closeBtn) closeBtn.addEventListener('click', closeWindow);
            if (cancelBtn) cancelBtn.addEventListener('click', closeWindow);
            if (overlay) overlay.addEventListener('click', closeWindow);
            if (confirmBtn) {
                confirmBtn.addEventListener('click', () => {
                    this.startBatchProcessing();
                });
            }
            if (confirmBtn2) {
                confirmBtn2.addEventListener('click', () => {
                    this.startBatchProcessingViaAPI();
                });
            }
            const ownVehicleYes = this.batchInfoWindow.querySelector('#own-vehicle-yes');
            const ownVehicleNo = this.batchInfoWindow.querySelector('#own-vehicle-no');
            const vehicleFields = this.batchInfoWindow.querySelector('#vehicle-fields');

            if (ownVehicleYes && ownVehicleNo && vehicleFields) {
                ownVehicleYes.addEventListener('change', () => {
                    vehicleFields.style.display = 'block';
                });

                ownVehicleNo.addEventListener('change', () => {
                    vehicleFields.style.display = 'none';
                });
            }
            const logisticsTypeSelect = this.batchInfoWindow.querySelector('#batch-logistics-type');
            const logisticsCompanyField = this.batchInfoWindow.querySelector('#logistics-company-field');
            
            if (logisticsTypeSelect && logisticsCompanyField) {
                logisticsTypeSelect.addEventListener('change', (e) => {
                    if (e.target.value === '物流代收') {
                        logisticsCompanyField.style.display = 'block';
                    } else {
                        logisticsCompanyField.style.display = 'none';
                    }
                });
            }
            setTimeout(() => {
                const pickerSelect = this.batchInfoWindow.querySelector('#batch-picker-select');
                const packerSelect = this.batchInfoWindow.querySelector('#batch-packer-select');
                
                if (pickerSelect) {
                    this.enableMultiSelectWithoutCtrl(pickerSelect);
                }
                
                if (packerSelect) {
                    this.enableMultiSelectWithoutCtrl(packerSelect);
                }
            }, 100);
            this.batchInfoWindow.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
        enableMultiSelectWithoutCtrl(selectElement) {
            selectElement.setAttribute('data-custom-multiselect', 'true');
            selectElement.selectedValues = new Set();
            selectElement.autoCloseTimer = null;
            selectElement.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const option = e.target.closest('option');
                if (!option || option.value === '') return;
                
                const value = option.value;
                if (selectElement.selectedValues.has(value)) {
                    selectElement.selectedValues.delete(value);
                    option.style.backgroundColor = '';
                    option.style.color = '';
                } else {
                    selectElement.selectedValues.add(value);
                    option.style.backgroundColor = '#007bff';
                    option.style.color = 'white';
                }
                updateSelectState(selectElement);
                if (selectElement.autoCloseTimer) {
                    clearTimeout(selectElement.autoCloseTimer);
                }
                selectElement.autoCloseTimer = setTimeout(() => {
                    selectElement.blur(); // 触发失焦事件来关闭下拉框
                }, 1500);
            });
            function updateSelectState(selectElem) {
                Array.from(selectElem.options).forEach(opt => {
                    opt.selected = false;
                });
                selectElem.selectedValues.forEach(value => {
                    const option = Array.from(selectElem.options).find(opt => opt.value === value);
                    if (option) {
                        option.selected = true;
                    }
                });
                const event = new Event('change', { bubbles: true });
                selectElem.dispatchEvent(event);
            }
        }
        collectBatchSettings() {
            const ownVehicleYes = document.getElementById('own-vehicle-yes');
            const warehouseInput = document.getElementById('batch-warehouse-select');
            const warehouseIdInput = document.getElementById('batch-warehouse-id');
            const warehouseName = warehouseInput?.value || '';
            const warehouseId = warehouseIdInput?.value || '';
            const pickerSelect = document.getElementById('batch-picker-select');
            const packerSelect = document.getElementById('batch-packer-select');
            
            let selectedPickers = [];
            let selectedPackers = [];
            if (pickerSelect) {
                if (pickerSelect.hasAttribute('data-custom-multiselect') && pickerSelect.selectedValues) {
                    selectedPickers = Array.from(pickerSelect.selectedValues);
                } 
                else if (pickerSelect.selectedOptions) {
                    selectedPickers = Array.from(pickerSelect.selectedOptions)
                        .map(option => option.value)
                        .filter(value => value !== '');
                }
                else {
                    selectedPickers = Array.from(pickerSelect.querySelectorAll('option:checked'))
                        .map(option => option.value)
                        .filter(value => value !== '');
                }
            }
            
            if (packerSelect) {
                if (packerSelect.hasAttribute('data-custom-multiselect') && packerSelect.selectedValues) {
                    selectedPackers = Array.from(packerSelect.selectedValues);
                } 
                else if (packerSelect.selectedOptions) {
                    selectedPackers = Array.from(packerSelect.selectedOptions)
                        .map(option => option.value)
                        .filter(value => value !== '');
                }
                else {
                    selectedPackers = Array.from(packerSelect.querySelectorAll('option:checked'))
                        .map(option => option.value)
                        .filter(value => value !== '');
                }
            }

            this.batchSettings = {
                warehouseId: warehouseId,
                warehouseName: warehouseName,
                pickers: selectedPickers,
                packers: selectedPackers,
                boxType: document.getElementById('batch-box-type')?.value,
                logisticsType: document.getElementById('batch-logistics-type')?.value,
                logisticsCompany: document.getElementById('batch-logistics-company')?.value,
                ownVehicle: ownVehicleYes?.checked ? '是' : '否',
                vehicleNumber: document.getElementById('batch-vehicle-number')?.value,
                driver: document.getElementById('batch-driver-select')?.value
            };

            console.log('批量处理设置:', this.batchSettings);
            GM_setValue('batchSettings', this.batchSettings);
        }
        // async startBatchProcessing() {
        //     try {
        //         this.collectBatchSettings();
        //         if (!this.validateBatchSettings()) {
        //             return;
        //         }
        //         this.closeBatchInfoWindow(false);
        //         this.batchProcessing = true;
        //         this.failedOrders = []; // 记录失败订单
        //         this.successCount = 0;
        //         this.showProgressBar();

        //         console.log(`🚀 开始批量处理 ${this.selectedOrders.length} 个订单`);
        //         for (let i = 0; i < this.selectedOrders.length; i++) {
        //             if (!this.batchProcessing) {
        //                 console.log('⏹️ 用户停止了批量处理');
        //                 break;
        //             }
        //             const currentOrders = await this.getAllPickingOrders();
        //             const orderToProcess = currentOrders.find(order =>
        //                 order.pickingNumber === this.selectedOrders[i].pickingNumber);

        //             if (!orderToProcess) {
        //                 console.error(`❌ 未找到订单: ${this.selectedOrders[i].pickingNumber}`);
        //                 this.failedOrders.push({
        //                     order: this.selectedOrders[i],
        //                     error: `未找到订单: ${this.selectedOrders[i].pickingNumber}`
        //                 });
        //                 continue;
        //             }

        //             try {

        //         console.log(`🎯 开始处理第 ${i + 1}/${this.selectedOrders.length} 个订单: ${orderToProcess.pickingNumber}`);
        //         console.log('当前batchSettings状态:', JSON.stringify(this.batchSettings));
        //         await this.processSinglePickingOrder(orderToProcess, i);

        //                 this.successCount++;
        //                 console.log(`✅ 第 ${i + 1} 个订单处理完成，等待 2 秒后继续...`);
        //                 await this.delay(300); // 快速等待弹窗关闭
        //             } catch (error) {
        //                 console.error(`❌ 订单 ${orderToProcess.pickingNumber} 处理失败，立即终止流程:`, error);
        //                 this.failedOrders.push({ order: orderToProcess, error: error.message });
        //                 this.completeBatchProcessing();
        //                 return; // 彻底退出循环
        //             }
        //         }
        //         this.completeBatchProcessing();

        //     } catch (error) {
        //         console.error('批量处理过程出错:', error);
        //         this.handleBatchProcessError(error);
        //     } finally {
        //         this.cleanupAfterBatchProcessing();
        //     }
        // }

        async startBatchProcessing() {
            try {
                this.collectBatchSettings();
                if (!this.validateBatchSettings()) {
                    return;
                }
                this.closeBatchInfoWindow(false);
                this.batchProcessing = true; // 设置批量处理标志
                this.failedOrders = []; // 记录失败订单
                this.successCount = 0;
                this.showProgressBar();

                console.log(`🚀 开始批量处理 ${this.selectedOrders.length} 个订单`);
                for (let i = 0; i < this.selectedOrders.length; i++) {
                    if (!this.batchProcessing) {
                        console.log('⏹️ 用户停止了批量处理');
                        break;
                    }
                    const currentOrders = await this.getAllPickingOrders();
                    const orderToProcess = currentOrders.find(order =>
                        order.pickingNumber === this.selectedOrders[i].pickingNumber);

                    if (!orderToProcess) {
                        console.error(`❌ 未找到订单: ${this.selectedOrders[i].pickingNumber}`);
                        this.failedOrders.push({
                            order: this.selectedOrders[i],
                            error: `未找到订单: ${this.selectedOrders[i].pickingNumber}`
                        });
                        continue;
                    }

                    try {
                        console.log(`🎯 开始处理第 ${i + 1}/${this.selectedOrders.length} 个订单: ${orderToProcess.pickingNumber}`);
                        console.log('当前batchSettings状态:', JSON.stringify(this.batchSettings));
                        await this.processSinglePickingOrder(orderToProcess, i);

                        this.successCount++;
                        console.log(`✅ 第 ${i + 1} 个订单处理完成，等待 2 秒后继续...`);
                        await this.delay(1000); // 快速等待弹窗关闭
                    } catch (error) {
                        console.error(`❌ 订单 ${orderToProcess.pickingNumber} 处理失败，立即终止流程:`, error);
                        this.failedOrders.push({ order: orderToProcess, error: error.message });
                        this.completeBatchProcessing();
                        return; // 彻底退出循环
                    }
                }
                this.completeBatchProcessing();

            } catch (error) {
                console.error('批量处理过程出错:', error);
                this.handleBatchProcessError(error);
            } finally {
                this.cleanupAfterBatchProcessing();
            }
        }

        /**
         * 开始处理2 - 使用API请求方式批量发运
         * 区别于 startBatchProcessing 的模拟操作方式
         */
        async startBatchProcessingViaAPI() {
            try {
                this.collectBatchSettings();
                if (!this.validateBatchSettings()) {
                    return;
                }
                this.closeBatchInfoWindow(false);
                this.batchProcessing = true;
                this.failedOrders = [];
                this.successCount = 0;
                this.showProgressBar();

                console.log(`🚀 开始使用API处理 ${this.selectedOrders.length} 个订单`);

                // 构造请求头（参考 Python HEADERS）
                const HEADERS = {
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'content-type': 'application/json;charset=UTF-8',
                    'Refer': 'https://xb.fy-carg.com/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0'
                };

                // 物流方式代码映射
                const logisticsCodeMap = {
                    "送货": 46171001,
                    "物流代收": 46171002,
                    "物流发货": 46171003,
                    "自提": 46171004,
                    "快递": 46171005
                };

                const logisticsCode = logisticsCodeMap[this.batchSettings.logisticsType];
                const boxInfo = this.apiData.boxes.find(b => b.name === this.batchSettings.boxType) || {};
                const logisticsCompanyInfo = this.apiData.logisticsCompanies.find(c => c.name === this.batchSettings.logisticsCompany) || {};

                // 根据 this.batchSettings.driver查找司机信息
                const driver = this.apiData.drivers.find(d => d.name === this.batchSettings.driver) || {};
                const contactPhone = driver ? driver.phone : "";

                // 构造发运数据
                const packingData = {
                    box_type: parseInt(boxInfo.id),
                    packing_by : this.batchSettings.packers,
                    forklift_driver: "",
                    has_vehicle: this.batchSettings.ownVehicle === '是' ? 10041001 : 10041002,
                    license_no1: this.batchSettings.vehicleNumber || "",
                    license_no2: "",
                    waybill_personnel: driver.name || "",
                    contact_information: contactPhone || "",
                    box_type1: parseInt(boxInfo.type),
                    box_model: boxInfo.model || "",
                    box_price: 0,
                    logistics_mode: logisticsCode,
                    logistics_company_id: logisticsCompanyInfo.id || null,
                    license_no: this.batchSettings.vehicleNumber || ""
                };

                // 只有当装箱人不为空时才添加packingBy字段
                if (this.batchSettings.packers && this.batchSettings.packers.length > 0) {
                    packingData.packingBy = this.batchSettings.packers.join(',');
                }

                let shippingData = {
                    picking_status: 47111003, // 默认值，将在循环内根据 dataList 动态重新计算
                    picking_by: this.batchSettings.pickers.join(','),
                    dataList: [],
                    packingData: packingData
                };

                const updateData = {
                    logistics_mode: logisticsCode,
                    logistics_company_id: logisticsCompanyInfo.id || null,
                    dataList: []
                };

                // 对每个拣货单串行处理
                for (let i = 0; i < this.selectedOrders.length; i++) {
                    if (!this.batchProcessing) {
                        console.log('⏹️ 用户停止了批量处理');
                        break;
                    }

                    const orderToProcess = this.selectedOrders[i];
                    console.log(`🎯 开始处理第 ${i + 1}/${this.selectedOrders.length} 个订单: ${orderToProcess.pickingNumber}`);

                    try {
                        // 步骤1: GET 获取拣货单详情
                        const getPickingListUrl = `https://xb.fy-carg.com/dmscloud.part/warehouse/outboundManagement/getPrintPickingList?picking_order_no=${orderToProcess.pickingNumber}`;

                        const getResp = await new Promise((resolve, reject) => {
                            GM_xmlhttpRequest({
                                method: 'GET',
                                url: getPickingListUrl,
                                headers: HEADERS,
                                onload: resolve,
                                onerror: reject,
                                timeout: 10000
                            });
                        });

                        if (getResp.status !== 200) {
                            this.failedOrders.push({ order: orderToProcess, error: `GET HTTP ${getResp.status}` });
                            continue;
                        }

                        const getJson = JSON.parse(getResp.responseText);
                        const dataList = getJson.data;

                        if (!Array.isArray(dataList)) {
                            this.failedOrders.push({ order: orderToProcess, error: 'GET 返回dataList非列表' });
                            continue;
                        }

                        // 先根据步骤1返回的 dataList 更新数据
                        updateData.dataList = dataList;
                        shippingData.dataList = dataList;

                        // 动态计算 picking_status（参照 indexNew 中 autoWaybill/handlePicking 的逻辑）
                        // 状态码: 47111002=拣货中, 47111003=拣货完成, 47111004=提前关闭, 47111005=作废
                        let pickingStatus = 47111003; // 默认：拣货完成
                        let totalPicked = 0;

                        for (const item of dataList) {
                            const pickNum = Number(item.pick_num) || 0;
                            totalPicked += pickNum;
                            // 期望数量：优先使用 split_num，其次 out_num
                            const expectedQty = Number(item.split_num || item.out_num) || 0;
                            // 如果实际拣货数不等于期望数量，则为部分拣货 → 提前关闭
                            if (pickNum !== expectedQty) {
                                pickingStatus = 47111004; // 提前关闭
                            }
                        }

                        // 如果总拣货数为 0，则为作废
                        if (totalPicked === 0) {
                            pickingStatus = 47111005; // 作废
                        }

                        shippingData.picking_status = pickingStatus;

                        // // 验证数据，同时显示完整的 updateData 和 shippingData
                        // const confirmed = await this.showCombinedDataConfirmation(
                        //     updateData,
                        //     shippingData,
                        //     orderToProcess.pickingNumber
                        // );


                        // if (!confirmed) {
                        //     console.log(`⏸️ 用户取消了订单 ${orderToProcess.pickingNumber} 的处理`);
                        //     this.failedOrders.push({
                        //         order: orderToProcess,
                        //         error: '用户取消操作'
                        //     });
                        //     // continue; // 跳过当前订单，处理下一个
                        //     break;
                        // }

                        // 步骤2: POST 更新物流方式
                        const updateLogisticsUrl = 'https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/updateLogisticsMode';

                        const updateResp = await new Promise((resolve, reject) => {
                            GM_xmlhttpRequest({
                                method: 'POST',
                                url: updateLogisticsUrl,
                                headers: HEADERS,
                                data: JSON.stringify(updateData),
                                onload: resolve,
                                onerror: reject,
                                timeout: 15000
                            });
                        });

                        if (updateResp.status !== 200) {
                            this.failedOrders.push({ order: orderToProcess, error: `UPDATE HTTP ${updateResp.status}` });
                            continue;
                        }

                        // 步骤3: POST 确认发运
                        const pickingUrl = 'https://xb.fy-carg.com/dmscloud.part//warehouse/outboundManagement/picking';

                        const shippingResp = await new Promise((resolve, reject) => {
                            GM_xmlhttpRequest({
                                method: 'POST',
                                url: pickingUrl,
                                headers: HEADERS,
                                data: JSON.stringify(shippingData),
                                onload: resolve,
                                onerror: reject,
                                timeout: 15000
                            });
                        });

                        if (shippingResp.status !== 200) {
                            this.failedOrders.push({ order: orderToProcess, error: `SHIPPING HTTP ${shippingResp.status}` });
                            continue;
                        }

                        // 成功
                        try {
                            JSON.parse(shippingResp.responseText);
                        } catch (e) {
                            // 忽略解析错误
                        }

                        this.successCount++;
                        console.log(`✅ 第 ${i + 1} 个订单处理成功: ${orderToProcess.pickingNumber}`);

                    } catch (error) {
                        console.error(`❌ 订单 ${orderToProcess.pickingNumber} 处理失败:`, error);
                        this.failedOrders.push({ order: orderToProcess, error: `异常: ${error.message}` });
                        // 继续处理下一个订单，不终止流程
                    }

                    // 更新进度
                    this.updateProgress(i, orderToProcess.pickingNumber);

                    // 等待1秒后继续
                    await this.delay(1000);
                }

                this.completeBatchProcessing();

            } catch (error) {
                console.error('API批量处理过程出错:', error);
                this.updateStatus(`API批量处理出错: ${error.message}`, 'error');
                this.handleBatchProcessError(error);
            } finally {
                this.cleanupAfterBatchProcessing();
            }
        }

        /**
         * 显示合并的数据确认弹窗
         * 同时显示 updateData 和 shippingData，让用户一次性确认所有数据
         * @param {Object} updateData - 更新物流方式的数据
         * @param {Object} shippingData - 确认发运的数据
         * @param {string} orderNumber - 订单号
         * @returns {Promise<boolean>} - 用户确认结果，true表示确认，false表示取消
         */
        async showCombinedDataConfirmation(updateData, shippingData, orderNumber) {
            const content = `
                <div class="confirmation-section">
                    <h3 style="color: #667eea;">【步骤2: 更新物流方式】</h3>
                    <div style="background: #f8f9fa;">
                        <pre>${JSON.stringify(updateData, null, 2)}</pre>
                    </div>
                </div>
                <div class="confirmation-section">
                    <h3 style="color: #667eea;">【步骤3: 确认发运】</h3>
                    <div style="background: #f8f9fa;">
                        <pre>${JSON.stringify(shippingData, null, 2)}</pre>
                    </div>
                </div>
            `;
            
            const modal = new CustomModal('数据确认', content);
            modal.show();
            
            return await modal.promise;
        }

        async getAllPickingOrders() {
            console.log('🔍 获取所有拣货单...');

            const allOrders = [];
            const table = document.querySelector('.el-table__body') ||
                         document.querySelector('.el-table') ||
                         document.querySelector('table');

            if (!table) {
                console.error('❌ 未找到拣货单表格');
                throw new Error('未找到拣货单表格');
            }
            const rows = table.querySelectorAll('tbody tr');
            console.log(`找到 ${rows.length} 行数据`);

            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const orderInfo = this.extractOrderInfoFromRow(row, i);
                if (orderInfo && orderInfo.operateButton) {
                    allOrders.push(orderInfo);
                    console.log(`✅ 添加订单: ${orderInfo.pickingNumber}`);
                } else {
                    console.log(`⚠️ 订单信息不完整，跳过: 行 ${i + 1}`);
                }
            }

            console.log(`✅ 找到 ${allOrders.length} 个拣货单`);

            if (allOrders.length === 0) {
                throw new Error('未找到任何拣货单，请确保页面上有订单数据');
            }

            return allOrders;
        }
        showProgressBar() {
            const progressContainer = document.getElementById('batch-progress-container');
            const progressText = document.getElementById('batch-progress-text');
            const progressFill = document.getElementById('batch-progress-fill');

            if (progressContainer) {
                progressContainer.style.display = 'block';
            }

            if (progressText) {
                progressText.textContent = '开始批量处理...';
            }

            if (progressFill) {
                progressFill.style.width = '0%';
            }
        }
        validateBatchSettings() {
            if (!this.batchSettings.pickers || this.batchSettings.pickers.length === 0) {
                alert('请至少选择一个拣货人');
                return false;
            }
            return true;
        }
        updateProgress(currentIndex, currentOrderNumber) {
            const progressContainer = document.getElementById('batch-progress-container');
            const progressText = document.getElementById('batch-progress-text');
            const progressFill = document.getElementById('batch-progress-fill');

            if (progressContainer) progressContainer.style.display = 'block';

            const progress = ((currentIndex + 1) / this.selectedOrders.length) * 100;
            if (progressFill) progressFill.style.width = `${progress}%`;

            if (progressText) {
                progressText.textContent = `正在处理第 ${currentIndex + 1}/${this.selectedOrders.length} 个订单: ${currentOrderNumber}`;
            }
        }
        completeBatchProcessing() {
            const progressText = document.getElementById('batch-progress-text');

            if (progressText) {
                if (this.failedOrders.length > 0) {
                    const failedList = this.failedOrders.map(f => f.order.pickingNumber).join(', ');
                    progressText.textContent = `批量处理完成！成功: ${this.successCount}/${this.selectedOrders.length}，失败: ${this.failedOrders.length} (${failedList})`;
                } else {
                    progressText.textContent = `批量处理完成！成功处理 ${this.successCount}/${this.selectedOrders.length} 个订单`;
                }
            }

            this.updateStatus(`批量处理完成: ${this.successCount}/${this.selectedOrders.length}`, 'success');
            
            // 发送完成通知
            GM_notification({
                title: '批量处理完成',
                text: `成功 ${this.successCount} 个，失败 ${this.failedOrders.length} 个`
            });
            
            if (this.failedOrders.length > 0) {
                this.showFailedOrdersReport();
            }
        }
        showFailedOrdersReport() {
            let report = '以下订单处理失败:\n\n';
            this.failedOrders.forEach((failed, index) => {
                report += `${index + 1}. 订单号: ${failed.order.pickingNumber}\n`;
                report += `   错误: ${failed.error}\n\n`;
            });

            console.log('📋 失败订单报告:\n' + report);
            if (confirm(`有 ${this.failedOrders.length} 个订单处理失败，是否查看详细信息？`)) {
                alert(report);
            }
        }
        handleBatchProcessError(error) {
            const progressText = document.getElementById('batch-progress-text');
            if (progressText) {
                progressText.textContent = `处理出错: ${error.message}`;
            }
            this.updateStatus(`批量处理出错: ${error.message}`, 'error');
        }
        // cleanupAfterBatchProcessing() {
        //     this.batchProcessing = false;
        //     this.cleanupBatchSettings();
        //     const progressContainer = document.getElementById('batch-progress-container');
        //     if (progressContainer) {
        //         setTimeout(() => {
        //             progressContainer.style.display = 'none';
        //         }, 5000); // 5秒后自动隐藏
        //     }
        // }

        cleanupAfterBatchProcessing() {
            this.batchProcessing = false; // 重置批量处理标志
            this.cleanupBatchSettings();
            const progressContainer = document.getElementById('batch-progress-container');
            if (progressContainer) {
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                }, 5000); // 5秒后自动隐藏
            }
            // 批量处理完成后重新检测页面
            setTimeout(() => {
                this.detectCurrentPage();
                this.injectControlPanel();
            }, 1000);
        }

        cleanupBatchSettings() {
            if (!this.batchProcessing) {
                this.batchSettings = {};
                GM_setValue('batchSettings', null);
                this.selectedOrders = [];
                this.currentBatchIndex = 0;

                console.log('✅ 批量设置已清理');
            } else {
                console.log('⏸️ 批量处理中，暂不清理设置');
            }
        }
        closeBatchInfoWindow(cleanup = false) {
            if (this.batchInfoWindow) {
                this.batchInfoWindow.remove();
                this.batchInfoWindow = null;
            }

            const overlay = document.querySelector('.batch-operation-overlay');
            if (overlay) {
                overlay.remove();
            }

            this.batchProcessing = false;
            if (cleanup) {
                this.cleanupBatchSettings();
            }
        }
        // async processSinglePickingOrder(order, index) {
        //     console.log(`🔄 开始处理第 ${index + 1} 个订单: ${order.pickingNumber}`);

        //     try {
        //         console.log(`📝 点击订单 ${order.pickingNumber} 的拣货按钮`);
        //         if (order.operateButton) {
        //             order.operateButton.click();
        //         } else {
        //             throw new Error('未找到操作按钮');
        //         }
        //         await this.waitForPickingDetailPage();
        //         await this.handlePickingDetailPage(order);

        //         console.log(`✅ 订单 ${order.pickingNumber} 处理完成`);
        //     } catch (error) {
        //         console.error(`❌ 处理订单 ${order.pickingNumber} 失败:`, error);

        //         throw error; // 重新抛出错误，让上层处理
        //     }
        // }

        async processSinglePickingOrder(order, index) {
            console.log(`🔄 开始处理第 ${index + 1} 个订单: ${order.pickingNumber}`);

            try {
                console.log(`📝 点击订单 ${order.pickingNumber} 的拣货按钮`);
                if (order.operateButton) {
                    // 确保元素在视口中
                    order.operateButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    await this.delay(100);
                    
                    // 尝试多种点击方式确保点击生效
                    order.operateButton.focus();
                    
                    // 方法1: 直接点击
                    order.operateButton.click();
                    console.log('✅ 已点击拣货按钮(方法1)');
                    await this.delay(300);
                    
                    // 验证点击是否生效
                    let clicked = false;
                    for (let i = 0; i < 2; i++) {
                        const hasDetailIndicators = document.querySelector('.el-form-item__label') && 
                                                  Array.from(document.querySelectorAll('.el-form-item__label'))
                                                      .some(label => label.textContent && label.textContent.includes('拣货人'));
                        
                        if (hasDetailIndicators) {
                            clicked = true;
                            console.log('✅ 点击生效，已进入详情页面');
                            break;
                        }
                        
                        if (i < 1) {
                            console.log(`⚠️ 点击似乎未生效，重试第 ${i + 1} 次...`);
                            order.operateButton.click();
                            await this.delay(500);
                        }
                    }
                    
                    if (!clicked) {
                        // 方法2: 使用事件触发
                        console.log('🔁 尝试第二种点击方式...');
                        const event = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        order.operateButton.dispatchEvent(event);
                        await this.delay(500);
                        
                        // 方法3: 如果还是不行，尝试通过jQuery触发(如果页面使用了jQuery)
                        console.log('🔁 尝试第三种点击方式...');
                        if (typeof $ !== 'undefined' && $(order.operateButton).length) {
                            $(order.operateButton).click();
                            await this.delay(300);
                        }
                    }
                } else {
                    throw new Error('未找到操作按钮');
                }
                
                await this.waitForPickingDetailPage();
                await this.handlePickingDetailPage(order);

                console.log(`✅ 订单 ${order.pickingNumber} 处理完成`);
            } catch (error) {
                console.error(`❌ 处理订单 ${order.pickingNumber} 失败:`, error);
                throw error;
            } finally {
                console.log('⏳ 等待页面恢复正常状态...');
                await this.delay(500);
            }
        }
        // 快速检查详情页面
        quickCheckDetailPage() {
            return new Promise((resolve) => {
                setTimeout(() => {
                    const hasDetailIndicators = document.querySelector('.el-form-item__label') && 
                                            Array.from(document.querySelectorAll('.el-form-item__label'))
                                                .some(label => label.textContent && label.textContent.includes('拣货人'));
                    resolve(hasDetailIndicators);
                }, 100); // 快速检查
            });
        }
        // async waitForPickingDetailPage() {
        //     console.log('⏳ 等待进入拣货详情页面');
        //     const maxWaitTime = 2000;
        //     const startTime = Date.now();

        //     return new Promise((resolve, reject) => {
        //         const checkPage = () => {
        //             const hasDetailTable = document.querySelector('.tabletitle') &&
        //                                  document.querySelector('.tabletitle').textContent.includes('明细信息');
        //             const hasPickingPersonField = Array.from(document.querySelectorAll('.el-form-item__label'))
        //                 .some(label => label.textContent && label.textContent.includes('拣货人'));
        //             const hasShippingButton = Array.from(document.querySelectorAll('button'))
        //                 .some(button => button.textContent && button.textContent.includes('一键发运'));

        //             if (hasDetailTable || hasPickingPersonField || hasShippingButton) {
        //                 console.log('✅ 已进入拣货详情页面');
        //                 setTimeout(resolve, 800); // 额外等待确保页面完全加载
        //                 return;
        //             }

        //             if (Date.now() - startTime > maxWaitTime) {
        //                 reject(new Error('等待进入拣货详情页面超时'));
        //                 return;
        //             }

        //             setTimeout(checkPage, 800);
        //         };

        //         checkPage();
        //     });
        // }
        async waitForPickingDetailPage() {
            console.log('⏳ 智能等待进入拣货详情页面');
            const maxWaitTime = 2000; // 从3000ms减少到2000ms
            const startTime = Date.now();
            
            while (Date.now() - startTime < maxWaitTime) {
                const hasDetailIndicators = await this.quickCheckDetailPage();
                
                if (hasDetailIndicators) {
                    console.log('✅ 已进入拣货详情页面');
                    await this.delay(200); // 从800ms减少到200ms
                    return;
                }
                
                await this.delay(100); // 检查间隔从800ms减少到100ms
            }
            
            throw new Error('智能等待进入拣货详情页面超时');
        }

        async handlePickingDetailPage(order) {
            console.log('🔄 处理拣货详情页面，订单号:', order.pickingNumber);
            
            // 验证是否真的在详情页面
            const isDetailPage = document.querySelector('.el-form-item__label') && 
                               Array.from(document.querySelectorAll('.el-form-item__label'))
                                   .some(label => label.textContent && label.textContent.includes('拣货人'));
            
            if (!isDetailPage) {
                console.warn('⚠️ 可能未正确进入详情页面，尝试重新检测...');
                // 等待一段时间再次检测
                await this.delay(3000);
                const isDetailPageRetry = document.querySelector('.el-form-item__label') && 
                                        Array.from(document.querySelectorAll('.el-form-item__label'))
                                            .some(label => label.textContent && label.textContent.includes('拣货人'));
                
                if (!isDetailPageRetry) {
                    console.error('❌ 确认未进入详情页面，终止处理');
                    throw new Error('未能正确进入拣货详情页面');
                }
            }

            try {
                // 新增：检查拣货人是否已设置
                const isPickerAlreadySet = this.checkPickerAlreadySet();
                
                if (!isPickerAlreadySet) {
                    console.log('❌ 拣货人未设置，进行设置');
                    await this.selectPickersInPickingDetailPage();
                } else {
                    console.log('✅ 拣货人已设置，跳过设置步骤');
                }
                // await this.selectPickersInPickingDetailPage();
                await this.delay(200);
                await this.clickOneKeyShippingInDetailPage();
                await this.confirmOneKeyShippingDialog(); // 处理"是否一键发运？"确认框
                await this.delay(400);

                console.log('🎯 即将进入 handleShippingDialog()');
                await this.handleShippingDialog();
                console.log('✅ handleShippingDialog() 已完成');

            } catch (error) {
                console.error('处理拣货详情页面时出错:', error);

                throw error;
            }
        }

        checkPickerAlreadySet() {
            console.log('🔍 检查拣货人是否已设置...');

            const pickerLabels = Array.from(document.querySelectorAll('.el-form-item__label'))
                .filter(label => label.textContent && label.textContent.includes('拣货人'));

            for (const label of pickerLabels) {
                const formItem = label.closest('.el-form-item');
                if (formItem) {
                    const input = formItem.querySelector('.el-input__inner');
                    const tagsContainer = formItem.querySelector('.el-select__tags');

                    // 检查输入框值
                    if (input && input.value && input.value.trim() !== '') {
                        console.log(`✅ 拣货人已设置: ${input.value}`);
                        return true;
                    }

                    // 检查标签容器（多选情况）
                    if (tagsContainer) {
                        const tags = tagsContainer.querySelectorAll('.el-tag');
                        if (tags.length > 0) {
                            console.log(`✅ 拣货人已设置 (多选): ${Array.from(tags).map(tag => tag.textContent?.trim()).join(', ')}`);
                            return true;
                        }
                    }
                }
            }

            console.log('❌ 拣货人未设置');
            return false;
        }


        async selectPickersInPickingDetailPage() {
            console.log('在拣货详情页面选择拣货人:', this.batchSettings.pickers);

            if (!this.batchSettings.pickers || this.batchSettings.pickers.length === 0) {
                console.log('⚠️ 未设置拣货人，跳过选择');
                return;
            }

            try {
                await this.delay(300);
                let targetSelect = null;
                const labels = Array.from(document.querySelectorAll('.el-form-item__label'));
                for (let label of labels) {
                    if (label.textContent && label.textContent.trim() === '拣货人') {
                        console.log('✅ 找到拣货人标签');
                        const formItem = label.closest('.el-form-item');
                        if (formItem) {
                            targetSelect = formItem.querySelector('.el-select');
                            if (targetSelect) break;
                        }
                    }
                }

                if (!targetSelect) {
                    console.log('❌ 未找到拣货人选择器，跳过选择');
                    return;
                }

                console.log('✅ 找到拣货人选择器，开始选择');
                targetSelect.click();
                await this.delay(300);
                const dropdowns = document.querySelectorAll('.el-select-dropdown');
                let targetDropdown = null;

                for (let dropdown of dropdowns) {
                    const style = window.getComputedStyle(dropdown);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        targetDropdown = dropdown;
                        break;
                    }
                }

                if (targetDropdown) {
                    console.log('✅ 下拉菜单已展开，查找选项');
                    const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
                    for (const pickerName of this.batchSettings.pickers) {
                        let found = false;

                        for (let option of options) {
                            const optionText = option.textContent?.trim();
                            console.log(`检查选项: "${optionText}"`);

                            if (optionText === pickerName) {
                                console.log(`✅ 找到匹配的拣货人: ${pickerName}`);
                                option.click();
                                found = true;
                                break;
                            }
                        }

                        if (!found) {
                            console.log(`⚠️ 未找到拣货人: ${pickerName}`);
                        }
                        if (this.batchSettings.pickers.length > 1) {
                            await this.delay(100);
                        }
                    }
                    await this.delay(100);
                    targetDropdown.style.display = 'none';
                    console.log('✅ 直接隐藏下拉菜单元素');
                    await this.delay(100);
                } else {
                    console.log('❌ 未找到展开的下拉菜单');
                }
            } catch (error) {
                console.error('选择拣货人时出错:', error);
            }
        }
        async waitForPageLoad(timeout = 5000) {
            return new Promise((resolve) => {
                const startTime = Date.now();

                const checkReadyState = () => {
                    if (document.readyState === 'complete') {
                        const vueApp = document.querySelector('#app') || document.querySelector('[data-vue-app]');
                        if (vueApp) {
                            const loadingElements = document.querySelectorAll('.loading, .el-loading-mask, [class*="loading"]');
                            if (loadingElements.length === 0) {
                                resolve();
                                return;
                            }
                        } else {
                            resolve();
                            return;
                        }
                    }

                    if (Date.now() - startTime > timeout) {
                        console.log('页面加载检查超时，继续执行');
                        resolve();
                        return;
                    }

                    setTimeout(checkReadyState, 800);
                };

                checkReadyState();
            });
        }

        async clickOneKeyShippingInDetailPage() {
            console.log('在详情页面点击一键发运按钮');
            await this.waitForPageLoad(2000);
            const formContainer = document.querySelector('.el-form');
            if (!formContainer) {
                throw new Error('未找到 .el-form 容器');
            }
            const buttons = document.querySelectorAll('button.el-button');
            let targetButton = null;
            for (const btn of buttons) {
                const txt = btn.textContent?.trim();
                if (txt && txt.includes('一键发运') && !this.isBatchButton(btn)) {
                    targetButton = btn;
                    break;
                }
            }
            if (!targetButton) {
                throw new Error('定位失败：未找到“一键发运”按钮，终止任务');
            }
            if (!this.isElementVisible(targetButton) || targetButton.disabled) {
                throw new Error('定位失败：一键发运按钮不可操作，终止任务');
            }

            targetButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
            targetButton.focus();
            targetButton.click();
            console.log('✅ 成功点击一键发运按钮');
            await this.delay(200);
            return true;
        }
        findShippingButtonInContainer(container) {
            const buttons = container.querySelectorAll('button');
            for (let button of buttons) {
                if (this.isBatchButton(button)) {
                    continue;
                }

                const buttonText = button.textContent?.trim() || '';
                if (buttonText.includes('一键发运')) {
                    console.log(`✅ 在容器中找到一键发运按钮: "${buttonText}"`);
                    return button;
                }
            }
            try {
                const xpath = './/button[.//span[contains(text(), "一键发运")]]';
                const result = document.evaluate(
                    xpath,
                    container,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                );
                const button = result.singleNodeValue;

                if (button && !this.isBatchButton(button)) {
                    console.log('✅ 通过XPath在容器中找到一键发运按钮');
                    return button;
                }
            } catch (error) {
                console.log('XPath查找失败:', error);
            }

            return null;
        }
        async findShippingButtonWithSelector() {
            const selector = 'div.el-form[style*="text-align: center"] button.el-button span';
            const targetButton = document.querySelector(selector)?.parentElement;
            if (targetButton && this.isElementVisible(targetButton) && !targetButton.disabled) {
                targetButton.click();
                await this.delay(300);
                return true;
            }
            throw new Error('精确选择器未找到一键发运按钮');
        }
        isBatchButton(button) {
            if (button.id && button.id.includes('batch')) {
                return true;
            }
            if (button.className && button.className.includes('batch')) {
                return true;
            }
            if (button.getAttribute('data-batch-operation')) {
                return true;
            }
            const text = button.textContent?.trim() || '';
            const batchKeywords = ['批量', 'Batch', 'bulk'];
            return batchKeywords.some(keyword => text.includes(keyword));
        }
        isCorrectShippingButton(button) {
            if (this.isBatchButton(button)) {
                return false;
            }
            const text = button.textContent?.trim() || '';
            if (!text.includes('一键发运')) {
                return false;
            }
            if (!this.isElementVisible(button) || button.disabled) {
                return false;
            }

            return true;
        }
        async waitForElementVisible(selector, timeout = 10000) {
            return new Promise((resolve, reject) => {
                const startTime = Date.now();

                const checkElement = () => {
                    let element = null;
                    const selectors = Array.isArray(selector) ? selector : [selector];

                    for (const sel of selectors) {
                        element = document.querySelector(sel);
                        if (element) break;
                    }

                    if (element && this.isElementVisible(element)) {
                        resolve(element);
                        return;
                    }

                    if (Date.now() - startTime > timeout) {
                        reject(new Error(`等待元素 ${selectors.join(' 或 ')} 可见超时`));
                        return;
                    }

                    setTimeout(checkElement, 500);
                };

                checkElement();
            });
        }
        async findElementByXPath(xpath) {
            return new Promise((resolve) => {
                try {
                    const result = document.evaluate(
                        xpath,
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    );
                    resolve(result.singleNodeValue);
                } catch (error) {
                    console.error('XPath查找失败:', error);
                    resolve(null);
                }
            });
        }

        isElementVisible(element) {
            if (!element) return false;
            if (!document.contains(element)) {
                return false;
            }

            const style = window.getComputedStyle(element);
            if (style.display === 'none' ||
                style.visibility === 'hidden' ||
                style.opacity === '0') {
                return false;
            }
            if (element.offsetWidth <= 0 && element.offsetHeight <= 0) {
                return false;
            }
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) {
                return false;
            }

            return true;
        }
        async handleShippingDialog() {
            console.log('🎯 开始处理一键发运弹窗（改进定位方式）');

            try {
                await this.waitForShippingDialog();
                let dialog = null;
                const dialogWrappers = document.querySelectorAll('.el-dialog__wrapper');
                if (!dialogWrappers.length) {
                    console.log('❌ 未找到弹窗容器');
                    throw new Error('未找到弹窗容器');
                }
                for (const wrapper of dialogWrappers) {
                    const isVisible = window.getComputedStyle(wrapper).display !== 'none';
                    if (!isVisible) continue;
                    const hasBoxType = wrapper.querySelector('label[for="box_type"]');
                    const hasLogisticsMode = wrapper.querySelector('label[for="logistics_mode"]');

                    if (hasBoxType && hasLogisticsMode) {
                        dialog = wrapper;
                        break;
                    }
                }

                if (!dialog) {
                    throw new Error('未找到弹窗');
                }

                console.log('✅ 弹窗已加载，开始设置字段...');
                // if (this.batchSettings.boxType) {
                //     await this.setSelectValueByEnhancedMethod(dialog, '箱子名称', this.batchSettings.boxType);
                // } else {
                //     console.log('⏭️ 跳过箱子名称设置（未设置）');
                // }

                // if (this.batchSettings.logisticsType) {
                //     await this.setSelectValueByEnhancedMethod(dialog, '物流方式', this.batchSettings.logisticsType);
                //     if (this.batchSettings.logisticsType === '物流代收' && this.batchSettings.logisticsCompany) {
                //         await this.setSelectValueByEnhancedMethod(dialog, '物流公司', this.batchSettings.logisticsCompany);
                //     }
                // } else {
                //     console.log('⏭️ 跳过物流方式设置（未设置）');
                // }

                // 新增：检查箱子名称是否与设置一致
                const isBoxTypeConsistent = await this.checkBoxTypeConsistency(dialog);
                if (!isBoxTypeConsistent && this.batchSettings.boxType) {
                    console.log('🔧 箱子名称不一致，重新设置');
                    await this.setSelectValueByEnhancedMethod(dialog, '箱子名称', this.batchSettings.boxType);
                } else if (isBoxTypeConsistent) {
                    console.log('✅ 箱子名称与设置一致，跳过设置');
                } else {
                    console.log('⏭️ 跳过箱子名称设置（未设置批量参数）');
                }
                
                // 新增：检查物流方式是否与设置一致
                const isLogisticsConsistent = await this.checkLogisticsConsistency(dialog);
                if (!isLogisticsConsistent && this.batchSettings.logisticsType) {
                    console.log('🔧 物流方式不一致，重新设置');
                    await this.setSelectValueByEnhancedMethod(dialog, '物流方式', this.batchSettings.logisticsType);
                    if (this.batchSettings.logisticsType === '物流代收' && this.batchSettings.logisticsCompany) {
                        await this.setSelectValueByEnhancedMethod(dialog, '物流公司', this.batchSettings.logisticsCompany);
                    }
                } else if (isLogisticsConsistent) {
                    console.log('✅ 物流方式与设置一致，跳过设置');
                } else {
                    console.log('⏭️ 跳过物流方式设置（未设置批量参数）');
                }

                if (this.batchSettings.packers && this.batchSettings.packers.length > 0) {
                    await this.setMultipleSelectValuesByEnhancedMethod(dialog, '装箱人', this.batchSettings.packers);
                } else {
                    console.log('⏭️ 跳过装箱人设置（未设置）');
                }
                if (this.batchSettings.ownVehicle) {
                    await this.setRadioValueByEnhancedMethod(dialog, '是否自有车辆', this.batchSettings.ownVehicle);
                } else {
                    console.log('⏭️ 跳过是否自有车辆设置（未设置）');
                }
                if (this.batchSettings.ownVehicle === '是') {
                    if (this.batchSettings.vehicleNumber) {
                        await this.setSelectValueByEnhancedMethod(dialog, '车牌号', this.batchSettings.vehicleNumber);
                    }
                    if (this.batchSettings.driver) {
                        await this.setSelectValueByEnhancedMethod(dialog, '送货人', this.batchSettings.driver);
                    }
                }

                // console.log('✅ 所有字段设置完成');
                await this.clickConfirmInShippingDialog(dialog);
                await this.delay(500);
                // await this.closeShippingDialog();
                // await this.clickReturnButtonInPickingPage();
                // console.log('🔄 等待弹窗关闭...');
                // await this.waitForDialogClose();
                console.log('✅ 弹窗已关闭，准备继续');

            } catch (error) {
                console.error('处理一键发运弹窗时出错:', error);
                throw error;
            }
        }

        async checkBoxTypeConsistency(dialog) {
            console.log('🔍 检查箱子名称一致性...');

            if (!this.batchSettings.boxType) {
                console.log('⚠️ 未设置批量箱子名称参数，跳过一致性检查');
                return false;
            }

            try {
                const boxLabels = Array.from(dialog.querySelectorAll('.el-form-item__label'))
                    .filter(label => label.textContent && label.textContent.trim() === '箱子名称');

                for (const label of boxLabels) {
                    const formItem = label.closest('.el-form-item');
                    if (formItem) {
                        const input = formItem.querySelector('.el-input__inner');
                        const tagsContainer = formItem.querySelector('.el-select__tags');

                        let currentValue = '';

                        // 获取当前值
                        if (input && input.value) {
                            currentValue = input.value.trim();
                        } else if (tagsContainer) {
                            const tags = tagsContainer.querySelectorAll('.el-tag');
                            if (tags.length > 0) {
                                currentValue = Array.from(tags).map(tag => tag.textContent?.trim()).join(',');
                            }
                        }

                        console.log(`📊 箱子名称检查: 当前值="${currentValue}", 批量设置="${this.batchSettings.boxType}"`);

                        if (currentValue && currentValue === this.batchSettings.boxType) {
                            console.log('✅ 箱子名称一致');
                            return true;
                        } else if (currentValue && currentValue !== this.batchSettings.boxType) {
                            console.log('❌ 箱子名称不一致');
                            return false;
                        }
                    }
                }

                console.log('❌ 未找到箱子名称字段或值为空');
                return false;

            } catch (error) {
                console.error('检查箱子名称一致性时出错:', error);
                return false;
            }
        }

        async checkLogisticsConsistency(dialog) {
            console.log('🔍 检查物流方式一致性...');

            if (!this.batchSettings.logisticsType) {
                console.log('⚠️ 未设置批量物流方式参数，跳过一致性检查');
                return false;
            }

            try {
                const logisticsLabels = Array.from(dialog.querySelectorAll('.el-form-item__label'))
                    .filter(label => label.textContent && label.textContent.trim() === '物流方式');

                for (const label of logisticsLabels) {
                    const formItem = label.closest('.el-form-item');
                    if (formItem) {
                        const input = formItem.querySelector('.el-input__inner');
                        const tagsContainer = formItem.querySelector('.el-select__tags');

                        let currentValue = '';

                        // 获取当前值
                        if (input && input.value) {
                            currentValue = input.value.trim();
                        } else if (tagsContainer) {
                            const tags = tagsContainer.querySelectorAll('.el-tag');
                            if (tags.length > 0) {
                                currentValue = Array.from(tags).map(tag => tag.textContent?.trim()).join(',');
                            }
                        }

                        console.log(`📊 物流方式检查: 当前值="${currentValue}", 批量设置="${this.batchSettings.logisticsType}"`);

                        if (currentValue && currentValue === this.batchSettings.logisticsType) {
                            console.log('✅ 物流方式一致');
                            return true;
                        } else if (currentValue && currentValue !== this.batchSettings.logisticsType) {
                            console.log('❌ 物流方式不一致');
                            return false;
                        }
                    }
                }

                console.log('❌ 未找到物流方式字段或值为空');
                return false;

            } catch (error) {
                console.error('检查物流方式一致性时出错:', error);
                return false;
            }
        }


        async closeShippingDialog() {
            console.log('🔍 查找并关闭一键发运弹窗');
            const dialogWrappers = document.querySelectorAll('.el-dialog__wrapper');
            if (!dialogWrappers.length) {
                console.log('❌ 未找到弹窗容器');
                return false;
            }
            let targetDialog = null;
            for (const wrapper of dialogWrappers) {
                const isVisible = window.getComputedStyle(wrapper).display !== 'none';
                if (!isVisible) continue;
                const hasBoxType = wrapper.querySelector('label[for="box_type"]');
                const hasLogisticsMode = wrapper.querySelector('label[for="logistics_mode"]');

                if (hasBoxType && hasLogisticsMode) {
                    targetDialog = wrapper;
                    break;
                }
            }

            if (!targetDialog) {
                console.log('❌ 未找到一键发运弹窗');
                return false;
            }
            const footer = targetDialog.querySelector('.el-dialog__footer');
            if (footer) {
                const cancelButtons = Array.from(footer.querySelectorAll('.el-button'));
                const cancelButton = cancelButtons.find(btn => {
                    const text = btn.textContent?.trim();
                    return text && (text.includes('取消'));
                });

                if (cancelButton) {
                    console.log('✅ 找到底部取消按钮，准备点击');
                    cancelButton.click();
                    console.log('✅ 点击了弹窗底部取消按钮');
                    await this.delay(500);
                    return true;
                }
            }
            const closeBtn = targetDialog.querySelector('.el-dialog__headerbtn');
            if (closeBtn) {
                console.log('✅ 找到右上角关闭按钮，准备点击');
                closeBtn.click();
                console.log('✅ 点击了弹窗右上角关闭按钮');
                await this.delay(500);
                return true;
            }

            console.log('❌ 未找到弹窗关闭按钮');
            return false;
        }
        async clickReturnButtonInPickingPage() {
            console.log('🔍 查找并点击拣货页面返回按钮');
            const buttons = document.querySelectorAll('.el-button');
            for (const button of buttons) {
                const hasReturnIcon = button.querySelector('.el-icon-back');
                const text = button.textContent?.trim();
                const hasReturnText = text && (text.includes('返回'));

                if (hasReturnIcon && hasReturnText) {
                    console.log('✅ 找到返回按钮，准备点击');
                    button.click();
                    console.log('✅ 点击了返回按钮');
                    await this.delay(500);
                    return true;
                }
            }
            for (const button of buttons) {
                const text = button.textContent?.trim();
                if (text && text.includes('返回')) {
                    console.log('✅ 通过文本找到返回按钮，准备点击');
                    button.click();
                    console.log('✅ 点击了返回按钮');
                    await this.delay(500);
                    return true;
                }
            }

            console.log('❌ 未找到返回按钮');
            return false;
        }
        async setSelectValueByEnhancedMethod(dialog, labelText, targetValue) {
            console.log(`🔍 设置下拉框值: ${labelText} = ${targetValue}`);

            if (!targetValue) {
                console.log(`⚠️ 未设置目标值，跳过选择: ${labelText}`);
                return;
            }

            try {
                await this.delay(200);
                let targetSelect = null;
                const labels = Array.from(dialog.querySelectorAll('.el-form-item__label'));
                for (let label of labels) {
                    if (label.textContent && label.textContent.trim() === labelText) {
                        console.log(`✅ 找到标签: ${labelText}`);
                        const formItem = label.closest('.el-form-item');
                        if (formItem) {
                            targetSelect = formItem.querySelector('.el-select');
                            if (targetSelect) break;
                        }
                    }
                }

                if (!targetSelect) {
                    console.log(`❌ 未找到选择器: ${labelText}`);
                    return;
                }

                console.log(`✅ 找到选择器: ${labelText}，开始选择`);
                targetSelect.click();
                await this.delay(200);
                const dropdowns = document.querySelectorAll('.el-select-dropdown');
                let targetDropdown = null;
                for (let dropdown of dropdowns) {
                    const style = window.getComputedStyle(dropdown);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        const dropdownRect = dropdown.getBoundingClientRect();
                        const selectRect = targetSelect.getBoundingClientRect();
                        if (Math.abs(dropdownRect.top - selectRect.bottom) < 50 ) {
                            targetDropdown = dropdown;
                            console.log('✅ 找到与目标select关联的下拉菜单');
                            break;
                        }
                    }
                }
                if (!targetDropdown) {
                    console.log('🔄 尝试通过z-index查找最新展开的下拉菜单');
                    const visibleDropdowns = Array.from(dropdowns).filter(dropdown => {
                        const style = window.getComputedStyle(dropdown);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }).sort((a, b) => {
                        return (parseInt(b.style.zIndex) || 0) - (parseInt(a.style.zIndex) || 0);
                    });
                    if (visibleDropdowns.length > 0) {
                        targetDropdown = visibleDropdowns[0];
                        console.log('✅ 通过z-index找到最新展开的下拉菜单');
                    }
                }
                if (!targetDropdown) {
                    console.log('🔄 仍未找到下拉菜单，尝试强制重新点击选择器');
                    dropdowns.forEach(d => {
                        d.style.display = 'none';
                    });
                    await this.delay(100);
                    targetSelect.click();
                    await this.delay(200);
                    const retryDropdowns = document.querySelectorAll('.el-select-dropdown');
                    for (let dropdown of retryDropdowns) {
                        const style = window.getComputedStyle(dropdown);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            targetDropdown = dropdown;
                            console.log('✅ 重新点击后找到下拉菜单');
                            break;
                        }
                    }
                }

                if (targetDropdown) {
                    console.log('✅ 下拉菜单已展开，查找选项');
                    const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
                    let found = false;
                    for (let option of options) {
                        const optionText = option.textContent?.trim();
                        console.log(`检查选项: "${optionText}"`);

                        if (optionText === targetValue) {
                            console.log(`✅ 找到匹配的选项: ${targetValue}`);
                            option.scrollIntoView({ block: 'nearest' });
                            await this.delay(100);
                            option.click();
                            found = true;
                            break;
                        }
                    }
                    if (!found && options.length > 0) {
                        console.log('⚠️ 未找到完全匹配的选项，尝试选择第一个可用选项');
                        options[0].scrollIntoView({ block: 'nearest' });
                        await this.delay(100);
                        options[0].click();
                        console.log('✅ 已选择第一个选项');
                    }
                    if (found || options.length > 0) {
                        await this.delay(200);
                        targetDropdown.style.display = 'none';
                        console.log('✅ 直接隐藏下拉菜单元素');
                    }
                    await this.delay(200);
                } else {
                    console.log('❌ 未找到展开的下拉菜单');
                    console.log('💡 所有下拉菜单状态:');
                    dropdowns.forEach((dropdown, index) => {
                        const style = window.getComputedStyle(dropdown);
                        const isInDialog = dialog.contains(dropdown);
                        const zIndex = dropdown.style.zIndex;
                        console.log(`  ${index + 1}. display: ${style.display}, visibility: ${style.visibility}, offsetParent: ${dropdown.offsetParent !== null}, isInDialog: ${isInDialog}, zIndex: ${zIndex}`);
                    });
                }

            } catch (error) {
                console.error(`选择时出错 ${labelText}:`, error);
            }
        }
        async setMultipleSelectValuesByEnhancedMethod(dialog, labelText, targetValues) {
            console.log(`🔍 设置多选下拉框值: ${labelText} = ${targetValues.join(', ')}`);

            if (!targetValues || targetValues.length === 0) {
                console.log(`⚠️ 未设置目标值，跳过选择: ${labelText}`);
                return;
            }

            try {
                await this.delay(300);
                let targetSelect = null;
                const labels = Array.from(dialog.querySelectorAll('.el-form-item__label'));
                for (let label of labels) {
                    if (label.textContent && label.textContent.trim() === labelText) {
                        console.log(`✅ 找到标签: ${labelText}`);
                        const formItem = label.closest('.el-form-item');
                        if (formItem) {
                            targetSelect = formItem.querySelector('.el-select');
                            if (targetSelect) break;
                        }
                    }
                }

                if (!targetSelect) {
                    console.log(`❌ 未找到选择器: ${labelText}`);
                    return;
                }

                console.log(`✅ 找到选择器: ${labelText}，开始选择`);
                targetSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                await this.delay(200);
                targetSelect.click();
                await this.delay(400); // 增加等待时间
                const dropdowns = document.querySelectorAll('.el-select-dropdown');
                let targetDropdown = null;
                for (let dropdown of dropdowns) {
                    const style = window.getComputedStyle(dropdown);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        const dropdownRect = dropdown.getBoundingClientRect();
                        const selectRect = targetSelect.getBoundingClientRect();
                        if (Math.abs(dropdownRect.top - selectRect.bottom) < 50 ) {
                            targetDropdown = dropdown;
                            console.log('✅ 找到与目标select关联的下拉菜单');
                            break;
                        }
                    }
                }
                if (!targetDropdown) {
                    console.log('🔄 尝试通过z-index查找最新展开的下拉菜单');
                    const visibleDropdowns = Array.from(dropdowns).filter(dropdown => {
                        const style = window.getComputedStyle(dropdown);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }).sort((a, b) => {
                        return (parseInt(b.style.zIndex) || 0) - (parseInt(a.style.zIndex) || 0);
                    });
                    if (visibleDropdowns.length > 0) {
                        targetDropdown = visibleDropdowns[0];
                        console.log('✅ 通过z-index找到最新展开的下拉菜单');
                    }
                }
                if (!targetDropdown) {
                    console.log('🔄 仍未找到下拉菜单，尝试强制重新点击选择器');
                    dropdowns.forEach(d => {
                        d.style.display = 'none';
                    });
                    await this.delay(100);
                    targetSelect.click();
                    await this.delay(200);
                    const retryDropdowns = document.querySelectorAll('.el-select-dropdown');
                    for (let dropdown of retryDropdowns) {
                        const style = window.getComputedStyle(dropdown);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            targetDropdown = dropdown;
                            console.log('✅ 重新点击后找到下拉菜单');
                            break;
                        }
                    }
                }

                if (targetDropdown) {
                    console.log('✅ 下拉菜单已展开，查找选项');
                    const options = targetDropdown.querySelectorAll('.el-select-dropdown__item');
                    for (const targetValue of targetValues) {
                        let found = false;
                        for (let option of options) {
                            const optionText = option.textContent?.trim();
                            console.log(`检查选项: "${optionText}"`);

                            if (optionText === targetValue) {
                                console.log(`✅ 找到匹配的选项: ${targetValue}`);
                                option.scrollIntoView({ block: 'nearest' });
                                await this.delay(100);
                                try {
                                    option.click();
                                } catch (clickError) {
                                    console.log('⚠️ 标准点击失败，尝试其他方式');
                                    const mouseEvent = new MouseEvent('click', {
                                        view: window,
                                        bubbles: true,
                                        cancelable: true
                                    });
                                    option.dispatchEvent(mouseEvent);
                                }
                                found = true;
                                break;
                            }
                        }

                        if (!found) {
                            console.log(`⚠️ 未找到匹配的选项: ${targetValue}`);
                        }
                        if (targetValues.length > 1) {
                            await this.delay(100);
                        }
                    }
                    await this.delay(300);
                    if (targetDropdown && targetDropdown.parentNode) {
                        targetDropdown.style.display = 'none';
                        console.log('✅ 已隐藏当前下拉菜单');
                    }
                    await this.delay(100);
                } else {
                    console.log('❌ 未找到展开的下拉菜单');
                    console.log('💡 所有下拉菜单状态:');
                    dropdowns.forEach((dropdown, index) => {
                        const style = window.getComputedStyle(dropdown);
                        const isInDialog = dialog.contains(dropdown);
                        const zIndex = dropdown.style.zIndex;
                        console.log(`  ${index + 1}. display: ${style.display}, visibility: ${style.visibility}, offsetParent: ${dropdown.offsetParent !== null}, isInDialog: ${isInDialog}, zIndex: ${zIndex}`);
                    });
                }

            } catch (error) {
                console.error(`选择时出错 ${labelText}:`, error);
            }
        }
        async setRadioValueByEnhancedMethod(dialog, labelText, targetValue) {
            console.log(`🔍 增强方法查找并设置单选框值: ${labelText} = ${targetValue}`);

            try {
                const searchRoot = dialog.querySelector('.el-dialog__body') || dialog;
                await this.delay(200);
                let label = null;
                const labels = searchRoot.querySelectorAll('label');
                for (const l of labels) {
                    if (l.textContent?.trim() === labelText) {
                        label = l;
                        break;
                    }
                }

                if (!label) {
                    console.log(`❌ 未找到精确匹配的标签: ${labelText}`);
                    for (const l of labels) {
                        if (l.textContent?.includes(labelText)) {
                            label = l;
                            console.log(`✅ 通过模糊匹配找到标签: "${l.textContent?.trim()}"`);
                            break;
                        }
                    }
                }

                if (!label) {
                    console.log(`❌ 未找到标签: ${labelText}`);
                    console.log(`弹窗中所有标签:`, Array.from(labels).map(l => `"${l.textContent?.trim()}"`));
                    return;
                }

                console.log(`✅ 找到标签: "${label.textContent?.trim()}"`);
                const formItem = label.closest('.el-form-item');
                if (!formItem) {
                    console.log('❌ 未找到表单项');
                    return;
                }
                const radioLabels = formItem.querySelectorAll('.el-radio__label');
                const radioInputs = formItem.querySelectorAll('.el-radio__original');

                console.log(`📋 找到 ${radioLabels.length} 个单选框标签`);
                radioLabels.forEach((rl, index) => {
                    console.log(`  单选框标签 ${index + 1}: "${rl.textContent?.trim()}"`);
                });
                let targetRadioInput = null;
                let targetRadioElement = null;

                for (let i = 0; i < radioLabels.length; i++) {
                    const radioLabel = radioLabels[i];
                    if (radioLabel.textContent?.trim() === targetValue) {
                        if (i < radioInputs.length) {
                            targetRadioInput = radioInputs[i];
                            targetRadioElement = radioLabel.closest('.el-radio');
                            break;
                        }
                    }
                }
                if (!targetRadioInput) {
                    for (let i = 0; i < radioLabels.length; i++) {
                        const radioLabel = radioLabels[i];
                        if (radioLabel.textContent?.trim().includes(targetValue) || targetValue.includes(radioLabel.textContent?.trim())) {
                            if (i < radioInputs.length) {
                                targetRadioInput = radioInputs[i];
                                targetRadioElement = radioLabel.closest('.el-radio');
                                break;
                            }
                        }
                    }
                }

                if (targetRadioElement) {
                    targetRadioElement.click();
                    console.log(`✅ 已选择单选框: "${targetValue}"`);
                    await this.delay(200);
                    return;
                } else if (targetRadioInput) {
                    targetRadioInput.click();
                    console.log(`✅ 已直接点击单选框输入: "${targetValue}"`);
                    await this.delay(200);
                    return;
                }

                console.log(`❌ 未找到匹配的单选框: ${targetValue}`);

            } catch (error) {
                console.error(`通过增强方法设置单选框值时出错 (${labelText}):`, error);
            }
        }
        async clickConfirmInShippingDialog(dialog) {
            console.log('在弹窗中点击确定按钮');

            try {
                const dialogFooter = dialog.querySelector('.el-dialog__footer');
                if (!dialogFooter) {
                    console.log('❌ 未找到弹窗底部区域');
                    return;
                }
                const confirmBtn = Array.from(dialogFooter.querySelectorAll('button'))
                    .find(btn => btn.textContent?.includes('确定'));

                if (confirmBtn) {
                    console.log(`✅ 找到确定按钮: "${confirmBtn.textContent?.trim()}"`);
                    confirmBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    confirmBtn.click();
                    console.log('✅ 已点击确定按钮');
                    await this.delay(200);
                    return true;
                } else {
                    console.log('❌ 未找到确定按钮');
                }

                throw new Error('未找到可用的确定按钮');
            } catch (error) {
                console.error('点击确定按钮时出错:', error);
                throw error;
            }
        }
        //async waitForDialogClose() {
        //     const maxWaitTime = 3000; // 增加超时时间
        //     const startTime = Date.now();
        //     let consecutiveChecks = 0; // 连续检查次数
        //     const requiredConsecutiveChecks = 3; // 需要连续3次检查都确认弹窗已关闭

        //     return new Promise((resolve) => {
        //         const checkClose = () => {
        //             const dialogs = Array.from(document.querySelectorAll('[role="dialog"], .el-dialog__wrapper'));
        //             const anyVisible = dialogs.some(d => {
        //                 const style = window.getComputedStyle(d);
        //                 return style.display !== 'none' &&
        //                     style.visibility !== 'hidden' &&
        //                     style.opacity !== '0' &&
        //                     d.offsetWidth > 0 &&
        //                     d.offsetHeight > 0;
        //             });

        //             if (!anyVisible) {
        //                 consecutiveChecks++;
        //                 console.log(`✅ 弹窗关闭检查 ${consecutiveChecks}/${requiredConsecutiveChecks}`);
        //                 if (consecutiveChecks >= requiredConsecutiveChecks) {
        //                     console.log('✅ 弹窗已完全关闭');
        //                     resolve();
        //                     return;
        //                 }
        //             } else {
        //                 consecutiveChecks = 0;
        //                 const visibleDialogs = dialogs.filter(d => {
        //                     const style = window.getComputedStyle(d);
        //                     return style.display !== 'none' &&
        //                         style.visibility !== 'hidden' &&
        //                         style.opacity !== '0';
        //                 });

        //                 if (visibleDialogs.length > 0) {
        //                     console.log(`⏳ 仍有 ${visibleDialogs.length} 个弹窗可见，继续等待...`);
        //                 }
        //             }

        //             if (Date.now() - startTime > maxWaitTime) {
        //                 console.warn('⚠️ 等待弹窗关闭超时，强制继续');
        //                 this.forceCloseAllDialogs();

        //                 resolve(); // 超时也继续，避免卡死
        //                 return;
        //             }

        //             setTimeout(checkClose, 200); // 减少检查间隔，提高响应速度
        //         };

        //         checkClose();
        //     });
        // }
        // forceCloseAllDialogs() {
        //     console.log('🔧 尝试强制关闭所有弹窗');
        //     const dialogs = document.querySelectorAll('[role="dialog"], .el-dialog__wrapper');

        //     dialogs.forEach(dialog => {
        //         try {
        //             const closeButton = dialog.querySelector('.el-dialog__headerbtn, .el-icon-close, [aria-label="Close"]');
        //             if (closeButton) {
        //                 closeButton.click();
        //                 console.log('✅ 点击了弹窗关闭按钮');
        //             }
        //             const cancelButton = dialog.querySelector('.el-button--default, .el-button--cancel, [class*="cancel"]');
        //             if (cancelButton) {
        //                 cancelButton.click();
        //                 console.log('✅ 点击了弹窗取消按钮');
        //             }
        //             setTimeout(() => {
        //                 const style = window.getComputedStyle(dialog);
        //                 if (style.display !== 'none') {
        //                     dialog.style.display = 'none';
        //                     console.log('🔧 强制隐藏弹窗');
        //                 }
        //             }, 100);
        //         } catch (error) {
        //             console.error('强制关闭弹窗时出错:', error);
        //         }
        //     });
        // }
        async waitForShippingDialog() {
            console.log('⏳ 等待一键发运弹窗出现');
            const maxWaitTime = 8000;
            const startTime = Date.now();

            return new Promise((resolve, reject) => {
                const checkDialog = () => {
                    const dialogWrappers = document.querySelectorAll('.el-dialog__wrapper');

                    for (const wrapper of dialogWrappers) {
                        const isVisible = window.getComputedStyle(wrapper).display !== 'none';
                        if (!isVisible) continue;
                        const hasBoxType = wrapper.querySelector('label[for="box_type"]');
                        const hasLogisticsMode = wrapper.querySelector('label[for="logistics_mode"]');

                        if (hasBoxType && hasLogisticsMode) {
                            console.log('✅ 找到一键发运弹窗');
                            setTimeout(resolve, 500); // 等待弹窗内容完全加载
                            return;
                        }
                    }

                    if (Date.now() - startTime > maxWaitTime) {
                        reject(new Error('等待一键发运弹窗超时'));
                        return;
                    }

                    setTimeout(checkDialog, 500);
                };

                checkDialog();
            });
        }
        async confirmOneKeyShippingDialog() {
            console.log('🔄 主动轮询"是否一键发运？"确认对话框');
            await this.delay(100);

            const maxChecks = 60; // 6秒总时长
            for (let i = 0; i < maxChecks; i++) {
                const messageBoxWrapper = document.querySelector('.el-message-box__wrapper');
                if (messageBoxWrapper && window.getComputedStyle(messageBoxWrapper).display !== 'none') {
                    const okBtn = messageBoxWrapper.querySelector('.el-message-box__btns .el-button--primary');

                    if (okBtn) {
                        console.log('✅ 找到"是否一键发运？"确认对话框的确定按钮');
                        okBtn.click();
                        console.log('✅ 已点击"确定"按钮');
                        await this.delay(200);
                        return true;
                    }
                }
                await this.delay(100);
            }

            console.log('⏭️ 未检测到确认对话框，继续后续流程');
            return false;
        }
        async getSelectedPickingOrders() {
            console.log('🔍 获取选中的拣货单...');

            this.selectedOrders = [];
            const table = document.querySelector('.el-table__body') ||
                         document.querySelector('.el-table') ||
                         document.querySelector('table');

            if (!table) {
                console.error('❌ 未找到拣货单表格');
                throw new Error('未找到拣货单表格');
            }
            const rows = table.querySelectorAll('tbody tr');
            console.log(`找到 ${rows.length} 行数据`);

            let selectedCount = 0;

            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const checkbox = row.querySelector('.el-checkbox input[type="checkbox"]');
                if (checkbox && checkbox.checked) {
                    selectedCount++;
                    const orderInfo = this.extractOrderInfoFromRow(row, i);
                    if (orderInfo && orderInfo.operateButton) {
                        this.selectedOrders.push(orderInfo);
                        console.log(`✅ 添加选中的订单: ${orderInfo.pickingNumber}`);
                    } else {
                        console.log(`⚠️ 订单信息不完整，跳过: 行 ${i + 1}`);
                    }
                }
            }

            console.log(`✅ 找到 ${this.selectedOrders.length} 个有效的选中拣货单（共 ${selectedCount} 个选中的行）`);

            if (this.selectedOrders.length === 0) {
                throw new Error('未找到有效的选中拣货单，请确保已选择订单且订单有操作按钮');
            }

            return this.selectedOrders;
        }
        extractOrderInfoFromRow(row, index) {
            try {
                const cells = row.querySelectorAll('td');
                console.log(`🔍 分析第 ${index + 1} 行，共 ${cells.length} 个单元格`);

                const orderInfo = {
                    index: index,
                    rowElement: row,
                    checkbox: row.querySelector('.el-checkbox input[type="checkbox"]'),
                    pickingNumber: cells[4]?.textContent?.trim() || `订单-${index + 1}`,
                    operateButton: this.findOperateButtonInRow(cells[2])
                };

                console.log(`✅ 提取订单信息: ${orderInfo.pickingNumber}`, {
                    hasCheckbox: !!orderInfo.checkbox,
                    hasOperateButton: !!orderInfo.operateButton,
                    checkboxChecked: orderInfo.checkbox?.checked
                });

                return orderInfo;
            } catch (error) {
                console.error('提取订单信息失败:', error);
                return null;
            }
        }
        findOperateButtonInRow(cell) {
            if (!cell) return null;
            const buttons = cell.querySelectorAll('.el-button');
            console.log(`🔍 在单元格中找到 ${buttons.length} 个按钮`);

            for (let button of buttons) {
                const icon = button.querySelector('.el-icon-shopping-cart-full');
                if (icon) {
                    console.log('✅ 找到购物车按钮（拣货按钮）');
                    return button;
                }
            }

            console.log('❌ 未找到拣货按钮');
            return null;
        }
        updateStatus(message, type = 'waiting') {
            const statusElement = document.getElementById('automationStatus');
            if (statusElement) {
                statusElement.textContent = message;
                statusElement.className = `status-indicator status-${type}`;
            }
            console.log(`🤖 ${message}`);
        }

        // 在类中添加优化后的delay方法
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, Math.min(ms, 500))); // 限制最大等待时间
        }

        setupKeyboardListeners() {
            if (this.keyboardHandler) {
                document.removeEventListener('keydown', this.keyboardHandler);
            }
            this.keyboardHandler = (e) => {
                if (e.ctrlKey && e.shiftKey) {
                    switch(e.key) {
                        case 'R':
                            e.preventDefault();
                            this.executeAction('refreshDetection');
                            break;
                        case 'M':
                        case 'm':
                            e.preventDefault();
                            this.toggleMinimize();
                            break;
                        case 'C':
                        case 'c':
                            e.preventDefault();
                            this.toggleCollapse();
                            break;
                    }
                }
            };

            document.addEventListener('keydown', this.keyboardHandler);
        }
        async refreshPageDetection() {
            this.updateStatus('正在重新检测页面...', 'running');
            this.panelInjected = false;
            this.pageButtonInjected = false;
            this.transferInButtonInjected = false; // 添加调拨入库按钮重置
            this.lastInjectionTime = 0;
            await this.delay(800);
            const oldPage = this.currentPage;
            this.detectCurrentPage();
            this.injectControlPanel();
            if (this.currentPage === 'picking') {
                this.injectPageBatchButton();
            } else if (this.currentPage === 'transferIn') {
                this.injectTransferInBatchButton();
            }

            if (oldPage !== this.currentPage) {
                this.updateStatus(`页面类型已变更: ${oldPage} -> ${this.currentPage}`, 'running');
            } else {
                this.updateStatus(`页面检测完成: ${this.currentPage}`, 'waiting');
            }
        }
        // showDebugInfo() {
        //     const info = `
        //     当前页面: ${this.currentPage}
        //     面板状态: ${this.panelInjected ? '已注入' : '未注入'}
        //     页面按钮状态: ${this.pageButtonInjected ? '已注入' : '未注入'}
        //     运行状态: ${this.isRunning ? '运行中' : '空闲'}
        //     URL: ${window.location.href}
        //     最后注入: ${new Date(this.lastInjectionTime).toLocaleTimeString()}
        //     用户代理: ${navigator.userAgent}
        //     `;
        //     console.log('🐛 调试信息:', info);
        //     this.updateStatus('调试信息已输出到控制台', 'waiting');
        // }

        // 判断是否为月末最后一天
        isLastDayOfMonth() {
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            
            // 如果明天是月份的第一天，那么今天就是月末最后一天
            return tomorrow.getDate() === 1;
        }

    }
    function initializeStableAutomation() {
        if (window.erpAutomationInstance) {
            console.log('🔁 自动化实例已存在，跳过初始化');
            return;
        }

        console.log('🎯 启动增强版ERP自动化系统...');
        window.erpAutomationInstance = new StableVueERPAutomation();
    }
    function setupAutomationStartup() {
        if (window.automationStarted) {
            console.log('🔄 自动化启动逻辑已设置，跳过重复设置');
            return;
        }
        window.automationStarted = true;
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(initializeStableAutomation, 1000);
            });
        } else {
            setTimeout(initializeStableAutomation, 500);
        }
    }
    window.startStableERPAutomation = initializeStableAutomation;

    window.restartERPAutomation = () => {
        if (window.erpAutomationInstance) {
            if (window.erpAutomationInstance.observer) {
                window.erpAutomationInstance.observer.disconnect();
            }
            if (window.erpAutomationInstance.routeCheckInterval) {
                clearInterval(window.erpAutomationInstance.routeCheckInterval);
            }
            if (window.erpAutomationInstance.routeObserver) {
                window.erpAutomationInstance.routeObserver.disconnect();
            }
            if (window.erpAutomationInstance.keyboardHandler) {
                document.removeEventListener('keydown', window.erpAutomationInstance.keyboardHandler);
            }
            window.erpAutomationInstance = null;
        }
        window.automationStarted = false;
        setupAutomationStartup();
    };
    setupAutomationStartup();


})();
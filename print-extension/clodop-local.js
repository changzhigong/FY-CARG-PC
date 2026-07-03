// CLodop 打印控件的本地实现 - 扩展版
// 基于真实 CLodopfuncs.js 的功能进行本地适配

// 全局变量定义
var CLODOP = {
    // 基本属性
    strWebPageID: "7BCAAAG",
    strTaskID: "",
    strHostURI: "http://localhost:8000",
    VERSION: "6.5.7.2",
    IVERSION: "6572", 
    CVERSION: "6.5.7.2",
    HTTPS_STATUS: 0,
    VERSION_EXT: true,
    iBaseTask: 0,
    timeThreshold: 5,
    Priority: 0,
    blIslocal: true,
    Iframes: [],
    ItemDatas: {},
    PageData: {},
    defStyleJson: {},
    PageDataEx: {},
    ItemCNameStyles: {},
    blWorking: false,
    blNormalItemAdded: false,
    blTmpSelectedIndex: null,
    Caption: null,
    Color: null,
    CompanyName: null,
    strBroadcastMS: null,
    Border: null,
    Inbrowse: null,
    webskt: null,
    SocketEnable: false,
    SocketOpened: false,
    NoClearAfterPrint: false,
    On_Return_Remain: false,
    On_Broadcast_Remain: false,
    On_Return: null,
    Result: null,
    OBO_Mode: 1,
    blOneByone: false,
    DelimChar: "\f\f",
    
    // 模拟的打印机列表 - 使用本地浏览器检测到的打印机
    Printers: {
        "default": "0",
        "list": [
            {
                "name": "EPSON LQ-630K ESC/P2",
                "DriverName": "EPSON LQ-630K ESC/P2",
                "PortName": "USB001",
                "Orientation": "1",
                "PaperSize": "9",
                "PaperLength": "2970",
                "PaperWidth": "2100",
                "Copies": "1",
                "DefaultSource": "15",
                "PrintQuality": "600",
                "Color": "2",
                "Duplex": "1",
                "FormName": "Letter",
                "Comment": "",
                "DriverVersion": "1539",
                "DCOrientation": "90",
                "MaxExtentWidth": "2970",
                "MaxExtentLength": "4318",
                "MinExtentWidth": "1397",
                "MinExtentlength": "2100",
                "pagelist": [
                    {"name": "A4"},
                    {"name": "A3"},
                    {"name": "A5"},
                    {"name": "Letter"}
                ],
                "subdevlist": []
            }
        ]
    },
    
    // 错误消息
    altMessageWebSocketInvalid: "WebSocket没准备好，请稍后重试!",
    altMessageNoReadWriteFile: "不能远程读写文件!",
    altMessageNoReadFile: "不能远程读文件!",
    altMessageNoWriteFile: "不能远程写文件!",
    altMessageNoPrintDesign: "不能远程打印设计!",
    altMessageNoPrintSetup: "不能远程打印维护!",
    altMessageSomeWindowExist: "有窗口已打开，先关闭它(持续如此时请刷新页面)!",
    altMessageBusy: "上一个请求正忙，请稍后再试！",
    
    // 获取浏览器信息
    Browser: (function(){
        var ua = navigator.userAgent;
        var isOpera = Object.prototype.toString.call(window.opera) == "[object Opera]";
        return {
          IE:             !!window.attachEvent && !isOpera,
          Opera:          isOpera,
          WebKit:         ua.indexOf("AppleWebKit/") > -1,
          Gecko:          ua.indexOf("Gecko") > -1 && ua.indexOf("KHTML") === -1,
          MobileSafari:   /Apple.*Mobile/.test(ua)
        };
    })(),
    
    // 获取任务ID
    GetTaskID: function(){
        if (!this.strTaskID || this.strTaskID === ""){
            var dt = new Date();
            this.iBaseTask++;
            this.strTaskID = "" + dt.getHours() + dt.getMinutes() + dt.getSeconds() + "_" + this.iBaseTask;
        }
        return this.strWebPageID + this.strTaskID;
    },
    
    // 初始化
    DoInit: function() {
        this.strTaskID = "";
        if (this.NoClearAfterPrint) return;
        this.ItemDatas = {"count": 0};
        this.PageData = {};
        this.ItemCNameStyles = {};
        this.defStyleJson = {"beginpage": 0, "beginpagea": 0};
        this.blNormalItemAdded = false;
    },
    
    // 打印初始化
    PRINT_INIT: function(strPrintTask) {
        return this.PRINT_INITA(null, null, null, null, strPrintTask);
    },
    
    PRINT_INITA: function(Top, Left, Width, Height, strPrintTask) {
        if (Top === undefined || Top === null) Top = "";
        if (Left === undefined || Left === null) Left = "";
        if (Width === undefined || Width === null) Width = "";
        if (Height === undefined || Height === null) Height = "";
        if (strPrintTask === undefined || strPrintTask === null) strPrintTask = "";
        
        this.NoClearAfterPrint = false;
        this.DoInit();
        this.PageData["top"] = Top;
        this.PageData["left"] = Left;
        this.PageData["width"] = Width;
        this.PageData["height"] = Height;
        this.PageData["printtask"] = strPrintTask;
        return true;
    },
    
    // 设置打印模式
    SET_PRINT_MODE: function(strModeType, ModeValue) {
        if (strModeType === undefined || strModeType === null) strModeType = "";
        if (ModeValue === undefined || ModeValue === null) ModeValue = "";
        if (strModeType === "") return false;
        
        strModeType = strModeType.toLowerCase();
        this.PageData[strModeType] = ModeValue;
        
        if (strModeType === "noclear_after_print") this.NoClearAfterPrint = ModeValue;
        return true;
    },
    
    // 添加打印文本
    ADD_PRINT_TEXT: function(top, left, width, height, strText) {
        return this.AddItemArray(2, top, left, width, height, strText);
    },
    
    // 添加HTML内容
    ADD_PRINT_HTM: function(top, left, width, height, strHTML) {
        return this.AddItemArray(4, top, left, width, height, strHTML);
    },
    
    // 添加打印HTML
    ADD_PRINT_HTML: function(top, left, width, height, strHTML) {
        return this.AddItemArray(1, top, left, width, height, strHTML);
    },
    
    // 添加打印表格
    ADD_PRINT_TABLE: function(top, left, width, height, strHTML) {
        return this.AddItemArray(6, top, left, width, height, strHTML);
    },
    
    // 添加新页面
    NewPage: function() {
        var blSomeNormal = false;
        var noItemType;
        
        for (var vItemNO in this.ItemDatas) {
            if (vItemNO === "count") {
                noItemType = false; 
            } else {
                noItemType = true;
            }
            
            for (var vItemxx in this.ItemDatas[vItemNO]) {
                if (vItemxx === "itemtype") {
                    noItemType = false;
                    if ((this.ItemDatas[vItemNO][vItemxx] === 0) || 
                        (this.ItemDatas[vItemNO][vItemxx] === 4)) {
                        blSomeNormal = true;
                        break;
                    }
                }
            }
            
            if (noItemType) blSomeNormal = true;
            if (blSomeNormal) break;
        }
        
        if (blSomeNormal) this.defStyleJson["beginpage"] = this.defStyleJson["beginpage"] + 1;
        return true;
    },
    
    // 设置打印样式
    SET_PRINT_STYLE: function(strStyleName, StyleValue) {
        if (strStyleName === undefined || strStyleName === null) strStyleName = "";
        if (StyleValue === undefined || StyleValue === null) StyleValue = "";
        if (strStyleName === "") return false;
        
        strStyleName = strStyleName.toLowerCase();
        this.defStyleJson[strStyleName] = StyleValue;
        return true;
    },
    
    // 设置单个元素的打印样式
    SET_PRINT_STYLEA: function(ItemNo, strKey, Value) {
        if (ItemNo === undefined || ItemNo === null) ItemNo = "";
        if (strKey === undefined || strKey === null) strKey = "";
        if (Value === undefined || Value === null) Value = "";
        if (ItemNo === "" || strKey === "") return false;
        
        if (this.ItemDatas["count"] <= 0) {
            if (this.PageData["add_print_program_data"] !== undefined) {
                this.ItemCNameStyles[strKey.toLowerCase() + "-" + ItemNo] = Value;
                return true;
            } else {
                return false;
            }
        }
        
        strKey = strKey.toLowerCase();
        if (strKey === "type") return false;
        var blResult = false;
        
        if (ItemNo === 0) {
            ItemNo = this.ItemDatas["count"];
        }
        
        for (var vItemNO in this.ItemDatas) {
            var ItemName = this.ItemDatas[vItemNO]["itemname"];
            if ((ItemNo === vItemNO) || 
                (ItemNo === ItemName) || 
                ((typeof ItemNo === "string") && (typeof ItemName === "string") && 
                (ItemNo.toUpperCase() === ItemName.toUpperCase()))) {
                this.ItemDatas[vItemNO][strKey] = Value;
                blResult = true;
            }
        }
        
        return blResult;
    },
    
    // 设置打印页面大小
    SET_PRINT_PAGESIZE: function(intOrient, PageWidth, PageHeight, strPageName) {
        if (intOrient !== undefined && intOrient !== null) {
            this.PageData["orient"] = intOrient;
        }
        if (PageWidth !== undefined && PageWidth !== null) {
            this.PageData["pagewidth"] = PageWidth;
        }
        if (PageHeight !== undefined && PageHeight !== null) {
            this.PageData["pageheight"] = PageHeight;
        }
        if (strPageName !== undefined && strPageName !== null) {
            this.PageData["pagename"] = strPageName;
        }
        return true;
    },
    
    // 设置打印机索引
    SET_PRINTER_INDEX: function(strName, strKeyModeName) {
        if (!this.Printers) return false;
        
        if (!strKeyModeName) strKeyModeName = "printerindex";
        strName = strName + "";
        strName = strName.replace(/^\s+|\s+$/g, "");
        
        var iPos = strName.indexOf(",");
        var strNameOrNO = strName;
        if (iPos > -1) strNameOrNO = strName.slice(0, iPos);
        
        if (strNameOrNO === "-1") {
            this.PageData[strKeyModeName] = this.Printers["default"];
            if (iPos > -1) this.PageData["printersubid"] = strName.slice(iPos + 1);
            return true;
        } else {
            for (var vNO in this.Printers["list"]) {
                var strPrinterName = this.Printers["list"][vNO].name;
                if (!strPrinterName) continue;
                
                if ((strPrinterName.replace(/\\/g, "") === strNameOrNO.replace(/\\/g, "")) || 
                    (vNO === strNameOrNO)) {
                    this.PageData[strKeyModeName] = strPrinterName;
                    if (iPos > -1) this.PageData["printersubid"] = strName.slice(iPos + 1);
                    return true;
                }
            }
            return false;
        }
    },
    
    SET_PRINTER_INDEXA: function(strName) {
        return this.SET_PRINTER_INDEX(strName, "printerindexa");
    },
    
    // 获取打印机数量
    GET_PRINTER_COUNT: function() {
        if (!this.Printers) return 0;
        return this.Printers["list"].length;
    },
    
    // 获取打印机名称
    GET_PRINTER_NAME: function(intNO) {
        if (!this.Printers) return "";
        
        if (typeof intNO == "string" && intNO.indexOf(":") > -1) {
            var strPPname = intNO.slice(intNO.indexOf(":") + 1);
            intNO = intNO.slice(0, intNO.indexOf(":"));
            
            if (intNO === "-1") {
                return this.Printers["list"][this.Printers["default"]][strPPname];
            } else {
                return this.Printers["list"][intNO][strPPname];
            }
        } else {
            if (intNO === -1) {
                return this.Printers["list"][this.Printers["default"]].name;
            } else if (intNO >= 0 && intNO < this.Printers["list"].length) {
                return this.Printers["list"][intNO].name;
            } else {
                return "Printer NO. overflow";
            }
        }
    },
    
    // 内部方法 - 添加项目到数组
    AddItemArray: function(itemType, top, left, width, height, strContent, itemName, type, intPenStyle, intPenWidth, intColor, strAngle, intBarCodeType, strChartType) {
        if (this.blWorking) {
            alert(this.altMessageBusy);
            return null;
        }
        
        var tResult = null;
        var ItemCount = this.ItemDatas["count"] || 0;
        this.ItemDatas[ItemCount] = {
            "itemtype": itemType,
            "top": top,
            "left": left,
            "width": width,
            "height": height,
            "content": strContent
        };
        
        if (itemName !== undefined && itemName !== null) {
            this.ItemDatas[ItemCount]["itemname"] = itemName;
        }
        
        if (type !== undefined && type !== null) {
            this.ItemDatas[ItemCount]["type"] = type;
        }
        
        if (intPenStyle !== undefined && intPenStyle !== null) {
            this.ItemDatas[ItemCount]["penstyle"] = intPenStyle;
        }
        
        if (intPenWidth !== undefined && intPenWidth !== null) {
            this.ItemDatas[ItemCount]["penwidth"] = intPenWidth;
        }
        
        if (intColor !== undefined && intColor !== null) {
            this.ItemDatas[ItemCount]["color"] = intColor;
        }
        
        if (strAngle !== undefined && strAngle !== null) {
            this.ItemDatas[ItemCount]["angle"] = strAngle;
        }
        
        if (intBarCodeType !== undefined && intBarCodeType !== null) {
            this.ItemDatas[ItemCount]["barcodetype"] = intBarCodeType;
        }
        
        if (strChartType !== undefined && strChartType !== null) {
            this.ItemDatas[ItemCount]["charttype"] = strChartType;
        }
        
        this.ItemDatas["count"] = ItemCount + 1;
        this.blNormalItemAdded = true;
        return this.GetTaskID();
    },
    
    // 打印预览
    PREVIEW: function(destView, iWidth, iHigh, iOption) {
        if (this.blWorking) {
            alert(this.altMessageBusy);
            return null;
        }
        
        var tResult = null;
        // 直接调用本地打印预览
        try {
            this.PRINT();
            tResult = this.GetTaskID();
        } catch (e) {
            console.error("预览失败:", e);
            tResult = null;
        }
        
        this.DoInit();
        this.blWorking = false;
        return tResult;
    },
    
    // // 执行打印 - 核心功能
    // PRINT: function() {
    //     if (this.blWorking) {
    //         alert(this.altMessageBusy);
    //         return null;
    //     }
        
    //     var tResult = null;
        
    //     try {
    //         // 创建打印窗口
    //         const printWindow = window.open('', '_blank');
            
    //         if (!printWindow) {
    //             throw new Error('无法打开打印窗口，请检查浏览器是否阻止了弹出窗口');
    //         }
            
    //         // 构建打印页面HTML
    //         let printHTML = this.GeneratePrintHTML();
            
    //         // 将HTML写入新窗口
    //         printWindow.document.write(printHTML);
    //         printWindow.document.close();
            
    //         // 等待内容加载完成后打印
    //         printWindow.onload = function() {
    //             setTimeout(() => {
    //                 printWindow.print();
    //             }, 500);
    //         };
            
    //         tResult = this.GetTaskID();
    //     } catch (e) {
    //         console.error("打印失败:", e);
    //         alert("打印失败: " + e.message);
    //         tResult = null;
    //     }
        
    //     this.DoInit();
    //     this.blWorking = false;
    //     return tResult;
    // },
    // 执行打印 - 核心功能
    PRINT: function () {
        if (this.blWorking) {
            alert(this.altMessageBusy);
            return null;
        }

        var tResult = null;

        try {
            // 生成打印HTML
            let printHTML = this.GeneratePrintHTML();

            // 创建一个隐藏的iframe用于打印
            const printFrame = document.createElement('iframe');
            printFrame.style.position = 'absolute';
            printFrame.style.left = '-9999px';
            printFrame.style.top = '-9999px';
            printFrame.style.width = '0px';
            printFrame.style.height = '0px';
            document.body.appendChild(printFrame);

            // 将HTML写入iframe
            const frameDoc = printFrame.contentDocument || printFrame.contentWindow.document;
            frameDoc.open();
            frameDoc.write(printHTML);
            frameDoc.close();

            // 等待内容加载完成后打印
            printFrame.onload = function () {
                setTimeout(() => {
                    printFrame.contentWindow.print();
                    // 打印完成后移除iframe
                    setTimeout(() => {
                        document.body.removeChild(printFrame);
                    }, 1000);
                }, 500);
            };

            tResult = this.GetTaskID();
        } catch (e) {
            console.error("打印失败:", e);
            alert("打印失败: " + e.message);
            tResult = null;
        }

        this.DoInit();
        this.blWorking = false;
        return tResult;
    },
    
    // 生成打印HTML - 核心功能
    GeneratePrintHTML: function() {
        let html = `
          <!DOCTYPE html>
          <html lang="zh-CN">
          <head>
            <meta charset="UTF-8">
            <title>${this.PageData["printtask"] || "打印文档"}</title>
            <style>
              body {
                margin: 0;
                padding: ${this.PageData["top"] || '10mm'} ${this.PageData["left"] || '10mm'};
                font-family: '${this.defStyleJson["fontname"] || "Microsoft YaHei"}', sans-serif;
                font-size: ${this.defStyleJson["fontsize"] || "12pt"};
              }
              
              .print-page {
                page-break-after: always;
                margin-bottom: 20mm;
              }
              
              .print-page:last-child {
                page-break-after: auto;
              }
              
              @media print {
                body {
                  margin: ${this.PageData["top"] || '10mm'} ${this.PageData["left"] || '10mm'};
                  padding: 0;
                }
                
                .print-page {
                  page-break-after: always;
                  margin-bottom: 0;
                }
                
                .print-page:last-child {
                  page-break-after: auto;
                }
              }
            </style>
          </head>
          <body>
        `;
        
        // 添加打印元素
        var pageCount = 0;
        var hasPageBreak = false;
        
        for (var itemIndex in this.ItemDatas) {
            if (itemIndex === "count") continue;
            
            var item = this.ItemDatas[itemIndex];
            
            // 如果需要分页
            if (hasPageBreak && pageCount > 0) {
                html += '</div><div class="print-page">';
                hasPageBreak = false;
            }
            
            // 处理不同类型的打印项
            if (item.itemtype === 1 || item.itemtype === 4) { // HTML
                html += this.ProcessHTMLItem(item);
            } else if (item.itemtype === 2) { // 文本
                html += this.ProcessTextItem(item);
            } else if (item.itemtype === 6) { // 表格
                html += this.ProcessTableItem(item);
            }
            
            // 检查是否需要分页
            if (this.defStyleJson["beginpage"] > pageCount) {
                pageCount = this.defStyleJson["beginpage"];
                hasPageBreak = true;
            }
        }
        
        html += `
          </body>
          </html>
        `;
        
        return html;
    },
    
    // 处理HTML项
    ProcessHTMLItem: function(item) {
        let style = this.GetItemStyle(item);
        return `<div style="${style}">${item.content}</div>`;
    },
    
    // 处理文本项
    ProcessTextItem: function(item) {
        let style = this.GetItemStyle(item);
        return `<div style="${style}">${item.content}</div>`;
    },
    
    // 处理表格项
    ProcessTableItem: function(item) {
        let style = this.GetItemStyle(item);
        return `<div style="${style}">${item.content}</div>`;
    },
    
    // 获取项目样式
    GetItemStyle: function(item) {
        let style = `
            position: absolute;
            top: ${item.top};
            left: ${item.left};
            width: ${item.width || 'auto'};
            height: ${item.height || 'auto'};
        `;
        
        // 添加字体样式
        if (item.fontname) style += `font-family: ${item.fontname};`;
        if (item.fontsize) style += `font-size: ${item.fontsize};`;
        if (item.fontcolor) style += `color: ${item.fontcolor};`;
        if (item.bold) style += `font-weight: bold;`;
        if (item.italic) style += `font-style: italic;`;
        if (item.underline) style += `text-decoration: underline;`;
        
        // 添加对齐方式
        if (item.alignment) {
            switch (item.alignment) {
                case 1: style += "text-align: left;"; break;
                case 2: style += "text-align: center;"; break;
                case 3: style += "text-align: right;"; break;
                default: style += "text-align: left;"; break;
            }
        }
        
        return style;
    },
    
    // 获取任务ID
    GetTaskID: function() {
        if (!this.strTaskID || this.strTaskID === "") {
            var dt = new Date();
            this.iBaseTask++;
            this.strTaskID = "" + dt.getHours() + dt.getMinutes() + dt.getSeconds() + "_" + this.iBaseTask;
        }
        return this.strWebPageID + this.strTaskID;
    }
};

// 导出全局变量
if (typeof window !== 'undefined') {
    window.getLodop = function() {
        return CLODOP;
    };
    
    // 兼容性处理
    window.GET_LODOP = function(oOBJECT, oEMBED) {
        if (oOBJECT !== undefined && typeof (oOBJECT.VERSION) !== "undefined") {
            return oOBJECT;
        }
        
        if (oEMBED !== undefined && typeof (oEMBED.VERSION) !== "undefined") {
            return oEMBED;
        }
        
        return CLODOP;
    };
    
    // 检查是否支持WebSocket（虽然本地不需要）
    window.CLODOP = CLODOP;
}

// 导出Node.js模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getLodop: function() {
            return CLODOP;
        },
        CLODOP: CLODOP
    };
}

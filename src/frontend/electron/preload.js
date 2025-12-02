const { contextBridge, ipcRenderer } = require('electron')

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 发送消息到后端
  sendToBackend: (message) => ipcRenderer.invoke('send-to-backend', message),
  
  // 接收后端响应
  onBackendResponse: (callback) => {
    ipcRenderer.on('backend-response', (event, data) => callback(data))
  },
  
  // 窗口控制
  windowMinimize: () => ipcRenderer.invoke('window-minimize'),
  windowMaximize: () => ipcRenderer.invoke('window-maximize'),
  windowClose: () => ipcRenderer.invoke('window-close'),
  windowIsMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  
  // 平台信息
  platform: process.platform,
  
  // 文件对话框
  showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options)
})


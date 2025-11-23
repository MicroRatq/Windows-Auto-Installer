const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 发送请求到Python后端
  sendToPython: (action, data) => {
    return ipcRenderer.invoke('python-request', { action, data });
  },

  // 监听Python后端响应
  onPythonResponse: (callback) => {
    ipcRenderer.on('python-response', (event, data) => {
      callback(data);
    });
  },

  // 监听Python后端错误
  onPythonError: (callback) => {
    ipcRenderer.on('python-error', (event, error) => {
      callback(error);
    });
  },

  // 移除监听器
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },

  // 窗口控制
  windowMinimize: () => {
    ipcRenderer.invoke('window-minimize');
  },
  windowMaximize: () => {
    ipcRenderer.invoke('window-maximize');
  },
  windowClose: () => {
    ipcRenderer.invoke('window-close');
  },
  windowIsMaximized: () => {
    return ipcRenderer.invoke('window-is-maximized');
  },

  // 监听窗口最大化状态变化
  onWindowMaximized: (callback) => {
    ipcRenderer.on('window-maximized', (event, isMaximized) => {
      callback(isMaximized);
    });
  }
});


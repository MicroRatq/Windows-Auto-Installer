const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow = null
let pythonProcess = null

// 启动Python后端
function startPythonBackend() {
  const isDev = process.env.NODE_ENV === 'development'
  const backendPath = isDev
    ? path.join(__dirname, '../../backend/main.py')
    : path.join(__dirname, '../../backend/main.exe')
  
  const options = {
    cwd: path.join(__dirname, '../..'),
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
  }
  
  if (isDev) {
    // 开发环境：使用conda环境中的python
    // 在Windows上，需要先激活conda环境再运行python
    const condaActivate = process.platform === 'win32' 
      ? `conda activate win-auto-installer && python "${backendPath}"`
      : `source activate win-auto-installer && python "${backendPath}"`
    
    pythonProcess = spawn(condaActivate, [], options)
  } else {
    // 生产环境：直接运行exe
    pythonProcess = spawn(backendPath, [], options)
  }
  
  // 处理Python输出
  pythonProcess.stdout.on('data', (data) => {
    const message = data.toString().trim()
    if (message) {
      try {
        const json = JSON.parse(message)
        // 发送到渲染进程
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('backend-response', json)
        }
      } catch (e) {
        // 非JSON输出，可能是日志
        console.log('[Python]', message)
      }
    }
  })
  
  pythonProcess.stderr.on('data', (data) => {
    console.error('[Python Error]', data.toString())
  })
  
  pythonProcess.on('exit', (code) => {
    console.log(`[Python] 进程退出，代码: ${code}`)
    if (code !== 0 && code !== null) {
      // 非正常退出，尝试重启
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          startPythonBackend()
        }
      }, 3000)
    }
  })
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    frame: false,  // 无边框窗口
    titleBarStyle: 'hidden',
    backgroundColor: '#181818',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })
  
  // 加载应用
  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
  
  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// IPC处理：发送消息到Python后端
ipcMain.handle('send-to-backend', async (event, message) => {
  return new Promise((resolve, reject) => {
    if (!pythonProcess || pythonProcess.killed) {
      reject(new Error('Python后端未运行'))
      return
    }
    
    // 发送JSON消息到Python
    const jsonMessage = JSON.stringify(message) + '\n'
    pythonProcess.stdin.write(jsonMessage, (error) => {
      if (error) {
        reject(error)
      } else {
        // 等待响应（通过backend-response事件）
        const timeout = setTimeout(() => {
          reject(new Error('后端响应超时'))
        }, 30000)
        
        const responseHandler = (response) => {
          if (response.id === message.id) {
            clearTimeout(timeout)
            ipcMain.removeListener('backend-response', responseHandler)
            if (response.error) {
              reject(new Error(response.error.message || '后端错误'))
            } else {
              resolve(response.result)
            }
          }
        }
        
        ipcMain.once('backend-response', responseHandler)
      }
    })
  })
})

// 窗口控制
ipcMain.handle('window-minimize', () => {
  if (mainWindow) mainWindow.minimize()
})

ipcMain.handle('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow.maximize()
    }
  }
})

ipcMain.handle('window-close', () => {
  if (mainWindow) mainWindow.close()
})

ipcMain.handle('window-is-maximized', () => {
  return mainWindow ? mainWindow.isMaximized() : false
})

// 应用准备就绪
app.whenReady().then(() => {
  createWindow()
  startPythonBackend()
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 所有窗口关闭时
app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
})


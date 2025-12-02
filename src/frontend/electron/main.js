const { app, BrowserWindow, ipcMain, globalShortcut, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow = null
let pythonProcess = null
const pendingRequests = new Map() // 存储待处理的请求

// 等待Vite服务器就绪
function waitForViteServer(maxRetries = 30, delay = 1000) {
  return new Promise((resolve, reject) => {
    const http = require('http')
    let retries = 0

    console.log('[Electron] 等待Vite服务器启动...')

    function checkServer() {
      // 尝试访问index.html来确认Vite服务器是否就绪
      const req = http.get('http://localhost:5173/index.html', (res) => {
        // 任何响应状态码都表示服务器在运行
        if (res.statusCode === 200) {
          console.log('[Electron] ✓ Vite服务器已就绪 (200)')
          resolve()
        } else if (res.statusCode === 404) {
          // 404可能表示服务器在运行但路径不对，也尝试继续
          console.log('[Electron] ✓ Vite服务器已就绪 (404, 但服务器运行中)')
          resolve()
        } else {
          console.log(`[Electron] Vite服务器响应状态码: ${res.statusCode}, 继续等待...`)
          retry()
        }
      })

      req.on('error', (err) => {
        if (retries % 5 === 0) {
          console.log(`[Electron] 等待Vite服务器... (${retries}/${maxRetries})`)
        }
        retry()
      })

      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }

    function retry() {
      retries++
      if (retries >= maxRetries) {
        console.error('[Electron] ✗ Vite服务器启动超时')
        reject(new Error('Vite服务器启动超时，请检查Vite开发服务器是否正在运行'))
      } else {
        setTimeout(checkServer, delay)
      }
    }

    checkServer()
  })
}

// 启动Python后端
function startPythonBackend() {
  const isDev = process.env.NODE_ENV === 'development'
  const backendPath = isDev
    ? path.join(__dirname, '../../backend/main.py')
    : path.join(__dirname, '../../backend/main.exe')

  const options = {
    cwd: path.join(__dirname, '../..'),
    stdio: ['pipe', 'pipe', 'pipe']
  }

  if (isDev) {
    // 开发环境：使用conda环境中的python
    // 在Windows上，尝试找到conda环境中的python.exe
    const os = require('os')
    const userHome = os.homedir()
    let pythonExe

    if (process.platform === 'win32') {
      // Windows: 尝试多个可能的conda路径
      const possiblePaths = [
        path.join(userHome, '.conda', 'envs', 'win-auto-installer', 'python.exe'),
        path.join(userHome, 'anaconda3', 'envs', 'win-auto-installer', 'python.exe'),
        path.join(userHome, 'miniconda3', 'envs', 'win-auto-installer', 'python.exe'),
        path.join('C:', 'Users', process.env.USERNAME, '.conda', 'envs', 'win-auto-installer', 'python.exe'),
        path.join('C:', 'Users', process.env.USERNAME, 'anaconda3', 'envs', 'win-auto-installer', 'python.exe'),
        path.join('C:', 'Users', process.env.USERNAME, 'miniconda3', 'envs', 'win-auto-installer', 'python.exe')
      ]

      const fs = require('fs')
      for (const possiblePath of possiblePaths) {
        if (fs.existsSync(possiblePath)) {
          pythonExe = possiblePath
          break
        }
      }

      // 如果找不到，使用系统PATH中的python（假设已激活conda环境）
      if (!pythonExe) {
        pythonExe = 'python'
      }
    } else {
      pythonExe = 'python'
    }

    console.log(`[Backend] 使用Python: ${pythonExe}`)
    console.log(`[Backend] 启动脚本: ${backendPath}`)

    try {
      pythonProcess = spawn(pythonExe, [backendPath], options)
    } catch (error) {
      console.error('[Backend] 启动Python进程失败:', error)
      pythonProcess = null
      return
    }
  } else {
    // 生产环境：直接运行exe
    try {
      pythonProcess = spawn(backendPath, [], options)
    } catch (error) {
      console.error('[Backend] 启动后端进程失败:', error)
      pythonProcess = null
      return
    }
  }

  // 处理Python输出
  let buffer = ''
  pythonProcess.stdout.on('data', (data) => {
    buffer += data.toString()
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // 保留最后一个不完整的行

    for (const line of lines) {
      const message = line.trim()
      if (message) {
        try {
          const json = JSON.parse(message)
          // 处理待处理的请求
          if (json.id && pendingRequests.has(json.id)) {
            const pending = pendingRequests.get(json.id)
            pendingRequests.delete(json.id)
            console.log(`[IPC] 收到后端响应 ID=${json.id}:`, JSON.stringify(json))
            if (json.error) {
              console.log(`[IPC] 后端返回错误:`, json.error)
              pending.reject(new Error(json.error.message || '后端错误'))
            } else {
              console.log(`[IPC] 后端返回结果:`, json.result, '类型:', typeof json.result)
              // 返回完整的响应对象，而不是只返回 result
              pending.resolve({
                result: json.result,
                error: json.error
              })
            }
          }
          // 也发送到渲染进程（如果需要）
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('backend-response', json)
          }
        } catch (e) {
          // 非JSON输出，可能是日志
          console.log('[Python]', message)
        }
      }
    }
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error('[Python Error]', data.toString())
  })

  pythonProcess.on('exit', (code) => {
    console.log(`[Python] 进程退出，代码: ${code}`)
    // 清理进程引用
    pythonProcess = null
    // 拒绝所有待处理的请求
    for (const [id, pending] of pendingRequests.entries()) {
      pending.reject(new Error('Python后端进程已退出'))
    }
    pendingRequests.clear()

    if (code !== 0 && code !== null) {
      // 非正常退出，尝试重启
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          startPythonBackend()
        }
      }, 3000)
    }
  })

  pythonProcess.on('error', (error) => {
    console.error('[Python] 进程错误:', error)
    // 清理进程引用
    pythonProcess = null
    // 拒绝所有待处理的请求
    for (const [id, pending] of pendingRequests.entries()) {
      pending.reject(new Error(`Python后端启动失败: ${error.message}`))
    }
    pendingRequests.clear()
  })
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 800, // 增加最小高度，避免二级菜单出现滚动条（顶部栏50px + 折叠按钮43px + 3个菜单组约600px + 设置按钮43px + 边距约50px = 约786px，设置为800px确保安全）
    frame: false,  // 无边框窗口
    titleBarStyle: 'hidden',
    backgroundColor: '#181818',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  // 注册窗口键盘事件（在窗口ready后）
  mainWindow.webContents.on('before-input-event', (event, input) => {
    // F12: 切换开发者工具
    if (input.key === 'F12') {
      event.preventDefault()
      console.log('[Electron] F12 pressed, toggling DevTools')
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools()
      } else {
        mainWindow.webContents.openDevTools()
      }
    }
    // F5: 刷新页面
    else if (input.key === 'F5' && !input.control && !input.shift && !input.alt && !input.meta) {
      event.preventDefault()
      mainWindow.reload()
    }
  })

  // 也尝试注册全局快捷键（F12可能被系统占用，使用全局快捷键作为备用）
  // 延迟注册，确保窗口已创建
  setTimeout(() => {
    const registered = globalShortcut.register('F12', () => {
      console.log('[Electron] F12 global shortcut triggered')
      if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.webContents.isDevToolsOpened()) {
          mainWindow.webContents.closeDevTools()
        } else {
          mainWindow.webContents.openDevTools()
        }
      }
    })

    if (!registered) {
      console.log('[Electron] F12 global shortcut registration failed, using before-input-event instead')
    } else {
      console.log('[Electron] F12 global shortcut registered successfully')
    }
  }, 1000)

  // 也注册全局快捷键作为备用（F5）
  globalShortcut.register('F5', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.reload()
    }
  })

  // Ctrl+R: 刷新页面（备用）
  globalShortcut.register('CommandOrControl+R', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.reload()
    }
  })

  // 加载应用
  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    // 等待Vite服务器就绪
    waitForViteServer().then(() => {
      console.log('[Electron] 加载Vite开发服务器...')
      // 加载Vite开发服务器（Vite会自动提供index.html）
      mainWindow.loadURL('http://localhost:5173/')
      mainWindow.webContents.openDevTools()

      // 监听页面加载完成
      mainWindow.webContents.on('did-finish-load', () => {
        console.log('[Electron] 页面加载完成')
      })

      // 监听加载错误
      mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
        console.error('[Electron] 页面加载失败:', errorCode, errorDescription, validatedURL)
        if (errorCode === -106 || errorCode === -105) {
          // ERR_INTERNET_DISCONNECTED 或 ERR_NAME_NOT_RESOLVED
          console.log('[Electron] 连接失败，等待Vite服务器...')
          setTimeout(() => {
            mainWindow.reload()
          }, 2000)
        } else {
          // 其他错误，尝试直接加载根路径
          console.log('[Electron] 尝试加载根路径...')
          setTimeout(() => {
            mainWindow.loadURL('http://localhost:5173/')
          }, 1000)
        }
      })
    }).catch((error) => {
      console.error('[Electron] Vite服务器启动失败:', error)
      const errorHtml = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Vite服务器未启动</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              display: flex;
              justify-content: center;
              align-items: center;
              height: 100vh;
              margin: 0;
              background: #181818;
              color: #f3f3f3;
            }
            .error-box {
              text-align: center;
              padding: 20px;
            }
            h1 { color: #ff6b6b; }
            button {
              margin-top: 20px;
              padding: 10px 20px;
              background: #4a90e2;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
            }
            button:hover { background: #357abd; }
          </style>
        </head>
        <body>
          <div class="error-box">
            <h1>Vite开发服务器未启动</h1>
            <p>请确保Vite开发服务器正在运行在 http://localhost:5173</p>
            <p>检查"Vite Dev Server"窗口是否有错误信息</p>
            <button onclick="location.reload()">重试</button>
          </div>
        </body>
        </html>
      `
      mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(errorHtml)}`)
    })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // 窗口关闭时注销快捷键
  mainWindow.on('close', () => {
    globalShortcut.unregisterAll()
  })
}

// IPC处理：发送消息到Python后端
ipcMain.handle('send-to-backend', async (event, message) => {
  return new Promise((resolve, reject) => {
    // 检查进程是否存在且未终止
    if (!pythonProcess || pythonProcess.killed) {
      reject(new Error('Python后端未运行'))
      return
    }

    // 检查 stdin 流是否可用
    if (!pythonProcess.stdin || pythonProcess.stdin.destroyed || !pythonProcess.stdin.writable) {
      console.error('[IPC] Python stdin 流不可用')
      reject(new Error('Python后端连接已断开'))
      return
    }

    // 发送JSON消息到Python
    const jsonMessage = JSON.stringify(message) + '\n'

    // 存储待处理的请求
    pendingRequests.set(message.id, { resolve, reject })

    // 超时机制已移除，完全依赖后端超时

    try {
      pythonProcess.stdin.write(jsonMessage, (error) => {
        if (error) {
          pendingRequests.delete(message.id)
          reject(error)
        }
      })
    } catch (error) {
      pendingRequests.delete(message.id)
      reject(error)
    }
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

// 文件对话框
ipcMain.handle('show-open-dialog', async (event, options) => {
  if (!mainWindow) return { canceled: true }
  const result = await dialog.showOpenDialog(mainWindow, options)
  return result
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
  // 注销所有全局快捷键
  globalShortcut.unregisterAll()

  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  // 注销所有全局快捷键
  globalShortcut.unregisterAll()

  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
})


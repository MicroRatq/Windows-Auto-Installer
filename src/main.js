const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const EventEmitter = require('events');

// 创建事件发射器用于Python响应
const pythonResponseEmitter = new EventEmitter();

let mainWindow;
let pythonProcess = null;

function createWindow() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  const windowOptions = {
    width: 1400,
    height: 900,
    frame: false, // 无边框窗口，使用自定义标题栏
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  };
  
  // 如果图标文件存在，添加图标
  if (fs.existsSync(iconPath)) {
    windowOptions.icon = iconPath;
  }
  
  mainWindow = new BrowserWindow(windowOptions);

  mainWindow.loadFile('renderer/index.html');

  // 开发环境下打开开发者工具
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 监听窗口最大化状态变化
  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window-maximized', true);
  });

  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window-maximized', false);
  });
}

function startPythonBackend() {
  // 获取Python可执行文件路径
  // 优先使用conda环境中的python
  let pythonPath = 'python';
  if (process.env.CONDA_PREFIX) {
    pythonPath = path.join(process.env.CONDA_PREFIX, 'python.exe');
  } else if (process.env.PYTHON_PATH) {
    pythonPath = process.env.PYTHON_PATH;
  }

  const scriptPath = path.join(__dirname, 'backend', 'main.py');
  
  console.log('Python path:', pythonPath);
  console.log('Script path:', scriptPath);
  console.log('Working directory:', path.join(__dirname, '..'));
  
  pythonProcess = spawn(pythonPath, [scriptPath], {
    stdio: ['pipe', 'pipe', 'pipe'],
    cwd: path.join(__dirname, '..'),
    shell: false
  });

  let stdoutBuffer = '';
  
  pythonProcess.stdout.on('data', (data) => {
    stdoutBuffer += data.toString();
    
    // 按行处理，每行应该是一个完整的JSON消息
    const lines = stdoutBuffer.split('\n');
    stdoutBuffer = lines.pop() || ''; // 保留最后不完整的行
    
    lines.forEach(line => {
      line = line.trim();
      if (!line) return;
      
      try {
        const message = JSON.parse(line);
        // 发送到主窗口
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('python-response', message);
        }
        // 触发事件发射器
        pythonResponseEmitter.emit('response', message);
      } catch (e) {
        // 非JSON数据，可能是日志输出
        console.log('Python stdout:', line);
      }
    });
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error('Python stderr:', data.toString());
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (error) => {
    console.error('Failed to start Python process:', error);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('python-error', {
        error: 'Failed to start Python backend',
        details: error.message
      });
    }
  });
}

// IPC消息处理：转发到Python后端
ipcMain.handle('python-request', async (event, message) => {
  return new Promise((resolve, reject) => {
    if (!pythonProcess) {
      reject(new Error('Python backend not started'));
      return;
    }

    const requestId = Date.now().toString();
    const request = {
      id: requestId,
      ...message
    };

    // 监听响应
    const responseHandler = (response) => {
      if (response.id === requestId) {
        pythonResponseEmitter.removeListener('response', responseHandler);
        if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response.data);
        }
      }
    };

    pythonResponseEmitter.on('response', responseHandler);

    // 发送请求到Python
    pythonProcess.stdin.write(JSON.stringify(request) + '\n');

    // 超时处理
    setTimeout(() => {
      pythonResponseEmitter.removeListener('response', responseHandler);
      reject(new Error('Request timeout'));
    }, 30000);
  });
});

app.whenReady().then(() => {
  createWindow();
  startPythonBackend();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
});

// 窗口控制
ipcMain.handle('window-minimize', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

ipcMain.handle('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('window-close', () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

ipcMain.handle('window-is-maximized', () => {
  return mainWindow ? mainWindow.isMaximized() : false;
});


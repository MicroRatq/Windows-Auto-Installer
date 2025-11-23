# 前端开发指南

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发模式

```bash
npm start
# 或
npm run dev
```

开发模式下会自动打开开发者工具。

### 3. 调试

#### 使用VS Code/Cursor调试

1. 按 `F5` 或点击调试按钮
2. 选择 "Debug Electron" 配置
3. 可以设置断点进行调试

#### 手动调试

- 主进程调试：在 `main.js` 中设置断点
- 渲染进程调试：在浏览器开发者工具中调试（开发模式自动打开）

## 项目结构

```
src/
├── main.js              # Electron主进程
├── preload.js          # IPC桥接脚本
├── package.json        # 项目配置
├── backend/            # Python后端（与前端通信）
└── renderer/           # 前端UI
    ├── index.html      # 主页面
    ├── css/
    │   └── style.css   # 样式文件
    └── js/
        └── main.js     # 前端逻辑
```

## 开发注意事项

1. **Python后端路径**：确保 `main.js` 中的Python路径正确指向 `backend/main.py`
2. **IPC通信**：前端通过 `window.electronAPI` 与主进程通信
3. **环境变量**：开发模式使用 `NODE_ENV=development` 自动打开开发者工具

## 常见问题

### Python后端无法启动

- 检查Python路径是否正确
- 确保Conda环境已激活
- 查看控制台错误信息

### IPC通信失败

- 检查 `preload.js` 是否正确加载
- 确保 `contextIsolation` 和 `nodeIntegration` 设置正确

### 样式不生效

- 检查CSS文件路径
- 清除浏览器缓存（Ctrl+Shift+R）


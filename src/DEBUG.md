# 前端调试指南

## 快速启动

### 方法1：使用npm脚本（推荐）

```bash
cd src
npm start
```

或使用开发模式（自动打开开发者工具）：

```bash
npm run dev
```

### 方法2：使用启动脚本

```bash
cd src
start.bat
```

### 方法3：使用VS Code/Cursor调试

1. 按 `F5` 启动调试
2. 选择 "Debug Electron" 配置
3. 可以在代码中设置断点

## 调试技巧

### 1. 主进程调试

- 在 `main.js` 中设置断点
- 查看控制台输出（Node.js控制台）
- 检查Python后端启动日志

### 2. 渲染进程调试

- 开发模式会自动打开开发者工具（DevTools）
- 使用 `Ctrl+Shift+I` 手动打开
- 在 `renderer/js/main.js` 中设置断点
- 使用 `console.log()` 输出调试信息

### 3. IPC通信调试

在 `main.js` 中已添加日志输出：
- Python路径
- 脚本路径
- 工作目录

在渲染进程中：
```javascript
console.log('Sending to Python:', action, data);
window.electronAPI.sendToPython(action, data)
  .then(response => console.log('Response:', response))
  .catch(error => console.error('Error:', error));
```

### 4. Python后端调试

- 查看Electron主进程控制台的Python输出
- 检查Python进程是否正常启动
- 查看错误信息

## 常见问题排查

### 问题1：应用无法启动

**检查项：**
- Node.js和npm是否正确安装
- 依赖是否已安装：`npm install`
- 查看控制台错误信息

### 问题2：Python后端无法启动

**检查项：**
- Python路径是否正确（查看控制台日志）
- Conda环境是否激活
- `backend/main.py` 文件是否存在
- Python依赖是否已安装

**解决方案：**
```bash
# 激活Conda环境
conda activate windows-auto-installer

# 安装Python依赖
pip install -r requirements.txt

# 测试Python后端
python src/backend/main.py
```

### 问题3：IPC通信失败

**检查项：**
- `preload.js` 是否正确加载
- `window.electronAPI` 是否可用
- 查看浏览器控制台错误

**调试代码：**
```javascript
if (window.electronAPI) {
  console.log('Electron API available');
} else {
  console.error('Electron API not available');
}
```

### 问题4：UI不显示或样式错误

**检查项：**
- HTML文件路径是否正确
- CSS文件是否正确加载
- 查看浏览器控制台的404错误

### 问题5：图标不显示

这是正常的，因为还没有添加图标文件。可以在 `assets/` 目录下添加 `icon.png` 文件。

## 开发工作流

1. **启动开发环境**
   ```bash
   npm run dev
   ```

2. **修改代码**
   - 修改 `renderer/` 下的文件会自动热重载
   - 修改 `main.js` 需要重启应用

3. **调试**
   - 使用开发者工具调试前端
   - 使用VS Code调试主进程
   - 查看控制台日志

4. **测试功能**
   - 测试各个标签页的切换
   - 测试与Python后端的通信
   - 测试UI交互

## 下一步开发

- [ ] 完善ISO镜像下载功能
- [ ] 实现本地ISO文件选择对话框
- [ ] 完善autounattend.xml配置UI
- [ ] 实现进度显示
- [ ] 添加错误提示UI
- [ ] 优化界面样式



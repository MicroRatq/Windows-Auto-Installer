# 前端测试指南

## 启动应用

### 1. 确保依赖已安装

```bash
cd src
npm install
```

### 2. 启动应用

```bash
npm start
# 或
npm run dev  # 开发模式（自动打开开发者工具）
```

## 测试清单

### ✅ 基础功能测试

- [ ] 应用窗口正常打开
- [ ] 标题栏显示正确
- [ ] 标签页可以正常切换
- [ ] UI样式正常显示

### ✅ IPC通信测试

1. **打开浏览器开发者工具**（开发模式自动打开，或按 `Ctrl+Shift+I`）

2. **测试Python后端连接**
   在控制台输入：
   ```javascript
   window.electronAPI.sendToPython('test', {})
     .then(response => console.log('Success:', response))
     .catch(error => console.error('Error:', error));
   ```

3. **检查Python后端启动**
   - 查看Electron主进程控制台
   - 应该看到 "Python path:", "Script path:" 等日志
   - 如果没有错误，Python后端应该已启动

### ✅ UI功能测试

1. **ISO镜像标签页**
   - 切换镜像来源（下载/本地）
   - 检查表单元素是否正常

2. **系统迁移标签页**
   - 检查输入框是否正常
   - 检查按钮是否可点击

3. **Office安装标签页**
   - 检查下拉菜单是否正常
   - 检查输入框是否正常

4. **激活标签页**
   - 切换激活方式（KMS/TSforge）
   - 检查KMS选项是否正常显示/隐藏

5. **软件安装标签页**
   - 检查按钮是否正常

### ✅ 错误处理测试

1. **Python后端未启动**
   - 关闭Python进程
   - 尝试发送请求
   - 应该显示错误提示

2. **网络错误**
   - 断开网络
   - 测试需要网络的功能
   - 应该显示错误提示

## 调试技巧

### 查看日志

1. **主进程日志**：在启动Electron的终端中查看
2. **渲染进程日志**：在浏览器开发者工具的控制台中查看
3. **Python后端日志**：在主进程控制台中查看

### 常见问题

1. **Python后端无法启动**
   - 检查Python路径
   - 检查 `backend/main.py` 是否存在
   - 检查Python依赖是否安装

2. **IPC通信失败**
   - 检查 `preload.js` 是否正确加载
   - 检查 `window.electronAPI` 是否可用
   - 查看控制台错误信息

3. **样式问题**
   - 检查CSS文件路径
   - 清除缓存（Ctrl+Shift+R）
   - 检查浏览器兼容性

## 下一步

完成基础测试后，可以开始：
1. 实现具体的功能逻辑
2. 完善UI交互
3. 添加错误处理和用户提示
4. 优化用户体验



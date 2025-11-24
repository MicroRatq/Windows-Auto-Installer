# Windows自动安装器

Windows系统自动安装和配置工具，基于Electron + Vue前端和Python后端实现。

## 功能特性

- **ISO镜像自定义和安装**：支持从微软官网及镜像站下载Windows 11镜像，配置autounattend.xml应答文件
- **系统迁移**：支持pagefile.sys和Users文件夹迁移
- **Office安装**：通过Office Tool Plus自动安装Office系列软件
- **系统激活**：支持KMS和TSforge两种激活方式
- **软件安装**：基于Winget和pywinauto的自动化软件安装

## 环境要求

- Node.js 20 LTS 或更高版本
- Conda (Anaconda 或 Miniconda)
- Windows 10/11

## 快速开始

### 1. 环境配置

运行环境配置脚本：

```bash
scripts\setup_env.bat
```

该脚本会：
- 检查Node.js和Conda是否安装
- 创建conda环境（win-auto-installer）
- 安装Python依赖
- 安装Node.js依赖

### 2. 开发模式运行

运行开发脚本：

```bash
scripts\run_dev.bat
```

该脚本会：
- 检查并清理可能占用的端口5173
- 启动Vite开发服务器（http://localhost:5173）
- 启动Electron窗口
- 自动启动Python后端并建立IPC通信
- 退出时自动清理所有相关进程

**注意**：如果遇到端口被占用的问题，可以手动运行：

```bash
scripts\cleanup_port.bat
```

### 3. 测试IPC通信

应用启动后，前端会自动发送ping请求到后端。打开浏览器开发者工具（F12）查看控制台输出，确认前后端通信正常。

## 项目结构

```
Windows-Auto-Installer/
├── src/
│   ├── frontend/          # Electron + Vue前端
│   │   ├── electron/      # Electron主进程
│   │   └── renderer/      # Vue渲染进程
│   ├── backend/           # Python后端
│   └── shared/            # 共享资源
├── scripts/               # 脚本目录
│   ├── setup_env.bat      # 环境配置脚本
│   └── run_dev.bat        # 开发模式启动脚本
└── environment.yml        # Conda环境配置
```

## 开发说明

- 所有源代码在`src`目录下开发
- `ref`目录为参考项目，不纳入git管理
- 高风险操作（系统更改、软件安装）必须在虚拟机中测试

## 许可证

MIT


# Windows自动安装和配置项目

基于Electron UI和Python后端的Windows系统自动安装和配置工具。

## 功能特性

- **ISO镜像自定义和安装**：支持从微软官网/镜像站下载Windows 11镜像，或使用本地ISO文件，自动生成autounattend.xml并集成到ISO中
- **系统迁移**：支持pagefile.sys和Users文件夹迁移到其他驱动器
- **Office安装**：通过Office Tool Plus自动安装Office系列软件
- **系统激活**：支持KMS和TSforge两种激活方式
- **软件安装**：基于Winget和pywinauto的自动化软件安装，支持多线程并行下载

## 项目结构

```
Windows-Auto-Installer/
├── src/                      # 源代码目录
│   ├── backend/             # Python后端代码
│   │   ├── main.py          # 主入口
│   │   ├── ipc_server.py    # IPC通信服务器
│   │   ├── iso_handler.py   # ISO镜像处理
│   │   ├── autounattend.py # autounattend.xml生成
│   │   ├── migration.py     # 系统迁移
│   │   ├── office_installer.py # Office安装
│   │   ├── activation.py    # 系统激活
│   │   └── software_installer.py # 软件安装
│   ├── main.js              # Electron主进程
│   ├── preload.js           # IPC桥接
│   ├── package.json         # Node.js配置
│   └── renderer/            # 前端UI
│       ├── index.html
│       ├── css/
│       └── js/
├── scripts/                 # 脚本目录
│   ├── setup_env.bat        # 环境配置脚本
│   └── build.bat            # 打包脚本
├── ref/                     # 参考代码（不纳入git管理）
├── .gitignore
├── README.md
└── requirements.txt         # Python依赖
```

## 环境要求

- Node.js (最新稳定版)
- Python 3.9+
- Conda (Anaconda或Miniconda)
- Windows 10/11

## 快速开始

### 1. 环境配置

运行环境配置脚本：

```batch
scripts\setup_env.bat
```

脚本会自动：
- 检查Node.js、Python和Conda环境
- 创建/激活Conda环境
- 安装Python依赖
- 安装Node.js依赖

### 2. 开发模式运行

```batch
cd src
npm start
```

### 3. 打包应用

```batch
scripts\build.bat
```

打包后的应用位于 `dist\` 目录。

## 开发说明

### Python后端

后端代码位于 `src/backend/` 目录，使用IPC（标准输入/输出）与Electron前端通信。

### Electron前端

前端代码位于 `src/` 目录，使用Electron框架构建桌面应用。

### IPC通信

前端通过 `preload.js` 暴露的API与后端通信，后端通过JSON格式的stdin/stdout进行消息传递。

## 注意事项

⚠️ **重要警告**：
- 所有高风险操作（系统更改、软件安装）必须在虚拟机中测试
- 不要在生产环境直接运行未测试的功能
- ref目录包含参考代码，不纳入git管理

## 技术栈

- **前端**: Electron
- **后端**: Python 3.9+
- **IPC通信**: Electron IPC + Python stdin/stdout
- **ISO编辑**: pycdlib
- **UI自动化**: pywinauto
- **打包工具**: electron-builder + PyInstaller

## 许可证

MIT License


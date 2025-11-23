#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows自动安装配置工具 - Python后端主入口
"""
import sys
import json
import traceback
from ipc_server import IPCServer

def main():
    """主函数"""
    try:
        # 创建IPC服务器
        server = IPCServer()
        
        # 启动服务器
        server.start()
        
    except KeyboardInterrupt:
        print("服务器已停止", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()


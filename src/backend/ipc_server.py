#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IPC服务器 - 处理Electron和Python之间的通信
"""
import sys
import json
import traceback
from typing import Dict, Callable, Any
from iso_handler import ISOHandler
from autounattend import AutounattendGenerator
from migration import MigrationHandler
from office_installer import OfficeInstaller
from activation import ActivationHandler
from software_installer import SoftwareInstaller

class IPCServer:
    """IPC服务器类"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.iso_handler = ISOHandler()
        self.autounattend_gen = AutounattendGenerator()
        self.migration_handler = MigrationHandler()
        self.office_installer = OfficeInstaller()
        self.activation_handler = ActivationHandler()
        self.software_installer = SoftwareInstaller()
        self.register_default_handlers()
    
    def register_handler(self, action: str, handler: Callable):
        """注册消息处理器"""
        self.handlers[action] = handler
    
    def register_default_handlers(self):
        """注册默认处理器"""
        # 测试处理器
        self.register_handler('test', self.handle_test)
        
        # 占位处理器（后续实现）
        self.register_handler('generate-iso', self.handle_generate_iso)
        self.register_handler('migrate-pagefile', self.handle_migrate_pagefile)
        self.register_handler('migrate-users', self.handle_migrate_users)
        self.register_handler('install-office', self.handle_install_office)
        self.register_handler('activate', self.handle_activate)
        self.register_handler('install-software', self.handle_install_software)
    
    def handle_test(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """测试处理器"""
        return {
            'message': 'Python后端运行正常',
            'data': data
        }
    
    def handle_generate_iso(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理ISO生成请求"""
        try:
            source = data.get('source', 'download')
            config = {
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'timezone': data.get('timezone', 'China Standard Time'),
                'options': data.get('options', {})
            }
            
            # 获取ISO文件
            if source == 'download':
                version = data.get('version', 'latest')
                iso_path = self.iso_handler.download_windows_iso(version)
            else:
                iso_path = data.get('isoPath', '')
                if not iso_path:
                    raise ValueError('未指定本地ISO文件路径')
                iso_path = self.iso_handler.select_local_iso(iso_path)
            
            # 准备ISO用于编辑
            edit_iso_path = self.iso_handler.prepare_iso_for_editing(iso_path)
            
            # 生成autounattend.xml
            autounattend_xml = self.autounattend_gen.generate(config)
            
            # 添加autounattend.xml到ISO
            output_iso = self.iso_handler.add_autounattend_to_iso(edit_iso_path, autounattend_xml)
            
            return {
                'message': 'ISO生成成功',
                'status': 'success',
                'iso_path': output_iso
            }
        except Exception as e:
            return {
                'message': f'ISO生成失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def handle_migrate_pagefile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理pagefile迁移请求"""
        try:
            target = data.get('target', '')
            if not target:
                raise ValueError('未指定目标路径')
            
            result = self.migration_handler.migrate_pagefile(target)
            return {
                'message': result.get('message', ''),
                'status': 'success' if result.get('success') else 'error',
                'error': result.get('error'),
                'note': result.get('note')
            }
        except Exception as e:
            return {
                'message': f'迁移失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def handle_migrate_users(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Users文件夹迁移请求"""
        try:
            target = data.get('target', '')
            if not target:
                raise ValueError('未指定目标路径')
            
            result = self.migration_handler.migrate_users(target)
            return {
                'message': result.get('message', ''),
                'status': 'success' if result.get('success') else 'error',
                'error': result.get('error'),
                'note': result.get('note'),
                'restart_required': result.get('restart_required', False)
            }
        except Exception as e:
            return {
                'message': f'迁移失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def handle_install_office(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Office安装请求"""
        try:
            version = data.get('version', 'ProPlus2024Volume_zh-cn')
            install_path = data.get('installPath', None)
            kms_server = data.get('kmsServer', None)
            kms_port = data.get('kmsPort', None)
            kms_key = data.get('kmsKey', None)
            
            result = self.office_installer.install_office(
                version=version,
                install_path=install_path,
                kms_server=kms_server,
                kms_port=kms_port,
                kms_key=kms_key
            )
            
            return {
                'message': result.get('message', ''),
                'status': 'success' if result.get('success') else 'error',
                'error': result.get('error'),
                'warning': result.get('warning')
            }
        except Exception as e:
            return {
                'message': f'Office安装失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def handle_activate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理激活请求"""
        try:
            method = data.get('method', 'kms')
            
            if method == 'kms':
                server = data.get('server', '')
                port = data.get('port', 1688)
                key = data.get('key', '')
                
                if not server:
                    raise ValueError('KMS服务器地址不能为空')
                
                # 激活Windows
                result = self.activation_handler.kms_activate_windows(server, port, key)
                
                # 如果提供了Office密钥，也激活Office
                office_key = data.get('officeKey', '')
                office_license = data.get('officeLicense', '')
                if office_key and office_license:
                    office_result = self.activation_handler.kms_activate_office(
                        server, port, office_key, office_license
                    )
                    if not office_result.get('success'):
                        return {
                            'message': 'Windows激活成功，但Office激活失败',
                            'status': 'partial',
                            'windows_result': result,
                            'office_result': office_result
                        }
                
                return {
                    'message': result.get('message', ''),
                    'status': 'success' if result.get('success') else 'error',
                    'error': result.get('error')
                }
                
            elif method == 'tsforge':
                result = self.activation_handler.tsforge_activate()
                return {
                    'message': result.get('message', ''),
                    'status': 'success' if result.get('success') else 'error',
                    'error': result.get('error')
                }
            else:
                raise ValueError(f'未知的激活方式: {method}')
                
        except Exception as e:
            return {
                'message': f'激活失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def handle_install_software(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理软件安装请求"""
        try:
            # 从配置或直接传入的包列表安装
            config = data.get('config', {})
            
            # 如果没有配置，尝试从data中直接获取包列表
            if not config:
                config = {
                    'winget_packages': data.get('winget_packages', []),
                    'manual_packages': data.get('manual_packages', [])
                }
            
            # 进度回调（如果需要）
            def progress_callback(current, total, package_name):
                # 可以通过IPC发送进度更新
                pass
            
            result = self.software_installer.install_from_config(config, progress_callback)
            
            return {
                'message': '软件安装完成',
                'status': 'success',
                'results': result
            }
        except Exception as e:
            return {
                'message': f'软件安装失败: {str(e)}',
                'status': 'error',
                'error': str(e)
            }
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理消息"""
        try:
            action = message.get('action')
            data = message.get('data', {})
            request_id = message.get('id')
            
            if not action:
                return {
                    'id': request_id,
                    'error': '缺少action字段'
                }
            
            if action not in self.handlers:
                return {
                    'id': request_id,
                    'error': f'未知的action: {action}'
                }
            
            # 调用处理器
            handler = self.handlers[action]
            result = handler(data)
            
            return {
                'id': request_id,
                'data': result
            }
            
        except Exception as e:
            return {
                'id': message.get('id'),
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def start(self):
        """启动IPC服务器"""
        # 从stdin读取消息，向stdout输出响应
        for line in sys.stdin:
            try:
                # 解析JSON消息
                message = json.loads(line.strip())
                
                # 处理消息
                response = self.process_message(message)
                
                # 输出响应
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = {
                    'error': f'JSON解析错误: {str(e)}'
                }
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    'error': f'处理消息时出错: {str(e)}',
                    'traceback': traceback.format_exc()
                }
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()


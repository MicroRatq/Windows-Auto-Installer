#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows/Office激活模块
支持KMS激活和TSforge激活
"""
import subprocess
import os
import sys
import requests
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile

class ActivationHandler:
    """激活处理器"""
    
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def kms_activate_windows(self, server: str, port: int = 1688, key: Optional[str] = None) -> Dict[str, Any]:
        """
        KMS激活Windows
        
        Args:
            server: KMS服务器地址
            port: KMS端口
            key: KMS密钥（可选）
        
        Returns:
            激活结果
        """
        try:
            # 如果提供了密钥，先安装密钥
            if key:
                result = subprocess.run(
                    ['slmgr', '/ipk', key],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'安装密钥失败: {result.stderr}'
                    }
            
            # 设置KMS服务器
            result = subprocess.run(
                ['slmgr', '/skms', f'{server}:{port}'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'设置KMS服务器失败: {result.stderr}'
                }
            
            # 激活Windows
            result = subprocess.run(
                ['slmgr', '/ato'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Windows激活成功'
                }
            else:
                return {
                    'success': False,
                    'error': f'激活失败: {result.stderr}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'KMS激活Windows时出错: {str(e)}'
            }
    
    def kms_activate_office(self, server: str, port: int = 1688, key: str, license_id: str) -> Dict[str, Any]:
        """
        KMS激活Office
        
        Args:
            server: KMS服务器地址
            port: KMS端口
            key: KMS密钥
            license_id: 许可证ID（如ProPlus2024Volume）
        
        Returns:
            激活结果
        """
        try:
            # 使用ospp.vbs脚本激活Office
            # ospp.vbs通常在Office安装目录下
            office_paths = [
                r'C:\Program Files\Microsoft Office\Office16',
                r'C:\Program Files (x86)\Microsoft Office\Office16',
                r'C:\Program Files\Microsoft Office\Office15',
                r'C:\Program Files (x86)\Microsoft Office\Office15',
            ]
            
            ospp_path = None
            for path in office_paths:
                test_path = Path(path) / 'ospp.vbs'
                if test_path.exists():
                    ospp_path = test_path
                    break
            
            if not ospp_path:
                return {
                    'success': False,
                    'error': '未找到ospp.vbs，请确保Office已安装'
                }
            
            # 安装许可证
            result = subprocess.run(
                ['cscript', '//nologo', str(ospp_path), '/inslicid', license_id],
                capture_output=True,
                text=True,
                check=False
            )
            
            # 安装密钥
            result = subprocess.run(
                ['cscript', '//nologo', str(ospp_path), '/inpkey', key],
                capture_output=True,
                text=True,
                check=False
            )
            
            # 设置KMS服务器
            result = subprocess.run(
                ['cscript', '//nologo', str(ospp_path), '/sethst', server],
                capture_output=True,
                text=True,
                check=False
            )
            
            # 设置端口
            result = subprocess.run(
                ['cscript', '//nologo', str(ospp_path), '/setprt', str(port)],
                capture_output=True,
                text=True,
                check=False
            )
            
            # 激活
            result = subprocess.run(
                ['cscript', '//nologo', str(ospp_path), '/act'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if 'successful' in result.stdout.lower() or result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Office激活成功'
                }
            else:
                return {
                    'success': False,
                    'error': f'Office激活失败: {result.stdout}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'KMS激活Office时出错: {str(e)}'
            }
    
    def download_tsforge(self) -> str:
        """
        下载TSforge工具
        
        Returns:
            TSforge工具目录路径
        """
        tsforge_dir = self.temp_dir / "TSforge"
        tsforge_dir.mkdir(parents=True, exist_ok=True)
        
        # 从GitHub下载最新版本
        # 注意：这里需要根据实际TSforge的发布方式调整
        repo_url = "https://api.github.com/repos/massgravel/TSforge/releases/latest"
        
        try:
            response = requests.get(repo_url, timeout=30)
            response.raise_for_status()
            release_data = response.json()
            
            # 查找Windows可执行文件
            download_url = None
            for asset in release_data.get('assets', []):
                if asset['name'].endswith('.exe') or 'windows' in asset['name'].lower():
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                raise Exception("未找到TSforge下载链接")
            
            # 下载文件
            exe_path = tsforge_dir / "TSforge.exe"
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(tsforge_dir)
            
        except Exception as e:
            raise Exception(f"下载TSforge失败: {str(e)}")
    
    def tsforge_activate(self) -> Dict[str, Any]:
        """
        使用TSforge激活Windows
        
        Returns:
            激活结果
        """
        try:
            # 下载TSforge
            tsforge_dir = self.download_tsforge()
            tsforge_exe = Path(tsforge_dir) / "TSforge.exe"
            
            if not tsforge_exe.exists():
                raise FileNotFoundError(f"TSforge.exe不存在: {tsforge_exe}")
            
            # 执行TSforge激活（后台运行，不显示终端）
            # 注意：TSforge可能需要管理员权限
            result = subprocess.run(
                [str(tsforge_exe)],
                capture_output=True,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # TSforge通常会自动激活，检查激活状态
            # 通过slmgr检查激活状态
            check_result = subprocess.run(
                ['slmgr', '/xpr'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if 'permanently activated' in check_result.stdout.lower() or 'activated' in check_result.stdout.lower():
                return {
                    'success': True,
                    'message': 'Windows激活成功（TSforge）'
                }
            else:
                return {
                    'success': False,
                    'error': '激活状态未知，请手动检查',
                    'output': check_result.stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'TSforge激活失败: {str(e)}'
            }


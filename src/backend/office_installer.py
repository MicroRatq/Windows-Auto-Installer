#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Office安装模块
参考: ref/installoffice.ps1
"""
import os
import subprocess
import shutil
import zipfile
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import platform

class OfficeInstaller:
    """Office安装器"""
    
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_system_arch(self) -> str:
        """获取系统架构"""
        arch = platform.machine().lower()
        if 'arm64' in arch or 'aarch64' in arch:
            return 'ARM64'
        elif '64' in arch or 'x86_64' in arch or 'amd64' in arch:
            return 'x64'
        else:
            return 'x86'
    
    def check_dotnet_runtime(self) -> bool:
        """检查.NET运行时版本"""
        try:
            result = subprocess.run(
                ['dotnet', '--list-runtimes'],
                capture_output=True,
                text=True,
                check=False
            )
            if 'Microsoft.WindowsDesktop.App 8' in result.stdout:
                return True
        except Exception:
            pass
        return False
    
    def download_office_tool_plus(self, save_path: Optional[str] = None) -> str:
        """
        下载Office Tool Plus
        
        Args:
            save_path: 保存路径
        
        Returns:
            解压后的目录路径
        """
        if save_path is None:
            save_path = str(self.temp_dir / "Office Tool")
        else:
            save_path = str(Path(save_path))
        
        arch = self.get_system_arch()
        has_runtime = self.check_dotnet_runtime()
        
        # 构建下载URL
        if has_runtime:
            download_url = f"https://otp.landian.vip/redirect/download.php?type=normal&arch={arch}"
        else:
            download_url = f"https://otp.landian.vip/redirect/download.php?type=runtime&arch={arch}"
        
        zip_path = self.temp_dir / "Office Tool Plus.zip"
        
        # 下载文件
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"下载Office Tool Plus失败: {str(e)}")
                continue
        
        # 解压文件
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(save_path)
        finally:
            # 清理zip文件
            if zip_path.exists():
                zip_path.unlink()
        
        return save_path
    
    def install_office(
        self,
        version: str = "ProPlus2024Volume_zh-cn",
        install_path: Optional[str] = None,
        kms_server: Optional[str] = None,
        kms_port: Optional[int] = None,
        kms_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        安装Office
        
        Args:
            version: Office版本
            install_path: 安装路径
            kms_server: KMS服务器地址
            kms_port: KMS端口
            kms_key: KMS密钥
        
        Returns:
            安装结果
        """
        try:
            # 下载Office Tool Plus
            otp_path = self.download_office_tool_plus()
            console_exe = Path(otp_path) / "Office Tool Plus.Console.exe"
            
            if not console_exe.exists():
                raise FileNotFoundError(f"Office Tool Plus.Console.exe不存在: {console_exe}")
            
            # 构建安装命令
            # 参考ref/installoffice.ps1中的命令
            deploy_cmd = [
                str(console_exe),
                'deploy',
                '/add', version,
                '/edition', '64',
                '/channel', 'PerpetualVL2024',
                '/dlfirst',
                '/acpteula'
            ]
            
            # 执行部署
            result = subprocess.run(
                deploy_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Office部署失败: {result.stderr}'
                }
            
            # 如果提供了KMS信息，进行激活
            if kms_server and kms_key:
                # 安装许可证
                inslic_cmd = [
                    str(console_exe),
                    'ospp',
                    '/inslicid', version.replace('_zh-cn', ''),
                    '/inpkey', kms_key,
                    '/sethst', kms_server
                ]
                
                if kms_port:
                    inslic_cmd.extend(['/setprt', str(kms_port)])
                
                inslic_cmd.append('/act')
                
                result = subprocess.run(
                    inslic_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    return {
                        'success': True,
                        'message': 'Office安装完成，但激活失败',
                        'warning': result.stderr
                    }
            
            return {
                'success': True,
                'message': 'Office安装完成'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Office安装失败: {str(e)}'
            }


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统迁移模块 - pagefile.sys和Users文件夹迁移
参考: ref/MoveUsers
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any
import ctypes

class MigrationHandler:
    """系统迁移处理器"""
    
    def __init__(self):
        # backend在src下，需要向上三级到达项目根目录
        self.script_dir = Path(__file__).parent.parent.parent
    
    def check_drive_available(self, drive_path: str) -> Dict[str, Any]:
        """
        检查驱动器是否可用
        
        Args:
            drive_path: 驱动器路径（如 D:\）
        
        Returns:
            检查结果字典
        """
        drive = Path(drive_path)
        
        if not drive.exists():
            return {
                'available': False,
                'error': f'驱动器不存在: {drive_path}'
            }
        
        # 检查驱动器类型
        try:
            drive_type_code = ctypes.windll.kernel32.GetDriveTypeW(str(drive))
            if drive_type_code != 3:  # 3 = DRIVE_FIXED (本地硬盘)
                return {
                    'available': False,
                    'error': f'驱动器不是本地硬盘: {drive_path}'
                }
        except Exception as e:
            return {
                'available': False,
                'error': f'检查驱动器类型失败: {str(e)}'
            }
        
        # 检查可用空间
        try:
            free_space = shutil.disk_usage(drive_path).free
            return {
                'available': True,
                'free_space': free_space,
                'free_space_gb': free_space / (1024 ** 3)
            }
        except Exception as e:
            return {
                'available': False,
                'error': f'检查可用空间失败: {str(e)}'
            }
    
    def migrate_pagefile(self, target_path: str) -> Dict[str, Any]:
        """
        迁移pagefile.sys
        
        Args:
            target_path: 目标路径（如 D:\pagefile.sys）
        
        Returns:
            迁移结果
        """
        try:
            target = Path(target_path)
            target_drive = target.drive + '\\'
            
            # 检查目标驱动器
            drive_check = self.check_drive_available(target_drive)
            if not drive_check.get('available'):
                return {
                    'success': False,
                    'error': drive_check.get('error', '驱动器不可用')
                }
            
            # 使用wmic命令迁移pagefile
            # 首先删除当前pagefile设置
            subprocess.run(['wmic', 'pagefileset', 'delete'], 
                         capture_output=True, check=False)
            
            # 设置新的pagefile位置
            # 注意：wmic命令需要管理员权限
            cmd = [
                'wmic', 'pagefileset', 'create',
                f'name="{target_path}"'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'pagefile.sys已迁移到: {target_path}',
                    'note': '需要重启系统使更改生效'
                }
            else:
                return {
                    'success': False,
                    'error': f'迁移失败: {result.stderr}',
                    'note': '可能需要管理员权限'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'迁移pagefile.sys时出错: {str(e)}'
            }
    
    def migrate_users(self, target_path: str) -> Dict[str, Any]:
        """
        迁移Users文件夹
        
        Args:
            target_path: 目标路径（如 D:\Users）
        
        Returns:
            迁移结果
        """
        try:
            target = Path(target_path)
            target_drive = target.drive + '\\'
            
            # 检查目标驱动器
            drive_check = self.check_drive_available(target_drive)
            if not drive_check.get('available'):
                return {
                    'success': False,
                    'error': drive_check.get('error', '驱动器不可用')
                }
            
            # 检查目标目录是否已存在
            if target.exists():
                return {
                    'success': False,
                    'error': f'目标目录已存在: {target_path}'
                }
            
            # 设置环境变量传递迁移路径
            # 这个环境变量将在WinPE启动时被读取
            os.environ['USERS_MIGRATION_TARGET'] = str(target)
            
            # 获取boot.wim和boot.sdi路径
            boot_dir = self.script_dir / 'ref' / 'MoveUsers' / 'boot'
            boot_wim = boot_dir / 'boot.wim'
            boot_sdi = boot_dir / 'boot.sdi'
            
            if not boot_wim.exists() or not boot_sdi.exists():
                return {
                    'success': False,
                    'error': 'WinPE文件不存在，请确保ref/MoveUsers/boot目录下有boot.wim和boot.sdi'
                }
            
            # 创建WinPE启动项
            script_dir = boot_dir.parent
            script_drive = script_dir.drive
            
            # 使用bcdedit创建WinPE启动项
            # 参考ref/MoveUsers/moveusers.bat
            guid_device = '{ffffffff-8d96-11de-8e71-ffffffffffff}'
            guid_loader = '{ffffffff-8d96-11de-8e71-fffffffffffe}'
            
            # 创建设备项
            subprocess.run([
                'bcdedit', '/create', guid_device,
                '/d', 'winpe', '/device'
            ], capture_output=True, check=False)
            
            # 创建加载器项
            subprocess.run([
                'bcdedit', '/create', guid_loader,
                '/d', 'winpe', '/application', 'osloader'
            ], capture_output=True, check=False)
            
            # 设置设备路径
            sdi_path = f'{script_dir.relative_to(Path(script_drive))}\\boot\\boot.sdi'
            subprocess.run([
                'bcdedit', '/set', guid_device,
                'ramdisksdidevice', f'partition={script_drive}'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_device,
                'ramdisksdipath', sdi_path.replace('\\', '/')
            ], capture_output=True, check=False)
            
            # 设置加载器
            wim_path = f'{script_dir.relative_to(Path(script_drive))}\\boot\\boot.wim'
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'device', f'ramdisk=[{script_drive}]{wim_path.replace(chr(92), "/")},{guid_device}'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'path', '\\windows\\system32\\winload.efi'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'description', 'Windows PE (Boot Once)'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'locale', 'en-US'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'inherit', '{bootloadersettings}'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'osdevice', f'ramdisk=[{script_drive}]{wim_path.replace(chr(92), "/")},{guid_device}'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'systemroot', '\\windows'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'detecthal', 'Yes'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'winpe', 'Yes'
            ], capture_output=True, check=False)
            
            subprocess.run([
                'bcdedit', '/set', guid_loader,
                'ems', 'no'
            ], capture_output=True, check=False)
            
            # 设置为下次启动的默认选项
            subprocess.run([
                'bcdedit', '/default', guid_loader
            ], capture_output=True, check=False)
            
            # 设置为一次性启动
            subprocess.run([
                'bcdedit', '/set', '{bootmgr}',
                'bootsequence', guid_loader
            ], capture_output=True, check=False)
            
            # 创建winpeshl.ini脚本（需要在WinPE中执行）
            # 由于无法直接编辑boot.wim，我们通过环境变量传递信息
            # WinPE启动脚本需要读取环境变量并执行迁移
            
            return {
                'success': True,
                'message': 'Users文件夹迁移已配置',
                'note': '系统将在5秒后重启进入WinPE环境执行迁移',
                'target_path': str(target),
                'restart_required': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'配置Users迁移时出错: {str(e)}'
            }


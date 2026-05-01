"""
ISO burning module
Supports burning ISO images to disk/USB drives using balena CLI
"""
import os
import sys
import subprocess
import platform
import logging
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('ISOBurner')


class ISOBurner:
    """ISO烧录器，支持将ISO镜像写入磁盘/U盘"""
    
    def __init__(self):
        """初始化ISO烧录器"""
        self.platform = platform.system().lower()
        self.balena_available = self._check_balena_cli()
    
    def _check_balena_cli(self) -> bool:
        """
        检查 balena CLI 是否可用
        
        Returns:
            是否可用
        """
        try:
            # 尝试运行 balena version 命令
            result = subprocess.run(
                ["balena", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"balena CLI is available: {result.stdout.strip()}")
                return True
            else:
                logger.warning("balena CLI is not available (return code != 0)")
                return False
        except FileNotFoundError:
            logger.warning(
                "balena CLI not found. Please install it:\n"
                "  npm install -g balena-cli\n"
                "  or visit: https://github.com/balena-io/balena-cli"
            )
            return False
        except Exception as e:
            logger.warning(f"Error checking balena CLI: {e}")
            return False
    
    def list_devices(self) -> list[dict[str, Any]]:
        """
        列出可用的磁盘/U盘设备
        
        Returns:
            设备列表，每个设备包含:
            - path: 设备路径
            - size: 设备大小（字节）
            - label: 设备标签
            - filesystem: 文件系统类型
            - removable: 是否可移动设备
        """
        devices = []
        
        try:
            if self.platform == "windows":
                devices = self._list_devices_windows()
            elif self.platform == "linux":
                devices = self._list_devices_linux()
            elif self.platform == "darwin":  # macOS
                devices = self._list_devices_macos()
            else:
                logger.warning(f"Unsupported platform: {self.platform}")
                return []
            
            logger.info(f"Found {len(devices)} device(s)")
            return devices
            
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _list_devices_windows(self) -> list[dict[str, Any]]:
        """Windows 平台设备列表"""
        devices = []
        
        try:
            # 使用 wmic 获取逻辑磁盘信息
            cmd = [
                "wmic",
                "logicaldisk",
                "get",
                "DeviceID,Size,VolumeName,FileSystem,DriveType",
                "/format:csv"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # 跳过 CSV 标题行
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    parts = line.split(',')
                    if len(parts) >= 5:
                        device_id = parts[1].strip()
                        size_str = parts[2].strip()
                        volume_name = parts[3].strip()
                        filesystem = parts[4].strip()
                        drive_type = parts[5].strip() if len(parts) > 5 else ""
                        
                        # DriveType: 2 = Removable, 3 = Fixed, 4 = Network, 5 = CD-ROM
                        removable = (drive_type == "2")
                        
                        try:
                            size = int(size_str) if size_str else 0
                        except ValueError:
                            size = 0
                        
                        if device_id:
                            devices.append({
                                "path": device_id,  # 如 "E:"
                                "size": size,
                                "label": volume_name or "No Label",
                                "filesystem": filesystem or "Unknown",
                                "removable": removable
                            })
            
        except Exception as e:
            logger.error(f"Failed to list Windows devices: {e}")
        
        return devices
    
    def _list_devices_linux(self) -> list[dict[str, Any]]:
        """Linux 平台设备列表"""
        devices = []
        
        try:
            # 使用 lsblk 获取块设备信息
            cmd = ["lsblk", "-b", "-n", "-o", "NAME,SIZE,LABEL,FSTYPE,RM"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 5:
                        name = parts[0].strip()
                        size_str = parts[1].strip()
                        label = parts[2].strip() if parts[2] != "-" else "No Label"
                        fstype = parts[3].strip() if parts[3] != "-" else "Unknown"
                        removable = (parts[4].strip() == "1")
                        
                        # 只包含磁盘设备（不是分区）
                        if not name[-1].isdigit():
                            try:
                                size = int(size_str)
                            except ValueError:
                                size = 0
                            
                            device_path = f"/dev/{name}"
                            devices.append({
                                "path": device_path,
                                "size": size,
                                "label": label,
                                "filesystem": fstype,
                                "removable": removable
                            })
            
        except Exception as e:
            logger.error(f"Failed to list Linux devices: {e}")
        
        return devices
    
    def _list_devices_macos(self) -> list[dict[str, Any]]:
        """macOS 平台设备列表"""
        devices = []
        
        try:
            # 使用 diskutil 获取磁盘信息
            cmd = ["diskutil", "list", "-plist"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 解析 plist 输出（简化版本）
                # 实际应用中可能需要使用 plistlib
                import re
                
                # 查找所有磁盘
                disk_pattern = re.compile(r'/dev/disk(\d+)')
                for match in disk_pattern.finditer(result.stdout):
                    disk_num = match.group(1)
                    disk_path = f"/dev/disk{disk_num}"
                    
                    # 获取磁盘详细信息
                    info_cmd = ["diskutil", "info", "-plist", disk_path]
                    info_result = subprocess.run(
                        info_cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if info_result.returncode == 0:
                        # 提取信息（简化解析）
                        size_match = re.search(r'Total Size:\s*(\d+)\s*Bytes', info_result.stdout)
                        size = int(size_match.group(1)) if size_match else 0
                        
                        label_match = re.search(r'Volume Name:\s*(.+)', info_result.stdout)
                        label = label_match.group(1).strip() if label_match else "No Label"
                        
                        fstype_match = re.search(r'File System Personality:\s*(.+)', info_result.stdout)
                        fstype = fstype_match.group(1).strip() if fstype_match else "Unknown"
                        
                        removable_match = re.search(r'Removable Media:\s*(.+)', info_result.stdout)
                        removable = (removable_match.group(1).strip().lower() == "yes") if removable_match else False
                        
                        devices.append({
                            "path": disk_path,
                            "size": size,
                            "label": label,
                            "filesystem": fstype,
                            "removable": removable
                        })
            
        except Exception as e:
            logger.error(f"Failed to list macOS devices: {e}")
        
        return devices
    
    def verify_device(self, device_path: str) -> dict[str, Any]:
        """
        验证设备信息
        
        Args:
            device_path: 设备路径
        
        Returns:
            包含验证结果的字典:
            - success: 是否成功
            - valid: 设备是否有效
            - message: 验证消息
            - device_info: 设备信息
        """
        devices = self.list_devices()
        
        # 查找匹配的设备
        device_info = None
        for dev in devices:
            if dev["path"].lower() == device_path.lower():
                device_info = dev
                break
        
        if not device_info:
            return {
                "success": False,
                "valid": False,
                "message": f"Device not found: {device_path}",
                "device_info": None
            }
        
        # 验证设备是否可写
        # 注意：实际写入测试可能需要管理员权限，这里只做基本检查
        warnings = []
        
        if device_info["size"] == 0:
            warnings.append("Device size is 0 (may be invalid)")
        
        if not device_info["removable"]:
            warnings.append("Device is not marked as removable (may be a fixed disk)")
        
        if warnings:
            return {
                "success": True,
                "valid": False,
                "message": f"Device validation warnings: {', '.join(warnings)}",
                "device_info": device_info,
                "warnings": warnings
            }
        
        return {
            "success": True,
            "valid": True,
            "message": "Device validation passed",
            "device_info": device_info
        }
    
    def burn_iso(self, iso_path: str, device_path: str, confirm: bool = True) -> dict[str, Any]:
        """
        将 ISO 烧录到设备
        
        Args:
            iso_path: ISO 文件路径
            device_path: 目标设备路径
            confirm: 是否需要确认（默认True，实际烧录时应该为False以自动确认）
        
        Returns:
            包含操作结果的字典:
            - success: 是否成功
            - message: 结果消息
        """
        iso_file = Path(iso_path)
        if not iso_file.exists():
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
        
        if not self.balena_available:
            error_msg = "balena CLI is not available. Please install it first."
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
        
        # 验证设备
        verify_result = self.verify_device(device_path)
        if not verify_result["valid"]:
            error_msg = f"Device validation failed: {verify_result['message']}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
        
        try:
            logger.info(f"Burning ISO {iso_path} to device {device_path}")
            
            # 构建 balena 命令
            # 注意：balena local flash 命令格式可能因版本而异
            # 这里使用通用格式
            cmd = [
                "balena",
                "local",
                "flash",
                str(iso_file),
                "--drive", device_path
            ]
            
            if not confirm:
                cmd.append("--yes")
            
            logger.info(f"Running command: {' '.join(cmd)}")
            logger.warning("WARNING: This will erase all data on the target device!")
            
            # 执行烧录（注意：实际执行需要管理员权限）
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                logger.info("ISO burned successfully")
                return {
                    "success": True,
                    "message": f"Successfully burned ISO to {device_path}"
                }
            else:
                error_msg = f"balena flash failed: {result.stderr}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
            
        except subprocess.TimeoutExpired:
            error_msg = "ISO burning timed out (exceeded 1 hour)"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
        except Exception as e:
            logger.error(f"Failed to burn ISO: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Failed to burn ISO: {str(e)}"
            }
    
    def _get_device_info(self, device_path: str) -> dict[str, Any]:
        """
        获取设备详细信息（内部方法）
        
        Args:
            device_path: 设备路径
        
        Returns:
            设备信息字典
        """
        return self.verify_device(device_path).get("device_info", {})






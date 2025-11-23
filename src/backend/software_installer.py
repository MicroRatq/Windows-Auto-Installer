#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
软件安装模块 - 基于Winget和pywinauto的软件安装
重构自ref/WindowsSoftwareInstaller，改进API规范性和代码质量
"""
import json
import multiprocessing
import os
import re
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import ctypes
import shutil
import requests
from pywinauto import Application, mouse

class SoftwareInstaller:
    """软件安装器 - 重构和改进版本"""
    
    def __init__(self, config_path: Optional[str] = None, temp_folder: str = "temp", max_retries: int = 50):
        """
        初始化软件安装器
        
        Args:
            config_path: 配置文件路径（如果为None，使用项目根目录）
            temp_folder: 临时文件夹路径
            max_retries: 最大重试次数
        """
        if config_path is None:
            # 从backend目录向上三级到达项目根目录
            self.config_path = Path(__file__).parent.parent.parent
        else:
            self.config_path = Path(config_path)
        
        self.temp_folder = Path(temp_folder)
        self.max_retries = max_retries
        
        # 清理并创建临时文件夹
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder, ignore_errors=True)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        
        # 加载配置（如果存在）
        self.winget_config = None
        self.manual_config = None
        try:
            winget_config_path = self.config_path / 'winget.json'
            if winget_config_path.exists():
                self.winget_config = self._load_config('winget.json')
        except Exception:
            pass
        
        try:
            manual_config_path = self.config_path / 'manual.json'
            if manual_config_path.exists():
                self.manual_config = self._load_config('manual.json')
        except Exception:
            pass
    
    def _load_config(self, filename: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        config_path = self.config_path / filename
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _update_config(self, filename: str, data: Dict[str, Any]):
        """更新JSON配置文件"""
        config_path = self.config_path / filename
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    @staticmethod
    def check_d_drive() -> bool:
        """
        检查D盘是否存在且为本地硬盘
        
        Returns:
            如果D盘可用返回True，否则抛出异常
        """
        if not os.path.exists('D:\\'):
            raise Exception("Drive D:\\ does not exist")
        
        try:
            drive_type_code = ctypes.windll.kernel32.GetDriveTypeW('D:\\')
            if drive_type_code == 3:  # DRIVE_FIXED
                return True
            else:
                raise Exception("Drive D:\\ is not a local hard drive")
        except WindowsError:
            raise Exception("Failed to check drive type")
    
    @staticmethod
    def agree_winget_terms() -> bool:
        """
        同意Winget使用条款
        
        Returns:
            成功返回True，否则抛出异常
        """
        process = subprocess.Popen(
            'winget list',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        time.sleep(2)  # 等待提示出现
        process.stdin.write(b'y\n')
        process.stdin.flush()
        process.communicate(timeout=20)
        
        if process.returncode == 0:
            return True
        else:
            raise Exception("Failed to agree to Winget terms")
    
    def install_winget(self) -> bool:
        """
        安装Winget（如果未安装）
        
        Returns:
            成功返回True，否则抛出异常
        """
        repo = 'microsoft/winget-cli'
        pattern = r'Microsoft\.DesktopAppInstaller_.*\.msixbundle'
        url = self._parse_github_release(repo, pattern)
        
        if not url:
            raise Exception("Failed to find Winget download URL")
        
        self._url_download(url, 'Microsoft.DesktopAppInstaller', 'msixbundle')
        
        bundle_path = self.temp_folder / 'Microsoft.DesktopAppInstaller.msixbundle'
        command = f'add-appxpackage "{bundle_path}"'
        
        result = subprocess.run(
            ["powershell", "-Command", command],
            shell=True,
            capture_output=True,
            text=True,
            encoding='gbk'
        )
        
        if result.returncode == 0:
            return True
        else:
            raise Exception(f"Failed to install Winget: {result.stdout}")
    
    def install_winget_packages(self, packages: List[Dict[str, Any]], progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        安装Winget软件包（多进程并行）
        
        Args:
            packages: 软件包列表，每个元素为 {'id': 'package.id', 'category': 'category', 'install_path': 'path'}
            progress_callback: 进度回调函数 (current, total, package_name)
        
        Returns:
            安装结果字典
        """
        results = {
            'success': [],
            'failed': []
        }
        
        total = len(packages)
        
        # 使用多进程池并行安装
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            tasks = [(pkg, i, total, progress_callback) for i, pkg in enumerate(packages)]
            pool_results = pool.map(self._install_winget_package_worker, tasks)
        
        for result in pool_results:
            if result['success']:
                results['success'].append(result)
            else:
                results['failed'].append(result)
        
        return results
    
    @staticmethod
    def _install_winget_package_worker(args) -> Dict[str, Any]:
        """工作进程函数（用于多进程）"""
        package, index, total, progress_callback = args
        
        package_id = package.get('id', '')
        category = package.get('category', 'Default')
        install_path = package.get('install_path')
        
        # 解析包名（处理版本号）
        if '-v' in package_id:
            raw_package_id = package_id.split(' -v')[0]
        else:
            raw_package_id = package_id
        
        folder_name = raw_package_id.split('.')[-1]
        
        # 构建安装命令
        command = f'winget install {package_id} --accept-package-agreements --accept-source-agreements'
        if install_path:
            command += f' -l "{install_path}"'
        elif category != 'Default':
            install_path = f'D:\\{category}\\{folder_name}'
            command += f' -l "{install_path}"'
        
        max_retries = 50
        for attempt in range(max_retries):
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if '已成功安装' in result.stdout or 'successfully installed' in result.stdout.lower():
                if progress_callback:
                    progress_callback(index + 1, total, package_id)
                return {
                    'success': True,
                    'package': package_id,
                    'message': f'{package_id} installed successfully'
                }
            
            time.sleep(1)
        
        return {
            'success': False,
            'package': package_id,
            'error': f'Failed to install {package_id} after {max_retries} attempts'
        }
    
    def install_manual_packages(self, packages: List[Dict[str, Any]], progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        安装手动配置的软件包
        
        Args:
            packages: 软件包配置列表
            progress_callback: 进度回调函数
        
        Returns:
            安装结果字典
        """
        results = {
            'success': [],
            'failed': []
        }
        
        total = len(packages)
        
        # 多进程下载
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            download_tasks = [(pkg, self.temp_folder) for pkg in packages]
            pool.map(self._download_manual_package_worker, download_tasks)
        
        # 单进程安装（避免UI冲突）
        for i, package in enumerate(packages):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, package.get('name', 'Unknown'))
                
                result = self._install_manual_package(package)
                if result['success']:
                    results['success'].append(result)
                else:
                    results['failed'].append(result)
            except Exception as e:
                results['failed'].append({
                    'success': False,
                    'package': package.get('name', 'Unknown'),
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def _download_manual_package_worker(args) -> None:
        """下载工作进程函数"""
        package, temp_folder = args
        name = package.get('name', '')
        get_method = package.get('get', {}).get('method', '')
        
        if get_method == 'winget':
            package_id = package['get']['id']
            # 这里需要实现winget下载逻辑
            pass
        elif get_method == 'url':
            url = package['get']['url']
            extension = package['get'].get('extension', 'exe')
            SoftwareInstaller._url_download_static(url, name, extension, temp_folder)
        elif get_method == 'copy':
            # 复制文件不需要下载
            pass
    
    @staticmethod
    def _url_download_static(url: str, name: str, extension: str, temp_folder: Path, max_retries: int = 50) -> str:
        """静态方法：下载URL文件"""
        local_filename = temp_folder / f"{name}.{extension}"
        
        for attempt in range(max_retries):
            try:
                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(local_filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return str(local_filename)
            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise Exception(f"Failed to download {url} after {max_retries} attempts")
    
    def _url_download(self, url: str, name: str, extension: str = 'exe') -> str:
        """下载URL文件"""
        return self._url_download_static(url, name, extension, self.temp_folder, self.max_retries)
    
    def _install_manual_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """安装单个手动配置的软件包"""
        name = package.get('name', '')
        get_method = package.get('get', {}).get('method', '')
        install_info = package.get('install', {})
        
        if get_method == 'copy':
            # 复制文件，不需要安装
            copy_path = package['get']['path']
            category = install_info.get('category', 'Default')
            self._copy_files(copy_path, name, category)
            return {
                'success': True,
                'package': name,
                'message': f'{name} copied successfully'
            }
        
        # 查找安装文件
        installer_path = None
        for file in self.temp_folder.iterdir():
            if name.lower() in file.name.lower():
                installer_path = file
                break
        
        if get_method == 'local':
            installer_path = Path(package['get']['path'])
            if not installer_path.exists():
                raise FileNotFoundError(f"Local file not found: {installer_path}")
        
        if not installer_path:
            raise FileNotFoundError(f"Installer not found for {name}")
        
        # 运行安装程序
        self._run_installer(name, install_info, str(installer_path))
        
        return {
            'success': True,
            'package': name,
            'message': f'{name} installed successfully'
        }
    
    def _run_installer(self, name: str, install_info: Dict[str, Any], installer_path: str):
        """
        运行安装程序（使用pywinauto自动化）
        
        Args:
            name: 软件名称
            install_info: 安装配置信息
            installer_path: 安装程序路径
        """
        extension = Path(installer_path).suffix.lower()
        app = None
        
        if extension == '.exe':
            app = Application(backend="uia").start(installer_path)
        elif extension == '.msi':
            installer_path = os.path.abspath(installer_path)
            app = Application(backend="uia").start(f'msiexec /i "{installer_path}"')
        else:
            raise ValueError(f"Unsupported installer type: {extension}")
        
        # 确定安装路径
        category = install_info.get('category', 'Default')
        if category == 'Default':
            install_path = f'C:\\Program Files\\{name}'
        else:
            install_path = f'D:\\{category}\\{name}'
        
        # 执行安装步骤
        dlg = self._connect_to_window(install_info.get('title', ''))
        
        for step in install_info.get('steps', []):
            dlg = self._execute_step(step, dlg, install_path)
            time.sleep(0.2)
        
        # 等待安装完成
        if app:
            app.wait_for_process_exit(timeout=300)
    
    def _connect_to_window(self, window_title: str):
        """连接到安装窗口"""
        if not window_title:
            return None
        
        for attempt in range(100):
            try:
                app = Application(backend="uia").connect(title_re=window_title)
                return app.window(title=window_title)
            except Exception:
                time.sleep(1)
        
        raise Exception(f"Failed to connect to window: {window_title}")
    
    def _execute_step(self, step: List[Any], dlg, install_path: str):
        """执行单个安装步骤"""
        if not step or len(step) == 0:
            return dlg
        
        action = step[0]
        
        # 连接操作
        if action == 'connect':
            new_title = step[1]
            return self._connect_to_window(new_title)
        
        # 控件操作
        if action in ['click', 'edit', 'wait', 'check', 'uncheck', 'click_input']:
            self._control_operation(step, dlg, install_path)
        
        # 键盘鼠标操作
        elif action in ['mouse_click', 'keyboard_input']:
            self._keyboard_mouse_operation(step, dlg, install_path)
        
        # 延迟操作
        elif action == 'delay':
            time.sleep(float(step[1]))
        
        # 子窗口操作
        elif action == 'shift_window':
            window_title = step[1]
            dlg_tmp = dlg.child_window(title=window_title)
            for substep in step[2:]:
                self._execute_step(substep, dlg_tmp, install_path)
        
        return dlg
    
    def _find_control(self, control_identifier: str, dlg):
        """查找控件"""
        control_types = ['Button', 'Edit', 'CheckBox', 'Pane', 'ComboBox', 'Text']
        control_title = control_identifier
        control_type = None
        
        for ctrl_tp in control_types:
            if ctrl_tp in control_identifier:
                control_title = control_identifier.split(ctrl_tp)[0].strip()
                control_type = ctrl_tp
                break
        
        if control_type:
            return dlg.child_window(title=control_title, control_type=control_type)
        else:
            return dlg.child_window(title=control_identifier)
    
    def _control_operation(self, step: List[Any], dlg, install_path: str):
        """控件操作"""
        action = step[0]
        control = self._find_control(step[1], dlg)
        
        if action == 'click':
            control.click()
        elif action == 'edit':
            path = step[2].replace('{path}', install_path)
            control.set_text(path)
        elif action == 'wait':
            while not control.exists():
                time.sleep(0.2)
        elif action == 'check':
            if not control.get_toggle_state():
                control.click()
        elif action == 'uncheck':
            if control.get_toggle_state():
                control.click()
        elif action == 'click_input':
            try:
                control.click_input()
            except Exception:
                pass
    
    def _keyboard_mouse_operation(self, step: List[Any], dlg, install_path: str):
        """键盘鼠标操作"""
        action = step[0]
        
        if action == 'mouse_click':
            rect = dlg.rectangle()
            x_ratio, y_ratio = float(step[1]), float(step[2])
            x = int(rect.left + (rect.right - rect.left) * x_ratio)
            y = int(rect.top + (rect.bottom - rect.top) * y_ratio)
            mouse.click(button='left', coords=(x, y))
        elif action == 'keyboard_input':
            keys = step[1].replace('{path}', install_path)
            dlg.set_focus()
            dlg.type_keys(keys)
    
    @staticmethod
    def _copy_files(source_path: str, name: str, category: str):
        """复制文件或目录"""
        dest_path = f'D:\\{category}\\{name}' if category != 'Default' else name
        source = Path(source_path)
        
        if source.is_file():
            dest = Path(dest_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        elif source.is_dir():
            shutil.copytree(source, dest_path, dirs_exist_ok=True)
    
    @staticmethod
    def _parse_github_release(repo: str, pattern: str) -> Optional[str]:
        """
        获取GitHub仓库最新release中符合条件的软件包URL
        
        Args:
            repo: 仓库名称，格式为 'owner/repo'
            pattern: 用于匹配软件包名称的正则表达式模式
        
        Returns:
            符合条件的软件包URL，如果未找到则返回None
        """
        url = f'https://api.github.com/repos/{repo}/releases/latest'
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            assets = response.json().get('assets', [])
            
            for asset in assets:
                if re.search(pattern, asset['name']):
                    return asset['browser_download_url']
        except Exception:
            pass
        
        return None
    
    def install_from_config(self, config: Dict[str, Any], progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从配置字典安装软件
        
        Args:
            config: 配置字典，包含winget_packages和manual_packages
            progress_callback: 进度回调函数
        
        Returns:
            安装结果
        """
        results = {
            'winget': {'success': [], 'failed': []},
            'manual': {'success': [], 'failed': []}
        }
        
        # 安装Winget包
        if 'winget_packages' in config:
            winget_results = self.install_winget_packages(
                config['winget_packages'],
                progress_callback
            )
            results['winget'] = winget_results
        
        # 安装手动包
        if 'manual_packages' in config:
            manual_results = self.install_manual_packages(
                config['manual_packages'],
                progress_callback
            )
            results['manual'] = manual_results
        
        return results


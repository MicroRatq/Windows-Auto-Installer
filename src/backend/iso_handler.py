#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ISO镜像处理模块
"""
import os
import shutil
import requests
from typing import Dict, Any, Optional, Callable
from pathlib import Path
try:
    import pycdlib
    PYCDLIB_AVAILABLE = True
except ImportError:
    PYCDLIB_AVAILABLE = False

class ISOHandler:
    """ISO镜像处理器"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def download_windows_iso(self, version: str = "latest", progress_callback: Optional[Callable] = None) -> str:
        """
        下载Windows 11 ISO镜像
        
        Args:
            version: Windows版本（latest或具体版本号）
            progress_callback: 进度回调函数 (current, total)
        
        Returns:
            ISO文件路径
        """
        # TODO: 实现从微软官网或镜像站下载Windows 11 ISO
        # 这里需要实现具体的下载逻辑
        # 1. 获取下载链接
        # 2. 下载文件
        # 3. 验证文件完整性
        
        if progress_callback:
            progress_callback(0, 100)
        
        # 占位实现
        iso_path = self.cache_dir / f"windows11_{version}.iso"
        
        if progress_callback:
            progress_callback(100, 100)
        
        return str(iso_path)
    
    def select_local_iso(self, iso_path: str) -> str:
        """
        选择本地ISO文件
        
        Args:
            iso_path: ISO文件路径
        
        Returns:
            验证后的ISO文件路径
        """
        path = Path(iso_path)
        
        if not path.exists():
            raise FileNotFoundError(f"ISO文件不存在: {iso_path}")
        
        if not path.is_file():
            raise ValueError(f"路径不是文件: {iso_path}")
        
        if not path.suffix.lower() == '.iso':
            raise ValueError(f"文件不是ISO格式: {iso_path}")
        
        # 复制到缓存目录
        cached_path = self.cache_dir / path.name
        if not cached_path.exists():
            shutil.copy2(path, cached_path)
        
        return str(cached_path)
    
    def get_available_versions(self) -> list:
        """
        获取可用的Windows版本列表
        
        Returns:
            版本列表
        """
        # TODO: 实现获取可用版本列表
        # 这里可以从微软API或镜像站获取版本信息
        return [
            {"version": "latest", "name": "最新版本"},
            {"version": "22H2", "name": "Windows 11 22H2"},
            {"version": "23H2", "name": "Windows 11 23H2"},
        ]
    
    def prepare_iso_for_editing(self, iso_path: str) -> str:
        """
        准备ISO文件用于编辑（创建副本）
        
        Args:
            iso_path: 原始ISO文件路径
        
        Returns:
            准备编辑的ISO文件路径
        """
        source = Path(iso_path)
        if not source.exists():
            raise FileNotFoundError(f"ISO文件不存在: {iso_path}")
        
        # 创建编辑副本
        edit_path = self.cache_dir / f"edit_{source.name}"
        if edit_path.exists():
            edit_path.unlink()
        
        shutil.copy2(source, edit_path)
        
        return str(edit_path)
    
    def add_autounattend_to_iso(self, iso_path: str, autounattend_xml: str, output_path: Optional[str] = None) -> str:
        """
        将autounattend.xml添加到ISO镜像
        
        Args:
            iso_path: ISO文件路径
            autounattend_xml: autounattend.xml内容
            output_path: 输出ISO路径（如果为None，则覆盖原文件）
        
        Returns:
            输出ISO文件路径
        """
        if not PYCDLIB_AVAILABLE:
            raise ImportError("pycdlib库未安装，请运行: pip install pycdlib")
        
        iso_file = Path(iso_path)
        if not iso_file.exists():
            raise FileNotFoundError(f"ISO文件不存在: {iso_path}")
        
        if output_path is None:
            output_path = str(iso_file)
        else:
            # 如果输出路径不同，先复制文件
            if output_path != iso_path:
                shutil.copy2(iso_path, output_path)
        
        # 创建临时autounattend.xml文件
        temp_xml = self.cache_dir / "autounattend.xml"
        with open(temp_xml, 'w', encoding='utf-8') as f:
            f.write(autounattend_xml)
        
        try:
            # 使用pycdlib编辑ISO
            iso = pycdlib.PyCdlib()
            iso.open(output_path)
            
            # 添加autounattend.xml到ISO根目录
            iso.add_file(str(temp_xml), '/AUTOUNATTEND.XML')
            
            # 保存ISO
            iso.write(output_path)
            iso.close()
            
        finally:
            # 清理临时文件
            if temp_xml.exists():
                temp_xml.unlink()
        
        return output_path


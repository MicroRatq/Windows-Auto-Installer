
import logging
import os
import hashlib
from pathlib import Path
from typing import Any, Optional

from iso_reader import ISOReader
from wim_handler import WIMHandler

logger = logging.getLogger('ISOInspector')

class ISOInspector:
    """
    ISO 镜像识别服务类
    负责分析 ISO 内容并提取 OS 版本、架构、语言等信息
    """
    
    def __init__(self, iso_path: str):
        self.iso_path = Path(iso_path)
        if not self.iso_path.exists():
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
            
    def get_summary(self) -> dict[str, Any]:
        """
        执行完整扫描并返回 ISO 信息的汇总
        """
        logger.info(f"Starting inspection for: {self.iso_path}")
        
        result = {
            "os_type": "Windows",
            "version": "",
            "build": "",
            "build_major": "",
            "build_minor": "",
            "arch": "x64",
            "language": "zh-cn",
            "edition": "",
            "source_type": "me", # Multi-Edition
            "checksum": "",
            "file_size": self.iso_path.stat().st_size
        }
        
        # 1. 计算哈希 (可选，如果速度太慢可以跳过)
        # result["checksum"] = self._calculate_sha256()
        
        # 2. 尝试从文件名解析 (初步猜测)
        filename_info = self._parse_filename(self.iso_path.name)
        if filename_info:
            result.update(filename_info)
            
        # 3. 深度扫描内容 (如果文件名信息不全)
        content_info = self._inspect_content()
        if content_info:
            result.update(content_info)
            
        return result

    def _parse_filename(self, filename: str) -> dict[str, str]:
        """
        从标准格式的文件名解析信息
        格式示例: win11me_24h2_26100_1742_zh-cn_x64.iso
        """
        parts = filename.lower().replace(".iso", "").split("_")
        if len(parts) < 6:
            return {}
            
        return {
            "os_type": "Windows11" if "win11" in parts[0] else "Windows10",
            "source_type": "me" if "me" in parts[0] else "ce",
            "version": parts[1].upper(),
            "build_major": parts[2],
            "build_minor": parts[3],
            "build": f"{parts[2]}.{parts[3]}",
            "language": parts[4],
            "arch": parts[5]
        }

    def _inspect_content(self) -> dict[str, Any]:
        """
        使用 ISOReader 提取关键文件进行深度识别
        """
        info = {}
        reader = ISOReader(str(self.iso_path))
        
        # 使用临时目录存放提取的小文件
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # 1. 尝试查找 lang.ini 获取语言
            lang_ini_path = tmp_path / "lang.ini"
            try:
                reader.extract_file("/sources/lang.ini", str(lang_ini_path))
                lang = self._parse_lang_ini(lang_ini_path)
                if lang:
                    info["language"] = lang
            except:
                pass
                
            # 2. 尝试识别 WIM/ESD 信息
            wim_info = self._inspect_wim_metadata(reader, tmp_path)
            if wim_info:
                info.update(wim_info)
                
        return info

    def _parse_lang_ini(self, path: Path) -> Optional[str]:
        """解析 lang.ini 中的可用语言"""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            in_section = False
            for line in content.splitlines():
                line = line.strip()
                if line == "[Available UI Languages]":
                    in_section = True
                    continue
                if in_section and "=" in line:
                    return line.split("=")[0].strip().lower()
        except:
            pass
        return None

    def _inspect_wim_metadata(self, reader: ISOReader, tmp_path: Path) -> dict[str, Any]:
        """
        定位并解析 install.wim/esd 的元数据
        """
        # 1. 获取 sources 目录下的文件列表以确定最佳识别目标
        try:
            files = [f.lower() for f in reader.list_directory("/sources")]
        except Exception as e:
            logger.debug(f"Failed to list /sources directory: {e}")
            return {}

        # 2. 按照准确度优先级确定目标文件
        # 优先使用安装镜像 (wim > esd)，最后回退到引导镜像 (boot.wim)
        target_name = None
        if "install.wim" in files:
            target_name = "install.wim"
        elif "install.esd" in files:
            target_name = "install.esd"
        elif "boot.wim" in files:
            target_name = "boot.wim"
            
        if not target_name:
            logger.warning("No suitable WIM/ESD file found in /sources")
            return {}
            
        iso_file_path = f"/sources/{target_name}"
        
        # 3. 提取并解析元数据
        try:
            local_wim = tmp_path / "metadata.wim"
            logger.info(f"Extracting {iso_file_path} for metadata inspection...")
            reader.extract_file(iso_file_path, str(local_wim))
            
            with WIMHandler(str(local_wim)) as handler:
                build_major = handler.get_image_info(1, "build") or ""
                build_minor = handler.get_image_info(1, "sp_build") or "0"
                arch_name = handler.get_image_info(1, "architecture_name") or "x64"
                edition = handler.get_image_info(1, "edition") or handler.get_image_info(1, "name") or ""
                os_type = handler.get_image_info(1, "os_type") or "Windows10"
                
                # 映射版本号 (例如 26100 -> 24H2)
                version_name = self._map_build_to_version(build_major)
                
                return {
                    "version": version_name,
                    "build_major": build_major,
                    "build_minor": build_minor,
                    "build": f"{build_major}.{build_minor}",
                    "arch": arch_name,
                    "edition": edition,
                    "os_type": os_type
                }
        except Exception as e:
            logger.error(f"Failed to inspect metadata from {iso_file_path}: {e}")
            
        return {}

    def _map_build_to_version(self, build: str) -> str:
        """将构建号映射为友好的版本名"""
        mapping = {
            "26100": "24H2",
            "22631": "23H2",
            "22621": "22H2",
            "22000": "21H2",
            "19045": "22H2",
            "19044": "21H2",
            "19043": "21H1",
        }
        return mapping.get(build, build)

    def _calculate_sha256(self) -> str:
        """计算大文件的 SHA256"""
        sha256_hash = hashlib.sha256()
        with open(self.iso_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096 * 1024), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

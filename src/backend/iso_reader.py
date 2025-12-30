"""
ISO image read-only operations module
Supports reading files, listing directories, and extracting files from ISO images
"""
import sys
import logging
import tempfile
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('ISOReader')


class ISOReader:
    """ISO 只读操作上下文管理器"""
    
    def __init__(self, iso_path: str):
        """
        初始化 ISO 读取器
        
        Args:
            iso_path: ISO 文件路径
        """
        self.iso_path = Path(iso_path)
        if not self.iso_path.exists():
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
        
        self.iso = None
        self.use_udf = False
        self.use_joliet = False
        self.facade = None
    
    def __enter__(self) -> 'ISOReader':
        """上下文管理器入口"""
        try:
            from pycdlib.pycdlib import PyCdlib
        except ImportError:
            raise ImportError("pycdlib not installed. Please install it with: pip install pycdlib")
        
        logger.info(f"Opening ISO file: {self.iso_path}")
        self.iso = PyCdlib()
        self.iso.open(str(self.iso_path))
        
        # 检测文件系统类型
        self.use_udf = self.iso.has_udf()
        self.use_joliet = self.iso.has_joliet()
        logger.debug(f"ISO filesystem: UDF={self.use_udf}, Joliet={self.use_joliet}")
        
        # 获取 facade
        self.facade = self._get_facade()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.iso:
            try:
                self.iso.close()
            except:
                pass
        return False
    
    def _get_facade(self) -> Any:
        """
        获取适当的 facade
        
        Returns:
            UDF、Joliet 或 ISO9660 facade
        """
        if self.use_udf:
            return self.iso.get_udf_facade()
        elif self.use_joliet:
            return self.iso.get_joliet_facade()
        else:
            return self.iso.get_iso9660_facade()
    
    def _decode_filename(self, identifier_bytes: bytes) -> str:
        """
        解码文件名
        
        Args:
            identifier_bytes: 文件名字节串
        
        Returns:
            解码后的文件名
        """
        if self.use_udf:
            # UDF 使用 UTF-16BE 编码
            try:
                return identifier_bytes.decode('utf-16-be', errors='ignore').strip('\x00')
            except:
                return identifier_bytes.decode('utf-8', errors='ignore').strip('\x00')
        else:
            # ISO9660/Joliet 使用 UTF-8 编码
            return identifier_bytes.decode('utf-8', errors='ignore').strip('\x00')
    
    def get_filesystem_info(self) -> dict[str, Any]:
        """
        获取文件系统信息
        
        Returns:
            包含文件系统信息的字典:
            - udf: 是否使用 UDF
            - joliet: 是否使用 Joliet
            - udf_version: UDF 版本（如果使用）
            - joliet_level: Joliet 级别（如果使用）
        """
        return {
            "udf": self.use_udf,
            "joliet": self.use_joliet,
            "udf_version": "2.60" if self.use_udf else None,
            "joliet_level": 3 if self.use_joliet else None
        }
    
    def read_file(self, iso_path: str) -> bytes:
        """
        读取 ISO 中的文件内容
        
        Args:
            iso_path: ISO 中的文件路径（如 '/sources/lang.ini'）
        
        Returns:
            文件内容的字节串
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        # 标准化路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        try:
            with self.facade.open_file_from_iso(iso_path) as infp:
                # 对于大文件，使用分块读取
                file_size = infp.seek(0, 2)  # 移动到末尾获取大小
                infp.seek(0)  # 回到开头
                
                if file_size > 100 * 1024 * 1024:  # > 100MB
                    # 大文件分块读取
                    content = bytearray()
                    chunk_size = 1024 * 1024  # 1MB
                    bytes_read = 0
                    while True:
                        chunk = infp.read(chunk_size)
                        if not chunk:
                            break
                        content.extend(chunk)
                        bytes_read += len(chunk)
                        # 每 100MB 显示一次进度
                        if bytes_read % (100 * 1024 * 1024) == 0:
                            logger.debug(f"Reading {bytes_read / (1024**2):.0f} MB / {file_size / (1024**2):.0f} MB")
                    return bytes(content)
                else:
                    # 小文件直接读取
                    return infp.read()
        except Exception as e:
            raise FileNotFoundError(f"File not found or cannot be read: {iso_path} ({e})")
    
    def read_file_text(self, iso_path: str, encoding: str = 'utf-8') -> str:
        """
        读取 ISO 中的文本文件
        
        Args:
            iso_path: ISO 中的文件路径
            encoding: 文本编码（默认 utf-8）
        
        Returns:
            文件内容的字符串
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        content = self.read_file(iso_path)
        return content.decode(encoding, errors='ignore')
    
    def list_directory(self, iso_path: str = '/') -> list[str]:
        """
        列出目录内容
        
        Args:
            iso_path: ISO 中的目录路径（默认 '/'）
        
        Returns:
            文件/目录名列表
        """
        # 标准化路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        try:
            children = list(self.facade.list_children(iso_path))
            result = []
            
            for item in children:
                if item is None:
                    continue
                
                try:
                    if hasattr(item, 'file_identifier'):
                        identifier_bytes = item.file_identifier()
                        name = self._decode_filename(identifier_bytes)
                    else:
                        name = str(item)
                    
                    if name:
                        result.append(name)
                except Exception as e:
                    logger.debug(f"Error decoding filename: {e}")
                    continue
            
            return result
        except Exception as e:
            logger.debug(f"Error listing directory {iso_path}: {e}")
            return []
    
    def extract_file(self, iso_path: str, output_path: str) -> None:
        """
        提取 ISO 中的文件到本地路径（支持大文件分块）
        
        Args:
            iso_path: ISO 中的文件路径
            output_path: 输出文件路径
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        # 标准化路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with self.facade.open_file_from_iso(iso_path) as infp:
                # 获取文件大小
                file_size = infp.seek(0, 2)
                infp.seek(0)
                
                logger.info(f"Extracting {iso_path} ({file_size / (1024**2):.2f} MB) to {output_path}")
                
                # 分块写入
                with open(output_file, 'wb') as outfp:
                    chunk_size = 1024 * 1024  # 1MB
                    bytes_written = 0
                    while True:
                        chunk = infp.read(chunk_size)
                        if not chunk:
                            break
                        outfp.write(chunk)
                        bytes_written += len(chunk)
                        # 每 100MB 显示一次进度
                        if bytes_written % (100 * 1024 * 1024) == 0:
                            progress = (bytes_written / file_size) * 100
                            logger.debug(f"Extraction progress: {progress:.1f}% ({bytes_written // (1024*1024)}MB / {file_size // (1024*1024)}MB)")
                
                logger.info(f"Successfully extracted {iso_path} to {output_path}")
        except Exception as e:
            raise FileNotFoundError(f"File not found or cannot be extracted: {iso_path} ({e})")
    
    def file_exists(self, iso_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            文件是否存在
        """
        # 标准化路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        try:
            with self.facade.open_file_from_iso(iso_path):
                return True
        except:
            return False
    
    def get_file_size(self, iso_path: str) -> int:
        """
        获取文件大小
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            文件大小（字节）
        
        Raises:
            FileNotFoundError: 文件不存在
        """
        # 标准化路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        try:
            with self.facade.open_file_from_iso(iso_path) as infp:
                file_size = infp.seek(0, 2)  # 移动到末尾
                return file_size
        except Exception as e:
            raise FileNotFoundError(f"File not found: {iso_path} ({e})")


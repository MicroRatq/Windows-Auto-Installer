"""
ISO image modification module
Supports adding/replacing files in ISO images while preserving boot information
"""
import sys
import logging
from pathlib import Path
from typing import Any

from iso_reader import ISOReader
from iso_writer import ISOWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('ISOModifier')


class ISOModifier:
    """ISO镜像修改器，支持添加/替换文件并保持引导信息"""
    
    def __init__(self, iso_path: str):
        """
        初始化ISO修改器
        
        Args:
            iso_path: 原始ISO文件路径
        """
        self.iso_path = Path(iso_path)
        if not self.iso_path.exists():
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
    
    # ==================== 只读操作 API（委托给 ISOReader） ====================
    
    def open_readonly(self) -> ISOReader:
        """
        打开 ISO 进行只读操作，返回 ISOReader 对象
        
        Returns:
            ISOReader 对象（上下文管理器）
        """
        return ISOReader(str(self.iso_path))
    
    def get_filesystem_info(self) -> dict[str, Any]:
        """
        获取文件系统信息（UDF/Joliet/ISO9660）
        
        Returns:
            包含文件系统信息的字典
        """
        with self.open_readonly() as reader:
            return reader.get_filesystem_info()
    
    def read_file(self, iso_path: str) -> bytes:
        """
        读取 ISO 中的文件内容
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            文件内容的字节串
        """
        with self.open_readonly() as reader:
            return reader.read_file(iso_path)
    
    def read_file_text(self, iso_path: str, encoding: str = 'utf-8') -> str:
        """
        读取 ISO 中的文本文件
        
        Args:
            iso_path: ISO 中的文件路径
            encoding: 文本编码（默认 utf-8）
        
        Returns:
            文件内容的字符串
        """
        with self.open_readonly() as reader:
            return reader.read_file_text(iso_path, encoding)
    
    def list_directory(self, iso_path: str = '/') -> list[str]:
        """
        列出目录内容
        
        Args:
            iso_path: ISO 中的目录路径（默认 '/'）
        
        Returns:
            文件/目录名列表
        """
        with self.open_readonly() as reader:
            return reader.list_directory(iso_path)
    
    def extract_file(self, iso_path: str, output_path: str) -> None:
        """
        提取 ISO 中的文件到本地路径（支持大文件分块）
        
        Args:
            iso_path: ISO 中的文件路径
            output_path: 输出文件路径
        """
        with self.open_readonly() as reader:
            reader.extract_file(iso_path, output_path)
    
    def file_exists(self, iso_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            文件是否存在
        """
        with self.open_readonly() as reader:
            return reader.file_exists(iso_path)
    
    def get_file_size(self, iso_path: str) -> int:
        """
        获取文件大小
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            文件大小（字节）
        """
        with self.open_readonly() as reader:
            return reader.get_file_size(iso_path)
    
    # ==================== 写入操作 API（委托给 ISOWriter） ====================
    
    def create_writer(self) -> ISOWriter:
        """
        创建 ISO 写入器，用于批量操作
        
        Returns:
            ISOWriter 对象
        """
        return ISOWriter(str(self.iso_path))
    
    def add_file(self, local_path: str, iso_path: str, output_path: str) -> dict[str, Any]:
        """
        添加文件到 ISO（创建新 ISO）
        
        Args:
            local_path: 本地文件路径
            iso_path: ISO 中的文件路径
            output_path: 输出ISO文件路径
        
        Returns:
            包含操作结果的字典
        """
        writer = self.create_writer()
        writer.add_file(local_path, iso_path)
        return writer.write(output_path)
    
    def replace_file(self, iso_path: str, local_path: str, output_path: str) -> dict[str, Any]:
        """
        替换 ISO 中的文件（创建新 ISO）
        
        Args:
            iso_path: ISO 中的文件路径（如 '/autounattend.xml'）
            local_path: 本地文件路径
            output_path: 输出ISO文件路径
        
        Returns:
            包含操作结果的字典
        """
        writer = self.create_writer()
        writer.replace_file(iso_path, local_path)
        return writer.write(output_path)
    
    def remove_file(self, iso_path: str, output_path: str) -> dict[str, Any]:
        """
        从 ISO 中删除文件（创建新 ISO）
        
        Args:
            iso_path: ISO 中的文件路径
            output_path: 输出ISO文件路径
        
        Returns:
            包含操作结果的字典
        """
        writer = self.create_writer()
        writer.remove_file(iso_path)
        return writer.write(output_path)
    
    # ==================== 高级业务 API（使用基本 API 实现） ====================
    
    def add_autounattend(self, xml_path: str, output_path: str) -> dict[str, Any]:
        """
        将 autounattend.xml 添加到 ISO 根目录并生成新 ISO
        
        Args:
            xml_path: autounattend.xml 文件路径
            output_path: 输出ISO文件路径
        
        Returns:
            包含操作结果的字典:
            - success: 是否成功
            - message: 结果消息
            - output_path: 输出文件路径
        """
        xml_file = Path(xml_path)
        if not xml_file.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        
        autounattend_path = '/autounattend.xml'
        
        # 检查文件是否已存在，如果存在则替换，否则添加
        if self.file_exists(autounattend_path):
            logger.info("Found existing autounattend.xml, will replace it")
            return self.replace_file(autounattend_path, str(xml_file), output_path)
        else:
            logger.info("Adding new autounattend.xml to ISO")
            return self.add_file(str(xml_file), autounattend_path, output_path)
    
    def extract_wim_file(self, output_path: str) -> dict[str, Any]:
        """
        提取 install.wim/install.esd 文件
        
        Args:
            output_path: 输出文件路径
        
        Returns:
            包含操作结果的字典:
            - success: 是否成功
            - message: 结果消息
            - output_path: 输出文件路径
            - file_size: 文件大小
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 查找 install.wim 或 install.esd
        sources_files = self.list_directory('/sources')
        wim_file = None
        
        for filename in sources_files:
            filename_lower = filename.lower()
            if 'install' in filename_lower and ('.wim' in filename_lower or '.esd' in filename_lower):
                wim_file = f'/sources/{filename}'
                break
        
        if not wim_file:
            return {
                "success": False,
                "message": "install.wim or install.esd not found in ISO",
                "output_path": str(output_file)
            }
        
        try:
            logger.info(f"Extracting {wim_file} to {output_path}")
            self.extract_file(wim_file, str(output_file))
            
            file_size = output_file.stat().st_size
            return {
                "success": True,
                "message": f"Successfully extracted {wim_file}",
                "output_path": str(output_file),
                "file_size": file_size
            }
        except Exception as e:
            logger.error(f"Failed to extract WIM file: {e}")
            return {
                "success": False,
                "message": f"Failed to extract WIM file: {str(e)}",
                "output_path": str(output_file)
            }
    
    def read_lang_ini(self) -> dict[str, Any]:
        """
        读取 sources/lang.ini 文件
        
        Returns:
            包含操作结果的字典:
            - success: 是否成功
            - content: 文件内容（如果成功）
            - message: 结果消息
        """
        lang_ini_path = '/sources/lang.ini'
        
        try:
            if not self.file_exists(lang_ini_path):
                return {
                    "success": False,
                    "message": "lang.ini not found in ISO"
                }
            
            content = self.read_file_text(lang_ini_path)
            return {
                "success": True,
                "content": content,
                "message": "Successfully read lang.ini"
            }
        except Exception as e:
            logger.error(f"Failed to read lang.ini: {e}")
            return {
                "success": False,
                "message": f"Failed to read lang.ini: {str(e)}"
            }


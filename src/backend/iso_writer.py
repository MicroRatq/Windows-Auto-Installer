"""
ISO image write operations module
Supports adding, replacing, and removing files in ISO images while preserving boot information
Uses xorriso for ISO creation to handle large files (>4GB) properly
"""
import sys
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('ISOWriter')


class ISOWriter:
    """ISO 写入操作构建器，使用 xorriso 进行 ISO 打包"""
    
    def __init__(self, source_iso_path: str):
        """
        初始化 ISO 写入器
        
        Args:
            source_iso_path: 源 ISO 文件路径
        """
        self.source_iso_path = Path(source_iso_path)
        if not self.source_iso_path.exists():
            raise FileNotFoundError(f"Source ISO file not found: {source_iso_path}")
        
        # xorriso 工具路径
        self.xorriso_exe_path = self._get_xorriso_path()
        
        # 源 ISO 信息（用于检测文件系统类型和引导信息）
        self.source_iso = None
        self.use_udf = False
        self.use_joliet = False
        
        # 临时目录（用于提取 ISO 内容和文件操作）
        self.temp_dir = None
        
        # 文件操作队列
        self.skip_files = set()  # 要跳过的文件（将被替换或删除）
        self.add_files = {}  # {iso_path: local_path} 要添加的文件
    
    def _get_xorriso_path(self) -> Path:
        """
        获取 xorriso.exe 的路径
        
        Returns:
            xorriso.exe 的 Path 对象
        
        Raises:
            FileNotFoundError: 如果 xorriso.exe 不存在
        """
        # 尝试从项目根目录查找
        # 假设 iso_writer.py 在 src/backend/，xorriso 在 src/shared/xorriso/
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        xorriso_path = project_root / "src" / "shared" / "xorriso" / "xorriso.exe"
        
        if xorriso_path.exists():
            logger.debug(f"Found xorriso at: {xorriso_path}")
            return xorriso_path
        
        # 如果找不到，抛出错误
        raise FileNotFoundError(
            f"xorriso.exe not found at: {xorriso_path}\n"
            f"Please ensure xorriso is available at src/shared/xorriso/xorriso.exe\n"
            f"Download from: https://github.com/PeyTy/xorriso-exe-for-windows"
        )
    
    def _detect_iso_filesystem(self, iso: Any) -> dict[str, Any]:
        """
        检测 ISO 的文件系统类型
        
        Args:
            iso: PyCdlib ISO 对象
        
        Returns:
            包含文件系统配置信息的字典
        """
        use_udf = iso.has_udf()
        use_joliet = iso.has_joliet()
        
        return {
            "udf": use_udf,
            "joliet": use_joliet,
            "udf_version": "2.60" if use_udf else None,
            "joliet_level": 3 if use_joliet else None
        }
    
    def _extract_iso_to_directory(self, extract_dir: Path) -> None:
        """
        使用 ISOReader 递归提取 ISO 所有内容到目录
        
        Args:
            extract_dir: 提取目标目录
        """
        from iso_reader import ISOReader
        
        logger.info(f"Extracting ISO contents to: {extract_dir}")
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        files_extracted = [0]
        
        def extract_recursive(reader: ISOReader, iso_path: str, local_path: Path) -> None:
            """递归提取文件和目录"""
            # 检查是否应该跳过此文件
            if iso_path in self.skip_files:
                logger.debug(f"Skipping file (will be replaced/removed): {iso_path}")
                return
            
            # 先尝试作为目录处理（目录通常有子项）
            try:
                children = reader.list_directory(iso_path)
                if children is not None and len(children) > 0:
                    # 是目录，创建本地目录并递归
                    local_path.mkdir(parents=True, exist_ok=True)
                    for child in children:
                        if not child:
                            continue
                        child_iso_path = (iso_path.rstrip('/') + '/' + child).replace('//', '/')
                        child_local_path = local_path / child
                        extract_recursive(reader, child_iso_path, child_local_path)
                    return
            except Exception:
                # 不是目录或无法列出，继续尝试作为文件
                pass
            
            # 尝试作为文件提取
            try:
                if reader.file_exists(iso_path):
                    reader.extract_file(iso_path, str(local_path))
                    files_extracted[0] += 1
                    if files_extracted[0] % 100 == 0:
                        logger.info(f"Extracted {files_extracted[0]} files...")
            except Exception as e:
                logger.debug(f"Error extracting {iso_path}: {e}")
        
        with ISOReader(str(self.source_iso_path)) as reader:
            extract_recursive(reader, '/', extract_dir)
        
        logger.info(f"Extracted {files_extracted[0]} files from ISO")
    
    def _identify_boot_type(self, boot_file_path: str) -> str:
        """
        根据文件路径识别引导类型
        
        Args:
            boot_file_path: 引导文件路径
        
        Returns:
            'bios' 或 'uefi'
        """
        boot_file_lower = boot_file_path.lower()
        
        # BIOS 引导文件特征
        if 'etfsboot.com' in boot_file_lower or 'bootmgr' in boot_file_lower:
            return 'bios'
        
        # UEFI 引导文件特征
        if 'efisys.bin' in boot_file_lower or 'efi/boot' in boot_file_lower:
            return 'uefi'
        
        # 默认返回 BIOS（大多数情况下第一个入口是 BIOS）
        return 'bios'
    
    def _detect_boot_info(self) -> dict[str, Any]:
        """
        检测源 ISO 的引导信息（El Torito boot catalog）
        检测所有引导入口，包括 BIOS 和 UEFI
        
        Returns:
            包含引导信息的字典:
            - has_boot: 是否有引导信息
            - bios_boot: BIOS 引导信息（如果存在）
            - uefi_boot: UEFI 引导信息（如果存在）
        """
        try:
            from pycdlib.pycdlib import PyCdlib
        except ImportError:
            return {"has_boot": False}
        
        try:
            iso = PyCdlib()
            iso.open(str(self.source_iso_path))
            
            boot_info: dict[str, Any] = {"has_boot": False}
            
            # 检查是否有 El Torito boot catalog
            if hasattr(iso, 'eltorito_boot_catalog') and iso.eltorito_boot_catalog:
                boot_catalog = iso.eltorito_boot_catalog
                boot_info["has_boot"] = True
                
                # 收集所有引导入口
                all_entries = []
                
                # 添加 initial_entry
                if hasattr(boot_catalog, 'initial_entry') and boot_catalog.initial_entry:
                    all_entries.append(boot_catalog.initial_entry)
                
                # 添加其他入口
                if hasattr(boot_catalog, 'entries'):
                    all_entries.extend(boot_catalog.entries)
                
                # 分析每个引导入口
                # 注意：pycdlib 的 EltoritoEntry 使用 inode 指向引导文件，不直接存储路径
                # 我们需要通过检查常见的引导文件来确定路径
                
                # 使用 ISOReader 检查引导文件（更可靠的方法）
                from iso_reader import ISOReader
                
                # 常见的 Windows 引导文件路径（注意大小写）
                # 注意：Windows ISO 的 UEFI 引导应该优先使用 efisys.bin，而不是 bootx64.efi
                common_boot_files = {
                    'bios': ['/boot/etfsboot.com', '/bootmgr', '/boot/bootmgr'],
                    'uefi': ['/efi/microsoft/boot/efisys.bin', '/efi/microsoft/boot/efisys_noprompt.bin', '/boot/efisys.bin', '/boot/efisys_noprompt.bin', '/efi/boot/bootx64.efi', '/efi/boot/bootia32.efi']
                }
                
                # 检查哪些引导文件存在（使用 ISOReader）
                found_boot_files = {}
                with ISOReader(str(self.source_iso_path)) as reader:
                    for boot_type, paths in common_boot_files.items():
                        for path in paths:
                            try:
                                if reader.file_exists(path):
                                    found_boot_files[boot_type] = path
                                    logger.info(f"Found {boot_type.upper()} boot file: {path}")
                                    break
                            except Exception as e:
                                logger.debug(f"Error checking boot file {path}: {e}")
                                continue
                
                if not found_boot_files:
                    logger.warning("No boot files found in ISO - ISO may not be bootable")
                else:
                    logger.info(f"Detected boot files: {found_boot_files}")
                
                # 根据找到的引导文件和 boot catalog 入口分配引导类型
                # 通常第一个入口是 BIOS，第二个是 UEFI
                entry_index = 0
                for entry in all_entries:
                    if not entry:
                        continue
                    
                    boot_file = None
                    boot_type = None
                    
                    # 根据入口索引和找到的文件分配
                    if entry_index == 0 and 'bios' in found_boot_files:
                        boot_file = found_boot_files['bios']
                        boot_type = 'bios'
                    elif entry_index == 1 and 'uefi' in found_boot_files:
                        boot_file = found_boot_files['uefi']
                        boot_type = 'uefi'
                    elif entry_index == 0 and 'uefi' in found_boot_files and 'bios' not in found_boot_files:
                        # 如果只有 UEFI，第一个入口可能是 UEFI
                        boot_file = found_boot_files['uefi']
                        boot_type = 'uefi'
                    
                    if not boot_file:
                        entry_index += 1
                        continue
                    
                    # 标准化路径（确保以 / 开头）
                    if not boot_file.startswith('/'):
                        boot_file = '/' + boot_file
                    
                    # 如果还没有确定类型，使用 _identify_boot_type 辅助方法
                    if not boot_type:
                        boot_type = self._identify_boot_type(boot_file)
                    
                    # 提取引导参数
                    boot_load_size = 8  # 默认值
                    if hasattr(entry, 'boot_load_size'):
                        boot_load_size = entry.boot_load_size
                    elif hasattr(entry, 'sector_count'):
                        # 如果没有 boot_load_size，尝试从 sector_count 推断
                        boot_load_size = entry.sector_count
                    
                    boot_info_table = True  # 默认启用
                    # pycdlib 的 EltoritoEntry 没有直接的 boot_info_table 属性
                    # 但通常 Windows ISO 的 BIOS 引导需要 boot-info-table
                    if boot_type == 'bios':
                        boot_info_table = True
                    
                    no_emul_boot = True  # 默认启用
                    if hasattr(entry, 'boot_indicator'):
                        # boot_indicator: 0x88 = no emulation boot
                        no_emul_boot = (entry.boot_indicator == 0x88)
                    
                    # 构建引导信息
                    entry_info = {
                        "file": boot_file,
                        "load_size": boot_load_size,
                        "info_table": boot_info_table,
                        "no_emul_boot": no_emul_boot
                    }
                    
                    # 根据类型存储
                    if boot_type == 'bios':
                        if 'bios_boot' not in boot_info:
                            boot_info['bios_boot'] = entry_info
                            logger.info(f"Detected BIOS boot file: {boot_file}")
                    elif boot_type == 'uefi':
                        if 'uefi_boot' not in boot_info:
                            boot_info['uefi_boot'] = entry_info
                            logger.info(f"Detected UEFI boot file: {boot_file}")
                    
                    entry_index += 1
                
                # 如果找到了 UEFI 引导文件，但 boot catalog 中没有对应的入口，仍然添加 UEFI 引导信息
                # （Windows ISO 通常支持双模式引导，即使 boot catalog 只有一个入口）
                if 'uefi' in found_boot_files and 'uefi_boot' not in boot_info:
                    uefi_file = found_boot_files['uefi']
                    boot_info['uefi_boot'] = {
                        "file": uefi_file,
                        "load_size": 0,  # UEFI 引导不需要 load_size
                        "info_table": False,  # UEFI 引导不需要 boot-info-table
                        "no_emul_boot": True
                    }
                    logger.info(f"Added UEFI boot file (not in boot catalog): {uefi_file}")
            
            iso.close()
            return boot_info
            
        except Exception as e:
            logger.warning(f"Could not detect boot information: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {"has_boot": False}
    
    def _windows_to_cygwin_path(self, path: Path) -> str:
        """
        将 Windows 路径转换为 Cygwin 路径格式
        
        Args:
            path: Windows 路径
        
        Returns:
            Cygwin 路径格式（如 /cygdrive/c/path/to/file）
        """
        path_str = str(path.resolve())
        # 将 Windows 路径转换为 Cygwin 格式
        # C:\path\to\file -> /cygdrive/c/path/to/file
        if path_str[1] == ':':
            drive = path_str[0].lower()
            rest = path_str[2:].replace('\\', '/')
            return f"/cygdrive/{drive}{rest}"
        return path_str.replace('\\', '/')
    
    def _build_xorriso_command(
        self,
        source_dir: Path,
        output_path: Path,
        fs_info: dict[str, Any],
        boot_info: dict[str, Any]
    ) -> list[str]:
        """
        构建 xorriso 命令参数
        
        Args:
            source_dir: 源目录路径（ISO 内容）
            output_path: 输出 ISO 文件路径
            fs_info: 文件系统信息
            boot_info: 引导信息
        
        Returns:
            xorriso 命令参数列表
        """
        cmd = [str(self.xorriso_exe_path)]
        
        # 使用 -as mkisofs 模式（兼容 mkisofs 命令）
        # 注意：对于 UDF ISO，我们使用 Joliet + Rock Ridge，因为 mkisofs 模式不支持 -udf
        # Joliet + Rock Ridge 也支持大文件（>4GB），可以满足需求
        cmd.extend(["-as", "mkisofs"])
        
        # 文件系统类型参数
        if fs_info.get("udf"):
            # UDF 文件系统：使用 Joliet + Rock Ridge 代替（也支持大文件）
            cmd.append("-J")  # Joliet
            cmd.append("-R")   # Rock Ridge
            logger.info("Source ISO uses UDF, creating with Joliet + Rock Ridge (supports large files)")
        elif fs_info.get("joliet"):
            # Joliet 文件系统
            cmd.append("-J")
            cmd.append("-R")  # 通常与 Rock Ridge 一起使用
            logger.info("Using Joliet filesystem with Rock Ridge")
        else:
            # ISO9660 with Rock Ridge
            cmd.append("-R")
            logger.info("Using ISO9660 with Rock Ridge")
        
        # 支持大文件（>4GB）
        cmd.extend(["-iso-level", "3"])
        
        # 卷标（可选，但建议添加以避免警告）
        cmd.extend(["-V", "ISO_IMAGE"])
        
        # 引导信息
        # BIOS 引导
        bios_boot_info = boot_info.get("bios_boot")
        if bios_boot_info and isinstance(bios_boot_info, dict):
            bios_file = bios_boot_info.get("file", "")
            if bios_file:
                bios_file_local = source_dir / bios_file.lstrip('/')
                
                if bios_file_local.exists():
                    # 使用正确的 El Torito BIOS 引导参数
                    cmd.extend([
                        "-eltorito-boot", bios_file.lstrip('/'),
                        "-no-emul-boot"
                    ])
                    
                    # 添加 boot-load-size（如果指定）
                    load_size = bios_boot_info.get("load_size", 8)
                    if load_size:
                        cmd.extend(["-boot-load-size", str(load_size)])
                    
                    # 添加 boot-info-table（如果启用）
                    if bios_boot_info.get("info_table", True):
                        cmd.append("-boot-info-table")
                    
                    logger.info(f"Adding BIOS boot: {bios_file}")
                else:
                    logger.warning(f"BIOS boot file not found in extracted directory: {bios_file}")
        
        # UEFI 引导
        uefi_boot_info = boot_info.get("uefi_boot")
        if uefi_boot_info and isinstance(uefi_boot_info, dict):
            uefi_file = uefi_boot_info.get("file", "")
            if uefi_file:
                uefi_file_local = source_dir / uefi_file.lstrip('/')
                
                if uefi_file_local.exists():
                    # 使用正确的 El Torito UEFI 引导参数
                    # Windows ISO 的 UEFI 引导使用 -eltorito-alt-boot -e 参数
                    # 引导文件路径应该是相对于 ISO 根目录的路径（不带前导 /）
                    uefi_path_in_iso = uefi_file.lstrip('/')
                    
                    # 使用 -eltorito-alt-boot 创建 UEFI 引导入口
                    # 注意：-eltorito-alt-boot 会自动创建 Platform ID 0xEF (EFI) 的 section
                    # 参数顺序：-eltorito-alt-boot 后跟 -e 指定引导文件
                    # 不需要显式指定 -eltorito-platform，因为 -eltorito-alt-boot 会自动处理
                    cmd.extend([
                        "-eltorito-alt-boot",
                        "-e", uefi_path_in_iso,
                        "-no-emul-boot"
                    ])
                    
                    # 验证引导文件确实存在
                    if not uefi_file_local.exists():
                        logger.error(f"UEFI boot file not found at: {uefi_file_local}")
                    else:
                        file_size = uefi_file_local.stat().st_size
                        logger.info(f"Adding UEFI boot: {uefi_file} (path in ISO: {uefi_path_in_iso}, size: {file_size / 1024:.2f} KB)")
                else:
                    logger.warning(f"UEFI boot file not found in extracted directory: {uefi_file}")
        
        # 兼容旧格式（如果只有 boot_file，尝试识别类型）
        elif boot_info.get("has_boot") and boot_info.get("boot_file"):
            boot_file_path = boot_info["boot_file"]
            boot_file_local = source_dir / boot_file_path.lstrip('/')
            
            if boot_file_local.exists():
                boot_type = self._identify_boot_type(boot_file_path)
                if boot_type == 'bios':
                    cmd.extend([
                        "-eltorito-boot", boot_file_path.lstrip('/'),
                        "-no-emul-boot",
                        "-boot-load-size", "8",
                        "-boot-info-table"
                    ])
                    logger.info(f"Adding BIOS boot (legacy format): {boot_file_path}")
                else:
                    cmd.extend([
                        "-eltorito-alt-boot",
                        "-e", boot_file_path.lstrip('/'),
                        "-no-emul-boot"
                    ])
                    logger.info(f"Adding UEFI boot (legacy format): {boot_file_path}")
            else:
                logger.warning(f"Boot file not found in extracted directory: {boot_file_path}")
        
        # 输出文件（转换为 Cygwin 路径）
        cygwin_output = self._windows_to_cygwin_path(output_path)
        cmd.extend(["-o", cygwin_output])
        
        # 源目录（转换为 Cygwin 路径，必须是最后一个参数）
        cygwin_source = self._windows_to_cygwin_path(source_dir)
        cmd.append(cygwin_source)
        
        return cmd
    
    def _run_xorriso(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """
        执行 xorriso 命令
        
        Args:
            cmd: xorriso 命令参数列表
        
        Returns:
            subprocess.CompletedProcess 对象
        
        Raises:
            subprocess.CalledProcessError: 如果命令执行失败
        """
        logger.info(f"Running xorriso command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # 不自动抛出异常，手动处理
            )
            
            if result.returncode != 0:
                logger.error(f"xorriso failed with return code {result.returncode}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode,
                    cmd,
                    result.stdout,
                    result.stderr
                )
            
            logger.info("xorriso completed successfully")
            if result.stdout:
                logger.debug(f"xorriso stdout: {result.stdout}")
            
            return result
            
        except FileNotFoundError:
            raise FileNotFoundError(
                f"xorriso.exe not found at: {self.xorriso_exe_path}\n"
                f"Please ensure xorriso is available"
            )
        except Exception as e:
            logger.error(f"Error running xorriso: {e}")
            raise
    
    def add_file(self, local_path: str, iso_path: str) -> 'ISOWriter':
        """
        添加文件到 ISO（将在 write 时执行）
        
        Args:
            local_path: 本地文件路径
            iso_path: ISO 中的文件路径
        
        Returns:
            self（支持链式调用）
        """
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # 标准化 ISO 路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        self.add_files[iso_path] = str(local_file)
        logger.debug(f"Queued file to add: {local_path} -> {iso_path}")
        
        return self
    
    def replace_file(self, iso_path: str, local_path: str) -> 'ISOWriter':
        """
        替换 ISO 中的文件（将在 write 时执行）
        
        Args:
            iso_path: ISO 中的文件路径
            local_path: 本地文件路径
        
        Returns:
            self（支持链式调用）
        """
        # 标准化 ISO 路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        # 添加到跳过列表和添加列表
        self.skip_files.add(iso_path)
        self.add_file(local_path, iso_path)
        logger.debug(f"Queued file to replace: {local_path} -> {iso_path}")
        
        return self
    
    def remove_file(self, iso_path: str) -> 'ISOWriter':
        """
        从 ISO 中删除文件（将在 write 时执行）
        
        Args:
            iso_path: ISO 中的文件路径
        
        Returns:
            self（支持链式调用）
        """
        # 标准化 ISO 路径
        if not iso_path.startswith('/'):
            iso_path = '/' + iso_path
        
        self.skip_files.add(iso_path)
        logger.debug(f"Queued file to remove: {iso_path}")
        
        return self
    
    def write(self, output_path: str) -> dict[str, Any]:
        """
        执行所有操作并写入新 ISO（使用 xorriso）
        
        Args:
            output_path: 输出 ISO 文件路径
        
        Returns:
            包含操作结果的字典:
            - success: 是否成功
            - message: 结果消息
            - output_path: 输出文件路径
            - output_size: 输出文件大小
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from pycdlib.pycdlib import PyCdlib
        except ImportError:
            error_msg = "pycdlib not installed. Please install it with: pip install pycdlib"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "output_path": str(output_file)
            }
        
        try:
            # 1. 打开源 ISO，检测文件系统类型
            logger.info(f"Opening source ISO file: {self.source_iso_path}")
            self.source_iso = PyCdlib()
            self.source_iso.open(str(self.source_iso_path))
            
            fs_info = self._detect_iso_filesystem(self.source_iso)
            self.use_udf = fs_info["udf"]
            self.use_joliet = fs_info["joliet"]
            logger.info(f"Source ISO filesystem: UDF={self.use_udf}, Joliet={self.use_joliet}")
            
            # 2. 检测引导信息
            boot_info = self._detect_boot_info()
            
            # 3. 创建临时目录用于提取 ISO 内容
            self.temp_dir = Path(tempfile.mkdtemp(prefix="iso_writer_"))
            logger.info(f"Created temporary directory: {self.temp_dir}")
            
            # 4. 提取源 ISO 所有内容到临时目录
            logger.info("Extracting source ISO contents to temporary directory...")
            logger.info("This may take a while for large ISO files...")
            self._extract_iso_to_directory(self.temp_dir)
            
            # 5. 验证引导文件是否存在
            if boot_info.get("has_boot"):
                logger.info("Validating boot files...")
                
                # 验证 BIOS 引导文件
                if boot_info.get("bios_boot"):
                    bios_file = boot_info["bios_boot"].get("file", "")
                    bios_file_local = self.temp_dir / bios_file.lstrip('/')
                    if bios_file_local.exists():
                        file_size = bios_file_local.stat().st_size
                        logger.info(f"  [OK] BIOS boot file found: {bios_file} ({file_size / 1024:.2f} KB)")
                    else:
                        logger.warning(f"  [WARN] BIOS boot file not found: {bios_file}")
                
                # 验证 UEFI 引导文件
                if boot_info.get("uefi_boot"):
                    uefi_file = boot_info["uefi_boot"].get("file", "")
                    uefi_file_local = self.temp_dir / uefi_file.lstrip('/')
                    if uefi_file_local.exists():
                        file_size = uefi_file_local.stat().st_size
                        logger.info(f"  [OK] UEFI boot file found: {uefi_file} ({file_size / 1024:.2f} KB)")
                    else:
                        logger.warning(f"  [WARN] UEFI boot file not found: {uefi_file}")
                
                # 兼容旧格式
                elif boot_info.get("boot_file"):
                    boot_file = boot_info["boot_file"]
                    boot_file_local = self.temp_dir / boot_file.lstrip('/')
                    if boot_file_local.exists():
                        file_size = boot_file_local.stat().st_size
                        boot_type = self._identify_boot_type(boot_file)
                        logger.info(f"  [OK] {boot_type.upper()} boot file found: {boot_file} ({file_size / 1024:.2f} KB)")
                    else:
                        logger.warning(f"  [WARN] Boot file not found: {boot_file}")
            
            # 6. 在临时目录中执行文件操作（添加/替换/删除）
            logger.info("Applying file operations...")
            
            # 6.1 删除文件
            for iso_path in self.skip_files:
                if iso_path not in self.add_files:  # 如果是替换，不删除（会在下一步添加）
                    local_path = self.temp_dir / iso_path.lstrip('/')
                    if local_path.exists():
                        if local_path.is_file():
                            local_path.unlink()
                            logger.debug(f"Deleted file: {iso_path}")
                        elif local_path.is_dir():
                            shutil.rmtree(local_path)
                            logger.debug(f"Deleted directory: {iso_path}")
            
            # 6.2 添加/替换文件
            for iso_path, local_path in self.add_files.items():
                # 标准化 ISO 路径
                iso_path_normalized = iso_path.lstrip('/')
                target_path = self.temp_dir / iso_path_normalized
                
                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(local_path, target_path)
                logger.info(f"Added/replaced file: {local_path} -> {iso_path}")
            
            # 7. 使用 xorriso 创建新 ISO
            logger.info(f"Creating new ISO using xorriso: {output_file}")
            xorriso_cmd = self._build_xorriso_command(
                self.temp_dir,
                output_file,
                fs_info,
                boot_info
            )
            self._run_xorriso(xorriso_cmd)
            
            # 8. 验证输出文件
            if not output_file.exists():
                raise FileNotFoundError(f"Output ISO file was not created: {output_file}")
            
            output_size = output_file.stat().st_size
            logger.info(f"Successfully created ISO: {output_file.name} ({output_size / (1024**3):.2f} GB)")
            
            return {
                "success": True,
                "message": f"Successfully created ISO: {output_file.name}",
                "output_path": str(output_file),
                "output_size": output_size
            }
            
        except Exception as e:
            logger.error(f"Failed to write ISO: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Failed to write ISO: {str(e)}",
                "output_path": str(output_file)
            }
        finally:
            # 清理资源
            if self.source_iso:
                try:
                    self.source_iso.close()
                except:
                    pass
            
            if self.temp_dir and self.temp_dir.exists():
                try:
                    shutil.rmtree(self.temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {e}")


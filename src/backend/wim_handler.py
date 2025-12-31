"""
WIM file handling module
Supports reading, extracting, and modifying WIM files using wimlib DLL API
Uses non-mount approach (extract + update) for better compatibility
"""
import sys
import logging
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('WIMHandler')


# ==================== Constants and Structures ====================

# Error codes (from wimlib.h)
WIMLIB_ERR_SUCCESS = 0
WIMLIB_ERR_INVALID_IMAGE = 18
WIMLIB_ERR_INVALID_PARAM = 24
WIMLIB_ERR_PATH_DOES_NOT_EXIST = 49
WIMLIB_ERR_NOT_A_WIM_FILE = 43

# Special image indices
WIMLIB_NO_IMAGE = 0
WIMLIB_ALL_IMAGES = -1

# Open flags
WIMLIB_OPEN_FLAG_CHECK_INTEGRITY = 0x00000001
WIMLIB_OPEN_FLAG_WRITE_ACCESS = 0x00000004

# Extract flags
WIMLIB_EXTRACT_FLAG_NTFS = 0x00000001
WIMLIB_EXTRACT_FLAG_NO_ACLS = 0x00000040
WIMLIB_EXTRACT_FLAG_RPFIX = 0x00000100
WIMLIB_EXTRACT_FLAG_NO_ATTRIBUTES = 0x00100000

# Default extract flags for temporary operations (avoid permission issues)
# Combines NO_ACLS and NO_ATTRIBUTES to prevent permission problems when cleaning up temp directories
WIMLIB_EXTRACT_FLAG_TEMP_DEFAULT = (
    WIMLIB_EXTRACT_FLAG_NO_ACLS | 
    WIMLIB_EXTRACT_FLAG_NO_ATTRIBUTES
)

# Update flags
WIMLIB_UPDATE_FLAG_SEND_PROGRESS = 0x00000001

# Write flags
WIMLIB_WRITE_FLAG_CHECK_INTEGRITY = 0x00000001
WIMLIB_WRITE_FLAG_REBUILD = 0x00000040

# Update operation types
WIMLIB_UPDATE_OP_ADD = 0
WIMLIB_UPDATE_OP_DELETE = 1
WIMLIB_UPDATE_OP_RENAME = 2

# Add flags
WIMLIB_ADD_FLAG_NO_REPLACE = 0x00000001
WIMLIB_ADD_FLAG_VERBOSE = 0x00000002

# Delete flags
WIMLIB_DELETE_FLAG_RECURSIVE = 0x00000001
WIMLIB_DELETE_FLAG_FORCE = 0x00000002

# GUID length
WIMLIB_GUID_LEN = 16

# WIM path separator (Windows uses backslash)
WIMLIB_WIM_PATH_SEPARATOR = '\\'
WIMLIB_WIM_ROOT_PATH = '\\'


# Structure definitions
class WIMStruct(ctypes.Structure):
    """Opaque WIMStruct - we only use pointers to it"""
    pass


class WimlibWimInfo(ctypes.Structure):
    """wimlib_wim_info structure - must match C struct exactly"""
    _fields_ = [
        ("guid", ctypes.c_uint8 * WIMLIB_GUID_LEN),  # 16 bytes
        ("image_count", ctypes.c_uint32),             # 4 bytes
        ("boot_index", ctypes.c_uint32),              # 4 bytes
        ("wim_version", ctypes.c_uint32),              # 4 bytes
        ("chunk_size", ctypes.c_uint32),              # 4 bytes
        ("part_number", ctypes.c_uint16),             # 2 bytes
        ("total_parts", ctypes.c_uint16),              # 2 bytes
        ("compression_type", ctypes.c_int32),         # 4 bytes
        ("total_bytes", ctypes.c_uint64),              # 8 bytes - was missing!
        # Bit fields packed into uint32_t (32 bits total)
        # has_integrity_table : 1
        # opened_from_file : 1
        # is_readonly : 1
        # has_rpfix : 1
        # is_marked_readonly : 1
        # spanned : 1
        # write_in_progress : 1
        # metadata_only : 1
        # resource_only : 1
        # pipable : 1
        # reserved_flags : 22
        ("flags", ctypes.c_uint32),                   # 4 bytes - all bit fields packed here
        ("reserved", ctypes.c_uint32 * 9),            # 36 bytes - was wrong type/size
    ]
    
    # Helper properties to access bit fields
    @property
    def has_integrity_table(self) -> bool:
        return bool(self.flags & 0x01)
    
    @property
    def opened_from_file(self) -> bool:
        return bool(self.flags & 0x02)
    
    @property
    def is_readonly(self) -> bool:
        return bool(self.flags & 0x04)
    
    @property
    def has_rpfix(self) -> bool:
        return bool(self.flags & 0x08)
    
    @property
    def is_marked_readonly(self) -> bool:
        return bool(self.flags & 0x10)
    
    @property
    def spanned(self) -> bool:
        return bool(self.flags & 0x20)
    
    @property
    def write_in_progress(self) -> bool:
        return bool(self.flags & 0x40)
    
    @property
    def metadata_only(self) -> bool:
        return bool(self.flags & 0x80)
    
    @property
    def resource_only(self) -> bool:
        return bool(self.flags & 0x100)
    
    @property
    def pipable(self) -> bool:
        return bool(self.flags & 0x200)


class WimlibAddCommand(ctypes.Structure):
    """wimlib_add_command structure"""
    _fields_ = [
        ("fs_source_path", ctypes.POINTER(ctypes.c_wchar)),
        ("wim_target_path", ctypes.POINTER(ctypes.c_wchar)),
        ("config_file", ctypes.POINTER(ctypes.c_wchar)),
        ("add_flags", ctypes.c_int),
    ]


class WimlibDeleteCommand(ctypes.Structure):
    """wimlib_delete_command structure"""
    _fields_ = [
        ("wim_path", ctypes.POINTER(ctypes.c_wchar)),
        ("delete_flags", ctypes.c_int),
    ]


class WimlibRenameCommand(ctypes.Structure):
    """wimlib_rename_command structure"""
    _fields_ = [
        ("wim_source_path", ctypes.POINTER(ctypes.c_wchar)),
        ("wim_target_path", ctypes.POINTER(ctypes.c_wchar)),
        ("rename_flags", ctypes.c_int),
    ]


class WimlibUpdateCommand(ctypes.Union):
    """wimlib_update_command union"""
    _fields_ = [
        ("add", WimlibAddCommand),
        ("delete_", WimlibDeleteCommand),  # Underscore for C++ compatibility
        ("rename", WimlibRenameCommand),
    ]


class WimlibUpdateCommandFull(ctypes.Structure):
    """wimlib_update_command structure with operation type"""
    _fields_ = [
        ("op", ctypes.c_int),  # enum wimlib_update_op
        ("cmd", WimlibUpdateCommand),
    ]


# ==================== DLL Loading ====================

def _load_wimlib_dll() -> ctypes.CDLL:
    """
    Load wimlib DLL and define function signatures
    
    Returns:
        Loaded DLL object
        
    Raises:
        FileNotFoundError: If DLL not found
        OSError: If DLL cannot be loaded
    """
    # Find DLL path
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    dll_path = project_root / "src" / "shared" / "wimlib" / "libwim-15.dll"
    
    if not dll_path.exists():
        raise FileNotFoundError(
            f"wimlib DLL not found at: {dll_path}\n"
            f"Please ensure libwim-15.dll is available"
        )
    
    logger.debug(f"Loading wimlib DLL from: {dll_path}")
    
    try:
        dll = ctypes.CDLL(str(dll_path))
    except OSError as e:
        raise OSError(f"Failed to load wimlib DLL: {e}")
    
    # Define function signatures (cdecl calling convention on Windows)
    # wimlib_global_init
    dll.wimlib_global_init.argtypes = [ctypes.c_int]
    dll.wimlib_global_init.restype = ctypes.c_int
    
    # wimlib_global_cleanup
    dll.wimlib_global_cleanup.argtypes = []
    dll.wimlib_global_cleanup.restype = None
    
    # wimlib_open_wim
    dll.wimlib_open_wim.argtypes = [
        ctypes.POINTER(ctypes.c_wchar),  # wim_file (wimlib_tchar*)
        ctypes.c_int,                     # open_flags
        ctypes.POINTER(ctypes.POINTER(WIMStruct))  # wim_ret (WIMStruct**)
    ]
    dll.wimlib_open_wim.restype = ctypes.c_int
    
    # wimlib_free
    dll.wimlib_free.argtypes = [ctypes.POINTER(WIMStruct)]
    dll.wimlib_free.restype = None
    
    # wimlib_get_wim_info
    dll.wimlib_get_wim_info.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.POINTER(WimlibWimInfo)
    ]
    dll.wimlib_get_wim_info.restype = ctypes.c_int
    
    # wimlib_get_image_property
    dll.wimlib_get_image_property.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int,  # image (1-based)
        ctypes.POINTER(ctypes.c_wchar)  # property_name
    ]
    dll.wimlib_get_image_property.restype = ctypes.POINTER(ctypes.c_wchar)
    
    # wimlib_get_image_name
    dll.wimlib_get_image_name.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int  # image (1-based)
    ]
    dll.wimlib_get_image_name.restype = ctypes.POINTER(ctypes.c_wchar)
    
    # wimlib_get_image_description
    dll.wimlib_get_image_description.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int  # image (1-based)
    ]
    dll.wimlib_get_image_description.restype = ctypes.POINTER(ctypes.c_wchar)
    
    # wimlib_extract_image
    dll.wimlib_extract_image.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int,  # image (1-based)
        ctypes.POINTER(ctypes.c_wchar),  # target directory
        ctypes.c_int  # extract_flags
    ]
    dll.wimlib_extract_image.restype = ctypes.c_int
    
    # wimlib_extract_paths
    dll.wimlib_extract_paths.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int,  # image (1-based)
        ctypes.POINTER(ctypes.c_wchar),  # target directory
        ctypes.POINTER(ctypes.POINTER(ctypes.c_wchar)),  # paths array
        ctypes.c_size_t,  # num_paths
        ctypes.c_int  # extract_flags
    ]
    dll.wimlib_extract_paths.restype = ctypes.c_int
    
    # wimlib_update_image
    dll.wimlib_update_image.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int,  # image (1-based)
        ctypes.POINTER(WimlibUpdateCommandFull),  # cmds array
        ctypes.c_size_t,  # num_cmds
        ctypes.c_int  # update_flags
    ]
    dll.wimlib_update_image.restype = ctypes.c_int
    
    # wimlib_write
    dll.wimlib_write.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.POINTER(ctypes.c_wchar),  # path
        ctypes.c_int,  # image (WIMLIB_ALL_IMAGES or specific index)
        ctypes.c_int,  # write_flags
        ctypes.c_uint  # num_threads
    ]
    dll.wimlib_write.restype = ctypes.c_int
    
    # wimlib_overwrite
    dll.wimlib_overwrite.argtypes = [
        ctypes.POINTER(WIMStruct),
        ctypes.c_int,  # write_flags
        ctypes.c_uint  # num_threads
    ]
    dll.wimlib_overwrite.restype = ctypes.c_int
    
    # wimlib_get_error_string
    dll.wimlib_get_error_string.argtypes = [ctypes.c_int]
    dll.wimlib_get_error_string.restype = ctypes.POINTER(ctypes.c_wchar)
    
    # Initialize wimlib
    init_result = dll.wimlib_global_init(0)
    if init_result != WIMLIB_ERR_SUCCESS:
        logger.warning(f"wimlib_global_init returned error code: {init_result}")
    
    return dll


# Global DLL instance (loaded on first use)
_wimlib_dll: Optional[ctypes.CDLL] = None


def _get_wimlib_dll() -> ctypes.CDLL:
    """Get or load wimlib DLL (singleton)"""
    global _wimlib_dll
    if _wimlib_dll is None:
        _wimlib_dll = _load_wimlib_dll()
    return _wimlib_dll


# ==================== Error Handling ====================

class WIMError(Exception):
    """Base exception for WIM operations"""
    pass


class WIMFileError(WIMError):
    """Error related to WIM file operations"""
    pass


def _check_error(result: int, operation: str = "WIM operation") -> None:
    """
    Check wimlib function return value and raise exception if error
    
    Args:
        result: Return value from wimlib function (0 = success)
        operation: Description of the operation for error message
        
    Raises:
        WIMFileError: If result indicates an error
    """
    if result != WIMLIB_ERR_SUCCESS:
        dll = _get_wimlib_dll()
        error_str_ptr = dll.wimlib_get_error_string(result)
        if error_str_ptr:
            error_str = ctypes.wstring_at(error_str_ptr)
        else:
            error_str = f"Unknown error code: {result}"
        
        raise WIMFileError(f"{operation} failed: {error_str} (code: {result})")


# ==================== WIMHandler Class ====================

class WIMHandler:
    """Handler for WIM file operations using wimlib DLL"""
    
    def __init__(self, wim_path: str, write_access: bool = False):
        """
        Initialize WIM handler
        
        Args:
            wim_path: Path to WIM file
            write_access: Whether to open with write access
            
        Raises:
            FileNotFoundError: If WIM file not found
            WIMFileError: If WIM file cannot be opened
        """
        self.wim_path = Path(wim_path)
        if not self.wim_path.exists():
            raise FileNotFoundError(f"WIM file not found: {wim_path}")
        
        self.write_access = write_access
        self._wim_ptr: Optional[Any] = None  # ctypes.POINTER(WIMStruct)
        self._dll = _get_wimlib_dll()
        
        # Open WIM file
        self._open_wim()
    
    def _open_wim(self) -> None:
        """Open WIM file"""
        open_flags = 0
        if self.write_access:
            open_flags |= WIMLIB_OPEN_FLAG_WRITE_ACCESS
        
        # Create a pointer variable to store the WIMStruct pointer
        # wimlib_open_wim expects WIMStruct** (pointer to pointer)
        wim_ptr_ptr = (ctypes.POINTER(WIMStruct) * 1)()  # Array of 1 pointer
        
        # Convert path to wchar_t*
        wim_path_wstr = str(self.wim_path.resolve())
        wim_path_ptr = ctypes.c_wchar_p(wim_path_wstr)
        
        result = self._dll.wimlib_open_wim(
            wim_path_ptr,
            open_flags,
            ctypes.cast(wim_ptr_ptr, ctypes.POINTER(ctypes.POINTER(WIMStruct)))
        )
        
        if result != WIMLIB_ERR_SUCCESS:
            _check_error(result, f"Opening WIM file: {self.wim_path}")
        
        # Store the pointer
        self._wim_ptr = wim_ptr_ptr[0]
        
        logger.info(f"Opened WIM file: {self.wim_path}")
    
    def get_image_count(self) -> int:
        """
        Get the number of images in the WIM file
        
        Returns:
            Number of images (1-based indexing)
        """
        info = WimlibWimInfo()
        result = self._dll.wimlib_get_wim_info(self._wim_ptr, ctypes.byref(info))
        _check_error(result, "Getting WIM info")
        return info.image_count
    
    def get_image_property(self, image: int, property_name: str) -> Optional[str]:
        """
        Get a property of a specific image
        
        Args:
            image: 1-based image index
            property_name: Property name (e.g., "NAME", "DESCRIPTION", "WINDOWS/VERSION/BUILD")
        
        Returns:
            Property value as string, or None if not found
        """
        property_name_ptr = ctypes.c_wchar_p(property_name)
        result_ptr = self._dll.wimlib_get_image_property(
            self._wim_ptr,
            image,
            property_name_ptr
        )
        
        if result_ptr:
            return ctypes.wstring_at(result_ptr)
        return None
    
    def get_image_name(self, image: int) -> str:
        """
        Get the name of a specific image
        
        Args:
            image: 1-based image index
        
        Returns:
            Image name, or empty string if unnamed
        """
        result_ptr = self._dll.wimlib_get_image_name(self._wim_ptr, image)
        if result_ptr:
            return ctypes.wstring_at(result_ptr)
        return ""
    
    def get_image_description(self, image: int) -> Optional[str]:
        """
        Get the description of a specific image
        
        Args:
            image: 1-based image index
        
        Returns:
            Image description, or None if not found
        """
        result_ptr = self._dll.wimlib_get_image_description(self._wim_ptr, image)
        if result_ptr:
            return ctypes.wstring_at(result_ptr)
        return None
    
    def extract_image(self, image: int, target_dir: str, extract_flags: Optional[int] = None) -> None:
        """
        Extract an image from the WIM to a directory (non-mount approach)
        
        Args:
            image: 1-based image index, or WIMLIB_ALL_IMAGES to extract all
            target_dir: Target directory path
            extract_flags: Extract flags (bitwise OR of WIMLIB_EXTRACT_FLAG_*).
                          If None, uses WIMLIB_EXTRACT_FLAG_TEMP_DEFAULT to avoid
                          permission issues when cleaning up temporary directories.
        
        Raises:
            WIMFileError: If extraction fails
        """
        logger.info(f"extract_image: Starting extraction of image {image} to {target_dir}")
        
        # Use default flags (NO_ACLS | NO_ATTRIBUTES) if not specified
        # This prevents permission issues when cleaning up temporary directories
        if extract_flags is None:
            extract_flags = WIMLIB_EXTRACT_FLAG_TEMP_DEFAULT
        
        target_dir_path = Path(target_dir)
        target_dir_path.mkdir(parents=True, exist_ok=True)
        
        target_dir_wstr = str(target_dir_path.resolve())
        target_dir_ptr = ctypes.c_wchar_p(target_dir_wstr)
        logger.info(f"extract_image: Target directory: {target_dir_wstr}, flags: {extract_flags}")
        
        logger.info(f"extract_image: Calling wimlib_extract_image")
        try:
            result = self._dll.wimlib_extract_image(
                self._wim_ptr,
                image,
                target_dir_ptr,
                extract_flags
            )
            logger.info(f"extract_image: wimlib_extract_image returned: {result}")
        except Exception as e:
            logger.error(f"extract_image: Exception during DLL call: {e}", exc_info=True)
            raise
        
        _check_error(result, f"Extracting image {image} to {target_dir}")
        logger.info(f"Extracted image {image} to {target_dir}")
    
    def extract_paths(self, image: int, target_dir: str, paths: list[str], extract_flags: Optional[int] = None) -> None:
        """
        Extract specific paths from an image
        
        Args:
            image: 1-based image index
            target_dir: Target directory path
            paths: List of paths to extract (WIM paths, e.g., "\\Windows\\System32")
            extract_flags: Extract flags. If None, uses WIMLIB_EXTRACT_FLAG_TEMP_DEFAULT
                          to avoid permission issues when cleaning up temporary directories.
        
        Raises:
            WIMFileError: If extraction fails
        """
        logger.info(f"extract_paths: Starting extraction of {len(paths)} path(s) from image {image}")
        
        # Use default flags (NO_ACLS | NO_ATTRIBUTES) if not specified
        # This prevents permission issues when cleaning up temporary directories
        if extract_flags is None:
            extract_flags = WIMLIB_EXTRACT_FLAG_TEMP_DEFAULT
        
        target_dir_path = Path(target_dir)
        target_dir_path.mkdir(parents=True, exist_ok=True)
        
        target_dir_wstr = str(target_dir_path.resolve())
        target_dir_ptr = ctypes.c_wchar_p(target_dir_wstr)
        logger.info(f"extract_paths: Target directory: {target_dir_wstr}")
        
        # Convert paths to wchar_t* array
        # Store normalized paths to keep them alive during the function call
        normalized_paths = []
        for path in paths:
            # Normalize path (use backslash on Windows)
            normalized_path = path.replace('/', '\\')
            if not normalized_path.startswith('\\'):
                normalized_path = '\\' + normalized_path
            normalized_paths.append(normalized_path)
            logger.info(f"extract_paths: Normalized path: {normalized_path}")
        
        # Create array of c_wchar_p pointers (const wimlib_tchar * const *paths)
        # Each element is a pointer to a wchar_t string
        # Store the array reference to keep it alive
        path_ptrs = (ctypes.c_wchar_p * len(normalized_paths))()
        for i, path_str in enumerate(normalized_paths):
            path_ptrs[i] = path_str
        
        # Cast to the expected type: POINTER(POINTER(c_wchar))
        # wimlib expects: const wimlib_tchar * const *paths
        # This is a pointer to an array of pointers
        paths_array = ctypes.cast(path_ptrs, ctypes.POINTER(ctypes.POINTER(ctypes.c_wchar)))
        
        logger.info(f"extract_paths: Calling wimlib_extract_paths with {len(paths)} path(s)")
        try:
            result = self._dll.wimlib_extract_paths(
                self._wim_ptr,
                image,
                target_dir_ptr,
                paths_array,
                len(paths),
                extract_flags
            )
            logger.info(f"extract_paths: wimlib_extract_paths returned: {result}")
        except Exception as e:
            logger.error(f"extract_paths: Exception during DLL call: {e}", exc_info=True)
            raise
        
        _check_error(result, f"Extracting paths from image {image}")
        logger.info(f"Extracted {len(paths)} path(s) from image {image} to {target_dir}")
    
    def update_image(
        self,
        image: int,
        add_files: Optional[list[tuple[str, str]]] = None,
        delete_paths: Optional[list[str]] = None,
        rename_paths: Optional[list[tuple[str, str]]] = None,
        update_flags: int = 0
    ) -> None:
        """
        Update an image by adding, deleting, or renaming files/directories
        
        Args:
            image: 1-based image index
            add_files: List of (source_path, wim_target_path) tuples to add
            delete_paths: List of WIM paths to delete
            rename_paths: List of (source_path, target_path) tuples to rename
            update_flags: Update flags (bitwise OR of WIMLIB_UPDATE_FLAG_*)
        
        Raises:
            WIMFileError: If update fails
        """
        if not self.write_access:
            raise WIMFileError("WIM file was opened without write access")
        
        # Build update commands
        commands = []
        
        # Add files
        if add_files:
            for fs_source_path, wim_target_path in add_files:
                cmd = WimlibUpdateCommandFull()
                cmd.op = WIMLIB_UPDATE_OP_ADD
                
                # Normalize WIM target path
                wim_target = wim_target_path.replace('/', '\\')
                if not wim_target.startswith('\\'):
                    wim_target = '\\' + wim_target
                
                # Allocate memory for strings (they need to persist)
                # Convert to POINTER(c_wchar) as expected by the structure
                fs_source_ptr = ctypes.cast(ctypes.c_wchar_p(fs_source_path), ctypes.POINTER(ctypes.c_wchar))
                wim_target_ptr = ctypes.cast(ctypes.c_wchar_p(wim_target), ctypes.POINTER(ctypes.c_wchar))
                
                cmd.cmd.add.fs_source_path = fs_source_ptr
                cmd.cmd.add.wim_target_path = wim_target_ptr
                cmd.cmd.add.config_file = None
                cmd.cmd.add.add_flags = 0  # Default flags
                
                commands.append(cmd)
        
        # Delete paths
        if delete_paths:
            for wim_path in delete_paths:
                cmd = WimlibUpdateCommandFull()
                cmd.op = WIMLIB_UPDATE_OP_DELETE
                
                # Normalize WIM path
                wim_path_normalized = wim_path.replace('/', '\\')
                if not wim_path_normalized.startswith('\\'):
                    wim_path_normalized = '\\' + wim_path_normalized
                
                wim_path_ptr = ctypes.cast(ctypes.c_wchar_p(wim_path_normalized), ctypes.POINTER(ctypes.c_wchar))
                cmd.cmd.delete_.wim_path = wim_path_ptr
                cmd.cmd.delete_.delete_flags = WIMLIB_DELETE_FLAG_RECURSIVE
                
                commands.append(cmd)
        
        # Rename paths
        if rename_paths:
            for source_path, target_path in rename_paths:
                cmd = WimlibUpdateCommandFull()
                cmd.op = WIMLIB_UPDATE_OP_RENAME
                
                # Normalize paths
                source_normalized = source_path.replace('/', '\\')
                if not source_normalized.startswith('\\'):
                    source_normalized = '\\' + source_normalized
                
                target_normalized = target_path.replace('/', '\\')
                if not target_normalized.startswith('\\'):
                    target_normalized = '\\' + target_normalized
                
                source_ptr = ctypes.cast(ctypes.c_wchar_p(source_normalized), ctypes.POINTER(ctypes.c_wchar))
                target_ptr = ctypes.cast(ctypes.c_wchar_p(target_normalized), ctypes.POINTER(ctypes.c_wchar))
                
                cmd.cmd.rename.wim_source_path = source_ptr
                cmd.cmd.rename.wim_target_path = target_ptr
                cmd.cmd.rename.rename_flags = 0
                
                commands.append(cmd)
        
        if not commands:
            logger.warning("No update commands provided")
            return
        
        # Create array of commands
        commands_array = (WimlibUpdateCommandFull * len(commands))(*commands)
        
        result = self._dll.wimlib_update_image(
            self._wim_ptr,
            image,
            commands_array,
            len(commands),
            update_flags
        )
        
        _check_error(result, f"Updating image {image}")
        logger.info(f"Updated image {image}: {len(commands)} command(s)")
    
    def write_wim(self, output_path: str, image: int = WIMLIB_ALL_IMAGES, write_flags: int = 0, num_threads: int = 0) -> None:
        """
        Write WIM to a new file
        
        Args:
            output_path: Output WIM file path
            image: Image index to write (default: all images)
            write_flags: Write flags (bitwise OR of WIMLIB_WRITE_FLAG_*)
            num_threads: Number of threads for compression (0 = auto)
        
        Raises:
            WIMFileError: If write fails
        """
        output_path_wstr = str(Path(output_path).resolve())
        output_path_ptr = ctypes.c_wchar_p(output_path_wstr)
        
        result = self._dll.wimlib_write(
            self._wim_ptr,
            output_path_ptr,
            image,
            write_flags,
            num_threads
        )
        
        _check_error(result, f"Writing WIM to {output_path}")
        logger.info(f"Wrote WIM to {output_path}")
    
    def overwrite_wim(self, write_flags: int = 0, num_threads: int = 0) -> None:
        """
        Overwrite the original WIM file with modifications
        
        Args:
            write_flags: Write flags (bitwise OR of WIMLIB_WRITE_FLAG_*)
            num_threads: Number of threads for compression (0 = auto)
        
        Raises:
            WIMFileError: If overwrite fails
        """
        if not self.write_access:
            raise WIMFileError("WIM file was opened without write access")
        
        result = self._dll.wimlib_overwrite(
            self._wim_ptr,
            write_flags,
            num_threads
        )
        
        _check_error(result, f"Overwriting WIM file: {self.wim_path}")
        logger.info(f"Overwrote WIM file: {self.wim_path}")
    
    def close(self) -> None:
        """Close WIM file and free resources"""
        if self._wim_ptr:
            self._dll.wimlib_free(self._wim_ptr)
            self._wim_ptr = None
            logger.debug(f"Closed WIM file: {self.wim_path}")
    
    def __enter__(self) -> 'WIMHandler':
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
        return None

"""
Backend main entry - IPC server
Communicates with Electron frontend via stdin/stdout
"""
import json
import os
import io
import sys
import traceback
import logging
import inspect
import shutil
import threading
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from iso_handler import ISOHandler
from downloader import Downloader

# 设置 stdout 和 stdin 编码为 UTF-8，避免 Windows 上的 GBK 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    # 确保 stdin 也使用 UTF-8 编码
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    # 如果 reconfigure 不可用，尝试设置环境变量
    if 'PYTHONIOENCODING' not in os.environ:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('Backend')


class TaskManager:
    """通用异步任务管理器"""

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock: threading.Lock = threading.Lock()

    def create_task(self, name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """创建后台任务并立即返回 task_id"""
        task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "name": name,
                "status": "pending",
                "result": None,
                "error": None,
                "progress": None,
                "created_at": time.time(),
                "updated_at": time.time(),
            }

        def _runner():
            with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    return
                task["status"] = "running"
                task["updated_at"] = time.time()

            try:
                func_kwargs = dict(kwargs)
                try:
                    signature = inspect.signature(func)
                    if "task_updater" in signature.parameters:
                        func_kwargs["task_updater"] = lambda **updates: self.update_task(task_id, **updates)
                except (TypeError, ValueError):
                    pass

                result = func(*args, **func_kwargs)
                with self._lock:
                    task = self._tasks.get(task_id)
                    if not task:
                        return
                    task["status"] = "completed"
                    task["result"] = result
                    task["updated_at"] = time.time()
            except Exception as e:
                logger.error(f"Task {name} failed: {e}")
                logger.debug("Task error traceback:\n%s", traceback.format_exc())
                with self._lock:
                    task = self._tasks.get(task_id)
                    if not task:
                        return
                    task["status"] = "failed"
                    task["error"] = str(e)
                    task["updated_at"] = time.time()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        return task_id

    def update_task(self, task_id: str, **updates: Any) -> None:
        """更新任务状态附加信息"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            for key, value in updates.items():
                task[key] = value
            task["updated_at"] = time.time()

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """查询任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return {"status": "not_found"}
            # 返回浅拷贝，避免外部修改内部结构
            return {
                "id": task["id"],
                "name": task["name"],
                "status": task["status"],
                "result": task.get("result"),
                "error": task.get("error"),
                "progress": task.get("progress"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
            }


class IPCError(Exception):
    """IPC通信错误"""
    pass


class BackendServer:
    """后端服务器，处理来自前端的IPC请求"""
    
    # iso_handler: "ISOHandler | None"
    # downloader: "Downloader | None"
    # download_tasks: dict[str, dict[str, Any]]
    # project_root: Path
    
    def __init__(self):
        self.running: bool = True
        self.handlers: dict[str, Callable[..., Any]] = {}
        self.task_manager: TaskManager = TaskManager()
        # 这些属性在run()方法中初始化
        self.iso_handler = None
        self.downloader = None
        self.download_tasks = {}
        self.project_root = Path(__file__).parent.parent.parent
        self.unattend_generator = None
    
    def register_handler(self, method: str, handler: Callable[..., Any]) -> None:
        """注册请求处理器"""
        self.handlers[method] = handler
    
    def send_response(self, request_id: str | None, result: Any = None, error: str | None = None) -> None:
        """发送响应到前端"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error:
            response["error"] = {
                "code": -1,
                "message": error
            }
        else:
            if result is not None:
                response["result"] = result
        
        try:
            json_str = json.dumps(response, ensure_ascii=False)
            # 确保输出使用 UTF-8 编码
            try:
                print(json_str, flush=True)  # Keep print for IPC communication
            except UnicodeEncodeError:
                # 如果 stdout 编码不是 UTF-8，尝试使用 UTF-8 编码输出
                import sys
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout.buffer.write(json_str.encode('utf-8'))
                    sys.stdout.buffer.write(b'\n')
                    sys.stdout.buffer.flush()
                else:
                    # 最后的后备方案：使用 ASCII 编码
                    json_str_ascii = json.dumps(response, ensure_ascii=True)
                    print(json_str_ascii, flush=True)
        except Exception as e:
            # If response serialization fails, try to send error information
            logger.error(f"Response serialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32700,
                    "message": f"Response serialization failed: {str(e)}"
                }
            }
            try:
                json_str = json.dumps(error_response, ensure_ascii=False)
                print(json_str, flush=True)
            except UnicodeEncodeError:
                # 使用 ASCII 编码作为后备
                json_str = json.dumps(error_response, ensure_ascii=True)
                print(json_str, flush=True)
    
    def handle_request(self, request: dict[str, Any]) -> None:
        """处理单个请求"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not request_id:
            self.send_response("", error="Missing request ID")
            return
        
        if not method:
            self.send_response(request_id, error="Missing method name")
            return
        
        # Find handler
        handler = self.handlers.get(method)
        if not handler:
            logger.warning(f"Unknown method: {method}")
            self.send_response(request_id, error=f"Unknown method: {method}")
            return
        
        # Execute handler
        try:
            # 确保 params 是字典类型
            if not isinstance(params, dict):
                logger.error(f"Invalid params type for method {method}: {type(params)}, value: {params}")
                # 如果 params 是字符串，尝试解析为 JSON
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        self.send_response(request_id, error=f"params must be a dict or valid JSON string")
                        return
                else:
                    self.send_response(request_id, error=f"params must be a dict, got {type(params)}")
                    return
            
            result = handler(params)
            self.send_response(request_id, result=result)
        except Exception as e:
            logger.error(f"Handler execution failed for {method}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            error_msg = f"{method} execution failed: {str(e)}"
            self.send_response(request_id, error=error_msg)
    
    def run(self):
        """运行服务器主循环"""
        # 注册基础处理器
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_platform", self._handle_get_platform)
        
        # 注册ISO镜像相关处理器
        try:
            # # 添加当前目录到Python路径，以便导入同目录下的模块
            backend_dir = Path(__file__).parent
            # if str(backend_dir) not in sys.path:
            #     sys.path.insert(0, str(backend_dir))
            
            # from .iso_handler import ISOHandler
            # from .downloader import Downloader
            
            # 计算项目根目录（main.py 在 src/backend/，所以需要向上两级）
            project_root = backend_dir.parent.parent
            cache_dir = project_root / "data" / "isos"
            
            self.iso_handler: ISOHandler = ISOHandler(cache_dir=str(cache_dir))
            self.downloader: Downloader = Downloader()
            self.download_tasks: dict[str, dict[str, Any]] = {}  # 存储下载任务
            self.project_root: Path = project_root
            
            self.register_handler("iso_list_sources", self._handle_iso_list_sources)
            self.register_handler("iso_list_versions", self._handle_iso_list_versions)
            self.register_handler("iso_list_images_start", self._handle_iso_list_images_start)
            self.register_handler("iso_list_images_status", self._handle_iso_list_images_status)
            self.register_handler("iso_fetch_download_url_start", self._handle_iso_fetch_download_url_start)
            self.register_handler("iso_fetch_download_url_status", self._handle_iso_fetch_download_url_status)
            self.register_handler("iso_test_mirror", self._handle_iso_test_mirror)
            self.register_handler("iso_test_mirror_start", self._handle_iso_test_mirror_start)
            self.register_handler("iso_test_mirror_status", self._handle_iso_test_mirror_status)
            self.register_handler("iso_start_test_mirror", self._handle_iso_start_test_mirror)
            self.register_handler("iso_get_test_status", self._handle_iso_get_test_status)
            self.register_handler("iso_cancel_test", self._handle_iso_cancel_test)
            self.register_handler("iso_download", self._handle_iso_download)
            self.register_handler("iso_download_progress", self._handle_iso_download_progress)
            self.register_handler("iso_cancel_download", self._handle_iso_cancel_download)
            self.register_handler("iso_verify", self._handle_iso_verify)
            self.register_handler("iso_verify_start", self._handle_iso_verify_start)
            self.register_handler("iso_verify_status", self._handle_iso_verify_status)
            self.register_handler("iso_delete", self._handle_iso_delete)
            self.register_handler("iso_import", self._handle_iso_import)
            self.register_handler("iso_import_start", self._handle_iso_import_start)
            self.register_handler("iso_import_status", self._handle_iso_import_status)
            self.register_handler("iso_redownload", self._handle_iso_redownload)
            self.register_handler("iso_identify", self._handle_iso_identify)
            self.register_handler("iso_identify_start", self._handle_iso_identify_start)
            self.register_handler("iso_identify_status", self._handle_iso_identify_status)
        except ImportError as e:
            logger.error(f"Failed to import ISO handler: {e}")
        
        # 注册 Unattend 配置相关处理器
        try:
            from unattend_generator import UnattendGenerator, Configuration
            # 数据目录位于项目根 data/unattend，相对于 src/backend/main.py 需要上溯两级到项目根
            data_dir = Path(__file__).parent.parent.parent / "data" / "unattend"
            self.unattend_generator = UnattendGenerator(data_dir=data_dir)
            
            self.register_handler("unattend_export_xml", self._handle_unattend_export_xml)
            self.register_handler("unattend_import_xml", self._handle_unattend_import_xml)
            self.register_handler("unattend_get_data", self._handle_unattend_get_data)
            
            # Phase 2 & 3: ISO Customize and Burn handlers
            self.register_handler("iso_customize_start", self._handle_iso_customize_start)
            self.register_handler("iso_customize_status", self._handle_iso_customize_status)
            self.register_handler("deployment_list_wim_images", self._handle_deployment_list_wim_images)
            self.register_handler("deployment_build_start", self._handle_deployment_build_start)
            self.register_handler("deployment_build_status", self._handle_deployment_build_status)
            self.register_handler("burn_list_devices", self._handle_burn_list_devices)
            self.register_handler("burn_start", self._handle_burn_start)
            self.register_handler("burn_status", self._handle_burn_status)
        except ImportError as e:
            logger.error(f"Failed to import Unattend generator: {e}")
            self.unattend_generator = None
        
        # 读取stdin并处理请求
        # 将 stdin 包装为 UTF-8 文本流
        stdin_text = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
        
        for line in stdin_text:
            if not self.running:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                self.handle_request(request)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                self.send_response("", error=f"JSON parsing failed: {str(e)}")
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
                self.send_response("", error=f"Request processing failed: {str(e)}")
    
    def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """处理ping请求"""
        return {"status": "ok", "message": "pong"}
    
    def _handle_get_platform(self, params: dict[str, Any]) -> dict[str, Any]:
        """获取平台信息"""
        import platform
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine()
        }
    
    def _handle_iso_list_sources(self, params: dict[str, Any]) -> list[str]:
        """获取镜像源列表"""
        return self.iso_handler.list_sources()
    
    def _handle_iso_list_versions(self, params: dict[str, Any]) -> dict[str, list[str]]:
        """获取可用版本列表（从配置文件读取）"""
        os_type = params.get("os_type")
        return self.iso_handler.list_available_versions(os_type)
    
    def _handle_iso_list_images_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步获取镜像列表：启动任务（仅支持local源）"""
        source = params.get("source", "local")
        filter_options = params.get("filter", {})
        
        # 只支持local源
        if source != "local":
            raise ValueError("iso_list_images_start only supports 'local' source. Use iso_fetch_download_url_start for remote sources.")
        
        task_id = self.task_manager.create_task(
            "iso_list_images",
            self.iso_handler.list_images,
            source,
            filter_options,
        )
        return {"task_id": task_id}

    def _handle_iso_list_images_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步获取镜像列表：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_fetch_download_url_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步获取下载URL：启动任务"""
        source = params.get("source")
        config = {
            "os": params.get("os"),
            "version": params.get("version"),
            "language": params.get("language"),
            "arch": params.get("arch")
        }
        
        if not source:
            raise ValueError("Missing source parameter")
        
        task_id = self.task_manager.create_task(
            "iso_fetch_download_url",
            self.iso_handler.fetch_download_url,
            source,
            config,
        )
        return {"task_id": task_id}
    
    def _handle_iso_fetch_download_url_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步获取下载URL：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_test_mirror(self, params: dict[str, Any]) -> dict[str, float]:
        """测试镜像站网络（同步版本，保持向后兼容）"""
        source = params.get("source", "msdl")
        test_url = params.get("url")
        return self.iso_handler.test_mirror(source, test_url)

    def _handle_iso_test_mirror_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步测试镜像站网络：启动任务"""
        source = params.get("source", "msdl")
        test_url = params.get("url")
        task_id = self.task_manager.create_task(
            "iso_test_mirror",
            self.iso_handler.test_mirror,
            source,
            test_url,
        )
        return {"task_id": task_id}

    def _handle_iso_test_mirror_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步测试镜像站网络：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_start_test_mirror(self, params: dict[str, Any]) -> dict[str, str]:
        """开始测试镜像站网络（异步）"""
        source = params.get("source", "microsoft")
        test_url = params.get("url")
        task_id = self.iso_handler.start_test_mirror(source, test_url)
        return {"task_id": task_id}
    
    def _handle_iso_get_test_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """获取测试任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.iso_handler.get_test_status(task_id)
    
    def _handle_iso_cancel_test(self, params: dict[str, Any]) -> dict[str, bool]:
        """中止测试任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        success = self.iso_handler.cancel_test(task_id)
        return {"success": success}
    
    def _handle_iso_download(self, params: dict[str, Any]) -> dict[str, str]:
        """下载镜像 - 支持配置参数或直接URL"""
        # 检查是配置参数还是直接URL
        source = params.get("source")
        config = params.get("config")
        url = params.get("url")
        url_type = params.get("url_type", "http")
        output_path = params.get("output_path")
        
        if not output_path:
            raise ValueError("Missing output_path parameter")
        
        # 标准化输出路径（相对路径默认以项目根目录为基准）
        if not os.path.isabs(output_path):
            base_dir = getattr(self, "project_root", Path(__file__).parent.parent)
            output_path = os.path.abspath(os.path.join(str(base_dir), output_path))
        
        # 如果提供了配置参数，先创建URL获取任务
        if source and config:
            # 创建URL获取任务
            url_task_id = self.task_manager.create_task(
                "iso_fetch_download_url",
                self.iso_handler.fetch_download_url,
                source,
                config,
            )
            
            # 创建下载任务，初始状态为fetching
            download_task_id = str(uuid.uuid4())
            self.download_tasks[download_task_id] = {
                "url_task_id": url_task_id,
                "output_path": output_path,
                "status": "fetching",
                "source": source,
                "config": config
            }
            
            # 在后台线程中等待URL获取完成，然后开始下载
            def start_download_after_url():
                try:
                    # 轮询URL获取任务状态
                    while True:
                        # 检查任务是否被取消
                        task_info = self.download_tasks.get(download_task_id)
                        if task_info and task_info.get("status") == "cancelled":
                            # 用户取消了，停止URL获取，不启动curl
                            logger.info(f"Download task {download_task_id} was cancelled during URL fetching")
                            break
                        
                        url_status = self.task_manager.get_task_status(url_task_id)
                        if url_status.get("status") == "completed":
                            url_result = url_status.get("result")
                            if url_result:
                                # 获取到URL，开始下载
                                actual_url = url_result.get("url")
                                actual_url_type = url_result.get("url_type", "http")
                                source_type = url_result.get("source_type", "ce")
                                
                                # 检查任务是否被取消（可能在URL获取完成后、启动curl前被取消）
                                if task_info and task_info.get("status") == "cancelled":
                                    # 用户取消了，不启动curl
                                    logger.info(f"Download task {download_task_id} was cancelled before starting download")
                                    break
                                
                                # 开始下载（下载器会返回自己的task_id）
                                if actual_url_type == "magnet":
                                    actual_task_id = self.downloader.download_bt(actual_url, output_path)
                                else:
                                    actual_task_id = self.downloader.download_with_curl(actual_url, output_path)
                                
                                # 立即保存downloader_task_id，防止竞态条件
                                self.download_tasks[download_task_id]["downloader_task_id"] = actual_task_id
                                
                                # 将下载器返回的task_id信息合并到download_tasks中
                                if actual_task_id in self.downloader.download_tasks:
                                    downloader_task = self.downloader.download_tasks[actual_task_id]
                                    self.download_tasks[download_task_id].update({
                                        "url": actual_url,
                                        "url_type": actual_url_type,
                                        "source_type": source_type,
                                        "status": downloader_task.get("status", "downloading"),
                                        "progress": downloader_task.get("progress", 0),
                                        "downloaded": downloader_task.get("downloaded", 0),
                                        "total": downloader_task.get("total", 0),
                                        "speed": downloader_task.get("speed", 0)
                                    })
                            break
                        elif url_status.get("status") == "failed":
                            # URL获取失败
                            error = url_status.get("error", "Failed to fetch download URL")
                            self.download_tasks[download_task_id].update({
                                "status": "failed",
                                "error": error
                            })
                            break
                        time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in start_download_after_url: {e}")
                    self.download_tasks[download_task_id].update({
                        "status": "failed",
                        "error": str(e)
                    })
            
            # 在后台线程中执行
            import threading
            thread = threading.Thread(target=start_download_after_url, daemon=True)
            thread.start()
            
            return {"task_id": download_task_id, "status": "fetching"}
        
        # 如果提供了直接URL，使用原有逻辑
        elif url:
            # 根据 URL 判断来源类型（用于后续文件重命名）
            source_type = "ce"  # 默认 Consumer Editions
            if "microsoft.com" in url or "dl.delivery.mp.microsoft.com" in url:
                source_type = "me"  # Multi Editions
            
            # 立即创建任务并返回task_id
            if url_type == "magnet":
                task_id = self.downloader.download_bt(url, output_path)
            else:
                task_id = self.downloader.download_with_curl(url, output_path)
            
            # 存储任务信息（包括来源类型，用于下载完成后重命名）
            self.download_tasks[task_id] = {
                "url": url,
                "output_path": output_path,
                "url_type": url_type,
                "source_type": source_type
            }
            
            return {"task_id": task_id, "status": "started"}
        else:
            raise ValueError("Must provide either (source+config) or url parameter")
    
    def _handle_iso_download_progress(self, params: dict[str, Any]) -> dict[str, Any]:
        """查询下载进度"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        
        # 检查是否是配置参数创建的下载任务
        if task_id in self.download_tasks:
            task_info = self.download_tasks[task_id]
            task_status = task_info.get("status", "fetching")
            
            # 如果任务已取消，直接返回取消状态
            if task_status == "cancelled":
                return {
                    "status": "cancelled",
                    "progress": 0,
                    "downloaded": 0,
                    "total": 0,
                    "speed": 0,
                    "error": task_info.get("error", "Download cancelled")
                }
            
            # 优先检查是否有下载器的task_id（即使状态还是fetching，如果已经有downloader_task_id，说明curl已经启动）
            downloader_task_id = task_info.get("downloader_task_id")
            if downloader_task_id:
                # 有downloader_task_id，从下载器获取最新进度
                progress_info = self.downloader.get_download_progress(downloader_task_id)
            elif task_status == "fetching":
                # 如果任务还在获取URL/magnet阶段，且没有downloader_task_id
                return {
                    "status": "fetching",
                    "progress": 0,
                    "downloaded": 0,
                    "total": 0,
                    "speed": 0
                }
            else:
                # 没有downloader_task_id，且状态不是fetching，返回当前状态
                return {
                    "status": task_status,
                    "progress": task_info.get("progress", 0),
                    "downloaded": task_info.get("downloaded", 0),
                    "total": task_info.get("total", 0),
                    "speed": task_info.get("speed", 0),
                    "error": task_info.get("error")
                }
            
            # 如果下载完成，尝试重命名文件为标准格式
            if progress_info and progress_info.get("status") == "completed":
                output_path = task_info.get("output_path")
                source_type = task_info.get("source_type", "ce")
                
                if output_path and os.path.exists(output_path):
                    try:
                        # 识别ISO版本信息
                        image_info = self.iso_handler._identify_iso_version(output_path)
                        
                        # 如果识别成功，生成标准文件名并重命名
                        if image_info.get("version") and image_info.get("build_major") and image_info.get("build_minor"):
                            new_filename = self.iso_handler._generate_iso_filename(
                                os_type=image_info.get("os_type", ""),
                                version=image_info.get("version", ""),
                                build_major=image_info.get("build_major", ""),
                                build_minor=image_info.get("build_minor", ""),
                                language=image_info.get("language", "zh-cn"),
                                arch=image_info.get("arch", "x64"),
                                source_type=source_type
                            )
                            
                            # 重命名文件
                            output_dir = os.path.dirname(output_path)
                            new_path = os.path.join(output_dir, new_filename)
                            if new_path != output_path:
                                os.rename(output_path, new_path)
                                logger.info(f"File renamed to standard format: {new_filename}")
                                # Update path in task info
                                task_info["output_path"] = new_path
                                progress_info["final_path"] = new_path
                    except Exception as e:
                        logger.error(f"Failed to rename file after download: {e}")
                        import traceback
                        traceback.print_exc()
            
            # 更新download_tasks中的进度信息
            task_info.update({
                "status": progress_info.get("status", task_info.get("status")),
                "progress": progress_info.get("progress", task_info.get("progress", 0)),
                "downloaded": progress_info.get("downloaded", task_info.get("downloaded", 0)),
                "total": progress_info.get("total", task_info.get("total", 0)),
                "speed": progress_info.get("speed", task_info.get("speed", 0)),
                "error": progress_info.get("error", task_info.get("error"))
            })
            
            return progress_info
        else:
            # 直接使用下载器的task_id查询（兼容旧代码）
            progress_info = self.downloader.get_download_progress(task_id)
            
            # 如果下载完成，尝试重命名文件为标准格式
            if progress_info.get("status") == "completed" and task_id in self.download_tasks:
                task_info = self.download_tasks[task_id]
                output_path = task_info.get("output_path")
                source_type = task_info.get("source_type", "ce")
                
                if output_path and os.path.exists(output_path):
                    try:
                        # 识别ISO版本信息
                        image_info = self.iso_handler._identify_iso_version(output_path)
                        
                        # 如果识别成功，生成标准文件名并重命名
                        if image_info.get("version") and image_info.get("build_major") and image_info.get("build_minor"):
                            new_filename = self.iso_handler._generate_iso_filename(
                                os_type=image_info.get("os_type", ""),
                                version=image_info.get("version", ""),
                                build_major=image_info.get("build_major", ""),
                                build_minor=image_info.get("build_minor", ""),
                                language=image_info.get("language", "zh-cn"),
                                arch=image_info.get("arch", "x64"),
                                source_type=source_type
                            )
                            
                            # 重命名文件
                            output_dir = os.path.dirname(output_path)
                            new_path = os.path.join(output_dir, new_filename)
                            if new_path != output_path:
                                os.rename(output_path, new_path)
                                logger.info(f"File renamed to standard format: {new_filename}")
                                # Update path in task info
                                task_info["output_path"] = new_path
                                progress_info["final_path"] = new_path
                    except Exception as e:
                        logger.error(f"Failed to rename file after download: {e}")
                        import traceback
                        traceback.print_exc()
            
            return progress_info

    def _handle_iso_cancel_download(self, params: dict[str, Any]) -> dict[str, Any]:
        """取消下载任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        
        # 检查是否是配置参数创建的下载任务
        if task_id in self.download_tasks:
            # 重新获取task_info以确保获取最新的downloader_task_id（防止竞态条件）
            task_info = self.download_tasks.get(task_id)
            if not task_info:
                return {"success": False}
            
            # 检查是否有下载器的task_id
            downloader_task_id = task_info.get("downloader_task_id")
            if downloader_task_id:
                # curl进程已经启动，调用cancel_download终止curl进程
                success = self.downloader.cancel_download(downloader_task_id)
            else:
                success = True
            
            # 统一设置状态为cancelled（无论curl是否已启动）
            task_info["status"] = "cancelled"
            task_info["error"] = "Download cancelled"
            return {"success": success}
        else:
            # 直接使用下载器的task_id取消（兼容旧代码）
            success = self.downloader.cancel_download(task_id)
            return {"success": success}
    
    def _handle_iso_verify(self, params: dict[str, Any]) -> dict[str, bool]:
        """校验镜像文件（同步版本，保留兼容性）"""
        file_path = params.get("file_path")
        expected_sha256 = params.get("checksum")
        
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        result = self.iso_handler.verify_iso(file_path, expected_sha256)
        return {"valid": result.get("valid", False)}
    
    def _handle_iso_verify_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步校验ISO文件：启动任务"""
        file_path = params.get("file_path")
        expected_sha256 = params.get("checksum")
        
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        task_id = self.task_manager.create_task(
            "iso_verify",
            self.iso_handler.verify_iso,
            file_path,
            expected_sha256,
        )
        return {"task_id": task_id}
    
    def _handle_iso_verify_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步校验ISO文件：获取任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_delete(self, params: dict[str, Any]) -> dict[str, bool | str]:
        """删除本地镜像"""
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        return self.iso_handler.delete_iso(file_path)
    
    def _handle_iso_import(self, params: dict[str, Any]) -> dict[str, Any]:
        """导入本地ISO文件（同步包装，保持兼容）"""
        iso_path = params.get("iso_path")
        overwrite = params.get("overwrite", False)
        if not iso_path:
            raise ValueError("Missing iso_path parameter")
        # 为兼容性，直接调用同步方法
        return self.iso_handler.import_iso(iso_path, overwrite)

    def _handle_iso_import_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步导入本地ISO文件：启动任务"""
        iso_path = params.get("iso_path")
        overwrite = params.get("overwrite", False)
        if not iso_path:
            raise ValueError("Missing iso_path parameter")
        task_id = self.task_manager.create_task(
            "iso_import",
            self.iso_handler.import_iso,
            iso_path,
            overwrite,
        )
        return {"task_id": task_id}

    def _handle_iso_import_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步导入本地ISO文件：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)

    def _handle_iso_identify(self, params: dict[str, Any]) -> dict[str, Any]:
        """同步识别ISO文件版本信息（保持兼容）"""
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Missing file_path parameter")
        return self.iso_handler.identify_iso(file_path)

    def _handle_iso_identify_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步识别ISO文件版本信息：启动任务"""
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Missing file_path parameter")
        task_id = self.task_manager.create_task(
            "iso_identify",
            self.iso_handler.identify_iso,
            file_path,
        )
        return {"task_id": task_id}

    def _handle_iso_identify_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步识别ISO文件版本信息：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_redownload(self, params: dict[str, Any]) -> dict[str, str]:
        """重新下载镜像"""
        file_path = params.get("file_path")
        image_id = params.get("image_id")
        
        # Prefer file_path, if not available use image_id to find from local image list
        if not file_path and not image_id:
            raise ValueError("Missing file_path or image_id parameter")
        
        # 如果只有 image_id，需要从本地镜像列表中查找对应的文件路径
        if not file_path and image_id:
            local_images = self.iso_handler.list_images("local", {})
            image = next((img for img in local_images if img.get("id") == image_id), None)
            if not image:
                raise ValueError(f"Image with ID {image_id} not found")
            file_path = image.get("url")
            if not file_path:
                raise ValueError(f"Image {image_id} has no file path")
        
        # 从镜像信息中提取原始下载URL
        # Note: Local images may not have original URL, need to infer from image info or use default source
        local_images = self.iso_handler.list_images("local", {})
        image = next((img for img in local_images if img.get("url") == file_path), None)
        
        if not image:
            raise ValueError(f"Image with file path {file_path} not found")
        
        # 根据镜像信息重新获取下载链接
        os_type = image.get("os_type", "").lower()
        version = image.get("version", "")
        language = image.get("language", "zh-cn")
        arch = image.get("architecture", "x64")
        source_type = image.get("source_type", "ce")
        
        # 确定下载源
        source = "microsoft" if source_type == "me" else "msdn"
        
        # 获取镜像列表并找到匹配的镜像
        filter_options = {
            "os": "Windows11" if "11" in os_type else "Windows10",
            "version": version,
            "language": language,
            "arch": arch
        }
        
        # 使用新的fetch_download_url方法获取URL
        config = {
            "os": "Windows11" if "11" in os_type else "Windows10",
            "version": version,
            "language": language,
            "arch": arch
        }
        
        # 生成输出路径（覆盖原文件）
        output_path = file_path
        
        # 使用配置参数创建下载任务（复用_handle_iso_download的逻辑）
        return self._handle_iso_download({
            "source": source,
            "config": config,
            "output_path": output_path
        })
    
    def _handle_unattend_export_xml(self, params: dict[str, Any]) -> dict[str, Any]:
        """处理导出 XML 请求"""
        if not self.unattend_generator:
            raise Exception("Unattend generator not initialized")
        
        try:
            # 确保 params 是字典类型
            if not isinstance(params, dict):
                logger.error(f"Invalid params type: {type(params)}, value: {params}")
                raise ValueError(f"params must be a dict, got {type(params)}")
            
            # 获取前端配置
            config_dict = params.get('config', {})
            logger.debug(f"Received config_dict type: {type(config_dict)}")
            logger.debug(f"Received config_dict keys: {list(config_dict.keys()) if isinstance(config_dict, dict) else 'N/A'}")
            
            # 如果 config 是字符串，尝试解析为 JSON
            if isinstance(config_dict, str):
                import json
                try:
                    config_dict = json.loads(config_dict)
                    logger.debug(f"Parsed config_dict from JSON string")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse config as JSON: {e}")
                    raise ValueError(f"config must be a dict or valid JSON string, got: {config_dict}")
            
            # 确保 config_dict 是字典
            if not isinstance(config_dict, dict):
                logger.error(f"Invalid config type: {type(config_dict)}, value: {config_dict}")
                raise ValueError(f"config must be a dict, got {type(config_dict)}")
            
            # 验证 config_dict 的结构（检查一些关键字段）
            if config_dict:
                logger.debug(f"Config dict has {len(config_dict)} top-level keys")
                # 检查一些可能被错误序列化的字段
                for key, value in config_dict.items():
                    if isinstance(value, str) and key in ['languageSettings', 'timeZone', 'computerName', 'accountSettings']:
                        logger.warning(f"Key '{key}' has string value, might need JSON parsing: {value[:100] if len(str(value)) > 100 else value}")
                        # 尝试解析为 JSON
                        import json
                        try:
                            config_dict[key] = json.loads(value)
                            logger.debug(f"Successfully parsed '{key}' from JSON string")
                        except (json.JSONDecodeError, TypeError):
                            pass  # 不是 JSON 字符串，继续
            
            # 转换为 Python Configuration 对象
            from unattend_generator import config_dict_to_configuration
            config = config_dict_to_configuration(config_dict, self.unattend_generator)
            
            # 生成 XML
            xml_bytes = self.unattend_generator.generate_xml(config)
            
            # 返回 base64 编码的 XML（便于 JSON 传输）
            import base64
            xml_base64 = base64.b64encode(xml_bytes).decode('ascii')
            
            return {
                "xml": xml_base64,
                "size": len(xml_bytes)
            }
        except Exception as e:
            logger.error(f"Export XML failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _handle_unattend_import_xml(self, params: dict[str, Any]) -> dict[str, Any]:
        """处理导入 XML 请求"""
        if not self.unattend_generator:
            raise Exception("Unattend generator not initialized")
        
        try:
            # 获取 XML 内容（base64 编码）
            xml_base64 = params.get('xml', '')
            if not xml_base64:
                raise ValueError("XML content is required")
            
            # 解码 XML
            import base64
            xml_bytes = base64.b64decode(xml_base64)
            
            # 解析 XML
            config_dict = self.unattend_generator.parse_xml(xml_bytes)
            
            return {
                "config": config_dict
            }
        except Exception as e:
            logger.error(f"Import XML failed: {e}")
            raise
    
    def _handle_unattend_get_data(self, params: dict[str, Any]) -> dict[str, Any]:
        """处理获取配置数据请求（支持 i18n）"""
        if not self.unattend_generator:
            raise Exception("Unattend generator not initialized")
        
            import logging
            logger = logging.getLogger('UnattendGetData')
        try:
            # 获取语言代码（用于 i18n 适配）
            lang = params.get('lang', 'en')
            # 如果语言代码是 'zh-CN' 或 'zh-TW'，转换为 'zh' 或 'zh-Hant'
            if lang == 'zh-CN':
                lang = 'zh'
            elif lang == 'zh-TW':
                lang = 'zh-Hant'
            elif '-' in lang:
                # 提取主要语言代码（如 'en-US' -> 'en'）
                lang = lang.split('-')[0]
            
            # 如果语言代码改变，重新加载数据
            if self.unattend_generator.lang != lang:
                self.unattend_generator.lang = lang
                self.unattend_generator._load_data()
            
            # 构建返回数据
            result = {
                "languages": [],
                "locales": [],
                "keyboards": [],
                "defaultInputProfiles": [],
                "timeZones": [],
                "geoLocations": [],
                "windowsEditions": [],
                "bloatwareItems": []
            }
            
            # 转换 ImageLanguage
            for lang_id, lang_obj in self.unattend_generator.image_languages.items():
                result["languages"].append({
                    "id": lang_obj.id,
                    "name": lang_obj.display_name
                })
            
            # 转换 UserLocale
            for locale_id, locale_obj in self.unattend_generator.user_locales.items():
                result["locales"].append({
                    "id": locale_obj.id,
                    "name": locale_obj.display_name
                })
            
            # 转换 KeyboardIdentifier
            for kb_id, kb_obj in self.unattend_generator.keyboard_identifiers.items():
                result["keyboards"].append({
                    "id": kb_obj.id,
                    "name": kb_obj.display_name,
                    "type": kb_obj.type.value if hasattr(kb_obj.type, 'value') else str(kb_obj.type)
                })

            # 转换 DefaultInputProfile
            for profile_id, profile_obj in self.unattend_generator.default_input_profiles.items():
                result["defaultInputProfiles"].append({
                    "id": profile_obj.id,
                    "name": profile_obj.display_name,
                    "primaryInputProfile": profile_obj.primary_input_profile,
                    "allowedInputProfiles": profile_obj.allowed_input_profiles
                })
            
            # 转换 TimeOffset
            for tz_id, tz_obj in self.unattend_generator.time_offsets.items():
                result["timeZones"].append({
                    "id": tz_obj.id,
                    "name": tz_obj.display_name
                })
            
            # 转换 GeoLocation
            for geo_id, geo_obj in self.unattend_generator.geo_locations.items():
                result["geoLocations"].append({
                    "id": geo_obj.id,
                    "name": geo_obj.display_name
                })
            
            # 转换 WindowsEdition
            for edition_id, edition_obj in self.unattend_generator.windows_editions.items():
                result["windowsEditions"].append({
                    "id": edition_obj.id,
                    "name": edition_obj.display_name,
                    "key": edition_obj.product_key if edition_obj.product_key else None,
                    "index": edition_obj.index if edition_obj.index else None
                })
            
            # 转换 Bloatware
            for bloatware_id, bloatware_obj in self.unattend_generator.bloatwares.items():
                result["bloatwareItems"].append({
                    "id": bloatware_obj.id,
                    "name": bloatware_obj.display_name
                })
            
            try:
                logger.info("[Unattend] get_data sizes - languages=%s locales=%s keyboards=%s defaultInputProfiles=%s timeZones=%s geoLocations=%s editions=%s bloatwares=%s",
                            len(result["languages"]), len(result["locales"]), len(result["keyboards"]), len(result["defaultInputProfiles"]),
                            len(result["timeZones"]), len(result["geoLocations"]), len(result["windowsEditions"]),
                            len(result["bloatwareItems"]))
            except Exception:
                pass
            
            return result
        except Exception as e:
            logger.error(f"Get data failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
            
    def _handle_iso_customize_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步定制ISO文件：启动任务"""
        source_iso = params.get("source_iso")
        target_iso = params.get("target_iso")
        config_dict = params.get("config")
        
        if not source_iso or not target_iso or not config_dict:
            raise ValueError("Missing source_iso, target_iso, or config parameter")
            
        if not self.unattend_generator:
            raise Exception("Unattend generator not initialized")
            
        # 生成 XML
        from unattend_generator import config_dict_to_configuration
        config = config_dict_to_configuration(config_dict, self.unattend_generator)
        xml_bytes = self.unattend_generator.generate_xml(config)
        
        def _customize_job(source_path, target_path, xml_data):
            import tempfile
            import os
            from iso_modifier import ISOModifier
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as temp_xml:
                temp_xml.write(xml_data)
                temp_xml_path = temp_xml.name
                
            try:
                # 遵循集成逻辑：通过 ISOModifier 协调写入 autounattend.xml 并利用内部机制使用 mkisofs 重新生成大文件 ISO
                modifier = ISOModifier(source_path)
                result = modifier.add_autounattend(temp_xml_path, target_path)
                if not result.get("success"):
                    raise Exception(result.get("message", "ISO modification failed"))
                return result
            finally:
                if os.path.exists(temp_xml_path):
                    try:
                        os.remove(temp_xml_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp xml file {temp_xml_path}: {e}")
                    
        task_id = self.task_manager.create_task(
            "iso_customize",
            _customize_job,
            source_iso,
            target_iso,
            xml_bytes
        )
        return {"task_id": task_id}
        
    def _handle_iso_customize_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步定制ISO文件：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)

    def _find_install_image_iso_path(self, template_iso: str) -> str:
        from iso_modifier import ISOModifier

        modifier = ISOModifier(template_iso)
        sources_files = modifier.list_directory('/sources')
        for filename in sources_files:
            normalized = filename.lower()
            if normalized.startswith('install.') and (normalized.endswith('.wim') or normalized.endswith('.esd')):
                return f"/sources/{filename}"

        raise FileNotFoundError("install.wim or install.esd not found in ISO")

    def _extract_install_image(self, template_iso: str, output_path: str) -> str:
        from iso_modifier import ISOModifier

        install_image_iso_path = self._find_install_image_iso_path(template_iso)
        modifier = ISOModifier(template_iso)
        modifier.extract_file(install_image_iso_path, output_path)
        return install_image_iso_path

    def _list_wim_images(self, wim_path: str) -> list[dict[str, Any]]:
        from wim_handler import WIMHandler

        images: list[dict[str, Any]] = []
        with WIMHandler(wim_path) as handler:
            image_count = handler.get_image_count()
            for index in range(1, image_count + 1):
                name = handler.get_image_name(index)
                edition = handler.get_image_info(index, "edition")
                architecture = handler.get_image_info(index, "architecture_name")
                build = handler.get_image_info(index, "build")
                description = handler.get_image_description(index)
                images.append({
                    "index": index,
                    "name": name,
                    "edition": edition,
                    "architecture": architecture,
                    "build": build,
                    "description": description,
                    "label": self._build_wim_image_label(index, name, edition, architecture, build),
                })

        return images

    def _build_wim_image_label(
        self,
        index: int,
        name: str | None,
        edition: str | None,
        architecture: str | None,
        build: str | None,
    ) -> str:
        primary = (name or "").strip() or f"Image {index}"
        extras = [value for value in [edition, architecture, build] if value]
        if extras:
            return f"{index} - {primary} ({', '.join(extras)})"
        return f"{index} - {primary}"

    def _normalize_wim_target_path(self, target_path: str) -> str:
        normalized = str(target_path or "").strip().replace('/', '\\')
        if not normalized:
            raise ValueError("target_path cannot be empty")
        if not normalized.startswith('\\'):
            normalized = '\\' + normalized
        return normalized

    def _validate_file_mappings(self, file_mappings: Any) -> list[tuple[str, str]]:
        normalized_mappings: list[tuple[str, str]] = []
        if not file_mappings:
            return normalized_mappings

        if not isinstance(file_mappings, list):
            raise ValueError("file_mappings must be a list")

        for index, mapping in enumerate(file_mappings, start=1):
            if not isinstance(mapping, dict):
                raise ValueError(f"file_mappings[{index}] must be an object")

            source_path = str(mapping.get("source_path") or "").strip()
            target_path = str(mapping.get("target_path") or "").strip()

            if not source_path:
                raise ValueError(f"file_mappings[{index}].source_path cannot be empty")
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"file_mappings[{index}].source_path not found: {source_path}")
            if not target_path:
                raise ValueError(f"file_mappings[{index}].target_path cannot be empty")

            normalized_mappings.append((source_path, self._normalize_wim_target_path(target_path)))

        return normalized_mappings

    def _resolve_wim_image_index(self, wim_path: str, selected_index: Any, config_dict: dict[str, Any]) -> int:
        from wim_handler import WIMHandler

        with WIMHandler(wim_path) as handler:
            image_count = handler.get_image_count()

            if selected_index not in (None, ""):
                try:
                    resolved_index = int(selected_index)
                except (TypeError, ValueError):
                    raise ValueError("selected_wim_image_index must be an integer")

                if resolved_index < 1 or resolved_index > image_count:
                    raise ValueError(f"selected_wim_image_index {resolved_index} is out of range (1-{image_count})")
                return resolved_index

            source_image = config_dict.get("sourceImage") or {}
            mode = source_image.get("mode", "automatic")

            if mode == "index":
                resolved_index = int(source_image.get("imageIndex") or 1)
                if resolved_index < 1 or resolved_index > image_count:
                    raise ValueError(f"sourceImage.imageIndex {resolved_index} is out of range (1-{image_count})")
                return resolved_index

            if mode == "name":
                target_name = str(source_image.get("imageName") or "").strip()
                if not target_name:
                    raise ValueError("sourceImage.imageName cannot be empty when mode=name")

                for index in range(1, image_count + 1):
                    if handler.get_image_name(index) == target_name:
                        return index

                raise ValueError(f"sourceImage.imageName not found: {target_name}")

            return 1

    def _build_installer_payload(self, work_dir: Path) -> Path:
        payload_root = work_dir / "installer_payload" / "WindowsAutoInstaller"
        payload_root.mkdir(parents=True, exist_ok=True)

        runtime_sources = [
            (self.project_root / "src" / "backend", payload_root / "backend"),
            (self.project_root / "src" / "shared", payload_root / "shared"),
            (self.project_root / "src" / "frontend" / "dist", payload_root / "frontend" / "dist"),
            (self.project_root / "src" / "frontend" / "electron", payload_root / "frontend" / "electron"),
        ]

        copied_any = False
        ignore_patterns = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "node_modules")

        for source_path, target_path in runtime_sources:
            if source_path.exists():
                shutil.copytree(source_path, target_path, dirs_exist_ok=True, ignore=ignore_patterns)
                copied_any = True

        frontend_package = self.project_root / "src" / "frontend" / "package.json"
        if frontend_package.exists():
            (payload_root / "frontend").mkdir(parents=True, exist_ok=True)
            shutil.copy2(frontend_package, payload_root / "frontend" / "package.json")
            copied_any = True

        if not copied_any:
            raise FileNotFoundError("No installer runtime payload was found to integrate into WIM")

        return payload_root

    def _handle_deployment_list_wim_images(self, params: dict[str, Any]) -> dict[str, Any]:
        """读取模板 ISO 中的 install.wim/install.esd 映像列表"""
        template_iso = params.get("template_iso")
        if not template_iso:
            raise ValueError("Missing template_iso parameter")

        template_path = Path(template_iso)
        if not template_path.exists() or not template_path.is_file():
            raise ValueError("template_iso does not exist or is not a file")

        with tempfile.TemporaryDirectory(prefix="deployment_wim_list_") as temp_dir:
            install_image_iso_path = self._find_install_image_iso_path(str(template_path))
            extracted_wim_path = Path(temp_dir) / Path(install_image_iso_path).name
            self._extract_install_image(str(template_path), str(extracted_wim_path))
            images = self._list_wim_images(str(extracted_wim_path))

        return {
            "install_image_path": install_image_iso_path,
            "images": images,
        }

    def _handle_deployment_build_start(self, params: dict[str, Any]) -> dict[str, str]:
        """集成与部署：构建带 WIM 修改和 autounattend 注入的新 ISO"""
        template_iso = params.get("template_iso")
        export_dir = params.get("export_dir")
        output_name = params.get("output_name")
        integrate_installer = bool(params.get("integrate_installer", False))
        file_mappings = params.get("file_mappings") or []
        selected_wim_image_index = params.get("selected_wim_image_index")
        config_dict = params.get("config")

        if not template_iso or not export_dir or not config_dict:
            raise ValueError("Missing template_iso, export_dir, or config parameter")

        if not self.unattend_generator:
            raise Exception("Unattend generator not initialized")

        export_dir_path = Path(export_dir)
        if not export_dir_path.exists() or not export_dir_path.is_dir():
            raise ValueError("export_dir does not exist or is not a directory")

        template_path = Path(template_iso)
        if not template_path.exists() or not template_path.is_file():
            raise ValueError("template_iso does not exist or is not a file")

        if not output_name:
            output_name = f"{template_path.stem}_customized.iso"
        elif not str(output_name).lower().endswith('.iso'):
            output_name = f"{output_name}.iso"

        target_iso = str(export_dir_path / output_name)

        from unattend_generator import config_dict_to_configuration
        config = config_dict_to_configuration(config_dict, self.unattend_generator)
        xml_bytes = self.unattend_generator.generate_xml(config)
        validated_mappings = self._validate_file_mappings(file_mappings)

        def _build_job(source_path, target_path, xml_data, mappings, should_integrate_installer, selected_image_index, full_config, task_updater=None):
            from iso_modifier import ISOModifier
            from wim_handler import WIMHandler

            def report(stage: str, message: str, percent: int) -> None:
                if task_updater:
                    task_updater(progress={
                        "stage": stage,
                        "message": message,
                        "percent": percent,
                    })

            report("validate", "正在校验构建参数", 5)

            work_dir = Path(tempfile.mkdtemp(prefix="deployment_build_"))
            install_image_iso_path = self._find_install_image_iso_path(source_path)
            wim_file_name = Path(install_image_iso_path).name
            original_wim_path = work_dir / wim_file_name
            updated_wim_path = work_dir / f"updated_{wim_file_name}"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as temp_xml:
                temp_xml.write(xml_data)
                temp_xml_path = temp_xml.name

            try:
                report("extract_wim", f"正在提取 {wim_file_name}", 15)
                self._extract_install_image(source_path, str(original_wim_path))

                report("resolve_image", "正在解析目标 WIM 映像", 25)
                target_image_index = self._resolve_wim_image_index(
                    str(original_wim_path),
                    selected_image_index,
                    full_config,
                )

                add_files = list(mappings)

                if should_integrate_installer:
                    report("integrate_installer", "正在准备 Windows Auto Installer 运行文件", 40)
                    payload_root = self._build_installer_payload(work_dir)
                    add_files.append((str(payload_root), "\\Windows\\Setup\\Scripts\\WindowsAutoInstaller"))

                if add_files:
                    report("apply_mappings", f"正在写入 {len(add_files)} 项 WIM 更新", 55)
                    with WIMHandler(str(original_wim_path), write_access=True) as handler:
                        handler.update_image(target_image_index, add_files=add_files)
                        report("write_wim", "正在写出更新后的 WIM 文件", 70)
                        handler.write_wim(str(updated_wim_path))
                else:
                    shutil.copy2(original_wim_path, updated_wim_path)

                modifier = ISOModifier(source_path)
                writer = modifier.create_writer()
                report("replace_wim_in_iso", "正在将新的 WIM 写回 ISO", 80)
                writer.replace_file(install_image_iso_path, str(updated_wim_path))

                report("inject_unattend", "正在写入 autounattend.xml", 90)
                if modifier.file_exists('/autounattend.xml'):
                    writer.replace_file('/autounattend.xml', temp_xml_path)
                else:
                    writer.add_file(temp_xml_path, '/autounattend.xml')

                report("finalize", "正在生成最终 ISO", 95)
                result = writer.write(target_path)
                if not result.get("success"):
                    raise Exception(result.get("message", "Deployment build failed"))

                result["iso_path"] = target_path
                result["source_iso"] = source_path
                result["install_image_path"] = install_image_iso_path
                result["selected_wim_image_index"] = target_image_index
                report("done", "构建完成", 100)
                return result
            finally:
                if os.path.exists(temp_xml_path):
                    try:
                        os.remove(temp_xml_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp xml file {temp_xml_path}: {e}")
                if work_dir.exists():
                    try:
                        shutil.rmtree(work_dir)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp work directory {work_dir}: {e}")

        task_id = self.task_manager.create_task(
            "deployment_build",
            _build_job,
            str(template_path),
            target_iso,
            xml_bytes,
            validated_mappings,
            integrate_installer,
            selected_wim_image_index,
            config_dict,
        )
        return {"task_id": task_id}

    def _handle_deployment_build_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """集成与部署：查询构建任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)

    def _handle_burn_list_devices(self, params: dict[str, Any]) -> dict[str, Any]:
        """同步获取可用磁盘/U盘设备列表"""
        from iso_burner import ISOBurner
        burner = ISOBurner()
        return {"devices": burner.list_devices()}

    def _handle_burn_start(self, params: dict[str, Any]) -> dict[str, str]:
        """异步烧录ISO文件：启动任务"""
        iso_path = params.get("iso_path")
        device_path = params.get("device_path")
        if not iso_path or not device_path:
            raise ValueError("Missing iso_path or device_path parameter")
            
        def _burn_job(iso, device):
            from iso_burner import ISOBurner
            burner = ISOBurner()
            result = burner.burn_iso(iso, device)
            if not result.get("success"):
                raise Exception(result.get("message", "Burning failed"))
            return result
            
        task_id = self.task_manager.create_task("iso_burn", _burn_job, iso_path, device_path)
        return {"task_id": task_id}

    def _handle_burn_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """异步烧录ISO文件：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)


def main():
    """主函数"""
    server = BackendServer()
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(e)}"
            }
        }
        logger.error(f"Internal server error: {e}")
        try:
            json_str = json.dumps(error_response, ensure_ascii=False)
            print(json_str, flush=True)  # Keep print for IPC communication
        except UnicodeEncodeError:
            # 如果仍然有编码问题，使用 ensure_ascii=True
            json_str = json.dumps(error_response, ensure_ascii=True)
            print(json_str, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


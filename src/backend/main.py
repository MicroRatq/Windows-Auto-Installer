"""
Backend main entry - IPC server
Communicates with Electron frontend via stdin/stdout
"""
import json
import os
import sys
import traceback
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

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
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(self, name: str, func, *args, **kwargs) -> str:
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
                result = func(*args, **kwargs)
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

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
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
    
    def __init__(self):
        self.running = True
        self.handlers = {}
        self.task_manager = TaskManager()
    
    def register_handler(self, method: str, handler):
        """注册请求处理器"""
        self.handlers[method] = handler
    
    def send_response(self, request_id: str, result: Any = None, error: Optional[str] = None):
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
            response["result"] = result
        
        try:
            json_str = json.dumps(response, ensure_ascii=False)
            print(json_str, flush=True)  # Keep print for IPC communication
        except Exception as e:
            # If response serialization fails, try to send error information
            logger.error(f"Response serialization failed: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32700,
                    "message": f"Response serialization failed: {str(e)}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)  # Keep print for IPC communication
    
    def handle_request(self, request: Dict[str, Any]):
        """处理单个请求"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not request_id:
            self.send_response(None, error="Missing request ID")
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
            result = handler(params)
            self.send_response(request_id, result=result)
        except Exception as e:
            logger.error(f"Handler execution failed for {method}: {e}")
            error_msg = f"{method} execution failed: {str(e)}"
            self.send_response(request_id, error=error_msg)
    
    def run(self):
        """运行服务器主循环"""
        # 注册基础处理器
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_platform", self._handle_get_platform)
        
        # 注册ISO镜像相关处理器
        try:
            # 添加当前目录到Python路径，以便导入同目录下的模块
            backend_dir = Path(__file__).parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            
            from iso_handler import ISOHandler
            from downloader import Downloader
            
            # 计算项目根目录（main.py 在 src/backend/，所以需要向上两级）
            project_root = backend_dir.parent.parent
            cache_dir = project_root / "data" / "isos"
            
            self.iso_handler = ISOHandler(cache_dir=str(cache_dir))
            self.downloader = Downloader()
            self.download_tasks = {}  # 存储下载任务
            self.project_root = project_root
            
            self.register_handler("iso_list_sources", self._handle_iso_list_sources)
            self.register_handler("iso_list_images", self._handle_iso_list_images)
            self.register_handler("iso_list_images_start", self._handle_iso_list_images_start)
            self.register_handler("iso_list_images_status", self._handle_iso_list_images_status)
            self.register_handler("iso_list_versions", self._handle_iso_list_versions)
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
        
        # 读取stdin并处理请求
        for line in sys.stdin:
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
                self.send_response(None, error=f"JSON parsing failed: {str(e)}")
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
                self.send_response(None, error=f"Request processing failed: {str(e)}")
    
    def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理ping请求"""
        return {"status": "ok", "message": "pong"}
    
    def _handle_get_platform(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取平台信息"""
        import platform
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine()
        }
    
    def _handle_iso_list_sources(self, params: Dict[str, Any]) -> list:
        """获取镜像源列表"""
        return self.iso_handler.list_sources()
    
    def _handle_iso_list_images(self, params: Dict[str, Any]) -> list:
        """获取镜像列表"""
        source = params.get("source", "local")
        filter_options = params.get("filter", {})
        return self.iso_handler.list_images(source, filter_options)

    def _handle_iso_list_images_start(self, params: Dict[str, Any]) -> Dict[str, str]:
        """异步获取镜像列表：启动任务"""
        source = params.get("source", "local")
        filter_options = params.get("filter", {})
        task_id = self.task_manager.create_task(
            "iso_list_images",
            self.iso_handler.list_images,
            source,
            filter_options,
        )
        return {"task_id": task_id}

    def _handle_iso_list_images_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """异步获取镜像列表：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_list_versions(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """获取可用版本列表（从配置文件读取）"""
        os_type = params.get("os_type")
        return self.iso_handler.list_available_versions(os_type)
    
    def _handle_iso_test_mirror(self, params: Dict[str, Any]) -> Dict[str, float]:
        """测试镜像站网络（同步版本，保持向后兼容）"""
        source = params.get("source", "msdl")
        test_url = params.get("url")
        return self.iso_handler.test_mirror(source, test_url)

    def _handle_iso_test_mirror_start(self, params: Dict[str, Any]) -> Dict[str, str]:
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

    def _handle_iso_test_mirror_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """异步测试镜像站网络：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_start_test_mirror(self, params: Dict[str, Any]) -> Dict[str, str]:
        """开始测试镜像站网络（异步）"""
        source = params.get("source", "microsoft")
        test_url = params.get("url")
        task_id = self.iso_handler.start_test_mirror(source, test_url)
        return {"task_id": task_id}
    
    def _handle_iso_get_test_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取测试任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.iso_handler.get_test_status(task_id)
    
    def _handle_iso_cancel_test(self, params: Dict[str, Any]) -> Dict[str, bool]:
        """中止测试任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        success = self.iso_handler.cancel_test(task_id)
        return {"success": success}
    
    def _handle_iso_download(self, params: Dict[str, Any]) -> Dict[str, str]:
        """下载镜像"""
        url = params.get("url")
        url_type = params.get("url_type", "http")
        output_path = params.get("output_path")
        
        if not url or not output_path:
            raise ValueError("Missing url or output_path parameter")
        
        # 标准化输出路径（相对路径默认以项目根目录为基准）
        if not os.path.isabs(output_path):
            base_dir = getattr(self, "project_root", Path(__file__).parent.parent)
            output_path = os.path.abspath(os.path.join(str(base_dir), output_path))
        
        # 根据 URL 判断来源类型（用于后续文件重命名）
        source_type = "ce"  # 默认 Consumer Editions
        if "microsoft.com" in url or "dl.delivery.mp.microsoft.com" in url:
            source_type = "me"  # Multi Editions
        
        # 使用下载器下载
        if url_type == "ed2k":
            task_id = self.downloader.download_ed2k(url, output_path)
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
    
    def _handle_iso_download_progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查询下载进度"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        
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

    def _handle_iso_cancel_download(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取消下载任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        success = self.downloader.cancel_download(task_id)
        return {"success": success}
    
    def _handle_iso_verify(self, params: Dict[str, Any]) -> Dict[str, bool]:
        """校验镜像文件"""
        file_path = params.get("file_path")
        expected_sha256 = params.get("checksum")
        
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        result = self.iso_handler.verify_iso(file_path, expected_sha256)
        return {"valid": result.get("valid", False)}
    
    def _handle_iso_delete(self, params: Dict[str, Any]) -> Dict[str, bool]:
        """删除本地镜像"""
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        return self.iso_handler.delete_iso(file_path)
    
    def _handle_iso_import(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """导入本地ISO文件（同步包装，保持兼容）"""
        iso_path = params.get("iso_path")
        overwrite = params.get("overwrite", False)
        if not iso_path:
            raise ValueError("Missing iso_path parameter")
        # 为兼容性，直接调用同步方法
        return self.iso_handler.import_iso(iso_path, overwrite)

    def _handle_iso_import_start(self, params: Dict[str, Any]) -> Dict[str, str]:
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

    def _handle_iso_import_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """异步导入本地ISO文件：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)

    def _handle_iso_identify(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """同步识别ISO文件版本信息（保持兼容）"""
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Missing file_path parameter")
        return self.iso_handler.identify_iso(file_path)

    def _handle_iso_identify_start(self, params: Dict[str, Any]) -> Dict[str, str]:
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

    def _handle_iso_identify_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """异步识别ISO文件版本信息：查询任务状态"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")
        return self.task_manager.get_task_status(task_id)
    
    def _handle_iso_redownload(self, params: Dict[str, Any]) -> Dict[str, str]:
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
        
        available_images = self.iso_handler.list_images(source, filter_options)
        if not available_images:
            raise ValueError("No matching images found for redownload")
        
        # 选择第一个匹配的镜像
        target_image = available_images[0]
        download_url = target_image.get("url")
        url_type = target_image.get("url_type", "http")
        
        if not download_url:
            raise ValueError("Image has no download URL")
        
        # 生成输出路径（覆盖原文件）
        output_path = file_path
        
        # 开始下载
        if url_type == "ed2k":
            task_id = self.downloader.download_ed2k(download_url, output_path)
        else:
            task_id = self.downloader.download_with_curl(download_url, output_path)
        
        # 存储任务信息
        self.download_tasks[task_id] = {
            "url": download_url,
            "output_path": output_path,
            "url_type": url_type,
            "source_type": source_type
        }
        
        return {"task_id": task_id, "status": "started"}
    
    def _handle_iso_identify(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """手动识别ISO文件版本信息"""
        file_path = params.get("file_path")
        
        if not file_path:
            raise ValueError("Missing file_path parameter")
        
        return self.iso_handler.identify_iso(file_path)


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
        print(json.dumps(error_response, ensure_ascii=False), flush=True)  # Keep print for IPC communication
        sys.exit(1)


if __name__ == "__main__":
    main()


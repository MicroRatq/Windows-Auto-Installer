"""
Universal download module
Supports HTTP/HTTPS multi-threaded downloads, ed2k downloads, network testing and file verification
"""
import os
import sys
import subprocess
import hashlib
import time
import threading
import uuid
import re
import logging
import atexit
import shutil
from typing import Any, Callable
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('Downloader')


class DownloadError(Exception):
    """下载错误"""
    pass


class Downloader:
    """通用下载器"""
    
    def __init__(self, curl_path: str | None = None, temp_dir: str | None = None):
        """
        初始化下载器
        
        Args:
            curl_path: curl.exe的路径，如果为None则自动查找或下载
            temp_dir: 临时文件目录，如果为None则使用./data/tmp
        """
        self.curl_path: str = curl_path or self._get_curl_path()
        # 设置临时文件目录（用于存储下载分片）
        if temp_dir:
            self.temp_dir: Path = Path(temp_dir)
        else:
            # 默认使用项目根目录下的 data/tmp
            project_root = Path(__file__).parent.parent.parent
            self.temp_dir = project_root / "data" / "tmp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.download_tasks: dict[str, dict[str, Any]] = {}
        self._lock: threading.Lock = threading.Lock()
        # 跟踪所有curl子进程以及按任务跟踪，用于取消和退出清理
        self._active_processes: list[subprocess.Popen[str]] = []
        self._task_processes: dict[str, list[subprocess.Popen[str]]] = {}
        atexit.register(self._cleanup_processes)

    def _register_process(self, process: subprocess.Popen[str], task_id: str | None = None) -> None:
        with self._lock:
            self._active_processes.append(process)
            if task_id:
                self._task_processes.setdefault(task_id, []).append(process)

    def _unregister_process(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if process in self._active_processes:
                self._active_processes.remove(process)
            # 同时从每个任务的进程列表中移除
            for task_id, plist in list(self._task_processes.items()):
                if process in plist:
                    plist.remove(process)
                    if not plist:
                        del self._task_processes[task_id]

    def _cleanup_processes(self) -> None:
        with self._lock:
            for process in list(self._active_processes):
                if process and process.poll() is None:
                    try:
                        process.terminate()
                        _ = process.wait(timeout=5)
                    except Exception:
                        try:
                            process.kill()
                        except Exception:
                            pass
            self._active_processes.clear()

    def _run_curl_command(self, cmd: list[str], timeout: int | None = None, task_id: str | None = None) -> tuple[int, str]:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )
        self._register_process(process, task_id)
        try:
            try:
                _, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate()
                raise DownloadError("curl command timed out")
            return process.returncode, stderr or ""
        finally:
            self._unregister_process(process)

    def cancel_download(self, task_id: str) -> bool:
        """
        取消指定任务的下载，终止相关curl进程并更新任务状态
        """
        with self._lock:
            processes = list(self._task_processes.get(task_id, []))
        for process in processes:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    _ = process.wait(timeout=5)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
        with self._lock:
            task = self.download_tasks.get(task_id)
            if task:
                task["status"] = "cancelled"
                task["speed"] = 0
            if task_id in self._task_processes:
                del self._task_processes[task_id]
        return True
    
    def _get_curl_path(self) -> str:
        """获取curl.exe路径，如果不存在则下载"""
        # 优先使用项目中的curl.exe（在curl目录下）
        project_root = Path(__file__).parent.parent.parent
        curl_dir = project_root / "src" / "shared" / "curl"
        curl_path = curl_dir / "curl.exe"
        
        if curl_path.exists():
            return str(curl_path)
        
        # 如果不存在，尝试下载
        logger.info(f"curl.exe not found at {curl_path}, downloading from curl.se/windows...")
        self._download_curl(str(curl_dir))
        return str(curl_path)
    
    def _download_curl(self, target_dir: str):
        """从curl.se/windows下载curl"""
        try:
            # 从curl.se/windows页面解析并下载
            self._download_curl_from_curl_se_windows(target_dir)
            logger.info(f"curl.exe downloaded to {target_dir}")
            
        except Exception as e:
            # 如果下载失败，使用requests作为备选（这是正常的备选方案）
            logger.warning(f"curl.exe download failed: {e}")
            logger.info("Will use requests library for downloads (this is normal and fully functional)")
            # 不抛出异常，允许使用requests作为备选
    
    def _download_curl_from_curl_se_windows(self, target_dir: str):
        """从curl.se/windows下载并解压curl"""
        import zipfile
        import tempfile
        
        # 访问curl.se/windows页面
        windows_url = "https://curl.se/windows/"
        logger.info(f"Parsing {windows_url}...")
        response = requests.get(windows_url, timeout=30)
        response.raise_for_status()
        
        # 解析HTML页面，查找最新的下载链接
        soup = BeautifulSoup(response.text, 'html.parser')
        curl_zip_url = None
        
        # 查找所有链接，寻找zip文件
        for link in soup.find_all('a', href=True):
            href = str(link.get('href', ''))
            # curl.se/windows通常提供类似 curl-8.x.x-win64-mingw.zip 的文件
            if href.endswith('.zip') and ('win64' in href.lower() or 'mingw' in href.lower()):
                # 如果是相对路径，转换为绝对路径
                if href.startswith('http'):
                    curl_zip_url = href
                else:
                    # 处理相对路径
                    if href.startswith('/'):
                        curl_zip_url = f"https://curl.se{href}"
                    else:
                        curl_zip_url = f"{windows_url.rstrip('/')}/{href}"
                break
        
        # 如果HTML解析失败，尝试直接访问已知的URL模式
        if not curl_zip_url:
            # 尝试获取最新版本号
            try:
                # 从页面中提取版本号（通常在标题或链接中）
                for text in soup.stripped_strings:
                    # 查找版本号模式，如 8.17.0
                    match = re.search(r'curl[-\s]?(\d+\.\d+\.\d+)', text, re.IGNORECASE)
                    if match:
                        version = match.group(1)
                        # 构建可能的下载URL
                        curl_zip_url = f"https://curl.se/windows/dl-{version.replace('.', '_')}/curl-{version.replace('.', '_')}-win64-mingw.zip"
                        break
            except:
                pass
        
        # 如果还是找不到，尝试直接访问最新版本
        if not curl_zip_url:
            # 尝试访问已知的最新版本URL（需要根据实际情况更新）
            # 这里使用一个通用的方法：访问dl目录
            try:
                dl_url = "https://curl.se/windows/dl-8_17_0/"
                dl_response = requests.get(dl_url, timeout=10)
                if dl_response.status_code == 200:
                    dl_soup = BeautifulSoup(dl_response.text, 'html.parser')
                    for link in dl_soup.find_all('a', href=True):
                        href = str(link.get('href', ''))
                        if href.endswith('.zip') and 'win64' in href.lower():
                            curl_zip_url = f"{dl_url.rstrip('/')}/{href}"
                            break
            except:
                pass
        
        if not curl_zip_url:
            raise DownloadError("Failed to parse download link from curl.se/windows")
        
        # 下载zip文件
        logger.info(f"Downloading curl from {curl_zip_url}...")
        zip_response = requests.get(curl_zip_url, stream=True, timeout=120)
        zip_response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            for chunk in zip_response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        try:
            # 确保目标目录存在（使用绝对路径）
            target_dir_abs = os.path.abspath(target_dir)
            try:
                os.makedirs(target_dir_abs, exist_ok=True)
            except OSError as e:
                raise DownloadError(f"Failed to create target directory {target_dir_abs}: {e}")
            
            if not os.path.isdir(target_dir_abs):
                raise DownloadError(f"Target path is not a directory: {target_dir_abs}")
            
            # 解压zip文件，提取bin目录中的所有内容
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                # 查找bin目录中的所有文件
                bin_files = []
                for file_info in zip_ref.filelist:
                    filename = file_info.filename.replace('\\', '/')
                    # 查找bin目录中的文件
                    if '/bin/' in filename or filename.startswith('bin/'):
                        bin_files.append(file_info)
                
                if not bin_files:
                    raise DownloadError("bin directory not found in zip file")
                
                # 解压bin目录中的所有文件到目标目录
                for file_info in bin_files:
                    # 跳过目录条目
                    if file_info.is_dir():
                        continue
                    
                    # 获取文件名（去掉bin/前缀）
                    relative_path = file_info.filename.replace('\\', '/')
                    if relative_path.startswith('bin/'):
                        relative_path = relative_path[4:]  # 去掉'bin/'前缀
                    elif '/bin/' in relative_path:
                        relative_path = relative_path.split('/bin/')[-1]
                    
                    # 获取文件名（去掉可能的路径）
                    filename = os.path.basename(relative_path)
                    if not filename:  # 如果basename为空，使用原始文件名
                        filename = os.path.basename(file_info.filename)
                    
                    if not filename:  # 如果还是为空，跳过
                        continue
                    
                    target_file = os.path.join(target_dir_abs, filename)
                    
                    # 解压文件
                    try:
                        with zip_ref.open(file_info) as source, open(target_file, 'wb') as target:
                            target.write(source.read())
                        logger.debug(f"Extracted {filename}")
                    except OSError as e:
                        raise DownloadError(f"Failed to write file {target_file}: {e}")
                
                # 验证curl.exe是否存在
                curl_exe_path = os.path.join(target_dir_abs, "curl.exe")
                if not os.path.exists(curl_exe_path):
                    raise DownloadError("curl.exe not found after extraction")
        
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_latency(self, url: str, timeout: int = 5) -> float:
        """
        测试网络延迟（毫秒）
        
        Args:
            url: 测试URL
            timeout: 超时时间（秒）
        
        Returns:
            延迟时间（毫秒），失败返回-1
        """
        try:
            start_time = time.time()
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            latency = (time.time() - start_time) * 1000
            return latency
        except Exception as e:
            logger.error(f"Latency test failed: {e}")
            return -1
    
    def test_download_speed(self, url: str, test_size: int = 1024 * 1024, timeout: int = 10) -> dict[str, float]:
        """
        测试下载速度
        
        Args:
            url: 测试URL
            test_size: 测试下载大小（字节），默认1MB
            timeout: 超时时间（秒）
        
        Returns:
            {"speed": 速度(字节/秒), "latency": 延迟(毫秒)}，失败返回-1
        """
        try:
            # 使用HEAD请求获取文件大小
            head_response = requests.head(url, timeout=timeout, allow_redirects=True)
            head_response.raise_for_status()
            
            # 如果支持Range请求，下载指定大小
            if 'accept-ranges' in head_response.headers:
                headers = {'Range': f'bytes=0-{test_size-1}'}
            else:
                # 不支持Range，下载整个文件（如果小于test_size）
                headers = {}
            
            start_time = time.time()
            response = requests.get(url, headers=headers, stream=True, timeout=timeout)
            response.raise_for_status()
            
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded >= test_size:
                    break
            
            elapsed = time.time() - start_time
            if elapsed > 0:
                speed = downloaded / elapsed
                latency = self.test_latency(url, timeout)
                return {"speed": speed, "latency": latency}
            else:
                return {"speed": -1, "latency": -1}
        except Exception as e:
            logger.error(f"Download speed test failed: {e}")
            return {"speed": -1, "latency": -1}
    
    def verify_file(self, file_path: str, expected_sha256: str | None = None) -> dict[str, Any]:
        """
        校验文件完整性
        
        Args:
            file_path: 文件路径
            expected_sha256: 期望的SHA256哈希值（可选）
        
        Returns:
            {"valid": bool, "sha256": str, "size": int}
        """
        if not os.path.exists(file_path):
            return {"valid": False, "sha256": "", "size": 0, "error": "File does not exist"}
        
        file_size = os.path.getsize(file_path)
        
        # 计算SHA256
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256_hash.update(chunk)
        
        calculated_sha256 = sha256_hash.hexdigest()
        
        valid = True
        if expected_sha256:
            valid = calculated_sha256.lower() == expected_sha256.lower()
        
        return {
            "valid": valid,
            "sha256": calculated_sha256,
            "size": file_size,
            "error": None if valid else "SHA256 mismatch"
        }
    
    def download_with_curl(
        self,
        url: str,
        output_path: str,
        num_threads: int = 4,
        progress_callback: Callable[[float, int, int], None] | None = None
    ) -> str:
        """
        使用curl进行多线程下载
        
        Args:
            url: 下载URL
            output_path: 输出文件路径
            num_threads: 线程数
            progress_callback: 进度回调函数 (progress, downloaded, total)
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 检查curl是否可用
        if not os.path.exists(self.curl_path):
            # 使用requests作为备选
            return self._download_with_requests(url, output_path, progress_callback)
        
        # 创建任务记录
        with self._lock:
            self.download_tasks[task_id] = {
                "status": "fetching",
                "progress": 0.0,
                "downloaded": 0,
                "total": 0,
                "speed": 0,
                "url": url,
                "output_path": output_path
            }
        
        # 在后台线程中执行下载
        def _download():
            try:
                # 首先获取文件大小（URL获取阶段）
                with self._lock:
                    self.download_tasks[task_id]["status"] = "fetching"
                
                head_cmd = [self.curl_path, "-I", "-L", url]
                try:
                    head_result = subprocess.run(head_cmd, capture_output=True, text=True, timeout=10)
                    total_size = 0
                    for line in head_result.stdout.split('\n'):
                        if line.lower().startswith('content-length:'):
                            total_size = int(line.split(':')[1].strip())
                            break
                except Exception:
                    total_size = 0
                
                # URL获取完成，切换到下载状态
                with self._lock:
                    self.download_tasks[task_id]["status"] = "downloading"
                    self.download_tasks[task_id]["total"] = total_size
                
                # 如果文件大小未知或小于10MB，使用单线程下载
                if total_size == 0 or total_size < 10 * 1024 * 1024:
                    self._download_single_thread_curl(url, output_path, task_id, progress_callback)
                else:
                    # 多线程下载
                    self._download_multi_thread_curl(url, output_path, num_threads, task_id, progress_callback)
                
                with self._lock:
                    self.download_tasks[task_id]["status"] = "completed"
                    self.download_tasks[task_id]["progress"] = 1.0
                
            except Exception as e:
                with self._lock:
                    self.download_tasks[task_id]["status"] = "failed"
                    self.download_tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        
        return task_id
    
    def _download_single_thread_curl(
        self,
        url: str,
        output_path: str,
        task_id: str,
        progress_callback: Callable[[float, int, int], None] | None
    ):
        """Single-threaded curl download"""
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            self.curl_path,
            "-L",  # 跟随重定向
            "-sS",  # 静默模式但保留错误输出
            "-o", output_path,  # 输出文件
            url
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )
        self._register_process(process, task_id)

        start_time = time.time()
        last_check = start_time
        last_bytes = 0

        try:
            while True:
                retcode = process.poll()
                current_size = 0
                if os.path.exists(output_path):
                    try:
                        current_size = os.path.getsize(output_path)
                    except OSError:
                        current_size = 0
                
                now = time.time()
                elapsed = max(now - last_check, 1e-6)
                
                with self._lock:
                    self.download_tasks[task_id]["downloaded"] = current_size
                    total = self.download_tasks[task_id].get("total", 0)
                    if total > 0:
                        progress_value = current_size / total
                        if progress_value >= 1.0:
                            progress_value = 0.999
                        self.download_tasks[task_id]["progress"] = progress_value
                    speed = (current_size - last_bytes) / elapsed if elapsed > 0 else 0
                    if speed >= 0:
                        self.download_tasks[task_id]["speed"] = speed
                
                last_bytes = current_size
                last_check = now
                
                if retcode is not None:
                    break
                
                time.sleep(1)
            
            stderr_output = process.stderr.read() if process.stderr else ''
            if process.returncode == 0:
                file_size = os.path.getsize(output_path)
                with self._lock:
                    self.download_tasks[task_id]["downloaded"] = file_size
                    if self.download_tasks[task_id]["total"] == 0:
                        self.download_tasks[task_id]["total"] = file_size
                    self.download_tasks[task_id]["progress"] = 1.0
                    self.download_tasks[task_id]["speed"] = 0
            else:
                raise DownloadError(f"curl download failed: {stderr_output.strip() or 'Unknown error'}")
        finally:
            self._unregister_process(process)
            if process.stderr:
                process.stderr.close()
    
    def _download_multi_thread_curl(
        self,
        url: str,
        output_path: str,
        num_threads: int,
        task_id: str,
        progress_callback: Callable[[float, int, int], None] | None
    ):
        """多线程curl下载（使用Range请求）"""
        with self._lock:
            total_size = self.download_tasks[task_id]["total"]
        
        chunk_size = total_size // num_threads
        chunks = []
        
        for i in range(num_threads):
            start = i * chunk_size
            if i == num_threads - 1:
                end = total_size - 1
            else:
                end = (i + 1) * chunk_size - 1
            chunks.append((start, end))
        
        # 下载各个分块
        chunk_files: list[str] = []
        stop_event = threading.Event()
        monitor_thread: threading.Thread | None = None

        def monitor_progress():
            last_total = 0
            last_time = time.time()
            while not stop_event.is_set():
                downloaded_bytes = 0
                for chunk_file in chunk_files:
                    if os.path.exists(chunk_file):
                        try:
                            downloaded_bytes += os.path.getsize(chunk_file)
                        except OSError:
                            continue
                now = time.time()
                elapsed = max(now - last_time, 1e-6)
                with self._lock:
                    self.download_tasks[task_id]["downloaded"] = downloaded_bytes
                    total = self.download_tasks[task_id]["total"]
                    if total > 0:
                        progress_value = downloaded_bytes / total
                        if progress_value >= 1.0:
                            progress_value = 0.999
                        self.download_tasks[task_id]["progress"] = progress_value
                    speed = (downloaded_bytes - last_total) / elapsed if elapsed > 0 else 0
                    if speed >= 0:
                        self.download_tasks[task_id]["speed"] = speed
                last_total = downloaded_bytes
                last_time = now
                time.sleep(1)

        # 生成临时分片文件路径（存储在临时目录中）
        output_filename = os.path.basename(output_path)
        temp_chunk_base = self.temp_dir / f"{output_filename}.{task_id}"
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i, (start, end) in enumerate(chunks):
                chunk_file = str(temp_chunk_base) + f".part{i}"
                chunk_files.append(chunk_file)
                future = executor.submit(self._download_chunk, url, chunk_file, start, end, task_id, 3600)
                futures.append((i, future))
            
            monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
            monitor_thread.start()
            
            # 等待所有分块下载完成并更新进度
            completed = 0
            try:
                for i, future in futures:
                    future.result(timeout=3600)  # 1小时超时
                    completed += 1
                    with self._lock:
                        if self.download_tasks[task_id]["total"] > 0:
                            self.download_tasks[task_id]["progress"] = completed / num_threads
                            self.download_tasks[task_id]["downloaded"] = int(
                                self.download_tasks[task_id]["total"] * self.download_tasks[task_id]["progress"]
                            )
            except Exception as e:
                for cf in chunk_files:
                    if os.path.exists(cf):
                        os.unlink(cf)
                raise DownloadError(f"Download failed: {e}")
            finally:
                stop_event.set()
                if monitor_thread:
                    monitor_thread.join(timeout=5)
        
        # Merge chunks to temporary file first, then move to final location
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 先合并到临时文件
        temp_output = str(temp_chunk_base) + ".tmp"
        try:
            with open(temp_output, 'wb') as outfile:
                for chunk_file in chunk_files:
                    with open(chunk_file, 'rb') as infile:
                        while True:
                            chunk = infile.read(8192)
                            if not chunk:
                                break
                            outfile.write(chunk)
                    os.unlink(chunk_file)
            
            # 合并完成后，移动到最终目标位置
            if os.path.exists(temp_output):
                shutil.move(temp_output, output_path)
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_output):
                try:
                    os.unlink(temp_output)
                except:
                    pass
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    try:
                        os.unlink(chunk_file)
                    except:
                        pass
            raise DownloadError(f"Failed to merge chunks: {e}")
        
        with self._lock:
            self.download_tasks[task_id]["downloaded"] = total_size
            self.download_tasks[task_id]["progress"] = 1.0
            self.download_tasks[task_id]["speed"] = 0
    
    def _download_chunk(self, url: str, output_path: str, start: int, end: int, task_id: str, timeout: int = 3600):
        """Download a single chunk"""
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            self.curl_path,
            "-L",
            "-o", output_path,
            "-r", f"{start}-{end}",
            url
        ]
        
        returncode, stderr = self._run_curl_command(cmd, timeout, task_id)
        if returncode != 0:
            raise DownloadError(f"Chunk download failed: {stderr.strip() or 'Unknown error'}")
    
    def _download_with_requests(
        self,
        url: str,
        output_path: str,
        progress_callback: Callable[[float, int, int], None] | None
    ) -> str:
        """使用requests作为备选下载方法"""
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self.download_tasks[task_id] = {
                "status": "fetching",
                "progress": 0.0,
                "downloaded": 0,
                "total": 0,
                "speed": 0,
                "url": url,
                "output_path": output_path
            }
        
        def _download():
            try:
                # URL获取阶段
                with self._lock:
                    self.download_tasks[task_id]["status"] = "fetching"
                
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # URL获取完成，切换到下载状态
                with self._lock:
                    self.download_tasks[task_id]["status"] = "downloading"
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                downloaded = 0
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            with self._lock:
                                self.download_tasks[task_id]["downloaded"] = downloaded
                                self.download_tasks[task_id]["total"] = total_size
                                if total_size > 0:
                                    self.download_tasks[task_id]["progress"] = downloaded / total_size
                            
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded / total_size, downloaded, total_size)
                
                with self._lock:
                    self.download_tasks[task_id]["status"] = "completed"
                    self.download_tasks[task_id]["progress"] = 1.0
                    
            except Exception as e:
                with self._lock:
                    self.download_tasks[task_id]["status"] = "failed"
                    self.download_tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        
        return task_id
    
    def get_download_progress(self, task_id: str) -> dict[str, Any]:
        """获取下载进度"""
        with self._lock:
            task = self.download_tasks.get(task_id)
            if not task:
                return {"error": "Task does not exist"}
            return {
                "status": task["status"],
                "progress": task["progress"],
                "downloaded": task["downloaded"],
                "total": task["total"],
                "speed": task.get("speed", 0),
                "error": task.get("error")
            }
    
    def _get_tracker_list(self) -> list:
        """
        获取tracker列表
        
        Returns:
            tracker URL列表
        """
        try:
            # 从GitHub获取tracker列表
            tracker_url = "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt"
            response = requests.get(tracker_url, timeout=10)
            response.raise_for_status()
            
            # 解析tracker列表
            trackers = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    trackers.append(line)
            
            logger.info(f"Retrieved {len(trackers)} trackers")
            return trackers
        except Exception as e:
            logger.warning(f"Failed to get tracker list: {e}, using default trackers")
            # 返回一些常用的默认tracker
            return [
                "udp://tracker.opentrackr.org:1337/announce",
                "udp://open.demonii.com:1337/announce",
                "udp://open.stealth.si:80/announce",
                "udp://tracker.torrent.eu.org:451/announce",
                "udp://tracker.coppersurfer.tk:6969/announce",
            ]
    
    def _create_optimized_session(self):
        """
        创建并优化libtorrent session配置
        
        Returns:
            优化后的libtorrent session对象
        """
        import libtorrent as lt
        
        # 创建session
        ses = lt.session()
        
        # 获取当前设置
        settings = ses.get_settings()
        
        # 启用并加强peer发现机制
        settings['enable_dht'] = True
        settings['enable_lsd'] = True  # Local Service Discovery
        settings['enable_upnp'] = True  # UPnP端口映射
        settings['enable_natpmp'] = True  # NAT-PMP端口映射
        
        # 提高连接aggressiveness
        settings['connections_limit'] = 500  # 增加最大连接数（默认200）
        settings['unchoke_slots_limit'] = 8  # 增加同时上传的peer数（默认8）
        settings['torrent_connect_boost'] = 50  # 新torrent的连接boost
        
        # 优化DHT设置
        settings['dht_announce_interval'] = 15  # DHT announce间隔（分钟）
        settings['dht_max_dht_items'] = 700  # DHT最大项目数
        settings['dht_max_peers'] = 500  # DHT最大peer数
        settings['dht_max_torrents'] = 2000  # DHT最大torrent数
        
        # 优化下载策略
        settings['active_downloads'] = 3  # 同时活跃下载数
        settings['active_seeds'] = 3  # 同时活跃做种数
        settings['active_limit'] = 15  # 总活跃数
        
        # 调整上传/下载速度限制（0表示无限制）
        settings['upload_rate_limit'] = 0
        settings['download_rate_limit'] = 0
        
        # 优化连接策略
        settings['connection_speed'] = 30  # 连接速度
        settings['num_want'] = 200  # 请求的peer数（默认50）
        settings['max_peerlist_size'] = 5000  # 最大peer列表大小
        
        # 启用uTP和TCP
        settings['enable_incoming_utp'] = True
        settings['enable_outgoing_utp'] = True
        settings['enable_incoming_tcp'] = True
        settings['enable_outgoing_tcp'] = True
        
        # 应用设置
        try:
            ses.apply_settings(settings)
        except Exception as e:
            logger.warning(f"Failed to apply some settings: {e}, continuing with default settings")
        
        # 监听端口
        ses.listen_on(6881, 6891)
        
        # 启动DHT
        try:
            ses.start_dht()
            # 添加DHT bootstrap节点
            ses.add_dht_node(('dht.libtorrent.org', 25401))
            ses.add_dht_node(('router.bittorrent.com', 6881))
            ses.add_dht_node(('router.utorrent.com', 6881))
            ses.add_dht_node(('dht.transmissionbt.com', 6881))
            logger.debug("DHT started")
        except Exception as e:
            logger.warning(f"DHT startup failed: {e}")
        
        # 启动LSD
        try:
            ses.start_lsd()
            logger.debug("LSD started")
        except Exception as e:
            logger.warning(f"LSD startup failed: {e}")
        
        # 启动UPnP和NAT-PMP
        try:
            ses.start_upnp()
            ses.start_natpmp()
            logger.debug("UPnP/NAT-PMP started")
        except Exception as e:
            logger.warning(f"UPnP/NAT-PMP startup failed: {e}")
        
        return ses
    
    def _add_trackers_to_handle(self, handle, trackers: list):
        """
        添加tracker到torrent handle
        
        Args:
            handle: libtorrent torrent handle
            trackers: tracker URL列表
        """
        try:
            for tracker_url in trackers:
                try:
                    handle.add_tracker({'url': tracker_url, 'tier': 0})
                except Exception as e:
                    # 某些tracker可能无效，继续添加其他的
                    continue
            logger.debug(f"Added {len(trackers)} trackers")
        except Exception as e:
            logger.warning(f"Failed to add trackers: {e}")
    
    def test_bt_latency(self, torrent_path: str, timeout: int | None = None) -> float:
        """
        测试BT网络延迟（通过tracker）
        
        Args:
            torrent_path: torrent文件路径或磁力链接
            timeout: 超时时间（秒），None表示不设置超时限制
        
        Returns:
            延迟时间（毫秒），失败返回-1
        """
        try:
            import libtorrent as lt
            
            # 创建优化的session
            ses = self._create_optimized_session()
            
            # 获取tracker列表
            trackers = self._get_tracker_list()
            
            # 解析torrent或磁力链接
            if torrent_path.startswith('magnet:'):
                # 磁力链接
                save_path = os.path.dirname(os.path.abspath('.')) or '.'
                params = {
                    'save_path': save_path,
                    'storage_mode': lt.storage_mode_t(2),
                }
                handle = lt.add_magnet_uri(ses, torrent_path, params)
            else:
                # torrent文件
                info = lt.torrent_info(torrent_path)
                save_path = os.path.dirname(os.path.abspath('.')) or '.'
                handle = ses.add_torrent(info, save_path)
            
            # 添加tracker
            self._add_trackers_to_handle(handle, trackers)
            
            # 等待元数据
            start_time = time.time()
            last_print_time = start_time
            while not handle.has_metadata():
                current_time = time.time()
                if current_time - last_print_time >= 5.0:
                    logger.debug(f"Waiting for BT metadata... ({current_time - start_time:.1f}s)")
                    last_print_time = current_time
                if timeout is not None and current_time - start_time > timeout:
                    logger.warning("BT metadata retrieval timeout")
                    ses.remove_torrent(handle)
                    return -1
                time.sleep(0.1)
            
            # 获取tracker信息并测试延迟
            trackers = handle.trackers()
            if not trackers:
                return -1
            
            # 测试第一个tracker的延迟
            first_tracker = trackers[0]
            # 注意：libtorrent不直接提供tracker延迟，这里使用连接建立时间作为近似
            latency = (time.time() - start_time) * 1000
            
            ses.remove_torrent(handle)
            return latency
            
        except ImportError:
            logger.warning("libtorrent not available")
            return -1
        except Exception as e:
            logger.error(f"BT latency test failed: {e}")
            return -1
    
    def test_bt_download_speed(
        self,
        torrent_path: str,
        test_size: int = 100 * 1024 * 1024,
        timeout: int | None = None,
        cancel_check: Callable[[], bool] | None = None
    ) -> dict[str, Any]:
        """
        测试BT下载速度（下载指定大小，不完整下载）
        
        Args:
            torrent_path: torrent文件路径或磁力链接
            test_size: 测试下载大小（字节），默认100MB
            timeout: 超时时间（秒），None表示不设置超时限制
        
        Returns:
            {"speed": 速度(字节/秒), "latency": 延迟(毫秒), "peers": 节点数, "seeds": 种子数}
        """
        try:
            import libtorrent as lt
            
            # 创建优化的session
            ses = self._create_optimized_session()
            
            # 获取tracker列表
            trackers = self._get_tracker_list()
            
            # 解析torrent或磁力链接
            # 使用统一的临时目录
            temp_dir = str(self.temp_dir / 'bt_test')
            os.makedirs(temp_dir, exist_ok=True)
            
            if torrent_path.startswith('magnet:'):
                # 磁力链接
                params = {
                    'save_path': temp_dir,
                    'storage_mode': lt.storage_mode_t(2),
                }
                handle = lt.add_magnet_uri(ses, torrent_path, params)
            else:
                # torrent文件
                info = lt.torrent_info(torrent_path)
                handle = ses.add_torrent(info, temp_dir)
            
            # 添加tracker
            self._add_trackers_to_handle(handle, trackers)
            
            # 等待元数据
            start_time = time.time()
            last_print_time = start_time
            logger.info("Retrieving BT metadata...")
            while not handle.has_metadata():
                # 检查取消标志
                if cancel_check and cancel_check():
                    logger.info("BT test cancelled during metadata retrieval")
                    ses.remove_torrent(handle)
                    return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
                
                current_time = time.time()
                if current_time - last_print_time >= 5.0:
                    logger.debug(f"Waiting for BT metadata... ({current_time - start_time:.1f}s)")
                    last_print_time = current_time
                if timeout is not None and current_time - start_time > timeout:
                    logger.warning("BT metadata retrieval timeout")
                    ses.remove_torrent(handle)
                    return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
                time.sleep(0.1)
            
            logger.info(f"BT metadata retrieval successful, elapsed: {time.time() - start_time:.1f}s")
            
            # 获取文件信息
            info = handle.get_torrent_info()
            files = info.files()
            
            # 选择第一个文件进行下载测试
            if files.num_files() == 0:
                ses.remove_torrent(handle)
                return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
            
            # 设置优先级，只下载第一个文件的前test_size字节
            file_index = 0
            file_size = files.file_size(file_index)
            test_pieces = min(test_size, file_size) // info.piece_length() + 1
            
            # 设置文件优先级
            file_priorities = [0] * files.num_files()
            file_priorities[file_index] = 1
            handle.prioritize_files(file_priorities)
            
            # 设置piece优先级（只下载前test_pieces个pieces）
            piece_priorities = [0] * info.num_pieces()
            for i in range(min(test_pieces, info.num_pieces())):
                piece_priorities[i] = 1
            handle.prioritize_pieces(piece_priorities)
            
            # 开始下载并监控速度
            download_start = time.time()
            last_downloaded = 0
            last_time = download_start
            speed_samples = []
            peers = 0
            seeds = 0
            last_status_time = download_start
            
            logger.info(f"Starting BT download test, target size: {test_size / 1024 / 1024:.2f} MB")
            
            while True:
                # 检查取消标志
                if cancel_check and cancel_check():
                    logger.info("BT test cancelled during download")
                    ses.remove_torrent(handle)
                    return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
                
                status = handle.status()
                downloaded = status.total_download
                peers = status.num_peers
                seeds = status.num_seeds
                
                # 每5秒输出一次状态
                current_time = time.time()
                if current_time - last_status_time >= 5.0:
                    logger.debug(f"BT download status: {downloaded / 1024 / 1024:.2f} MB / {test_size / 1024 / 1024:.2f} MB, "
                          f"peers: {peers}, seeds: {seeds}, progress: {status.progress * 100:.1f}%")
                    last_status_time = current_time
                
                elapsed = current_time - download_start
                
                # 计算当前速度
                if current_time - last_time >= 1.0:  # 每秒计算一次速度
                    if downloaded > last_downloaded:
                        current_speed = (downloaded - last_downloaded) / (current_time - last_time)
                        if current_speed > 0:
                            speed_samples.append(current_speed)
                    last_downloaded = downloaded
                    last_time = current_time
                
                # 如果下载了足够的数据或超时，停止
                if downloaded >= test_size:
                    logger.info(f"Downloaded sufficient data: {downloaded / 1024 / 1024:.2f} MB")
                    break
                
                if timeout is not None and elapsed > timeout:
                    logger.warning(f"BT download test timeout: {elapsed:.1f}s")
                    break
                
                # 如果已完成，停止
                if status.progress >= 1.0:
                    logger.info("BT download completed")
                    break
                
                time.sleep(0.5)
            
            total_time = time.time() - download_start
            avg_speed = downloaded / total_time if total_time > 0 and downloaded > 0 else 0
            
            # 清理
            ses.remove_torrent(handle)
            
            # 清理临时文件
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            # 测试延迟（不设置超时限制）
            latency = self.test_bt_latency(torrent_path, timeout=None)
            
            return {
                "speed": avg_speed,
                "latency": latency,
                "peers": peers,
                "seeds": seeds,
                "downloaded": downloaded
            }
            
        except ImportError:
            logger.warning("libtorrent not available")
            return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
        except Exception as e:
            logger.error(f"BT download speed test failed: {e}")
            import traceback
            traceback.print_exc()
            return {"speed": -1, "latency": -1, "peers": 0, "seeds": 0}
    
    def download_bt(
        self,
        torrent_path: str,
        output_path: str,
        progress_callback: Callable[[float, int, int], None] | None = None
    ) -> str:
        """
        使用libtorrent进行BT下载
        
        Args:
            torrent_path: torrent文件路径或磁力链接
            output_path: 输出文件路径（目录）
            progress_callback: 进度回调函数 (progress, downloaded, total)
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        try:
            import libtorrent as lt
        except ImportError:
            with self._lock:
                self.download_tasks[task_id] = {
                    "status": "failed",
                    "error": "libtorrent library not installed, please install: pip install libtorrent python-libtorrent-bin"
                }
            return task_id
        
        # 创建任务记录
        with self._lock:
            self.download_tasks[task_id] = {
                "status": "fetching",
                "progress": 0.0,
                "downloaded": 0,
                "total": 0,
                "speed": 0,
                "url": torrent_path,
                "output_path": output_path
            }
        
        # 在后台线程中执行下载
        def _download():
            try:
                import libtorrent as lt
                
                # 创建优化的session
                ses = self._create_optimized_session()
                
                # 获取tracker列表
                trackers = self._get_tracker_list()
                
                # 解析torrent或磁力链接（fetching阶段：获取magnet/torrent元数据）
                if torrent_path.startswith('magnet:'):
                    params = {
                        'save_path': output_path,
                        'storage_mode': lt.storage_mode_t(2),
                    }
                    handle = lt.add_magnet_uri(ses, torrent_path, params)
                else:
                    info = lt.torrent_info(torrent_path)
                    handle = ses.add_torrent(info, output_path)
                
                # 添加tracker
                self._add_trackers_to_handle(handle, trackers)
                
                # 等待元数据（fetching阶段）
                while not handle.has_metadata():
                    time.sleep(0.1)
                
                # 获取元数据完成，切换到下载状态
                with self._lock:
                    self.download_tasks[task_id]["status"] = "downloading"
                
                # 获取总大小
                info = handle.get_torrent_info()
                total_size = info.total_size()
                
                with self._lock:
                    self.download_tasks[task_id]["total"] = total_size
                
                # 下载循环
                while True:
                    status = handle.status()
                    
                    with self._lock:
                        self.download_tasks[task_id]["progress"] = status.progress
                        self.download_tasks[task_id]["downloaded"] = status.total_download
                        self.download_tasks[task_id]["speed"] = status.download_rate
                    
                    if progress_callback:
                        progress_callback(status.progress, status.total_download, total_size)
                    
                    # 检查是否完成
                    if status.state == lt.torrent_status.seeding or status.progress >= 1.0:
                        with self._lock:
                            self.download_tasks[task_id]["status"] = "completed"
                            self.download_tasks[task_id]["progress"] = 1.0
                        break
                    
                    # 检查是否失败
                    if status.state == lt.torrent_status.downloading and status.paused:
                        with self._lock:
                            self.download_tasks[task_id]["status"] = "failed"
                            self.download_tasks[task_id]["error"] = "Download paused"
                        break
                    
                    time.sleep(0.5)
                
                ses.remove_torrent(handle)
                
            except Exception as e:
                with self._lock:
                    self.download_tasks[task_id]["status"] = "failed"
                    self.download_tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        
        return task_id


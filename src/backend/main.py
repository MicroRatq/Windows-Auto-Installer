"""
后端主入口 - IPC服务器
通过stdin/stdout与Electron前端通信
"""
import json
import sys
import traceback
from typing import Dict, Any, Optional


class IPCError(Exception):
    """IPC通信错误"""
    pass


class BackendServer:
    """后端服务器，处理来自前端的IPC请求"""
    
    def __init__(self):
        self.running = True
        self.handlers = {}
    
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
            print(json_str, flush=True)
        except Exception as e:
            # 如果响应本身失败，至少尝试发送错误信息
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32700,
                    "message": f"响应序列化失败: {str(e)}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)
    
    def handle_request(self, request: Dict[str, Any]):
        """处理单个请求"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not request_id:
            self.send_response(None, error="缺少请求ID")
            return
        
        if not method:
            self.send_response(request_id, error="缺少方法名")
            return
        
        # 查找处理器
        handler = self.handlers.get(method)
        if not handler:
            self.send_response(request_id, error=f"未知方法: {method}")
            return
        
        # 执行处理器
        try:
            result = handler(params)
            self.send_response(request_id, result=result)
        except Exception as e:
            error_msg = f"{method}执行失败: {str(e)}"
            self.send_response(request_id, error=error_msg)
    
    def run(self):
        """运行服务器主循环"""
        # 注册基础处理器
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_platform", self._handle_get_platform)
        
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
                self.send_response(None, error=f"JSON解析失败: {str(e)}")
            except Exception as e:
                self.send_response(None, error=f"请求处理失败: {str(e)}")
    
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
                "message": f"服务器内部错误: {str(e)}"
            }
        }
        print(json.dumps(error_response, ensure_ascii=False), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


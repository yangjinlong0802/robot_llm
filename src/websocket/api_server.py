"""
外部访问接口服务器
提供 HTTP 和 WebSocket 两种方式从外部调用 AI 助手

HTTP 用法:
    POST http://localhost:8765/api/process_input
    Content-Type: application/json
    {"text": "帮我抓一个瓶子"}

    GET http://localhost:8765/api/status

WebSocket 用法 (需安装 websockets: pip install websockets):
    本程序作为客户端连接到 ws://localhost:8005/robot/ws
    接收来自服务端的指令: {"action": "process_input", "text": "帮我抓一个瓶子"}
    向服务端推送状态:    {"event": "status_changed", "status": "分析中..."}
                        {"event": "preview_ready", "step_count": 3}
                        {"event": "execution_finished", "success": true, "message": "执行成功"}
                        {"event": "error", "message": "..."}
"""

import asyncio
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class _APIBridge(QObject):
    """线程安全的 Qt 信号桥接器，将来自外部线程的调用安全转发到 Qt 主线程"""
    input_requested = pyqtSignal(str)


class ExternalAPIServer:
    """
    外部访问接口服务器

    - HTTP: 监听本地端口，接受 POST 请求触发 process_input
    - WebSocket: 作为客户端连接到指定服务端，接收指令并上报状态
    """

    def __init__(
        self,
        ai_assistant_widget,
        host: str = "0.0.0.0",
        http_port: int = 8765,
        ws_url: str = "ws://localhost:8005/robot/ws",
    ):
        self._widget = ai_assistant_widget
        self._host = host
        self._http_port = http_port
        self._ws_url = ws_url
        self._http_server: Optional[HTTPServer] = None
        self._ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_connection = None   # 当前活跃的 WS 连接对象

        # 桥接器必须在 Qt 主线程中创建
        self._bridge = _APIBridge()
        ctrl = ai_assistant_widget.ai_controller
        self._bridge.input_requested.connect(ctrl.process_input)

        # 监听 AI 控制器信号，向 WS 服务端推送状态
        ctrl.status_changed.connect(
            lambda s: self._send_ws({"event": "status_changed", "status": s})
        )
        ctrl.preview_ready.connect(
            lambda items, info: self._send_ws({
                "event": "preview_ready",
                "step_count": len(items),
                "skill_name": info.get("name", ""),
            })
        )
        ctrl.execution_finished.connect(
            lambda ok, msg: self._send_ws({
                "event": "execution_finished",
                "success": ok,
                "message": msg,
            })
        )
        ctrl.error_occurred.connect(
            lambda err: self._send_ws({"event": "error", "message": err})
        )

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def start(self, http: bool = True, ws: bool = True) -> None:
        """启动服务（在 Qt app.exec() 之前调用）"""
        if http:
            self.start_http_server()
        if ws:
            self.start_ws_client()

    def stop(self) -> None:
        """停止服务"""
        if self._http_server:
            self._http_server.shutdown()
            logger.info("HTTP 服务器已停止")
        if self._ws_loop:
            self._ws_loop.call_soon_threadsafe(self._ws_loop.stop)
            logger.info("WebSocket 客户端已停止")

    # ------------------------------------------------------------------
    # HTTP 服务器
    # ------------------------------------------------------------------

    def start_http_server(self) -> None:
        """在后台线程启动 HTTP 服务器（使用标准库，零额外依赖）"""
        server_ref = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/api/process_input":
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        self._json(400, {"error": "invalid JSON"})
                        return

                    text = data.get("text", "").strip()
                    if not text:
                        self._json(400, {"error": "'text' field is required"})
                        return

                    server_ref._bridge.input_requested.emit(text)
                    self._json(200, {"status": "accepted", "message": "处理中"})
                else:
                    self._json(404, {"error": "not found"})

            def do_GET(self):
                if self.path == "/api/status":
                    ctrl = server_ref._widget.ai_controller
                    self._json(200, {
                        "llm_available": ctrl.is_llm_available(),
                        "api_key_set": ctrl.is_api_key_set(),
                        "model": ctrl.get_llm_model_name(),
                        "provider": ctrl.get_model_provider(),
                    })
                else:
                    self._json(404, {"error": "not found"})

            def _json(self, code: int, data: dict) -> None:
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                logger.debug("HTTP %s", fmt % args)

        self._http_server = HTTPServer((self._host, self._http_port), _Handler)
        thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True, name="APIServer-HTTP"
        )
        thread.start()
        logger.info("HTTP 接口已启动: http://%s:%d", self._host, self._http_port)

    # ------------------------------------------------------------------
    # WebSocket 客户端
    # ------------------------------------------------------------------

    def start_ws_client(self) -> None:
        """在后台线程启动 WebSocket 客户端，连接到 ws_url，断线自动重连"""
        try:
            import websockets  # noqa: F401
        except ImportError:
            logger.warning(
                "websockets 库未安装，WebSocket 客户端不可用。"
                "可通过 'pip install websockets' 安装。"
            )
            return

        server_ref = self

        async def _run_client():
            import websockets

            retry_delay = 1  # 初始重连间隔（秒）

            while True:
                try:
                    async with websockets.connect(server_ref._ws_url) as ws:
                        server_ref._ws_connection = ws
                        retry_delay = 1  # 连接成功后重置
                        logger.info("WebSocket 已连接: %s", server_ref._ws_url)

                        async for raw in ws:
                            try:
                                data = json.loads(raw)
                            except json.JSONDecodeError:
                                await ws.send(json.dumps(
                                    {"event": "error", "message": "invalid JSON"},
                                    ensure_ascii=False,
                                ))
                                continue

                            instruction = data.get("Instruction", "").strip()
                            print(instruction)
                            if instruction:
                                server_ref._bridge.input_requested.emit(instruction)
                                await ws.send(json.dumps(
                                    {"event": "accepted", "message": "处理中"},
                                    ensure_ascii=False,
                                ))
                            else:
                                await ws.send(json.dumps(
                                    {"event": "error", "message": "'Instruction' field is required"},
                                    ensure_ascii=False,
                                ))

                except Exception as e:
                    server_ref._ws_connection = None
                    logger.warning(
                        "WebSocket 连接断开 (%s)，%ds 后重连...", e, retry_delay
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)  # 指数退避，最长 30s

        def _thread_main():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server_ref._ws_loop = loop
            loop.run_until_complete(_run_client())

        thread = threading.Thread(target=_thread_main, daemon=True, name="APIServer-WS")
        thread.start()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _send_ws(self, data: dict) -> None:
        """从任意线程向 WS 服务端发送消息（连接不存在时静默忽略）"""
        if self._ws_loop is None or self._ws_connection is None:
            return
        msg = json.dumps(data, ensure_ascii=False)

        async def _do_send():
            try:
                await self._ws_connection.send(msg)
            except Exception as e:
                logger.debug("WS 发送失败: %s", e)

        asyncio.run_coroutine_threadsafe(_do_send(), self._ws_loop)


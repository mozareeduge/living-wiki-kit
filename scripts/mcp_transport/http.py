"""MCP Streamable HTTP transport: endpoint /mcp and liveness check /healthz."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


class McpHttpRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler implementing MCP Streamable HTTP and /healthz."""

    handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None]
    profile_provider: Callable[[], str]

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Mcp-Session-Id, Accept")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_HEAD(self) -> None:
        path = self.path.split("?")[0]
        if path == "/healthz":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._set_cors_headers()
            self.end_headers()
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/healthz":
            payload = json.dumps({"status": "ok", "service": "wiki-governance"}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(payload)
        elif path == "/mcp":
            accept = self.headers.get("Accept", "")
            if "text/event-stream" in accept:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b": ping\n\n")
            else:
                self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
                self.send_header("Allow", "POST, OPTIONS")
                self._set_cors_headers()
                self.end_headers()
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path != "/mcp":
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            msg = json.loads(raw)
        except Exception:  # noqa: BLE001
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            return

        resp = self.handle_fn(msg, "http")
        if resp is None:
            self.send_response(HTTPStatus.ACCEPTED)
            self._set_cors_headers()
            self.end_headers()
            return

        accept = self.headers.get("Accept", "")
        if "text/event-stream" in accept:
            body = f"event: message\ndata: {json.dumps(resp, ensure_ascii=False)}\n\n".encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        else:
            body = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard logging during normal operation
        pass


def create_mcp_http_server(
    host: str,
    port: int,
    handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None],
    profile_provider: Callable[[], str],
) -> ThreadingHTTPServer:
    handler_class = type(
        "ConfiguredMcpHttpRequestHandler",
        (McpHttpRequestHandler,),
        {"handle_fn": staticmethod(handle_fn), "profile_provider": staticmethod(profile_provider)},
    )
    return ThreadingHTTPServer((host, port), handler_class)


class HttpTransport:
    """Streamable HTTP transport running on ThreadingHTTPServer."""

    def __init__(
        self,
        handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None],
        profile_provider: Callable[[], str],
        host: str = "127.0.0.1",
        port: int = 8787,
    ) -> None:
        self.server = create_mcp_http_server(host, port, handle_fn, profile_provider)

    def run(self) -> int:
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.server_close()
        return 0


def run_http(
    handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None],
    profile_provider: Callable[[], str],
    host: str = "127.0.0.1",
    port: int = 8787,
) -> int:
    transport = HttpTransport(handle_fn, profile_provider, host=host, port=port)
    return transport.run()

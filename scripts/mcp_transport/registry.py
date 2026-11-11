"""Transport-agnostic MCP tool registry and JSON-RPC dispatch."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[[dict[str, Any]], str]
    profile: str = "read"
    is_write: bool = False

    def to_mcp_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class ToolRegistry:
    """Registry holding tool declarations and transport-agnostic message dispatch."""

    def __init__(self, server_name: str = "wiki-governance", server_version: str = "2.0.0") -> None:
        self.server_name = server_name
        self.server_version = server_version
        self._tools: dict[str, ToolDefinition] = {}
        self._aliases: dict[str, str] = {}
        # Set only by `--insecure-local-only` (loopback bind); default keeps writes refused over HTTP.
        self.http_writes_allowed = False

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def register_alias(self, alias_name: str, target_name: str) -> None:
        self._aliases[alias_name] = target_name

    def get_tool(self, name: str) -> ToolDefinition | None:
        resolved = self._aliases.get(name, name)
        return self._tools.get(resolved)

    def advertised_tools(self, profile: str = "read") -> list[dict[str, Any]]:
        # In read profile, only read-profile tools are advertised.
        # In capture profile, read and capture tools are advertised.
        allowed_profiles = {"read"} if profile == "read" else {"read", "capture"}
        return [
            tool.to_mcp_dict()
            for tool in self._tools.values()
            if tool.profile in allowed_profiles
        ]

    def handle(
        self,
        msg: dict[str, Any],
        profile: str = "read",
        transport: str = "stdio",
    ) -> dict[str, Any] | None:
        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.server_name, "version": self.server_version},
                },
            }

        if method is None or str(method).startswith("notifications/"):
            return None

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.advertised_tools(profile)},
            }

        if method == "tools/call":
            params = msg.get("params") or {}
            name = str(params.get("name") or "")
            allowed_names = {t["name"] for t in self.advertised_tools(profile)}
            if name not in allowed_names and self._aliases.get(name) not in allowed_names:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": f"tool not enabled in {profile!r} profile: {name}",
                    },
                }

            tool = self.get_tool(name)
            if tool is None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": f"unknown tool: {name}"},
                }

            # Enforce write authentication gate over HTTP transport until auth exists (H3)
            if transport == "http" and tool.is_write and not self.http_writes_allowed:
                err_payload = json.dumps({
                    "ok": False,
                    "code": "E_AUTH_REQUIRED",
                    "error": "E_AUTH_REQUIRED",
                    "message": "Authentication required for write operations over HTTP",
                })
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": err_payload}],
                        "isError": True,
                    },
                }

            try:
                text = tool.fn(params.get("arguments") or {})
                is_error = False
            except Exception as exc:  # noqa: BLE001
                text = json.dumps({"error": f"{type(exc).__name__}: {exc}"})
                is_error = True

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}], "isError": is_error},
            }

        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }

        return None

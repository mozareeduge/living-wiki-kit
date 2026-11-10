"""Stdio transport implementation for Living Wiki MCP server."""
from __future__ import annotations

import json
import sys
from typing import Any, Callable


class StdioTransport:
    """Stdio line-oriented JSON-RPC transport."""

    def __init__(self, handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None]) -> None:
        self.handle_fn = handle_fn

    def run(self) -> int:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = self.handle_fn(msg, "stdio")
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        return 0


def run_stdio(handle_fn: Callable[[dict[str, Any], str], dict[str, Any] | None]) -> int:
    transport = StdioTransport(handle_fn)
    return transport.run()

"""The MCP server must speak UTF-8 on stdio whatever the host's locale.

On Windows a piped stdout defaults to the locale code page (cp1252), so the
first reply containing Persian text raised UnicodeEncodeError and killed the
server (found on mozare-wiki 2026-09-24). Forcing a cp1252 locale
reproduces that on any OS.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSIAN = "بوف_کور"


def test_non_ascii_request_and_reply_survive_a_cp1252_locale():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
           "params": {"name": PERSIAN, "arguments": {}}}
    proc = subprocess.run(
        [sys.executable, "scripts/wiki_mcp_server.py"], cwd=ROOT, env=env,
        input=(json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"),
        capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    resp = json.loads(proc.stdout.decode("utf-8").splitlines()[0])
    assert PERSIAN in json.dumps(resp, ensure_ascii=False)

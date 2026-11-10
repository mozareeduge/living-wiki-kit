"""Rung H1: transport split golden tests (stdio vs HTTP) and /healthz.

Invariants verified:
- Same tools/list and same results over stdio and HTTP (golden test).
- /healthz returns 200 OK and no corpus data.
- Streamable HTTP protocol at /mcp (application/json and text/event-stream).
- HTTP server is read-profile only by default.
- In write-capable profile over HTTP, write tools refuse with E_AUTH_REQUIRED.
- Stdio transport remains 100% backward-compatible.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wiki_mcp_server as srv  # noqa: E402


def _rpc_stdio(method: str, params: dict | None = None, profile: str = "read", msg_id: int = 1) -> dict:
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    orig_profile = srv.ACTIVE_PROFILE
    try:
        srv.ACTIVE_PROFILE = profile
        return srv.handle(msg, transport="stdio")
    finally:
        srv.ACTIVE_PROFILE = orig_profile


def _post_http(url: str, payload: dict, accept: str = "application/json") -> tuple[int, dict | str, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": accept},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            if "application/json" in headers.get("Content-Type", ""):
                return status, json.loads(body), headers
            return status, body, headers
    except urllib.error.HTTPError as err:
        headers = dict(err.headers)
        body = err.read().decode("utf-8")
        try:
            return err.code, json.loads(body), headers
        except Exception:
            return err.code, body, headers


def _get_http(url: str) -> tuple[int, dict | str, dict]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            try:
                return status, json.loads(body), headers
            except Exception:
                return status, body, headers
    except urllib.error.HTTPError as err:
        headers = dict(err.headers)
        body = err.read().decode("utf-8")
        try:
            return err.code, json.loads(body), headers
        except Exception:
            return err.code, body, headers


@pytest.fixture()
def http_server():
    """Start an ephemeral HTTP transport server pointed at the repo ROOT."""
    from mcp_transport.http import create_mcp_http_server

    server = create_mcp_http_server(
        host="127.0.0.1",
        port=0,
        handle_fn=lambda msg, transport="http": srv.handle(msg, transport=transport),
        profile_provider=lambda: srv.ACTIVE_PROFILE,
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    base_url = f"http://127.0.0.1:{port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_h1_golden_tools_list_stdio_vs_http(http_server):
    """tools/list must return the exact same tools over stdio and HTTP in read profile."""
    stdio_res = _rpc_stdio("tools/list", profile="read")
    status, http_res, headers = _post_http(f"{http_server}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert status == 200
    assert "application/json" in headers.get("Content-Type", "")
    assert http_res["result"]["tools"] == stdio_res["result"]["tools"]


def test_h1_golden_tool_results_stdio_vs_http(http_server):
    """Tool execution results must match across stdio and HTTP."""
    # 1. wiki_state
    stdio_state = _rpc_stdio("tools/call", {"name": "wiki_state", "arguments": {}}, profile="read", msg_id=2)
    status, http_state, _ = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wiki_state", "arguments": {}}},
    )
    assert status == 200
    assert http_state == stdio_state

    # 2. wiki_read_text
    args = {"path": "00-system/configuration/qmd-collections-v1.1.0.json"}
    stdio_read = _rpc_stdio("tools/call", {"name": "wiki_read_text", "arguments": args}, profile="read", msg_id=3)
    status, http_read, _ = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wiki_read_text", "arguments": args}},
    )
    assert status == 200
    assert http_read == stdio_read


def test_h1_healthz_endpoint_returns_no_corpus_data(http_server):
    """GET /healthz returns 200 OK and strictly liveness information, with no corpus data."""
    status, body, headers = _get_http(f"{http_server}/healthz")
    assert status == 200
    assert isinstance(body, dict)
    assert body.get("status") == "ok"

    # Invariant: No corpus data leaked in /healthz
    serialized = json.dumps(body).lower()
    for forbidden in ["records", "sources", "claims", "objects", "proposals", "content", "corpus", "03-objects"]:
        assert forbidden not in serialized, f"Corpus data leaked in /healthz: {forbidden}"

    # Also test HEAD /healthz
    req = urllib.request.Request(f"{http_server}/healthz", method="HEAD")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert resp.read() == b""


def test_h1_http_default_read_profile_refuses_unadvertised_tools(http_server):
    """In default read profile, write tools are not enabled."""
    status, res, _ = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "wiki_capture_text", "arguments": {"text": "hello"}}},
    )
    assert status == 200
    assert "error" in res
    assert res["error"]["code"] == -32602
    assert "not enabled in 'read' profile" in res["error"]["message"]


def test_h1_http_capture_profile_refuses_writes_with_e_auth_required(http_server, monkeypatch):
    """When capture profile is enabled on HTTP, write tools refuse with E_AUTH_REQUIRED until auth exists."""
    monkeypatch.setattr(srv, "ACTIVE_PROFILE", "capture")

    # Read capture tools still work
    status, list_res, _ = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "wiki_list_captures", "arguments": {}}},
    )
    assert status == 200
    assert "error" not in list_res

    # Write tools refuse with E_AUTH_REQUIRED
    write_tools_to_check = [
        ("wiki_capture_text", {"text": "hello"}),
        ("wiki_propose", {"kind": "concept-add", "body": "test proposal"}),
        ("wiki_propose_from_capture", {"ids": ["mw-cap-1"], "note": "test note"}),
        ("wiki_mark_capture_reviewed", {"id": "mw-cap-1", "actor": "human"}),
        ("wiki_transcribe_capture", {"id": "mw-cap-1", "text": "transcription"}),
    ]
    for tool_name, args in write_tools_to_check:
        status, resp, _ = _post_http(
            f"{http_server}/mcp",
            {"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": tool_name, "arguments": args}},
        )
        assert status == 200
        raw_text = resp["result"]["content"][0]["text"]
        payload = json.loads(raw_text)
        assert payload.get("code") == "E_AUTH_REQUIRED" or "E_AUTH_REQUIRED" in payload.get("error", "")
        assert resp["result"]["isError"] is True


def test_h1_streamable_http_accept_header(http_server):
    """Streamable HTTP responds with text/event-stream when requested via Accept."""
    # 1. Accept: text/event-stream
    status, body, headers = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "id": 20, "method": "tools/list"},
        accept="text/event-stream",
    )
    assert status == 200
    assert "text/event-stream" in headers.get("Content-Type", "")
    assert body.startswith("event: message\ndata: ")
    # Extract data line and parse JSON
    data_line = [line for line in body.splitlines() if line.startswith("data: ")][0]
    rpc_res = json.loads(data_line[len("data: "):])
    assert "tools" in rpc_res["result"]

    # 2. Notification returns 202 Accepted without body
    status, notif_body, _ = _post_http(
        f"{http_server}/mcp",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert status in (202, 204)


def test_h1_cli_transport_flags():
    """CLI must support --transport (stdio, http) and --bind."""
    proc = subprocess.run(
        [sys.executable, "scripts/wiki_mcp_server.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "--transport" in proc.stdout
    assert "--bind" in proc.stdout


def test_h1_http_cors_and_methods(http_server):
    """OPTIONS and disallowed methods on /mcp and /healthz."""
    # OPTIONS /mcp
    req = urllib.request.Request(f"{http_server}/mcp", method="OPTIONS")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    # GET /mcp without text/event-stream -> 405 Method Not Allowed
    status, body, headers = _get_http(f"{http_server}/mcp")
    assert status == 405
    assert "POST" in headers.get("Allow", "")

    # GET /mcp with text/event-stream -> 200 OK ping
    req = urllib.request.Request(f"{http_server}/mcp", headers={"Accept": "text/event-stream"}, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")

    # 404 for unknown path
    status, _, _ = _get_http(f"{http_server}/nonexistent")
    assert status == 404


def test_h1_http_invalid_json_payload(http_server):
    """Malformed JSON in POST /mcp returns 400 Bad Request."""
    req = urllib.request.Request(
        f"{http_server}/mcp",
        data=b"not a valid json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 400


def test_h1_http_persian_text_transport(http_server):
    """Non-ASCII / Persian text survives round-trip over HTTP transport without corruption."""
    persian_text = "بوف کور"
    payload = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {"name": "wiki_read_text", "arguments": {"path": persian_text}},
    }
    status, res, headers = _post_http(f"{http_server}/mcp", payload)
    assert status == 200
    assert "application/json" in headers.get("Content-Type", "")
    assert res.get("id") == 99
    assert res["result"]["isError"] is False
    content_text = res["result"]["content"][0]["text"]
    assert persian_text in content_text


def test_h1_cli_subprocess_http_mode():
    """Start wiki_mcp_server.py via CLI in HTTP mode and query /healthz."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    proc = subprocess.Popen(
        [sys.executable, "scripts/wiki_mcp_server.py", "--transport", "http", "--bind", f"127.0.0.1:{free_port}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Wait for server to bind
        time.sleep(0.5)
        status, body, _ = _get_http(f"http://127.0.0.1:{free_port}/healthz")
        assert status == 200
        assert body.get("status") == "ok"
    finally:
        proc.terminate()
        proc.wait(timeout=5)

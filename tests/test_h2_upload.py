"""Rung H2: upload page, single-use upload refs, wiki_ingest_file tool.

Proves: ref format, single use, TTL, size cap, extension allowlist, cleanup,
no arbitrary path read from the MCP side, and the fail-closed HTTP gate
(--insecure-local-only + capture profile + loopback bind only).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ingest"
sys.path.insert(0, str(ROOT / "scripts"))

import wiki_mcp_server as srv  # noqa: E402
from upload.store import UploadError, UploadStore  # noqa: E402
from upload.tools import make_ingest_tool  # noqa: E402

REF_RE = re.compile(r"^upl-[A-Za-z0-9_-]{43}$")


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def store(tmp_path: Path):
    clock = Clock()
    return UploadStore(tmp_path, ttl_seconds=100, max_bytes=1024, clock=clock), clock


@pytest.fixture
def clean_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        src = ROOT / rel
        if src.is_file():
            (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, wiki / rel)
    res = subprocess.run([sys.executable, "scripts/instantiate.py", "--name", "Test Wiki", "--prefix", "tst"], cwd=wiki, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    return wiki


def _staged(root: Path, pattern: str) -> list[Path]:
    base = root / "_staging" / "uploads"
    return list(base.rglob(pattern)) if base.exists() else []


# ---- store ----------------------------------------------------------------

def test_ref_format_and_staging_location(store, tmp_path):
    s, _ = store
    out = s.save("note.txt", b"hello")
    assert REF_RE.match(out["upload_ref"])
    staged = _staged(tmp_path, "note.txt")
    assert len(staged) == 1 and staged[0].read_bytes() == b"hello"
    assert out["upload_ref"] != s.save("note.txt", b"hello")["upload_ref"]


def test_ref_is_single_use(store):
    s, _ = store
    ref = s.save("a.txt", b"x")["upload_ref"]
    s.claim(ref).finish()
    with pytest.raises(UploadError) as e:
        s.claim(ref)
    assert e.value.code == "E_UPLOAD_USED"


def test_unknown_and_malformed_refs_fail_cleanly(store):
    s, _ = store
    for bad in ["upl-" + "A" * 43, "", "../../etc/passwd", "upl-../../x", "upl-" + "A" * 42, "C:\\x", None]:
        with pytest.raises(UploadError) as e:
            s.claim(bad)  # type: ignore[arg-type]
        assert e.value.code in {"E_UPLOAD_UNKNOWN", "E_UPLOAD_BAD_REF"}


def test_expired_ref_fails_and_bytes_removed(store, tmp_path):
    s, clock = store
    ref = s.save("a.txt", b"x")["upload_ref"]
    clock.t += 101
    with pytest.raises(UploadError) as e:
        s.claim(ref)
    assert e.value.code == "E_UPLOAD_EXPIRED"
    assert not _staged(tmp_path, "a.txt")


def test_size_cap_and_extension_allowlist(store):
    s, _ = store
    with pytest.raises(UploadError) as e:
        s.save("big.txt", b"x" * 1025)
    assert e.value.code == "E_UPLOAD_TOO_LARGE"
    for name in ["evil.exe", "a.sh", "noext", "a.txt.exe", ".txt"]:
        with pytest.raises(UploadError) as e:
            s.save(name, b"x")
        assert e.value.code == "E_UPLOAD_TYPE"


def test_filename_is_sanitized_no_traversal(store, tmp_path):
    s, _ = store
    s.save("../../../evil name.txt", b"x")
    files = [p for p in (tmp_path / "_staging").rglob("*.txt")]
    assert len(files) == 1
    assert (tmp_path / "_staging" / "uploads") in files[0].parents
    assert ".." not in files[0].name


def test_cleanup_removes_expired_and_tombstones(store, tmp_path):
    s, clock = store
    old = s.save("old.txt", b"x")["upload_ref"]
    used = s.save("used.txt", b"x")["upload_ref"]
    s.claim(used).finish()
    clock.t += 50
    keep = s.save("keep.txt", b"x")["upload_ref"]
    clock.t += 60  # first batch is 110 s old (> ttl 100), keep is 60 s old
    removed = s.cleanup()
    assert removed >= 2
    assert not _staged(tmp_path, "old.txt")
    with pytest.raises(UploadError) as e:
        s.claim(old)
    assert e.value.code == "E_UPLOAD_UNKNOWN"
    s.claim(keep).finish()


def test_release_after_failed_ingest_allows_retry(store):
    s, _ = store
    ref = s.save("a.txt", b"x")["upload_ref"]
    s.claim(ref).release()
    s.claim(ref).finish()


# ---- MCP tool ---------------------------------------------------------------

def _call(tool, **args):
    return json.loads(tool(args))


def test_ingest_tool_happy_path_and_reuse(clean_wiki):
    s = UploadStore(clean_wiki)
    tool = make_ingest_tool(lambda: clean_wiki, lambda: s)
    ref = s.save("sample.txt", (FIXTURES / "sample.txt").read_bytes())["upload_ref"]
    out = _call(tool, upload_ref=ref, request_id="req-h2-0001")
    assert out["ok"] is True and out["source_ref"].startswith("rec:tst-src-")
    again = _call(tool, upload_ref=ref)
    assert again["ok"] is False and again["code"] == "E_UPLOAD_USED"
    assert not _staged(clean_wiki, "sample.txt")


def test_ingest_tool_unknown_expired_and_bad_args(clean_wiki):
    clock = Clock()
    s = UploadStore(clean_wiki, ttl_seconds=10, clock=clock)
    tool = make_ingest_tool(lambda: clean_wiki, lambda: s)
    assert _call(tool, upload_ref="upl-" + "B" * 43)["code"] == "E_UPLOAD_UNKNOWN"
    ref = s.save("sample.txt", b"hi")["upload_ref"]
    clock.t += 11
    assert _call(tool, upload_ref=ref)["code"] == "E_UPLOAD_EXPIRED"
    assert _call(tool)["ok"] is False


def test_ingest_tool_cannot_read_arbitrary_paths(clean_wiki, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("top secret", encoding="utf-8")
    s = UploadStore(clean_wiki)
    tool = make_ingest_tool(lambda: clean_wiki, lambda: s)
    outs = []
    for payload in [
        {"upload_ref": str(secret)},
        {"upload_ref": "../" * 5 + "secret.txt"},
        {"upload_ref": "upl-" + "A" * 43, "path": str(secret)},
        {"upload_ref": "upl-" + "A" * 43, "staged_path": str(secret)},
    ]:
        out = _call(tool, **payload)
        assert out["ok"] is False
        outs.append(out)
    assert "top secret" not in json.dumps(outs)
    originals = clean_wiki / "_originals"
    assert not originals.exists() or not [p for p in originals.rglob("*") if p.is_file()]
    schema = srv.REGISTRY.get_tool("wiki_ingest_file").input_schema
    assert set(schema["properties"]) == {"upload_ref", "title", "description", "request_id"}


def test_ingest_tool_failure_releases_ref(clean_wiki):
    s = UploadStore(clean_wiki)
    seen = []

    def boom(*a, **k):
        seen.append(1)
        from gov_kernel.ingest import IngestError
        raise IngestError("E_UNSUPPORTED_TYPE", "nope")

    tool = make_ingest_tool(lambda: clean_wiki, lambda: s, ingest_fn=boom)
    ref = s.save("a.txt", b"x")["upload_ref"]
    out = _call(tool, upload_ref=ref)
    assert out["ok"] is False and out["code"] == "E_UNSUPPORTED_TYPE"
    s.claim(ref).finish()  # ref still usable after a failed ingest


# ---- registry / gate ----------------------------------------------------------

def test_tool_registered_capture_write_only():
    t = srv.REGISTRY.get_tool("wiki_ingest_file")
    assert t is not None and t.profile == "capture" and t.is_write is True
    assert "wiki_ingest_file" not in {x["name"] for x in srv.REGISTRY.advertised_tools("read")}
    assert "wiki_ingest_file" in {x["name"] for x in srv.REGISTRY.advertised_tools("capture")}


def test_http_refuses_ingest_without_insecure_flag():
    res = srv.REGISTRY.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "wiki_ingest_file", "arguments": {"upload_ref": "x"}}},
        profile="capture", transport="http",
    )
    assert "E_AUTH_REQUIRED" in res["result"]["content"][0]["text"]


# ---- HTTP routes ---------------------------------------------------------------

def _multipart(filename: str, data: bytes):
    b = "----lwkboundary7d1"
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b}"


def _req(url, method="GET", body=None, ctype=None, headers=None):
    h = dict(headers or {})
    if ctype:
        h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


def _serve(tmp_path, profile="capture", insecure=True, max_bytes=2048):
    from mcp_transport.http import create_mcp_http_server
    store = UploadStore(tmp_path, max_bytes=max_bytes)
    server = create_mcp_http_server(
        host="127.0.0.1", port=0,
        handle_fn=lambda msg, transport="http": srv.handle(msg, transport=transport),
        profile_provider=lambda: profile,
        upload_store=store, insecure_local_only=insecure,
    )
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    time.sleep(0.05)
    return server, th, f"http://127.0.0.1:{server.server_address[1]}", store


@pytest.fixture
def upload_server(tmp_path):
    server, th, base, store = _serve(tmp_path)
    try:
        yield base, store, tmp_path
    finally:
        server.shutdown()
        server.server_close()
        th.join(timeout=2)


def test_get_upload_form_and_post_returns_ref(upload_server):
    base, store, _ = upload_server
    code, html, headers = _req(f"{base}/upload")
    assert code == 200 and "text/html" in headers["Content-Type"] and "<form" in html and "multipart/form-data" in html
    body, ct = _multipart("a.txt", b"hello")
    code, out, _h = _req(f"{base}/upload", "POST", body, ct)
    data = json.loads(out)
    assert code == 200 and REF_RE.match(data["upload_ref"])
    assert store.claim(data["upload_ref"]).path.read_bytes() == b"hello"


def test_post_upload_rejects_oversize_and_bad_type(upload_server):
    base, _, _ = upload_server
    body, ct = _multipart("a.txt", b"x" * 5000)
    code, out, _h = _req(f"{base}/upload", "POST", body, ct)
    assert code == 413 and json.loads(out)["code"] == "E_UPLOAD_TOO_LARGE"
    body, ct = _multipart("a.exe", b"x")
    code, out, _h = _req(f"{base}/upload", "POST", body, ct)
    assert code == 415 and json.loads(out)["code"] == "E_UPLOAD_TYPE"
    code, out, _h = _req(f"{base}/upload", "POST", b"not multipart", "text/plain")
    assert code == 400


def test_upload_rejects_foreign_host_header(upload_server):
    base, _, _ = upload_server
    code, _o, _h = _req(f"{base}/upload", headers={"Host": "evil.example.com"})
    assert code == 403


def test_upload_refused_without_flag_or_in_read_profile(tmp_path):
    for profile, insecure in [("capture", False), ("read", True)]:
        server, th, base, _ = _serve(tmp_path, profile=profile, insecure=insecure)
        try:
            assert _req(f"{base}/upload")[0] == 403
            body, ct = _multipart("a.txt", b"x")
            code, out, _h = _req(f"{base}/upload", "POST", body, ct)
            assert code == 403 and json.loads(out)["code"] == "E_UPLOAD_DISABLED"
        finally:
            server.shutdown()
            server.server_close()
            th.join(timeout=2)
    assert not _staged(tmp_path, "*.txt")


def test_insecure_flag_refuses_non_loopback_bind(tmp_path):
    from mcp_transport.http import create_mcp_http_server
    for host in ["0.0.0.0", "192.168.1.5", ""]:
        with pytest.raises(ValueError):
            create_mcp_http_server(host, 0, lambda m, t="http": None, lambda: "capture",
                                   upload_store=UploadStore(tmp_path), insecure_local_only=True)


def test_cli_insecure_flag_requires_capture_and_loopback():
    base = [sys.executable, str(ROOT / "scripts" / "wiki_mcp_server.py"), "--transport", "http", "--insecure-local-only"]
    r = subprocess.run(base + ["--profile", "read"], capture_output=True, text=True, timeout=30)
    assert r.returncode != 0 and "capture" in (r.stderr + r.stdout)
    r = subprocess.run(base + ["--profile", "capture", "--bind", "0.0.0.0:0"], capture_output=True, text=True, timeout=30)
    assert r.returncode != 0 and "127.0.0.1" in (r.stderr + r.stdout)


def test_end_to_end_upload_then_ingest_over_http(clean_wiki):
    """Upload page -> ref -> wiki_ingest_file over /mcp with the insecure flag on."""
    old_root, old_prof = srv.ROOT, srv.ACTIVE_PROFILE
    srv.ROOT = clean_wiki
    srv.ACTIVE_PROFILE = "capture"
    srv.REGISTRY.http_writes_allowed = True
    server, th, base, _ = _serve(clean_wiki, max_bytes=1_000_000)
    try:
        body, ct = _multipart("sample.txt", (FIXTURES / "sample.txt").read_bytes())
        ref = json.loads(_req(f"{base}/upload", "POST", body, ct)[1])["upload_ref"]
        rpc = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "wiki_ingest_file", "arguments": {"upload_ref": ref, "title": "T"}}}
        code, out, _h = _req(f"{base}/mcp", "POST", json.dumps(rpc).encode(), "application/json", {"Accept": "application/json"})
        res = json.loads(json.loads(out)["result"]["content"][0]["text"])
        assert code == 200 and res["ok"] is True
        code, out, _h = _req(f"{base}/mcp", "POST", json.dumps(rpc).encode(), "application/json", {"Accept": "application/json"})
        assert json.loads(json.loads(out)["result"]["content"][0]["text"])["code"] == "E_UPLOAD_USED"
    finally:
        srv.REGISTRY.http_writes_allowed = False
        srv.ROOT, srv.ACTIVE_PROFILE = old_root, old_prof
        server.shutdown()
        server.server_close()
        th.join(timeout=2)

"""Rung H4: remote server runbook, systemd/cloudflared templates and smoke script.

Paper and templates only: nothing here touches a VM, Cloudflare or DNS.
Lints the unit files, checks every path the runbook names exists, and runs
ops/remote/smoke.sh against a local in-process server.
"""
from __future__ import annotations

import configparser
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops" / "remote"
RUNBOOK = ROOT / "RUNBOOK_REMOTE_SERVER.md"
sys.path.insert(0, str(ROOT / "scripts"))

UNITS = ["wiki-mcp.service", "cloudflared.service", "wiki-backup.service", "wiki-backup.timer",
         "wiki-validate.service", "wiki-validate.timer"]
SECRET_KEY = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL)", re.I)


def _unit(name: str) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str  # type: ignore[assignment]
    cp.read_string((OPS / name).read_text(encoding="utf-8"))
    return cp


def _opt(cp: configparser.ConfigParser, section: str, key: str) -> str:
    return " ".join(cp.get(section, key, fallback="").split())


@pytest.mark.parametrize("name", UNITS)
def test_unit_file_exists_and_has_sections(name):
    cp = _unit(name)
    assert "Unit" in cp and "Description" in cp["Unit"]
    kind = name.rsplit(".", 1)[1]
    assert kind.capitalize() in cp
    if kind == "timer":
        assert cp["Timer"].get("OnCalendar") and cp["Timer"].get("Persistent") == "true"
        assert cp["Install"]["WantedBy"] == "timers.target"
        assert (OPS / cp["Timer"]["Unit"]).exists()
    elif name in ("wiki-mcp.service", "cloudflared.service"):
        assert cp["Install"]["WantedBy"] == "multi-user.target"
        assert cp["Service"]["Restart"] in ("always", "on-failure")


def test_mcp_service_is_loopback_capture_without_insecure_flag():
    s = _unit("wiki-mcp.service")["Service"]
    exe = _opt(_unit("wiki-mcp.service"), "Service", "ExecStart")
    assert "--transport http" in exe and "--profile capture" in exe and "--bind 127.0.0.1:8787" in exe
    assert "--insecure-local-only" not in exe and "0.0.0.0" not in exe
    assert s["User"] == "wiki" and s["EnvironmentFile"] == "/etc/@PREFIX@-wiki/env"
    assert s["WorkingDirectory"] == "/srv/@PREFIX@-wiki"
    assert s.get("NoNewPrivileges") == "true" and s.get("ProtectHome") == "true"
    assert exe.split()[0].startswith("/")


def test_insecure_dropin_is_example_only_and_loopback():
    dropin = (OPS / "wiki-mcp-insecure-local-only.conf.example").read_text(encoding="utf-8")
    assert "--insecure-local-only" in dropin and "--bind 127.0.0.1:8787" in dropin
    assert "D-1" in dropin  # names the pending owner decision


def test_cloudflared_points_at_loopback_only():
    cp = _unit("cloudflared.service")
    exe = _opt(cp, "Service", "ExecStart")
    assert "tunnel" in exe and exe.rstrip().endswith("run") and "--token" not in exe
    assert "http://127.0.0.1:8787" in (OPS / "cloudflared.service").read_text(encoding="utf-8")
    assert cp["Service"]["EnvironmentFile"] == "/etc/@PREFIX@-wiki/env"
    cfg = (OPS / "cloudflared-config.yml.example").read_text(encoding="utf-8")
    assert "service: http://127.0.0.1:8787" in cfg and "http_status:404" in cfg.replace(" ", "")


def test_timer_services_run_expected_commands():
    assert "wiki-backup.sh" in _opt(_unit("wiki-backup.service"), "Service", "ExecStart")
    assert _unit("wiki-backup.service")["Service"]["Type"] == "oneshot"
    val = _opt(_unit("wiki-validate.service"), "Service", "ExecStart")
    assert "scripts/wiki_validate.py" in val and "--format json" in val
    assert _unit("wiki-validate.timer")["Timer"]["OnCalendar"].startswith("*-*-* ")  # nightly


def test_env_template_has_no_secrets():
    text = (OPS / "wiki.env.example").read_text(encoding="utf-8")
    seen = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        seen[k] = v
        if SECRET_KEY.search(k):
            assert v == "", f"secret-looking key must be empty in the template: {k}"
    for needed in ("LWK_UPLOAD_MAX_BYTES", "LWK_UPLOAD_TTL_SECONDS", "BACKUP_GIT_REMOTE", "BACKUP_EBS_VOLUME_ID"):
        assert needed in seen
    assert not re.search(r"[A-Za-z0-9_-]{40,}", text), "token-like blob in env template"
    assert "0600" in text


def test_no_personal_traces_in_ops_files():
    for p in list(OPS.rglob("*")) + [RUNBOOK]:
        if p.is_file():
            t = p.read_text(encoding="utf-8", errors="ignore").lower()
            for bad in ("mohammad", "mozare", "0xbrain", "c:\\users", "/home/", "zarinpal"):
                assert bad not in t, f"{p.name}: {bad}"


def test_runbook_paths_exist_and_cover_h4():
    text = RUNBOOK.read_text(encoding="utf-8")
    paths = set(re.findall(r"`((?:ops/remote|scripts|tests)/[A-Za-z0-9_./-]+)`", text))
    assert paths, "runbook names no repo paths"
    missing = [p for p in paths if not (ROOT / p).exists()]
    assert not missing, missing
    for unit in UNITS + ["smoke.sh", "wiki-backup.sh", "wiki.env.example", "cloudflared-config.yml.example"]:
        assert f"ops/remote/{unit}" in text, unit
    for phrase in ("no inbound", "encrypted", "0600", "/srv/@PREFIX@-wiki", "--insecure-local-only",
                   "D-1", "/healthz", "smoke.sh", "Roll back", "wiki_retrieve"):
        assert phrase.lower() in text.lower(), phrase
    assert "--full" not in text.split("wiki_validate.py")[1][:40] if "wiki_validate.py" in text else True


def test_smoke_script_syntax_and_step_order():
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash missing")
    assert subprocess.run([bash, "-n", str(OPS / "smoke.sh")], capture_output=True).returncode == 0
    t = (OPS / "smoke.sh").read_text(encoding="utf-8")
    order = [t.index(x) for x in ("step healthz", "step status", "step capture", "step search", "step ingest", "step retrieve")]
    assert order == sorted(order)
    assert "skip retrieve" in t and "wiki_retrieve" in t


# ---- run the smoke against a local server ----------------------------------------

def _need_tools():
    if not shutil.which("bash") or not shutil.which("curl"):
        pytest.skip("bash/curl missing")


def _smoke(base: str, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which("bash"), str(OPS / "smoke.sh"), *flags, base],
        capture_output=True, text=True, timeout=120, env={**__import__("os").environ, "PYTHON": sys.executable},
        cwd=ROOT,
    )


@pytest.fixture(scope="module")
def smoke_wiki(tmp_path_factory):
    wiki = tmp_path_factory.mktemp("smokewiki") / "wiki"
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        if (ROOT / rel).is_file():
            (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, wiki / rel)
    r = subprocess.run([sys.executable, "scripts/instantiate.py", "--name", "Smoke Wiki", "--prefix", "smk"], cwd=wiki, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return wiki


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Server:
    """Real server process (the CLI), so the flags and the gate are exercised end to end."""

    def __init__(self, wiki: Path, *extra: str):
        self.port = _free_port()
        self.proc = subprocess.Popen(
            [sys.executable, "scripts/wiki_mcp_server.py", "--transport", "http", "--profile", "capture",
             "--bind", f"127.0.0.1:{self.port}", *extra],
            cwd=wiki, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        import urllib.request

        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz", timeout=1).read()
                return
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        self.stop()
        raise RuntimeError("server did not start")

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stderr:
            self.proc.stderr.close()


@pytest.fixture
def local_server(smoke_wiki):
    srv = _Server(smoke_wiki, "--insecure-local-only")
    try:
        yield srv.base
    finally:
        srv.stop()


def test_smoke_full_run_against_local_insecure_server(local_server):
    _need_tools()
    r = _smoke(local_server)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    for step in ("healthz", "status", "capture", "search", "ingest"):
        assert f"PASS {step}" in out, out
    # wiki_retrieve is another lane's tool: either it passes or is skipped with a clear reason
    assert "PASS retrieve" in out or "SKIP retrieve: tool wiki_retrieve not advertised" in out, out


def test_smoke_read_only_skips_writes_with_message(local_server):
    _need_tools()
    r = _smoke(local_server, "--read-only")
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "SKIP capture: --read-only" in out and "SKIP ingest: --read-only" in out
    assert "PASS healthz" in out and "PASS search" in out


def test_smoke_fails_when_writes_refused(smoke_wiki):
    """Server without --insecure-local-only refuses writes; smoke must fail loudly, not pass."""
    _need_tools()
    srv = _Server(smoke_wiki)
    try:
        r = _smoke(srv.base)
    finally:
        srv.stop()
    out = r.stdout + r.stderr
    assert r.returncode != 0
    assert "FAIL capture" in out and "E_AUTH_REQUIRED" in out and "FAIL ingest" in out

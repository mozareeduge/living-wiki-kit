"""The QMD index is machine-wide (one SQLite file shared by every wiki on the
machine). These tests pin that every kit path that talks to QMD stays inside
the instance's own collections, read from its own config.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import qmd_scope  # noqa: E402
import context_pack as cp  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_semantic_benchmark", ROOT / "scripts/run-semantic-benchmark.py")
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

KIT_DEFAULT = ["wiki-root", "wiki-system", "wiki-objects", "wiki-notes",
               "wiki-claims", "wiki-relations", "wiki-genesis", "wiki-indexes"]


def _cfg(root: Path, names_paths: list[tuple[str, str, bool]]) -> Path:
    p = root / qmd_scope.QMD_CONFIG
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"collections": [
        {"name": n, "path": path, "mask": "**/*.md", "include_by_default": inc, "context": "x"}
        for n, path, inc in names_paths]}), encoding="utf-8")
    return root


def test_names_come_from_the_kit_config():
    assert qmd_scope.names(ROOT, "default") == KIT_DEFAULT
    assert qmd_scope.names(ROOT, "source-records") == ["wiki-source-records"]
    assert qmd_scope.names(ROOT, "derivatives") == ["wiki-derivatives"]
    assert len(qmd_scope.names(ROOT, "all")) == 10


def test_no_config_means_no_names_and_no_scope_flags(tmp_path):
    assert qmd_scope.names(tmp_path) == []
    assert qmd_scope.scope_args([]) == []


def test_scope_args_repeats_the_collection_flag():
    assert qmd_scope.scope_args(["a", "b"]) == ["-c", "a", "-c", "b"]


def test_a_name_registered_outside_the_repo_is_foreign(tmp_path):
    _cfg(tmp_path, [("x-objects", "03-objects", True), ("x-notes", "04-notes", True),
                    ("x-new", "09-indexes", True)])
    other = tmp_path.parent / "another-wiki"
    registered = {"x-objects": str(tmp_path / "03-objects"), "x-notes": str(other)}
    foreign = qmd_scope.foreign_collections(tmp_path, lookup=registered.get)
    assert foreign == [("x-notes", str(other))]


def test_context_pack_search_is_scoped_to_own_default_collections(tmp_path, monkeypatch):
    _cfg(tmp_path, [("x-objects", "03-objects", True), ("x-src", "02-sources/records", False)])
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    monkeypatch.setattr("shutil.which", lambda name: "qmd")
    monkeypatch.setattr(subprocess, "run", fake_run)
    cp.default_search("grave", 5, tmp_path)
    cmd = seen["cmd"]
    assert cmd.count("-c") == 1 and cmd[cmd.index("-c") + 1] == "x-objects"
    assert "wiki" not in cmd  # the old hardcoded collection that matched nothing


def test_context_pack_without_config_does_not_query_the_whole_index(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "qmd")

    def boom(*a, **k):
        raise AssertionError("unscoped qmd call")

    monkeypatch.setattr(subprocess, "run", boom)
    assert cp.default_search("grave", 5, tmp_path) == []


def test_context_pack_maps_any_collection_prefix_to_a_stem():
    import re
    f = "qmd://swk-objects/mw-src-3333333333--essay-grave.md"
    assert Path(re.sub(r"^qmd://[^/]+/", "", f)).stem == "mw-src-3333333333--essay-grave"


def test_benchmark_case_without_collection_is_scoped_to_own_defaults(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    monkeypatch.setattr(sb.subprocess, "run", fake_run)
    sb.run_case({"id": "q", "question": "x", "expected_suffixes": ["a.md"]}, 5, 10)
    cmd = seen["cmd"]
    assert [cmd[i + 1] for i, t in enumerate(cmd) if t == "-c"] == KIT_DEFAULT


def test_benchmark_case_with_collection_uses_only_that_one(monkeypatch):
    seen = {}
    monkeypatch.setattr(sb.subprocess, "run", lambda cmd, **kw: seen.setdefault("cmd", cmd)
                        and subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr=""))
    sb.run_case({"id": "q", "question": "x", "collection": "wiki-source-records",
                 "expected_suffixes": ["a.md"]}, 5, 10)
    cmd = seen["cmd"]
    assert [cmd[i + 1] for i, t in enumerate(cmd) if t == "-c"] == ["wiki-source-records"]


@pytest.mark.parametrize("script", ["scripts/refresh-search.ps1", "scripts/configure-search.ps1"])
def test_powershell_never_runs_machine_wide_update_or_embed(script):
    text = (ROOT / script).read_text(encoding="utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "& qmd update" not in code
    assert "& qmd embed" not in code
    assert "qmd_scope.py check-owned" in code


def test_configure_search_never_removes_a_bare_wiki_collection():
    text = (ROOT / "scripts/configure-search.ps1").read_text(encoding="utf-8")
    assert '@("wiki") +' not in text


def test_no_kit_script_hardcodes_an_instance_collection_name():
    offenders = []
    for p in list((ROOT / "scripts").glob("*.ps1")) + list((ROOT / "scripts").glob("*.py")):
        t = p.read_text(encoding="utf-8")
        for n in qmd_scope.names(ROOT, "all") + ["qmd://wiki/"]:
            if n in t:
                offenders.append((p.name, n))
    assert offenders == []

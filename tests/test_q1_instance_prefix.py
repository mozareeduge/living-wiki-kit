"""Q1 (F11): a new wiki's record IDs carry its own prefix everywhere.

`instantiate.py --prefix smk` must leave no kit-prefixed record id (`mw-…`)
in the code and docs it rewrites, including the schema-drift fixer's patch
manifests, which used to stay `mw-patch-…`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

KIT_ID = re.compile(r"\bmw-(?:src|cap|corpus|evidence|patch|obj|rel|claim)-")


def _copy_kit(base: Path) -> Path:
    dst = base / "kit"
    for rel in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.splitlines():
        src = ROOT / rel
        if src.is_file():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / rel)
    return dst


def test_instance_code_and_docs_carry_only_the_instance_prefix() -> None:
    import instantiate
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        kit = _copy_kit(Path(td))
        r = subprocess.run([sys.executable, "scripts/instantiate.py", "--name", "Smoke",
                            "--prefix", "smk"], cwd=kit, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        leftovers = []
        for pattern in instantiate.TARGET_GLOBS:
            for path in kit.glob(pattern):
                if path.is_file():
                    for m in KIT_ID.finditer(path.read_text(encoding="utf-8")):
                        leftovers.append(f"{path.relative_to(kit).as_posix()}: {m.group(0)}")
        assert leftovers == []
        fixer = (kit / "scripts" / "schema_drift_fixer.py").read_text(encoding="utf-8")
        assert 'f"smk-patch-{run_id}"' in fixer


def test_patch_run_id_uses_the_current_year() -> None:
    src = (ROOT / "scripts" / "schema_drift_fixer.py").read_text(encoding="utf-8")
    assert 'time.strftime("2026-' not in src
    assert time.strftime("%Y") in time.strftime("%Y-%m-%d--schema-drift-reconcile")
    assert 'time.strftime("%Y-%m-%d--schema-drift-reconcile")' in src

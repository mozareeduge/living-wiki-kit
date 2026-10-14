"""Author-confirmation authority is an explicit instance setting.

A promoted capture counts as author confirmation (authority level 3) only
when its promoting actor is listed in `author_actors` in
00-system/configuration/evidence-sources.json. Nothing else, and no name
built into the kit, earns level 3; everyone else's promotion is level 6.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import evidence  # noqa: E402

FIXTURE = (ROOT / "scripts" / "capture" / "fixtures" / "valid" / "2026" / "202609"
           / "cap-20260927-212221-42df.md")


def _wiki(tmp_path: Path, actor: str, author_actors: list[str] | None) -> Path:
    text = FIXTURE.read_text(encoding="utf-8").replace("actor:Owner", f"actor:{actor}")
    dst = tmp_path / "01-inbox" / "captures" / FIXTURE.name
    dst.parent.mkdir(parents=True)
    dst.write_text(text, encoding="utf-8")
    cfg = {"promoted_capture_globs": ["01-inbox/captures/**/*.md"]}
    if author_actors is not None:
        cfg["author_actors"] = author_actors
    (tmp_path / "00-system" / "configuration").mkdir(parents=True)
    (tmp_path / "00-system" / "schemas").mkdir(parents=True)
    shutil.copy(ROOT / "00-system" / "schemas" / "accepted-evidence-row.schema.json",
                tmp_path / "00-system" / "schemas")
    (tmp_path / "00-system" / "configuration" / "evidence-sources.json").write_text(
        json.dumps(cfg), encoding="utf-8")
    return tmp_path


def _levels(root: Path) -> list[int]:
    cfg = json.loads((root / "00-system/configuration/evidence-sources.json").read_text())
    findings: list = []
    rows = evidence._capture_rows(root, cfg["promoted_capture_globs"], findings,
                                  cfg.get("author_actors", []))
    assert findings == []
    return [r["authority_level"] for r in rows]


@pytest.mark.parametrize("actor", ["Owner", "Admin", "owner-bot"])
def test_no_built_in_name_earns_author_authority(tmp_path: Path, actor: str) -> None:
    assert _levels(_wiki(tmp_path, actor, None)) == [6]


def test_listed_author_earns_level_3_exact_name_only(tmp_path: Path) -> None:
    assert _levels(_wiki(tmp_path / "a", "Ada", ["ada"])) == [3]
    assert _levels(_wiki(tmp_path / "b", "Ada Lovelace", ["Ada"])) == [6]


def test_kit_ships_no_author_actor() -> None:
    cfg = json.loads((ROOT / "00-system/configuration/evidence-sources.json").read_text())
    assert cfg.get("author_actors") == []

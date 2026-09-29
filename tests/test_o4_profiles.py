"""O4: profile substrate (dossier §14-19, §47, §49).

Profiles compose additively, cannot weaken kernel invariants, surface
conflicts instead of silently resolving them, and ship inactive.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wiki_profiles as wp  # noqa: E402

EXAMPLES = ["practice-research", "practice-creative",
            "practice-product-discovery", "practice-investigation",
            "practice-experimental", "practice-community-archive"]


def _profile_doc(tmp_path: Path, pid: str, **kw) -> Path:
    fm = {"id": pid, "type": "wiki-profile", "profile_class": "practice",
          "title": pid, "version": "1.0.0", "status": "active"}
    fm.update(kw)
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            lines.append(f"{k}: {v}")
    d = tmp_path / "00-system" / "configuration" / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{pid}.md"
    p.write_text("\n".join(lines) + "\n---\n\nBody.\n", encoding="utf-8")
    (tmp_path / "00-system" / "schemas").mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(ROOT / "00-system" / "schemas" / "wiki-profile.schema.json",
                tmp_path / "00-system" / "schemas" / "wiki-profile.schema.json")
    return p


def _activate(tmp_path: Path, ids: list[str], overrides: dict | None = None) -> None:
    reg = tmp_path / "00-system" / "registers"
    reg.mkdir(parents=True, exist_ok=True)
    inst: dict = {"active_profiles": ids}
    if overrides:
        inst["profile_overrides"] = overrides
    (reg / "INSTANCE.json").write_text(json.dumps(inst), encoding="utf-8")


def test_empty_actives_valid_on_bare_kit() -> None:
    assert wp.cmd_check(ROOT) == 0


def test_unknown_profile_fails_clearly(tmp_path: Path) -> None:
    _profile_doc(tmp_path, "solo")
    _activate(tmp_path, ["no-such-profile"])
    composed, findings = wp.compose(tmp_path)
    assert any("unknown profile" in f and "no-such-profile" in f for f in findings)


def test_compatible_profiles_compose_additively(tmp_path: Path) -> None:
    _profile_doc(tmp_path, "aa", seed_labels=["rehearsal"], suggested_outputs=["dossier"])
    _profile_doc(tmp_path, "bb", seed_labels=["rehearsal", "risk"], suggested_outputs=["memo"])
    _activate(tmp_path, ["aa", "bb"])
    composed, findings = wp.compose(tmp_path)
    assert findings == []
    assert composed["seed_labels"] == ["rehearsal", "risk"]
    assert composed["suggested_outputs"] == ["dossier", "memo"]


def test_retired_profile_cannot_activate(tmp_path: Path) -> None:
    _profile_doc(tmp_path, "old", status="retired")
    _activate(tmp_path, ["old"])
    _, findings = wp.compose(tmp_path)
    assert any("retired" in f for f in findings)


def test_weakening_key_is_rejected(tmp_path: Path) -> None:
    p = _profile_doc(tmp_path, "sneaky")
    text = p.read_text(encoding="utf-8").replace("---\n\nBody.",
                                                 "disable_validation: true\n---\n\nBody.")
    p.write_text(text, encoding="utf-8")
    _activate(tmp_path, ["sneaky"])
    _, findings = wp.compose(tmp_path)
    assert findings, "a disable_* key must not pass as advisory vocabulary"
    assert any("sneaky" in f for f in findings)


def test_slot_conflict_surfaced_not_silenced(tmp_path: Path) -> None:
    _profile_doc(tmp_path, "aa", preferred_lens="lens-x")
    _profile_doc(tmp_path, "bb", preferred_lens="lens-y")
    _activate(tmp_path, ["aa", "bb"])
    _, findings = wp.compose(tmp_path)
    assert any("conflict" in f and "lens-x" in f and "lens-y" in f for f in findings)


def test_override_resolves_conflict(tmp_path: Path) -> None:
    _profile_doc(tmp_path, "aa", preferred_lens="lens-x")
    _profile_doc(tmp_path, "bb", preferred_lens="lens-y")
    _activate(tmp_path, ["aa", "bb"], overrides={"preferred_lens": "lens-x"})
    composed, findings = wp.compose(tmp_path)
    assert findings == []
    assert composed["preferred_lens"] == "lens-x"


def test_shipped_examples_validate_and_stay_inactive() -> None:
    from gov_kernel.schemas import validate_record
    schema_dir = ROOT / "00-system" / "schemas"
    for pid in EXAMPLES:
        doc = ROOT / "00-system" / "configuration" / "profiles" / f"{pid}.md"
        assert doc.exists(), pid
        record, errs = wp.read_profile(doc, schema_dir)
        assert errs == [], (pid, errs)
        assert record["status"] == "example", pid
        assert validate_record(record, schema_dir,
                               explicit_schema="wiki-profile.schema.json") == []
    assert wp.load_active_ids(ROOT) == []

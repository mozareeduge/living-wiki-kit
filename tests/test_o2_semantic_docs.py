"""O2: semantic policy + agent guidance (dossier §30-35).

SEMANTIC_MODEL.md carries the maxims; SYSTEM_DESIGN, LIFECYCLE, AGENTS,
CLAUDE and wiki-write inherit them; no doc presents the 8 legacy object
kinds as an exhaustive closed list.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "00-system" / "policies" / "SEMANTIC_MODEL.md"


def _read(rel: str) -> str:
    # Collapse line wraps: maxims must survive prose reflow.
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def test_semantic_policy_exists_with_maxims() -> None:
    text = " ".join(SEM.read_text(encoding="utf-8").lower().split())
    for maxim in ("object before kind",
                  "labels organize discovery",
                  "profiles configure the practice",
                  "adjudication upgrades authority",
                  "governs how knowledge is handled"):
        assert maxim in text, maxim


def test_system_design_carries_object_before_kind() -> None:
    text = _read("SYSTEM_DESIGN.md").lower()
    assert "object before kind" in text


def test_lifecycle_stage4_needs_no_classification() -> None:
    text = _read("LIFECYCLE.md").lower()
    assert "characterize before classifying" in text


def test_agents_inherits_label_rule() -> None:
    assert "never evidence" in _read("AGENTS.md").lower()
    assert "label" in _read("CLAUDE.md").lower()


def test_wiki_write_teaches_label_discipline() -> None:
    text = _read(".claude/skills/wiki-write/SKILL.md")
    for rule in ("characterize before labeling", "minimum useful labels",
                 "merge object identities", "relations when context matters"):
        assert rule in text, rule


def test_no_doc_presents_legacy_kinds_as_exhaustive() -> None:
    # The precise prohibition: the old 8-kind run presented as a closed set.
    for rel in ("SYSTEM_DESIGN.md", "LIFECYCLE.md",
                ".claude/skills/wiki-write/SKILL.md"):
        text = _read(rel)
        assert "collection, concept, institution" not in text, rel

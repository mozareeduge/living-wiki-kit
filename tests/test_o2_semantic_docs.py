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


def test_object_page_profiles_section_is_not_an_instance_profile() -> None:
    """§29: an object page's `## Profiles` section and the instance's
    configuration profiles are different things; the policy says so."""
    text = " ".join(SEM.read_text(encoding="utf-8").lower().split())
    assert "an object page's `## profiles` section" in text
    assert "not an instance profile" in text


def test_profile_tightening_is_described_as_it_exists() -> None:
    """F18 then D-b: the docs describe tightening exactly as built (a closed
    set of rules enforced by `wiki_profiles.py check`), never as open-ended."""
    for rel in ("00-system/policies/SEMANTIC_MODEL.md", "scripts/wiki_profiles.py"):
        text = _read(rel).lower()
        assert "may tighten kernel rules" not in text, rel
        assert "tightening is not implemented" not in text, rel
        for rule in ("object-labels", "relation-type", "record-visibility"):
            assert rule in text, (rel, rule)


def test_evidence_audit_docstring_names_the_durable_queue() -> None:
    head = (ROOT / "scripts" / "evidence_audit.py").read_text(encoding="utf-8")[:600]
    assert "_proposals/records/" in head
    assert "Reads _proposals/proposals.jsonl," not in head

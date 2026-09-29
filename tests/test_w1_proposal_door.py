"""W1: kernel wiki_propose validates at the door.

- kind must be one of the 17 H0 kinds (schema enum == policy kinds);
- source_passage (quote >= 20 chars, verbatim in a canonical path) is
  required for every kind except intake-registration (artifact is the
  evidence) and capture-promotion (capture: refs are the evidence);
- object-create/object-update carry optional labels, never a closed kind;
- evidence_audit.py and report_holdings.py read _proposals/records/ +
  _proposals/adjudications/ (legacy proposals.jsonl stays read-only).
"""
from __future__ import annotations

import io
import json
import contextlib
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import proposals as kp  # noqa: E402
import evidence_audit as ea  # noqa: E402
import report_holdings as rh  # noqa: E402

PASSAGE = "The grave machine organizes absence into citation."
CANON = "02-sources/records/mw-src-1111111111--n.md"

H0_17 = {
    "relation-edge", "claim-amendment", "object-note", "intake-registration",
    "tier-change", "record-correction", "link-repair", "retirement-request",
    "object-create", "object-update", "relation-create", "relation-amend",
    "claim-create", "claim-amend", "lineage-link", "research-question",
    "capture-promotion",
}


@pytest.fixture()
def gate(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "00-system" / "schemas", tmp_path / "00-system" / "schemas")
    (tmp_path / "00-system" / "policies").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    rec = tmp_path / CANON
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"---\nid: mw-src-1111111111\n---\n{PASSAGE}\n", encoding="utf-8")
    return tmp_path


def _body(**kw) -> str:
    return json.dumps(kw)


def test_schema_enum_equals_h0_17(gate: Path) -> None:
    schema = json.loads((gate / "00-system" / "schemas" / "proposal.schema.json").read_text())
    policy = json.loads((gate / "00-system" / "policies" / "proposal_schema.json").read_text())
    assert set(schema["properties"]["kind"]["enum"]) == H0_17
    assert set(policy["kinds"]) == H0_17


def test_door_refuses_unknown_kind(gate: Path) -> None:
    with pytest.raises(ValueError, match="[Kk]ind"):
        kp.create_proposal(gate, kind="object-create-delete",
                           body=_body(title="t", characterization="c" * 30, why="w",
                                      source_passage={"path": CANON, "quote": PASSAGE}),
                           submitted_by={"actor_type": "agent", "tool": "t"})


def test_door_refuses_missing_passage(gate: Path) -> None:
    with pytest.raises(ValueError, match="[Pp]assage"):
        kp.create_proposal(gate, kind="relation-edge",
                           body=_body(target_id="x", proposed_type="supports", why="w"),
                           submitted_by={"actor_type": "agent", "tool": "t"})


def test_door_refuses_fabricated_quote(gate: Path) -> None:
    with pytest.raises(ValueError, match="[Vv]erbatim"):
        kp.create_proposal(gate, kind="object-note",
                           body=_body(object_id="x", note="n", why="w",
                                      source_passage={"path": CANON,
                                                      "quote": "This sentence is nowhere in the file at all."}),
                           submitted_by={"actor_type": "agent", "tool": "t"})


def test_door_accepts_verbatim_passage(gate: Path) -> None:
    p = kp.create_proposal(gate, kind="relation-edge",
                           body=_body(target_id="x", proposed_type="supports", why="w",
                                      source_passage={"path": CANON, "quote": PASSAGE}),
                           submitted_by={"actor_type": "agent", "tool": "t"})
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["authority_tier"] == "candidate"
    assert p.relative_to(gate).as_posix().startswith("_proposals/records/")


def test_door_intake_needs_no_passage(gate: Path) -> None:
    art = gate / "01-inbox" / "arrival.txt"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_bytes(b"hello intake")
    p = kp.create_proposal(gate, kind="intake-registration",
                           body=_body(original_path="01-inbox/arrival.txt",
                                      sha256="a" * 64, why="new arrival"),
                           submitted_by={"actor_type": "agent", "tool": "t"})
    assert p.exists()


def test_door_capture_promotion_needs_refs(gate: Path) -> None:
    with pytest.raises(ValueError, match="[Ee]vidence"):
        kp.create_proposal(gate, kind="capture-promotion",
                           body="Promotion proposal for captures cap-1. Rationale: looks useful.",
                           submitted_by={"actor_type": "agent", "tool": "t"})
    p = kp.create_proposal(gate, kind="capture-promotion",
                           body="Promotion proposal for captures cap-1. Rationale: looks useful.",
                           submitted_by={"actor_type": "agent", "tool": "t"},
                           evidence_refs=["capture:cap-1:" + "b" * 64])
    assert p.exists()


def test_door_object_create_labels_optional_no_kind(gate: Path) -> None:
    p = kp.create_proposal(gate, kind="object-create",
                           body=_body(title="First session", characterization="A first gathering",
                                      labels=["rehearsal"], why="stable identity useful",
                                      source_passage={"path": CANON, "quote": PASSAGE}),
                           submitted_by={"actor_type": "agent", "tool": "t"})
    assert p.exists()
    p2 = kp.create_proposal(gate, kind="object-create",
                            body=_body(title="Unlabeled thing", characterization="Exists first",
                                       why="identity before classification",
                                       source_passage={"path": CANON, "quote": PASSAGE}),
                            submitted_by={"actor_type": "agent", "tool": "t"})
    assert p2.exists()


def test_audit_reads_durable_records(gate: Path) -> None:
    (gate / "_audits").mkdir(exist_ok=True)
    kp.create_proposal(gate, kind="relation-edge",
                       body=_body(target_id="x", proposed_type="supports", why="w",
                                  source_passage={"path": CANON, "quote": PASSAGE}),
                       submitted_by={"actor_type": "agent", "tool": "t"})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ea.audit(gate)
    assert rc == 0
    rep = sorted((gate / "_audits").glob("evidence-audit-*.json"))[-1]
    data = json.loads(rep.read_text())
    assert data["totals"]["audited"] == 1


def test_audit_skips_terminally_adjudicated(gate: Path) -> None:
    (gate / "_audits").mkdir(exist_ok=True)
    p = kp.create_proposal(gate, kind="relation-edge",
                           body=_body(target_id="x", proposed_type="supports", why="w",
                                      source_passage={"path": CANON, "quote": PASSAGE}),
                           submitted_by={"actor_type": "agent", "tool": "t"})
    pid = json.loads(p.read_text())["id"]
    kp.adjudicate(gate, proposal_id=pid, decision="accepted", by="owner",
                  decision_note="good", applied_to=["03-objects/x.md"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ea.audit(gate)
    rep = sorted((gate / "_audits").glob("evidence-audit-*.json"))[-1]
    data = json.loads(rep.read_text())
    assert data["totals"]["skipped"] == 1
    assert data["totals"]["audited"] == 0


def test_holdings_counts_durable_proposals(gate: Path) -> None:
    kp.create_proposal(gate, kind="relation-edge",
                       body=_body(target_id="x", proposed_type="supports", why="w",
                                  source_passage={"path": CANON, "quote": PASSAGE}),
                       submitted_by={"actor_type": "agent", "tool": "t"})
    report = rh.generate_report(gate)
    assert report["proposals_by_status"]["total"] >= 1

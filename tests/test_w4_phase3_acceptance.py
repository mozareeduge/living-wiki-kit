"""W4: Phase 3 acceptance (50 speculative proposals, durable records).

Every proposal ends audited or rejected-audit; nothing canonical changes;
nothing lands outside _proposals/. Runs in an isolated fixture wiki, so the
kit tree itself stays clean (the ladder's `git status` clause).
"""
from __future__ import annotations

import io
import contextlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import proposals as kp  # noqa: E402
import evidence_audit as ea  # noqa: E402

TEXTS = [
    "The grave machine organizes absence into citation.",
    "Method follows the material, never the other way round.",
    "A rehearsal is a promise the performance may not keep.",
]


def _wiki(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "00-system" / "schemas", tmp_path / "00-system" / "schemas")
    (tmp_path / "00-system" / "policies").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    for i, text in enumerate(TEXTS):
        rec = tmp_path / f"02-sources/records/mw-src-{i:010d}--n.md"
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(f"---\nid: mw-src-{i:010d}\n---\n{text}\n", encoding="utf-8")
    stale_text = "A passage that will soon be rewritten away completely."
    stale_rec = tmp_path / "02-sources/records/mw-src-0000000009--n.md"
    stale_rec.write_text("---\nid: mw-src-0000000009\n---\n" + stale_text + "\n",
                         encoding="utf-8")
    (tmp_path / "_audits").mkdir(exist_ok=True)
    return tmp_path, stale_text


def _canon(i: int) -> str:
    return f"02-sources/records/mw-src-{i:010d}--n.md"


def _sp(i: int) -> dict:
    return {"path": _canon(i % 3), "quote": TEXTS[i % 3]}


def _valid_body(kind: str, i: int) -> str:
    sp = _sp(i)
    shapes = {
        "relation-edge": {"target_id": f"mw-x-{i}", "proposed_type": "supports",
                          "why": "parallel", "source_passage": sp},
        "claim-amendment": {"claim_id": f"c-{i}", "amendment": "narrower scope",
                            "why": "evidence", "source_passage": sp},
        "object-note": {"object_id": f"o-{i}", "note": "observed",
                        "why": "reading", "source_passage": sp},
        "tier-change": {"target_id": f"mw-src-{i:010d}", "from_tier": "pending-registration",
                        "to_tier": "registered", "why": "verified",
                        "source_passage": sp},
        "record-correction": {"target_id": f"o-{i}", "field": "title",
                              "old_value": "a", "new_value": "b",
                              "why": "typo", "source_passage": sp},
        "link-repair": {"target_id": f"o-{i}", "broken_link": "[[gone]]",
                        "repaired_link": "[[here]]", "why": "moved",
                        "source_passage": sp},
        "retirement-request": {"target_id": f"o-{i}", "why": "superseded",
                               "source_passage": sp, "superseded_by": f"o-new-{i}"},
        "object-create": {"title": f"Thing {i}", "characterization": "characterized",
                          "labels": ["rehearsal"], "why": "identity",
                          "source_passage": sp},
        "object-update": {"object_id": f"o-{i}", "update": "revised",
                          "why": "new reading", "source_passage": sp},
        "relation-create": {"subject_id": f"o-{i}", "proposed_type": "rehearses",
                            "why": "session", "source_passage": sp},
        "relation-amend": {"relation_id": f"r-{i}", "amendment": "retype",
                           "why": "evidence", "source_passage": sp},
        "claim-create": {"claim": f"Claim number {i} about the material",
                         "why": "argued", "source_passage": sp},
        "claim-amend": {"claim_id": f"c-{i}", "amendment": "soften",
                        "why": "counter-evidence", "source_passage": sp},
        "lineage-link": {"target_id": f"o-{i}", "event_ref": f"ev-{i}",
                         "why": "genesis", "source_passage": sp},
        "research-question": {"question": f"What does record {i} change?",
                              "why": "open", "source_passage": sp},
    }
    return json.dumps(shapes[kind])


DOOR_KINDS = ["relation-edge", "claim-amendment", "object-note", "tier-change",
              "record-correction", "link-repair", "retirement-request",
              "object-create", "object-update", "relation-create",
              "relation-amend", "claim-create", "claim-amend",
              "lineage-link", "research-question"]


def test_fifty_proposals_all_adjudicated_or_rejected(tmp_path: Path) -> None:
    wiki, stale_text = _wiki(tmp_path)
    by = {"actor_type": "agent", "tool": "w4-acceptance"}

    # 30 valid through the door (all 15 passage kinds x2).
    for n in range(30):
        kp.create_proposal(wiki, kind=DOOR_KINDS[n % len(DOOR_KINDS)],
                           body=_valid_body(DOOR_KINDS[n % len(DOOR_KINDS)], n),
                           submitted_by=by)

    # 10 stale: valid at creation, passage destroyed afterwards.
    stale_sp = {"path": "02-sources/records/mw-src-0000000009--n.md",
                "quote": stale_text}
    for n in range(30, 40):
        kp.create_proposal(wiki, kind="object-note",
                           body=json.dumps({"object_id": f"o-{n}", "note": "n",
                                            "why": "w", "source_passage": stale_sp}),
                           submitted_by=by)
    (wiki / "02-sources/records/mw-src-0000000009--n.md").write_text(
        "---\nid: mw-src-0000000009\n---\nRewritten entirely.\n", encoding="utf-8")

    # 10 defective, written directly (import path bypasses the door).
    recs = wiki / "_proposals" / "records" / "2026"
    recs.mkdir(parents=True, exist_ok=True)
    for n in range(40, 50):
        pid = f"prop-w4-{n:04d}"
        (recs / f"{pid}.json").write_text(json.dumps({
            "id": pid, "type": "proposal", "received": "2026-09-28T00:00:00Z",
            "kind": "relation-edge" if n % 2 else "not-a-kind",
            "authority_tier": "candidate",
            "submitted_by": by, "body": json.dumps({"target_id": "x"}),
            "body_sha256": "0" * 64, "evidence_refs": [], "target_refs": []}),
            encoding="utf-8")

    made = list((wiki / "_proposals" / "records").rglob("*.json"))
    assert len(made) == 50

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ea.audit(wiki)
    assert rc == 1  # rejections present, as designed
    rep = sorted((wiki / "_audits").glob("evidence-audit-*.json"))[-1]
    data = json.loads(rep.read_text())
    assert data["totals"]["total"] == 50
    assert data["totals"]["audited"] + data["totals"]["rejected-audit"] == 50
    assert data["totals"]["skipped"] == 0
    for r in data["results"]:
        assert r["verdict"] in ("audited", "rejected-audit"), r
    assert data["totals"]["audited"] == 30
    assert data["totals"]["rejected-audit"] == 20  # 10 stale + 10 defective

    # Zero canonical change: no canonical zones created or touched.
    for zone in ("03-objects", "04-notes", "05-claims", "06-relations"):
        assert not (wiki / zone).exists()
    for i in range(3):
        assert TEXTS[i] in (wiki / _canon(i)).read_text()
    writes = [p for p in wiki.rglob("*") if p.is_file()
              and "_proposals/records" not in p.relative_to(wiki).as_posix()
              and "_audits/evidence-audit-" not in p.relative_to(wiki).as_posix()]
    written_names = {p.name for p in writes}
    assert "expected-invalid.json" not in written_names  # sanity: no fixture bleed

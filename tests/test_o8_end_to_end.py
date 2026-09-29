"""O8: end-to-end semantic acceptance (dossier §69).

One fixture walks the whole dossier flow: intake source -> kindless labeled
object proposal -> candidate retrieval -> relation + claim proposals ->
two profiles -> two lenses with different foregrounding over the same
records -> proof that nothing canonical mutated off the promotion path.
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
import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
import candidate_projection as cand  # noqa: E402
import evidence_audit as ea  # noqa: E402
import wiki_profiles as wp  # noqa: E402

PASSAGE = "The grave machine organizes absence into citation."
METHOD_PASSAGE = "Method follows the material, never the other way round."
CANON = "02-sources/records/mw-src-1111111111--n.md"
CANON2 = "02-sources/records/mw-src-2222222222--m.md"


def _wiki(tmp_path: Path) -> Path:
    for s in ("proposal.schema.json", "wiki-profile.schema.json", "wiki-lens.schema.json"):
        (tmp_path / "00-system" / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "00-system" / "schemas" / s,
                    tmp_path / "00-system" / "schemas" / s)
    (tmp_path / "00-system" / "policies").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    rec = tmp_path / CANON
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"---\nid: mw-src-1111111111\n---\n{PASSAGE}\n", encoding="utf-8")
    rec2 = tmp_path / CANON2
    rec2.write_text(f"---\nid: mw-src-2222222222\n---\n{METHOD_PASSAGE}\n", encoding="utf-8")
    shutil.copytree(ROOT / "00-system" / "configuration" / "profiles",
                    tmp_path / "00-system" / "configuration" / "profiles")
    shutil.copytree(ROOT / "00-system" / "configuration" / "lenses",
                    tmp_path / "00-system" / "configuration" / "lenses")
    (tmp_path / "00-system" / "registers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "00-system" / "registers" / "INSTANCE.json").write_text(
        json.dumps({"active_profiles": ["practice-research", "practice-creative"]}),
        encoding="utf-8")
    (tmp_path / "_audits").mkdir(exist_ok=True)
    return tmp_path


def _body(**kw) -> str:
    return json.dumps(kw)


def test_full_dossier_flow(tmp_path: Path) -> None:
    root = _wiki(tmp_path)

    # 1-3. kindless object proposal with two labels, then candidate retrieval.
    pid = json.loads(kp.create_proposal(
        root, kind="object-create",
        body=_body(title="First session", characterization="A first gathering",
                   labels=["rehearsal", "methodological"], why="identity useful",
                   source_passage={"path": CANON, "quote": PASSAGE}),
        submitted_by={"actor_type": "agent", "tool": "t"}).read_text())["id"]
    assert cand.rebuild(root)["projections"]
    bgi.build(root)
    pack = cp.build_pack(root, "mw-src-1111111111", hops=0, query="rehearsal",
                         search_fn=lambda q, n: [])
    found = [e for e in pack["records"] if e.get("proposal_id") == pid]
    assert len(found) == 1 and found[0]["authority"] == "candidate"

    # 4-5. relation + claim proposals on the same material.
    kp.create_proposal(
        root, kind="relation-create",
        body=_body(subject_id=pid, proposed_type="rehearses", why="session prepares work",
                   source_passage={"path": CANON, "quote": PASSAGE}),
        submitted_by={"actor_type": "agent", "tool": "t"})
    kp.create_proposal(
        root, kind="claim-create",
        body=_body(claim="The session marks a methodological turn",
                   why="argued from the record",
                   source_passage={"path": CANON2, "quote": METHOD_PASSAGE}),
        submitted_by={"actor_type": "agent", "tool": "t"})

    # Audit sees all three, all pass.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ea.audit(root)
    assert rc == 0

    # 6. two profiles compose.
    composed, findings = wp.compose(root)
    assert findings == []
    assert composed["active_profiles"] == ["practice-research", "practice-creative"]
    assert "rehearsal" in composed["seed_labels"]

    # 7-8. two lenses foreground differently over the same records.
    drama = cp.build_pack(root, "mw-src-1111111111", hops=0, query="rehearsal",
                          search_fn=lambda q, n: [], lens="lens-dramaturg")
    scholar = cp.build_pack(root, "mw-src-1111111111", hops=0, query="rehearsal",
                            search_fn=lambda q, n: [], lens="lens-scholar")
    d_reasons = {e["id"]: e["reason"] for e in drama["records"]}
    s_reasons = {e["id"]: e["reason"] for e in scholar["records"]}
    assert {e["id"] for e in drama["records"]} == {e["id"] for e in scholar["records"]}
    assert "foregrounded by lens lens-dramaturg" in d_reasons[pid]
    assert "foregrounded by lens lens-dramaturg" not in s_reasons[pid]

    # Negative control: accepted-only drops the candidate but keeps canonical.
    strict = cp.build_pack(root, "mw-src-1111111111", hops=0, query="rehearsal",
                           search_fn=lambda q, n: [], accepted_only=True)
    assert pid not in {e.get("proposal_id") for e in strict["records"]}
    assert "mw-src-1111111111" in {e["id"] for e in strict["records"]}

    # 9. nothing canonical mutated off the promotion path.
    assert not (root / "03-objects").exists()
    assert not (root / "05-claims").exists()
    assert not (root / "06-relations").exists()
    assert (root / CANON).read_text(encoding="utf-8").endswith(PASSAGE + "\n")

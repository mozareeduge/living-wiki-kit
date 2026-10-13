"""O11 (F16): six heterogeneous practices on one unchanged kernel (dossier §36, §59, §69.13, D30).

For each shipped example profile, a small wiki is expressed with the kernel
as it is: an object with no `kind`, labels (one wiki in Persian, §46), one
typed relation and one claim, the profile active, and a candidate
`object-create` proposal. Retrieval then shows the profile's reasons, the
profile's own lens foregrounding its relation language, and the candidate
visible and marked, while nothing canonical changes.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import proposals as kp  # noqa: E402
from gov_kernel.schemas import validate_record  # noqa: E402
import build_graph_index as bgi  # noqa: E402
import candidate_projection as cand  # noqa: E402
import context_pack as cp  # noqa: E402
import wiki_profiles as wp  # noqa: E402

SCHEMAS = ROOT / "00-system" / "schemas"

# profile -> (object title, object labels, other object title, passage); the
# first label is a seed label of that profile and also the retrieval query.
CONTEXTS = {
    "practice-research": (
        "Archive letter of 1931", ["primary-source", "correspondence"],
        "Thesis chapter two",
        "The letter was written in the spring and never sent."),
    "practice-creative": (
        "First rehearsal", ["rehearsal", "fragment"],
        "The finished piece",
        "We rehearsed the opening three times before it held."),
    "practice-product-discovery": (
        "Checkout drop-off signal", ["signal", "risk"],
        "Decision to simplify checkout",
        "Users abandoned the checkout at the address step."),
    "practice-investigation": (
        "Warehouse fire allegation", ["allegation", "unverified"],
        "Port authority logbook",
        "The source alleged the fire was set before midnight."),
    "practice-experimental": (
        "Run 14 of the assay", ["run", "measurement"],
        "Assay protocol v2",
        "Run fourteen produced the same curve as run nine."),
    "practice-community-archive": (
        "گردهمایی محلهٔ قدیم", ["memory", "خاطره"],
        "عکس میدان در سال ۱۳۵۰",
        "همه در میدان جمع شدند و آن عکس را گرفتند."),
}


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fm(record: dict) -> str:
    lines = []
    for k, v in record.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def _profile(pid: str) -> dict:
    record, errs = wp.read_profile(
        ROOT / "00-system" / "configuration" / "profiles" / f"{pid}.md", SCHEMAS)
    assert errs == []
    return record


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for zone in ("02-sources", "03-objects", "05-claims", "06-relations"):
        for p in sorted((root / zone).rglob("*")):
            if p.is_file():
                h.update(p.relative_to(root).as_posix().encode())
                h.update(p.read_bytes())
    return h.hexdigest()


def _wiki(root: Path, pid: str) -> dict:
    title, labels, other_title, passage = CONTEXTS[pid]
    prof = _profile(pid)
    rtype = prof["suggested_relation_language"][0]
    src = "02-sources/records/sx-src-0123456789ab--note.md"
    _w(root / src, f"---\nid: sx-src-0123456789ab\ntype: source-record\n---\n\n{passage}\n")
    obj = {"id": "sx-obj-subject", "type": "object", "title": title,
           "status": "active-record", "labels": labels}
    other = {"id": "sx-obj-other", "type": "object", "title": other_title,
             "status": "active-record", "labels": []}
    rel = {"id": "sx-rel-subject-other", "type": "relation-object",
           "title": f"{title} {rtype} {other_title}",
           "participants": ["sx-obj-subject", "sx-obj-other"], "relation_type": rtype,
           "relation_status": "candidate", "current_claim_permission": "may-note"}
    claim = {"id": "sx-claim-subject", "type": "claim-object", "title": f"About {title}",
             "statement": passage, "about": ["sx-obj-subject"],
             "supporting_sources": ["sx-src-0123456789ab"], "unsupported_zones": [],
             "counter_evidence": [], "certainty": "candidate",
             "current_claim_permission": "may-note", "responsible_language": "en"}
    for rec, path in ((obj, "03-objects/subject.md"), (other, "03-objects/other.md"),
                      (rel, "06-relations/subject-other.md"), (claim, "05-claims/subject.md")):
        _w(root / path, _fm(rec) + "\nBody.\n")
    for s in ("proposal.schema.json", "wiki-profile.schema.json", "wiki-lens.schema.json"):
        _w(root / "00-system" / "schemas" / s, (SCHEMAS / s).read_text(encoding="utf-8"))
    _w(root / "00-system" / "policies" / "proposal_schema.json",
       (ROOT / "00-system" / "policies" / "proposal_schema.json").read_text(encoding="utf-8"))
    shutil.copytree(ROOT / "00-system" / "configuration" / "profiles",
                    root / "00-system" / "configuration" / "profiles")
    shutil.copytree(ROOT / "00-system" / "configuration" / "lenses",
                    root / "00-system" / "configuration" / "lenses")
    _w(root / "00-system" / "registers" / "INSTANCE.json",
       json.dumps({"active_profiles": [pid]}))
    return {"obj": obj, "rel": rel, "claim": claim, "src": src, "passage": passage,
            "rtype": rtype, "lens": prof["suggested_lenses"][0], "query": labels[0]}


def test_every_suggested_lens_ships() -> None:
    lenses = ROOT / "00-system" / "configuration" / "lenses"
    for pid in CONTEXTS:
        for lid in _profile(pid)["suggested_lenses"]:
            assert (lenses / f"{lid}.md").is_file(), f"{pid} suggests missing {lid}"
            cp.resolve_lens(ROOT, lid)  # schema-valid, not retired


@pytest.mark.parametrize("pid", list(CONTEXTS))
def test_practice_on_unchanged_kernel(tmp_path: Path, pid: str) -> None:
    w = _wiki(tmp_path, pid)

    # Records validate against the kernel's own schemas; the object has no kind.
    assert "kind" not in w["obj"]
    assert validate_record(w["obj"], SCHEMAS, explicit_schema="object-record.schema.json") == []
    assert validate_record(w["rel"], SCHEMAS) == []
    assert validate_record(w["claim"], SCHEMAS) == []
    assert wp.compose(tmp_path)[1] == []

    # A candidate object-create proposal, quoting the canonical source.
    pid_prop = json.loads(kp.create_proposal(
        tmp_path, kind="object-create",
        body=json.dumps({"title": "A candidate", "characterization": "Proposed object",
                         "labels": [w["query"]], "why": "identity is useful",
                         "source_passage": {"path": w["src"], "quote": w["passage"]}}),
        submitted_by={"actor_type": "agent", "tool": "test"}).read_text())["id"]
    before = _tree_digest(tmp_path)
    assert cand.rebuild(tmp_path)["projections"]
    bgi.build(tmp_path)

    pack = cp.build_pack(tmp_path, "sx-obj-subject", hops=2, query=w["query"],
                         search_fn=lambda q, n: [], lens=w["lens"])
    recs = {e["id"]: e for e in pack["records"]}

    # Relation, claim and the other object are all reached through the graph.
    assert {"sx-obj-subject", "sx-rel-subject-other", "sx-claim-subject",
            "sx-obj-other"} <= set(recs)
    # The profile explains, the profile's lens foregrounds its relation language.
    assert f"(profile {pid} seed label `{w['query']}`)" in recs["sx-obj-subject"]["reason"]
    tag = f"lens {w['lens']} foregrounds relation `{bgi.normalize_label(w['rtype'])}`"
    assert tag in recs["sx-rel-subject-other"]["reason"]
    assert tag in recs["sx-obj-other"]["reason"]
    # The candidate is visible and marked, never canonical.
    c = recs[pid_prop]
    assert c["candidate"] is True and c["authority"] == "candidate"
    assert c["path"] is None
    assert pack["meta"]["active_profiles"] == [pid]
    # Nothing canonical changed on the way.
    assert _tree_digest(tmp_path) == before


def test_persian_labels_retrieve_by_their_own_words(tmp_path: Path) -> None:
    _wiki(tmp_path, "practice-community-archive")
    bgi.build(tmp_path)
    pack = cp.build_pack(tmp_path, "sx-obj-other", hops=0, query="خاطره",
                         search_fn=lambda q, n: [])
    recs = {e["id"]: e for e in pack["records"]}
    assert recs["sx-obj-subject"]["reason"].startswith("label: `خاطره` matched query context")

"""O7: compatibility + label audit (dossier §42-44).

Legacy kind stays searchable with its source visibly marked; the label
audit is read-only; migration is dry-run by default and never automatic.
"""
from __future__ import annotations

import io
import json
import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
import report_labels as rl  # noqa: E402
import migrate_object_kinds as mk  # noqa: E402
from gov_kernel import proposals as kp  # noqa: E402
import candidate_projection as cand  # noqa: E402

PASSAGE = "The grave machine organizes absence into citation."
CANON = "02-sources/records/mw-src-1111111111--n.md"


def _obj(path: Path, rid: str, fm_extra: str = "", labels: list[str] | None = None) -> None:
    listed = ""
    if labels is not None:
        listed = "labels: [" + ", ".join(labels) + "]\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {rid}\ntype: object\ntitle: T {rid}\n"
                    f"status: active-record\n{fm_extra}{listed}---\n\nBody.\n",
                    encoding="utf-8")


def _wiki(tmp_path: Path) -> Path:
    _obj(tmp_path / "03-objects" / "legacy--person.md", "xx-obj-legacy", "kind: person\n")
    _obj(tmp_path / "03-objects" / "labeled--one.md", "xx-obj-one", labels=["Theatre", "phase/rehearsal"])
    _obj(tmp_path / "03-objects" / "labeled--two.md", "xx-obj-two", labels=["theater"])
    _obj(tmp_path / "03-objects" / "bare--note.md", "xx-obj-bare")
    rec = tmp_path / CANON
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"---\nid: mw-src-1111111111\n---\n{PASSAGE}\n", encoding="utf-8")
    (tmp_path / "00-system" / "schemas").mkdir(parents=True, exist_ok=True)
    (tmp_path / "00-system" / "policies").mkdir(parents=True, exist_ok=True)
    for s in ("proposal.schema.json",):
        shutil.copy(ROOT / "00-system" / "schemas" / s,
                    tmp_path / "00-system" / "schemas" / s)
    shutil.copy(ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    (tmp_path / "_audits").mkdir(exist_ok=True)
    bgi.build(tmp_path)
    return tmp_path


def test_legacy_kind_searchable_and_marked(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    pack = cp.build_pack(root, "xx-obj-bare", hops=0, query="person",
                         search_fn=lambda q, n: [])
    found = [e for e in pack["records"] if e["id"] == "xx-obj-legacy"]
    assert len(found) == 1
    assert found[0]["label_source"] == "legacy-kind"
    assert "legacy kind compatibility" in found[0]["reason"]


def test_report_counts_variants_namespaces(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    rep = rl.build_report(root)
    assert rep["nodes_indexed"] == 5
    assert rep["unlabeled_nodes"] == 2  # bare note + source record
    assert "person" in rep["legacy_kind_derived"]
    norms = [d["norm"] for d in rep["normalization_duplicates"]]
    assert "theater" not in norms  # Theatre/theater differ; case variants:
    assert rep["namespace_distribution"].get("phase") == 1


def test_report_case_variant_detection(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    _obj(root / "03-objects" / "labeled--three.md", "xx-obj-three", labels=["THEATRE"])
    bgi.build(root)
    rep = rl.build_report(root)
    dup = next(d for d in rep["normalization_duplicates"] if d["norm"] == "theatre")
    assert set(dup["raws"]) == {"Theatre", "THEATRE"}


def test_report_candidate_usage(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    body = json.dumps({"title": "Cand", "characterization": "c",
                       "labels": ["rehearsal"], "why": "w",
                       "source_passage": {"path": CANON, "quote": PASSAGE}})
    kp.create_proposal(root, kind="object-create", body=body,
                       submitted_by={"actor_type": "agent", "tool": "t"})
    cand.rebuild(root)
    rep = rl.build_report(root)
    assert rep["candidate_label_usage"].get("rehearsal") == 1


def test_report_performs_no_write(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    rl.build_report(root)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rl.main(["--repo", str(root)])
        rl.main(["--repo", str(root), "--format", "json"])
    after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    assert before == after


def test_migration_dry_run_by_default(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    assert mk.main(["--repo", str(root)]) == 0
    items = mk.plan(root)
    assert [i["path"] for i in items] == ["03-objects/legacy--person.md"]
    after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    assert before == after


def test_migration_apply_refuses_dirty_tree(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    assert mk.main(["--repo", str(root), "--apply"]) == 2


def test_migration_apply_on_clean_tree(tmp_path: Path) -> None:
    root = _wiki(tmp_path)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=root, check=True, capture_output=True)
    assert mk.main(["--repo", str(root), "--apply"]) == 0
    text = (root / "03-objects" / "legacy--person.md").read_text(encoding="utf-8")
    import re
    assert not re.search(r"^kind:", text, re.MULTILINE)
    assert "legacy_kind: person" in text
    assert "person" in text.split("labels:")[1].split("---")[0]

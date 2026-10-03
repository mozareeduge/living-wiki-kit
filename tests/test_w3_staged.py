"""W3: staged reconciliation (RC classes, modes, classed receipts).

Every run declares RC-0..RC-4 first; incremental reconciles one new source
in batches without rereading every row and resumes across sessions;
loss and >30% drift escalate to full.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import reconcile_runner as rr  # noqa: E402
from gov_kernel.schemas import validate_record  # noqa: E402


def _row(i: int, **over) -> dict:
    r = {"id": f"mw-src-{i:010d}", "family": "alpha",
         "ingested_on": "2026-09-01", "word_count": 100 + i,
         "sha256": f"hash-{i:03d}",
         "source_record_path": f"02-sources/records/mw-src-{i:010d}--n.md",
         "format": "md", "filename": f"mw-src-{i:010d}--n.md"}
    r.update(over)
    return r


def _wiki(tmp_path: Path, n: int = 10) -> tuple[Path, list[dict]]:
    import shutil
    shutil.copytree(KIT_ROOT / "00-system" / "schemas",
                    tmp_path / "00-system" / "schemas")
    reg = tmp_path / "00-system" / "registers"
    reg.mkdir(parents=True)
    (tmp_path / "_audits").mkdir()
    rows = [_row(i) for i in range(1, n + 1)]
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (reg / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": len(rows)}), encoding="utf-8")
    return tmp_path, rows


def _run_dir(wiki: Path) -> Path:
    runs = sorted(p for p in (wiki / "_audits").iterdir() if p.name.startswith("recon-"))
    return runs[-1]


def test_run_class_recorded_and_receipt_schema_valid() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wiki, _ = _wiki(Path(td))
        assert rr.plan(wiki, "full", "RC-3") == 0
        run = _run_dir(wiki)
        plan = json.loads((run / "batch-plan.json").read_text())
        assert plan["class"] == "RC-3"
        receipt = json.loads((run / "run-receipt.json").read_text())
        assert receipt["class"] == "RC-3" and receipt["status"] == "planned"
        assert validate_record(receipt, wiki / "00-system" / "schemas",
                               explicit_schema="reconciliation-receipt.schema.json") == []


def test_unknown_class_refused() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wiki, _ = _wiki(Path(td))
        assert rr.plan(wiki, "full", "RC-9") == 2


def test_incremental_covers_only_new_rows_and_resumes(tmp_path: Path) -> None:
    wiki, rows = _wiki(tmp_path)
    assert rr.plan(wiki, "full", "RC-3") == 0
    # One new source arrives with a count bump.
    rows.append(_row(11))
    reg = wiki / "00-system" / "registers"
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (reg / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": len(rows)}), encoding="utf-8")
    assert rr.plan(wiki, "incremental", "RC-1") == 0
    run = _run_dir(wiki)
    scoped = [(json.loads(line))["id"] for line in
              (run / "expected.jsonl").read_text().splitlines() if line.strip()]
    assert scoped == ["mw-src-0000000011"]  # one row, not all eleven
    plan = json.loads((run / "batch-plan.json").read_text())
    assert plan["mode"] == "incremental" and plan["class"] == "RC-1"
    # Resume across sessions: nothing new -> clean no-op on persisted state.
    assert rr.plan(wiki, "incremental", "RC-1") == 0
    assert _run_dir(wiki) == run


def test_loss_escalates_to_full(tmp_path: Path) -> None:
    wiki, rows = _wiki(tmp_path)
    assert rr.plan(wiki, "full", "RC-3") == 0
    rows = rows[:-1]  # a row disappears AND the count drops
    reg = wiki / "00-system" / "registers"
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (reg / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": len(rows)}), encoding="utf-8")
    assert rr.plan(wiki, "incremental", "RC-1") == 0
    plan = json.loads((_run_dir(wiki) / "batch-plan.json").read_text())
    assert plan["mode"] == "full"


def test_mass_drift_escalates_to_full(tmp_path: Path) -> None:
    wiki, rows = _wiki(tmp_path, n=10)
    assert rr.plan(wiki, "full", "RC-3") == 0
    for r in rows[:4]:  # 40% changed, count steady
        r["sha256"] = "hash-CHANGED"
    reg = wiki / "00-system" / "registers"
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert rr.plan(wiki, "incremental", "RC-1") == 0
    plan = json.loads((_run_dir(wiki) / "batch-plan.json").read_text())
    assert plan["mode"] == "full"

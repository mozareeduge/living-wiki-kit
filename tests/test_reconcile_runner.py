"""Tests for reconcile_runner.py (Phase 2 core)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import reconcile_runner as rr  # noqa: E402


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    reg = tmp_path / "00-system" / "registers"
    reg.mkdir(parents=True)
    (tmp_path / "_audits").mkdir()
    rows = []
    for i in range(1, 26):  # 25 rows -> 3 batches under 8..12 policy
        rows.append({
            "id": f"mw-src-{i:010d}",
            "family": "gamma" if i > 18 else ("beta" if i > 12 else "alpha"),
            "ingested_on": f"2026-09-{(i % 8) + 1:02d}",
            "word_count": 100 + i,
            "sha256": f"hash-{i:03d}",
            "source_record_path": f"02-sources/records/mw-src-{i:010d}--n.md",
            "format": "md",
            "filename": f"mw-src-{i:010d}--n.md",
        })
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (reg / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": len(rows)}), encoding="utf-8")
    return tmp_path


def test_plan_full_batches_and_scaffold(wiki: Path) -> None:
    assert rr.plan(wiki, "full") == 0
    runs = sorted((wiki / "_audits").iterdir())
    run = [r for r in runs if r.name.startswith("recon-")][0]
    expected = (run / "expected.jsonl").read_text(encoding="utf-8-sig").splitlines()
    assert len(expected) == 25
    plan = json.loads((run / "batch-plan.json").read_text(encoding="utf-8-sig"))
    assert sum(b["n"] for b in plan["plan"]) == 25
    assert all(8 <= b["n"] <= 12 or b is plan["plan"][-1] for b in plan["plan"])
    files = list(run.glob("batch-*-files.txt"))
    assert len(files) == len(plan["plan"])


def test_verify_pass_on_exact_once_receipts(wiki: Path) -> None:
    rr.plan(wiki, "full")
    run = sorted((wiki / "_audits").iterdir())[0]
    ids = [json.loads(l)["id"] for l in
           (run / "expected.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    receipts = run / "receipts.txt"
    receipts.write_text("\n".join(
        f"artifact {i} read ok\nBATCH RECEIPT: batch complete. opened=N/K, ids=[{i}]"
        for i in ids), encoding="utf-8")
    assert rr.verify(wiki, run.name, receipts) == 0


def test_verify_fails_on_missing_and_escalates(wiki: Path) -> None:
    rr.plan(wiki, "full")
    run = sorted((wiki / "_audits").iterdir())[0]
    ids = [json.loads(l)["id"] for l in
           (run / "expected.jsonl").read_text(encoding="utf-8-sig").splitlines()][:20]
    receipts = run / "receipts.txt"
    receipts.write_text("\n".join(f"artifact {i} ok" for i in ids), encoding="utf-8")
    rc = rr.verify(wiki, run.name, receipts)
    assert rc == 2  # 5 missing -> >3 conflicts -> human escalation


def test_incremental_scope_and_escalation(wiki: Path) -> None:
    rr.plan(wiki, "full")
    reg = wiki / "00-system" / "registers"
    rows = [json.loads(l) for l in
            (reg / "MATERIALS_INDEX.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    # normal intake: 1 changed + 1 new, CORPUS_STATE count follows (25 -> 26)
    rows[3]["sha256"] = "hash-changed"
    rows.append({**rows[0], "id": "mw-src-9999999999", "sha256": "hash-new"})
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (reg / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": len(rows)}), encoding="utf-8")
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rr.plan(wiki, "incremental")
    out = buf.getvalue()
    # 2 in-scope rows of 25 frozen = 8% < 30% -> stays incremental
    assert "incremental scope" in out, out
    # >30% drift -> escalation to full (snapshot + counts stay consistent)
    rr.plan(wiki, "full")  # re-freeze on the 26-row corpus
    rows2 = [json.loads(l) for l in
             (reg / "MATERIALS_INDEX.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    for r in rows2[:10]:
        r["sha256"] = f"drift-{r['id']}"
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows2), encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rr.plan(wiki, "incremental")
    out = buf.getvalue()
    assert "ESCALATION to full mode" in out, out
    assert "38% rows changed" in out or "rows changed" in out, out



def test_state_cmd_reports_signature_change(wiki: Path) -> None:
    rr.plan(wiki, "full")
    reg = wiki / "00-system" / "registers"
    rows = [json.loads(l) for l in
            (reg / "MATERIALS_INDEX.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    rows[0]["sha256"] = "hash-mutated"
    (reg / "MATERIALS_INDEX.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert rr.state_cmd(wiki) == 0


def test_signature_sensitivity() -> None:
    a = [{"id": "x", "sha256": "1", "source_record_path": "p"}]
    b = [{"id": "x", "sha256": "2", "source_record_path": "p"}]
    assert rr.rows_signature(a) != rr.rows_signature(b)
    assert rr.rows_signature(a) == rr.rows_signature(list(reversed(a)))

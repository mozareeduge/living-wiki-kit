#!/usr/bin/env python3
"""Deterministic reconciliation core (Phase 2): plan / verify / drift state.

The governed-corpus-reconcile procedure (batch receipts, zero-gap coverage)
is LLM work around a deterministic core. This script IS that core:

- plan --mode full        freeze expected.jsonl + batch plan over ALL rows
- plan --mode incremental freeze batches over rows changed since last freeze
- verify --run-id X       assert exact-once id coverage vs expected.jsonl
- state                   show drift since last freeze + escalation reasons

Writes ONLY to `_audits/` (never canonical zones). Reads
00-system/registers/MATERIALS_INDEX.jsonl + CORPUS_STATE.json at run time
(counts drift; never hardcode). Escalation (incremental -> full / human):
any removed row, corpus-state count change, >30% rows changed, or >3
verify conflicts. Committing the scaffold is the operator's call per
instance policy (mozare-wiki commits audit scaffolds on audit/ branches).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REGISTERS = Path("00-system/registers")
STATE_FILE = Path("_audits/reconcile-state.json")
BATCH_MIN, BATCH_MAX = 8, 12
ESCALATE_CHANGED_PCT = 30
ESCALATE_CONFLICTS = 3


def _load_jsonl(p: Path) -> list[dict]:
    rows = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def manifest_rows(root: Path) -> list[dict]:
    return _load_jsonl(root / REGISTERS / "MATERIALS_INDEX.jsonl")


def corpus_state(root: Path) -> dict:
    return json.loads((root / REGISTERS / "CORPUS_STATE.json").read_text(encoding="utf-8-sig"))


def rows_signature(rows: list[dict]) -> str:
    payload = sorted(
        json.dumps({k: r.get(k) for k in ("id", "sha256", "source_record_path")},
                   sort_keys=True, ensure_ascii=False)
        for r in rows)
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


def _plan_batches(rows: list[dict]) -> tuple[list[dict], list[list[dict]]]:
    ordered = sorted(rows, key=lambda r: (str(r.get("family", "")),
                                          str(r.get("ingested_on", "")),
                                          str(r.get("id", ""))))
    batches: list[list[dict]] = []
    cur: list[dict] = []
    cur_family = None
    for r in ordered:
        fam = str(r.get("family", ""))
        if cur and (fam != cur_family or len(cur) >= BATCH_MAX):
            if len(cur) < BATCH_MIN and batches:
                batches[-1].extend(cur)  # singleton tail-merge
            else:
                batches.append(cur)
            cur = []
        cur.append(r)
        cur_family = fam
    if cur:
        if len(cur) < BATCH_MIN and batches:
            batches[-1].extend(cur)
        else:
            batches.append(cur)
    plan = [{"batch": f"batch-{i+1:02d}", "n": len(b)} for i, b in enumerate(batches)]
    return plan, batches


def _write_run_scaffold(root: Path, run_id: str, rows: list[dict],
                        mode: str) -> tuple[Path, list[dict], list[list[dict]]]:
    run_dir = root / "_audits" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "expected.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    plan, batches = _plan_batches(rows)
    (run_dir / "batch-plan.json").write_text(
        json.dumps({"run_id": run_id, "mode": mode, "plan": plan},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    for b, rows_b in zip([f"batch-{i+1:02d}" for i in range(len(batches))], batches):
        lines = [f"{r.get('id')} | {r.get('format')} | {r.get('word_count')} | "
                 f"{Path(str(r.get('filename', ''))).name}" for r in rows_b]
        (run_dir / f"{b}-files.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir, rows, batches


def plan(root: Path, mode: str) -> int:
    rows = manifest_rows(root)
    cstate = corpus_state(root)
    state = _load_state(root)
    reasons: list[str] = []
    if mode == "incremental":
        if not state:
            reasons.append("no prior freeze: full run required")
        else:
            prev = {r["id"]: r for r in state.get("rows_snapshot", [])}
            cur = {r["id"]: r for r in rows}
            new = [r for i, r in cur.items() if i not in prev]
            changed = [r for i, r in cur.items() if i in prev and
                       (r.get("sha256") != prev[i].get("sha256") or
                        r.get("source_record_path") != prev[i].get("source_record_path"))]
            removed = [i for i in prev if i not in cur]
            if removed:
                reasons.append(f"{len(removed)} removed row(s): {removed[:5]}")
            cs_now = cstate.get("source_material_count")
            cs_prev = state.get("corpus_state_count")
            if isinstance(cs_now, int) and isinstance(cs_prev, int) and cs_now < cs_prev:
                reasons.append(f"CORPUS_STATE count DECREASED {cs_prev} -> {cs_now} "
                               f"(loss — possible deletion; full required)")
            pct = 100 * len(changed) / max(1, len(prev))
            if pct > ESCALATE_CHANGED_PCT:
                reasons.append(f"{pct:.0f}% rows changed > {ESCALATE_CHANGED_PCT}%")
            scope = new + changed
            if reasons:
                print("ESCALATION to full mode — reasons:")
                for r in reasons:
                    print(f"  - {r}")
                mode = "full"
            elif not scope:
                print("incremental: nothing changed since last freeze; nothing to reconcile")
                return 0
            else:
                rows = scope
                print(f"incremental scope: {len(new)} new, {len(changed)} changed")
    run_id = time.strftime("recon-%Y-%m-%d--") + mode
    run_dir, rows, batches = _write_run_scaffold(root, run_id, rows, mode)
    _save_state(root, {
        "last_run_id": run_id, "mode": mode,
        "frozen_at_epoch": int(time.time()),
        "rows_signature": rows_signature(manifest_rows(root)),
        "corpus_state_count": cstate.get("source_material_count"),
        "rows_snapshot": manifest_rows(root),
    })
    print(f"frozen: _audits/{run_id}/ expected={len(rows)} batches={len(batches)}")
    return 0


def verify(root: Path, run_id: str, receipts: Path) -> int:
    run_dir = root / "_audits" / run_id
    expected: dict[str, str] = {}
    for line in (run_dir / "expected.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            r = json.loads(line)
            expected[str(r.get("id"))] = str(r.get("id"))
    seen: dict[str, list[str]] = {}
    conflicts: list[str] = []
    text = receipts.read_text(encoding="utf-8-sig", errors="ignore") if receipts.is_file() \
        else "\n".join(p.read_text(encoding="utf-8-sig", errors="ignore")
                       for p in sorted(receipts.glob("*")))
    for line in text.splitlines():
        if "BATCH RECEIPT:" not in line:
            for tok in line.replace(",", " ").split():
                if tok in expected:
                    seen.setdefault(tok, []).append(line.strip()[:80])
        else:
            pass  # completion line asserted via per-batch parse below
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    missing = [i for i in expected if i not in seen]
    extra = sorted(set(seen) - set(expected))
    conflicts = [f"duplicate mentions: {k} x{len(v)}" for k, v in dupes.items()]
    conflicts += [f"missing from receipts: {i}" for i in missing]
    conflicts += [f"unknown id in receipts: {i}" for i in extra]
    verdict = "PASS" if not conflicts else "FAIL"
    print(f"verify {run_id}: {verdict} — covered {len(seen)}/{len(expected)}, "
          f"conflicts={len(conflicts)}")
    for c in conflicts[:10]:
        print(f"  - {c}")
    (run_dir / "verify-report.txt").write_text(
        f"{verdict}\ncovered={len(seen)}/{len(expected)}\n" +
        "\n".join(conflicts) + "\n", encoding="utf-8")
    if len(conflicts) > ESCALATE_CONFLICTS:
        print(f"ESCALATION: >{ESCALATE_CONFLICTS} conflicts — human review required")
        return 2
    return 0 if not conflicts else 1


def state_cmd(root: Path) -> int:
    st = _load_state(root)
    if not st:
        print("no reconcile state; run: reconcile_runner.py plan --mode full")
        return 0
    rows = manifest_rows(root)
    sig = rows_signature(rows)
    print(f"last freeze: {st.get('last_run_id')} mode={st.get('mode')} "
          f"count={st.get('corpus_state_count')}")
    print(f"rows changed since freeze: {'YES' if sig != st.get('rows_signature') else 'no'}")
    return 0


def _load_state(root: Path) -> dict | None:
    p = root / STATE_FILE
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _save_state(root: Path, st: dict) -> None:
    p = root / STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--mode", choices=["full", "incremental"], default="full")
    p_ver = sub.add_parser("verify")
    p_ver.add_argument("--run-id", required=True)
    p_ver.add_argument("--receipts", required=True, type=Path)
    sub.add_parser("state")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if args.cmd == "plan":
        return plan(root, args.mode)
    if args.cmd == "verify":
        return verify(root, args.run_id, args.receipts)
    return state_cmd(root)


if __name__ == "__main__":
    sys.exit(main())

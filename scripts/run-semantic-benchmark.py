#!/usr/bin/env python3
"""Run the Mozare Wiki 1.1.0 QMD semantic benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "00-system/configuration/semantic-benchmark-v1.1.0.json"
QMD = shutil.which("qmd") or "qmd"


def load_config(path: Path) -> dict:
    """The case set is instance data, not kit data (finding F2): an empty kit
    has no corpus to ask questions about. Each instance supplies its own file
    at CONFIG, or passes --config. A missing file is a clear exit, not a trace."""
    if not path.is_file():
        raise SystemExit(
            f"benchmark case set not found: {path}\n"
            "The kit ships no case set; benchmarks are instance-supplied. Create "
            "00-system/configuration/semantic-benchmark-v1.1.0.json in your "
            "instance (see SEARCH_GUIDE.md section 7) or pass --config <file>.")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    value = value.replace("\\", "/").strip()
    value = re.sub(r"^qmd://[^/]+/", "", value)
    return value.casefold()


def collect_paths(value) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in {
                "path", "displaypath", "file", "filepath", "uri", "document",
            } and isinstance(item, str):
                paths.append(item)
            paths.extend(collect_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(collect_paths(item))
    elif isinstance(value, str) and ".md" in value:
        for match in re.findall(r"(?:qmd://[^\s\"']+|[^\s\"']+\.md)", value):
            paths.append(match.rstrip("),.;"))
    return paths


def parse_qmd_json(stdout: str):
    text = stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
        for start in sorted(starts):
            try:
                return json.loads(text[start:])
            except json.JSONDecodeError:
                continue
    raise ValueError("QMD did not return parseable JSON")


def run_case(case: dict, top_k: int, timeout: int) -> dict:
    command = [QMD, "query", case["question"], "--no-rerank", "--json", "-n", str(top_k)]
    if case.get("collection"):
        command.extend(["-c", case["collection"]])
    # qmd prints UTF-8 box-drawing glyphs on stderr/stdout. Without an explicit
    # UTF-8 decode Windows uses cp1252, the reader thread raises
    # UnicodeDecodeError, and proc.stdout silently becomes None - which used to
    # crash this function's own error path instead of reporting a bad result.
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
        env=env,
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    result = {
        "id": case["id"],
        "question": case["question"],
        "collection": case.get("collection", "canonical-default"),
        "command": command,
        "returncode": proc.returncode,
        "stderr": stderr.strip(),
    }
    if proc.returncode != 0:
        result.update({"passed": False, "error": "qmd command failed", "paths": []})
        return result
    try:
        payload = parse_qmd_json(stdout)
    except Exception as exc:
        result.update({
            "passed": False,
            "error": str(exc),
            "stdout_excerpt": stdout[-2000:],
            "paths": [],
        })
        return result

    raw_paths = collect_paths(payload)
    seen = set()
    paths = []
    for item in raw_paths:
        norm = normalize(item)
        if norm not in seen:
            seen.add(norm)
            paths.append(item)
        if len(paths) >= top_k:
            break

    expected = [normalize(x) for x in case["expected_suffixes"]]
    ranked = [normalize(x) for x in paths]
    hits = [
        exp for exp in expected
        if any(path.endswith(exp) or exp.endswith(path) for path in ranked)
    ]
    result.update({
        "passed": bool(hits),
        "expected_suffixes": case["expected_suffixes"],
        "matched_expected": hits,
        "paths": paths,
    })
    return result


def compute_neighborhood_recall(results: list[dict], k: int) -> dict:
    """Compute neighborhood recall@K for each case and aggregate.

    recall@K = |expected ∩ retrieved@K| / |expected|

    A case with zero expected items is excluded from the aggregate mean
    (it has no neighborhood to recall) but is reported with recall=None.
    """
    per_case = []
    recalls = []
    for r in results:
        expected = r.get("expected_suffixes", [])
        matched = r.get("matched_expected", [])
        if not expected:
            recall = None
        else:
            recall = len(matched) / len(expected)
            recalls.append(recall)
        per_case.append({
            "id": r["id"],
            "expected_count": len(expected),
            "matched_count": len(matched),
            "recall_at_k": round(recall, 4) if recall is not None else None,
        })
    mean_recall = round(sum(recalls) / len(recalls), 4) if recalls else None
    return {
        "k": k,
        "mean_recall_at_k": mean_recall,
        "cases_with_expected": len(recalls),
        "per_case": per_case,
    }


def compute_human_rejection_rate(results: list[dict]) -> dict:
    """Compute human rejection rate.

    Scope note (read before trusting this number): this is a *proxy* for human
    rejection, not a measurement of it. A case counts as rejected when the
    retrieval was inadequate by the only signal available offline - some
    expected item was not in the top-K, or the case errored / returned nothing.
    That makes it a function of the same expected-vs-matched comparison as
    neighborhood recall@K: with expected==matched everywhere, rejection_rate
    tracks 1 - mean_recall_at_k exactly. It adds an operational reading
    ("what fraction of questions would a reviewer send back?") and it also
    counts hard errors that recall@K reports as None, so it is not redundant -
    but it is NOT an independent axis of quality, and a real human-rejection
    rate needs recorded reviewer decisions, not a heuristic.

    rejection_rate = rejected_cases / total_cases
    """
    total = len(results)
    rejected = 0
    per_case = []
    for r in results:
        expected = r.get("expected_suffixes", [])
        matched = r.get("matched_expected", [])
        paths = r.get("paths", [])
        error = r.get("error")

        # A case is rejected if:
        # 1. It errored (no paths, error message present)
        # 2. It has expected items but not all were matched
        # 3. It has expected items but no paths were returned
        # A case with no expected items is never rejected (nothing to find).
        is_rejected = False
        if error:
            is_rejected = True
        elif expected and len(matched) < len(expected):
            is_rejected = True
        elif expected and not paths:
            is_rejected = True

        if is_rejected:
            rejected += 1
        per_case.append({
            "id": r["id"],
            "rejected": is_rejected,
            "reason": (
                "error" if error
                else "incomplete_recall" if expected and len(matched) < len(expected)
                else "no_paths" if not paths
                else None
            ),
        })
    rate = round(rejected / total, 4) if total else None
    return {
        "rejection_rate": rate,
        "rejected": rejected,
        "total": total,
        "per_case": per_case,
    }


def compute_evidence_trace_completeness(results: list[dict]) -> dict:
    """Compute evidence-trace completeness.

    A case has a complete evidence trace if ALL of the following hold:
    1. expected_suffixes is non-empty (the case defines what should be found)
    2. paths is non-empty (the system returned at least one result)
    3. matched_expected is non-empty (at least one expected item was found)

    completeness_rate = cases_with_complete_trace / total_cases
    """
    total = len(results)
    complete = 0
    per_case = []
    for r in results:
        expected = r.get("expected_suffixes", [])
        matched = r.get("matched_expected", [])
        paths = r.get("paths", [])

        has_expected = bool(expected)
        has_paths = bool(paths)
        has_match = bool(matched)
        is_complete = has_expected and has_paths and has_match

        if is_complete:
            complete += 1
        per_case.append({
            "id": r["id"],
            "complete": is_complete,
            "has_expected": has_expected,
            "has_paths": has_paths,
            "has_match": has_match,
        })
    rate = round(complete / total, 4) if total else None
    return {
        "completeness_rate": rate,
        "complete": complete,
        "total": total,
        "per_case": per_case,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Semantic Benchmark 1.1.0",
        "",
        f"- Run: `{report['run_at']}`",
        f"- Passed: **{report['passed']} / {report['total']}**",
        f"- Threshold: **{report['threshold']}**",
        f"- Result: **{report['result']}**",
        "",
    ]

    # Add metrics summary if present
    metrics = report.get("metrics", {})
    if metrics:
        lines.extend([
            "## Metrics",
            "",
        ])
        if "neighborhood_recall" in metrics:
            nr = metrics["neighborhood_recall"]
            lines.append(
                f"- **Neighborhood Recall@{nr['k']}**: "
                f"{nr['mean_recall_at_k'] if nr['mean_recall_at_k'] is not None else 'N/A'}"
            )
        if "human_rejection_rate" in metrics:
            hr = metrics["human_rejection_rate"]
            lines.append(
                f"- **Human Rejection Rate**: "
                f"{hr['rejection_rate'] if hr['rejection_rate'] is not None else 'N/A'}"
            )
        if "evidence_trace_completeness" in metrics:
            etc = metrics["evidence_trace_completeness"]
            lines.append(
                f"- **Evidence-Trace Completeness**: "
                f"{etc['completeness_rate'] if etc['completeness_rate'] is not None else 'N/A'}"
            )
        lines.append("")

    lines.extend([
        "| ID | Scope | Pass | Expected hit | Top paths |",
        "|---|---|---:|---|---|",
    ])
    for item in report["cases"]:
        top = "<br>".join(item.get("paths", [])[:5]).replace("|", "\\|")
        hit = ", ".join(item.get("matched_expected", [])) or "—"
        lines.append(
            f"| {item['id']} | {item['collection']} | "
            f"{'yes' if item['passed'] else 'no'} | {hit} | {top} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG,
                        help="case-set JSON (default: the instance's 00-system/configuration file)")
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--threshold", type=int)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument(
        "--output",
        default="_audits/runtime/semantic-benchmark-1.1.0.json",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    top_k = args.top_k or config.get("top_k", 5)
    threshold = args.threshold or config.get("threshold", 27)

    results = []
    for case in config["cases"]:
        print(f"[{case['id']}] {case['question']}", flush=True)
        try:
            result = run_case(case, top_k, args.timeout)
        except subprocess.TimeoutExpired:
            result = {
                "id": case["id"],
                "question": case["question"],
                "collection": case.get("collection", "canonical-default"),
                "passed": False,
                "error": f"timeout after {args.timeout} seconds",
                "paths": [],
            }
        results.append(result)
        print("  PASS" if result["passed"] else "  FAIL", flush=True)

    passed = sum(1 for x in results if x["passed"])
    metrics = {
        "neighborhood_recall": compute_neighborhood_recall(results, top_k),
        "human_rejection_rate": compute_human_rejection_rate(results),
        "evidence_trace_completeness": compute_evidence_trace_completeness(results),
    }
    report = {
        "benchmark_id": config["id"],
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results),
        "passed": passed,
        "threshold": threshold,
        "result": "PASS" if passed >= threshold else "FAIL",
        "metrics": metrics,
        "cases": results,
    }

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(report, output.with_suffix(".md"))

    print(f"{report['result']}: {passed}/{len(results)} benchmark cases passed")
    print(f"Reports: {output} and {output.with_suffix('.md')}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

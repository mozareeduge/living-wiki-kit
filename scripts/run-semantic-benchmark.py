#!/usr/bin/env python3
"""Run the Mozare Wiki 1.1.0 QMD semantic benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "00-system/configuration/semantic-benchmark-v1.1.0.json"


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
    command = ["qmd", "query", case["question"], "--json", "-n", str(top_k)]
    if case.get("collection"):
        command.extend(["-c", case["collection"]])
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    result = {
        "id": case["id"],
        "question": case["question"],
        "collection": case.get("collection", "canonical-default"),
        "command": command,
        "returncode": proc.returncode,
        "stderr": proc.stderr.strip(),
    }
    if proc.returncode != 0:
        result.update({"passed": False, "error": "qmd command failed", "paths": []})
        return result
    try:
        payload = parse_qmd_json(proc.stdout)
    except Exception as exc:
        result.update({
            "passed": False,
            "error": str(exc),
            "stdout_excerpt": proc.stdout[-2000:],
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


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Semantic Benchmark 1.1.0",
        "",
        f"- Run: `{report['run_at']}`",
        f"- Passed: **{report['passed']} / {report['total']}**",
        f"- Threshold: **{report['threshold']}**",
        f"- Result: **{report['result']}**",
        "",
        "| ID | Scope | Pass | Expected hit | Top paths |",
        "|---|---|---:|---|---|",
    ]
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
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--threshold", type=int)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument(
        "--output",
        default="_audits/runtime/semantic-benchmark-1.1.0.json",
    )
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
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
    report = {
        "benchmark_id": config["id"],
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results),
        "passed": passed,
        "threshold": threshold,
        "result": "PASS" if passed >= threshold else "FAIL",
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

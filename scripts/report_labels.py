#!/usr/bin/env python3
"""Read-only label audit (dossier §44).

Reports over the disposable graph index + candidate projections:
distinct labels, most-used, singletons, post-normalization duplicates,
spelling/case variants, namespace distribution, legacy-kind-derived labels,
unlabeled objects, candidate-vs-canonical usage.

Attention tool only: reads, never writes, never merges, never repairs.

Usage: python scripts/report_labels.py [--repo .] [--format text|json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_projection as _cp  # noqa: E402


def build_report(root: Path) -> dict:
    db = root / "_search" / "graph.db"
    rows: list[tuple] = []
    nodes = 0
    if db.exists():
        con = sqlite3.connect(db)
        try:
            rows = con.execute(
                "SELECT node_id, label_raw, label_norm, label_source FROM labels").fetchall()
            nodes = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        except Exception:
            rows = []
        finally:
            con.close()
    by_norm: dict[str, dict] = {}
    for nid, raw, norm, source in rows:
        by_norm.setdefault(norm, {"raws": set(), "nodes": set(), "sources": set()})
        by_norm[norm]["raws"].add(raw)
        by_norm[norm]["nodes"].add(nid)
        by_norm[norm]["sources"].add(source)

    node_use = Counter(nid for _, _, _, _ in rows for nid in [_[0]])
    labeled_nodes = {nid for nid, _, _, _ in rows}
    namespaces: Counter[str] = Counter()
    for norm in by_norm:
        namespaces[norm.split("/")[0] if "/" in norm else "(none)"] += 1

    candidates = _cp.load_projections(root)
    candidate_labels: Counter[str] = Counter()
    for c in candidates:
        for lb in c.get("labels", []):
            candidate_labels[str(lb)] += 1

    return {
        "nodes_indexed": nodes,
        "labeled_nodes": len(labeled_nodes),
        "unlabeled_nodes": nodes - len(labeled_nodes),
        "distinct_labels": len(by_norm),
        "most_used": [{"label": n, "objects": len(v["nodes"])}
                      for n, v in sorted(by_norm.items(),
                                         key=lambda kv: -len(kv[1]["nodes"]))[:20]],
        "singletons": sorted(n for n, v in by_norm.items() if len(v["nodes"]) == 1),
        "normalization_duplicates": sorted(
            [{"norm": n, "raws": sorted(v["raws"])} for n, v in by_norm.items()
             if len(v["raws"]) > 1], key=lambda d: d["norm"]),
        "namespace_distribution": dict(sorted(namespaces.items())),
        "legacy_kind_derived": sorted(
            {n for n, v in by_norm.items() if "legacy-kind" in v["sources"]}),
        "candidate_label_usage": dict(sorted(candidate_labels.items())),
        "node_label_counts": dict(sorted(node_use.items())),
    }


def render_text(report: dict) -> str:
    lines = ["Label audit (read-only; attention tool, not a repair):",
             f"  nodes indexed: {report['nodes_indexed']} "
             f"({report['labeled_nodes']} labeled, {report['unlabeled_nodes']} unlabeled)",
             f"  distinct labels: {report['distinct_labels']}"]
    lines.append("  most used:")
    for m in report["most_used"][:10]:
        lines.append(f"    {m['label']}: {m['objects']} objects")
    lines.append(f"  singletons ({len(report['singletons'])}): "
                 + (", ".join(report["singletons"][:10]) or "(none)"))
    if report["normalization_duplicates"]:
        lines.append("  spelling/case variants (NOT auto-merged):")
        for d in report["normalization_duplicates"][:10]:
            lines.append(f"    {d['norm']}: {', '.join(d['raws'])}")
    lines.append(f"  namespaces: {json.dumps(report['namespace_distribution'], ensure_ascii=False)}")
    lines.append("  legacy-kind-derived: "
                 + (", ".join(report["legacy_kind_derived"]) or "(none)"))
    lines.append("  candidate usage: "
                 + (json.dumps(report["candidate_label_usage"], ensure_ascii=False) or "(none)"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    report = build_report(root)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=1, default=list))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

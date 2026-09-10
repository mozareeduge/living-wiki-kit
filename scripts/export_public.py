#!/usr/bin/env python3
"""Public export valve for This Wiki — Engine 4 (publication layer).

One-way static export of canonical objects gated on their own `visibility:`
frontmatter. Private material NEVER leaks:

  - only records with `visibility: public` are rendered;
  - `_originals/`, registers, templates, genesis, runtime dirs are excluded
    outright regardless of flags;
  - every emitted page carries a provenance footer (source id, authority
    fields as recorded, export stamp);
  - the output is plain HTML, no build system required.

This is the T1 backlog item-3 / T2 item-6 mechanism in its minimal credible
form: a valve, not a publication pipeline. Redaction rules stay with the
records themselves (`visibility:` is the single gate by design).
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT.parent / "wiki-public-export"  # OUTSIDE the repo

EXCLUDED_PARTS = {"_originals", "_search", "_audits", "_exports", "_proposals",
                  ".git", ".obsidian", ".claude", "00-system", "07-genesis",
                  "01-inbox", "09-indexes"}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def parse_fm(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    data = yaml.safe_load(text[4:end])
    return (data if isinstance(data, dict) else {}), text[end + 5:]


def render_body(body: str) -> str:
    """Minimal deterministic markdown->HTML subset (no external deps):
    paragraphs, headings, lists, code fences; wikilinks render as plain
    spans (targets may be private - never linked)."""
    body = WIKILINK_RE.sub(lambda m: f'<span class="wikilink">{html.escape(m.group(1).strip())}</span>', body)
    out, in_code, lines_buf = [], False, []

    def flush_para():
        if lines_buf:
            out.append(f"<p>{'<br>'.join(html.escape(l) for l in lines_buf)}</p>")
            lines_buf.clear()

    for line in body.splitlines():
        if line.strip().startswith("```"):
            flush_para()
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        h = re.match(r"^(#{1,4}) (.*)$", line)
        li = re.match(r"^[-*] (.*)$", line)
        if h:
            flush_para()
            lvl = len(h.group(1))
            out.append(f"<h{lvl}>{h.group(2)}</h{lvl}>")
        elif li:
            flush_para()
            out.append(f"<li>{li.group(1)}</li>")
        elif not line.strip():
            flush_para()
        else:
            lines_buf.append(line)
    flush_para()
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def cmd_export(args) -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_root = Path(args.out)
    exported, skipped_private, skipped_other = [], 0, 0

    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT)
        if EXCLUDED_PARTS.intersection(rel.parts):
            skipped_other += 1
            continue
        fm, body = parse_fm(p)
        vis = str(fm.get("visibility", "unspecified"))
        if vis != "public":
            skipped_private += 1
            continue
        title = str(fm.get("title", p.stem))
        meta_rows = "".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in fm.items() if k not in ("body",))
        page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>body{{font-family:Georgia,serif;max-width:44em;margin:2em auto;padding:0 1em;line-height:1.55}}
table{{border-collapse:collapse}}td{{border:1px solid #ccc;padding:.25em .6em;font-size:.85em}}
footer{{margin-top:3em;padding-top:1em;border-top:1px solid #ccc;font-size:.8em;color:#555}}
.wikilink{{color:#0a58ca}}</style></head><body>
<h1>{html.escape(title)}</h1>
{render_body(body)}
<footer>
<p>Exported from This Wiki · record <code>{html.escape(str(fm.get('id', '?')))}</code>
· visibility gate: <code>{html.escape(vis)}</code> (record's own property)</p>
<details><summary>Record properties</summary><table>{meta_rows}</table></details>
<p>Stamp: {stamp} · This is a derived view; the wiki remains the sole system of record.</p>
</footer></body></html>"""
        dest = out_root / rel.with_suffix(".html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        exported.append(rel.as_posix())

    manifest = {
        "exported": stamp,
        "gate": "visibility == public (per-record frontmatter)",
        "counts": {"pages": len(exported), "not_public": skipped_private,
                   "excluded_paths": skipped_other},
        "pages": exported,
        "note": "Derived view only. _originals/ and governance trees are "
                "structurally excluded; no redaction beyond the visibility gate.",
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "EXPORT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exported {len(exported)} public pages -> {out_root}")
    print(f"withheld: {skipped_private} not-public records, "
          f"{skipped_other} structurally excluded files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    return cmd_export(args)


if __name__ == "__main__":
    raise SystemExit(main())

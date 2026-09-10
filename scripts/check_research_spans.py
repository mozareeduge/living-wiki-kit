#!/usr/bin/env python3
"""Deterministic citation-span checker for the research quarantine.

Engine 1 / LineageRAG-style verbatim-span verification, packaged for
the instantiated wiki. Zero LLM, zero network. Checks every track under
others/research/ (outside this repo, one level up):

  1. SOURCES.json is a flat array; entries carry id/url_or_api_query/
     authority_tier; tier in the protocol enum.
  2. Every source id is referenced by >=1 atomic inline marker in DOSSIER.md.
  3. No phantom markers (backlog tags, prose conventions, inline-code spans,
     and short noise tokens excluded).
  4. Every quoted span near a marker appears VERBATIM (normalized token
     sequence) in some raw capture - or in the instantiated wiki itself for quotes of
     canonical rules - or is classified URL-only (protocol-legal). A quote
     missing while the cited source has a same-named capture in raw/ is a
     FAILURE.

Invoked directly, or from validate_repo.py via --research.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent
DEFAULT_RESEARCH = WORKSPACE / "others" / "research"

TIER_ENUM = {
    "external-primary", "derivative-witness", "interpretive-synthesis", "candidate",
}
STOPLIST_TAGS = {
    "adopt", "adapt", "reject", "reject-with-reason", "defer", "candidate",
    "partial", "todo", "done",
    "p1", "p2", "p3", "p4", "p5", "p5b", "p6", "p7", "p8",
    "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "d10", "d11",
    "source-id", "sources", "link", "links", "wikilink", "optional", "required",
    "tbd", "note", "nb", "sic", "redacted", "unavailable",
}
MARKER_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_\-]{0,40})\]")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
QUOTE_RE = re.compile(r"[“\"]([^“”\"]{15,600})[”\"]|«([^»]{15,600})»")
TOKEN_RE = re.compile(r"[a-z0-9\u0600-\u06FF]+")
SPAN_CHECKABLE = {".txt", ".md", ".html", ".htm", ".nt", ".json", ".xml"}
HTMLISH = {".html", ".htm", ".xml"}
MAX_FILE_BYTES = 3_000_000
MAX_CORPUS_BYTES = 20_000_000
EDGE_JUNK = " \t\r\n:;,.\u2026()\u2014\u2013-–'\"“”«»*"


def norm_seq(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("\u200c", " ")
    return " ".join(TOKEN_RE.findall(text))


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data)


def strip_html(text: str) -> str:
    try:
        ext = _TextExtractor()
        ext.feed(text)
        return " ".join(ext.parts)
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", text)


def _decode_json_escapes(text: str) -> str:
    return re.sub(r"\\u([0-9a-fA-F]{4})",
                  lambda m: chr(int(m.group(1), 16)), text)


def load_capture_text(path: Path) -> str | None:
    try:
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if path.suffix.lower() == ".json":
        body = _decode_json_escapes(body)
    if path.suffix.lower() in HTMLISH:
        body = strip_html(body)
    return body


def clean_candidate(span: str) -> str:
    s = re.sub(r"\[[A-Za-z0-9][A-Za-z0-9_\-]{0,40}\]", " ", span)
    s = s.replace("**", " ").replace("__", " ")
    return s.strip(EDGE_JUNK)


def build_raw_corpus(track: Path) -> tuple[list[tuple[str, str]], set[str]]:
    corpus: list[tuple[str, str]] = []
    stems: set[str] = set()
    total = 0
    raw = track / "raw"
    if not raw.exists():
        return corpus, stems
    for p in sorted(raw.rglob("*")):
        if not p.is_file():
            continue
        stems.add(norm_seq(p.stem))
        if p.suffix.lower() not in SPAN_CHECKABLE:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        body = load_capture_text(p)
        if body is None:
            continue
        total += len(body)
        if total > MAX_CORPUS_BYTES:
            break
        corpus.append((p.name, norm_seq(body)))
    return corpus, stems


def build_wiki_corpus(wiki: Path, exclude: Path | None = None) -> list[tuple[str, str]]:
    corpus: list[tuple[str, str]] = []
    total = 0
    if not wiki.exists():
        return corpus
    excl_resolved = exclude.resolve() if exclude else None
    for p in sorted(wiki.rglob("*.md")):
        if ".git" in p.parts or "_search" in p.parts:
            continue
        if excl_resolved is not None:
            try:
                p.resolve().relative_to(excl_resolved)
                continue  # never treat the audited research tree as its own canon
            except ValueError:
                pass
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += len(body)
        if total > MAX_CORPUS_BYTES:
            break
        corpus.append((f"wiki:{p.relative_to(wiki).as_posix()}", norm_seq(body)))
    return corpus


def parse_sources(track: Path) -> tuple[list[dict] | None, list[str]]:
    errors: list[str] = []
    path = track / "SOURCES.json"
    if not path.exists():
        return None, [f"{track.name}: missing SOURCES.json"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, [f"{track.name}: SOURCES.json unparseable: {exc}"]
    if isinstance(data, dict) and isinstance(data.get("sources"), list):
        errors.append(f"{track.name}: SOURCES.json dict-wrapped (must be flat array)")
        data = data["sources"]
    if not isinstance(data, list):
        return None, [f"{track.name}: SOURCES.json is neither array nor dict-with-sources"]
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(f"{track.name}: SOURCES.json entry #{i} not an object")
            continue
        for key in ("id", "url_or_api_query", "authority_tier"):
            if not entry.get(key):
                errors.append(f"{track.name}: SOURCES.json entry #{i} missing '{key}'")
        tier = entry.get("authority_tier")
        if tier and tier not in TIER_ENUM:
            errors.append(f"{track.name}: entry #{i} bad authority_tier: {tier!r}")
    return data, errors


def dossier_markers(track: Path, known_ids: set[str]):
    errors: list[str] = []
    path = track / "DOSSIER.md"
    if not path.exists():
        return "", [], [f"{track.name}: missing DOSSIER.md"]
    raw_text = path.read_text(encoding="utf-8")
    text = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), raw_text)
    markers: list[tuple[str, int]] = []
    for m in MARKER_RE.finditer(text):
        base = m.group(1)
        probe = base.casefold()
        if probe in STOPLIST_TAGS:
            continue
        if len(base) < 3 and base not in known_ids:
            continue
        markers.append((base, text.count("\n", 0, m.start()) + 1))
    return raw_text, markers, errors


def check_track(track: Path, wiki_corpus: list[tuple[str, str]]) -> tuple[list[str], dict]:
    errors: list[str] = []
    stats = {"sources": 0, "markers": 0, "spans_ok": 0, "spans_wiki_ok": 0,
             "spans_url_only": 0, "spans_failed": 0}

    sources, errs = parse_sources(track)
    errors.extend(errs)
    if sources is None:
        return errors, stats
    ids = {str(s["id"]) for s in sources if s.get("id")}
    stats["sources"] = len(ids)

    text, markers, errs = dossier_markers(track, ids)
    errors.extend(errs)
    stats["markers"] = len(markers)

    used = {tok for tok, _ln in markers}
    for sid in sorted(ids - used):
        errors.append(f"{track.name}: source id never referenced inline: {sid}")
    seen: set[str] = set()
    for tok, ln in markers:
        if tok not in seen and tok not in ids:
            errors.append(f"{track.name}: phantom marker [{tok}] (line {ln})")
        seen.add(tok)

    corpus, capture_stems = build_raw_corpus(track)
    if not corpus:
        return errors, stats

    lines = text.splitlines()
    windows: set[int] = set()
    for _tok, ln in markers:
        windows.update(range(max(0, ln - 3), min(len(lines), ln + 2)))
    for ln in sorted(windows):
        for q in QUOTE_RE.finditer(lines[ln]):
            span = next((g for g in q.groups() if g), "")
            span = clean_candidate(span)
            snorm = norm_seq(span)
            if not snorm:
                continue
            if any(snorm in body for _n, body in corpus):
                stats["spans_ok"] += 1
                continue
            if any(snorm in body for _n, body in wiki_corpus):
                stats["spans_wiki_ok"] += 1
                continue
            src = next((s for s in sources
                        if isinstance(s.get("id"), str) and s["id"] in lines[ln]), {})
            sid = str(src.get("id") or "")
            if sid and norm_seq(sid) in capture_stems:
                stats["spans_failed"] += 1
                errors.append(
                    f"{track.name}: line {ln + 1} cites [{sid}] whose capture exists "
                    f"in raw/ but the quoted span is NOT verbatim in it: {span[:80]}...")
            else:
                stats["spans_url_only"] += 1
    return errors, stats


def collect_errors(research_root: Path, wiki: Path = REPO) -> list[str]:
    """Library entry point (used by validate_repo.py --research)."""
    if not research_root.exists():
        return [f"research root not found: {research_root}"]
    tracks = [p for p in sorted(research_root.iterdir())
              if p.is_dir() and (p / "SOURCES.json").exists()]
    if not tracks:
        return [f"no research tracks found under {research_root}"]
    wiki_corpus = build_wiki_corpus(wiki, exclude=research_root)
    errors: list[str] = []
    for track in tracks:
        errs, _stats = check_track(track, wiki_corpus)
        errors.extend(errs)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--research-root", default=str(DEFAULT_RESEARCH))
    ap.add_argument("--wiki", default=str(REPO))
    args = ap.parse_args()
    print(f"research root: {args.research_root}")
    errors = collect_errors(Path(args.research_root), Path(args.wiki))
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"FAILED: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("PASS: research provenance chain intact "
          "(flat arrays, atomic marker coverage, no phantoms, quotes verbatim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

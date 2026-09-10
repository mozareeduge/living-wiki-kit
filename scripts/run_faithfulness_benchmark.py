#!/usr/bin/env python3
"""Faithfulness benchmark for This Wiki — Engine 1 (evaluation loop).

Extends the QMD retrieval benchmark (30 questions,
00-system/configuration/semantic-benchmark-v1.1.0.json) with answer
generation and two-tier verification:

  Tier 1 (gates PASS/FAIL, deterministic, no LLM):
    - lexical support floor per atomic claim (containment + token order)
    - verbatim citation spans against the retrieved context windows
    - hallucinated .md path detection
  Tier 2 (diagnostic only, candidate-tier LLM judgments):
    - claim-to-passage entailment verdicts (supported/refuted/neutral)

Authority framing (SYSTEM_DESIGN.md / CLAUDE.md #6): generated answers are
candidate-tier inputs to verification, never evidence; retrieval scores
organize attention and are never evidence.

Provenance: developed and end-to-end proven in the research quarantine
(others/research/E1-evaluation-loop/) before this intake; see
FINAL_REPORT.md section 6 for pilot results and calibration notes.

Stages (each checkpointed under _audits/runtime/faithfulness/<stamp>/):
  retrieve -> generate -> verify -> entail -> report
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "00-system/configuration/semantic-benchmark-v1.1.0.json"
RUNS_DIR = ROOT / "_audits/runtime/faithfulness"

# ---------------------------------------------------------------- utilities

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in", "on",
    "at", "by", "for", "with", "about", "into", "from", "as", "is", "are",
    "was", "were", "be", "been", "being", "it", "its", "this", "that", "these",
    "those", "which", "who", "whom", "what", "where", "when", "how", "why",
    "can", "could", "may", "might", "will", "would", "shall", "should", "do",
    "does", "did", "done", "have", "has", "had", "not", "no", "yes", "also",
    "than", "so", "such", "their", "them", "they", "there", "here", "he",
    "she", "his", "her", "we", "us", "our", "you", "your", "i", "me", "my",
}
TOKEN_RE = re.compile(r"[a-z0-9\u0600-\u06FF]+")


def norm_tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.casefold().replace("\u200c", " "))


def content_words(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Run:
    def __init__(self, stamp: str | None, resume: bool = False):
        if resume and stamp:
            self.dir = RUNS_DIR / stamp
            if not self.dir.exists():
                raise SystemExit(f"cannot resume: no run dir {self.dir}")
        else:
            stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
            self.dir = RUNS_DIR / stamp
            self.dir.mkdir(parents=True, exist_ok=True)
        self.stamp = self.dir.name
        self.state_path = self.dir / "state.json"
        self.state = load_json(self.state_path) if self.state_path.exists() else {
            "run": self.stamp, "started": now_iso(), "stages": {},
        }

    def stage_done(self, name: str) -> bool:
        info = self.state["stages"].get(name)
        return bool(info and info.get("complete"))

    def mark_done(self, name: str, detail: dict | None = None) -> None:
        self.state["stages"][name] = {"complete": True, "at": now_iso(), **(detail or {})}
        dump_json(self.state_path, self.state)

    def path_for(self, name: str) -> Path:
        return self.dir / f"{name}.json"


# ---------------------------------------------------------------- retrieval

def _norm_path_key(s: str) -> str:
    return re.sub(r"-{2,}", "-", s.replace("\\", "/").strip().lower())


def build_disk_index(repo: Path) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for p in repo.rglob("*.md"):
        if ".git" in p.parts or "_search" in p.parts:
            continue
        rel = p.relative_to(repo).as_posix()
        idx.setdefault(_norm_path_key(rel), []).append(rel)
    return idx


def resolve_qmd_path(qmd_ref: str, disk_index: dict[str, list[str]]) -> str | None:
    rel = re.sub(r"^qmd://[^/]+/", "", qmd_ref.replace("\\", "/"))
    cands = disk_index.get(_norm_path_key(rel), [])
    return cands[0] if len(cands) == 1 else None


def window_text(path: Path, line_no: int, radius: int = 45, cap: int = 4200) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    lo = max(0, line_no - 1 - radius)
    hi = min(len(lines), line_no - 1 + radius)
    return "\n".join(lines[lo:hi])[:cap]


def cmd_retrieve(args, run: Run) -> None:
    if run.stage_done("retrieve"):
        # Guard here (not only in main) so programmatic callers cannot
        # overwrite a checkpointed stage accidentally.
        print("retrieve: already complete, skipping")
        return
    config = load_json(CONFIG)
    cases = config["cases"][: args.limit] if args.limit else config["cases"]
    top_k = args.top_k or config.get("top_k", 5)
    mode = args.engine  # "search" (BM25, deterministic) | "query" (hybrid, may hang)

    qmd_exe = shutil.which("qmd")
    if not qmd_exe:
        raise SystemExit("qmd executable not found on PATH")
    disk_index = build_disk_index(ROOT)

    out = []
    for i, case in enumerate(cases, 1):
        print(f"[retrieve {i}/{len(cases)}] {case['id']}", flush=True)
        rec = {"id": case["id"], "question": case["question"],
               "expected_suffixes": case.get("expected_suffixes", []),
               "results": [], "error": None}
        try:
            proc = subprocess.run(
                [qmd_exe, mode, case["question"], "--json", "-n", str(top_k)],
                cwd=ROOT, text=True, capture_output=True, timeout=args.timeout,
            )
            payload = json.loads(proc.stdout)
            for hit in payload[:top_k]:
                rel = resolve_qmd_path(hit.get("file", ""), disk_index)
                p = ROOT / rel if rel else None
                text = window_text(p, hit.get("line") or 1) if p else ""
                rec["results"].append({
                    "file": hit.get("file", ""),
                    "resolved": rel,
                    "line": hit.get("line"),
                    "title": hit.get("title"),
                    "score": hit.get("score"),
                    "context": text or hit.get("snippet", ""),
                })
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        out.append(rec)

    dump_json(run.path_for("retrieval"), out)
    errs = sum(1 for r in out if r["error"])
    empties = sum(1 for r in out if not r["error"] and not r["results"])
    run.mark_done("retrieve", {"engine": mode, "cases": len(out),
                               "errors": errs, "empty": empties})
    print(f"retrieve done ({mode}): {len(out)} cases, {errs} errors, {empties} empty")


# ---------------------------------------------------------------- generate

SYSTEM_PROMPT = """You are the answering component of an evaluation harness for a \
private scholarly knowledge wiki (a genetic archive of literary work).

Rules:
- Answer ONLY from the numbered context passages provided.
- Cite every load-bearing statement with the passage number(s) it rests on.
- In "span", copy an EXACT contiguous quote from the cited passage (verbatim).
- Decompose your answer into minimal atomic claims (one fact each, no pronouns \
without antecedents, no hedging filler).
- If the passages do not contain enough information, set "insufficient": true \
and explain briefly. NEVER guess, NEVER invent file names or paths.
- Respond with STRICT JSON only. No markdown fences, no commentary.

JSON schema:
{"answer": string,
 "insufficient": boolean,
 "citations": [{"passage": integer, "span": string}],
 "claims": [string]}"""


def build_user_prompt(case: dict) -> str:
    parts = [f"QUESTION: {case['question']}", "", "CONTEXT PASSAGES:"]
    for n, r in enumerate(case["results"], 1):
        body = r.get("context") or ""
        parts.append(f"\n--- PASSAGE {n} | title: {r.get('title')} | file: {r.get('file')} ---")
        parts.append(body.strip() or "(empty passage)")
    parts.append("\nProduce the STRICT JSON object now.")
    return "\n".join(parts)


def extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    s = text.find("{")
    depth = 0
    for i in range(s, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[s:i + 1])
    raise ValueError("no parseable JSON object in LLM output")


def cmd_generate(args, run: Run) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("openai package required (Hermes venv python)")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set in environment")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    retrieval = load_json(run.path_for("retrieval"))
    todo = [c for c in retrieval
            if any((r.get("context") or "").strip() for r in c.get("results", []))]
    if args.limit:
        todo = todo[: args.limit]

    answers = []
    if run.path_for("answers").exists():
        answers = load_json(run.path_for("answers"))
        done_ids = {a["id"] for a in answers}
        todo = [c for c in todo if c["id"] not in done_ids]

    for i, case in enumerate(todo, 1):
        print(f"[generate {i}/{len(todo)}] {case['id']} via {args.model}", flush=True)
        rec = {"id": case["id"], "model": args.model, "ok": False,
               "answer": None, "insufficient": None, "citations": [],
               "claims": [], "error": None}
        try:
            t0 = time.time()
            resp = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": build_user_prompt(case)}],
                temperature=0.0, max_tokens=args.max_tokens,
            )
            parsed = extract_json(resp.choices[0].message.content or "")
            rec.update({
                "ok": True,
                "answer": str(parsed.get("answer", "")).strip(),
                "insufficient": bool(parsed.get("insufficient", False)),
                "citations": parsed.get("citations", []) or [],
                "claims": [str(c) for c in (parsed.get("claims", []) or [])],
                "latency_s": round(time.time() - t0, 1),
            })
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        answers.append(rec)
        dump_json(run.path_for("answers"), answers)  # checkpoint every case

    oks = sum(1 for a in answers if a["ok"])
    run.mark_done("generate", {"model": args.model, "answered": oks,
                               "failed": len(answers) - oks})
    print(f"generate done: {oks}/{len(answers)} answered")


# ---------------------------------------------------------------- verify

def ordered_subsequence(needles: list[str], haystack: list[str]) -> bool:
    it = iter(haystack)
    return all(any(tok == h for h in it) for tok in needles)


def verify_claim(claim: str, chunks: list[str]) -> dict:
    cw = content_words(norm_tokens(claim))
    if not cw:
        return {"support": "degenerate", "overlap": 0.0, "ordered": False, "best_chunk": None}
    best = {"overlap": 0.0, "ordered": False, "best_chunk": None}
    for ci, chunk in enumerate(chunks):
        gt = norm_tokens(chunk)
        gset = set(gt)
        ov = sum(1 for t in cw if t in gset) / len(cw)
        ordered = ordered_subsequence(cw, gt) if ov >= 0.5 else False
        if ov > best["overlap"] or (ov == best["overlap"] and ordered and not best["ordered"]):
            best = {"overlap": round(ov, 3), "ordered": ordered, "best_chunk": ci}
    if best["overlap"] >= 0.75 and best["ordered"]:
        level = "supported"
    elif best["overlap"] >= 0.45:
        level = "partial"
    else:
        level = "unsupported"
    return {"support": level, **best}


MD_PATH_RE = re.compile(r"[A-Za-z0-9_\-./\u200c]+\.md\b")


def cmd_verify(args, run: Run) -> None:
    retrieval = {c["id"]: c for c in load_json(run.path_for("retrieval"))}
    answers = load_json(run.path_for("answers"))

    out = []
    for a in answers:
        case = retrieval.get(a["id"], {})
        chunks = [r.get("context") or "" for r in case.get("results", [])]
        chunk_norm = [" ".join(norm_tokens(c)) for c in chunks]

        vrec = {"id": a["id"], "ok": a.get("ok", False),
                "insufficient": a.get("insufficient"),
                "n_claims": len(a.get("claims", [])), "claims": [],
                "citations": [], "paths": [], "unresolved_passages": 0}
        if not a.get("ok"):
            vrec["error"] = a.get("error")
            out.append(vrec)
            continue

        for claim in a.get("claims", []):
            vrec["claims"].append({"claim": claim, **verify_claim(claim, chunks)})

        for cit in a.get("citations", []):
            pi = cit.get("passage")
            span = str(cit.get("span", "")).strip()
            entry = {"passage": pi, "span": span[:160]}
            if not span:
                entry["status"] = "NO_SPAN"
            elif not isinstance(pi, int) or pi < 1 or pi > len(chunks):
                entry["status"] = "BAD_PASSAGE_REF"
            else:
                snorm = " ".join(norm_tokens(span))
                entry["status"] = "OK" if snorm and snorm in chunk_norm[pi - 1] else "SPAN_NOT_FOUND"
            vrec["citations"].append(entry)

        mentioned = {m.replace("\\", "/").lstrip("./")
                     for m in MD_PATH_RE.findall(a.get("answer") or "")}
        known_files, unresolved = set(), 0
        for r in case.get("results", []):
            if r.get("resolved"):
                known_files.add(r["resolved"].lower())
            else:
                unresolved += 1
        for p in sorted(mentioned):
            exists = (ROOT / p).exists()
            known = p.lower() in known_files
            vrec["paths"].append({
                "path": p,
                "status": "OK" if exists else ("UNRESOLVED_RETRIEVED" if known else "HALLUCINATED"),
            })
        vrec["unresolved_passages"] = unresolved
        out.append(vrec)

    dump_json(run.path_for("verification"), out)
    tot = sum(v["n_claims"] for v in out)
    sup = sum(1 for v in out for c in v["claims"] if c["support"] == "supported")
    par = sum(1 for v in out for c in v["claims"] if c["support"] == "partial")
    hall = sum(1 for v in out for p in v["paths"] if p["status"] == "HALLUCINATED")
    bad_span = sum(1 for v in out for c in v["citations"]
                   if c["status"] in ("SPAN_NOT_FOUND", "BAD_PASSAGE_REF"))
    run.mark_done("verify", {"claims": tot, "supported": sup, "partial": par,
                             "hallucinated_paths": hall, "bad_citation_spans": bad_span})
    print(f"verify done: {tot} claims, {sup} supported, {par} partial, "
          f"{hall} hallucinated paths, {bad_span} bad citation spans")


# ---------------------------------------------------------------- entail

ENTAIL_SYSTEM = """You are the entailment component of an evaluation harness for a \
scholarly wiki. You judge ONE atomic claim against ONE source passage.

Verdicts:
- "supported": a careful reader of ONLY this passage would accept the claim as stated.
- "refuted": the passage contradicts the claim.
- "neutral": neither - the claim asserts something the passage does not establish.

Be strict about facts (names, paths, numbers, attributions); be fair about \
paraphrase and word order. Respond with STRICT JSON only:
{"verdict": "supported|refuted|neutral", "confidence": <number 0..1>}"""


def cmd_entail(args, run: Run) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("openai package required (Hermes venv python)")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set in environment")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    retrieval = {c["id"]: c for c in load_json(run.path_for("retrieval"))}
    verification = load_json(run.path_for("verification"))

    out_path = run.path_for("entailment")
    out = load_json(out_path) if out_path.exists() else []
    done = {(r["id"], r["claim"]) for r in out}

    todo = [(v["id"], c) for v in verification if v.get("ok") for c in v["claims"]
            if (v["id"], c["claim"]) not in done]
    if args.limit:
        todo = todo[: args.limit]

    for i, (cid, item) in enumerate(todo, 1):
        case = retrieval.get(cid, {})
        chunks = [r.get("context") or "" for r in case.get("results", [])]
        ci = item.get("best_chunk")
        passage = chunks[ci] if isinstance(ci, int) and 0 <= ci < len(chunks) else ""
        print(f"[entail {i}/{len(todo)}] {cid}", flush=True)
        rec = {"id": cid, "claim": item["claim"], "ok": False,
               "verdict": None, "confidence": None, "error": None}
        try:
            resp = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "system", "content": ENTAIL_SYSTEM},
                          {"role": "user",
                           "content": f"CLAIM: {item['claim']}\n\nPASSAGE:\n{passage[:3500]}"}],
                temperature=0.0, max_tokens=120,
            )
            parsed = extract_json(resp.choices[0].message.content or "")
            verdict = str(parsed.get("verdict", "")).lower()
            if verdict not in ("supported", "refuted", "neutral"):
                raise ValueError(f"bad verdict: {verdict!r}")
            conf = parsed.get("confidence")
            rec.update({"ok": True, "verdict": verdict,
                        "confidence": round(float(conf), 2)
                        if isinstance(conf, (int, float)) else None})
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        out.append(rec)
        dump_json(out_path, out)

    oks = sum(1 for r in out if r["ok"])
    sup = sum(1 for r in out if r.get("verdict") == "supported")
    ref = sum(1 for r in out if r.get("verdict") == "refuted")
    run.mark_done("entail", {"model": args.model, "judged": oks,
                             "failed": len(out) - oks, "supported": sup, "refuted": ref})
    print(f"entail done: {oks}/{len(out)} judged, {sup} supported, {ref} refuted")


# ---------------------------------------------------------------- report

def cmd_report(args, run: Run) -> None:
    retrieval = {c["id"]: c for c in load_json(run.path_for("retrieval"))}
    answers = {a["id"]: a for a in load_json(run.path_for("answers"))}
    verification = load_json(run.path_for("verification"))
    entail_path = run.path_for("entailment")
    entail_map: dict[tuple[str, str], dict] = {}
    if entail_path.exists():
        for r in load_json(entail_path):
            if r.get("ok"):
                entail_map[(r["id"], r["claim"])] = r

    rows = []
    agg = {"cases": len(verification), "answered": 0, "insufficient": 0,
           "claims_total": 0, "supported": 0, "partial": 0, "unsupported": 0,
           "citations_total": 0, "citations_ok": 0, "paths_hallucinated": 0,
           "paths_unresolved": 0}
    for v in verification:
        aid = v["id"]
        exp = retrieval.get(aid, {}).get("expected_suffixes", [])
        got = [r.get("file", "") for r in retrieval.get(aid, {}).get("results", [])]
        exp_hits = sum(1 for e in exp
                       if any(g.replace("\\", "/").lower().endswith(e.lower()) for g in got))
        n = v["n_claims"]
        sup = sum(1 for c in v["claims"] if c["support"] == "supported")
        par = sum(1 for c in v["claims"] if c["support"] == "partial")
        uns = sum(1 for c in v["claims"] if c["support"] == "unsupported")
        cit_ok = sum(1 for c in v["citations"] if c["status"] == "OK")
        hall = sum(1 for p in v["paths"] if p["status"] == "HALLUCINATED")

        agg["claims_total"] += n
        agg["supported"] += sup
        agg["partial"] += par
        agg["unsupported"] += uns
        agg["citations_total"] += len(v["citations"])
        agg["citations_ok"] += cit_ok
        agg["paths_hallucinated"] += hall
        agg["paths_unresolved"] += int(v.get("unresolved_passages", 0))
        if v.get("ok"):
            agg["answered"] += 1
        if v.get("insufficient"):
            agg["insufficient"] += 1

        denom = n if n else 1
        ent = [entail_map[(aid, c["claim"])] for c in v["claims"]
               if (aid, c["claim"]) in entail_map]
        rows.append({
            "id": aid, "answered": bool(v.get("ok")),
            "insufficient": bool(v.get("insufficient")),
            "claims": n, "supported": sup, "partial": par, "unsupported": uns,
            "faithfulness": round((sup + 0.5 * par) / denom, 3),
            "citations": f"{cit_ok}/{len(v['citations'])}",
            "hallucinated_paths": hall,
            "entail_sup": sum(1 for e in ent if e["verdict"] == "supported"),
            "entail_ref": sum(1 for e in ent if e["verdict"] == "refuted"),
            "entail_neu": sum(1 for e in ent if e["verdict"] == "neutral"),
            "retrieval_expected_hits": f"{exp_hits}/{len(exp)}",
        })

    with_claims = [r for r in rows
                   if r["answered"] and not r["insufficient"] and r["claims"] > 0]
    mean_faith = (round(sum(r["faithfulness"] for r in with_claims) / len(with_claims), 3)
                  if with_claims else None)
    cit_prec = (round(agg["citations_ok"] / agg["citations_total"], 3)
                if agg["citations_total"] else None)
    passed = bool(mean_faith is not None and mean_faith >= args.min_faithfulness
                  and agg["paths_hallucinated"] == 0
                  and cit_prec is not None and cit_prec >= args.min_citation_precision)

    entail_agg = {
        "tier": "candidate (LLM-judged, diagnostic only)",
        "judged": sum(r["entail_sup"] + r["entail_ref"] + r["entail_neu"] for r in rows),
        "supported": sum(r["entail_sup"] for r in rows),
        "refuted": sum(r["entail_ref"] for r in rows),
        "neutral": sum(r["entail_neu"] for r in rows),
    }
    report = {
        "run": run.stamp, "generated": now_iso(),
        "model": next(iter(answers.values()), {}).get("model"),
        "aggregates": agg, "mean_faithfulness": mean_faith,
        "citation_precision": cit_prec,
        "thresholds": {"min_mean_faithfulness": args.min_faithfulness,
                       "max_hallucinated_paths": 0,
                       "min_citation_precision": args.min_citation_precision},
        "passed": passed, "entailment": entail_agg,
        "authority_note": (
            "Two verification tiers. Tier 1 gates PASS/FAIL mechanically "
            "(lexical support floor, verbatim citation spans, path existence). "
            "Tier 2 entailment verdicts are candidate-tier diagnostics and never gate. "
            "Retrieval scores organize attention and are never evidence."),
        "rows": rows,
    }
    dump_json(run.dir / "report.json", report)

    md = [
        "# Faithfulness Benchmark Report (Engine 1)", "",
        f"- Run: `{run.stamp}` · Generated: {report['generated']} · Model: `{report['model']}`",
        f"- Result: **{'PASS' if passed else 'FAIL'}** "
        f"(mean faithfulness {mean_faith}, citation precision {cit_prec}, "
        f"hallucinated paths {agg['paths_hallucinated']})",
        f"- Tier-2 entailment (candidate): {entail_agg['supported']} supported / "
        f"{entail_agg['refuted']} refuted / {entail_agg['neutral']} neutral "
        f"of {entail_agg['judged']}", "",
        f"> {report['authority_note']}", "",
        "| ID | ans | insuff | claims | supp | part | unsup | faith | cites | hall | retr-hits |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['id']} | {'y' if r['answered'] else 'n'} | "
            f"{'y' if r['insufficient'] else 'n'} | {r['claims']} | {r['supported']} | "
            f"{r['partial']} | {r['unsupported']} | {r['faithfulness']} | "
            f"{r['citations']} | {r['hallucinated_paths']} | "
            f"{r['retrieval_expected_hits']} |")
    (run.dir / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    run.mark_done("report", {"passed": passed})
    print(f"report written: {run.dir / 'REPORT.md'} — {'PASS' if passed else 'FAIL'}")


# ---------------------------------------------------------------- cli

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", help="existing run stamp to operate on")
    sub = ap.add_subparsers(dest="stage", required=True)

    p = sub.add_parser("retrieve")
    p.add_argument("--limit", type=int)
    p.add_argument("--top-k", type=int)
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--engine", choices=["search", "query"], default="search",
                   help="search=BM25 deterministic (default; query/vsearch hang on some setups)")

    p = sub.add_parser("generate")
    p.add_argument("--model", default="openai/gpt-4o-mini")
    p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=1200)

    sub.add_parser("verify")

    p = sub.add_parser("entail")
    p.add_argument("--model", default="openai/gpt-4o-mini")
    p.add_argument("--limit", type=int)

    p = sub.add_parser("report")
    p.add_argument("--min-faithfulness", type=float, default=0.85)
    p.add_argument("--min-citation-precision", type=float, default=0.80)

    args = ap.parse_args()
    run = Run(args.run, resume=bool(args.run))

    stages = [args.stage] if args.stage != getattr(main, "__allstage__", "") else []
    if args.stage == "retrieve":
        if run.stage_done("retrieve"):
            print("retrieve: already complete, skipping (use a new stamp to rerun)")
            return 0
        cmd_retrieve(args, run)
    elif args.stage == "generate":
        cmd_generate(args, run)
    elif args.stage == "verify":
        cmd_verify(args, run)
    elif args.stage == "entail":
        cmd_entail(args, run)
    elif args.stage == "report":
        cmd_report(args, run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

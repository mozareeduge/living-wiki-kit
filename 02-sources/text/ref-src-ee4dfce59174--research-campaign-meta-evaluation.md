# Extracted from: META_EVALUATION.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: ee4dfce59174648278cb3e0a6e8619277ffe2c6a7e4b7fd5c72ab7ee3654154c
- original_path: _originals/ref-src-ee4dfce59174--research-campaign-meta-evaluation.md
- extraction_quality: full
- language: en

---

# META-EVALUATION — Research Setup Performance Log

Running retrospective on the evidence-governed research protocol itself.
Updated continuously during Waves 1–2. Referenced from README.md — do not archive
or fold these into track dossiers; they govern future runs.

---

## Defects observed (with evidence)

**D1 — Budget exhaustion at the WRITE step (T3, critical).**
Subagent spent its 50-call budget downloading and verifying all normative specs,
then died with zero deliverables. All research value nearly lost; recovered only
because raw files survived on disk and the orchestrator hand-wrote the dossier.
Evidence: deleg_e5b0b5bd task-3 report ("deliverables NOT yet written"), transcript
`...\cache\delegation\live\deleg_e5b0b5bd\task-2.log`.

**D2 — Upstream rate-limit kill at final summarization (T1, critical).**
Agent completed ~23 min / 50 calls of genuine research (44 raw files captured),
then the provider pool returned 429 on the summary turn; no dossier written.
Evidence: deleg_e5b0b5bd task-0 report (429, 'stealth/ox-alpha temporarily
rate-limited upstream'), transcript task-0.log.

**D3 — Concurrency amplifies D2.**
Three heavy agents ran simultaneously on one shared model pool — exactly the
condition that produces upstream 429s. Wave 1 lost 2 of 3 agents to failure;
both failures came at the END of long runs (maximum waste).

**D4 — Missing environment preflight.**
execute_code python had pip disabled (`No module named pip`); pymupdf needed
manual ensurepip + install mid-analysis. Cost: one failed call + extra round-trip.
Any PDF/HTML-heavy track hits this.

**D5 — Terminal parser hard-block on complex grep pipelines.**
A legitimate read-only grep pipeline was unconditionally blocked ("parser limit");
had to fall back to Python. Not fatal, but the protocol should default to
execute_code for text extraction instead of shell one-liners.

**D6 — Bot-blocked authoritative sources (PREMIS/loc.gov 403; w3id RO-Crate 404;
LRM-ER machine-readable endpoints error-shell).**
Negative findings were correctly recorded (good), but no fallback-mirror step
exists, so coverage silently thins where institutions block automation.

**D7 — Citation-marker inconsistency (T2, minor).**
SOURCES.json fully populated, but inline `[S#]` markers absent at some dossier
mentions (subagent self-reported). Weakens the provenance chain the protocol
promises.

**D8 — Approval-path ambiguity (process, minor).**
clarify() timed out on the setup-approval question; proceeding on best judgment
was right here (user had pre-authorized), but the protocol should state the
default explicitly rather than improvise each time.

**D9 — Pre-P6 briefings lack inline [S#] markers (T1, RESOLVED 2026-08-25).**
T1 dossier verified complete (29KB, four sections, 42-entry SOURCES.json) but had
0 inline citation markers — it was synthesized before P6 was adopted. **Closed by the
provenance-repair pass:** T1 fully marked (42/42), T2 normalized + grounded (37/37),
T3 schema-normalized with missing TEI captures fetched and PREMIS fallback exhausted (19/19),
T4 gaps anchored (30/30); T5/T6 were already complete. Scripted verification confirms zero
unreferenced source IDs and zero phantom markers across all six tracks.

## Improvements adopted (binding for Wave 2 onward)

**P1 — Checkpoint-first writing (fixes D1/D2).**
Every research agent MUST write deliverables incrementally: SOURCES.json after
each source batch, DOSSIER.md section-by-section as completed — never leave all
writing to the end of budget. An interrupted run must always leave usable partial
output. (Being enforced verbatim in Wave-2 briefs.)

**P2 — Concurrency cap 2 (fixes D3).**
Max 2 research agents in flight at once on this provider; third queues. Slower
wall-clock, dramatically lower tail-risk of losing whole batches to 429s.

**P3 — Environment preflight step (fixes D4).**
Before any wave: verify python -m pip works, install pymupdf + requests once,
confirm curl/jq presence. One cheap command block, run once per session.

**P4 — Text extraction via execute_code/Python by default (fixes D5).**
HTML→text, JSON parsing, PDF extraction go through scripted Python; shell pipes
reserved for trivial ops.

**P5 — Blocked-source fallback ladder (fixes D6).**
On 403/404 of a primary authority: (1) official mirror domain, (2) web.archive.org
snapshot, (3) record as negative finding and move on — never silent thinning.
P5b (from T1 finisher): HTTP 200 does not mean right target — verify page identity
after every fetch (ests.org now serves a thoracic-surgery society; a DHQ URL
served an unrelated OCR article). Domain collisions and stale URLs are common;
title/scope check is part of capture, not review.

**P6 — Mandatory inline [S#] markers (fixes D7).**
Dossier contract now requires every load-bearing statement to carry its SOURCES.json
marker inline. T1/T2 dossiers get patched to comply during review pass if needed.

**P7 — Stated approval default (fixes D8).**
Standing rule recorded: if an approval question times out AND the action is
already covered by prior user authorization, proceed and say so plainly; otherwise
stop and ask again next turn.

**P8 — Quotation discipline (fixes D11).**
Inside quotation marks only text that appears verbatim in a capture; translations
must be marked "(translation)"; never place your own coinage in quotes near a
citation marker. Enforced mechanically by
`E1-evaluation-loop/check_citation_spans.py`.

## Recovery patterns proven (keep using)

- **Orchestrator-finisher:** when a child dies post-research pre-write, dispatch a
  narrow synthesizer over the local raw corpus (worked for T1) or hand-write from
  local captures (worked for T3). Raw-files-on-disk is the insurance policy —
  hence P1 makes even raw capture incremental.
- **Quarantine discipline held:** zero writes to the three wikis across all runs.

**D11 — Quote-mark hygiene defects (T1, RESOLVED 2026-08-25).**
Surfaced by the first mechanical citation-span audit (Engine 1): (a) an unmarked
English *translation* of the APCG 2027 congress title presented inside quotation
marks as if verbatim — the capture proves only the Portuguese/French title;
(b) the dossier's own coined phrase ("static publication layer") placed in
quotation marks beside a citation, fabricating a quotation signal. Repair: dedicated
congress page captured (raw/apcg-2027.html, HTTP 200, title/dates identity-verified),
new source entry [item-apcg-2027], dossier corrected to quote the captured title with
the translation explicitly marked, coinage de-quoted.

**D10 — Connection-error storm killed two children early (T4-finisher & T6 at 9 API calls each).**
Distinct from rate-limiting: provider connection failures, retried 3x then abort.
Recovery: orchestrator hand-completed both dossiers from checkpointed local
captures (~1h orchestrator work total). Pattern confirmed: children are expendable
if raw captures land on disk continuously; the orchestrator is the durable finisher.

## Confirmation of design under fire

**C1 — P1 checkpoint-first vindicated (T4, second rate-limit kill).**
T4's agent died at its summary turn exactly like T1's original run (same upstream
429), but this time the dossier was ~40% written with 26 sourced entries and 27 raw
captures on disk. Recovery cost dropped from "orchestrator hand-writes whole dossier"
(T3) / "full synthesis job" (T1) to a narrow section-finisher. P1 is confirmed as
the single most valuable rule in this protocol.

## Open questions for the skill version

- Whether a lighter/faster model can be pinned for subagent final summaries
  (config-level setting, not per-call) to reduce 429 surface.
- Whether SOURCES.json should migrate to JSONL for append-friendly checkpoints.
- Cron-based standing monitors (weekly arXiv/Crossref sweeps) — deferred until
  Wave-2 quality review.


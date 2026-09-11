# Extracted from: FINAL_REPORT.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: aca75aca2552f699e13f21d55453b8154f3fe4167ec6c5d993e3b7547ee33f96
- original_path: _originals/ref-src-aca75aca2552--research-campaign-final-report.md
- extraction_quality: full
- language: en

---

# FINAL REPORT — Six-Track Research Campaign & Convergent Phase

**Campaign window:** 2026-08-25 (single-day snapshot) · **Workspace:** `others/research/`
(quarantine) · **Protocol:** evidence-governed v2.0.0 (`mozare-research-protocol` skill)
**Authority level of this document:** interpretive synthesis (level 6), built from six
level-6 dossiers whose statements are typed in per-track SOURCES.json. Candidate-tier
inferences are marked *[cand]*.

---

## 1 · Provenance of this process

| Session | Contribution |
|---|---|
| `20260825_142859_74f07e` | Repo orientation; campaign design; T1–T3 wave 1 |
| (wave-2 subagent runs) | T4–T6 dispatch, kills, orchestrator finishers |
| `20260825_194946_4cbb66` | Provenance repair pass A1–A4; skill v2.0.0; full evaluation delivery; Engine-1 approval |
| (this session) | Engine 1 built & proven end-to-end; citation-span audit; D11 repair; this convergence |

## 2 · The campaign at a glance

- **Six tracks completed** under the four-section dossier contract:
  T1 digital genetic criticism · T2 PKM/agentic-wiki landscape ·
  T3 ontology/provenance standards · T4 OOO-in-the-wild ·
  T5 AI-scholarship & evidence governance · T6 artistic-research living archives.
- **185 typed sources**, every one referenced atomically inline (423 markers);
  ~200 raw captures on disk; negative findings recorded in all six tracks.
- **Machine-verified end state:** flat-array SOURCES.json everywhere, zero unreferenced
  IDs, zero phantom markers, 52 dossier quotes verified verbatim inside raw captures,
  zero span failures (`E1-evaluation-loop/check_citation_spans.py`, exit 0).
- Quarantine discipline held across every run: **zero uninvited writes to the three wikis.**

## 3 · The convergent verdict

Three independent methods (bibliometrics, structured-API sweeps, normative-spec reading)
across six fields converge on one shape:

> **Mozare's governance layer is ahead of every surveyed system** — flagship genetic
> editions (BDMP/Faust/Woolf Online), the agentic-PKM genre, standards bodies
> (Wikibase/PREMIS/CIDOC-CRM/SKOS/PROV-O/TEI), AI-RAG products and frameworks, and
> artistic-research platforms (RC/JAR/Ruukku/VMQ). No surveyed system combines
> checksummed immutable originals, an eight-level authority hierarchy over assertions,
> permission-qualified claims, genesis-preserving typed relations, and multi-agent patch
> governance.
>
> **He is behind exactly where governance meets an outside**, and nowhere else:
> interchange formats (T1/T3), public readership (T1/T6), agent-facing surfaces (T2),
> evaluation loops (T5), succession planning (T6).

T5's sharpest single formulation: *the ecosystem standardized citations; nobody
standardized authority.* The 2026 research frontier (LineageRAG verbatim spans,
FActScore-lineage audits, EvoTrustRAG conflict tagging) is converging on mechanisms he
already runs manually.

## 4 · Unified improvement backlog → four engines

All adopt/adapt items from the six dossiers deduplicate into exactly four additive
engines (protocol §8 ordering by leverage-per-risk). None touches the authority model.

**Engine 1 — Evaluation loop** *(built this session, quarantine-proven)*
Faithfulness harness over the QMD benchmark (generate answers + atomic claims;
deterministic lexical support floor + verbatim-span citation checks + candidate-tier LLM
entailment as diagnostic-only second tier); LineageRAG-style span checks integrable into
`validate_repo.py`; FActScore-lineage spot audits on claim records. *(Serves T5-1/2/3.)*

**Engine 2 — Interchange exports**
PROV-O profile for the eight relations; SKOS export of controlled vocabularies;
TEI P5 export path (`teiHeader/msDesc`, `sourceDoc/surface/zone`,
`listChange/change[@ordered]`); PREMIS-shaped fixity blocks in source records;
Wikibase-style rank on claims; E13-pattern naming in claim frontmatter; RO-Crate 1.3
conformance check. *(Serves T3-1..5, T1-1.)*

**Engine 3 — Agent surfaces, views & proposal queues**
`AGENTS.md`/minimal MCP honoring authority tiers so any harness inherits governance
instead of being locked out; Obsidian `.base` views over existing frontmatter (zero
schema change); embedding-fed typed-edge `_proposals/` queue (level-7 authority by
construction); shared versioned `wiki-spec/` package across the three wikis; CRediT-style
typed contribution roles on handoff records. *(Serves T2-1/2/4/5, T5-5, T4-4.)*

**Engine 4 — Preservation, publication & succession**
Static public valve gated on `visibility:` with redaction rules; VMQ-style succession
records per object family; Webrecorder/browsertrix capture pipeline turning cited pages
into checksummed derivatives; editorial-charter versioning; one-way RC/JAR-compatible
exposition export path. *(Serves T1-3/4, T6-1/2/3, T2-6.)*

**Standing rejects (do not revisit without new evidence):** RDF/graph-DB/JSON-LD or
vector-store as system of record · engine migrations (Logseq/Tana/Anytype/Monoskop/
Are.na) · full CIDOC-CRM event modelling · claim-ledger rewrites à la claude-obsidian ·
spaced repetition over archive notes · IIIF image-server infrastructure (deferred until
image-heavy intake exists) · retrieval-score display in user-facing answers (kotaemon
pattern — violates "scores are never evidence").

**Theory-field intake shelves (T4, wiki-side):** more-than-human-design uptake cluster;
hyperobject-critique dossier; AI-era rereading watch bridging to AI-philology;
term-disambiguation records protecting "ontograph" vocabulary.

## 5 · Cross-track negative findings (searched and not found)

- No PKM tool combines checksummed originals + authority grading + permissions. [T2]
- No flagship genetic-criticism project governs AI-mediated intake or grades
  machine-authored content below human-reviewed levels. [T1] *[generalized absence =
  candidate-tier]*
- No scholarly standard grades assertion authority; CRM has no first-class version-of
  property. [T3]
- No serious computational implementation of OOO exists; Wikidata coverage near-empty;
  no recent peer-reviewed "state of OOO" reassessment. [T4]
- No faithfulness/attribution evaluation has ever been run over QMD answers — the one
  behind-criterion in T5 (now closed in quarantine by Engine 1's pilot). [T5]
- No surveyed artistic-research platform governs provenance; none plans succession. [T6]
- Documented bot-walls thinned coverage at loc.gov/PREMIS (403), Rhizome (Cloudflare),
  Ruukku (Anubis), larvalsubjects (403), ests.org (domain collision). [multiple]

## 6 · Evaluation of the research setup itself

The campaign audited its own process continuously (META_EVALUATION.md): eleven defects
(D1–D11), eight binding counter-rules (P1–P8), one live-fire confirmation (C1).

**What the setup proved:** checkpoint-first writing is the single most valuable rule
(recovery cost dropped from whole-dossier rewrite to narrow section-finisher when it was
in force); children are expendable when raw captures land on disk continuously; the
orchestrator is the durable finisher; quarantine discipline survives contact with
aggressive automation.

**What the setup caught about itself:** its own integrity narrative lagged disk state
once (D9-class overclaim, fixed by scripted verification); its own quote-mark hygiene had
three defects (D11, found by Engine 1's mechanical audit, repaired same day). The
evaluation loop now enforces both mechanically.

**Engine-1 pilot results (honest):**
- Retrieval: BM25-only baseline finds expected docs in 10/30 cases (test set designed
  for hybrid+rerank; index 28 days stale; benchmark file self-matches — three concrete
  benchmark-design findings). **Environment blocker discovered: `qmd query` and
  `vsearch` hang on this machine — the existing benchmark script cannot currently run.**
- Generation+verification (6-case pilot, gpt-4o-mini): citation precision 1.0, zero
  hallucinated paths, zero fully-unsupported claims; Tier-1 lexical gate honestly FAILs
  at ≈0.62 < 0.85 because paraphrase is invisible to pure lexical matching;
  Tier-2 entailment confirmed 12/12 sampled "partial" claims as entailed. Conclusion:
  the two-tier design works; Tier-1 thresholds need calibration once hybrid retrieval
  is restored (`qmd update` + hang diagnosis).

## 7 · Verification state of this report

| Claim class | Status |
|---|---|
| Track verdicts & backlog contents | read directly from the six DOSSIER.md files this session |
| Provenance completeness | scripted audit, exit 0, 2026-08-25 (185/185 sources marked) |
| Quote fidelity | 52 spans verbatim-in-capture; 30 URL-only (protocol-legal); 0 failures |
| Engine-1 behavior | executed end-to-end this session; artifacts under `E1-evaluation-loop/runs/` |
| Strategic verdict | synthesis of six dossiers — interpretive-synthesis tier, not independently re-measured |

## 8 · Next operations (awaiting approval — nothing enters the wikis without an intake patch)

1. **Approve Engine-1 intake** into `mozare-wiki` on a branch: add
   `run_faithfulness_benchmark.py` (adapted paths) + optional `--research` hook spec for
   `validate_repo.py`; fix the environment blockers first (`qmd update`; diagnose the
   `qmd query`/`vsearch` hang).
2. Approve the T4 intake shelves and T2 `.base` views as the next low-risk additions.
3. Optional: schedule standing monitors (weekly arXiv/Crossref sweeps) — deferred by
   META_EVALUATION until after this review; this report clears that condition.

---
*Generated by the convergence pass of 2026-08-25. Sources: six track dossiers +
LANDSCAPE_MAP.md + META_EVALUATION.md + E1-evaluation-loop run artifacts. Per protocol,
this file lives in the research quarantine; intake into any wiki requires an approved
patch manifest.*


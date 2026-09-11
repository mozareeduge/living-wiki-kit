# Extracted from: README.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: 702ab37396b6d8936d4c1ab896e6914c19fac08176311697f9b77cf324753add
- original_path: _originals/ref-src-702ab37396b6--research-campaign-readme.md
- extraction_quality: full
- language: en

---

# Mozare External Research Workspace

> **META-EVALUATION.md** (setup defects & binding improvements) lives beside this
> README and governs every run — read it before executing any track.

Quarantine zone for external landscape research. Nothing here enters
`mozare-wiki/`, `casebook-wiki/`, or `OOO-living-wiki/` without an
explicitly approved intake patch.

## Protocol (evidence-governed research)

Mirrors mozare-wiki SYSTEM_DESIGN.md:

1. **Authority typing on arrival.** Every imported statement is typed using
   the 8-level hierarchy (original > verified external primary > author
   confirmation > accepted canonical record > derivative witness >
   interpretive synthesis > candidate/AI-generated > generated view).
   Fluency, repetition, or similarity never upgrades a source.
2. **Structured sweep first** (Crossref / OpenAlex / Wikidata SPARQL /
   GitHub API / arXiv), browser reading only for survivors. Every query
   string recorded in `SOURCES.json`.
3. **Four mandatory dossier sections:** (a) landscape map, (b) where
   Mozare's work sits (explicit criteria), (c) improvement backlog tagged
   adopt/adapt/reject-with-reason, (d) negative findings — searched and
   not found stays visible.
4. **Provenance chain per fact:** statement → source record (SOURCES.json
   entry) → retrievable URL or raw copy under `raw/`.
5. **Dossiers are interpretive synthesis (level 6).** Facts inside them are
   only as strong as their typed sources. Candidate inferences are marked.

## Layout

```
T1-genetic-criticism-digital/
T2-pkm-landscape/
T3-ontology-provenance-standards/
T4-ooo-in-the-wild/
T5-ai-scholarship-evidence-governance/
T6-artistic-research-living-archives/
LANDSCAPE_MAP.md          <- cross-track synthesis (written last)
```

Each track folder contains at minimum:
- `DOSSIER.md` — findings in the four-section format
- `SOURCES.json` — typed provenance register
- `raw/` — saved copies of decisive pages (optional but encouraged)

## Waves

- Wave 1: T1, T2, T3 (wiki-improvement value first)
- Wave 2: T4, T5, T6

## Status

- [x] T1 dossier (DOSSIER.md 29KB four sections + SOURCES.json 42 entries; D9 marker debt)
- [x] T2 dossier (DOSSIER.md + SOURCES.json 37 entries + raw/28)
- [x] T3 dossier (written by orchestrator from local spec captures)
- [x] LANDSCAPE_MAP.md (Wave 1 synthesis)
- [x] T4 dossier (killed by 429 at ~40% → finished by orchestrator from local captures; markers clean)
- [x] T5 dossier (complete: citation gate 38/38, verdict ahead-on-governance/behind-on-evals)
- [x] T6 dossier (connection-storm kill at 9 calls → completed by orchestrator from local captures; markers clean)
- [x] LANDSCAPE_MAP.md updated (Wave 2 + six-track strategic summary)
- [x] Protocol persisted as Hermes skill `mozare-research-protocol` (v2.0.0)
- [x] Provenance repair pass A1–A4 + full three-part evaluation delivered
- [x] E1-evaluation-loop/ — Engine 1 built & proven end-to-end in quarantine
      (faithfulness benchmark, two-tier verification; pilot run artifacts under runs/)
- [x] Citation-span audit across all six tracks (185 sources, 423 markers, 0 failures;
      D11 quote-hygiene defects found & repaired)
- [x] FINAL_REPORT.md — convergent synthesis of the whole research process


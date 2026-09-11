# Extracted from: LANDSCAPE_MAP.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: bbb62335d9847fb45b46667b10adc7d92fd2ea741dfa33eb6a4d747b1d4d4fdd
- original_path: _originals/ref-src-bbb62335d984--research-campaign-landscape-map.md
- extraction_quality: full
- language: en

---

# LANDSCAPE MAP — Wave 1 Cross-Track Synthesis

Scope: T1 (digital genetic criticism), T2 (PKM landscape), T3 (ontology/provenance standards).
Wave 2 tracks (T4–T6) will be appended when their dossiers land.
Status labels: [verified across N tracks] / single-track findings stay inside their dossiers.

---

## The headline [verified across 3 tracks]

Three independent research threads, using different sources and methods, converged on
the same verdict:

**Mozare's evidence-governance stack is original.** No surveyed system combines:
SHA-256-immutable originals, an authority hierarchy over assertions (8 levels),
permission-qualified claims, genesis-preserving typed version relations, and
multi-agent patch governance. Flagship genetic editions (BDMP, Faustedition,
Woolf Online) don't have it; the entire agentic PKM genre doesn't have it;
no ontology/provenance standard grades *assertions* by authority tier.

**The recurring gaps are equally consistent — and they are not governance gaps:**
1. **Interchange** — no TEI path, no PROV-O/SKOS/LRM export, RO-Crate usage unverified.
   His knowledge is Markdown-locked; machines outside his toolchain can't consume it.
2. **Publication** — private-only. Every flagship project publishes; he doesn't.
3. **Agent-facing surfaces** — no AGENTS.md/MCP-style entry points that would let
   arbitrary AI harnesses inherit his governance instead of being locked out.
4. **Presentation ergonomics** — property-driven views (Obsidian Bases/Dataview)
   over existing frontmatter would fix human navigation without schema change.

Strategic reading: **ahead on governance, behind on interfaces.** All four gaps are
additive layers; none requires touching the authority model that makes the work original.

## Improvement clusters (merged backlog, deduplicated)

**A. Interchange exports** (from T3, reinforced by T1's TEI finding)
- PROV-O mapping of the eight relations (`derived-from→wasDerivedFrom`,
  `supersedes→wasRevisionOf`, `is-version-of→specializationOf`, …)
- SKOS export of controlled vocabularies
- Wikibase-style `rank` field on claims (preferred/normal/deprecated)
- E13-shaped fields in claim records; PREMIS-shaped fixity blocks in source records
- TEI P5 export path (T1 table stakes); RO-Crate conformance verification vs 1.3

**B. Human interface** (from T2)
- Obsidian Bases/Dataview presentation layer over existing frontmatter —
  tables/cards over claims' `current_claim_permission`, sources' `validation_status`
- Zero schema change; addresses weakest criterion in both T1/T2 evaluations

**C. Agent surfaces & proposal queues** (from T2, harmonious with T3)
- AGENTS.md / minimal MCP honoring authority tiers so any harness inherits governance
- Embedding-proposed typed edges → `_proposals/` adjudication queue
  (authority level 7 by construction) — scales graph growth past manual linking

**D. Publication layer** (from T1+T2)
- Static-site publication path (digital-garden movement's standard machinery)
  with explicit redaction rules for private material

## Cross-track negative findings [reinforced]

- No PKM tool combines checksummed originals + authority + permissions. [T2]
- No flagship genetic-criticism project governs AI-mediated intake or grades
  machine-authored content below human-reviewed levels. [T1]
- No scholarly standard defines assertion-authority grading; Wikibase stops at
  references+ranks, PREMIS at fixity, CRM at event semantics. [T3]
- CIDOC-CRM v7.3.2 has no first-class version-of property — pairwise version edges
  have no CRM equivalent. [T3]
- No cross-tool typed-edge Markdown convention exists (`relations:[{target,type}]`
  frontmatter is non-portable today). [T2+T3]

## What NOT to do (recurring reject verdicts)

- Do not migrate the store to RDF/graph-DB/JSON-LD as system of record —
  Git-diffable Markdown is load-bearing for multi-agent audit.
- Do not adopt full CIDOC-CRM event modelling; E13-pattern fields capture the benefit.
- Do not chase every agentic-PKM product feature; the genre standardized conveniences,
  not governance.

---

*Synthesis of interpretive-synthesis-level dossiers; see per-track SOURCES.json for provenance.*
*D9 compliance debt resolved 2026-08-25: every track now carries full inline [S#] coverage (repair pass; see META_EVALUATION.md).*

---

# WAVE 2 SYNTHESIS (T4 OOO-in-the-wild · T5 AI-scholarship/evidence governance · T6 artistic-research living archives)

## Track verdicts

- **T4:** OOO's real-world infrastructure is books+blogs, not code or museums — zero serious computational implementations exist (GitHub toys only, arXiv empty). Criticism is strong and institutionalized (Todd c=1813, Wolfendale's systematic campaign, movement-skepticism from Brassier/Sparrow). The OOO wiki's critic integration is verified deep on-disk (Brassier ~29 files, Todd ~20, Wolfendale ~20, dedicated correlationism concept) — its gaps are the design-led uptake shelf and post-2020/AI-era rereadings.
- **T5:** The sharpest track finding of the campaign: **the ecosystem standardized citations; nobody standardized authority.** Products stop at citation display (kotaemon even shows relevance scores beside citations — the exact conflation his 'QMD scores are never evidence' rule forbids); the 2026 research frontier (ProvenAI, LineageRAG verbatim spans, EvoTrustRAG conflict attribution) is converging on what he already built. The one behind-criterion: no faithfulness/attribution evaluation has ever been run over QMD answers (his 30-question benchmark tests retrieval regression only).
- **T6:** His provenance discipline exceeds every surveyed artistic-research platform (RC/JAR/Ruukku publish process but govern nothing; VMQ records plans not evidence). The structural gaps are publication (no public layer vs RC's free open backbone), media-rich exposition format, and succession planning (VMQ-style 'what happens when steward/software disappears' has no counterpart).

## New improvement clusters added by Wave 2

**E. Evaluation loop (from T5 — highest-leverage single adoption of the campaign):**
append a faithfulness stage to `run-semantic-benchmark.py` (generate answers over the same 30 questions, score claim-to-source entailment RAGAS-style); FActScore-lineage atomic claim audits; LineageRAG-style verbatim-span citation checks inside `validate_repo.py`.

**F. Preservation & succession (from T6):**
VMQ-style succession record per object family; Webrecorder/browsertrix capture pipeline turning cited web pages into checksummed derivatives with source records.

**G. Theory-field intake shelves (from T4):**
more-than-human-design uptake cluster; hyperobject-critique dossier; AI-era rereading watch bridging to the AI-philology frontier; term-disambiguation records protecting 'ontograph' vocabulary from Bogost-'ontography'/OOP collisions.

## Six-track strategic summary

Across all six tracks the same shape holds: **Mozare's governance layer is ahead of every surveyed system — academic editions, PKM tools, standards bodies, AI products, artistic-research platforms.** He is behind exactly where governance meets an outside: interchange formats (T1/T3), public readership (T1/T6), agent surfaces (T2), evaluation loops (T5), succession planning (T6). Every gap closes additively without touching the authority model.

## Campaign integrity

All six dossiers follow the four-section contract with typed SOURCES.json provenance. Inline `[S#]` marker coverage is **verified complete across all six tracks** (provenance-repair pass, 2026-08-25): T1 received full marker insertion (42/42); T2's compound markers were normalized to atomic form and 8 previously-unanchored sources grounded (37/37); T3's SOURCES.json was normalized from dict-wrapped to array schema, its missing TEI captures were fetched and identity-verified, its PREMIS fallback ladder was exhausted per P5 (archive.org yields only an interstitial — negative finding stands), and all statements marked (19/19); T4 had four sources anchored (30/30). Verification method: scripted cross-check of every SOURCES.json id against DOSSIER.md markers — zero unreferenced IDs and zero phantom markers remain in any track. Negative findings recorded everywhere; bot-walls and dead targets documented rather than papered over. Full defect/improvement history in META_EVALUATION.md.

**Post-campaign audit addendum (2026-08-25, Engine 1):** the first mechanical citation-span
audit (`E1-evaluation-loop/check_citation_spans.py`) verified 52 dossier quotes verbatim
inside raw captures and classified the remaining quoted material as URL-only provenance
(protocol-legal) or wiki-canonical quotes — after surfacing and repairing three genuine
T1 defects (unmarked translation quoted as verbatim; own coinage placed in quotes;
misattributed citation). Final state: **185 sources, 423 atomic markers, zero span
failures across all six tracks.**


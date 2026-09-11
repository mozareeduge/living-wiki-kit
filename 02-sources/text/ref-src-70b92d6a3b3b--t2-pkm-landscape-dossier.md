# Extracted from: T2-pkm-landscape/DOSSIER.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: 70b92d6a3b3b65ade94f881c79ddcba2a21fc6201e42828c693333229c79b279
- original_path: _originals/ref-src-70b92d6a3b3b--t2-pkm-landscape-dossier.md
- extraction_quality: full
- language: en

---

# T2 — The PKM & Personal-Wiki Landscape (2026) and Where the Zare Wikis Sit

**Track:** T2-pkm-landscape · **Date of research:** 2026-08-25 · **Status:** interpretive synthesis (authority level 6 per mozare-wiki SYSTEM_DESIGN.md §3)
**Method:** structured API sweep first (GitHub REST search API, OpenAlex), browser/curl verification for load-bearing claims; raw page copies in `raw/`. Every load-bearing fact has a SOURCES.json entry. Candidate-tier inferences are marked inline.

---

## (a) LANDSCAPE MAP

Five clusters, ordered by data-model rigidity (loosest → strictest). Star counts are GitHub `stargazers_count` on 2026-08-25; activity is last push date.

### A1. Outliners / database-tools (structure first, prose second)

| System | What it does structurally | Data model | Evidence handling | Community |
|---|---|---|---|---|
| **Logseq** 44,612★, active (pushed 2026-08-24) [S1] | Outliner-first daily notes, block refs, local-first; long-running "DB version" rebuild toward queryable block database [S8] (candidate-tier) | Blocks + untyped `[[links]]` + page properties; no typed edges | None built-in | Very large OSS community |
| **Roam Research** (site live, closed) | Originator of bidirectional-block outlining (2020 wave) | Proprietary cloud blocks, Datomic | None | Legacy: declined but alive; its ideas absorbed everywhere |
| **Tana** (site live, closed) | Supertags = schema-on nodes; every node can be a typed record with fields; AI commands (closed beta era) | Node graph w/ tag-defined property schemas (supertags); closest mainstream thing to a typed personal graph | Provenance only as free fields | Commercial, closed source; strong niche |
| **Capacities** (site live, closed) | "Object-based" note app: objects have types + properties | Typed objects/properties in a managed DB, not files | None notable | Commercial indie |
| **Anytype** (anyproto/anytype-ts 8,701★, pushed 2026-08-25) | Local-first object database w/ types, relations, sets; P2P sync (any-sync) | Typed objects + relations, encrypted, CRDT-based | None | Significant OSS community |
| **SiYuan** (siyuan-note/siyuan 45,971★, pushed 2026-08-25) | Block-level self-hosted workspace; SQL-queryable blocks; human+AI-agent positioning | Blocks in SQLite; attribute views | None | Large, mostly East-Asian community |

**Cluster signature:** rich *property* models, weak *edge* semantics (Tana's supertags excepted), essentially zero provenance machinery.

### A2. File-over-app Markdown systems (the Obsidian gravity well)

- **Obsidian** is the de facto substrate. Two 2024–2026 inflections verified from vendor help/docs:
  - **Obsidian Bases** — now a *core plugin*: "database-like views of your notes… view, edit, sort, and filter files and their Properties," stored as `.base` YAML or code-block embeds, with table/list/cards/map layouts [S2]. Notion-style databases over plain files, officially.
  - **Obsidian CLI + agent skills** — kepano's `obsidian-skills` repo ("Agent skills for Obsidian… Obsidian CLI and open formats including Markdown, Bases, JSON Canvas") shows 47,225★ and was heavily forked/copied within months [S3] — the strongest single signal that *agent-operated vaults* became a mainstream concern in 2026.
  - Plugin mass: Dataview 9,294★ (frontmatter query language; slowed development — last push 2025-11), Templater 5,239★, obsidian-git 11,851★, Smart Connections 5,396★, spaced repetition 2,531★, Copilot 7,622★ [S9][S10].
- **Logseq** overlaps here too; **Foam** 17,376★ (VSCode wikilink toolkit, active) is the file-over-app purist option [S30].
- **Dendron** 7,463★ — hierarchical-schema PKM; effectively dormant (archived:false but no pushes since 2025-11) — cautionary tale about schema-heavy tooling without maintenance energy [S30].
- **Org-roam** 6,016★ + org-roam-ui 2,275★ — Emacs Zettelkasten; the oldest still-active file-over-app lineage [S30].
- **Semantic MediaWiki** 628★, very active — properties/typed values inside wiki engine; heavy for one person; Wikibase-class machinery rarely run personally [S35].

**Cluster signature:** links are untyped strings; structure lives in conventions (folders, frontmatter, MOCs). Whatever rigor exists is user-authored discipline — exactly where Zare's system operates, but with far more formalization than typical.

### A3. Digital-garden / publishing movement

- Maggie Appleton's garden-history essay remains the canonical articulation: gardens as "imperfect," public, learning-in-public spaces with seedling→budding→evergreen maturity stages [S5].
- Andy Matuschak's evergreen notes: atomicity, concept-orientation, densely linked, written *to evolve* — the methodological core under most modern vaults [S4].
- Infrastructure: Quartz 13,094★ (active static publishing), obsidian-digital-garden 2,475★ (one-click publish), digital-gardeners resources repo 4,789★ [S31].
- Publishing is *identity-bearing* (public epistemic status per note) — orthogonal to Zare's fully private wikis (`visibility: private` throughout).

### A4. AI-native PKM — the 2024–2026 explosion (this is the live frontier)

Two waves are distinguishable:

**Wave 1 — RAG/chat-with-notes:** Khoj 36,715★ (self-hosted second brain, agents), Smart Connections 5,396★ (embedding-based related-notes while writing), obsidian-copilot 7,622★, smart-second-brain 1,214★, Reor 8,569★ (**archived** — local-AI PKM apps struggled), infio-copilot 663★. Signature: retrieval at question time; nothing accumulates. [S32]

**Wave 2 — agentic compilation ("LLM wikis"):** catalyzed by Andrej Karpathy's LLM-wiki gist [S6]: RAG "rediscover[s] knowledge from scratch on every question… Nothing is built up"; instead an agent "incrementally builds and maintains a persistent wiki… compiled once and then kept current." Karpathy explicitly names the failure mode this solves: "Humans abandon wikis because the maintenance burden grows faster than the value." Clones/derivatives (all verified via README fetches in `raw/`):
- SamurAIGPT/**llm-wiki-agent** 3,453★: ingest → entities/concepts/syntheses pages, contradiction flagging, graph.json, lint. No evidence model beyond source-summary links [S7].
- swarmclawai/**swarmvault** 670★: three-layer architecture (immutable `raw/` → generated wiki → state/graph.json), review workflow, candidate queue [S11].
- Ar9av/**obsidian-wiki** 3,283★: answers "with `[[wikilink]]` citations, not vibes"; manifest-tracked delta ingestion [S12].
- AgriciDaniel/**claude-obsidian** 12,280★ — the closest structural cousin found: "immutable, content-addressed copies before synthesis"; "source and claim ledgers retain authority, freshness, support, contradiction, confidence, and review state"; plan-SHA256 approved-write transactions; single-orchestrator merge discipline [S13].
- eugeniughelbur/**obsidian-second-brain** 4,189★: nightly agent reconciles contradictions, freshness policy ("every fact timeless, dated, or a pointer"), provenance-per-claim distill, typed-edge lint over a `relations:` graph, bounded recall hook with abstention logging [S14].
- breferrari/**obsidian-mind** 4,554★: epistemic contract — every recorded item carries `confidence: verified|inferred|unverified`, declared generality scope at write time, server-side provenance, corrections-supersede semantics [S15].
- Adjacent editors/harnesses: inkeep/open-knowledge 3,640★ (WYSIWYG markdown IDE "for knowledge bases, LLM wikis" with MCP/skills), YishenTu/claudian 14,967★ (Claude/Codex embedded in Obsidian); wider agent-client layer surveyed in [S36].
- QMD (tobi/qmd): on-device hybrid BM25+vector+rerank search "ideal for your agentic flows" — the tool Zare already uses [S16].

**Assessment of Wave-2 provenance depth (verified against primary text):** most projects' "evidence" = source-page citations or confidence labels. claude-obsidian is the only one with claim ledgers + authority fields approaching Zare's model; even it lacks a multi-level authority hierarchy, immutable-original checksums, or permission-to-argue states.

### A5. Methods-only movements (no tooling required)

- **Zettelkasten (Ahrens/Luhmann lineage):** zettelkasten.de intro — atomic notes, unique IDs, linking as thinking; the folk method under most clusters above [S17]. OpenAlex shows modest scholarly trickle (e.g., 2023 paper pairing Zettelkasten with interval repetition), not a research field [S18].
- **Evergreen notes / progressive summarization / PARA** etc.: practice cultures, not systems; they specify note *behavior*, not evidence.
- **Spaced-repetition-in-notes:** obsidian-spaced-repetition 2,531★, incremental-writing 209★ (last push 2022), FSRS-based newcomers; persistent minority practice, never dominant [S33].

---

## (b) WHERE MOZARE SITS — five criteria

Criteria chosen to span data model, governance, lifecycle, operability, and ecosystem position. Ratings compare against the full landscape above.

### C1. Evidence governance
Landscape norm: none (A1/A2/A3) or citation-lists/confidence labels (A4-wave-2 best case).
Mozare: **ahead of everything found.** Immutable SHA-256 originals + derivative-subordination + 8-level authority hierarchy + evidence-state/permission fields on claims (`may-argue`) + anti-fluency rules ("do not upgrade evidence because language is fluent, repeated, similar, or AI-generated") + promotion rule requiring source-opening and counter-evidence [S19][S20][S21][S22]. Closest rival (claude-obsidian claim ledgers) has authority/confidence fields but no hierarchy, no checksummed originals, no permission semantics.
**Verdict: ahead.**

### C2. Genesis/version modeling
Landscape norm: git history at best (every A2/A4 tool treats history as infra, not meaning); genetic criticism absent from all PKM tooling found.
Mozare: additive-only version relations (`supersedes`, `is-version-of`, `derived-from`, `translates`…) preserving intellectual genesis as *first-class content*. No landscape system does this. [S20]
**Verdict: alone.**

### C3. Agent-operability
Mozare already does what Wave-2 advertises: PATCH_MANIFEST.json gated writes, GPT-authors/Claude-applies split, validator gates, handoff protocol, QMD authority-aware search tiers [S37]. This is architecturally equivalent to (and more conservative than) claude-obsidian's transaction model.
Gap: the ecosystem standardized in 2025–26 on **agent-discovery surfaces** — MCP servers, skills manifests, AGENTS.md conventions, CLI entry points (kepano obsidian-skills 47k★ [S3]; anytype-mcp 512★ [S23]; OpenKnowledge shipping MCP by default [S24]). Mozare's protocols are bespoke CLAUDE.md lore: powerful for his two named agents, invisible to every other harness.
**Verdict: at parity on discipline, behind on interface standards.**

### C4. Interface/navigation ergonomics
Mozare relies on hand-built index pages, reading routes (PATH-*), generated register graphs. That is 2019-era MOC practice, executed well.
Landscape moved: Bases gives property-driven table/card/board/map views natively [S2]; graph views, Canvas, spatial tools (voicetree 918★) are commodity; org-roam-ui showed interactive graph navigation years ago.
**Verdict: behind; heaviest friction point for a human reader.**

### C5. Ecosystem leverage / future-proofing
Mozare bets correctly on the durable substrate (Markdown + YAML frontmatter + git + GitHub + Obsidian-readable), same bet as Foam/Obsidian/Karpathy pattern. But typed edges as frontmatter `relations:[{target,type}]` are a *private dialect*: no Bases/Dataview queries, no standard tooling reads them; validators are homegrown. Anytype/SiYuan/Tana chose richer engines with real query layers at the cost of lock-in; Mozare keeps freedom but pays full maintenance cost (his own docs admit validator-driven upkeep).
**Verdict: correct foundation, unleveraged dialect.**

### C6 (bonus). Audience/publishing path
All three wikis are private archives with no rendering pipeline (casebook `site/` is nascent). The entire A3 cluster treats publishing as epistemically meaningful (maturity stages, public learning). For an artistic-research project, invisibility is a strategic cost, not just a feature gap. [S25] (candidate-tier inference)

**Where he is heavier than needed (honesty pass):**
1. The 8-level hierarchy is applied uniformly across three wikis whose stakes differ; OOO theory notes arguably need 3 levels, not 8. Governance overhead scales with corpus even where risk doesn't. (candidate-tier)
2. ~3000 hand-typed edges maintained through manifest round-trips is a cost the landscape avoids via inference/embedding suggestions with human confirmation — his validators could auto-*propose* typed edges without weakening authority rules.
3. Triple-wiki duplication of identical schemas/policies (three CONTROLLED_VOCABULARY-like files) re-implements what a shared spec layer would give once.

---

## (c) IMPROVEMENT BACKLOG

1. **[adopt] Publish the wikis' machine contract as standard agent surfaces.** Add `AGENTS.md` (or symlink CLAUDE.md), a minimal MCP server (read/search/propose-edge endpoints honoring the authority tiers), and skills-package metadata. Mechanism: mirror kepano obsidian-skills + anytype-mcp patterns; keep PATCH_MANIFEST as the write gate. Serves: all three wikis. Effect: any harness (Codex, Gemini CLI, Cursor) inherits the governance instead of being locked out. Low risk: read-path only.
2. **[adopt] Bases/Dataview view layer over existing frontmatter.** Write `.base` definitions per object type (claims with `current_claim_permission`, sources with `validation_status`) so humans get tables/card views without touching data. Mechanism: pure presentation; zero schema change. Serves: mozare-wiki intake triage, casebook testbed matrices. Fixes criterion C4 directly.
3. **[adapt] Claim-review cadence borrowed from freshness policies.** obsidian-second-brain enforces "every fact timeless, dated, or a pointer" plus stale-claim lint [S14]; Zare has `updated:` dates but no staleness lint on claims. Adapt conservatively: add a validator warning (not error) for claims untouched >N months whose `evidence_state` allows revision. Serves: casebook-wiki (fast-moving), NOT mozare-wiki archive (timelessness is correct there).
4. **[adapt] Edge-proposal lane using embeddings.** Keep typed-edge authority human/governed, but let QMD/embedding similarity *propose* candidate `relations:[{target,type}]` entries into a `_proposals/` queue (authority level 7 by construction) for batch human adjudication. Mechanism: Smart-Connections-style similarity, but writing proposals, not auto-links. Serves: OOO-living-wiki graph growth (~340 pages is past manual-linking scale).
5. **[adopt] Shared spec package across the three wikis.** Extract common schemas (source-record, relation-object, claim grammar) into one versioned `wiki-spec/` (single repo/package, semver'd like his schema_version field) consumed by all three validators. Mechanism: he already versions schemas; this deduplicates three diverging copies. Serves: maintenance cost (criterion C5).
6. **[adapt] One-way publishing valve for artistic-research audience.** A Quartz (or Obsidian Publish-equivalent) pipeline rendering only `visibility: public` canonical objects, with authority levels displayed per claim (an honest-garden: publish the evidence state alongside the prose — something *no* garden in the landscape does). Serves: mozare-wiki as portfolio artifact; addresses C6. Reject if privacy outweighs; the mechanism itself is cheap.
7. **[reject-with-reason] Migrating to Logseq/Tana/Anytype-class engines.** Any would supply databases/queries natively, but all abandon either file-over-markdown durability (Tana/Capacities closed formats; Logseq DB-version drift) or the evidence layer entirely; migration would destroy genesis modeling (C2) which no engine represents. His substrate bet is right; the deficit is views (fix #2), not storage.
8. **[reject-with-reason] Full claim-ledger rewrite à la claude-obsidian.** Its ledgers overlap ~80% with his existing claim objects/evidence_state; adopting its shape would churn 340 pages for marginal gain. Cherry-pick only #3's cadence idea instead.
9. **[reject-with-reason] Spaced repetition over notes.** His archive is reference-not-memorization material; SR adds scheduling state incompatible with additive-only records. (Landscape interest is real but narrow: 2.5k★ plugin vs 46k★ platform.)

---

## (d) NEGATIVE FINDINGS — searched and not found

1. **No general-purpose PKM system with cryptographic original-integrity guarantees.** GitHub searches (`provenance+notes+markdown`: total_count=4, none relevant at scale; multiple obsidian/RAG sweeps): nothing besides claude-obsidian's content-addressed capture even attempts it; nobody combines checksums + authority hierarchy + permission states. [S26]
2. **No evidence-governed digital garden.** Garden literature (Appleton/Matuschak lineage) concerns maturity stages and public learning; no found instance publishes per-claim evidence state or provenance chains. [S5][S4]
3. **No genetic-criticism concepts in PKM tooling.** OpenAlex keyword sweep on "personal knowledge management zettelkasten" returned no work connecting avant-garde textual genetics (version families, dossier genesis) to note systems; the PKM literature treats "genesis" as git history at most. [S18]
4. **No typed-edge standard for personal Markdown.** Searches for personal-knowledge-graph markdown tooling returned ad-hoc schemas (each project invents its own `relations:` dialect — obsidian-second-brain's typed-edge lint is the nearest, still private). No cross-tool convention comparable to schema.org exists. [S14][S27]
5. **Tana/Capacities/Roam programmatic verification blocked:** closed-source, no keyless public APIs surfaced; findings for them rest on marketing-site liveness checks + secondary reputation (marked derivative-witness/candidate). Their internal evidence-handling could not be audited [S34] — absence of public proof is not proof of absence, but nothing in public materials claims provenance features.
6. **GitHub user 'mokteson' does not exist** (API 404, twice) — earlier session memory of that name is unverifiable; flagged in case it resurfaces elsewhere. [S28]
7. **arXiv has no active "AI maintains personal knowledge base" research thread yet** (export.arxiv.org query returned no on-point hits on 2026-08-25); the practice is running ahead of the literature. [S29]

---

## Bottom line

The 2026 landscape converged exactly onto the terrain Zare occupied early: agentic maintenance of compounding Markdown wikis is now a genre with tens of thousands of stars across clones. What the genre standardized (agent interfaces, view layers, freshness linting) he lacks; what none of it has (checksummed originals, an authority hierarchy, permission-qualified claims, genesis-preserving version relations) is precisely his contribution. He should spend 2026 importing their interfaces, not their epistemics.


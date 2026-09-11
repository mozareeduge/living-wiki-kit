# Track T5 — AI-Mediated Scholarship & Evidence Governance (2024–2026)

Scope: the 2024–2026 landscape of RAG over personal archives, attributed/faithful
generation, hallucination evaluation, AI-in-philology, and provenance standards for
machine-authored content — and where Mohammad Zare's evidence-governed multi-agent
wiki triad (mozare-wiki / casebook-wiki / OOO-living-wiki) sits against it.

Method note: structured keyless APIs (GitHub REST, arXiv, Crossref, OpenAlex) plus
direct fetches of official docs; every load-bearing statement carries an [S#] marker
resolved in SOURCES.json. Subject-side statements were verified by read-only
inspection of the actual repositories. Session date 2026-08-25.

## Criteria used for positioning

Six criteria, stated before the map. Each maps to a question the subject himself asks:
of the "chat with your archive" wave, what is worth adopting?

1. **Grounding discipline** — does the system bind generated text to verifiable source
   spans, and treat citation as necessary-but-insufficient? [S21]
2. **Source-authority grading** — does it rank or gate sources by epistemic authority
   (not just retrieve and cite them)? [S36]
3. **Original immutability** — are source artifacts preserved bit-exactly with
   checksums, separate from searchable derivatives? [S28][S37]
4. **Auditability of machine edits** — are AI-authored changes bounded, manifested,
   validated, and attributable to a named contributor role? [S25][S26]
5. **Semantic-search-as-evidence safeguards** — is retrieval scoring explicitly barred
   from functioning as truth? [S38]
6. **Evaluation loops** — is there a running, threshold-bearing benchmark for grounding/
   faithfulness of generated output (not just retrieval)? [S34]

## A. Landscape map

### A1. Consumer RAG-over-notes/archive products

The mass-market "chat with your documents" wave consolidated around four large active
projects: Open WebUI (149,847 stars) [S04], AnythingLLM (65,177) [S03], privateGPT
(57,465) [S01], and kotaemon (25,714) [S02]. Khoj (36,715) is the closest mass-market
RAG-over-personal-notes product [S07]; Quivr (39,422) shows the momentum stall of the
2025 second-brain-RAG shape (no push since 2025-07) [S10]. A companion artifact of this
literature is Amazon's RefChecker pipeline + benchmark for fine-grained hallucination
checking against references [S12].

Product-level provenance behavior, verified from official docs/readmes:

- **NotebookLM** defines the grounded-notebook paradigm: "grounded in your own
  documents", responses "with citations, showing you the most relevant original quotes",
  model restricted to uploaded sources [S27]. Citation display is the entire provenance
  surface; no authority tiers, no immutability contract.
- **Open WebUI** is the notable partial exception on criterion 3: its Knowledge bases
  support citations in agentic tool output AND `Add Content → Sync Directory`, in which
  "the client hashes each local file (SHA-256), the server compares hashes and paths…
  only new, modified, deleted files are touched" [S28]. This is checksum-based sync,
  not an immutable-original preservation contract — files can be updated in place, and
  there are no authority tiers.
- **kotaemon** advertises "advanced citations with document preview… View your citations
  (incl. relevant score)" [S30] — the retrieval score is displayed as if it were part of
  answer verification, precisely conflation his governance forbids [S38].
- **AnythingLLM**: "drag-and-drop uploads and source citations" [S29] — same
  citation-display-only provenance.
- **Inside Obsidian itself**, the plugin mass works on note text directly: Copilot
  (7,622 stars) adds chat + vault QA [S08]; Smart Connections (5,397) is a local-embedding
  "related notes while writing" attention organizer [S09]; smart-second-brain (1,214)
  wires a privacy-focused local assistant to the vault [S11]. None carries provenance
  machinery beyond link suggestion or citation display.

### A2. Developer frameworks

LangChain (144,956 stars) and LlamaIndex (51,865) remain the default substrates; their
RAG abstractions return retrieved chunks plus optional citations, with authority grading
and immutable originals left as user-built add-ons rather than primitives [S06].
Enterprise cited-answer RAG continues via Onyx (ex-Danswer, 31,754 stars) [S05], whose
feature surface ("Custom Agents… unique instructions, knowledge, and actions") is
capability-oriented, with connector-admin configuration standing in for authority [S35].

### A3. Evaluation & attribution research

The canonical lineage, all verified live on arXiv: ALCE citation generation [S13],
RAGAS automated RAG evaluation (EACL 2024 demo, 402 cites) [S13][S34], Self-RAG's
retrieve/generate/critique loop [S13], HaluEval [S13], FActScore atomic factual precision
[S14], CRAG corrective retrieval [S13], and the long-context-vs-RAG debate [S13].
The definitional anchor for attribution is Rashkin et al.'s AIS — Attributable to
Identified Sources [S15]; the documentation precedents are Model Cards [S13] and
Datasheets for Datasets [S16] (Bender & Friedman's Data Statements lives in the ACL
Anthology, not arXiv [S17]). Agentic retrieval with trained search policies arrived with
Search-R1 [S14].

The 2025–2026 frontier converges on exactly the subject's concerns:

- **Provenance-native evaluation.** ProvenAI decomposes transparency into correctness /
  citation fidelity / per-document influence, showing citation ≠ influence [S21].
  "Do You Need a Frontier Model as a Citation Verifier?" benchmarks judge calibration
  for deep-research source attribution [S22].
- **Evidence lineages.** LineageRAG constructs one evidence lineage per evidence demand,
  completed with a *verbatim* source span when the evidence supports the answer [S18].
- **Conflict and evolution awareness.** EvoTrustRAG attributes conflicts to legitimate
  knowledge evolution vs malicious manipulation — first-class authority/conflict
  reasoning entering mainstream RAG [S19].
- **Layered grounding.** LayerRAG-Bench shows answers can "appear grounded while failing
  at the evidence, tool-contract, authorization, or session-state layer" [S20] —
  grounding as a layered property, matching his multi-plane architecture.

### A4. AI-in-philology

Neural philology is established: Assiel et al., "Restoring and attributing ancient texts
using deep neural networks" (Nature 2022, ~202 cites) [S33]; the survey "Machine Learning
for Ancient Languages" [S33-query context]; arXiv hosts an explicit LLM-for-classics
thread ("Exploring Large Language Models for Classical Philology"; Latin BERT) [S32].
This literature restores/attributes text but has no governance layer for machine-authored
scholarly claims about those texts — the gap the subject's claim/evidence grammar fills.

### A5. Governance & norms bodies

- **ICMJE** now carries a dedicated section "V. Use of Artificial Intelligence in
  Publishing" (AI use by authors, reviewers, editors' role), atop the authorship regime
  under which AI cannot take author responsibility [S25].
- **COPE** maintains dedicated AI positions (AI in decision-making; authorship/AI tools),
  but publicationethics.org Cloudflare-blocks unauthenticated fetches (403) and the
  web.archive.org fallback rung also failed (no snapshot; CDX non-JSON) — full text
  unread this session, recorded honestly [S23][S24].
- **CRediT** is formalized as ANSI/NISO Z39.104-2022 (Contributor Roles Taxonomy) —
  typed contributor roles are institutional infrastructure; whether "AI" is a legitimate
  contributor role remains contested and unresolved by the taxonomy itself [S26].
- **C2PA** provides the cryptographic provenance-manifest standard for machine-touched
  media: signed bindings of capture/edit history to content, motivated explicitly by
  trust ("establishing the provenance of media is critical…") [S31].

## B. Where Mozare sits

Scored against the six criteria above. Advantages first, gaps stated with equal weight.

1. **Grounding discipline — LEADS THE FIELD (among surveyed systems).** Every consumer
   product stops at citation display [S27][S29][S30]. Research knows better: ProvenAI
   proves citations may not have shaped answers [S21], LineageRAG demands verbatim spans
   [S18]. His derivative-points-to-checksummed-original + evidence-qualified-claims
   design already implements the research frontier's aspiration [S37][S38]. What he lacks
   is the *measurement*: none of these metrics has been run over his system.
2. **Source-authority grading — UNMATCHED IN PRACTICE; RESEARCH ONLY NOW ARRIVING.**
   GitHub-wide search for source-credibility + RAG returns one zero-star repo [S36];
   no surveyed product grades sources by authority. EvoTrustRAG/LayerRAG-Bench show
   research beginning to treat conflict/authority/layering as first-class [S19][S20].
   His 8-level hierarchy (AI-generated at level 7, below all human/reviewed levels;
   generated views at level 8) anticipates this by design [S37-context; SYSTEM_DESIGN.md
   §3 verified locally].
3. **Original immutability — STRONGEST SURVEYED.** 94 SHA-256 checksummed originals in
   `_originals/`, never edited, derivatives always secondary [S37]. Closest external
   analogue is Open WebUI's hash-sync directory mirroring [S28] — sync, not an
   immutability contract; C2PA binds provenance cryptographically but for media
   capture chains, not scholarly archives [S31].
4. **Auditability of machine edits — MATCHES OR EXCEEDS GOVERNANCE NORMS.** ICMJE
   requires human accountability for AI-assisted text [S25]; CRediT types human roles
   without settling AI's status [S26]. His PATCH_MANIFEST.json → Claude Code local
   validation (`validate_repo.py --full`) → bounded-bundle pipeline makes every
   machine-authored change declared, diffable, and gated before landing — stronger than
   journal post-hoc disclosure norms.
5. **Semantic-search-as-evidence safeguards — EXPLICIT AND CODIFIED.** "QMD scores
   organize attention and are never evidence," written into CLAUDE.md and the
   authority-aware-search decision record, with rebuildable non-source index state [S38].
   kotaemon displays relevance scores next to citations as quasi-verification [S30] —
   the industry default is exactly the confusion he forbids.
6. **Evaluation loops — REAL BUT RETRIEVAL-ONLY; THE HONEST GAP.** He ships a genuine,
   threshold-bearing harness (26 canonical + 4 source-record questions, top-five expected
   paths, pass ≥27/30) plus release validators [S37]. But it measures *retrieval*
   regression, not *faithfulness/attribution* of generated answers — no RAGAS-style
   faithfulness score, no FActScore-style atomic claim check, no ProvenAI-style
   citation-influence test has ever been run over QMD-mediated answers. The evaluation
   research field is ahead of him on this single axis; he is ahead of it on every other.

## C. Improvement backlog

Numbered; each tagged adopt/adapt/reject-with-reason, naming mechanism + serving wiki.

1. **ADOPT — Faithfulness regression harness over QMD answers.** Extend
   `run-semantic-benchmark.py` (mozare-wiki) with a second stage: for each of the 30
   questions, generate an answer via the normal QMD flow, then score answer-groundedness
   (claim-to-source entailment, RAGAS-faithfulness style) against the cited canonical
   pages [S34][S37]. Threshold form matches house style (e.g. ≥27/30 fully supported).
2. **ADOPT — Claim-attribution spot audit (FActScore lineage).** Decompose a sample of
   canonical claim records into atomic claims and verify each traces to an original or
   verified primary source [S14]. Serves mozare-wiki's claim-object family; converts
   "source record proves presence, not internal assertions" from caveat into tested
   property.
3. **ADAPT — Verbatim-span completion rule (LineageRAG-style).** For interpretive
   answers, require each cited derivative to resolve to a quoted span in the checksummed
   original before the answer ships [S18]. Cheap to implement inside validate_repo.py;
   serves casebook-wiki workbench flows.
4. **ADAPT — Conflict-evolution tagging (EvoTrustRAG-style).** When two records at the
   same authority level disagree, require the intake patch to classify: legitimate
   supersession vs unresolved contradiction vs candidate error [S19]. Maps directly onto
   casebook-wiki's later-round-supersedes discipline.
5. **ADAPT — Typed machine-contribution roles.** Mirror CRediT's typed-role structure
   with a wiki-local "contribution type" on every manifest entry (authored-by-GPT,
   applied-by-Claude, validated-by-script) — making the ICMJE/CRediT normative move
   machine-checkable [S25][S26]. Serves all three wikis' handoff records.
6. **REJECT — Vector-store-first KB migration (the AnythingLLM/Open WebUI default).**
   Rejected: replaces Markdown source-of-truth with version-less vector state, losing
   immutability and authority gating; his QMD collections are already rebuildable views
   [S28][S38]. Only the SHA-256 sync-directory UX idea is worth copying, onto his terms.
7. **REJECT — Retrieval-score display in user-facing answers (kotaemon pattern).**
   Rejected as presented [S30]: it invites reading similarity as verification. If scores
   are surfaced at all, label them "attention ranking, not evidence" per his own rule.
8. **WATCH, NOT ADOPT YET — LayerRAG-Bench-style cross-layer fault injection.** Its
   evidence/tool-contract/authorization/session fault taxonomy is the right long-term
   stress test for the agent pipeline [S20], but the harness cost exceeds current need;
   revisit after items 1–2 exist.

## D. Negative findings

All searched-and-not-found items, kept visible per protocol.

1. **No product treats source-authority grading as first-class.** GitHub-wide repository
   search `"source credibility" "retrieval-augmented"`: total_count=1, a zero-star repo
   [S36]. Combined with the README/docs sweep above, no surveyed consumer or enterprise
   RAG tool implements epistemic authority tiers over sources. This absence is the core
   finding: the ecosystem standardized citations, not authority.
2. **No faithfulness-evaluation artifact exists for any personal-archive RAG product.**
   None of privateGPT/kotaemon/AnythingLLM/Khoj/Open WebUI/Onyx publishes a RAGAS-style
   or AIS-style evaluation of its own answers; their docs stop at citation UI
   [S01][S02][S07][S27][S28][S29][S35]. Evaluation lives only in academic papers.
3. **COPE full text unreadable this session.** publicationethics.org = Cloudflare 403;
   fallback ladder rung 2 (web.archive.org snapshot) = 404/no snapshot; CDX API returned
   non-JSON [S23][S24]. Existence of COPE's AI positions stands on site metadata only;
   tier kept at derivative-witness/candidate deliberately.
4. **arXiv ID collisions are real traps:** 2402.10817 is a statistics paper, not AIS
   [S15]; the LLM-philology guesses 2310.16764 / 2401.14449 were physics/ML papers
   [S32-query context]. All load-bearing IDs here were re-verified by title match.
5. **"Data Statements" (Bender & Friedman) is not on arXiv** — it resolves in the ACL
   Anthology (W18-30031); recorded as routing finding so future sessions don't re-hunt
   arXiv for it [S17].
6. **AI-generated-content provenance standards for TEXT lag media.** C2PA covers
   media manifests [S31]; CRediT/ICMJE cover human accountability [S25][S26]; no
   standard located that types machine-authored *textual scholarship* contributions at
   the granularity his PATCH_MANIFEST already implements. His format is ahead of the
   standards bodies; nothing external to adopt wholesale here yet.

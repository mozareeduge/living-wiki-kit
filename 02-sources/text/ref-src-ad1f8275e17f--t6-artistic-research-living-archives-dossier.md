# Extracted from: T6-artistic-research-living-archives/DOSSIER.md

- extracted: 2026-09-10
- method: direct md copy (source was clean markdown)
- sha256: ad1f8275e17f9533bda1288aa290fc70729762b4a0c2f7c3682c0e35d6f3902d
- original_path: _originals/ref-src-ad1f8275e17f--t6-artistic-research-living-archives-dossier.md
- extraction_quality: full
- language: en

---

# T6 — Artistic Research Exposition Infrastructures & Living Archives

Track: mozare-wiki external-research campaign, wave T6 · Date: 2026-08-25 · Operator: ox-alpha subagent.

Subject positioned: Mohammad Zare ("Mozare") — practitioner-researcher whose three evidence-governed Markdown/Obsidian wikis carry strong practice-as-research components ('Grave' / نمایشنامه گور, 'Ten Research Poems', scenography/staging-mediation research grounded in Appia/Svoboda; projects visible-genesis-artistic-research, avant-trace, ontograph). System traits distinctive vs artistic-research norms: SHA-256 immutable originals, 8-level authority hierarchy over assertions, typed version relations (supersedes / is-version-of / derived-from / translates / adapts), claims as evidence-qualified records, multi-agent patch governance; currently PRIVATE (unpublished).

Method note: keyless structured APIs + static Python-urllib fetches + headless browser only where needed. Every load-bearing claim carries a zero-padded [S##] marker resolving to SOURCES.json ({id, statement_or_finding, url_or_api_query, http_status, access_date, authority_tier}). Fetch log: raw/_fetch_manifest_*.json (successes AND failures). Stripped text: raw/_txt/. Subject repositories were NOT modified (quarantine rule).

## (a) LANDSCAPE MAP

### A1 Publication platforms / exposition genres (Research Catalogue, JAR, Ruukku …)
### A1 Publication platforms / exposition genres (Research Catalogue, JAR, Ruukku …)
- **Research Catalogue (RC)** [S01][S03]: non-commercial, free collaboration & publishing platform of the Society for Artistic Research; doubles as backbone for teaching, student assessment, peer-review workflows and research-funding administration; exposition editor supports media-rich, process-forward documents. Scale: the de-facto infrastructure of the field.
- **JAR (Journal for Artistic Research)** [S02]: international online open-access peer-reviewed expositions journal (ISSN 2235-0225); its 'About' page 404'd on capture but identity/ISSN confirmed via archive-page capture and RC cross-links.
- **Ruukku** [S04][S18]: Finnish multidisciplinary exposition journal on the RC editor — but now behind an Anubis proof-of-work anti-bot wall.

### A2 Institutional degree formats (PhD-in-practice Vienna, a.pass, Nordic third cycle)
### A2 Institutional degree formats
- **a.pass (Brussels)** [S12]: post-master program in advanced performance & scenography studies with research center and publications — the closest institutional analogue to Mozare's staging-mediation line.
- **PhD-in-practice (Vienna)**: fetch returned empty payload — not verifiable this session [S14].
- Nordic third-cycle formats: not captured (agent death); candidate-tier absence only.

### A3 Living-archive projects in dance/performance (Stuart Hall lineage, McGregor, Davies, Bristol)
### A3 Living-archive projects in dance/performance
- **Stuart Hall lineage** ('Constituting an Archive'): the conceptual anchor for 'living archive' discourse — not directly captured this session (candidate-tier).
- **Studio Wayne McGregor Living Archive**: AI-trained dance heritage project — never captured before agent death [S16]; presence unverified.
- **Siobhan Davies Replay**: erroring at capture time [S15].
- **University of Bristol Theatre Collection** [S13]: live theatre/performance archive shell captured (holdings detail not fetched).

### A4 Media/net-art preservation infrastructure (Rhizome/Webrecorder, Guggenheim CCBA, Variable Media, Matters in Media Art)

### A4. Media/net-art preservation infrastructure (fixity & versioning)
- **Variable Media Questionnaire** [S07]: project of the Forging the Future alliance; records *opinions on how to preserve creative works* — behavior/medium-independent preservation planning via structured questionnaires (3rd-generation beta). Core insight: preservation decisions are metadata about future behavior, not file formats.
- **Webrecorder suite** [S08]: automated browser-based crawling at scale (Browsertrix), serverless web-archive replay, developer tools + file-format specs — the working open-source stack for capturing volatile web artworks; GitHub presence verified.
- **Guggenheim CCBA**: both guessed URLs 404'd [S06]; program exists but was not directly captured this session (candidate-tier knowledge only).
- **Matters in Media Art**: returned a stub page only [S17] — consortium guidance not capturable this session.


### A5 Artist-run knowledge bases (UbuWeb, Monoskop, Are.na)

### A5. Artist-run knowledge bases
- **UbuWeb** (1996–) [S09]: self-described largest free archive of avant-garde material (film/sound/visual poetry/papers); pure HTML longevity model, no formal provenance layer.
- **Monoskop** [S10]: live MediaWiki 'wiki for arts and studies' with page histories, categories, publishing arm; closest functioning analogue to a wiki-as-studio at scale.
- **Are.na** [S11]: commercial blocks-and-channels curation platform ('connected knowledge collectors'); no provenance/versioning semantics, closed API.


## (b) WHERE MOZARE SITS

## (b) WHERE MOZARE SITS
Criteria: process visibility · provenance discipline · publication/readership · media handling · longevity/preservation planning.

- **Provenance discipline — far ahead of the entire surveyed field.** SHA-256 originals, authority hierarchy, typed relations, evidence-qualified claims: none of RC/JAR/Ruukku expositions, artist KBs, or preservation tooling carries assertion-level governance. Even VMQ records *plans*, not evidence-graded assertions; Webrecorder captures bits, not epistemics.
- **Process visibility — behind by design choice, not capacity.** The RC exposition genre is built to publish process (sketches, failures, versions) as scholarship [S01][S02]; Mozare's genesis machinery models process better than anyone — but keeps it private, so from the field's viewpoint the process work is invisible.
- **Publication/readership — the structural gap.** No public layer at all vs RC's free open platform backbone used for teaching/assessment/funding administration [S03].
- **Media handling — gap.** His corpus is document-centric; the artistic-research mainstream assumes media-rich exposition (audio/video/embeds) as first-class [S02][S04]. Ruukku's Anubis wall also shows where automated capture of such platforms now stands [S18].
- **Longevity planning — ahead technically, behind institutionally.** His checksums beat most artists' practice outright, but VMQ/Webrecorder/Guggenheim-style *succession planning* (what happens to the archive when its steward or software disappears) has no counterpart in his system docs.


## (c) IMPROVEMENT BACKLOG

## (c) IMPROVEMENT BACKLOG
1. **ADOPT — VMQ-style succession record per wiki.** A short questionnaire-derived record per major object family: behaviors to preserve if software/steward changes (inspired by Variable Media Questionnaire) [S07]. Cheap; serves longevity criterion.
2. **ADAPT — Exposition-format export path.** Define a one-way export from casebook-wiki/mozare-wiki canonical objects into an RC/JAR-compatible media-rich exposition draft for future submission — without ever making it the system of record [S01][S02]. Serves publication gap while keeping governance private-first.
3. **ADOPT — Webrecorder capture pipeline for cited web sources.** Browsertrix/archive-webpage captures stored as checksummed derivatives with source-record entries — upgrades 'verified external primary' claims against link rot, using the exact stack the media-art world trusts [S08].
4. **REJECT — Migrating into Monoskop/Are.na-style hosted wikis.** Community platforms would surrender authority hierarchy and immutability for reach; wrong trade for this corpus [S10][S11].
5. **CANDIDATE — UbuWeb-style minimal-publication mirror.** If a public layer is wanted later: static, dependency-free HTML mirror of selected canonical objects (digital-garden machinery from T2 + hash-addressed pages), avoiding platform entanglement entirely [S09].


## (d) NEGATIVE FINDINGS

## (d) NEGATIVE FINDINGS
- **Wayne McGregor 'Living Archive' never captured** — connection storm killed the agent before fetch; unverified this session [S16].
- **Siobhan Davies Replay erroring/unreachable** at capture time (16-byte payload) [S15].
- **Rhizome ArtBase Cloudflare-blocked (403)** twice [S05]; Guggenheim CCBA URLs guessed wrong (404×2) [S06]; Matters in Media Art stub-only [S17]; PhD-in-practice Vienna empty payload [S14]; Bristol Live Art Archive URL mis-captured (document-not-found shell; Theatre Collection shell captured instead) [S13].
- **Ruukku inaccessible beyond Anubis proof-of-work notice** — anti-AI-scraping walls are becoming standard on artistic-research platforms, itself a finding for any automated-intake ambition [S18].
- **No surveyed artistic-research platform publishes assertion-level provenance or authority grading** — the gap that defines Mozare's position is total, not partial [S01][S02][S07][S09][S10].



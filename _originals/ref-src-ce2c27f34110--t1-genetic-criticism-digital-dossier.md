# DOSSIER — Track T1: Digital Genetic Criticism — Landscape & Mozare Positioning

- **Date compiled:** 2026-08-25
- **Method:** Synthesis of 44 locally cached raw files (`raw/`, fetched 2026-08-25 per `_fetch_manifest_1.json`; 47 fetch attempts, 26 OK / 21 failed-or-wrong-target). HTML stripped to `raw/_txt/` for analysis. Two small provenance gap-fills re-fetched live: TEI P5 ch. 11 & 12 via `tei-c.org/Vault/P5/current/` (original manifest URLs 404). Provenance per fact in `SOURCES.json`. Inline `[source-id]` markers added 2026-08-25 (P6 compliance pass); no substantive claims altered.
- **Subject positioned:** Mohammad Zare's **mozare-wiki** — private living genetic archive: 94 SHA-256-checksummed immutable originals in `_originals/`, one source record per artifact, extracted derivatives, canonical wiki objects, evidence-qualified CLAIM records, 8-level authority hierarchy, typed relations (supersedes, is-version-of, derived-from, duplicates-text-of, embedded-in, translates, summarizes, adapts), Git-versioned Markdown/Obsidian interface, QMD semantic search, multi-agent authoring governance (GPT authors patches via PATCH_MANIFEST.json, Claude applies/validates). Domains: Persian modernist literature, Joyce–Beckett archives, Dante–Milton, scenography, AI-mediated philology. **Private, unpublished.**

> **Corpus-health caveat (load-bearing):** several raw files did not contain their intended target. `ests-home.html` resolved to the **European Society of Thoracic Surgeons** (domain collision on `ests.org`); `dhq-pierazzo-genetic.html` contains a different DHQ article (see §d); `variants-journal-ests.html` = HTTP 500; `whitman-archive.html` = 403 bot-wall; BDMP subpages returned 196-char app shells without body content (only `/manual/` carried substance). Claims below are restricted accordingly. [ests-wrong-site][dhq-mislabeled][variants-journal-500][whitman-403][bdmp-subpages-shells]

---

## (a) LANDSCAPE MAP

### A. Edition-centric genetic platforms

**A1. Beckett Digital Manuscript Project (BDMP) / beckettarchive.org**
- **Institution:** Centre for Manuscript Genetics (Univ. Antwerp) + Beckett International Foundation (Reading) + OCTET (Oxford) + Harry Ransom Center (UT Austin), with the Beckett Estate. Directors: Dirk Van Hulle, Mark Nixon; technical realisation: Vincent Neyt. Funded by ERC FP7 grant nº 313609. [bdmp-home]
- **URL:** https://www.beckettarchive.org/
- **Corpus scale:** 11 genetic editions published to date (latest: *Murphy*), bilingual EN/FR modules (*Molloy*, *Malone meurt*, *L'Innommable*, *Godot*, *Endgame*, *Krapp*, *Not I*, *That Time*, *Footfalls*, *Murphy*…); plus ancillary **Beckett Digital Library** and *Samuel Beckett: A Bibliography*. Won MLA Prize for a Bibliography, Archive, or Digital Project (Dec 2018). [bdmp-home]
- **How it models genesis:** finest-grained model in the corpus. Per-document overview with physical description, transcriber attribution, holding library, and **revision history of the transcription itself** ("if there were any revisions to the transcription since it was first published"). Facsimile/transcript alignment via **clickable image zones of ≤8 lines**, individually clickable doodles, marginal additions, dates, titles, **metamarks**. Five layered views: default transcription (strikethrough deletions, superscript additions, facing-leaf additions in green) → place indications (supralinear etc.) → **writing-tool layer** (colour-coded black ink/pencil/red ink) → "top layer" reading text → **raw XML encoding exposed**. Genesis accessed two ways: **chronology/genetic map** linking documents, and **sentence-level composition history** ("Compare sentences"): every sentence that reached the base text is numbered; clicking shows all versions in **vertical juxtaposition**, delegable to **CollateX** (Java collation service, InterEdition project) for automated collation. [bdmp-manual][collatex-ref] Full-text search with curated "suggested searches" (intertextual references, calculations, transpositions, gaps, stage drawings…). Free demos exist (*Krapp's Last Tape*, *Writing Sequence of L'Innommable*); full archive is **access-code gated**. [bdmp-manual]
- **Stack:** server-rendered HTML app shells (`$resources/` asset paths suggest a Java/XML pipeline; dedicated Technical Documentation + Encoding Guidelines sections exist but their bodies were not capturable in this corpus — SPA shells). [bdmp-subpages-shells] Editorial documentation is itself **versioned by state** (manual states preserved at 2011-06-24, L'Innommable 2013, Krapp Nov 2015, *Play/Comédie* Dec 2021). [bdmp-manual]

**A2. Faustedition**
- **Institution:** Anne Bohnenkamp, Silke Henke, Fotis Jannidis (eds.), with Gerrit Brüning, Katrin Henzel, Gregor Middell, Dietmar Pravida et al. Frankfurt am Main / Weimar / Würzburg, 2018. Version 1.3 RC. [faust-home]
- **URL:** https://www.faustedition.net/
- **Corpus scale:** the **complete surviving transmission** of *Faust* — manuscripts and prints c. 1774–1831 — as facsimiles, transcriptions, and witness descriptions. [faust-home]
- **How it models genesis:** explicit three-part architecture — **Archiv** (all witnesses: images, transcriptions, *Zeugenbeschreibungen*/witness descriptions), **Genese** (multiple **diagrams offering a genetically oriented access** to the whole work and its transmission across Goethe's lifetime of intermittent work), **Text** (newly constituted reading text from which every manuscript and print witness is reachable). Witness-first modeling: the witness description is a first-class object, matching TEI `msDesc` practice. [faust-home]
- **Stack:** JavaScript-required SPA (v1.3 RC); deep links like `/genese` return 404 to plain GETs (client-routed). [faust-genese-404] Corroborated by OpenAlex hit "Multiple Encoding in Genetic Editions: The Case of *Faust*" (2013) — the project publishes on its multi-layer encoding strategy. [openalex-sample]

**A3. Woolf Online**
- **Institution:** independent scholarly project (mojulem), NEH Scholarly Editions grant; ModNets peer-reviewed; published 2013. [woolf-online]
- **URL:** http://www.woolfonline.com/ (methodology page: `?q=about/methodology` — captured page duplicated home-page content [woolf-methodology-same])
- **Corpus scale:** one work, total documentary depth: holograph drafts (**three Berg Collection notebooks**, NYPL — physically fragile, access-restricted, hence high preservation value), typescripts, proofs, and ≥6 published states (GB 1st, USA 1st, Uniform, Everyman, Albatross editions **with variants**), plus dense context (diary entries, essays, letters, reviews, contracts, photographs). [woolf-online]
- **How it models genesis:** **embryonic-to-print witness chain** per section (*The Window*, *Time Passes*, *The Lighthouse*) with a **composition/revision/printing sequence** and a **timeline of composition**; transcriptions overlay page images with magnifier; even versos with word-count calculations included. Contextual materials linked to textual states rather than kept separate. [woolf-online]
- **Stack:** Drupal-style query-string routing (`?q=`…); image viewer + overlay transcription; login for advanced features. [woolf-online]

### B. Archive / corpus platforms

**B1. Nietzsche Source**
- **Institution:** General editor Paolo D'Iorio; partners CNRS, European Commission, Klassik Stiftung Weimar, Humboldt Stiftung, DFG.
- **URL:** http://www.nietzschesource.org/
- **Scale/model:** twin pillars — **Digitale Kritische Gesamtausgabe** (digital version of the Colli–Montinari critical edition of the complete works) and **Digitale Faksimile-Gesamtausgabe** (facsimile reproduction of the **entire Nietzsche archive**). Critical apparatus + total facsimile in one portal; the corpus captured only the home page (707 chars of substance), so internal modeling detail is thin here. [nietzsche-source]

**B2. ITEM — Institut des textes et manuscrits modernes (CNRS/ENS)**
- **URL:** http://www.item.ens.fr/
- **Scale/model:** the institutional home of French *critique génétique* and of the journal **Genesis**. Current corpus-visible signals: active Proust team (Proust pilgrimage study day, 05/2026), Flaubert seminar, multilingual-archives colloquia; and — key for this track — presentation of **Genesis nº 62 « Genèses artificielles »** (Rudolf Mahrer, 09/06/2026) and the announced **17th APCG International Congress: « Processos Criativos, Arquivos e Autoria em Tempos de IA Generativa / Processus créatifs, archives et autorité à l'ère de l'IA générative »** (English: "Creative processes, archives and authorship in the era of generative AI" — translation) (UEFS Bahia, April 2027). [item-apcg-2027] ITEM is where the field's AI discourse is concentrating — as **conference/journal discourse, not as archival infrastructure** (the dedicated Genesis 62 page itself returned HTTP 500). [item-genesis62-500]
- **Stack:** CMS site; deep item pages unstable (Proust item page 404). [proust-item-404]

**B3. Shelley-Godwin Archive (S-GA)**
- **Institution:** New York Public Library + MARYLAND Institute for Technology in the Humanities (MITH), with Bodleian, Huntington, British Library, Houghton, V&A — partners holding **over 90% of all known relevant manuscripts**. [sga-home]
- **URL:** https://shelleygodwinarchive.org/
- **Scale/model:** digitized manuscripts of the Godwin–Shelley circle (*Frankenstein* draft notebooks, *Prometheus Unbound*, *Political Justice*, *Caleb Williams*). Reuniting dispersed family papers online "for the first time". Licensed **CC BY-NC-SA 2.0**. [sga-home] (The captured page is an about/home shell; the project's well-known TEI-based transcription model is *not* asserted in this corpus file.)

**B4. Vincent van Gogh – The Letters**
- **Institution:** Van Gogh Museum + Huygens ING; 15 years of research; web edition of the 2009 scholarly edition. [vangoghletters]
- **URL:** https://vangoghletters.org/vg/
- **Scale/model:** **all** letters (to Theo, Gauguin, Bernard, etc.), richly annotated and illustrated, **new transcriptions plus authorized English translations**, navigation by period/correspondent/place/sketches, concordance, chronology, publication history. Model point: translation treated as a parallel, authorized textual layer — relevant to mozare's `translates` relation type. [vangoghletters]

**B5. Borges Center (Univ. of Pittsburgh)**
- **URL:** https://www.borges.pitt.edu/
- **Scale/model:** manuscript collections (In The Arts, The Secret Book, **The Helft Collection**, La Biblioteca Total), journal *Variaciones Borges* (no. 60 current). A writer-centric hub with manuscript galleries but no visible genesis-modeling machinery in the captured page; Ficciones resource page 404. [borges-center][borges-ficciones-404]

**B6. Cambridge Digital Library**
- **Institution:** University of Cambridge.
- **URL:** https://cudl.lib.cam.ac.uk/
- **Scale/model:** collection-level platform (Newton Papers, Cairo Genizah, Sanskrit MSS, Sterneana…) built on the **Cambridge Digital Collections Platform**; includes **crowdsourced transcription** ("Help us transcribe the notebooks of Oliver Rackham") — archive platform + participation hybrid. No genesis modeling; fixity/preservation claims not surfaced in captured page. [cudl]

**B7. Walt Whitman Archive** — **NOT CAPTURED**: whitmanarchive.org returned **HTTP 403** (Cloudflare JS challenge). Existence known from bibliography; content unverified in this corpus. [whitman-403]

**B8. Bodleian Kafka holdings** — the captured page is a generic "past exhibitions" template with no Kafka content; the digital catalogue `kafka.bodleian.ox.ac.uk/catalogue` was **unreachable (status 0)**. Kafka digital archive therefore **unverified** in this corpus. [kafka-bodleian-shell]

### C. Crowdsourcing / transcription infrastructure

**C1. Transcribe Bentham (UCL)**
- **URL:** https://blogs.ucl.ac.uk/transcribe-bentham/ (+ Transcription Desk)
- **Scale:** launched 2010; volunteers have transcribed **44,000+ pages** of Bentham's MSS; transcripts feed the *Collected Works of Jeremy Bentham*. Double award-winning; canonical participatory-transcription workflow (account → Transcription Desk → transcribe → review → edition). [transcribe-bentham][tb-about]
- **How it models genesis:** it does not model *authorial* genesis — it models **crowd transcription as a quality-controlled derivation process** with a public **Recent Changes log**, per-transcriber profiles/statistics, and explicit error-reporting channels. Its 07/2025 server-migration incident report candidly documents breakage of side-by-side image/transcript preview "without TEI tags" — evidence that the desk produces **lightly-tagged (TEI-influenced) text** validated against images. [transcribe-bentham]
- **Lesson for mozare:** transparency logging and contribution attribution as first-class metadata.

**C2. Cambridge Rackham transcription** — see B6; institutional crowdsourcing call inside an archive platform. [cudl]

### D. Theory / methodology bodies & journals

**D1. ESTS / Variants — verification failure.** The corpus intended to capture the European Society for Textual Scholarship and its journal *Variants*. In reality `ests.org` now serves the **European Society of Thoracic Surgeons** (captured 200), and `ests.org/journal` returned **HTTP 500**; `est-journal.eu` was unreachable (status 0). The society's web presence could **not** be documented from this corpus. *Variants* remains bibliographically visible via Crossref/OpenAlex (below). [ests-wrong-site][variants-journal-500]

**D2. DHQ — Digital Humanities Quarterly** (open access, ISSN 1938-4122).
- Captured: vol. 7.2 (2013) and vol. 8.1 (2014) tables of contents — **general DH issues**, no genetics special issue in either. [dhq-72][dhq-81] Load-bearing item found: Reed, *"Managing an Established Digital Humanities Project: Principles and Practices from the Twentieth Year of the William Blake Archive"* (DHQ 8.1, 2014) — the corpus's main testimony on **long-term maintenance economics** of mature digital archives (staff turnover, funding cliffs, scope drift). [dhq-81]
- **Mislabeled file:** `dhq-pierazzo-genetic.html` actually contains DHQ 13.1 (2019) 000412, Hawk/Karaisl/White, *"Modelling Medieval Hands: Practical OCR for Caroline Minuscule"* — neural-network (Krutheisera/OCRise-style, open-source) OCR of medieval handwriting reaching **90–97% character/word accuracy**. Relevant to mozare as evidence that **HTR/OCR-assisted intake of manuscript images is production-grade**; Pierazzo's genetic-editions article itself is **absent** (present only as OpenAlex author metadata). [dhq-mislabeled][openalex-sample]

**D3. Textual Cultures** (Indiana University ScholarWorks; successor to *TEXT*, journal of the Society for Textual Scholarship).
- **URL:** https://scholarworks.iu.edu/journals/index.php/textual
- Vol. 19.1 (July 2026): "Writers' Libraries, Extant and Lost" incl. Van Hulle on reading notes/marginalia, Melville's Marginalia Online data analysis. Venue for textual scholarship bridging editors/bibliographers/digital humanists. [textual-cultures]

**D4. Bibliometric picture (Crossref + OpenAlex samples).**
- Crossref query sample (25 items): Gabler, *"Digital Genetic Editing and Computer-Assisted Genetic Criticism"* (2022) and *"Compiling a Genetic Dossier"* (2022); *"Editing the Wake's Genesis: Digital Genetic Criticism"* (2018, *James Joyce and Genetic Criticism*); *"The 'Version History' as a Digital Variorum: Tracking Genetic Criticism…"* (2026); *"Genetic Criticism Put to the Test by Digital Technology"* (Variants 2016); *"Modelling a Digital Scholarly Edition for Genetic Criticism: A Rapprochement"* (Variants 2016); *"Dynamic Facsimiles: Note on the Transcription of Born-Digital Works for Genetic Criticism"* (Variants 2021); *"Genetic Game Criticism"* (2022); *"Genetic Criticism and Analysis of Interface Design. A Case Study"* (Digital Studies 2022). [crossref-sample]
- OpenAlex query: **meta.count = 3,312** total works for the broad search string (heavy tail includes off-topic noise, e.g. unrelated "digital fascism" hits — treat count as upper bound of a fuzzy query, not a field census). Sampled 25 results: top author **Dirk Van Hulle (7)**, then Hans Walter Gabler (2); top venues **Variants (5)**, Digital Scholarship in the Humanities (2), Open Book Publishers (2), jTEI (1), Textual Cultures (1), DHQ (1). Span 2009–2023. [openalex-sample]
- Read: the field's digital core is small, Antwerp-centred (Van Hulle/Gabler/CollateX/ERC 313609 cluster), venue-poor (essentially *Variants* + DHQ + jTEI), and its recent frontier topics are exactly **born-digital drafts ("dynamic facsimiles"), computer-assisted genetic editing, version histories as variorums, and generative-AI authorship** — all adjacent to mozare's design space. [crossref-sample][openalex-sample]

### E. Tooling, standards, infrastructure

**E1. TEI P5 Guidelines** (TEI Consortium).
- **URL:** https://www.tei-c.org/Guidelines/P5/ ; chapter texts captured from the versioned Vault: ch. 11 *Manuscript Description*, ch. 12 *Representation of Primary Sources* (current release 4.12.0, rev 113e933e2, 2026-07-28). [tei-msdesc][tei-transcription]
- **Genesis-modeling vocabulary (ch. 12, transcr module):** `facsimile` / `surface` / `zone` / `line` for image-coordinated transcription (`att.coordinated`, SVG-compatible polygon points); `add`, `del`, `subst`, `substJoin`, `addSpan`/`delSpan`, `restore`, `redo`, `undo`, `retrace`, `secl`, `surplus`, `transpose`/`listTranspose`, `metamark`, `mod`, `handShift`/`handNotes`, `fw`, `space`, `damage`, `supplied`; attributes `seq` (order of additions/deletions — explicitly described as supporting "'genetic' textual criticism typified by … Gabler's work on … *Ulysses* overlay levels"), `hand`, `resp`, certainty machinery, and `att.global.facs`/`att.global.change`. **§12.7 Identifying Changes and Revisions** defines the *revision-campaign* model: `profileDesc/creation/listChange/change[@ordered]` groups alterations into named, orderable, nestable **changes** ("First stage, written in ink", "Second stage, pencil revisions"…) — i.e., TEI's native answer to mozare's staged-genesis problem. Ch. 11 supplies `msDesc` with `physDesc`, `history` (`origin`, `provenance`, `acquisition`) — witness metadata as structured data. [tei-transcription][tei-msdesc]
- **Governance/sustainability model:** fully open source (GitHub-traceable development, per-release **Vault** archives, Zenodo concept DOI 10.5281/zenodo.3413524, Debian packages, Roma schema builder, TEIGarage, oXygen bundling). The TEI's release-Vault pattern — every published state permanently addressable — is the standards-world analogue of mozare's `_originals/` immutability. [tei-p5]

**E2. Versioning Machine 5.0** (Susan Schreibman; last modified 2016-01-21).
- **URL:** http://v-machine.org/
- **Model:** display framework for **multiple versions of TEI-encoded texts** (P5-compatible), building on the TEI critical-apparatus chapter; diplomatic witness panels, manuscript-image ↔ diplomatic-text comparison, annotation, resizable panels, pan/zoom image viewer, text-audio interlinking; runs **locally on Mac/PC or mounted on the web**. A lightweight, file-based witness-comparison viewer — the closest corpus ancestor of what this dossier calls a static publication layer. [versioning-machine]

**E3. TextGrid** (textgrid.de; Repository textgridrep.org).
- **Model:** virtual research environment optimised for **TEI-coded resources**: **TextGrid Laboratory** (work environment covering the entire editing→publication workflow; open-source tools/community/tutorials/bug tracker/source code) + **TextGrid Repository** (**long-term research-data archive**, CoreTrustSeal 2020, aligned with **FAIR and Open Access**; publish TEI/XML + images citably with required metadata; bulk download XML/TXT; user collections via "shelf"; filter by author/genre/filetype/project). Content base: Digital Library of German-language world literature by **~600 authors**; project-specific edition content (Library of Neology, ARCHITRAVE). Offered under DARIAH-DE since 2015; developed within NFDI. Site itself built with Hugo; content CC BY 4.0. [textgrid-home][textgrid-repo]

**E4. DARIAH-DE** (de.dariah.eu).
- Since 2021 coordinated through **Verein GKFI e.V.** (transformation of TextGrid e.V.); services anchored in NFDI consortia **Text+, NFDI4Culture, NFDI4Memory, NFDI4Objects**. Signal: national-scale DH infrastructure is consolidating into persistent associations — sustainability-by-design, contrasted with grant-cycle project mortality documented in DHQ 8.1. [dariah-de][dhq-81]

**E5. CollateX** (via BDMP manual): Java-based collation software producing critical apparatus; used as third-party service from BDMP's synoptic sentence view (<https://collatex.net/>; InterEdition project). [collatex-ref][bdmp-manual]

---

## (b) WHERE MOZARE SITS

**Evaluation criteria (stated up front):**
1. **Genesis-modeling granularity** — how finely drafts/witnesses/version-steps and their relations are distinguished.
2. **Evidence & claim governance** — whether interpretation is separated from source and qualified by authority level.
3. **Immutability / fixity guarantees** — whether original states are protected against silent alteration (checksums, versioned vaults).
4. **Machine-readability & interchange** — structured, exportable formats others can consume.
5. **Human interface** — reading/comparison experience (alignment, juxtaposition, maps).
6. **Publication openness** — public availability, licensing, citation.

| Criterion | Published flagship practice (corpus-verified) | mozare-wiki | Verdict |
|---|---|---|---|
| 1. Genesis granularity | BDMP: sentence-level composition histories, writing-tool layers, metamarks; TEI §12.7 revision campaigns; Faust witness descriptions + genese diagrams [bdmp-manual][tei-transcription][faust-home] | One source record per artifact; extracted derivatives; typed relations incl. `supersedes`, `is-version-of`, `derived-from` | **Parity on relations; below flagship on intra-document granularity** (no sentence-level alignment or writing-tool layer) |
| 2. Evidence/claim governance | **Absent everywhere.** BDMP tracks transcription revisions as prose metadata; nobody separates CLAIM from SOURCE or grades authority levels [bdmp-manual] | Explicit 8-level authority hierarchy; evidence-qualified CLAIM objects | **Clear mozare advantage** |
| 3. Immutability/fixity | TEI Vault + Zenodo DOIs (standards level) [tei-p5]; CoreTrustSeal repository promises (TextGrid) [textgrid-repo]; BDMP manual preserves historical states [bdmp-manual]. **No corpus file documents per-artifact checksums at any flagship** [cand-no-checksums] | SHA-256-checksummed immutable `_originals/`, Git-versioned interface | **mozare advantage at artifact level** (flagships rely on institutional trust, not cryptography) |
| 4. Machine-readability | Universal convergence on **TEI P5 XML** (BDMP exposes XML; TextGrid XML/TEI; VM P5-only; TEI chapters define interchange) [tei-p5][textgrid-repo][versioning-machine][bdmp-manual] + stable APIs/DOIs | Markdown/QMD, JSON-ish records, PATCH_MANIFEST.json; **no TEI import/export** | **Flagship advantage — mozare's biggest structural gap** |
| 5. Human interface | Image↔text zone alignment, vertical juxtaposition, collation views, genetic maps (BDMP/Faust/Woolf/VM) [bdmp-manual][faust-home][woolf-online][versioning-machine] | Obsidian/Git Markdown browsing + QMD semantic search | **Split:** mozare wins on semantic retrieval; loses on diplomatic comparison UI (no facsimile alignment at all) |
| 6. Publication openness | All flagships public, mostly licensed (CC BY-NC-SA, CC BY 4.0) [sga-home][textgrid-home]; one access-code exception (BDMP full archive) [bdmp-home] | **Private, unpublished** — by design | **Flagship advantage; mozare currently forfeits citability/reuse entirely** |

**Honest summary.** Mozare's distinctive contributions — claim/evidence governance, an explicit authority hierarchy, typed inter-artifact relations, cryptographic fixity of originals, and multi-agent patch governance — are **not present in any surveyed flagship project**; the corpus supports this as a genuine white space rather than marketing. [cand-mozare-white-space] Conversely, mozare lacks the three things the field treats as table stakes: a TEI-based interchange format, witness-level facsimile alignment, and a public, citable publication layer. Its multi-agent intake (GPT authors, Claude validates) has **no precedent anywhere in the corpus** — neither as strength nor warning; there is no prior art to inherit, only adjacent discourse (ITEM Genesis 62, APCG 2027, Gabler 2022 "computer-assisted" framing). [item-ens][crossref-sample]

---

## (c) IMPROVEMENT BACKLOG

1. **[ADOPT] TEI P5 export path.** Map each source record → `teiHeader` + `msDesc` (physDesc/history/provenance), each derivative/canonical object → `text` or `sourceDoc/surface/zone`, each staged interpretation → `creation/listChange/change[@ordered]`, relations → `@copyOf/@sameAs/@prev/rel` attributes. Serves criterion 4 (interchange) and makes the archive legible to BDMP/TextGrid-class consumers. Grounded in captured TEI ch. 11–12. [tei-msdesc][tei-transcription]
2. **[ADOPT] Witness-level sentence alignment view.** Port BDMP's numbered-sentence "vertical juxtaposition" pattern (optionally delegating diffing to Collatex or a pure-Python equivalent) over extracted derivatives. Serves criteria 1 and 5 without requiring image servers. [bdmp-manual][collatex-ref]
3. **[ADOPT] Static public publication layer.** Generate a read-only static site (Hugo — the exact choice TextGrid's own site uses) from canonical objects, excluding `_originals/` where rights demand; give canonical objects stable IDs + content-hash addresses à la TEI Vault/Zenado DOIs. Serves criterion 6; converts "private" into "publishable at will". [textgrid-home][tei-p5]
4. **[ADOPT] Editorial-charter versioning.** Preserve dated immutable states of mozare's own editorial principles/governance docs (BDMP keeps its manual's 2011/2013/2015/2021 states addressable). Serves criterion 3 applied to policy, not just artifacts. [bdmp-manual]
5. **[ADAPT] Transcription-revision ledger.** BDMP records who revised a transcription and when as document metadata; generalize into mozare's Git history + a first-class "derivative revision" relation, feeding the derivative-witness authority tier. Serves criterion 2. [bdmp-manual]
6. **[ADAPT] HTR/OCR-assisted intake with confidence tiering.** DHQ 13.1 shows neural OCR at 90–97% accuracy on difficult hands; route machine-extracted text into mozare as **candidate-tier** derivatives with per-field confidence, never auto-promoted. Serves criteria 1–2; formalizes AI-mediated philology inside the existing hierarchy instead of inventing a parallel channel. [dhq-mislabeled]
7. **[ADAPT] Maintenance-cost plan.** DHQ 8.1 (Blake Archive at 20 years) documents staff/funding decay; mozare's counter-model is Git + static files, but add an explicit low-power fallback (plain Markdown renders without QMD/search stack). Serves longevity. [dhq-81]
8. **[REJECT] Facsimile image-server infrastructure (IIIF-class, image/text zone maps à la BDMP).** Reason: operational weight (image hosting, coordinate tooling) is unjustified while the archive is private and text-first; revisit only if item 3 ships and scans enter `_originals/` at scale. The *capability* it serves (diplomatic comparison) is partly covered by item 2. [bdmp-manual]
9. **[REJECT] Access-code gating model (BDMP-style).** Reason: incompatible with the Git/local philosophy and unnecessary pre-publication; if publication happens, prefer open static + license statements (CC BY-NC-SA precedent from S-GA). [bdmp-home][sga-home]
10. **[REJECT] Institutional VRE adoption (TextGrid Laboratory as working environment).** Reason: Eclipse-era desktop VRE duplicates what mozare already gets from Git/Obsidian at personal scale; borrow only its **FAIR/CoreTrustSeal checklist** as a self-audit rubric. [textgrid-repo]

*(Items 1–3 are the load-bearing trio: interchange, comparison, publication.)*

---

## (d) NEGATIVE FINDINGS (verified absences in this corpus)

1. **No AI-mediated intake governance exists in any flagship project.** The corpus's only AI-adjacent items are discourse, not systems: ITEM's Genesis 62 "Genèses artificielles" presentation (06/2026), the APCG 2027 congress on archives and authorship in the era of generative AI (title captured verbatim in Portuguese/French), and Gabler's 2022 title "Computer-Assisted Genetic Criticism" (content not captured). None describes authority tiers, validation chains, or checksum governance for machine-generated text. [item-apcg-2027][crossref-sample][cand-no-ai-governance] *(Grounded in corpus files; generalized absence is an inference → candidate-tier.)*
2. **No personal-archive-scale system.** Every functioning project surveyed is institutional, grant-funded, and work-centric (one author or one corpus). Nothing resembles a single scholar's living archive spanning multiple domains with self-service ingest. [cand-no-personal-scale] *(Candidate-tier inference from all 26 successful captures.)*
3. **No cryptographic fixity at any flagship.** BDMP, Faust, Woolf Online, S-GA, TextGrid pages document trust via institutions, licenses, CoreTrustSeal, and DOIs; none mentions per-artifact checksums. TEI's Vault/Zenodo is the nearest analogue, at standards level. [cand-no-checksums][tei-p5] *(Verified against captured texts.)*
4. **ESTS/Variants web presence unverifiable:** `ests.org` domain-serves a thoracic-surgery society (HTTP 200), `ests.org/journal` = 500, `est-journal.eu` = unreachable. The field's principal journal could not be directly documented here. [ests-wrong-site][variants-journal-500]
5. **Mislabeled corpus file:** `dhq-pierazzo-genetic.html` ≠ a Pierazzo genetic-criticism article; it is Hawk/Karaisl/White, "Modelling Medieval Hands" (DHQ 13.1, 2019). Pierazzo appears only in OpenAlex author metadata. Similarly, `dhq-genetic-editions-index.html` (vol. 8.1) and `dhq-vol7-no2-index.html` are ordinary issues — no DHQ genetics special issue was captured. [dhq-mislabeled][dhq-81][dhq-72]
6. **Bot-walls and dead ends:** Whitman Archive (403 challenge); van Hulle "Modelling a Digital Scholarly Edition for Genetic Criticism" (doi 10.4000/variants.293 → OpenEdition Anubis bot-check on two attempts — metadata only); Wikidata SPARQL for BDMP returned **zero bindings**; Fontane Notizbücher, both jTEI articles (Sahle; Pierazzo), and the Bodleian Kafka catalogue all status-0 fetches; BDMP editorial-principles/encoding-guidelines/technical-documentation pages exist (200) but are JS shells whose substantive text was not captured — BDMP's *encoding guidelines proper* remain unread. [whitman-403][van-hulle-anubis][wikidata-bdmp-empty][kafka-bodleian-shell][bdmp-subpages-shells]
7. **No corpus file documents born-digital-draft handling in practice:** "Dynamic Facsimiles" (Variants 2021) exists only as a title; the practical question of archiving word-processor/AI-era drafts — central to a *living* archive — is unaddressed in every captured project page. [crossref-sample][cand-no-ai-governance]

---

*Local copies: `raw/*.html` (+ `_txt/` stripped text, incl. `tei-vault-msdesc.txt`, `tei-vault-transc.txt` re-fetched 2026-08-25). Provenance, statuses, and authority tiers per fact: see `SOURCES.json`.*

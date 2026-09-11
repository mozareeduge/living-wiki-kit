#!/usr/bin/env python3
"""Generate candidate objects/relations/claims for ref-wiki deepen phase (2026-09-11).

All records are CANDIDATE-tier (authority level 7): interpretive synthesis mined from
the eleven registered research-campaign sources. Nothing here upgrades evidence.
Run from the ref-wiki root: python _proposals/2026-09-11_mine_objects.py
"""
import json, os, datetime

ROOT = os.path.dirname(os.path.abspath(__file__)).replace("/_proposals", "")
if not os.path.isdir(os.path.join(ROOT, "03-objects")):
    ROOT = r"C:/Users/Zarinpal/Documents/Personal Formal Documents/living-wiki-kit"
TODAY = "2026-09-11"

# source id shorthands
T1 = "ref-src-ce2c27f34110"  # digital genetic criticism
T2 = "ref-src-70b92d6a3b3b"  # PKM landscape
T3 = "ref-src-aea0e94fe5c9"  # ontology/provenance standards
T4 = "ref-src-6e5e5f482216"  # OOO in the wild
T5 = "ref-src-02e16ccb7ee5"  # AI scholarship & evidence governance
T6 = "ref-src-ad1f8275e17f"  # artistic research living archives
T7 = "ref-src-f3873bdd4b43"  # research-through-making terms
LM = "ref-src-bbb62335d984"  # wave-1 landscape map
FR = "ref-src-aca75aca2552"  # final report
RD = "ref-src-702ab37396b6"  # campaign readme
ME = "ref-src-ee4dfce59174"  # meta evaluation

def fm(d):
    return "---\n" + json.dumps(d, indent=2, ensure_ascii=False) + "\n---\n\n"

def slug_fn(base, slug):
    return f"{base}-{slug}"

def write_object(kind_dir, slug, title, kind, characterization, grounding, relations, sources, extra=None):
    rid = f"ref-obj-{slug}"
    path = os.path.join(ROOT, "03-objects", kind_dir, slug + ".md")
    meta = {
        "id": rid, "type": "object", "title": title, "kind": kind, "aliases": [],
        "candidate_tier": True, "authority_note": "candidate (level 7); mined from registered dossier sources; never asserted as verified beyond the dossier text",
        "status": "active-record", "visibility": "private",
        "created": TODAY, "updated": TODAY, "schema_version": "1.0.0",
    }
    if extra: meta.update(extra)
    rel_lines = "\n".join(f"- [[{r}]]" for r in relations) if relations else "- (none yet)"
    src_lines = "\n".join(f"- [[{s}]]" for s in sources)
    body = f"""# {title}

## Characterization

{characterization}

## Source grounding

{grounding}

Supporting sources (registered in this wiki):

{src_lines_block(sources)}

## Relations

{rel_lines if relations else '- (none yet)'}

## Open work

- Adjudication: candidate-tier until human review upgrades or corrects it.
"""
    meta_block = fm(meta)
    with open(path, "w", encoding="utf-8") as f:
        f.write(meta_block + "\n" + body)
    return rid

def src_lines_block(sources):
    return "\n".join(f"- [[{s}]]" for s in sources)

def write_relation(slug, title, participants, description, sources):
    rid = f"ref-rel-{slug}"
    path = os.path.join(ROOT, "06-relations", slug + ".md")
    meta = {
        "id": rid, "type": "relation-object", "title": title,
        "participants": participants,
        "relation_status": "candidate",
        "current_claim_permission": "may-note",
        "supporting_sources": sources,
        "counter_evidence": [],
        "use_status": ["candidate-mining"],
        "status": "active", "visibility": "private",
        "created": TODAY, "updated": TODAY, "schema_version": "1.0.0",
    }
    part_lines = "\n".join(f"- [[{p}]]" for p in participants)
    src_lines = "\n".join(f"- [[{s}]]" for s in sources)
    body = f"""# {title}

## Initial pressure

The research-campaign dossiers profile concrete external systems and standards and position the
operator's evidence-governed grammar against them. Relations below record how the profiled things
connect, at candidate tier, grounded only in the registered dossier text.

## Participants and profiles

{part_lines}

## Current description

{description}

## Sources

{src_lines}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm(meta) + "\n" + body)
    return rid

def write_claim(slug, title, statement, scope, sources, counter=None, note=""):
    rid = f"ref-claim-{slug}"
    path = os.path.join(ROOT, "05-claims", slug + ".md")
    meta = {
        "id": rid, "type": "claim-object", "title": title,
        "statement": statement, "scope": scope,
        "supporting_sources": sources,
        "unsupported_zones": [], "counter_evidence": [],
        "evidence_state": ["candidate-mining-2026-09-11"],
        "certainty": "candidate",
        "current_claim_permission": "may-note",
        "responsible_language": "en",
        "citation_status": "dossier-grounded; per-fact provenance lives in the origin campaign's SOURCES.json (not copied into this wiki)",
        "status": "active", "visibility": "private",
        "created": TODAY, "updated": TODAY, "schema_version": "1.0.0",
    }
    src_lines = "\n".join(f"- [[{s}]]" for s in sources)
    body = f"""# {title}

## Current statement

{statement}

## Support

{src_lines}

## Limits and counter-evidence

{counter if counter else '- None recorded beyond the dossier caveats quoted in the statement.'}

## Use history

- Mined {TODAY} from the research-campaign intake; candidate tier.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm(meta) + "\n" + body)
    return rid

counter = None  # placeholder

# ================= OBJECT DATA =================
# kind_dir in {references, concepts, methods, people, works, institutions}

OBJECTS = []

def O(kind_dir, slug, title, char, ground, sources, rels=None, kind=None):
    OBJECTS.append((kind_dir, slug, title, kind or kind_dir[:-1], char, ground, rels or [], sources))

# ---- references ----
O("references","bdmp","Beckett Digital Manuscript Project (BDMP / beckettarchive.org)",
  "The finest-grained genesis model in the surveyed corpus: per-document transcription with a revision history of the transcription itself, five layered views (including a writing-tool layer), clickable image zones, and a sentence-level composition history presenting every version of each base-text sentence in vertical juxtaposition, delegable to CollateX. Directed by Dirk Van Hulle and Mark Nixon; full archive access-code gated.",
  "T1 dossier section A1, with inline [bdmp-home]/[bdmp-manual]/[bdmp-subpages-shells] markers; BDMP's own encoding-guidances were JS shells, so its encoding guidelines proper remain unread in that corpus.",
  [T1], ["bdmp-delegates-collation-to-collatex","tei-underpins-genetic-editions","bdmp-witness-model-matches-tei"])
O("references","faustedition","Faustedition",
  "Digital critical edition of the complete surviving transmission of Faust (c. 1774-1831) with an explicit three-part architecture: Archiv (witnesses), Genese (genetically oriented diagrams), Text (constituted reading text). Witness-first modeling, matching TEI msDesc practice.",
  "T1 dossier section A2 [faust-home][faust-genese-404].",
  [T1], ["faust-witness-first-matches-tei","tei-underpins-genetic-editions"])
O("references","woolf-online","Woolf Online",
  "One-work scholarly edition with an embryonic-to-print witness chain per section, a composition/revision/printing sequence, and a timeline of composition; contextual materials linked to textual states rather than kept separate.",
  "T1 dossier section A3 [woolf-online].",
  [T1], [])
O("references","nietzsche-source","Nietzsche Source",
  "Twin-pillar Nietzsche portal (Paolo D'Iorio, CNRS/Weimar partners): the digital Colli-Montinari critical edition plus a facsimile reproduction of the entire Nietzsche archive in one site.",
  "T1 dossier section B1 [nietzsche-source]; corpus captured only the home page, so internal modeling detail is thin.",
  [T1], [])
O("institutions","item-cnrs","ITEM — Institut des textes et manuscrits modernes (CNRS/ENS)",
  "Institutional home of French critique génétique and of the journal Genesis; the field's AI discourse is concentrating here as conference and journal discourse (Genesis 62 'Genèses artificielles', APCG 2027 congress on archives and authorship in the era of generative AI) rather than as archival infrastructure.",
  "T1 dossier section B2 [item-apcg-2027][item-genesis62-500]; the Genesis 62 page itself returned HTTP 500 during capture.",
  [T1], ["ai-discourse-in-field-is-not-infrastructure"])
O("references","tei-p5","TEI P5 (Text Encoding Initiative)",
  "The XML encoding standard every digital genetic edition builds on: manuscript description (msDesc, physDesc, history), transcription of primary sources, genetic apparatus, facsimile/sourceDoc modules. The dossier positions the operator's Markdown grammar as an alternative, lighter representation of the same problem space.",
  "T3 dossier landscape table [TEI01][TEI02] and T1 backlog item 1 [tei-msdesc][tei-transcription].",
  [T1,T3], ["tei-underpins-genetic-editions","faust-witness-first-matches-tei"])
O("references","collatex","CollateX",
  "Java collation service (InterEdition project) that BDMP delegates automated collation to; candidate for porting a witness-level sentence-alignment view over the wiki's derivatives.",
  "T1 dossier section A1 [collatex-ref] and backlog item 2.",
  [T1], ["bdmp-delegates-collation-to-collatex"])
O("references","prov-o","PROV-O (W3C)",
  "W3C provenance ontology (Entity/Activity/Agent) whose predicates — wasDerivedFrom, wasRevisionOf, specializationOf, wasAttributedTo, hadPrimarySource — are the direct standard counterparts of the operator's derivation-family relations; the dossier's top adoption target (export profile for the eight relations).",
  "T3 dossier convergence table [S04] and backlog item 1.",
  [T3], ["derived-from-maps-to-prov-wasderivedfrom","supersedes-maps-partially-to-prov","summarizes-and-adapts-are-reinvented"])
O("references","skos","SKOS (W3C)",
  "W3C Simple Knowledge Organization System: ConceptScheme/Concept with prefLabel, broader/narrower, exactMatch/closeMatch; the standard shape for exporting the wiki's controlled vocabularies (relation types, statuses) as machine-readable schemes.",
  "T3 dossier standards table [SKOS01].",
  [T3], [])
O("references","cidoc-crm","CIDOC-CRM v7.3.2 (ISO 21127)",
  "Event-centric cultural-heritage ontology whose E13 Attribute Assignment is the formal class for claims about relations; ships no first-class is-version-of property (versioning expressed through activities instead). Claim records approximate E13 instances.",
  "T3 dossier standards table and convergence table [S01][S02][S03].",
  [T3], ["claim-records-approximate-e13-assignments","cidoc-has-no-version-predicate"])
O("references","wikibase-datamodel","Wikibase DataModel",
  "Wikimedia's data model in which a Statement = claim (snak) + qualifiers + ReferenceRecords + Rank (preferred/normal/deprecated); the closest large-system analogue to the operator's claim/evidence design — but it grades by rank, not an authority ladder, and allows empty references.",
  "T3 dossier convergence table [WB01] and backlog item 2 (rank field adoption).",
  [T3], ["claim-records-vs-wikibase-statements","supersedes-maps-partially-to-prov"])
O("references","premis","PREMIS (preservation metadata)",
  "Preservation standard whose fixity core (checksums per artifact) is the concept-level analogue of the operator's SHA-256 immutable originals; official docs were blocked to automated capture in the campaign (403, archive fallback empty), so the comparison stands at concept level, candidate-tier.",
  "T3 dossier convergence table [PREMIS01] and negative findings.",
  [T3], ["checksum-fixity-concept-aligned-with-premis"])
O("references","ifla-lrm","IFLA LRM-ER",
  "Library-world consolidation of FRBR/FRAD/FRSAAD: Work-Expression-Manifestation-Item layering as the model of textual genesis across versions and carriers; maps onto the wiki's drafts/witnesses/version-families, though via class layering rather than pairwise edges.",
  "T3 dossier standards table [LRM01][LRM02]; machine-readable distributions were unreachable during the campaign.",
  [T3], ["is-version-of-maps-partially-to-lrm"])
O("references","ro-crate","RO-Crate (Research Object packaging)",
  "JSON-LD research-object packaging standard (Dataset root, conformsTo, hasPart, CreateAction provenance, Profiles). The operator's repos already ship ro-crate-metadata.json; structure follows the crate pattern but alignment against the 1.3 Profiles machinery was unverified in the campaign corpus.",
  "T3 dossier convergence table [ROC01][ROC02].",
  [T3], [])
O("references","consumer-rag-products","Consumer RAG-over-archive products",
  "The 'chat with your documents' wave: NotebookLM (grounded-notebook paradigm, citation-display-only provenance), Open WebUI (partial exception: SHA-256 hash-sync directory mirroring — sync, not an immutability contract), kotaemon (displays relevance scores next to citations, the exact score-as-evidence conflation the operator's governance forbids), AnythingLLM, privateGPT, Khoj, Quivr.",
  "T5 dossier section A1, verified from official docs/readmes [S01-S12][S27-S30].",
  [T5], ["kotaemon-conflates-retrieval-score-with-verification","open-webui-sync-is-not-immutability"])
O("references","claude-obsidian","claude-obsidian (agentic vault system)",
  "The closest structural cousin found in the agentic-wiki wave: immutable content-addressed copies before synthesis, claim ledgers with authority/freshness/support/contradiction/confidence fields, plan-SHA256 approved-write transactions, single-orchestrator merge discipline. Even it lacks a multi-level authority hierarchy, immutable-original checksums as contract, and permission-to-argue states.",
  "T2 dossier section A4 wave-2 assessment, verified from the project README [S13]; T2 criterion C1 verdict 'ahead of everything found'.",
  [T2], ["claude-obsidian-closest-cousin-still-behind"])
O("references","karpathy-llm-wiki","Karpathy LLM-wiki pattern",
  "Andrej Karpathy's formulation that RAG 'rediscovers knowledge from scratch on every question — nothing is built up', against which an agent should 'incrementally build and maintain a persistent wiki... compiled once and then kept current', naming wiki-maintenance burden as the failure mode this solves; catalyzed the agentic-wiki clone wave.",
  "T2 dossier section A4 [S6] and the clone list [S7][S11][S12][S13][S14][S15].",
  [T2], ["karpathy-catalyzed-agentic-wiki-wave"])
O("references","research-catalogue","Research Catalogue (RC)",
  "Non-commercial collaboration and publishing platform of the Society for Artistic Research; the de-facto infrastructure of the artistic-research field, built to publish process (sketches, failures, versions) as scholarship — the publication genre the operator's private-first archives currently lack a path into.",
  "T6 dossier sections A1 and (b) [S01][S02][S03].",
  [T6], ["publication-gap-against-research-catalogue"])
O("references","variable-media-questionnaire","Variable Media Questionnaire",
  "Forging the Future alliance project recording opinions on how to preserve creative works: behavior/medium-independent preservation planning via structured questionnaires. Core insight adopted here: preservation decisions are metadata about future behavior, not file formats.",
  "T6 dossier section A4 [S07] and backlog item 1.",
  [T6], ["vmq-informs-succession-records"])
O("references","webrecorder-suite","Webrecorder suite (Browsertrix)",
  "The working open-source stack for capturing volatile web artworks: automated browser-based crawling at scale, serverless replay, file-format specs. Candidate backbone for a capture pipeline that stores cited web sources as checksummed derivatives with source-record entries.",
  "T6 dossier section A4 [S08] and backlog item 3.",
  [T6], ["webrecorder-informs-capture-pipeline"])
O("references","c2pa","C2PA (content provenance standard)",
  "Cryptographic content-provenance standard for media capture chains; binds provenance for media capture chains, not scholarly archives — the nearest external analogue to fixity binding, with a scope mismatch.",
  "T5 dossier criterion-3 verdict [S31].",
  [T5], ["c2pa-scope-mismatch-with-scholarly-archives"])
O("references","icmje-cope","ICMJE / COPE authorship norms",
  "Journal governance bodies whose norms require human accountability for AI-assisted text (ICMJE) and type human contribution roles without settling AI's status (CRediT, via COPE discourse); the operator's PATCH_MANIFEST pipeline makes every machine-authored change declared, diffable, and gated before landing — stronger than journal post-hoc disclosure.",
  "T5 dossier criterion 4 [S25][S26].",
  [T5], ["machine-edit-auditability-exceeds-journal-norms"])
O("references","rag-eval-lineage","Faithfulness & attribution evaluation lineage",
  "The canonical evaluation/attribution research line: ALCE, RAGAS, Self-RAG, HaluEval, FActScore, CRAG, AIS (Rashkin et al., Attributable to Identified Sources), Model Cards, Datasheets for Datasets, Search-R1, and the 2025-26 frontier (ProvenAI citation-influence decomposition, LineageRAG verbatim evidence lineages, EvoTrustRAG conflict-evolution attribution, LayerRAG-Bench layered grounding). The operator's benchmark measures retrieval only — no faithfulness score has ever been run over QMD-mediated answers.",
  "T5 dossier sections A3 and criterion 6 [S13-S22][S34].",
  [T5], ["evaluation-gap-is-faithfulness-not-retrieval"])
O("references","kepano-obsidian-skills","Obsidian CLI + agent skills (kepano)",
  "kepano's obsidian-skills repo (47k+ stars, heavily forked within months): the strongest single signal that agent-operated vaults became a mainstream concern in 2026 — the ecosystem standard the operator's bespoke CLAUDE.md protocols are invisible to.",
  "T2 dossier section A2 [S3] and criterion C3 verdict 'at parity on discipline, behind on interface standards'.",
  [T2], ["agent-interface-standards-gap"])

# ---- persons ----
O("people","graham-harman","Graham Harman",
  "Founder of object-oriented ontology; author of Realist Magic (OHP 2013) and OOO: A New Theory of Everything (2018); formulates the lineage as classical metaphysics mated with actor-network theory; target of the campaign's most sustained internal-camp critique.",
  "T4 dossier sections A1-A2 [S3][S7][S22] and A4 [S16][S28].",
  [T4], ["wolfendale-critiques-harman","blake-charges-harman-with-subjectivism"])
O("people","ian-bogost","Ian Bogost",
  "Author of Alien Phenomenology, or What It's Like to Be a Thing (UMP, ~1,192 citations), the practice-oriented bridge text whose 'ontography' and 'carpentry' vocabulary artists cite; his 'ontography' term competes with a laboratory-studies and media-theory usage of the same word.",
  "T4 dossier sections A2-A3 [S26][S25][S4].",
  [T4], ["ontography-term-is-polysemic","carpentry-bridges-to-practice"])
O("people","timothy-morton","Timothy Morton",
  "Author of Hyperobjects (UMP 2013) — the largest single citation footprint in the OOO corpus (~2,649); the concept anchors Anthropocene and platform critique, and sits under empirical pressure from a WIREs Climate Change (2016) critique of its scientific usefulness.",
  "T4 dossier sections A1-A2, A4 [S23][S24][S5].",
  [T4], ["hyperobjects-under-empirical-pressure"])
O("people","levi-bryant","Levi Bryant",
  "Author of Democracy of Objects (OHP 2011, ~640 citations) and Onto-Cartography: An Ontology of Machines and Media; part of the movement's open-access publishing infrastructure (OHP).",
  "T4 dossier sections A1-A2 [S3][S2].",
  [T4], [])
O("people","zoe-todd","Zoe Todd",
  "Author of the single highest-cited critical intervention captured: 'An Indigenous Feminist's Take On The Ontological Turn: Ontology Is Just Another Word For Colonialism' (J Historical Sociology 2016, ~1,813 cites), arguing ontological turns recolonize Indigenous thought by rebranding it.",
  "T4 dossier section A4 [S18][S27][S13].",
  [T4], ["todd-pressures-the-ontological-turn"])
O("people","peter-wolfendale","Peter Wolfendale",
  "Author of Object-Oriented Philosophy: The Noumenon's New Clothes — the most sustained internal-camp critique of Harman (correlationism charge); the associated blog remains active through 2025, now applying post-Searlean frames to LLMs.",
  "T4 dossier section A4 [S16][S28].",
  [T4], ["wolfendale-pressures-harman"])
O("people","ray-brassier","Ray Brassier",
  "Speculative realism co-founder who publicly dissolved the label in 2011 ('orgy of stupidity'), rejecting the blog-mediated movement culture in which OOO grew; holds that a movement cannot be bound merely to anti-correlationism.",
  "T4 dossier sections A1, A4 [S8][S9][S29].",
  [T4], ["brassier-dissolved-speculative-realism"])
O("people","terence-blake","Terence Blake",
  "Critic whose review-line charges Harman with recurring subjectivism ('Materialism without matter...'); part of the external counter-pressure field the OOO wiki must keep connected to its propositions.",
  "T4 dossier section A4 [S15][S22].",
  [T4], ["blake-charges-harman-with-subjectivism"])
O("people","andy-matuschak","Andy Matuschak",
  "Author of the evergreen-notes method (atomicity, concept-orientation, densely linked, written to evolve) — the methodological core under most modern personal-vault practice.",
  "T2 dossier section A3 [S4].",
  [T2], ["evergreen-notes-underpin-vault-practice"])
O("people","andrej-karpathy","Andrej Karpathy",
  "Author of the LLM-wiki gist that catalyzed the agentic-compilation wave of personal-wiki systems (see the Karpathy LLM-wiki pattern reference).",
  "T2 dossier section A4 [S6].",
  [T2], ["karpathy-catalyzed-agentic-wiki-wave"])
O("people","maria-lahman","Maria Lahman (research poetry lineage)",
  "Author (et al.) of the 2011 Qualitative Inquiry paper that anchors the external sense of 'research poetry': poems composed FROM qualitative data as representation. The decisive external contrast with the operator's own speculative research poetry.",
  "T7 dossier sections A4-A5 [S10][S11].",
  [T7], ["external-research-poetry-is-data-to-poem"])
O("people","jan-baetens","Jan Baetens (candidate referent)",
  "Cultural-studies scholar whose 'Monomedial Hybridization in Contemporary Poetry' (CLCWeb 2013, DOI 10.7771/1481-4374.2389) is the nearest external anchor in the concept space where 'mixt' is suspected to originate — a CANDIDATE REFERENT ONLY, not an identification; the registry sweep found no 'mixt/mixte' as a Baetens term.",
  "T7 dossier section A5 [S14][S15]; attribution must wait for author identification or an intake document.",
  [T7], ["mixt-attribution-blocked"])

# ---- works ----
O("works","frayling-1993","Frayling (1993), 'Research in Art and Design'",
  "The root of the into/through/about triad in research-through-design discourse; grey literature with NO DOI registration, witnessed through DOI-bearing secondary literature (Frankel & Racine, DRS 2008).",
  "T7 dossier section A1 [S01][S12][S13].",
  [T7], ["frayling-lineage-to-rtd"])
O("works","zimmerman-2007","Zimmerman, Forlizzi & Evenson (2007), CHI",
  "The formalization of research through design for HCI: designers produce artifacts that 'transform the world from its current state to a preferred state', contributions evaluated through four lenses, addressing under-constrained problems. DOI 10.1145/1240624.1240704, ~2,275 citations — the highest-velocity anchor in the whole terminology family.",
  "T7 dossier section A1 [S02].",
  [T7], ["frayling-lineage-to-rtd"])
O("works","candy-edmonds-2017","Candy & Edmonds (2017), Practice-Based Research (Leonardo)",
  "The practice-based research tradition: creative practice as a method of inquiry whose outcomes are new knowledge communicable in rich, scrutinizable forms. DOI 10.1162/leon_a_01471, ~313 cites.",
  "T7 dossier section A2 [S03].",
  [T7], [])
O("works","smith-dean-2009","Smith & Dean (2009), Practice-led Research, Research-led Practice",
  "The sharpest external gloss on 'research through practice': practice-led research generates insights through practice; research-led practice feeds research back into practice; the relation is 'iterative and web-like'. DOI 10.1515/9780748636303, ~553 cites.",
  "T7 dossier section A2 [S04].",
  [T7], [])
O("works","borgdorff-2012","Borgdorff (2012), The Conflict of the Faculties",
  "The institutional-epistemological program of artistic research: 'artistic research is an endeavour in which the artistic and the academic are connected... artistic practices contribute as research to what we know and understand.' Open access (Leiden UP), DOI 10.26530/oapen_595042, ~370 cites.",
  "T7 dossier section A3 [S06]; exposition culture cross-ref T6.",
  [T7], ["borgdorff-grounds-artistic-research"])
O("works","prendergast-2009","Prendergast, Leggo & Sameshima (2009), Poetic Inquiry handbook",
  "The handbook establishing poetic inquiry: poetry as qualitative-research methodology. DOI 10.1163/9789087909512, ~296 cites.",
  "T7 dossier section A4 [S09].",
  [T7], ["external-research-poetry-is-data-to-poem"])
O("works","baetens-2013-monomedial-hybridization","Baetens (2013), 'Monomedial Hybridization in Contemporary Poetry'",
  "CLCWeb article (DOI 10.7771/1481-4374.2389) — the nearest external anchor in the concept space where 'mixt' is suspected to originate; a candidate referent only, NOT an identification of the adopted concept's source.",
  "T7 dossier section A5 [S15]; registry sweep found no 'mixt' as a Baetens term [S14].",
  [T7], ["mixt-attribution-blocked"])
O("works","bryant-democracy-of-objects","Bryant (2011), Democracy of Objects",
  "Open Humanities Press founding text of OOO (~640 citations); part of the movement's open-access infrastructure.",
  "T4 dossier section A1 [S3].",
  [T4], [])
O("works","harman-realist-magic","Harman (2013), Realist Magic",
  "Harman's OOO aesthetics/ontology text (OHP, ~243 citations) on the movement's open-access infrastructure.",
  "T4 dossier section A1 [S3].",
  [T4], [])
O("works","morton-hyperobjects","Morton (2013), Hyperobjects",
  "The largest single citation footprint in the OOO corpus (~2,649); hyperobjects as infrastructure for Anthropocene and platform critique, under empirical pressure from WIREs Climate Change (2016).",
  "T4 dossier sections A1-A2 [S23][S24].",
  [T4], ["hyperobjects-under-empirical-pressure"])
O("works","bogost-alien-phenomenology","Bogost (2012), Alien Phenomenology",
  "The practice-oriented bridge text of OOO (~1,192 citations) whose 'ontography'/'carpentry' vocabulary artists cite.",
  "T4 dossier sections A2-A3 [S26].",
  [T4], ["carpentry-bridges-to-practice"])
O("works","todd-2016-ontology-colonialism","Todd (2016), 'Ontology Is Just Another Word For Colonialism'",
  "The single highest-cited critical intervention captured in the OOO field (~1,813 cites; count qualified by author-disambiguation noise): Indigenous feminist critique of the ontological turn.",
  "T4 dossier section A4 [S18][S27][S13].",
  [T4], ["todd-pressures-the-ontological-turn"])
O("works","wolfendale-noumenons-new-clothes","Wolfendale, Object-Oriented Philosophy: The Noumenon's New Clothes",
  "The most sustained internal-camp critique of Harman's OOO (the correlationism charge).",
  "T4 dossier section A4 [S16][S28].",
  [T4], ["wolfendale-pressures-harman"])
O("works","lahman-2011-research-poetry","Lahman et al. (2011), research poetry (Qualitative Inquiry)",
  "The canonical external 'research poetry' anchor (DOI 10.1177/1077800411423219): poem as representation of qualitative data (data-to-poem). Davis (2019) 'critical poetic inquiry' extends the line.",
  "T7 dossier sections A4-A5 [S10][S11].",
  [T7], ["external-research-poetry-is-data-to-poem"])

# ---- concepts ----
O("concepts","speculative-realism","Speculative realism",
  "Movement named at the Goldsmiths College workshop, April 2007 (Brassier, Grant, Harman, Meillassoux; Toscano moderating), with post-Kantian 'correlationism' as the shared target; Brassier publicly dissolved the label in 2011. Harman's lineage formula: classical metaphysics mated with actor-network theory.",
  "T4 dossier section A1 [S7][S8][S9][S10]; the Wikipedia article carries an original-research banner (May 2025).",
  [T4], ["brassier-dissolved-speculative-realism","todd-pressures-the-ontological-turn"])
O("concepts","object-oriented-ontology","Object-oriented ontology (OOO)",
  "The philosophical program within/adjacent to speculative realism whose uptake 2010-2026 is design- and architecture-led (OpenAlex: 3,936 works, rising monotonically to ~443/yr), with no serious computational implementation found (6 toy repos, zero arXiv entries) and term-collision pressure from object-oriented programming.",
  "T4 dossier sections A2-A4 [S1][S19][S20][S21].",
  [T4], ["ontography-term-polysemy","no-computational-ooo-implementation"])
O("concepts","hyperobjects","Hyperobjects",
  "Morton's concept for entities massively distributed in time and space relative to humans; the OOO term with the largest external uptake (climate communication, education, archaeology, platform studies) and a dedicated peer-reviewed critique of its scientific usefulness (WIREs 2016).",
  "T4 dossier sections A2, A4 [S23][S24][S5].",
  [T4], ["hyperobjects-under-empirical-pressure"])
O("concepts","ontography","Ontography (Bogost) — polysemy pressure",
  "Bogost's term for an inventory-based ontographic method in Alien Phenomenology; the word competes with a laboratory-studies 'ontography' (Social Studies of Science 2013, ~197 cites) and media-theory uses (ZfMK 2019) — a live term-divergence risk the operator's own 'ontograph' project must track.",
  "T4 dossier section A2 [S25][S4].",
  [T4], ["ontography-term-polysemy"])
O("concepts","carpentry","Carpentry (Bogost)",
  "Bogost's term for making things that do philosophical work (how objects make one another, in ALIEN PHENOMENOLOGY's practice-oriented vocabulary); the practice bridge artists cite, and the term the operator's 'carpentry' concept page relates to.",
  "T4 dossier sections A2-A3 [S26][S21] ('Turning Philosophy with a Speculative Lathe' DRS 2018).",
  [T4], ["carpentry-bridges-to-practice"])
O("concepts","evergreen-notes","Evergreen notes",
  "Matuschak's methodological core for modern vaults: atomicity, concept-orientation, densely linked notes written to evolve; practice culture specifying note behavior, not evidence.",
  "T2 dossier sections A3, A5 [S4].",
  [T2], ["evergreen-notes-underpin-vault-practice"])
O("concepts","zettelkasten","Zettelkasten",
  "The Ahrens/Luhmann-lineage folk method (atomic notes, unique IDs, linking as thinking) under most modern PKM clusters; OpenAlex shows modest scholarly trickle, not a research field.",
  "T2 dossier section A5 [S17][S18].",
  [T2], [])
O("concepts","agentic-compilation","Agentic compilation (LLM-wiki pattern)",
  "Karpathy's pattern: an agent incrementally builds and maintains a persistent wiki compiled once and kept current, against RAG's rediscover-on-every-question failure mode. The 2024-2026 wave-2 tools (llm-wiki-agent, swarmvault, obsidian-wiki, claude-obsidian, obsidian-second-brain, obsidian-mind) implement variants with thin provenance.",
  "T2 dossier section A4 [S6][S7][S11][S12][S13][S14][S15].",
  [T2], ["karpathy-catalyzed-agentic-wiki-wave","claude-obsidian-closest-cousin-still-behind"])
O("concepts","research-through-design","Research through design",
  "Design-research axis from Frayling (1993) to Zimmerman et al. (2007): research conducted THROUGH the making of artifacts, formalized for HCI with four evaluation lenses and under-constrained problems.",
  "T7 dossier sections A1 [S01][S02][S13].",
  [T7], ["frayling-lineage-to-rtd"])
O("concepts","practice-led-research-bidirectionality","Practice-led / research-led practice",
  "Smith & Dean's bidirectional model: practice-led research generates insights through practice; research-led practice feeds research back into practice; the relation is 'iterative and web-like' — the sharpest external gloss on 'research through practice'.",
  "T7 dossier section A2 [S04].",
  [T7], [])
O("concepts","artistic-research","Artistic research (Borgdorff)",
  "The institutional-epistemological program in which artistic practices contribute as research to knowledge, inside academia, with its own exposition culture (Research Catalogue, JAR, Ruukku — cf. the T6 track).",
  "T7 dossier section A3 [S06]; T6 sections A1 and (b).",
  [T7,T6], ["borgdorff-grounds-artistic-research","publication-gap-against-research-catalogue"])
O("concepts","speculative-research-poetry","Speculative research poetry (شعر پژوهشی گمانه‌زن)",
  "The author's OWN term (author confirmation, 2026-09-06) for the specific expressions of his methodology: source-field to poem where the poem is itself an instrument of inquiry, staging uncertain relations while their status stays available — formally distinct from the external representational sense (Lahman) and from practice-based/artistic-research families.",
  "T7 dossier sections A4-A5; decisive contrast recorded against Lahman's data-to-poem sense [S10][S11].",
  [T7], ["external-research-poetry-is-data-to-poem"])
O("concepts","mixt","mixt (adopted concept, external origin UNVERIFIED)",
  "An adopted concept of external origin per author confirmation (2026-09-06): the concept is someone else's; the suspected home is the Baetens-facing corpus route, but the registry sweep found NO 'mixt/mixte' as a Baetens term. The exact external source must be author-identified or intakeed before canonical attribution names anyone. The compound 'mixt research poetry' is RETRACTED (mis-segmentation of two separate terms).",
  "T7 dossier section A5 [S14][S15]; matches the standing attribution-guard item (prop-20260906-154145-567 lineage).",
  [T7], ["mixt-attribution-blocked"])
O("concepts","typed-version-relations","Typed version relations (supersedes / is-version-of / derived-from / translates / adapts / summarizes / embedded-in / duplicates-text-of)",
  "The operator's additive-only typed relations preserving intellectual genesis as first-class content — 'alone' in the surveyed landscape (no PKM or flagship genetic platform models genesis this way), and partially mappable onto PROV-O/LRM predicates (see the mapping relations).",
  "T2 criterion C2 verdict 'alone' [S20]; T3 convergence table [S04][LRM01][DC01][S03].",
  [T2,T3], ["derived-from-maps-to-prov-wasderivedfrom","supersedes-maps-partially-to-prov","is-version-of-maps-partially-to-lrm","summarizes-and-adapts-are-reinvented"])
O("concepts","authority-hierarchy","8-level authority hierarchy over assertions",
  "The operator's ladder grading assertions from original through verified external primary, author confirmation, canonical record, derivative witness, interpretive synthesis, candidate/AI-generated, to generated views. No surveyed standard or system grades assertions by authority tier — 'divergent-by-design', a genuine contribution; the 2025-26 RAG frontier (EvoTrustRAG, LayerRAG-Bench) is only beginning to treat conflict/authority as first-class.",
  "T3 convergence table [S01][S04][WB01][SKOS01]; T5 criteria 2 and B.2 [S19][S20][S37].",
  [T3,T5], ["authority-hierarchy-has-no-standard-equivalent","claude-obsidian-closest-cousin-still-behind"])
O("concepts","checksummed-immutable-originals","Checksummed immutable originals",
  "SHA-256-fixity originals that are never edited, with derivatives always secondary — the strongest surveyed provenance contract ('STRONGEST SURVEYED', T5 criterion 3); concept-aligned with PREMIS fixity and cryptographically bound C2PA (different scope), with no cryptographic fixity at any flagship genetic project.",
  "T5 criterion 3 [S37][S28][S31]; T1 negative finding 3 [cand-no-checksums]; T3 [PREMIS01].",
  [T5,T1,T3], ["checksum-fixity-concept-aligned-with-premis","open-webui-sync-is-not-immutability","no-cryptographic-fixity-in-flagships"])
O("concepts","claim-records-evidence-qualified","Claim records with evidence qualification",
  "Claims as records carrying evidence state, permission-to-argue (may-note/may-argue), counter-evidence, and supporting-source lists — independent convergence with Wikibase's Statement+ReferenceRecord+Rank design, but stricter: unevidenced consequential claims are forbidden, whereas Wikibase allows empty references.",
  "T3 dossier convergence table [WB01]; T2 criterion C1 [S21][S22].",
  [T3,T2], ["claim-records-vs-wikibase-statements"])

# ---- methods (improvement backlog, adopt/adapt items only) ----
O("methods","tei-p5-export-path","TEI P5 export path [ADOPT]",
  "Map each source record to teiHeader+msDesc (physDesc/history/provenance), derivatives/objects to text or sourceDoc/surface/zone, staged interpretations to creation/listChange/change[@ordered], relations to @copyOf/@sameAs/@prev/rel. Serves interchange; makes the archive legible to BDMP/TextGrid-class consumers.",
  "T1 dossier backlog item 1, grounded in captured TEI ch. 11-12 [tei-msdesc][tei-transcription].",
  [T1], ["tei-underpins-genetic-editions"])
O("methods","witness-sentence-alignment","Witness-level sentence alignment view [ADOPT]",
  "Port BDMP's numbered-sentence vertical-juxtaposition pattern (optionally delegating diffing to CollateX or a pure-Python equivalent) over extracted derivatives; serves comparison without image servers.",
  "T1 dossier backlog item 2 [bdmp-manual][collatex-ref].",
  [T1], ["bdmp-delegates-collation-to-collatex"])
O("methods","static-publication-layer","Static public publication layer [ADOPT]",
  "Generate a read-only static site (Hugo — TextGrid's own choice) from canonical objects, excluding _originals where rights demand; stable IDs + content-hash addresses à la TEI Vault/Zenodo DOIs. Converts 'private' into 'publishable at will'.",
  "T1 dossier backlog item 3 [textgrid-home][tei-p5].",
  [T1], ["publication-gap-against-research-catalogue"])
O("methods","editorial-charter-versioning","Editorial-charter versioning [ADOPT]",
  "Preserve dated immutable states of the operator's own editorial/governance docs, as BDMP keeps its manual's 2011/2013/2015/2021 states addressable; applies criterion 3 to policy, not just artifacts.",
  "T1 dossier backlog item 4 [bdmp-manual].",
  [T1], [])
O("methods","transcription-revision-ledger","Transcription-revision ledger [ADAPT]",
  "Generalize BDMP's who-revised-what-and-when transcription metadata into Git history plus a first-class derivative-revision relation feeding the derivative-witness authority tier.",
  "T1 dossier backlog item 5 [bdmp-manual].",
  [T1], [])
O("methods","htr-ocr-confidence-tiering","HTR/OCR-assisted intake with confidence tiering [ADAPT]",
  "Route machine-extracted text into the wiki as candidate-tier derivatives with per-field confidence, never auto-promoted — formalizes AI-mediated philology inside the existing authority hierarchy (DHQ 13.1 shows neural OCR at 90-97% on difficult hands).",
  "T1 dossier backlog item 6 [dhq-mislabeled].",
  [T1], [])
O("methods","prov-o-export-profile","PROV-O export profile for the typed relations [ADOPT]",
  "Map derived-from→prov:wasDerivedFrom, supersedes→prov:wasRevisionOf, is-version-of→prov:specializationOf (pairwise), translates/adapts/summarizes→prov:wasDerivedFrom + dcterms:type qualifier, embedded-in→dcterms:isPartOf; deliverable one exports/prov-mapping.jsonld + validator check.",
  "T3 dossier backlog item 1 [S04].",
  [T3], ["derived-from-maps-to-prov-wasderivedfrom","supersedes-maps-partially-to-prov","embedded-in-maps-to-dcterms-ispartof","summarizes-and-adapts-are-reinvented"])
O("methods","wikibase-rank-field","Wikibase-style rank field on claim records [ADOPT]",
  "Add preferred/normal/deprecated rank values to claim records so competing canonical accounts coexist while queries select the preferred — the operator's 'later formulation does not erase the earlier' rule made queryable.",
  "T3 dossier backlog item 2 [WB01].",
  [T3], ["claim-records-vs-wikibase-statements"])
O("methods","faithfulness-regression-harness","Faithfulness regression harness over QMD answers [ADOPT]",
  "Extend the existing retrieval benchmark with a second stage: generate answers via the normal QMD flow, then score answer-groundedness (claim-to-source entailment, RAGAS-faithfulness style) against cited canonical pages, with a house-style threshold. The honest gap: current evaluation measures retrieval regression, not faithfulness of generated answers.",
  "T5 dossier backlog item 1 and criterion 6 [S34][S37].",
  [T5], ["evaluation-gap-is-faithfulness-not-retrieval"])
O("methods","claim-attribution-spot-audit","Claim-attribution spot audit (FActScore lineage) [ADOPT]",
  "Decompose a sample of canonical claim records into atomic claims and verify each traces to an original or verified primary source; converts 'source record proves presence, not internal assertions' from caveat into tested property.",
  "T5 dossier backlog item 2 [S14].",
  [T5], [])
O("methods","verbatim-span-completion-rule","Verbatim-span completion rule (LineageRAG-style) [ADAPT]",
  "For interpretive answers, require each cited derivative to resolve to a quoted span in the checksummed original before the answer ships; implementable inside validate_repo.py.",
  "T5 dossier backlog item 3 [S18].",
  [T5], [])
O("methods","conflict-evolution-tagging","Conflict-evolution tagging (EvoTrustRAG-style) [ADAPT]",
  "When two records at the same authority level disagree, require the intake patch to classify: legitimate supersession vs unresolved contradiction vs candidate error; maps onto later-round-supersedes discipline.",
  "T5 dossier backlog item 4 [S19].",
  [T5], [])
O("methods","succession-record-vmq","VMQ-style succession record per wiki [ADOPT]",
  "A short questionnaire-derived record per major object family: behaviors to preserve if software/steward changes (inspired by the Variable Media Questionnaire); cheap, serves the longevity criterion the archive currently lacks institutionally.",
  "T6 dossier backlog item 1 [S07].",
  [T6], ["vmq-informs-succession-records"])
O("methods","exposition-format-export","Exposition-format export path [ADAPT]",
  "One-way export from canonical objects into an RC/JAR-compatible media-rich exposition draft for future submission — never the system of record; serves the publication gap while keeping governance private-first.",
  "T6 dossier backlog item 2 [S01][S02].",
  [T6], ["publication-gap-against-research-catalogue"])
O("methods","webrecorder-capture-pipeline","Webrecorder capture pipeline for cited web sources [ADOPT]",
  "Browsertrix/archive-webpage captures stored as checksummed derivatives with source-record entries — upgrades 'verified external primary' claims against link rot, using the stack the media-art world trusts.",
  "T6 dossier backlog item 3 [S08].",
  [T6], ["webrecorder-informs-capture-pipeline"])

print(f"objects prepared: {len(OBJECTS)}")
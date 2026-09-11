# T3 Dossier — Ontology & Provenance Standards vs. Mozare Grammar

Track: T3-ontology-provenance-standards
Date: 2026-08-25
Method: normative specifications fetched to `raw/` and read directly; subject grammar read from
`mozare-wiki/SYSTEM_DESIGN.md` §3–§5.6, `CONTROLLED_VOCABULARY.md`, `relation-object.schema.json`,
OOO `SCHEMA.md`, shipped `ro-crate-metadata.json`. All dossier claims are interpretive synthesis
(authority level 6); every load-bearing fact carries its `[S#]` SOURCES.json marker inline.
*Provenance-repair pass 2026-08-25: SOURCES.json normalized to array form; missing TEI captures
executed and marked; PREMIS fallback ladder completed (archive.org interstitial — negative stands).*

---

## (a) LANDSCAPE MAP

| Standard | Body | Core model | Relevance to Mozare grammar |
|---|---|---|---|
| **CIDOC-CRM v7.3.2** (ISO 21127) | ICOM CIDOC | Event-centric classes/properties for cultural heritage. Key: **E13 Attribute Assignment** = "actions of making assertions about one property of an object or any single relation between two items" (p70 of PDF) [S01] — the formal class for *claims about relations*. E81 Transformation = simultaneous destruction/production (state change); E78 Curated Holding = collections; P70 documents. **No first-class "is-version-of" property exists** [S02] — versioning is expressed through activities (E65 Creation, E81 Transformation), not object-to-object version edges. | The scholarly-museum heavyweight. His claim records ≈ E13 instances; his relation objects ≈ typed E13 assertions. |
| **IFLA LRM-ER** | IFLA | Consolidation of FRBR/FRAD/FRSAAD into one entity-relationship model; 117 elements; built "to be used in linked data environments" [LRM01]. WEMI layering (Work→Expression→Manifestation→Item) is the library world's model of *textual genesis across versions/carriers*. | Maps onto his drafts/witnesses/version-families. Machine-readable distributions were unreachable this session [LRM02] (see negative findings). |
| **PROV-O** | W3C Rec. 2013 | Entity/Activity/Agent; predicates verified present in fetched spec: `wasDerivedFrom`(46×), `wasAttributedTo`(51×), `hadPrimarySource`(23×), `wasRevisionOf`(22×), `specializationOf`, `alternateOf`, `hadMember` [S04]. | Direct standard counterpart of his derivation-family relations and attribution logic. |
| **Dublin Core / DCMI Terms** | DCMI | Cross-domain descriptive terms incl. `dcterms:isPartOf`, `references`, provenance-side free-text `dcterms:provenance` [DC01]. | Lightweight baseline vocabulary; weakest of the set for genesis. |
| **SKOS** | W3C Rec. | ConceptScheme/Concept; `prefLabel`(65×), `broader/narrower`(110/67×), `exactMatch`(43×), `closeMatch`(32×) [SKOS01]. | The standard shape for his controlled vocabularies (relation types, statuses) as machine-readable exports. |
| **TEI P5** | TEI Consortium | Chapters on manuscript description & transcription (captured: Ch. 11 msDesc structure, physDesc, history, att.witnessed [TEI01]; Ch. 12 transcription of primary sources, genetic apparatus, facsimile/sourceDoc [TEI02]): witness-level encoding, apparatus, genetic modules. | The textual-scholarship encoding standard every digital genetic edition uses; his Markdown grammar is an alternative, lighter representation of the same problem space. |
| **IIIF Presentation 3.0** | IIIF | Manifest/canvas/range model for presenting page images with metadata [IIIF01]. | Only relevant if/when manuscript *images* enter the corpus. |
| **W3C Web Annotation** | W3C Rec. 2017 | Annotation = Body + Target (+ SpecificResource/Selector); Motivation vocabulary; provenance-carrying annotation graphs (Annotation 326×, Selector 206× in fetched spec) [WA01]. | Standard home for critical-pressure notes attached to propositions without mutating them — exactly his OOO "critique connected to propositions" invariant. |
| **RO-Crate 1.1 (now 1.3)** | Research Object community | JSON-LD research-object packaging over schema.org context; root Dataset, `conformsTo`, `hasPart`, CreateAction provenance; Profiles mechanism. Fetched page confirms section structure & version lineage; local copy is navigation shell (full class text not captured — see negatives) [ROC01][ROC02]. | He already ships `ro-crate-metadata.json`; question is whether his usage aligns. |
| **Wikibase DataModel** | Wikimedia | Verified from fetched spec: **Statement = Claim(snak) + qualifiers + ReferenceRecords + Rank**; "The reference is given by a ReferenceRecord, and the list of references is allowed to be empty"; rank "used for simplifying the selection of Statements" [WB01]. | Closest large-system analogue to his claim/evidence/permission design — but with ranks, not an 8-level authority ladder. |

---

## (b) CONVERGENCE / DIVERGENCE TABLE

Verdict scale: **aligned** · **partially-aligned** · **divergent-by-design** · **reinvented**

| Mozare construct | Nearest standard construct | Verdict | Justification (one line) |
|---|---|---|---|
| relation `supersedes` | `prov:wasRevisionOf` [S04] + Wikibase deprecated-rank [WB01] | partially-aligned | Same intent (succession without deletion); PROV ties revisions via Entities, his edge is a direct object-to-object assertion. |
| relation `is-version-of` | LRM-ER Work/Expression layering [LRM01]; `prov:specializationOf` [S04] | partially-aligned | Both express version families; LRM does it via class layering rather than an explicit pairwise edge. |
| relation `derived-from` | `prov:wasDerivedFrom` [S04] | **aligned** | Nearly one-to-one semantic match. |
| relation `duplicates-text-of` | CIDOC-CRM E33 linguistic-object identity ("the identity of a (version of a) text … is given by the exact arrangement of its relevant symbols", CRM v7.3.2 p103) [S03] | partially-aligned | CRM states the identity criterion in prose but ships no dedicated duplicate predicate; his edge is operationally clearer. |
| relation `embedded-in` | `dcterms:isPartOf` [DC01]; CRM P46 is composed of [S01] | **aligned** | Standard part-whole, trivially mappable. |
| relation `translates` | LRM-ER: translation = new Expression of same Work [LRM01]; schema:workTranslation exists in schema.org | partially-aligned | Library modelling handles it structurally; no lightweight universal pairwise predicate in PROV/DCT [S04][DC01]. |
| relation `summarizes` | none clean (nearest: `dcterms:` has no summarize; schema:abstract is a property not a relation) [DC01] | **reinvented** | No mainstream predicate exists [S04][DC01]; keeping the custom edge is correct. |
| relation `adapts` | none direct (practice: `prov:wasDerivedFrom` + type qualifier) [S04] | **reinvented** | Same conclusion as summarizes — custom edge justified. |
| Claim records with evidence qualification | Wikibase Statement + ReferenceRecord + Rank [WB01] | **aligned (design)** | Independent convergence on statement-level sourcing; Wikibase allows empty references, his system forbids unevidenced consequential claims — his is stricter. |
| 8-level authority hierarchy | nothing equivalent; nearest partials: PROV attribution chains [S04], PREMIS aggregation (blocked capture [PREMIS01]) | **divergent-by-design** | No surveyed standard grades *assertions* by authority tier [S01][S04][WB01][SKOS01]; his own ladder is defined in SYSTEM_DESIGN §3 with eight typed levels [SUBJ01] — a genuine contribution. |
| Navigation links ≠ governed edges | nothing equivalent | **divergent-by-design** | SKOS mapping relations are closest in spirit [SKOS01]; the two-graph discipline (273 governed / 759 associative in OOO wiki) is his own [SUBJ02]. |
| Checksummed immutable originals | PREMIS fixity (official docs blocked to automated fetch this session — 403, archive fallback empty [PREMIS01]) | **aligned (concept)** | Fixity-by-checksum is precisely PREMIS's preservation core; his implementation predates any need for PREMIS XML. Concept-level comparison, candidate-tier backing. |
| Shipped `ro-crate-metadata.json` | RO-Crate 1.1 spec (JSON-LD, Dataset root, conformsTo) [ROC01] | partially-aligned | Structure follows the crate pattern; alignment against the 1.3 Profiles machinery unverified (spec body not fully captured locally) [ROC02]. |

---

## (c) IMPROVEMENT BACKLOG

1. **ADOPT — PROV-O export profile for the eight relations.** [S04]
   Map: `derived-from→prov:wasDerivedFrom`, `supersedes→prov:wasRevisionOf`, `is-version-of→prov:specializationOf` (pairwise), `translates/adapts/summarizes→prov:wasDerivedFrom` + `dcterms:type` qualifier, `embedded-in→dcterms:isPartOf`. Deliverable: one `exports/prov-mapping.jsonld` + validator check. Serves all three wikis; cost ≈ days; makes the vaults legible to every DH/provenance tool without changing the Markdown-first authority model.
2. **ADOPT — Wikibase-style `rank` field on claim records.** [WB01]
   Values preferred/normal/deprecated let competing canonical accounts coexist while queries select the preferred — exactly his "later formulation does not erase the earlier" rule, made queryable. Cost: schema field + validation enum.
3. **ADAPT — E13 pattern naming inside claim frontmatter.** [S01]
   Claims already behave like Attribute Assignments; adding explicit `asserted_property`, `assignment_time`, `assigning_agent` fields aligns record semantics with CRM vocabulary at zero infrastructure cost. Serves casebook-wiki evidence grammar most.
4. **ADAPT — PREMIS-shaped fixity block in source records.** [PREMIS01]
   He has SHA-256 already; add `fixity: {algorithm, value, checked_at, checked_by}` structure so preservation audits become mechanical. Serves mozare-wiki source-record schema. (Shape borrowed concept-level: primary docs uncapturable this session.)
5. **ADAPT — SKOS export of controlled vocabularies.** [SKOS01]
   `CONTROLLED_VOCABULARY.md` → `skos:ConceptScheme` JSON-LD with `skos:exactMatch` to PROV-O predicates where the mapping above applies. Cheap interoperability for agents.
6. **REJECT — full CIDOC-CRM/RDF adoption as primary store.** [S01][S02]
   Event-centric modelling would force every relation through activity reification — enormous overhead against his Markdown-as-authority design; the E13 pattern (idea 3) captures the benefit.
7. **REJECT — JSON-LD/graph-DB as system of record.**
   Exports yes; store no. Git-diffable Markdown is load-bearing for multi-agent governance and human audit. (Own inference, candidate-tier.)
8. **DEFER — IIIF.** No image-heavy corpus yet [IIIF01]; revisit when scans/manuscript photos enter intake.
9. **CANDIDATE — Web Annotation for OOO critical pressure.** [WA01]
   Critique notes as side-file annotations targeting proposition IDs would implement the "critique connected to propositions, not parked outside the graph" invariant with a standard serialisation. Needs design pass before adopting.

---

## (d) NEGATIVE FINDINGS

- **CIDOC-CRM v7.3.2 contains no first-class version-of property** (full-text search of the 243-page PDF: two incidental occurrences of "version of", neither a defined property) [S02]. Versioning must be activity-modelled; his pairwise edges have no CRM equivalent to map onto.
- **LRM-ER machine-readable distributions unreachable:** `iflastandards.info/ns/lrm/lrmer.{jsonld,nt}` returned HTML error pages this session; only the landing page (117 elements count, linked-data mandate) was captured [LRM02].
- **PREMIS documentation blocked to automated access:** loc.gov returned HTTP 403 twice (`id.loc.gov/vocabulary/preservation`, premis recommended-documentation URL); web.archive.org fallback yielded only a Wayback interstitial with no document body [PREMIS01]. Concept-level comparison rests on secondary knowledge, marked accordingly in SOURCES.json.
- **`w3id.org/ro/crate/1.1` resolved 404 via curl**, and the fetched `ro-crate-11.html` mirror is a navigation shell without class definitions — full RO-Crate conformance verification remains open [ROC02].
- **meta.wikimedia.org `Wikibase/DataModel` 404'd**; recovered from mediawiki.org (200) [WB02].
- **No surveyed standard combines fixity + assertion-authority-grading + permission-qualified claims.** Wikibase stops at references+ranks [WB01]; PREMIS stops at fixity [PREMIS01]; CRM stops at event semantics [S01]. The *combination* in Mozare's grammar appears original across everything examined this track.
- No standard defines a Markdown-native typed-edge convention (`relations: [{target,type}]` frontmatter) across the captured spec set [S01][S04][WB01][SKOS01][DC01] — confirming the T2 finding that no cross-tool typed-edge Markdown standard exists.

---

*Prepared under the evidence-governed research protocol (others/research/README.md). This file is interpretive synthesis (level 6); underlying captures live in `raw/`, provenance in `SOURCES.json`.*

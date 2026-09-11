---
{
  "id": "ref-obj-prov-o-export-profile",
  "type": "object",
  "title": "PROV-O export profile for the typed relations [ADOPT]",
  "kind": "method",
  "aliases": [],
  "candidate_tier": true,
  "authority_note": "candidate (level 7); mined from registered dossier sources; never asserted as verified beyond the dossier text",
  "status": "active-record",
  "visibility": "private",
  "created": "2026-09-11",
  "updated": "2026-09-11",
  "schema_version": "1.0.0"
}
---


# PROV-O export profile for the typed relations [ADOPT]

## Characterization

Map derived-from→prov:wasDerivedFrom, supersedes→prov:wasRevisionOf, is-version-of→prov:specializationOf (pairwise), translates/adapts/summarizes→prov:wasDerivedFrom + dcterms:type qualifier, embedded-in→dcterms:isPartOf; deliverable one exports/prov-mapping.jsonld + validator check.

## Source grounding

T3 dossier backlog item 1 [S04].

Supporting sources (registered in this wiki):

- [[ref-src-aea0e94fe5c9]]

## Relations

- [[derived-from-maps-to-prov-wasderivedfrom]]
- [[supersedes-maps-partially-to-prov]]
- [[embedded-in-maps-to-dcterms-ispartof]]
- [[summarizes-and-adapts-are-reinvented]]

## Open work

- Adjudication: candidate-tier until human review upgrades or corrects it.

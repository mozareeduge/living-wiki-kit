---
{
  "id": "ref-obj-faithfulness-regression-harness",
  "type": "object",
  "title": "Faithfulness regression harness over QMD answers [ADOPT]",
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


# Faithfulness regression harness over QMD answers [ADOPT]

## Characterization

Extend the existing retrieval benchmark with a second stage: generate answers via the normal QMD flow, then score answer-groundedness (claim-to-source entailment, RAGAS-faithfulness style) against cited canonical pages, with a house-style threshold. The honest gap: current evaluation measures retrieval regression, not faithfulness of generated answers.

## Source grounding

T5 dossier backlog item 1 and criterion 6 [S34][S37].

Supporting sources (registered in this wiki):

- [[ref-src-02e16ccb7ee5]]

## Relations

- [[evaluation-gap-is-faithfulness-not-retrieval]]

## Open work

- Adjudication: candidate-tier until human review upgrades or corrects it.

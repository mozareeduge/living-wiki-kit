---
id: kit-controlled-vocabulary
type: system-document
title: Controlled Vocabulary
status: active
created: 2026-09-10
updated: 2026-09-10
schema_version: 1.0.0
---

# Controlled Vocabulary

Values whose meaning must remain stable across records. Add a value only
when an existing value cannot describe a recurring real condition.

## Workflow status

| Value | Meaning |
|---|---|
| inbox | Received but not registered |
| registered | Preserved, identified, and indexed |
| processing | Under active extraction or analysis |
| active | Currently used for its stated function |
| accepted | Reviewed and approved for its stated function |
| published | Released publicly |
| superseded | No longer current for the same function |
| disputed | Actively challenged |
| rejected | Not accepted for the proposed use |
| archived | Preserved outside the active route |

## Validation status

| Value | Meaning |
|---|---|
| unreviewed | No validation pass recorded |
| registered-not-fully-claim-validated | Preserved and described; internal claims not all verified |
| source-checked | Compared with the named source |
| author-confirmed | Confirmed by the author for matters under their authority |
| externally-verified | Checked against an independent authoritative source |
| partially-verified | Some but not all consequential claims checked |
| disputed | Strong conflict remains |
| not-verifiable | Available conditions do not permit verification |

## Claim permission

| Value | Meaning |
|---|---|
| may-note | Record as a possible trace or relation |
| may-describe | Make a bounded descriptive statement |
| may-argue-cautiously | Advance an interpretation while stating limits |
| may-argue | Support a sustained claim |
| blocked | Do not use for public or scholarly assertion |

## Extraction quality

| Value | Meaning |
|---|---|
| good | Suitable for search; original still authoritative |
| partial | Important content, tables, or formatting may be missing |
| poor | Would materially misrepresent the artifact; excluded from semantic indexing |
| not-applicable | No responsible text extraction in this release |

## Delivery status

| Value | Meaning |
|---|---|
| not-applicable | Delivery is not part of the artifact's function |
| prepared | Prepared for possible delivery |
| sent | Author confirms it was sent |
| submitted | Author confirms formal submission |
| received | Recipient receipt confirmed |
| responded | A response exists |
| accepted / rejected | Receiving body's decision |
| unknown | Current evidence does not establish delivery |

## Use-status

| Value | Meaning |
|---|---|
| poetic | May function in poetic composition |
| documentary | May function as a document or documented juxtaposition |
| technical | May guide implementation |
| strategic | May guide routing or outreach |
| scholarly | May support scholarly formulation at its claim permission |
| design-testing | May function in prototype or evaluation |
| internal-routing | May guide internal selection |
| residual | Preserved outside the active route |
| quarantined | Kept separate pending validation |
| blocked-from-export | Must not enter external output |

## Change operations

| Value | Meaning |
|---|---|
| create | Add a new record |
| update | Revise an existing record without changing its identity |
| append | Add a dated layer |
| link | Add an explicit relation |
| split | Separate one record into several identities |
| merge | Combine records while preserving predecessor identities |
| supersede | Assign the current function to a later record |
| dispute | Mark a claim or relation as challenged |
| archive | Move outside the active route without deletion |
| no-change | Record that comparison produced no justified change |

## Holdings tier

| Value | Meaning |
|---|---|
| registered | Adjudicated, provenance-complete, part of the corpus of record |
| pending-registration | Held, intended for registration, not yet adjudicated |
| reference-shelf | Held deliberately as background; never intended for the corpus of record |

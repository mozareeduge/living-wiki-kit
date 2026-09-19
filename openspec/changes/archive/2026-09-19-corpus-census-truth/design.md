# Design: corpus-census-truth

## 1. Horizon

The state this ladder ends at, stated so that any agent can test whether it
has been reached:

> **No unchecked number, no undeclared document, no stale register presented
> as current.**

Concretely, at the horizon:

- every file in `_originals/` carries exactly one declared holdings tier;
- `status: registered` on a source record is true exactly when the manifest
  contains it, and a deterministic check proves it;
- every number restated on a human-facing page is machine-compared against the
  register that owns it;
- every `.md` register declares how often it must be refreshed, and the
  validator fails a `per-intake` register that lags the corpus;
- `SYSTEM_DESIGN.md` section 6 distinguishes operational scripts from
  available-but-unexercised ones;
- one read-only command reproduces the entire audit that motivated this
  change.

Reaching the horizon does not require registering any backlog artifact,
adjudicating any proposal, or writing any content.

## 2. Why a tier vocabulary rather than "register everything"

Registering 447 artifacts is content work: each needs a family, an authority
scope, a version role, and an extraction-quality judgment. That is the
operator's adjudication labour and it is the archive's bottleneck already
(20 proposals sit at `new`).

The defect is not that the 447 are unregistered. **The defect is that the
archive does not say so.** A held artifact honestly labelled
`pending-registration` is governed. A held artifact whose record claims
`registered` while the register omits it is a lie the validator endorses.

So the tier vocabulary is the minimum honest structure, and it is cheap: three
tiers, one policy file, one biconditional check.

## 3. Tier vocabulary

Declared in `00-system/policies/HOLDINGS_POLICY.json` and mirrored in
`00-system/policies/CONTROLLED_VOCABULARY.md`:

| tier | meaning | manifest row | counted in |
|---|---|---|---|
| `registered` | adjudicated, provenance-complete, part of the corpus of record | required | `source_material_count` |
| `pending-registration` | held, intended for registration, not yet adjudicated | forbidden | `held_artifact_count` only |
| `reference-shelf` | held deliberately as background; never intended for the corpus of record | forbidden | `held_artifact_count` only |

Two rules make this enforceable rather than decorative:

1. `registered` is the *only* tier permitted to appear in
   `MATERIALS_INDEX.jsonl`, and every manifest row's record must carry it.
2. The default tier for held-but-unregistered material is
   `pending-registration`, because it asserts no decision the operator has not
   made. Moving an artifact to `reference-shelf` is an operator act, recorded
   per family in `HOLDINGS_POLICY.json`.

**Open operator decision, deliberately not pre-empted:** whether
`mozare-wiki`'s 447 are a registration backlog or a reference shelf. Task B4
stops and emits an `advisor-request.v1` if the operator has not recorded a
mapping; the default keeps the archive honest in the meantime.

## 4. Where the numbers live

`CORPUS_STATE.json` gains two keys and one clarified one:

```json
{
  "source_material_count": 97,
  "held_artifact_count": 544,
  "holdings_by_tier": {"registered": 97, "pending-registration": 447, "reference-shelf": 0}
}
```

- `source_material_count` keeps its exact current meaning: **the number of
  rows in `MATERIALS_INDEX.jsonl`**. It is not redefined; redefining it would
  silently change every document that cites it.
- `held_artifact_count` is the count of files under `_originals/`.
- `holdings_by_tier` must sum to `held_artifact_count`.

No JSON Schema file is added for corpus state. The validator is the schema,
and a second declaration of the same shape is a second thing to drift.

## 5. Why two markers, not one compound string

Entry pages will show:

```text
Registered source artifacts: 97
Artifacts held: 544
```

not `Registered source artifacts: 97 of 544 held`. Two independent labelled
markers extend the 1.1.0 gate by exact string match, which is the property
that makes that gate reliable. A compound string requires parsing, and a
parser is a place for a lighter model to guess.

The `Artifacts held:` check is skipped when `held_artifact_count` is absent
from state, so an instance that has not yet adopted this change is not broken
by a kit upgrade.

## 6. Where enforcement lands, and where it deliberately does not

Added to `validate()`, therefore active in the pre-commit hook and in CI:

- `check_holdings_census(root, state, errors)` — the biconditional, the tier
  coverage of `_originals/`, and the count agreement.
- `check_entry_pages()` — extended with the `Artifacts held:` marker.
- the mojibake guard — extended from manifest rows to every source record's
  `aliases`, `original_path`, `filename`, and `title`.
- `check_register_policies(root, state, errors)` — every `.md` under
  `00-system/registers/` carries `refresh_policy` from a fixed enum, and a
  `per-intake` register whose `updated` predates `CORPUS_STATE.updated` fails.

Deliberately **not** enforced:

- whether a tier assignment is *correct* — that is adjudication;
- whether a register's *content* is right — only its declared freshness;
- anything about the 20 pending proposals.

## 7. Refresh policy enum, and why not a time window

`refresh_policy` takes exactly one of:

| value | fails when |
|---|---|
| `per-intake` | `updated` is older than `CORPUS_STATE.updated` |
| `per-release` | `updated` is older than the `updated` of `00-system/configuration/content-release.json` |
| `static` | never |

A day-count window ("stale after 90 days") fails a legitimately quiet archive
and passes a busy one that is actually behind. A comparison against the
register that *causes* the staleness is deterministic, timezone-free, and
correct on a repo nobody touched for a year.

## 8. Migration safety for populated instances

`scripts/retier_holdings.py` is read-only by default:

- `--dry-run` (default) prints the planned retiering and writes nothing;
- `--apply` refuses on a dirty working tree, so the change is always a
  reviewable diff;
- it never writes into `_originals/`, never edits `MATERIALS_INDEX.jsonl`, and
  never changes a record that is correctly `registered`;
- it refuses outright if the manifest row count and `source_material_count`
  disagree, because then the base state is already broken and retiering would
  bake in a wrong number.

Adoption in an existing instance is a single reviewable change per instance,
in the order given by task B4. Rerunning `instantiate.py` is never part of it.

## 9. Shared-register serialization

`MATERIALS_INDEX.jsonl` and `CORPUS_STATE.json` are monolithic files with a
snapshot hash over the whole manifest, so two branches touching them conflict
(`AGENTS.md`, "Shared-register serialization"). Tasks A3, B4 and C3 touch
state. They are strictly ordered in the ladder and must never run in parallel
lanes.

## 10. Rollback

Every kit task is revertible with `git revert` on a branch plus a validator
rerun. The one irreversible-feeling step is B4's `--apply` in `mozare-wiki`;
it is reversible because it runs on a clean tree, so discarding the working
tree restores the prior state before commit, and `git revert` restores it
after.

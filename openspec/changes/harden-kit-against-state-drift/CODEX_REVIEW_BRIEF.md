# CODEX BRIEF — Adversarial review of OpenSpec change `harden-kit-against-state-drift`

## Role and write scope (your whole write scope)

You are the adversarial reviewer for a planning change in the **living-wiki-kit**
repo (`C:\Users\Zarinpal\Documents\Personal Formal Documents\living-wiki-kit`,
branch `system/2026-09-16--harden-kit-spec`, HEAD 48dd711). You may edit ONLY:

- `openspec/changes/harden-kit-against-state-drift/proposal.md`
- `openspec/changes/harden-kit-against-state-drift/design.md`
- `openspec/changes/harden-kit-against-state-drift/tasks.md`
- `openspec/changes/harden-kit-against-state-drift/specs/entry-consistency/spec.md`

FORBIDDEN (do not touch): `scripts/`, `tests/`, `.claude/`, `00-system/`,
all root `*.md` docs, `openspec/config.yaml`, anything under `openspec/changes/`
other than this change, git history (no commits — leave changes uncommitted in
the worktree).

## Project in one paragraph

Living Wiki Kit 1.0.0 is the empty template for governed "living genetic
archive" wikis (git-versioned, Obsidian-readable, immutable `_originals/`,
8-level authority hierarchy, deterministic validators + pre-commit/CI gate).
Instances are created by `scripts/instantiate.py --name X --prefix pxx`
(rewrites `mw-` record-prefix → `pxx-`, stamps INSTANCE.json). Tests run as
plain python (`python tests/test_validator_mutations.py`; no pytest in venv).
Kit state is empty and must PASS both validators at birth
(`wiki-corpus-empty`, count 0).

## Evidence motivating this change (2026-09-16, verified in the ref-wiki instance)

1. Entry docs (README/HOME/SYSTEM_DESIGN §1/CLAUDE.md/reconcile skill)
   asserted a 6-day-stale seed state ("11 sources, intake paused") after the
   corpus had grown to 103 sources / 3 intake waves — a fully-ingested batch
   looked un-ingested.
2. Root causes were kit-level: nothing binds entry prose to the registers;
   INSTANTIATE.md invites hardcoding "corpus facts"; the shipped
   wiki-reconcile skill hardcodes a mozare baseline ("94 artifacts,
   `mw-corpus-a33b260403015901`") wrong for every instance; the shipped
   TEMPLATE_source-record.md omits the `filename` field its own validator
   requires; the intake skill never says to refresh entry pages.
3. The fix (validator `check_entry_pages()` gate + skill/template/instantiator
   alignment) was designed, TDD'd, e2e-proven (hook-blocked a drift commit),
   and merged in ref-wiki PRs #3–#7 (main db27adf).

## Artifacts to review (in the change dir)

1. `proposal.md` — WHAT/WHY (freely revisable)
2. `specs/entry-consistency/spec.md` — capability delta (freely revisable,
   must stay a valid OpenSpec delta: every requirement needs ≥1
   `#### Scenario:` block; keep `## ADDED Requirements` header)
3. `design.md` — HOW (freely revisable)
4. `tasks.md` — implementation checklist (freely revisable)

You may restructure, split, reorder, tighten, or add refusal rules/gates.
Do NOT delete the evidence record. Do NOT change scope away from the named
root causes; flag anything you believe is missing rather than inventing new
scope. Invariants that must survive: `_originals/` immutability; candidate
tier; empty-kit-birth PASS; no pytest dependency; validator error messages
self-explanatory; pre-commit hook + CI enforce the gate identically.

## Evaluation questions (answer each explicitly)

1. Do the four artifacts cover all five root causes end-to-end, or is there
   a gap (e.g. entry docs beyond the three named; capture/HOME edge cases)?
2. Is the spec delta's enforcement requirement testable as written? Are the
   scenarios concrete enough to drive TDD task rows 1.1/1.2 without
   interpretation?
3. Design D2 (empty-kit birth PASS) and D5 (plain-python tests): any hidden
   conflict (e.g. gate vs empty directories; `re` behaviors on count 0)?
4. Task ordering/dependencies: is the TDD tracer-bullet order right, and is
   the instantiate smoke test (4.1) sufficient to catch seeding regressions?
5. Migration risk: what breaks in *existing* instances if they later pull
   kit updates? Is "out of scope" acceptable here, and is it stated?
6. Anything in the plan that would fail the kit's own governance rules
   (branch naming, baseline discipline, no-force-push, reviewable diffs)?

## Output contract

- Edit the four artifacts in place (in the worktree, no commits).
- Keep the OpenSpec change valid: after your edits run
  `openspec validate harden-kit-against-state-drift` and fix until valid.
- No new runtime dependencies. No edits outside your scope.
- End with a summary ≤300 words: what you changed and why, top 3 risks you
  see in implementation, and any question for the human owner.

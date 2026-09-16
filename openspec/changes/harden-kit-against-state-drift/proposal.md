# Proposal: harden-kit-against-state-drift

## Why

The ref-wiki instance (living-wiki-kit 1.0.0) suffered a real governance
incident on 2026-09-16: its entry-level documents (README.md, HOME.md,
SYSTEM_DESIGN.md §1, wiki-reconcile skill, CLAUDE.md) asserted the
2026-09-10 seed state ("11 sources, intake paused, Horizon C open") for six
days after the corpus had grown to 103 sources across three intake waves.
The consequence: a fully-ingested batch appeared un-ingested to a reader,
and intake could have been wrongly resumed as "first intake".

Root-cause analysis traced every failure to a **kit-level design gap**, not
an instance-level mistake. The kit today:

1. **Ships no enforcement binding entry-level prose to the registers.**
   CORPUS_STATE.json is the live truth, but nothing fails a commit when
   README/HOME/SYSTEM_DESIGN restate stale counts. (Fix validated in
   ref-wiki PR #6: `check_entry_pages()` in validate_repo.py, e2e-proven.)
2. **Ships instance docs that invite hardcoded state.** Kit CLAUDE.md has no
   Current-State block, but INSTANTIATE.md step 3 tells users to rewrite
   "the corpus facts" in SYSTEM_DESIGN §1 with nothing saying how to keep
   them true. ref-wiki (and mozare-wiki before it) grew hardcoded blocks.
3. **Ships a stale baseline inside a skill.** `.claude/skills/wiki-reconcile/
   SKILL.md` hardcodes "94 artifacts, `mw-corpus-a33b260403015901`" — a
   mozare-wiki snapshot that is wrong for the empty kit and wrong for every
   future instance at birth.
4. **Ships a template that contradicts its own validator.**
   TEMPLATE_source-record.md omits the `filename` frontmatter field that
   validate_repo.py requires — bit zarinpal-product-wiki on 2026-09-14 and
   cost a debugging round.
5. **Loses provenance in the intake workflow.** The intake skill updates
   records but never instructs refreshing entry pages, so the drift recurs
   at every intake unless a human remembers. (ref-wiki fix: step-10
   instruction + enforcement.)

## What changes

- **Validator**: port the proven `check_entry_pages()` freshness gate from
  ref-wiki into the kit's validate_repo.py (entry pages: HOME.md, README.md,
  SYSTEM_DESIGN.md; presence of snapshot id + source count; layer-count
  contradiction check) — behind TDD with mutation tests.
- **Skills**: wiki-reconcile baseline line reads CORPUS_STATE.json at run
  start (never hardcoded); wiki-intake step 10 gains the explicit
  entry-page-refresh instruction.
- **Templates**: TEMPLATE_source-record.md gains the required `filename:`
  field.
- **Docs**: INSTANTIATE.md gains a "keep entry docs pointer-true" rule;
  SYSTEM_DESIGN §1/§6 updated (pointer-style, live-truth named, script-role
  table documents the gate); README/HOME corrected where they hardcode.
- **Instantiator**: instantiate.py seeds the three entry pages with the
  instance's own snapshot id and count (0), so a fresh instance starts
  gate-clean and the habit is structural.

## Impact

- Affected specs: `entry-consistency` (new capability)
- Affected code: scripts/validate_repo.py, scripts/instantiate.py,
  .claude/skills/wiki-reconcile/SKILL.md,
  .claude/skills/wiki-intake/SKILL.md,
  00-system/templates/TEMPLATE_source-record.md, SYSTEM_DESIGN.md,
  INSTANTIATE.md, README.md, HOME.md
- Existing instances (ref-wiki) already carry the gate; this change makes
  every *future* instantiation inherit it at birth.

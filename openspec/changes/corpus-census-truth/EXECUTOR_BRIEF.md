# Executor brief: corpus-census-truth

Read this once per task, before touching a file. It is written for a
fresh-context agent on a lighter model (**Sonnet 5, high effort** is the
assumed default) running one rung of the ladder under the harness.

## 1. The contract

You execute **exactly one task row** from `tasks.md`, then stop.

You do not plan the next rung, you do not start it, you do not "also fix"
something you noticed. A noticed problem goes in the task's review note as one
line and nothing more. Scope creep in this repo is a governance failure, not a
kindness.

A rung is finished when every lettered acceptance criterion in its row prints
the stated result **from a command you actually ran and pasted**. Not
"should pass". Ran, pasted.

## 2. What to load, and nothing else

Each task row names its `Context` files. Load those, plus:

- `openspec/changes/corpus-census-truth/design.md` — sections named in the row
- `CLAUDE.md` — the always-on rules
- the file you are editing

Do **not** read the corpus, the 556 source records, `_originals/`, or another
instance. If a row needs a number from `mozare-wiki`, it says so and gives the
exact read-only command that produces it.

Budget: if you are past ~15 tool calls on a `[size:S]` rung or ~40 on an
`[size:M]` rung, stop and emit an `advisor-request.v1` (section 6). Being
behind budget is information, not failure.

## 3. TDD is mandatory where the row says `[tdd:required]`

The order is fixed and both halves must appear in your report:

1. **RED** — write the test, run
   `python tests/test_validator_mutations.py`, and paste the **named
   failures**. A test that passes before the implementation exists is a broken
   test; fix the test, do not proceed.
2. **GREEN** — implement the minimum that makes those named tests pass, run
   the suite again, paste `N/N passed`.

`tests/test_validator_mutations.py` is plain Python with its own `__main__`
runner. There is no pytest in this repo. Do not introduce one. Do not add a
dependency: `requirements.txt` contains exactly `PyYAML` and that is a
governance constraint, not an oversight.

## 4. The four commands that decide everything

```bash
python tests/test_validator_mutations.py        # the suite; expect N/N passed
python scripts/validate_repo.py --full          # expect PASS: ... are valid
python scripts/validate_content_release.py      # expect PASS: populated wiki ...
python scripts/check_against_baseline.py        # expect OK: validators clean.
```

`WARNING:` lines are expected and harmless — fourteen of them exist on a clean
tree. Only `ERROR:` and the final verdict line matter.

Windows note: subprocesses in tests must be launched with
`encoding="utf-8", errors="replace"`. A child process writing an em dash in
cp1252 crashes a reader thread otherwise. This is already the pattern in the
suite; copy it.

## 5. Absolute prohibitions

These are not preferences. Violating one fails the rung regardless of the
diff's quality.

1. Never edit, move, rename or delete anything under `_originals/`.
2. Never add a line to `.githooks/known-baseline-errors.txt`. If a check you
   add fires on existing content, **report the count and stop** — tolerating
   debt is an operator decision made in its own reviewed commit.
3. Never use `--no-verify`, never force-push, never `git add -A` from the repo
   root. Stage named paths only; `.claude/`, `.harness-mem/` and `_search/`
   must stay untracked.
4. Never edit `MATERIALS_INDEX.jsonl` or a `sha256` value. Ever. In any task.
5. Never redefine `source_material_count`. It means "rows in the manifest" and
   six documents depend on that.
6. Never run `scripts/instantiate.py` in a populated instance.

## 6. When to stop and ask instead of deciding

Emit an `advisor-request.v1` and stop if any of these is true:

- the row needs a judgment about **what the corpus means** (which tier a
  family of artifacts belongs in, whether a register is still consulted,
  whether a claim is supported);
- a check you implemented fires on existing content and the row does not
  already tell you the expected count;
- two acceptance criteria contradict each other;
- the base state fails before you change anything — `validate_repo.py --full`
  is not `PASS` on a clean checkout of your branch point.

Shape:

```json
{"kind": "advisor-request.v1", "task": "<row id>", "blocked_on": "<one sentence>",
 "options": ["<a>", "<b>"], "recommendation": "<a or b, with one reason>",
 "evidence": ["<path or command output line>"]}
```

Then hand back. Do not pick for the operator on a corpus-semantics question;
that is the authority hierarchy working, not you being unhelpful.

## 7. Harness surfaces per rung

| Surface | Use |
|---|---|
| `/harness-work <row id>` | run one rung end to end |
| `claude-code-harness:worker` | the implementation agent inside a rung |
| `claude-code-harness:reviewer` | verdict against this brief and the row's criteria; read-only |
| `claude-code-harness:test-wiring-auditor` | run after **A4**, **B1**, **C1**, **C2** — confirms the test net actually covers the new branch, in fresh context |
| `claude-code-harness:advisor` | receives an `advisor-request.v1`; returns direction only, never an edit |
| `/harness-sync` | reconcile `Plans.md` markers with what actually landed |

Marker discipline in `Plans.md`: `cc:todo` to `cc:wip` when you start, to
`cc:done` when every criterion is pasted and green. Only the operator writes
`pm:approved`. One rung at `cc:wip` at a time — the registers do not tolerate
concurrent branches (design section 9).

## 8. Loop and pacing

`/harness-loop` in dynamic mode owns the long tail. Per wake-up:

1. `/harness-sync` — read `Plans.md`, find the lowest-numbered `cc:todo` whose
   `Depends` are all `cc:done` or `pm:approved`;
2. run that one rung;
3. `ScheduleWakeup` with `noop: false` if anything landed, `noop: true` if you
   were blocked, and a `reason` naming the rung.

Wake cadence: **1200–1800s** when idle or waiting on operator review. Do not
poll in minutes — nothing here changes on a timescale shorter than a human
reading a diff. Stop the loop when every row is `cc:done` or `pm:approved`, or
when two consecutive wake-ups end in the same `advisor-request.v1`.

## 9. Commit and report shape

One rung, one commit, on the branch the row names. Message:

```
<area>: <what changed> (<row id>)

<why, 2-4 lines, including the number that motivated it>

python tests/test_validator_mutations.py -> N/N passed
python scripts/validate_repo.py --full -> PASS
<any other criterion command and its decisive line>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Then report to the operator in plain language: what now works, which command
proves it, what you deliberately did not do. No diffs — the operator does not
read them.

## 10. Model routing

| rungs | model | why |
|---|---|---|
| A2, A4, B1, C1, C2 | Sonnet 5, high effort | mechanical TDD against a written invariant; the test is the spec |
| A1, A3, A5, B2, B3, D1, E1 | Sonnet 5, high effort | bounded edits with exact acceptance strings |
| **B4, C3** | escalate to Opus, or run under operator review | they touch a populated instance and carry corpus-semantics decisions |

If you are a lighter model and the row you drew is B4 or C3, do the read-only
half (the `--dry-run`, the counts, the proposed per-register table), paste the
numbers, and hand back rather than applying.

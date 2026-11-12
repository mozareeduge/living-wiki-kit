# living-wiki-kit 1.5.0: shared lane contract (wave 1)

You are one of 3 parallel Gemini lanes on a Linux VM. The full owner handoff is pasted below (HANDOFF). It is the authority. Read sections 0–5 and 10 before you code.

## Setup (do exactly this; you may write ONLY inside ../out/)
```
cd ../out
git clone https://github.com/mozareeduge/living-wiki-kit.git repo && cd repo
git checkout -b system/2026-11-09--remote-ingest-chunks ac66be81cc865645253a09e4c3b27f04c80fd0b3
python3 -m venv ../venv && ../venv/bin/pip install -q -r requirements.txt -r requirements-governance.txt pytest
python3 -c "import sqlite3;c=sqlite3.connect(':memory:');c.execute('create virtual table t using fts5(x)');print('FTS5 ok')"
../venv/bin/python -m pytest -q tests scripts/tests 2>&1 | tail -5 > ../BASELINE-TESTS.txt   # baseline BEFORE any edit
```
If the clone or pip fails, write `../out/BLOCKED.md` with the exact error and stop.

## Rules
1. TDD: write the failing test first, then the code. One commit per rung (`<ID>: <what>`), git user "Jimmy lane" <jimmy@localhost>.
2. All invariants in HANDOFF §2 hold. Especially: no owner names, personal paths or "0xbrain" in shipped code (the kit-independence and privacy tests must stay green); instance prefix, never a hard-coded `wiki`; fail closed; deterministic on LF/CRLF and UTF-8 NFC.
3. **Touch only the files your lane owns** (listed in your lane). If you need a change outside them, write it to `../out/CROSS-LANE-REQUEST.md`, do not make it.
4. Do not edit Plans.md, CHANGELOG.md or the version number (Jimmy merges them).
5. At the end, run the WHOLE suite again: `../venv/bin/python -m pytest -q tests scripts/tests 2>&1 | tail -15 > ../FINAL-TESTS.txt`. New failures compared with the baseline must be fixed or listed.
6. Deliver in ../out/:
   - `patches/`: `git format-patch ac66be81cc865645253a09e4c3b27f04c80fd0b3..HEAD -o ../patches`
   - `RESULT-<lane>.md`: per rung, done / partial / not done, with the test names that prove it; baseline and final test tails; deviations from HANDOFF and why; open questions.
7. Never invent results. If a test was not run, say so. End your reply with STATUS / CHANGED / CHECKED / OPEN lines.

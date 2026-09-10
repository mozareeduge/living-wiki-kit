---
name: wiki-validate
description: Run deterministic validation and prepare a semantic audit report. Read-only unless the user separately approves repairs.
---

# Wiki Validate

1. Run `python scripts/validate_repo.py --full`.
2. Run `qmd status`.
3. Run the semantic regression queries in `09-indexes/semantic-search-test-set.md`.
4. Check:
   - duplicate or drifting terms;
   - unsupported claim upgrades;
   - repeated AI reports treated as corroboration;
   - stale current-version labels;
   - source/derivative confusion;
   - public records depending on private or unverified sources;
   - broken lineage and relation links.
5. Produce `_audits/<date>--validation.md`.
6. Do not silently repair canonical content. Separate deterministic repair proposals from interpretive decisions.

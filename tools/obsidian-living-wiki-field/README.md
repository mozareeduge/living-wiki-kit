# Living Wiki Field

A local Obsidian interface for exploring the archive spatially and reading its records. The inherited interaction grammar is **Field → Reader → Route → View**, extended by **Review** and **Health**. It works offline without a model or hosted service.

## Install

Run `python scripts/install_obsidian_field.py --vault <existing-vault-folder>` from the kit checkout. It copies only the plugin files to `.obsidian/plugins/living-wiki-field/` and preserves existing plugins and settings. Enable **Living Wiki Field** in Community plugins. The command palette and ribbon expose Field, Reader, Route, Index, Review and Health.

## Experience

1. **Field:** zoom, pan, drag, select a node and inspect its neighbors. Dotted participant projections retain the generating relation record. The projection is navigation, never evidence.
2. **Reader:** see the record's authority exactly as recorded, its claim permission, linked records and immutable original. Internal links follow the same Reader; Persian text uses automatic direction. No authority is inferred from color, a label or a retrieval score.
3. **Route / View:** retrace the last eleven visits after reopening Obsidian. Filter by record type, authority, updated date, permission and candidate state. Filters change attention, never records.
4. **Review:** inspect durable candidate proposals, their evidence pointers and adjudication status. The interface cannot accept, reject or apply them. The owner uses the established adjudication workflow.
5. **Health:** inspect register counts and run the four existing governance checks. Until run, validation is explicitly unverified. A passing result is dated; later edits require another check. Python interpreter is configurable in plugin settings.

## Data boundaries

Record IDs, paths and wikilinks resolve to their existing records. Relation `participants`, claim `supporting_sources`, lineage references and source `original_path` become view edges. Duplicate IDs are reported instead of guessed. Unresolved references remain visible in Health. Original artifacts stay separate from source records. Candidate nodes are marked in the graph and Reader, and never become canonical files.

Saved context packs under `_search/packs/` provide optional related-record hints with reasons. No pack means ordinary recorded neighbors remain available. Hints are not evidence. The UI does not generate packs, run a model, or silently query another archive.

UI state is stored only in `.obsidian/plugins/living-wiki-field/data.json`. All archive surfaces are read-only; the ordinary Obsidian editor remains a separate host feature. The kit continues to work without this plugin.

## Verification and limits

`node --test tools/obsidian-living-wiki-field/model.test.js` exercises participant IDs, source traces, duplicate identity, candidate boundaries and bounded projection. `python -m pytest tests/test_obsidian_field_install.py -q` tests installation isolation. `node --check` checks the UI scripts. Live Obsidian acceptance covers graph, Reader, Route, filters, Review and Health.

The desktop graph is optimized for a local working archive. Index pages show up to 300 matching records; narrow the filter to inspect larger inventories. Hyperedges above forty participants stay as star connections to avoid quadratic expansion. Route memory is navigation history, never a historical claim. Mobile capture remains in the separate governed capture client; this desktop UI is not a mobile Git client. Generative assistance cards are deferred.

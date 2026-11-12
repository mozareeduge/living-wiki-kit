# Promotion proposal — <capture-id>

1. `read <capture-id>` — confirm status `reviewed`, note the sha256.
2. `wiki_propose_from_capture` with IDs + hashes + rationale.
3. An agent runs `/wiki-intake` on it and merges when the gates are green (no approval gate, OM-888), stamping the change in `CHANGE_LEDGER.jsonl`.
4. Then: `set-state <capture-id> promoted --actor <agent or you> --target <path>`.

Nothing here edits canonical pages. Proposals are inert until adjudicated.

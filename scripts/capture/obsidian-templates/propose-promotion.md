# Promotion proposal — <capture-id>

1. `read <capture-id>` — confirm status `reviewed`, note the sha256.
2. `wiki_propose_from_capture` with IDs + hashes + rationale.
3. A human approves through the normal governance path.
4. On approval: `set-state <capture-id> promoted --actor <you> --target <path>`.

Nothing here edits canonical pages. Proposals are inert until adjudicated.

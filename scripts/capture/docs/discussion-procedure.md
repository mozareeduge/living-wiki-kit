---
id: mw-doc-capture-discussion
type: system-document
title: "Capture discussion procedure (client-neutral, 1.2.0)"
status: candidate
---
# Discussing captures (all clients)

1. Resolve capture IDs or explicit `wiki_search_captures` results.
2. Tell the user which items AND which representation (raw, literal,
   description, reviewed) the answer uses.
3. Read raw/literal material before summaries when accuracy matters.
4. Label every inference and uncertainty; unreviewed machine text is never
   quoted as a wiki statement.
5. Requested wiki change → `wiki_propose_from_capture` with IDs + hashes →
   existing approval path. No direct canonical writes, on any client.

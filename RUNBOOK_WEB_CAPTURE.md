---
id: mw-runbook-web-capture
type: system-document
title: Web Capture Runbook — Cited Pages to Checksummed Derivatives
status: active
visibility: private
created: '2026-08-25'
updated: '2026-08-25'
schema_version: 1.0.0
---

# Web Capture Runbook

Engine 4 mechanism (T6 backlog item 3): turn cited web sources into checksummed
derivatives so "verified external primary" survives link rot. Uses the stack the
media-art preservation world trusts (Webrecorder/browsertrix); a plain curl
fallback keeps the runbook usable before any tooling install.

## When to capture

A claim or relation cites a web page whose content is load-bearing → capture at
intake time, not later. Link rot is not hypothetical (the research campaign met
dead/redirected/bot-walled pages repeatedly).

## Procedure A — plain fallback (no installs)

1. Fetch with identity recording:

   ```bash
   TS=$(date -u +%Y%m%d)
   curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
        -o "_captures/<slug>--${TS}.html" -w "%{http_code} %{url_effective}\n" "<url>"
   ```

2. **P5b identity check (mandatory):** confirm page `<title>`/scope matches the
   claimed source. HTTP 200 ≠ right target.
3. Hash + register:

   ```bash
   sha256sum "_captures/<slug>--${TS}.html"
   ```

4. Add a source record / MATERIALS_INDEX row per intake rules
   (`preservation_status: captured-copy`; record fetch date, effective URL,
   http status, and the identity-check result in the record body).
5. If the page blocked automation (403/Cloudflare/Anubis): apply the P5 ladder
   (official mirror → web.archive.org) and record the negative finding if
   exhausted. Never fabricate content.

## Procedure B — browsertrix-crawl (high-value multi-page targets)

```bash
pipx install browsertrix-crawler
browsertrix-crawl --url "<url>" --workers 2 --save-state visited \
                  --collection <slug> --generateWACZ
```

The resulting `.wacz` bundles WARCs + screenshots + metadata. Store it like an
original (checksummed, immutable), register it, and extract text derivatives
for search as with any artifact.

## Rules

1. Captures are derivatives-with-provenance: they never upgrade the authority
   of the claims they support.
2. Every capture gets an event record (`type: event-object`) noting tool,
   version, date, and identity check.
3. Bot-walls are documented negative findings, not invitations to bypass.

*(Established on branch convergent-phase-engines, Engine 4 intake, 2026-08-25;
mechanism validated during the six-field campaign's own capture passes.)*

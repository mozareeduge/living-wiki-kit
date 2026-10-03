---
id: practice-investigation
type: wiki-profile
profile_class: practice
title: Investigation
version: 1.0.0
status: example
seed_labels: [allegation, hypothesis, timeline, verified, unverified]
suggested_relation_language: [alleges, corroborates, contradicts, places-on-timeline]
suggested_lenses: [lens-investigator]
suggested_outputs: [timeline, evidence-memo, hypothesis-register]
preferred_lens: null
preferred_output: null
---

# Purpose

Journalistic or OSINT-style inquiry where unverified hypotheses must stay
distinguishable from facts.

# What this profile helps the system notice

Source reliability, corroboration structure, and the exact boundary between
what is shown and what is suspected.

# Anti-patterns

Never let a label (`verified`) substitute for the underlying
relation/claim evidence.

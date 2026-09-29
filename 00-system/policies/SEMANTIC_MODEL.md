# Semantic model — how the kit describes the world without locking it

> **The kernel governs how knowledge is handled. It does not dictate what
> kinds of things knowledge is allowed to describe.**

## Structural type is closed; semantic vocabulary is open

`type` says what kind of *record* a file is inside the kernel
(`source-record`, `object`, `relation-object`, `claim-object`, `handoff`,
`proposal`, `adjudication`, …). It never says whether an object is a person,
a rehearsal, a risk queue, or anything else. That question belongs to the
adaptive layer below.

## Object before kind

Stable identity may be recorded before semantic classification is known or
useful. An object can have sources, relations, claims, labels, history, and
retrieval presence without first passing through a taxonomy. Classification
is optional enrichment, never a precondition of existence.

## Labels organize discovery; they do not constitute evidence

A label is a lightweight descriptive marker (`labels:` list on object
records). Labels may be broad or narrow, temporary, local, human- or
agent-supplied, overlapping, even contradictory in early work — and absent.

A label is never evidence, never a claim, never authority, never a reason to
merge identities or to suppress or demote a record. If it matters that
*person A was the translator of book B*, that belongs in a relation or claim
with sources — the label `translator` only helps you find the person.

Mechanical rules only: non-empty strings, at most 120 characters, no
line-breaks, no exact duplicates. An unfamiliar label is always valid. The
search layer may normalize labels for indexing (NFKC, trim, case-fold) but
must never rewrite the written label and never auto-merge synonyms.

## Substantive classification uses relations and claims

When a classification carries meaning — *session X is a rehearsal of work
Y*, *project X should be understood as documentary theatre* — express it as
an evidence-bearing relation or claim, not as a label and never as a
mandatory kind. No new classification record type exists; the kernel's
relation/claim machinery is sufficient.

## Profiles configure the practice; they do not define the truth

Profiles (`00-system/configuration/profiles/`) bundle suggestions —
vocabulary, relation language, lenses, outputs — for a practice, domain,
collaboration shape, or compliance context. They compose additively, may
tighten kernel rules, and may never weaken them. A profile never requires an
object to fit its vocabulary; unknown labels always remain allowed.

## Lenses foreground; they do not filter truth

Lenses (`00-system/configuration/lenses/`) configure retrieval and
presentation for a persona or task. Defaults: candidates included,
authority annotated. A lens may prioritize, group, and format; it must never
silently hide contradictory evidence, promote candidate material, treat a
label as evidence, suppress non-adjudicated records, or change authority.
Authority-only views must be explicit.

## Adjudication upgrades authority; it does not grant visibility

Candidate objects remain visible in default retrieval, visibly marked
candidate, with relevance and authority reported as separate axes. Rejected
material leaves ordinary results but stays available to audit and genesis.

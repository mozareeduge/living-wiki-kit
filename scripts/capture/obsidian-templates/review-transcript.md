# Transcript review — <capture-id>

1. Read the record (`read <capture-id>`): raw text first, then the literal.
2. Play the media. Fix names, dates, numbers; mark uncertain spans.
3. `commit-transcript --id <capture-id> --adapter manual --text-file <fixed>`
4. `set-state <capture-id> reviewed --actor <you> --note <what changed>`

A reviewed transcript is still level-7 candidate material — correction
records effort, not truth.

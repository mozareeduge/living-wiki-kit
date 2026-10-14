#!/usr/bin/env python3
"""Create an isolated, fictional Field walkthrough vault. Refuses an existing destination."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(root: pathlib.Path, *args: str) -> str:
    p = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(' '.join(args) + '\n' + p.stdout + p.stderr)
    return p.stdout

def note(root: pathlib.Path, path: str, record: dict, body: str) -> None:
    f = root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        raise FileExistsError(f'Demo never overwrites an existing record: {path}')
    record = {'created': '2026-10-14', 'updated': '2026-10-14', 'schema_version': '1.0.0', **record}
    f.write_text('---\n' + yaml.safe_dump(record, allow_unicode=True, sort_keys=False) + '---\n\n' + body + '\n', encoding='utf-8')

def create(destination: pathlib.Path) -> pathlib.Path:
    destination = destination.resolve()
    if destination.exists():
        raise ValueError('Destination already exists; choose a new folder. Nothing was changed.')
    subprocess.run(['git', 'clone', '--local', '--no-hardlinks', str(ROOT), str(destination)], check=True, capture_output=True)
    run(destination, 'scripts/instantiate.py', '--name', 'Living Wiki Walkthrough', '--prefix', 'demo')
    passage = 'In this fictional rehearsal, the second scene changed after a recorded discussion.'
    original = destination / '_originals/demo-rehearsal.txt'
    original.parent.mkdir(exist_ok=True)
    original.write_text('FICTIONAL WALKTHROUGH FIXTURE — not personal archive evidence.\n\n' + passage + '\n', encoding='utf-8')
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    sid = 'demo-src-' + digest[:12]
    spath = '02-sources/records/' + sid + '.md'
    note(destination, spath, {'id': sid, 'type': 'source-record', 'title': 'Demo rehearsal receipt',
         'filename': original.name, 'format': 'txt', 'sha256': digest, 'original_path': '_originals/' + original.name,
         'extracted_text_path': None, 'authority_scope': 'fictional-demo-fixture',
         'validation_status': 'registered-not-fully-claim-validated', 'status': 'registered', 'visibility': 'private'},
         '# Demo rehearsal receipt\n\n' + passage + '\n\nThis synthetic source proves only its own fixture bytes. It makes no claim about a real work.')
    claim_text = 'After the director\'s note, the second scene was rewritten.'
    for slug,title,text in [('first','First rehearsal','An early fictional rehearsal.'),('second','بازنویسی صحنه','A later fictional scene revision. Persian title demonstrates bidirectional reading.')]:
        note(destination, '03-objects/' + slug + '.md', {'id': 'demo-obj-' + slug, 'type': 'object', 'title': title,
             'status': 'active-record', 'labels': ['demo', 'rehearsal'], 'authority_tier': 'candidate', 'visibility': 'private',
             'supporting_sources': [sid]}, '# ' + title + '\n\n' + text + '\n\n[[06-relations/revision|Inspect the candidate relation]]\n\n[[02-sources/records/' + sid + '|Trace the receipt]]')
    note(destination, '06-relations/revision.md', {'id': 'demo-rel-revision', 'type': 'relation-object',
         'title': 'Candidate: rehearsal leads to revision', 'participants': ['demo-obj-first', 'demo-obj-second'],
         'relation_status': 'candidate', 'current_claim_permission': 'may-note', 'authority_tier': 'candidate',
         'supporting_sources': [sid], 'counter_evidence': [], 'status': 'active', 'visibility': 'private'},
         '# Candidate: rehearsal leads to revision\n\nA fictional, unaccepted relation. Its graph projection is an aid to navigation.\n\nThe source passage is: ' + passage)
    note(destination, '05-claims/change.md', {'id': 'demo-claim-change', 'type': 'claim-object',
         'title': 'Candidate claim: the scene was rewritten', 'statement': claim_text, 'supporting_sources': [sid],
         'unsupported_zones': ['No evidence about an actual artwork'], 'counter_evidence': [], 'certainty': 'candidate',
         'current_claim_permission': 'may-note', 'responsible_language': 'en', 'status': 'active', 'visibility': 'private'},
         '# Candidate claim\n\n' + claim_text + '\n\nThis remains candidate material. [[03-objects/second|Read the revised scene]].')
    run(destination, 'scripts/wiki_state.py', '--repo', '.', 'rebuild')
    run(destination, 'scripts/sync_intake_registers.py', '--accept-corpus-change', '--apply')
    sys.path.insert(0, str(destination / 'scripts'))
    from gov_kernel.proposals import create_proposal
    create_proposal(destination, kind='object-create', body=json.dumps({'title': 'Candidate: the discussion as an object',
        'source_passage': {'path': spath, 'quote': passage}, 'labels': ['demo', 'discussion']}, ensure_ascii=False),
        submitted_by={'actor_type': 'agent', 'tool': 'fictional-demo-generator'}, evidence_refs=[sid], target_refs=['demo-obj-second'])
    run(destination, 'scripts/build_graph_index.py')
    run(destination, 'scripts/candidate_projection.py', 'rebuild')
    run(destination, 'scripts/context_pack.py', '--seed', 'demo-obj-first', '--hops', '1')
    case = {'claim_id': 'demo-claim-change', 'title': 'The scene that changed', 'minutes': 4,
            'brief': 'A colleague wants to cite this claim in a programme note. Before they do, check it against the passage it points to.',
            'answer': 'overstated',
            'options': [{'key': 'supported', 'label': 'Supported'}, {'key': 'overstated', 'label': 'Overstated'}, {'key': 'unclear', 'label': 'Needs more evidence'}],
            'reveal_right': 'Right. The source says the scene changed after a recorded discussion. It never mentions a director, a note, or a rewrite. The claim adds all three.',
            'reveal_other': 'Look at the highlighted words: the claim adds a director, a note and a rewrite that the source never states.',
            'next_label': 'Start with your own document', 'next_path': 'QUICKSTART.md'}
    note(destination, 'WALKTHROUGH.md', {'id': 'demo-index-walkthrough', 'type': 'index', 'title': 'Start the walkthrough', 'status': 'active', 'case': case},
        '# Start the walkthrough\n\nThis vault is fictional. No personal archive has been changed.\n\n'
        '**Case file: the scene that changed.** About four minutes.\n\n'
        '1. The **Case** tab should already be open. If not, run **Living Wiki Field: Open the case**.\n'
        '2. Press **Show it on the map**. The pulsing dashed ring is the claim.\n'
        '3. Compare the claim with the source. Highlighted words are not in the source.\n'
        '4. Choose a verdict. It is saved in the plugin only, never in the archive.\n'
        '5. Optional: open **Review** to see an AI suggestion waiting for a person, and **Health** to run the governance checks.\n\n'
        'Afterwards you will know what the kit is for: it does not stop you from writing claims, it shows you which ones outrun their evidence.\n\n'
        '[[03-objects/first|Browse from First rehearsal]] · [[05-claims/change|Open the claim record]]')
    from install_obsidian_field import install
    install(destination)
    obs = destination / '.obsidian'
    (obs / 'community-plugins.json').write_text('["living-wiki-field"]\n', encoding='utf-8')
    (obs / 'app.json').write_text(json.dumps({'showInlineTitle': True, 'defaultViewMode': 'preview'}), encoding='utf-8')
    for args in [('scripts/wiki_validate.py', '--repo', '.', '--format', 'json'),
                 ('scripts/wiki_state.py', '--repo', '.', 'check'), ('scripts/wiki_evidence.py', '--repo', '.', 'check'),
                 ('scripts/wiki_profiles.py', 'check')]:
        output = run(destination, *args)
        print('PASS ' + ' '.join(args))
    print(f'Demo ready: {destination}')
    return destination

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--destination', required=True, type=pathlib.Path)
    args = ap.parse_args()
    try:
        create(args.destination)
    except (ValueError, RuntimeError, OSError) as exc:
        ap.exit(1, str(exc) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install the local Field plugin; writes only its plugin folder, never archive records."""
from __future__ import annotations
import argparse
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ('main.js', 'model.js', 'extensions.js', 'manifest.json', 'styles.css',
         'NOTICE.md', 'vendor/d3.min.js', 'vendor/D3-LICENSE.txt')

def install(vault: pathlib.Path) -> pathlib.Path:
    vault = vault.resolve()
    if not vault.is_dir():
        raise ValueError('Vault must be an existing directory')
    src = ROOT / 'tools/obsidian-living-wiki-field'
    dest = vault / '.obsidian/plugins/living-wiki-field'
    for rel in FILES:
        source = src / rel
        if not source.is_file():
            raise ValueError(f'Plugin incomplete: {rel}')
        target = dest / rel
        resolved = target.resolve()
        if not resolved.is_relative_to(vault):
            raise ValueError(f'Plugin destination escapes vault: {target}')
        if resolved != target or any(p.is_symlink() or (getattr(p, 'is_junction', lambda: False)())
                                     for p in (target, *target.parents) if p != vault and p.is_relative_to(vault)):
            raise ValueError(f'Plugin destination is redirected by a link: {target}')
        if target.is_file() and target.stat().st_nlink > 1:
            raise ValueError(f'Plugin destination has shared hard links: {target}')
    for rel in FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
    return dest

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vault', required=True, type=pathlib.Path)
    args = ap.parse_args()
    try:
        dest = install(args.vault)
    except (ValueError, OSError) as exc:
        ap.exit(1, f'Install refused: {exc}\n')
    print(f'Installed Living Wiki Field: {dest}')
    print('Enable Living Wiki Field in Obsidian Community plugins, then open Field.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

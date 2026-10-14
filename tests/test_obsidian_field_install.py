from pathlib import Path
import importlib.util
import pytest
import os
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('field_install', ROOT / 'scripts/install_obsidian_field.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

def test_install_preserves_archive_and_existing_plugins(tmp_path):
    original = tmp_path / '_originals/receipt.txt'
    original.parent.mkdir(); original.write_bytes(b'untouchable\r\n')
    other = tmp_path / '.obsidian/plugins/existing/main.js'
    other.parent.mkdir(parents=True); other.write_bytes(b'other plugin')
    settings = tmp_path / '.obsidian/community-plugins.json'
    settings.write_bytes(b'["existing"]')
    installer.install(tmp_path)
    assert original.read_bytes() == b'untouchable\r\n'
    assert other.read_bytes() == b'other plugin'
    assert settings.read_bytes() == b'["existing"]'
    dest = tmp_path / '.obsidian/plugins/living-wiki-field'
    assert all((dest / name).is_file() for name in installer.FILES)
    assert 'cdn.jsdelivr.net' not in (dest / 'main.js').read_text(encoding='utf-8')
    assert not re.search(r'require\([\'\"]\./', (dest / 'main.js').read_text(encoding='utf-8'))

def test_install_refuses_missing_vault_without_creating_it(tmp_path):
    target = tmp_path / 'missing'
    with pytest.raises(ValueError, match='existing directory'):
        installer.install(target)
    assert not target.exists()

def test_install_refuses_symlink_escape_before_any_copy(tmp_path):
    outside = tmp_path / 'outside'; outside.mkdir()
    vault = tmp_path / 'vault'; vault.mkdir()
    try:
        (vault / '.obsidian').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Creating a symlink is not permitted on this platform')
    with pytest.raises(ValueError, match='escapes'):
        installer.install(vault)
    assert not list(outside.rglob('*'))

def test_install_refuses_link_into_immutable_originals(tmp_path):
    original_dir = tmp_path / '_originals'; original_dir.mkdir()
    original = original_dir / 'main.js'; original.write_bytes(b'immutable original')
    plugins = tmp_path / '.obsidian/plugins'; plugins.mkdir(parents=True)
    try:
        (plugins / 'living-wiki-field').symlink_to(original_dir, target_is_directory=True)
    except OSError:
        pytest.skip('Creating a symlink is not permitted on this platform')
    with pytest.raises(ValueError, match='redirected'):
        installer.install(tmp_path)
    assert original.read_bytes() == b'immutable original'
    assert list(original_dir.iterdir()) == [original]

def test_install_refuses_hardlinked_original_before_copying(tmp_path):
    original_dir = tmp_path / '_originals'; original_dir.mkdir()
    original = original_dir / 'source.bin'; original.write_bytes(b'immutable original')
    plugins = tmp_path / '.obsidian/plugins/living-wiki-field'; plugins.mkdir(parents=True)
    os.link(original, plugins / 'main.js')
    with pytest.raises(ValueError, match='shared hard links'):
        installer.install(tmp_path)
    assert original.read_bytes() == b'immutable original'
    assert not (plugins / 'manifest.json').exists()

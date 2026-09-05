from pathlib import Path

import pytest

from scripts.retained_build_inputs import freeze_input, load_input, tree_hash


def test_freeze_copies_only_declared_inputs_and_checks_hash(tmp_path: Path) -> None:
    source = tmp_path / 'old'
    (source / 'geometry').mkdir(parents=True)
    (source / 'geometry/asset.usda').write_text('#usda 1.0')
    (source / 'unused_video.mp4').write_bytes(b'not-a-build-input')
    entry = freeze_input(source, tmp_path / 'inputs', 'room', ['geometry'])
    root = load_input(entry)
    assert (root / 'geometry/asset.usda').is_file()
    assert not (root / 'unused_video.mp4').exists()
    assert entry['tree_sha256'] == tree_hash(root)
    (root / 'geometry/asset.usda').write_text('changed')
    with pytest.raises(ValueError, match='hash'):
        load_input(entry)


def test_freeze_refuses_entire_old_package(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='explicit'):
        freeze_input(tmp_path, tmp_path / 'dest', 'old-package', ['.'])


def test_freeze_rejects_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        freeze_input(tmp_path, tmp_path / 'dest', 'missing', ['scene.usd'])

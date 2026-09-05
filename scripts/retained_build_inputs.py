"""Explicit, hash-locked build inputs, independent of historical output trees."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile


INDEX = Path(__file__).resolve().parents[1] / 'configs/build_inputs/scientific_workbench.v1.json'


def tree_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'build input cannot contain symlink: {path}')
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b'\0')
            with path.open('rb') as stream:
                file_digest = sha256()
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                    file_digest.update(block)
            digest.update(file_digest.digest())
    return digest.hexdigest()


def freeze_input(source: Path, store: Path, name: str, includes: list[str]) -> dict:
    if not includes or any(p in ('', '.') or Path(p).is_absolute() or '..' in Path(p).parts for p in includes):
        raise ValueError('explicit relative build inputs are required; whole-package copies are forbidden')
    if Path(name).name != name or name in ('', '.', '..'):
        raise ValueError('invalid input name')
    for relative in includes:
        if not (source / relative).exists():
            raise FileNotFoundError(source / relative)
    store.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.freeze-', dir=store) as temporary:
        staging = Path(temporary) / 'input'
        staging.mkdir()
        for relative in includes:
            origin, dest = source / relative, staging / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if origin.is_dir():
                shutil.copytree(origin, dest)
            else:
                shutil.copy2(origin, dest)
        digest = tree_hash(staging)
        target = store / f'{name}-{digest[:16]}'
        if target.exists():
            if tree_hash(target) != digest:
                raise ValueError('existing input hash mismatch')
        else:
            staging.rename(target)
    return {'path': str(target.resolve()), 'tree_sha256': digest,
            'origin': str(source.resolve()), 'includes': includes,
            'bytes': sum(p.stat().st_size for p in target.rglob('*') if p.is_file())}


def load_input(entry: dict) -> Path:
    root = Path(entry['path'])
    if not root.is_dir():
        raise FileNotFoundError(f'restore build input from archive: {root}')
    if tree_hash(root) != entry['tree_sha256']:
        raise ValueError(f'build input hash mismatch: {root}')
    return root


def input_path(name: str, *, verify: bool = False) -> Path:
    data = json.loads(INDEX.read_text())
    if data['schema_version'] != 'scenario-forge-build-inputs/v1':
        raise ValueError('unsupported build inputs index')
    entry = data['inputs'][name]
    return load_input(entry) if verify else Path(entry['path'])


def verify_registered_input(path: Path) -> None:
    """Check locked inputs at use time; explicit caller-supplied fixtures stay supported."""
    resolved = path.resolve()
    for entry in json.loads(INDEX.read_text())['inputs'].values():
        root = Path(entry['path']).resolve()
        if resolved == root or root in resolved.parents:
            load_input(entry)
            return

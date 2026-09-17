"""Clone the latest 120 Hz scene and add grain linear damping to calm rest jitter."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

GRAIN_COUNT = 10240
DEFAULT_LINEAR_DAMPING = 1.0
UNDAMPED_BLOCK = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:maxLinearVelocity = 0.15\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)
DAMPED_BLOCK = (
    '        float physxRigidBody:linearDamping = 1\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:maxLinearVelocity = 0.15\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)


def patch_scene_config(cfg, linear_damping=DEFAULT_LINEAR_DAMPING):
    cfg = dict(cfg)
    if linear_damping <= 0:
        raise ValueError('r5.8 must set a positive grain linearDamping')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.8'
    cfg['status'] = 'candidate'
    cfg['grain_linear_damping'] = float(linear_damping)
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_grain_linear_damping(text):
    found = text.count(UNDAMPED_BLOCK)
    if found != GRAIN_COUNT:
        raise ValueError(f'Expected {GRAIN_COUNT} undamped powder grains, found {found}')
    return text.replace(UNDAMPED_BLOCK, DAMPED_BLOCK)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--linear-damping', type=float, default=DEFAULT_LINEAR_DAMPING)
    a = p.parse_args()
    if a.linear_damping != DEFAULT_LINEAR_DAMPING:
        raise ValueError('r5.8 authored USDA patch only supports linearDamping=1')
    source = a.source.resolve()
    out = a.out.resolve()
    if out.exists():
        raise ValueError('Refusing to overwrite '+str(out))
    out.mkdir(parents=True)
    for path in source.iterdir():
        if path.name in SKIP or path.name.endswith('.zip') or path.name.endswith('.sha256'):
            continue
        dest = out/path.name
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
    cfg_path = out/'scene_config.json'
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.linear_damping)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    scene = out/'scene.usda'
    scene.write_text(patch_grain_linear_damping(scene.read_text()))
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'grain_linear_damping':cfg['grain_linear_damping']}))


if __name__ == '__main__':
    main()

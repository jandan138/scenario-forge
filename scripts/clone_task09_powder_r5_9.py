"""Clone the latest 120 Hz scene and allow powder grains to sleep at rest."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

GRAIN_COUNT = 10240
DEFAULT_SLEEP_THRESHOLD = 5e-5
DEFAULT_STABILIZATION_THRESHOLD = 1e-5
AWAKE_BLOCK = (
    '        float physxRigidBody:sleepThreshold = 0\n'
    '        int physxRigidBody:solverPositionIterationCount = 32\n'
    '        int physxRigidBody:solverVelocityIterationCount = 4\n'
    '        float physxRigidBody:stabilizationThreshold = 0\n'
)
SLEEPING_BLOCK = (
    '        float physxRigidBody:sleepThreshold = 0.00005\n'
    '        int physxRigidBody:solverPositionIterationCount = 32\n'
    '        int physxRigidBody:solverVelocityIterationCount = 4\n'
    '        float physxRigidBody:stabilizationThreshold = 0.00001\n'
)


def patch_scene_config(cfg, sleep_threshold=DEFAULT_SLEEP_THRESHOLD,
                       stabilization_threshold=DEFAULT_STABILIZATION_THRESHOLD):
    cfg = dict(cfg)
    if sleep_threshold <= 0 or stabilization_threshold <= 0:
        raise ValueError('r5.9 must set positive grain sleep and stabilization thresholds')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.9'
    cfg['status'] = 'candidate'
    cfg['grain_sleep_threshold'] = float(sleep_threshold)
    cfg['grain_stabilization_threshold'] = float(stabilization_threshold)
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_grain_sleep(text):
    found = text.count(AWAKE_BLOCK)
    if found != GRAIN_COUNT:
        raise ValueError(f'Expected {GRAIN_COUNT} never-sleeping powder grains, found {found}')
    return text.replace(AWAKE_BLOCK, SLEEPING_BLOCK)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()))
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    scene = out/'scene.usda'
    scene.write_text(patch_grain_sleep(scene.read_text()))
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'grain_sleep_threshold':cfg['grain_sleep_threshold'],
                      'grain_stabilization_threshold':cfg['grain_stabilization_threshold']}))


if __name__ == '__main__':
    main()

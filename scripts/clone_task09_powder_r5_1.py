"""Clone the r4 near-full powder scene, lock 120 Hz, and cap grain velocity for r5.1."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP, patch_physics_hz

GRAIN_COUNT = 10240
MAX_LINEAR_VELOCITY = 0.15
MAX_DEPENETRATION_VELOCITY = 0.2
GRAIN_BLOCK = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)
CAPPED_BLOCK = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:maxLinearVelocity = 0.15\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)


def patch_scene_config(cfg):
    cfg = dict(cfg)
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.1'
    cfg['status'] = 'candidate'
    cfg['grain_max_linear_velocity_m_s'] = MAX_LINEAR_VELOCITY
    cfg['grain_max_depenetration_velocity_m_s'] = MAX_DEPENETRATION_VELOCITY
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_grain_velocity_caps(text):
    found = text.count(GRAIN_BLOCK)
    if found != GRAIN_COUNT:
        raise ValueError(f'Expected {GRAIN_COUNT} uncapped powder grains, found {found}')
    return text.replace(GRAIN_BLOCK, CAPPED_BLOCK)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
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
            shutil.copytree(path,dest)
        else:
            shutil.copy2(path,dest)
    cfg_path = out/'scene_config.json'
    cfg = patch_scene_config(json.loads(cfg_path.read_text()))
    cfg_path.write_text(json.dumps(cfg,indent=2)+'\n')
    scene = out/'scene.usda'
    text = patch_physics_hz(scene.read_text(), 240, 120)
    scene.write_text(patch_grain_velocity_caps(text))
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'grain_max_linear_velocity_m_s':cfg['grain_max_linear_velocity_m_s'],
                      'grain_max_depenetration_velocity_m_s':cfg['grain_max_depenetration_velocity_m_s']}))


if __name__=='__main__':
    main()

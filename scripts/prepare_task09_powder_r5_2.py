"""Prepare a 120 Hz r5.2 gravity column from the r4 bottle and r3 base scene."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import patch_physics_hz

DEFAULT_BASE = Path('outputs/task09_powder_bottle_r3_20260910/handoff/task09_powder_bottle_r3')
DEFAULT_MODEL = Path('outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4/source_bottle/geometry.json')
DEFAULT_PRODUCER = Path('/cpfs/user/zhuzihou/dev/ConvertAsset/scripts/build_full_powder_scene.py')
GRAIN_COLLISION_SOURCE = (
    '            float physxCollision:contactOffset = 0.00003\n'
    '            float physxCollision:restOffset = 0\n'
)
DEFAULT_CONTACT_OFFSET = 0.00015
DEFAULT_REST_OFFSET = 0.00005


def format_offset(value):
    if value == 0:
        return '0'
    return f'{value:.8f}'.rstrip('0').rstrip('.')


def collision_block(contact_offset_m, rest_offset_m):
    return (
        f'            float physxCollision:contactOffset = {format_offset(contact_offset_m)}\n'
        f'            float physxCollision:restOffset = {format_offset(rest_offset_m)}\n'
    )


def patch_preparation_config(cfg, contact_offset_m=DEFAULT_CONTACT_OFFSET, rest_offset_m=DEFAULT_REST_OFFSET):
    cfg = dict(cfg)
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.2'
    cfg['status'] = 'candidate'
    cfg['preparation_only'] = True
    cfg['initial_state'] = 'preparation_gravity_column'
    cfg['grain_contact_offset_m'] = contact_offset_m
    cfg['grain_rest_offset_m'] = rest_offset_m
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_grain_collision_offsets(text, count, contact_offset_m, rest_offset_m):
    found = text.count(GRAIN_COLLISION_SOURCE)
    if found != count:
        raise ValueError(f'Expected {count} powder-grain collision blocks, found {found}')
    return text.replace(GRAIN_COLLISION_SOURCE, collision_block(contact_offset_m, rest_offset_m))


def apply_r5_2_patches(root, contact_offset_m=DEFAULT_CONTACT_OFFSET, rest_offset_m=DEFAULT_REST_OFFSET):
    cfg_path = root/'scene_config.json'
    cfg = patch_preparation_config(json.loads(cfg_path.read_text()), contact_offset_m, rest_offset_m)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    scene = root/'scene.usda'
    text = patch_physics_hz(scene.read_text(), 240, 120)
    scene.write_text(patch_grain_collision_offsets(text, cfg['count'], contact_offset_m, rest_offset_m))
    return cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=DEFAULT_BASE)
    p.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    p.add_argument('--producer', type=Path, default=DEFAULT_PRODUCER)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--count', type=int, default=10240)
    p.add_argument('--contact-offset', type=float, default=DEFAULT_CONTACT_OFFSET)
    p.add_argument('--rest-offset', type=float, default=DEFAULT_REST_OFFSET)
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists():
        raise ValueError('Refusing to overwrite '+str(out))
    subprocess.run(
        [sys.executable, str(a.producer.resolve()), 'prepare',
         '--base', str(a.base.resolve()), '--model', str(a.model.resolve()),
         '--out', str(out), '--count', str(a.count)],
        check=True)
    cfg = apply_r5_2_patches(out, a.contact_offset, a.rest_offset)
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'count':cfg['count'],'grain_contact_offset_m':cfg['grain_contact_offset_m'],
                      'grain_rest_offset_m':cfg['grain_rest_offset_m']}))


if __name__=='__main__':
    main()

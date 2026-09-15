"""Clone the r5.2 120 Hz near-full scene and thicken bottle-wall colliders."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from pxr import Usd, UsdGeom

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

WALL_COUNT = 256
DEFAULT_WALL_CONTACT_M = 0.001
DEFAULT_WALL_REST_M = 0.0002


def patch_scene_config(cfg, wall_contact_m=DEFAULT_WALL_CONTACT_M, wall_rest_m=DEFAULT_WALL_REST_M):
    cfg = dict(cfg)
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.3'
    cfg['status'] = 'candidate'
    cfg['wall_contact_offset_m'] = wall_contact_m
    cfg['wall_rest_offset_m'] = wall_rest_m
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_wall_collision_offsets(scene_path, count, contact_offset_m, rest_offset_m):
    stage = Usd.Stage.Open(str(scene_path))
    bottle = stage.GetPrimAtPath('/World/obj_powder_bottle')
    if not bottle:
        raise ValueError('Missing /World/obj_powder_bottle')
    found = 0
    for prim in Usd.PrimRange(bottle):
        if not prim.IsA(UsdGeom.Mesh) or not prim.GetName().startswith('Wall_'):
            continue
        prim.GetAttribute('physxCollision:contactOffset').Set(float(contact_offset_m))
        prim.GetAttribute('physxCollision:restOffset').Set(float(rest_offset_m))
        found += 1
    if found != count:
        raise ValueError(f'Expected {count} Wall_* collision meshes, found {found}')
    stage.GetRootLayer().Save()
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--wall-contact-offset', type=float, default=DEFAULT_WALL_CONTACT_M)
    p.add_argument('--wall-rest-offset', type=float, default=DEFAULT_WALL_REST_M)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.wall_contact_offset, a.wall_rest_offset)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    patch_wall_collision_offsets(out/'scene.usda', WALL_COUNT, a.wall_contact_offset, a.wall_rest_offset)
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'wall_contact_offset_m':cfg['wall_contact_offset_m'],
                      'wall_rest_offset_m':cfg['wall_rest_offset_m']}))


if __name__ == '__main__':
    main()

"""Clone the r5.3 120 Hz scene and thicken insert colliders to stop delayed slab leaks."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from pxr import Usd, UsdGeom

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

INSERT_COUNT = 32
DEFAULT_INSERT_CONTACT_M = 0.003
DEFAULT_INSERT_REST_M = 0.0006


def patch_scene_config(cfg, insert_contact_m=DEFAULT_INSERT_CONTACT_M, insert_rest_m=DEFAULT_INSERT_REST_M):
    cfg = dict(cfg)
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.4'
    cfg['status'] = 'candidate'
    cfg['insert_contact_offset_m'] = insert_contact_m
    cfg['insert_rest_offset_m'] = insert_rest_m
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_insert_collision_offsets(scene_path, count, contact_offset_m, rest_offset_m):
    stage = Usd.Stage.Open(str(scene_path))
    bottle = stage.GetPrimAtPath('/World/obj_powder_bottle')
    if not bottle:
        raise ValueError('Missing /World/obj_powder_bottle')
    found = 0
    for prim in Usd.PrimRange(bottle):
        if not prim.IsA(UsdGeom.Mesh) or not prim.GetName().startswith('Insert_'):
            continue
        prim.GetAttribute('physxCollision:contactOffset').Set(float(contact_offset_m))
        prim.GetAttribute('physxCollision:restOffset').Set(float(rest_offset_m))
        found += 1
    if found != count:
        raise ValueError(f'Expected {count} Insert_* collision meshes, found {found}')
    stage.GetRootLayer().Save()
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--insert-contact-offset', type=float, default=DEFAULT_INSERT_CONTACT_M)
    p.add_argument('--insert-rest-offset', type=float, default=DEFAULT_INSERT_REST_M)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.insert_contact_offset, a.insert_rest_offset)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    patch_insert_collision_offsets(out/'scene.usda', INSERT_COUNT, a.insert_contact_offset, a.insert_rest_offset)
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'insert_contact_offset_m':cfg['insert_contact_offset_m'],
                      'insert_rest_offset_m':cfg['insert_rest_offset_m']}))


if __name__ == '__main__':
    main()

"""Clone the latest 120 Hz scene and raise friction only on the spoon bowl."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from pxr import Usd, UsdPhysics, UsdShade

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

SPOON_BOWL_MESH_PATH = (
    '/World/obj_sampling_spoon/GeometryOffset/Normalize/Axis/CategoryOrient/Model/'
    'textured_mesh/textured_mesh'
)
SPOON_BOWL_MATERIAL_PATH = '/World/obj_sampling_spoon/BowlContact'
SPOON_GRIP_MATERIAL_PATH = '/World/obj_sampling_spoon/PhysicsMaterial'
POWDER_CONTACT_PATH = '/World/PowderLooks/Contact'
CONTACT_STATIC_FRICTION = 0.65
CONTACT_DYNAMIC_FRICTION = 0.5
DEFAULT_SPOON_STATIC_FRICTION = 0.9
DEFAULT_SPOON_DYNAMIC_FRICTION = 0.7


def patch_scene_config(cfg, static_friction=DEFAULT_SPOON_STATIC_FRICTION,
                       dynamic_friction=DEFAULT_SPOON_DYNAMIC_FRICTION):
    cfg = dict(cfg)
    if static_friction <= CONTACT_STATIC_FRICTION or dynamic_friction <= CONTACT_DYNAMIC_FRICTION:
        raise ValueError('r5.6 must raise spoon-bowl friction above shared PowderLooks/Contact 0.65 / 0.5')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.6'
    cfg['status'] = 'candidate'
    cfg['spoon_static_friction'] = float(static_friction)
    cfg['spoon_dynamic_friction'] = float(dynamic_friction)
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_spoon_bowl_friction(scene_path, static_friction, dynamic_friction):
    stage = Usd.Stage.Open(str(scene_path))
    mesh = stage.GetPrimAtPath(SPOON_BOWL_MESH_PATH)
    if not mesh:
        raise ValueError('Missing '+SPOON_BOWL_MESH_PATH)
    material = UsdShade.Material.Define(stage, SPOON_BOWL_MATERIAL_PATH)
    api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    api.CreateStaticFrictionAttr(float(static_friction))
    api.CreateDynamicFrictionAttr(float(dynamic_friction))
    bind = mesh.GetRelationship('material:binding:physics')
    if not bind:
        bind = mesh.CreateRelationship('material:binding:physics')
    bind.SetTargets([SPOON_BOWL_MATERIAL_PATH])
    stage.GetRootLayer().Save()
    return SPOON_BOWL_MATERIAL_PATH


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--static-friction', type=float, default=DEFAULT_SPOON_STATIC_FRICTION)
    p.add_argument('--dynamic-friction', type=float, default=DEFAULT_SPOON_DYNAMIC_FRICTION)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.static_friction, a.dynamic_friction)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    patch_spoon_bowl_friction(out/'scene.usda', a.static_friction, a.dynamic_friction)
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'spoon_static_friction':cfg['spoon_static_friction'],
                      'spoon_dynamic_friction':cfg['spoon_dynamic_friction'],
                      'spoon_bowl_material':SPOON_BOWL_MATERIAL_PATH}))


if __name__ == '__main__':
    main()

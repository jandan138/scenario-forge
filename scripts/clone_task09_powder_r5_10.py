"""Clone the latest 120 Hz scene and freeze grains until just before insert."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

DEFAULT_KINEMATIC_FROM_S = 0.5
DEFAULT_KINEMATIC_UNTIL_S = 18.0
INSERT_KEYFRAME_S = 20.0


def hold_grains_kinematic(time_s, until_s, start_s=DEFAULT_KINEMATIC_FROM_S):
    return float(start_s) <= float(time_s) < float(until_s)


def patch_scene_config(cfg, kinematic_until_s=DEFAULT_KINEMATIC_UNTIL_S,
                       kinematic_from_s=DEFAULT_KINEMATIC_FROM_S):
    cfg = dict(cfg)
    if kinematic_from_s < 0 or kinematic_until_s <= kinematic_from_s:
        raise ValueError('r5.10 rest kinematic hold needs 0 <= start < release')
    if kinematic_until_s >= INSERT_KEYFRAME_S + 8:
        raise ValueError('r5.10 rest kinematic hold must end before the slow scoop')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.10'
    cfg['status'] = 'candidate'
    cfg['grain_rest_kinematic_from_s'] = float(kinematic_from_s)
    cfg['grain_rest_kinematic_until_s'] = float(kinematic_until_s)
    cfg.pop('qualified_runtime', None)
    return cfg


def set_grain_ccd(stage, paths, enabled):
    from pxr import Sdf
    with Sdf.ChangeBlock():
        for path in paths:
            stage.GetPrimAtPath(path).GetAttribute('physxRigidBody:enableCCD').Set(bool(enabled))


def set_grain_kinematic(stage, paths, enabled):
    from pxr import Sdf, UsdPhysics
    with Sdf.ChangeBlock():
        for path in paths:
            UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath(path)).CreateKinematicEnabledAttr(bool(enabled))


def apply_grain_kinematic(stage, paths, enabled):
    # USD convenience for tests. Runtime must flush CCD off before kinematic on.
    if enabled:
        set_grain_ccd(stage, paths, False)
        set_grain_kinematic(stage, paths, True)
    else:
        set_grain_kinematic(stage, paths, False)
        set_grain_ccd(stage, paths, True)


def apply_grain_kinematic_runtime(stage, paths, enabled, flush):
    if enabled:
        set_grain_ccd(stage, paths, False)
        flush()
        set_grain_kinematic(stage, paths, True)
        flush()
    else:
        set_grain_kinematic(stage, paths, False)
        flush()
        set_grain_ccd(stage, paths, True)
        flush()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--until', type=float, default=DEFAULT_KINEMATIC_UNTIL_S)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.until)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'grain_rest_kinematic_from_s':cfg['grain_rest_kinematic_from_s'],
                      'grain_rest_kinematic_until_s':cfg['grain_rest_kinematic_until_s']}))


if __name__ == '__main__':
    main()

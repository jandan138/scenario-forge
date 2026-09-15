"""Clone the latest 120 Hz scene and add a short early-lift hold without changing the 50 s timeline."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

DEFAULT_LIFT_EARLY_HOLD_M = 0.006


def patch_scene_config(cfg, lift_early_hold_m=DEFAULT_LIFT_EARLY_HOLD_M):
    cfg = dict(cfg)
    if lift_early_hold_m <= 0:
        raise ValueError('r5.7 must raise the spoon by a positive early-lift hold')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.7'
    cfg['status'] = 'candidate'
    cfg['lift_early_hold_m'] = float(lift_early_hold_m)
    cfg.pop('qualified_runtime', None)
    return cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--lift-early-hold', type=float, default=DEFAULT_LIFT_EARLY_HOLD_M)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.lift_early_hold)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'lift_early_hold_m':cfg['lift_early_hold_m']}))


if __name__ == '__main__':
    main()

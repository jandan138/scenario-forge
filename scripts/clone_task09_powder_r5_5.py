"""Clone the r5.4 120 Hz scene and lower the authored scoop surface for a deeper cut."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP

DEFAULT_SURFACE_TARGET_M = 0.091


def patch_scene_config(cfg, surface_target_m=DEFAULT_SURFACE_TARGET_M):
    cfg = dict(cfg)
    current = float(cfg.get('powder_surface_target_m', 0.095))
    if surface_target_m >= current:
        raise ValueError('r5.5 must lower powder_surface_target_m to deepen the scoop')
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.5'
    cfg['status'] = 'candidate'
    cfg['powder_surface_target_m'] = surface_target_m
    cfg.pop('qualified_runtime', None)
    return cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--surface-target', type=float, default=DEFAULT_SURFACE_TARGET_M)
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
    cfg = patch_scene_config(json.loads(cfg_path.read_text()), a.surface_target)
    cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz'],
                      'powder_surface_target_m':cfg['powder_surface_target_m']}))


if __name__ == '__main__':
    main()

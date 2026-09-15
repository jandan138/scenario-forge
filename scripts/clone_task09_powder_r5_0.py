"""Clone the r4 near-full powder scene and lock physics at 120 Hz for the r5.0 trial."""
import argparse
import json
from pathlib import Path
import shutil

SKIP = {'evidence','video','recording','package_manifest.json','README.md','objects.json','scripts','source_scripts'}


def patch_scene_config(cfg):
    cfg = dict(cfg)
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r5.0'
    cfg['status'] = 'candidate'
    cfg.pop('qualified_runtime', None)
    return cfg


def patch_physics_hz(text, old_hz, new_hz):
    needle = f'uint physxScene:timeStepsPerSecond = {old_hz}'
    replacement = f'uint physxScene:timeStepsPerSecond = {new_hz}'
    if text.count(needle)!=1:
        raise ValueError('Expected one PhysicsScene timestep declaration')
    return text.replace(needle, replacement, 1)


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
    scene.write_text(patch_physics_hz(scene.read_text(), 240, 120))
    print(json.dumps({'out':str(out),'revision':cfg['revision'],'physics_hz':cfg['physics_hz']}))


if __name__=='__main__':
    main()

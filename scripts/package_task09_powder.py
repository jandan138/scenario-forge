"""Package the qualified 4.5 task09 powder scene and its exact-content evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.task09_powder_evidence import NEAR_FULL_REVISIONS, validate_report

COMPACT_REVISIONS = ('r2','r3','r4','r5.0','r5.1','r5.2','r5.3','r5.4','r5.5','r5.6','r5.7')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    for mode in ('settle','scoop','calibration'):
        p.add_argument('--'+mode,type=Path)
    p.add_argument('--video',type=Path)
    p.add_argument('--producer-scripts',type=Path,required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if (out/'scene.usda').exists() and sha(out/'scene.usda')!=sha(a.candidate/'scene.usda'):
        raise ValueError('Refusing to replace another scene')
    shutil.copytree(a.candidate,out,dirs_exist_ok=True)
    cfg = json.loads((out/'scene_config.json').read_text())
    compact = 'inner_profile' in cfg
    revision = cfg.get('revision','r3') if compact else 'r2'
    if revision not in COMPACT_REVISIONS:
        raise ValueError('Unsupported task09 revision')
    source_root = Path(__file__).resolve().parents[1]
    scripts = out/'scripts'
    scripts.mkdir(exist_ok=True)
    for name in ('balance_force_state.py','balance_force_runtime.py','powder_balance_runtime.py',
                 'powder_weighing_protocol.py','task09_powder_runtime.py','task09_powder_protocol.py',
                 'validate_task09_powder.py','render_task09_powder.py','task09_powder_evidence.py'):
        shutil.copy2(source_root/'scripts'/name,scripts/name)
    (scripts/'__init__.py').write_text('')
    if compact:
        shutil.copy2(source_root/'scripts/compact_powder_protocol.py',scripts/'compact_powder_protocol.py')
    (out/'source_scripts').mkdir(exist_ok=True)
    for name in ('build_task09_powder_bottle.py','model_task09_weighing_boat.py'):
        shutil.copy2(a.producer_scripts/name,out/'source_scripts'/name)
    if compact:
        for name in ('build_compact_powder_scene.py','model_compact_powder_bottle.py'):
            shutil.copy2(a.producer_scripts/name,out/'source_scripts'/name)
    if revision in NEAR_FULL_REVISIONS:
        for name in ('build_full_powder_scene.py','model_full_powder_bottle.py'):
            shutil.copy2(a.producer_scripts/name,out/'source_scripts'/name)
    guide = source_root/f'docs/operations/task09-powder-bottle-{revision}-guide.md'
    if guide.exists():
        shutil.copy2(guide,out/'README.md')
    manifest = dict(package_id=f'task09_powder_bottle_{revision}',status='candidate',runtime='Isaac Sim 4.5.0',
                    scene_sha256=sha(out/'scene.usda'),powder_count=cfg['count'],
                    original_large_samples_preserved=True,robot_grasp_verified=False,
                    measurement_source='pan_contact_force',display_resolution_g=cfg['display_resolution_g'])
    if all((a.settle,a.scoop,a.calibration,a.video)):
        (out/'evidence').mkdir(exist_ok=True)
        for mode in ('settle','scoop','calibration'):
            path = getattr(a,mode)
            report = json.loads((path/'report.json').read_text())
            validate_report(report,manifest['scene_sha256'],mode,cfg)
            shutil.copy2(path/'report.json',out/'evidence'/f'{mode}.json')
            if path.with_suffix('.log').exists():
                shutil.copy2(path.with_suffix('.log'),out/'evidence'/f'{mode}.log')
        (out/'recording').mkdir(exist_ok=True)
        shutil.copy2(a.scoop/'states.npz',out/'recording/states.npz')
        shutil.copytree(a.video,out/'video',dirs_exist_ok=True)
        for view in ('overview','close'):
            render = json.loads((out/'video'/f'{view}_render.json').read_text())
            if (render.get('status')!='rendered' or render.get('entry_sha256')!=manifest['scene_sha256']
                    or render.get('states_sha256')!=sha(out/'recording/states.npz')
                    or not (out/'video'/f'{view}.mp4').is_file()):
                raise ValueError('Stale or missing '+view+' video')
        review = json.loads((out/'video/visual_review.json').read_text())
        if review.get('blocking_visual_failures') or review.get('status') not in ('PASS','WARN'):
            raise ValueError('Visual review unresolved')
        from pxr import UsdUtils,Usd,UsdPhysics
        layers,assets,missing = UsdUtils.ComputeAllDependencies(str(out/'scene.usda'))
        if missing or any(not Path(path).resolve().is_relative_to(out) for path in [*(x.realPath for x in layers),*assets]):
            raise ValueError('Scene dependency closure failed')
        stage = Usd.Stage.Open(str(out/'scene.usda'))
        objects = []
        for prim in stage.GetPrimAtPath('/World').GetChildren():
            if prim.GetName().startswith('obj_'):
                objects.append(dict(path=str(prim.GetPath()),type=prim.GetTypeName(),
                                    rigid_body=prim.HasAPI(UsdPhysics.RigidBodyAPI),
                                    mass_kg=prim.GetAttribute('physics:mass').Get()))
        (out/'objects.json').write_text(json.dumps(objects,indent=2))
        manifest.update(status='scene_fixture_verified',object_count=len(objects),
                        dependency_closure={'layers':len(layers),'assets':len(assets),'unresolved':[]},
                        visual_review=review['status'])
        cfg['status'] = 'scene_fixture_verified'
        cfg['qualified_runtime'] = 'Isaac Sim 4.5.0'
        if 'boat_collision_signed_volume_m3' in cfg:
            cfg['original_boat_reference_shell_volume_m3'] = cfg.pop('boat_collision_signed_volume_m3')
        (out/'scene_config.json').write_text(json.dumps(cfg,indent=2))
    manifest['files'] = {str(path.relative_to(out)):sha(path) for path in sorted(out.rglob('*'))
                         if path.is_file() and path.name!='package_manifest.json' and '__pycache__' not in path.parts}
    (out/'package_manifest.json').write_text(json.dumps(manifest,indent=2))
    if manifest['status']=='scene_fixture_verified':
        archive = out.with_suffix('.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(out.rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    zipped.write(path,str(Path(out.name)/path.relative_to(out)))
        with zipfile.ZipFile(archive) as zipped:
            assert zipped.testzip() is None
        print(json.dumps({'zip':str(archive),'sha256':sha(archive),'files':len(manifest['files'])}))
    else:
        print('STAGED',out)


if __name__=='__main__':
    main()

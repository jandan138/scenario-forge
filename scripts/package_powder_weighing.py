"""Stage/finalize the bounded powder demonstration with hash-bound evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--scoop',type=Path)
    parser.add_argument('--calibration',type=Path)
    parser.add_argument('--body-contact',type=Path)
    parser.add_argument('--videos',type=Path)
    parser.add_argument('--blender-source',type=Path)
    parser.add_argument('--producer-scripts',type=Path)
    parser.add_argument('--template',type=Path)
    parser.add_argument('--seed-evidence',type=Path,action='append',default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if (out/'scene.usda').exists() and sha(out/'scene.usda') != sha(args.fixture/'scene.usda'):
        raise ValueError('Refusing to replace a different staged scene')
    shutil.copytree(args.fixture,out,dirs_exist_ok=True)
    scripts = out/'scripts'
    scripts.mkdir(exist_ok=True)
    for name in ('validate_powder_weighing.py','render_powder_recording.py','powder_weighing_protocol.py',
                 'balance_force_state.py','balance_force_runtime.py','powder_balance_runtime.py'):
        shutil.copy2(root/'scripts'/name,scripts/name)
    (scripts/'__init__.py').write_text('')
    if args.blender_source:
        (out/'source').mkdir(exist_ok=True)
        shutil.copy2(args.blender_source,out/'source/powder_tools.blend')
    if args.producer_scripts and args.template:
        target = out/'source/producer_scripts'
        target.mkdir(parents=True,exist_ok=True)
        for name in ('build_powder_fixture.py','build_powder_balance_fixture.py','powder_tools_blender.py'):
            shutil.copy2(args.producer_scripts/name,target/name)
        target = out/'source/reference_generator'
        target.mkdir(exist_ok=True)
        for name in ('build_scene.py','config.json','provenance.json','README_复现说明.md'):
            shutil.copy2(args.template/name,target/name)
    guide = root/'docs/operations/powder-weighing-r1-guide.md'
    if guide.exists():
        shutil.copy2(guide,out/'README.md')
    manifest = dict(package_id='powder_weighing_r1',status='candidate',runtime='Isaac Sim 4.5.0',
                    scene_sha256=sha(out/'scene.usda'),robot_grasp_verified=False,
                    measurement_source='pan_contact_force',display_resolution_g=.1,
                    protocol='prescribed kinematic scoop with fully dynamic grains and receiver')
    if args.scoop and args.calibration and args.body_contact and args.videos:
        (out/'evidence').mkdir(exist_ok=True)
        for name,path in [('scoop',args.scoop),('calibration',args.calibration),('body_contact',args.body_contact)]:
            report = json.loads((path/'report.json').read_text())
            if report['status'] != 'passed' or not all(report['checks'].values()):
                raise ValueError('Unqualified '+name)
            if report['scene_sha256'] != manifest['scene_sha256']:
                raise ValueError('Evidence scene mismatch: '+name)
            shutil.copy2(path/'report.json',out/'evidence'/f'{name}.json')
            log = path.with_suffix('.log')
            if log.exists():
                shutil.copy2(log,out/'evidence'/f'{name}.log')
        for path in args.seed_evidence:
            report = json.loads((path/'report.json').read_text())
            if report['status'] != 'passed' or not all(report['checks'].values()):
                raise ValueError('Unqualified seed '+str(path))
            shutil.copy2(path/'report.json',out/'evidence'/f'{path.name}.json')
            if path.with_suffix('.log').exists():
                shutil.copy2(path.with_suffix('.log'),out/'evidence'/f'{path.name}.log')
        (out/'recording').mkdir(exist_ok=True)
        shutil.copy2(args.scoop/'states.npz',out/'recording/states.npz')
        shutil.copytree(args.videos,out/'video',dirs_exist_ok=True)
        for view in ('close','overview'):
            report = json.loads((out/'video'/f'{view}_render.json').read_text())
            if report['status'] != 'rendered' or not (out/'video'/f'{view}.mp4').is_file():
                raise ValueError('Missing rendered video '+view)
            if (report.get('scene_sha256') != manifest['scene_sha256']
                    or report.get('states_sha256') != sha(out/'recording/states.npz')):
                raise ValueError('Video evidence identity mismatch: '+view)
        review = json.loads((out/'video/visual_review.json').read_text())
        if review['blocking_visual_failures'] or review['status'] != 'passed_with_caveats':
            raise ValueError('Unresolved visual review')
        manifest['visual_review'] = review['combined_verdict']
        manifest['status'] = 'scene_fixture_verified'
        metadata = json.loads((out/'scene.json').read_text())
        metadata['validation'] = 'scene_fixture_verified; see package_manifest.json and evidence/'
        (out/'scene.json').write_text(json.dumps(metadata,indent=2))
    manifest['files'] = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                         if p.is_file() and p.name != 'package_manifest.json'}
    (out/'package_manifest.json').write_text(json.dumps(manifest,indent=2))
    if manifest['status'] == 'scene_fixture_verified':
        archive = Path(shutil.make_archive(str(out),'zip',out.parent,out.name))
        with zipfile.ZipFile(archive) as z:
            bad = z.testzip()
            if bad:
                raise ValueError('ZIP CRC failed '+bad)
        print(json.dumps({'zip':str(archive),'sha256':sha(archive),'files':len(manifest['files'])}))
    else:
        print('STAGED',out)


if __name__ == '__main__':
    main()

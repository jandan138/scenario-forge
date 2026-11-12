"""Freeze native120 task10 VR evidence, docs and a portable ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from task10_native120_evidence import validate_report

ROOT=Path(__file__).resolve().parents[1]
CASES=('mounted_full','direct_full','corner_pp','corner_mm','corner_mp','seeded_random','direct_play60')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finalize(output,package):
    OUTPUT,PACKAGE=output.resolve(),package.resolve()
    from pxr import UsdUtils
    reports={name:json.loads((OUTPUT/'checks'/name/'report.json').read_text()) for name in CASES}
    inputs=reports[CASES[0]]['input_files_sha256']
    acceptance=json.loads((OUTPUT/'acceptance_matrix.json').read_text())
    matrix=acceptance['cases']
    for name,r in reports.items():
        if r['offset_m']!=matrix[name]['offset_m']:
            raise ValueError('Wrong randomized offset: '+name)
    for name,r in reports.items():
        full=name in ('mounted_full','direct_full')
        validate_report(r,inputs,sha(ROOT/'scripts/validate_task10_native120.py'),
                        sha(ROOT/'scripts/task10_clock.py'),full=full,play=name=='direct_play60')
        if full and r.get('motion_protocol')!=acceptance['motion_protocol']:
            raise ValueError('Wrong motion qualification scope: '+name)
        if r['runtime_requested']!='45':
            raise ValueError('VR requires Isaac4.5 evidence')
    if len({r['pid'] for r in reports.values()})!=len(reports):
        raise ValueError('Independent cold starts required')
    if reports['mounted_full']['scope']!='full_task_fixture' or reports['direct_full']['scope']!='full_task_fixture':
        raise ValueError('Direct and mounted full fixtures required')
    if reports['mounted_full']['active_physics_scenes']!=['/World/CollectorPhysics']:
        raise ValueError('Collector physics scene was not validated')
    if reports['mounted_full']['scene_root']!='/World/_scene':
        raise ValueError('Mounted root was not validated')
    if len(reports['mounted_full']['episode_reset_results'])<2:
        raise ValueError('Repeated collection resets required')
    for name,digest in inputs.items():
        if sha(PACKAGE/name)!=digest:
            raise ValueError('Runtime input changed: '+name)
    review=json.loads((OUTPUT/'visual_review.json').read_text())
    if review['status']!='PASS' or review['scene_sha256']!=sha(PACKAGE/'scene.usd'):
        raise ValueError('Matching visual review required')
    render_path=Path(review['render_report'])
    render=json.loads(render_path.read_text())
    if (render.get('status')!='rendered' or render.get('particle_replay_exact') is not True
            or render.get('surface_bounds_match') is not True
            or render['candidate_sha256']!=sha(PACKAGE/'manifest.json')
            or render['renderer_sha256']!=sha(ROOT/'scripts/render_task10_vr.py')
            or render['recording_sha256']!=reports['direct_full']['snapshot_recording_sha256']):
        raise ValueError('Replay does not match qualified direct-run snapshots')
    for name,digest in render['frame_files_sha256'].items():
        if reports['direct_full']['snapshot_files_sha256'].get(name)!=digest:
            raise ValueError('Replay frame is not qualified: '+name)
    layers,assets,missing=UsdUtils.ComputeAllDependencies(str(PACKAGE/'scene.usd'))
    if missing or any(not Path(p.realPath).resolve().is_relative_to(PACKAGE) for p in layers) or any(not Path(p).resolve().is_relative_to(PACKAGE) for p in assets):
        raise ValueError('Unresolved/external dependencies')
    for cache in PACKAGE.rglob('__pycache__'):
        shutil.rmtree(cache)
    evidence=PACKAGE/'evidence'
    evidence.mkdir(exist_ok=True)
    for name in CASES:
        shutil.copytree(OUTPUT/'checks'/name,evidence/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('mounted.usda'))
    shutil.copytree(OUTPUT/'validator_sources',evidence/'validator_sources',dirs_exist_ok=True)
    tools=evidence/'tools'
    tools.mkdir(exist_ok=True)
    for name in ('validate_task10_native120.py','task10_clock.py','task10_native120_evidence.py','task10_pbd_geometry.py','build_task10_vr.py','render_task10_vr.py'):
        shutil.copy2(ROOT/'scripts'/name,tools/name)
    images=PACKAGE/'preview'
    images.mkdir(exist_ok=True)
    for row in review['images']:
        path=Path(row['path'])
        if row['verdict']!='PASS' or sha(path)!=row['sha256']:
            raise ValueError('Stale visual image')
        shutil.copy2(path,images/path.name)
    shutil.copy2(OUTPUT/'visual_review.json',evidence/'visual_review.json')
    shutil.copy2(render_path,evidence/'render_report.json')
    shutil.copy2(OUTPUT/'relocation.json',evidence/'relocation.json')
    shutil.copy2(OUTPUT/'source_preservation.json',evidence/'source_preservation.json')
    shutil.copy2(OUTPUT/'acceptance_matrix.json',evidence/'acceptance_matrix.json')
    shutil.copy2(OUTPUT/'make_check.log',evidence/'make_check.log')
    readme=(ROOT/'docs/operations/task10-real-liquid-vr-120hz-guide.md').read_text()
    (PACKAGE/'README.md').write_text(readme.replace('../records/2026-10-10-task10-real-liquid-120hz.md','evidence/task_record.md'))
    shutil.copy2(ROOT/'docs/records/2026-10-10-task10-real-liquid-120hz.md',evidence/'task_record.md')
    delivery={'status':'scene_integration_verified','runtime':'Isaac Sim4.5','scene_sha256':sha(PACKAGE/'scene.usd'),
              'episode_api_sha256':sha(PACKAGE/'task10_vr_episode.py'),'runtime_inputs':inputs,
              'motion_protocol':acceptance['motion_protocol'],
              'runs':{name:{k:r[k] for k in ('pid','scope','scene_root','offset_m','checks','wall_seconds','simulated_seconds','physics_time_ratio','actual_step_dt_evidence','step_mode')} for name,r in reports.items()},
              'limits':['No actual headset or VR collector plugin run.','Collector must call prepare_episode after layout randomization and reset_episode after Stop.','Identity mount; localXY+-1cm/yaw0 only.','Qualified motion requires2simulationseconds settle after wobble before return; arbitrary hand motion is not qualified.','Timing includes cold start, per-particle QA and rendering; not a headset-frame-rate measurement.']}
    (evidence/'delivery.json').write_text(json.dumps(delivery,indent=2))
    archive=PACKAGE.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PACKAGE.rglob('*')):
            if p.is_file():
                z.write(p,Path(PACKAGE.name)/p.relative_to(PACKAGE))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError('ZIP CRC failed')
    receipt={'package':str(PACKAGE),'scene':str(PACKAGE/'scene.usd'),'zip':str(archive),'zip_sha256':sha(archive),
             'scene_sha256':sha(PACKAGE/'scene.usd'),'episode_api_sha256':sha(PACKAGE/'task10_vr_episode.py')}
    (OUTPUT/'handoff/delivery_receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--package',type=Path,required=True)
    args=parser.parse_args()
    finalize(args.output,args.package)

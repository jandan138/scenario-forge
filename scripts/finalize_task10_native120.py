"""Promote task10 r2 only with native120 dual-runtime and matching visual evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

import yaml
from task10_native120_evidence import CHECKS, validate_reports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}



def finalize(package, reports, play_reports, render_dir, recording, review):
    from scenario_forge.package import validate_package
    from pxr import UsdUtils
    package = package.resolve()
    composed = package/'assets/composed'
    rows = [json.loads(p.read_text()) for p in reports]
    inputs = inventory(composed)
    validate_reports(rows,inputs,sha(ROOT/'scripts/validate_task10_native120.py'),sha(ROOT/'scripts/task10_clock.py'))
    play_rows=[json.loads(p.read_text()) for p in play_reports]
    validate_reports(play_rows,inputs,sha(ROOT/'scripts/validate_task10_native120.py'),sha(ROOT/'scripts/task10_clock.py'),full=False,play=True)
    render = json.loads((render_dir/'render_report.json').read_text())
    visual = json.loads(review.read_text())
    candidate_sha = sha(composed/'manifest.json')
    if (render.get('status')!='rendered' or render.get('particle_replay_exact') is not True or render.get('surface_bounds_match') is not True
            or render.get('kind')!='recorded_particle_state_replay'
            or render.get('candidate_sha256')!=candidate_sha
            or render.get('recording_sha256')!=sha(recording)
            or render.get('renderer_sha256')!=sha(ROOT/'scripts/render_task10_pbd.py')
            or visual.get('status')!='PASS' or visual.get('candidate_sha256')!=candidate_sha):
        raise ValueError('Visual evidence is missing, failed, or stale')
    video = render_dir/'task10_real_liquid_demo.mp4'
    if not video.is_file() or not visual.get('video_decode_pass') or visual.get('video_sha256')!=sha(video):
        raise ValueError('Reviewed and decoded video required')
    dependencies = {}
    for entry in ('main.usda','isaac45.usda','demo41.usda','demo45.usda'):
        layers,assets,missing = UsdUtils.ComputeAllDependencies(str(package/'scene'/entry))
        paths = [Path(p.realPath) for p in layers if p.realPath]+[Path(p) for p in assets]
        if missing or any(not p.resolve().is_relative_to(package) for p in paths):
            raise ValueError('Package has unresolved or external dependencies')
        dependencies[entry] = {'unresolved':[],'layers':len(layers),'assets':len(assets)}
    evidence = package/'evidence'
    for path,row in zip(reports+play_reports,rows+play_rows):
        dest = evidence/f'runtime{row["runtime_requested"]}_{row["pid"]}'
        dest.mkdir(exist_ok=True)
        for name in ('report.json','telemetry.jsonl','cavity_trace.json','cavity_violations.json'):
            source = path.parent/name
            if source.exists():
                shutil.copy2(source,dest/name)
    media = package/'media'
    media.mkdir(exist_ok=True)
    shutil.copy2(video,media/video.name)
    for item in visual['images']:
        path = Path(item['path'])
        if item.get('verdict')!='PASS' or item.get('sha256')!=sha(path):
            raise ValueError('Reviewed image is stale or failed')
        shutil.copy2(path,media/path.name)
    shutil.copy2(review,evidence/'visual_review.json')
    shutil.copy2(render_dir/'render_report.json',evidence/'render_report.json')
    # Raw particle frames are a separate, hash-bound evidence artifact. They
    # are not runtime dependencies and do not inflate the portable scene ZIP.
    record_files = inventory(recording.parent/'frames')
    frame_total = len(json.loads(recording.read_text())['frames'])
    frame_step = render.get('frame_step',1)
    if frame_step not in (1,2) or abs(render.get('fps',0)-30/frame_step)>1e-9:
        raise ValueError('Unsupported replay sampling or playback rate')
    selected_files = {f'{i:05d}.npz':record_files[f'{i:05d}.npz'] for i in range(0,frame_total,frame_step)}
    if (render.get('frame_files_sha256')!=selected_files
            or render.get('frame_count')!=len(selected_files)
            or not any(row.get('recording_sha256')==sha(recording)
                       and row.get('recording_frames_sha256')==record_files for row in rows)):
        raise ValueError('Rendered frames do not match a qualified physical recording')
    shutil.copy2(recording,evidence/'recording.json')
    (evidence/'recording_files.json').write_text(json.dumps({
        'source_directory':str(recording.parent/'frames'),'files':record_files},indent=2))
    scripts = package/'scripts'
    scripts.mkdir(exist_ok=True)
    for name in ('task10_pbd_policy.py','task10_pbd_runtime.py','task10_pbd_geometry.py',
                 'validate_task10_native120.py','task10_clock.py','task10_native120_evidence.py','render_task10_pbd.py'):
        shutil.copy2(ROOT/'scripts'/name,scripts/name)
    readme = (ROOT/'docs/operations/task10-real-liquid-120hz-guide.md').read_text()
    (package/'README.md').write_text(readme.replace('../records/2026-10-10-task10-real-liquid-120hz.md','evidence/task_record.md'))
    shutil.copy2(ROOT/'docs/records/2026-10-10-task10-real-liquid-120hz.md',evidence/'task_record.md')
    provenance_path = package/'provenance/provenance.yaml'
    provenance = yaml.safe_load(provenance_path.read_text())
    provenance.update(runtime_status='scene_fixture_verified',runtime_scope='prescribed_no_robot_liquid_fixture')
    provenance_path.write_text(yaml.safe_dump(provenance,sort_keys=False))
    (evidence/'runtime_smoke.yaml').write_text(yaml.safe_dump({'checks':[
        {'runtime':r['runtime_requested'],'pid':r['pid'],'status':'passed',
         'report':f'evidence/runtime{r["runtime_requested"]}_{r["pid"]}/report.json'} for r in rows]},sort_keys=False))
    (evidence/'validation_report.yaml').write_text(yaml.safe_dump({
        'schema_version':'validation-report/v0.2','status':'passed','overall_level':'scene_fixture_verified',
        'scope':'prescribed_no_robot_liquid_fixture','checks':[{'name':k,'status':'passed'} for k in sorted(CHECKS)]},sort_keys=False))
    summary = {'status':'scene_fixture_verified','candidate_sha256':candidate_sha,'runtime_inputs':inputs,
        'runtime_reports':[{'runtime':r['runtime_requested'],'pid':r['pid'],'physics_dt':r['physics_dt'],'step_mode':r['step_mode'],'actual_step_dt_evidence':r['actual_step_dt_evidence']} for r in rows+play_rows],
        'dependency_closure':dependencies,'video':{'path':'media/'+video.name,'sha256':sha(video)},
        'limits':['Controlled conservative source-to-tip transfer, not a resolved valve/capillary solver.',
                  'Prescribed kinematic container motion; particles remain dynamic. No robot qualification.',
                  'Indicator uses original phenomenological curve and received nominal particle volume.',
                  'Stirrer ON is a static display repair; no physical stirring added.']}
    (package/'manifest.json').write_text(json.dumps(summary,indent=2))
    if inventory(composed)!=inputs:
        raise ValueError('Finalization changed runtime inputs')
    result = validate_package(package,require_asset_lock=True)
    if not result.ok:
        raise ValueError(result.messages)
    archive = package.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                z.write(path,Path(package.name)/path.relative_to(package))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError('Archive CRC failed')
    receipt = {'package':str(package),'zip':str(archive),'zip_sha256':sha(archive),
               'candidate_sha256':candidate_sha,'video':str(media/video.name),
               'video_sha256':sha(video),'raw_recording':str(recording),'raw_recording_sha256':sha(recording)}
    (package.parent/'delivery_receipt.json').write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',required=True)
    parser.add_argument('--play-report',type=Path,action='append',required=True)
    parser.add_argument('--render-dir',type=Path,required=True)
    parser.add_argument('--recording',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.package,args.report,args.play_report,args.render_dir,args.recording,args.review),indent=2))

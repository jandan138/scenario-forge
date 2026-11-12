"""Finalize the task09 fixture only with exact-content dual-runtime evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
CHECKS = {'empty', 'empty_boat', 'tare', 'incremental_loads', 'five_complete',
          'unload_zero', 'partial_unloads', 'negative_tare', 'reset', 'hover_not_counted', 'stability'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(root):
    digest = hashlib.sha256()
    for folder in ('assets', 'scene'):
        for p in sorted((root/folder).rglob('*')):
            if p.is_file():
                digest.update(str(p.relative_to(root)).encode())
                digest.update(hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()


def validate_reports(reports, scene_sha, content_sha):
    if Counter(r['runtime_requested'] for r in reports) != {'41': 3, '45': 3}:
        raise ValueError('Three cold starts per version required')
    if len({r['pid'] for r in reports}) != 6:
        raise ValueError('Independent processes required')
    if len({r.get('validator_sha256') for r in reports}) != 1:
        raise ValueError('Validation protocols differ')
    for r in reports:
        if (r.get('status') != 'pass' or r.get('scene_sha256') != scene_sha
                or r.get('runtime_content_sha256') != content_sha or abs(r.get('physics_dt', 0)-1/120) > 1e-12
                or any(r.get('checks', {}).get(k) is not True for k in CHECKS)):
            raise ValueError('Missing, failed or stale runtime evidence')


def finalize(package, reports, render_dir, recording, producer, review, mass_reports):
    from pxr import UsdUtils
    from scenario_forge.package import validate_package
    package = package.resolve()
    rows = [json.loads(p.read_text()) for p in reports]
    content = fingerprint(package)
    scene = sha(package/'assets/composed/scene.usdc')
    validate_reports(rows, scene, content)
    mass_rows = [json.loads(p.read_text()) for p in mass_reports]
    if Counter(r['runtime'] for r in mass_rows) != {'41': 1, '45': 1}:
        raise ValueError('Physical mass audit required for both runtimes')
    for r in mass_rows:
        if r['status'] != 'pass' or r['scene_sha256'] != scene or len(r['bodies']) != 5:
            raise ValueError('Missing or stale physical mass audit')
        for body in r['bodies']:
            if abs(body['physx_kg']-rows[0]['mass_g'][body['path']]/1000) > 1e-8:
                raise ValueError('Configured and actual physical mass differ')
    if rows[0]['validator_sha256'] != sha(ROOT/'scripts/validate_task09_inventory.py'):
        raise ValueError('Validator changed after qualification')
    for r in rows:
        if not str(r['runtime_version'][0]).startswith('4.'+r['runtime_requested'][1]):
            raise ValueError('Unexpected installed runtime version')
    render = json.loads((render_dir/'render_report.json').read_text())
    visual = json.loads(review.read_text())
    if (render.get('status') != 'rendered' or render.get('scene_sha256') != scene
            or render.get('recording_sha256') != sha(recording)
            or render.get('visual_overlay_sha256') is not None
            or visual.get('status') not in ('PASS', 'WARN')
            or visual.get('scene_sha256') != scene):
        raise ValueError('Visual evidence missing or stale')
    closures = {}
    for entry in ('main.usda', 'demo41.usda', 'demo45.usda'):
        layers, assets, missing = UsdUtils.ComputeAllDependencies(str(package/'scene'/entry))
        paths = [*(Path(x.realPath) for x in layers if x.realPath), *(Path(x) for x in assets)]
        if missing or any(not p.resolve().is_relative_to(package) for p in paths):
            raise ValueError('Unresolved or external dependency')
        closures[entry] = {'layers': len(layers), 'assets': len(assets), 'unresolved': []}
    evidence = package/'evidence'
    for p, row in zip(mass_reports, mass_rows):
        shutil.copy2(p, evidence/f'physical_mass{row["runtime"]}.json')
    entries = []
    for path, row in zip(reports, rows):
        destination = evidence/path.parent.name
        destination.mkdir(exist_ok=True)
        for name in ('report.json', 'physics_steps.npz', 'telemetry.jsonl'):
            shutil.copy2(path.parent/name, destination/name)
        entries.append({'path': str((destination/'report.json').relative_to(package)),
                        'sha256': sha(destination/'report.json'), 'runtime': row['runtime_requested'], 'pid': row['pid']})
    media = package/'media'
    media.mkdir(exist_ok=True)
    shutil.copy2(render_dir/'task09_weighing_demo.mp4', media/'task09_weighing_demo.mp4')
    shutil.copy2(recording, evidence/'recording.npz')
    shutil.copy2(render_dir/'render_report.json', evidence/'render_report.json')
    shutil.copy2(review, evidence/'visual_review.json')
    for image in visual['images']:
        source = Path(image['path'])
        if sha(source) != image['sha256'] or image['verdict'] == 'FAIL':
            raise ValueError('Stale or failed reviewed image')
        shutil.copy2(source, media/source.name)
    profile_dir = package/'provenance/producer'
    profile_dir.mkdir(exist_ok=True)
    for relative in ('mass_profiles.json', 'reference_x1.usda', 'source_collider_audit.json',
                     'contact_candidates/contact_profiles.json', 'contact_candidates/contact_1mm.usda',
                     'contact_candidates/grain_sleep.usda'):
        shutil.copy2(producer/relative, profile_dir/Path(relative).name)
    for name in ('validate_task09_inventory.py', 'render_task09_inventory.py', 'inspect_task09_physical_mass.py'):
        shutil.copy2(ROOT/'scripts'/name, package/'scripts'/name)
    (package/'README.md').write_text((ROOT/'docs/operations/task09-supported-weighing-guide.md').read_text())
    shutil.copy2(ROOT/'docs/records/2026-10-08-task09-supported-solid-weighing.md', evidence/'task_record.md')
    summary = {'status': 'scene_fixture_verified', 'scene_sha256': scene, 'runtime_content_sha256': content,
               'measurement_source': 'supported_mass_inventory', 'runtime_evidence': entries,
               'dependency_closure': closures, 'mass_g': rows[0]['mass_g'], 'total_g': rows[0]['total_g'],
               'display_total_g': f"{rows[0]['total_g']:.2f}",
               'stability_metric': rows[0]['stability_velocity_metric'],
               'limitations': ['No robot or scooping qualification.',
                              'Mass inventory readout is not independent force metrology.',
                              'Raw engine velocity residual remains; per-step geometry motion is independently recorded.',
                              'Use PathTracing for the supplied salt material; RayTracedLighting renders dark salt tops.',
                              'Source SDF contacts emit repeated material-face-index warnings; physics completed normally.'],
               'video': {'path': 'media/task09_weighing_demo.mp4', 'sha256': sha(media/'task09_weighing_demo.mp4')}}
    (package/'manifest.json').write_text(json.dumps(summary, indent=2))
    validation = {'schema_version': 'validation-report/v0.2', 'status': 'passed',
                  'overall_level': 'scene_fixture_verified', 'scope': 'prescribed_no_robot_fixture',
                  'checks': [{'name': k, 'status': 'passed'} for k in sorted(CHECKS)]}
    (evidence/'validation_report.yaml').write_text(yaml.safe_dump(validation, sort_keys=False))
    (evidence/'runtime_smoke.yaml').write_text(yaml.safe_dump({'checks': entries}, sort_keys=False))
    if fingerprint(package) != content:
        raise ValueError('Finalization changed validated runtime content')
    check = validate_package(package, require_asset_lock=True)
    if not check.ok:
        raise ValueError(check.messages)
    archive = package.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                z.write(path, str(Path(package.name)/path.relative_to(package)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError('ZIP CRC failure')
    receipt = {'package': str(package), 'zip': str(archive), 'zip_sha256': sha(archive),
               'runtime_content_sha256': content, 'scene_sha256': scene,
               'video': str(media/'task09_weighing_demo.mp4'), 'video_sha256': sha(media/'task09_weighing_demo.mp4')}
    (package.parent/'delivery_receipt.json').write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    parser.add_argument('--render-dir', type=Path, required=True)
    parser.add_argument('--recording', type=Path, required=True)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--mass-report', type=Path, action='append', required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.package, args.report, args.render_dir, args.recording,
                              args.producer, args.review, args.mass_report), indent=2))

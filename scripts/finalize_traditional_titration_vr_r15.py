"""Finalize only r1.5 evidence tied to the exact delivered scene and policy."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from scripts.finalize_traditional_titration_vr_r1 import main as finalize
from scripts.validate_traditional_titration_vr_r1 import evaluate_report


def prepare(root, reports):
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    if len(reports) != 3:
        raise ValueError('exactly three cold starts required')
    for path in reports:
        report = json.loads(path.read_text())
        if (report.get('scene_sha256') != digest or report.get('runtime_version') != '4.5.0'
                or report.get('policy_version') != 'linear_deadzone_v1'
                or evaluate_report(report)['status'] != 'pass'):
            raise ValueError(f'unqualified report: {path}')
    images = root/'evidence/initial_scene'
    render = json.loads((images/'render_manifest_after.json').read_text())
    review = json.loads((images/'visual_review.json').read_text())
    audit = json.loads((root/'evidence/physical_revision_audit.json').read_text())
    for record in (render, review, audit):
        if record.get('scene_sha256') != digest or record.get('status') != 'pass':
            raise ValueError('stale or failed scene evidence')
    if not render.get('linear_policy_color_states') or render.get('runtime_version') != '4.5.0':
        raise ValueError('missing 4.5 color-state renders')
    if {view['state'] for view in render['views']} != {'initial', 'transition', 'endpoint', 'overshoot'}:
        raise ValueError('incomplete color-state renders')
    for view in render['views']:
        if sha256((root/view['path']).read_bytes()).hexdigest() != view['sha256']:
            raise ValueError('render image changed')
    if review.get('render_manifest_sha256') != sha256((images/'render_manifest_after.json').read_bytes()).hexdigest():
        raise ValueError('visual review belongs to different renders')
    shutil.copy2(images/'render_manifest_after.json', images/'render_manifest.json')
    shutil.copy2(images/'after_initial_scene_overview.png', images/'scene_overview.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    prepare(args.root, args.report)
    argv = ['--root', str(args.root)]
    for report in args.report:
        argv.extend(['--report', str(report)])
    raise SystemExit(finalize(argv))

"""Finalize exact r8 clear-bath evidence without rewriting r7."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.fehlings_r6_state import POLICY_VERSION
from scripts.finalize_fehlings_water_bath import main as finalize
from scripts.finalize_fehlings_water_bath_r6 import compose_progression
from scripts.finalize_fehlings_water_bath_r7 import REQUIRED_CHECKS as TUBE_CHECKS

REQUIRED_CHECKS = TUBE_CHECKS
IN_BATH_VIEWS = (
    't3_closeup.png',
    't15_closeup.png',
    't30_closeup.png',
    't3_through_wall.png',
    't15_through_wall.png',
    't30_through_wall.png',
)


def prepare(root, reports):
    """Require three exact passes and in-bath color views of the r8 scene."""
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    manifest = json.loads((root / 'manifest.json').read_text())
    if not str(manifest.get('package_id', '')).endswith('_vr_r8'):
        raise ValueError('r8 package identity required')
    folder = root / 'evidence/initial_scene'
    if not (folder / 'render_manifest.json').is_file():
        raise ValueError('in-bath render evidence required')
    data = [json.loads(path.read_text()) for path in reports]
    if (
        len(data) != 3
        or len({path.resolve() for path in reports}) != 3
        or len({item.get('process_id') for item in data}) != 3
        or any(type(item.get('process_id')) is not int or item['process_id'] <= 0 for item in data)
    ):
        raise ValueError('three independent r8 cold starts required')
    for report in data:
        if (
            report.get('status') != 'pass'
            or report.get('scene_sha256') != digest
            or report.get('policy_version') != POLICY_VERSION
            or report.get('runtime_version') != '4.5.0'
            or report.get('glass_tube_r7') is not True
            or not all(report.get('checks', {}).get(name) is True for name in REQUIRED_CHECKS)
        ):
            raise ValueError('unqualified r8 runtime report')
    render = json.loads((folder / 'render_manifest.json').read_text())
    review = json.loads((folder / 'visual_review.json').read_text())
    audit = json.loads((root / 'evidence/physical_revision_audit.json').read_text())
    if any(item.get('status') != 'pass' or item.get('scene_sha256') != digest for item in (render, review, audit)):
        raise ValueError('stale or failed r8 evidence')
    if not audit.get('all_r7_physics_identical') or not audit.get('water_volume_unchanged'):
        raise ValueError('r8 water/physics scope missing')
    if review.get('render_manifest_sha256') != sha256((folder / 'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('visual review does not cover final renders')
    if review.get('verdict') == 'FAIL' or review.get('blocking_failures'):
        raise ValueError('visual review has blocking defects')
    names = {Path(item['path']).name for item in render['images']}
    if not set(IN_BATH_VIEWS).issubset(names):
        raise ValueError('missing in-bath color views')
    withdrawn = {
        'outside_no_heating_closeup.png',
        't15_withdrawn_closeup.png',
        't30_withdrawn_closeup.png',
        'observed_closeup.png',
    }
    if not withdrawn.issubset(names):
        raise ValueError('withdrawn color views missing')
    for item in render['images']:
        if sha256((root / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('reviewed image changed')
    recipe = json.loads((root / 'evidence/water_recipe.json').read_text())
    if recipe['scene_sha256'] != digest or recipe.get('fill_height_ratio') != 0.8:
        raise ValueError('water volume recipe mismatch')
    if recipe.get('material', {}).get('shader') != 'OmniGlass':
        raise ValueError('clear OmniGlass water recipe required')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    prepare(root, args.report)
    compose_progression(root, label='Fehling r8 | clear bath water | 8 mL', crop=(855, 425, 1065, 850))
    manifest = json.loads((root / 'manifest.json').read_text())
    manifest.setdefault('claims', {})['in_bath_color_verified'] = True
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finalize()

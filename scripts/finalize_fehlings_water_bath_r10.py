"""Finalize r10 only when deep in-bath front views exist."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.fehlings_r6_state import POLICY_VERSION
from scripts.finalize_fehlings_water_bath import main as finalize
from scripts.finalize_fehlings_water_bath_r7 import REQUIRED_CHECKS as TUBE_CHECKS

REQUIRED_CHECKS = TUBE_CHECKS + ('color_sample_below_waterline',)
FRONT_BATH_VIEWS = (
    't3_front_bath.png',
    't15_front_bath.png',
    't21_front_bath.png',
    't30_front_bath.png',
)
COLOR_STATES = ('t3', 't9', 't15', 't21', 't27', 't30')


def color_snapshots_are_deep(report, sample_top_m):
    """True when color playback sits well below the waterline with sample submerged."""
    water = float(report.get('water_world_surface_z') or 0)
    found = False
    for snap in report.get('snapshots', []):
        if snap.get('name') not in COLOR_STATES:
            continue
        found = True
        z = float(snap['tube_xyz'][2])
        if z + float(sample_top_m) >= water - 1e-4 or water - z < 0.05:
            return False
    return found


def prepare(root, reports):
    """Require three exact passes, deep heating, and front-on in-bath views."""
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    manifest = json.loads((root / 'manifest.json').read_text())
    if not str(manifest.get('package_id', '')).endswith('_vr_r10'):
        raise ValueError('r10 package identity required')
    folder = root / 'evidence/initial_scene'
    if not (folder / 'render_manifest.json').is_file():
        raise ValueError('front_bath render evidence required')
    data = [json.loads(path.read_text()) for path in reports]
    if (
        len(data) != 3
        or len({path.resolve() for path in reports}) != 3
        or len({item.get('process_id') for item in data}) != 3
        or any(type(item.get('process_id')) is not int or item['process_id'] <= 0 for item in data)
    ):
        raise ValueError('three independent r10 cold starts required')
    sample_top = float(json.loads((root / 'evidence/sample_recipe.json').read_text())['sample_top_m'])
    for report in data:
        if (
            report.get('status') != 'pass'
            or report.get('scene_sha256') != digest
            or report.get('policy_version') != POLICY_VERSION
            or report.get('runtime_version') != '4.5.0'
            or report.get('glass_tube_r7') is not True
            or report.get('heating_style') != 'deep'
            or not all(report.get('checks', {}).get(name) is True for name in REQUIRED_CHECKS)
        ):
            raise ValueError('unqualified r10 runtime report')
        if not color_snapshots_are_deep(report, sample_top):
            raise ValueError('deep immersion required for color snapshots')
    render = json.loads((folder / 'render_manifest.json').read_text())
    review = json.loads((folder / 'visual_review.json').read_text())
    audit = json.loads((root / 'evidence/physical_revision_audit.json').read_text())
    if any(item.get('status') != 'pass' or item.get('scene_sha256') != digest for item in (render, review, audit)):
        raise ValueError('stale or failed r10 evidence')
    if not audit.get('all_r9_physics_identical') or not audit.get('water_volume_unchanged'):
        raise ValueError('r10 water/physics scope missing')
    if review.get('render_manifest_sha256') != sha256((folder / 'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('visual review does not cover final renders')
    if review.get('verdict') == 'FAIL' or review.get('blocking_failures'):
        raise ValueError('visual review has blocking defects')
    names = {Path(item['path']).name for item in render['images']}
    if not set(FRONT_BATH_VIEWS).issubset(names):
        raise ValueError('missing front_bath color views')
    for item in render['images']:
        if sha256((root / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('reviewed image changed')
    recipe = json.loads((root / 'evidence/water_recipe.json').read_text())
    if recipe['scene_sha256'] != digest or recipe.get('fill_height_ratio') != 0.8:
        raise ValueError('water volume recipe mismatch')
    if recipe.get('material', {}).get('representation') != 'lining_and_surface':
        raise ValueError('lining water representation required')


def compose_front_progression(root):
    """Contact sheet of deep in-bath front views; no withdrawn crops."""
    from PIL import Image, ImageDraw, ImageFont

    folder = root / 'evidence/initial_scene'
    render_path = folder / 'render_manifest.json'
    render = json.loads(render_path.read_text())
    inputs = {Path(item['path']).name: item for item in render['images']}
    sheet = Image.new('RGB', (1920, 430), '#18232c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    draw.text(
        (18, 8),
        'Fehling r10 | front_bath | deep immerse | identical scale, no recolor',
        font=small,
        fill='white',
    )
    sources = []
    for index, second in enumerate((3, 9, 15, 21, 27, 30)):
        name = f't{second}_front_bath.png'
        record = inputs[name]
        path = root / record['path']
        if sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('progression source differs from render manifest')
        draw.text((index * 320 + 18, 40), f'{second} s', font=font, fill='white')
        with Image.open(path) as image:
            sheet.paste(image.resize((300, 169)), (index * 320 + 10, 80))
        sources.append(record)
    output = folder / 'color_progression.png'
    sheet.save(output)
    (folder / 'color_progression_manifest.json').write_text(
        json.dumps(
            dict(
                scene_sha256=render['scene_sha256'],
                render_manifest_sha256=sha256(render_path.read_bytes()).hexdigest(),
                image_sha256=sha256(output.read_bytes()).hexdigest(),
                method='front_bath_full_frame_resize_no_color_adjustment',
                sources=sources,
            ),
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    prepare(root, args.report)
    compose_front_progression(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    manifest.setdefault('claims', {})['in_bath_color_verified'] = True
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finalize()

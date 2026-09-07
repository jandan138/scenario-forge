"""Verify a liquid-only titration revision preserves all other authored content."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from scripts.generate_traditional_titration_vr_r13 import LIQUID_ROOT, water_controller


def audit(source, root):
    from pxr import Usd

    old = Usd.Stage.Open(str(source/'scene.usd'))
    new = Usd.Stage.Open(str(root/'scene.usd'))
    changes = []
    for prim in old.TraverseAll():
        path = str(prim.GetPath())
        if path.startswith(LIQUID_ROOT):
            continue
        other = new.GetPrimAtPath(path)
        if not other or prim.GetTypeName() != other.GetTypeName() or prim.GetAppliedSchemas() != other.GetAppliedSchemas():
            changes.append(path)
            continue
        for attr in prim.GetAttributes():
            if path.endswith('/FlowController') and attr.GetName() == 'inputs:script':
                if other.GetAttribute(attr.GetName()).Get() != water_controller(attr.Get()):
                    changes.append(str(attr.GetPath()))
                continue
            compare = other.GetAttribute(attr.GetName())
            # Asset paths resolve under different package roots but authored paths must match.
            if not compare or str(attr.Get()) != str(compare.Get()) or attr.GetTimeSamples() != compare.GetTimeSamples():
                changes.append(str(attr.GetPath()))
            elif any(str(attr.Get(t)) != str(compare.Get(t)) for t in attr.GetTimeSamples()):
                changes.append(str(attr.GetPath()))
        for rel in prim.GetRelationships():
            if path == '/World/obj_titration_station' and rel.GetName() in (
                'titration:receiverLiquidVisuals', 'titration:receiverLiquidShader'
            ):
                continue
            if rel.GetTargets() != other.GetRelationship(rel.GetName()).GetTargets():
                changes.append(str(rel.GetPath()))
    physical_liquid = [str(p.GetPath()) for p in Usd.PrimRange(new.GetPrimAtPath(LIQUID_ROOT))
                       if any('Physics' in s or 'Physx' in s for s in p.GetAppliedSchemas())]
    dependency_changes = []
    for path in (source/'deps').rglob('*'):
        if path.is_file():
            target = root/path.relative_to(source)
            if not target.is_file() or sha256(path.read_bytes()).digest() != sha256(target.read_bytes()).digest():
                dependency_changes.append(str(path.relative_to(source)))
    report = {'status': 'pass' if not changes and not physical_liquid and not dependency_changes else 'blocked',
              'unexpected_scene_changes': changes, 'physics_in_visual_liquid': physical_liquid,
              'dependency_changes': dependency_changes,
              'source_scene_sha256': sha256((source/'scene.usd').read_bytes()).hexdigest(),
              'scene_sha256': sha256((root/'scene.usd').read_bytes()).hexdigest(),
              'allowed_changes': ['VisualLiquid subtree', 'liquid shader/visual relationships',
                                  'controller color constants and glass_color update interface']}
    (root/'evidence/visual_revision_audit.json').write_text(json.dumps(report, indent=2)+'\n')
    if report['status'] != 'pass':
        raise ValueError(report)
    return report


def merge_render_evidence(root):
    from PIL import Image, ImageDraw, ImageFont

    out = root/'evidence/initial_scene'
    records = [json.loads((out/f'render_manifest_{label}.json').read_text()) for label in ('before', 'after')]
    for key in ('status', 'runtime_version', 'resolution', 'renderer', 'refraction_bounces'):
        if records[0][key] != records[1][key]:
            raise ValueError(f'comparison mismatch: {key}')
    if records[0]['status'] != 'pass':
        raise ValueError('render incomplete')
    for before, after in zip(records[0]['views'], records[1]['views'], strict=True):
        for key in ('state', 'view', 'camera_position', 'target'):
            if before[key] != after[key]:
                raise ValueError(f'camera/state mismatch: {key}')
    merged = dict(records[1])
    merged['views'] = records[0]['views']+records[1]['views']
    (out/'render_manifest.json').write_text(json.dumps(merged, indent=2)+'\n')
    shutil.copy2(out/'after_initial_scene_overview.png', out/'scene_overview.png')
    shutil.copy2(out/'after_endpoint_flask_detail.png', out/'endpoint_pale_pink.png')
    sheet = Image.new('RGB', (1920, 1160), '#18232c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    for row, phase in enumerate(('initial', 'endpoint')):
        for col, label in enumerate(('before', 'after')):
            title = f'{"r1.2 BEFORE" if label == "before" else "r1.3 AFTER"} | {phase}'
            draw.text((col*960+18, row*580+8), title, font=font, fill='white')
            with Image.open(out/f'{label}_{phase}_flask_detail.png') as frame:
                sheet.paste(frame.resize((960, 540)), (col*960, row*580+40))
    sheet.save(out/'liquid_before_after.png')
    diagnostics = root.parent.parent/'diagnostic_renders'
    for path in (root/'evidence').glob('diagnostic_*'):
        if path.is_dir():
            diagnostics.mkdir(exist_ok=True)
            shutil.move(str(path), str(diagnostics/path.name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--merge-render', action='store_true')
    args = parser.parse_args()
    print(audit(args.source, args.root))
    if args.merge_render:
        merge_render_evidence(args.root)

"""Bind r1.4 to the promoted producer package and retain final evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from scripts.finalize_traditional_titration_vr_r1 import main as finalize


def physical_state(stage):
    result = {}
    for prim in stage.TraverseAll():
        apis = list(prim.GetAppliedSchemas())
        if not any('Physics' in a or 'Physx' in a for a in apis) and 'Joint' not in prim.GetTypeName():
            continue
        result[str(prim.GetPath())] = {'type': prim.GetTypeName(), 'apis': apis,
            'attrs': {a.GetName(): str(a.Get()) for a in prim.GetAttributes()
                      if a.GetName().startswith(('physics:', 'physx', 'xformOp')) or a.GetName() in ('points', 'height', 'radius', 'size', 'faceVertexIndices', 'faceVertexCounts')},
            'rels': {r.GetName(): [str(t) for t in r.GetTargets()] for r in prim.GetRelationships() if r.GetName().startswith(('physics:', 'physx'))}}
    return result


def prepare(root, source, producer, reports):
    from pxr import Usd
    from PIL import Image, ImageDraw, ImageFont

    old = Usd.Stage.Open(str(source/'scene.usd'))
    new = Usd.Stage.Open(str(root/'scene.usd'))
    if physical_state(old) != physical_state(new):
        raise ValueError('physical composition changed')
    receipt = json.loads((producer/'promotion_receipt.json').read_text())
    if receipt['status'] != 'promoted':
        raise ValueError('producer is not promoted')
    embedded = root/'deps/titration_assets'
    if sha256((embedded/'packages/station/asset.usd').read_bytes()).hexdigest() != receipt['asset_sha256']:
        raise ValueError('embedded producer differs from qualification')
    # Only refresh producer evidence/receipt; never rewrite the qualified scene or asset.
    shutil.copytree(producer/'packages/station/evidence', embedded/'packages/station/evidence', dirs_exist_ok=True)
    shutil.copy2(producer/'promotion_receipt.json', embedded/'promotion_receipt.json')
    # An earlier candidate copied producer scratch runs; only qualified evidence ships.
    if (embedded/'runtime').exists():
        shutil.rmtree(embedded/'runtime')
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    if len(reports) != 3 or any(json.loads(p.read_text()).get('scene_sha256') != digest for p in reports):
        raise ValueError('reports do not cover the exact final scene')
    out = root/'evidence/initial_scene'
    render = json.loads((out/'render_manifest_after.json').read_text())
    if render['status'] != 'pass' or render['runtime_version'] != '4.5.0':
        raise ValueError('final 4.5 render missing')
    render['all_states_are_visual_snapshots'] = True
    (out/'render_manifest.json').write_text(json.dumps(render, indent=2)+'\n')
    shutil.copy2(out/'after_initial_scene_overview.png', out/'scene_overview.png')
    shutil.copy2(source/'evidence/initial_scene/after_initial_flask_detail.png', out/'r13_stir_bar.png')
    sheet = Image.new('RGB', (1920, 580), '#18232c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    for i, (name, title) in enumerate((('r13_stir_bar.png', 'r1.3 | 32 x 6 mm'),
                                      ('after_initial_flask_detail.png', 'r1.4 | 20 x 5 mm'))):
        draw.text((i*960+15, 8), title, fill='white', font=font)
        with Image.open(out/name) as frame:
            sheet.paste(frame.resize((960,540)), (i*960,40))
    sheet.save(out/'stir_bar_before_after.png')
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['assets']['titration_station_receipt_sha256'] = sha256((embedded/'promotion_receipt.json').read_bytes()).hexdigest()
    manifest['claims'].update(asset_functionality=True, full_burette_visual_precharge=True)
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    (root/'evidence/physical_revision_audit.json').write_text(json.dumps({
        'status': 'pass', 'physical_content_identical': True, 'physical_prims': len(physical_state(new)),
        'scene_sha256': digest, 'source_scene_sha256': sha256((source/'scene.usd').read_bytes()).hexdigest()}, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    prepare(args.root, args.source, args.producer, args.report)
    argv = ['--root', str(args.root)]
    for report in args.report:
        argv.extend(['--report', str(report)])
    raise SystemExit(finalize(argv))

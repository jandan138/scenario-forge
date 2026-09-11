"""Finalize r1.7 with reference-placement, nozzle and exact-scene evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from scripts.finalize_traditional_titration_vr_r1 import main as finalize
from scripts.validate_traditional_titration_vr_r1 import evaluate_report


def prepare(root,reports):
    digest=sha256((root/'scene.usd').read_bytes()).hexdigest()
    if len(reports)!=3 or len({p.resolve() for p in reports})!=3:
        raise ValueError('three distinct r1.7 cold starts required')
    for path in reports:
        r=json.loads(path.read_text())
        if r.get('scene_sha256')!=digest or r.get('runtime_version')!='4.5.0' or evaluate_report(r)['status']!='pass':
            raise ValueError('unqualified scene report')
        if not all(r.get('r17_checks',{}).get(n) is True for n in ('reference_poses_match','station_keeps_reference_pose','mesh_tip','flask_supported_xy')):
            raise ValueError('missing r1.7 checks')
    embedded=root/'deps/titration_assets'
    receipt=json.loads((embedded/'promotion_receipt.json').read_text())
    if receipt['status']!='promoted' or receipt['asset_sha256']!=sha256((embedded/'packages/station/asset.usd').read_bytes()).hexdigest():
        raise ValueError('producer qualification mismatch')
    folder=root/'evidence/initial_scene'
    render=json.loads((folder/'render_manifest_after.json').read_text())
    review=json.loads((folder/'visual_review.json').read_text())
    audit=json.loads((root/'evidence/physical_revision_audit.json').read_text())
    for item in (render,review,audit):
        if item.get('status')!='pass' or item.get('scene_sha256')!=digest:
            raise ValueError('stale or failed scene evidence')
    if not audit['prim_paths_identical'] or not audit['reference_poses_match']:
        raise ValueError('structure/pose audit failed')
    if not render.get('burette_views') or not render.get('tip_detail') or not render.get('follow_task_pose'):
        raise ValueError('missing nozzle views')
    if {v['state'] for v in render['views']}!={'initial','mid','end_scale'}:
        raise ValueError('missing liquid states')
    required_views={'scene_overview','flask_detail','burette_lower','tip_side','tip_outlet'}
    for state in ('initial','mid','end_scale'):
        if not required_views.issubset({v['view'] for v in render['views'] if v['state']==state}):
            raise ValueError('incomplete nozzle capture set')
    for view in render['views']:
        if sha256((root/view['path']).read_bytes()).hexdigest()!=view['sha256']:
            raise ValueError('render checksum differs')
    if review.get('render_manifest_sha256')!=sha256((folder/'render_manifest_after.json').read_bytes()).hexdigest():
        raise ValueError('review does not cover final renders')
    shutil.copy2(folder/'render_manifest_after.json',folder/'render_manifest.json')
    shutil.copy2(folder/'after_initial_scene_overview.png',folder/'scene_overview.png')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--report',type=Path,action='append',required=True)
    args=p.parse_args()
    prepare(args.root,args.report)
    argv=['--root',str(args.root)]
    for report in args.report:
        argv.extend(['--report',str(report)])
    raise SystemExit(finalize(argv))

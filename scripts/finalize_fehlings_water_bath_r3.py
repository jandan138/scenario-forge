"""Finalize exact-scene visual-water/contact evidence for Fehling r3."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.finalize_fehlings_water_bath import main as finalize


def prepare(root,reports,*,policy_version='visual_water_contact_v3'):
    digest=sha256((root/'scene.usd').read_bytes()).hexdigest()
    data=[json.loads(p.read_text()) for p in reports]
    if len(data)!=3 or len({d.get('process_id') for d in data})!=3:
        raise ValueError('three independent r3 cold starts required')
    required=('no_pbd_components','water_has_no_physics','cup_colliders_retained','passes_water_surface',
              'cup_bottom_blocks','cup_wall_blocks','above_surface','outside','wall_only','upper_only',
              'shallow_contact','tilted_contact','actual_tilt_exceeds_old_limit','partial_contact',
              'bath_motion_follows','pause_and_geometry_freeze','complete_at_60',
              'not_success_before_three_seconds','observation_success','reset_complete','actual_materials','actual_geometry')
    if policy_version=='visual_fixed_regions_v5':
        required+=('fixed_geometry_all_snapshots','fixed_height_all_snapshots')
    for r in data:
        if (r.get('scene_sha256')!=digest or r.get('status')!='pass' or r.get('policy_version')!=policy_version
                or r.get('runtime_version')!='4.5.0' or not all(r.get('checks',{}).get(k) is True for k in required)):
            raise ValueError('unqualified r3 report')
    folder=root/'evidence/initial_scene'
    render=json.loads((folder/'render_manifest.json').read_text())
    review=json.loads((folder/'visual_review.json').read_text())
    audit=json.loads((root/'evidence/physical_revision_audit.json').read_text())
    for r in (render,review,audit):
        if r.get('scene_sha256')!=digest or r.get('status')!='pass':
            raise ValueError('stale or failed r3 evidence')
    required_images={'scene_overview.png','shallow_contact_closeup.png','tilted_contact_closeup.png',
                     't45_closeup.png','t60_closeup.png','observed_closeup.png'}
    if policy_version=='visual_fixed_regions_v5':
        required_images.update({'outside_no_heating_closeup.png','t37_5_closeup.png','t52_5_closeup.png','reset_closeup.png'})
    if not required_images.issubset({Path(v['path']).name for v in render['images']}):
        raise ValueError('required water/contact images missing')
    if review.get('render_manifest_sha256')!=sha256((folder/'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('review does not cover final renders')
    for item in render['images']:
        if sha256((root/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('image modified after review')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--report',type=Path,action='append',required=True)
    args=p.parse_args()
    prepare(args.root,args.report)
    finalize()

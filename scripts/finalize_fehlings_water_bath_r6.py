"""Require exact-scene five-layer/30 s runtime and visual evidence before packaging."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.fehlings_r6_state import POLICY_VERSION
from scripts.finalize_fehlings_water_bath import main as finalize

REQUIRED_CHECKS = (
    'no_pbd_components','water_has_no_physics','rack_stable','cup_colliders_retained',
    'passes_water_surface','cup_bottom_blocks','cup_wall_blocks','above_surface','outside',
    'wall_only','upper_only','shallow_contact','tilted_contact','actual_tilt_exceeds_old_limit',
    'partial_contact','bath_motion_follows','pause_and_geometry_freeze','pause_all_materials',
    'not_ready_before_30','complete_at_30','not_success_before_three_seconds','observation_success',
    'reset_complete','actual_materials','actual_geometry','five_equal_fixed_layers',
    'layer_progress_matches','global_progress_matches',
)


def compose_progression(root, *, label='Fehling r6', crop=(865,500,1055,835)):
    """Same crop and scale from actual withdrawn snapshots; no color adjustment."""
    from PIL import Image, ImageDraw, ImageFont
    folder = root/'evidence/initial_scene'
    render_path = folder/'render_manifest.json'
    render = json.loads(render_path.read_text())
    inputs = {Path(v['path']).name:v for v in render['images']}
    image_height=round(300*(crop[3]-crop[1])/(crop[2]-crop[0]))
    sheet = Image.new('RGB',(1920,max(640,110+image_height)),'#18232c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    draw.text((18,12),label+' | cumulative water-contact time | retained states, withdrawn for inspection',font=small,fill='white')
    sources = []
    for i,t in enumerate((0,9,15,21,27,30)):
        name = 'outside_no_heating_closeup.png' if t==0 else f't{t}_withdrawn_closeup.png'
        record = inputs[name]
        path = root/record['path']
        if sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('progression source differs from render manifest')
        draw.text((i*320+18,46),f'{t} s',font=font,fill='white')
        with Image.open(path) as image:
            if image.size!=(1920,1080):
                raise ValueError('unexpected source framing')
            sheet.paste(image.crop(crop).resize((300,image_height)),(i*320+10,90))
        sources.append(record)
    output = folder/'color_progression.png'
    sheet.save(output)
    (folder/'color_progression_manifest.json').write_text(json.dumps(dict(
        scene_sha256=render['scene_sha256'],render_manifest_sha256=sha256(render_path.read_bytes()).hexdigest(),
        image_sha256=sha256(output.read_bytes()).hexdigest(),crop_xyxy=crop,
        method='identical_crop_and_scale_no_color_adjustment',sources=sources),indent=2)+'\n')


def prepare(root, reports):
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    data = [json.loads(p.read_text()) for p in reports]
    if len(data)!=3 or len({d.get('process_id') for d in data})!=3:
        raise ValueError('three distinct cold-start processes required')
    for report in data:
        if (report.get('scene_sha256')!=digest or report.get('status')!='pass'
                or report.get('runtime_version')!='4.5.0' or report.get('policy_version')!=POLICY_VERSION
                or not all(report.get('checks',{}).get(k) is True for k in REQUIRED_CHECKS)):
            raise ValueError('unqualified r6 runtime report')
    folder = root/'evidence/initial_scene'
    render = json.loads((folder/'render_manifest.json').read_text())
    review = json.loads((folder/'visual_review.json').read_text())
    audit = json.loads((root/'evidence/physical_revision_audit.json').read_text())
    if any(v.get('status')!='pass' or v.get('scene_sha256')!=digest for v in (render,review,audit)):
        raise ValueError('stale or failed scene evidence')
    if not audit.get('all_r5_physics_identical'):
        raise ValueError('missing r5 physics equivalence')
    if render.get('policy_version')!=POLICY_VERSION:
        raise ValueError('wrong render policy')
    if review.get('render_manifest_sha256')!=sha256((folder/'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('review does not cover final renders')
    required = {'scene_overview.png','outside_no_heating_closeup.png','t9_withdrawn_closeup.png',
                't15_withdrawn_closeup.png','t21_withdrawn_closeup.png','t27_withdrawn_closeup.png',
                't30_closeup.png','observed_closeup.png','reset_closeup.png'}
    if not required.issubset({Path(v['path']).name for v in render['images']}):
        raise ValueError('missing color milestones')
    for item in render['images']:
        if sha256((root/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('image changed after review')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',required=True)
    args = parser.parse_args()
    prepare(args.root,args.report)
    compose_progression(args.root)
    finalize()

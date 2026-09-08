"""Require exact-scene r2 sedimentation evidence before packaging."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.finalize_fehlings_water_bath import main as finalize


def prepare(root,reports):
    digest=sha256((root/'scene.usd').read_bytes()).hexdigest()
    required=('before_onset_unchanged','t30_is_onset','heated_60','developed_at_60',
              'paused_geometry','paused_appearance','observed_three_seconds','reset_geometry',
              'reset_color','actual_material_values','actual_geometry_values','sediment_height_increases')
    if len(reports)!=3:
        raise ValueError('three fresh r2 cold starts required')
    for path in reports:
        report=json.loads(path.read_text())
        if (report.get('policy_version')!='visual_sedimentation_v2' or report.get('scene_sha256')!=digest
                or report.get('status')!='pass' or not all(report.get('checks',{}).get(n) is True for n in required)):
            raise ValueError('unqualified r2 runtime report: '+str(path))
    folder=root/'evidence/initial_scene'
    render=json.loads((folder/'render_manifest.json').read_text())
    review=json.loads((folder/'visual_review.json').read_text())
    physical=json.loads((root/'evidence/physical_revision_audit.json').read_text())
    for record in (render,review,physical):
        if record.get('status')!='pass' or record.get('scene_sha256')!=digest:
            raise ValueError('stale or failed r2 scene evidence')
    if review.get('render_manifest_sha256')!=sha256((folder/'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('visual review refers to different renders')
    expected={'initial_closeup.png','t30_closeup.png','t37_5_closeup.png','t45_closeup.png',
              't52_5_closeup.png','t60_closeup.png','observed_closeup.png'}
    if not expected.issubset({Path(v['path']).name for v in render['images']}):
        raise ValueError('missing reaction milestones')
    for view in render['images']:
        if sha256((root/view['path']).read_bytes()).hexdigest()!=view['sha256']:
            raise ValueError('render image modified')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',required=True)
    args=parser.parse_args()
    prepare(args.root,args.report)
    finalize()

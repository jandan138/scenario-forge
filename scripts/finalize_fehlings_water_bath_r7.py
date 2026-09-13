"""Finalize exact r7 glass/rack/bath evidence and its fixture-qualified producer."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.fehlings_r6_state import POLICY_VERSION
from scripts.finalize_fehlings_water_bath import main as finalize
from scripts.finalize_fehlings_water_bath_r6 import REQUIRED_CHECKS as COLOR_CHECKS, compose_progression

REQUIRED_CHECKS = COLOR_CHECKS + ('glass_body_mass','rack_extraction','rack_reinsertion',
    'rack_guided_path_clear','sample_eight_ml','new_tube_dimensions','finite_actual_poses')


def prepare(root, reports):
    """Require three exact passes, qualified embedded source and reviewed final images."""
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    manifest = json.loads((root/'manifest.json').read_text())
    asset_file = root/manifest['tube_producer_manifest']
    producer = json.loads(asset_file.read_text())
    asset_sha = sha256((asset_file.parent.parent/'asset.usd').read_bytes()).hexdigest()
    if (not manifest['package_id'].endswith('_vr_r7') or producer['overall_status']!='pass'
            or producer['asset_sha256']!=asset_sha or manifest['tube_asset_sha256']!=asset_sha
            or producer['runtime_qualification']['scene_sha256']!=digest):
        raise ValueError('exact r7 producer qualification required')
    data = [json.loads(path.read_text()) for path in reports]
    if (len(data)!=3 or len({path.resolve() for path in reports})!=3
            or len({v.get('process_id') for v in data})!=3
            or any(type(v.get('process_id')) is not int or v['process_id']<=0 for v in data)):
        raise ValueError('three independent r7 cold starts required')
    if {sha256(path.read_bytes()).hexdigest() for path in reports}!=set(producer['runtime_qualification']['original_report_sha256']):
        raise ValueError('finalization must use the promoted report triplet')
    for report in data:
        if (report.get('status')!='pass' or report.get('scene_sha256')!=digest
                or report.get('tube_asset_sha256')!=asset_sha or report.get('glass_tube_r7') is not True
                or report.get('policy_version')!=POLICY_VERSION or report.get('runtime_version')!='4.5.0'
                or not all(report.get('checks',{}).get(k) is True for k in REQUIRED_CHECKS)):
            raise ValueError('unqualified r7 runtime report')
    folder = root/'evidence/initial_scene'
    render = json.loads((folder/'render_manifest.json').read_text())
    review = json.loads((folder/'visual_review.json').read_text())
    audit = json.loads((root/'evidence/physical_revision_audit.json').read_text())
    if any(v.get('status')!='pass' or v.get('scene_sha256')!=digest for v in (render,review,audit)):
        raise ValueError('stale or failed r7 evidence')
    if not audit.get('non_tube_physics_preserved') or not render.get('glass_tube_r7'):
        raise ValueError('r7 physics/render scope missing')
    if review.get('render_manifest_sha256')!=sha256((folder/'render_manifest.json').read_bytes()).hexdigest():
        raise ValueError('visual review does not cover final renders')
    if review.get('verdict')=='FAIL' or review.get('blocking_failures'):
        raise ValueError('visual review has blocking defects')
    required = {'scene_overview.png','initial_tube_full.png','rack_extracted_tube_full.png',
        'rack_reinserted_tube_full.png','outside_no_heating_mouth_detail.png','observed_mouth_detail.png',
        'outside_no_heating_closeup.png','t9_withdrawn_closeup.png','t15_withdrawn_closeup.png',
        't21_withdrawn_closeup.png','t27_withdrawn_closeup.png','t30_closeup.png','observed_closeup.png','reset_closeup.png'}
    if not required.issubset({Path(v['path']).name for v in render['images']}):
        raise ValueError('missing glass/rack/color views')
    for item in render['images']:
        if sha256((root/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('reviewed image changed')
    recipe = json.loads((root/'evidence/sample_recipe.json').read_text())
    if recipe['scene_sha256']!=digest or abs(recipe['realized_mesh_volume_ml']-8)>.002:
        raise ValueError('eight-mL recipe mismatch')
    fit_path = root/'evidence/rack_fit.json'
    fit = json.loads(fit_path.read_text())
    if fit['scene_sha256']!=digest:
        raise ValueError('rack fit is stale')
    fit.update(runtime_verified=True,qualification='three r7 prescribed dynamic extraction/reinsertion fixtures')
    fit_path.write_text(json.dumps(fit,indent=2)+'\n')
    manifest['claims']['glass_tube_runtime_verified']=True
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',required=True)
    args = parser.parse_args()
    prepare(args.root,args.report)
    compose_progression(args.root,label='Fehling r7 | 18 x 150 mm glass | 8 mL',crop=(855,425,1065,850))
    finalize()

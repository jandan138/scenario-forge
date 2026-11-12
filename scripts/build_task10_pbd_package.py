"""Package a producer-bound task10 candidate without modifying producer assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
PACKAGE_ID = 'scientific_workbench_titration_task10_real_liquid_r1'
STATION = '/World/obj_titration_station'


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def build(candidate, out, package_id=PACKAGE_ID):
    from pxr import Usd, UsdGeom, UsdUtils
    from scenario_forge.scaffold import scaffold_starter_package
    from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
    from scenario_forge.assets.checksum import compute_sha256
    from scenario_forge.package import validate_package
    candidate, out = Path(candidate).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    metadata = json.loads((candidate/'manifest.json').read_text())
    scaffold_starter_package(out)
    shutil.rmtree(out/'assets/objects')
    shutil.rmtree(out/'assets/markers')
    shutil.copytree(candidate, out/'assets/composed')
    for name, entry in [('main','scene41'),('isaac45','scene45'),('demo41','demo41'),('demo45','demo45')]:
        stage = Usd.Stage.CreateNew(str(out/f'scene/{name}.usda'))
        stage.GetRootLayer().subLayerPaths = [f'../assets/composed/{entry}.usda']
        UsdGeom.SetStageMetersPerUnit(stage,1.)
        UsdGeom.SetStageUpAxis(stage,'Z')
        stage.SetMetadata('kilogramsPerUnit',1.)
        stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
        stage.GetRootLayer().Save()
    rows = []
    for version in ('41','45'):
        path = f'assets/composed/scene{version}.usda'
        rows.append({'asset_id':f'task10_composed_scene{version}','role':'environment','asset_type':'scene',
                     'canonical_usd':path,'license':'internal-colleague-source-and-preserved-NVIDIA-notices',
                     'sha256':compute_sha256(out/path)})
    write_yaml(out/'assets/asset_manifest.yaml',{'schema_version':'asset-manifest/v0.2','assets':rows})
    write_asset_lock(out,generate_asset_lock(out))
    write_yaml(out/'scene/instances.yaml',{'schema_version':'scene-instances/v0.2','instances':[{
        'id':'task10_scene','asset_id':'task10_composed_scene41','source_prim_path':'/World',
        'pose':{'xyz':[0,0,0],'wxyz':[1,0,0,0]},'initial_state':{}}]})
    write_yaml(out/'scene/layout.yaml',{'schema_version':'scene-layout/v0.2','frames':[{'id':'world','type':'root'}],'zones':[]})
    write_yaml(out/'task/task.yaml',{'schema_version':'task/v0.2','task_id':package_id,'task_family':'titration',
        'instruction':'Titrate into the receiver until pale pink, close the valve, and hold for 3 simulation seconds.',
        'measurement_source':'unique_real_reagent_particles_contacting_receiver_liquid_after_mouth_entry',
        'liquid_model':'GPU_PBD_with_controlled_conservative_source_to_tip_transfer',
        'success':{'type':'runtime_attribute','path':STATION,'attribute':'titration:task_success'}})
    write_yaml(out/'task/task_graph.yaml',{'schema_version':'task-graph/v0.2',
        'nodes':[{'id':n} for n in ('align_receiver','titrate','close_and_hold')],
        'edges':[{'from':'align_receiver','to':'titrate'},{'from':'titrate','to':'close_and_hold'}]})
    write_yaml(out/'task/predicates.yaml',{'schema_version':'predicates/v0.2','predicates':[{
        'id':'pale_endpoint_held','type':'runtime_attribute','path':STATION,'attribute':'titration:task_success'}]})
    write_yaml(out/'task/safety_rules.yaml',{'schema_version':'safety-rules/v0.2','rules':[]})
    write_yaml(out/'robot/robot.yaml',{'schema_version':'robot/v0.2','robot_id':'none','embodiment':'none','action_space':'none','sensors':[]})
    write_yaml(out/'robot/robot_profile.yaml',{'schema_version':'robot-profile/v0.2','robot_id':'none','workspace':{'frame':'world'}})
    write_yaml(out/'metrics/metrics.yaml',{'schema_version':'metrics/v0.2','metrics':[],'claim':'no_robot_fixture_only'})
    write_yaml(out/'metrics/splits.yaml',{'schema_version':'splits/v0.2','splits':[{'name':'fixture','package_ids':[package_id]}]})
    manifest = yaml.safe_load((out/'manifest.yaml').read_text())
    manifest.update(package_id=package_id,targets=['ebench','embodied-eval-os'])
    manifest['validation']['minimum_required_level'] = 'package_schema_validated'
    write_yaml(out/'manifest.yaml',manifest)
    write_yaml(out/'generation_plan.yaml',{'schema_version':'scenario-generation-plan/v0.2','package_id':package_id,
        'seed':0,'target_exports':['ebench','embodied-eval-os'],'package_mode':'fat'})
    sources = [{'path':str(candidate/'manifest.json'),'sha256':compute_sha256(candidate/'manifest.json')}]
    write_yaml(out/'provenance/provenance.yaml',{'schema_version':'provenance/v0.2',
        'generator':'build_task10_pbd_package.py','sources':sources,'source_scene_sha256':metadata['source_sha256'],
        'runtime_status':'not_qualified','producer_assets_modified':False})
    write_yaml(out/'provenance/source_refs.yaml',{'sources':sources})
    unresolved = set()
    for entry in ('main','isaac45'):
        _,_,missing = UsdUtils.ComputeAllDependencies(str(out/f'scene/{entry}.usda'))
        unresolved.update(missing)
    (out/'evidence/build.json').write_text(json.dumps({'unresolved':sorted(unresolved),'runtime_status':'not_qualified'},indent=2))
    hashes = {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((out/'assets').rglob('*')) if p.is_file()}
    (out/'evidence/asset_hashes.json').write_text(json.dumps(hashes,indent=2))
    result = validate_package(out,require_asset_lock=True)
    if not result.ok or unresolved:
        raise ValueError({'package':result.messages,'unresolved':sorted(unresolved)})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--package-id',default=PACKAGE_ID)
    args = parser.parse_args()
    print(build(args.candidate,args.out,args.package_id))

"""Integrate the qualified r4 nozzle at existing paths and import five reference poses."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import yaml

from scripts.generate_traditional_titration_vr_r16 import ROOT,STATION

SOURCE=ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_6_20260907/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_6'
PRODUCER=Path('/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/traditional_titration_assets_r4_open_tip_20260908')
OUTPUT=ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_20260908'
TASK_ID='scientific_workbench_traditional_acid_base_titration_vr_r1_7'
POSE_ZIP=ROOT/'external_artifacts/incoming/from_xinyu/task_10_titration_experiment.zip'
OBJECTS=('obj_titration_station','obj_receiver_flask','obj_magnetic_stirrer','obj_sample_beaker','obj_context_conical_flask')
VISUAL=STATION+'/Instance/Burette/body_link/Visual'
PRODUCER_ROOT='/World/TitrationStation'


def pose_reference(path=POSE_ZIP):
    from pxr import Usd,UsdGeom
    with zipfile.ZipFile(path) as archive:
        data=archive.read('task_10_titration_experiment/scene.usd')
    with tempfile.TemporaryDirectory(prefix='titration-reference-') as cache:
        scene=Path(cache)/'scene.usdc'
        scene.write_bytes(data)
        stage=Usd.Stage.Open(str(scene))
        if UsdGeom.GetStageMetersPerUnit(stage)!=1 or UsdGeom.GetStageUpAxis(stage)!='Z':
            raise ValueError('unexpected reference coordinates')
        transforms=UsdGeom.XformCache()
        poses={}
        for name in OBJECTS:
            prim=stage.GetPrimAtPath('/World/'+name)
            if not prim:
                raise ValueError('reference object missing: '+name)
            matrix=transforms.GetLocalToWorldTransform(prim)
            if max(abs(matrix[i][j]-(1 if i==j else 0)) for i in range(3) for j in range(3))>1e-9:
                raise ValueError('reference has non-translation placement')
            poses[str(prim.GetPath())]=[[float(matrix[i][j]) for j in range(4)] for i in range(4)]
    return dict(zip_sha256=sha256(path.read_bytes()).hexdigest(),source_scene_sha256=sha256(data).hexdigest(),
                entry='task_10_titration_experiment/scene.usd',units='meters',up_axis='Z',poses=poses)


def audit_changes(old,new,poses):
    from pxr import UsdGeom
    a={str(p.GetPath()):p for p in old.TraverseAll()}
    b={str(p.GetPath()):p for p in new.TraverseAll()}
    if set(a)!=set(b):
        raise ValueError('prim paths changed')
    tip=VISUAL+'/delivery_tip'
    types=[p for p in a if a[p].GetTypeName()!=b[p].GetTypeName()]
    if types!=[tip] or b[tip].GetTypeName()!='Mesh':
        raise ValueError('unexpected type change')
    allowed=set(UsdGeom.Mesh.GetSchemaAttributeNames(False))|set(UsdGeom.PointBased.GetSchemaAttributeNames(False))|{'extent','doubleSided','axis','height','radius'}
    differences=[]
    for path in a:
        pa,pb=a[path],b[path]
        if list(pa.GetAppliedSchemas())!=list(pb.GetAppliedSchemas()):
            raise ValueError('applied schemas changed: '+path)
        rel_a={r.GetName():str(r.GetTargets()) for r in pa.GetRelationships()}
        rel_b={r.GetName():str(r.GetTargets()) for r in pb.GetRelationships()}
        if rel_a!=rel_b:
            raise ValueError('relationships changed: '+path)
        aa={x.GetName():x for x in pa.GetAttributes()}
        bb={x.GetName():x for x in pb.GetAttributes()}
        for name in set(aa)|set(bb):
            def signature(attr):
                return None if attr is None else (str(attr.GetTypeName()),str(attr.Get()),
                    [(t,str(attr.Get(t))) for t in attr.GetTimeSamples()],str(attr.GetConnections()))
            if signature(aa.get(name))==signature(bb.get(name)):
                continue
            if path in poses and name=='xformOp:translate':
                pass
            elif path in (tip,VISUAL+'/liquid_precharge') and name in allowed:
                pass
            else:
                raise ValueError('unexpected attribute change: '+path+'.'+name)
            differences.append(path+'.'+name)
    cache=UsdGeom.XformCache()
    for path,matrix in poses.items():
        actual=cache.GetLocalToWorldTransform(b[path])
        if max(abs(actual[i][j]-matrix[i][j]) for i in range(4) for j in range(4))>1e-8:
            raise ValueError('reference placement mismatch')
    return dict(status='pass',prim_paths_identical=True,prim_count=len(a),changed_types=types,
                changed_attributes=sorted(differences),physics_unchanged_except_approved_root_placement=True,
                reference_poses_match=True)


def build(source=SOURCE,producer=PRODUCER,output=OUTPUT,reference=POSE_ZIP):
    from pxr import Gf,Sdf,Usd
    package=producer/'packages/station'
    receipt=json.loads((producer/'promotion_receipt.json').read_text())
    digest=sha256((package/'asset.usd').read_bytes()).hexdigest()
    if receipt['status']!='promoted' or receipt['package_id']!='traditional_titration_station_r4' or receipt['asset_sha256']!=digest:
        raise ValueError('r4 producer not qualified')
    root=output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    reference_data=pose_reference(reference)
    shutil.copytree(source,root,ignore=lambda directory,names:{'evidence'} if Path(directory)==source else set())
    evidence=root/'evidence'
    evidence.mkdir()
    for name in ('receiver_cavity.json','visual_liquid_recipe.json','titration_policy.json'):
        shutil.copy2(source/'evidence'/name,evidence/name)
    embedded=root/'deps/titration_assets'
    shutil.rmtree(embedded/'packages/station')
    shutil.copytree(package,embedded/'packages/station')
    shutil.copy2(producer/'promotion_receipt.json',embedded/'promotion_receipt.json')
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    asset=Usd.Stage.Open(str(package/'asset.usd'))
    for name in ('delivery_tip','liquid_precharge'):
        target=VISUAL+'/'+name
        origin=target.replace(STATION,PRODUCER_ROOT,1)
        Sdf.CopySpec(asset.GetRootLayer(),origin,stage.GetRootLayer(),target)
        prim=stage.GetPrimAtPath(target)
        for rel in prim.GetRelationships():
            rel.SetTargets([p.ReplacePrefix(Sdf.Path(PRODUCER_ROOT),Sdf.Path(STATION)) for p in rel.GetTargets()])
    for path,matrix in reference_data['poses'].items():
        stage.GetPrimAtPath(path).GetAttribute('xformOp:translate').Set(Gf.Vec3d(*matrix[3][:3]))
    stage.GetRootLayer().Save()
    old=Usd.Stage.Open(str(source/'scene.usd'))
    audit=audit_changes(old,stage,reference_data['poses'])
    scene_hash=sha256((root/'scene.usd').read_bytes()).hexdigest()
    audit.update(scene_sha256=scene_hash,source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest())
    (evidence/'physical_revision_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (evidence/'initial_pose_reference.json').write_text(json.dumps(reference_data,indent=2)+'\n')
    (evidence/'tip_geometry.json').write_text((package/'evidence/static_audit.json').read_text())
    policy=json.loads((evidence/'titration_policy.json').read_text())
    policy['scene_sha256']=scene_hash
    (evidence/'titration_policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    for name in ('task.yaml','metrics.yaml'):
        p=root/name
        data=yaml.safe_load(p.read_text())
        data['task_id']=TASK_ID
        p.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False))
    p=root/'task_config.py'
    p.write_text(p.read_text().replace('vr_r1_6','vr_r1_7'))
    p=root/'manifest.json'
    manifest=json.loads(p.read_text())
    for key in ('runtime_evidence','render_evidence','package_closure'):
        manifest.pop(key,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',source_revision=dict(package_id=source.name,scene_sha256=audit['source_scene_sha256']),
                    initial_pose_reference='evidence/initial_pose_reference.json',tip_geometry='evidence/tip_geometry.json')
    manifest['claims'].update(scene_cold_start_passes=0,scene_static_validation=False,materialized_state_machine_success_path=False)
    manifest['assets'].update(titration_station_package_id='traditional_titration_station_r4',
        titration_station_receipt_sha256=sha256((embedded/'promotion_receipt.json').read_bytes()).hexdigest())
    manifest['layout'].update(station_xyz_m=reference_data['poses'][STATION][3][:3],
        receiver_flask_xyz_m=reference_data['poses']['/World/obj_receiver_flask'][3][:3],
        stirrer_xyz_m=reference_data['poses']['/World/obj_magnetic_stirrer'][3][:3],
        initial_object_poses=reference_data['poses'])
    p.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    text=(source/'README_CN.md').read_text().replace('VR r1.6','VR r1.7')
    text+='\n玻璃滴嘴已修为向下渐细的中空Mesh，内部预充假液体同步收细；出口位置与所有Prim路径保留。\n五个任务对象初始位姿取自task_10_titration_experiment.zip；背景和内部装配沿用r1.6。\n'
    (root/'README_CN.md').write_text(text)
    shutil.copy2(ROOT/'docs/operations/titration-r17-color-guide.md',root/'COLOR_GUIDE_CN.md')
    return root


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--producer',type=Path,default=PRODUCER)
    p.add_argument('--out',type=Path,default=OUTPUT)
    p.add_argument('--reference',type=Path,default=POSE_ZIP)
    args=p.parse_args()
    print(build(args.source,args.producer,args.out,args.reference))

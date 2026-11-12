"""Assemble a task10-only Isaac4.5 VR delivery from immutable qualified inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.task10_vr_episode import GROUP, prepare_episode  # noqa: E402

TASK_ID='scientific_workbench_titration_task10_real_liquid_vr_r1'
SOURCE=ROOT/'outputs/task10_real_liquid_20261009/handoff_v3/scientific_workbench_titration_task10_real_liquid_r1'
OLD=ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_20260908/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_7'
SHARED=Path('/mnt/data/chenjiantong/scene_usd/zzh_fixed/task_10_titration_experiment')
OUT=ROOT/'outputs/task10_real_liquid_vr_r1_20261009/handoff'/TASK_ID


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(out=OUT, *, source=SOURCE, shared=SHARED, task_id=TASK_ID):
    import numpy as np
    from pxr import Usd,UsdGeom,UsdLux,UsdPhysics,UsdUtils,Sdf
    source,shared=Path(source).resolve(),Path(shared).resolve()
    if out.exists():
        raise FileExistsError(out)
    expected=json.loads((source/'assets/composed/manifest.json').read_text())['configuration']
    shared_stage=Usd.Stage.Open(str(shared/'scene_isaac45.usda'))
    delivered=json.loads(shared_stage.GetPrimAtPath('/World/obj_titration_station').GetAttribute('titration:pbd_config').Get())
    if delivered!=expected:
        raise ValueError('Clean export and source package configurations differ; pass matching --source and --shared')
    out.mkdir(parents=True)
    shutil.copytree(shared,out/'deps/task')
    shutil.copytree(OLD/'deps/environment',out/'deps/environment')
    stage=Usd.Stage.Open(Sdf.Layer.CreateNew(str(out/'scene.usd'),args={'format':'usda'}))
    layer=stage.GetRootLayer()
    layer.subLayerPaths=['./deps/task/scene_isaac45.usda']
    UsdGeom.SetStageMetersPerUnit(stage,1.)
    UsdGeom.SetStageUpAxis(stage,'Z')
    stage.SetMetadata('kilogramsPerUnit',1.)
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    Sdf.CreatePrimInLayer(layer,'/World')
    old=Usd.Stage.Open(str(OLD/'scene.usd')).Flatten(False)
    for path in ('/World/background','/World/Preview'):
        Sdf.CopySpec(old,path,layer,path)
    def localize(path):
        if not path or path.startswith('./deps/'):
            return path
        src=Path(path)
        if src.is_relative_to(OLD/'deps/environment'):
            return './deps/environment/'+src.relative_to(OLD/'deps/environment').as_posix()
        raise ValueError('Unexpected old-room dependency: '+path)
    UsdUtils.ModifyAssetPaths(layer,localize)
    # Retain the colleague's support and apparatus, not the old room's duplicates.
    for name in ('table','Beaker325ml','GraduatedCylinder250ml','PhysicsScene'):
        p=stage.GetPrimAtPath('/World/background/'+name)
        if p:
            p.SetActive(False)
    UsdLux.DomeLight.Define(stage,'/World/vr_direct_open_light').CreateIntensityAttr(750.)
    physics=Usd.Stage.Open(str(source/'scene/demo45.usda')).Flatten(False)
    Sdf.CopySpec(physics,'/World/PhysicsScene',layer,'/World/PhysicsScene')
    station=stage.GetPrimAtPath('/World/obj_titration_station')
    cfg=json.loads(station.GetAttribute('titration:pbd_config').Get())
    from scripts.task10_clock import runtime_settings,scene_capacity_settings
    timing=runtime_settings(cfg)
    bodies={}
    for item in cfg['systems'].values():
        body=item.get('container_body_path','/World/obj_titration_station/Instance/Burette/body_link')
        bodies[body]=np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(body)).ComputeLocalToWorldTransform(0)).tolist()
        prim=stage.GetPrimAtPath(item['particle_path'])
        for dest,source_attr,typ in [('vr:canonical_points','titration:initial_points',Sdf.ValueTypeNames.Point3fArray),('vr:canonical_velocities','titration:initial_velocities',Sdf.ValueTypeNames.Vector3fArray)]:
            prim.CreateAttribute(dest,typ).Set(prim.GetAttribute(source_attr).Get())
    station.CreateAttribute('vr:canonical_bodies',Sdf.ValueTypeNames.String).Set(json.dumps(bodies))
    group={name:np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath('/World/'+name)).ComputeLocalToWorldTransform(0)).tolist() for name in GROUP}
    station.CreateAttribute('vr:canonical_group',Sdf.ValueTypeNames.String).Set(json.dumps(group))
    node=stage.GetPrimAtPath('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/FlowController')
    code=node.GetAttribute('inputs:script').Get()
    original="        if db.per_instance_state.runtime is None:\n            db.per_instance_state.runtime = Task10PbdRuntime(stage,root)"
    replacement="        epoch = stage.GetPrimAtPath(root).GetAttribute('vr:episode_id').Get()\n        if db.per_instance_state.runtime is None or getattr(db.per_instance_state.runtime,'vr_epoch',None) != epoch:\n            db.per_instance_state.runtime = Task10PbdRuntime(stage,root)\n            db.per_instance_state.runtime.vr_epoch = epoch"
    if original not in code:
        raise ValueError('Source runtime constructor changed')
    node.GetAttribute('inputs:script').Set(code.replace(original,replacement))
    prepare_episode(stage)
    layer.Save()
    old_cfg=next(iter(runpy.run_path(str(OLD/'task_config.py'))['TASKS'].values()))
    old_cfg['scene_usd_file_path']={'scene1':'SCENE_PATH'}
    old_cfg['physx_scene_cfg']={'BroadphaseType':'GPU','EnableGPUDynamics':True,'SolverType':'TGS','TimeStepsPerSecond':timing['physics_hz'],'MinPositionIterationCount':timing['min_iterations'],'MaxPositionIterationCount':timing['max_iterations'],'EnableCCD':True}
    for name,value in scene_capacity_settings(cfg).items():
        old_cfg['physx_scene_cfg'][name[0].upper()+name[1:]]=value
    old_cfg['titration_contract'].update(liquid_model='GPU_PBD_with_controlled_conservative_source_to_tip_transfer',measurement_source='actual_particle_bulk_contact_after_mouth_crossing')
    config="from pathlib import Path\nTASKS = "+repr({task_id:old_cfg}).replace("'SCENE_PATH'","str(Path(__file__).resolve().parent / 'scene.usd')")+'\n'
    (out/'task_config.py').write_text(config)
    shutil.copy2(ROOT/'scripts/task10_vr_episode.py',out/'task10_vr_episode.py')
    shutil.copy2(ROOT/'scripts/task10_clock.py',out/'task10_clock.py')
    layers,assets,missing=UsdUtils.ComputeAllDependencies(str(out/'scene.usd'))
    paths=[Path(p.realPath) for p in layers if p.realPath]+[Path(p) for p in assets]
    if missing or any(not p.resolve().is_relative_to(out.resolve()) for p in paths):
        raise ValueError('VR dependencies escape package: '+str(missing))
    physics_paths=[str(p.GetPath()) for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]
    if physics_paths!=['/World/PhysicsScene']:
        raise ValueError(physics_paths)
    manifest={'package_id':task_id,'status':'assembled; qualification in evidence/delivery.json','runtime':'Isaac Sim4.5','source_package':str(source),'source_candidate_sha256':sha(source/'assets/composed/manifest.json'),'old_room_scene_sha256':sha(OLD/'scene.usd'),'scene_sha256':sha(out/'scene.usd'),'episode_api_sha256':sha(out/'task10_vr_episode.py'),'configuration':cfg,'physics_dt':timing['physics_dt'],'dependency_closure':{'unresolved':[],'layers':len(layers),'assets':len(assets)},'physics_scene_paths':physics_paths,'shared_source_files':{p.relative_to(shared).as_posix():sha(p) for p in shared.rglob('*') if p.is_file()},'limits':['Isaac4.5 scene integration; actual headset/collector not available.','Identity scene mount; group XY +/-1cm and yaw0 only.','Collector must call prepare_episode after randomization, before Play.','Stop and reset_episode before repeating or re-randomizing.']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(out)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--shared',type=Path,default=SHARED)
    parser.add_argument('--task-id',default=TASK_ID)
    args=parser.parse_args()
    build(args.out,source=args.source,shared=args.shared,task_id=args.task_id)

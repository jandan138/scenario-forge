"""Integrate a producer-repaired force balance into the immutable task09 layout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from scripts.balance_force_state import validate_target

ROOT=Path(__file__).resolve().parents[1]
TASK='scientific_workbench_solid_sample_weighing_vr_r1'
BALANCE='/World/obj_analytical_balance'


def build(asset, table_source, out, target_g=None, tolerance_g=None):
    from pxr import Usd, UsdGeom, UsdPhysics, UsdLux, Sdf, Gf
    out.mkdir(parents=True,exist_ok=True)
    deps=out/'deps'
    deps.mkdir(exist_ok=True)
    shutil.copytree(asset,deps/'balance',dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('incoming'))
    shutil.copytree(table_source/'deps/table',deps/'table',dirs_exist_ok=True)
    shutil.copytree(asset/'incoming/task_09_solid_weighing/SubUSDs',out/'SubUSDs',dirs_exist_ok=True)
    if (asset/'materials').exists():
        shutil.copytree(asset/'materials',out/'materials',dirs_exist_ok=True)
    source=asset/'incoming/task_09_solid_weighing/scene.usd'
    src=Usd.Stage.Open(str(asset/'scene_support.usda'),load=Usd.Stage.LoadNone)
    src.GetRootLayer().Export(str(out/'scene.usd'))
    stage=Usd.Stage.Open(str(out/'scene.usd'),load=Usd.Stage.LoadNone)
    manifest=json.loads((asset/'manifest.json').read_text())
    stage.RemovePrim(BALANCE)
    p=stage.DefinePrim(BALANCE,'Xform')
    p.GetReferences().AddReference('./deps/balance/asset.usda',BALANCE)
    p.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*manifest['source_root_translation']))
    for name,value in [('target_g',target_g),('tolerance_g',tolerance_g)]:
        if value is not None:
            if not 0 < value < float('inf'):
                raise ValueError('positive finite '+name+' required')
            p.GetAttribute('balance:'+name).Set(value)
    validate_target(p.GetAttribute('balance:target_g').Get(),p.GetAttribute('balance:tolerance_g').Get(),
                    manifest.get('grain_mass_g',10.),5,p.GetAttribute('balance:capacity_g').Get())
    stage.RemovePrim('/World/table')
    ptable=stage.DefinePrim('/World/table','Xform')
    ptable.GetReferences().AddReference('./deps/table/asset.usd','/World/table')
    stage.Load()
    cache=UsdGeom.BBoxCache(0,['default'])
    table_box=cache.ComputeWorldBound(ptable).ComputeAlignedRange()
    tabletop=float(table_box.GetMax()[2])
    p.GetAttribute('balance:tabletop_z').Set(tabletop)
    # Place the source instrument on the qualified table, retaining source XY.
    feet=cache.ComputeWorldBound(stage.GetPrimAtPath(BALANCE+'/Instance/Body/Feet')).ComputeAlignedRange()
    xyz=Gf.Vec3d(*manifest['source_root_translation'])
    xyz[2]+=tabletop-float(feet.GetMin()[2])+.0005
    p.GetAttribute('xformOp:translate').Set(xyz)
    p.GetRelationship('balance:container').SetTargets(['/World/obj_weighing_boat'])
    p.GetRelationship('balance:spoon').SetTargets(['/World/obj_sampling_spoon'])
    p.GetRelationship('balance:samples').SetTargets([f'/World/obj_grain_{i:02d}' for i in range(1,6)])
    sample_source=stage.GetPrimAtPath('/World/obj_weighing_bottle_body')
    source_xyz=UsdGeom.Xformable(sample_source).ComputeLocalToWorldTransform(0).ExtractTranslation()
    for i,(x,y) in enumerate([(-.012,-.008),(0,-.008),(.012,-.008),(-.007,.009),(.007,.009)],1):
        grain=stage.GetPrimAtPath(f'/World/obj_grain_{i:02d}')
        grain.GetAttribute('xformOp:translate').Set(source_xyz+Gf.Vec3d(x,y,.015))
    spoon=stage.GetPrimAtPath('/World/obj_sampling_spoon')
    home=UsdGeom.Xformable(spoon).ComputeLocalToWorldTransform(0).ExtractTranslation()
    p.GetAttribute('balance:spoon_home_xyz').Set(home)
    # Clear missing external table payloads by replacing that object only.
    # External source material paths are relocated without changing materials.
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith(BALANCE) or str(prim.GetPath()).startswith('/World/table'):
            continue
        for a in prim.GetAttributes():
            if a.GetTypeName()==Sdf.ValueTypeNames.Asset:
                v=a.Get()
                if v and 'SubUSDs/' in v.path:
                    a.Set(Sdf.AssetPath('./SubUSDs/'+v.path.split('SubUSDs/',1)[1]))
    scenes=[x for x in stage.Traverse() if x.IsA(UsdPhysics.Scene)]
    for scene in scenes:
        stage.RemovePrim(scene.GetPath())
    physics=UsdPhysics.Scene.Define(stage,'/World/PhysicsScene')
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1))
    physics.CreateGravityMagnitudeAttr(9.81)
    ps=physics.GetPrim()
    ps.AddAppliedSchema('PhysxSceneAPI')
    for name,kind,value in [('enableGPUDynamics',Sdf.ValueTypeNames.Bool,True),
                           ('broadphaseType',Sdf.ValueTypeNames.Token,'GPU'),
                           ('solverType',Sdf.ValueTypeNames.Token,'TGS'),
                           ('timeStepsPerSecond',Sdf.ValueTypeNames.UInt,120)]:
        ps.CreateAttribute('physxScene:'+name,kind).Set(value)
    if not any(x.IsA(UsdLux.DomeLight) for x in stage.Traverse()):
        light=UsdLux.DomeLight.Define(stage,'/World/WeighingLight')
        light.CreateIntensityAttr(900)
    stage.GetRootLayer().Save()
    compat=Usd.Stage.CreateNew(str(out/'scene_isaac41.usda'))
    compat.GetRootLayer().subLayerPaths=['./scene.usd']
    compat.OverridePrim(BALANCE+'/BalanceRuntime/Graph/OnPhysicsStep').CreateAttribute(
        'node:type',Sdf.ValueTypeNames.Token).Set('omni.isaac.core_nodes.OnPhysicsStep')
    for prim in compat.Traverse():
        for attr in prim.GetAttributes():
            if attr.GetTypeName()==Sdf.ValueTypeNames.Asset:
                value=attr.Get()
                if value and '/materials/isaac45/' in value.path:
                    attr.Set(Sdf.AssetPath(value.path.replace('/isaac45/','/isaac41/')))
    compat.GetRootLayer().Save()
    objects=[]
    for child in stage.GetPrimAtPath('/World').GetChildren():
        if child.GetName().startswith('obj_'):
            objects.append(str(child.GetPath()).replace('/World/','/World/_scene/',1))
            objects.extend(str(x.GetPath()).replace('/World/','/World/_scene/',1)
                           for x in Usd.PrimRange(child) if x!=child and x.HasAPI(UsdPhysics.RigidBodyAPI))
    for version,entry in [('45','scene.usd'),('41','scene_isaac41.usda')]:
        config=dict(scene_usd_file_path={'scene1':'__SCENE__'},obj_prim_list=objects,
                    layout_randomization={'table':'table','objects':[]},
                    robot_cfg={'position':[0,-1.02,.31],'orientation':[.7071067812,0,0,.7071067812]},
                    physx_scene_cfg={'BroadphaseType':'GPU','SolverType':'TGS','EnableGPUDynamics':True,'TimeStepsPerSecond':120},
                    weighing={k:p.GetAttribute('balance:'+k).Get() for k in ['target_g','tolerance_g','resolution_g','capacity_g']})
        text=repr({TASK:config}).replace("'__SCENE__'",f"str(Path(__file__).resolve().parent / '{entry}')")
        (out/('task_config.py' if version=='45' else 'task_config_isaac41.py')).write_text('from pathlib import Path\nTASKS = '+text+'\n')
    receipt=dict(package_id=TASK,status='candidate',producer_manifest=manifest,
                 source_scene_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 scene_sha256=hashlib.sha256((out/'scene.usd').read_bytes()).hexdigest(),
                 tabletop_z=tabletop,physics='GPU TGS 120 Hz',runtime_qualification='pending')
    (out/'manifest.json').write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset',type=Path,required=True)
    p.add_argument('--table-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--target-g',type=float)
    p.add_argument('--tolerance-g',type=float)
    a=p.parse_args()
    print(json.dumps(build(a.asset.resolve(),a.table_source.resolve(),a.out.resolve(),a.target_g,a.tolerance_g),indent=2))

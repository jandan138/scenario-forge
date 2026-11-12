"""Integrate a source-bound producer fluid scene and task10's conservative ledger."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.task10_clock import scene_capacity_settings  # noqa: E402
STATION = '/World/obj_titration_station'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(producer, out, emit_clearance_m=None):
    from pxr import Usd, UsdGeom, UsdPhysics, UsdLux, Sdf, Gf
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    shutil.copytree(producer/'package',out/'producer')
    shutil.copy2(producer/'manifest.json',out/'producer_manifest.json')
    config = json.loads((out/'producer_manifest.json').read_text())
    if 'receiver_mouth_radius_m' not in config:
        raise ValueError('Producer must declare source-derived mouth geometry')
    if emit_clearance_m is not None:
        config['recommended_emit_world_m'] = list(config['drop_origin_world_m'])
        config['recommended_emit_world_m'][2] -= emit_clearance_m
        config['controlled_outlet_clearance_m'] = emit_clearance_m
    origin = config['source_local_to_world'][3][:3]
    config['emit_body_local_m'] = [v-o for v,o in zip(config['recommended_emit_world_m'],origin)]
    stage = Usd.Stage.CreateNew(str(out/'task.usda'))
    stage.GetRootLayer().subLayerPaths = ['./producer/isaac41.usda']
    UsdGeom.SetStageMetersPerUnit(stage,1.)
    UsdGeom.SetStageUpAxis(stage,'Z')
    stage.SetMetadata('kilogramsPerUnit',1.)
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    node = STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController'
    stage.OverridePrim(STATION+'/Instance/Runtime/TitrationFlowGraph').SetActive(True)
    code = (ROOT/'scripts/task10_pbd_policy.py').read_text()+'\n\n'+(ROOT/'scripts/task10_pbd_runtime.py').read_text()
    stage.GetPrimAtPath(node).GetAttribute('inputs:script').Set(code)
    station = stage.GetPrimAtPath(STATION)
    station.CreateAttribute('titration:pbd_config',Sdf.ValueTypeNames.String).Set(json.dumps(config))
    station.GetAttribute('titration:reset_requested').Set(True)
    station.GetAttribute('titration:policy_version').Set('real_pbd_received_volume_v1')
    for name,typ,value in [('pbd_valid',Sdf.ValueTypeNames.Bool,False),('pbd_error',Sdf.ValueTypeNames.String,''),
                           ('released_volume_ml',Sdf.ValueTypeNames.Double,0.),('inflight_volume_ml',Sdf.ValueTypeNames.Double,0.),
                           ('source_total_volume_ml',Sdf.ValueTypeNames.Double,config['systems']['Source']['initial_volume_ml']),
                           ('conservation_error_ml',Sdf.ValueTypeNames.Double,0.),
                           ('source_particle_count',Sdf.ValueTypeNames.Int,config['systems']['Source']['count']),
                           ('receiver_particle_count',Sdf.ValueTypeNames.Int,config['systems']['Receiver']['count']),
                           ('falling_particle_count',Sdf.ValueTypeNames.Int,0)]:
        station.CreateAttribute('titration:'+name,typ).Set(value)
    station.GetRelationship('titration:receiverLiquidShader').SetTargets([
        config['systems']['Receiver']['material_path']+'/Shader'])
    station.GetRelationship('titration:receiverLiquidVisuals').SetTargets([
        config['systems']['Receiver']['system_path']])
    for item in config['systems'].values():
        p = stage.GetPrimAtPath(item['particle_path'])
        p.CreateAttribute('titration:initial_points',Sdf.ValueTypeNames.Point3fArray).Set(p.GetAttribute('points').Get())
        p.CreateAttribute('titration:initial_velocities',Sdf.ValueTypeNames.Vector3fArray).Set(p.GetAttribute('velocities').Get())
        stage.GetPrimAtPath(item['system_path']).CreateRelationship('simulationOwner').SetTargets([])
    stage.GetRootLayer().Save()
    for version in ['41','45']:
        clean = Usd.Stage.CreateNew(str(out/f'scene{version}.usda'))
        # Task/controller overrides strongest, then matching producer material
        # version. Do not let task's weak41 dependencies override45 materials.
        clean.GetRootLayer().subLayerPaths = ['./task.usda']
        UsdGeom.SetStageMetersPerUnit(clean,1.)
        UsdGeom.SetStageUpAxis(clean,'Z')
        clean.SetMetadata('kilogramsPerUnit',1.)
        clean.SetDefaultPrim(clean.GetPrimAtPath('/World'))
        clean.OverridePrim(STATION+'/Instance/Runtime/TitrationFlowGraph/OnPhysicsStep').CreateAttribute(
            'node:type',Sdf.ValueTypeNames.Token).Set('omni.isaac.core_nodes.OnPhysicsStep' if version=='41' else 'isaacsim.core.nodes.OnPhysicsStep')
        if version == '45':
            material_source = Usd.Stage.Open(str(out/'producer/materials/isaac45/materials.usda'))
            for p in material_source.TraverseAll():
                for a in p.GetAttributes():
                    if a.GetTypeName() == Sdf.ValueTypeNames.Asset and a.HasAuthoredValueOpinion():
                        value = a.Get()
                        absolute = Path(value.resolvedPath)
                        relative = absolute.relative_to(out.resolve())
                        clean.OverridePrim(p.GetPath()).CreateAttribute(a.GetName(),a.GetTypeName()).Set(Sdf.AssetPath('./'+relative.as_posix()))
        clean.GetRootLayer().Save()
        demo = Usd.Stage.CreateNew(str(out/f'demo{version}.usda'))
        demo.GetRootLayer().subLayerPaths = [f'./scene{version}.usda']
        UsdGeom.SetStageMetersPerUnit(demo,1.)
        UsdGeom.SetStageUpAxis(demo,'Z')
        demo.SetMetadata('kilogramsPerUnit',1.)
        demo.SetDefaultPrim(demo.GetPrimAtPath('/World'))
        scene = UsdPhysics.Scene.Define(demo,'/World/PhysicsScene')
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1))
        scene.CreateGravityMagnitudeAttr(9.81)
        prim = scene.GetPrim()
        prim.AddAppliedSchema('PhysxSceneAPI')
        for name,typ,value in [('enableGPUDynamics',Sdf.ValueTypeNames.Bool,True),
                               ('broadphaseType',Sdf.ValueTypeNames.Token,'GPU'),('solverType',Sdf.ValueTypeNames.Token,'TGS'),
                               ('enableCCD',Sdf.ValueTypeNames.Bool,True),
                               ('timeStepsPerSecond',Sdf.ValueTypeNames.UInt,round(1/config['runtime_contract']['physics_dt']))]:
            prim.CreateAttribute('physxScene:'+name,typ).Set(value)
        for bound in ('min','max'):
            value = config['runtime_contract'].get(f'scene_{bound}_position_iterations')
            if value is not None:
                prim.CreateAttribute(f'physxScene:{bound}PositionIterationCount',Sdf.ValueTypeNames.UInt).Set(value)
        for item in config['systems'].values():
            demo.GetPrimAtPath(item['system_path']).CreateRelationship('simulationOwner').SetTargets(['/World/PhysicsScene'])
        for name,value in scene_capacity_settings(config).items():
            prim.CreateAttribute('physxScene:'+name,Sdf.ValueTypeNames.UInt).Set(value)
        UsdLux.DomeLight.Define(demo,'/World/DemoLight').CreateIntensityAttr(700)
        demo.GetRootLayer().Save()
    manifest = {'status':'candidate','producer_manifest_sha256':sha(out/'producer_manifest.json'),
                'controller_sha256':hashlib.sha256(code.encode()).hexdigest(),'source_sha256':config['source_sha256'],
                'physics_dt':config['runtime_contract']['physics_dt'], 'configuration':config}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--emit-clearance-m',type=float)
    a = p.parse_args()
    print(build(a.producer.resolve(),a.out.resolve(),a.emit_clearance_m))

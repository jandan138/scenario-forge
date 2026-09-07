"""Compile the independent Fehling visual-reaction water-bath VR task."""
import json
from hashlib import sha256
from pathlib import Path
import runpy
import shutil
import argparse

from scripts.generate_visual_static_liquid_prototype import build_liquid_mesh, _frustum_volume
from scripts.generate_scientific_workbench_water_bath_tube_heat_vr import _author_mesh

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'outputs/scientific_workbench_water_bath_tube_heat_vr_r1_20260902'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r1'
OUT = ROOT/('outputs/'+TASK_ID+'_20260907')
PRODUCER = Path('/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/fehlings_open_tube15_r1_20260907/package')
TUBE = '/World/obj_sample_tube'
GRAPH = TUBE+'/ReactionRuntime/FehlingsGraph'
TEMPLATE = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_4_20260907/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_4/scene.usd'


def write_task_documents(root):
    import yaml
    # Keep the VR hint consistent with the actual sample-top and floor predicates.
    if (root/'task_config.py').exists() and (root/'manifest.json').exists():
        config=next(iter(runpy.run_path(str(root/'task_config.py'))['TASKS'].values()))
        sample_height=json.loads((root/'manifest.json').read_text())['sample_height_m']
        config['water_bath']['immersion_depth_range_m']=[sample_height+0.003,0.8793-0.837-0.001]
        config['scene_usd_file_path']={'scene1':'__SCENE__'}
        content=repr({TASK_ID:config}).replace("'__SCENE__'","str(Path(__file__).resolve().parent / 'scene.usd')")
        (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+content+'\n')
    task = {'schema_version':'task/v0.4','task_id':TASK_ID,
        'instruction':'拿起开口离心管，夹持浸入预热60°C水浴。30秒完成显色但继续有效加热至120秒；取出近竖直稳定观察3秒，不强制回架。',
        'container_semantics':'open_15ml_centrifuge_tube_as_glass_test_tube_substitute',
        'chemistry_simulated':False,'sample_preparation_in_scope':False,'positive_sample_only':True,
        'temperature_setpoint_c':60,'color_complete_seconds':30,'immersion_hold_seconds':120,
        'observation_seconds':3,'time_basis':'valid_simulation_time','invalid_immersion':'pause_without_reset',
        'steps':[{'id':name} for name in ('pick_tube','immerse_tube','heat_120s','withdraw_tube','observe_3s')],
        'runtime_state':{'prim':'/World/obj_sample_tube','heated_seconds':'fehlings:heated_seconds',
                         'success':'fehlings:success','reset':'fehlings:reset_requested'},
        'robot_grasp_verified':False}
    metrics={'schema_version':'metrics/v0.4','enabled':False,
        'aggregation':{'type':'weighted_progress_score','normalization':'declared_sum','primary_metric_id':'heat_120s'},
        'metrics':[{'id':name,'type':'rubric_condition','weight':weight,'source_ref':{'task':TASK_ID,'item':index}}
                   for name,weight,index in [('heat_120s',0.7,3),('observe_3s',0.3,5)]],
        'claim_boundary':'Portable criterion references only; not benchmark evaluation or robot policy proof.'}
    for name,data in [('task.yaml',task),('metrics.yaml',metrics)]:
        (root/name).write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False))


def author_readability(stage):
    from pxr import Sdf,Usd,UsdGeom
    paths=['/World/fluid_runtime','/World/fluid_runtime/ParticleSystem',
           '/World/fluid_runtime/ParticleSets/beaker_liquid',TUBE+'/VisualLiquid']
    for root in (TUBE+'/Visual','/World/obj_beaker/Visual',TUBE+'/VisualLiquid'):
        paths.extend(str(p.GetPath()) for p in Usd.PrimRange(stage.GetPrimAtPath(root)) if p.IsA(UsdGeom.Mesh))
    for path in paths:
        UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(path)).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
    return paths


def refresh_visual_only():
    from pxr import Usd
    root=OUT/'handoff'/TASK_ID
    path=root/'manifest.json'
    manifest=json.loads(path.read_text())
    if manifest['status']!='runtime_pending':
        raise ValueError('cannot modify a released package')
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    manifest['readability_shadow_overrides']=author_readability(stage)
    stage.GetRootLayer().Save()
    manifest['scene_sha256']=sha256((root/'scene.usd').read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    write_task_documents(root)


def build(refresh=False):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    from scenario_forge.adapters.vr_object_materialization import materialize_vr_object_subtrees

    root = OUT/'handoff'/TASK_ID
    if root.exists():
        if not refresh or ((root/'manifest.json').exists() and json.loads((root/'manifest.json').read_text())['status'] != 'runtime_pending'):
            raise FileExistsError(root)
        shutil.rmtree(root)
    shutil.copytree(BASE/'vr', root, ignore=lambda directory,names: {'evidence'} if Path(directory)==BASE/'vr' else set())
    (root/'evidence').mkdir()
    producer = json.loads((PRODUCER/'evidence/manifest.json').read_text())
    shutil.rmtree(root/'deps/objects/obj_sample_tube')
    shutil.copytree(PRODUCER, root/'deps/objects/obj_sample_tube')
    scene = root/'scene.usd'
    stage = Usd.Stage.Open(str(scene))
    pose = stage.GetPrimAtPath(TUBE).GetAttribute('xformOp:translate').Get()
    stage.RemovePrim(TUBE)
    tube = UsdGeom.Xform.Define(stage, TUBE)
    tube.GetPrim().GetReferences().AddReference('deps/objects/obj_sample_tube/asset.usd', producer['entrypoints']['asset_entry_prim'])
    attr = tube.GetPrim().GetAttribute('xformOp:translate')
    (attr if attr else tube.AddTranslateOp().GetAttr()).Set(pose)
    stage.GetRootLayer().Save()
    stage = None
    materialize_vr_object_subtrees(scene_path=scene, scene_prim_paths=[TUBE],
        runtime_prim_paths=['/World/_scene/obj_sample_tube'], evidence_path=root/'object_materialization.json')
    stage = Usd.Stage.Open(str(scene))
    water = stage.GetPrimAtPath('/World/fluid_runtime/LiquidMaterial/PreviewSurface')
    water.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(0.95,0.98,1.0))
    water.GetAttribute('inputs:emissiveColor').Set(Gf.Vec3f(0,0,0))
    water.GetAttribute('inputs:opacity').Set(0.16)
    tube = stage.GetPrimAtPath(TUBE)
    profile = producer['cavity_profile_m']
    volume = sum(_frustum_volume(a,b) for a,b in zip(profile,profile[1:]))
    sample = build_liquid_mesh(profile,3e-6/volume,radial_segments=64,meniscus_depth_m=0.00015)
    precip = build_liquid_mesh(profile,0.3e-6/volume,radial_segments=64,meniscus_depth_m=0.0001)
    UsdGeom.Xform.Define(stage,TUBE+'/VisualLiquid')
    for name, color, opacity, data in [('Sample',(0.4,0.72,0.95),0.55,sample), ('Sediment',(0.55,0.08,0.025),0.0,precip)]:
        material = UsdShade.Material.Define(stage,TUBE+'/VisualLiquid/Looks/'+name)
        shader = UsdShade.Shader.Define(stage,str(material.GetPath())+'/Shader')
        shader.CreateIdAttr('UsdPreviewSurface')
        for attr,kind,value in [('diffuseColor',Sdf.ValueTypeNames.Color3f,Gf.Vec3f(*color)),
                                ('opacity',Sdf.ValueTypeNames.Float,opacity),('roughness',Sdf.ValueTypeNames.Float,0.2)]:
            shader.CreateInput(attr,kind).Set(value)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
        group = UsdGeom.Xform.Define(stage,TUBE+'/VisualLiquid/'+name)
        for part in ('body','surface'):
            _author_mesh(stage,str(group.GetPath())+'/'+part,data[part],material,double_sided=True)
        if name == 'Sediment':
            UsdGeom.Imageable(group).CreateVisibilityAttr('invisible')
    values = [
        ('water_surface_z',Sdf.ValueTypeNames.Double,0.8793),
        ('bath_center_xyz',Sdf.ValueTypeNames.Double3,Gf.Vec3d(0.37,-0.028,0.8267)),
        ('bath_inner_radius',Sdf.ValueTypeNames.Double,0.032),
        ('bath_inner_floor_z',Sdf.ValueTypeNames.Double,0.837),
        ('sample_height_m',Sdf.ValueTypeNames.Double,sample['fill_height_m']),
        ('mouth_height_m',Sdf.ValueTypeNames.Double,producer['mouth_z_m']),
        ('outer_radius_m',Sdf.ValueTypeNames.Double,producer['outer_radius_m']),
        ('heated_seconds',Sdf.ValueTypeNames.Double,0.0),('color_progress',Sdf.ValueTypeNames.Double,0.0),
        ('observation_seconds',Sdf.ValueTypeNames.Double,0.0),('stage',Sdf.ValueTypeNames.Token,'ready'),
        ('success',Sdf.ValueTypeNames.Bool,False),('immersed',Sdf.ValueTypeNames.Bool,False),
        ('pose_available',Sdf.ValueTypeNames.Bool,False),('reset_requested',Sdf.ValueTypeNames.Bool,False)]
    for name,kind,value in values:
        tube.CreateAttribute('fehlings:'+name,kind).Set(value)
    template = Usd.Stage.Open(str(TEMPLATE))
    old = Sdf.Path('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph')
    UsdGeom.Xform.Define(stage,TUBE+'/ReactionRuntime')
    Sdf.CopySpec(template.GetRootLayer(),old,stage.GetRootLayer(),Sdf.Path(GRAPH))
    for prim in Usd.PrimRange(stage.GetPrimAtPath(GRAPH)):
        for attr in prim.GetAttributes():
            connections = attr.GetConnections()
            if connections:
                attr.SetConnections([p.ReplacePrefix(old,Sdf.Path(GRAPH)) for p in connections])
    code = (ROOT/'scripts/fehlings_state.py').read_text()+'\n'+(ROOT/'scripts/fehlings_usd_controller.py').read_text()
    stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Set(code)
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    shadows=author_readability(stage)
    stage.GetRootLayer().Save()
    tasks = runpy.run_path(str(BASE/'vr/task_config.py'))['TASKS']
    cfg = next(iter(tasks.values()))
    cfg['scene_usd_file_path'] = {'scene1': '__SCENE__'}
    cfg['water_bath'].update(hold_seconds=120.0, color_complete_seconds=30.0, observation_seconds=3.0,
                           thermal_transfer_simulated=False, container='open_15ml_centrifuge_tube_substitute')
    text = repr({TASK_ID: cfg}).replace("'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')")
    (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+text+'\n')
    manifest = {'package_id':TASK_ID,'status':'runtime_pending','runtime':'Isaac Sim 4.5',
        'entrypoints':{'scene':'scene.usd','vr_config':'task_config.py'},
        'source_scene_sha256':sha256((BASE/'vr/scene.usd').read_bytes()).hexdigest(),
        'scene_sha256':sha256(scene.read_bytes()).hexdigest(),'tube_asset_sha256':producer['asset_sha256'],
        'readability_shadow_overrides':shadows,
        'sample_volume_ml':3.0,'sample_height_m':sample['fill_height_m'],
        'claims':{'pbd_water':True,'particle_count':969,'real_chemistry':False,'robot_policy_success':False,
                  'continuous_robot_grasp_verified':False,'benchmark_success':False}}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (root/'README_CN.md').write_text('''# 斐林还原糖阳性显色：VR 替代容器演示

Isaac Sim 4.5 打开 scene.usd，允许脚本节点；整包保留依赖。不是标准玻璃试管实操教程。
初始使用开口 15 mL 离心管，预混约 3 mL 浅蓝样液；烧杯为语义预热 60°C 的 PBD 水浴。
拿管并保持夹持，近竖直浸泡，样液上沿低于水面 3 mm，管口高于水面 10 mm。
有效浸泡 30 秒完成砖红显色与假沉淀，但需累计到 120 秒才可取出。
出水后管底高于水面 10 mm、近竖直，在 2 cm 半径内停留 3 秒完成观察。
无效姿态或提前出水暂停计时和显色；重新浸入可继续。仿真暂停不计时。
通过 obj_sample_tube 的 fehlings:reset_requested=true 重置反应计时和外观。
热台不模拟升温；液体显色是确定性视觉演示，不是化学动力学；无机器人成功声明。
''')
    write_task_documents(root)
    print(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-candidate',action='store_true')
    parser.add_argument('--visual-refresh',action='store_true')
    args=parser.parse_args()
    if args.visual_refresh:
        refresh_visual_only()
    else:
        build(args.refresh_candidate)

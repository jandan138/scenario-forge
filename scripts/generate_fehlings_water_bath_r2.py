"""Build the 30/60/3-second Fehling r2 visual sedimentation task."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts import fehlings_r2_state as policy
from scripts.finalize_traditional_titration_vr_r14 import physical_state

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r1_20260907/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r1'
TASK_ID='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r2'
OUTPUT=ROOT/('outputs/'+TASK_ID+'_20260908')
TUBE='/World/obj_sample_tube'
GRAPH=TUBE+'/ReactionRuntime/FehlingsGraph'


def contract():
    return dict(version=policy.POLICY_VERSION,onset_seconds=30,cloud_peak_seconds=45,
                heating_complete_seconds=60,observation_seconds=3,sediment_max_volume_ml=.3,
                temperature_setpoint_c=60,thermal_transfer_simulated=False,time_basis='valid_simulation_time',
                invalid_immersion='pause_without_reset')


def write_task_documents(root):
    task=yaml.safe_load((root/'task.yaml').read_text())
    task.update(task_id=TASK_ID,instruction='夹持开口离心管近竖直浸入预热60°C水浴；累计有效浸泡30秒出现反应，60秒形成底部砖红沉淀、上层较清；取出稳定观察3秒。',
                color_complete_seconds=60,immersion_hold_seconds=60,reaction_policy=contract())
    task['steps']=[{'id':name} for name in ('pick_tube','immerse_tube','heat_60s','withdraw_tube','observe_3s')]
    (root/'task.yaml').write_text(yaml.safe_dump(task,allow_unicode=True,sort_keys=False))
    metrics=yaml.safe_load((root/'metrics.yaml').read_text())
    metrics['aggregation']['primary_metric_id']='heat_60s'
    for m in metrics['metrics']:
        if m['id']=='heat_120s':
            m['id']='heat_60s'
        m['source_ref']['task']=TASK_ID
    (root/'metrics.yaml').write_text(yaml.safe_dump(metrics,allow_unicode=True,sort_keys=False))
    cfg=next(iter(runpy.run_path(str(root/'task_config.py'))['TASKS'].values()))
    cfg['scene_usd_file_path']={'scene1':'__SCENE__'}
    cfg['water_bath'].update(hold_seconds=60.0,color_complete_seconds=60.0,observation_seconds=3.0,
                             reaction_onset_seconds=30.0,reaction_policy=contract())
    text=repr({TASK_ID:cfg}).replace("'__SCENE__'","str(Path(__file__).resolve().parent / 'scene.usd')")
    (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+text+'\n')


def build(source=SOURCE,output=OUTPUT):
    from pxr import Gf,Sdf,Usd,UsdGeom
    root=output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source,root,ignore=lambda directory,names: {'evidence','.thumbs'} if Path(directory)==source else set())
    evidence=root/'evidence'
    evidence.mkdir()
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    tube=stage.GetPrimAtPath(TUBE)
    producer=json.loads((root/'deps/objects/obj_sample_tube/evidence/manifest.json').read_text())
    profile=producer['cavity_profile_m']
    top=float(tube.GetAttribute('fehlings:sample_height_m').Get())
    data=policy.geometry(profile,top,0)
    for label in ('Sample','Sediment'):
        group=stage.GetPrimAtPath(TUBE+'/VisualLiquid/'+label)
        UsdGeom.Imageable(group).GetVisibilityAttr().Set('inherited')
        for part in ('body','surface'):
            p=stage.GetPrimAtPath(str(group.GetPath())+'/'+part)
            p.RemoveProperty('normals')
            mesh=UsdGeom.Mesh(p)
            counts,indices=policy.mesh_topology(part)
            points=data[label][part]
            mesh.GetPointsAttr().Set([Gf.Vec3f(*v) for v in points])
            mesh.GetFaceVertexCountsAttr().Set(counts)
            mesh.GetFaceVertexIndicesAttr().Set(indices)
            mesh.GetSubdivisionSchemeAttr().Set('none')
            mesh.GetExtentAttr().Set([Gf.Vec3f(*[min(v[i] for v in points) for i in range(3)]),
                                      Gf.Vec3f(*[max(v[i] for v in points) for i in range(3)])])
            mesh.GetVisibilityAttr().Set('invisible' if label=='Sediment' else 'inherited')
            tube.CreateRelationship('fehlings:'+label.lower()+part.capitalize()).SetTargets([p.GetPath()])
        shader=stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/'+label+'/Shader')
        tube.CreateRelationship('fehlings:'+label.lower()+'Shader').SetTargets([shader.GetPath()])
        if label=='Sediment':
            shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(.70,.18,.07))
            shader.GetAttribute('inputs:roughness').Set(.65)
            shader.GetAttribute('inputs:opacity').Set(0.0)
    for name,kind,value in (
        ('policy_version',Sdf.ValueTypeNames.String,policy.POLICY_VERSION),
        ('reaction_stage',Sdf.ValueTypeNames.Token,'warming'),
        ('sediment_progress',Sdf.ValueTypeNames.Double,0.0),
        ('sediment_height_m',Sdf.ValueTypeNames.Double,0.0),
        ('cavity_profile_m',Sdf.ValueTypeNames.Double2Array,[Gf.Vec2d(*v) for v in profile])):
        tube.CreateAttribute('fehlings:'+name,kind,custom=True).Set(value)
    # Keep only the established immersion predicate, without obsolete r1 functions.
    source_policy=(ROOT/'scripts/fehlings_state.py').read_text()
    predicate=next(n for n in ast.parse(source_policy).body if isinstance(n,ast.FunctionDef) and n.name=='geometry_flags')
    code=ast.get_source_segment(source_policy,predicate)+'\n'+Path(policy.__file__).read_text()+'\n'+(ROOT/'scripts/fehlings_r2_usd_controller.py').read_text()
    compile(code,'<fehlings r2>','exec')
    stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Set(code)
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    stage.GetRootLayer().Save()
    old=Usd.Stage.Open(str(source/'scene.usd'))
    if physical_state(old)!=physical_state(stage):
        raise ValueError('physical scene changed')
    digest=sha256((root/'scene.usd').read_bytes()).hexdigest()
    (evidence/'physical_revision_audit.json').write_text(json.dumps(dict(status='pass',scene_sha256=digest,
        source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest(),
        physical_content_identical=True,physical_prims=len(physical_state(stage))),indent=2)+'\n')
    path=root/'manifest.json'
    manifest=json.loads(path.read_text())
    for key in ('runtime_cold_starts','runtime_reports','render_evidence','closure'):
        manifest.pop(key,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',scene_sha256=digest,
                    source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest(),reaction_policy=contract())
    manifest['claims'].update(scene_fixture_verified=False,visual_reaction_verified=False)
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    (evidence/'reaction_recipe.json').write_text(json.dumps(dict(policy=contract(),profile=profile,
        sample_top_m=top,sediment_final_height_m=policy.geometry(profile,top,1)['sediment_height_m'],
        controller_sha256=sha256(code.encode()).hexdigest(),scene_sha256=digest),indent=2)+'\n')
    write_task_documents(root)
    (root/'README_CN.md').write_text('''# 斐林水浴显色 r2：30秒出现现象，60秒完成

Isaac Sim 4.5 打开 scene.usd 并允许脚本节点；保留 deps 和 task_config.py。
夹持开口15 mL离心管近竖直浸入预热60°C水浴；原浸泡范围与姿态判定不变。
0–30秒保持浅蓝；30–45秒逐渐浑浊、偏橙棕；45–60秒底部砖红沉淀增厚、上层变清。
累计有效浸泡60秒即可取出，近竖直且在2 cm半径内稳定观察3秒成功。
无效浸泡暂停，不清零；重置恢复初始外观与状态，成功锁定至重置。
时间为仿真时间。没有温度求解、化学动力学或沉淀颗粒物理；底部沉淀是动态假几何。
水浴保留原969个PBD水粒子。离心管是教学替代容器，不代表标准玻璃试管实操。

节点、属性和读取方法见 [颜色与沉淀教学文档](COLOR_GUIDE_CN.md)。
''')
    shutil.copy2(ROOT/'docs/operations/fehlings-r2-color-guide.md',root/'COLOR_GUIDE_CN.md')
    return root


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--out',type=Path,default=OUTPUT)
    args=parser.parse_args()
    print(build(args.source,args.out))

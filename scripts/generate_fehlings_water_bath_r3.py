"""Replace PBD with collision-free visual water and sample-region thermal contact."""
import argparse
import ast
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.fehlings_r3_contact import CONTACT_POLICY_VERSION,water_mesh
from scripts.finalize_traditional_titration_vr_r14 import physical_state

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r2_20260908/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r2'
TASK_ID='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3'
OUTPUT=ROOT/('outputs/'+TASK_ID+'_20260909')
TUBE='/World/obj_sample_tube'
BEAKER='/World/obj_beaker'
WATER=BEAKER+'/VisualWater'
GRAPH=TUBE+'/ReactionRuntime/FehlingsGraph'

COMPUTE='''def compute(db):
    global _state,_last_geometry_progress
    stage=omni.usd.get_context().get_stage()
    if stage is None:
        return True
    tube_path=str(db.node.get_prim_path()).split('/ReactionRuntime/')[0]
    tube=stage.GetPrimAtPath(tube_path)
    if not tube:
        return True
    def put(name,value):
        tube.GetAttribute('fehlings:'+name).Set(value)
    if tube.GetAttribute('fehlings:reset_requested').Get():
        _state,_last_geometry_progress=initial_state(),None
        put('reset_requested',False)
        put('immersed',False)
        put('bath_contact',False)
        _apply_state(stage,tube)
        return True
    bath=_target(stage,tube,'bath')
    water=_target(stage,tube,'bathWater')
    dc=_dynamic_control.acquire_dynamic_control_interface()
    handle=dc.get_rigid_body(tube_path)
    bath_handle=dc.get_rigid_body(str(bath.GetPath()))
    if not handle or not bath_handle:
        put('pose_available',False)
        put('immersed',False)
        put('bath_contact',False)
        return True
    pose=dc.get_rigid_body_pose(handle)
    bath_pose=dc.get_rigid_body_pose(bath_handle)
    xyz=Gf.Vec3d(pose.p.x,pose.p.y,pose.p.z)
    bath_xyz=Gf.Vec3d(bath_pose.p.x,bath_pose.p.y,bath_pose.p.z)
    rotation=Gf.Rotation(Gf.Quatd(pose.r.w,Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z)))
    bath_rotation=Gf.Rotation(Gf.Quatd(bath_pose.r.w,Gf.Vec3d(bath_pose.r.x,bath_pose.r.y,bath_pose.r.z)))
    inverse=bath_rotation.GetInverse()
    world_axis=rotation.TransformDir(Gf.Vec3d(0,0,1))
    origin=tuple(inverse.TransformDir(xyz-bath_xyz))
    axis=tuple(inverse.TransformDir(world_axis))
    profile=[tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    water_profile=[tuple(v) for v in water.GetAttribute('water:profile_m').Get()]
    contact=bath_contact(profile,float(tube.GetAttribute('fehlings:sample_height_m').Get()),origin,axis,water_profile)
    withdrawn=(not contact and world_axis[2]>=math.cos(math.radians(20)) and origin[2]>=water_profile[-1][0]+.010)
    _state=advance(_state,max(0.0,float(db.inputs.deltaSeconds)),contact,withdrawn,tuple(xyz))
    put('pose_available',True)
    put('immersed',contact)
    put('bath_contact',contact)
    put('bath_center_xyz',bath_xyz)
    put('water_surface_z',float((bath_xyz+bath_rotation.TransformDir(Gf.Vec3d(0,0,water_profile[-1][0])))[2]))
    _apply_state(stage,tube)
    return True
'''


def contract():
    return dict(version=CONTACT_POLICY_VERSION,onset_seconds=30,cloud_peak_seconds=45,
                heating_complete_seconds=60,observation_seconds=3,time_basis='sample_region_contact_time',
                contact_rule='sample_region_water_volume_intersection',outside_water='pause_without_reset',
                heating_tilt_limit=None,complete_immersion_required=False,water_fill_height_ratio=.8,
                pbd_water=False,visual_water_collision=False,thermal_transfer_simulated=False)


def measure_water(stage):
    from pxr import Gf,UsdGeom
    cache=UsdGeom.XformCache()
    inverse=cache.GetLocalToWorldTransform(stage.GetPrimAtPath(BEAKER)).GetInverse()
    def local_points(path):
        prim=stage.GetPrimAtPath(path)
        transform=cache.GetLocalToWorldTransform(prim)*inverse
        return [transform.Transform(Gf.Vec3d(*v)) for v in prim.GetAttribute('points').Get()]
    points=local_points(BEAKER+'/Visual/Source/Beaker_Hollow_Body/Beaker_Hollow_Body_Mesh')
    levels=defaultdict(list)
    for x,y,z in points:
        levels[round(z,6)].append((x*x+y*y)**.5)
    if len(levels)!=3:
        raise ValueError('unrecognized qualified beaker geometry')
    bottom,floor,top=sorted(levels)
    r_floor=max(levels[floor])
    r_top=min(levels[top])
    rim=min(v[2] for v in local_points(BEAKER+'/Visual/Source/Rolled_Rim/Torus'))
    usable_rim=min(top,rim)
    low=floor+.0001
    high=low+.8*(usable_rim-low)
    def radius(z):
        return r_floor+(r_top-r_floor)*(z-floor)/(top-floor)-.0001
    return dict(profile_m=[[low,radius(low)],[high,radius(high)]],fill_height_ratio=.8,
                measured_inner_floor_m=floor,usable_rim_m=usable_rim,measured_outer_bottom_m=bottom,
                radial_clearance_m=.0001,floor_clearance_m=.0001,
                material=dict(diffuseColor=[.95,.98,1.0],opacity=.12,ior=1.333,roughness=.02))


def write_task_documents(root):
    task=yaml.safe_load((root/'task.yaml').read_text())
    task.update(task_id=TASK_ID,instruction='让装有样液的试管下段接触水浴；浅浸、倾斜或部分接触均可累计。30秒开始变化、60秒完成；取出后近竖直稳定观察3秒。',
                reaction_policy=contract(),time_basis='sample_region_contact_time',invalid_immersion='pause_without_reset')
    (root/'task.yaml').write_text(yaml.safe_dump(task,allow_unicode=True,sort_keys=False))
    metrics=yaml.safe_load((root/'metrics.yaml').read_text())
    for item in metrics['metrics']:
        item['source_ref']['task']=TASK_ID
    (root/'metrics.yaml').write_text(yaml.safe_dump(metrics,allow_unicode=True,sort_keys=False))
    cfg=next(iter(runpy.run_path(str(root/'task_config.py'))['TASKS'].values()))
    for group in cfg['layout_randomization']['objects']:
        group['objs']=[n for n in group['objs'] if n!='fluid_runtime']
    cfg['physx_scene_cfg'].pop('GpuMaxParticleContacts',None)
    cfg['water_bath'].pop('pbd_particle_count',None)
    cfg['water_bath'].pop('immersion_depth_range_m',None)
    cfg['water_bath'].update(reaction_policy=contract(),water_representation='visual_mesh',contact_rule=contract()['contact_rule'])
    cfg['scene_usd_file_path']={'scene1':'__SCENE__'}
    text=repr({TASK_ID:cfg}).replace("'__SCENE__'","str(Path(__file__).resolve().parent / 'scene.usd')")
    (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+text+'\n')


def controller(script):
    lines=script.splitlines(keepends=True)
    nodes=[n for n in ast.parse(script).body if isinstance(n,ast.FunctionDef) and n.name in ('geometry_flags','compute')]
    if len(nodes)!=2:
        raise ValueError('unexpected r2 controller')
    for n in sorted(nodes,key=lambda n:n.lineno,reverse=True):
        del lines[n.lineno-1:n.end_lineno]
    code=''.join(lines)+'\n'+(ROOT/'scripts/fehlings_r3_contact.py').read_text()+'\n'+COMPUTE
    compile(code,'<r3 controller>','exec')
    return code


def build(source=SOURCE,output=OUTPUT):
    from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
    root=output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source,root,ignore=lambda directory,names:{'evidence','.thumbs'} if Path(directory)==source else set())
    evidence=root/'evidence'
    evidence.mkdir()
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    before=physical_state(stage)
    recipe=measure_water(stage)
    proxy=BEAKER+'/__aan_pbd_collision_proxy'
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith(proxy) and prim.HasAttribute('physics:collisionEnabled') and prim.GetAttribute('physics:collisionEnabled').Get():
            raise ValueError('cannot remove an active beaker collider')
    stage.RemovePrim('/World/fluid_runtime')
    stage.RemovePrim(proxy)
    for prim in stage.Traverse():
        if prim.GetTypeName()=='PhysicsScene':
            prim.RemoveProperty('physxScene:gpuMaxParticleContacts')
    water=UsdGeom.Xform.Define(stage,WATER).GetPrim()
    water.CreateAttribute('water:profile_m',Sdf.ValueTypeNames.Double2Array,custom=True).Set([Gf.Vec2d(*v) for v in recipe['profile_m']])
    water.CreateAttribute('water:fill_height_ratio',Sdf.ValueTypeNames.Double,custom=True).Set(.8)
    material=UsdShade.Material.Define(stage,WATER+'/Looks/Water')
    shader=UsdShade.Shader.Define(stage,str(material.GetPath())+'/Shader')
    shader.CreateIdAttr('UsdPreviewSurface')
    for name,kind,value in [('diffuseColor',Sdf.ValueTypeNames.Color3f,Gf.Vec3f(.95,.98,1)),
                            ('opacity',Sdf.ValueTypeNames.Float,.12),('ior',Sdf.ValueTypeNames.Float,1.333),
                            ('roughness',Sdf.ValueTypeNames.Float,.02),('emissiveColor',Sdf.ValueTypeNames.Color3f,Gf.Vec3f(0,0,0))]:
        shader.CreateInput(name,kind).Set(value)
    shader.CreateOutput('surface',Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    for name,(points,counts,indices) in water_mesh(recipe['profile_m']).items():
        mesh=UsdGeom.Mesh.Define(stage,WATER+'/'+name)
        mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
        mesh.CreateFaceVertexCountsAttr(counts)
        mesh.CreateFaceVertexIndicesAttr(indices)
        mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateExtentAttr([Gf.Vec3f(*[min(p[i] for p in points) for i in range(3)]),Gf.Vec3f(*[max(p[i] for p in points) for i in range(3)])])
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    tube=stage.GetPrimAtPath(TUBE)
    tube.GetAttribute('fehlings:policy_version').Set(CONTACT_POLICY_VERSION)
    tube.CreateAttribute('fehlings:bath_contact',Sdf.ValueTypeNames.Bool,custom=True).Set(False)
    tube.CreateRelationship('fehlings:bath').SetTargets([BEAKER])
    tube.CreateRelationship('fehlings:bathWater').SetTargets([WATER])
    transform=UsdGeom.XformCache().GetLocalToWorldTransform(water)
    tube.GetAttribute('fehlings:water_surface_z').Set(transform.Transform(Gf.Vec3d(0,0,recipe['profile_m'][-1][0]))[2])
    tube.GetAttribute('fehlings:bath_inner_floor_z').Set(transform.Transform(Gf.Vec3d(0,0,recipe['profile_m'][0][0]))[2])
    tube.GetAttribute('fehlings:bath_inner_radius').Set(recipe['profile_m'][-1][1])
    attr=stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script')
    attr.Set(controller(attr.Get()))
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    stage.GetRootLayer().Save()
    after=physical_state(stage)
    def allowed(path):
        return path.startswith(('/World/fluid_runtime',proxy))
    if {p:v for p,v in before.items() if not allowed(p)}!={p:v for p,v in after.items() if not allowed(p)}:
        raise ValueError('non-PBD physical content changed')
    for p in stage.TraverseAll():
        if 'Particle' in p.GetTypeName() or any('Particle' in x for x in p.GetAppliedSchemas()):
            raise ValueError('remaining particle component')
    digest=sha256((root/'scene.usd').read_bytes()).hexdigest()
    (evidence/'physical_revision_audit.json').write_text(json.dumps(dict(status='pass',scene_sha256=digest,
        source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest(),
        non_pbd_physics_identical=True,removed_physical_prims=[p for p in before if p not in after]),indent=2)+'\n')
    (evidence/'water_recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    path=root/'manifest.json'
    manifest=json.loads(path.read_text())
    for key in ('runtime_cold_starts','runtime_reports','render_evidence','closure'):
        manifest.pop(key,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',scene_sha256=digest,
                    source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest(),reaction_policy=contract(),
                    visual_water='evidence/water_recipe.json')
    manifest['claims'].update(pbd_water=False,particle_count=0,scene_fixture_verified=False,visual_reaction_verified=False)
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    write_task_documents(root)
    (root/'README_CN.md').write_text('''# 斐林水浴 r3：无碰撞假水，接触即可累计

Isaac Sim 4.5 打开 scene.usd 并允许脚本节点；保留依赖与task_config.py。
烧杯内为80%有效高度的水状假液体，没有碰撞；杯壁、杯口和杯底仍保留实体碰撞。
含样液的下段进入水体就累计，不要求特定倾角、完整浸没或管口高于水面。
离水暂停，重入继续；累计30秒开始变化，60秒完成。
取出后仍需近竖直、在2 cm半径内稳定观察3秒，成功锁定至重置。
样液/沉淀、变色和增长规则沿用r2。没有PBD水、温度求解、残热或真实化学动力学。
假水随杯子移动，不模拟洒水。仅试管上段触水不会累计。

节点与读取方法见 [颜色与假水教学文档](COLOR_GUIDE_CN.md)。
''')
    shutil.copy2(ROOT/'docs/operations/fehlings-r3-color-guide.md',root/'COLOR_GUIDE_CN.md')
    return root


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--out',type=Path,default=OUTPUT)
    a=p.parse_args()
    print(build(a.source,a.out))

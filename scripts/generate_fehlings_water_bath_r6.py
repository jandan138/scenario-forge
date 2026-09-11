"""Derive five equal-height material regions and a 30 s color reaction from r5."""
import argparse
import ast
from hashlib import sha256
import json
import math
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.fehlings_r2_state import fitted_region, mesh_topology, radius_at, RADIAL
from scripts.fehlings_r6_state import (POLICY_VERSION, LAYER_COUNT, COMPLETE_SECONDS, ONSET_SECONDS,
                                     COLOR_NAMES, PALETTE, OPACITIES, ROUGHNESSES, appearance, layer_key_times)
from scripts.finalize_traditional_titration_vr_r14 import physical_state
from scripts.generate_fehlings_water_bath_r3 import TUBE, GRAPH, contract as contact_contract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5_20260911/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6'
OUTPUT = ROOT/('outputs/'+TASK_ID+'_20260911')


def contract():
    result = contact_contract()
    result.pop('cloud_peak_seconds')
    result.update(version=POLICY_VERSION, contact_policy_version='visual_water_contact_v3',
                  onset_seconds=ONSET_SECONDS, heating_complete_seconds=COMPLETE_SECONDS,
                  layer_count=LAYER_COUNT, layer_height_fractions=[1/LAYER_COUNT]*LAYER_COUNT,
                  layer_order='bottom_to_top', geometry_updates=False, visibility_updates=False,
                  color_stages=list(COLOR_NAMES), layer_key_times_seconds=[layer_key_times(i) for i in range(LAYER_COUNT)],
                  material_inputs=['diffuseColor','opacity','roughness'], final_appearance='all_layers_turbid_orange_red')
    # Use JSON-native lists in both Python config and YAML/manifest outputs.
    return json.loads(json.dumps(result))


def fixed_regions(profile, top):
    floor = profile[0][0]
    if not floor < top <= profile[-1][0]:
        raise ValueError('invalid sample height')
    result = []
    for i in range(LAYER_COUNT):
        low,high = floor+(top-floor)*i/LAYER_COUNT, floor+(top-floor)*(i+1)/LAYER_COUNT
        shape = fitted_region(profile,low,high,.00015 if i==LAYER_COUNT-1 else 0)
        points = shape['body'][:-1]
        counts,indices = mesh_topology('body')
        counts,indices = counts[:-RADIAL],indices[:-3*RADIAL]
        normals = []
        for x,y,z in points:
            slope = (radius_at(profile,min(profile[-1][0],z+1e-6))
                     - radius_at(profile,max(floor,z-1e-6))) / (min(profile[-1][0],z+1e-6)-max(floor,z-1e-6))
            radius = math.hypot(x,y)
            length = math.sqrt(1+slope*slope)
            normals.append((x/radius/length,y/radius/length,-slope/length))
        # Only the outer bottom and the top meniscus are capped. No internal discs.
        if i==0:
            offset = len(points)
            points += shape['body'][:RADIAL]+[(0,0,low)]
            counts += [3]*RADIAL
            indices += [offset+v for j in range(RADIAL) for v in (RADIAL,(j+1)%RADIAL,j)]
            normals += [(0,0,-1)]*(RADIAL+1)
        if i==LAYER_COUNT-1:
            offset = len(points)
            points += shape['surface']
            caps,cap_indices = mesh_topology('surface')
            counts += caps
            indices += [offset+v for v in cap_indices]
            normals += [(0,0,1)]*len(shape['surface'])
        result.append(dict(low=low,high=high,points=points,counts=counts,indices=indices,normals=normals))
    return result


def controller(source_script):
    tree = ast.parse(source_script)
    replace = {'initial_state','advance','appearance','setup','cleanup','_target','_apply_state'}
    inherited = [ast.get_source_segment(source_script,n) for n in tree.body
                 if isinstance(n,ast.FunctionDef) and n.name not in replace]
    code = ((ROOT/'scripts/fehlings_r6_state.py').read_text()+'\n'
            +(ROOT/'scripts/fehlings_r6_usd_controller.py').read_text()+'\n'+'\n\n'.join(inherited)+'\n')
    compile(code,'<r6 controller>','exec')
    return code


def write_task_documents(root):
    task = yaml.safe_load((root/'task.yaml').read_text())
    task.update(task_id=TASK_ID, color_complete_seconds=COMPLETE_SECONDS, immersion_hold_seconds=COMPLETE_SECONDS,
                instruction='让装有样液的试管下段接触水浴；五层样液依次经过蓝、绿、黄、橙、橙红，累计触水30秒完成显色，取出后近竖直稳定观察3秒。离水暂停，重新接触继续。',
                reaction_policy=contract())
    for step in task['steps']:
        if step['id'].startswith('heat_'):
            step['id'] = 'heat_30s'
    task['runtime_state']['layer_progress'] = 'fehlings:layer_progress'
    (root/'task.yaml').write_text(yaml.safe_dump(task,allow_unicode=True,sort_keys=False))
    metrics = yaml.safe_load((root/'metrics.yaml').read_text())
    metrics['aggregation']['primary_metric_id'] = 'heat_30s'
    for metric in metrics['metrics']:
        metric['source_ref']['task'] = TASK_ID
        if metric['id'].startswith('heat_'):
            metric['id'] = 'heat_30s'
    (root/'metrics.yaml').write_text(yaml.safe_dump(metrics,allow_unicode=True,sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root/'task_config.py'))['TASKS'].values()))
    cfg['water_bath'].update(hold_seconds=COMPLETE_SECONDS,color_complete_seconds=COMPLETE_SECONDS,
                             reaction_onset_seconds=ONSET_SECONDS,reaction_policy=contract())
    cfg['scene_usd_file_path'] = {'scene1':'__SCENE__'}
    text = repr({TASK_ID:cfg}).replace("'__SCENE__'","str(Path(__file__).resolve().parent / 'scene.usd')")
    (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+text+'\n')
    shutil.copy2(ROOT/'docs/operations/fehlings-r6-color-guide.md',root/'COLOR_GUIDE_CN.md')


def build(source=SOURCE, output=OUTPUT):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    source = source.resolve()
    manifest = json.loads((source/'manifest.json').read_text())
    source_sha = sha256((source/'scene.usd').read_bytes()).hexdigest()
    if (manifest['package_id']!='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5'
            or manifest['status']!='pass' or manifest['scene_sha256']!=source_sha):
        raise ValueError('qualified unmodified r5 source required')
    root = output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source,root,ignore=lambda directory,names: {'evidence','.thumbs'} if Path(directory)==source else set())
    evidence = root/'evidence'
    evidence.mkdir()
    shutil.copy2(source/'evidence/water_recipe.json',evidence/'water_recipe.json')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    before = physical_state(stage)
    tube = stage.GetPrimAtPath(TUBE)
    profile = [tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    top = float(tube.GetAttribute('fehlings:sample_height_m').Get())
    regions = fixed_regions(profile,top)
    visual = TUBE+'/VisualLiquid'
    for child in ('Sample','Sediment','Looks'):
        stage.RemovePrim(visual+'/'+child)
    for name in ('sampleShader','sedimentShader','sampleBody','sampleSurface','sedimentBody','sedimentSurface',
                 'sediment_height_m','sediment_height_fraction','sediment_progress'):
        tube.RemoveProperty('fehlings:'+name)
    shaders,meshes = [],[]
    for i,region in enumerate(regions):
        label = 'Layer'+str(i)
        material = UsdShade.Material.Define(stage,visual+'/Looks/'+label)
        shader = UsdShade.Shader.Define(stage,str(material.GetPath())+'/Shader')
        shader.CreateIdAttr('UsdPreviewSurface')
        for name,kind,value in [('diffuseColor',Sdf.ValueTypeNames.Color3f,Gf.Vec3f(*PALETTE[0])),
                                ('opacity',Sdf.ValueTypeNames.Float,OPACITIES[0]),
                                ('roughness',Sdf.ValueTypeNames.Float,ROUGHNESSES[0])]:
            shader.CreateInput(name,kind).Set(value)
        shader.CreateOutput('surface',Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
        mesh = UsdGeom.Mesh.Define(stage,visual+'/'+label)
        mesh.CreatePointsAttr([Gf.Vec3f(*v) for v in region['points']])
        mesh.CreateFaceVertexCountsAttr(region['counts'])
        mesh.CreateFaceVertexIndicesAttr(region['indices'])
        mesh.CreateNormalsAttr([Gf.Vec3f(*v) for v in region['normals']])
        mesh.SetNormalsInterpolation('vertex')
        mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateVisibilityAttr('inherited')
        mesh.CreateExtentAttr([Gf.Vec3f(*[min(v[j] for v in region['points']) for j in range(3)]),
                              Gf.Vec3f(*[max(v[j] for v in region['points']) for j in range(3)])])
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
        shaders.append(shader.GetPath())
        meshes.append(mesh.GetPath())
    tube.CreateRelationship('fehlings:layerShaders').SetTargets(shaders)
    tube.CreateRelationship('fehlings:layerMeshes').SetTargets(meshes)
    for name,kind,value in [('layer_count',Sdf.ValueTypeNames.Int,LAYER_COUNT),
                            ('layer_height_fraction',Sdf.ValueTypeNames.Double,1/LAYER_COUNT),
                            ('layer_progress',Sdf.ValueTypeNames.DoubleArray,[0.0]*LAYER_COUNT),
                            ('layer_bounds_m',Sdf.ValueTypeNames.Double2Array,[Gf.Vec2d(r['low'],r['high']) for r in regions])]:
        tube.CreateAttribute('fehlings:'+name,kind,custom=True).Set(value)
    tube.GetAttribute('fehlings:policy_version').Set(POLICY_VERSION)
    tube.GetAttribute('fehlings:reaction_stage').Set(appearance(0)['reaction_stage'])
    script = stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script')
    script.Set(controller(script.Get()))
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    if physical_state(stage)!=before:
        raise ValueError('r5 physical content changed')
    stage.GetRootLayer().Save()
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    (evidence/'physical_revision_audit.json').write_text(json.dumps(dict(status='pass',scene_sha256=digest,
        source_scene_sha256=source_sha,all_r5_physics_identical=True),indent=2)+'\n')
    (evidence/'fixed_regions_recipe.json').write_text(json.dumps(dict(scene_sha256=digest,
        layer_bounds_m=[[r['low'],r['high']] for r in regions],layer_height_fraction=1/LAYER_COUNT,
        internal_caps=False,palette=PALETTE,opacities=OPACITIES,roughnesses=ROUGHNESSES,
        layer_key_times_seconds=[layer_key_times(i) for i in range(LAYER_COUNT)]),indent=2)+'\n')
    for name in ('runtime_cold_starts','runtime_reports','render_evidence','closure'):
        manifest.pop(name,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',scene_sha256=digest,
                    source_package_id='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5',
                    source_scene_sha256=source_sha,reaction_policy=contract())
    manifest['claims'].update(scene_fixture_verified=False,visual_reaction_verified=False)
    manifest['readability_shadow_overrides'] = [p for p in manifest.get('readability_shadow_overrides',[])
                                               if stage.GetPrimAtPath(p)] + [str(p) for p in meshes]
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    write_task_documents(root)
    (root/'README_CN.md').write_text('''# 斐林水浴 r6：五层等高、30秒多阶段显色

从 r5 派生；Isaac Sim 4.5 打开 scene.usd 并允许脚本节点，保留 deps 和 task_config.py。
累计有效触水30秒完成；离水暂停、重入继续，完成后取出近竖直稳定观察3秒成功。
五层均占原液柱高度20%，各自连续经过蓝、绿、黄、橙、橙红；中下部较早，上部较晚。
最终全部趋于橙红浑浊。固定几何，运行只改五套材质的颜色、opacity、roughness及任务遥测。
不模拟真实化学、传热、颗粒、搅拌或洒出；假液体随试管刚性运动。
节点、色序、时间曲线和读取方法见 [颜色教学](COLOR_GUIDE_CN.md)。
''')
    return root


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--out',type=Path,default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source,args.out))

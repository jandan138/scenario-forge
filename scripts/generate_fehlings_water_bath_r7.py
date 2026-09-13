"""Integrate a Blender-made 18x150 mm glass tube and five fixed 8 mL regions."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.fehlings_r2_state import radius_at, volume_to_height
from scripts.generate_fehlings_water_bath_r6 import fixed_regions, contract as color_contract
from scripts.generate_fehlings_water_bath_r3 import TUBE, GRAPH as GRAPH
from scripts.finalize_traditional_titration_vr_r14 import physical_state
from scenario_forge.adapters.vr_object_materialization import materialize_vr_object_subtrees

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6_20260911/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6'
PRODUCER = Path('/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/chemistry_test_tube_18x150_r1_20260912/package')
PRODUCER_REL = 'deps/chemistry_test_tube_18x150_r1'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7'
OUTPUT = ROOT/('outputs/'+TASK_ID+'_20260912')
RACK = '/World/obj_tube_rack'


def mesh_volume_ml(shapes):
    """Signed volume of the combined fixed-region exterior, in millilitres."""
    import numpy as np
    volume = 0.0
    for shape in shapes:
        triangles, offset = [], 0
        for count in shape['counts']:
            face = shape['indices'][offset:offset+count]
            triangles.extend((face[0],face[j],face[j+1]) for j in range(1,count-1))
            offset += count
        a,b,c = np.asarray(shape['points'])[np.asarray(triangles)].transpose(1,0,2)
        volume += float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
    return volume*1e6


def sample_recipe(cavity_profile, volume_ml=8.0):
    """Solve actual fixed-Mesh volume with a small clearance above the inner pole."""
    if not math.isfinite(volume_ml) or volume_ml<=0:
        raise ValueError('positive finite sample volume required')
    floor = cavity_profile[0][0]+.0001
    profile = [(floor,radius_at(cavity_profile,floor))]+[tuple(p) for p in cavity_profile if p[0]>floor]
    effective = [(z,max(0,r-.00002)) for z,r in profile]
    top = volume_to_height(effective,volume_ml*1e-6)
    if top>=profile[-1][0]-.002:
        raise ValueError('sample must leave clearance below the mouth')
    # Account for the 64-sided section, meniscus, and rounded-bottom discretization.
    for _ in range(4):
        actual = mesh_volume_ml(fixed_regions(profile,top))
        if abs(actual-volume_ml)<1e-5:
            break
        area = math.pi*(radius_at(profile,top)-.00002)**2
        top += (volume_ml-actual)*1e-6/area
    actual = mesh_volume_ml(fixed_regions(profile,top))
    if abs(actual-volume_ml)>.001 or top>=profile[-1][0]-.002:
        raise ValueError('fixed sample volume solution failed')
    return dict(sample_volume_ml=volume_ml,realized_mesh_volume_ml=actual,profile_m=profile,
                sample_top_m=top,inner_pole_clearance_m=.0001,radial_inset_m=.00002,
                layer_height_m=(top-floor)/5)


def rack_fit(stage, producer, scale=1.0):
    """Measure the occupied slot's actual guide rings and support, not rack metadata."""
    from pxr import Gf, Usd, UsdGeom
    if not math.isfinite(scale) or scale<=0:
        raise ValueError('positive finite rack scale required')
    rack = stage.GetPrimAtPath(RACK)
    rack.GetAttribute('xformOp:scale').Set(Gf.Vec3d(scale))
    cache = UsdGeom.XformCache()
    tube_position = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(TUBE)).ExtractTranslation()
    supports = [p for p in Usd.PrimRange(rack) if p.IsA(UsdGeom.Cylinder) and p.GetName().startswith('slot_15ml')]
    if not supports:
        raise ValueError('qualified rack support slots missing')
    support = min(supports,key=lambda p: sum((cache.GetLocalToWorldTransform(p).ExtractTranslation()[i]-tube_position[i])**2 for i in (0,1)))
    inverse = cache.GetLocalToWorldTransform(rack).GetInverse()
    support_center = inverse.Transform(cache.GetLocalToWorldTransform(support).ExtractTranslation())
    support_top = support_center[2]+support.GetAttribute('height').Get()/2
    mesh = stage.GetPrimAtPath(RACK+'/Cube_015')
    transform = cache.GetLocalToWorldTransform(mesh)*inverse
    points = [transform.Transform(Gf.Vec3d(*p)) for p in mesh.GetAttribute('points').Get()]
    rings = [(math.hypot(p[0]-support_center[0],p[1]-support_center[1]),p[2]) for p in points
             if p[2]>support_top+.010 and math.hypot(p[0]-support_center[0],p[1]-support_center[1])<.013]
    if not rings:
        raise ValueError('rack guide rings not found')
    guide_radius = min(v[0] for v in rings)*scale
    clearance = guide_radius-producer['outer_radius_m']
    if clearance<.0005:
        raise ValueError('insufficient guide clearance; validate an adjusted rack scale')
    matrix = cache.GetLocalToWorldTransform(rack)
    resting = matrix.Transform(Gf.Vec3d(support_center[0],support_center[1],support_top))
    return dict(rack_scale=[scale]*3,support_path=str(support.GetPath()),guide_diameter_m=2*guide_radius,
                radial_clearance_m=clearance,guide_levels_local_m=sorted(set(round(v[1],8) for v in rings)),
                support_top_world_m=resting[2],tube_start_xyz_m=[resting[0],resting[1],resting[2]+.0005],
                rack_top_world_m=matrix.Transform(Gf.Vec3d(0,0,max(p[2] for p in points)))[2],
                measurement='actual visible mesh guide rings and existing support collider',runtime_verified=False)


def write_task_documents(root):
    """Preserve r6 timing while recording the new container and eight-mL sample."""
    task = yaml.safe_load((root/'task.yaml').read_text())
    task.update(task_id=TASK_ID,container_semantics='open_round_bottom_borosilicate_test_tube_18x150mm',
                sample_volume_ml=8.0,reaction_policy=color_contract())
    (root/'task.yaml').write_text(yaml.safe_dump(task,allow_unicode=True,sort_keys=False))
    metrics = yaml.safe_load((root/'metrics.yaml').read_text())
    for metric in metrics['metrics']:
        metric['source_ref']['task'] = TASK_ID
    (root/'metrics.yaml').write_text(yaml.safe_dump(metrics,allow_unicode=True,sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root/'task_config.py'))['TASKS'].values()))
    cfg['water_bath'].update(container='open_round_bottom_glass_test_tube_18x150mm',sample_volume_ml=8.0,
                             reaction_policy=color_contract())
    cfg['scene_usd_file_path'] = {'scene1':'__SCENE__'}
    text = repr({TASK_ID:cfg}).replace("'__SCENE__'","str(Path(__file__).resolve().parent / 'scene.usd')")
    (root/'task_config.py').write_text('from pathlib import Path\nTASKS = '+text+'\n')
    shutil.copy2(ROOT/'docs/operations/fehlings-r7-glass-tube-guide.md',root/'COLOR_GUIDE_CN.md')


def build(source=SOURCE,producer=PRODUCER,output=OUTPUT,rack_scale=1.0):
    """Build a runtime-pending candidate from qualified r6 and statically checked producer."""
    from pxr import Gf, Sdf, Usd, UsdGeom
    source,producer = source.resolve(),producer.resolve()
    source_manifest = json.loads((source/'manifest.json').read_text())
    source_hash = sha256((source/'scene.usd').read_bytes()).hexdigest()
    if source_manifest['package_id']!='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6' or source_manifest['status']!='pass' or source_manifest['scene_sha256']!=source_hash:
        raise ValueError('qualified unchanged r6 source required')
    asset = json.loads((producer/'evidence/manifest.json').read_text())
    asset_hash = sha256((producer/'asset.usd').read_bytes()).hexdigest()
    static = json.loads((producer/asset['static_validation']['path']).read_text())
    if asset['package_id']!='chemistry_test_tube_18x150_r1' or asset['asset_sha256']!=asset_hash or static['status']!='pass' or static['asset_sha256']!=asset_hash:
        raise ValueError('exact statically validated Blender tube required')
    root = output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source,root,ignore=lambda d,n: {'evidence','.thumbs'} if Path(d)==source else set())
    evidence = root/'evidence'
    evidence.mkdir()
    shutil.copy2(source/'evidence/water_recipe.json',evidence/'water_recipe.json')
    shutil.copytree(producer,root/PRODUCER_REL)
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    before = physical_state(stage)
    saved = Sdf.Layer.CreateAnonymous()
    Sdf.CreatePrimInLayer(saved,'/World')
    Sdf.CopySpec(stage.GetRootLayer(),TUBE,saved,TUBE)
    fit = rack_fit(stage,asset,rack_scale)
    stage.RemovePrim(TUBE)
    tube = UsdGeom.Xform.Define(stage,TUBE).GetPrim()
    tube.GetReferences().AddReference(PRODUCER_REL+'/asset.usd',asset['entrypoints']['asset_entry_prim'])
    # Retain the task's established glass-shadow readability policy. RTX shadow
    # rays through this glass otherwise create black stripes on the near-wall sample.
    glass_path=TUBE+'/Visual/GlassShell'
    UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(glass_path)).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
    for prop in saved.GetPrimAtPath(TUBE).properties:
        if prop.name.startswith(('fehlings:','xformOp')):
            Sdf.CopySpec(saved,prop.path,stage.GetRootLayer(),prop.path)
    for child in ('VisualLiquid','ReactionRuntime'):
        Sdf.CopySpec(saved,TUBE+'/'+child,stage.GetRootLayer(),TUBE+'/'+child)
    tube.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*fit['tube_start_xyz_m']))
    recipe = sample_recipe(asset['cavity_profile_m'])
    shapes = fixed_regions(recipe['profile_m'],recipe['sample_top_m'])
    for path,shape in zip(tube.GetRelationship('fehlings:layerMeshes').GetTargets(),shapes):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
        mesh.GetPointsAttr().Set([Gf.Vec3f(*v) for v in shape['points']])
        mesh.GetNormalsAttr().Set([Gf.Vec3f(*v) for v in shape['normals']])
        mesh.GetFaceVertexCountsAttr().Set(shape['counts'])
        mesh.GetFaceVertexIndicesAttr().Set(shape['indices'])
        mesh.GetExtentAttr().Set(UsdGeom.PointBased.ComputeExtent(mesh.GetPointsAttr().Get()))
    tube.GetAttribute('fehlings:cavity_profile_m').Set([Gf.Vec2d(*v) for v in recipe['profile_m']])
    tube.GetAttribute('fehlings:sample_height_m').Set(recipe['sample_top_m'])
    tube.GetAttribute('fehlings:mouth_height_m').Set(asset['mouth_z_m'])
    tube.GetAttribute('fehlings:outer_radius_m').Set(asset['outer_radius_m'])
    tube.GetAttribute('fehlings:layer_bounds_m').Set([Gf.Vec2d(v['low'],v['high']) for v in shapes])
    tube.CreateAttribute('fehlings:container_kind',Sdf.ValueTypeNames.Token,custom=True).Set('glass_test_tube_18x150')
    tube.CreateAttribute('fehlings:sample_volume_ml',Sdf.ValueTypeNames.Double,custom=True).Set(8.0)
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId',TASK_ID)
    stage.GetRootLayer().Save()
    materialize_vr_object_subtrees(scene_path=root/'scene.usd',scene_prim_paths=[TUBE],
        runtime_prim_paths=['/World/_scene/obj_sample_tube'],evidence_path=root/'object_materialization.json')
    stage.GetRootLayer().Reload()
    after = physical_state(stage)
    def retained(values):
        return {p:v for p,v in values.items() if not p.startswith(TUBE) and not (rack_scale!=1 and p.startswith(RACK))}
    if retained(before)!=retained(after):
        raise ValueError('unapproved non-tube physics change')
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    for path,payload in [('rack_fit.json',fit),('sample_recipe.json',recipe),
                         ('physical_revision_audit.json',dict(status='pass',source_scene_sha256=source_hash,
                          tube_asset_sha256=asset_hash,non_tube_physics_preserved=True,rack_scale=rack_scale,
                          new_tube_mass_kg=asset['mass_kg'],old_tube_mass_kg=float(before[TUBE]['attrs']['physics:mass'])))]:
        (evidence/path).write_text(json.dumps(dict(payload,scene_sha256=digest),indent=2)+'\n')
    manifest = source_manifest
    for key in ('runtime_cold_starts','runtime_reports','render_evidence','closure','fixed_regions_recipe'):
        manifest.pop(key,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',source_package_id=source.name,
                    source_scene_sha256=source_hash,scene_sha256=digest,tube_asset_sha256=asset_hash,
                    tube_producer_manifest=PRODUCER_REL+'/evidence/manifest.json',sample_volume_ml=8.0,
                    sample_height_m=recipe['sample_top_m'],sample_recipe='evidence/sample_recipe.json',
                    rack_fit='evidence/rack_fit.json')
    manifest['claims'].update(scene_fixture_verified=False,visual_reaction_verified=False,glass_tube_runtime_verified=False)
    manifest['readability_shadow_overrides'] = [p for p in manifest.get('readability_shadow_overrides',[]) if stage.GetPrimAtPath(p)]+[glass_path]
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    write_task_documents(root)
    (root/'README_CN.md').write_text('''# 斐林水浴 r7：18×150 mm 玻璃试管，8 mL 五层显色

Isaac Sim 4.5 打开 scene.usd 并允许脚本节点，保留 deps 与 task_config.py。
试管为 Blender 制作的1 mm壁厚、轻卷口圆底素玻璃；实体质量约18.01 g。8 mL为视觉样液，不额外添加物理液体质量。
五层依次经过蓝、绿、黄、橙、橙红；累计有效触水30秒完成，离水暂停，重入继续。
取出后近竖直稳定观察3秒成功。五层几何固定，重置恢复初始同蓝材质。
尺寸、架子适配、玻璃源文件、属性读取和证据范围见 [操作指南](COLOR_GUIDE_CN.md)。
''')
    return root


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--producer',type=Path,default=PRODUCER)
    parser.add_argument('--out',type=Path,default=OUTPUT)
    parser.add_argument('--rack-scale',type=float,default=1.0)
    args = parser.parse_args()
    print(build(args.source,args.producer,args.out,args.rack_scale))

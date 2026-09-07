"""Build r1.3 with an inner-wall-fitted, transmissive visual receiver liquid."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil

from scripts.generate_visual_static_liquid_prototype import build_liquid_mesh

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_2_20260905/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_2'
OUTPUT = ROOT / 'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_3_20260907'
TASK_ID = 'scientific_workbench_traditional_acid_base_titration_vr_r1_3'
LIQUID_ROOT = '/World/obj_receiver_flask/VisualLiquid'
PHASES = (
    ('colorless', 'Colorless', (0.97, 0.99, 1.0)),
    ('transition', 'Transition', (1.0, 0.90, 0.94)),
    ('endpoint_pale_pink', 'EndpointPalePink', (1.0, 0.80, 0.88)),
    ('overshoot', 'Overshoot', (0.85, 0.12, 0.28)),
)


def closed_liquid_mesh(profile):
    data = build_liquid_mesh(profile, 1.0, radial_segments=64, meniscus_depth_m=0.0002)
    body = data['body']
    points = list(body['points'])
    counts = list(body['face_vertex_counts'])
    indices = list(body['face_vertex_indices'])
    top_ring = len(points)-1-64
    center = len(points)
    points.append(data['surface']['points'][0])
    counts.extend(data['surface']['face_vertex_counts'])
    indices.extend(center if i == 0 else top_ring+i-1 for i in data['surface']['face_vertex_indices'])
    return points, counts, indices


def water_controller(script: str) -> str:
    replacements = {
        'colorless = (0.92, 0.97, 1.0)': 'colorless = (0.97, 0.99, 1.0)',
        'pale = (1.0, 0.48, 0.65)': 'pale = (1.0, 0.80, 0.88)',
        'deep = (0.75, 0.02, 0.2)': 'deep = (0.85, 0.12, 0.28)',
        '("inputs:diffuseColor", "inputs:baseColor")': '("inputs:diffuseColor", "inputs:baseColor", "inputs:glass_color")',
    }
    for old, new in replacements.items():
        if script.count(old) != 1:
            raise ValueError(f'expected one reviewed controller fragment: {old}')
        script = script.replace(old, new)
    return script


def liquid_normals(profile, counts, indices):
    normals = []
    cursor = 0
    side_faces = (len(profile)-1)*64
    for face_index, count in enumerate(counts):
        for vertex in indices[cursor:cursor+count]:
            if face_index >= side_faces:
                normals.append((0.0, 0.0, -1.0 if face_index < side_faces+64 else 1.0))
            else:
                ring, angle_index = divmod(vertex, 64)
                lo, hi = max(0, ring-1), min(len(profile)-1, ring+1)
                slope = (profile[hi][1]-profile[lo][1])/(profile[hi][0]-profile[lo][0])
                length = math.sqrt(1+slope*slope)
                angle = 2*math.pi*angle_index/64
                normals.append((math.cos(angle)/length, math.sin(angle)/length, -slope/length))
        cursor += count
    return normals


def author_liquid(stage, profile):
    from pxr import Gf, Sdf, UsdGeom, UsdShade

    stage.RemovePrim(LIQUID_ROOT)
    root = UsdGeom.Xform.Define(stage, LIQUID_ROOT).GetPrim()
    root.SetCustomDataByKey('scenario_forge:visualOnly', True)
    root.SetCustomDataByKey('scenario_forge:liquidGeometry', 'inner_cavity_fitted_closed_mesh')
    points, counts, indices = closed_liquid_mesh(profile['axial_profile_m'])
    targets, shaders = [], []
    for phase, suffix, color in PHASES:
        path = f'{LIQUID_ROOT}/Solution{suffix}'
        mesh = UsdGeom.Mesh.Define(stage, path)
        mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
        mesh.CreateFaceVertexCountsAttr(counts)
        mesh.CreateFaceVertexIndicesAttr(indices)
        mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreateNormalsAttr([Gf.Vec3f(*n) for n in liquid_normals(profile['axial_profile_m'], counts, indices)])
        mesh.SetNormalsInterpolation('faceVarying')
        mesh.CreateDoubleSidedAttr(False)
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('doNotCastShadows', Sdf.ValueTypeNames.Bool).Set(True)
        mesh.CreateExtentAttr([Gf.Vec3f(*[min(p[i] for p in points) for i in range(3)]),
                               Gf.Vec3f(*[max(p[i] for p in points) for i in range(3)])])
        mesh.CreateVisibilityAttr('inherited' if phase == 'colorless' else 'invisible')
        mesh.GetPrim().CreateAttribute('titration:phase', Sdf.ValueTypeNames.Token).Set(phase)
        material = UsdShade.Material.Define(stage, f'{LIQUID_ROOT}/Looks/Water{suffix}')
        shader = UsdShade.Shader.Define(stage, str(material.GetPath())+'/Shader')
        shader.SetSourceAsset(Sdf.AssetPath('deps/beaker/deps/mdl/OmniGlass.mdl'), 'mdl')
        shader.SetSourceAssetSubIdentifier('OmniGlass', 'mdl')
        for name, kind, value in (
            ('glass_color', Sdf.ValueTypeNames.Color3f, Gf.Vec3f(*color)),
            ('reflection_color', Sdf.ValueTypeNames.Color3f, Gf.Vec3f(1.0)),
            ('glass_ior', Sdf.ValueTypeNames.Float, 1.333),
            ('frosting_roughness', Sdf.ValueTypeNames.Float, 0.02),
            ('depth', Sdf.ValueTypeNames.Float, 0.05),
            ('thin_walled', Sdf.ValueTypeNames.Bool, False),
            ('enable_opacity', Sdf.ValueTypeNames.Bool, False),
            ('cutout_opacity', Sdf.ValueTypeNames.Float, 1.0),
        ):
            shader.CreateInput(name, kind).Set(value)
        shader.CreateOutput('out', Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput('mdl').ConnectToSource(shader.ConnectableAPI(), 'out')
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'out')
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
        targets.append(path)
        shaders.append(str(shader.GetPath()))
    bar = UsdGeom.Xform.Define(stage, LIQUID_ROOT+'/StirBar')
    bar.AddTranslateOp().Set(Gf.Vec3d(0, 0, profile['inner_floor_m']+0.00315))
    rotation = bar.AddRotateZOp()
    for frame in range(0, 3601, 15):
        rotation.Set(float(frame)*2, frame)
    capsule = UsdGeom.Capsule.Define(stage, LIQUID_ROOT+'/StirBar/Visual')
    capsule.CreateAxisAttr('Z')
    capsule.CreateRadiusAttr(0.003)
    capsule.CreateHeightAttr(0.026)
    capsule.AddRotateYOp().Set(90.0)
    capsule.CreateDisplayColorAttr([Gf.Vec3f(0.94, 0.94, 0.92)])
    station = stage.GetPrimAtPath('/World/obj_titration_station')
    station.GetRelationship('titration:receiverLiquidVisuals').SetTargets(targets)
    station.GetRelationship('titration:receiverLiquidShader').SetTargets(shaders)
    controller = stage.GetPrimAtPath('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/FlowController')
    old_script = controller.GetAttribute('inputs:script').Get()
    new_script = water_controller(old_script)
    controller.GetAttribute('inputs:script').Set(new_script)
    return {'mesh_vertices': len(points), 'mesh_faces': len(counts),
            'controller_before_sha256': sha256(old_script.encode()).hexdigest(),
            'controller_after_sha256': sha256(new_script.encode()).hexdigest(),
            'shader_paths': shaders, 'phase_paths': targets, 'ior': 1.333,
            'initial_color': list(PHASES[0][2]), 'frosting_roughness': 0.02,
            'absorption_depth_m': 0.05, 'casts_shadow': False, 'physics_added': False}


def build(source: Path, output: Path, profile_path: Path) -> Path:
    from pxr import Usd

    profile = json.loads(profile_path.read_text())
    if sha256((source/'scene.usd').read_bytes()).hexdigest() != profile['source_scene_sha256']:
        raise ValueError('cavity profile is not bound to this source scene')
    root = output / 'handoff' / TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source, root, ignore=lambda directory, names: {'evidence'} if Path(directory) == source else set())
    (root/'task_r16.json').unlink(missing_ok=True)
    evidence = root/'evidence'
    evidence.mkdir()
    shutil.copy2(profile_path, evidence/'receiver_cavity.json')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    recipe = author_liquid(stage, profile)
    stage.GetRootLayer().Save()
    for name in ('task.yaml','task_config.py'):
        path = root/name
        path.write_text(path.read_text().replace('vr_r1_2', 'vr_r1_3'))
    manifest = json.loads((root/'manifest.json').read_text())
    manifest.update(package_id=TASK_ID, status='visual_revision_runtime_pending', runtime='Isaac Sim 4.5')
    manifest['receiver_liquid'] = recipe
    manifest['source_revision'] = {'package_id': 'scientific_workbench_traditional_acid_base_titration_vr_r1_2',
                                   'scene_sha256': profile['source_scene_sha256']}
    for key in ('runtime_evidence','render_evidence','package_closure'):
        manifest.pop(key, None)
    manifest['claims'].update(scene_static_validation=False, scene_cold_start_passes=0,
                             materialized_state_machine_success_path=False,
                             receiver_liquid_fitted_visual=True, robot_policy_success=False, benchmark_success=False)
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    (root/'README_CN.md').write_text('''# 传统酸碱滴定 r1.3：贴壁透明液体

使用 Isaac Sim 4.5 打开 scene.usd；整包保留 deps 与 task_config.py。
锥形瓶内为贴合实际内底和内壁的闭合假液体网格，液面固定约 89 mm。
初始清澈略淡蓝，随原滴定状态机转为淡粉色；假磁子已放回内底。
旋塞操作规则仍为 OPEN → FINE → DRIP → CLOSED，14.7–15.3 mL 内关闭保持 3 秒。
本包不含真实液体粒子或化学求解，不新增机器人策略成功声明。
''')
    (evidence/'visual_liquid_recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')
    print(root)
    return root


def refresh_candidate(source, output, profile_path):
    from pxr import Usd

    root = output / 'handoff' / TASK_ID
    manifest = json.loads((root/'manifest.json').read_text())
    if manifest['status'] != 'visual_revision_runtime_pending':
        raise ValueError('cannot refresh a finalized package')
    profile = json.loads(profile_path.read_text())
    if sha256((source/'scene.usd').read_bytes()).hexdigest() != profile['source_scene_sha256']:
        raise ValueError('source hash changed')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    original = Usd.Stage.Open(str(source/'scene.usd'))
    controller = '/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/FlowController'
    stage.GetPrimAtPath(controller).GetAttribute('inputs:script').Set(
        original.GetPrimAtPath(controller).GetAttribute('inputs:script').Get())
    recipe = author_liquid(stage, profile)
    stage.GetRootLayer().Save()
    manifest['receiver_liquid'] = recipe
    manifest['runtime'] = 'Isaac Sim 4.5'
    readme = root/'README_CN.md'
    readme.write_text(readme.read_text().replace('Isaac Sim 4.1', 'Isaac Sim 4.5'))
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    (root/'evidence/visual_liquid_recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    parser.add_argument('--profile', type=Path, default=OUTPUT/'source_profile/receiver_cavity.json')
    parser.add_argument('--refresh-candidate', action='store_true')
    args = parser.parse_args()
    (refresh_candidate if args.refresh_candidate else build)(args.source, args.out, args.profile)

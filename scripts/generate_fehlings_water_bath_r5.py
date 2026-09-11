"""Derive r5 directly from r3: two fixed visual regions and material-only development."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.fehlings_r2_state import fitted_region, mesh_topology, RADIAL
from scripts.fehlings_r5_state import POLICY_VERSION, appearance
from scripts.finalize_traditional_titration_vr_r14 import physical_state
from scripts.generate_fehlings_water_bath_r3 import TUBE, GRAPH, contract as contact_contract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3_20260909/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5'
OUTPUT = ROOT / ('outputs/' + TASK_ID + '_20260911')


def contract():
    return dict(contact_contract(), version=POLICY_VERSION, contact_policy_version='visual_water_contact_v3',
                geometry_updates=False, visibility_updates=False, sediment_height_fraction=1/3,
                sediment_progress_meaning='material_development_not_volume',
                material_inputs=['diffuseColor', 'opacity', 'roughness'])


def fixed_geometry(profile, sample_top):
    floor = profile[0][0]
    split = floor + (sample_top - floor) / 3
    if not floor < split < sample_top <= profile[-1][0]:
        raise ValueError('invalid fixed sample region')
    return dict(Sample=fitted_region(profile, split, sample_top, .00015),
                Sediment=fitted_region(profile, floor, split, 0),
                sediment_height_m=split-floor, split_z_m=split)


def controller(source_script):
    # Keep the actual source package's task/contact functions, not a reimplementation.
    tree = ast.parse(source_script)
    removed = {'appearance', 'geometry', 'fitted_region', 'mesh_topology', 'radius_at',
               'volume_to_height', 'water_mesh', 'setup', 'cleanup', '_target', '_apply_state', 'compute'}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name not in removed]
    compute = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'compute')
    text = ast.get_source_segment(source_script, compute)
    text = text.replace('global _state,_last_geometry_progress', 'global _state')
    text = text.replace('_state,_last_geometry_progress=initial_state(),None', '_state=initial_state()')
    if '_last_geometry_progress' in text:
        raise ValueError('unexpected source geometry dependency')
    code = ('import math\n' + '\n\n'.join(ast.get_source_segment(source_script, n) for n in functions)
            + '\n' + (ROOT / 'scripts/fehlings_r5_state.py').read_text()
            + '\n' + (ROOT / 'scripts/fehlings_r5_usd_controller.py').read_text() + '\n' + text + '\n')
    compile(code, '<r5 controller>', 'exec')
    return code


def write_task_documents(root):
    task = yaml.safe_load((root / 'task.yaml').read_text())
    task.update(task_id=TASK_ID, reaction_policy=contract())
    (root / 'task.yaml').write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    metrics = yaml.safe_load((root / 'metrics.yaml').read_text())
    for item in metrics['metrics']:
        item['source_ref']['task'] = TASK_ID
    (root / 'metrics.yaml').write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root / 'task_config.py'))['TASKS'].values()))
    cfg['water_bath']['reaction_policy'] = contract()
    cfg['scene_usd_file_path'] = {'scene1': '__SCENE__'}
    text = repr({TASK_ID: cfg}).replace("'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')")
    (root / 'task_config.py').write_text('from pathlib import Path\nTASKS = ' + text + '\n')
    shutil.copy2(ROOT / 'docs/operations/fehlings-r5-color-guide.md', root / 'COLOR_GUIDE_CN.md')


def build(source=SOURCE, output=OUTPUT):
    from pxr import Gf, Sdf, Usd, UsdGeom
    source = source.resolve()
    source_manifest = json.loads((source / 'manifest.json').read_text())
    source_hash = sha256((source / 'scene.usd').read_bytes()).hexdigest()
    if (source_manifest['package_id'] != 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3'
            or source_manifest['status'] != 'pass' or source_manifest['scene_sha256'] != source_hash):
        raise ValueError('a qualified, unmodified r3 source package is required')
    root = output / 'handoff' / TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source, root, ignore=lambda directory, names: {'evidence', '.thumbs'} if Path(directory) == source else set())
    evidence = root / 'evidence'
    evidence.mkdir()
    shutil.copy2(source / 'evidence/water_recipe.json', evidence / 'water_recipe.json')
    stage = Usd.Stage.Open(str(root / 'scene.usd'))
    before = physical_state(stage)
    tube = stage.GetPrimAtPath(TUBE)
    profile = [tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    top = float(tube.GetAttribute('fehlings:sample_height_m').Get())
    geometry = fixed_geometry(profile, top)
    look = appearance(0)
    for label, prefix in [('Sample', ''), ('Sediment', 'sediment_')]:
        UsdGeom.Imageable(stage.GetPrimAtPath(TUBE + '/VisualLiquid/' + label)).CreateVisibilityAttr('inherited')
        for part in ('body', 'surface'):
            prim = stage.GetPrimAtPath(TUBE + '/VisualLiquid/' + label + '/' + part)
            mesh = UsdGeom.Mesh(prim)
            points = geometry[label][part]
            counts, indices = mesh_topology(part)
            # A single lower top surface: no coincident upper bottom cap at the interface.
            if label == 'Sample' and part == 'body':
                points = points[:-1]
                counts, indices = counts[:-RADIAL], indices[:-3*RADIAL]
            mesh.GetPointsAttr().Set([Gf.Vec3f(*v) for v in points])
            mesh.GetFaceVertexCountsAttr().Set(counts)
            mesh.GetFaceVertexIndicesAttr().Set(indices)
            mesh.GetExtentAttr().Set([Gf.Vec3f(*[min(v[i] for v in points) for i in range(3)]),
                                      Gf.Vec3f(*[max(v[i] for v in points) for i in range(3)])])
            prim.RemoveProperty('normals')
            UsdGeom.Imageable(prim).CreateVisibilityAttr('inherited')
        shader = stage.GetPrimAtPath(TUBE + '/VisualLiquid/Looks/' + label + '/Shader')
        shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*look[prefix + 'color']))
        shader.GetAttribute('inputs:opacity').Set(look[prefix + 'opacity'])
        shader.GetAttribute('inputs:roughness').Set(look[prefix + 'roughness'])
    tube.GetAttribute('fehlings:policy_version').Set(POLICY_VERSION)
    tube.GetAttribute('fehlings:sediment_height_m').Set(geometry['sediment_height_m'])
    tube.CreateAttribute('fehlings:sediment_height_fraction', Sdf.ValueTypeNames.Double, custom=True).Set(1/3)
    tube.GetAttribute('fehlings:sediment_height_m').SetDocumentation('Fixed lower-region height, including at reset; not growing sediment.')
    tube.GetAttribute('fehlings:sediment_progress').SetDocumentation('Material development 0–1, not volume or height growth.')
    script = stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script')
    script.Set(controller(script.Get()))
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId', TASK_ID)
    if physical_state(stage) != before:
        raise ValueError('r3 physics or placement changed')
    stage.GetRootLayer().Save()
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    (evidence / 'physical_revision_audit.json').write_text(json.dumps(dict(status='pass', scene_sha256=digest,
        source_scene_sha256=source_hash, all_r3_physics_identical=True), indent=2) + '\n')
    (evidence / 'fixed_regions_recipe.json').write_text(json.dumps(dict(scene_sha256=digest,
        floor_m=profile[0][0], sample_top_m=top, split_z_m=geometry['split_z_m'],
        sediment_height_m=geometry['sediment_height_m'], height_fraction=1/3,
        internal_interface='single_lower_top_cap_no_upper_bottom_cap', geometry_updates=False), indent=2) + '\n')
    manifest = source_manifest
    for key in ('runtime_cold_starts', 'runtime_reports', 'render_evidence', 'closure'):
        manifest.pop(key, None)
    manifest.update(package_id=TASK_ID, status='runtime_pending', scene_sha256=digest,
                    source_package_id='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r3',
                    source_scene_sha256=source_hash, reaction_policy=contract(),
                    fixed_regions_recipe='evidence/fixed_regions_recipe.json')
    manifest['claims'].update(scene_fixture_verified=False, visual_reaction_verified=False, dynamic_sediment_geometry=False)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    write_task_documents(root)
    (root / 'README_CN.md').write_text('''# 斐林水浴 r5：两块固定假液体，随加热时间改变材质

严格由 r3 派生；Isaac Sim 4.5 打开 scene.usd 并允许脚本节点，保留包内依赖和 task_config.py。
保持 r3 的触水累计、离水暂停、30秒开始变化、60秒显色完成、取出稳定观察3秒规则。
下块占初始样液高度三分之一，上块占三分之二；两块初始都是蓝色半透明，运行时不改几何或可见性。
上块先浑浊再变清，下块逐渐变为砖红、不透明、偏哑光。只更新颜色、opacity、roughness。
不是沉淀体积增长、真实化学、颗粒或自由液面仿真；假液体随容器刚性运动。
节点、时间曲线、读取方法与证据边界见 [颜色教学](COLOR_GUIDE_CN.md)。
''')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.out))

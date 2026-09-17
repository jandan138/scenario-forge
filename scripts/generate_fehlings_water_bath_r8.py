"""Keep r7 volume and reaction; make beaker fake water optically clear."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.generate_fehlings_water_bath_r3 import GRAPH, WATER
from scripts.generate_fehlings_water_bath_r6 import contract as color_contract
from scripts.finalize_traditional_titration_vr_r14 import physical_state

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8'
OUTPUT = ROOT / ('outputs/' + TASK_ID + '_20260914')
OMNI_GLASS = 'deps/objects/obj_beaker/deps/mdl/OmniGlass.mdl'
WATER_RECIPE = dict(
    shader='OmniGlass',
    mdl=OMNI_GLASS,
    glass_color=(0.97, 0.99, 1.0),
    reflection_color=(1.0, 1.0, 1.0),
    glass_ior=1.333,
    frosting_roughness=0.02,
    depth=0.002,
    thin_walled=True,
    enable_opacity=False,
    cutout_opacity=1.0,
    double_sided=False,
)


def apply_water_optics(stage, recipe=WATER_RECIPE):
    """Replace VisualWater PreviewSurface alpha with package-local OmniGlass."""
    from pxr import Gf, Sdf, UsdGeom, UsdShade

    looks = WATER + '/Looks/Water'
    stage.RemovePrim(looks)
    material = UsdShade.Material.Define(stage, looks)
    shader = UsdShade.Shader.Define(stage, looks + '/Shader')
    shader.SetSourceAsset(Sdf.AssetPath(recipe['mdl']), 'mdl')
    shader.SetSourceAssetSubIdentifier('OmniGlass', 'mdl')
    for name, kind, value in (
        ('glass_color', Sdf.ValueTypeNames.Color3f, Gf.Vec3f(*recipe['glass_color'])),
        ('reflection_color', Sdf.ValueTypeNames.Color3f, Gf.Vec3f(*recipe['reflection_color'])),
        ('glass_ior', Sdf.ValueTypeNames.Float, recipe['glass_ior']),
        ('frosting_roughness', Sdf.ValueTypeNames.Float, recipe['frosting_roughness']),
        ('depth', Sdf.ValueTypeNames.Float, recipe['depth']),
        ('thin_walled', Sdf.ValueTypeNames.Bool, recipe['thin_walled']),
        ('enable_opacity', Sdf.ValueTypeNames.Bool, recipe['enable_opacity']),
        ('cutout_opacity', Sdf.ValueTypeNames.Float, recipe['cutout_opacity']),
    ):
        shader.CreateInput(name, kind).Set(value)
    shader.CreateOutput('out', Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput('mdl').ConnectToSource(shader.ConnectableAPI(), 'out')
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'out')
    for name in ('body', 'surface'):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/' + name))
        mesh.CreateDoubleSidedAttr(recipe['double_sided'])
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return recipe


def write_task_documents(root):
    """Keep r7 timing/sample while recording the clear-bath optics identity."""
    task = yaml.safe_load((root / 'task.yaml').read_text())
    task.update(task_id=TASK_ID, sample_volume_ml=8.0, reaction_policy=color_contract())
    (root / 'task.yaml').write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    metrics = yaml.safe_load((root / 'metrics.yaml').read_text())
    for metric in metrics['metrics']:
        metric['source_ref']['task'] = TASK_ID
    (root / 'metrics.yaml').write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root / 'task_config.py'))['TASKS'].values()))
    cfg['water_bath'].update(
        container='open_round_bottom_glass_test_tube_18x150mm',
        sample_volume_ml=8.0,
        reaction_policy=color_contract(),
        water_representation='visual_mesh',
        water_shader='OmniGlass',
    )
    cfg['scene_usd_file_path'] = {'scene1': '__SCENE__'}
    text = repr({TASK_ID: cfg}).replace("'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')")
    (root / 'task_config.py').write_text('from pathlib import Path\nTASKS = ' + text + '\n')
    shutil.copy2(ROOT / 'docs/operations/fehlings-r8-clear-bath-guide.md', root / 'COLOR_GUIDE_CN.md')


def build(source=SOURCE, output=OUTPUT):
    """Build a runtime-pending r8 candidate from qualified r7."""
    from pxr import Usd

    source = source.resolve()
    source_manifest = json.loads((source / 'manifest.json').read_text())
    source_hash = sha256((source / 'scene.usd').read_bytes()).hexdigest()
    if (
        source_manifest['package_id'] != 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7'
        or source_manifest['status'] != 'pass'
        or source_manifest['scene_sha256'] != source_hash
    ):
        raise ValueError('qualified unchanged r7 source required')
    if not (source / OMNI_GLASS).is_file():
        raise ValueError('package-local OmniGlass required')
    root = output / 'handoff' / TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(
        source,
        root,
        ignore=lambda directory, names: {'evidence', '.thumbs'} if Path(directory) == source else set(),
    )
    evidence = root / 'evidence'
    evidence.mkdir()
    recipe = json.loads((source / 'evidence/water_recipe.json').read_text())
    stage = Usd.Stage.Open(str(root / 'scene.usd'))
    before = physical_state(stage)
    controller = stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
    apply_water_optics(stage)
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId', TASK_ID)
    stage.GetRootLayer().Save()
    after = physical_state(stage)
    if before != after:
        raise ValueError('unapproved physics change')
    if stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get() != controller:
        raise ValueError('reaction controller changed')
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    recipe.update(material=dict(WATER_RECIPE), scene_sha256=digest)
    (evidence / 'water_recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
    for name in ('sample_recipe.json', 'rack_fit.json'):
        payload = json.loads((source / 'evidence' / name).read_text())
        payload['scene_sha256'] = digest
        (evidence / name).write_text(json.dumps(payload, indent=2) + '\n')
    (evidence / 'physical_revision_audit.json').write_text(
        json.dumps(
            dict(
                status='pass',
                scene_sha256=digest,
                source_scene_sha256=source_hash,
                all_r7_physics_identical=True,
                water_volume_unchanged=True,
                water_shader=WATER_RECIPE['shader'],
            ),
            indent=2,
        )
        + '\n'
    )
    for key in ('runtime_cold_starts', 'runtime_reports', 'render_evidence', 'closure'):
        source_manifest.pop(key, None)
    source_manifest.update(
        package_id=TASK_ID,
        status='runtime_pending',
        source_package_id=source.name,
        source_scene_sha256=source_hash,
        scene_sha256=digest,
        water_shader=WATER_RECIPE['shader'],
    )
    source_manifest['claims'].update(
        scene_fixture_verified=False,
        visual_reaction_verified=False,
        in_bath_color_verified=False,
    )
    (root / 'manifest.json').write_text(json.dumps(source_manifest, indent=2) + '\n')
    write_task_documents(root)
    (root / 'README_CN.md').write_text(
        '''# 斐林水浴 r8：透过烧杯清水看清试管内变色

从 r7 派生。Isaac Sim 4.5 打开 scene.usd 并允许脚本节点，保留 deps 与 task_config.py。
试管、8 mL 五层样液、30 秒显色和接触判定不变。烧杯假水几何与 80% 液面保持不变，
材质改为包内 OmniGlass 近无色清水，避免 PreviewSurface 双面 alpha 把水下样液吃成空管。
取出观察规则不变。不模拟真实化学、传热、洒出或破碎。
节点、光学配方和证据范围见 [操作指南](COLOR_GUIDE_CN.md)。
'''
    )
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.out))

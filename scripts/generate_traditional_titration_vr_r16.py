"""Build r1.6: one continuously colored receiver mesh and material."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import shutil

import yaml

from scripts.generate_traditional_titration_vr_r15 import ROOT, STATION
from scripts.finalize_traditional_titration_vr_r14 import physical_state

SOURCE = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_5_20260907/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_5'
OUTPUT = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_6_20260907'
TASK_ID = 'scientific_workbench_traditional_acid_base_titration_vr_r1_6'
LIQUID = '/World/obj_receiver_flask/VisualLiquid'
SYNC = '''def _sync_receiver(stage, dispensed):
    station = _prim(stage, ROOT)
    targets = station.GetRelationship("titration:receiverLiquidShader").GetTargets()
    if len(targets) != 1:
        raise RuntimeError("r1.6 requires one receiver liquid shader")
    phase, rgb, _ = _color(dispensed)
    shader = stage.GetPrimAtPath(targets[0])
    attr = shader.GetAttribute("inputs:glass_color") if shader else None
    if not attr:
        raise RuntimeError("receiver liquid glass_color missing")
    attr.Set(Gf.Vec3f(*rgb))
    _set(stage, ROOT, "titration:indicator_phase", phase)
'''


def controller(script):
    nodes = [n for n in ast.parse(script).body if isinstance(n, ast.FunctionDef) and n.name == '_sync_receiver']
    if len(nodes) != 1:
        raise ValueError('expected one receiver update function')
    node = nodes[0]
    lines = script.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [SYNC]
    result = ''.join(lines)
    compile(result, '<r16 controller>', 'exec')
    return result


def build(source=SOURCE, output=OUTPUT):
    from pxr import Sdf, Usd, UsdGeom, UsdShade

    root = output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source, root, ignore=lambda directory, names: {'evidence'} if Path(directory) == source else set())
    evidence = root/'evidence'
    evidence.mkdir()
    shutil.copy2(source/'evidence/receiver_cavity.json', evidence/'receiver_cavity.json')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    layer = stage.GetRootLayer()
    Sdf.CopySpec(layer, LIQUID+'/SolutionColorless', layer, LIQUID+'/Solution')
    Sdf.CopySpec(layer, LIQUID+'/Looks/WaterColorless', layer, LIQUID+'/Looks/Water')
    mesh = stage.GetPrimAtPath(LIQUID+'/Solution')
    mesh.RemoveProperty('titration:phase')
    UsdGeom.Imageable(mesh).GetVisibilityAttr().Set('inherited')
    material = UsdShade.Material(stage.GetPrimAtPath(LIQUID+'/Looks/Water'))
    shader = UsdShade.Shader(stage.GetPrimAtPath(LIQUID+'/Looks/Water/Shader'))
    material.CreateSurfaceOutput('mdl').ConnectToSource(shader.ConnectableAPI(), 'out')
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'out')
    UsdShade.MaterialBindingAPI.Apply(mesh).Bind(material)
    for suffix in ('Colorless', 'Transition', 'EndpointPalePink', 'Overshoot'):
        stage.RemovePrim(LIQUID+'/Solution'+suffix)
        stage.RemovePrim(LIQUID+'/Looks/Water'+suffix)
    station = stage.GetPrimAtPath(STATION)
    station.GetRelationship('titration:receiverLiquidVisuals').SetTargets([LIQUID+'/Solution'])
    station.GetRelationship('titration:receiverLiquidShader').SetTargets([LIQUID+'/Looks/Water/Shader'])
    attr = stage.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script')
    old_script = attr.Get()
    new_script = controller(old_script)
    attr.Set(new_script)
    layer.Save()
    old_stage = Usd.Stage.Open(str(source/'scene.usd'))
    if physical_state(old_stage) != physical_state(stage):
        raise ValueError('physical content changed')
    # Removed nodes must not survive as dangling relationship or connection targets.
    for prim in stage.Traverse():
        targets = [t for r in prim.GetRelationships() for t in r.GetTargets()]
        targets += [t for a in prim.GetAttributes() for t in a.GetConnections()]
        for target in targets:
            if str(target).startswith(LIQUID) and not stage.GetObjectAtPath(target):
                raise ValueError(f'dangling liquid target: {target}')
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    (evidence/'physical_revision_audit.json').write_text(json.dumps(dict(
        status='pass',physical_content_identical=True,physical_prims=len(physical_state(stage)),
        scene_sha256=digest,source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest()),indent=2)+'\n')
    for name in ('task.yaml', 'metrics.yaml'):
        path = root/name
        data = yaml.safe_load(path.read_text())
        data['task_id'] = TASK_ID
        path.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False))
    config = root/'task_config.py'
    config.write_text(config.read_text().replace('vr_r1_5', 'vr_r1_6'))
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name in ('runtime_evidence', 'render_evidence', 'package_closure'):
        manifest.pop(name,None)
    manifest.update(package_id=TASK_ID,status='runtime_pending',source_revision=dict(
        package_id=source.name,scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest()))
    manifest['claims'].update(scene_cold_start_passes=0,scene_static_validation=False,
                             materialized_state_machine_success_path=False)
    recipe = manifest['receiver_liquid']
    recipe.pop('phase_paths',None)
    recipe.update(visual_mode='single_material',visual_paths=[LIQUID+'/Solution'],
                  shader_paths=[LIQUID+'/Looks/Water/Shader'],
                  controller_before_sha256=sha256(old_script.encode()).hexdigest(),
                  controller_after_sha256=sha256(new_script.encode()).hexdigest())
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    (evidence/'visual_liquid_recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    from scripts import titration_linear_policy as policy
    (evidence/'titration_policy.json').write_text(json.dumps(dict(
        policy=policy.contract(),scene_sha256=digest,owner='Scenario Forge task policy',
        policy_source_sha256=sha256(Path(policy.__file__).read_bytes()).hexdigest(),
        controller_sha256=sha256(new_script.encode()).hexdigest()),indent=2)+'\n')
    readme = (source/'README_CN.md').read_text().replace('VR r1.5','VR r1.6')
    readme += '\n锥形瓶采用唯一液体 Mesh `VisualLiquid/Solution` 和唯一 Shader `VisualLiquid/Looks/Water/Shader`。\n颜色连续写入 `inputs:glass_color`；阶段只用于逻辑判断，不切换液体几何。\n'
    (root/'README_CN.md').write_text(readme)
    shutil.copy2(ROOT/'docs/operations/titration-r16-color-guide.md',root/'COLOR_GUIDE_CN.md')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--out',type=Path,default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source,args.out))

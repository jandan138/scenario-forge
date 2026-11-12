"""Build the clean task09 scene with task14's supported-mass instrument."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
B = '/World/obj_analytical_balance'
PACKAGE_ID = 'scientific_workbench_solid_weighing_task09_r1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def controller_source(source):
    from pxr import Usd
    stage = Usd.Stage.Open(str(source))
    code = stage.GetPrimAtPath(B+'/BalanceRuntime/Graph/FlowController').GetAttribute('inputs:script').Get()
    # Reuse source device state/LCD/button implementations verbatim. The old PBD
    # inventory subclass is replaced with task09's rigid support graph.
    prefix = code.split('class Task14MassRuntime')[0]
    return '\n\n'.join([prefix, (ROOT/'scripts/task09_inventory.py').read_text(),
                         (ROOT/'scripts/task09_inventory_runtime.py').read_text(),
                         'def setup(db):\n    db.per_instance_state.runtime = None\n'
                         'def cleanup(db):\n    db.per_instance_state.runtime = None\n'])


def build(source_root, out, profile=None, material_closure=None, physics_profiles=()):
    from pxr import Usd, UsdGeom, UsdPhysics, UsdLux, Sdf, Gf, UsdUtils
    from scenario_forge.scaffold import scaffold_starter_package
    from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
    from scenario_forge.assets.checksum import compute_sha256
    from scenario_forge.package import validate_package
    out = Path(out).resolve()
    if (out/'manifest.yaml').exists():
        raise FileExistsError('Use a new candidate directory: '+str(out))
    scaffold_starter_package(out)
    shutil.rmtree(out/'assets/objects')
    shutil.rmtree(out/'assets/markers')
    source = source_root/'task_09_solid_weighing/scene.usd'
    donor = source_root/'task_14_fixed_weight_weighing/scene.usd'
    assets = out/'assets/composed'
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source.parent/'SubUSDs', assets/'SubUSDs')
    shutil.copytree(donor.parent/'SubUSDs', assets/'task14/SubUSDs')
    src = Usd.Stage.Open(str(source))
    src.GetRootLayer().Export(str(assets/'scene.usdc'))
    stage = Usd.Stage.Open(str(assets/'scene.usdc'))
    original_xform = UsdGeom.Xformable(stage.GetPrimAtPath(B)).ComputeLocalToWorldTransform(0)
    stage.RemovePrim(B)
    balance_stage = Usd.Stage.Open(str(donor))
    Sdf.CopySpec(balance_stage.GetRootLayer(), B, stage.GetRootLayer(), B)
    balance = stage.GetPrimAtPath(B)
    xf = UsdGeom.Xformable(balance)
    xf.ClearXformOpOrder()
    xf.AddTransformOp(opSuffix='task09Placement').Set(original_xform)
    for p in Usd.PrimRange(balance):
        for a in p.GetAttributes():
            if a.GetTypeName() == Sdf.ValueTypeNames.Asset:
                v = a.Get()
                if v and 'SubUSDs/' in v.path:
                    a.Set(Sdf.AssetPath('./task14/SubUSDs/'+v.path.split('SubUSDs/', 1)[1]))
    bbox = UsdGeom.BBoxCache(0, ['default', 'render'])
    feet = bbox.ComputeWorldBound(stage.GetPrimAtPath(B+'/Instance/Body/Feet')).ComputeAlignedRange()
    table = bbox.ComputeWorldBound(stage.GetPrimAtPath('/World/table')).ComputeAlignedRange()
    tabletop = float(table.GetMax()[2])
    corrected = Gf.Matrix4d(original_xform)
    xyz = corrected.ExtractTranslation()
    xyz[2] += tabletop - float(feet.GetMin()[2]) + .0005
    corrected.SetTranslateOnly(xyz)
    xf.GetOrderedXformOps()[0].Set(corrected)
    balance.GetAttribute('balance:tabletop_z').Set(tabletop)
    balance.GetAttribute('balance:resolution_g').Set(.01)
    balance.GetAttribute('balance:tolerance_g').Set(.01)
    balance.GetAttribute('balance:revision').Set('task09_supported_rigid_inventory_r1')
    balance.GetRelationship('balance:container').SetTargets(['/World/obj_weighing_boat'])
    balance.GetRelationship('balance:samples').SetTargets([f'/World/obj_grain_{i:02d}' for i in range(1, 6)])
    balance.CreateAttribute('balance:supported_sample_count', Sdf.ValueTypeNames.Int).Set(0)
    balance.CreateAttribute('balance:supported_paths', Sdf.ValueTypeNames.StringArray).Set([])
    balance.CreateAttribute('balance:support_diagnostics', Sdf.ValueTypeNames.String).Set('{}')
    stage.GetPrimAtPath(B+'/BalanceRuntime/Graph/FlowController').GetAttribute('inputs:script').Set(controller_source(donor))
    # Source dumps contain stale live values. Clear through the device reset on
    # first physics step, and publish an honest uninitialized static display.
    balance.GetAttribute('balance:reset_requested').Set(True)
    balance.GetAttribute('balance:lcd_readout').Set('------')
    balance.GetAttribute('balance:success').Set(False)
    balance.GetAttribute('balance:valid').Set(False)
    balance.GetAttribute('balance:stable').Set(False)
    balance.GetAttribute('balance:tared').Set(False)
    for p in list(stage.Traverse()):
        if p.IsA(UsdPhysics.Scene) or p.IsA(UsdLux.DomeLight) or p.IsA(UsdLux.DistantLight):
            stage.RemovePrim(p.GetPath())
    if profile:
        # Producer owns mass/inertia overrides; consume its authored values.
        mass_stage = Usd.Stage.Open(str(profile))
        for i in range(1, 6):
            path = f'/World/obj_grain_{i:02d}'
            for a in mass_stage.GetPrimAtPath(path).GetAttributes():
                if a.HasAuthoredValueOpinion():
                    stage.GetPrimAtPath(path).CreateAttribute(a.GetName(), a.GetTypeName()).Set(a.Get())
    for physics_profile in physics_profiles:
        producer = Usd.Stage.Open(str(physics_profile))
        for p in producer.TraverseAll():
            target = stage.GetPrimAtPath(p.GetPath())
            if not target:
                raise ValueError('Producer profile target missing: '+str(p.GetPath()))
            for a in p.GetAttributes():
                if a.HasAuthoredValueOpinion():
                    target.CreateAttribute(a.GetName(), a.GetTypeName()).Set(a.Get())
    masses = {f'/World/obj_grain_{i:02d}': float(stage.GetPrimAtPath(
        f'/World/obj_grain_{i:02d}').GetAttribute('physics:mass').Get())*1000 for i in range(1, 6)}
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            p.AddAppliedSchema('PhysxContactReportAPI')
            p.CreateAttribute('physxContactReport:threshold', Sdf.ValueTypeNames.Float).Set(0.)
    balance.GetAttribute('balance:target_g').Set(sum(masses.values()))
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    stage.GetRootLayer().Save()
    # Whole-scene composition preserves authored object transforms and source
    # collider structures; only the task's named changes are made above.
    main = out/'scene/main.usda'
    main.write_text('#usda 1.0\n(\n defaultPrim = "World"\n metersPerUnit = 1\n upAxis = "Z"\n subLayers = [@../assets/composed/scene.usdc@]\n)\n')
    if material_closure:
        shutil.copytree(material_closure, out/'assets/material_closure')
        main.write_text('#usda 1.0\n(\n defaultPrim = "World"\n metersPerUnit = 1\n upAxis = "Z"\n'
                        ' subLayers = [@../assets/material_closure/isaac45/task09/materials.usda@, '
                        '@../assets/material_closure/isaac45/task14/materials.usda@, '
                        '@../assets/composed/scene.usdc@]\n)\n')
    for version in ('41', '45'):
        compat = Usd.Stage.CreateNew(str(out/f'scene/runtime{version}.usda'))
        material_layers = ([f'../assets/material_closure/isaac{version}/{task}/materials.usda'
                            for task in ('task09', 'task14')] if material_closure else [])
        compat.GetRootLayer().subLayerPaths = [*material_layers, './main.usda']
        compat.SetDefaultPrim(compat.GetPrimAtPath('/World'))
        compat.OverridePrim(B+'/BalanceRuntime/Graph/OnPhysicsStep').CreateAttribute(
            'node:type', Sdf.ValueTypeNames.Token).Set(
                'omni.isaac.core_nodes.OnPhysicsStep' if version == '41' else 'isaacsim.core.nodes.OnPhysicsStep')
        compat.GetRootLayer().Save()
        demo = Usd.Stage.CreateNew(str(out/f'scene/demo{version}.usda'))
        demo.GetRootLayer().subLayerPaths = [f'./runtime{version}.usda']
        UsdGeom.SetStageUpAxis(demo, 'Z')
        UsdGeom.SetStageMetersPerUnit(demo, 1.)
        demo.SetDefaultPrim(demo.GetPrimAtPath('/World'))
        physics = UsdPhysics.Scene.Define(demo, '/World/PhysicsScene')
        physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
        physics.CreateGravityMagnitudeAttr(9.81)
        p = physics.GetPrim()
        p.AddAppliedSchema('PhysxSceneAPI')
        for name, kind, value in [('enableGPUDynamics', Sdf.ValueTypeNames.Bool, True),
                                 ('broadphaseType', Sdf.ValueTypeNames.Token, 'GPU'),
                                 ('solverType', Sdf.ValueTypeNames.Token, 'TGS'),
                                 ('timeStepsPerSecond', Sdf.ValueTypeNames.UInt, 120)]:
            p.CreateAttribute('physxScene:'+name, kind).Set(value)
        UsdLux.DomeLight.Define(demo, '/World/DemoLight').CreateIntensityAttr(900)
        demo.GetRootLayer().Save()
    # Package contract: one composed asset owns the full imported scene.
    asset_id = 'task09_composed_scene'
    asset_rows = [{
        'asset_id': asset_id, 'role': 'environment', 'asset_type': 'scene',
        'canonical_usd': 'assets/composed/scene.usdc', 'license': 'internal-colleague-source',
        'sha256': compute_sha256(assets/'scene.usdc')}]
    if material_closure:
        for version in ('41', '45'):
            for task in ('task09', 'task14'):
                relative = f'assets/material_closure/isaac{version}/{task}/materials.usda'
                asset_rows.append({'asset_id': f'{task}_materials{version}', 'role': 'environment',
                                   'asset_type': 'material_overlay', 'canonical_usd': relative,
                                   'license': 'source-NVIDIA-notices-preserved',
                                   'sha256': compute_sha256(out/relative)})
    write_yaml(out/'assets/asset_manifest.yaml', {'schema_version': 'asset-manifest/v0.2', 'assets': asset_rows})
    write_asset_lock(out, generate_asset_lock(out))
    write_yaml(out/'scene/instances.yaml', {'schema_version': 'scene-instances/v0.2', 'instances': [{
        'id': 'task09_scene', 'asset_id': asset_id, 'source_prim_path': '/World',
        'pose': {'xyz': [0, 0, 0], 'wxyz': [1, 0, 0, 0]}, 'initial_state': {}}]})
    write_yaml(out/'scene/layout.yaml', {'schema_version': 'scene-layout/v0.2', 'frames': [{'id': 'world', 'type': 'root'}], 'zones': []})
    write_yaml(out/'task/task.yaml', {'schema_version': 'task/v0.2', 'task_id': PACKAGE_ID,
        'task_family': 'solid_weighing', 'instruction': 'Tare the empty boat, then weigh all five solids.',
        'mass_g': masses, 'target_g': sum(masses.values()), 'tolerance_g': .01,
        'hold_s': 2., 'measurement_source': 'supported_mass_inventory',
        'success': {'type': 'runtime_attribute', 'path': B, 'attribute': 'balance:success'}})
    write_yaml(out/'task/task_graph.yaml', {'schema_version': 'task-graph/v0.2', 'nodes': [
        {'id': 'tare'}, {'id': 'load_five'}, {'id': 'stable_total'}], 'edges': [
        {'from': 'tare', 'to': 'load_five'}, {'from': 'load_five', 'to': 'stable_total'}]})
    write_yaml(out/'task/predicates.yaml', {'schema_version': 'predicates/v0.2', 'predicates': [
        {'id': 'weighed_five', 'type': 'runtime_attribute', 'path': B, 'attribute': 'balance:success'}]})
    write_yaml(out/'task/safety_rules.yaml', {'schema_version': 'safety-rules/v0.2', 'rules': []})
    write_yaml(out/'robot/robot.yaml', {'schema_version': 'robot/v0.2', 'robot_id': 'none', 'embodiment': 'none', 'action_space': 'none', 'sensors': []})
    write_yaml(out/'robot/robot_profile.yaml', {'schema_version': 'robot-profile/v0.2', 'robot_id': 'none', 'workspace': {'frame': 'world'}})
    write_yaml(out/'metrics/metrics.yaml', {'schema_version': 'metrics/v0.2', 'metrics': [], 'claim': 'fixture_only_no_benchmark'})
    write_yaml(out/'metrics/splits.yaml', {'schema_version': 'splits/v0.2', 'splits': [{'name': 'fixture', 'package_ids': [PACKAGE_ID]}]})
    manifest = yaml.safe_load((out/'manifest.yaml').read_text())
    manifest.update(package_id=PACKAGE_ID, targets=['ebench', 'embodied-eval-os'])
    manifest['validation']['minimum_required_level'] = 'package_schema_validated'
    write_yaml(out/'manifest.yaml', manifest)
    write_yaml(out/'generation_plan.yaml', {'schema_version': 'scenario-generation-plan/v0.2',
        'package_id': PACKAGE_ID, 'seed': 0, 'target_exports': ['ebench', 'embodied-eval-os'], 'package_mode': 'fat'})
    provenance = {'schema_version': 'provenance/v0.2', 'generator': 'build_task09_inventory_package.py',
        'sources': [{'path': str(p), 'sha256': sha(p)} for p in [source, donor] + ([profile] if profile else []) + list(physics_profiles)],
        'measurement_source': 'supported_mass_inventory', 'runtime_status': 'not_run'}
    write_yaml(out/'provenance/provenance.yaml', provenance)
    write_yaml(out/'provenance/source_refs.yaml', {'sources': provenance['sources']})
    (out/'scripts').mkdir(exist_ok=True)
    for name in ('task09_inventory.py', 'task09_inventory_runtime.py'):
        shutil.copy2(ROOT/'scripts'/name, out/'scripts'/name)
    # Source scenes carry only file assets; report every unresolved dependency.
    _, _, unresolved = UsdUtils.ComputeAllDependencies(str(main))
    checks = {'unresolved': list(unresolved), 'scene_sha256': sha(assets/'scene.usdc'), 'mass_g': masses}
    (out/'evidence/build.json').write_text(json.dumps(checks, indent=2))
    result = validate_package(out, require_asset_lock=True)
    if not result.ok:
        raise ValueError(result.messages)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/mnt/data/chenjiantong/scene_usd'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--profile', type=Path)
    p.add_argument('--material-closure', type=Path)
    p.add_argument('--physics-profile', type=Path, action='append', default=[])
    a = p.parse_args()
    print(build(a.source, a.out, a.profile, a.material_closure, a.physics_profile))

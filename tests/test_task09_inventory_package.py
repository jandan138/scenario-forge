"""Checks against the candidate generated from the colleague's source USD."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT/'outputs/task09_solid_weighing_r1_20261008/handoff/scientific_workbench_solid_weighing_task09_r1'


@pytest.mark.local_artifacts
def test_clean_entry_has_functional_balance_without_demo_environment():
    from pxr import Usd, UsdPhysics, UsdLux, UsdUtils
    from scenario_forge.package import validate_package
    assert validate_package(PACKAGE).ok
    stage = Usd.Stage.Open(str(PACKAGE/'scene/main.usda'))
    assert not any(p.IsA(UsdPhysics.Scene) or p.HasAPI(UsdLux.LightAPI) for p in stage.Traverse())
    assert stage.GetPrimAtPath('/World/table')
    b = stage.GetPrimAtPath('/World/obj_analytical_balance')
    assert not stage.GetPrimAtPath(str(b.GetPath())+'/Instance/Chassis')
    assert stage.GetPrimAtPath(str(b.GetPath())+'/Instance/Body').GetAttribute('physics:mass').Get() == pytest.approx(6.8)
    assert stage.GetPrimAtPath(str(b.GetPath())+'/Instance/WeighingPan').HasAPI(UsdPhysics.RigidBodyAPI)
    assert b.GetAttribute('balance:measurement_source').Get() == 'supported_mass_inventory'
    assert b.GetAttribute('balance:target_g').Get() == pytest.approx(4.5587398927)
    assert b.GetAttribute('balance:resolution_g').Get() == .01
    code = stage.GetPrimAtPath(str(b.GetPath())+'/BalanceRuntime/Graph/FlowController').GetAttribute('inputs:script').Get()
    assert 'class Task09InventoryRuntime' in code
    assert 'from scripts.' not in code
    assert UsdUtils.ComputeAllDependencies(str(PACKAGE/'scene/main.usda'))[2] == []
    for p in stage.Traverse():
        if p.IsA(UsdPhysics.Joint):
            for rel in ('physics:body0', 'physics:body1'):
                assert all(stage.GetPrimAtPath(t) for t in p.GetRelationship(rel).GetTargets())


@pytest.mark.local_artifacts
def test_runtime_entrypoints_have_one_physics_scene_and_correct_step_node():
    from pxr import Usd, UsdPhysics
    for version, node in [('41', 'omni.isaac.core_nodes.OnPhysicsStep'),
                          ('45', 'isaacsim.core.nodes.OnPhysicsStep')]:
        stage = Usd.Stage.Open(str(PACKAGE/f'scene/demo{version}.usda'))
        assert sum(p.IsA(UsdPhysics.Scene) for p in stage.Traverse()) == 1
        graph = stage.GetPrimAtPath('/World/obj_analytical_balance/BalanceRuntime/Graph/OnPhysicsStep')
        assert graph.GetAttribute('node:type').Get() == node


@pytest.mark.local_artifacts
def test_embedded_source_policy_tare_completion_live_unload_and_reset():
    from pxr import Usd
    stage = Usd.Stage.Open(str(PACKAGE/'scene/main.usda'))
    p = stage.GetPrimAtPath('/World/obj_analytical_balance/BalanceRuntime/Graph/FlowController')
    namespace = {}
    exec(p.GetAttribute('inputs:script').Get(), namespace)
    state = namespace['BalanceState'](.01, target_g=4.55874, tolerance_g=.01)
    for _ in range(360):
        state.update(10., 1/120)
    state.update(10., 1/120, pressed=True)
    for _ in range(360):
        state.update(10., 1/120)
    assert state.tared and abs(state.net_g) < .01
    for _ in range(480):
        state.update(14.55874, 1/120, eligible=False)
    assert not state.success
    for _ in range(300):
        state.update(14.55874, 1/120, eligible=True)
    assert state.success and state.display() == '4.56'
    for _ in range(360):
        state.update(10., 1/120)
    assert state.success and state.display() == '0.00'
    state.reset()
    assert not state.success and not state.tared


@pytest.mark.local_artifacts
def test_vr_entry_adds_wet_chemistry_room_and_direct_open_light(tmp_path):
    from pxr import Usd, UsdLux, UsdPhysics, UsdUtils
    from scripts.build_task09_solid_weighing_vr import TASK_ID, build

    before = (PACKAGE / 'scene/main.usda').read_bytes()
    vr = build(PACKAGE, tmp_path / 'vr')
    assert (PACKAGE / 'scene/main.usda').read_bytes() == before
    stage = Usd.Stage.Open(str(vr / 'scene.usd'))
    assert str(stage.GetDefaultPrim().GetPath()) == '/World'
    assert not stage.GetPrimAtPath('/World/_scene').IsValid()
    world = stage.GetPrimAtPath('/World')
    names = [child.GetName() for child in world.GetChildren()]
    assert 'background' in names and 'table' in names and 'vr_direct_open_light' in names
    assert any(name.startswith('obj_') for name in names)
    light = world.GetChild('vr_direct_open_light')
    assert light.GetTypeName() == 'DomeLight'
    assert light.GetAttribute('inputs:intensity').Get() == pytest.approx(750)
    assert light.GetAttribute('inputs:exposure').Get() == pytest.approx(0)
    assert tuple(light.GetAttribute('inputs:color').Get()) == pytest.approx((1, 1, 1))
    texture = light.GetAttribute('inputs:texture:file').Get()
    assert texture is None or not texture.path
    room = world.GetChild('background').GetMetadata('references').GetAddedOrExplicitItems()[0]
    assert 'scientific_environment_code_room_wet_chemistry_v2' in room.assetPath
    assert not Path(room.assetPath).is_absolute()
    assert not any(prim.IsA(UsdPhysics.Scene) and prim.IsActive() for prim in stage.Traverse())
    clean = Usd.Stage.Open(str(PACKAGE / 'scene/main.usda'))
    assert not any(prim.IsA(UsdPhysics.Scene) or prim.HasAPI(UsdLux.LightAPI) for prim in clean.Traverse())
    assert UsdUtils.ComputeAllDependencies(str(vr / 'scene.usd'))[2] == []
    config_path = vr / 'task_config.py'
    namespace: dict = {'__file__': str(config_path)}
    exec(compile(config_path.read_text(encoding='utf-8'), str(config_path), 'exec'), namespace)
    task = namespace['TASKS'][TASK_ID]
    roots = [name for name in names if name.startswith('obj_')]
    links = [
        str(prim.GetPath()).replace('/World/', '/World/_scene/', 1)
        for prim in Usd.PrimRange(stage.GetPrimAtPath('/World/obj_analytical_balance'))
        if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    ]
    assert task['obj_prim_list'] == [f'/World/_scene/{name}' for name in roots] + links
    randomized = [item for group in task['layout_randomization']['objects'] for item in group['objs']]
    assert randomized == roots
    assert task['layout_randomization']['table'] == 'table'
    assert 'background' not in randomized and 'vr_direct_open_light' not in randomized
    for group in task['layout_randomization']['objects']:
        assert group['x_offset_range'] == [-0.01, 0.01]
        assert group['yaw_range_degrees'] == [0.0, 0.0]
    assert task['physx_scene_cfg']['TimeStepsPerSecond'] == 120
    assert task['scene_usd_file_path']['scene1'].endswith(f'scenes/{TASK_ID}/scene.usd')

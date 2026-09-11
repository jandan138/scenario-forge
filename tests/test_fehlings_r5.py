import ast
import json
import math
import runpy

import pytest

from scripts.fehlings_r5_state import appearance


def test_initial_regions_match_and_final_material_is_solid_red():
    for t in (-10, 0, 15, 30):
        look = appearance(t)
        assert look['color'] == look['sediment_color'] == (.40, .72, .95)
        assert look['opacity'] == look['sediment_opacity'] == .55
        assert look['roughness'] == look['sediment_roughness']
    end = appearance(60)
    assert end['color'] == pytest.approx((.94, .97, 1))
    assert end['opacity'] == pytest.approx(.25)
    assert end['sediment_color'] == pytest.approx((.70, .18, .07))
    assert end['sediment_opacity'] == 1
    assert end['sediment_roughness'] == pytest.approx(.65)
    assert appearance(100) == end


def test_cloud_peak_and_continuous_monotonic_bottom_development():
    assert appearance(45)['color'] == pytest.approx((.65, .30, .14))
    assert appearance(45)['opacity'] == pytest.approx(.8)
    previous = appearance(30)
    for i in range(1, 301):
        look = appearance(30 + i / 10)
        assert look['sediment_opacity'] >= previous['sediment_opacity']
        assert look['sediment_roughness'] >= previous['sediment_roughness']
        assert look['sediment_color'][0] >= previous['sediment_color'][0]
        assert look['sediment_color'][2] <= previous['sediment_color'][2]
        previous = look
    for boundary in (30, 45, 60):
        left, right = appearance(boundary - 1e-6), appearance(boundary + 1e-6)
        for key in ('opacity', 'sediment_opacity', 'roughness', 'sediment_roughness'):
            assert abs(left[key] - right[key]) < 1e-6
        for key in ('color', 'sediment_color'):
            assert math.dist(left[key], right[key]) < 1e-6


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r5 import build
    return build(output=tmp_path_factory.mktemp('bath-r5'))


def visual_snapshot(stage, tube):
    from pxr import Usd
    return {str(p.GetPath()): {a.GetName(): str(a.Get()) for a in p.GetAttributes()}
            for p in Usd.PrimRange(stage.GetPrimAtPath(tube + '/VisualLiquid'))
            if '/Looks' not in str(p.GetPath())}


@pytest.mark.local_artifacts
def test_fixed_regions_fit_cavity_and_only_materials_change_in_embedded_controller(package):
    from pxr import Gf, Usd, UsdGeom
    from scripts.generate_fehlings_water_bath_r5 import TUBE, GRAPH
    from scripts.fehlings_r2_state import radius_at
    stage = Usd.Stage.Open(str(package / 'scene.usd'))
    tube = stage.GetPrimAtPath(TUBE)
    profile = [tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    floor, top = profile[0][0], tube.GetAttribute('fehlings:sample_height_m').Get()
    split = floor + (top - floor) / 3
    assert tube.GetAttribute('fehlings:sediment_height_m').Get() == pytest.approx(split-floor)
    assert tube.GetAttribute('fehlings:sediment_height_fraction').Get() == pytest.approx(1/3)
    for label, low, high in [('Sample', split, top), ('Sediment', floor, split)]:
        points = stage.GetPrimAtPath(TUBE + '/VisualLiquid/' + label + '/body').GetAttribute('points').Get()
        assert min(p[2] for p in points) == pytest.approx(low)
        assert max(p[2] for p in points) == pytest.approx(high)
        for x, y, z in points:
            assert math.hypot(x, y) <= radius_at(profile, z) + 1e-7
    script = stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
    tree = ast.parse(script)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert not {'geometry', 'fitted_region', 'volume_to_height', 'mesh_topology'} & functions.keys()
    # Exercise the actual embedded material writer on a real USD Stage without Isaac imports.
    namespace = {'Gf': Gf, 'UsdGeom': UsdGeom, 'appearance': appearance}
    selected = [functions[n] for n in ('initial_state', '_target', '_apply_state')]
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<r5 writer>', 'exec'), namespace)
    before = visual_snapshot(stage, TUBE)
    for seconds in (0, 30, 37.5, 45, 52.5, 60, 0):
        namespace['_state'] = dict(namespace['initial_state'](), heated_s=seconds)
        namespace['_apply_state'](stage, tube)
        assert visual_snapshot(stage, TUBE) == before
        look = appearance(seconds)
        for label, prefix in [('Sample', ''), ('Sediment', 'sediment_')]:
            shader = stage.GetPrimAtPath(TUBE + '/VisualLiquid/Looks/' + label + '/Shader')
            assert tuple(shader.GetAttribute('inputs:diffuseColor').Get()) == pytest.approx(look[prefix+'color'])
            assert shader.GetAttribute('inputs:opacity').Get() == pytest.approx(look[prefix+'opacity'])
            assert shader.GetAttribute('inputs:roughness').Get() == pytest.approx(look[prefix+'roughness'])


@pytest.mark.local_artifacts
def test_r3_physics_contact_and_task_documents_survive_r5_finalization(package):
    from pxr import Usd
    from scripts.generate_fehlings_water_bath_r5 import SOURCE, TUBE, GRAPH, POLICY_VERSION, TASK_ID
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    from scripts.finalize_fehlings_water_bath import write_versioned_task_documents
    old = Usd.Stage.Open(str(SOURCE / 'scene.usd'))
    new = Usd.Stage.Open(str(package / 'scene.usd'))
    assert physical_state(old) == physical_state(new)
    def functions(stage):
        script = stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
        return {n.name: ast.dump(n) for n in ast.parse(script).body if isinstance(n, ast.FunctionDef)}
    a, b = functions(old), functions(new)
    for name in ('advance', 'initial_state', 'bath_contact', 'frustum_overlap'):
        assert a[name] == b[name]
    assert new.GetPrimAtPath(TUBE).GetAttribute('fehlings:policy_version').Get() == POLICY_VERSION
    write_versioned_task_documents(package)
    cfgs = runpy.run_path(str(package/'task_config.py'))['TASKS']
    assert list(cfgs) == [TASK_ID]
    cfg = cfgs[TASK_ID]
    assert cfg['water_bath']['reaction_policy']['geometry_updates'] is False
    assert cfg['water_bath']['reaction_policy']['version'] == POLICY_VERSION
    manifest = json.loads((package/'manifest.json').read_text())
    assert manifest['status'] == 'runtime_pending'
    assert manifest['claims']['visual_reaction_verified'] is False


@pytest.mark.local_artifacts
def test_reset_restores_both_materials_without_readable_pose_and_missing_pose_pauses(package):
    from types import SimpleNamespace
    from pxr import Gf, Usd
    from scripts.generate_fehlings_water_bath_r5 import TUBE, GRAPH
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    stage.SetEditTarget(stage.GetSessionLayer())
    tube = stage.GetPrimAtPath(TUBE)
    script = stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
    selected = [n for n in ast.parse(script).body if isinstance(n, ast.FunctionDef)
                and n.name in ('initial_state', '_target', '_apply_state', 'compute')]
    class NoPose:
        calls = 0

        def acquire_dynamic_control_interface(self):
            self.calls += 1
            return SimpleNamespace(get_rigid_body=lambda path: 0)
    dc = NoPose()
    namespace = dict(Gf=Gf, math=math, appearance=appearance, _dynamic_control=dc,
                     omni=SimpleNamespace(usd=SimpleNamespace(get_context=lambda: SimpleNamespace(get_stage=lambda: stage))))
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<r5 compute>', 'exec'), namespace)
    db = SimpleNamespace(node=SimpleNamespace(get_prim_path=lambda: GRAPH+'/FlowController'),
                         inputs=SimpleNamespace(deltaSeconds=1))
    namespace['_state'] = dict(namespace['initial_state'](), heated_s=60, success=True)
    namespace['_apply_state'](stage, tube)
    before = visual_snapshot(stage, TUBE)
    tube.GetAttribute('fehlings:reset_requested').Set(True)
    assert namespace['compute'](db)
    assert dc.calls == 0
    assert namespace['_state'] == namespace['initial_state']()
    for label in ('Sample', 'Sediment'):
        shader = stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/'+label+'/Shader')
        assert tuple(shader.GetAttribute('inputs:diffuseColor').Get()) == pytest.approx((.40,.72,.95))
        assert shader.GetAttribute('inputs:opacity').Get() == pytest.approx(.55)
        assert shader.GetAttribute('inputs:roughness').Get() == pytest.approx(.08)
    namespace['_state']['heated_s'] = 37.5
    namespace['_apply_state'](stage, tube)
    assert namespace['compute'](db)
    assert dc.calls == 1
    assert namespace['_state']['heated_s'] == 37.5
    assert not tube.GetAttribute('fehlings:pose_available').Get()
    assert not tube.GetAttribute('fehlings:bath_contact').Get()
    assert visual_snapshot(stage, TUBE) == before

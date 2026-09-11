import ast
import colorsys
import json
import math
import runpy
from types import SimpleNamespace

import pytest
import yaml

from scripts.fehlings_r6_state import appearance, advance, initial_state


def test_five_layers_start_blue_visit_green_yellow_orange_and_end_red_at_30():
    start, end = appearance(0), appearance(30)
    assert len(start['layers']) == len(end['layers']) == 5
    assert all(layer == start['layers'][0] for layer in start['layers'])
    assert all(layer == end['layers'][0] for layer in end['layers'])
    assert start['layers'][0]['color'][2] > start['layers'][0]['color'][0]
    red = end['layers'][0]
    assert red['color'][0] > 3 * red['color'][1] and red['opacity'] >= .95
    assert appearance(-100) == start and appearance(100) == end
    for i in range(5):
        hues = [colorsys.rgb_to_hsv(*appearance(t/10)['layers'][i]['color'])[0]*360
                for t in range(301)]
        for low, high in ((100,140), (45,65), (20,35)):
            assert any(low < hue < high for hue in hues), (i,low,high)


def test_layer_progress_is_staggered_and_all_inputs_change_continuously():
    for t in (6, 9, 12, 15, 21, 27):
        layers = appearance(t)['layers']
        assert layers[0]['progress'] > layers[-1]['progress']
        assert all(a['progress'] >= b['progress'] for a,b in zip(layers,layers[1:]))
    assert len({tuple(v['color']) for v in appearance(15)['layers']}) == 5
    previous = appearance(0)['layers']
    for tick in range(1,3001):
        current = appearance(tick/100)['layers']
        for a,b in zip(previous,current):
            assert math.dist(a['color'],b['color']) < .02
            assert abs(a['opacity']-b['opacity']) < .01
            assert abs(a['roughness']-b['roughness']) < .01
            assert b['progress'] >= a['progress']
        previous = current


def test_30_second_gate_pause_observation_motion_and_success_latch():
    state = advance(initial_state(),29.9,True,False,(0,0,0))
    paused = advance(state,100,False,True,(0,0,0))
    assert paused['heated_s'] == 29.9 and paused['observe_s'] == 0 and not paused['success']
    ready = advance(paused,.1,True,False,(0,0,0))
    assert ready['heated_s'] == pytest.approx(30) and ready['stage'] == 'ready_to_withdraw'
    observing = advance(ready,2.9,False,True,(0,0,0))
    assert not observing['success']
    moved = advance(observing,.1,False,True,(.03,0,0))
    assert moved['observe_s'] == 0
    success = advance(moved,3,False,True,(.03,0,0))
    assert success['success']
    assert advance(success,100,True,False,(1,1,1)) == success
    assert advance(initial_state(),100,True,False,(0,0,0))['heated_s'] == 30


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r6 import build
    return build(output=tmp_path_factory.mktemp('bath-r6'))


@pytest.mark.local_artifacts
def test_equal_height_fitted_layers_have_no_internal_caps_and_resolving_bindings(package):
    from pxr import Usd, UsdGeom, UsdShade
    from scripts.fehlings_r2_state import radius_at
    from scripts.generate_fehlings_water_bath_r6 import TUBE
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    tube = stage.GetPrimAtPath(TUBE)
    profile = [tuple(p) for p in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    low, high = profile[0][0], tube.GetAttribute('fehlings:sample_height_m').Get()
    paths = tube.GetRelationship('fehlings:layerMeshes').GetTargets()
    shaders = tube.GetRelationship('fehlings:layerShaders').GetTargets()
    assert len(paths) == len(shaders) == 5
    previous_ring = None
    for i,path in enumerate(paths):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
        points = mesh.GetPointsAttr().Get()
        zs = [p[2] for p in points]
        assert min(zs) == pytest.approx(low+(high-low)*i/5)
        assert max(zs) == pytest.approx(low+(high-low)*(i+1)/5)
        for x,y,z in points:
            assert math.hypot(x,y) <= radius_at(profile,z)+1e-7
        counts,indices = mesh.GetFaceVertexCountsAttr().Get(), mesh.GetFaceVertexIndicesAttr().Get()
        assert UsdGeom.Mesh.ValidateTopology(indices,counts,len(points))[0]
        assert len(mesh.GetNormalsAttr().Get()) == len(points)
        ring = {tuple(p) for p in points if abs(p[2]-min(zs)) < 1e-8}
        if previous_ring is not None:
            assert ring == previous_ring
        previous_ring = {tuple(p) for p in points if abs(p[2]-max(zs)) < 1e-8}
        offset = 0
        for count in counts:
            face = [points[j] for j in indices[offset:offset+count]]
            offset += count
            if max(p[2] for p in face)-min(p[2] for p in face) < 1e-8:
                assert face[0][2] == pytest.approx(low) or face[0][2] == pytest.approx(high)
        material,_ = UsdShade.MaterialBindingAPI(mesh.GetPrim()).ComputeBoundMaterial()
        assert material.GetSurfaceOutput().GetConnectedSource()[0].GetPrim().GetPath() == shaders[i]
    assert not tube.GetRelationship('fehlings:sampleShader')
    assert not tube.GetAttribute('fehlings:sediment_height_m')


@pytest.mark.local_artifacts
def test_embedded_writer_changes_all_layers_and_reset_needs_no_pose(package):
    from pxr import Usd, Gf
    from scripts.generate_fehlings_water_bath_r6 import TUBE, GRAPH
    from scripts.fehlings_r6_evidence import capture_visual
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    stage.SetEditTarget(stage.GetSessionLayer())
    tube = stage.GetPrimAtPath(TUBE)
    script = stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
    # Execute the actual shipped functions without importing Isaac in unit tests.
    tree = ast.parse(script)
    tree.body = [n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    ns = dict(math=math,Gf=Gf,omni=SimpleNamespace(usd=SimpleNamespace(
        get_context=lambda: SimpleNamespace(get_stage=lambda: stage))))
    exec(compile(tree,'<r6 controller>','exec'),ns)
    before = capture_visual(stage,tube)['geometry_sha256']
    for t in (0,3,9,15,21,27,30):
        ns['_state'] = dict(ns['initial_state'](),heated_s=t)
        ns['_apply_state'](stage,tube)
        snap = capture_visual(stage,tube)
        assert snap['geometry_sha256'] == before
        for actual,expected in zip(snap['layers'],appearance(t)['layers']):
            assert actual['color'] == pytest.approx(expected['color'])
            assert actual['opacity'] == pytest.approx(expected['opacity'])
            assert actual['roughness'] == pytest.approx(expected['roughness'])
    tube.GetAttribute('fehlings:reset_requested').Set(True)
    db = SimpleNamespace(node=SimpleNamespace(get_prim_path=lambda: GRAPH+'/FlowController'),
                         inputs=SimpleNamespace(deltaSeconds=1))
    # No dynamic-control object provided: reset must return before attempting pose access.
    assert ns['compute'](db)
    assert ns['_state'] == initial_state()
    snap = capture_visual(stage,tube)
    assert all(layer['color'] == pytest.approx(appearance(0)['layers'][0]['color']) for layer in snap['layers'])
    assert snap['geometry_sha256'] == before
    ns['_dynamic_control'] = SimpleNamespace(acquire_dynamic_control_interface=lambda: SimpleNamespace(get_rigid_body=lambda path:0))
    ns['_state']['heated_s'] = 15
    assert ns['compute'](db)
    assert ns['_state']['heated_s'] == 15 and not tube.GetAttribute('fehlings:pose_available').Get()


@pytest.mark.local_artifacts
def test_r5_physics_contact_and_all_30_second_documents_survive_finalization(package):
    from pxr import Usd, UsdGeom
    from scripts.generate_fehlings_water_bath_r6 import SOURCE, TASK_ID, GRAPH
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    from scripts.finalize_fehlings_water_bath import write_versioned_task_documents
    old, new = Usd.Stage.Open(str(SOURCE/'scene.usd')), Usd.Stage.Open(str(package/'scene.usd'))
    assert physical_state(old) == physical_state(new)
    oc,nc = UsdGeom.XformCache(),UsdGeom.XformCache()
    for p in old.TraverseAll():
        if UsdGeom.Xformable(p) and '/VisualLiquid' not in str(p.GetPath()):
            assert oc.GetLocalToWorldTransform(p) == nc.GetLocalToWorldTransform(new.GetPrimAtPath(p.GetPath()))
    def functions(stage):
        code = stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
        return {n.name: ast.dump(n) for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
    a,b = functions(old),functions(new)
    for name in ('compute','bath_contact','frustum_overlap'):
        assert a[name] == b[name]
    write_versioned_task_documents(package)
    task = yaml.safe_load((package/'task.yaml').read_text())
    assert task['color_complete_seconds'] == task['immersion_hold_seconds'] == 30
    assert {'id':'heat_30s'} in task['steps'] and {'id':'heat_60s'} not in task['steps']
    metrics = yaml.safe_load((package/'metrics.yaml').read_text())
    assert metrics['aggregation']['primary_metric_id'] == 'heat_30s'
    assert metrics['metrics'][0]['id'] == 'heat_30s'
    cfgs = runpy.run_path(str(package/'task_config.py'))['TASKS']
    assert list(cfgs) == [TASK_ID]
    bath = cfgs[TASK_ID]['water_bath']
    assert bath['hold_seconds'] == bath['color_complete_seconds'] == 30
    assert bath['reaction_policy']['layer_count'] == 5
    assert bath['reaction_policy']['heating_complete_seconds'] == 30
    manifest = json.loads((package/'manifest.json').read_text())
    assert manifest['status'] == 'runtime_pending'
    assert not manifest['claims']['visual_reaction_verified']

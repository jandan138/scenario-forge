import ast
import json

import pytest
from pxr import Gf, Usd, UsdGeom, UsdShade

from scripts.generate_traditional_titration_vr_r16 import build, SOURCE, STATION, LIQUID
from scripts.titration_linear_policy import color, TRANSITION_START, PINK_END
from scripts.finalize_traditional_titration_vr_r14 import physical_state


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    return build(output=tmp_path_factory.mktemp('r16'))


def test_single_mesh_material_binding_and_unchanged_physics(package):
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    old = Usd.Stage.Open(str(SOURCE/'scene.usd'))
    assert physical_state(stage) == physical_state(old)
    prims = list(Usd.PrimRange(stage.GetPrimAtPath(LIQUID)))
    assert [str(p.GetPath()) for p in prims if p.IsA(UsdGeom.Mesh)] == [LIQUID+'/Solution']
    assert [str(p.GetPath()) for p in prims if p.IsA(UsdShade.Material)] == [LIQUID+'/Looks/Water']
    assert [str(p.GetPath()) for p in prims if p.IsA(UsdShade.Shader)] == [LIQUID+'/Looks/Water/Shader']
    mesh = stage.GetPrimAtPath(LIQUID+'/Solution')
    material, _ = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial()
    assert str(material.GetPath()) == LIQUID+'/Looks/Water'
    assert str(material.ComputeSurfaceSource('mdl')[0].GetPath()) == LIQUID+'/Looks/Water/Shader'
    for name in ('points', 'normals', 'faceVertexCounts', 'faceVertexIndices'):
        assert mesh.GetAttribute(name).Get() == old.GetPrimAtPath(LIQUID+'/SolutionColorless').GetAttribute(name).Get()
    assert not mesh.GetAttribute('titration:phase')
    station = stage.GetPrimAtPath(STATION)
    assert [str(t) for t in station.GetRelationship('titration:receiverLiquidVisuals').GetTargets()] == [LIQUID+'/Solution']
    assert [str(t) for t in station.GetRelationship('titration:receiverLiquidShader').GetTargets()] == [LIQUID+'/Looks/Water/Shader']


def test_embedded_update_uses_same_visible_mesh_for_all_colors(package):
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    stage.SetEditTarget(stage.GetSessionLayer())
    script = stage.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script').Get()
    # Retain the source Stage while reading its prim.
    old = Usd.Stage.Open(str(SOURCE/'scene.usd'))
    old_script = old.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script').Get()
    def functions(text):
        return {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
    before, after = functions(old_script), functions(script)
    assert {n for n in before if before[n] != after[n]} == {'_sync_receiver'}
    node = next(n for n in ast.parse(script).body if isinstance(n, ast.FunctionDef) and n.name == '_sync_receiver')
    namespace = dict(Gf=Gf, ROOT=STATION, _color=color,
                     _prim=lambda s, p: s.GetPrimAtPath(str(p)),
                     _set=lambda s, p, n, v: s.GetPrimAtPath(str(p)).GetAttribute(n).Set(v))
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<receiver controller>', 'exec'), namespace)
    paths = [str(p.GetPath()) for p in stage.Traverse()]
    for volume in (0, TRANSITION_START, (TRANSITION_START+15)/2, 15, PINK_END, PINK_END+.5, PINK_END+1, 0):
        namespace['_sync_receiver'](stage, volume)
        shader = stage.GetPrimAtPath(LIQUID+'/Looks/Water/Shader')
        assert tuple(shader.GetAttribute('inputs:glass_color').Get()) == pytest.approx(color(volume)[1])
        assert UsdGeom.Imageable(stage.GetPrimAtPath(LIQUID+'/Solution')).ComputeVisibility() == 'inherited'
        assert stage.GetPrimAtPath(STATION).GetAttribute('titration:indicator_phase').Get() == color(volume)[0]
        assert [str(p.GetPath()) for p in stage.Traverse()] == paths


def test_new_package_identity_docs_and_fresh_evidence(package):
    manifest = json.loads((package/'manifest.json').read_text())
    assert manifest['package_id'].endswith('r1_6')
    assert manifest['status'] == 'runtime_pending'
    assert manifest['receiver_liquid']['visual_mode'] == 'single_material'
    assert 'runtime_evidence' not in manifest
    assert not (package/'evidence/runtime').exists()
    assert '/Looks/Water/Shader' in (package/'COLOR_GUIDE_CN.md').read_text()
    assert '(COLOR_GUIDE_CN.md)' in (package/'README_CN.md').read_text()


def test_runtime_observer_rejects_missing_binding_or_hidden_liquid(package):
    from scripts.validate_titration_linear_runtime import receiver_visual_state
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    stage.SetEditTarget(stage.GetSessionLayer())
    station = stage.GetPrimAtPath(STATION)
    assert receiver_visual_state(station)['single_material_valid']
    mesh = stage.GetPrimAtPath(LIQUID+'/Solution')
    mesh.GetAttribute('visibility').Set('invisible')
    assert not receiver_visual_state(station)['single_material_valid']
    mesh.GetAttribute('visibility').Set('inherited')
    mesh.GetRelationship('material:binding').SetTargets([])
    assert not receiver_visual_state(station)['single_material_valid']


def test_r16_finalizer_rejects_old_multi_material_evidence(tmp_path):
    from scripts.finalize_traditional_titration_vr_r16 import prepare
    path = tmp_path/'old_report.json'
    path.write_text(json.dumps({'receiver_visual_mode': 'phase_meshes', 'status': 'pass'}))
    with pytest.raises(ValueError, match='single-material'):
        prepare(tmp_path, [path]*3)

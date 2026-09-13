from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest
import yaml

from scripts.generate_fehlings_water_bath_r7 import sample_recipe, mesh_volume_ml
from scripts.generate_fehlings_water_bath_r6 import fixed_regions


def test_eight_ml_is_measured_from_the_five_meshes_and_equal_height():
    profile = [(.001, 0), (.003, .0053), (.006, .0074), (.009, .008), (.15, .008)]
    recipe = sample_recipe(profile, 8)
    assert recipe['profile_m'][0][0] > .001
    assert .04 < recipe['sample_top_m'] < .05
    shapes = fixed_regions(recipe['profile_m'], recipe['sample_top_m'])
    assert mesh_volume_ml(shapes) == pytest.approx(8, abs=.002)
    heights = [s['high']-s['low'] for s in shapes]
    assert max(heights)-min(heights) < 1e-12
    for volume in (-1, 0, float('nan'), 1000):
        with pytest.raises(ValueError):
            sample_recipe(profile, volume)


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r7 import build
    return build(output=tmp_path_factory.mktemp('bath-r7'))


@pytest.mark.local_artifacts
def test_real_glass_asset_materialization_and_local_dependency_closure(package):
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils
    from scripts.generate_fehlings_water_bath_r7 import TUBE, PRODUCER
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    source = Usd.Stage.Open(str(PRODUCER/'asset.usd'))
    body = stage.GetPrimAtPath(TUBE+'/Visual/GlassShell')
    original = source.GetPrimAtPath('/World/TestTube/Visual/GlassShell')
    for name in ('points','normals','faceVertexCounts','faceVertexIndices'):
        assert body.GetAttribute(name).Get() == original.GetAttribute(name).Get()
    assert body.GetAttribute('physics:approximation').Get() == 'sdf'
    tube = stage.GetPrimAtPath(TUBE)
    for name in ('mass','centerOfMass','diagonalInertia','principalAxes'):
        assert tube.GetAttribute('physics:'+name).Get() == source.GetPrimAtPath('/World/TestTube').GetAttribute('physics:'+name).Get()
    rigid = [p for p in Usd.PrimRange(tube) if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    assert rigid == [tube]
    assert not any(p.HasAuthoredReferences() or p.HasAuthoredPayloads() for p in Usd.PrimRange(tube))
    material,_ = UsdShade.MaterialBindingAPI(body).ComputeBoundMaterial()
    shader = stage.GetPrimAtPath(str(material.GetPath())+'/Shader')
    assert shader.GetAttribute('inputs:glass_ior').Get() == pytest.approx(1.47)
    assert shader.GetAttribute('inputs:enable_opacity').Get() is False
    assert tuple(shader.GetAttribute('inputs:glass_color').Get()) == (1,1,1)
    for p in Usd.PrimRange(tube):
        for a in p.GetAttributes():
            if a.GetTypeName() == Sdf.ValueTypeNames.Asset and a.Get():
                assert not Path(a.Get().path).is_absolute()
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    layers,assets,missing = UsdUtils.ComputeAllDependencies(str(package/'scene.usd'))
    assert not missing
    assert all(Path(p.realPath).resolve().is_relative_to(package) for p in layers)
    assert all(Path(str(p)).resolve().is_relative_to(package) for p in assets)


@pytest.mark.local_artifacts
def test_new_liquid_fits_cavity_and_preserves_r6_reaction_code(package):
    from pxr import Usd, UsdGeom
    from scripts.generate_fehlings_water_bath_r7 import SOURCE, TUBE, GRAPH
    from scripts.fehlings_r2_state import radius_at
    import math
    stage = Usd.Stage.Open(str(package/'scene.usd'))
    old = Usd.Stage.Open(str(SOURCE/'scene.usd'))
    assert stage.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get() == old.GetPrimAtPath(GRAPH+'/FlowController').GetAttribute('inputs:script').Get()
    tube = stage.GetPrimAtPath(TUBE)
    assert tube.GetAttribute('fehlings:mouth_height_m').Get() == pytest.approx(.15)
    assert tube.GetAttribute('fehlings:outer_radius_m').Get() == pytest.approx(.009)
    profile = [tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
    shapes = []
    for path in tube.GetRelationship('fehlings:layerMeshes').GetTargets():
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
        points = mesh.GetPointsAttr().Get()
        for x,y,z in points:
            assert math.hypot(x,y) <= radius_at(profile,z)+1e-7
        shapes.append(dict(points=points,counts=mesh.GetFaceVertexCountsAttr().Get(),indices=mesh.GetFaceVertexIndicesAttr().Get()))
    assert mesh_volume_ml(shapes) == pytest.approx(8,abs=.002)


@pytest.mark.local_artifacts
def test_only_tube_physics_changes_and_rack_fit_is_measured(package):
    from pxr import Usd
    from scripts.generate_fehlings_water_bath_r7 import SOURCE, TUBE
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    before = physical_state(Usd.Stage.Open(str(SOURCE/'scene.usd')))
    after = physical_state(Usd.Stage.Open(str(package/'scene.usd')))
    assert {p:v for p,v in before.items() if not p.startswith(TUBE)} == {p:v for p,v in after.items() if not p.startswith(TUBE)}
    fit = json.loads((package/'evidence/rack_fit.json').read_text())
    assert fit['rack_scale'] == [1,1,1]
    assert fit['guide_diameter_m'] == pytest.approx(.02046,abs=1e-6)
    assert fit['radial_clearance_m'] > .001
    assert fit['runtime_verified'] is False


@pytest.mark.local_artifacts
def test_r7_metadata_survives_versioned_finalization_without_promoting_pending_asset(package):
    from scripts.generate_fehlings_water_bath_r7 import TASK_ID, PRODUCER_REL
    from scripts.finalize_fehlings_water_bath import write_versioned_task_documents
    write_versioned_task_documents(package)
    task = yaml.safe_load((package/'task.yaml').read_text())
    assert task['task_id'] == TASK_ID
    assert task['container_semantics'] == 'open_round_bottom_borosilicate_test_tube_18x150mm'
    assert task['sample_volume_ml'] == 8
    assert task['color_complete_seconds'] == 30
    cfg = runpy.run_path(str(package/'task_config.py'))['TASKS'][TASK_ID]
    assert cfg['water_bath']['sample_volume_ml'] == 8
    manifest = json.loads((package/'manifest.json').read_text())
    assert manifest['status'] == 'runtime_pending' and not manifest['claims']['scene_fixture_verified']
    assert manifest['tube_producer_manifest'] == PRODUCER_REL+'/evidence/manifest.json'
    producer = json.loads((package/manifest['tube_producer_manifest']).read_text())
    assert sha256((package/PRODUCER_REL/'asset.usd').read_bytes()).hexdigest() == producer['asset_sha256']


def test_finalizer_rejects_reports_other_than_the_promoted_triplet(tmp_path):
    from scripts.finalize_fehlings_water_bath_r7 import prepare, REQUIRED_CHECKS
    scene = tmp_path/'scene.usd'
    scene.write_bytes(b'fixed scene identity')
    producer_dir = tmp_path/'deps/tube'
    (producer_dir/'evidence').mkdir(parents=True)
    (producer_dir/'asset.usd').write_bytes(b'fixed asset identity')
    scene_sha = sha256(scene.read_bytes()).hexdigest()
    asset_sha = sha256((producer_dir/'asset.usd').read_bytes()).hexdigest()
    (tmp_path/'manifest.json').write_text(json.dumps(dict(package_id='test_vr_r7',
        tube_producer_manifest='deps/tube/evidence/manifest.json',tube_asset_sha256=asset_sha)))
    (producer_dir/'evidence/manifest.json').write_text(json.dumps(dict(overall_status='pass',asset_sha256=asset_sha,
        runtime_qualification=dict(scene_sha256=scene_sha,original_report_sha256=['old1','old2','old3']))))
    reports = []
    for i in range(3):
        path = tmp_path/f'run{i}.json'
        path.write_text(json.dumps(dict(status='pass',scene_sha256=scene_sha,tube_asset_sha256=asset_sha,
            glass_tube_r7=True,policy_version='visual_five_layers_v6',runtime_version='4.5.0',
            process_id=i+1,checks={name:True for name in REQUIRED_CHECKS})))
        reports.append(path)
    with pytest.raises(ValueError,match='promoted report'):
        prepare(tmp_path,reports)

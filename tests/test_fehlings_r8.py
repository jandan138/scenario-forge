import json
from hashlib import sha256

import pytest
import yaml


def test_clear_omniglass_water_recipe_is_near_colorless_and_not_preview_alpha():
    from scripts.generate_fehlings_water_bath_r8 import WATER_RECIPE

    assert WATER_RECIPE['shader'] == 'OmniGlass'
    assert WATER_RECIPE['enable_opacity'] is False
    assert WATER_RECIPE['thin_walled'] is True
    assert WATER_RECIPE['double_sided'] is False
    assert WATER_RECIPE['glass_ior'] == pytest.approx(1.333)
    assert max(abs(a - b) for a, b in zip(WATER_RECIPE['glass_color'], (1, 1, 1))) < 0.05
    assert WATER_RECIPE['glass_color'] != pytest.approx((0.32, 0.72, 0.95))


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r8 import build

    return build(output=tmp_path_factory.mktemp('bath-r8'))


@pytest.mark.local_artifacts
def test_r8_keeps_r7_water_volume_and_has_no_water_collision(package):
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade
    from scripts.generate_fehlings_water_bath_r3 import WATER
    from scripts.generate_fehlings_water_bath_r8 import SOURCE, WATER_RECIPE

    old = Usd.Stage.Open(str(SOURCE / 'scene.usd'))
    stage = Usd.Stage.Open(str(package / 'scene.usd'))
    water = stage.GetPrimAtPath(WATER)
    source_water = old.GetPrimAtPath(WATER)
    assert [tuple(v) for v in water.GetAttribute('water:profile_m').Get()] == [
        tuple(v) for v in source_water.GetAttribute('water:profile_m').Get()
    ]
    assert water.GetAttribute('water:fill_height_ratio').Get() == pytest.approx(0.8)
    for name in ('body', 'surface'):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/' + name))
        source = UsdGeom.Mesh(old.GetPrimAtPath(WATER + '/' + name))
        assert mesh.GetPointsAttr().Get() == source.GetPointsAttr().Get()
        assert mesh.GetFaceVertexCountsAttr().Get() == source.GetFaceVertexCountsAttr().Get()
        assert mesh.GetFaceVertexIndicesAttr().Get() == source.GetFaceVertexIndicesAttr().Get()
        assert mesh.GetDoubleSidedAttr().Get() is WATER_RECIPE['double_sided']
    for prim in Usd.PrimRange(water):
        assert not any('Physics' in schema or 'Physx' in schema for schema in prim.GetAppliedSchemas())
        assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    material, _ = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(WATER + '/body')).ComputeBoundMaterial()
    shader = stage.GetPrimAtPath(str(material.GetPath()) + '/Shader')
    assert shader.GetAttribute('info:mdl:sourceAsset:subIdentifier').Get() == 'OmniGlass'
    assert shader.GetAttribute('inputs:thin_walled').Get() is True
    assert shader.GetAttribute('inputs:enable_opacity').Get() is False
    assert shader.GetAttribute('inputs:glass_ior').Get() == pytest.approx(WATER_RECIPE['glass_ior'])
    assert tuple(shader.GetAttribute('inputs:glass_color').Get()) == pytest.approx(WATER_RECIPE['glass_color'])
    recipe = json.loads((package / 'evidence/water_recipe.json').read_text())
    assert recipe['profile_m'] == json.loads((SOURCE / 'evidence/water_recipe.json').read_text())['profile_m']
    assert recipe['fill_height_ratio'] == pytest.approx(0.8)
    assert recipe['material']['shader'] == 'OmniGlass'


@pytest.mark.local_artifacts
def test_r8_preserves_r7_physics_tube_reaction_and_controller(package):
    from pxr import Usd
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    from scripts.generate_fehlings_water_bath_r7 import GRAPH, TUBE
    from scripts.generate_fehlings_water_bath_r8 import SOURCE, TASK_ID

    old = Usd.Stage.Open(str(SOURCE / 'scene.usd'))
    new = Usd.Stage.Open(str(package / 'scene.usd'))
    assert physical_state(old) == physical_state(new)
    assert (
        old.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
        == new.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
    )
    tube = new.GetPrimAtPath(TUBE)
    assert tube.GetAttribute('fehlings:sample_volume_ml').Get() == pytest.approx(8)
    assert tube.GetAttribute('fehlings:policy_version').Get() == 'visual_five_layers_v6'
    assert json.loads((package / 'manifest.json').read_text())['package_id'] == TASK_ID
    assert json.loads((package / 'manifest.json').read_text())['status'] == 'runtime_pending'


@pytest.mark.local_artifacts
def test_r8_documents_dispatch_without_rewriting_r7(package):
    from scripts.finalize_fehlings_water_bath import write_versioned_task_documents
    from scripts.generate_fehlings_water_bath_r8 import TASK_ID

    write_versioned_task_documents(package)
    task = yaml.safe_load((package / 'task.yaml').read_text())
    assert task['task_id'] == TASK_ID
    assert task['sample_volume_ml'] == 8
    assert task['color_complete_seconds'] == 30
    assert task['reaction_policy']['visual_water_collision'] is False
    assert task['reaction_policy']['water_fill_height_ratio'] == pytest.approx(0.8)


def test_finalizer_requires_in_bath_views_and_rejects_r7_scene(tmp_path):
    from scripts.finalize_fehlings_water_bath_r8 import prepare

    scene = tmp_path / 'scene.usd'
    scene.write_bytes(b'r8 scene identity')
    (tmp_path / 'manifest.json').write_text(
        json.dumps(
            dict(
                package_id='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8',
                tube_producer_manifest='deps/tube/evidence/manifest.json',
                tube_asset_sha256=sha256(b'tube').hexdigest(),
            )
        )
    )
    (tmp_path / 'deps/tube/evidence').mkdir(parents=True)
    (tmp_path / 'deps/tube/asset.usd').write_bytes(b'tube')
    (tmp_path / 'deps/tube/evidence/manifest.json').write_text(
        json.dumps(dict(overall_status='pass', asset_sha256=sha256(b'tube').hexdigest()))
    )
    reports = []
    for i in range(3):
        path = tmp_path / f'run{i}.json'
        path.write_text(
            json.dumps(
                dict(
                    status='pass',
                    scene_sha256=sha256(scene.read_bytes()).hexdigest(),
                    process_id=i + 1,
                    policy_version='visual_five_layers_v6',
                    runtime_version='4.5.0',
                    glass_tube_r7=True,
                    checks={},
                )
            )
        )
        reports.append(path)
    with pytest.raises(ValueError, match='in-bath'):
        prepare(tmp_path, reports)

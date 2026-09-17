import json
from hashlib import sha256

import pytest


def test_water_lining_has_open_core_and_keeps_fill_profile():
    from scripts.generate_fehlings_water_bath_r9 import LINING_THICKNESS, water_lining_mesh, water_surface_ring

    profile = ((0.0031, 0.03517), (0.09013, 0.03629))
    points, counts, indices = water_lining_mesh(profile)
    radii = [((x * x + y * y) ** 0.5) for x, y, _z in points]
    assert min(radii) >= profile[0][1] - LINING_THICKNESS - 1e-6
    assert min(radii) > 0.02
    assert max(radii) == pytest.approx(max(r for _z, r in profile), abs=1e-6)
    assert min(counts) >= 3
    assert len(indices) == sum(counts)
    ring_points, ring_counts, ring_indices = water_surface_ring(profile)
    ring_radii = [((x * x + y * y) ** 0.5) for x, y, _z in ring_points]
    assert min(ring_radii) > 0.02
    assert len(ring_indices) == sum(ring_counts)


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r9 import build

    return build(output=tmp_path_factory.mktemp('bath-r9'))


@pytest.mark.local_artifacts
def test_r9_keeps_r8_fill_and_opens_water_core(package):
    from pxr import Usd, UsdGeom, UsdPhysics
    from scripts.generate_fehlings_water_bath_r3 import WATER
    from scripts.generate_fehlings_water_bath_r9 import SOURCE, LINING_THICKNESS

    old = Usd.Stage.Open(str(SOURCE / 'scene.usd'))
    stage = Usd.Stage.Open(str(package / 'scene.usd'))
    water = stage.GetPrimAtPath(WATER)
    source_water = old.GetPrimAtPath(WATER)
    assert [tuple(v) for v in water.GetAttribute('water:profile_m').Get()] == [
        tuple(v) for v in source_water.GetAttribute('water:profile_m').Get()
    ]
    assert water.GetAttribute('water:fill_height_ratio').Get() == pytest.approx(0.8)
    surface = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/surface'))
    source_surface = UsdGeom.Mesh(old.GetPrimAtPath(WATER + '/surface'))
    assert surface.GetPointsAttr().Get() != source_surface.GetPointsAttr().Get()
    surface_radii = [((p[0] * p[0] + p[1] * p[1]) ** 0.5) for p in surface.GetPointsAttr().Get()]
    assert min(surface_radii) > 0.02
    body = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/body'))
    source_body = UsdGeom.Mesh(old.GetPrimAtPath(WATER + '/body'))
    assert body.GetPointsAttr().Get() != source_body.GetPointsAttr().Get()
    radii = [((p[0] * p[0] + p[1] * p[1]) ** 0.5) for p in body.GetPointsAttr().Get()]
    assert min(radii) > 0.02
    assert min(radii) <= max(radii) - LINING_THICKNESS + 1e-4
    for prim in Usd.PrimRange(water):
        assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    recipe = json.loads((package / 'evidence/water_recipe.json').read_text())
    assert recipe['fill_height_ratio'] == pytest.approx(0.8)
    assert recipe['material']['representation'] == 'lining_and_surface'


@pytest.mark.local_artifacts
def test_r9_preserves_r8_physics_tube_and_controller(package):
    from pxr import Usd
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    from scripts.generate_fehlings_water_bath_r7 import GRAPH, TUBE
    from scripts.generate_fehlings_water_bath_r9 import SOURCE, TASK_ID

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


def test_finalizer_requires_front_bath_views(tmp_path):
    from scripts.finalize_fehlings_water_bath_r9 import prepare

    scene = tmp_path / 'scene.usd'
    scene.write_bytes(b'r9 scene identity')
    (tmp_path / 'manifest.json').write_text(
        json.dumps(dict(package_id='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9'))
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
    with pytest.raises(ValueError, match='front_bath'):
        prepare(tmp_path, reports)

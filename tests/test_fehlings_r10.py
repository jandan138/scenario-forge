import json
from hashlib import sha256

import numpy as np
import pytest


PROFILE = ((0.0031, 0.03517), (0.09013, 0.03629))
SAMPLE_TOP_M = 0.04378056203043218


def test_default_heating_pose_stays_shallow_six_mm_tilt():
    from scripts.validate_fehlings_water_bath_r3 import color_heating_pose, heating_local

    local, tilt = heating_local(PROFILE, 'shallow')
    assert local[2] == pytest.approx(PROFILE[-1][0] - 0.006)
    assert tilt == 55
    first, first_tilt = color_heating_pose(PROFILE, 'shallow', 'first')
    last, last_tilt = color_heating_pose(PROFILE, 'shallow', 'last')
    assert first == local and first_tilt == 55
    assert last == (0.0, 0.0, PROFILE[-1][0] - 0.006) and last_tilt == 0
    assert first[2] + SAMPLE_TOP_M > PROFILE[-1][0]


def test_r10_heating_pose_puts_eight_ml_below_waterline():
    from scripts.validate_fehlings_water_bath_r3 import color_heating_pose, heating_local

    local, tilt = heating_local(PROFILE, 'deep')
    assert tilt == 0
    assert local[0] == 0 and local[1] == 0
    assert PROFILE[0][0] < local[2] < PROFILE[0][0] + 0.004
    assert local[2] + SAMPLE_TOP_M < PROFILE[-1][0]
    assert color_heating_pose(PROFILE, 'deep', 'first') == (local, 0)
    assert color_heating_pose(PROFILE, 'deep', 'last') == (local, 0)


def test_front_bath_with_waterline_looks_at_submerged_midpoint():
    from scripts.render_fehlings_water_bath import front_bath_view

    tube = (0.3701, -0.0281, 0.8313)
    water_z = 0.91609
    name, position, target, focal = front_bath_view(tube, water_surface_z=water_z)
    assert name == 'front_bath'
    assert target[0] == pytest.approx(tube[0])
    assert target[1] == pytest.approx(tube[1])
    assert target[2] == pytest.approx(0.5 * (tube[2] + water_z))
    assert position[1] < target[1]
    offset = np.asarray(position) - np.asarray(target)
    assert 0.25 <= float(np.linalg.norm(offset)) <= 0.35
    assert focal >= 50


def test_r10_finalizer_rejects_shallow_color_snapshots(tmp_path):
    from scripts.finalize_fehlings_water_bath_r10 import prepare

    scene = tmp_path / 'scene.usd'
    scene.write_bytes(b'r10 scene identity')
    digest = sha256(scene.read_bytes()).hexdigest()
    (tmp_path / 'manifest.json').write_text(
        json.dumps(dict(package_id='scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10'))
    )
    (tmp_path / 'evidence/water_recipe.json').parent.mkdir(parents=True)
    (tmp_path / 'evidence/water_recipe.json').write_text(
        json.dumps(dict(scene_sha256=digest, fill_height_ratio=0.8, material=dict(representation='lining_and_surface')))
    )
    (tmp_path / 'evidence/sample_recipe.json').write_text(json.dumps(dict(sample_top_m=SAMPLE_TOP_M)))
    (tmp_path / 'evidence/physical_revision_audit.json').write_text(
        json.dumps(
            dict(
                status='pass',
                scene_sha256=digest,
                all_r9_physics_identical=True,
                water_volume_unchanged=True,
            )
        )
    )
    folder = tmp_path / 'evidence/initial_scene'
    folder.mkdir()
    (folder / 't3_front_bath.png').write_bytes(b'img')
    for name in ('t15_front_bath.png', 't21_front_bath.png', 't30_front_bath.png'):
        (folder / name).write_bytes(b'img')
    (folder / 'render_manifest.json').write_text(
        json.dumps(
            dict(
                status='pass',
                scene_sha256=digest,
                images=[
                    dict(path='evidence/initial_scene/' + name, sha256=sha256(b'img').hexdigest())
                    for name in ('t3_front_bath.png', 't15_front_bath.png', 't21_front_bath.png', 't30_front_bath.png')
                ],
            )
        )
    )
    (folder / 'visual_review.json').write_text(
        json.dumps(
            dict(
                status='pass',
                scene_sha256=digest,
                verdict='WARN',
                blocking_failures=[],
                render_manifest_sha256=sha256((folder / 'render_manifest.json').read_bytes()).hexdigest(),
            )
        )
    )
    from scripts.finalize_fehlings_water_bath_r10 import REQUIRED_CHECKS

    reports = []
    for i in range(3):
        path = tmp_path / f'run{i}.json'
        path.write_text(
            json.dumps(
                dict(
                    status='pass',
                    scene_sha256=digest,
                    process_id=i + 1,
                    policy_version='visual_five_layers_v6',
                    runtime_version='4.5.0',
                    glass_tube_r7=True,
                    heating_style='deep',
                    water_world_surface_z=0.916,
                    checks={name: True for name in REQUIRED_CHECKS},
                    snapshots=[
                        dict(
                            name='t3',
                            immersed=True,
                            tube_xyz=[0.35, -0.028, 0.910],
                        )
                    ],
                )
            )
        )
        reports.append(path)
    with pytest.raises(ValueError, match='deep'):
        prepare(tmp_path, reports)


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    from scripts.generate_fehlings_water_bath_r10 import build

    return build(output=tmp_path_factory.mktemp('bath-r10'))


@pytest.mark.local_artifacts
def test_r10_keeps_r9_fill_lining_and_physics(package):
    from pxr import Usd, UsdGeom, UsdPhysics
    from scripts.finalize_traditional_titration_vr_r14 import physical_state
    from scripts.generate_fehlings_water_bath_r3 import WATER
    from scripts.generate_fehlings_water_bath_r7 import GRAPH, TUBE
    from scripts.generate_fehlings_water_bath_r10 import SOURCE, TASK_ID

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
    for prim in Usd.PrimRange(water):
        assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    assert physical_state(old) == physical_state(stage)
    assert (
        old.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
        == stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
    )
    tube = stage.GetPrimAtPath(TUBE)
    assert tube.GetAttribute('fehlings:sample_volume_ml').Get() == pytest.approx(8)
    recipe = json.loads((package / 'evidence/water_recipe.json').read_text())
    assert recipe['fill_height_ratio'] == pytest.approx(0.8)
    assert recipe['material']['representation'] == 'lining_and_surface'
    assert json.loads((package / 'manifest.json').read_text())['package_id'] == TASK_ID
    assert json.loads((package / 'manifest.json').read_text())['heating_style'] == 'deep'

import pytest

from scripts.clone_task09_powder_r5_10 import (
    DEFAULT_KINEMATIC_FROM_S,
    DEFAULT_KINEMATIC_UNTIL_S,
    hold_grains_kinematic,
    patch_scene_config,
)


def test_r5_10_config_keeps_120hz_and_sets_only_rest_kinematic_hold():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.9',
        'status': 'candidate',
        'grain_linear_damping': 1.0,
        'grain_sleep_threshold': 5e-5,
        'lift_early_hold_m': 0.006,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.10'
    assert cfg['grain_linear_damping'] == 1.0
    assert cfg['lift_early_hold_m'] == 0.006
    assert cfg['grain_rest_kinematic_from_s'] == DEFAULT_KINEMATIC_FROM_S
    assert cfg['grain_rest_kinematic_until_s'] == DEFAULT_KINEMATIC_UNTIL_S
    assert DEFAULT_KINEMATIC_FROM_S == 0.5
    assert DEFAULT_KINEMATIC_UNTIL_S == 18.0
    assert 'qualified_runtime' not in cfg


def test_r5_10_rejects_hold_that_covers_the_scoop():
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.9'}, kinematic_until_s=0)
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.9'}, kinematic_until_s=28)


def test_hold_grains_kinematic_covers_rest_only():
    assert hold_grains_kinematic(0.0, 18.0) is False
    assert hold_grains_kinematic(0.5, 18.0) is True
    assert hold_grains_kinematic(1.0, 18.0) is True
    assert hold_grains_kinematic(17.999, 18.0) is True
    assert hold_grains_kinematic(18.0, 18.0) is False
    assert hold_grains_kinematic(20.0, 18.0) is False


def test_apply_grain_kinematic_disables_ccd_while_held(tmp_path):
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics
    from scripts.clone_task09_powder_r5_10 import apply_grain_kinematic

    path = tmp_path / 'grain.usda'
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, '/World')
    grain = UsdGeom.Xform.Define(stage, '/World/g0')
    UsdPhysics.RigidBodyAPI.Apply(grain.GetPrim())
    grain.GetPrim().CreateAttribute('physxRigidBody:enableCCD', Sdf.ValueTypeNames.Bool).Set(True)
    stage.GetRootLayer().Save()
    apply_grain_kinematic(stage, ['/World/g0'], True)
    assert grain.GetPrim().GetAttribute('physics:kinematicEnabled').Get() is True
    assert grain.GetPrim().GetAttribute('physxRigidBody:enableCCD').Get() is False
    apply_grain_kinematic(stage, ['/World/g0'], False)
    assert grain.GetPrim().GetAttribute('physics:kinematicEnabled').Get() is False
    assert grain.GetPrim().GetAttribute('physxRigidBody:enableCCD').Get() is True

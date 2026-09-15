import pytest

from scripts.clone_task09_powder_r5_7 import (
    DEFAULT_LIFT_EARLY_HOLD_M,
    patch_scene_config,
)


def test_r5_7_config_keeps_120hz_and_sets_only_early_lift_hold():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.6',
        'status': 'candidate',
        'powder_surface_target_m': 0.091,
        'spoon_static_friction': 0.9,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.7'
    assert cfg['powder_surface_target_m'] == 0.091
    assert cfg['spoon_static_friction'] == 0.9
    assert cfg['lift_early_hold_m'] == DEFAULT_LIFT_EARLY_HOLD_M
    assert DEFAULT_LIFT_EARLY_HOLD_M > 0
    assert 'qualified_runtime' not in cfg


def test_r5_7_rejects_zero_or_negative_hold():
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.6'}, lift_early_hold_m=0)

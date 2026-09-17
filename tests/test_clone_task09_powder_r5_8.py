import pytest

from scripts.clone_task09_powder_r5_8 import (
    DAMPED_BLOCK,
    DEFAULT_LINEAR_DAMPING,
    GRAIN_COUNT,
    UNDAMPED_BLOCK,
    patch_grain_linear_damping,
    patch_scene_config,
)
from scripts.task09_powder_evidence import authored_linear_damping_matches


OTHER_BODY_BLOCK = (
    '        float physxRigidBody:linearDamping = 0.04\n'
    '        float physxRigidBody:maxLinearVelocity = 1\n'
)
OTHER_ZERO_DAMPING = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxAngularVelocity = 25\n'
)


def test_r5_8_config_keeps_120hz_and_sets_only_grain_damping():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.7',
        'status': 'candidate',
        'powder_surface_target_m': 0.091,
        'lift_early_hold_m': 0.006,
        'spoon_static_friction': 0.9,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.8'
    assert cfg['powder_surface_target_m'] == 0.091
    assert cfg['lift_early_hold_m'] == 0.006
    assert cfg['spoon_static_friction'] == 0.9
    assert cfg['grain_linear_damping'] == DEFAULT_LINEAR_DAMPING
    assert DEFAULT_LINEAR_DAMPING == 1.0
    assert 'qualified_runtime' not in cfg


def test_r5_8_rejects_zero_or_negative_damping():
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.7'}, linear_damping=0)


def test_grain_damping_replaces_only_powder_grains():
    text = UNDAMPED_BLOCK * GRAIN_COUNT + OTHER_BODY_BLOCK + OTHER_ZERO_DAMPING
    patched = patch_grain_linear_damping(text)
    assert patched.count(DAMPED_BLOCK) == GRAIN_COUNT
    assert patched.count(UNDAMPED_BLOCK) == 0
    assert OTHER_BODY_BLOCK in patched
    assert OTHER_ZERO_DAMPING in patched
    assert patched.count('linearDamping = 1') == GRAIN_COUNT


def test_grain_damping_reject_wrong_replacement_count():
    with pytest.raises(ValueError):
        patch_grain_linear_damping(UNDAMPED_BLOCK * 3)


def test_r5_8_damping_accepts_usda_float32_rounding():
    assert authored_linear_damping_matches(1.0)
    assert authored_linear_damping_matches(1.0000001192092896)
    assert not authored_linear_damping_matches(0)
    assert not authored_linear_damping_matches(None)

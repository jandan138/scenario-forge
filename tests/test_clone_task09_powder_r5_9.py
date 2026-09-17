import pytest

from scripts.clone_task09_powder_r5_9 import (
    AWAKE_BLOCK,
    DEFAULT_SLEEP_THRESHOLD,
    DEFAULT_STABILIZATION_THRESHOLD,
    GRAIN_COUNT,
    SLEEPING_BLOCK,
    patch_grain_sleep,
    patch_scene_config,
)
from scripts.task09_powder_evidence import authored_sleep_matches


OTHER_SLEEP = (
    '        float physxRigidBody:sleepThreshold = 0\n'
    '        float physxRigidBody:maxAngularVelocity = 25\n'
)


def test_r5_9_config_keeps_120hz_and_sets_only_grain_sleep():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.8',
        'status': 'candidate',
        'grain_linear_damping': 1.0,
        'lift_early_hold_m': 0.006,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.9'
    assert cfg['grain_linear_damping'] == 1.0
    assert cfg['lift_early_hold_m'] == 0.006
    assert cfg['grain_sleep_threshold'] == DEFAULT_SLEEP_THRESHOLD
    assert cfg['grain_stabilization_threshold'] == DEFAULT_STABILIZATION_THRESHOLD
    assert DEFAULT_SLEEP_THRESHOLD == 5e-5
    assert DEFAULT_STABILIZATION_THRESHOLD == 1e-5
    assert 'qualified_runtime' not in cfg


def test_r5_9_rejects_zero_sleep():
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.8'}, sleep_threshold=0)


def test_grain_sleep_replaces_only_powder_grains():
    text = AWAKE_BLOCK * GRAIN_COUNT + OTHER_SLEEP
    patched = patch_grain_sleep(text)
    assert patched.count(SLEEPING_BLOCK) == GRAIN_COUNT
    assert patched.count(AWAKE_BLOCK) == 0
    assert OTHER_SLEEP in patched


def test_grain_sleep_reject_wrong_replacement_count():
    with pytest.raises(ValueError):
        patch_grain_sleep(AWAKE_BLOCK * 3)


def test_r5_9_sleep_accepts_usda_float32_rounding():
    assert authored_sleep_matches(5e-5, 1e-5)
    assert authored_sleep_matches(4.999999873689376e-5, 9.999999747378752e-6)
    assert not authored_sleep_matches(0, 1e-5)
    assert not authored_sleep_matches(None, 1e-5)

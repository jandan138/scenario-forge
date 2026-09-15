import pytest

from scripts.clone_task09_powder_r5_1 import (
    GRAIN_COUNT,
    patch_grain_velocity_caps,
    patch_physics_hz,
    patch_scene_config,
)
from scripts.task09_powder_evidence import authored_velocity_cap_matches


GRAIN_BLOCK = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)
CAPPED_BLOCK = (
    '        float physxRigidBody:linearDamping = 0\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.2\n'
    '        float physxRigidBody:maxLinearVelocity = 0.15\n'
    '        float physxRigidBody:sleepThreshold = 0\n'
)
LARGE_SAMPLE_BLOCK = (
    '        float physxRigidBody:linearDamping = 0.04\n'
    '        float physxRigidBody:maxAngularVelocity = 25\n'
    '        float physxRigidBody:maxDepenetrationVelocity = 0.15\n'
    '        float physxRigidBody:maxLinearVelocity = 1\n'
)


def test_r5_1_clone_locks_120hz_velocity_caps_and_candidate_status():
    cfg = patch_scene_config({'physics_hz':240,'revision':'r4','status':'scene_fixture_verified',
                              'qualified_runtime':'Isaac Sim 4.5.0'})
    assert cfg['physics_hz']==120
    assert cfg['revision']=='r5.1'
    assert cfg['status']=='candidate'
    assert cfg['grain_max_linear_velocity_m_s']==0.15
    assert cfg['grain_max_depenetration_velocity_m_s']==0.2
    assert 'qualified_runtime' not in cfg


def test_usda_physics_scene_timestep_is_rewritten_once():
    text = 'uniform token physxScene:solverType = "PGS"\n        uint physxScene:timeStepsPerSecond = 240\n'
    patched = patch_physics_hz(text, 240, 120)
    assert 'timeStepsPerSecond = 120' in patched
    assert 'timeStepsPerSecond = 240' not in patched


def test_grain_velocity_caps_insert_max_linear_velocity_without_lowering_depen():
    text = GRAIN_BLOCK*GRAIN_COUNT + LARGE_SAMPLE_BLOCK
    patched = patch_grain_velocity_caps(text)
    assert patched.count(CAPPED_BLOCK)==GRAIN_COUNT
    assert patched.count(GRAIN_BLOCK)==0
    assert LARGE_SAMPLE_BLOCK in patched
    assert patched.count('maxLinearVelocity = 0.15')==GRAIN_COUNT
    assert patched.count('maxDepenetrationVelocity = 0.2')==GRAIN_COUNT


def test_grain_velocity_caps_reject_wrong_replacement_count():
    with pytest.raises(ValueError):
        patch_grain_velocity_caps(GRAIN_BLOCK*3 + LARGE_SAMPLE_BLOCK)


def test_r5_1_velocity_caps_accept_usda_float32_rounding():
    assert authored_velocity_cap_matches(0.15000000596046448, 0.20000000298023224)
    assert not authored_velocity_cap_matches(1.0, 0.2)
    assert not authored_velocity_cap_matches(0.15, 0.05)
    assert not authored_velocity_cap_matches(None, 0.2)

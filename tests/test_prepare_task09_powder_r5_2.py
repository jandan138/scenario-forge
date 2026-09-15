import pytest

from scripts.prepare_task09_powder_r5_2 import (
    GRAIN_COLLISION_SOURCE,
    patch_grain_collision_offsets,
    patch_physics_hz,
    patch_preparation_config,
    collision_block,
)


def test_r5_2_preparation_config_locks_120hz_and_offsets():
    cfg = patch_preparation_config({'physics_hz':240,'revision':'r4','status':'scene_fixture_verified',
                                    'qualified_runtime':'Isaac Sim 4.5.0','count':10240})
    assert cfg['physics_hz']==120
    assert cfg['revision']=='r5.2'
    assert cfg['preparation_only'] is True
    assert cfg['initial_state']=='preparation_gravity_column'
    assert cfg['grain_contact_offset_m']==0.00015
    assert cfg['grain_rest_offset_m']==0.00005
    assert cfg['count']==10240
    assert 'qualified_runtime' not in cfg


def test_r5_2_preparation_config_keeps_requested_count_and_offsets():
    cfg = patch_preparation_config({'physics_hz':240,'revision':'r4','count':14336},
                                   contact_offset_m=0.0002, rest_offset_m=0.0001)
    assert cfg['count']==14336
    assert cfg['grain_contact_offset_m']==0.0002
    assert cfg['grain_rest_offset_m']==0.0001


def test_usda_physics_scene_timestep_is_rewritten_once():
    text = 'uniform token physxScene:solverType = "PGS"\n        uint physxScene:timeStepsPerSecond = 240\n'
    patched = patch_physics_hz(text, 240, 120)
    assert 'timeStepsPerSecond = 120' in patched
    assert 'timeStepsPerSecond = 240' not in patched


def test_grain_collision_offsets_replace_exactly_count_grains():
    bottle = '            float physxCollision:contactOffset = 0.00005\n            float physxCollision:restOffset = 0\n'
    text = GRAIN_COLLISION_SOURCE*10240 + bottle
    patched = patch_grain_collision_offsets(text, 10240, 0.00015, 0.00005)
    assert patched.count(collision_block(0.00015, 0.00005))==10240
    assert patched.count(GRAIN_COLLISION_SOURCE)==0
    assert bottle in patched


def test_grain_collision_offsets_reject_wrong_replacement_count():
    with pytest.raises(ValueError):
        patch_grain_collision_offsets(GRAIN_COLLISION_SOURCE*3, 10240, 0.00015, 0.00005)

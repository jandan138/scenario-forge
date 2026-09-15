import pytest

from scripts.clone_task09_powder_r5_5 import (
    DEFAULT_SURFACE_TARGET_M,
    patch_scene_config,
)


def test_r5_5_config_keeps_120hz_and_lowers_scoop_surface_target():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.4',
        'status': 'candidate',
        'powder_surface_target_m': 0.095,
        'insert_contact_offset_m': 0.003,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.5'
    assert cfg['powder_surface_target_m'] == DEFAULT_SURFACE_TARGET_M
    assert DEFAULT_SURFACE_TARGET_M < 0.095
    assert cfg['insert_contact_offset_m'] == 0.003
    assert 'qualified_runtime' not in cfg


def test_r5_5_rejects_raising_surface_target_back_to_r4_height():
    with pytest.raises(ValueError):
        patch_scene_config({'physics_hz': 120, 'revision': 'r5.4', 'powder_surface_target_m': 0.095},
                           surface_target_m=0.095)

from scripts.clone_task09_powder_r5_0 import patch_scene_config, patch_physics_hz


def test_r5_0_clone_locks_120hz_and_candidate_status():
    cfg = patch_scene_config({'physics_hz':240,'revision':'r4','status':'scene_fixture_verified',
                              'qualified_runtime':'Isaac Sim 4.5.0'})
    assert cfg['physics_hz']==120
    assert cfg['revision']=='r5.0'
    assert cfg['status']=='candidate'
    assert 'qualified_runtime' not in cfg


def test_usda_physics_scene_timestep_is_rewritten_once():
    text = 'uniform token physxScene:solverType = "PGS"\n        uint physxScene:timeStepsPerSecond = 240\n'
    patched = patch_physics_hz(text, 240, 120)
    assert 'timeStepsPerSecond = 120' in patched
    assert 'timeStepsPerSecond = 240' not in patched

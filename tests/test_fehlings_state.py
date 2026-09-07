from scripts.fehlings_state import initial_state, advance, appearance, geometry_flags


def test_color_is_not_permission_to_withdraw():
    state = initial_state()
    for _ in range(30):
        state = advance(state, 1, True, False, (0,0,0))
    assert appearance(state['heated_s'])['progress'] == 1
    assert state['stage'] == 'heating'
    for _ in range(5):
        state = advance(state, 1, False, True, (0,0,0))
    assert not state['success']
    assert state['heated_s'] == 30
    for _ in range(90):
        state = advance(state, 1, True, False, (0,0,0))
    for _ in range(3):
        state = advance(state, 1, False, True, (0,0,0))
    assert state['success']


def test_invalid_immersion_and_pause_do_not_heat():
    state = initial_state()
    assert advance(state, 120, False, False, (0,0,0))['heated_s'] == 0
    assert advance(state, 0, True, False, (0,0,0))['heated_s'] == 0


def test_observation_motion_restarts_dwell():
    state = initial_state()
    state['heated_s'] = 120
    state = advance(state, 2, False, True, (0,0,0))
    state = advance(state, 1, False, True, (0.03,0,0))
    assert state['observe_s'] == 0
    assert initial_state()['heated_s'] == 0


def test_tilt_alone_and_shallow_sample_are_rejected():
    import math
    spec = {'water_surface_z':0.05,'bath_center_xyz':(0,0,0),'bath_inner_radius':1.0,
            'outer_radius_m':0.008,'sample_height_m':0.03,'mouth_height_m':0.10,'bath_inner_floor_z':-0.01}
    assert geometry_flags((0,0,0),(0,0,1),spec)[0]
    assert not geometry_flags((0,0,0),(math.sin(math.radians(35)),0,math.cos(math.radians(35))),spec)[0]
    assert not geometry_flags((0,0,0.025),(0,0,1),spec)[0]


def test_vr_config_depth_hint_matches_sample_and_floor(tmp_path):
    import json
    import runpy
    from scripts.generate_fehlings_water_bath import write_task_documents, TASK_ID
    (tmp_path/'task_config.py').write_text("TASKS={'old':{'water_bath':{},'scene_usd_file_path':{}}}")
    (tmp_path/'manifest.json').write_text(json.dumps({'sample_height_m':0.032}))
    write_task_documents(tmp_path)
    task=runpy.run_path(str(tmp_path/'task_config.py'))['TASKS'][TASK_ID]
    low,high=task['water_bath']['immersion_depth_range_m']
    assert abs(low-0.035)<1e-10
    assert abs(high-0.0413)<1e-10
    assert task['scene_usd_file_path']['scene1']==str(tmp_path/'scene.usd')

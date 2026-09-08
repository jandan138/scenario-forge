import math

import pytest

from scripts.titration_linear_policy import (
    MAX_RATE, PINK_END, TRANSITION_START, advance, color, flow_rate, initial_state,
)


def run_for(state, angle, seconds, dt=1/60):
    for _ in range(round(seconds/dt)):
        state = advance(state, angle, dt)
    return state


def test_linear_deadzone_and_saturation():
    assert all(flow_rate(a) == 0 for a in (0, 4.99, 5))
    assert flow_rate(5.01) > 0
    assert flow_rate(45) == pytest.approx(MAX_RATE*40/85)
    assert flow_rate(90) == flow_rate(120) == MAX_RATE
    assert flow_rate(-45) == flow_rate(45)
    values = [flow_rate(a/10) for a in range(50, 901)]
    assert all(a < b for a, b in zip(values, values[1:]))
    with pytest.raises(ValueError):
        flow_rate(math.nan)


def test_timing_and_color_boundaries():
    assert TRANSITION_START/MAX_RATE == pytest.approx(5)
    assert (15-TRANSITION_START)/MAX_RATE == pytest.approx(.5)
    assert (PINK_END-15)/flow_rate(45) == pytest.approx(1.5)
    assert (PINK_END-15)/flow_rate(10) == pytest.approx(12)
    assert color(TRANSITION_START-1e-6)[0] == 'colorless'
    assert color(TRANSITION_START)[0] == 'transition'
    assert color(15)[0] == color(PINK_END)[0] == 'endpoint_pale_pink'
    assert color(PINK_END+1e-6)[0] == 'overshoot'
    assert color((TRANSITION_START+15)/2)[1] == pytest.approx((.985, .895, .94))


def test_angle_change_preserves_volume_and_pause_freezes_color():
    state = run_for(initial_state(), 90, 5.25)
    assert TRANSITION_START < state['dispensed_volume_ml'] < 15
    paused = run_for(state, 4.9, 10)
    assert paused['dispensed_volume_ml'] == state['dispensed_volume_ml']
    assert not paused['task_success']
    changed = run_for(paused, 45, .5)
    assert changed['dispensed_volume_ml'] == pytest.approx(state['dispensed_volume_ml']+flow_rate(45)*.5)


def test_free_angle_success_interrupt_and_latch():
    state = advance(initial_state(), 25, 15.5/flow_rate(25))
    assert not state['visited_open']
    state = advance(state, 0, 2.9)
    assert not state['task_success']
    state = advance(state, 10, .1)
    assert state['endpoint_hold_seconds'] == 0
    state = advance(state, 5, 3)
    assert state['task_success']
    completed_volume = state['completion_volume_ml']
    state = advance(state, 90, 10)
    assert state['overshoot'] and state['task_success']
    assert state['completion_volume_ml'] == completed_volume
    assert state['completion_hold_seconds'] == 3
    assert state['burette_liquid_volume_ml'] == 0
    assert initial_state()['task_success'] is False
    assert initial_state()['completion_volume_ml'] == -1


def test_overshoot_before_success_is_irrecoverable_until_reset():
    state = advance(initial_state(), 90, (PINK_END+.01)/MAX_RATE)
    assert state['overshoot']
    assert not advance(state, 0, 100)['task_success']


def test_time_integration_and_receiver_accounting():
    large = advance(initial_state(), 90, .5)
    small = run_for(initial_state(), 90, .5)
    assert large['dispensed_volume_ml'] == pytest.approx(small['dispensed_volume_ml'])
    assert advance(large, 90, 0)['dispensed_volume_ml'] == large['dispensed_volume_ml']
    spilled = advance(initial_state(), 90, 20, target=False)
    assert spilled['dispensed_volume_ml'] == 0
    assert spilled['spilled_volume_ml'] == 25
    assert spilled['burette_liquid_volume_ml'] == 0


def test_r15_package_embeds_policy_and_preserves_physics(tmp_path):
    import json
    import yaml
    from pxr import Usd
    from scripts.generate_traditional_titration_vr_r15 import build, SOURCE, STATION
    from scripts.finalize_traditional_titration_vr_r14 import physical_state

    root = build(output=tmp_path)
    assert (root/'COLOR_GUIDE_CN.md').is_file()
    assert '(COLOR_GUIDE_CN.md)' in (root/'README_CN.md').read_text()
    old, new = Usd.Stage.Open(str(SOURCE/'scene.usd')), Usd.Stage.Open(str(root/'scene.usd'))
    assert physical_state(old) == physical_state(new)
    script = new.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script').Get()
    assert 'state = advance(' in script
    assert 'min(0.1,' not in script
    assert 'success = hold >= 3.0 and visited_open' not in script
    task = yaml.safe_load((root/'task.yaml').read_text())
    assert task['state_contract']['required_sequence'] == []
    assert task['state_contract']['success_window_ml'] == [15, PINK_END]
    metrics = yaml.safe_load((root/'metrics.yaml').read_text())
    assert sum(m['weight'] for m in metrics['metrics']) == pytest.approx(1)
    assert not any(m['id'] in ('coarse_open_phase', 'fine_phase') for m in metrics['metrics'])
    assert metrics['task_id'] == root.name
    namespace = {'__file__': str(root/'task_config.py')}
    exec((root/'task_config.py').read_text(), namespace)
    config = namespace['TASKS'][root.name]['titration_contract']
    assert config['success_window_ml'] == [15, PINK_END]
    assert config['success_latched'] is True
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['status'] == 'runtime_pending'
    assert 'runtime_evidence' not in manifest
    assert not (root/'evidence/runtime').exists()


def test_runtime_review_requires_all_new_policy_checks():
    from scripts.validate_traditional_titration_vr_r1 import evaluate_report
    from scripts.validate_titration_linear_runtime import REQUIRED_CHECKS
    report = dict(policy_version='linear_deadzone_v1',
                  linear_policy_checks={k: True for k in REQUIRED_CHECKS},
                  state_machine=dict(success=True, endpoint_dispensed_ml=16.5,
                                     visited={}, hold_seconds=3.1,
                                     indicator_phase='endpoint_pale_pink', pale_visual_visible=True,
                                     reset_dispensed_ml=0),
                  dof_count=1, layout=dict(tip_to_receiver_vertical_clearance_m=.014,
                                          tip_receiver_xy_error_m=0),
                  objects={name: {'translation_drift_m': 0} for name in (
                      'obj_magnetic_stirrer', 'obj_receiver_flask',
                      'obj_sample_beaker', 'obj_context_conical_flask')})
    assert evaluate_report(report)['status'] == 'pass'
    del report['linear_policy_checks']['timing_45']
    assert evaluate_report(report)['status'] == 'blocked'


def test_finalizer_rejects_stale_scene_report(tmp_path):
    import json
    from scripts.finalize_traditional_titration_vr_r15 import prepare
    (tmp_path/'scene.usd').write_text('changed scene')
    report = tmp_path/'report.json'
    report.write_text(json.dumps(dict(scene_sha256='old', status='pass')))
    with pytest.raises(ValueError, match='unqualified report'):
        prepare(tmp_path, [report]*3)

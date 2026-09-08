"""Prescribed-joint cold-start checks for the r1.5 task, not a robot episode runner."""
import math

from scripts.titration_linear_policy import MAX_RATE, PINK_END, TRANSITION_START, color, flow_rate

REQUIRED_CHECKS = (
    'flow_curve', 'timing_90', 'timing_45', 'actual_transition_color',
    'free_angle_success', 'hold_interrupt', 'success_latched',
    'overshoot_before_success_fails', 'reset_complete', 'pause_freezes_color',
)


def receiver_visual_state(station):
    from pxr import Usd, UsdGeom, UsdShade
    stage = station.GetStage()
    targets = station.GetRelationship('titration:receiverLiquidVisuals').GetTargets()
    shaders = station.GetRelationship('titration:receiverLiquidShader').GetTargets()
    visible, bindings = [], []
    for path in targets:
        prim = stage.GetPrimAtPath(path)
        if not prim:
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() != 'invisible':
            visible.append(str(path))
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if material:
            shader, _, _ = material.ComputeSurfaceSource('mdl')
            if shader:
                bindings.append(str(shader.GetPath()))
    valid = len(targets) == len(shaders) == len(visible) == len(bindings) == 1
    if valid:
        tree = list(Usd.PrimRange(stage.GetPrimAtPath(targets[0]).GetParent()))
        valid = (bindings == [str(shaders[0])]
                 and sum(p.IsA(UsdGeom.Mesh) for p in tree) == 1
                 and sum(p.IsA(UsdShade.Material) for p in tree) == 1
                 and sum(p.IsA(UsdShade.Shader) for p in tree) == 1)
    return dict(visual_paths=[str(p) for p in targets], shader_paths=[str(p) for p in shaders],
                visible_paths=visible, bound_shader_paths=bindings, single_material_valid=bool(valid))


def exercise(world, articulation, station, report, burette_state, liquid_colors):
    import numpy as np
    dt = 1/60
    checks, traces = {}, {}
    single = report.get('receiver_visual_mode') == 'single_material'
    expected_visuals = receiver_visual_state(station)
    report['receiver_visual_initial'] = expected_visuals

    def value(name):
        return station.GetAttribute('titration:'+name).Get()

    def tick(angle, count=1):
        for _ in range(count):
            articulation.set_joint_positions(np.asarray([math.radians(angle)]))
            world.step(render=False)
            if single:
                current = receiver_visual_state(station)
                checks['single_material_persistent'] = (checks.get('single_material_persistent', True)
                    and current['single_material_valid'] and current == expected_visuals)

    def reset():
        station.GetAttribute('titration:reset_requested').Set(True)
        tick(0, 3)

    def snapshot():
        return dict(volume=float(value('dispensed_volume_ml')), phase=value('indicator_phase'),
                    angle=float(value('stopcock_angle_deg')), colors=liquid_colors(),
                    success=bool(value('task_success')), hold=float(value('endpoint_hold_seconds')))

    def until(angle, threshold):
        for _ in range(6000):
            tick(angle)
            if float(value('dispensed_volume_ml')) >= threshold:
                return
        raise RuntimeError('volume threshold not reached')

    reset()
    report['burette_states']['running_initial'] = burette_state()
    report['liquid_material'] = {'initial': liquid_colors()}
    flow_samples = []
    for angle in (0, 4.9, 5, 5.1, 10, 25, 45, 90):
        reset()
        tick(angle, 12)
        flow_samples.append(dict(requested_angle=angle, actual_angle=float(value('stopcock_angle_deg')),
                                measured_rate=float(value('flow_rate_ml_s')),
                                expected_rate=flow_rate(angle)))
    checks['flow_curve'] = all(abs(s['measured_rate']-s['expected_rate']) < 1e-5 for s in flow_samples)
    report['linear_flow_samples'] = flow_samples
    for angle in (90, 45):
        reset()
        entries = {}
        trace = []
        transition_colors_ok = False
        for frame in range(1, 1000):
            tick(angle)
            snap = snapshot()
            snap['time_s'] = frame*dt
            trace.append(snap)
            entries.setdefault(snap['phase'], frame*dt)
            if snap['phase'] == 'transition':
                expected = color(snap['volume'])[1]
                transition_colors_ok |= bool(snap['colors']) and all(
                    max(abs(a-b) for a, b in zip(c, expected)) < 1e-5 for c in snap['colors'])
            if 12.5 <= snap['volume'] < 12.5+MAX_RATE*dt:
                report['burette_states']['mid'] = burette_state()
            if snap['phase'] == 'overshoot':
                break
        q = flow_rate(angle)
        tolerance = dt+1e-5
        checks[f'timing_{angle}'] = (
            abs(entries.get('transition', -100)-TRANSITION_START/q) <= tolerance
            and abs(entries.get('endpoint_pale_pink', -100)-15/q) <= tolerance
            and abs(entries.get('overshoot', -100)-PINK_END/q) <= tolerance
            and abs((entries.get('overshoot', 0)-entries.get('endpoint_pale_pink', 0))-(PINK_END-15)/q) <= tolerance)
        checks['actual_transition_color'] = checks.get('actual_transition_color', True) and transition_colors_ok
        traces[str(angle)] = dict(entries=entries, samples=trace)
    # A low-angle-only path must succeed without ever visiting OPEN.
    reset()
    until(25, (TRANSITION_START+15)/2)
    before = snapshot()
    tick(0, 190)
    after = snapshot()
    report['paused_transition'] = dict(before=before, after=after)
    checks['pause_freezes_color'] = (after['volume'] == before['volume']
        and after['phase'] == before['phase'] and not value('task_success')
        and all(max(abs(a-b) for a, b in zip(c, d)) < 1e-5
                for c, d in zip(after['colors'], before['colors'])))
    until(25, 15.3)
    tick(0, 120)
    incomplete = not value('task_success')
    tick(10, 3)
    interrupted = float(value('endpoint_hold_seconds')) == 0
    tick(0, 179)
    checks['hold_interrupt'] = incomplete and interrupted and not value('task_success')
    tick(0, 3)
    completed = snapshot()
    checks['free_angle_success'] = (bool(value('task_success')) and not value('visited_open')
                                   and float(value('completion_hold_seconds')) >= 3)
    completion_volume = float(value('completion_volume_ml'))
    completion_hold = float(value('completion_hold_seconds'))
    report['liquid_material']['endpoint'] = liquid_colors()
    success_state = dict(success=bool(value('task_success')), endpoint_dispensed_ml=completion_volume,
                         hold_seconds=completion_hold, indicator_phase=value('indicator_phase'),
                         visited={n: bool(value('visited_'+n)) for n in ('open', 'fine', 'drip')},
                         pale_visual_visible=len(receiver_visual_state(station)['visible_paths']) == 1)
    until(90, 25)
    checks['success_latched'] = (bool(value('task_success')) and bool(value('overshoot'))
                                and float(value('completion_volume_ml')) == completion_volume
                                and float(value('completion_hold_seconds')) == completion_hold)
    report['burette_states']['end_scale'] = burette_state()
    reset()
    until(90, PINK_END+.1)
    tick(0, 190)
    checks['overshoot_before_success_fails'] = bool(value('overshoot')) and not value('task_success')
    reset()
    checks['reset_complete'] = (value('dispensed_volume_ml') == 0 and value('burette_liquid_volume_ml') == 25
                                and not value('task_success') and not value('overshoot')
                                and value('completion_volume_ml') == -1 and value('completion_hold_seconds') == 0)
    success_state['reset_dispensed_ml'] = float(value('dispensed_volume_ml'))
    report['liquid_material']['reset'] = liquid_colors()
    report['burette_states']['reset'] = burette_state()
    report['linear_policy_checks'] = checks
    report['linear_timing'] = traces
    report['completion_snapshot'] = completed
    tick(0, 300)
    return success_state

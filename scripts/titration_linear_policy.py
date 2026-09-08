"""Portable arithmetic for the r1.5 visual titration task; embedded into its USD controller."""
import math

POLICY_VERSION = 'linear_deadzone_v1'
MAX_RATE = 30.0/11.0
TRANSITION_START = MAX_RATE*5.0
PINK_START = 15.0
PINK_END = PINK_START + MAX_RATE*(40.0/85.0)*1.5


def flow_rate(angle):
    if not math.isfinite(angle):
        raise ValueError('nonfinite stopcock angle')
    return MAX_RATE*max(0.0, min(90.0, abs(angle))-5.0)/85.0


def color(volume):
    clear, pale, deep = (0.97, 0.99, 1.0), (1.0, 0.80, 0.88), (0.85, 0.12, 0.28)
    if volume < TRANSITION_START:
        return 'colorless', clear, 0.36
    if volume < PINK_START:
        alpha = (volume-TRANSITION_START)/(PINK_START-TRANSITION_START)
        return 'transition', tuple(clear[i]+(pale[i]-clear[i])*alpha for i in range(3)), .36+.32*alpha
    if volume <= PINK_END:
        return 'endpoint_pale_pink', pale, .68
    alpha = min(1.0, volume-PINK_END)
    return 'overshoot', tuple(pale[i]+(deep[i]-pale[i])*alpha for i in range(3)), .68+.10*alpha


def initial_state():
    return dict(stopcock_angle_deg=0.0, valve_open_fraction=0.0, valve_state='CLOSED',
                flow_rate_ml_s=0.0, burette_liquid_volume_ml=25.0, burette_liquid_level=1.0,
                dispensed_volume_ml=0.0, spilled_volume_ml=0.0, visited_open=False,
                visited_fine=False, visited_drip=False, overshoot=False, task_success=False,
                endpoint_hold_seconds=0.0, completion_volume_ml=-1.0,
                completion_hold_seconds=0.0, indicator_phase='colorless', reset_requested=False)


def advance(previous, angle, dt, target=True):
    rate = flow_rate(angle)
    if not math.isfinite(dt) or dt < 0:
        raise ValueError('invalid simulation timestep')
    angle = min(90.0, abs(angle))
    state = dict(previous)
    band = 'CLOSED' if angle <= 5 else 'DRIP' if angle < 15 else 'FINE' if angle < 40 else 'OPEN'
    dv = min(rate*dt, max(0.0, state['burette_liquid_volume_ml']))
    remaining = max(0.0, state['burette_liquid_volume_ml']-dv)
    volume = state['dispensed_volume_ml']+(dv if target else 0.0)
    overshoot = state['overshoot'] or volume > PINK_END
    hold = state['endpoint_hold_seconds']+dt if (
        band == 'CLOSED' and PINK_START <= volume <= PINK_END and not overshoot) else 0.0
    success = state['task_success'] or hold >= 3.0
    if success and not state['task_success']:
        state.update(completion_volume_ml=volume, completion_hold_seconds=hold)
    state.update(stopcock_angle_deg=angle, valve_open_fraction=rate/MAX_RATE, valve_state=band,
                 flow_rate_ml_s=rate if remaining > 0 else 0.0,
                 burette_liquid_volume_ml=remaining, burette_liquid_level=remaining/25.0,
                 dispensed_volume_ml=volume,
                 spilled_volume_ml=state['spilled_volume_ml']+(0.0 if target else dv),
                 overshoot=overshoot, task_success=success, endpoint_hold_seconds=hold,
                 indicator_phase=color(volume)[0])
    # Retained diagnostics only: these flags no longer gate success.
    state['visited_open'] |= band == 'OPEN'
    state['visited_fine'] |= state['visited_open'] and band == 'FINE'
    state['visited_drip'] |= state['visited_fine'] and band == 'DRIP'
    return state


def contract():
    return dict(policy_version=POLICY_VERSION, target_volume_ml=PINK_START,
                success_window_ml=[PINK_START, PINK_END], transition_start_ml=TRANSITION_START,
                closed_endpoint_hold_seconds=3.0, success_latched=True, required_sequence=[],
                overshoot_continues_episode=True, overshoot_can_succeed=False,
                flow_curve=dict(type='linear_with_deadzone', closed_max_angle_deg=5.0,
                                max_angle_deg=90.0, max_rate_ml_s=MAX_RATE),
                time_basis='simulation_seconds')

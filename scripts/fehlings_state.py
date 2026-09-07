"""Pure semantics embedded verbatim in the VR USD; not chemical kinetics."""
import math


def geometry_flags(xyz, axis, spec):
    water = spec['water_surface_z']
    center = spec['bath_center_xyz']
    tilt_ok = axis[2] >= math.cos(math.radians(20))
    radial_ok = (math.hypot(xyz[0]-center[0], xyz[1]-center[1])+spec['outer_radius_m']
                 +spec['mouth_height_m']*math.hypot(axis[0],axis[1]) < spec['bath_inner_radius'])
    immersed = bool(tilt_ok and radial_ok and xyz[2]+spec['sample_height_m']*axis[2] <= water-0.003
                    and xyz[2]+spec['mouth_height_m']*axis[2] >= water+0.010
                    and xyz[2] >= spec['bath_inner_floor_z']+0.001)
    return immersed, bool(tilt_ok and xyz[2] >= water+0.010)


def initial_state():
    return {'heated_s': 0.0, 'observe_s': 0.0, 'anchor': None,
            'stage': 'ready', 'success': False}


def appearance(seconds):
    progress = min(1.0, max(0.0, seconds/30))
    blue, brown, red = (0.4,0.72,0.95), (0.55,0.28,0.12), (0.70,0.18,0.07)
    start, end, mix = (blue, brown, seconds/10) if seconds < 10 else (brown, red, min(1,(seconds-10)/20))
    return {'progress': progress, 'color': tuple(a+(b-a)*mix for a,b in zip(start,end)),
            'opacity': 0.55+0.30*progress, 'sediment': max(0.0, min(1.0,(seconds-10)/20))}


def advance(state, dt, immersed, withdrawn, position):
    state = dict(state)
    if state['success'] or dt <= 0:
        return state
    if immersed:
        state['heated_s'] = min(120.0, state['heated_s']+dt)
    ready = state['heated_s'] >= 120-1e-6
    if ready and withdrawn:
        if state['anchor'] is None:
            state['anchor'] = tuple(position)
        if math.dist(position, state['anchor']) > 0.02:
            state['anchor'], state['observe_s'] = tuple(position), 0.0
        else:
            state['observe_s'] += dt
        state['success'] = state['observe_s'] >= 3-1e-6
    else:
        state['observe_s'], state['anchor'] = 0.0, None
    state['stage'] = ('complete' if state['success'] else 'observing' if ready and withdrawn
                      else 'ready_to_withdraw' if ready else 'heating' if state['heated_s'] else 'ready')
    return state

"""Five fixed visual regions; teaching color progression, not chemical kinetics."""
import math

POLICY_VERSION = 'visual_five_layers_v6'
LAYER_COUNT = 5
COMPLETE_SECONDS = 30.0
ONSET_SECONDS = 3.0
COLOR_NAMES = ('blue', 'green', 'yellow', 'orange', 'orange_red')
# UsdPreviewSurface linear RGB inputs, calibrated through the retained tube glass.
PALETTE = ((.08, .45, .95), (.12, .70, .20), (.95, .80, .07), (1.0, .40, .04), (1.0, .22, .035))
OPACITIES = (.70, .82, .90, .95, .98)
ROUGHNESSES = (.10, .18, .28, .40, .50)


def initial_state():
    return {'heated_s': 0.0, 'observe_s': 0.0, 'anchor': None, 'stage': 'ready', 'success': False}


def layer_key_times(index):
    if not 0 <= index < LAYER_COUNT:
        raise ValueError('layer index must be in bottom-to-top order 0..4')
    return (3 + .5*index, 7 + 1.25*index, 12 + 1.5*index, 18 + 1.5*index, 24 + 1.5*index)


def appearance(seconds):
    if not math.isfinite(seconds):
        raise ValueError('finite contact time required')
    t = min(COMPLETE_SECONDS, max(0.0, seconds))
    layers = []
    for i in range(LAYER_COUNT):
        times = layer_key_times(i)
        segment, fraction = 0, 0.0
        if t >= times[-1]:
            segment, fraction = 3, 1.0
        elif t > times[0]:
            for segment in range(4):
                if t <= times[segment+1]:
                    fraction = (t-times[segment])/(times[segment+1]-times[segment])
                    break
        def mix(a, b):
            return a + (b-a)*fraction
        layers.append(dict(color=tuple(mix(a,b) for a,b in zip(PALETTE[segment],PALETTE[segment+1])),
                           opacity=mix(OPACITIES[segment],OPACITIES[segment+1]),
                           roughness=mix(ROUGHNESSES[segment],ROUGHNESSES[segment+1]),
                           progress=(segment+fraction)/4))
    return dict(layers=layers, progress=max(0.0,(t-ONSET_SECONDS)/(COMPLETE_SECONDS-ONSET_SECONDS)),
                reaction_stage='warming' if t<=3 else 'greening' if t<9 else 'yellowing' if t<16
                else 'reddening' if t<23 else 'converging' if t<30 else 'developed')


def advance(state, dt, immersed, withdrawn, position):
    state = dict(state)
    if state['success'] or dt <= 0:
        return state
    if immersed:
        state['heated_s'] = min(COMPLETE_SECONDS, state['heated_s']+dt)
    ready = state['heated_s'] >= COMPLETE_SECONDS-1e-6
    if ready and withdrawn:
        if state['anchor'] is None:
            state['anchor'] = tuple(position)
        if math.dist(position,state['anchor']) > .02:
            state['anchor'],state['observe_s'] = tuple(position),0.0
        else:
            state['observe_s'] += dt
        state['success'] = state['observe_s'] >= 3-1e-6
    else:
        state['observe_s'],state['anchor'] = 0.0,None
    state['stage'] = ('complete' if state['success'] else 'observing' if ready and withdrawn
                      else 'ready_to_withdraw' if ready else 'heating' if state['heated_s'] else 'ready')
    return state

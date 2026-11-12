"""Simulator-neutral, conserved reagent ledger; volumes are nominal millilitres."""
import math

MAX_RATE = 30.0/11.0
TRANSITION_START = MAX_RATE*5.0
PINK_START = 15.0
PINK_END = PINK_START+MAX_RATE*(40.0/85.0)*1.5


def flow_rate(angle):
    if not math.isfinite(angle):
        raise ValueError('nonfinite stopcock angle')
    return MAX_RATE*max(0., min(90., abs(angle))-5.)/85.


def emission_speed(rate_ml_s, spacing_m):
    """Controlled numerical outlet: clear four emission lanes between doses."""
    return max(.08, 1.5 * rate_ml_s * 1e-6 / (4 * spacing_m**2))


def indicator(volume):
    clear, pale, deep = (0.97, .99, 1.), (1., .80, .88), (.85, .12, .28)
    if volume < TRANSITION_START:
        return 'colorless', clear
    if volume < PINK_START:
        t = (volume-TRANSITION_START)/(PINK_START-TRANSITION_START)
        return 'transition', tuple(a+(b-a)*t for a,b in zip(clear,pale))
    if volume <= PINK_END:
        return 'endpoint_pale_pink', pale
    t = min(1., volume-PINK_END)
    return 'overshoot', tuple(a+(b-a)*t for a,b in zip(pale,deep))


def touching_liquid(points, liquid_points, contact_distance):
    """Match actual reagent and liquid particle neighborhoods, not air in a neck."""
    import numpy as np
    points = np.asarray(points,dtype=float).reshape(-1,3)
    liquid = np.asarray(liquid_points,dtype=float).reshape(-1,3)
    result = np.zeros(len(points),dtype=bool)
    if not len(points) or not len(liquid):
        return result
    lower,upper = points.min(axis=0)-contact_distance,points.max(axis=0)+contact_distance
    nearby = liquid[np.all((liquid>=lower)&(liquid<=upper),axis=1)]
    # Bounded chunks keep unusual dispersed streams from making a huge matrix.
    for start in range(0,len(nearby),512):
        delta = points[:,None,:]-nearby[None,start:start+512,:]
        result |= np.any(np.einsum('ijk,ijk->ij',delta,delta)<=contact_distance**2,axis=1)
    return result


def touching_receiver_bulk(points, liquid_points, initial_count, origin, up, contact_distance, surface_pad):
    """Exclude isolated newly received droplets above the original solution bulk."""
    import numpy as np
    liquid = np.asarray(liquid_points,dtype=float).reshape(-1,3)
    if initial_count<=0 or initial_count>len(liquid):
        raise ValueError('Receiver initial solution cohort is missing')
    heights = (liquid-np.asarray(origin)) @ np.asarray(up)
    surface = np.quantile(heights[:initial_count],.995)+surface_pad
    return touching_liquid(points,liquid[heights<=surface],contact_distance)


class TitrationLedger:
    def __init__(self, quantum_ml, initial_source_ml, usable_ml=25., dose_batch=8):
        if (not all(math.isfinite(v) and v > 0 for v in (quantum_ml, initial_source_ml, usable_ml))
                or initial_source_ml < usable_ml or quantum_ml > usable_ml
                or not isinstance(dose_batch, int) or dose_batch < 1):
            raise ValueError('positive usable inventory and particle quantum required')
        self.quantum_ml = quantum_ml
        self.initial_source_ml = initial_source_ml
        self.usable_ml = usable_ml
        self.dose_batch = dose_batch
        self.reset()

    def reset(self):
        self.states = {}
        self.credit_ml = 0.
        self.hold_s = 0.
        self.time_s = 0.
        self.success = False
        self.overshoot = False
        self.completed_volume_ml = None

    def _volume(self, name):
        return sum(state == name for state in self.states.values())*self.quantum_ml

    @property
    def source_ml(self):
        return self.initial_source_ml-len(self.states)*self.quantum_ml

    @property
    def inflight_ml(self):
        return self._volume('inflight')

    @property
    def received_ml(self):
        return self._volume('received')

    @property
    def spilled_ml(self):
        return self._volume('spilled')

    @property
    def phase(self):
        return indicator(self.received_ml)[0]

    @property
    def conservation_error_ml(self):
        return self.initial_source_ml-self.source_ml-self.inflight_ml-self.received_ml-self.spilled_ml

    def tick(self, angle, dt, *, received=(), spilled=()):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('positive simulation delta required')
        rate = flow_rate(angle)
        received, spilled = set(received), set(spilled)
        if received & spilled or any(i not in self.states for i in received | spilled):
            raise ValueError('unknown or contradictory dose observation')
        for i in received:
            if self.states[i] != 'received':
                self.states[i] = 'received'
        for i in spilled:
            if self.states[i] == 'inflight':
                self.states[i] = 'spilled'
        self.time_s += dt
        self.credit_ml += rate*dt
        available = max(0, math.floor(self.usable_ml/self.quantum_ml+1e-9)-len(self.states))
        n = min(available, math.floor(self.credit_ml/self.quantum_ml+1e-9)) if rate else 0
        if 5 < abs(angle) < 15:
            n = n//self.dose_batch*self.dose_batch
        ids = list(range(len(self.states), len(self.states)+n))
        for i in ids:
            self.states[i] = 'inflight'
        self.credit_ml -= n*self.quantum_ml
        if not available:
            self.credit_ml = 0.
        volume = self.received_ml
        self.overshoot |= volume > PINK_END
        eligible = rate == 0 and PINK_START <= volume <= PINK_END and not self.overshoot
        self.hold_s = self.hold_s+dt if eligible else 0.
        if self.hold_s >= 3.-1e-9 and not self.success:
            self.success = True
            self.completed_volume_ml = volume
        return ids

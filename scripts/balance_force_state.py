"""Simulator-neutral force readout policy; input is measured gross mass in grams."""
from collections import deque
import math


def validate_target(target_g, tolerance_g, grain_mass_g, count, capacity_g):
    if (not all(math.isfinite(x) and x>0 for x in (target_g,tolerance_g,grain_mass_g,capacity_g))
            or tolerance_g >= grain_mass_g/2 or target_g>capacity_g
            or not any(abs(k*grain_mass_g-target_g)<=tolerance_g for k in range(1,count+1))):
        raise ValueError('target must be reachable and distinguish adjacent grain counts')


def vertical_mass_g(force, quaternion_xyzw, gravity, pan_mass_g):
    """Project the measured link-local force onto world vertical before F/g."""
    x, y, z, w = quaternion_xyzw
    vertical = (2*(x*z-y*w)*force[0] + 2*(y*z+x*w)*force[1]
                + (1-2*(x*x+y*y))*force[2])
    return vertical / gravity * 1000 - pan_mass_g


def choose_resolution(errors_and_ranges):
    """Select finest common display division supported by every held-out run."""
    runs = list(errors_and_ranges)
    if not runs or any(not all(math.isfinite(v) and v >= 0 for v in row) for row in runs):
        raise ValueError('finite validation measurements required')
    for division in (.0001, .001, .01, .1):
        if all(error <= division and spread <= 2 * division for error, spread in runs):
            return division
    raise ValueError('force measurement did not qualify at 0.1 g')


class BalanceState:
    def __init__(self, resolution_g, target_g=30, tolerance_g=.02, capacity_g=200):
        if not all(math.isfinite(x) and x > 0 for x in
                   (resolution_g, target_g, tolerance_g, capacity_g)):
            raise ValueError('positive finite balance configuration required')
        self.resolution_g = resolution_g
        self.target_g = target_g
        self.tolerance_g = tolerance_g
        self.capacity_g = capacity_g
        self.reset()

    def reset(self):
        self.time = 0.
        self.filtered_g = None
        self.net_g = 0.
        self.tare_g = 0.
        self.stable = False
        self.tared = False
        self.pending_tare = False
        self.tare_requested_at = 0.
        self.was_pressed = False
        self.error = ''
        self.status = 'initializing'
        self.success = False
        self.completed_net_g = None
        self.target_hold_s = 0.
        self.history = deque()

    def update(self, gross_g, dt, *, pressed=False, valid=True, eligible=False):
        if not math.isfinite(dt) or dt <= 0:
            return
        self.time += dt
        if pressed and not self.was_pressed:
            self.pending_tare = True
            self.tare_requested_at = self.time
            self.error = ''
        self.was_pressed = pressed
        overload = math.isfinite(gross_g) and gross_g > self.capacity_g
        valid = valid and math.isfinite(gross_g) and not overload
        self.stable = False
        if valid:
            if self.filtered_g is None:
                self.filtered_g = gross_g
            else:
                self.filtered_g += (1 - math.exp(-dt / .25)) * (gross_g - self.filtered_g)
            self.history.append((self.time, self.filtered_g))
            while len(self.history) > 1 and self.history[1][0] <= self.time - .6:
                self.history.popleft()
            values = [v for _, v in self.history]
            self.stable = (self.time - self.history[0][0] >= .6 - 1e-8
                           and max(values) - min(values) <= 2 * self.resolution_g)
            self.status = 'stable' if self.stable else 'settling'
        else:
            self.filtered_g = None
            self.history.clear()
            self.status = 'overload' if overload else 'invalid'
        if self.pending_tare:
            if self.time - self.tare_requested_at >= 5:
                self.pending_tare = False
                self.error = 'tare_timeout'
            elif self.stable and self.filtered_g >= -self.resolution_g:
                self.tare_g = self.filtered_g
                self.tared = True
                self.pending_tare = False
                self.target_hold_s = 0
            elif valid:
                self.status = 'tare_wait'
        if self.filtered_g is not None:
            self.net_g = self.filtered_g - self.tare_g
        if (self.stable and self.tared and not self.pending_tare and eligible
                and abs(self.net_g - self.target_g) <= self.tolerance_g):
            self.target_hold_s += dt
            if self.target_hold_s >= 2 and not self.success:
                self.success = True
                self.completed_net_g = self.net_g
        else:
            self.target_hold_s = 0

    def display(self):
        if self.status in ('invalid', 'initializing'):
            return '------'
        if self.status == 'overload':
            return 'OL'
        places = max(0, round(-math.log10(self.resolution_g)))
        value = round(self.net_g / self.resolution_g) * self.resolution_g
        if abs(value) < self.resolution_g / 2:
            value = 0.
        return f'{value:.{places}f}'

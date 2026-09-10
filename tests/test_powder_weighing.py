"""Behavior tests for the prescribed powder fixture and its measurement checks."""
import pytest

from scripts.powder_weighing_protocol import spoon_target, measurement_check


def test_spoon_waits_for_tare_and_clears_receiver():
    assert spoon_target(0,.18,.16)[0] == spoon_target(4,.18,.16)[0]
    position, angle, phase = spoon_target(15,.18,.16)
    assert position == pytest.approx((.18,0,.20))
    assert angle == 0
    assert phase == 'transfer'
    position, angle, phase = spoon_target(26,.18,.16)
    assert abs(position[0]-.18) > .04
    assert phase == 'settled_readout'


def test_force_acceptance_requires_valid_stable_known_load():
    rows = [dict(net_g=.49,valid=True,stable=True),dict(net_g=.51,valid=True,stable=True)]
    assert measurement_check(rows,.5,.1)['passed']
    assert not measurement_check(rows,.8,.1)['passed']
    assert not measurement_check([dict(net_g=.5,valid=False,stable=True)],.5,.1)['passed']
    assert not measurement_check([],0,.1)['passed']
    assert not measurement_check([dict(net_g=float('nan'),valid=True,stable=True)],.5,.1)['passed']


def test_contact_channel_preserves_load_when_incoming_joint_loses_it():
    import numpy as np
    from scripts.powder_balance_runtime import PowderBalanceRuntime
    class JointView:
        def get_link_incoming_joint_force(self):
            return np.array([[[0.,0.,.4905,0.,0.,0.]]])  # pan self-weight only
    class Contacts:
        def get_net_contact_forces(self, dt):
            assert dt == pytest.approx(1/480)
            return np.array([[0.,0.,-.0981]])  # independent measured 10 g load
    runtime = PowderBalanceRuntime.__new__(PowderBalanceRuntime)
    runtime.view, runtime.contacts, runtime.pan = JointView(), Contacts(), 0
    from collections import deque
    runtime.force_window = deque()
    runtime.force_time = runtime.window_impulse_g_s = runtime.window_duration_s = 0.
    runtime.get = {'gravity_m_s2':9.81,'pan_mass_g':50.}.__getitem__
    diagnostics = {}
    runtime.put = diagnostics.__setitem__
    gross = runtime.measure_gross(np.array([[0.,0.,0.,0.,0.,0.,1.]]),1/480)
    assert gross == pytest.approx(10.)
    assert diagnostics['joint_gross_g'] == pytest.approx(0.)
    assert diagnostics['channel_disagreement_g'] == pytest.approx(-10.)
    runtime.reset_force_window()
    assert runtime.window_duration_s == 0.
    assert not runtime.force_window

"""Force readout and tare must not fabricate mass or accept transient success."""
import math

import pytest

from scripts.balance_force_state import BalanceState, choose_resolution, vertical_mass_g, validate_target


def test_configured_target_must_be_reachable_without_accepting_wrong_grain_count():
    validate_target(30,.2,10,5,200)
    validate_target(1,.02,.2,5,200)
    for args in [(31,.2,10,5,200),(30,10,10,5,200),(60,.2,10,5,200)]:
        with pytest.raises(ValueError):
            validate_target(*args)


def test_vertical_projection_does_not_lose_weight_under_small_tilt():
    angle=math.radians(4)
    mass=.08
    force=(-mass*9.81*math.sin(angle),0,mass*9.81*math.cos(angle))
    q=(0,math.sin(angle/2),0,math.cos(angle/2))
    assert vertical_mass_g(force,q,9.81,50)==pytest.approx(30)


def settle(state, mass, seconds=4, **kwargs):
    for _ in range(round(seconds * 120)):
        state.update(mass, 1 / 120, **kwargs)


def test_tare_waits_for_stability_then_removal_is_negative():
    s = BalanceState(resolution_g=0.01)
    s.update(10, 1 / 120, pressed=True)
    assert s.pending_tare and s.tare_g == 0
    settle(s, 10, pressed=True)
    assert s.tare_g == pytest.approx(10)
    settle(s, 20, pressed=True)
    assert s.net_g == pytest.approx(10, abs=.01)  # long press cannot tare twice
    settle(s, 0)
    assert s.net_g == pytest.approx(-10, abs=.01)


def test_invalid_force_does_not_become_zero_or_complete_tare():
    s = BalanceState(resolution_g=.01)
    settle(s, 10)
    s.update(10, .01, pressed=True, valid=False)
    settle(s, math.nan, seconds=6, valid=False)
    assert not s.stable and s.tare_g == 0 and s.error == 'tare_timeout'
    assert not s.success


def test_motion_preserves_tare_but_clears_filter_and_stability():
    s = BalanceState(resolution_g=.01)
    settle(s, 10)
    s.update(10, .01, pressed=True)
    settle(s, 10)
    assert s.tare_g == pytest.approx(10)
    settle(s, 100, valid=False)
    settle(s, 15)
    assert s.net_g == pytest.approx(5, abs=.01)


def test_target_needs_tare_eligibility_and_hold_then_latches_snapshot():
    s = BalanceState(resolution_g=.01, target_g=30, tolerance_g=.02)
    settle(s, 30, eligible=True)
    assert not s.success
    settle(s, 0)
    s.update(0, .01, pressed=True)
    settle(s, 0)
    settle(s, 30, eligible=False)
    assert not s.success
    settle(s, 30, seconds=3, eligible=True)
    assert s.success and s.completed_net_g == pytest.approx(30, abs=.01)
    settle(s, 0)
    assert s.success and s.completed_net_g == pytest.approx(30, abs=.01)
    s.reset()
    assert not s.success and s.tare_g == 0 and not s.tared


def test_resolution_selected_from_all_runs_not_best_case():
    assert choose_resolution([(.00003, .0001), (.004, .008)]) == .01
    with pytest.raises(ValueError):
        choose_resolution([(.2, .01)])


def test_pause_does_not_advance_and_overload_blocks_tare():
    s = BalanceState(resolution_g=.01, capacity_g=200)
    s.update(10, 0, pressed=True)
    assert not s.pending_tare
    settle(s, 250, pressed=True)
    assert s.status == 'overload' and s.tare_g == 0

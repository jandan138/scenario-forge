"""Conserved dose accounting and original indicator rules for real liquid."""
import pytest

from scripts.task10_pbd_policy import TitrationLedger, flow_rate, indicator, PINK_END


def test_source_flow_curve_and_indicator_boundaries():
    assert flow_rate(5) == 0
    assert flow_rate(90) == pytest.approx(30/11)
    assert flow_rate(-90) == flow_rate(90)
    assert indicator(0)[0] == 'colorless'
    assert indicator(15)[0] == 'endpoint_pale_pink'
    assert indicator(PINK_END+.5)[0] == 'overshoot'


def test_emission_is_conserved_quantized_and_does_not_change_color_in_air():
    ledger = TitrationLedger(.01, 32., dose_batch=3)
    ids = ledger.tick(10, 1.)
    assert len(ids) % 3 == 0
    assert ledger.received_ml == 0
    assert ledger.phase == 'colorless'
    assert ledger.source_ml + ledger.inflight_ml == pytest.approx(32.)
    assert not ledger.tick(0, 1.)
    ledger.tick(0, .1, received=ids[:2], spilled=ids[2:])
    assert ledger.received_ml == .02
    assert ledger.conservation_error_ml == pytest.approx(0.)


def test_duplicate_reentry_cannot_recolor_or_double_count():
    ledger = TitrationLedger(.01, 32.)
    ids = ledger.tick(90, 1.)
    ledger.tick(0, .1, received=ids)
    before = ledger.received_ml
    ledger.tick(0, .1, received=ids)
    assert ledger.received_ml == before
    with pytest.raises(ValueError):
        ledger.tick(0, .1, received=[99999])


def test_closed_endpoint_hold_requires_received_volume_then_resets_everything():
    ledger = TitrationLedger(.01, 32.)
    ids = ledger.tick(90, 15.1/(30/11))
    assert not ledger.success
    ledger.tick(0, 1., received=ids)
    assert not ledger.success
    ledger.tick(0, 2.)
    assert ledger.success
    more = ledger.tick(90, 2.)
    ledger.tick(0, .1, received=more)
    assert ledger.phase == 'overshoot' and ledger.success
    ledger.reset()
    assert ledger.source_ml == 32. and ledger.received_ml == 0
    assert not ledger.success and not ledger.overshoot


def test_overshoot_and_source_exhaustion_do_not_manufacture_liquid():
    ledger = TitrationLedger(.01, 32.)
    ids = ledger.tick(90, 100.)
    assert len(ids) == 2500
    assert ledger.source_ml == pytest.approx(7.)
    assert not ledger.tick(90, 100.)
    ledger.tick(0, 4., received=ids)
    assert ledger.overshoot and not ledger.success
    assert ledger.conservation_error_ml == pytest.approx(0.)


@pytest.mark.parametrize('quantum,total', [(0,32),(.01,20),(float('nan'),32)])
def test_rejects_unusable_inventory(quantum,total):
    with pytest.raises(ValueError):
        TitrationLedger(quantum,total)


def test_emitter_clears_a_particle_layer_before_reusing_its_lane():
    from scripts.task10_pbd_policy import emission_speed
    spacing = .0015
    rate = flow_rate(90)
    lane_reuse_s = 4 * spacing**3 * 1e6 / rate
    assert emission_speed(rate, spacing) * lane_reuse_s >= spacing
    assert 0 < emission_speed(.01, spacing) < 1


def test_previously_spilled_dose_can_enter_later_without_duplicating_mass():
    ledger = TitrationLedger(.01, 32.)
    ids = ledger.tick(90, .1)
    ledger.tick(0, .1, spilled=ids)
    ledger.tick(0, .1, received=ids)
    assert ledger.spilled_ml == 0
    assert ledger.received_ml == pytest.approx(len(ids)*.01)
    assert ledger.conservation_error_ml == pytest.approx(0)


def test_received_reagent_requires_contact_with_real_liquid():
    import numpy as np
    from scripts.task10_pbd_policy import touching_liquid
    bulk = np.array([[0.,0.,0.], [.001,0.,0.], [0.,.001,0.]])
    drops = np.array([[0.,0.,.01], [0.,0.,.001], [.05,0.,0.]])
    assert touching_liquid(drops,bulk,.002).tolist() == [False,True,False]
    assert not touching_liquid(drops,np.empty((0,3)),.002).any()


def test_airborne_reagent_column_is_not_the_receiver_bulk():
    import numpy as np
    from scripts.task10_pbd_policy import touching_receiver_bulk
    liquid = np.array([[0,0,0], [.001,0,0], [0,.001,0], [0,0,.1]])
    drops = np.array([[0,0,.101], [0,0,.001]])
    assert touching_receiver_bulk(drops,liquid,3,[0,0,0],[0,0,1],.002,.001).tolist() == [False,True]

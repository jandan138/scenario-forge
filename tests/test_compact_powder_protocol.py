import numpy as np
import pytest

from scripts.compact_powder_protocol import (
    bed_depth, cavity_mask, exclusive_loose_count, prescribed_spoon,
)

CFG = dict(bottle_height_m=.1,false_floor_m=.059,powder_surface_target_m=.070,
           grain_bound_m=.000827,inner_profile=[dict(z=.002,radius=.0282,exponent=5),dict(z=.1,radius=.024,exponent=2)],
           spoon_floor_envelope=[[0,0],[30,-.0028],[50,-.0065],[70,-.01024],[80,-.01175]])


def test_exclusive_loose_count_ignores_overlapping_spoon_in_bottle():
    in_bottle = [True, True, False, False]
    in_spoon = [True, False, True, False]
    in_boat = [False, False, False, True]
    assert exclusive_loose_count(in_bottle, in_spoon, in_boat) == 0
    assert exclusive_loose_count([False, False], [False, False], [False, False]) == 2


def test_profile_distinguishes_corner_from_circular_neck():
    p = np.array([[.023,.023,.01],[.023,.023,.099],[0,0,.06]])
    assert cavity_mask(p,CFG).tolist()==[True,False,True]


def test_depth_comes_from_observed_particle_columns():
    p = np.array([[x,y,z] for x in [-.006,.002,.010] for y in [-.006,.002]
                  for z in np.linspace(.060,.070,8)])
    depth = bed_depth(p,CFG)
    assert depth['surface_depth_median_m']==pytest.approx(.011827)
    assert depth['columns']==6


def test_pbd_bed_uses_solid_rest_offset_not_ico_hull():
    p = np.array([[x,y,z] for x in [-.006,.002,.010] for y in [-.006,.002]
                  for z in np.linspace(.060,.070,8)])
    depth = bed_depth(p, dict(CFG, powder_kind='pbd_solid', grain_radius_m=0.0007,
                             pbd_solid_rest_offset_m=0.0014))
    assert depth['surface_depth_median_m']==pytest.approx(.0117)


def test_pouring_keeps_head_in_place_and_new_bottle_is_reached():
    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle,receiver = (-.08,-.065,.756),(.287,-.105,.93)
    pose,_ = prescribed_spoon(38,initial,bottle,receiver,CFG)
    angle = 2*np.arctan2(pose[5],pose[3])
    assert pose[0]+.087*np.cos(angle)==pytest.approx(receiver[0])
    assert pose[2]-.087*np.sin(angle)==pytest.approx(receiver[2]+.05)
    pose,_ = prescribed_spoon(20,initial,bottle,receiver,CFG)
    assert pose[2]-.087*np.sin(2*np.arctan2(pose[5],pose[3])) < bottle[2]+.09


def _head_z(pose):
    return pose[2]-.087*np.sin(2*np.arctan2(pose[5],pose[3]))


def test_optional_early_lift_hold_stays_lower_at_t30():
    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle,receiver = (-.08,-.065,.756),(.287,-.105,.93)
    default,_ = prescribed_spoon(30,initial,bottle,receiver,CFG)
    held,_ = prescribed_spoon(30,initial,bottle,receiver,dict(CFG,lift_early_hold_m=0.006))
    assert _head_z(held) < _head_z(default) - 0.004
    # Total timeline is unchanged: carry still happens at t=32.
    _,phase = prescribed_spoon(32,initial,bottle,receiver,dict(CFG,lift_early_hold_m=0.006))
    assert phase=='lift_powder'


def test_retime_keys_only_stretches_segments_that_exceed_max_speed():
    from scripts.compact_powder_protocol import retime_keys_max_speed
    keys = [
        (8.0, (0.0, 0.0, 0.0), 0, 'a'),
        (10.0, (0.02, 0.0, 0.0), 0, 'b'),  # 2s, dist 20mm, peak 15 mm/s
        (12.0, (0.22, 0.0, 0.0), 0, 'c'),  # 2s, dist 200mm, peak 150 mm/s
    ]
    out = retime_keys_max_speed(keys, 0.04)
    assert out[0][0] == pytest.approx(8.0)
    assert out[1][0] == pytest.approx(10.0)
    assert out[2][0] == pytest.approx(10.0 + 1.5 * 0.20 / 0.04)


def test_spoon_max_speed_keeps_head_at_or_below_cap():
    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle,receiver = (-.08,-.065,.756),(.287,-.105,.93)
    cfg = dict(CFG, lift_early_hold_m=0.006, spoon_max_speed_m_s=0.04)
    times = np.arange(0.0, 70.0, 0.05)
    heads = []
    for t in times:
        pose, _ = prescribed_spoon(float(t), initial, bottle, receiver, cfg)
        pitch = 2 * np.arctan2(pose[5], pose[3])
        heads.append((pose[0] + .087 * np.cos(pitch), pose[1], pose[2] - .087 * np.sin(pitch)))
    heads = np.asarray(heads)
    speed = np.linalg.norm(np.diff(heads, axis=0), axis=1) / np.diff(times)
    assert speed.max() <= 0.04 + 0.003
    default_pose, default_phase = prescribed_spoon(36, initial, bottle, receiver, dict(CFG, lift_early_hold_m=0.006))
    limited_pose, limited_phase = prescribed_spoon(36, initial, bottle, receiver, cfg)
    assert default_phase == 'transfer'
    assert limited_phase != 'transfer' or limited_pose[0] != pytest.approx(default_pose[0])


def test_retimed_clock_maps_stretched_transfer_back_to_official_50s():
    from scripts.compact_powder_protocol import map_retimed_clock, prescribed_spoon_keys

    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle, receiver = (-.08,-.065,.756),(.287,-.105,.93)
    official = prescribed_spoon_keys(initial, bottle, receiver, dict(CFG, lift_early_hold_m=0.006))
    stretched = prescribed_spoon_keys(
        initial, bottle, receiver, dict(CFG, lift_early_hold_m=0.006, spoon_max_speed_m_s=0.04),
    )
    assert map_retimed_clock(8.0, stretched, official) == pytest.approx(8.0)
    assert map_retimed_clock(36.0, official, official) == pytest.approx(36.0)
    transfer_end = next(k[0] for k in official if k[3] == 'transfer')
    stretched_end = next(k[0] for k in stretched if k[3] == 'transfer')
    assert stretched_end > transfer_end + 5
    assert map_retimed_clock(stretched_end, stretched, official) == pytest.approx(transfer_end)
    mid = 0.5 * (next(k[0] for k in stretched if k[3] == 'lift_powder' and k[0] > 20) + stretched_end)
    mapped = map_retimed_clock(mid, stretched, official)
    assert 32 <= mapped <= 36


def test_canonical_close_time_keeps_stretched_pour_on_official_pour_beat():
    from scripts.compact_powder_protocol import canonical_close_time, phase_progress
    import numpy as np

    times = np.array([56.94, 58.94, 60.94, 62.94, 70.0])
    phases = np.array(['slow_pour', 'slow_pour', 'slow_pour', 'withdraw', 'settled_readout'])
    phase, u = phase_progress(times, phases, 0)
    assert phase == 'slow_pour'
    assert canonical_close_time(phase, u) == pytest.approx(36.0)
    phase, u = phase_progress(times, phases, 2)
    assert canonical_close_time(phase, u) == pytest.approx(40.0)
    assert 36 <= canonical_close_time(*phase_progress(times, phases, 1)) <= 40
    assert canonical_close_time(*phase_progress(times, phases, 4)) >= 42


def _pitch_deg(pose):
    return float(np.degrees(2 * np.arctan2(pose[5], pose[3])))


def test_carry_pitch_keeps_bowl_pocket_until_after_the_neck():
    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle, receiver = (-.08,-.065,.756),(.287,-.105,.93)
    default_lift, _ = prescribed_spoon(32, initial, bottle, receiver, CFG)
    kept, phase = prescribed_spoon(32, initial, bottle, receiver, dict(CFG, carry_pitch_deg=25))
    assert phase == 'lift_powder'
    assert _pitch_deg(default_lift) == pytest.approx(0.0, abs=0.5)
    assert _pitch_deg(kept) == pytest.approx(25.0, abs=0.5)
    late_lift, _ = prescribed_spoon(31, initial, bottle, receiver, dict(CFG, carry_pitch_deg=25))
    assert _pitch_deg(late_lift) >= 20.0
    over_boat, transfer = prescribed_spoon(36, initial, bottle, receiver, dict(CFG, carry_pitch_deg=25))
    assert transfer == 'transfer'
    assert _pitch_deg(over_boat) == pytest.approx(0.0, abs=0.5)
    held, _ = prescribed_spoon(36, initial, bottle, receiver,
                               dict(CFG, carry_pitch_deg=25, carry_pitch_through_transfer=True))
    assert _pitch_deg(held) == pytest.approx(25.0, abs=0.5)

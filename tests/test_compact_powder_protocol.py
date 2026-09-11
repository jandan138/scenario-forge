import numpy as np
import pytest

from scripts.compact_powder_protocol import bed_depth, cavity_mask, prescribed_spoon

CFG = dict(bottle_height_m=.1,false_floor_m=.059,powder_surface_target_m=.070,
           grain_bound_m=.000827,inner_profile=[dict(z=.002,radius=.0282,exponent=5),dict(z=.1,radius=.024,exponent=2)],
           spoon_floor_envelope=[[0,0],[30,-.0028],[50,-.0065],[70,-.01024],[80,-.01175]])


def test_profile_distinguishes_corner_from_circular_neck():
    p = np.array([[.023,.023,.01],[.023,.023,.099],[0,0,.06]])
    assert cavity_mask(p,CFG).tolist()==[True,False,True]


def test_depth_comes_from_observed_particle_columns():
    p = np.array([[x,y,z] for x in [-.006,.002,.010] for y in [-.006,.002]
                  for z in np.linspace(.060,.070,8)])
    depth = bed_depth(p,CFG)
    assert depth['surface_depth_median_m']==pytest.approx(.011827)
    assert depth['columns']==6


def test_pouring_keeps_head_in_place_and_new_bottle_is_reached():
    initial = (.083,.192,.861,.7809008,0,.62465507,0)
    bottle,receiver = (-.08,-.065,.756),(.287,-.105,.93)
    pose,_ = prescribed_spoon(38,initial,bottle,receiver,CFG)
    angle = 2*np.arctan2(pose[5],pose[3])
    assert pose[0]+.087*np.cos(angle)==pytest.approx(receiver[0])
    assert pose[2]-.087*np.sin(angle)==pytest.approx(receiver[2]+.05)
    pose,_ = prescribed_spoon(20,initial,bottle,receiver,CFG)
    assert pose[2]-.087*np.sin(2*np.arctan2(pose[5],pose[3])) < bottle[2]+.09

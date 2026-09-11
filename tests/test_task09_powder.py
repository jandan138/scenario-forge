import pytest

from scripts.task09_powder_protocol import prescribed_spoon


INITIAL = (.083692295,.192479053,.860885687,.7809008,0.,.62465507,0.)
BOTTLE = (-.08,-.065,.756)
RECEIVER = (.287,-.105,.93)


def test_original_spoon_is_lifted_before_reorientation():
    pose,phase = prescribed_spoon(0,INITIAL,BOTTLE,RECEIVER)
    assert pose == pytest.approx(INITIAL)
    pose,phase = prescribed_spoon(11,INITIAL,BOTTLE,RECEIVER)
    assert pose[2] > .985
    assert pose[3:] == pytest.approx(INITIAL[3:])
    assert phase == 'extract_from_beaker'


def test_horizontal_carry_uses_head_offset_and_clears_receiver():
    pose,phase = prescribed_spoon(36,INITIAL,BOTTLE,RECEIVER)
    assert pose[0]+.087 == pytest.approx(RECEIVER[0])
    assert pose[2] == pytest.approx(RECEIVER[2]+.04)
    assert pose[3:] == pytest.approx((1,0,0,0))
    pose,phase = prescribed_spoon(49,INITIAL,BOTTLE,RECEIVER)
    assert phase == 'settled_readout'
    assert pose[2] > RECEIVER[2]+.06


def test_pour_rotates_about_spoon_head_not_root():
    import math
    pose,_ = prescribed_spoon(38,INITIAL,BOTTLE,RECEIVER)
    angle = 2*math.atan2(pose[5],pose[3])
    assert pose[0]+.087*math.cos(angle) == pytest.approx(RECEIVER[0])
    assert pose[2]-.087*math.sin(angle) == pytest.approx(RECEIVER[2]+.04)


def test_wake_optimization_only_excludes_explicit_never_sleeping_grains():
    from scripts.task09_powder_runtime import requires_wake
    assert not requires_wake('obj_powder_grain_00000',0.,0.)
    assert requires_wake('obj_powder_grain_00000',None,0.)
    assert requires_wake('obj_powder_grain_00000',1e-6,0.)
    assert requires_wake('obj_weighing_boat',0.,0.)

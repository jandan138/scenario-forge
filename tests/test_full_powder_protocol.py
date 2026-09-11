import numpy as np
import pytest

from scripts.compact_powder_protocol import fill_level, near_full_check
from scripts.task09_powder_evidence import REQUIRED, validate_report


def test_fullness_requires_both_actual_depth_and_rim_clearance():
    cfg = dict(bottle_height_m=.1,false_floor_m=.084,grain_bound_m=.0008,
               inner_profile=[dict(z=.002,radius=.024,exponent=2),dict(z=.1,radius=.024,exponent=2)])
    points = np.array([[x,y,z] for x in [-.006,.002] for y in [-.006,.002]
                       for z in np.linspace(.085,.0942,8)])
    level = fill_level(points,cfg)
    assert level['median_headspace_m']==pytest.approx(.005)
    assert near_full_check(level)
    for shift in [-.004,.006]:
        moved = points+np.array([0,0,shift])
        assert not near_full_check(fill_level(moved,cfg))


def test_preparation_or_low_initial_bed_cannot_qualify_r4():
    cfg = dict(revision='r4',physics_hz=240,inner_profile=[{}],initial_state='presettled')
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = dict(status='passed',mode='settle',runtime='4.5.0',requested_runtime='45',
                scene_sha256='scene',entry_sha256='scene',physics_dt=1/240,solver='PGS',
                position_iterations_override=None,wake_all_override=False,engine_errors=[],
                requested_seconds=8,rows=[{'time_s':7.97}],profile_revision='r4',authored_physics_hz=240,
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level,
                checks={name:True for name in REQUIRED['settle']|{'deep_powder_bed','near_full_initial_state','near_full_settled_state'}})
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    for change in [dict(initial_state='preparation_gravity_column'),
                   dict(initial_fill_level=dict(level,median_headspace_m=.030))]:
        with pytest.raises(ValueError):
            validate_report(dict(data,**change),'scene','settle',cfg)

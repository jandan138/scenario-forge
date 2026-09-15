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


def _near_full_settle(revision, hz):
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    cfg = dict(revision=revision,physics_hz=hz,inner_profile=[{}],initial_state='presettled')
    data = dict(status='passed',mode='settle',runtime='4.5.0',requested_runtime='45',
                scene_sha256='scene',entry_sha256='scene',physics_dt=1/hz,solver='PGS',
                position_iterations_override=None,wake_all_override=False,engine_errors=[],
                requested_seconds=8,rows=[{'time_s':7.97}],profile_revision=revision,authored_physics_hz=hz,
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level,
                checks={name:True for name in REQUIRED['settle']|{'deep_powder_bed','near_full_initial_state','near_full_settled_state'}})
    return cfg, data, level


def test_preparation_or_low_initial_bed_cannot_qualify_r4():
    cfg, data, level = _near_full_settle('r4', 240)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    for change in [dict(initial_state='preparation_gravity_column'),
                   dict(initial_fill_level=dict(level,median_headspace_m=.030))]:
        with pytest.raises(ValueError):
            validate_report(dict(data,**change),'scene','settle',cfg)


def test_r5_0_qualifies_at_120hz_pgs_and_rejects_r4_timestep_or_tgs():
    cfg, data, _ = _near_full_settle('r5.0', 120)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,solver='TGS'),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,physics_hz=240))


def test_r5_0_requires_near_full_initial_state_like_r4():
    cfg, data, level = _near_full_settle('r5.0', 120)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    with pytest.raises(ValueError):
        validate_report(dict(data,initial_fill_level=dict(level,median_headspace_m=.030)),'scene','settle',cfg)


def test_r5_1_qualifies_at_120hz_pgs_and_rejects_r4_timestep_or_tgs():
    cfg, data, _ = _near_full_settle('r5.1', 120)
    cfg.update(grain_max_linear_velocity_m_s=0.15,grain_max_depenetration_velocity_m_s=0.2)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,solver='TGS'),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,physics_hz=240))


def test_r5_1_requires_near_full_initial_state_like_r4():
    cfg, data, level = _near_full_settle('r5.1', 120)
    cfg.update(grain_max_linear_velocity_m_s=0.15,grain_max_depenetration_velocity_m_s=0.2)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    with pytest.raises(ValueError):
        validate_report(dict(data,initial_fill_level=dict(level,median_headspace_m=.030)),'scene','settle',cfg)


def test_r5_2_qualifies_at_120hz_pgs_and_rejects_r4_timestep_or_tgs():
    cfg, data, _ = _near_full_settle('r5.2', 120)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,solver='TGS'),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,physics_hz=240))


def test_r5_2_requires_near_full_initial_state_like_r4():
    cfg, data, level = _near_full_settle('r5.2', 120)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    with pytest.raises(ValueError):
        validate_report(dict(data,initial_fill_level=dict(level,median_headspace_m=.030)),'scene','settle',cfg)


def test_r5_3_qualifies_at_120hz_pgs_and_rejects_r4_timestep_or_tgs():
    cfg, data, _ = _near_full_settle('r5.3', 120)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,solver='TGS'),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,physics_hz=240))


def test_r5_3_requires_near_full_initial_state_like_r4():
    cfg, data, level = _near_full_settle('r5.3', 120)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,preparation_only=True))
    with pytest.raises(ValueError):
        validate_report(dict(data,initial_fill_level=dict(level,median_headspace_m=.030)),'scene','settle',cfg)


def test_r5_4_qualifies_at_120hz_pgs_and_rejects_r4_timestep_or_tgs():
    cfg, data, _ = _near_full_settle('r5.4', 120)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,solver='TGS'),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,physics_hz=240))


def test_r5_5_qualifies_at_120hz_pgs_and_rejects_r4_timestep():
    cfg, data, _ = _near_full_settle('r5.5', 120)
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)

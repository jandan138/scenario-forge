import pytest

from scripts.package_task09_powder import COMPACT_REVISIONS, NEAR_FULL_REVISIONS
from scripts.task09_powder_evidence import REQUIRED, validate_report


def report(mode='scoop'):
    seconds = {'scoop':50,'settle':5,'calibration':43}[mode]
    return dict(status='passed',mode=mode,runtime='4.5.0',requested_runtime='45',
                scene_sha256='scene',entry_sha256='scene',physics_dt=1/480,solver='PGS',
                position_iterations_override=None,wake_all_override=False,engine_errors=[],
                requested_seconds=seconds,rows=[{'time_s':seconds-.02}],
                checks={name:True for name in REQUIRED[mode]})


def test_complete_run_is_required_not_just_finite_frozen_positions():
    validate_report(report(),'scene','scoop')
    for field,value in [('engine_errors',['GPU kernel failed']),('checks',{'finite':True}),
                        ('rows',[{'time_s':2.}]),('runtime','4.1.0'),('scene_sha256','stale')]:
        data = report()
        data[field] = value
        with pytest.raises(ValueError):
            validate_report(data,'scene','scoop')


def test_wrong_protocol_or_session_override_cannot_qualify_scene():
    for field,value in [('mode','settle'),('solver','TGS'),('wake_all_override',True),
                        ('position_iterations_override',32),('physics_dt',1/60)]:
        data = report()
        data[field] = value
        with pytest.raises(ValueError):
            validate_report(data,'scene','scoop')


def test_compact_evidence_uses_candidate_timestep_and_requires_measured_bed():
    cfg = {'revision':'r3','physics_hz':240,'inner_profile':[{}]}
    data = report('settle')
    data.update(physics_dt=1/240,authored_physics_hz=240,profile_revision='r3',
                settled_bed={'surface_depth_median_m':.011,'columns':184})
    data['checks']['deep_powder_bed'] = True
    validate_report(data,'scene','settle',cfg)
    for field,value in [('physics_dt',1/480),('profile_revision','r2'),
                        ('settled_bed',{'surface_depth_median_m':.0096,'columns':184})]:
        invalid = dict(data,**{field:value})
        with pytest.raises(ValueError):
            validate_report(invalid,'scene','settle',cfg)
    del data['checks']['deep_powder_bed']
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',cfg)


def test_r5_0_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.0','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled'}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.0',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_0_as_compact_near_full_revision():
    assert 'r5.0' in COMPACT_REVISIONS
    assert 'r4' in NEAR_FULL_REVISIONS
    assert 'r5.0' in NEAR_FULL_REVISIONS


def test_r5_1_compact_evidence_requires_120hz_velocity_caps_not_r4_240hz():
    cfg = {'revision':'r5.1','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_max_linear_velocity_m_s':0.15,'grain_max_depenetration_velocity_m_s':0.2}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.1',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,grain_max_linear_velocity_m_s=1.0))
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,grain_max_depenetration_velocity_m_s=0.05))


def test_packager_treats_r5_1_as_compact_near_full_revision():
    assert 'r5.1' in COMPACT_REVISIONS
    assert 'r5.1' in NEAR_FULL_REVISIONS


def test_r5_2_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.2','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_contact_offset_m':0.00015,'grain_rest_offset_m':0.00005}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.2',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_2_as_compact_near_full_revision():
    assert 'r5.2' in COMPACT_REVISIONS
    assert 'r5.2' in NEAR_FULL_REVISIONS


def test_r5_3_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.3','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_contact_offset_m':0.00025,'grain_rest_offset_m':0.00015,
           'wall_contact_offset_m':0.001,'wall_rest_offset_m':0.0002}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.3',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_3_as_compact_near_full_revision():
    assert 'r5.3' in COMPACT_REVISIONS
    assert 'r5.3' in NEAR_FULL_REVISIONS


def test_r5_4_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.4','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'insert_contact_offset_m':0.003,'insert_rest_offset_m':0.0006}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.4',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_4_as_compact_near_full_revision():
    assert 'r5.4' in COMPACT_REVISIONS
    assert 'r5.4' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_5_as_compact_near_full_revision():
    assert 'r5.5' in COMPACT_REVISIONS
    assert 'r5.5' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_6_as_compact_near_full_revision():
    assert 'r5.6' in COMPACT_REVISIONS
    assert 'r5.6' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_7_as_compact_near_full_revision():
    assert 'r5.7' in COMPACT_REVISIONS
    assert 'r5.7' in NEAR_FULL_REVISIONS

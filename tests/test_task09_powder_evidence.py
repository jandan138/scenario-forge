import pytest

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

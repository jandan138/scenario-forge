"""Native evidence must reject a configured-only or hidden240 qualification."""
import copy
import pytest

from scripts.task10_native120_evidence import CHECKS, validate_reports


def evidence():
    return [{'status':'pass','runtime_requested':v,'runtime_version':['4.'+v[1]+'.0'],
             'pid':int(v),'scope':'full_task_fixture','controller_mode':'graph',
             'physical_containment_qualified':True,
             'cavity_sampling':'every_physics_step_including_sdk_warmup',
             'measurement_readback':'native_post_step; verified_against_after_fetch',
             'physx_errors':[],'input_files_sha256':{'scene.usda':'abc'},
             'validator_sha256':'validator','clock_module_sha256':'clock',
             'physics_dt':1/120,'authored_scene_hz':120,'world_reported_dt':1/120,
             'authored_position_iterations':{'min':64,'max':64},
             'cavity_steps':120,'warmup_native_steps':2,'post_readback_spot_checks':10,
             'cavity_max_outside':{'Source':0,'Receiver':0,'DeadPrecharge':0},
             'step_mode':'world','render_hz':120,
             'actual_step_dt_evidence':{'source':'native_physics_step_callback','count':120,
                 'min_s':1/120,'max_s':1/120,'sum_s':1.,'target_s':1/120,
                 'world_physics_dt_s':1/120,'scene_time_steps_per_second':120},
             'checks':dict.fromkeys(CHECKS,True)} for v in ('41','45')]


def test_native_dual_runtime_evidence():
    rows=evidence()
    validate_reports(rows,{'scene.usda':'abc'},'validator','clock')
    for key,value in [('authored_scene_hz',240),('world_reported_dt',1/60),
                      ('clock_module_sha256','stale'),('cavity_steps',118),
                      ('cavity_max_outside',{'Source':1}),('post_readback_spot_checks',0),
                      ('scope','integration_api_smoke')]:
        changed=copy.deepcopy(rows)
        changed[0][key]=value
        with pytest.raises(ValueError):
            validate_reports(changed,{'scene.usda':'abc'},'validator','clock')
    for key,value in [('min_s',1/240),('max_s',1/60),('sum_s',.5),('count',0),
                      ('source','requested_configuration')]:
        changed=copy.deepcopy(rows)
        changed[0]['actual_step_dt_evidence'][key]=value
        with pytest.raises(ValueError):
            validate_reports(changed,{'scene.usda':'abc'},'validator','clock')


def test_dual_runtime_full_runs_and_separate_play_smokes():
    rows=evidence()
    with pytest.raises(ValueError):
        validate_reports(rows[:1],{'scene.usda':'abc'},'validator','clock')
    for r in rows:
        r.update(scope='integration_api_smoke',step_mode='play',render_hz=60)
    validate_reports(rows,{'scene.usda':'abc'},'validator','clock',full=False,play=True)
    rows[0]['step_mode']='world'
    with pytest.raises(ValueError):
        validate_reports(rows,{'scene.usda':'abc'},'validator','clock',full=False,play=True)

"""Task10 r2 admission: actual native120 clock and complete physical evidence."""
import math

BASE_CHECKS={'closed_no_release','actual_arrival','continuous_delivery_while_open',
             'conservation','set_mass_conservation','no_physx_errors','controller_valid',
             'containment','initial_surface_height','native_120hz','post_step_readback',
             'native_post_count'}
CHECKS=BASE_CHECKS|{'endpoint','reset','overshoot','miss_target','delivery_efficiency'}


def close(value,target):
    return isinstance(value,(int,float)) and math.isfinite(value) and abs(value-target)<=1e-8


def validate_report(row,inputs,validator_sha,clock_sha,*,full=True,play=False):
    required=CHECKS if full else BASE_CHECKS
    version=row.get('runtime_requested')
    if (version not in ('41','45') or row.get('status')!='pass'
            or row.get('scope')!=('full_task_fixture' if full else 'integration_api_smoke')
            or row.get('controller_mode')!='graph'
            or row.get('physical_containment_qualified') is not True
            or row.get('cavity_sampling')!='every_physics_step_including_sdk_warmup'
            or row.get('measurement_readback')!='native_post_step; verified_against_after_fetch'
            or row.get('physx_errors')!=[] or row.get('input_files_sha256')!=inputs
            or row.get('validator_sha256')!=validator_sha or row.get('clock_module_sha256')!=clock_sha
            or not str(row.get('runtime_version',[''])[0]).startswith('4.'+version[1])
            or any(row.get('checks',{}).get(name) is not True for name in required)
            or not all(value is True for value in row.get('checks',{}).values())):
        raise ValueError('Missing, failed, partial or stale native120 runtime evidence')
    clock=row.get('actual_step_dt_evidence',{})
    count=clock.get('count',0)
    outside=row.get('cavity_max_outside',{})
    if (clock.get('source')!='native_physics_step_callback' or count<=0
            or any(not close(clock.get(key),1/120) for key in ('min_s','max_s','target_s','world_physics_dt_s'))
            or not close(clock.get('sum_s'),count/120)
            and not (isinstance(clock.get('sum_s'),(int,float)) and math.isfinite(clock['sum_s'])
                     and abs(clock['sum_s']-count/120)<=count*1e-8)
            or clock.get('scene_time_steps_per_second')!=120
            or row.get('authored_scene_hz')!=120
            or row.get('authored_position_iterations')!={'min':64,'max':64}
            or not close(row.get('physics_dt'),1/120)
            or not close(row.get('world_reported_dt'),1/120)
            or row.get('cavity_steps')!=count or row.get('warmup_native_steps',0)<=0
            or row.get('post_readback_spot_checks',0)<=0
            or set(outside)!={'Source','Receiver','DeadPrecharge'} or any(outside.values())
            or row.get('step_mode')!=('play' if play else 'world')
            or row.get('render_hz')!=(60 if play else 120)):
        raise ValueError('Native120 callback, warmup, readback or clock evidence is inconsistent')


def validate_reports(reports,inputs,validator_sha,clock_sha,*,full=True,play=False):
    if (len(reports)!=2 or {r.get('runtime_requested') for r in reports}!={'41','45'}
            or len({r.get('pid') for r in reports})!=2):
        raise ValueError('Independent cold starts on both runtimes required')
    for row in reports:
        validate_report(row,inputs,validator_sha,clock_sha,full=full,play=play)

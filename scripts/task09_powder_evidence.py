"""Strict evidence selection for the 4.5 original-scene powder handoff."""
import math

COMMON = {'finite','root_bodies','powder_mass','no_engine_errors','no_leak_below_insert','no_below_table'}
REQUIRED = {
    'settle':COMMON|{'retained'},
    'scoop':COMMON|{'tare','transfer','sustained_carry','positive_force','valid_stable','force_region_agreement'},
    'calibration':COMMON|{'known_loads','boat_removed','instrument_reset'},
}
MIN_SECONDS = {'settle':5,'scoop':50,'calibration':43}


def validate_report(report, scene_hash, mode, config=None):
    config = config or {}
    hz = config.get('physics_hz',480)
    compact = 'inner_profile' in config
    required = REQUIRED[mode] | ({'deep_powder_bed'} if compact and mode=='settle' else set())
    if compact:
        bed = report.get('settled_bed',{})
        if (report.get('profile_revision')!=config.get('revision')
                or report.get('authored_physics_hz')!=hz
                or (mode=='settle' and not (.010<=bed.get('surface_depth_median_m',0)<=.012
                                           and bed.get('columns',0)>0))):
            raise ValueError('Incomplete compact-powder profile or settled-depth evidence')
    checks = report.get('checks',{})
    rows = report.get('rows',[])
    seconds = report.get('requested_seconds',0.)
    if (report.get('status')!='passed' or report.get('mode')!=mode
            or not report.get('runtime','').startswith('4.5')
            or report.get('requested_runtime')!='45'
            or report.get('scene_sha256')!=scene_hash or report.get('entry_sha256')!=scene_hash
            or report.get('engine_errors')!=[] or not required.issubset(checks)
            or any(value is not True for value in checks.values())
            or report.get('solver')!='PGS' or report.get('position_iterations_override') is not None
            or report.get('wake_all_override') is not False
            or not math.isclose(report.get('physics_dt',0),1/hz,rel_tol=0,abs_tol=1e-9)
            or not math.isfinite(seconds) or seconds<MIN_SECONDS[mode]
            or not rows or rows[-1].get('time_s',0)<seconds-1/30-1/hz):
        raise ValueError('Incomplete, stale, overridden or unhealthy '+mode+' evidence')

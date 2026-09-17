"""Strict evidence selection for the 4.5 original-scene powder handoff."""
import math

COMMON = {'finite','root_bodies','powder_mass','no_engine_errors','no_leak_below_insert','no_below_table'}
REQUIRED = {
    'settle':COMMON|{'retained'},
    'scoop':COMMON|{'tare','transfer','sustained_carry','positive_force','valid_stable','force_region_agreement'},
    'calibration':COMMON|{'known_loads','boat_removed','instrument_reset'},
}
MIN_SECONDS = {'settle':5,'scoop':50,'calibration':43}
NEAR_FULL_REVISIONS = ('r4','r5.0','r5.1','r5.2','r5.3','r5.4','r5.5','r5.6','r5.7','r5.8','r5.9','r5.10','r6.0')
PBD_REVISIONS = ('r6.0',)
R60_SOLID_REST_OFFSET_M = 0.00104
R60_PARTICLE_CONTACT_OFFSET_M = 0.00114
R60_RIGID_REST_OFFSET_M = 0.0007
R60_RIGID_CONTACT_OFFSET_M = 0.00072
R60_GRAVITY_SCALE = 1.0
R60_VISUAL_RADIUS_M = 0.0007
R60_FLUID_REST_OFFSET_M = 0.00052
R51_LINEAR_VELOCITY = 0.15
R51_DEPENETRATION_VELOCITY = 0.2
R58_LINEAR_DAMPING = 1.0
R59_SLEEP_THRESHOLD = 5e-5
R59_STABILIZATION_THRESHOLD = 1e-5
R510_KINEMATIC_FROM_S = 0.5
R510_KINEMATIC_UNTIL_S = 18.0
REST_SPEED_MEDIAN_MAX_M_S = 0.0015
REST_DRIFT_MEDIAN_MAX_M = 0.0013


def authored_velocity_cap_matches(linear, depen):
    if linear is None or depen is None:
        return False
    return (math.isclose(float(linear), R51_LINEAR_VELOCITY, rel_tol=0, abs_tol=1e-5)
            and math.isclose(float(depen), R51_DEPENETRATION_VELOCITY, rel_tol=0, abs_tol=1e-5))


def authored_linear_damping_matches(damping):
    if damping is None:
        return False
    return math.isclose(float(damping), R58_LINEAR_DAMPING, rel_tol=0, abs_tol=1e-5)


def authored_pbd_dry_powder_matches(config):
    if config.get('powder_kind') != 'pbd_solid' or config.get('pbd_fluid') is not False:
        return False
    solid_rest = float(config.get('pbd_solid_rest_offset_m', -1))
    contact = float(config.get('pbd_particle_contact_offset_m', -1))
    rigid_rest = float(config.get('pbd_rigid_rest_offset_m', -1))
    rigid_contact = float(config.get('pbd_rigid_contact_offset_m', -1))
    return 0 < solid_rest < contact and 0 < rigid_rest < rigid_contact


def authored_pbd_viscous_particles_matches(config):
    if config.get('powder_kind') != 'pbd_viscous' or config.get('pbd_fluid') is not True:
        return False
    if config.get('pbd_display') != 'particles':
        return False
    fluid_rest = float(config.get('pbd_fluid_rest_offset_m', -1))
    contact = float(config.get('pbd_particle_contact_offset_m', -1))
    rigid_rest = float(config.get('pbd_rigid_rest_offset_m', -1))
    rigid_contact = float(config.get('pbd_rigid_contact_offset_m', -1))
    return (
        0 < fluid_rest < contact
        and 0 < rigid_rest < rigid_contact
        and float(config.get('pbd_solid_rest_offset_m', -1)) > 0
    )


def authored_sleep_matches(sleep_threshold, stabilization_threshold):
    if sleep_threshold is None or stabilization_threshold is None:
        return False
    return (
        math.isclose(float(sleep_threshold), R59_SLEEP_THRESHOLD, rel_tol=0, abs_tol=1e-8)
        and math.isclose(float(stabilization_threshold), R59_STABILIZATION_THRESHOLD, rel_tol=0, abs_tol=1e-8)
    )


def summarize_rest_motion(positions, times, t_end=15.0):
    import numpy as np
    times = np.asarray(times, dtype=np.float64)
    positions = np.asarray(positions)
    mask = times <= t_end + 1e-9
    t = times[mask]
    x = positions[mask]
    if len(t) < 2:
        raise ValueError('rest motion needs at least two samples')
    step = np.linalg.norm(np.diff(x, axis=0), axis=2)
    speed = step / np.diff(t)[:, None]
    drift = np.linalg.norm(x[-1] - x[0], axis=1)
    median_speed = float(np.median(speed))
    median_drift = float(np.median(drift))
    return {
        't_end_s': float(t[-1]),
        'n_frames': int(len(t)),
        'median_speed_m_s': median_speed,
        'p90_speed_m_s': float(np.percentile(speed, 90)),
        'median_drift_m': median_drift,
        'p90_drift_m': float(np.percentile(drift, 90)),
        'meets_r4_rest_gate': (
            median_speed <= REST_SPEED_MEDIAN_MAX_M_S
            and median_drift <= REST_DRIFT_MEDIAN_MAX_M
        ),
    }


def validate_report(report, scene_hash, mode, config=None):
    config = config or {}
    hz = config.get('physics_hz',480)
    compact = 'inner_profile' in config
    required = REQUIRED[mode] | ({'deep_powder_bed'} if compact and mode=='settle' else set())
    if config.get('revision') in PBD_REVISIONS and mode=='scoop':
        required -= {'force_region_agreement','positive_force'}
    if config.get('revision')=='r5.1' and (
            config.get('grain_max_linear_velocity_m_s')!=R51_LINEAR_VELOCITY
            or config.get('grain_max_depenetration_velocity_m_s')!=R51_DEPENETRATION_VELOCITY):
        raise ValueError('r5.1 requires grain maxLinearVelocity 0.15 and maxDepenetrationVelocity 0.2')
    if config.get('revision')=='r5.8' and config.get('grain_linear_damping')!=R58_LINEAR_DAMPING:
        raise ValueError('r5.8 requires grain linearDamping 1.0')
    if config.get('revision')=='r5.9' and (
            config.get('grain_sleep_threshold')!=R59_SLEEP_THRESHOLD
            or config.get('grain_stabilization_threshold')!=R59_STABILIZATION_THRESHOLD):
        raise ValueError('r5.9 requires grain sleepThreshold 5e-5 and stabilizationThreshold 1e-5')
    if config.get('revision')=='r5.10' and (
            config.get('grain_rest_kinematic_from_s')!=R510_KINEMATIC_FROM_S
            or config.get('grain_rest_kinematic_until_s')!=R510_KINEMATIC_UNTIL_S):
        raise ValueError('r5.10 requires grain rest kinematic hold from 0.5 s until 18 s')
    if config.get('revision') in PBD_REVISIONS:
        if config.get('pbd_fluid'):
            if not authored_pbd_viscous_particles_matches(config):
                raise ValueError('r6.x viscous-particle trial needs pbd_viscous, fluid=true, particle display, and authored rest offsets')
        elif not authored_pbd_dry_powder_matches(config):
            raise ValueError('r6.x requires dry PBD powder_kind and authored solid/rigid rest offsets')
    if config.get('revision') in NEAR_FULL_REVISIONS:
        from scripts.compact_powder_protocol import near_full_check
        required |= {'near_full_initial_state'}
        if (config.get('preparation_only') or config.get('initial_state')!='presettled' or report.get('initial_state')!='presettled'
                or not near_full_check(report.get('initial_fill_level',{}))):
            raise ValueError('near-full revision requires a verified near-full initial state')
        if mode=='settle':
            required |= {'near_full_settled_state'}
            if not near_full_check(report.get('settled_fill_level',{})):
                raise ValueError('near-full revision must remain near-full after cold-start settlement')
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

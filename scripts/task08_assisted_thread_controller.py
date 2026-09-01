"""USD-embedded Task08 one-turn assisted-thread controller.

The file is read as text by the r13 generator.  It is not imported by the
generated package at runtime.
"""

import math

import omni.usd
from omni.isaac.dynamic_control import _dynamic_control


TUBE_PATH = "/World/obj_tube_01"
CAP_PATH = "/World/obj_cap_01"
CONTRACT_PATH = "/World/TaskRuntime/AssistedThreadContract"
LOCK_PATH = "/World/TaskRuntime/ClosedLock"
CLOSED_Z_M = 0.1074
TRAVEL_M = 0.0076
CLOSE_ANGLE_DEG = 350.0
FULL_TURN_DEG = 360.0
CAPTURE_RADIAL_M = 0.006
CAPTURE_TILT_DEG = 20.0
CAPTURE_Z_MIN_M = CLOSED_Z_M - 0.002
CAPTURE_Z_MAX_M = CLOSED_Z_M + TRAVEL_M + 0.004
ABORT_RADIAL_M = 0.012
ABORT_TILT_DEG = 35.0


def _q_conjugate(q):
    return (q[0], -q[1], -q[2], -q[3])


def _q_multiply(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def _q_normalize(q):
    length = math.sqrt(sum(value * value for value in q))
    if length < 1.0e-12:
        return (1.0, 0.0, 0.0, 0.0)
    return tuple(value / length for value in q)


def _q_rotate(q, vector):
    rotated = _q_multiply(
        _q_multiply(q, (0.0, vector[0], vector[1], vector[2])),
        _q_conjugate(q),
    )
    return (rotated[1], rotated[2], rotated[3])


def _q_yaw(degrees):
    half = math.radians(degrees) * 0.5
    return (math.cos(half), 0.0, 0.0, math.sin(half))


def _yaw_degrees(q):
    q = _q_normalize(q)
    return math.degrees(
        math.atan2(
            2.0 * (q[0] * q[3] + q[1] * q[2]),
            1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3]),
        )
    )


def _wrap_degrees(value):
    return (value + 180.0) % 360.0 - 180.0


def _stage():
    return omni.usd.get_context().get_stage()


def _set(stage, name, value):
    attr = stage.GetPrimAtPath(CONTRACT_PATH).GetAttribute(name)
    if attr and attr.Get() != value:
        attr.Set(value)


def _pose(dc, path):
    handle = dc.get_rigid_body(path)
    if handle == _dynamic_control.INVALID_HANDLE:
        return None
    pose = dc.get_rigid_body_pose(handle)
    return (
        handle,
        (float(pose.p.x), float(pose.p.y), float(pose.p.z)),
        (float(pose.r.w), float(pose.r.x), float(pose.r.y), float(pose.r.z)),
    )


def _relative_pose(tube, cap):
    delta_world = tuple(cap[1][index] - tube[1][index] for index in range(3))
    tube_inverse = _q_conjugate(tube[2])
    local_position = _q_rotate(tube_inverse, delta_world)
    local_rotation = _q_normalize(_q_multiply(tube_inverse, cap[2]))
    axis = _q_rotate(local_rotation, (0.0, 0.0, 1.0))
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, axis[2]))))
    radial = math.hypot(local_position[0], local_position[1])
    return local_position, local_rotation, radial, tilt


def _world_target(tube, local_z, relative_yaw):
    delta = _q_rotate(tube[2], (0.0, 0.0, local_z))
    position = tuple(tube[1][index] + delta[index] for index in range(3))
    rotation = _q_normalize(_q_multiply(tube[2], _q_yaw(relative_yaw)))
    return position, rotation


def _set_cap_pose(dc, handle, position, rotation):
    dc.set_rigid_body_pose(
        handle,
        _dynamic_control.Transform(
            position,
            (rotation[1], rotation[2], rotation[3], rotation[0]),
        ),
    )


def _enable_closed_lock(stage, relative_yaw):
    lock = stage.GetPrimAtPath(LOCK_PATH)
    lock.GetAttribute("assistedThread:active").Set(True)
    lock.GetAttribute("assistedThread:relativeYawDegrees").Set(float(relative_yaw))


def _reset_state(stage, state):
    lock = stage.GetPrimAtPath(LOCK_PATH).GetAttribute("assistedThread:active")
    if lock:
        lock.Set(False)
    state.mode = "free"
    state.accumulated = 0.0
    state.last_yaw = None
    state.closed_yaw = None
    _set(stage, "assistedThread:state", "free")
    _set(stage, "assistedThread:progress", 0.0)
    _set(stage, "assistedThread:accumulatedClockwiseDegrees", 0.0)


def setup(db):
    state = db.per_instance_state
    state.dc = _dynamic_control.acquire_dynamic_control_interface()
    state.initialized = False


def compute(db):
    stage = _stage()
    if stage is None:
        return False
    state = db.per_instance_state
    if not state.initialized:
        _reset_state(stage, state)
        state.initialized = True
    tube = _pose(state.dc, TUBE_PATH)
    cap = _pose(state.dc, CAP_PATH)
    if tube is None or cap is None:
        return True
    local_position, local_rotation, radial, tilt = _relative_pose(tube, cap)
    yaw = _yaw_degrees(local_rotation)
    _set(stage, "assistedThread:rawRadialErrorM", float(radial))
    _set(stage, "assistedThread:rawTiltErrorDegrees", float(tilt))
    _set(stage, "assistedThread:rawRelativeZM", float(local_position[2]))

    if state.mode == "free":
        eligible = (
            radial <= CAPTURE_RADIAL_M
            and tilt <= CAPTURE_TILT_DEG
            and CAPTURE_Z_MIN_M <= local_position[2] <= CAPTURE_Z_MAX_M
        )
        if eligible:
            state.mode = "capture"
            state.last_yaw = yaw
            state.accumulated = 0.0
            _set(stage, "assistedThread:state", "capture")
        return True

    if state.mode == "capture":
        state.mode = "engaged"
        state.last_yaw = yaw
        _set(stage, "assistedThread:state", "engaged")

    if state.mode == "engaged":
        if radial > ABORT_RADIAL_M or tilt > ABORT_TILT_DEG:
            _reset_state(stage, state)
            return True
        delta = _wrap_degrees(yaw - state.last_yaw)
        state.last_yaw = yaw
        if abs(delta) <= 30.0:
            state.accumulated = max(
                0.0, min(FULL_TURN_DEG, state.accumulated - delta)
            )
        progress = min(1.0, state.accumulated / FULL_TURN_DEG)
        target_z = CLOSED_Z_M + TRAVEL_M * (1.0 - progress)
        target_position, target_rotation = _world_target(tube, target_z, yaw)
        correction = math.sqrt(
            sum((target_position[index] - cap[1][index]) ** 2 for index in range(3))
        )
        _set_cap_pose(state.dc, cap[0], target_position, target_rotation)
        _set(stage, "assistedThread:progress", float(progress))
        _set(
            stage,
            "assistedThread:accumulatedClockwiseDegrees",
            float(state.accumulated),
        )
        _set(stage, "assistedThread:targetRelativeZM", float(target_z))
        _set(stage, "assistedThread:lastCorrectionM", float(correction))
        if state.accumulated >= CLOSE_ANGLE_DEG:
            state.mode = "closed"
            state.closed_yaw = yaw
            target_position, target_rotation = _world_target(
                tube, CLOSED_Z_M, state.closed_yaw
            )
            _set_cap_pose(state.dc, cap[0], target_position, target_rotation)
            _enable_closed_lock(stage, state.closed_yaw)
            _set(stage, "assistedThread:state", "closed")
            _set(stage, "assistedThread:progress", 1.0)
            _set(stage, "assistedThread:targetRelativeZM", CLOSED_Z_M)
            _set(stage, "assistedThread:closed", True)
        return True

    if state.mode == "closed":
        target_position, target_rotation = _world_target(
            tube, CLOSED_Z_M, state.closed_yaw
        )
        _set_cap_pose(state.dc, cap[0], target_position, target_rotation)
        _set(stage, "assistedThread:closed", True)
        return True
    return True


def cleanup(db):
    db.per_instance_state.initialized = False
    db.per_instance_state.dc = None

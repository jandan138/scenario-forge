"""Appended to fehlings_state.py and embedded in the ScriptNode."""
# ruff: noqa: F821
import omni.usd
from omni.isaac.dynamic_control import _dynamic_control
from pxr import Gf, UsdGeom

_state = initial_state()
_handle = None


def setup(db):
    global _state, _handle
    _state, _handle = initial_state(), None


def cleanup(db):
    global _state, _handle
    _state, _handle = initial_state(), None


def compute(db):
    global _state, _handle
    stage = omni.usd.get_context().get_stage()
    tube_path = str(db.node.get_prim_path()).split('/ReactionRuntime/')[0]
    tube = stage.GetPrimAtPath(tube_path)
    def get(name):
        return tube.GetAttribute('fehlings:'+name).Get()
    def put(name, value):
        tube.GetAttribute('fehlings:'+name).Set(value)
    if get('reset_requested'):
        _state = initial_state()
        put('reset_requested', False)
    dc = _dynamic_control.acquire_dynamic_control_interface()
    _handle = dc.get_rigid_body(tube_path)
    if not _handle:
        put('pose_available', False)
        return True
    pose = dc.get_rigid_body_pose(_handle)
    xyz = (float(pose.p.x), float(pose.p.y), float(pose.p.z))
    rotation = Gf.Rotation(Gf.Quatd(float(pose.r.w), Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z)))
    axis = rotation.TransformDir(Gf.Vec3d(0,0,1))
    spec = {name:get(name) for name in ('water_surface_z','bath_center_xyz','bath_inner_radius',
            'outer_radius_m','sample_height_m','mouth_height_m','bath_inner_floor_z')}
    immersed, withdrawn = geometry_flags(xyz, axis, spec)
    _state = advance(_state, max(0.0,float(db.inputs.deltaSeconds)), immersed, withdrawn, xyz)
    look = appearance(_state['heated_s'])
    for name,value in [('pose_available',True), ('immersed',immersed), ('heated_seconds',_state['heated_s']),
                       ('color_progress',look['progress']), ('observation_seconds',_state['observe_s']),
                       ('stage',_state['stage']), ('success',_state['success'])]:
        put(name,value)
    shader = stage.GetPrimAtPath(tube_path+'/VisualLiquid/Looks/Sample/Shader')
    shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*look['color']))
    shader.GetAttribute('inputs:opacity').Set(look['opacity'])
    sediment = stage.GetPrimAtPath(tube_path+'/VisualLiquid/Sediment')
    UsdGeom.Imageable(sediment).GetVisibilityAttr().Set('inherited' if look['sediment'] > 0 else 'invisible')
    shader = stage.GetPrimAtPath(tube_path+'/VisualLiquid/Looks/Sediment/Shader')
    shader.GetAttribute('inputs:opacity').Set(look['sediment'])
    return True

"""Embedded USD bridge for the r2 pure visual policy and geometry."""
# ruff: noqa: F821
import omni.usd
from omni.isaac.dynamic_control import _dynamic_control
from pxr import Gf, UsdGeom

_state=initial_state()
_last_geometry_progress=None


def setup(db):
    global _state,_last_geometry_progress
    _state,_last_geometry_progress=initial_state(),None


def cleanup(db):
    global _state,_last_geometry_progress
    _state,_last_geometry_progress=initial_state(),None


def _target(stage,tube,name):
    paths=tube.GetRelationship('fehlings:'+name).GetTargets()
    if len(paths)!=1:
        raise RuntimeError('expected one target for '+name)
    prim=stage.GetPrimAtPath(paths[0])
    if not prim:
        raise RuntimeError('missing reaction target '+name)
    return prim


def _apply_state(stage,tube):
    global _last_geometry_progress
    look=appearance(_state['heated_s'])
    for name,value in [('heated_seconds',_state['heated_s']),('color_progress',look['progress']),
                       ('observation_seconds',_state['observe_s']),('stage',_state['stage']),
                       ('success',_state['success']),('reaction_stage',look['reaction_stage']),
                       ('sediment_progress',look['sediment'])]:
        tube.GetAttribute('fehlings:'+name).Set(value)
    shader=_target(stage,tube,'sampleShader')
    shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*look['color']))
    shader.GetAttribute('inputs:opacity').Set(look['opacity'])
    _target(stage,tube,'sedimentShader').GetAttribute('inputs:opacity').Set(look['sediment_opacity'])
    for part in ('Body','Surface'):
        prim=_target(stage,tube,'sediment'+part)
        UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if look['sediment']>0 else 'invisible')
    if _last_geometry_progress!=look['sediment']:
        profile=[tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
        result=geometry(profile,float(tube.GetAttribute('fehlings:sample_height_m').Get()),look['sediment'])
        for label in ('Sample','Sediment'):
            for part in ('body','surface'):
                mesh=_target(stage,tube,label.lower()+part.capitalize())
                points=result[label][part]
                mesh.GetAttribute('points').Set([Gf.Vec3f(*v) for v in points])
                mesh.GetAttribute('extent').Set([Gf.Vec3f(*[min(v[i] for v in points) for i in range(3)]),
                                                Gf.Vec3f(*[max(v[i] for v in points) for i in range(3)])])
        tube.GetAttribute('fehlings:sediment_height_m').Set(result['sediment_height_m'])
        _last_geometry_progress=look['sediment']


def compute(db):
    global _state,_last_geometry_progress
    stage=omni.usd.get_context().get_stage()
    if stage is None:
        return True
    tube_path=str(db.node.get_prim_path()).split('/ReactionRuntime/')[0]
    tube=stage.GetPrimAtPath(tube_path)
    if not tube:
        return True
    def get(name):
        return tube.GetAttribute('fehlings:'+name).Get()
    def put(name,value):
        tube.GetAttribute('fehlings:'+name).Set(value)
    if get('reset_requested'):
        _state,_last_geometry_progress=initial_state(),None
        put('reset_requested',False)
        put('immersed',False)
        _apply_state(stage,tube)
        return True
    dc=_dynamic_control.acquire_dynamic_control_interface()
    handle=dc.get_rigid_body(tube_path)
    if not handle:
        put('pose_available',False)
        put('immersed',False)
        return True
    pose=dc.get_rigid_body_pose(handle)
    xyz=(float(pose.p.x),float(pose.p.y),float(pose.p.z))
    rotation=Gf.Rotation(Gf.Quatd(float(pose.r.w),Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z)))
    axis=rotation.TransformDir(Gf.Vec3d(0,0,1))
    spec={name:get(name) for name in ('water_surface_z','bath_center_xyz','bath_inner_radius',
          'outer_radius_m','sample_height_m','mouth_height_m','bath_inner_floor_z')}
    immersed,withdrawn=geometry_flags(xyz,axis,spec)
    _state=advance(_state,max(0.0,float(db.inputs.deltaSeconds)),immersed,withdrawn,xyz)
    put('pose_available',True)
    put('immersed',immersed)
    _apply_state(stage,tube)
    return True

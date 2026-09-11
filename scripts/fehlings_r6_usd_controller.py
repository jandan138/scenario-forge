"""Embedded five-material writer. Contact/pose compute comes from the r5 source."""
# ruff: noqa: F821
import omni.usd  # noqa: F401 — used by source compute
from omni.isaac.dynamic_control import _dynamic_control  # noqa: F401
from pxr import Gf

_state = initial_state()


def setup(db):
    global _state
    _state = initial_state()


def cleanup(db):
    global _state
    _state = initial_state()


def _target(stage, tube, name):
    paths = tube.GetRelationship('fehlings:'+name).GetTargets()
    if len(paths) != 1:
        raise RuntimeError('expected one target for '+name)
    prim = stage.GetPrimAtPath(paths[0])
    if not prim:
        raise RuntimeError('missing target '+name)
    return prim


def _apply_state(stage, tube):
    look = appearance(_state['heated_s'])
    for name,value in [('heated_seconds',_state['heated_s']), ('color_progress',look['progress']),
                       ('observation_seconds',_state['observe_s']), ('stage',_state['stage']),
                       ('success',_state['success']), ('reaction_stage',look['reaction_stage']),
                       ('layer_progress',[v['progress'] for v in look['layers']])]:
        tube.GetAttribute('fehlings:'+name).Set(value)
    paths = tube.GetRelationship('fehlings:layerShaders').GetTargets()
    if len(paths) != LAYER_COUNT:
        raise RuntimeError('expected five bottom-to-top layer shaders')
    for path,layer in zip(paths,look['layers']):
        shader = stage.GetPrimAtPath(path)
        if not shader:
            raise RuntimeError('missing layer shader '+str(path))
        shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*layer['color']))
        shader.GetAttribute('inputs:opacity').Set(layer['opacity'])
        shader.GetAttribute('inputs:roughness').Set(layer['roughness'])

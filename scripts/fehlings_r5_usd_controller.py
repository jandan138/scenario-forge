"""Embedded material-only writer; fixed geometry is authored once by the generator."""
# ruff: noqa: F821
import omni.usd  # noqa: F401 — consumed by the embedded r3 compute function
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
    paths = tube.GetRelationship('fehlings:' + name).GetTargets()
    if len(paths) != 1:
        raise RuntimeError('expected one target for ' + name)
    prim = stage.GetPrimAtPath(paths[0])
    if not prim:
        raise RuntimeError('missing reaction target ' + name)
    return prim


def _apply_state(stage, tube):
    look = appearance(_state['heated_s'])
    for name, value in [('heated_seconds', _state['heated_s']), ('color_progress', look['progress']),
                        ('observation_seconds', _state['observe_s']), ('stage', _state['stage']),
                        ('success', _state['success']), ('reaction_stage', look['reaction_stage']),
                        ('sediment_progress', look['sediment'])]:
        tube.GetAttribute('fehlings:' + name).Set(value)
    for relationship, prefix in [('sampleShader', ''), ('sedimentShader', 'sediment_')]:
        shader = _target(stage, tube, relationship)
        shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*look[prefix + 'color']))
        shader.GetAttribute('inputs:opacity').Set(look[prefix + 'opacity'])
        shader.GetAttribute('inputs:roughness').Set(look[prefix + 'roughness'])

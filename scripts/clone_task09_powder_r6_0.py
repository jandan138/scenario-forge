"""Clone r5.7 and replace rigid ico grains with a dry GPU-PBD particle set.

Does not flip current_task_heads. Measurement still uses region count × mass;
the rigid pan contact channel is not the r6.0 gate.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clone_task09_powder_r5_0 import SKIP
from scripts.task09_powder_evidence import (
    R60_FLUID_REST_OFFSET_M,
    R60_PARTICLE_CONTACT_OFFSET_M,
    R60_RIGID_CONTACT_OFFSET_M,
    R60_RIGID_REST_OFFSET_M,
    R60_SOLID_REST_OFFSET_M,
    R60_VISUAL_RADIUS_M,
    R60_GRAVITY_SCALE,
)

PARTICLE_SYSTEM = '/World/powder_pbd/ParticleSystem'
PARTICLE_SET = '/World/powder_pbd/ParticleSet'
PBD_MATERIAL = '/World/powder_pbd/PBDMaterial'
DISPLAY_COLOR = Gf.Vec3f(0.91, 0.82, 0.45)
VISUAL_WIDTH_M = 0.0014
MAX_VELOCITY = 0.06
MAX_DEPENETRATION = 0.08
FRICTION = 0.65
DAMPING = 0.4


def patch_scene_config(cfg):
    cfg = dict(cfg)
    paths = dict(cfg.get('paths') or {})
    paths['powder_pbd'] = PARTICLE_SET
    cfg['paths'] = paths
    cfg['physics_hz'] = 120
    cfg['revision'] = 'r6.0'
    cfg['status'] = 'candidate'
    cfg['powder_kind'] = 'pbd_solid'
    cfg['pbd_fluid'] = False
    cfg['pbd_solid_rest_offset_m'] = R60_SOLID_REST_OFFSET_M
    cfg['pbd_particle_contact_offset_m'] = R60_PARTICLE_CONTACT_OFFSET_M
    cfg['pbd_rigid_rest_offset_m'] = R60_RIGID_REST_OFFSET_M
    cfg['pbd_rigid_contact_offset_m'] = R60_RIGID_CONTACT_OFFSET_M
    cfg['pbd_max_velocity_m_s'] = MAX_VELOCITY
    cfg['pbd_damping'] = DAMPING
    cfg['pbd_friction'] = FRICTION
    cfg['pbd_gravity_scale'] = R60_GRAVITY_SCALE
    cfg['grain_bound_m'] = R60_VISUAL_RADIUS_M
    cfg['grain_radius_m'] = R60_VISUAL_RADIUS_M
    cfg.pop('qualified_runtime', None)
    return cfg


def read_pbd_particle_xyz(prim):
    """Prefer live PhysX simulationPoints; fall back to authored display points."""
    import numpy as np
    live = prim.GetAttribute('physxParticle:simulationPoints').Get()
    if live:
        xyz = np.asarray(live, dtype=np.float64).reshape(-1, 3)
        if len(xyz):
            return xyz
    points = UsdGeom.Points(prim).GetPointsAttr().Get()
    if not points:
        return np.zeros((0, 3), dtype=np.float64)
    return np.asarray(points, dtype=np.float64).reshape(-1, 3)


def set_pbd_particle_xyz(scene, xyz, mass_per_particle, visual_width_m=None):
    """Replace authored PBD points without changing material or rest offsets."""
    import numpy as np
    pts = np.asarray(xyz, dtype=np.float64).reshape(-1, 3)
    if len(pts) == 0:
        raise ValueError('PBD point set is empty')
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    particle_set = stage.GetPrimAtPath(PARTICLE_SET)
    if not particle_set:
        raise ValueError('Missing '+PARTICLE_SET)
    points = UsdGeom.Points(particle_set)
    world = [Gf.Vec3f(float(p[0]), float(p[1]), float(p[2])) for p in pts]
    points.GetPointsAttr().Set(Vt.Vec3fArray(world))
    points.GetVelocitiesAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.0)] * len(world)))
    width_attr = points.GetWidthsAttr()
    current = width_attr.Get()
    width = float(visual_width_m) if visual_width_m is not None else (
        float(current[0]) if current else VISUAL_WIDTH_M)
    width_attr.Set(Vt.FloatArray([width] * len(world)))
    UsdPhysics.MassAPI.Apply(particle_set).CreateMassAttr(float(len(world)) * float(mass_per_particle))
    stage.GetRootLayer().Save()
    return len(world)


def _schema_attr(prim, name, type_name, value):
    attr = prim.CreateAttribute(name, type_name, custom=False)
    attr.Set(value)
    return attr


def _prepend_api_schemas(prim, names):
    existing = []
    current = prim.GetMetadata('apiSchemas')
    if current is not None:
        existing = list(current.prependedItems) + list(current.explicitItems)
    merged = list(names) + [name for name in existing if name not in names]
    prim.SetMetadata('apiSchemas', Sdf.TokenListOp.Create(prependedItems=merged))


def replace_grains_with_pbd(scene, mass_per_particle):
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    grain_paths = []
    positions = []
    for prim in stage.GetPrimAtPath('/World').GetChildren():
        if prim.GetName().startswith('obj_powder_grain_'):
            grain_paths.append(prim.GetPath())
            translate = cache.GetLocalToWorldTransform(prim).ExtractTranslation()
            positions.append(Gf.Vec3f(float(translate[0]), float(translate[1]), float(translate[2])))
    if not positions:
        raise ValueError('No obj_powder_grain_* prims to convert')
    for path in grain_paths:
        stage.RemovePrim(path)
    UsdGeom.Xform.Define(stage, '/World/powder_pbd')
    system = stage.DefinePrim(PARTICLE_SYSTEM, 'PhysxParticleSystem')
    _schema_attr(system, 'particleSystemEnabled', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(system, 'solidRestOffset', Sdf.ValueTypeNames.Float, R60_SOLID_REST_OFFSET_M)
    _schema_attr(system, 'particleContactOffset', Sdf.ValueTypeNames.Float, R60_PARTICLE_CONTACT_OFFSET_M)
    _schema_attr(system, 'fluidRestOffset', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(system, 'restOffset', Sdf.ValueTypeNames.Float, R60_RIGID_REST_OFFSET_M)
    _schema_attr(system, 'contactOffset', Sdf.ValueTypeNames.Float, R60_RIGID_CONTACT_OFFSET_M)
    _schema_attr(system, 'enableCCD', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(system, 'globalSelfCollisionEnabled', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(system, 'nonParticleCollisionEnabled', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(system, 'maxVelocity', Sdf.ValueTypeNames.Float, MAX_VELOCITY)
    _schema_attr(system, 'maxDepenetrationVelocity', Sdf.ValueTypeNames.Float, MAX_DEPENETRATION)
    _schema_attr(system, 'solverPositionIterationCount', Sdf.ValueTypeNames.Int, 16)
    if stage.GetPrimAtPath('/World/PhysicsScene'):
        system.CreateRelationship('simulationOwner', custom=False).SetTargets(['/World/PhysicsScene'])
    material = UsdShade.Material.Define(stage, PBD_MATERIAL)
    mat_prim = material.GetPrim()
    _prepend_api_schemas(mat_prim, ['PhysxPBDMaterialAPI'])
    _schema_attr(mat_prim, 'physxPBDMaterial:friction', Sdf.ValueTypeNames.Float, FRICTION)
    _schema_attr(mat_prim, 'physxPBDMaterial:particleFrictionScale', Sdf.ValueTypeNames.Float, 1.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:damping', Sdf.ValueTypeNames.Float, DAMPING)
    _schema_attr(mat_prim, 'physxPBDMaterial:adhesion', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:particleAdhesionScale', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:adhesionOffsetScale', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:cohesion', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:viscosity', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:surfaceTension', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(mat_prim, 'physxPBDMaterial:gravityScale', Sdf.ValueTypeNames.Float, R60_GRAVITY_SCALE)
    UsdShade.MaterialBindingAPI.Apply(system).Bind(material)
    points = UsdGeom.Points.Define(stage, PARTICLE_SET)
    points.GetPointsAttr().Set(Vt.Vec3fArray(positions))
    points.GetVelocitiesAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.0)] * len(positions)))
    points.GetWidthsAttr().Set(Vt.FloatArray([VISUAL_WIDTH_M] * len(positions)))
    points.GetDisplayColorAttr().Set(Vt.Vec3fArray([DISPLAY_COLOR]))
    set_prim = points.GetPrim()
    UsdPhysics.MassAPI.Apply(set_prim).CreateMassAttr(float(len(positions)) * float(mass_per_particle))
    _prepend_api_schemas(set_prim, ['PhysxParticleSetAPI', 'PhysxParticleAPI'])
    _schema_attr(set_prim, 'physxParticle:fluid', Sdf.ValueTypeNames.Bool, False)
    _schema_attr(set_prim, 'physxParticle:selfCollision', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(set_prim, 'physxParticle:particleEnabled', Sdf.ValueTypeNames.Bool, True)
    _schema_attr(set_prim, 'physxParticle:particleGroup', Sdf.ValueTypeNames.Int, 0)
    set_prim.CreateRelationship('physxParticle:particleSystem', custom=False).SetTargets([PARTICLE_SYSTEM])
    stage.GetRootLayer().Save()
    return len(positions)


def apply_pbd_motion_caps(scene, damping=None, max_velocity=None, friction=None, cohesion=None,
                         particle_friction_scale=None, adhesion=None, particle_adhesion_scale=None,
                         adhesion_offset_scale=None, solver_position_iterations=None, viscosity=None):
    """Tighten PBD fly-off without changing rest/contact offsets."""
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    system = stage.GetPrimAtPath(PARTICLE_SYSTEM)
    material = stage.GetPrimAtPath(PBD_MATERIAL)
    if not system or not material:
        raise ValueError('Missing PBD system or material in '+str(scene))
    if max_velocity is not None:
        system.GetAttribute('maxVelocity').Set(float(max_velocity))
    if solver_position_iterations is not None:
        system.GetAttribute('solverPositionIterationCount').Set(int(solver_position_iterations))
    if damping is not None:
        material.GetAttribute('physxPBDMaterial:damping').Set(float(damping))
    if viscosity is not None:
        visc = material.GetAttribute('physxPBDMaterial:viscosity')
        if not visc:
            visc = _schema_attr(material, 'physxPBDMaterial:viscosity', Sdf.ValueTypeNames.Float, float(viscosity))
        else:
            visc.Set(float(viscosity))
    if friction is not None:
        material.GetAttribute('physxPBDMaterial:friction').Set(float(friction))
    if cohesion is not None:
        material.GetAttribute('physxPBDMaterial:cohesion').Set(float(cohesion))
    if particle_friction_scale is not None:
        material.GetAttribute('physxPBDMaterial:particleFrictionScale').Set(float(particle_friction_scale))
    if adhesion is not None:
        material.GetAttribute('physxPBDMaterial:adhesion').Set(float(adhesion))
    if particle_adhesion_scale is not None:
        material.GetAttribute('physxPBDMaterial:particleAdhesionScale').Set(float(particle_adhesion_scale))
    if adhesion_offset_scale is not None:
        attr = material.GetAttribute('physxPBDMaterial:adhesionOffsetScale')
        if not attr:
            attr = _schema_attr(material, 'physxPBDMaterial:adhesionOffsetScale',
                                Sdf.ValueTypeNames.Float, float(adhesion_offset_scale))
        else:
            attr.Set(float(adhesion_offset_scale))
    stage.GetRootLayer().Save()


def apply_pbd_viscous_particle_fluid(scene, cohesion=5.0, viscosity=2.0, friction=0.85,
                                    surface_tension=0.05, fluid_rest_offset_m=R60_FLUID_REST_OFFSET_M,
                                    particle_friction_scale=1.5, particle_contact_offset_m=None,
                                    rigid_rest_offset_m=None, rigid_contact_offset_m=None):
    """Turn the dry PBD set into a viscous fluid that still renders as particles."""
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    system = stage.GetPrimAtPath(PARTICLE_SYSTEM)
    material = stage.GetPrimAtPath(PBD_MATERIAL)
    particle_set = stage.GetPrimAtPath(PARTICLE_SET)
    if not system or not material or not particle_set:
        raise ValueError('Missing PBD system, material, or set in '+str(scene))
    rest = float(fluid_rest_offset_m)
    contact = float(particle_contact_offset_m) if particle_contact_offset_m is not None else R60_PARTICLE_CONTACT_OFFSET_M
    if rest <= 0 or rest >= contact:
        raise ValueError('fluidRestOffset must be in (0, particleContactOffset)')
    if particle_contact_offset_m is not None:
        _schema_attr(system, 'particleContactOffset', Sdf.ValueTypeNames.Float, contact)
    if rigid_rest_offset_m is not None:
        _schema_attr(system, 'restOffset', Sdf.ValueTypeNames.Float, float(rigid_rest_offset_m))
    if rigid_contact_offset_m is not None:
        _schema_attr(system, 'contactOffset', Sdf.ValueTypeNames.Float, float(rigid_contact_offset_m))
    _schema_attr(system, 'fluidRestOffset', Sdf.ValueTypeNames.Float, rest)
    iso = system.GetAttribute('physxParticleIsosurface:isosurfaceEnabled')
    if iso:
        iso.Set(False)
    particle_set.GetAttribute('physxParticle:fluid').Set(True)
    material.GetAttribute('physxPBDMaterial:cohesion').Set(float(cohesion))
    visc = material.GetAttribute('physxPBDMaterial:viscosity')
    if not visc:
        visc = _schema_attr(material, 'physxPBDMaterial:viscosity', Sdf.ValueTypeNames.Float, float(viscosity))
    else:
        visc.Set(float(viscosity))
    tension = material.GetAttribute('physxPBDMaterial:surfaceTension')
    if not tension:
        tension = _schema_attr(material, 'physxPBDMaterial:surfaceTension',
                              Sdf.ValueTypeNames.Float, float(surface_tension))
    else:
        tension.Set(float(surface_tension))
    material.GetAttribute('physxPBDMaterial:friction').Set(float(friction))
    material.GetAttribute('physxPBDMaterial:particleFrictionScale').Set(float(particle_friction_scale))
    material.GetAttribute('physxPBDMaterial:adhesion').Set(0.0)
    material.GetAttribute('physxPBDMaterial:particleAdhesionScale').Set(0.0)
    offset = material.GetAttribute('physxPBDMaterial:adhesionOffsetScale')
    if offset:
        offset.Set(0.0)
    stage.GetRootLayer().Save()


def apply_pbd_dry_solid(scene, solid_rest_offset_m=R60_SOLID_REST_OFFSET_M,
                        particle_contact_offset_m=R60_PARTICLE_CONTACT_OFFSET_M,
                        rigid_rest_offset_m=R60_RIGID_REST_OFFSET_M,
                        rigid_contact_offset_m=R60_RIGID_CONTACT_OFFSET_M,
                        friction=FRICTION, damping=DAMPING, max_velocity=MAX_VELOCITY):
    """Turn a viscous particle set back into dry solid PBD (fluid=False, no cohesion)."""
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    system = stage.GetPrimAtPath(PARTICLE_SYSTEM)
    material = stage.GetPrimAtPath(PBD_MATERIAL)
    particle_set = stage.GetPrimAtPath(PARTICLE_SET)
    if not system or not material or not particle_set:
        raise ValueError('Missing PBD system, material, or set in '+str(scene))
    solid = float(solid_rest_offset_m)
    contact = float(particle_contact_offset_m)
    rigid_rest = float(rigid_rest_offset_m)
    rigid_contact = float(rigid_contact_offset_m)
    if not (0 < solid < contact and 0 < rigid_rest < rigid_contact):
        raise ValueError('dry solid rest must be in (0, particleContactOffset) and rigid rest < contact')
    _schema_attr(system, 'solidRestOffset', Sdf.ValueTypeNames.Float, solid)
    _schema_attr(system, 'particleContactOffset', Sdf.ValueTypeNames.Float, contact)
    _schema_attr(system, 'fluidRestOffset', Sdf.ValueTypeNames.Float, 0.0)
    _schema_attr(system, 'restOffset', Sdf.ValueTypeNames.Float, rigid_rest)
    _schema_attr(system, 'contactOffset', Sdf.ValueTypeNames.Float, rigid_contact)
    _schema_attr(system, 'maxVelocity', Sdf.ValueTypeNames.Float, float(max_velocity))
    iso = system.GetAttribute('physxParticleIsosurface:isosurfaceEnabled')
    if iso:
        iso.Set(False)
    particle_set.GetAttribute('physxParticle:fluid').Set(False)
    material.GetAttribute('physxPBDMaterial:cohesion').Set(0.0)
    visc = material.GetAttribute('physxPBDMaterial:viscosity')
    if not visc:
        _schema_attr(material, 'physxPBDMaterial:viscosity', Sdf.ValueTypeNames.Float, 0.0)
    else:
        visc.Set(0.0)
    tension = material.GetAttribute('physxPBDMaterial:surfaceTension')
    if tension:
        tension.Set(0.0)
    material.GetAttribute('physxPBDMaterial:friction').Set(float(friction))
    material.GetAttribute('physxPBDMaterial:damping').Set(float(damping))
    scale = material.GetAttribute('physxPBDMaterial:particleFrictionScale')
    if scale:
        scale.Set(1.0)
    material.GetAttribute('physxPBDMaterial:adhesion').Set(0.0)
    material.GetAttribute('physxPBDMaterial:particleAdhesionScale').Set(0.0)
    offset = material.GetAttribute('physxPBDMaterial:adhesionOffsetScale')
    if offset:
        offset.Set(0.0)
    stage.GetRootLayer().Save()


def planned_cavity_lattice(cfg, spacing_m, surface_depth_m, wall_margin_m=0.002,
                           neck_z_m=None, neck_wall_margin_m=None):
    """Hex-layer points in bottle-local frame, inside the inner profile."""
    import numpy as np
    from scripts.compact_powder_protocol import cavity_mask

    spacing = float(spacing_m)
    floor = float(cfg['false_floor_m'])
    z_hi = floor + float(surface_depth_m)
    z_step = spacing * (2.0 / 3.0) ** 0.5
    y_step = spacing * (3.0 ** 0.5) / 2.0
    max_r = max(float(p['radius']) for p in cfg['inner_profile'])
    pts = []
    layer = 0
    z = floor + 0.5 * spacing
    while z <= z_hi + 1e-12:
        xoff = (layer % 2) * (0.5 * spacing)
        y = -max_r
        while y <= max_r:
            x = -max_r + xoff
            while x <= max_r:
                pts.append((x, y, z))
                x += spacing
            y += y_step
        z += z_step
        layer += 1
    if not pts:
        return np.zeros((0, 3), dtype=np.float64)
    local = np.asarray(pts, dtype=np.float64)
    body_margin = abs(float(wall_margin_m))
    keep = cavity_mask(local, cfg, margin=-body_margin)
    if neck_z_m is not None and neck_wall_margin_m is not None:
        neck_keep = cavity_mask(local, cfg, margin=-abs(float(neck_wall_margin_m)))
        keep = np.where(local[:, 2] >= float(neck_z_m), neck_keep, keep)
    keep &= local[:, 2] >= floor
    keep &= local[:, 2] <= z_hi + 1e-9
    return local[keep]


def fill_pbd_cavity_lattice(scene, cfg, spacing_m, surface_depth_m, mass_per_particle,
                            wall_margin_m=0.002, neck_z_m=None, neck_wall_margin_m=None,
                            visual_width_m=None):
    """Replace the PBD set with a cavity lattice so a viscous rest can stay near-full."""
    local = planned_cavity_lattice(
        cfg, spacing_m, surface_depth_m, wall_margin_m,
        neck_z_m=neck_z_m, neck_wall_margin_m=neck_wall_margin_m,
    )
    if len(local) == 0:
        raise ValueError('cavity lattice is empty')
    origin = [float(v) for v in cfg['bottle_xyz']]
    world = [
        Gf.Vec3f(float(p[0] + origin[0]), float(p[1] + origin[1]), float(p[2] + origin[2]))
        for p in local
    ]
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    particle_set = stage.GetPrimAtPath(PARTICLE_SET)
    if not particle_set:
        raise ValueError('Missing '+PARTICLE_SET)
    points = UsdGeom.Points(particle_set)
    points.GetPointsAttr().Set(Vt.Vec3fArray(world))
    points.GetVelocitiesAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.0)] * len(world)))
    width = VISUAL_WIDTH_M if visual_width_m is None else float(visual_width_m)
    points.GetWidthsAttr().Set(Vt.FloatArray([width] * len(world)))
    UsdPhysics.MassAPI.Apply(particle_set).CreateMassAttr(float(len(world)) * float(mass_per_particle))
    stage.GetRootLayer().Save()
    return len(world)


SPOON_COLLISION_SCOPE = '/World/obj_sampling_spoon/PhysicsCollision'
SPOON_BOWL_CONTACT = '/World/obj_sampling_spoon/BowlContact'
# Inner weirs stay inside the visual bowl (extent y±9.3 mm, z≤8.3 mm, x≤100 mm)
# so they cannot hook the bottle neck the way the a23 outer lips did.
SPOON_RIM_PRIMS = (
    ('BowlRimPositiveY', (0.084, 0.0074, 0.0064), (0.028, 0.0014, 0.003)),
    ('BowlRimNegativeY', (0.084, -0.0074, 0.0064), (0.028, 0.0014, 0.003)),
    ('BowlRimDistal', (0.097, 0.0, 0.0064), (0.0014, 0.013, 0.003)),
)
# Taller carry lips. Only safe if collision stays off through insert.
SPOON_CARRY_RIM_PRIMS = (
    ('BowlRimPositiveY', (0.084, 0.0096, 0.0085), (0.034, 0.0022, 0.006)),
    ('BowlRimNegativeY', (0.084, -0.0096, 0.0085), (0.034, 0.0022, 0.006)),
    ('BowlRimDistal', (0.102, 0.0, 0.0085), (0.0022, 0.019, 0.006)),
)


def spoon_weir_collision_enabled(t, window):
    """True while t is in [start, end) for a carry-only spoon weir."""
    if not window:
        return False
    start, end = window
    return float(start) <= float(t) < float(end)


def apply_spoon_bowl_rim(scene, rims=None, collision_enabled=True):
    """Add invisible low lips around the spoon bowl so spheres do not roll off."""
    stage = Usd.Stage.Open(str(scene))
    if stage is None:
        raise ValueError('Cannot open '+str(scene))
    parent = stage.GetPrimAtPath(SPOON_COLLISION_SCOPE)
    if not parent:
        raise ValueError('Missing '+SPOON_COLLISION_SCOPE)
    material = stage.GetPrimAtPath(SPOON_BOWL_CONTACT)
    if not material:
        raise ValueError('Missing '+SPOON_BOWL_CONTACT)
    specs = list(rims) if rims is not None else list(SPOON_RIM_PRIMS)
    for name, translate, scale in specs:
        cube = UsdGeom.Cube.Define(stage, f'{SPOON_COLLISION_SCOPE}/{name}')
        prim = cube.GetPrim()
        _prepend_api_schemas(prim, [
            'PhysicsCollisionAPI', 'PhysxCollisionAPI', 'PhysicsMassAPI', 'MaterialBindingAPI',
        ])
        cube.GetSizeAttr().Set(1.0)
        cube.GetVisibilityAttr().Set('invisible')
        prim.CreateAttribute('physics:collisionEnabled', Sdf.ValueTypeNames.Bool, custom=False).Set(
            bool(collision_enabled))
        prim.CreateAttribute('physics:density', Sdf.ValueTypeNames.Float, custom=False).Set(1e-6)
        prim.CreateAttribute('physxCollision:contactOffset', Sdf.ValueTypeNames.Float, custom=False).Set(0.0005)
        prim.CreateAttribute('physxCollision:restOffset', Sdf.ValueTypeNames.Float, custom=False).Set(0.0)
        xform = UsdGeom.Xformable(prim)
        xform.ClearXformOpOrder()
        xform.AddTranslateOp().Set(Gf.Vec3d(*translate))
        xform.AddOrientOp().Set(Gf.Quatf(1, 0, 0, 0))
        xform.AddScaleOp().Set(Gf.Vec3f(*scale))
        bind = prim.CreateRelationship('material:binding:physics', custom=False)
        bind.SetTargets([SPOON_BOWL_CONTACT])
    stage.GetRootLayer().Save()
    return [name for name, _, _ in specs]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    source = a.source.resolve()
    out = a.out.resolve()
    if out.exists():
        raise ValueError('Refusing to overwrite '+str(out))
    out.mkdir(parents=True)
    for path in source.iterdir():
        if path.name in SKIP or path.name.endswith('.zip') or path.name.endswith('.sha256'):
            continue
        dest = out / path.name
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
    cfg_path = out / 'scene_config.json'
    cfg = json.loads(cfg_path.read_text())
    count = replace_grains_with_pbd(out / 'scene.usda', cfg['mass_per_grain_kg'])
    if count != cfg.get('count'):
        raise ValueError(f'Converted {count} grains, config count is {cfg.get("count")}')
    cfg = patch_scene_config(cfg)
    cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
    print(json.dumps({
        'out': str(out),
        'revision': cfg['revision'],
        'physics_hz': cfg['physics_hz'],
        'powder_kind': cfg['powder_kind'],
        'count': count,
        'pbd_solid_rest_offset_m': cfg['pbd_solid_rest_offset_m'],
    }))


if __name__ == '__main__':
    main()

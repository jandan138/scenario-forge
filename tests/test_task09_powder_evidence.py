import pytest

from scripts.package_task09_powder import COMPACT_REVISIONS, NEAR_FULL_REVISIONS
from scripts.task09_powder_evidence import REQUIRED, validate_report


def report(mode='scoop'):
    seconds = {'scoop':50,'settle':5,'calibration':43}[mode]
    return dict(status='passed',mode=mode,runtime='4.5.0',requested_runtime='45',
                scene_sha256='scene',entry_sha256='scene',physics_dt=1/480,solver='PGS',
                position_iterations_override=None,wake_all_override=False,engine_errors=[],
                requested_seconds=seconds,rows=[{'time_s':seconds-.02}],
                checks={name:True for name in REQUIRED[mode]})


def test_complete_run_is_required_not_just_finite_frozen_positions():
    validate_report(report(),'scene','scoop')
    for field,value in [('engine_errors',['GPU kernel failed']),('checks',{'finite':True}),
                        ('rows',[{'time_s':2.}]),('runtime','4.1.0'),('scene_sha256','stale')]:
        data = report()
        data[field] = value
        with pytest.raises(ValueError):
            validate_report(data,'scene','scoop')


def test_wrong_protocol_or_session_override_cannot_qualify_scene():
    for field,value in [('mode','settle'),('solver','TGS'),('wake_all_override',True),
                        ('position_iterations_override',32),('physics_dt',1/60)]:
        data = report()
        data[field] = value
        with pytest.raises(ValueError):
            validate_report(data,'scene','scoop')


def test_compact_evidence_uses_candidate_timestep_and_requires_measured_bed():
    cfg = {'revision':'r3','physics_hz':240,'inner_profile':[{}]}
    data = report('settle')
    data.update(physics_dt=1/240,authored_physics_hz=240,profile_revision='r3',
                settled_bed={'surface_depth_median_m':.011,'columns':184})
    data['checks']['deep_powder_bed'] = True
    validate_report(data,'scene','settle',cfg)
    for field,value in [('physics_dt',1/480),('profile_revision','r2'),
                        ('settled_bed',{'surface_depth_median_m':.0096,'columns':184})]:
        invalid = dict(data,**{field:value})
        with pytest.raises(ValueError):
            validate_report(invalid,'scene','settle',cfg)
    del data['checks']['deep_powder_bed']
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',cfg)


def test_r5_0_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.0','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled'}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.0',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_0_as_compact_near_full_revision():
    assert 'r5.0' in COMPACT_REVISIONS
    assert 'r4' in NEAR_FULL_REVISIONS
    assert 'r5.0' in NEAR_FULL_REVISIONS


def test_r5_1_compact_evidence_requires_120hz_velocity_caps_not_r4_240hz():
    cfg = {'revision':'r5.1','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_max_linear_velocity_m_s':0.15,'grain_max_depenetration_velocity_m_s':0.2}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.1',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,grain_max_linear_velocity_m_s=1.0))
    with pytest.raises(ValueError):
        validate_report(data,'scene','settle',dict(cfg,grain_max_depenetration_velocity_m_s=0.05))


def test_packager_treats_r5_1_as_compact_near_full_revision():
    assert 'r5.1' in COMPACT_REVISIONS
    assert 'r5.1' in NEAR_FULL_REVISIONS


def test_r5_2_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.2','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_contact_offset_m':0.00015,'grain_rest_offset_m':0.00005}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.2',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_2_as_compact_near_full_revision():
    assert 'r5.2' in COMPACT_REVISIONS
    assert 'r5.2' in NEAR_FULL_REVISIONS


def test_r5_3_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.3','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'grain_contact_offset_m':0.00025,'grain_rest_offset_m':0.00015,
           'wall_contact_offset_m':0.001,'wall_rest_offset_m':0.0002}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.3',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_3_as_compact_near_full_revision():
    assert 'r5.3' in COMPACT_REVISIONS
    assert 'r5.3' in NEAR_FULL_REVISIONS


def test_r5_4_compact_evidence_requires_120hz_not_r4_240hz():
    cfg = {'revision':'r5.4','physics_hz':120,'inner_profile':[{}],'initial_state':'presettled',
           'insert_contact_offset_m':0.003,'insert_rest_offset_m':0.0006}
    level = dict(surface_depth_median_m=.011,median_headspace_m=.005,minimum_headspace_m=.004,columns=120)
    data = report('settle')
    data.update(physics_dt=1/120,authored_physics_hz=120,profile_revision='r5.4',
                initial_state='presettled',initial_fill_level=level,settled_bed=level,settled_fill_level=level)
    data['checks']['deep_powder_bed'] = True
    data['checks']['near_full_initial_state'] = True
    data['checks']['near_full_settled_state'] = True
    validate_report(data,'scene','settle',cfg)
    with pytest.raises(ValueError):
        validate_report(dict(data,physics_dt=1/240,authored_physics_hz=240),'scene','settle',cfg)


def test_packager_treats_r5_4_as_compact_near_full_revision():
    assert 'r5.4' in COMPACT_REVISIONS
    assert 'r5.4' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_5_as_compact_near_full_revision():
    assert 'r5.5' in COMPACT_REVISIONS
    assert 'r5.5' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_6_as_compact_near_full_revision():
    assert 'r5.6' in COMPACT_REVISIONS
    assert 'r5.6' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_7_as_compact_near_full_revision():
    assert 'r5.7' in COMPACT_REVISIONS
    assert 'r5.7' in NEAR_FULL_REVISIONS


def test_packager_stages_1g_task_contract_and_zip_sha256(tmp_path):
    from scripts.package_task09_powder import include_task_contract, write_zip_sha256

    spec = tmp_path / 'scenario.yaml'
    spec.write_text('scenario_id: demo\n')
    bindings = tmp_path / 'source_bindings.yaml'
    bindings.write_text(
        'bindings:\n  task09_powder_bottle_r5_7:\n'
        '    source_usd: /abs/scene.usda\n'
    )
    out = tmp_path / 'pkg'
    out.mkdir()
    (out / 'scene.usda').write_text('#usda 1.0\n')
    include_task_contract(out, spec, bindings)
    assert (out / 'task/scenario.yaml').read_text() == 'scenario_id: demo\n'
    staged = (out / 'task/source_bindings.yaml').read_text()
    assert '../scene.usda' in staged
    assert '/abs/scene.usda' not in staged
    archive = tmp_path / 'pkg.zip'
    archive.write_bytes(b'zip-bytes')
    sidecar = write_zip_sha256(archive)
    assert sidecar.name == 'pkg.zip.sha256'
    digest = __import__('hashlib').sha256(b'zip-bytes').hexdigest()
    assert sidecar.read_text() == f'{digest}  pkg.zip\n'


def test_packager_treats_r5_8_as_compact_near_full_revision():
    assert 'r5.8' in COMPACT_REVISIONS
    assert 'r5.8' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_9_as_compact_near_full_revision():
    assert 'r5.9' in COMPACT_REVISIONS
    assert 'r5.9' in NEAR_FULL_REVISIONS


def test_packager_treats_r5_10_as_compact_near_full_revision():
    assert 'r5.10' in COMPACT_REVISIONS
    assert 'r5.10' in NEAR_FULL_REVISIONS


def test_packager_treats_r6_0_as_compact_near_full_pbd_revision():
    from scripts.task09_powder_evidence import PBD_REVISIONS, authored_pbd_dry_powder_matches

    assert 'r6.0' in COMPACT_REVISIONS
    assert 'r6.0' in NEAR_FULL_REVISIONS
    assert 'r6.0' in PBD_REVISIONS
    cfg = {
        'revision': 'r6.0',
        'physics_hz': 120,
        'powder_kind': 'pbd_solid',
        'pbd_fluid': False,
        'pbd_solid_rest_offset_m': 0.00104,
        'pbd_particle_contact_offset_m': 0.00114,
        'pbd_rigid_rest_offset_m': 0.0007,
        'pbd_rigid_contact_offset_m': 0.00072,
        'mass_per_grain_kg': 2.15513256e-6,
    }
    assert authored_pbd_dry_powder_matches(cfg)
    assert not authored_pbd_dry_powder_matches(dict(cfg, pbd_fluid=True))
    assert not authored_pbd_dry_powder_matches(dict(cfg, pbd_solid_rest_offset_m=0.0012))
    assert not authored_pbd_dry_powder_matches(dict(cfg, pbd_particle_contact_offset_m=0.0010))
    assert authored_pbd_dry_powder_matches(dict(
        cfg, pbd_solid_rest_offset_m=0.00149, pbd_particle_contact_offset_m=0.00163,
        pbd_rigid_rest_offset_m=0.0010, pbd_rigid_contact_offset_m=0.00103,
    ))


def test_authored_pbd_viscous_particles_requires_fluid_and_particle_display():
    from scripts.task09_powder_evidence import authored_pbd_viscous_particles_matches

    cfg = {
        'powder_kind': 'pbd_viscous',
        'pbd_fluid': True,
        'pbd_display': 'particles',
        'pbd_solid_rest_offset_m': 0.00104,
        'pbd_particle_contact_offset_m': 0.00114,
        'pbd_rigid_rest_offset_m': 0.0007,
        'pbd_rigid_contact_offset_m': 0.00072,
        'pbd_fluid_rest_offset_m': 0.00052,
    }
    assert authored_pbd_viscous_particles_matches(cfg)
    assert authored_pbd_viscous_particles_matches(dict(cfg, pbd_fluid_rest_offset_m=0.00078))
    assert not authored_pbd_viscous_particles_matches(dict(cfg, powder_kind='pbd_solid'))
    assert not authored_pbd_viscous_particles_matches(dict(cfg, pbd_display='isosurface'))
    assert not authored_pbd_viscous_particles_matches(dict(cfg, pbd_fluid_rest_offset_m=0.00114))
    assert authored_pbd_viscous_particles_matches(dict(
        cfg, pbd_fluid_rest_offset_m=0.00093, pbd_particle_contact_offset_m=0.00163,
        pbd_rigid_rest_offset_m=0.0010, pbd_rigid_contact_offset_m=0.00103,
        pbd_solid_rest_offset_m=0.00149,
    ))


def test_r6_0_replaces_rigid_grains_with_dry_pbd_points(tmp_path):
    from pxr import Usd, UsdGeom
    from scripts.clone_task09_powder_r6_0 import replace_grains_with_pbd, patch_scene_config

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_bottle" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
    def Xform "obj_powder_grain_00001"
    {
        double3 xformOp:translate = (0.11, 0.21, 0.81)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    count = replace_grains_with_pbd(usda, mass_per_particle=2.15513256e-6)
    assert count == 2
    stage = Usd.Stage.Open(str(usda))
    assert not stage.GetPrimAtPath('/World/obj_powder_grain_00000').IsValid()
    system = stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem')
    points = UsdGeom.Points(stage.GetPrimAtPath('/World/powder_pbd/ParticleSet'))
    assert system.IsValid()
    assert points
    assert system.GetAttribute('solidRestOffset').Get() == pytest.approx(0.00104)
    assert system.GetAttribute('particleContactOffset').Get() == pytest.approx(0.00114)
    assert system.GetAttribute('restOffset').Get() == pytest.approx(0.0007)
    fluid = points.GetPrim().GetAttribute('physxParticle:fluid')
    assert fluid.Get() is False
    assert not fluid.IsCustom()
    assert not system.GetAttribute('solidRestOffset').IsCustom()
    text = usda.read_text()
    assert 'PhysxParticleSetAPI' in text
    assert 'PhysxParticleAPI' in text
    assert 'PhysxPBDMaterialAPI' in text
    assert 'custom bool physxParticle:fluid' not in text
    material = stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial')
    assert not material.GetAttribute('physxPBDMaterial:friction').IsCustom()
    assert material.GetAttribute('physxPBDMaterial:gravityScale').Get() == pytest.approx(1.0)
    assert list(points.GetPointsAttr().Get())[0] == pytest.approx((0.1, 0.2, 0.8))
    cfg = patch_scene_config({'physics_hz': 120, 'count': 2, 'mass_per_grain_kg': 2.15513256e-6,
                              'paths': {'powder_pattern': '/World/obj_powder_grain_*'}})
    assert cfg['revision'] == 'r6.0'
    assert cfg['powder_kind'] == 'pbd_solid'
    assert cfg['pbd_fluid'] is False
    assert cfg['paths']['powder_pbd'] == '/World/powder_pbd/ParticleSet'
    assert cfg['grain_bound_m'] == pytest.approx(0.0007)
    assert cfg['grain_radius_m'] == pytest.approx(0.0007)
    assert cfg['pbd_gravity_scale'] == pytest.approx(1.0)


def test_set_pbd_particle_xyz_keeps_dry_offsets_and_updates_count(tmp_path):
    from pxr import Usd, UsdGeom, UsdPhysics
    from scripts.clone_task09_powder_r6_0 import replace_grains_with_pbd, set_pbd_particle_xyz

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
    def Xform "obj_powder_grain_00001"
    {
        double3 xformOp:translate = (0.11, 0.21, 0.81)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=2.15513256e-6)
    n = set_pbd_particle_xyz(usda, [(0.1, 0.2, 0.8)], mass_per_particle=2.15513256e-6)
    assert n == 1
    stage = Usd.Stage.Open(str(usda))
    system = stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem')
    prim = stage.GetPrimAtPath('/World/powder_pbd/ParticleSet')
    assert prim.GetAttribute('physxParticle:fluid').Get() is False
    assert system.GetAttribute('solidRestOffset').Get() == pytest.approx(0.00104)
    pts = UsdGeom.Points(prim).GetPointsAttr().Get()
    assert len(pts) == 1
    assert UsdPhysics.MassAPI(prim).GetMassAttr().Get() == pytest.approx(2.15513256e-6)


def test_apply_pbd_motion_caps_writes_damping_and_max_velocity(tmp_path):
    from pxr import Usd
    from scripts.clone_task09_powder_r6_0 import apply_pbd_motion_caps, replace_grains_with_pbd

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=2.15513256e-6)
    apply_pbd_motion_caps(usda, damping=0.55, max_velocity=0.045, friction=0.85, cohesion=0.02,
                         particle_friction_scale=4.0, adhesion=2.0, particle_adhesion_scale=1.0,
                         adhesion_offset_scale=0.25, solver_position_iterations=32, viscosity=1.0)
    stage = Usd.Stage.Open(str(usda))
    assert stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem').GetAttribute('maxVelocity').Get() == pytest.approx(0.045)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:damping').Get() == pytest.approx(0.55)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:friction').Get() == pytest.approx(0.85)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:cohesion').Get() == pytest.approx(0.02)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:particleFrictionScale').Get() == pytest.approx(4.0)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:adhesion').Get() == pytest.approx(2.0)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:particleAdhesionScale').Get() == pytest.approx(1.0)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:adhesionOffsetScale').Get() == pytest.approx(0.25)
    assert stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem').GetAttribute('solverPositionIterationCount').Get() == 32
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:viscosity').Get() == pytest.approx(1.0)


def test_apply_pbd_viscous_particle_fluid_enables_fluid_keeps_points(tmp_path):
    from pxr import Usd
    from scripts.clone_task09_powder_r6_0 import apply_pbd_viscous_particle_fluid, replace_grains_with_pbd

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=2.15513256e-6)
    apply_pbd_viscous_particle_fluid(usda, cohesion=5.0, viscosity=2.0, friction=0.85)
    stage = Usd.Stage.Open(str(usda))
    assert stage.GetPrimAtPath('/World/powder_pbd/ParticleSet').GetAttribute('physxParticle:fluid').Get() is True
    assert stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem').GetAttribute('fluidRestOffset').Get() == pytest.approx(0.00052)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:cohesion').Get() == pytest.approx(5.0)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:viscosity').Get() == pytest.approx(2.0)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:friction').Get() == pytest.approx(0.85)
    assert stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial').GetAttribute('physxPBDMaterial:adhesionOffsetScale').Get() == pytest.approx(0.0)
    iso = stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem').GetAttribute('physxParticleIsosurface:isosurfaceEnabled')
    assert (not iso) or iso.Get() is False


def test_apply_pbd_viscous_particle_fluid_can_scale_contact_with_larger_rest(tmp_path):
    from pxr import Usd
    from scripts.clone_task09_powder_r6_0 import apply_pbd_viscous_particle_fluid, replace_grains_with_pbd

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=6.28e-6)
    apply_pbd_viscous_particle_fluid(
        usda, cohesion=0.2, viscosity=2.0, friction=0.85,
        fluid_rest_offset_m=0.00093, particle_contact_offset_m=0.00163,
        rigid_rest_offset_m=0.0010, rigid_contact_offset_m=0.00103,
    )
    stage = Usd.Stage.Open(str(usda))
    system = stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem')
    assert system.GetAttribute('fluidRestOffset').Get() == pytest.approx(0.00093)
    assert system.GetAttribute('particleContactOffset').Get() == pytest.approx(0.00163)
    assert system.GetAttribute('restOffset').Get() == pytest.approx(0.0010)
    assert system.GetAttribute('contactOffset').Get() == pytest.approx(0.00103)


def test_apply_pbd_dry_solid_disables_fluid_and_can_scale_rest(tmp_path):
    from pxr import Usd
    from scripts.clone_task09_powder_r6_0 import (
        apply_pbd_dry_solid, apply_pbd_viscous_particle_fluid, replace_grains_with_pbd,
    )

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=6.28e-6)
    apply_pbd_viscous_particle_fluid(
        usda, cohesion=0.2, viscosity=2.0, friction=0.85,
        fluid_rest_offset_m=0.00093, particle_contact_offset_m=0.00163,
        rigid_rest_offset_m=0.0010, rigid_contact_offset_m=0.00103,
    )
    apply_pbd_dry_solid(
        usda, solid_rest_offset_m=0.00149, particle_contact_offset_m=0.00163,
        rigid_rest_offset_m=0.0010, rigid_contact_offset_m=0.00103,
        friction=0.65, damping=0.4, max_velocity=0.06,
    )
    stage = Usd.Stage.Open(str(usda))
    system = stage.GetPrimAtPath('/World/powder_pbd/ParticleSystem')
    material = stage.GetPrimAtPath('/World/powder_pbd/PBDMaterial')
    assert stage.GetPrimAtPath('/World/powder_pbd/ParticleSet').GetAttribute('physxParticle:fluid').Get() is False
    assert system.GetAttribute('fluidRestOffset').Get() == pytest.approx(0.0)
    assert system.GetAttribute('solidRestOffset').Get() == pytest.approx(0.00149)
    assert system.GetAttribute('particleContactOffset').Get() == pytest.approx(0.00163)
    assert system.GetAttribute('restOffset').Get() == pytest.approx(0.0010)
    assert system.GetAttribute('contactOffset').Get() == pytest.approx(0.00103)
    assert system.GetAttribute('maxVelocity').Get() == pytest.approx(0.06)
    assert material.GetAttribute('physxPBDMaterial:cohesion').Get() == pytest.approx(0.0)
    assert material.GetAttribute('physxPBDMaterial:viscosity').Get() == pytest.approx(0.0)
    assert material.GetAttribute('physxPBDMaterial:friction').Get() == pytest.approx(0.65)
    assert material.GetAttribute('physxPBDMaterial:damping').Get() == pytest.approx(0.4)


def test_fill_pbd_cavity_lattice_writes_visual_width(tmp_path):
    from pxr import Usd, UsdGeom
    from scripts.clone_task09_powder_r6_0 import fill_pbd_cavity_lattice, replace_grains_with_pbd

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (1.0, 2.0, 3.0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=6.28e-6)
    cfg = {
        'bottle_xyz': [-0.08, -0.065, 0.756],
        'false_floor_m': 0.084,
        'bottle_height_m': 0.100,
        'inner_profile': [
            {'z': 0.002, 'radius': 0.0278, 'exponent': 5.0},
            {'z': 0.100, 'radius': 0.0249, 'exponent': 2.0},
        ],
    }
    fill_pbd_cavity_lattice(
        usda, cfg, spacing_m=0.004, surface_depth_m=0.011, mass_per_particle=6.28e-6,
        visual_width_m=0.002,
    )
    stage = Usd.Stage.Open(str(usda))
    widths = UsdGeom.Points(stage.GetPrimAtPath('/World/powder_pbd/ParticleSet')).GetWidthsAttr().Get()
    assert widths
    assert widths[0] == pytest.approx(0.002)


def test_spoon_weir_collision_enabled_is_half_open_window():
    from scripts.clone_task09_powder_r6_0 import spoon_weir_collision_enabled

    assert spoon_weir_collision_enabled(32.0, None) is False
    assert spoon_weir_collision_enabled(31.9, (32.0, 36.0)) is False
    assert spoon_weir_collision_enabled(32.0, (32.0, 36.0)) is True
    assert spoon_weir_collision_enabled(35.9, (32.0, 36.0)) is True
    assert spoon_weir_collision_enabled(36.0, (32.0, 36.0)) is False


def test_apply_spoon_bowl_rim_adds_invisible_collision_lips(tmp_path):
    from pxr import Usd, UsdGeom
    from scripts.clone_task09_powder_r6_0 import apply_spoon_bowl_rim, SPOON_RIM_PRIMS

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def Xform "obj_sampling_spoon"
    {
        def Scope "PhysicsCollision" {}
        def Material "BowlContact" {}
    }
}
'''
    )
    names = apply_spoon_bowl_rim(usda)
    assert names == [item[0] for item in SPOON_RIM_PRIMS]
    stage = Usd.Stage.Open(str(usda))
    for name, translate, scale in SPOON_RIM_PRIMS:
        prim = stage.GetPrimAtPath(f'/World/obj_sampling_spoon/PhysicsCollision/{name}')
        assert prim
        assert UsdGeom.Imageable(prim).GetVisibilityAttr().Get() == 'invisible'
        assert prim.GetAttribute('physics:collisionEnabled').Get() is True
        xform = UsdGeom.Xformable(prim)
        ops = {op.GetOpName(): op.Get() for op in xform.GetOrderedXformOps()}
        assert ops['xformOp:translate'] == pytest.approx(translate)
        assert tuple(ops['xformOp:scale']) == pytest.approx(scale)
        assert prim.GetAttribute('physics:collisionEnabled').Get() is True


def test_apply_spoon_bowl_rim_can_start_disabled(tmp_path):
    from pxr import Usd
    from scripts.clone_task09_powder_r6_0 import apply_spoon_bowl_rim, SPOON_CARRY_RIM_PRIMS

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def Xform "obj_sampling_spoon"
    {
        def Scope "PhysicsCollision" {}
        def Material "BowlContact" {}
    }
}
'''
    )
    apply_spoon_bowl_rim(usda, rims=SPOON_CARRY_RIM_PRIMS, collision_enabled=False)
    stage = Usd.Stage.Open(str(usda))
    prim = stage.GetPrimAtPath('/World/obj_sampling_spoon/PhysicsCollision/BowlRimDistal')
    assert prim.GetAttribute('physics:collisionEnabled').Get() is False


def test_read_pbd_particle_xyz_prefers_live_simulation_points(tmp_path):
    from pxr import Usd, UsdGeom, Sdf, Gf, Vt
    from scripts.clone_task09_powder_r6_0 import read_pbd_particle_xyz

    stage = Usd.Stage.CreateNew(str(tmp_path / 'p.usda'))
    points = UsdGeom.Points.Define(stage, '/World/powder_pbd/ParticleSet')
    points.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0)]))
    prim = points.GetPrim()
    rest = read_pbd_particle_xyz(prim)
    assert rest[0] == pytest.approx((0.0, 0.0, 0.0))
    prim.CreateAttribute('physxParticle:simulationPoints', Sdf.ValueTypeNames.Point3fArray).Set(
        Vt.Vec3fArray([Gf.Vec3f(0, 0, 0.01), Gf.Vec3f(1, 0, 0.02)])
    )
    live = read_pbd_particle_xyz(prim)
    assert live[1] == pytest.approx((1.0, 0.0, 0.02))


def test_r6_0_scoop_uses_region_mass_not_pan_force():
    cfg = {
        'revision': 'r6.0', 'physics_hz': 120, 'inner_profile': [{}], 'initial_state': 'presettled',
        'powder_kind': 'pbd_solid', 'pbd_fluid': False,
        'pbd_solid_rest_offset_m': 0.00104, 'pbd_particle_contact_offset_m': 0.00114,
        'pbd_rigid_rest_offset_m': 0.0007, 'pbd_rigid_contact_offset_m': 0.00072,
    }
    level = dict(surface_depth_median_m=.011, median_headspace_m=.005, minimum_headspace_m=.004, columns=120)
    data = report('scoop')
    data.update(physics_dt=1/120, authored_physics_hz=120, profile_revision='r6.0',
                initial_state='presettled', initial_fill_level=level)
    data['checks']['near_full_initial_state'] = True
    data['checks'].pop('force_region_agreement')
    data['checks'].pop('positive_force')
    validate_report(data, 'scene', 'scoop', cfg)
    with pytest.raises(ValueError):
        validate_report(data, 'scene', 'scoop', dict(cfg, pbd_fluid=True))
    viscous = dict(
        cfg, powder_kind='pbd_viscous', pbd_fluid=True, pbd_display='particles',
        pbd_fluid_rest_offset_m=0.00052,
    )
    validate_report(data, 'scene', 'scoop', viscous)


def test_validate_task09_does_not_import_pxr_before_simulation_app():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / 'scripts/validate_task09_powder.py').read_text()
    head, _, _ = text.partition('SimulationApp')
    assert 'from pxr' not in head
    assert 'clone_task09_powder_r6_0' not in head


def test_r6_0_does_not_replace_current_powder_delivery_head():
    import json
    from pathlib import Path

    heads = json.loads((Path(__file__).resolve().parents[1]
                        / 'configs/artifact_retention/current_task_heads.v1.json').read_text())
    powder = [row for row in heads['entries']
              if row.get('variant_key') == 'isaac45_original_scene_powder_bottle']
    assert powder
    assert powder[0]['handoff_zip'] == 'handoff/task09_powder_bottle_r4.zip'


def test_rest_motion_reports_median_speed_and_drift():
    from scripts.task09_powder_evidence import summarize_rest_motion
    import numpy as np
    times = np.linspace(0.0, 15.0, 451)
    # 1.2 mm/s along x, no extra noise: 15 s drift = 18 mm
    positions = np.zeros((len(times), 4, 3), dtype=np.float32)
    positions[:, :, 0] = (0.0012 * times)[:, None]
    summary = summarize_rest_motion(positions, times, t_end=15.0)
    assert summary['n_frames'] == 451
    assert abs(summary['median_speed_m_s'] - 0.0012) < 1e-6
    assert abs(summary['median_drift_m'] - 0.018) < 1e-6
    assert summary['meets_r4_rest_gate'] is False


def test_fill_pbd_cavity_lattice_replaces_set_inside_profile(tmp_path):
    from pxr import Usd, UsdGeom, UsdPhysics
    from scripts.clone_task09_powder_r6_0 import fill_pbd_cavity_lattice, replace_grains_with_pbd
    from scripts.compact_powder_protocol import cavity_mask
    import numpy as np

    usda = tmp_path / 'scene.usda'
    usda.write_text(
        '''#usda 1.0
def Xform "World"
{
    def PhysicsScene "PhysicsScene" {}
    def Xform "obj_powder_grain_00000"
    {
        double3 xformOp:translate = (1.0, 2.0, 3.0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
'''
    )
    replace_grains_with_pbd(usda, mass_per_particle=2e-6)
    cfg = {
        'bottle_xyz': [-0.08, -0.065, 0.756],
        'false_floor_m': 0.084,
        'bottle_height_m': 0.100,
        'inner_profile': [
            {'z': 0.002, 'radius': 0.0278, 'exponent': 5.0},
            {'z': 0.100, 'radius': 0.0249, 'exponent': 2.0},
        ],
        'mass_per_grain_kg': 2e-6,
    }
    count = fill_pbd_cavity_lattice(
        usda, cfg, spacing_m=0.004, surface_depth_m=0.011, mass_per_particle=2e-6,
    )
    assert count > 20
    stage = Usd.Stage.Open(str(usda))
    prim = stage.GetPrimAtPath('/World/powder_pbd/ParticleSet')
    pts = np.array(UsdGeom.Points(prim).GetPointsAttr().Get(), dtype=np.float64)
    assert len(pts) == count
    local = pts - np.array(cfg['bottle_xyz'])
    assert cavity_mask(local, cfg, margin=-0.001).all()
    assert local[:, 2].min() >= cfg['false_floor_m']
    assert local[:, 2].max() < cfg['false_floor_m'] + 0.011 + 1e-6
    mass = UsdPhysics.MassAPI(prim).GetMassAttr().Get()
    assert mass == pytest.approx(count * 2e-6)


def test_planned_cavity_lattice_neck_margin_clears_the_rim():
    import numpy as np
    from scripts.clone_task09_powder_r6_0 import planned_cavity_lattice

    cfg = {
        'false_floor_m': 0.084,
        'bottle_height_m': 0.100,
        'inner_profile': [
            {'z': 0.002, 'radius': 0.0278, 'exponent': 5.0},
            {'z': 0.066, 'radius': 0.0282, 'exponent': 5.0},
            {'z': 0.090, 'radius': 0.024, 'exponent': 2.0},
            {'z': 0.100, 'radius': 0.0249, 'exponent': 2.0},
        ],
    }
    body = planned_cavity_lattice(cfg, 0.00116, 0.0105, wall_margin_m=0.0025)
    neck = planned_cavity_lattice(
        cfg, 0.00116, 0.0105, wall_margin_m=0.0025,
        neck_z_m=0.090, neck_wall_margin_m=0.0035,
    )
    assert len(neck) < len(body)
    above = neck[neck[:, 2] >= 0.090]
    assert len(above) > 0
    radii = np.interp(above[:, 2], [p['z'] for p in cfg['inner_profile']],
                      [p['radius'] for p in cfg['inner_profile']])
    clearance = radii - np.hypot(above[:, 0], above[:, 1])
    assert clearance.min() >= 0.0035 - 1e-9

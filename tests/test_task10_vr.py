"""VR episode preparation must preserve particle/container alignment across resets."""
import json
import numpy as np
import pytest
from pxr import Usd, UsdGeom, UsdPhysics, Sdf, Vt
from scripts.task10_vr_episode import prepare_episode, reset_episode


def fixture(root='/World'):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage,root)
    for name in ('obj_titration_station','obj_magnetic_stirrer','obj_receiver_flask'):
        UsdGeom.Xform.Define(stage,root+'/'+name).AddTranslateOp().Set((0,0,0))
    station = stage.GetPrimAtPath(root+'/obj_titration_station')
    body = UsdGeom.Xform.Define(stage,root+'/obj_titration_station/Instance/Burette/body_link')
    UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
    receiver = stage.GetPrimAtPath(root+'/obj_receiver_flask')
    UsdPhysics.RigidBodyAPI.Apply(receiver)
    systems = {}
    bases = {}
    for name,container in [('Source',body.GetPath()),('Receiver',receiver.GetPath()),('Falling',body.GetPath())]:
        particle = UsdGeom.Points.Define(stage,root+'/Task10Fluid/'+name+'Particles')
        points = np.array([[.1,.2,.3],[.2,.3,.4]],dtype=np.float32) if name!='Falling' else np.empty((0,3),np.float32)
        velocities = np.ones_like(points)*.02
        for key,array in [('points',points),('velocities',velocities),('titration:initial_points',points),('titration:initial_velocities',velocities),('vr:canonical_points',points),('vr:canonical_velocities',velocities)]:
            particle.GetPrim().CreateAttribute(key,Sdf.ValueTypeNames.Point3fArray if 'points' in key else Sdf.ValueTypeNames.Vector3fArray).Set(Vt.Vec3fArray.FromNumpy(array))
        UsdPhysics.MassAPI.Apply(particle.GetPrim()).CreateMassAttr(.002)
        system_path=root+'/Task10Fluid/'+name+'System'
        stage.DefinePrim(system_path)
        systems[name]={'particle_path':str(particle.GetPath()).replace(root,'/World',1),'system_path':system_path.replace(root,'/World',1),'material_path':'/World/Material','container_body_path':str(container).replace(root,'/World',1),'particle_spacing_m':.001,'per_particle_mass_kg':.001}
        bases[str(container).replace(root,'/World',1)] = np.eye(4).tolist()
    station.CreateAttribute('titration:pbd_config',Sdf.ValueTypeNames.String).Set(json.dumps({'systems':systems,'runtime_contract':{'physics_dt':1/240,'scene_min_position_iterations':64,'scene_max_position_iterations':64}}))
    station.CreateAttribute('vr:canonical_bodies',Sdf.ValueTypeNames.String).Set(json.dumps(bases))
    station.CreateAttribute('vr:canonical_group',Sdf.ValueTypeNames.String).Set(json.dumps({name:np.eye(4).tolist() for name in ('obj_titration_station','obj_magnetic_stirrer','obj_receiver_flask')}))
    UsdPhysics.Scene.Define(stage,root+'/PhysicsScene')
    return stage,station


def shift(stage,root,x,y):
    for name in ('obj_titration_station','obj_magnetic_stirrer','obj_receiver_flask'):
        stage.GetPrimAtPath(root+'/'+name).GetAttribute('xformOp:translate').Set((x,y,0))


@pytest.mark.parametrize('root',['/World','/World/_scene'])
def test_prepare_and_reset_use_episode_positions_without_cumulative_drift(root):
    stage,station=fixture(root)
    shift(stage,root,.01,-.01)
    prepare_episode(stage,root)
    p=stage.GetPrimAtPath(root+'/Task10Fluid/ReceiverParticles')
    canonical=np.asarray(p.GetAttribute('vr:canonical_points').Get())
    expected=canonical+np.array([.01,-.01,0])
    assert np.allclose(p.GetAttribute('points').Get(),expected)
    prepare_episode(stage,root)
    assert np.allclose(p.GetAttribute('points').Get(),expected)
    shift(stage,root,-.004,.007)
    p.GetAttribute('points').Set(Vt.Vec3fArray([(9,9,9)]))
    reset_episode(stage,root)
    assert np.allclose(p.GetAttribute('points').Get(),expected)
    assert np.allclose(UsdGeom.Xformable(stage.GetPrimAtPath(root+'/obj_receiver_flask')).ComputeLocalToWorldTransform(0).ExtractTranslation(),[.01,-.01,0])
    assert station.GetAttribute('titration:reset_requested').Get()
    assert stage.GetPrimAtPath(root+'/Task10Fluid/SourceSystem').GetRelationship('simulationOwner').GetTargets()==[Sdf.Path(root+'/PhysicsScene')]
    shift(stage,root,-.01,.01)
    prepare_episode(stage,root)
    assert np.allclose(p.GetAttribute('points').Get(),canonical+[-.01,.01,0])


def test_mismatched_randomization_is_rejected_before_particle_mutation():
    stage,_=fixture()
    p=stage.GetPrimAtPath('/World/Task10Fluid/ReceiverParticles')
    before=list(p.GetAttribute('points').Get())
    stage.GetPrimAtPath('/World/obj_receiver_flask').GetAttribute('xformOp:translate').Set((.01,0,0))
    with pytest.raises(ValueError,match='group'):
        prepare_episode(stage,'/World')
    assert list(p.GetAttribute('points').Get())==before


def test_external_physics_scene_has_one_owner():
    stage,_=fixture('/World/_scene')
    UsdPhysics.Scene.Define(stage,'/World/CollectorPhysics')
    prepare_episode(stage,'/World/_scene','/World/CollectorPhysics')
    assert not stage.GetPrimAtPath('/World/_scene/PhysicsScene').IsActive()
    assert [str(p.GetPath()) for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]==['/World/CollectorPhysics']
    for name in ('Source','Receiver','Falling'):
        assert stage.GetPrimAtPath('/World/_scene/Task10Fluid/'+name+'System').GetRelationship('simulationOwner').GetTargets()==[Sdf.Path('/World/CollectorPhysics')]


def test_nonidentity_mount_is_rejected():
    stage,_=fixture('/World/_scene')
    UsdGeom.Xformable(stage.GetPrimAtPath('/World/_scene')).AddTranslateOp().Set((1,0,0))
    with pytest.raises(ValueError,match='identity'):
        prepare_episode(stage,'/World/_scene')


def test_vr_package_closure_registration_and_randomization(tmp_path):
    import runpy
    from pxr import UsdUtils
    from scripts.build_task10_vr import build,SOURCE,OLD,TASK_ID
    from scripts.export_task10_colleague_layout import export_layout
    if not all(p.exists() for p in (SOURCE,OLD)):
        pytest.skip('Local task10 and old-room production inputs unavailable')
    # Keep this legacy regression tied to its frozen source, not the mutable
    # shared delivery head (which can contain a newer physical contract).
    shared=tmp_path/'clean'
    export_layout(SOURCE,shared)
    package=build(tmp_path/'vr',shared=shared)
    config=runpy.run_path(str(package/'task_config.py'))['TASKS'][TASK_ID]
    assert config['physx_scene_cfg']['TimeStepsPerSecond']==240
    assert config['physx_scene_cfg']['MinPositionIterationCount']==64
    group=config['layout_randomization']['objects'][0]
    assert group['objs']==['obj_titration_station','obj_magnetic_stirrer','obj_receiver_flask']
    assert group['x_offset_range']==[-.01,.01]
    assert group['yaw_range_degrees']==[0.,0.]
    stage=Usd.Stage.Open(str(package/'scene.usd'))
    assert stage.GetDefaultPrim().GetPath()==Sdf.Path('/World')
    assert not stage.GetPrimAtPath('/World/_scene')
    assert stage.GetPrimAtPath('/World/background')
    assert stage.GetPrimAtPath('/World/vr_direct_open_light').GetAttribute('inputs:intensity').Get()==750
    for path in config['obj_prim_list']:
        assert stage.GetPrimAtPath(path.replace('/World/_scene','/World',1))
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith('/World/obj_'):
            assert not prim.HasAuthoredReferences() and not prim.HasAuthoredPayloads()
    layers,assets,missing=UsdUtils.ComputeAllDependencies(str(package/'scene.usd'))
    assert not missing
    from pathlib import Path
    assert all(Path(p.realPath).is_relative_to(package) for p in layers)
    assert all(Path(p).is_relative_to(package) for p in assets)
    for path in shared.rglob('*'):
        if path.is_file():
            assert (package/'deps/task'/path.relative_to(shared)).read_bytes()==path.read_bytes()
    changed=Usd.Stage.Open(str(shared/'scene_isaac45.usda'))
    attr=changed.GetPrimAtPath('/World/obj_titration_station').GetAttribute('titration:pbd_config')
    configuration=json.loads(attr.Get())
    configuration['runtime_contract']['physics_dt']=1/120
    attr.Set(json.dumps(configuration))
    changed.GetRootLayer().Save()
    with pytest.raises(ValueError,match='source package'):
        build(tmp_path/'mismatched',shared=shared)


def test_episode_obeys_120_contract_on_prepare_and_reset():
    stage,station=fixture()
    cfg=json.loads(station.GetAttribute('titration:pbd_config').Get())
    cfg['runtime_contract']={'physics_dt':1/120,'scene_min_position_iterations':64,'scene_max_position_iterations':64}
    station.GetAttribute('titration:pbd_config').Set(json.dumps(cfg))
    prepare_episode(stage)
    assert stage.GetPrimAtPath('/World/PhysicsScene').GetAttribute('physxScene:timeStepsPerSecond').Get()==120
    reset_episode(stage)
    assert stage.GetPrimAtPath('/World/PhysicsScene').GetAttribute('physxScene:timeStepsPerSecond').Get()==120


def test_external_scene_preserves_producer_broadphase_capacity():
    stage,station=fixture('/World/_scene')
    cfg=json.loads(station.GetAttribute('titration:pbd_config').Get())
    cfg['runtime_contract'].update(scene_gpu_found_lost_aggregate_pairs_capacity=8192,
                                   scene_gpu_total_aggregate_pairs_capacity=8192)
    station.GetAttribute('titration:pbd_config').Set(json.dumps(cfg))
    physics=UsdPhysics.Scene.Define(stage,'/World/CollectorPhysics').GetPrim()
    prepare_episode(stage,'/World/_scene','/World/CollectorPhysics')
    for name in ('gpuFoundLostAggregatePairsCapacity','gpuTotalAggregatePairsCapacity'):
        assert physics.GetAttribute('physxScene:'+name).Get()==8192
    reset_episode(stage,'/World/_scene')
    assert physics.GetAttribute('physxScene:gpuFoundLostAggregatePairsCapacity').Get()==8192

"""Task10 VR collection lifecycle; call while stopped before physics steps.

No simulator imports are required for USD preparation. The collector owns the
call order: stop -> randomize -> prepare_episode -> play. For same-layout reset:
stop -> reset_episode -> play. Do not randomize live actors.
"""
import json
import numpy as np

GROUP = ('obj_titration_station','obj_magnetic_stirrer','obj_receiver_flask')


def _clock_module():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('_task10_local_clock',Path(__file__).with_name('task10_clock.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def _paused():
    try:
        import omni.timeline
    except ImportError:
        return
    if not omni.timeline.get_timeline_interface().is_stopped():
        raise RuntimeError('Stop physics before preparing/resetting an episode')


def _path(path, root):
    if not path.startswith('/World/'):
        raise ValueError('Expected canonical /World path: '+path)
    return root+path[len('/World'):]


def _matrix(prim):
    from pxr import UsdGeom
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0))


def _local_snapshot(prim):
    from pxr import UsdGeom,Gf
    result={'order':list(prim.GetAttribute('xformOpOrder').Get() or []),'ops':{}}
    for op in UsdGeom.Xformable(prim).GetOrderedXformOps():
        value=op.Get()
        if isinstance(value,(Gf.Quatd,Gf.Quatf,Gf.Quath)):
            packed={'quat':[float(value.GetReal()),*map(float,value.GetImaginary())]}
        else:
            packed=np.asarray(value).tolist()
        result['ops'][op.GetOpName()]=packed
    return result


def _restore_local(prim,snapshot):
    from pxr import Gf
    for name,value in snapshot['ops'].items():
        attr=prim.GetAttribute(name)
        if isinstance(value,dict):
            q=value['quat']
            typ=str(attr.GetTypeName())
            value=(Gf.Quatd if typ=='quatd' else Gf.Quatf)(q[0],Gf.Vec3d(*q[1:]) if typ=='quatd' else Gf.Vec3f(*q[1:]))
        elif str(attr.GetTypeName())=='matrix4d':
            value=Gf.Matrix4d(*np.asarray(value).flatten().tolist())
        elif isinstance(value,list):
            value=tuple(value)
        attr.Set(value)
    prim.GetAttribute('xformOpOrder').Set(snapshot['order'])


def _put(prim,name,value):
    from pxr import Sdf
    typ = Sdf.ValueTypeNames.Bool if isinstance(value,bool) else Sdf.ValueTypeNames.Int if isinstance(value,int) else Sdf.ValueTypeNames.Double if isinstance(value,float) else Sdf.ValueTypeNames.String
    prim.CreateAttribute(name,typ).Set(value)


def prepare_episode(stage, scene_root='/World', physics_scene_path=None):
    """Synchronize a translated task group and capture this episode's home poses.

Supported collector mount has identity ancestry and local XY +/-1 cm, yaw=0.
Explicitly reject other mount transforms rather than mixing local/world points.
An external physics scene may be supplied; the owned scene is then deactivated.
"""
    from pxr import UsdPhysics,Vt,Sdf
    _paused()
    root=scene_root.rstrip('/')
    if not np.allclose(_matrix(stage.GetPrimAtPath(root)),np.eye(4),atol=1e-7):
        raise ValueError('VR scene mount must have identity transform')
    station=stage.GetPrimAtPath(root+'/obj_titration_station')
    cfg=json.loads(station.GetAttribute('titration:pbd_config').Get())
    clock=_clock_module()
    timing=clock.runtime_settings(cfg)
    bases=json.loads(station.GetAttribute('vr:canonical_bodies').Get())
    group=json.loads(station.GetAttribute('vr:canonical_group').Get())
    deltas=[np.linalg.inv(np.asarray(group[name])) @ _matrix(stage.GetPrimAtPath(root+'/'+name)) for name in GROUP]
    delta=deltas[0]
    expected=np.eye(4)
    expected[3,:2]=delta[3,:2]
    if (not all(np.allclose(d,delta,atol=2e-6) for d in deltas)
            or not np.allclose(delta,expected,atol=2e-6) or np.max(np.abs(delta[3,:2]))>.010002):
        raise ValueError('Task group must share one XY translation within +/-0.01m, yaw=0')
    active=[p for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]
    owned=root+'/PhysicsScene'
    chosen=physics_scene_path or (str(active[0].GetPath()) if len(active)==1 else None)
    if not chosen or not stage.GetPrimAtPath(chosen).IsA(UsdPhysics.Scene):
        raise ValueError('One valid physics scene, or an explicit collector physics_scene_path, is required')
    if any(str(p.GetPath()) not in (owned,chosen) for p in active):
        raise ValueError('Unexpected additional physics scene')
    # Validate all transforms before making any changes.
    arrays={}
    for name,item in cfg['systems'].items():
        prim=stage.GetPrimAtPath(_path(item['particle_path'],root))
        pts=np.asarray(prim.GetAttribute('vr:canonical_points').Get(),dtype=np.float32).reshape(-1,3)
        vel=np.asarray(prim.GetAttribute('vr:canonical_velocities').Get(),dtype=np.float32).reshape(-1,3)
        body=item.get('container_body_path', '/World/obj_titration_station/Instance/Burette/body_link')
        transform=np.linalg.inv(np.asarray(bases[body])) @ _matrix(stage.GetPrimAtPath(_path(body,root)))
        if not np.allclose(transform,delta,atol=2e-6):
            raise ValueError('Container body differs from the randomized group: '+body)
        arrays[name]=(prim,(pts@transform[:3,:3]+transform[3,:3]).astype(np.float32),(vel@transform[:3,:3]).astype(np.float32))
    if chosen!=owned and stage.GetPrimAtPath(owned):
        stage.GetPrimAtPath(owned).SetActive(False)
    physics=stage.GetPrimAtPath(chosen)
    physics.AddAppliedSchema('PhysxSceneAPI')
    from pxr import Gf
    UsdPhysics.Scene(physics).CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1))
    UsdPhysics.Scene(physics).CreateGravityMagnitudeAttr(9.81)
    for name,typ,value in [('enableGPUDynamics',Sdf.ValueTypeNames.Bool,True),('broadphaseType',Sdf.ValueTypeNames.Token,'GPU'),('solverType',Sdf.ValueTypeNames.Token,'TGS'),('enableCCD',Sdf.ValueTypeNames.Bool,True),('timeStepsPerSecond',Sdf.ValueTypeNames.UInt,timing['physics_hz']),('minPositionIterationCount',Sdf.ValueTypeNames.UInt,timing['min_iterations']),('maxPositionIterationCount',Sdf.ValueTypeNames.UInt,timing['max_iterations'])]:
        physics.CreateAttribute('physxScene:'+name,typ).Set(value)
    clock_sync=clock.synchronize_loaded_scene(stage,chosen)
    for name,value in clock.scene_capacity_settings(cfg).items():
        physics.CreateAttribute('physxScene:'+name,Sdf.ValueTypeNames.UInt).Set(value)
    homes={}
    for prim in stage.Traverse():
        if (prim.GetParent().GetPath()==stage.GetPrimAtPath(root).GetPath() and prim.GetName().startswith('obj_')
                or (prim.HasAPI(UsdPhysics.RigidBodyAPI) and str(prim.GetPath()).startswith(root+'/obj_'))):
            homes[str(prim.GetPath())[len(root):]]=_local_snapshot(prim)
    for name,(prim,pts,vel) in arrays.items():
        item=cfg['systems'][name]
        for attr,array in [('points',pts),('velocities',vel),('titration:initial_points',pts),('titration:initial_velocities',vel)]:
            prim.GetAttribute(attr).Set(Vt.Vec3fArray.FromNumpy(array))
        prim.CreateAttribute('widths',Sdf.ValueTypeNames.FloatArray).Set(Vt.FloatArray([item['particle_spacing_m']]*len(pts)))
        prim.CreateAttribute('ids',Sdf.ValueTypeNames.Int64Array).Set(Vt.Int64Array(range(len(pts))))
        UsdPhysics.MassAPI(prim).GetMassAttr().Set(item['per_particle_mass_kg']*len(pts))
        system=stage.GetPrimAtPath(_path(item['system_path'],root))
        system.CreateRelationship('simulationOwner').SetTargets([chosen])
        if name=='Falling':
            system.CreateAttribute('physxParticleIsosurface:isosurfaceEnabled',Sdf.ValueTypeNames.Bool).Set(False)
    _put(station,'vr:episode_home',json.dumps(homes))
    _put(station,'vr:physics_scene',chosen)
    _clear_state(stage,root,station)
    _put(station,'vr:episode_id',int(station.GetAttribute('vr:episode_id').Get() or 0)+1)
    return {'scene_root':root,'physics_dt':timing['physics_dt'],'clock_sync':clock_sync,'translation_m':delta[3,:3].tolist(),'physics_scene':chosen,'particle_counts':{n:len(a[1]) for n,a in arrays.items()}}


def _clear_state(stage,root,station):
    from pxr import UsdPhysics,Gf
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith(root+'/obj_') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            api=UsdPhysics.RigidBodyAPI(prim)
            api.CreateVelocityAttr(Gf.Vec3f(0))
            api.CreateAngularVelocityAttr(Gf.Vec3f(0))
    joint=stage.GetPrimAtPath(root+'/obj_titration_station/Instance/Burette/stopcock_joint')
    if joint:
        for name in ('drive:angular:physics:targetPosition','drive:angular:physics:targetVelocity','state:angular:physics:position','state:angular:physics:velocity'):
            joint.GetAttribute(name).Set(0.)
    for name in ('dispensed_volume_ml','released_volume_ml','inflight_volume_ml','spilled_volume_ml','conservation_error_ml','endpoint_hold_seconds','completion_hold_seconds','stopcock_angle_deg','flow_rate_ml_s','valve_open_fraction'):
        _put(station,'titration:'+name,0.)
    _put(station,'titration:completion_volume_ml',-1.)
    _put(station,'titration:burette_liquid_volume_ml',25.)
    _put(station,'titration:burette_liquid_level',1.)
    _put(station,'titration:valve_state','CLOSED')
    for name in ('task_success','overshoot','pbd_valid','controller_pose_valid'):
        _put(station,'titration:'+name,False)
    _put(station,'titration:indicator_phase','colorless')
    _put(station,'titration:pbd_error','')
    _put(station,'titration:reset_requested',True)
    cfg=json.loads(station.GetAttribute('titration:pbd_config').Get())
    _put(station,'titration:source_total_volume_ml',float(cfg['systems']['Source'].get('initial_volume_ml',0.)))
    for name,field in [('Source','source_particle_count'),('Receiver','receiver_particle_count'),('Falling','falling_particle_count')]:
        points=stage.GetPrimAtPath(_path(cfg['systems'][name]['particle_path'],root)).GetAttribute('points').Get()
        _put(station,'titration:'+field,len(points))
    shader=stage.GetPrimAtPath(_path(cfg['systems']['Receiver']['material_path'],root)+'/Shader')
    if shader:
        shader.GetAttribute('inputs:glass_color').Set(Gf.Vec3f(.97,.99,1.))


def reset_episode(stage,scene_root='/World'):
    """Restore the last prepared home before starting another same-layout trial."""
    _paused()
    root=scene_root.rstrip('/')
    station=stage.GetPrimAtPath(root+'/obj_titration_station')
    attr=station.GetAttribute('vr:episode_home')
    if not attr or not attr.Get():
        raise ValueError('Call prepare_episode before reset_episode')
    homes=json.loads(attr.Get())
    for path,matrix in sorted(homes.items(),key=lambda item:item[0].count('/')):
        _restore_local(stage.GetPrimAtPath(root+path),matrix)
    return prepare_episode(stage,root,station.GetAttribute('vr:physics_scene').Get())

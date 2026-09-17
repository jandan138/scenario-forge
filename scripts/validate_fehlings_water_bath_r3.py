"""Isaac 4.5 dynamic insertion and contact fixtures for the collision-free visual bath."""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

DEEP_FLOOR_CLEARANCE_M = 0.0015


def heating_local(profile, style='shallow', clearance=DEEP_FLOOR_CLEARANCE_M):
    """Return (x, y, z) in beaker-local metres and tilt degrees for a heating pose."""
    surface = float(profile[-1][0])
    floor = float(profile[0][0])
    if style == 'deep':
        return (0.0, 0.0, floor + clearance), 0
    if style == 'shallow':
        return (-0.020, 0.0, surface - 0.006), 55
    if style == 'shallow_upright':
        return (0.0, 0.0, surface - 0.006), 0
    raise ValueError('unsupported heating style: ' + str(style))


def color_heating_pose(profile, heating_style='shallow', phase='first'):
    """Color-replay pose. Default keeps r7–r9 shallow dip; r10 uses deep upright."""
    if heating_style == 'deep':
        return heating_local(profile, 'deep')
    if phase == 'last':
        return heating_local(profile, 'shallow_upright')
    return heating_local(profile, 'shallow')


def main(*, fixed_materials=False, five_layers=False, glass_tube=False, heating_style='shallow'):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.root=args.root.resolve()
    argv=sys.argv
    sys.argv=[argv[0]]
    from isaacsim import SimulationApp
    app=SimulationApp({'headless':True,'multi_gpu':False})
    sys.argv=argv
    if heating_style not in ('shallow', 'deep'):
        raise ValueError('unsupported heating style: ' + str(heating_style))
    completion=30 if five_layers else 60
    version='visual_five_layers_v6' if five_layers else 'visual_fixed_regions_v5' if fixed_materials else 'visual_water_contact_v3'
    report=dict(status='blocked',scene_sha256=sha256((args.root/'scene.usd').read_bytes()).hexdigest(),
                policy_version=version,process_id=os.getpid(),protocol='dynamic_insertion_and_prescribed_contact_fixtures',robot_policy_success=False,
                heating_style=heating_style)
    try:
        if glass_tube:
            manifest=json.loads((args.root/'manifest.json').read_text())
            producer_path=args.root/manifest['tube_producer_manifest']
            producer=json.loads(producer_path.read_text())
            asset_hash=sha256((producer_path.parent.parent/'asset.usd').read_bytes()).hexdigest()
            if asset_hash!=producer['asset_sha256'] or asset_hash!=manifest['tube_asset_sha256']:
                raise ValueError('r7 producer asset identity mismatch')
            report.update(package_id=manifest['package_id'],glass_tube_r7=True,tube_asset_sha256=asset_hash)
        import carb.settings
        import omni.usd
        import omni.physx
        import omni.physx.bindings._physx as pb
        from omni.isaac.dynamic_control import _dynamic_control
        from isaacsim.core.api import World
        from pxr import Usd,UsdGeom,UsdPhysics,Gf
        from scripts.fehlings_r2_state import appearance,geometry
        if fixed_materials:
            from scripts.fehlings_r5_state import appearance
            from scripts.generate_fehlings_water_bath_r5 import fixed_geometry
        if five_layers:
            from scripts.fehlings_r6_state import appearance
            from scripts.fehlings_r6_evidence import capture_visual
        from scripts.generate_fehlings_water_bath_r3 import TUBE,BEAKER,WATER
        if not app.app.get_app_version().startswith('4.5'):
            raise RuntimeError('Isaac Sim 4.5 required')
        settings=carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        settings.set_bool('/physics/suppressReadback',False)
        settings.set_bool(pb.SETTING_UPDATE_TO_USD,True)
        settings.set_bool(pb.SETTING_UPDATE_VELOCITIES_TO_USD,True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        context=omni.usd.get_context()
        context.open_stage(str(args.root/'scene.usd'))
        while context.get_stage_loading_status()[2]:
            app.update()
        for _ in range(30):
            app.update()
        stage=context.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        tube=stage.GetPrimAtPath(TUBE)
        water=stage.GetPrimAtPath(WATER)
        profile=[tuple(p) for p in water.GetAttribute('water:profile_m').Get()]
        world=World(stage_units_in_meters=1,physics_prim_path='/World/physicsScene',set_defaults=False,physics_dt=1/120,rendering_dt=1/120)
        world.reset()
        dc=_dynamic_control.acquire_dynamic_control_interface()
        tube_handle=dc.get_rigid_body(TUBE)
        bath_handle=dc.get_rigid_body(BEAKER)
        if not tube_handle or not bath_handle:
            raise RuntimeError('rigid body pose unavailable')
        snapshots=[]
        report['snapshots']=snapshots
        tick=0
        def val(name):
            return tube.GetAttribute('fehlings:'+name).Get()
        def step(n):
            nonlocal tick
            for _ in range(n):
                world.step(render=False)
                tick+=1
        def pose(handle):
            p=dc.get_rigid_body_pose(handle)
            return [float(p.p.x),float(p.p.y),float(p.p.z)],[float(p.r.x),float(p.r.y),float(p.r.z),float(p.r.w)]
        def move(handle,xyz,degrees=0):
            q=(0,math.sin(math.radians(degrees)/2),0,math.cos(math.radians(degrees)/2))
            prim=stage.GetPrimAtPath(TUBE if handle==tube_handle else BEAKER)
            prim.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*xyz))
            orient=prim.GetAttribute('xformOp:orient')
            if not orient:
                orient=UsdGeom.Xformable(prim).AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
            orient.Set(Gf.Quatf(q[3],Gf.Vec3f(*q[:3])) if str(orient.GetTypeName())=='quatf' else Gf.Quatd(q[3],Gf.Vec3d(*q[:3])))
            dc.set_rigid_body_pose(handle,_dynamic_control.Transform(xyz,q))
            if not UsdPhysics.RigidBodyAPI(prim).GetKinematicEnabledAttr().Get():
                dc.set_rigid_body_linear_velocity(handle,(0,0,0))
                dc.set_rigid_body_angular_velocity(handle,(0,0,0))
        def bath_position():
            return pose(bath_handle)[0]
        def local_position(local):
            p,q=pose(bath_handle)
            v=Gf.Rotation(Gf.Quatd(q[3],Gf.Vec3d(*q[:3]))).TransformDir(Gf.Vec3d(*local))+Gf.Vec3d(*p)
            return tuple(v)
        def capture(name):
            xyz,q=pose(tube_handle)
            bxyz,bq=pose(bath_handle)
            snap=dict(name=name,step=tick,heated_s=val('heated_seconds'),color_progress=val('color_progress'),
                stage=val('stage'),success=val('success'),immersed=val('immersed'),bath_contact=val('bath_contact'),
                reaction_stage=val('reaction_stage'),
                observation_seconds=val('observation_seconds'),tube_xyz=xyz,tube_quat_xyzw=q,beaker_xyz=bxyz,beaker_quat_xyzw=bq,
                geometry={})
            if five_layers:
                snap.update(capture_visual(stage,tube))
            else:
                snap.update(sediment_progress=val('sediment_progress'),sediment_height_m=val('sediment_height_m'),
                sample_color=list(stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sample/Shader').GetAttribute('inputs:diffuseColor').Get()),
                sample_opacity=stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sample/Shader').GetAttribute('inputs:opacity').Get(),
                sediment_opacity=stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sediment/Shader').GetAttribute('inputs:opacity').Get())
            if fixed_materials:
                for label in ('Sample', 'Sediment'):
                    shader=stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/'+label+'/Shader')
                    snap[label.lower()+'_color']=list(shader.GetAttribute('inputs:diffuseColor').Get())
                    snap[label.lower()+'_roughness']=shader.GetAttribute('inputs:roughness').Get()
            for label in (() if five_layers else ('Sample','Sediment')):
                for part in ('body','surface'):
                    relative='VisualLiquid/'+label+'/'+part
                    mesh=stage.GetPrimAtPath(TUBE+'/'+relative)
                    snap['geometry'][relative]=dict(points=[list(p) for p in mesh.GetAttribute('points').Get()],visibility=mesh.GetAttribute('visibility').Get())
                    if fixed_materials:
                        snap['geometry'][relative].update(
                            extent=[list(p) for p in mesh.GetAttribute('extent').Get()],
                            faceVertexCounts=list(mesh.GetAttribute('faceVertexCounts').Get()),
                            faceVertexIndices=list(mesh.GetAttribute('faceVertexIndices').Get()),
                            normals=str(mesh.GetAttribute('normals').Get()),
                            local_transform=str(UsdGeom.Xformable(mesh).GetLocalTransformation()))
            snapshots.append(snap)
            print(name,snap['heated_s'],snap['bath_contact'],flush=True)
            return snap
        initial_xyz=pose(tube_handle)[0]
        step(1200)
        initial=capture('initial')
        checks=dict(no_pbd_components=not any('Particle' in p.GetTypeName() or any('Particle' in a for a in p.GetAppliedSchemas()) for p in stage.TraverseAll()),
                    water_has_no_physics=not any(any('Physics' in a or 'Physx' in a for a in p.GetAppliedSchemas()) for p in Usd.PrimRange(water)),
                    rack_stable=math.dist(initial_xyz,initial['tube_xyz'])<.005)
        report['checks']=checks
        if glass_tube:
            fit=json.loads((args.root/'evidence/rack_fit.json').read_text())
            checks['glass_body_mass']=abs(dc.get_rigid_body_properties(tube_handle).mass-producer['mass_kg'])<1e-6
            start=pose(tube_handle)[0]
            trajectory=[]
            for _ in range(600):
                # Command must exceed gravity loss during a native simulation step.
                dc.set_rigid_body_linear_velocity(tube_handle,(0,0,.25))
                dc.set_rigid_body_angular_velocity(tube_handle,(0,0,0))
                step(1)
                xyz=pose(tube_handle)[0]
                trajectory.append(xyz)
                if xyz[2]>=fit['rack_top_world_m']+.015:
                    break
            extracted=capture('rack_extracted')
            checks['rack_extraction']=extracted['tube_xyz'][2]>=fit['rack_top_world_m']+.015
            for _ in range(800):
                dc.set_rigid_body_linear_velocity(tube_handle,(0,0,-.03))
                dc.set_rigid_body_angular_velocity(tube_handle,(0,0,0))
                step(1)
                xyz=pose(tube_handle)[0]
                trajectory.append(xyz)
                if xyz[2]<=start[2]+.001:
                    break
            dc.set_rigid_body_linear_velocity(tube_handle,(0,0,0))
            step(240)
            reinserted=capture('rack_reinserted')
            checks['rack_reinsertion']=math.dist(start,reinserted['tube_xyz'])<.004
            checks['rack_guided_path_clear']=max(math.hypot(p[0]-start[0],p[1]-start[1]) for p in trajectory)<.005
            report['rack_cycle']=dict(method='dynamic body, prescribed vertical velocities; no grasp claim',
                                      sampled_positions=trajectory,start=start,final=reinserted['tube_xyz'])
        colliders=[p for p in Usd.PrimRange(stage.GetPrimAtPath(BEAKER)) if p.HasAPI(UsdPhysics.CollisionAPI) and p.GetAttribute('physics:collisionEnabled').Get()]
        checks['cup_colliders_retained']=len(colliders)==3
        # Actual dynamic body passes through the fake surface and lands on the cup bottom.
        move(tube_handle,local_position((0,0,profile[-1][0]+.004)))
        depths=[]
        for _ in range(200):
            dc.set_rigid_body_linear_velocity(tube_handle,(0,0,-.03))
            step(1)
            depths.append(pose(tube_handle)[0][2]-bath_position()[2])
            if depths[-1]<profile[0][0]+.002:
                break
        for _ in range(30):
            step(1)
            depths.append(pose(tube_handle)[0][2]-bath_position()[2])
        drop=capture('dynamic_insert')
        checks['passes_water_surface']=min(depths)<profile[-1][0]-.03
        checks['cup_bottom_blocks']=min(depths)>profile[0][0]-.004
        # A low-speed lateral impulse reaches the wall before the bottom.
        move(tube_handle,local_position((.020,0,.025)))
        dc.set_rigid_body_linear_velocity(tube_handle,(.3,0,0))
        lateral=[]
        for _ in range(30):
            step(1)
            lateral.append(pose(tube_handle)[0][0]-bath_position()[0])
        checks['cup_wall_blocks']=max(lateral)<.041
        report['dynamic_insertion']=dict(relative_z_samples=depths,lateral_x_samples=lateral,final=drop['tube_xyz'])
        # Controlled trajectories isolate the relaxed contact rule from user motor skills.
        UsdPhysics.RigidBodyAPI(tube).CreateKinematicEnabledAttr(True)
        step(2)
        tube_handle=dc.get_rigid_body(TUBE)
        def reset_at(local,degrees=0):
            if glass_tube:
                # Wall-contact negative cases can move a dynamic beaker. Isolate
                # each semantic case instead of reusing its displaced/tilted pose.
                move(tube_handle,local_position((.15,0,profile[-1][0]+.080)))
                move(bath_handle,initial['beaker_xyz'])
                step(120)
            move(tube_handle,local_position(local),degrees)
            tube.GetAttribute('fehlings:reset_requested').Set(True)
            step(1)
            if val('heated_seconds')!=0:
                raise RuntimeError('reset advanced in same step')
        surface=profile[-1][0]
        cases=[('above_surface',(0,0,surface+.003),0,False),
               ('outside',(0.055,0,.05),0,False),
               ('wall_only',(.046,0,.05),0,False),
               ('upper_only',(0,0,surface+(.090 if glass_tube else .060)),180,False),
               ('shallow_contact',(0,0,surface-.006),0,True),
               ('tilted_contact',(-.020,0,surface-.006),55,True),
               ('partial_contact',(.026,0,surface-.010),0,True)]
        report['contact_cases']=[]
        for name,local,angle,expected in cases:
            reset_at(local,angle)
            step(120)
            snap=capture(name)
            checks[name]=(bool(snap['bath_contact'])==expected and (snap['heated_s']>.9 if expected else snap['heated_s']==0))
            report['contact_cases'].append(dict(name=name,expected=expected,actual=snap['bath_contact'],heated_s=snap['heated_s']))
            if name=='tilted_contact':
                q=snap['tube_quat_xyzw']
                axis=Gf.Rotation(Gf.Quatd(q[3],Gf.Vec3d(*q[:3]))).TransformDir(Gf.Vec3d(0,0,1))
                checks['actual_tilt_exceeds_old_limit']=axis[2]<math.cos(math.radians(50))
        # Show that bath translation changes the semantic water region too.
        old_bath,bq=pose(bath_handle)
        reset_at((0,0,surface-.006))
        step(3)
        contacted=bool(val('bath_contact'))
        move(bath_handle,(old_bath[0]+.15,old_bath[1],old_bath[2]))
        step(3)
        checks['bath_motion_follows']=contacted and not val('bath_contact')
        move(bath_handle,old_bath)
        step(3)
        reset_at((0,0,surface+.030))
        step(3)
        capture('outside_no_heating')
        heat_first,tilt_first=color_heating_pose(profile,heating_style,'first')
        heat_last,tilt_last=color_heating_pose(profile,heating_style,'last')
        move(tube_handle,local_position(heat_first),tilt_first)
        first_milestones=[('t3',3),('t6',6),('t9',9),('t12',12),('t15',15)] if five_layers else [('t30',30),('t37_5',37.5),('t45',45)]
        for name,threshold in first_milestones:
            for _ in range(8000):
                step(1)
                if val('heated_seconds')>=threshold:
                    break
            if val('heated_seconds')<threshold:
                capture('heating_stalled')
                raise RuntimeError('relaxed contact did not heat')
            capture(name)
            if five_layers:
                move(tube_handle,local_position((0,0,surface+.030)))
                step(2)
                capture(name+'_withdrawn')
                move(tube_handle,local_position(heat_first),tilt_first)
                step(2)
        move(tube_handle,local_position((0,0,surface+.030)))
        step(3)
        paused=capture('pause_begin')
        step(240)
        pause_end=capture('pause_end')
        checks['pause_and_geometry_freeze']=(paused['heated_s']==pause_end['heated_s'] and paused['geometry']==pause_end['geometry'] and not pause_end['success'])
        if five_layers:
            checks['pause_and_geometry_freeze'] &= paused['geometry_sha256']==pause_end['geometry_sha256']
            checks['pause_all_materials']=paused['layers']==pause_end['layers'] and paused['layer_progress']==pause_end['layer_progress']
        move(tube_handle,local_position(heat_last),tilt_last)
        last_milestones=[('t18',18),('t21',21),('t24',24),('t27',27),('t29_9',29.9),('t30',30)] if five_layers else [('t52_5',52.5),('t60',60)]
        for name,threshold in last_milestones:
            for _ in range(8000):
                step(1)
                if val('heated_seconds')>=threshold:
                    break
            capture(name)
            if five_layers:
                if name=='t29_9':
                    checks['not_ready_before_30']=val('heated_seconds')<30 and val('stage')=='heating'
                move(tube_handle,local_position((0,0,surface+.030)))
                step(2)
                capture(name+'_withdrawn')
                move(tube_handle,local_position(heat_last),tilt_last)
                step(2)
        checks['complete_at_'+str(completion)]=val('heated_seconds')==completion and val('color_progress')==1 and not val('success')
        move(tube_handle,local_position((0,0,surface+.030)))
        for _ in range(400):
            step(1)
            if val('observation_seconds')>=2:
                break
        checks['not_success_before_three_seconds']=not val('success') and val('observation_seconds')<3
        for _ in range(400):
            step(1)
            if val('success'):
                break
        observed=capture('observed')
        checks['observation_success']=bool(observed['success']) and observed['observation_seconds']>=3-1e-6
        tube.GetAttribute('fehlings:reset_requested').Set(True)
        step(1)
        reset=capture('reset')
        if glass_tube:
            checks['sample_eight_ml']=abs(val('sample_volume_ml')-8)<1e-9
            checks['new_tube_dimensions']=abs(val('mouth_height_m')-.15)<1e-9 and abs(val('outer_radius_m')-.009)<1e-9
            checks['finite_actual_poses']=all(all(math.isfinite(v) for v in snap['tube_xyz']+snap['tube_quat_xyzw']) for snap in snapshots)
        checks['reset_complete']=reset['heated_s']==0 and not reset['success'] and reset['geometry']==initial['geometry']
        checks['actual_materials']=True
        checks['actual_geometry']=True
        sample_profile=[tuple(v) for v in tube.GetAttribute('fehlings:cavity_profile_m').Get()]
        for snap in snapshots:
            look=appearance(snap['heated_s'])
            if five_layers:
                checks['actual_materials'] &= len(snap['layers'])==5 and all(
                    max(abs(a-b) for a,b in zip(actual['color'],expected['color']))<1e-5
                    and abs(actual['opacity']-expected['opacity'])<1e-5
                    and abs(actual['roughness']-expected['roughness'])<1e-5
                    for actual,expected in zip(snap['layers'],look['layers']))
                checks['actual_geometry'] &= snap['geometry_sha256']==initial['geometry_sha256']
                bounds=snap['layer_bounds_m']
                floor=sample_profile[0][0]
                top=float(tube.GetAttribute('fehlings:sample_height_m').Get())
                checks['five_equal_fixed_layers']=checks.get('five_equal_fixed_layers',True) and len(bounds)==5 and all(
                    abs(low-(floor+(top-floor)*i/5))<1e-7 and abs(high-(floor+(top-floor)*(i+1)/5))<1e-7
                    for i,(low,high) in enumerate(bounds))
                checks['layer_progress_matches']=checks.get('layer_progress_matches',True) and len(snap['layer_progress'])==5 and all(
                    abs(p-v['progress'])<1e-6 for p,v in zip(snap['layer_progress'],look['layers']))
                checks['global_progress_matches']=checks.get('global_progress_matches',True) and abs(snap['color_progress']-look['progress'])<1e-6
                checks['reset_complete'] &= reset['geometry_sha256']==initial['geometry_sha256'] and reset['layers']==initial['layers']
                if heating_style=='deep':
                    sample_top=float(tube.GetAttribute('fehlings:sample_height_m').Get())
                    water_z=val('water_surface_z')
                    color_names={'t3','t6','t9','t12','t15','t18','t21','t24','t27','t29_9','t30'}
                    checks['color_sample_below_waterline']=all(
                        snap['name'] not in color_names or snap['tube_xyz'][2]+sample_top<water_z
                        for snap in snapshots)
                continue
            checks['actual_materials'] &= (max(abs(a-b) for a,b in zip(snap['sample_color'],look['color']))<1e-5
                                          and abs(snap['sample_opacity']-look['opacity'])<1e-5
                                          and abs(snap['sediment_opacity']-look['sediment_opacity'])<1e-5)
            if fixed_materials:
                checks['actual_materials'] &= (
                    max(abs(a-b) for a,b in zip(snap['sediment_color'],look['sediment_color']))<1e-5
                    and abs(snap['sample_roughness']-look['roughness'])<1e-5
                    and abs(snap['sediment_roughness']-look['sediment_roughness'])<1e-5)
                checks['fixed_geometry_all_snapshots']=checks.get('fixed_geometry_all_snapshots',True) and snap['geometry']==initial['geometry']
                expected=fixed_geometry(sample_profile,float(tube.GetAttribute('fehlings:sample_height_m').Get()))
                expected['Sample']['body']=expected['Sample']['body'][:-1]
                checks['fixed_height_all_snapshots']=checks.get('fixed_height_all_snapshots',True) and abs(snap['sediment_height_m']-expected['sediment_height_m'])<1e-7
            else:
                expected=geometry(sample_profile,float(tube.GetAttribute('fehlings:sample_height_m').Get()),look['sediment'])
            for label in ('Sample','Sediment'):
                for part in ('body','surface'):
                    actual=snap['geometry']['VisualLiquid/'+label+'/'+part]['points']
                    checks['actual_geometry'] &= (len(actual)==len(expected[label][part]) and
                        max(abs(a-b) for p,q in zip(actual,expected[label][part]) for a,b in zip(p,q))<1e-7)
        report.update(status='pass' if all(checks.values()) else 'blocked',checks=checks,snapshots=snapshots,
                      runtime='Isaac Sim 4.5',runtime_version=app.app.get_app_version(),water_profile_m=profile,water_world_surface_z=val('water_surface_z'),
                      kinematic_trajectory_fixture=True,dynamic_collision_fixture=True)
    except Exception as error:
        import traceback
        traceback.print_exc()
        report['error']=str(error)
    finally:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n')
        app.close()
    return 0 if report['status']=='pass' else 2


if __name__=='__main__':
    raise SystemExit(main())

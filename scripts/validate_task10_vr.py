"""Task10 VR integration fixture: same physical gates after mount and randomization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--runtime',choices=['45'],default='45')
    parser.add_argument('--mount',action='store_true')
    parser.add_argument('--external-physics',action='store_true')
    parser.add_argument('--offset',type=float,nargs=2,default=[0.,0.])
    parser.add_argument('--episode-resets',type=int,default=0)
    parser.add_argument('--seconds',type=float,default=4.)
    parser.add_argument('--open-seconds',type=float,default=1.)
    parser.add_argument('--full',action='store_true')
    parser.add_argument('--motion-only',action='store_true')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--record',action='store_true')
    parser.add_argument('--trace-falling',action='store_true')
    parser.add_argument('--controller-mode',choices=['graph','post-readback'],default='graph')
    args = parser.parse_args()
    if args.motion_only:
        args.full = True
    args.package = args.package.resolve()
    args.out.mkdir(parents=True,exist_ok=True)
    meta = json.loads((args.package/'manifest.json').read_text())
    scene_root = '/World/_scene' if args.mount else '/World'
    cfg = meta['configuration']
    for item in cfg['systems'].values():
        for key in ('system_path','particle_path','material_path','container_body_path'):
            if key in item:
                item[key] = scene_root+item[key][len('/World'):]
    started = time.monotonic()
    dt = meta['physics_dt']
    report = {'status':'failed','runtime_requested':args.runtime,'pid':os.getpid(),'physics_dt':dt,
              'scope':'motion_probe' if args.motion_only else 'full_task_fixture' if args.full else 'integration_api_smoke',
              'physical_containment_qualified':False,
              'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'input_files_sha256':{p.relative_to(args.package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(args.package.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
              'manifest_sha256':hashlib.sha256((args.package/'manifest.json').read_bytes()).hexdigest(),
              'snapshots':[],'checks':{},'scene_root':scene_root,'offset_m':args.offset}
    telemetry = []
    cavity_trace = []
    cavity_violations = []
    # Small 3-column transforms are slower with an oversubscribed BLAS pool.
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    report['numpy_threads'] = 1
    sys.dont_write_bytecode = True
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False,
                         'renderer':'PathTracing' if args.render else 'RayTracedLighting',
                         'samples_per_pixel_per_frame':16})
    try:
        import numpy as np
        from task10_pbd_geometry import cavity_metrics
        import carb.settings
        import omni.usd
        import omni.physx
        import omni.physx.bindings._physx as pb
        from omni.isaac.dynamic_control import _dynamic_control
        from omni.isaac.version import get_version
        from pxr import Usd,UsdGeom,UsdPhysics,Gf
        try:
            from isaacsim.core.api import World
            from isaacsim.core.prims import SingleArticulation as Articulation
        except ImportError:
            from omni.isaac.core import World
            from omni.isaac.core.articulations import Articulation
        report['physx_errors'] = []
        def physics_error(event):
            report['physx_errors'].append({'type':int(event.type),'message':str(event.payload['errorString'])})
        error_subscription = omni.physx.get_physx_interface().get_error_event_stream().create_subscription_to_push(physics_error)
        settings = carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        for key in [pb.SETTING_UPDATE_TO_USD,pb.SETTING_UPDATE_PARTICLES_TO_USD,pb.SETTING_UPDATE_VELOCITIES_TO_USD]:
            settings.set(key,True)
        settings.set(pb.SETTING_SUPPRESS_READBACK,False)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        from omni.kit.viewport.utility import get_active_viewport
        viewport = get_active_viewport()
        if viewport:
            viewport.updates_enabled = False
        ctx = omni.usd.get_context()
        entry = args.package/'scene.usd'
        if args.mount:
            wrapper = Usd.Stage.CreateNew(str((args.out/'mounted.usda').resolve()))
            UsdGeom.SetStageMetersPerUnit(wrapper,1.)
            UsdGeom.SetStageUpAxis(wrapper,'Z')
            UsdGeom.Xform.Define(wrapper,'/World')
            UsdGeom.Xform.Define(wrapper,scene_root).GetPrim().GetReferences().AddReference(str(entry),'/World')
            wrapper.SetDefaultPrim(wrapper.GetPrimAtPath('/World'))
            wrapper.GetRootLayer().Save()
            entry = Path(wrapper.GetRootLayer().realPath)
        ctx.open_stage(str(entry))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        for _ in range(10):
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        import importlib.util
        spec = importlib.util.spec_from_file_location('delivered_task10_vr_episode',args.package/'task10_vr_episode.py')
        episode = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(episode)
        for name in (*episode.GROUP,'obj_sample_beaker','obj_context_conical_flask'):
            prim = stage.GetPrimAtPath(scene_root+'/'+name)
            attr = prim.GetAttribute('xformOp:translate')
            value = attr.Get()
            attr.Set(Gf.Vec3d(value[0]+args.offset[0],value[1]+args.offset[1],value[2]))
        physics_path = '/World/CollectorPhysics' if args.external_physics else scene_root+'/PhysicsScene'
        if args.external_physics:
            physics=UsdPhysics.Scene.Define(stage,physics_path)
            physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1))
            physics.CreateGravityMagnitudeAttr(9.81)
        report['episode_preparation'] = episode.prepare_episode(stage,scene_root,physics_path)
        report['active_physics_scenes'] = [str(p.GetPath()) for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]
        if report['active_physics_scenes'] != [physics_path]:
            raise RuntimeError('Multiple active physics scenes')
        root = scene_root+'/obj_titration_station'
        station = stage.GetPrimAtPath(root)
        bridge_namespace = {}
        if args.controller_mode == 'post-readback':
            node = stage.GetPrimAtPath(root+'/Instance/Runtime/TitrationFlowGraph/FlowController')
            exec(node.GetAttribute('inputs:script').Get(),bridge_namespace)
            stage.GetPrimAtPath(root+'/Instance/Runtime/TitrationFlowGraph').SetActive(False)
        if args.full:
            UsdPhysics.RigidBodyAPI(stage.GetPrimAtPath(scene_root+'/obj_receiver_flask')).CreateKinematicEnabledAttr(True)
            report['container_motion_driver'] = 'kinematic_targets_with_swept_collision; liquid_remains_dynamic'
            report['motion_protocol'] = 'clear80mm/2s; wobble8deg+lift25mm/2s; settle2s; return80mm/2s; settle3s'
        world = World(stage_units_in_meters=1,physics_prim_path=physics_path,
                      set_defaults=False,physics_dt=dt,rendering_dt=dt)
        articulation = world.scene.add(Articulation(root,name='station'))
        world.reset()
        bridge = bridge_namespace['Task10PbdRuntime'](stage,root) if bridge_namespace else None
        report['controller_mode'] = args.controller_mode
        report['measurement_readback'] = 'explicit_after_fetch_results'
        report['runtime_version'] = list(get_version())
        report['world_reported_dt'] = world.get_physics_dt()
        dc = _dynamic_control.acquire_dynamic_control_interface()
        dof = articulation.dof_names.index('stopcock_joint')
        receiver = dc.get_rigid_body(scene_root+'/obj_receiver_flask')
        receiver_home = dc.get_rigid_body_pose(receiver)
        kinematic_view = None
        if args.full:
            import omni.physics.tensors
            motion_view = omni.physics.tensors.create_simulation_view('numpy')
            motion_view.set_subspace_roots('/')
            kinematic_view = motion_view.create_rigid_body_view(scene_root+'/obj_receiver_flask')
        sets = {name: UsdGeom.Points(stage.GetPrimAtPath(item['particle_path'])) for name,item in cfg['systems'].items()}
        t = 0.
        frame = 0
        phase = 'settle'
        records = []
        snapshot_records = []
        snapshot_folder = args.out/'snapshot_frames'
        snapshot_folder.mkdir(exist_ok=True)
        telemetry = []
        paths = [str(p.GetPath()) for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
        handles = {path:dc.get_rigid_body(path) for path in paths}
        camera_product = annotator = None
        cavity_trace = []
        cavity_violations = []
        cavity_max_outside = {name:0 for name in cfg['systems'] if name!='Falling'}
        cavity_step_count = 0
        report['cavity_sampling'] = 'every_physics_step'
        cavity_configured = all(
            'cavity_profile_local_m' in item for name,item in cfg['systems'].items() if name != 'Falling')

        def cavity_state(measure_surface=True):
            result = {}
            if not cavity_configured:
                return result
            for name,item in cfg['systems'].items():
                if name == 'Falling':
                    continue
                q = dc.get_rigid_body_pose(handles[item['container_body_path']])
                rotation = np.array(Gf.Matrix3d(Gf.Quatd(q.r.w,Gf.Vec3d(q.r.x,q.r.y,q.r.z))))
                points = np.asarray(sets[name].GetPointsAttr().Get(),dtype=float).reshape(-1,3)
                local = (points-np.array([q.p.x,q.p.y,q.p.z])) @ rotation.T
                radius = cfg.get('particle_system_parameters',{}).get(name,{}).get(
                    'physxParticleIsosurface:surfaceDistance',item['particle_spacing_m']*.8)
                result[name] = cavity_metrics(local,item,surface_radius_m=radius,measure_surface=measure_surface)
            return result

        def val(key):
            return station.GetAttribute('titration:'+key).Get()

        def pose(handle):
            q = dc.get_rigid_body_pose(handle)
            return [q.p.x,q.p.y,q.p.z,q.r.x,q.r.y,q.r.z,q.r.w]

        def angle(value):
            radians = np.array([np.deg2rad(value)])
            articulation.set_joint_positions(radians,joint_indices=np.array([dof]))
            articulation._articulation_view.set_joint_position_targets(radians.reshape(1,1),joint_indices=np.array([dof]))

        def step(seconds):
            nonlocal t,frame,cavity_step_count
            for _ in range(round(seconds/dt)):
                omni.physx.get_physx_interface().update_simulation(dt,t)
                omni.physx.get_physx_simulation_interface().fetch_results()
                # Sample points and rigid poses from the same completed step.
                omni.physx.get_physx_interface().update_transformations(False,True,True)
                if bridge is not None:
                    bridge.update(dt)
                if report['physx_errors']:
                    raise RuntimeError('PhysX reported an error: '+report['physx_errors'][-1]['message'])
                t += dt
                frame += 1
                if cavity_configured:
                    cavities = cavity_state(measure_surface=False)
                    cavity_step_count += 1
                    failed = {}
                    for name,item in cavities.items():
                        cavity_max_outside[name] = max(cavity_max_outside[name],item['outside_count'])
                        if not item['contained']:
                            failed[name] = item
                    if failed:
                        cavity_violations.append({'time':t,'phase':phase,'systems':failed})
                if frame % max(1,round(1/(30*dt))) == 0:
                    # Drain Kit/isosurface authoring queues without another
                    # physics step; World.render temporarily disables playSimulations.
                    before = (val('released_volume_ml'),val('endpoint_hold_seconds'))
                    world.render()
                    if before != (val('released_volume_ml'),val('endpoint_hold_seconds')):
                        raise RuntimeError('Application refresh unexpectedly advanced the task')
                    data = {'t':t,'phase':phase,'received_ml':val('dispensed_volume_ml'),
                            'released_ml':val('released_volume_ml'),'inflight_ml':val('inflight_volume_ml'),
                            'spilled_ml':val('spilled_volume_ml'),'color_phase':val('indicator_phase'),
                            'valid':val('pbd_valid'),'error':val('pbd_error'),'success':val('task_success')}
                    if args.trace_falling:
                        falling = sets['Falling']
                        data['falling_sample'] = {
                            'ids':list(falling.GetIdsAttr().Get())[:24],
                            'points':np.asarray(falling.GetPointsAttr().Get()).reshape(-1,3)[:24].tolist(),
                            'velocities':np.asarray(falling.GetVelocitiesAttr().Get()).reshape(-1,3)[:24].tolist()}
                    telemetry.append(data)
                    if cavity_configured:
                        cavity_trace.append({'time':t,'phase':phase,'systems':cavity_state()})
                    if args.record and not phase.startswith('miss_target'):
                        records.append({'time':t,'phase':phase,'particles':{n:np.array(p.GetPointsAttr().Get(),dtype=np.float32) for n,p in sets.items()},
                                        'body_poses':np.array([pose(handles[p]) for p in paths]),'color':list(stage.GetPrimAtPath(cfg['systems']['Receiver']['material_path']+'/Shader').GetAttribute('inputs:glass_color').Get()),
                                        'state':data})

        def snap(name):
            keys = ['pbd_valid','pbd_error','dispensed_volume_ml','released_volume_ml','inflight_volume_ml',
                    'spilled_volume_ml','source_total_volume_ml','conservation_error_ml','indicator_phase',
                    'task_success','overshoot','endpoint_hold_seconds','stopcock_angle_deg',
                    'source_particle_count','receiver_particle_count','falling_particle_count']
            data = {'name':name,'time':t,**{k:val(k) for k in keys}}
            data['cavity'] = cavity_state()
            data['particle_bounds'] = {}
            for n,p in sets.items():
                pts = np.asarray(p.GetPointsAttr().Get(),dtype=float).reshape(-1,3)
                data['particle_bounds'][n] = {'count':len(pts),'finite':bool(np.isfinite(pts).all()),
                    'total_mass_kg':float(UsdPhysics.MassAPI(p.GetPrim()).GetMassAttr().Get()),
                    'min':pts.min(axis=0).tolist() if len(pts) else None,
                    'max':pts.max(axis=0).tolist() if len(pts) else None,
                    'z_q995':float(np.quantile(pts[:,2],.995)) if len(pts) else None}
            report['snapshots'].append(data)
            snapshot_index=len(snapshot_records)
            snapshot_file=snapshot_folder/f'{snapshot_index:05d}.npz'
            np.savez_compressed(snapshot_file,**{n:np.asarray(p.GetPointsAttr().Get(),dtype=np.float32).reshape(-1,3) for n,p in sets.items()},
                body_poses=np.array([pose(handles[path]) for path in paths]),
                color=np.asarray(stage.GetPrimAtPath(cfg['systems']['Receiver']['material_path']+'/Shader').GetAttribute('inputs:glass_color').Get()))
            snapshot_records.append({'time':t,'phase':name,'state':{'received_ml':data['dispensed_volume_ml'],'released_ml':data['released_volume_ml'],'color_phase':data['indicator_phase'],'success':data['task_success']}})
            report.setdefault('snapshot_files_sha256',{})[snapshot_file.name]=hashlib.sha256(snapshot_file.read_bytes()).hexdigest()

            print('SNAP',json.dumps(data),flush=True)
            if args.render:
                capture(name)
            return data

        def capture(name):
            nonlocal camera_product,annotator
            import omni.replicator.core as rep
            from PIL import Image
            if camera_product is None:
                camera = UsdGeom.Camera.Define(stage,'/World/ReviewCamera')
                camera.CreateHorizontalApertureAttr(36)
                camera.CreateFocalLengthAttr(28)
                camera.CreateClippingRangeAttr(Gf.Vec2f(.001,20))
                eye = Gf.Vec3d(.50,-1.15,1.35)
                target = Gf.Vec3d(-.03,-.1767,1.175)
                camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse())
                camera_product = rep.create.render_product(str(camera.GetPath()),(1920,1080))
                annotator = rep.AnnotatorRegistry.get_annotator('rgb')
                annotator.attach([camera_product])
            camera_product.hydra_texture.set_updates_enabled(True)
            for _ in range(3):
                rep.orchestrator.step(rt_subframes=4,pause_timeline=True,delta_time=0)
            Image.fromarray(annotator.get_data()).save(args.out/(name+'.png'))
            if name=='initial':
                camera=UsdGeom.Camera(stage.GetPrimAtPath('/World/ReviewCamera'))
                attr=camera.GetPrim().GetAttribute('xformOp:transform')
                original=attr.Get()
                attr.Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(2.,-3.,2.3),Gf.Vec3d(0.,0.,1.),Gf.Vec3d(0,0,1)).GetInverse())
                for _ in range(3):
                    rep.orchestrator.step(rt_subframes=4,pause_timeline=True,delta_time=0)
                Image.fromarray(annotator.get_data()).save(args.out/'room_overview.png')
                attr.Set(original)

            if name in ('initial','endpoint','overshoot'):
                camera=UsdGeom.Camera(stage.GetPrimAtPath('/World/ReviewCamera'))
                attr=camera.GetPrim().GetAttribute('xformOp:transform')
                original=attr.Get()
                focal=camera.GetFocalLengthAttr().Get()
                attr.Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.24,-.62,1.05),Gf.Vec3d(-.02,-.1867,.90),Gf.Vec3d(0,0,1)).GetInverse())
                camera.GetFocalLengthAttr().Set(58.)
                for _ in range(3):
                    rep.orchestrator.step(rt_subframes=4,pause_timeline=True,delta_time=0)
                Image.fromarray(annotator.get_data()).save(args.out/(name+'_detail.png'))
                attr.Set(original)
                camera.GetFocalLengthAttr().Set(focal)
            camera_product.hydra_texture.set_updates_enabled(False)
            import omni.timeline
            omni.timeline.get_timeline_interface().play()

        angle(0)
        step(args.seconds)
        first = snap('initial')
        if not first['pbd_valid']:
            raise RuntimeError(first['pbd_error'])
        report['checks']['closed_no_release'] = first['released_volume_ml'] == 0
        if args.full:
            phase = 'gentle_flask_motion'
            # Clear the fixed nozzle before tilting: lifting/tilting directly
            # beneath it would drive the flask rim through the burette tip.
            for segment in ('clear_nozzle','wobble','return_aligned'):
                if segment=='return_aligned':
                    phase='settle_before_return'
                    step(2.)
                phase = 'flask_wobble' if segment=='wobble' else segment
                for k in range(round(2/dt)):
                    alpha = k*dt/2
                    smooth_phase = alpha*alpha*(3-2*alpha)
                    x_offset = .08*smooth_phase if segment=='clear_nozzle' else .08*(1-smooth_phase) if segment=='return_aligned' else .08
                    tilt = 8*np.sin(smooth_phase*2*np.pi) if segment=='wobble' else 0.
                    lift = .025*np.sin(np.pi*alpha)**2 if segment=='wobble' else 0.
                    rotation = Gf.Rotation(Gf.Vec3d(1,0,0),tilt).GetQuat()
                    q = (float(rotation.GetImaginary()[0]),float(rotation.GetImaginary()[1]),float(rotation.GetImaginary()[2]),float(rotation.GetReal()))
                    target = np.array([[receiver_home.p.x+x_offset,receiver_home.p.y,receiver_home.p.z+lift,*q]],dtype=np.float32)
                    kinematic_view.set_kinematic_targets(target,np.array([0],dtype=np.uint32))
                    step(dt)
            kinematic_view.set_kinematic_targets(np.array([[receiver_home.p.x,receiver_home.p.y,receiver_home.p.z,
                receiver_home.r.x,receiver_home.r.y,receiver_home.r.z,receiver_home.r.w]],dtype=np.float32),
                np.array([0],dtype=np.uint32))
            phase = 'settle_after_motion'
            step(3)
            snap('after_motion')
            if not args.motion_only:
                phase = 'coarse_titration'
                angle(90)
                step(4.85)
                snap('coarse')
                phase = 'fine_titration'
                angle(20)
                for _ in range(round(15/dt)):
                    step(dt)
                    if val('dispensed_volume_ml') >= 15.2:
                        break
                angle(0)
                phase = 'closed_pale_endpoint'
                step(4)
                endpoint = snap('endpoint')
                report['checks']['actual_arrival'] = endpoint['dispensed_volume_ml'] > 15
                report['checks']['endpoint'] = endpoint['task_success'] and endpoint['indicator_phase']=='endpoint_pale_pink'
                phase = 'reset'
                station.GetAttribute('titration:reset_requested').Set(True)
                step(3)
                reset = snap('reset')
                report['checks']['reset'] = (not reset['task_success'] and not reset['overshoot']
                    and reset['dispensed_volume_ml']==0 and reset['released_volume_ml']==0
                    and reset['indicator_phase']=='colorless' and all(
                        reset['particle_bounds'][name]['count']==item['count'] for name,item in cfg['systems'].items()))
                phase = 'overshoot'
                angle(90)
                step(7)
                angle(0)
                step(4)
                over = snap('overshoot')
                report['checks']['overshoot'] = over['overshoot'] and not over['task_success'] and over['indicator_phase']=='overshoot'
                phase = 'miss_target_reset'
                station.GetAttribute('titration:reset_requested').Set(True)
                step(1)
                phase = 'miss_target_position'
                for k in range(round(2/dt)):
                    alpha = (k+1)*dt/2
                    offset = .08*alpha*alpha*(3-2*alpha)
                    target = np.array([[receiver_home.p.x+offset,receiver_home.p.y,receiver_home.p.z,
                        receiver_home.r.x,receiver_home.r.y,receiver_home.r.z,receiver_home.r.w]],dtype=np.float32)
                    kinematic_view.set_kinematic_targets(target,np.array([0],dtype=np.uint32))
                    step(dt)
                phase = 'miss_target'
                angle(90)
                step(.5)
                angle(0)
                step(1)
                miss = snap('miss_target')
                report['checks']['miss_target'] = (miss['dispensed_volume_ml']==0 and miss['released_volume_ml']>1
                    and miss['spilled_volume_ml']>1 and miss['indicator_phase']=='colorless' and not miss['task_success'])
        else:
            phase = 'short_titration'
            angle(90)
            step(args.open_seconds)
            angle(0)
            phase = 'short_closed'
            step(1)
            drop = snap('first_dose')
            report['checks']['actual_arrival'] = drop['dispensed_volume_ml'] > 0
        flowing = [row for row in telemetry if row['phase'] in ('short_titration','coarse_titration','fine_titration')
                   and row['released_ml'] is not None and row['released_ml'] > .5]
        if not args.motion_only:
            report['checks']['continuous_delivery_while_open'] = bool(flowing) and all(
                row['inflight_ml'] < .25 and row['received_ml'] > 0 for row in flowing)
        report['checks']['conservation'] = all(abs(row['conservation_error_ml'])<1e-7 for row in report['snapshots'])
        initial_mass = sum(item['initial_total_mass_kg'] for item in cfg['systems'].values())
        report['checks']['set_mass_conservation'] = all(
            abs(sum(item['total_mass_kg'] for item in row['particle_bounds'].values())-initial_mass)<1e-7
            and all(abs(item['total_mass_kg']-item['count']*cfg['systems'][name]['per_particle_mass_kg'])<1e-7
                    for name,item in row['particle_bounds'].items()) for row in report['snapshots'])
        report['checks']['no_physx_errors'] = not report['physx_errors']
        assert error_subscription is not None
        report['checks']['controller_valid'] = all(row['pbd_valid'] for row in report['snapshots'])
        if cavity_configured:
            report['checks']['containment'] = cavity_step_count > 0 and not cavity_violations
            report['cavity_steps'] = cavity_step_count
            report['cavity_max_outside'] = cavity_max_outside
            (args.out/'cavity_violations.json').write_text(json.dumps(cavity_violations))
            report['checks']['initial_surface_height'] = all(
                item['surface_height_pass'] for item in first['cavity'].values())
            report['physical_containment_qualified'] = report['checks']['containment']
            (args.out/'cavity_trace.json').write_text(json.dumps(cavity_trace))
        elif args.full:
            report['checks']['containment'] = False
        if args.full and not args.motion_only:
            report['checks']['delivery_efficiency'] = all(
                row['spilled_volume_ml'] < .02 and row['inflight_volume_ml'] < .02
                for row in report['snapshots'] if row['name'] in ('endpoint','overshoot'))
        report['episode_reset_results'] = []
        for repeat in range(args.episode_resets):
            world.stop()
            app.update()
            report['episode_reset_results'].append(episode.reset_episode(stage,scene_root))
            world.reset()
            dof = articulation.dof_names.index('stopcock_joint')
            handles = {path:dc.get_rigid_body(path) for path in paths}
            angle(0)
            phase = 'collection_reset_'+str(repeat)
            step(1)
            clean = snap(phase)
            report['checks']['collection_reset_'+str(repeat)] = (clean['dispensed_volume_ml']==0 and not clean['task_success'] and clean['indicator_phase']=='colorless' and clean['pbd_valid'] and all(x['contained'] for x in clean['cavity'].values()))
        report['checks']['containment'] = cavity_step_count>0 and not cavity_violations
        report['cavity_steps'] = cavity_step_count
        report['cavity_max_outside'] = cavity_max_outside
        report['checks']['no_physx_errors'] = not report['physx_errors']
        report['physical_containment_qualified'] = report['checks']['containment']
        report['status'] = 'pass' if all(report['checks'].values()) else 'failed'
        (args.out/'telemetry.jsonl').write_text('\n'.join(json.dumps(row) for row in telemetry)+'\n')
        if records:
            # Variable particle counts require one compressed chunk per frame;
            # numeric arrays only, no object/pickle serialization.
            frames = args.out/'frames'
            frames.mkdir(exist_ok=True)
            index = []
            report['recording_frames_sha256'] = {}
            for i,r in enumerate(records):
                np.savez_compressed(frames/f'{i:05d}.npz',**r['particles'],body_poses=r['body_poses'],color=r['color'])
                report['recording_frames_sha256'][f'{i:05d}.npz'] = hashlib.sha256((frames/f'{i:05d}.npz').read_bytes()).hexdigest()
                index.append({'time':r['time'],'phase':r['phase'],'state':r['state']})
            (args.out/'recording.json').write_text(json.dumps({'body_paths':paths,'frames':index,
                'manifest_sha256':report['manifest_sha256'],'runtime_version':report['runtime_version'],
                'physics_dt':dt,'scope':'demonstration; miss-target negative test retained in telemetry'},indent=2))
            report['recording_sha256'] = hashlib.sha256((args.out/'recording.json').read_bytes()).hexdigest()
    except BaseException:
        report['exception'] = traceback.format_exc()
        print(report['exception'],flush=True)
    finally:
        if cavity_violations:
            (args.out/'cavity_violations.json').write_text(json.dumps(cavity_violations))
        if cavity_trace:
            (args.out/'cavity_trace.json').write_text(json.dumps(cavity_trace))
        if telemetry:
            (args.out/'telemetry.jsonl').write_text('\n'.join(json.dumps(row) for row in telemetry)+'\n')
        if locals().get('snapshot_records'):
            (args.out/'snapshot_recording.json').write_text(json.dumps({'body_paths':paths,'frames':snapshot_records,'manifest_sha256':report['manifest_sha256'],'runtime_version':report['runtime_version']},indent=2))
            report['snapshot_recording_sha256']=hashlib.sha256((args.out/'snapshot_recording.json').read_bytes()).hexdigest()
        report['wall_seconds'] = time.monotonic()-started
        report['simulated_seconds'] = locals().get('t',0.)
        report['physics_time_ratio'] = report['simulated_seconds']/report['wall_seconds']
        (args.out/'report.json').write_text(json.dumps(report,indent=2))
        print('RESULT',report['status'],report['checks'],flush=True)
        app.close(wait_for_replicator=False)
    return 0 if report['status']=='pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

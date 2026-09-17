"""Isaac 4.5 bounded qualification of task09 with a shallow powder bottle."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.task09_powder_protocol import prescribed_spoon
from scripts.powder_weighing_protocol import measurement_check
from scripts.clone_task09_powder_r5_10 import hold_grains_kinematic
from scripts.task09_powder_evidence import (
    authored_linear_damping_matches,
    authored_pbd_dry_powder_matches,
    authored_pbd_viscous_particles_matches,
    authored_velocity_cap_matches,
    NEAR_FULL_REVISIONS,
    PBD_REVISIONS,
    R51_DEPENETRATION_VELOCITY,
    R51_LINEAR_VELOCITY,
    R58_LINEAR_DAMPING,
    R59_SLEEP_THRESHOLD,
    R59_STABILIZATION_THRESHOLD,
    R510_KINEMATIC_FROM_S,
    R510_KINEMATIC_UNTIL_S,
    authored_sleep_matches,
    summarize_rest_motion,
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--runtime',choices=['45'],default='45')
    p.add_argument('--mode',choices=['settle','scoop','calibration','hold'],default='scoop')
    p.add_argument('--seconds',type=float,default=50)
    p.add_argument('--solver',choices=['TGS','PGS'])
    p.add_argument('--iterations',type=int)
    p.add_argument('--wake-all',action='store_true')
    args = p.parse_args()
    args.root = args.root.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    cfg = json.loads((args.root/'scene_config.json').read_text())
    entry = args.root/cfg['entrypoints'][args.runtime]
    report = dict(status='failed',mode=args.mode,requested_runtime=args.runtime,
                  entry_sha256=hashlib.sha256(entry.read_bytes()).hexdigest(),
                  scene_sha256=hashlib.sha256((args.root/'scene.usda').read_bytes()).hexdigest(),robot_grasp_verified=False,
                  requested_seconds=args.seconds,
                  validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  protocol_sha256=hashlib.sha256((Path(__file__).parent/'task09_powder_protocol.py').read_bytes()).hexdigest())
    compact = 'inner_profile' in cfg
    if compact:
        from scripts.compact_powder_protocol import prescribed_spoon as compact_spoon, cavity_mask, bed_depth, fill_level, near_full_check, exclusive_loose_count, in_spoon_mask
        report['protocol_sha256'] = hashlib.sha256((Path(__file__).parent/'compact_powder_protocol.py').read_bytes()).hexdigest()
        report['profile_revision'] = cfg.get('revision')
        report['initial_state'] = cfg.get('initial_state','generated')
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False})
    try:
        import numpy as np
        import omni.usd
        import omni.physx
        import omni.physics.tensors as tensors
        import carb.settings
        import carb.logging
        from pxr import Gf,Usd,UsdGeom,UsdPhysics,Sdf
        from scripts.clone_task09_powder_r6_0 import (
            read_pbd_particle_xyz, spoon_weir_collision_enabled, SPOON_COLLISION_SCOPE,
        )
        try:
            from isaacsim.core.api import World
            from isaacsim.core.prims import SingleArticulation as Articulation
        except ImportError:
            from omni.isaac.core import World
            from omni.isaac.core.articulations import Articulation
        report['runtime'] = app.app.get_app_version()
        fatal_errors = []
        log_stream = app.app.get_log_event_stream()
        def on_log(event):
            if event.payload['level']>=carb.logging.LEVEL_ERROR:
                fatal_errors.append(str(event.payload))
        # Consume queued log events on the main thread. A synchronous Python
        # logger invoked by a PhysX worker can deadlock while the main thread waits.
        logger_handle = log_stream.create_subscription_to_pop(on_log,name='task09 physics errors')
        settings = carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        ctx = omni.usd.get_context()
        ctx.open_stage(str(entry))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        if args.solver:
            stage.GetPrimAtPath('/World/PhysicsScene').GetAttribute('physxScene:solverType').Set(args.solver)
        report['solver'] = stage.GetPrimAtPath('/World/PhysicsScene').GetAttribute('physxScene:solverType').Get()
        if args.iterations:
            for prim in stage.Traverse():
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                    prim.CreateAttribute('physxRigidBody:solverPositionIterationCount',Sdf.ValueTypeNames.Int).Set(args.iterations)
            stage.GetPrimAtPath(cfg['paths']['balance']).GetAttribute('physxArticulation:solverPositionIterationCount').Set(args.iterations)
        report['position_iterations_override'] = args.iterations
        paths = cfg['paths']
        spoon_prim = stage.GetPrimAtPath(paths['spoon'])
        # Only this bounded fixture drives the ordinary dynamic spoon kinematically.
        if args.mode in ('scoop','hold'):
            UsdPhysics.RigidBodyAPI(spoon_prim).CreateKinematicEnabledAttr(True)
            spoon_prim.GetAttribute('physxRigidBody:enableCCD').Set(False)
        pbd = cfg.get('revision') in PBD_REVISIONS
        if pbd:
            if cfg.get('pbd_fluid'):
                if not authored_pbd_viscous_particles_matches(cfg):
                    raise ValueError('r6.x viscous-particle trial needs pbd_viscous, fluid=true, particle display, and authored rest offsets')
            elif not authored_pbd_dry_powder_matches(cfg):
                raise ValueError('r6.x requires dry PBD powder_kind and authored solid/rigid rest offsets')
        powder_paths = [f'/World/obj_powder_grain_{i:05d}' for i in range(cfg['count'])]
        pbd_set = stage.GetPrimAtPath(cfg.get('paths',{}).get('powder_pbd','/World/powder_pbd/ParticleSet'))
        if pbd:
            assert pbd_set.IsValid()
            assert bool(pbd_set.GetAttribute('physxParticle:fluid').Get()) is bool(cfg.get('pbd_fluid'))
            powder_paths = [str(pbd_set.GetPath())]
        else:
            for path in powder_paths:
                prim = stage.GetPrimAtPath(path)
                assert prim.IsA(UsdGeom.Xform) and prim.HasAPI(UsdPhysics.RigidBodyAPI)
                assert not any(child.HasAPI(UsdPhysics.RigidBodyAPI) for child in Usd.PrimRange(prim) if child!=prim)
        if cfg.get('revision')=='r5.10':
            if (cfg.get('grain_rest_kinematic_from_s')!=R510_KINEMATIC_FROM_S
                    or cfg.get('grain_rest_kinematic_until_s')!=R510_KINEMATIC_UNTIL_S):
                raise ValueError('r5.10 grain rest kinematic hold missing or wrong')
            report['authored_grain_rest_kinematic_from_s'] = R510_KINEMATIC_FROM_S
            report['authored_grain_rest_kinematic_until_s'] = R510_KINEMATIC_UNTIL_S
        dt = 1/cfg['physics_hz']
        import omni.physx.bindings._physx as pb
        def enable_live_pbd_usd():
            settings.set(pb.SETTING_UPDATE_TO_USD, bool(pbd))
            settings.set(pb.SETTING_UPDATE_PARTICLES_TO_USD, bool(pbd))
            settings.set_bool(pb.SETTING_SUPPRESS_READBACK, False)
            settings.set_bool('/physics/updateVelocitiesToUsd',False)
        enable_live_pbd_usd()
        world = World(physics_dt=dt,rendering_dt=1/30,physics_prim_path='/World/PhysicsScene',set_defaults=False)
        world.get_physics_context().enable_gpu_dynamics(True)
        world.get_physics_context().set_broadphase_type('GPU')
        scale = world.scene.add(Articulation(paths['balance'],name='balance'))
        enable_live_pbd_usd()
        world.reset()
        enable_live_pbd_usd()
        log_stream.pump()
        if fatal_errors:
            raise RuntimeError('Physics initialization error: '+fatal_errors[0])
        report['world_manager_dt'] = world.get_physics_dt()
        report['authored_physics_hz'] = stage.GetPrimAtPath('/World/PhysicsScene').GetAttribute('physxScene:timeStepsPerSecond').Get()
        report['update_particles_to_usd'] = bool(settings.get(pb.SETTING_UPDATE_PARTICLES_TO_USD))
        if cfg.get('revision')=='r5.1':
            for path in powder_paths:
                grain = stage.GetPrimAtPath(path)
                linear = grain.GetAttribute('physxRigidBody:maxLinearVelocity').Get()
                depen = grain.GetAttribute('physxRigidBody:maxDepenetrationVelocity').Get()
                if not authored_velocity_cap_matches(linear, depen):
                    raise ValueError('r5.1 grain velocity caps missing or wrong on '+path)
            report['authored_grain_max_linear_velocity'] = R51_LINEAR_VELOCITY
            report['authored_grain_max_depenetration_velocity'] = R51_DEPENETRATION_VELOCITY
        if cfg.get('revision')=='r5.8':
            for path in powder_paths:
                grain = stage.GetPrimAtPath(path)
                damping = grain.GetAttribute('physxRigidBody:linearDamping').Get()
                if not authored_linear_damping_matches(damping):
                    raise ValueError('r5.8 grain linearDamping missing or wrong on '+path)
            report['authored_grain_linear_damping'] = R58_LINEAR_DAMPING
        if cfg.get('revision')=='r5.9':
            for path in powder_paths:
                grain = stage.GetPrimAtPath(path)
                sleep = grain.GetAttribute('physxRigidBody:sleepThreshold').Get()
                stab = grain.GetAttribute('physxRigidBody:stabilizationThreshold').Get()
                if not authored_sleep_matches(sleep, stab):
                    raise ValueError('r5.9 grain sleep thresholds missing or wrong on '+path)
            report['authored_grain_sleep_threshold'] = R59_SLEEP_THRESHOLD
            report['authored_grain_stabilization_threshold'] = R59_STABILIZATION_THRESHOLD
        sim = tensors.create_simulation_view('numpy')
        sim.set_subspace_roots('/')
        powder = None if pbd else sim.create_rigid_body_view(paths['powder_pattern'])
        spoon = sim.create_rigid_body_view(paths['spoon'])
        bottle = sim.create_rigid_body_view(paths['bottle'])
        boat = sim.create_rigid_body_view(paths['boat'])
        aview = sim.create_articulation_view(paths['balance'])
        contact_view = sim.create_rigid_contact_view(paths['balance']+'/Instance/WeighingPan')
        from omni.isaac.dynamic_control import _dynamic_control
        dc = _dynamic_control.acquire_dynamic_control_interface()
        wake_handles = [] if pbd or not args.wake_all else [dc.get_rigid_body(path) for path in powder_paths]
        # Articulations have a separate view; never treat their placement root
        # as an ordinary rigid actor. Grain arrays are already recorded in batch.
        body_paths = [str(prim.GetPath()) for prim in stage.GetPrimAtPath('/World').GetChildren()
                      if prim.HasAPI(UsdPhysics.RigidBodyAPI) and not prim.GetName().startswith('obj_powder_grain_')]
        body_views = [sim.create_rigid_body_view(path) for path in body_paths]
        report['observed_body_paths'] = body_paths
        report['wake_all_override'] = args.wake_all
        if pbd:
            authored_points = np.array(UsdGeom.Points(pbd_set).GetPointsAttr().Get(), dtype=np.float64)
            assert len(authored_points)==cfg['count']
            mass = np.full(cfg['count'], float(cfg['mass_per_grain_kg']), dtype=np.float64)
            report['powder_kind'] = 'pbd_solid'
        else:
            mass = powder.get_masses().copy().reshape(-1)
            assert powder.count == cfg['count'] and list(powder.prim_paths)==powder_paths
            assert np.allclose(mass,cfg['mass_per_grain_kg'],rtol=1e-4,atol=1e-12)
        report['mass_per_grain_kg'] = float(mass[0])
        report['total_powder_mass_g'] = float(mass.sum()*1000)
        if not pbd:
            inertia = powder.get_inertias().copy().reshape(-1,3,3)
            report['inertia_diagonal_min'] = np.diagonal(inertia,axis1=1,axis2=2).min(0).tolist()
        report['boat_runtime_mass_kg'] = boat.get_masses().tolist()
        report['boat_runtime_inertia'] = boat.get_inertias().tolist()
        link_names = aview.shared_metatype.link_names
        pan_index = link_names.index('WeighingPan')
        button = scale.dof_names.index('RightTarePress')
        scale.set_joint_positions(np.array([0.]),joint_indices=np.array([button]))
        def pan_point(local):
            pose = aview.get_link_transforms()[0,pan_index]
            rot = Gf.Rotation(Gf.Quatd(float(pose[6]),Gf.Vec3d(*map(float,pose[3:6]))))
            return np.array(rot.TransformDir(Gf.Vec3d(*local)))+pose[:3]
        prim = stage.GetPrimAtPath(paths['balance'])
        def val(name):
            return prim.GetAttribute('balance:'+name).Get()
        def powder_transforms():
            if pbd:
                xyz = read_pbd_particle_xyz(pbd_set)
                out = np.zeros((len(xyz),7), dtype=np.float64)
                out[:,:3] = xyz
                out[:,6] = 1.0
                return out
            return powder.get_transforms().copy()
        initial_tool = spoon.get_transforms()[0].copy()[[0,1,2,6,3,4,5]]
        initial_powder = powder_transforms()
        initial_bottle = bottle.get_transforms()[0].copy()
        ids = np.array([0],dtype=np.uint32)
        target = spoon.get_transforms().copy()
        if args.mode=='hold':
            target[0] = [-.08,-.065,1.02,0.,0.,0.,1.]
            spoon.set_transforms(target,ids)
            initial_tool = target[0,[0,1,2,6,3,4,5]].copy()
            loaded = initial_powder.copy()
            for j in range(64):
                loaded[j,:3] = target[0,:3]+np.array([.083+(j%8)*.0013,((j//8)-3.5)*.0013,.005])
            if not pbd:
                indices = np.arange(powder.count,dtype=np.uint32)
                powder.set_transforms(loaded,indices)
                powder.set_velocities(np.zeros((powder.count,6),dtype=np.float32),indices)
        link_paths = [paths['balance']+'/Instance/'+name for name in link_names]
        rows,points,rotations,body_states,link_states,steps = [],[],[],[],[],[]
        last_case = -1
        moved_boat = False
        removed_boat = False
        reset_sent = False
        frozen_powder = None
        rest_from = float(cfg.get('grain_rest_kinematic_from_s') or 0)
        rest_until = float(cfg.get('grain_rest_kinematic_until_s') or 0)
        powder_ids = np.arange(cfg['count'] if pbd else powder.count, dtype=np.uint32)
        calibration_counts = cfg.get('calibration_counts',[0,128,512,1024,0])
        ccd_attrs = [] if pbd else [stage.GetPrimAtPath(path).GetAttribute('physxRigidBody:enableCCD') for path in powder_paths]
        restore_ccd = False
        weir_window = cfg.get('pbd_spoon_weir_carry_window_s') if args.mode == 'scoop' else None
        weir_attrs = []
        if weir_window and cfg.get('pbd_spoon_bowl_rim'):
            for name in cfg['pbd_spoon_bowl_rim']:
                prim = stage.GetPrimAtPath(f'{SPOON_COLLISION_SCOPE}/{name}')
                if not prim:
                    raise ValueError('Missing spoon weir '+name)
                weir_attrs.append(prim.GetAttribute('physics:collisionEnabled'))
        weir_on = False
        start = time.perf_counter()
        for i in range(round(args.seconds/dt)):
            t = i*dt
            if weir_attrs:
                enabled = spoon_weir_collision_enabled(t, weir_window)
                if enabled != weir_on:
                    with Sdf.ChangeBlock():
                        for attr in weir_attrs:
                            attr.Set(bool(enabled))
                    omni.physx.get_physx_simulation_interface().flush_changes()
                    weir_on = enabled
            if restore_ccd:
                with Sdf.ChangeBlock():
                    for attr in ccd_attrs:
                        attr.Set(True)
                omni.physx.get_physx_simulation_interface().flush_changes()
                restore_ccd = False
            if t>=2 and not moved_boat and args.mode in ('scoop','calibration'):
                pose = boat.get_transforms().copy()
                pose[0,:3] = pan_point((0,.020,.174))
                pose[0,3:] = [0,0,0,1]
                boat.set_transforms(pose,ids)
                boat.set_velocities(np.zeros((1,6),dtype=np.float32),ids)
                moved_boat = True
            if 6<=t<6.1 and args.mode in ('scoop','calibration'):
                scale.set_joint_positions(np.array([.0014]),joint_indices=np.array([button]))
            bottle_pose = bottle.get_transforms()[0].copy()
            receiver = boat.get_transforms()[0,:3].copy()+np.array([0.,-.005,0.])
            command,phase = (compact_spoon(t,initial_tool,bottle_pose[:3],receiver,cfg) if compact
                             else prescribed_spoon(t,initial_tool,bottle_pose[:3],receiver))
            if args.mode!='scoop':
                command,phase = tuple(initial_tool),args.mode
            target[0] = [*command[:3],*command[4:],command[3]]
            if args.mode in ('scoop','hold'):
                spoon.set_kinematic_targets(target,ids)
            if args.mode=='calibration' and t>=9:
                case = min(int((t-9)//5),4)
                if case!=last_case:
                    count = calibration_counts[case]
                    transforms = initial_powder.copy()
                    spacing = cfg.get('grain_spacing_m',.00135)
                    for j in range(count):
                        transforms[j,:3] = receiver+np.array([((j%18)-8.5)*spacing,(((j//18)%16)-7.5)*spacing,.004+(j//288)*spacing])
                    indices = np.arange(cfg['count'] if pbd else powder.count,dtype=np.uint32)
                    # A prescribed calibration teleport must not become a CCD
                    # sweep from the source bottle across intervening equipment.
                    with Sdf.ChangeBlock():
                        for attr in ccd_attrs:
                            attr.Set(False)
                    omni.physx.get_physx_simulation_interface().flush_changes()
                    if pbd:
                        UsdGeom.Points(pbd_set).GetPointsAttr().Set(transforms[:,:3].tolist())
                    else:
                        powder.set_transforms(transforms,indices)
                        powder.set_velocities(np.zeros((powder.count,6),dtype=np.float32),indices)
                    restore_ccd = True
                    last_case = case
                phase = f'known_load_{calibration_counts[last_case]}'
            if args.mode=='calibration' and t>=34:
                if not removed_boat:
                    pose = boat.get_transforms().copy()
                    pose[0,:3] = [-.26,-.08,cfg['tabletop_z']+.012]
                    boat.set_transforms(pose,ids)
                    boat.set_velocities(np.zeros((1,6),dtype=np.float32),ids)
                    removed_boat = True
                phase = 'boat_removed'
                if t>=39:
                    if not reset_sent:
                        prim.GetAttribute('balance:reset_requested').Set(True)
                        reset_sent = True
                    phase = 'instrument_reset'
            if frozen_powder is not None and not pbd:
                powder.set_transforms(frozen_powder, powder_ids)
                powder.set_velocities(np.zeros((powder.count,6), dtype=np.float32), powder_ids)
            tick = time.perf_counter()
            for handle in wake_handles:
                dc.wake_up_rigid_body(handle)
            omni.physx.get_physx_interface().update_simulation(dt,t)
            omni.physx.get_physx_simulation_interface().fetch_results()
            if rest_until > 0 and hold_grains_kinematic(t+dt, rest_until, rest_from):
                if frozen_powder is None:
                    frozen_powder = powder_transforms()
                    report['grain_rest_kinematic_held_s'] = t+dt
                elif not pbd:
                    powder.set_transforms(frozen_powder, powder_ids)
                    powder.set_velocities(np.zeros((powder.count,6), dtype=np.float32), powder_ids)
            elif frozen_powder is not None:
                report['grain_rest_kinematic_released_s'] = t+dt
                frozen_powder = None
            log_stream.pump()
            if fatal_errors:
                raise RuntimeError('Physics engine error: '+fatal_errors[0])
            steps.append((time.perf_counter()-tick)*1000)
            if i%(cfg['physics_hz']//30):
                continue
            grain = frozen_powder.copy() if frozen_powder is not None else powder_transforms()
            if not np.isfinite(grain).all():
                raise RuntimeError('Nonfinite grain state')
            bp = bottle.get_transforms()[0].copy()
            bowl = boat.get_transforms()[0].copy()
            tool = spoon.get_transforms()[0].copy()
            def local_to(pose):
                r = Gf.Matrix3d(Gf.Rotation(Gf.Quatd(float(pose[6]),Gf.Vec3d(*map(float,pose[3:6])))).GetInverse())
                return (grain[:,:3]-pose[:3])@np.array(r)
            local = local_to(bp)
            if cfg.get('revision') in NEAR_FULL_REVISIONS and not rows:
                report['initial_fill_level'] = fill_level(local,cfg)
            if compact:
                within = cavity_mask(local,cfg)
                in_bottle = within&(local[:,2]>=cfg['false_floor_m']-.001)&(local[:,2]<cfg['bottle_height_m']+.01)
                below_insert = within&(local[:,2]<cfg['false_floor_m']-.001)&(local[:,2]>.003)
            else:
                in_bottle = (np.linalg.norm(local[:,:2],axis=1)<.0285)&(local[:,2]>=cfg['false_floor_m']-.0008)&(local[:,2]<.155)
                below_insert = (np.linalg.norm(local[:,:2],axis=1)<.027)&(local[:,2]<cfg['false_floor_m']-.001)&(local[:,2]>.003)
            boat_local = local_to(bowl)
            in_boat = (abs(boat_local[:,0])<.027)&(abs(boat_local[:,1])<.037)&(boat_local[:,2]>-.006)&(boat_local[:,2]<.030)
            tool_local = local_to(tool)
            in_spoon = in_spoon_mask(tool_local, cfg) if compact else ((tool_local[:,0]>.067)&(tool_local[:,0]<.101)
                        &(abs(tool_local[:,1])<.009)&(tool_local[:,2]>.001)&(tool_local[:,2]<.012))
            loose_count = exclusive_loose_count(in_bottle, in_spoon, in_boat) if compact else int((~in_bottle & ~in_spoon & ~in_boat).sum())
            row = dict(time_s=t+dt,phase=phase,bottle_count=int(in_bottle.sum()),below_insert_count=int(below_insert.sum()),
                       spoon_count=int(in_spoon.sum()),boat_count=int(in_boat.sum()),boat_region_g=float(mass[in_boat].sum()*1000),
                       loose_count=loose_count,below_table_count=int((grain[:,2]<cfg['tabletop_z']-.003).sum()),
                       bottle_shift_m=float(np.linalg.norm(bp[:3]-initial_bottle[:3])),
                       **{k:val(k) for k in ('gross_g','net_g','tare_g','valid','stable','tared','status','error','tare_pending','lcd_readout')})
            row['post_fetch_contact_g'] = -float(contact_view.get_net_contact_forces(dt)[0,2])/9.81*1000
            row['callback_contact_g'] = val('contact_raw_gross_g')
            row['callback_joint_g'] = val('joint_gross_g')
            row['boat_xyz'] = bowl[:3].tolist()
            if compact and i%cfg['physics_hz']==0:
                row['bed_depth'] = bed_depth(local,cfg)
            rows.append(row)
            points.append(grain[:,:3].copy())
            rotations.append(grain[:,[6,3,4,5]].copy())
            body_states.append(np.stack([view.get_transforms()[0].copy() for view in body_views]))
            link_states.append(aview.get_link_transforms()[0].copy())
            if i%cfg['physics_hz']==0:
                print('SAMPLE',row,flush=True)
        report.update(rows=rows,physics_dt=dt,wall_seconds=time.perf_counter()-start,
                      step_ms_p50=float(np.percentile(steps,50)),step_ms_p95=float(np.percentile(steps,95)))
        if points and rows[-1]['time_s'] >= 15 - 1/30 - dt:
            report['rest_motion'] = summarize_rest_motion(points, [r['time_s'] for r in rows], t_end=15.0)
        report['calibration_teleport_ccd_reset'] = args.mode=='calibration'
        checks = dict(finite=True,root_bodies=True,powder_mass=True,no_engine_errors=not fatal_errors,
                      no_leak_below_insert=not any(r['below_insert_count'] for r in rows),
                      no_below_table=not any(r['below_table_count'] for r in rows))
        if cfg.get('initial_state')=='presettled':
            checks['near_full_initial_state'] = near_full_check(report['initial_fill_level'])
        if args.mode=='settle':
            checks['retained'] = rows[-1]['bottle_count']==cfg['count']
            if compact:
                report['settled_bed'] = bed_depth(local,cfg)
                checks['deep_powder_bed'] = .010<=report['settled_bed']['surface_depth_median_m']<=.012
                if cfg.get('initial_state')=='presettled':
                    report['settled_fill_level'] = fill_level(local,cfg)
                    checks['near_full_settled_state'] = near_full_check(report['settled_fill_level'])
        elif args.mode=='hold':
            checks['spoon_retains_known_grains'] = rows[-1]['spoon_count']==64
        elif args.mode=='scoop':
            carried = [r for r in rows if 33<=r['time_s']<35]
            checks.update(tare=any(r['tared'] for r in rows),transfer=rows[-1]['boat_count']>=32,
                          sustained_carry=bool(carried) and all(r['spoon_count']>=32 for r in carried),
                          valid_stable=rows[-1]['valid'] and rows[-1]['stable'])
            report['force_region_crosscheck'] = measurement_check(rows[-30:],rows[-1]['boat_region_g'],.01)
            if pbd:
                report['region_mass_g'] = rows[-1]['boat_region_g']
            else:
                checks['positive_force'] = rows[-1]['net_g']>.03
                checks['force_region_agreement'] = report['force_region_crosscheck']['passed']
        else:
            cases = []
            for case,count in enumerate(calibration_counts):
                end = 9+(case+1)*5
                cases.append(measurement_check([r for r in rows if end-1<=r['time_s']<end],count*float(mass[0])*1000,.01))
            report['calibration'] = cases
            checks['known_loads'] = all(c['passed'] for c in cases)
            if args.seconds>=43:
                report['boat_removed'] = measurement_check([r for r in rows if 38<=r['time_s']<39],-10.,.1)
                report['instrument_reset'] = measurement_check([r for r in rows if 42<=r['time_s']<43],0.,.1)
                checks['boat_removed'] = report['boat_removed']['passed']
                checks['instrument_reset'] = report['instrument_reset']['passed'] and not rows[-1]['tared']
        report.update(checks=checks,status='passed' if all(checks.values()) else 'failed')
        np.savez_compressed(args.out/'states.npz',times=[r['time_s'] for r in rows],positions=points,orientations=rotations,
                            body_paths=body_paths,body_poses=body_states,link_paths=link_paths,link_poses=link_states,
                            paths=powder_paths,balance_net_g=[r['net_g'] for r in rows],phases=[r['phase'] for r in rows],
                            balance_stable=[r['stable'] for r in rows],balance_valid=[r['valid'] for r in rows],
                            tare_pending=[r['tare_pending'] for r in rows],lcd_readout=[r['lcd_readout'] for r in rows])
        logger_handle.unsubscribe()
    except BaseException:
        report.update(status='failed',exception=traceback.format_exc())
        print(report['exception'],flush=True)
    finally:
        report['engine_errors'] = locals().get('fatal_errors',[])
        (args.out/'report.json').write_text(json.dumps(report,indent=2))
        print('REPORT',args.out,report['status'],flush=True)
        app.close(wait_for_replicator=False)


if __name__=='__main__':
    main()

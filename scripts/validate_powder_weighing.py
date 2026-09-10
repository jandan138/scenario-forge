"""Bounded powder transfer/load-cell fixture. No robot or episode runner."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.powder_weighing_protocol import spoon_target, measurement_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['scoop','calibration','body_contact'], default='scoop')
    parser.add_argument('--seconds', type=float, default=28)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    report = dict(status='failed',mode=args.mode,scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),robot_grasp_verified=False)
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False})
    try:
        import numpy as np
        import carb.settings
        import omni.usd
        import omni.physx
        import omni.physics.tensors as tensors
        from pxr import Gf, PhysxSchema
        from scripts.balance_force_state import vertical_mass_g
        from isaacsim.core.api import World
        from isaacsim.core.prims import SingleArticulation
        from omni.isaac.dynamic_control import _dynamic_control
        meta = json.loads(args.scene.with_suffix('.json').read_text())
        hz = meta['config']['physics_hz']
        dt = 1/hz
        offset = meta['workspace_offset']
        rx = meta['receiver_x']
        settings = carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        ctx = omni.usd.get_context()
        ctx.open_stage(str(args.scene.resolve()))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        PhysxSchema.PhysxContactReportAPI.Apply(stage.GetPrimAtPath('/World/obj_analytical_balance/Instance/WeighingPan')).CreateThresholdAttr(0.)
        world = World(physics_dt=dt,rendering_dt=1/30,physics_prim_path='/World/PhysicsScene',set_defaults=False)
        world.get_physics_context().enable_gpu_dynamics(True)
        world.get_physics_context().set_broadphase_type('GPU')
        root = '/World/obj_analytical_balance'
        scale = world.scene.add(SingleArticulation(root,name='balance'))
        world.reset()
        settings.set_bool('/physics/updateToUsd',False)
        settings.set_bool('/physics/updateVelocitiesToUsd',False)
        sim = tensors.create_simulation_view('numpy')
        sim.set_subspace_roots('/')
        powder = sim.create_rigid_body_view('/World/Powder/g_*')
        spoon = sim.create_rigid_body_view('/World/Spoon')
        boat = sim.create_rigid_body_view('/World/Pan')
        articulation = sim.create_articulation_view(root)
        pan_contacts = sim.create_rigid_contact_view(root+'/Instance/WeighingPan')
        if pan_contacts.sensor_count != 1:
            raise RuntimeError('Expected one pan contact sensor')
        link_names = articulation.shared_metatype.link_names
        pan_index = link_names.index('WeighingPan')
        masses = powder.get_masses().copy().reshape(-1)
        if len(masses) != meta['config']['count'] or not np.allclose(masses,meta['mass_per_grain_kg'],rtol=1e-4,atol=1e-12):
            raise RuntimeError('Runtime grain mass/count mismatch')
        report['mass_per_grain_g'] = float(masses[0]*1000)
        report['total_mass_g'] = float(masses.sum()*1000)
        report['asset_sha256'] = meta['balance_asset_sha256']
        prim = stage.GetPrimAtPath(root)
        def val(name):
            return prim.GetAttribute('balance:'+name).Get()
        target = spoon.get_transforms().copy()
        ids = np.array([0],dtype=np.uint32)
        tare_idx = scale.dof_names.index('RightTarePress')
        dc = _dynamic_control.acquire_dynamic_control_interface()
        boat_handle = dc.get_rigid_body('/World/Pan')
        balance_handle = dc.get_articulation(root)
        joint_indices = np.array([tare_idx])
        scale.set_joint_positions(np.array([0.]),joint_indices=joint_indices)
        rows, positions, orientations, tools, times, body_poses, step_ms = [], [], [], [], [], [], []
        initial_powder = powder.get_transforms().copy()
        calibration_counts = [0,128,512,1024,0]
        last_case = -1
        removed_boat = False
        reset_sent = False
        body_paths = [root+'/Instance/'+name for name in link_names]+['/World/Pan']
        start = time.perf_counter()
        for i in range(round(args.seconds*hz)):
            t = i*dt
            pos, angle, phase = spoon_target(t,rx,offset[2])
            if args.mode != 'scoop':
                pos,angle,phase = (rx+.065,0,offset[2]+.065),0.,'calibration'
            q = Gf.Rotation(Gf.Vec3d(0,1,0),angle).GetQuat()
            target[0] = [*pos,*q.GetImaginary(),q.GetReal()]
            spoon.set_kinematic_targets(target,ids)
            if 3 <= t < 3.1:
                scale.set_joint_positions(np.array([.0014]),joint_indices=joint_indices)
            if args.mode != 'scoop' and t >= 5:
                case = min(int((t-5)//4),len(calibration_counts)-1)
                if case != last_case:
                    count = calibration_counts[case]
                    transforms = initial_powder.copy()
                    # Prescribed known-load placement is a separate calibration fixture.
                    # Unloaded grains are parked in the source, never destroyed.
                    transforms[:,2] += .01
                    boat_pose = boat.get_transforms()[0]
                    for j in range(count):
                        transforms[j,:3] = boat_pose[:3]+np.array([((j%18)-8.5)*.00135,(((j//18)%16)-7.5)*.00135,.003+(j//288)*.00135])
                    if args.mode == 'body_contact':
                        transforms = initial_powder.copy()
                        if case in (1,3):
                            transforms[0,:3] = [.098,-.009,.133]
                    powder.set_transforms(transforms,np.arange(len(masses),dtype=np.uint32))
                    powder.set_velocities(np.zeros((len(masses),6),dtype=np.float32),np.arange(len(masses),dtype=np.uint32))
                    last_case = case
                phase = f'known_load_{calibration_counts[last_case]}' if args.mode == 'calibration' else f'body_contact_{last_case in (1,3)}'
            if args.mode == 'calibration' and t >= 25:
                if not removed_boat:
                    pose = boat.get_transforms().copy()
                    pose[0,:3] = [-.2,0,.004]
                    boat.set_transforms(pose,ids)
                    boat.set_velocities(np.zeros((1,6),dtype=np.float32),ids)
                    removed_boat = True
                phase = 'boat_removed'
                if t >= 29:
                    if not reset_sent:
                        prim.GetAttribute('balance:reset_requested').Set(True)
                        reset_sent = True
                    phase = 'reset'
            tick = time.perf_counter()
            dc.wake_up_articulation(balance_handle)
            dc.wake_up_rigid_body(boat_handle)
            omni.physx.get_physx_interface().update_simulation(dt,t)
            omni.physx.get_physx_simulation_interface().fetch_results()
            step_ms.append((time.perf_counter()-tick)*1000)
            if i % (hz//30):
                continue
            transforms = powder.get_transforms().copy()
            p = transforms[:,:3]
            if not np.isfinite(transforms).all():
                raise RuntimeError('Nonfinite particle state')
            boat_pose = boat.get_transforms()[0].copy()
            rotation = Gf.Rotation(Gf.Quatd(float(boat_pose[6]),Gf.Vec3d(*map(float,boat_pose[3:6]))))
            inverse = np.array(Gf.Matrix3d(rotation.GetInverse()))
            local = (p-boat_pose[:3]) @ inverse
            in_boat = (abs(local[:,0])<.017)&(abs(local[:,1])<.015)&(local[:,2]>-.0007)&(local[:,2]<.025)
            row = dict(time_s=t+dt,phase=phase,**{k:val(k) for k in ['gross_g','net_g','tare_g','stable','valid','tared','status','error']},
                       receiver_region_count=int(in_boat.sum()),region_mass_g=float(masses[in_boat].sum()*1000),
                       below_ground_count=int((p[:,2]<-.001).sum()))
            links = articulation.get_link_transforms()[0].copy()
            force = articulation.get_link_incoming_joint_force()[0,pan_index].copy()
            row['post_fetch_joint_gross_g'] = vertical_mass_g(force[:3],links[pan_index,3:],9.81,50.)
            row['pan_contact_gross_g'] = -float(pan_contacts.get_net_contact_forces(dt)[0,2])/9.81*1000
            rows.append(row)
            positions.append(p.copy())
            orientations.append(transforms[:,[6,3,4,5]].copy())
            observed_tool = spoon.get_transforms()[0].copy()
            tools.append(observed_tool[[0,1,2,6,3,4,5]])
            times.append(t+dt)
            body_poses.append(np.concatenate([links,boat_pose[None]],axis=0))
            if i % hz == 0:
                print('SAMPLE',row,'step_ms',step_ms[-1],flush=True)
        report.update(runtime=app.app.get_app_version(),physics_dt=dt,rows=rows,
                      wall_seconds=time.perf_counter()-start,step_ms_p50=float(np.percentile(step_ms,50)),
                      step_ms_p95=float(np.percentile(step_ms,95)),workspace_offset=offset)
        checks = dict(finite=True,no_below_ground=not any(r['below_ground_count'] for r in rows),
                      tared=any(r['tared'] for r in rows), final_valid=rows[-1]['valid'],final_stable=rows[-1]['stable'])
        if args.mode == 'scoop':
            checks.update(transferred=rows[-1]['receiver_region_count']>50,force_increased=rows[-1]['net_g']>.05)
            # Region membership is only a cross-check in this isolated fixture.
            report['settled_region_crosscheck'] = measurement_check(rows[-30:],rows[-1]['region_mass_g'],.1)
            checks['force_region_agreement'] = report['settled_region_crosscheck']['passed']
        elif args.mode == 'calibration':
            cases = []
            for case,count in enumerate(calibration_counts):
                end = 5+(case+1)*4
                window = [r for r in rows if end-1 <= r['time_s'] < end]
                item = measurement_check(window,count*float(masses[0])*1000,.1)
                item['count'] = count
                cases.append(item)
            report['calibration'] = cases
            checks['known_loads'] = all(c['passed'] for c in cases)
            if args.seconds >= 32:
                removed = [r for r in rows if 28 <= r['time_s'] < 29]
                reset = [r for r in rows if 31 <= r['time_s'] < 32]
                report['boat_removal'] = measurement_check(removed,-meta['receiver_mass_kg']*1000,.1)
                report['reset'] = measurement_check(reset,0.,.1)
                checks['boat_removal'] = report['boat_removal']['passed']
                checks['reset'] = report['reset']['passed'] and all(not r['tared'] for r in reset)
        else:
            cases = []
            for case in range(5):
                end = 5+(case+1)*4
                window = [r for r in rows if end-1 <= r['time_s'] < end]
                item = measurement_check(window,0.,.1)
                item['grain_on_body'] = case in (1,3)
                cases.append(item)
            report['body_contact_regression'] = cases
            checks['body_contact_readout_preserved'] = all(c['passed'] for c in cases)
        report.update(checks=checks,status='passed' if all(checks.values()) else 'failed')
        paths = [f'/World/Powder/g_{i:05d}' for i in range(len(masses))]
        # Tensor ordering is checked against the documented explicit prim list.
        if list(powder.prim_paths) != paths:
            raise RuntimeError('Unexpected tensor body ordering')
        np.savez_compressed(args.out/'states.npz',times=times,positions=positions,orientations=orientations,
                            tools=tools,masses=masses,paths=paths,workspace_offset=offset,body_paths=body_paths,
                            body_poses=body_poses,balance_net_g=[r['net_g'] for r in rows],phases=[r['phase'] for r in rows])
    except BaseException:
        report.update(status='failed',exception=traceback.format_exc())
        print(report['exception'],flush=True)
    finally:
        (args.out/'report.json').write_text(json.dumps(report,indent=2))
        print('REPORT',args.out,report['status'],flush=True)
        app.close(wait_for_replicator=False)


if __name__ == '__main__':
    main()

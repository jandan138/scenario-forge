"""No-robot prescribed placement and stability fixture, not an episode runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--runtime', choices=['41', '45'], required=True)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    args.package = args.package.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {'status': 'failed', 'pid': os.getpid(), 'runtime_requested': args.runtime,
              'scene_sha256': hashlib.sha256((args.package/'assets/composed/scene.usdc').read_bytes()).hexdigest(),
              'physics_dt': 1/120, 'snapshots': [], 'stability': [], 'checks': {}}
    report['validator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fingerprint = hashlib.sha256()
    for folder in ('assets', 'scene'):
        for f in sorted((args.package/folder).rglob('*')):
            if f.is_file():
                fingerprint.update(str(f.relative_to(args.package)).encode())
                fingerprint.update(hashlib.sha256(f.read_bytes()).digest())
    report['runtime_content_sha256'] = fingerprint.hexdigest()
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'multi_gpu': False})
    try:
        import numpy as np
        import carb.settings
        import omni.usd
        import omni.physx
        from pxr import UsdGeom, UsdPhysics, Gf
        from omni.isaac.dynamic_control import _dynamic_control
        try:
            from isaacsim.core.api import World
            from isaacsim.core.prims import SingleArticulation as Articulation
        except ImportError:
            from omni.isaac.core import World
            from omni.isaac.core.articulations import Articulation
        report['kit_version'] = app.app.get_app_version()
        from omni.isaac.version import get_version
        report['runtime_version'] = list(get_version())
        settings = carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in', False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in', True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        ctx = omni.usd.get_context()
        ctx.open_stage(str(args.package/f'scene/demo{args.runtime}.usda'))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        for _ in range(10):
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        world = World(stage_units_in_meters=1, physics_prim_path='/World/PhysicsScene',
                      set_defaults=False, physics_dt=1/120, rendering_dt=1/120)
        root = '/World/obj_analytical_balance'
        articulation = world.scene.add(Articulation(root, name='balance'))
        world.reset()
        dc = _dynamic_control.acquire_dynamic_control_interface()
        index = articulation.dof_names.index('RightTarePress')
        articulation._articulation_view.set_joint_position_targets(np.array([[0.]]), joint_indices=np.array([index]))
        prim = stage.GetPrimAtPath(root)
        paths = [str(p.GetPath()) for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)
                 and p.GetAttribute('physics:rigidBodyEnabled').Get() is not False]
        handles = {p: dc.get_rigid_body(p) for p in paths}
        assert all(handles.values()), 'Some authored bodies were rejected by PhysX'
        samples = [f'/World/obj_grain_{i:02d}' for i in range(1, 6)]
        staging = [(-.60+i*.04, -.30) for i in range(5)]
        report['staging_xy'] = staging
        boat = '/World/obj_weighing_boat'
        masses = {p: float(stage.GetPrimAtPath(p).GetAttribute('physics:mass').Get())*1000 for p in samples}
        report['mass_g'] = masses
        report['total_g'] = sum(masses.values())
        local_vertices = {}
        for path in samples:
            p = stage.GetPrimAtPath(path)
            matrix = UsdGeom.Xformable(p).ComputeLocalToWorldTransform(0)
            rigid = Gf.Matrix4d().SetRotate(matrix.ExtractRotation())
            rigid.SetTranslateOnly(matrix.ExtractTranslation())
            verts = []
            from pxr import Usd
            for child in Usd.PrimRange(p):
                if child.IsA(UsdGeom.Mesh):
                    relative = UsdGeom.Xformable(child).ComputeLocalToWorldTransform(0)*rigid.GetInverse()
                    verts.extend(relative.Transform(Gf.Vec3d(*v)) for v in UsdGeom.Mesh(child).GetPointsAttr().Get())
            local_vertices[path] = np.array(verts)
        t = 0.
        step_index = 0
        phase = 'initial_rest'
        recording = False
        records = []
        telemetry = []
        series = []
        previous_vertices = {}
        report['stability_velocity_metric'] = 'max per-vertex displacement / actual physics dt, sampled every 1/120 s'
        report['engine_velocity_policy'] = 'reported independently; not interchangeable with geometric motion'

        def val(key):
            return prim.GetAttribute('balance:'+key).Get()

        def pose(path):
            q = dc.get_rigid_body_pose(handles[path])
            return [q.p.x, q.p.y, q.p.z, q.r.x, q.r.y, q.r.z, q.r.w]

        def step(n):
            nonlocal t, step_index
            for _ in range(n):
                omni.physx.get_physx_interface().update_simulation(1/120, t)
                omni.physx.get_physx_simulation_interface().fetch_results()
                t += 1/120
                step_index += 1
                positions, bottom_z, geometry_speed, velocities = [], [], [], []
                for path in samples:
                    q = pose(path)
                    r = np.array(Gf.Matrix3d(Gf.Quatd(q[6], Gf.Vec3d(*q[3:6]))))
                    vertices = local_vertices[path] @ r + np.array(q[:3])
                    positions.append(vertices.mean(axis=0).tolist())
                    bottom_z.append(float(vertices[:, 2].min()))
                    previous = previous_vertices.get(path, vertices)
                    geometry_speed.append(float(np.linalg.norm(vertices-previous, axis=1).max()*120))
                    previous_vertices[path] = vertices
                    v = dc.get_rigid_body_linear_velocity(handles[path])
                    velocities.append([v.x, v.y, v.z])
                series.append((t, positions, velocities, bottom_z, geometry_speed))
                if step_index % 4 == 0:
                    telemetry.append({'t': t, 'phase': phase, 'net_g': val('net_g'),
                                      'lcd': val('lcd_readout'), 'valid': val('valid'),
                                      'supported': list(val('supported_paths') or []),
                                      'positions': positions, 'velocities': velocities, 'geometry_bottom_z': bottom_z})
                    if recording and args.record:
                        records.append((t, [pose(p) for p in paths], phase,
                                        val('lcd_readout'), val('net_g'), val('success')))

        def snap(name):
            keys = ['gross_g', 'net_g', 'tare_g', 'valid', 'stable', 'status', 'error',
                    'lcd_readout', 'tared', 'success', 'supported_sample_count', 'supported_paths']
            item = {'name': name, 'time': t, **{k: val(k) for k in keys}}
            item['supported_paths'] = list(item['supported_paths'] or [])
            item['sample_positions'] = {p: pose(p)[:3] for p in samples}
            item['boat_pose'] = pose(boat)
            item['diagnostics'] = json.loads(val('support_diagnostics') or '{}')
            report['snapshots'].append(item)
            print('SNAP', json.dumps({k: v for k, v in item.items() if k != 'diagnostics'}), flush=True)
            return item

        def move(path, xyz, quat=None):
            h = handles[path]
            quat = pose(path)[3:] if quat is None else quat
            dc.set_rigid_body_pose(h, _dynamic_control.Transform(tuple(map(float, xyz)), tuple(map(float, quat))))
            dc.set_rigid_body_linear_velocity(h, (0, 0, 0))
            dc.set_rigid_body_angular_velocity(h, (0, 0, 0))
            dc.wake_up_rigid_body(h)

        def smooth_move(path, target, seconds=.6):
            start = np.array(pose(path)[:3])
            for i in range(int(seconds*120)):
                u = (i+1)/(seconds*120)
                u = u*u*(3-2*u)
                move(path, start*(1-u)+np.array(target)*u)
                step(1)

        def stability(name, seconds=15):
            start = len(series)
            step(round(seconds*120))
            rows = series[start:]
            # Discard the first five seconds after release/initialization.
            tail = [r for r in rows if r[0] >= rows[0][0] + 5 - 1e-6]
            if not tail:
                return
            xyz = np.array([r[1] for r in tail])
            vel = np.array([r[2] for r in tail if r[0] >= tail[-1][0]-2])
            drift = np.max(np.linalg.norm(xyz-xyz[0], axis=2), axis=0)
            speed = np.max(np.linalg.norm(vel, axis=2), axis=0)
            motion_speed = np.max([r[4] for r in tail if r[0] >= tail[-1][0]-2], axis=0)
            bottom = np.array([r[3] for r in tail])
            item = {'name': name, 'drift_m': drift.tolist(), 'max_tail_speed_m_s': speed.tolist(),
                    'max_tail_geometry_speed_m_s': motion_speed.tolist(),
                    'raw_engine_speed_below_1mm_s': bool((speed <= .001).all()),
                    'finite': bool(np.isfinite(xyz).all()),
                    'minimum_geometry_z': bottom.min(axis=0).tolist(),
                    'above_table': bool((bottom >= .754).all()),
                    'pass': bool(np.isfinite(xyz).all() and (drift <= .001).all()
                                 and (motion_speed <= .001).all() and (bottom >= .754).all())}
            report['stability'].append(item)
            print('STABILITY', json.dumps(item), flush=True)

        stability('original_layout', 8 if args.quick else 30)
        initial_probe = snap('initial_layout')
        if initial_probe['error']:
            raise RuntimeError('Controller initialization failed: '+initial_probe['error'])
        if args.quick:
            report['checks']['runtime_initialized'] = bool(val('valid'))
        for i, p in enumerate(samples):
            move(p, (*staging[i], .785))
        step(360)
        recording = True
        phase = 'Empty pan'
        step(120)
        initial = snap('empty_pan')
        pan_pose = dc.get_rigid_body_pose(handles[root+'/Instance/WeighingPan'])
        pan_pos = Gf.Vec3d(pan_pose.p.x, pan_pose.p.y, pan_pose.p.z)
        rotation = Gf.Rotation(Gf.Quatd(pan_pose.r.w, Gf.Vec3d(pan_pose.r.x, pan_pose.r.y, pan_pose.r.z)))

        def pan_point(x, y, z):
            return np.array(pan_pos + rotation.TransformDir(Gf.Vec3d(x, y, z)))

        # Known source receiver bottom is 6.44 mm below its rigid origin.
        phase = 'Place empty boat'
        smooth_move(boat, np.array(pose(boat)[:3])+[0, 0, .15])
        smooth_move(boat, pan_point(0, .020, .210))
        smooth_move(boat, pan_point(0, .020, .174))
        step(480)
        container = snap('empty_boat')
        phase = 'Press TARE'
        for _ in range(18):
            articulation.set_joint_positions(np.array([.0014]), joint_indices=np.array([index]))
            step(1)
        articulation._articulation_view.set_joint_position_targets(np.array([[0.]]), joint_indices=np.array([index]))
        step(300)
        tare = snap('tared')
        phase = 'Add solids'
        # Use the actual source floor footprint, offset from the boat origin;
        # the raised pouring lip has no flat supporting floor beneath it.
        offsets = [(-.010, -.027), (.010, -.027), (-.010, -.005), (.010, -.005), (0, -.016)]
        expected = 0.
        addition_checks = []
        for i, (path, (x, y)) in enumerate(zip(samples, offsets)):
            phase = f'Add solid {i+1} / 5'
            smooth_move(path, np.array(pose(path)[:3])+[0, 0, .20], .4)
            boat_pose = np.array(pose(boat)[:3])
            q = pose(path)
            rotation_now = np.array(Gf.Matrix3d(Gf.Quatd(q[6], Gf.Vec3d(*q[3:6]))))
            vertices = local_vertices[path] @ rotation_now
            center = vertices.mean(axis=0)
            target = boat_pose + [x-center[0], y-center[1], -.00496+.005-vertices[:, 2].min()]
            smooth_move(path, target+[0, 0, .06], .5)
            smooth_move(path, target, .4)
            step(360)
            expected += masses[path]
            item = snap('solid_'+str(i+1))
            addition_checks.append(bool(item['valid'] and abs(item['net_g']-expected) <= .01))
        phase = 'All five: stable total'
        if args.quick:
            step(360)
        else:
            stability('loaded_boat', 15)
        total = snap('five_total')
        phase = 'Unload solids'
        remaining = expected
        partial_unload_checks = []
        for i, path in enumerate(samples):
            smooth_move(path, np.array(pose(path)[:3])+[0, 0, .10], .35)
            smooth_move(path, (*staging[i], .79), .5)
            step(120)
            remaining -= masses[path]
            item = snap('unload_'+str(i+1))
            partial_unload_checks.append(bool(item['valid'] and abs(item['net_g']-remaining) <= .01))
        step(240)
        zero = snap('unloaded_zero')
        phase = 'Remove empty boat'
        smooth_move(boat, np.array(pose(boat)[:3])+[0, 0, .10])
        smooth_move(boat, (-.26, -.196, .775))
        step(360)
        negative = snap('negative_tare')
        recording = False
        prim.GetAttribute('balance:reset_requested').Set(True)
        step(240)
        reset = snap('reset')
        report['checks'].update(
            empty=bool(initial['valid'] and abs(initial['net_g']) <= .01),
            empty_boat=bool(container['valid'] and abs(container['net_g']-10) <= .01),
            tare=bool(tare['tared'] and abs(tare['net_g']) <= .01),
            incremental_loads=all(addition_checks),
            five_complete=bool(total['success'] and total['supported_sample_count'] == 5
                               and abs(total['net_g']-expected) <= .01),
            unload_zero=bool(zero['valid'] and abs(zero['net_g']) <= .01),
            partial_unloads=all(partial_unload_checks),
            negative_tare=bool(negative['valid'] and abs(negative['net_g']+tare['tare_g']) <= .01),
            reset=bool(not reset['tared'] and not reset['success'] and abs(reset['net_g']) <= .01))
        # A prescribed hovering object is visibly above the scale but carries
        # no load. Holding occurs only in this explicit negative-control phase.
        phase = 'hover_negative_control'
        hover = pan_point(0, .02, .25)
        for _ in range(240):
            move(samples[0], hover)
            step(1)
        hovering = snap('hovering_unloaded')
        report['checks']['hover_not_counted'] = bool(hovering['valid'] and abs(hovering['net_g']) <= .01)
        move(samples[0], (*staging[0], .78))
        if not args.quick:
            for height in (.005, .020):
                phase = f'release_{height}'
                for i, path in enumerate(samples):
                    q = pose(path)
                    rotation_now = np.array(Gf.Matrix3d(Gf.Quatd(q[6], Gf.Vec3d(*q[3:6]))))
                    vertices = local_vertices[path] @ rotation_now
                    center = vertices.mean(axis=0)
                    move(path, (staging[i][0]-center[0], staging[i][1]-center[1], .755-vertices[:, 2].min()+height))
                stability(phase)
        report['checks']['stability'] = all(x['pass'] for x in report['stability'])
        report['status'] = 'pass' if all(report['checks'].values()) else 'failed'
        report['simulated_seconds'] = t
        (args.out/'telemetry.jsonl').write_text('\n'.join(json.dumps(row) for row in telemetry)+'\n')
        np.savez_compressed(args.out/'physics_steps.npz', times=[r[0] for r in series],
                            geometry_centers=[r[1] for r in series], engine_velocities=[r[2] for r in series],
                            geometry_min_z=[r[3] for r in series], geometry_max_speed=[r[4] for r in series])
        if records:
            np.savez_compressed(args.out/'recording.npz', times=[r[0] for r in records],
                paths=paths, poses=[r[1] for r in records], phases=[r[2] for r in records],
                lcd=[r[3] for r in records], net_g=[r[4] for r in records], success=[r[5] for r in records])
    except BaseException:
        report['exception'] = traceback.format_exc()
        print(report['exception'], flush=True)
    finally:
        (args.out/'report.json').write_text(json.dumps(report, indent=2))
        print('RESULT', report['status'], report['checks'], flush=True)
        app.close(wait_for_replicator=False)
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

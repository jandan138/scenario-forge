"""Isaac 4.5 fixture validation, not robot or human VR success."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    argv = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False})
    sys.argv = argv
    report = {'status':'blocked','scene_sha256':sha256((args.root/'scene.usd').read_bytes()).hexdigest(),
              'protocol':'kinematic_fixture_tube_trajectory_actual_pbd','robot_policy_success':False}
    try:
        if not str(app.app.get_app_version()).startswith('4.5'):
            raise RuntimeError('this qualification requires Isaac Sim 4.5')
        import carb.settings
        import numpy as np
        import omni.usd
        import omni.physx
        import omni.physx.bindings._physx as pb
        from omni.isaac.dynamic_control import _dynamic_control
        from isaacsim.core.api import World
        from pxr import Usd, UsdPhysics, Gf
        settings = carb.settings.get_settings()
        for name in (pb.SETTING_UPDATE_TO_USD,pb.SETTING_UPDATE_PARTICLES_TO_USD,pb.SETTING_UPDATE_VELOCITIES_TO_USD):
            settings.set(name,True)
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        settings.set_bool('/physics/suppressReadback',False)
        settings.set_bool(pb.SETTING_SUPPRESS_READBACK,False)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        log_path = Path(str(settings.get('/log/file')))
        log_start = log_path.stat().st_size if log_path.exists() else 0
        context = omni.usd.get_context()
        context.open_stage(str(args.root/'scene.usd'))
        while context.get_stage_loading_status()[2]:
            app.update()
        for _ in range(30):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        TUBE = '/World/obj_sample_tube'
        tube = stage.GetPrimAtPath(TUBE)
        particles = stage.GetPrimAtPath('/World/fluid_runtime/ParticleSets/beaker_liquid')
        world = World(stage_units_in_meters=1,physics_prim_path='/World/physicsScene',set_defaults=False,physics_dt=1/120,rendering_dt=1/120)
        world.reset()
        dc = _dynamic_control.acquire_dynamic_control_interface()
        handle = dc.get_rigid_body(TUBE)
        if not handle:
            raise RuntimeError('no real tube rigid body')
        start = dc.get_rigid_body_pose(handle)
        initial = (start.p.x,start.p.y,start.p.z)
        snapshots = []
        tick = 0

        def value(name):
            return tube.GetAttribute('fehlings:'+name).Get()

        def step(n):
            nonlocal tick
            for _ in range(n):
                world.step(render=False)
                tick += 1

        def capture(name):
            pose = dc.get_rigid_body_pose(handle)
            record = {'name':name,'step':tick,'heated_s':value('heated_seconds'),'color_progress':value('color_progress'),
                'stage':value('stage'),'success':value('success'),'immersed':value('immersed'),
                'tube_xyz':[float(pose.p.x),float(pose.p.y),float(pose.p.z)],
                'tube_quat_xyzw':[float(pose.r.x),float(pose.r.y),float(pose.r.z),float(pose.r.w)],
                'particle_points':[list(p) for p in particles.GetAttribute('points').Get()],
                'sample_color':list(stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sample/Shader').GetAttribute('inputs:diffuseColor').Get()),
                'sample_opacity':stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sample/Shader').GetAttribute('inputs:opacity').Get(),
                'sediment_opacity':stage.GetPrimAtPath(TUBE+'/VisualLiquid/Looks/Sediment/Shader').GetAttribute('inputs:opacity').Get()}
            record['beaker_xyz'] = list(stage.GetPrimAtPath('/World/obj_beaker').GetAttribute('xformOp:translate').Get())
            snapshots.append(record)
            print(name,record['heated_s'],record['stage'],flush=True)
            return record

        step(1200)
        stable = capture('initial')
        pts = np.asarray(particles.GetAttribute('points').Get())
        water_q95 = float(np.quantile(pts[:,2],0.95))
        drift = float(np.linalg.norm(np.asarray(stable['tube_xyz'])-initial))
        if drift > 0.005:
            raise RuntimeError(f'tube unstable in rack: {drift}')
        UsdPhysics.RigidBodyAPI(tube).CreateKinematicEnabledAttr(True)
        step(2)
        handle = dc.get_rigid_body(TUBE)

        def move(position, tilt=False):
            nonlocal handle
            import math
            q = (0,math.sin(math.radians(35)/2),0,math.cos(math.radians(35)/2)) if tilt else (0,0,0,1)
            tube.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*position))
            orient = tube.GetAttribute('xformOp:orient')
            if orient:
                orient.Set(Gf.Quatf(q[3],Gf.Vec3f(*q[:3])) if str(orient.GetTypeName())=='quatf'
                           else Gf.Quatd(q[3],Gf.Vec3d(*q[:3])))
            dc.set_rigid_body_pose(handle,_dynamic_control.Transform(position,q))

        def travel(end,n=120):
            pose = dc.get_rigid_body_pose(handle)
            begin = np.asarray([pose.p.x,pose.p.y,pose.p.z])
            for i in range(1,n+1):
                move(begin+(np.asarray(end)-begin)*i/n)
                step(1)

        travel((initial[0],initial[1],1.0))
        travel((0.37,-0.028,1.0))
        step(360)
        outside = capture('outside_no_heating')
        shallow_z = float(value('water_surface_z'))-float(value('sample_height_m'))+0.010
        travel((0.37,-0.028,shallow_z))
        step(360)
        shallow = capture('too_shallow')
        target = (0.37,-0.028,float(value('water_surface_z'))-float(value('sample_height_m'))-0.006)
        # Test the rejected tilt in free space, avoiding an intentional rim strike.
        # Tilt alone is independently covered by the pure geometry predicate tests.
        travel((0.37,-0.028,1.0))
        move((0.37,-0.028,1.0),tilt=True)
        step(360)
        tilted = capture('tilted_invalid')
        move((0.37,-0.028,1.0))
        travel(target,240)
        for name,threshold in [('t10',10),('t30',30)]:
            for _ in range(int((threshold+3)*120)):
                step(1)
                if float(value('heated_seconds')) >= threshold:
                    break
            if float(value('heated_seconds')) < threshold:
                raise RuntimeError(f'valid immersion did not reach {threshold}s; surface q95={water_q95}, target={target}, sample={value("sample_height_m")}')
            capture(name)
        travel((0.37,-0.028,1.0))
        before = float(value('heated_seconds'))
        step(600)
        early = capture('early_withdrawal')
        travel(target)
        for _ in range(120*100):
            step(1)
            if float(value('heated_seconds')) >= 120-1e-6:
                break
        heated = capture('t120')
        travel((0.37,-0.028,1.0))
        step(360)
        observed = capture('observed')
        tube.GetAttribute('fehlings:reset_requested').Set(True)
        step(3)
        reset = capture('reset')
        pts = np.asarray(particles.GetAttribute('points').Get())
        below = int(np.sum(pts[:,2] < 0.8267-0.005))
        retained = int(np.sum((np.linalg.norm(pts[:,:2]-[0.37,-0.028],axis=1) < 0.047)&(pts[:,2]>0.8267)))
        log = log_path.read_text(errors='replace')[log_start:] if log_path.exists() else ''
        errors = [line for line in log.splitlines() if '[Error]' in line]
        checks = {'rack_stable':drift<=0.005,'outside_does_not_heat':outside['heated_s']==0,
            'shallow_does_not_heat':shallow['heated_s']==0,'tilted_does_not_heat':tilted['heated_s']==0,
            't30_not_success':not next(s for s in snapshots if s['name']=='t30')['success'],
            't30_color_complete':next(s for s in snapshots if s['name']=='t30')['color_progress']>=1-1e-6,
            'early_withdrawal_pauses':abs(early['heated_s']-before)<1e-6 and not early['success'],
            'heated_120':heated['heated_s']>=120-1e-6,'observed_success':observed['success'],
            'reset':reset['heated_s']==0 and reset['color_progress']==0 and not reset['success'],
            'particles_retained':retained==969 and below==0,'no_runtime_errors':not errors,
            'water_reference_matches':abs(water_q95-float(value('water_surface_z')))<0.006}
        report.update(status='pass' if all(checks.values()) else 'blocked',checks=checks,
            runtime='Isaac Sim 4.5',rack_drift_m=drift,water_q95=water_q95,particle_count=len(pts),retained=retained,
            below=below,errors=errors,snapshots=snapshots,kinematic_trajectory_fixture=True)
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

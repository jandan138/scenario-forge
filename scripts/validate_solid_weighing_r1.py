"""Cold-start and live force/tare integration fixture; no robot-policy claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--runtime',choices=['41','45'],default='45')
    p.add_argument('--init',choices=['omitted','zero','pressed'],default='zero')
    p.add_argument('--render',action='store_true')
    args=p.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from scripts.balance_evidence import scene_content_digest
    args.root=args.root.resolve()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    entry=args.root/('scene.usd' if args.runtime=='45' else 'scene_isaac41.usda')
    report=dict(status='failed',pid=os.getpid(),initialization=args.init,
                scene_sha256=hashlib.sha256((args.root/'scene.usd').read_bytes()).hexdigest(),snapshots=[],
                closure_sha256=scene_content_digest(args.root),
                asset_sha256=hashlib.sha256((args.root/'deps/balance/asset.usda').read_bytes()).hexdigest())
    sys.argv=[sys.argv[0]]
    from isaacsim import SimulationApp
    app=SimulationApp({'headless':True,'multi_gpu':False})
    try:
        import numpy as np
        import carb.settings
        import omni.usd
        import omni.physx
        from pxr import UsdGeom,Gf
        from omni.isaac.dynamic_control import _dynamic_control
        try:
            from isaacsim.core.api import World
            from isaacsim.core.prims import SingleArticulation as Articulation
        except ImportError:
            from omni.isaac.core import World
            from omni.isaac.core.articulations import Articulation
        report['runtime']=app.app.get_app_version()
        settings=carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in',False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in',True)
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        ctx=omni.usd.get_context()
        ctx.open_stage(str(entry))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        for _ in range(20):
            app.update()
        stage=ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        world=World(stage_units_in_meters=1,physics_prim_path='/World/PhysicsScene',
                    set_defaults=False,physics_dt=1/120,rendering_dt=1/120)
        root='/World/obj_analytical_balance'
        a=world.scene.add(Articulation(root,name='balance'))
        world.reset()
        world.get_physics_context().set_physics_dt(1/120)
        report['world_manager_physics_dt']=world.get_physics_dt()
        report['physics_dt']=1/120
        index=a.dof_names.index('RightTarePress')
        if args.init!='omitted':
            a.set_joint_positions(np.array([.001 if args.init=='pressed' else 0]),joint_indices=np.array([index]))
        report['initial_joint_readback_m']=float(a.get_joint_positions()[index])
        a._articulation_view.set_joint_position_targets(np.array([[0.]]),joint_indices=np.array([index]))
        dc=_dynamic_control.acquire_dynamic_control_interface()
        prim=stage.GetPrimAtPath(root)
        def val(name):
            return prim.GetAttribute('balance:'+name).Get()
        elapsed=0.
        series=[]
        def step(n):
            nonlocal elapsed
            for _ in range(n):
                # Isaac 4.5's World manager can retain a 60 Hz fallback for
                # pre-opened scenes. Drive the qualified physics dt explicitly.
                omni.physx.get_physx_interface().update_simulation(1/120,elapsed)
                omni.physx.get_physx_simulation_interface().fetch_results()
                elapsed+=1/120
                series.append((elapsed,val('gross_g'),val('net_g'),val('stable')))
        def snap(name):
            names=['gross_g','net_g','tare_g','valid','stable','status','error','lcd_readout',
                   'tare_pending','tared','success','completed_net_g','target_hold_s','tare_position_m']
            data={'name':name,'physics_time':elapsed,**{k:val(k) for k in names}}
            report['snapshots'].append(data)
            print('SNAPSHOT',data,flush=True)
            if args.render and name in ('initial_empty_pan','tared_container','loaded_target','container_removed'):
                capture(name)
            return data
        def capture(name):
            import omni.replicator.core as rep
            import omni.timeline
            from PIL import Image
            timeline=omni.timeline.get_timeline_interface()
            timeline.pause()
            camera=UsdGeom.Camera.Define(stage,'/World/WeighingReviewCamera')
            camera.CreateClippingRangeAttr(Gf.Vec2f(.01,20))
            camera.CreateFocalLengthAttr(35)
            xf=UsdGeom.Xformable(camera)
            xf.ClearXformOpOrder()
            pose=dc.get_rigid_body_pose(dc.get_rigid_body(root+'/Instance/Body'))
            rotation=Gf.Rotation(Gf.Quatd(pose.r.w,Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z)))
            position=Gf.Vec3d(pose.p.x,pose.p.y,pose.p.z)
            eye=position+rotation.TransformDir(Gf.Vec3d(.11,-.47,.30))
            target=position+rotation.TransformDir(Gf.Vec3d(.01,-.085,.125))
            xf.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse())
            product=rep.create.render_product(str(camera.GetPath()),(1280,800))
            rgb=rep.AnnotatorRegistry.get_annotator('rgb')
            rgb.attach([product])
            for _ in range(3):
                rep.orchestrator.step(rt_subframes=8,pause_timeline=True,delta_time=0)
            data=rgb.get_data()
            if data.ndim != 3 or data.shape[2] not in (3,4):
                raise RuntimeError('RGB capture unavailable: '+str(data.shape))
            dest=args.out.parent/(args.out.stem+'_'+name+'.png')
            Image.fromarray(data).save(dest)
            report.setdefault('images',[]).append(str(dest.resolve()))
            if name=='initial_empty_pan':
                xf.GetOrderedXformOps()[0].Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(1.3,-1.8,1.9),Gf.Vec3d(0,0,.82),Gf.Vec3d(0,0,1)).GetInverse())
                camera.GetFocalLengthAttr().Set(28)
                for _ in range(3):
                    rep.orchestrator.step(rt_subframes=8,pause_timeline=True,delta_time=0)
                dest=args.out.parent/(args.out.stem+'_overview.png')
                Image.fromarray(rgb.get_data()).save(dest)
                report['images'].append(str(dest.resolve()))
            rgb.detach([product.path])
            product.destroy()
            timeline.play()
        def move(path,xyz):
            h=dc.get_rigid_body(path)
            dc.set_rigid_body_pose(h,_dynamic_control.Transform(tuple(xyz),(0,0,0,1)))
            dc.set_rigid_body_linear_velocity(h,(0,0,0))
            dc.set_rigid_body_angular_velocity(h,(0,0,0))
            dc.wake_up_rigid_body(h)
        def pan_point(local):
            h=dc.get_rigid_body(root+'/Instance/WeighingPan')
            pose=dc.get_rigid_body_pose(h)
            q=Gf.Quatd(pose.r.w,Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z))
            return Gf.Rotation(q).TransformDir(Gf.Vec3d(*local))+Gf.Vec3d(pose.p.x,pose.p.y,pose.p.z)
        # Move samples aside during this controlled fixture; no mass edits.
        for i in range(1,6):
            move(f'/World/obj_grain_{i:02d}',(.6+i*.035,.2,.80))
        step(480)
        initial=snap('initial_empty_pan')
        if not initial['valid']:
            raise RuntimeError('runtime invalid: '+str(initial))
        boat='/World/obj_weighing_boat'
        move(boat,pan_point((0,.02,.173)))
        step(480)
        container=snap('container')
        a.set_joint_positions(np.array([.0014]),joint_indices=np.array([index]))
        # Hold via repeated physical joint state positioning only for this
        # prescribed press fixture; production reads actual button motion.
        for _ in range(12):
            a.set_joint_positions(np.array([.0014]),joint_indices=np.array([index]))
            step(1)
        a._articulation_view.set_joint_position_targets(np.array([[0.]]),joint_indices=np.array([index]))
        step(360)
        tare=snap('tared_container')
        if not tare['tared'] or abs(tare['net_g'])>.2:
            raise RuntimeError('tare failed')
        for i,xy in enumerate([(-.010,.010),(.008,.010),(0,.03)],start=1):
            move(f'/World/obj_grain_{i:02d}',pan_point((xy[0],xy[1],.191)))
            step(360)
            snap('sample_'+str(i))
        step(480)
        loaded=snap('loaded_target')
        pan_handle=dc.get_rigid_body(root+'/Instance/WeighingPan')
        for _ in range(120):
            point=pan_point((0,.02,.15))
            dc.apply_body_force(pan_handle,(0,0,-.02*9.81),tuple(point),True)
            step(1)
        snap('hand_pressure_20g_equivalent')
        step(480)
        snap('pressure_released')
        for _ in range(120):
            dc.apply_body_force(pan_handle,(0,0,-.25*9.81),tuple(pan_point((0,.02,.15))),True)
            step(1)
        over=snap('overload')
        step(480)
        snap('overload_released')
        saved_tare=val('tare_g')
        origin,orientation=a.get_world_pose()
        a.set_world_pose(origin+np.array([0,0,.12]),orientation)
        step(1)
        moved=snap('lifted')
        assert not moved['valid'] and abs(val('tare_g')-saved_tare)<1e-9
        quat=Gf.Rotation(Gf.Vec3d(0,0,1),30).GetQuat()
        a.set_world_pose(origin+np.array([.12,0,0]),np.array([quat.GetReal(),*quat.GetImaginary()]))
        a.set_linear_velocity(np.zeros(3))
        a.set_angular_velocity(np.zeros(3))
        step(480)
        snap('moved_and_rotated_empty')
        move(boat,pan_point((0,.02,.173)))
        for i,xy in enumerate([(-.010,.010),(.008,.010),(0,.03)],start=1):
            move(f'/World/obj_grain_{i:02d}',pan_point((xy[0],xy[1],.191)))
        step(720)
        snap('moved_and_rotated_loaded')
        move(boat,(-.3,-.18,.80))
        for i in range(1,4):
            move(f'/World/obj_grain_{i:02d}',(.6+i*.035,.2,.8))
        step(480)
        negative=snap('container_removed')
        prim.GetAttribute('balance:reset_requested').Set(True)
        step(240)
        reset=snap('reset')
        d=val('resolution_g')
        checks=dict(
            empty=abs(initial['net_g'])<=d,
            container=abs(container['net_g']-10)<=d,
            tare=tare['tared'] and abs(tare['net_g'])<=d,
            target=loaded['success'] and loaded['stable'] and abs(loaded['net_g']-30)<=val('tolerance_g'),
            negative=negative['stable'] and abs(negative['net_g']+saved_tare)<=d,
            reset=not reset['success'] and not reset['tared'] and abs(reset['net_g'])<=d,
            lifted_invalid=not moved['valid'],
            overload=over['status']=='overload' and over['lcd_readout']=='OL' and not over['stable'],
        )
        by_name={x['name']:x for x in report['snapshots']}
        checks['pressure_responds']=by_name['hand_pressure_20g_equivalent']['net_g']>loaded['net_g']+15
        checks['pressure_recovers']=abs(by_name['pressure_released']['net_g']-30)<=val('tolerance_g')
        recovery=by_name['moved_and_rotated_loaded']
        checks['move_recovers']=recovery['valid'] and recovery['stable'] and abs(recovery['net_g']-30)<=val('tolerance_g')
        report.update(status='observed',container=container,loaded=loaded,negative=negative,reset=reset,
                      robot_policy_success=False,protocol='prescribed_live_body_placement_and_joint_press',
                      checks=checks,series=series)
        report['status']='passed' if all(checks.values()) else 'failed'
    except BaseException:
        import traceback
        report['exception']=traceback.format_exc()
        print(report['exception'],flush=True)
    finally:
        args.out.write_text(json.dumps(report,indent=2))
        print('REPORT',args.out,report['status'],flush=True)
        app.close(wait_for_replicator=False)


if __name__=='__main__':
    main()

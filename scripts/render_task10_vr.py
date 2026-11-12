"""Render qualified task10 VR snapshots with the delivered room and lighting."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


def format_volume_ml(volume, quantum):
    count = round(volume/quantum)
    value = Decimal(count)*Decimal(str(quantum))
    return str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--runtime',choices=['41','45'],default='45')
    parser.add_argument('--recording',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--source-baseline',action='store_true')
    parser.add_argument('--spp',type=int,default=16)
    parser.add_argument('--frame-step',type=int,choices=[1,2],default=1)
    parser.add_argument('--preview-frames',help='Optional comma-separated frame indices for diagnostic stills')
    args = parser.parse_args()
    if args.source_baseline and not args.preview:
        raise ValueError('Source baseline is a visual-reference still, never the physical demonstration video')
    args.out.mkdir(parents=True,exist_ok=True)
    metadata = json.loads((args.package/'manifest.json').read_text())
    recording = json.loads(args.recording.read_text())
    expected_hash = hashlib.sha256((args.package/'manifest.json').read_bytes()).hexdigest()
    if recording.get('manifest_sha256',expected_hash) != expected_hash:
        raise ValueError('Recording and candidate content do not match')
    cfg = metadata['configuration']
    report = {'status':'failed','kind':'recorded_particle_state_replay','fps':30/args.frame_step,'frame_step':args.frame_step,'images':[],
              'recording_sha256':hashlib.sha256(args.recording.read_bytes()).hexdigest(),
              'candidate_sha256':hashlib.sha256((args.package/'manifest.json').read_bytes()).hexdigest(),
              'renderer_runtime_requested':args.runtime,'recorded_runtime':recording.get('runtime_version'),
              'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frame_files_sha256':{}}
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False,'renderer':'PathTracing','samples_per_pixel_per_frame':args.spp})
    encoder = None
    try:
        import numpy as np
        import omni.usd
        import omni.physx
        import omni.timeline
        import carb.settings
        import omni.replicator.core as rep
        from pxr import Usd,UsdGeom,UsdPhysics,UsdLux,Sdf,Gf,Vt
        from PIL import Image,ImageDraw,ImageFont
        from omni.kit.viewport.utility import get_active_viewport
        viewport = get_active_viewport()
        if viewport:
            viewport.updates_enabled = False
        ctx = omni.usd.get_context()
        entry = (args.package/f'demo{args.runtime}.usda').resolve()
        if args.source_baseline:
            reference = Usd.Stage.CreateNew(str((args.out/'source_reference.usda').resolve()))
            reference.GetRootLayer().subLayerPaths = [
                str((args.package/f'producer/materials/isaac{args.runtime}/materials.usda').resolve()),
                str((args.package/'producer/source/scene.usd').resolve())]
            UsdGeom.SetStageMetersPerUnit(reference,1.)
            UsdGeom.SetStageUpAxis(reference,'Z')
            UsdLux.DomeLight.Define(reference,'/World/DemoLight').CreateIntensityAttr(700)
            reference.GetRootLayer().Save()
            entry = Path(reference.GetRootLayer().realPath)
            report['kind'] = 'original_source_visual_reference'
        ctx.open_stage(str(entry))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        stage.GetPrimAtPath('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph').SetActive(False)
        for prim in list(stage.Traverse()):
            if prim.IsA(UsdPhysics.Joint):
                prim.SetActive(False)
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                prim.GetAttribute('physics:rigidBodyEnabled').Set(False)
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                prim.GetAttribute('physics:collisionEnabled').Set(False)
        # A render-only reconstruction stage: zero forces and velocities keep
        # the measured particles exact while the SDK updates its surface buffers.
        scene = UsdPhysics.Scene(stage.GetPrimAtPath('/World/PhysicsScene'))
        if scene:
            scene.GetGravityMagnitudeAttr().Set(0.)
            scene.GetPrim().CreateAttribute('physxScene:minPositionIterationCount',Sdf.ValueTypeNames.UInt).Set(1)
            scene.GetPrim().CreateAttribute('physxScene:maxPositionIterationCount',Sdf.ValueTypeNames.UInt).Set(1)
        for item in ([] if args.source_baseline else cfg['systems'].values()):
            system = stage.GetPrimAtPath(item['system_path'])
            system.GetAttribute('solverPositionIterationCount').Set(1)
            # Grid filtering erases isolated drops; preserve their measured surface.
            if item['system_path'].endswith('/FallingSystem'):
                system.GetAttribute('physxParticleIsosurface:gridFilteringPasses').Set('')
                system.GetAttribute('physxParticleIsosurface:numMeshSmoothingPasses').Set(0)
                system.GetAttribute('physxParticleIsosurface:gridSmoothingRadius').Set(0.)
            system.CreateAttribute('globalSelfCollisionEnabled',Sdf.ValueTypeNames.Bool).Set(True)
            system.CreateAttribute('nonParticleCollisionEnabled',Sdf.ValueTypeNames.Bool).Set(False)
            stage.GetPrimAtPath(item['particle_path']).GetAttribute('physxParticle:selfCollision').Set(False)
        carb.settings.get_settings().set_bool('/app/player/playSimulations',False)
        for setting in ('updateToUsd','updateParticlesToUsd','updateVelocitiesToUsd'):
            carb.settings.get_settings().set_bool('/physics/'+setting,True)
        carb.settings.get_settings().set_bool('/physics/suppressReadback',False)
        products = []
        for name,size,eye,target,focal in [
            ('Overview',(620,900),(2.,-3.,2.3),(0.,0.,1.),28),
            ('Detail',(1280,900),(.24,-.62,1.05),(-.03,-.1767,.90),58),
            ('Display',(440,220),(-.03,-.39,.96),(-.03,-.2603,.8131),120),
            ('Room',(1920,1080),(2.,-3.,2.3),(0.,0.,1.),28)]:
            camera = UsdGeom.Camera.Define(stage,'/World/Review'+name)
            camera.CreateHorizontalApertureAttr(36)
            camera.CreateFocalLengthAttr(focal)
            camera.CreateClippingRangeAttr(Gf.Vec2f(.001,20))
            camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
            product = rep.create.render_product(str(camera.GetPath()),size)
            rgb = rep.AnnotatorRegistry.get_annotator('rgb')
            rgb.attach([product])
            products.append(rgb)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',27)
        frames = recording['frames']
        boundaries = [0,*[i for i,f in enumerate(frames) if i and f['phase'] != frames[i-1]['phase']],len(frames)]
        selected = {0,len(frames)-1}
        for first,last in zip(boundaries,boundaries[1:]):
            selected.update((first,last-1))
            if frames[first]['phase']=='flask_wobble':
                selected.update((first+int((last-first)*.325),first+int((last-first)*.675)))
        selected = sorted(selected)
        if args.preview_frames:
            if not args.preview:
                raise ValueError('--preview-frames requires --preview')
            selected = sorted(set(map(int,args.preview_frames.split(','))))
        if not args.preview:
            selected = sorted({i-i%args.frame_step for i in selected})
        indices = selected if args.preview else range(0,len(frames),args.frame_step)
        if not args.preview:
            encoder = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1920x1080','-r',str(30/args.frame_step),'-i','-','-an','-c:v','libx264','-threads','4','-preset','fast','-crf','19',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(args.out/'task10_real_liquid_demo.mp4')],stdin=subprocess.PIPE)
        scales = {path:np.linalg.norm(np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0))[:3,:3],axis=1)
                  for path in recording['body_paths']}
        sets = {} if args.source_baseline else {name:UsdGeom.Points(stage.GetPrimAtPath(item['particle_path'])) for name,item in cfg['systems'].items()}
        if sets:
            for geom in sets.values():
                initial = np.asarray(geom.GetPointsAttr().Get(),dtype=np.float32).reshape(-1,3)
                geom.GetVelocitiesAttr().Set(Vt.Vec3fArray.FromNumpy(np.zeros_like(initial)))
            rep.orchestrator.step(rt_subframes=1,pause_timeline=True,delta_time=0)
        previous_presence = {name:bool(len(geom.GetPointsAttr().Get() or [])) for name,geom in sets.items()}
        for index in indices:
            frame_path = args.recording.parent/'frames'/f'{index:05d}.npz'
            report['frame_files_sha256'][frame_path.name] = hashlib.sha256(frame_path.read_bytes()).hexdigest()
            data = np.load(frame_path,allow_pickle=False)
            presence = {name:bool(len(data[name])) for name in sets}
            if presence!=previous_presence:
                omni.timeline.get_timeline_interface().stop()
                app.update()
                app.update()
                omni.physx.get_physx_interface().release_physics_objects()
            appeared = [name for name in sets if presence[name] and not previous_presence[name]]
            previous_presence = presence
            for path,pose in sorted(zip(recording['body_paths'],data['body_poses']),key=lambda x:x[0].count('/')):
                prim = stage.GetPrimAtPath(path)
                parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(0)
                world = Gf.Matrix4d().SetScale(Gf.Vec3d(*map(float,scales[path])))
                world *= Gf.Matrix4d().SetRotate(Gf.Quatd(float(pose[6]),Gf.Vec3d(*map(float,pose[3:6]))))
                world.SetTranslateOnly(Gf.Vec3d(*map(float,pose[:3])))
                xf = UsdGeom.Xformable(prim)
                attr = prim.GetAttribute('xformOp:transform:recorded')
                op = UsdGeom.XformOp(attr) if attr else xf.AddTransformOp(opSuffix='recorded')
                xf.SetXformOpOrder([op])
                op.Set(world*parent.GetInverse())
            for name,geom in sets.items():
                pts = np.asarray(data[name],dtype=np.float32).reshape(-1,3)
                with Sdf.ChangeBlock():
                    geom.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(pts))
                    geom.GetVelocitiesAttr().Set(Vt.Vec3fArray.FromNumpy(np.zeros_like(pts)))
                    geom.GetWidthsAttr().Set(Vt.FloatArray([cfg['systems'][name]['particle_spacing_m']]*len(pts)))
                    geom.GetIdsAttr().Set(Vt.Int64Array(range(len(pts))))
                    UsdPhysics.MassAPI(geom.GetPrim()).GetMassAttr().Set(cfg['systems'][name]['per_particle_mass_kg']*len(pts))
                iso_enabled = stage.GetPrimAtPath(cfg['systems'][name]['system_path']).GetAttribute('physxParticleIsosurface:isosurfaceEnabled')
                if iso_enabled.Get()!=bool(len(pts)):
                    iso_enabled.Set(bool(len(pts)))
            shader_path = ('/World/obj_receiver_flask/VisualLiquid/Looks/Water/Shader' if args.source_baseline
                           else cfg['systems']['Receiver']['material_path']+'/Shader')
            stage.GetPrimAtPath(shader_path).GetAttribute('inputs:glass_color').Set(Gf.Vec3f(*map(float,data['color'])))
            for name in appeared:
                relation = sets[name].GetPrim().GetRelationship('physxParticle:particleSystem')
                relation.SetTargets([])
                app.update()
                relation.SetTargets([cfg['systems'][name]['system_path']])
                app.update()
                app.update()
            if appeared:
                omni.physx.get_physx_interface().force_load_physics_from_usd()
                app.update()
                app.update()
            if sets:
                omni.timeline.get_timeline_interface().play()
                app.update()
                omni.physx.get_physx_simulation_interface().simulate(metadata['physics_dt'],float(frames[index]['time']))
                omni.physx.get_physx_simulation_interface().fetch_results()
                omni.physx.get_physx_interface().update_transformations(False,True,True)
            # SDK reconstruction uses the recorded points with zero forces.
            # Explicit render-only SDK synchronization prevents stale surface buffers;
            # positions must remain bit-exact and every surface must match them.
            for _ in range(4 if index==indices[0] else 2):
                rep.orchestrator.step(rt_subframes=4 if args.preview else 1,pause_timeline=True,delta_time=0)
            for name,geom in sets.items():
                if not np.array_equal(np.asarray(geom.GetPointsAttr().Get()).reshape(-1,3),data[name].reshape(-1,3)):
                    current = np.asarray(geom.GetPointsAttr().Get()).reshape(-1,3)
                    original = data[name].reshape(-1,3)
                    report['replay_mismatch'] = {'system':name,'actual_shape':list(current.shape),
                        'expected_shape':list(original.shape),'first_actual':current[:3].tolist(),
                        'first_expected':original[:3].tolist(),
                        'max_delta_m':float(np.max(np.abs(current-original))) if current.shape==original.shape else None}
                    raise RuntimeError('Replay unexpectedly advanced physical particles: '+name)
                if len(data[name]):
                    iso = UsdGeom.Mesh(stage.GetPrimAtPath(cfg['systems'][name]['system_path']+'/Isosurface'))
                    if not iso or not len(iso.GetPointsAttr().Get()):
                        raise RuntimeError('SDK did not reconstruct liquid surface: '+name)
                    mesh = np.asarray(iso.GetPointsAttr().Get()).reshape(-1,3)
                    transform = np.asarray(UsdGeom.Xformable(iso).ComputeLocalToWorldTransform(0))
                    mesh_world = mesh @ transform[:3,:3]+transform[3,:3]
                    pts = data[name].reshape(-1,3)
                    tolerance = max(cfg['systems'][name]['particle_spacing_m']*4,.002)
                    if np.any(mesh_world.min(axis=0)<pts.min(axis=0)-tolerance) or np.any(mesh_world.max(axis=0)>pts.max(axis=0)+tolerance):
                        report['surface_mismatch'] = {'system':name,'mesh_min':mesh_world.min(axis=0).tolist(),
                            'mesh_max':mesh_world.max(axis=0).tolist(),'particle_min':pts.min(axis=0).tolist(),
                            'particle_max':pts.max(axis=0).tolist()}
                        raise RuntimeError('Stale or misplaced SDK isosurface: '+name)
            image = Image.new('RGB',(1920,1080),(18,25,31))
            image.paste(Image.fromarray(products[0].get_data()).convert('RGB'),(0,100))
            image.paste(Image.fromarray(products[1].get_data()).convert('RGB'),(640,100))
            display_image = Image.fromarray(products[2].get_data()).convert('RGB')
            show_display = frames[index]['phase'] not in ('clear_nozzle','flask_wobble','return_aligned')
            if show_display:
                image.paste(display_image,(1460,130))
            row = frames[index]
            state = row['state']
            draw = ImageDraw.Draw(image)
            if show_display:
                draw.rectangle((1460,100,1900,130),fill=(18,25,31))
                draw.text((1467,101),'Display / same frame',font=font,fill='white')
            labels = {'settle':'Initial liquid','clear_nozzle':'Move flask clear','flask_wobble':'Liquid motion',
                'return_aligned':'Align receiver','settle_after_motion':'Settle liquid','coarse_titration':'Titration',
                'fine_titration':'Approach endpoint','closed_pale_endpoint':'Closed valve / endpoint hold',
                'reset':'Reset','overshoot':'Overshoot check'}
            label = {'initial':'Initial liquid','endpoint':'Confirmed endpoint','overshoot':'Overshoot check','reset':'Reset'}.get(row['phase'],labels.get(row['phase'],row['phase']))
            draw.text((24,15),f'TASK 10  |  {label}  |  {row["time"]:.2f} s',font=font,fill='white')
            subtitle = 'Original colleague scene / matching tint / visual reference' if args.source_baseline else 'VR room / actual recorded particle state / no robot'
            draw.text((24,55),subtitle,font=font,fill=(210,221,230))
            color_label = {'colorless':'Clear','transition':'Turning pink',
                'endpoint_pale_pink':'Pale pink endpoint','overshoot':'Excess reagent'}.get(state['color_phase'],state['color_phase'])
            outcome = 'Endpoint confirmed' if state['success'] else 'Endpoint not confirmed'
            received_text = format_volume_ml(state['received_ml'],cfg['particle_volume_ml'])
            released_text = format_volume_ml(state['released_ml'],cfg['particle_volume_ml'])
            footer = (f'Received: {received_text} mL   Released: {released_text} mL   '
                      f'{color_label}   |   {outcome}')
            if args.source_baseline:
                footer = 'Original visual reference at matching tint; not a physical-fluid demonstration'
            draw.text((24,1020),footer,font=font,fill='white')
            if index==indices[0]:
                room_target=args.out/'room_overview.png'
                Image.fromarray(products[3].get_data()).convert('RGB').save(room_target)
                report['images'].append(str(room_target))
            if index in selected:
                target = args.out/f'frame_{index:05d}.png'
                image.save(target)
                report['images'].append(str(target))
            if encoder:
                encoder.stdin.write(image.tobytes())
            if args.preview or index%60==0:
                print('FRAME',index,row['phase'],flush=True)
        if encoder:
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError('ffmpeg encoding failed')
            encoder = None
        report.update(status='rendered',frame_count=len(indices),particle_replay_exact=not args.source_baseline,
                      surface_bounds_match=not args.source_baseline)
    except BaseException:
        report['exception'] = traceback.format_exc()
        print(report['exception'],flush=True)
    finally:
        if encoder:
            encoder.stdin.close()
            encoder.wait()
        (args.out/'render_report.json').write_text(json.dumps(report,indent=2))
        app.close(wait_for_replicator=False)
    return 0 if report['status']=='rendered' else 1


if __name__ == '__main__':
    raise SystemExit(main())

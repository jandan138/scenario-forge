"""Replay observed body and particle poses from the original-scene powder fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def load_recording(path):
    """Snapshot each compressed array once instead of decompressing per frame."""
    import numpy as np
    with np.load(path,allow_pickle=False) as archive:
        return {name:archive[name] for name in archive.files}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--states',type=Path,required=True)
    p.add_argument('--runtime',choices=['45'],default='45')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--view',choices=['overview','close','bottle'],default='close')
    p.add_argument('--frames',default='0,180,330,600,750,840,960,1080,1140,1200,1470')
    p.add_argument('--video',action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    cfg = json.loads((a.root/'scene_config.json').read_text())
    bottle_focus_z = cfg.get('powder_surface_target_m',.133)+(.010 if 'inner_profile' in cfg else 0.)
    entry = (a.root/cfg['entrypoints'][a.runtime]).resolve()
    result = dict(status='failed',kind='observed_physics_replay',runtime=a.runtime,
                  entry_sha256=hashlib.sha256(entry.read_bytes()).hexdigest(),
                  states_sha256=hashlib.sha256(a.states.read_bytes()).hexdigest(),images=[])
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless':True,'multi_gpu':False})
    encoder = None
    try:
        import numpy as np
        import omni.usd
        import omni.replicator.core as rep
        from pxr import UsdGeom,UsdPhysics,UsdLux,Sdf,Gf,Vt
        from PIL import Image,ImageDraw,ImageFont
        from scripts.balance_force_runtime import SEGMENTS
        d = load_recording(a.states)
        ctx = omni.usd.get_context()
        ctx.open_stage(str(entry))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        flattened = stage.Flatten()
        inst = UsdGeom.PointInstancer.Define(stage,'/World/RecordedPowder')
        prototype = '/World/RecordedPowder/Prototype'
        Sdf.CopySpec(flattened,str(d['paths'][0])+'/Mesh',stage.GetSessionLayer(),prototype)
        proto = stage.GetPrimAtPath(prototype)
        for api in list(proto.GetAppliedSchemas()):
            if api.startswith(('Physics','Physx')):
                proto.RemoveAppliedSchema(api)
        inst.CreatePrototypesRel().SetTargets([prototype])
        inst.CreateProtoIndicesAttr([0]*len(d['paths']))
        for path in d['paths']:
            UsdGeom.Imageable(stage.GetPrimAtPath(str(path))).CreateVisibilityAttr('invisible')
        for prim in stage.Traverse():
            if prim.IsA(UsdPhysics.Joint):
                UsdPhysics.Joint(prim).CreateJointEnabledAttr(False)
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(False)
        stage.GetPrimAtPath(cfg['paths']['balance']+'/BalanceRuntime').SetActive(False)
        body_paths = [str(x) for x in d['body_paths']]
        link_paths = [str(x) for x in d['link_paths']]
        scales = {path:Gf.Transform(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0)).GetScale()
                  for path in body_paths+link_paths}
        def set_pose(path,pose):
            prim = stage.GetPrimAtPath(path)
            parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(0)
            world = Gf.Transform()
            world.SetScale(scales[path])
            world.SetRotation(Gf.Rotation(Gf.Quatd(float(pose[6]),Gf.Vec3d(*map(float,pose[3:6])))))
            world.SetTranslation(Gf.Vec3d(*map(float,pose[:3])))
            xf = UsdGeom.Xformable(prim)
            attr = prim.GetAttribute('xformOp:transform:recorded')
            op = UsdGeom.XformOp(attr) if attr else xf.AddTransformOp(opSuffix='recorded')
            xf.SetXformOpOrder([op])
            op.Set(world.GetMatrix()*parent.GetInverse())
        camera = UsdGeom.Camera.Define(stage,'/World/Task09ReviewCamera')
        camera.CreateClippingRangeAttr(Gf.Vec2f(.001,20))
        camera.CreateFocalLengthAttr(36)
        camera_op = camera.AddTransformOp()
        dome = UsdLux.DomeLight.Define(stage,'/World/task09_powder_light')
        dome.CreateIntensityAttr(650)
        key = UsdLux.DistantLight.Define(stage,'/World/task09_powder_key')
        key.CreateIntensityAttr(1800)
        key.CreateAngleAttr(3)
        rotation = key.GetPrim().GetAttribute('xformOp:rotateXYZ')
        if rotation:
            rotation.Set(Gf.Vec3f(-35,-20,35))
        else:
            key.AddRotateXYZOp().Set(Gf.Vec3f(-35,-20,35))
        product = rep.create.render_product(str(camera.GetPath()),(1280,800))
        rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        rgb.attach([product])
        requested = set(map(int,a.frames.split(',')))
        selected = list(range(len(d['times']))) if a.video else sorted(i for i in requested if 0<=i<len(d['times']))
        if not selected:
            raise ValueError('No requested frames are available')
        if a.video:
            encoder = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x800',
                '-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                '-movflags','+faststart',str(a.out/(a.view+'.mp4'))],stdin=subprocess.PIPE)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
        for frame in selected:
            inst.GetPositionsAttr().Set(Vt.Vec3fArray.FromNumpy(d['positions'][frame]))
            inst.CreateOrientationsAttr().Set(Vt.QuathArray([Gf.Quath(float(q[0]),Gf.Vec3h(*map(float,q[1:]))) for q in d['orientations'][frame]]))
            for path,pose in zip(body_paths,d['body_poses'][frame]):
                set_pose(path,pose)
            for path,pose in zip(link_paths,d['link_poses'][frame]):
                set_pose(path,pose)
            now = float(d['times'][frame])
            bottle = d['body_poses'][frame,body_paths.index(cfg['paths']['bottle']),:3]
            boat = d['body_poses'][frame,body_paths.index(cfg['paths']['boat']),:3]
            if a.view=='overview':
                eye,target = (1.6,-2.25,1.95),(0.,0.,.86)
                camera.GetFocalLengthAttr().Set(29)
            elif a.view=='bottle':
                target = bottle+np.array([0.,0.,bottle_focus_z])
                eye = target+np.array([.045,-.09,.20])
                camera.GetFocalLengthAttr().Set(36)
            else:
                beaker_target = np.array([.088,.19,.86])
                bottle_target = bottle+np.array([0.,0.,bottle_focus_z])
                boat_target = boat+np.array([0.,-.005,.008])
                if now<11:
                    target = beaker_target
                    eye = target+np.array([.15,-.33,.23])
                    camera.GetFocalLengthAttr().Set(30)
                elif now<14:
                    u = (now-11)/3
                    target = (1-u)*beaker_target+u*bottle_target
                    eye = target+np.array([.08,-.16,.15])
                elif now<32:
                    target = bottle_target
                    eye = target+np.array([.065,-.13,.15])
                    camera.GetFocalLengthAttr().Set(34 if 'inner_profile' in cfg else 38)
                else:
                    u = min(1.,(now-32)/4)
                    target = (1-u)*bottle_target+u*boat_target
                    eye = target+np.array([.06,-.14,.14])
                    camera.GetFocalLengthAttr().Set(36)
                if 'inner_profile' in cfg and 8<=now<42:
                    spoon_matrix = UsdGeom.Xformable(stage.GetPrimAtPath(cfg['paths']['spoon'])).ComputeLocalToWorldTransform(0)
                    head = np.array(spoon_matrix.Transform(Gf.Vec3d(.087,0,0)))
                    if now<14:
                        u = min(1.,(now-8)/3)
                        target = (1-u)*beaker_target+u*head
                        eye = target+(1-u)*np.array([.15,-.33,.23])+u*np.array([.065,-.13,.15])
                    elif now<20:
                        u = (now-14)/6
                        target = (1-u)*head+u*bottle_target
                        eye = target+np.array([.065,-.13,.15])
                    elif now>=28:
                        if now<36:
                            u = min(1.,(now-28)/2)
                            target = (1-u)*bottle_target+u*head
                        elif now<40:
                            u = min(1.,now-36)/2
                            target = (1-u)*head+u*boat_target
                        else:
                            target = boat_target+np.array([0.,0.,.021*(42-now)/2])
                        eye = target+np.array([.08,-.20,.20])
                        camera.GetFocalLengthAttr().Set(35)
                if now>=42:
                    body_index = link_paths.index(cfg['paths']['balance']+'/Instance/Body')
                    body = d['link_poses'][frame,body_index,:3]
                    u = min(1.,(now-42)/4)
                    target = (1-u)*target+u*(body+np.array([.01,-.085,.125]))
                    eye = (1-u)*eye+u*(body+np.array([.11,-.47,.30]))
                    camera.GetFocalLengthAttr().Set(35)
            camera_op.Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*map(float,eye)),Gf.Vec3d(*map(float,target)),Gf.Vec3d(0,0,1)).GetInverse())
            division = cfg.get('display_resolution_g',.1)
            value = round(float(d['balance_net_g'][frame])/division)*division
            text = str(d['lcd_readout'][frame]).removesuffix(' g') if 'lcd_readout' in d else f"{0. if abs(value)<division/2 else value:.2f}"
            decimal_places = len(text.split('.')[1]) if '.' in text else -1
            base = cfg['paths']['balance']+'/Instance/Body/ControlPanel/LiveDigits'
            for i,char in enumerate(text.replace('.','').rjust(8)):
                for seg in 'abcdefg':
                    prim = stage.GetPrimAtPath(f'{base}/D{i}_{seg}')
                    if prim:
                        UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if seg in SEGMENTS.get(char,'') else 'invisible')
                prim = stage.GetPrimAtPath(f'{base}/P{i}')
                if prim:
                    UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if decimal_places>=0 and i==7-decimal_places else 'invisible')
            if 'balance_stable' in d:
                for i,visible in enumerate((d['balance_stable'][frame],d['tare_pending'][frame],not d['balance_valid'][frame])):
                    led = stage.GetPrimAtPath(cfg['paths']['balance']+f'/Instance/Body/ControlPanel/Status/LED_{i}')
                    if led:
                        UsdGeom.Imageable(led).GetVisibilityAttr().Set('inherited' if visible else 'invisible')
            for _ in range(3 if frame==selected[0] else 1):
                rep.orchestrator.step(rt_subframes=2,pause_timeline=True,delta_time=0)
            image = Image.fromarray(rgb.get_data()).convert('RGB')
            draw = ImageDraw.Draw(image)
            draw.rectangle((0,0,1280,72),fill=(16,24,30))
            draw.text((20,10),f"Isaac {a.runtime[0]}.{a.runtime[1]} observed-state replay | {now:05.2f} s | {len(d['paths'])} obj_ grains",font=font,fill=(240,243,245))
            draw.text((20,40),f"Pan-contact net: {float(d['balance_net_g'][frame]):.4f} g | {str(d['phases'][frame])}",font=font,fill=(235,202,99))
            if frame in requested:
                dest = a.out/f'{a.view}_{frame:04d}.png'
                image.save(dest)
                result['images'].append(dest.name)
            if encoder:
                encoder.stdin.write(image.tobytes())
            if frame%120==0:
                print('FRAME',frame,flush=True)
        if encoder:
            encoder.stdin.close()
            if encoder.wait()!=0:
                raise RuntimeError('Encoder failed')
            encoder = None
        result.update(status='rendered',frame_count=len(selected),fps=30)
    except BaseException:
        result['exception'] = traceback.format_exc()
        print(result['exception'],flush=True)
    finally:
        if encoder:
            encoder.stdin.close()
            encoder.wait()
        (a.out/(a.view+'_render.json')).write_text(json.dumps(result,indent=2))
        app.close(wait_for_replicator=False)


if __name__=='__main__':
    main()

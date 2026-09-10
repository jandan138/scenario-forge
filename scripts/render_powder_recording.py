"""Render recorded PhysX states without advancing or inventing particle motion."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--states', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--frames', default='0,90,210,270,390,450,600')
    parser.add_argument('--video', action='store_true')
    parser.add_argument('--view', choices=['close','overview','detail'], default='close')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'multi_gpu': False})
    report = {'status': 'failed', 'kind': 'recorded_physics_state_replay', 'images': [],
              'scene_sha256':hashlib.sha256(args.scene.read_bytes()).hexdigest(),
              'states_sha256':hashlib.sha256(args.states.read_bytes()).hexdigest(), 'fps':30}
    encoder = None
    try:
        import numpy as np
        import omni.usd
        import omni.replicator.core as rep
        from pxr import UsdGeom, Usd, Sdf, Gf, Vt, UsdLux
        from PIL import Image, ImageDraw, ImageFont
        data = np.load(args.states, allow_pickle=False)
        ctx = omni.usd.get_context()
        ctx.open_stage(str(args.scene.resolve()))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        # A visual instance per recorded grain; physical source scene stays intact.
        source = stage.GetPrimAtPath(str(data['paths'][0]))
        flattened = stage.Flatten()
        proto_path = '/World/RecordedPowder/Prototype'
        instancer = UsdGeom.PointInstancer.Define(stage, '/World/RecordedPowder')
        Sdf.CopySpec(flattened, source.GetPath(), stage.GetSessionLayer(), proto_path)
        proto = stage.GetPrimAtPath(proto_path)
        proto.SetMetadata('apiSchemas', Sdf.TokenListOp())
        xform = UsdGeom.Xformable(proto)
        scales = [op for op in xform.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeScale]
        xform.SetXformOpOrder(scales)
        instancer.CreatePrototypesRel().SetTargets([proto_path])
        instancer.CreateProtoIndicesAttr([0]*len(data['paths']))
        UsdGeom.Imageable(stage.GetPrimAtPath('/World/Powder')).CreateVisibilityAttr('invisible')
        for p in stage.Traverse():
            if p.GetName() == 'BalanceRuntime':
                p.SetActive(False)
        camera = UsdGeom.Camera.Define(stage, '/World/RecordingCamera')
        camera.CreateClippingRangeAttr(Gf.Vec2f(.0005,20))
        camera.CreateFocalLengthAttr(48)
        offset = np.array(data['workspace_offset']) if 'workspace_offset' in data else np.zeros(3)
        if args.view in ('close','detail'):
            eye = offset + np.array([.17,-.23,.20])
            target = offset + np.array([.04,0,.022])
            camera.GetFocalLengthAttr().Set(40)
        else:
            eye = offset + np.array([.48,-.82,.55])
            target = offset + np.array([.12,-.05,-.035])
            camera.GetFocalLengthAttr().Set(32)
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
        key = UsdLux.DistantLight.Define(stage,'/World/RecordingKey')
        key.CreateIntensityAttr(2200)
        key.CreateAngleAttr(2)
        key.AddRotateXYZOp().Set(Gf.Vec3f(-30,-20,25))
        product = rep.create.render_product(str(camera.GetPath()), (1280,800))
        rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        rgb.attach([product])
        requested = set(map(int,args.frames.split(',')))
        indices = range(len(data['times'])) if args.video else sorted(i for i in requested if i<len(data['times']))
        if args.video:
            encoder = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1280x800','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(args.out/(args.view+'.mp4'))], stdin=subprocess.PIPE)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
        for frame in indices:
            if args.view in ('close','detail') and 'body_paths' in data:
                progress = np.clip((float(data['times'][frame])-11)/4,0,1)
                target = offset+np.array([.01+.17*progress,0,.02])
                eye = target+np.array([.04,-.07,.15] if args.view=='detail' else [.055,-.13,.10])
                camera.GetFocalLengthAttr().Set(38)
                UsdGeom.Xformable(camera).GetOrderedXformOps()[0].Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
            instancer.GetPositionsAttr().Set(Vt.Vec3fArray.FromNumpy(data['positions'][frame]))
            q = data['orientations'][frame]
            instancer.CreateOrientationsAttr().Set(Vt.QuathArray([Gf.Quath(float(v[0]),Gf.Vec3h(*map(float,v[1:]))) for v in q]))
            tool = data['tools'][frame]
            spoon = stage.GetPrimAtPath('/World/Spoon')
            spoon.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*map(float,tool[:3])))
            spoon.GetAttribute('xformOp:orient').Set(Gf.Quatf(float(tool[3]),Gf.Vec3f(*map(float,tool[4:]))))
            if 'body_paths' in data:
                for path, pose in zip(data['body_paths'], data['body_poses'][frame]):
                    prim = stage.GetPrimAtPath(str(path))
                    parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                    world = Gf.Matrix4d().SetRotate(Gf.Quatd(float(pose[6]),Gf.Vec3d(*map(float,pose[3:6]))))
                    world.SetTranslateOnly(Gf.Vec3d(*map(float,pose[:3])))
                    xf = UsdGeom.Xformable(prim)
                    xf.ClearXformOpOrder()
                    attr = prim.GetAttribute('xformOp:transform:recorded')
                    op = UsdGeom.XformOp(attr) if attr else xf.AddTransformOp(opSuffix='recorded')
                    xf.SetXformOpOrder([op])
                    op.Set(world*parent.GetInverse())
            if 'balance_net_g' in data:
                # Seven-segment instrument display comes from the recorded force value.
                from scripts.balance_force_runtime import SEGMENTS
                text = f"{float(data['balance_net_g'][frame]):.1f}"
                base = '/World/obj_analytical_balance/Instance/Body/ControlPanel/LiveDigits'
                for i,char in enumerate(text.replace('.','').rjust(8)):
                    for seg in 'abcdefg':
                        p = stage.GetPrimAtPath(f'{base}/D{i}_{seg}')
                        if p:
                            UsdGeom.Imageable(p).GetVisibilityAttr().Set('inherited' if seg in SEGMENTS.get(char,'') else 'invisible')
                    p = stage.GetPrimAtPath(f'{base}/P{i}')
                    if p:
                        UsdGeom.Imageable(p).GetVisibilityAttr().Set('inherited' if i==6 else 'invisible')
            for _ in range(3 if frame==indices[0] else 1):
                rep.orchestrator.step(rt_subframes=2, pause_timeline=True, delta_time=0)
            image = Image.fromarray(rgb.get_data()).convert('RGB')
            draw = ImageDraw.Draw(image)
            draw.rectangle((0,0,1280,72),fill=(16,24,30))
            label = f"Recorded PhysX simulation | {float(data['times'][frame]):05.2f} s | {len(data['paths'])} rigid grains"
            draw.text((22,12),label,font=font,fill=(240,243,245))
            if 'balance_net_g' in data:
                draw.text((22,40),f"Pan-contact net: {data['balance_net_g'][frame]:.4f} g  |  {str(data['phases'][frame])}",font=font,fill=(235,202,99))
            else:
                draw.text((22,40),'Prescribed kinematic spoon; particle motion solved by contacts',font=font,fill=(180,200,210))
            if frame in requested:
                dest = args.out/f'{args.view}_{frame:04d}.png'
                image.save(dest)
                report['images'].append(str(dest.resolve()))
            if encoder:
                encoder.stdin.write(image.tobytes())
            if frame % 60 == 0:
                print('FRAME', frame, flush=True)
        if encoder:
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError('Video encoder failed')
            encoder = None
        report['status'] = 'rendered'
    except BaseException:
        report['exception'] = traceback.format_exc()
        print(report['exception'],flush=True)
    finally:
        if encoder:
            encoder.stdin.close()
            encoder.wait()
        (args.out/f'{args.view}_render.json').write_text(json.dumps(report,indent=2))
        app.close(wait_for_replicator=False)


if __name__ == '__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    main()

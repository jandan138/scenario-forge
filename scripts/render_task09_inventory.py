"""Render the recorded physical poses and actual LCD of the task09 fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--recording', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--visual-overlay', type=Path)
    p.add_argument('--renderer', choices=['RayTracedLighting', 'PathTracing'], default='PathTracing')
    p.add_argument('--spp', type=int, default=16)
    p.add_argument('--frame-step', type=int, choices=[1, 2], default=2)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'multi_gpu': False, 'renderer': a.renderer,
                         'samples_per_pixel_per_frame': a.spp})
    encoder = None
    report = {'status': 'failed', 'kind': 'recorded_physics_state_replay', 'fps': 30,
              'renderer': a.renderer,
              'samples_per_pixel_per_frame': a.spp,
              'playback_speed': a.frame_step,
              'renderer_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scene_sha256': hashlib.sha256((a.package/'assets/composed/scene.usdc').read_bytes()).hexdigest(),
              'recording_sha256': hashlib.sha256(a.recording.read_bytes()).hexdigest(), 'images': []}
    try:
        import numpy as np
        import omni.usd
        import omni.replicator.core as rep
        from pxr import Usd, UsdGeom, UsdPhysics, UsdLux, Gf
        from PIL import Image, ImageDraw, ImageFont
        data = np.load(a.recording, allow_pickle=False)
        ctx = omni.usd.get_context()
        ctx.open_stage(str((a.package/'scene/demo45.usda').resolve()))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        stage.SetEditTarget(stage.GetSessionLayer())
        masses_g = [float(stage.GetPrimAtPath(f'/World/obj_grain_{i:02d}').GetAttribute(
            'physics:mass').Get())*1000 for i in range(1, 6)]
        if a.visual_overlay:
            overlay = Usd.Stage.Open(str(a.visual_overlay.resolve()))
            for p in overlay.TraverseAll():
                target_prim = stage.GetPrimAtPath(p.GetPath())
                for attr in p.GetAttributes():
                    if attr.HasAuthoredValueOpinion():
                        target_prim.CreateAttribute(attr.GetName(), attr.GetTypeName()).Set(attr.Get())
            report['visual_overlay_sha256'] = hashlib.sha256(a.visual_overlay.read_bytes()).hexdigest()
        root = '/World/obj_analytical_balance'
        stage.GetPrimAtPath(root+'/BalanceRuntime').SetActive(False)
        # Replay never starts a second physical experiment. Disable the physics
        # interfaces in the session layer before Replicator touches the timeline.
        for prim in list(stage.Traverse()):
            if prim.IsA(UsdPhysics.Joint):
                prim.SetActive(False)
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                prim.GetAttribute('physics:rigidBodyEnabled').Set(False)
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                prim.GetAttribute('physics:collisionEnabled').Set(False)
        stage.GetPrimAtPath('/World/PhysicsScene').SetActive(False)
        key = UsdLux.DistantLight.Define(stage, '/World/DemoKey')
        key.CreateIntensityAttr(1500)
        key.CreateAngleAttr(5.)
        key.AddRotateXYZOp().Set(Gf.Vec3f(15, -25, -20))
        scales = {}
        for path in data['paths']:
            m = np.array(UsdGeom.Xformable(stage.GetPrimAtPath(str(path))).ComputeLocalToWorldTransform(0))
            scales[str(path)] = np.linalg.norm(m[:3, :3], axis=1)
        body = list(data['paths']).index(root+'/Instance/Body')
        initial = data['poses'][0, body]
        pos = Gf.Vec3d(*map(float, initial[:3]))
        rot = Gf.Rotation(Gf.Quatd(float(initial[6]), Gf.Vec3d(*map(float, initial[3:6]))))
        camera = UsdGeom.Camera.Define(stage, '/World/DemoCamera')
        camera.CreateClippingRangeAttr(Gf.Vec2f(.001, 20))
        camera.CreateFocalLengthAttr(38)
        camera.CreateHorizontalApertureAttr(36)
        eye = pos + rot.TransformDir(Gf.Vec3d(.16, -.70, .48))
        target = pos + rot.TransformDir(Gf.Vec3d(0, -.055, .12))
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse())
        product = rep.create.render_product(str(camera.GetPath()), (1920, 1080))
        rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        rgb.attach([product])
        detail = UsdGeom.Camera.Define(stage, '/World/BoatDetailCamera')
        detail.CreateClippingRangeAttr(Gf.Vec2f(.001, 20))
        detail.CreateHorizontalApertureAttr(36)
        detail.CreateFocalLengthAttr(85)
        detail_eye = pos + rot.TransformDir(Gf.Vec3d(0, .02, .5))
        detail_target = pos + rot.TransformDir(Gf.Vec3d(0, .02, .17))
        detail.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(
            detail_eye, detail_target, rot.TransformDir(Gf.Vec3d(0, 1, 0))).GetInverse())
        detail_product = rep.create.render_product(str(detail.GetPath()), (600, 500))
        detail_rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        detail_rgb.attach([detail_product])
        script_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(script_root))
        segments = {'0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg',
                    '5': 'acdfg', '6': 'acdefg', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg',
                    '-': 'g', 'O': 'abcdef', 'L': 'def', ' ': ''}
        target_frames = sorted({i-i % a.frame_step for i in [0, len(data['times'])//3,
                                len(data['times'])//2, int(len(data['times'])*.72), len(data['times'])-1]})
        indices = target_frames if a.preview else range(0, len(data['times']), a.frame_step)
        if not a.preview:
            encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo',
                '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '30', '-i', '-', '-an',
                '-c:v', 'libx264', '-threads', '4', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', str(a.out/'task09_weighing_demo.mp4')], stdin=subprocess.PIPE)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 27)
        for frame in indices:
            for path, pose in zip(data['paths'], data['poses'][frame]):
                path = str(path)
                prim = stage.GetPrimAtPath(path)
                parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(0)
                world = Gf.Matrix4d().SetScale(Gf.Vec3d(*map(float, scales[path])))
                world *= Gf.Matrix4d().SetRotate(Gf.Quatd(float(pose[6]), Gf.Vec3d(*map(float, pose[3:6]))))
                world.SetTranslateOnly(Gf.Vec3d(*map(float, pose[:3])))
                xf = UsdGeom.Xformable(prim)
                xf.ClearXformOpOrder()
                attr = prim.GetAttribute('xformOp:transform:recorded')
                op = UsdGeom.XformOp(attr) if attr else xf.AddTransformOp(opSuffix='recorded')
                xf.SetXformOpOrder([op])
                op.Set(world * parent.GetInverse())
            text = str(data['lcd'][frame]).removesuffix(' g')
            places = len(text.split('.')[1]) if '.' in text else -1
            base = root+'/Instance/Body/ControlPanel/LiveDigits'
            for i, char in enumerate(text.replace('.', '').rjust(8)):
                for segment in 'abcdefg':
                    item = stage.GetPrimAtPath(f'{base}/D{i}_{segment}')
                    UsdGeom.Imageable(item).GetVisibilityAttr().Set(
                        'inherited' if segment in segments.get(char, '') else 'invisible')
                UsdGeom.Imageable(stage.GetPrimAtPath(f'{base}/P{i}')).GetVisibilityAttr().Set(
                    'inherited' if i == 7-places and places >= 0 else 'invisible')
            for _ in range(4 if frame == indices[0] else 1):
                rep.orchestrator.step(rt_subframes=4 if a.preview else 2, pause_timeline=True, delta_time=0)
            image = Image.fromarray(rgb.get_data()).convert('RGB')
            closeup = Image.fromarray(detail_rgb.get_data()).convert('RGB')
            image.paste(closeup, (1300, 120))
            draw = ImageDraw.Draw(image)
            draw.rectangle((1298, 96, 1902, 122), fill=(18, 25, 31))
            draw.text((1310, 96), 'Boat detail / same recorded frame', font=font, fill='white')
            draw.rectangle((0, 0, 1920, 88), fill=(18, 25, 31))
            elapsed = float(data['times'][frame]-data['times'][0])
            draw.text((25, 12), f'TASK 09  |  {str(data["phases"][frame])}  |  {elapsed:.1f} s', font=font, fill='white')
            draw.text((25, 48), f'Isaac Sim 4.5 / 120 Hz  |  {a.frame_step}x replay  |  '
                      f'LCD: {str(data["lcd"][frame])}  |  Supported-mass readout', font=font, fill=(207, 218, 225))
            draw.rectangle((0, 1032, 1920, 1080), fill=(18, 25, 31))
            draw.text((25, 1041), 'Solid masses (g): '+ ' / '.join(f'{m:.3f}' for m in masses_g)
                      + f'     |     All-five net target: {sum(masses_g):.5f} g', font=font, fill='white')
            if frame in target_frames:
                dest = a.out/f'frame_{frame:04d}.png'
                image.save(dest)
                report['images'].append(str(dest))
            if encoder:
                encoder.stdin.write(image.tobytes())
            if frame % 120 == 0 or a.preview:
                print('FRAME', frame, str(data['lcd'][frame]), flush=True)
        if encoder:
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError('ffmpeg failed')
            encoder = None
        report['status'] = 'rendered'
        report['frames'] = len(indices)
    except BaseException:
        report['exception'] = traceback.format_exc()
        print(report['exception'], flush=True)
    finally:
        if encoder:
            encoder.kill()
        (a.out/'render_report.json').write_text(json.dumps(report, indent=2))
        app.close(wait_for_replicator=False)
    return 0 if report['status'] == 'rendered' else 1


if __name__ == '__main__':
    raise SystemExit(main())

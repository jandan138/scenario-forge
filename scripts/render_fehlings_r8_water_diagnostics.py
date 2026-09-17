"""Isaac 4.5 in-bath water-optics diagnostics on retained r7 states."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from scripts.generate_fehlings_water_bath_r3 import WATER
from scripts.generate_fehlings_water_bath_r8 import apply_water_optics

STATES = ('t3', 't15', 't30')


def hide_water(stage):
    from pxr import UsdGeom

    for name in ('body', 'surface'):
        UsdGeom.Imageable(stage.GetPrimAtPath(WATER + '/' + name)).MakeInvisible()


def apply_preview_alpha(stage, opacity=0.05):
    from pxr import UsdGeom

    shader = stage.GetPrimAtPath(WATER + '/Looks/Water/Shader')
    shader.GetAttribute('inputs:opacity').Set(opacity)
    for name in ('body', 'surface'):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/' + name))
        mesh.GetDoubleSidedAttr().Set(False)
        UsdGeom.Imageable(mesh.GetPrim()).MakeVisible()


def restore_snapshot(stage, snapshot, tube):
    from pxr import Gf, UsdGeom

    tube.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*snapshot['tube_xyz']))
    attr = stage.GetPrimAtPath('/World/obj_beaker').GetAttribute('xformOp:translate')
    attr.Set(
        Gf.Vec3f(*snapshot['beaker_xyz'])
        if str(attr.GetTypeName()) == 'float3'
        else Gf.Vec3d(*snapshot['beaker_xyz'])
    )
    beaker = stage.GetPrimAtPath('/World/obj_beaker')
    orient = beaker.GetAttribute('xformOp:orient')
    if not orient:
        orient = UsdGeom.Xformable(beaker).AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
    q = snapshot['beaker_quat_xyzw']
    orient.Set(
        Gf.Quatf(q[3], Gf.Vec3f(*q[:3]))
        if str(orient.GetTypeName()) == 'quatf'
        else Gf.Quatd(q[3], Gf.Vec3d(*q[:3]))
    )
    quat = snapshot['tube_quat_xyzw']
    attr = tube.GetAttribute('xformOp:orient')
    if not attr:
        attr = UsdGeom.Xformable(tube).AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
    attr.Set(
        Gf.Quatf(quat[3], Gf.Vec3f(*quat[:3]))
        if str(attr.GetTypeName()) == 'quatf'
        else Gf.Quatd(quat[3], Gf.Vec3d(*quat[:3]))
    )
    paths = tube.GetRelationship('fehlings:layerShaders').GetTargets()
    for path, values in zip(paths, snapshot['layers']):
        shader = stage.GetPrimAtPath(path)
        shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*values['color']))
        shader.GetAttribute('inputs:opacity').Set(values['opacity'])
        shader.GetAttribute('inputs:roughness').Set(values['roughness'])


def capture(camera, rep, np, Image, Rotation, math, out, name, position, target, focal):
    offset = position - target
    elevation = math.degrees(math.asin(offset[2] / np.linalg.norm(offset)))
    azimuth = math.degrees(math.atan2(offset[1], offset[0]))
    q = Rotation.from_euler('xyz', [0, elevation, azimuth - 180], degrees=True).as_quat()
    camera.set_focal_length(focal)
    camera.set_world_pose(position=position, orientation=np.asarray([q[3], *q[:3]]))
    for _ in range(6):
        rep.orchestrator.step(rt_subframes=8, pause_timeline=True, delta_time=0)
    frame = np.asarray(camera.get_rgba())
    if frame.size == 0:
        raise RuntimeError('empty image')
    if frame.dtype != np.uint8:
        frame = np.clip(frame * 255 if frame.max() <= 1 else frame, 0, 255).astype(np.uint8)
    path = out / (name + '.png')
    Image.fromarray(frame[:, :, :3]).save(path)
    return dict(path=str(path), sha256=sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.root, args.report, args.out = args.root.resolve(), args.report.resolve(), args.out.resolve()
    data = json.loads(args.report.read_text())
    if data['status'] != 'pass' or data['scene_sha256'] != sha256((args.root / 'scene.usd').read_bytes()).hexdigest():
        raise ValueError('no passing exact-scene capture')
    argv = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {'headless': True, 'renderer': 'RayTracedLighting', 'width': 1920, 'height': 1080, 'multi_gpu': False}
    )
    sys.argv = argv
    temporary = args.root / '.fehlings_r8_diag.usda'
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        import math

        import carb.settings
        import numpy as np
        import omni.replicator.core as rep
        import omni.usd
        from isaacsim.sensors.camera import Camera
        from PIL import Image
        from pxr import Sdf, Usd
        from scipy.spatial.transform import Rotation

        layer = Sdf.Layer.CreateNew(str(temporary))
        layer.TransferContent(Sdf.Layer.FindOrOpen(str(args.root / 'scene.usd')))
        layer.GetPrimAtPath('/World/obj_sample_tube/ReactionRuntime/FehlingsGraph').active = False
        layer.Save()
        context = omni.usd.get_context()
        context.open_stage(str(temporary))
        while context.get_stage_loading_status()[2]:
            app.update()
        for _ in range(40):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        settings = carb.settings.get_settings()
        settings.set('/rtx/post/aa/autoExposureMode', 0)
        settings.set('/rtx/post/aa/exposureMultiplier', 0.92)
        settings.set('/rtx/translucency/maxRefractionBounces', 12)
        camera = Camera(prim_path='/World/__fehlings_camera', resolution=(1920, 1080))
        camera.initialize()
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(11.784)
        camera.set_clipping_range(0.005, 100)
        tube = stage.GetPrimAtPath('/World/obj_sample_tube')
        snapshots = {item['name']: item for item in data['snapshots'] if item['name'] in STATES}
        if set(STATES) - set(snapshots):
            raise ValueError('retained t3/t15/t30 states required')
        records = []
        variants = (
            ('hide', hide_water),
            ('preview_alpha', apply_preview_alpha),
            ('omniglass', apply_water_optics),
        )
        for variant, apply in variants:
            apply(stage)
            for name, snapshot in snapshots.items():
                restore_snapshot(stage, snapshot, tube)
                target = np.asarray(snapshot['tube_xyz']) + np.asarray([0, 0, 0.035])
                records.append(
                    capture(
                        camera,
                        rep,
                        np,
                        Image,
                        Rotation,
                        math,
                        args.out,
                        variant + '_' + name + '_closeup',
                        target + np.asarray([0.25, -0.38, 0.15]),
                        target,
                        45,
                    )
                )
                print('CAPTURE', records[-1]['path'], flush=True)
        (args.out / 'render_manifest.json').write_text(
            json.dumps(
                dict(
                    status='pass',
                    scene_sha256=data['scene_sha256'],
                    report_sha256=sha256(args.report.read_bytes()).hexdigest(),
                    variants=['hide', 'preview_alpha', 'omniglass'],
                    states=list(STATES),
                    images=records,
                ),
                indent=2,
            )
            + '\n'
        )
    finally:
        temporary.unlink(missing_ok=True)
        app.close()


if __name__ == '__main__':
    main()

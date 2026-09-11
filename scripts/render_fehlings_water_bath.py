"""Isaac 4.5 renders of exact retained physics milestone states (not live video)."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument('--diagnostic-no-shadows', action='store_true')
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.report = args.report.resolve()
    data = json.loads(args.report.read_text())
    if (
        data["status"] != "pass"
        or data["scene_sha256"] != sha256((args.root / "scene.usd").read_bytes()).hexdigest()
    ):
        raise ValueError("no passing exact-scene capture")
    argv = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "width": 1920,
            "height": 1080,
            "multi_gpu": False,
        }
    )
    sys.argv = argv
    temporary = args.root / ".fehlings_render.usda"
    try:
        import numpy as np
        import carb.settings
        import omni.usd
        import omni.replicator.core as rep
        from isaacsim.sensors.camera import Camera
        from PIL import Image
        from pxr import Gf, Sdf, Usd, UsdGeom
        import math
        from scipy.spatial.transform import Rotation

        layer = Sdf.Layer.CreateNew(str(temporary))
        layer.TransferContent(Sdf.Layer.FindOrOpen(str(args.root / "scene.usd")))
        layer.GetPrimAtPath("/World/obj_sample_tube/ReactionRuntime/FehlingsGraph").active = False
        layer.Save()
        context = omni.usd.get_context()
        context.open_stage(str(temporary))
        while context.get_stage_loading_status()[2]:
            app.update()
        for _ in range(40):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        if args.diagnostic_no_shadows:
            for path in ('/World/fluid_runtime','/World/fluid_runtime/ParticleSystem',
                         '/World/fluid_runtime/ParticleSets/beaker_liquid','/World/obj_sample_tube/VisualLiquid'):
                UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(path)).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
            for path in ('/World/obj_sample_tube/Visual','/World/obj_beaker/Visual', '/World/obj_sample_tube/VisualLiquid'):
                for prim in Usd.PrimRange(stage.GetPrimAtPath(path)):
                    if prim.IsA(UsdGeom.Mesh):
                        UsdGeom.PrimvarsAPI(prim).CreatePrimvar('doNotCastShadows',Sdf.ValueTypeNames.Bool).Set(True)
        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.92)
        camera = Camera(prim_path="/World/__fehlings_camera", resolution=(1920, 1080))
        camera.initialize()
        camera.set_horizontal_aperture(20.955)
        camera.set_vertical_aperture(11.784)
        camera.set_clipping_range(0.005, 100)
        out = args.root / "evidence/initial_scene"
        if args.diagnostic_no_shadows:
            out = args.root/'evidence/diagnostic_no_shadows'
        out.mkdir(parents=True, exist_ok=True)
        records = []
        tube = stage.GetPrimAtPath("/World/obj_sample_tube")
        particles = stage.GetPrimAtPath("/World/fluid_runtime/ParticleSets/beaker_liquid")
        for snapshot in data["snapshots"]:
            name = snapshot["name"]
            five_layers = data.get('policy_version') == 'visual_five_layers_v6'
            selected = ("initial", "outside_no_heating", "t10", "t30", "t37_5", "t45", "t52_5", "t60", "t120", "pause_begin", "shallow_contact", "tilted_contact", "partial_contact", "dynamic_insert", "observed", "reset")
            if five_layers:
                selected = ("initial", "outside_no_heating", "pause_begin", "shallow_contact", "tilted_contact", "observed", "reset") + tuple(
                    't'+str(t)+suffix for t in (3,9,15,21,27,30) for suffix in ('','_withdrawn'))
            if name not in selected:
                continue
            tube.GetAttribute("xformOp:translate").Set(Gf.Vec3d(*snapshot["tube_xyz"]))
            if 'beaker_xyz' in snapshot:
                attr = stage.GetPrimAtPath('/World/obj_beaker').GetAttribute('xformOp:translate')
                attr.Set(Gf.Vec3f(*snapshot['beaker_xyz']) if str(attr.GetTypeName()) == 'float3'
                         else Gf.Vec3d(*snapshot['beaker_xyz']))
            if 'beaker_quat_xyzw' in snapshot:
                beaker=stage.GetPrimAtPath('/World/obj_beaker')
                orient=beaker.GetAttribute('xformOp:orient')
                if not orient:
                    orient=UsdGeom.Xformable(beaker).AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
                q=snapshot['beaker_quat_xyzw']
                orient.Set(Gf.Quatf(q[3],Gf.Vec3f(*q[:3])) if str(orient.GetTypeName())=='quatf' else Gf.Quatd(q[3],Gf.Vec3d(*q[:3])))
            quat = snapshot["tube_quat_xyzw"]
            attr = tube.GetAttribute("xformOp:orient")
            if not attr:
                attr = UsdGeom.Xformable(tube).AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
            attr.Set(
                Gf.Quatf(quat[3], Gf.Vec3f(*quat[:3]))
                if str(attr.GetTypeName()) == "quatf"
                else Gf.Quatd(quat[3], Gf.Vec3d(*quat[:3]))
            )
            if 'particle_points' in snapshot:
                pts = [Gf.Vec3f(*p) for p in snapshot["particle_points"]]
                particles.GetAttribute("points").Set(pts)
                particles.GetAttribute("physxParticle:simulationPoints").Set(pts)
                arr = np.asarray(snapshot["particle_points"])
                particles.GetAttribute("extent").Set(
                    [Gf.Vec3f(*arr.min(axis=0)), Gf.Vec3f(*arr.max(axis=0))]
                )
            if five_layers:
                paths = tube.GetRelationship('fehlings:layerShaders').GetTargets()
                if len(paths)!=5 or len(snapshot['layers'])!=5:
                    raise ValueError('five retained material states required')
                for path,values in zip(paths,snapshot['layers']):
                    shader=stage.GetPrimAtPath(path)
                    shader.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*values['color']))
                    shader.GetAttribute('inputs:opacity').Set(values['opacity'])
                    shader.GetAttribute('inputs:roughness').Set(values['roughness'])
            else:
                shader = stage.GetPrimAtPath("/World/obj_sample_tube/VisualLiquid/Looks/Sample/Shader")
                shader.GetAttribute("inputs:diffuseColor").Set(Gf.Vec3f(*snapshot["sample_color"]))
                shader.GetAttribute("inputs:opacity").Set(snapshot["sample_opacity"])
                sediment = stage.GetPrimAtPath("/World/obj_sample_tube/VisualLiquid/Sediment")
                UsdGeom.Imageable(sediment).GetVisibilityAttr().Set(
                    "inherited" if snapshot["sediment_opacity"] > 0 else "invisible"
                )
                stage.GetPrimAtPath(
                    "/World/obj_sample_tube/VisualLiquid/Looks/Sediment/Shader"
                ).GetAttribute("inputs:opacity").Set(snapshot["sediment_opacity"])
            if data.get('policy_version') == 'visual_fixed_regions_v5':
                shader.GetAttribute('inputs:roughness').Set(snapshot['sample_roughness'])
                lower=stage.GetPrimAtPath('/World/obj_sample_tube/VisualLiquid/Looks/Sediment/Shader')
                lower.GetAttribute('inputs:diffuseColor').Set(Gf.Vec3f(*snapshot['sediment_color']))
                lower.GetAttribute('inputs:roughness').Set(snapshot['sediment_roughness'])
            for relative,values in snapshot.get('geometry',{}).items():
                mesh=stage.GetPrimAtPath('/World/obj_sample_tube/'+relative)
                points=np.asarray(values['points'])
                mesh.GetAttribute('points').Set([Gf.Vec3f(*p) for p in points])
                mesh.GetAttribute('extent').Set([Gf.Vec3f(*points.min(axis=0)),Gf.Vec3f(*points.max(axis=0))])
                mesh.GetAttribute('visibility').Set(values['visibility'])
            target = np.asarray(snapshot["tube_xyz"]) + np.asarray([0, 0, 0.035])
            views = [("closeup", target + np.asarray([0.25, -0.38, 0.15]), target, 45)]
            if name == "initial":
                views.append(
                    (
                        "scene_overview",
                        np.asarray([1.35, -2.05, 1.75]),
                        np.asarray([0.12, -0.03, 0.84]),
                        31,
                    )
                )
            for view, position, target, focal in views:
                offset = position - target
                elevation = math.degrees(math.asin(offset[2] / np.linalg.norm(offset)))
                azimuth = math.degrees(math.atan2(offset[1], offset[0]))
                q = Rotation.from_euler(
                    "xyz", [0, elevation, azimuth - 180], degrees=True
                ).as_quat()
                camera.set_focal_length(focal)
                camera.set_world_pose(position=position, orientation=np.asarray([q[3], *q[:3]]))
                for _ in range(6):
                    rep.orchestrator.step(rt_subframes=8, pause_timeline=True, delta_time=0)
                frame = np.asarray(camera.get_rgba())
                if frame.size == 0:
                    raise RuntimeError("empty image")
                if frame.dtype != np.uint8:
                    frame = np.clip(frame * 255 if frame.max() <= 1 else frame, 0, 255).astype(
                        np.uint8
                    )
                path = out / (
                    ("scene_overview" if view == "scene_overview" else name + "_" + view) + ".png"
                )
                Image.fromarray(frame[:, :, :3]).save(path)
                records.append(
                    {
                        "path": str(path.relative_to(args.root)),
                        "sha256": sha256(path.read_bytes()).hexdigest(),
                        "physics_step": snapshot["step"],
                        "heated_s": snapshot["heated_s"],
                    }
                )
                print("CAPTURE", path, flush=True)
        (out / "render_manifest.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "scene_sha256": data["scene_sha256"],
                    "policy_version": data.get("policy_version", "visual_reaction_v1"),
                    "runtime": "Isaac Sim 4.5",
                    "method": "paused_physics_replay_of_retained_milestone_states",
                    "live_camera_physics_capture": False,
                    "snapshot_step_kind": "fixture_world_step" if data.get("policy_version") in ("visual_water_contact_v3", "visual_fixed_regions_v5", "visual_five_layers_v6") else "legacy_fixture_step",
                    "report_sha256": sha256(args.report.read_bytes()).hexdigest(),
                    "images": records,
                },
                indent=2,
            )
            + "\n"
        )
    except Exception:
        import traceback
        traceback.print_exc()
        raise
    finally:
        temporary.unlink(missing_ok=True)
        app.close()


if __name__ == "__main__":
    main()

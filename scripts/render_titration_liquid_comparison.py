"""Isaac same-camera visual snapshots for the fitted-liquid revision."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

VIEWS = (
    ('scene_overview', (1.55, -2.05, 1.80), (0.0, 0.02, 0.90), 30.0),
    ('flask_detail', (0.32, -0.52, 1.09), (-0.03, 0.03, 0.895), 45.0),
    ('flask_top_oblique', (0.19, -0.30, 1.17), (-0.03, 0.03, 0.89), 45.0),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', choices=('before', 'after'), required=True)
    parser.add_argument('--refraction-bounces', type=int)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--thin-liquid', action='store_true', help='Diagnostic session-only transmission comparison')
    parser.add_argument('--liquid-ior', type=float, help='Diagnostic session-only IOR comparison')
    parser.add_argument('--no-liquid-shadow', action='store_true')
    parser.add_argument('--burette-views', action='store_true')
    parser.add_argument('--linear-states', action='store_true', help='Render r1.5 cumulative-volume color states')
    parser.add_argument('--tip-detail', action='store_true', help='Close views of the nozzle wall and outlet')
    parser.add_argument('--follow-task-pose', action='store_true', help='Translate cameras with the receiver placement')
    args = parser.parse_args()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'renderer': 'RayTracedLighting', 'anti_aliasing': 4,
                         'width': 1920, 'height': 1080, 'multi_gpu': False})
    sys.argv = original
    try:
        import carb.settings
        import numpy as np
        import omni.usd
        import omni.replicator.core as rep
        try:
            from isaacsim.sensors.camera import Camera
        except ImportError:
            from omni.isaac.sensor import Camera
        from scipy.spatial.transform import Rotation
        from PIL import Image
        from pxr import Usd, UsdGeom

        settings = carb.settings.get_settings()
        settings.set_bool('/app/omni.graph.scriptnode/enable_opt_in', False)
        settings.set_bool('/app/omni.graph.scriptnode/opt_in', True)
        settings.set('/rtx/post/aa/autoExposureMode', 0)
        settings.set('/rtx/post/aa/exposureMultiplier', 0.92)
        if args.refraction_bounces is not None:
            settings.set('/rtx/translucency/maxRefractionBounces', args.refraction_bounces)
        print('REFRACTION_BOUNCES', settings.get('/rtx/translucency/maxRefractionBounces'), flush=True)
        out = args.root/'evidence/initial_scene'
        if args.quick:
            out = args.root/f'evidence/diagnostic_bounces_{args.refraction_bounces}'
            if args.thin_liquid:
                out = args.root/'evidence/diagnostic_thin_liquid'
            if args.liquid_ior is not None:
                out = args.root/f'evidence/diagnostic_ior_{args.liquid_ior}'
            if args.no_liquid_shadow:
                out = args.root/'evidence/diagnostic_no_liquid_shadow'
        out.mkdir(parents=True, exist_ok=True)
        records = []
        context = omni.usd.get_context()
        for label, root in [(args.variant, args.baseline if args.variant == 'before' else args.root)]:
            from pxr import Sdf
            render_scene = root / '.titration_render_scene.usda'
            layer = Sdf.Layer.FindOrOpen(str(root / 'scene.usd'))
            temporary = Sdf.Layer.CreateNew(str(render_scene))
            temporary.TransferContent(layer)
            temporary.GetPrimAtPath('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph').active = False
            temporary.Save()
            if not context.open_stage(str(render_scene)):
                raise RuntimeError('cannot open scene')
            stage = context.get_stage()
            stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
            station = stage.GetPrimAtPath('/World/obj_titration_station')
            shader_targets = station.GetRelationship('titration:receiverLiquidShader').GetTargets()
            visual_targets = station.GetRelationship('titration:receiverLiquidVisuals').GetTargets()
            if args.thin_liquid:
                for target in shader_targets:
                    stage.GetPrimAtPath(target).GetAttribute('inputs:thin_walled').Set(True)
            if args.liquid_ior is not None:
                for target in shader_targets:
                    stage.GetPrimAtPath(target).GetAttribute('inputs:glass_ior').Set(args.liquid_ior)
            if args.no_liquid_shadow:
                for target in visual_targets:
                    UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(target)).CreatePrimvar('doNotCastShadows', Sdf.ValueTypeNames.Bool).Set(True)
            stage.GetPrimAtPath('/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph').SetActive(False)
            while context.get_stage_loading_status()[2]:
                app.update()
            for _ in range(30):
                app.update()
            camera = Camera(prim_path='/World/__liquid_evidence_camera', resolution=(1920,1080))
            camera.initialize()
            camera.set_horizontal_aperture(20.955)
            camera.set_vertical_aperture(11.784)
            camera.set_clipping_range(0.005, 100)
            phases = ('initial', 'mid', 'end_scale') if args.burette_views else ('initial','endpoint')
            if args.linear_states and not args.burette_views:
                phases = ('initial', 'transition', 'endpoint', 'overshoot')
            for phase in (('initial',) if args.quick else phases):
                suffix = 'Colorless' if phase=='initial' else 'EndpointPalePink'
                if args.burette_views:
                    suffix = 'Overshoot' if phase == 'end_scale' else 'Colorless'
                    from pxr import Gf
                    remaining = {'initial': 25, 'mid': 12.5, 'end_scale': 0}[phase]
                    height = 0.32*remaining/25
                    base = '/World/obj_titration_station/Instance/Burette/body_link/Visual/'
                    column = stage.GetPrimAtPath(base+'liquid_column')
                    meniscus = stage.GetPrimAtPath(base+'liquid_meniscus')
                    cap = 0.0003 if meniscus.GetTypeName() == 'Mesh' else 0
                    h = max(0.0001, height-cap)
                    column.GetAttribute('height').Set(h)
                    column.GetAttribute('xformOp:translate').Set(Gf.Vec3d(0,0,-0.09+h/2))
                    meniscus.GetAttribute('xformOp:translate').Set(Gf.Vec3d(0,0,-0.09+height))
                    # Initial captures preserve authored visibility; later states mirror the controller.
                    if phase != 'initial':
                        for prim in (column, meniscus):
                            UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if remaining else 'invisible')
                station = stage.GetPrimAtPath('/World/obj_titration_station')
                for target in station.GetRelationship('titration:receiverLiquidVisuals').GetTargets():
                    prim = stage.GetPrimAtPath(target)
                    phase_attr = prim.GetAttribute('titration:phase')
                    enabled = not phase_attr or prim.GetName() == 'Solution'+suffix
                    UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if enabled else 'invisible')
                if args.linear_states or args.burette_views:
                    from pxr import Gf
                    from scripts.titration_linear_policy import TRANSITION_START, PINK_END, color
                    from scripts.generate_traditional_titration_vr_r15 import STATION
                    volume = (25-{'initial':25,'mid':12.5,'end_scale':0}[phase] if args.burette_views
                              else {'initial':0,'transition':(TRANSITION_START+15)/2,'endpoint':15.5,'overshoot':PINK_END+1}[phase])
                    state, rgb, opacity = color(volume)
                    suffix = {'colorless': 'Colorless', 'transition': 'Transition',
                              'endpoint_pale_pink': 'EndpointPalePink', 'overshoot': 'Overshoot'}[state]
                    station = stage.GetPrimAtPath(STATION)
                    for target in station.GetRelationship('titration:receiverLiquidShader').GetTargets():
                        shader = stage.GetPrimAtPath(target)
                        shader.GetAttribute('inputs:glass_color').Set(Gf.Vec3f(*rgb))
                    for target in station.GetRelationship('titration:receiverLiquidVisuals').GetTargets():
                        prim = stage.GetPrimAtPath(target)
                        enabled = not prim.GetAttribute('titration:phase') or prim.GetName() == 'Solution'+suffix
                        prim.GetAttribute('visibility').Set('inherited' if enabled else 'invisible')
                    base = STATION+'/Instance/Burette/body_link/Visual/'
                    height = .32*(25-volume)/25
                    col = stage.GetPrimAtPath(base+'liquid_column')
                    h = max(.0001, height-.0003)
                    col.GetAttribute('height').Set(h)
                    col.GetAttribute('xformOp:translate').Set(Gf.Vec3d(0, 0, -.09+h/2))
                    stage.GetPrimAtPath(base+'liquid_meniscus').GetAttribute('xformOp:translate').Set(Gf.Vec3d(0, 0, -.09+height))
                views = VIEWS
                if args.burette_views:
                    views = (VIEWS[0], VIEWS[1],
                             ('burette_full', (0.45,-0.90,1.33), (-0.03,0.03,1.28), 20),
                             ('burette_lower', (0.19,-0.32,1.12), (-0.03,0.03,1.10), 27),
                             ('burette_surface', (0.15,-0.27,1.49), (-0.03,0.03,1.48), 35))
                if args.tip_detail:
                    views = (*views,
                        ('tip_side',(.07,-.15,1.027),(-.03,.03,1.015),35),
                        ('tip_outlet',(.01,-.02,.97),(-.03,.03,.99),70))
                shift = np.zeros(3)
                if args.follow_task_pose:
                    pose = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath('/World/obj_receiver_flask')).ExtractTranslation()
                    shift = np.asarray(pose)-np.asarray([-.03,.03,.8267])
                for view, position, target, focal in (views[1:2] if args.quick else views):
                    position = tuple(float(v) for v in np.asarray(position)+shift)
                    target = tuple(float(v) for v in np.asarray(target)+shift)
                    camera.set_focal_length(focal)
                    offset = np.asarray(position)-np.asarray(target)
                    elevation = math.degrees(math.asin(offset[2]/np.linalg.norm(offset)))
                    azimuth = math.degrees(math.atan2(offset[1], offset[0]))
                    quat = Rotation.from_euler('xyz', [0, elevation, azimuth-180], degrees=True).as_quat()
                    camera.set_world_pose(position=np.asarray(position), orientation=np.asarray([quat[3],*quat[:3]]))
                    for _ in range(8):
                        rep.orchestrator.step(rt_subframes=8, pause_timeline=True, delta_time=0.0)
                    rgba = np.asarray(camera.get_rgba())
                    if rgba.size == 0:
                        raise RuntimeError('empty camera frame')
                    if rgba.dtype != np.uint8:
                        rgba = np.clip(rgba*255 if rgba.max()<=1 else rgba, 0,255).astype(np.uint8)
                    path = out/f'{label}_{phase}_{view}.png'
                    Image.fromarray(rgba[:,:,:3]).save(path)
                    records.append({'path': str(path.relative_to(args.root)), 'sha256':sha256(path.read_bytes()).hexdigest(),
                                    'state':phase, 'variant':label,'view':view,'camera_position':position,'target':target})
                    print('CAPTURE '+str(path), flush=True)
        (out/f'render_manifest_{args.variant}.json').write_text(json.dumps({'status':'pass','renderer':'RayTracedLighting',
            'runtime_version': app.app.get_app_version(),
            'scene_sha256': sha256((root/'scene.usd').read_bytes()).hexdigest(),
            'linear_policy_color_states': args.linear_states,
            'burette_views': args.burette_views, 'tip_detail': args.tip_detail, 'follow_task_pose': args.follow_task_pose,
            'refraction_bounces': settings.get('/rtx/translucency/maxRefractionBounces'),
            'resolution':[1920,1080],'views':records,'endpoint_is_visual_state_snapshot':True},indent=2)+'\n')
    finally:
        if 'render_scene' in locals():
            render_scene.unlink(missing_ok=True)
        app.close()


if __name__ == '__main__':
    main()

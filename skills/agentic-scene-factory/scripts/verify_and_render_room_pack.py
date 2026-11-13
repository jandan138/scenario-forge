#!/usr/bin/env python3
"""Deterministic Blender 4.4.3 room gate and 6-view Cycles AgX renderer.

Invoke with Blender 4.4.3:
  blender --background --python skills/agentic-scene-factory/scripts/verify_and_render_room_pack.py -- \\
    --source-script <room_builder.py> --out-dir <renders_dir> [--clearance-xy 4.2 4.0]

Hard-checks configurable structural, texture, floor-flatness, and central
workcell clearance gates, renders the 6 canonical inspection views:
  - corner_ne.png
  - corner_nw.png
  - corner_se.png
  - corner_sw.png
  - entrance_eye_level.png
  - topdown_floorplan.png
(hiding ceiling occluders from camera rays on topdown/corner overhead views and
entrance door leaves on entrance_eye_level), writes ``room_gate_report.json``,
and exits non-zero if any gate fails.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA_VERSION = "scenario-forge-room-gate-report/v1.0"
CEILING_NAME_RE = re.compile(
    r"(ceiling|roof|soffit|tgrid|troffer|baffle|hvac|diffuser|sprinkler|pendant|linear_led|suspended_light)",
    re.IGNORECASE,
)
DOOR_LEAF_NAME_RE = re.compile(
    r"(door_?0|door_?1|doorleaf|door_leaf|doorpull|door_pull|push_bar|airlock.*(leaf|window|push_bar|closer)|sidelight|daylight|entrance.*leaf)",
    re.IGNORECASE,
)
PROP_NAME_RE = re.compile(
    r"(^prop_|_prop_|minorplace_|orphan_|__top__|cup|mug|bottle|canister|kettle|dripper|scale|hopper|portafilter|tamper|oscilloscope|multimeter|microscope|solder|reel|pcba|bin|binder|ream|toner|trimmer|stapler|monitor|keyboard|mouse|lamp|clock|plant|plush|poster|board|printer|phone|pad|notebook|pen)",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--source-script", type=Path, help="Python room builder script.")
    src_group.add_argument("--blend-file", type=Path, help="Existing .blend file to inspect/render.")
    src_group.add_argument("--usd-file", type=Path, help="Existing .usd/.usda/.usdc file to inspect/render.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for 6 PNGs and report.")
    parser.add_argument("--report-json", type=Path, default=None, help="Optional override path for room_gate_report.json.")
    parser.add_argument("--room-id", default=None, help="Optional logical room identifier.")
    parser.add_argument(
        "--clearance-xy",
        nargs=2,
        type=float,
        default=[4.2, 4.0],
        metavar=("WIDTH_M", "DEPTH_M"),
        help="Central open-floor clearance width (X) and depth (Y) in meters (default: 4.2 4.0).",
    )
    parser.add_argument(
        "--clearance-center-xy",
        nargs=2,
        type=float,
        default=[0.0, 0.0],
        metavar=("CENTER_X_M", "CENTER_Y_M"),
        help="Center (X, Y) of the clearance zone in meters (default: 0.0 0.0).",
    )
    parser.add_argument(
        "--clearance-z-max",
        type=float,
        default=2.60,
        help="Upper Z bound of central robot/workcell clearance box in meters (default: 2.60).",
    )
    parser.add_argument(
        "--floor-max-z",
        type=float,
        default=0.003,
        help="Maximum allowed Z (m) for floor slab/seams inside central clearance (default: 0.003).",
    )
    parser.add_argument("--min-assemblies", type=int, default=18)
    parser.add_argument("--min-total-meshes", "--min-meshes", dest="min_total_meshes", type=int, default=200)
    parser.add_argument("--min-props", type=int, default=25)
    parser.add_argument("--resolution", nargs=2, type=int, default=[1280, 960], metavar=("W", "H"))
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--skip-render", action="store_true", help="Run deterministic gate checks without rendering.")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args()

    import bpy  # type: ignore[import-not-found]
    import mathutils  # type: ignore[import-not-found]

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = (args.report_json.resolve() if args.report_json else out_dir / "room_gate_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    source_kind = ""
    source_path: Path
    if args.source_script is not None:
        source_kind = "python_script"
        source_path = args.source_script.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"missing --source-script: {source_path}")
        namespace: dict[str, Any] = {
            "__name__": "__main__",
            "__file__": str(source_path),
        }
        code = source_path.read_text(encoding="utf-8")
        exec(compile(code, str(source_path), "exec"), namespace, namespace)
    elif args.blend_file is not None:
        source_kind = "blend_file"
        source_path = args.blend_file.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"missing --blend-file: {source_path}")
        bpy.ops.wm.open_mainfile(filepath=str(source_path))
    else:
        source_kind = "usd_file"
        source_path = args.usd_file.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"missing --usd-file: {source_path}")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.usd_import(filepath=str(source_path))

    bpy.context.view_layer.update()
    room_id = args.room_id or source_path.parent.name

    # Helper functions on Blender objects
    def _obj_world_aabb(obj: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        pts = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
        return (
            (min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)),
            (max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)),
        )

    def _descendants(root: Any) -> list[Any]:
        res = [root]
        for child in root.children:
            res.extend(_descendants(child))
        return res

    def _in_prop_collection(obj: Any) -> bool:
        def _check_coll(coll: Any) -> bool:
            if "prop" in coll.name.lower():
                return True
            return False

        return any(_check_coll(c) for c in obj.users_collection)

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH" and not obj.hide_render]
    total_mesh_count = len(mesh_objects)

    # Count multi-part assemblies: top-level hierarchies with >=2 meshes OR prefix groups
    top_roots = [obj for obj in bpy.data.objects if obj.parent is None and obj.type not in {"CAMERA", "LIGHT"}]
    multipart_roots = [
        obj.name
        for obj in top_roots
        if sum(1 for d in _descendants(obj) if d.type == "MESH") >= 2
    ]
    prefix_groups = {
        "_".join(obj.name.split("_")[:2])
        for obj in mesh_objects
        if "_" in obj.name and not obj.name.lower().startswith(("arch_", "wall", "floor", "ceiling"))
    }
    assembly_count = max(len(multipart_roots), len(prefix_groups))

    # Count domain props
    prop_meshes: list[str] = []
    prop_roots: set[str] = set()
    for obj in mesh_objects:
        bmin, bmax = _obj_world_aabb(obj)
        dx = bmax[0] - bmin[0]
        dy = bmax[1] - bmin[1]
        dz = bmax[2] - bmin[2]
        vol = dx * dy * dz
        ancestors = []
        cur = obj
        while cur is not None:
            ancestors.append(cur.name)
            cur = cur.parent
        is_named_prop = (
            _in_prop_collection(obj)
            or any(PROP_NAME_RE.search(name) for name in ancestors)
        )
        is_geom_prop = (
            bmin[2] >= 0.35
            and bmax[2] <= 2.45
            and max(dx, dy) <= 0.85
            and vol <= 0.12
            and not any(
                k in obj.name.lower()
                for k in ("wall", "floor", "ceiling", "window", "door", "column", "baseboard")
            )
        )
        if is_named_prop or is_geom_prop:
            prop_meshes.append(obj.name)
            prop_roots.add(ancestors[-1])

    prop_count = max(len(prop_roots), len(prop_meshes))

    # Texture audit
    ignored_images = {"Render Result", "Viewer Node"}
    texture_records: list[dict[str, object]] = []
    packed_textures: list[str] = []
    missing_textures: list[str] = []
    file_backed_count = 0
    for image in sorted(bpy.data.images, key=lambda im: im.name):
        if image.name in ignored_images:
            continue
        is_packed = image.packed_file is not None
        if is_packed:
            packed_textures.append(image.name)
        exists = False
        resolved_str = ""
        if image.source == "FILE":
            resolved = Path(bpy.path.abspath(image.filepath)).resolve()
            resolved_str = str(resolved)
            exists = resolved.is_file()
            if exists and not is_packed:
                file_backed_count += 1
            if not exists:
                missing_textures.append(image.name)
        else:
            missing_textures.append(f"{image.name} (source={image.source})")
        texture_records.append(
            {
                "name": image.name,
                "source": image.source,
                "filepath": image.filepath,
                "resolved": resolved_str,
                "exists": exists,
                "packed": is_packed,
            }
        )
    textures_pass = (
        file_backed_count >= 1
        and len(packed_textures) == 0
        and len(missing_textures) == 0
    )

    # Central clearance & raised floor strip check (polygon-exact broadphase + narrowphase)
    cx, cy = float(args.clearance_center_xy[0]), float(args.clearance_center_xy[1])
    half_w, half_d = float(args.clearance_xy[0]) / 2.0, float(args.clearance_xy[1]) / 2.0
    c_xmin, c_xmax = cx - half_w, cx + half_w
    c_ymin, c_ymax = cy - half_d, cy + half_d
    floor_max_z = float(args.floor_max_z)
    c_zmax = float(args.clearance_z_max)

    raised_floor_strips: list[dict[str, object]] = []
    clearance_intrusions: list[dict[str, object]] = []

    for obj in mesh_objects:
        bmin, bmax = _obj_world_aabb(obj)
        # Broadphase AABB overlap against (c_xmin, c_xmax) x (c_ymin, c_ymax) x (floor_max_z, c_zmax)
        if (
            bmax[0] <= c_xmin
            or bmin[0] >= c_xmax
            or bmax[1] <= c_ymin
            or bmin[1] >= c_ymax
            or bmax[2] <= floor_max_z
            or bmin[2] >= c_zmax
        ):
            continue

        # Narrowphase polygon AABB check so hollow 4-wall room shells never false-positive
        mesh = obj.data
        mw = obj.matrix_world
        world_verts = [mw @ v.co for v in mesh.vertices]
        intruding_poly_zmax = None
        intruding_poly_zmin = None
        for poly in mesh.polygons:
            pts = [world_verts[idx] for idx in poly.vertices]
            px0, px1 = min(p.x for p in pts), max(p.x for p in pts)
            py0, py1 = min(p.y for p in pts), max(p.y for p in pts)
            pz0, pz1 = min(p.z for p in pts), max(p.z for p in pts)
            if (
                px1 > c_xmin + 1e-4
                and px0 < c_xmax - 1e-4
                and py1 > c_ymin + 1e-4
                and py0 < c_ymax - 1e-4
                and pz1 > floor_max_z + 1e-5
                and pz0 < c_zmax - 1e-4
            ):
                intruding_poly_zmax = pz1 if intruding_poly_zmax is None else max(intruding_poly_zmax, pz1)
                intruding_poly_zmin = pz0 if intruding_poly_zmin is None else min(intruding_poly_zmin, pz0)
        if intruding_poly_zmax is not None:
            entry = {
                "object": obj.name,
                "aabb_min": [round(v, 4) for v in bmin],
                "aabb_max": [round(v, 4) for v in bmax],
                "intruding_z_range": [round(float(intruding_poly_zmin), 4), round(float(intruding_poly_zmax), 4)],
            }
            if intruding_poly_zmax <= 0.08:
                raised_floor_strips.append(entry)
            else:
                clearance_intrusions.append(entry)

    density_pass = (assembly_count >= args.min_assemblies) or (total_mesh_count >= args.min_total_meshes)
    props_pass = prop_count >= args.min_props
    floor_flat_pass = len(raised_floor_strips) == 0
    clearance_pass = len(clearance_intrusions) == 0

    # Estimate interior room envelope for camera placement (clamp out distant sky cards > 12m)
    interior_boxes = []
    for obj in mesh_objects:
        bmin, bmax = _obj_world_aabb(obj)
        if max(abs(bmin[0]), abs(bmax[0]), abs(bmin[1]), abs(bmax[1])) <= 12.0:
            interior_boxes.append((bmin, bmax))
    if interior_boxes:
        r_xmin = min(b[0][0] for b in interior_boxes)
        r_xmax = max(b[1][0] for b in interior_boxes)
        r_ymin = min(b[0][1] for b in interior_boxes)
        r_ymax = max(b[1][1] for b in interior_boxes)
        r_zmax = min(4.2, max(2.6, max(b[1][2] for b in interior_boxes)))
    else:
        r_xmin, r_xmax, r_ymin, r_ymax, r_zmax = -4.2, 4.2, -4.2, 4.2, 3.2

    rcx = (r_xmin + r_xmax) / 2.0
    rcy = (r_ymin + r_ymax) / 2.0

    # Identify ceiling occluders and entrance door leaf occluders
    ceiling_occluders: list[Any] = []
    entrance_occluders: list[Any] = []
    for obj in mesh_objects:
        bmin, bmax = _obj_world_aabb(obj)
        dx, dy = bmax[0] - bmin[0], bmax[1] - bmin[1]
        if CEILING_NAME_RE.search(obj.name) or (bmin[2] >= r_zmax - 0.55 and max(dx, dy) >= 0.25):
            ceiling_occluders.append(obj)
        if DOOR_LEAF_NAME_RE.search(obj.name) or (
            bmin[1] <= r_ymin + 0.55
            and bmax[1] <= r_ymin + 0.95
            and abs(((bmin[0] + bmax[0]) / 2.0) - rcx) <= 1.35
            and "door" in obj.name.lower()
        ):
            entrance_occluders.append(obj)

    rendered_views: dict[str, dict[str, object]] = {}
    if not args.skip_render:
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.samples = int(args.samples)
        scene.cycles.use_denoising = True
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.get_devices()
            gpu_found = False
            for dev_type in ("OPTIX", "CUDA"):
                prefs.compute_device_type = dev_type
                prefs.get_devices()
                for dev in prefs.devices:
                    if dev.type == dev_type:
                        dev.use = True
                        gpu_found = True
                if gpu_found:
                    scene.cycles.device = "GPU"
                    break
        except Exception:
            pass

        try:
            scene.view_settings.view_transform = "AgX"
            scene.view_settings.look = "Medium High Contrast"
        except Exception:
            pass
        scene.render.resolution_x = int(args.resolution[0])
        scene.render.resolution_y = int(args.resolution[1])
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"

        # Ensure scene has interior illumination if script created zero lights
        temp_lights: list[Any] = []
        if not any(obj.type == "LIGHT" for obj in bpy.data.objects):
            for idx, (lx, ly) in enumerate(((-2.0, -2.0), (2.0, -2.0), (-2.0, 2.0), (2.0, 2.0))):
                ldata = bpy.data.lights.new(f"_GateFillLight_{idx}", type="AREA")
                ldata.size = 1.6
                ldata.energy = 140.0
                lobj = bpy.data.objects.new(f"_GateFillLight_{idx}", ldata)
                lobj.location = (rcx + lx, rcy + ly, r_zmax - 0.15)
                scene.collection.objects.link(lobj)
                temp_lights.append(lobj)

        cam_data = bpy.data.cameras.new("_RoomGateVerifyCamera")
        cam_obj = bpy.data.objects.new("_RoomGateVerifyCamera", cam_data)
        scene.collection.objects.link(cam_obj)
        prev_cam = scene.camera
        scene.camera = cam_obj

        inset_x = min(0.55, (r_xmax - r_xmin) * 0.10)
        inset_y = min(0.55, (r_ymax - r_ymin) * 0.10)
        corner_z = r_zmax + 0.35

        views = [
            (
                "corner_ne",
                (r_xmax - inset_x, r_ymax - inset_y, corner_z),
                (rcx - 0.35, rcy - 0.35, 0.80),
                "PERSP",
                21.0,
                True,
                False,
            ),
            (
                "corner_nw",
                (r_xmin + inset_x, r_ymax - inset_y, corner_z),
                (rcx + 0.35, rcy - 0.35, 0.80),
                "PERSP",
                21.0,
                True,
                False,
            ),
            (
                "corner_se",
                (r_xmax - inset_x, r_ymin + inset_y, corner_z),
                (rcx - 0.35, rcy + 0.35, 0.80),
                "PERSP",
                21.0,
                True,
                False,
            ),
            (
                "corner_sw",
                (r_xmin + inset_x, r_ymin + inset_y, corner_z),
                (rcx + 0.35, rcy + 0.35, 0.80),
                "PERSP",
                21.0,
                True,
                False,
            ),
            (
                "entrance_eye_level",
                (rcx, r_ymin + 0.45, 1.55),
                (rcx, r_ymax - 1.0, 1.05),
                "PERSP",
                22.0,
                False,
                True,
            ),
            (
                "topdown_floorplan",
                (rcx, rcy, r_zmax + 4.5),
                (rcx, rcy, 0.0),
                "ORTHO",
                max(r_xmax - r_xmin, r_ymax - r_ymin) * 1.08,
                True,
                False,
            ),
        ]

        saved_vis = {obj.name: bool(getattr(obj, "visible_camera", True)) for obj in mesh_objects}
        try:
            for name, eye, target, cam_type, lens_or_scale, hide_ceil, hide_door in views:
                for obj in mesh_objects:
                    vis = saved_vis[obj.name]
                    if hide_ceil and obj in ceiling_occluders:
                        vis = False
                    if hide_door and obj in entrance_occluders:
                        vis = False
                    obj.visible_camera = vis

                cam_data.type = cam_type
                if cam_type == "ORTHO":
                    cam_data.ortho_scale = float(lens_or_scale)
                    cam_obj.location = eye
                    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
                else:
                    cam_data.lens = float(lens_or_scale)
                    cam_obj.location = eye
                    direction = mathutils.Vector(target) - mathutils.Vector(eye)
                    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

                bpy.context.view_layer.update()
                out_png = out_dir / f"{name}.png"
                scene.render.filepath = str(out_png)
                bpy.ops.render.render(write_still=True)
                if not out_png.is_file():
                    raise RuntimeError(f"failed to render {out_png}")
                rendered_views[name] = {
                    "path": str(out_png),
                    "sha256": _sha256(out_png),
                    "ceiling_hidden": hide_ceil,
                    "entrance_door_hidden": hide_door,
                }
        finally:
            for obj in mesh_objects:
                obj.visible_camera = saved_vis[obj.name]
            scene.camera = prev_cam
            bpy.data.objects.remove(cam_obj, do_unlink=True)
            bpy.data.cameras.remove(cam_data, do_unlink=True)
            for lobj in temp_lights:
                ldata = lobj.data
                bpy.data.objects.remove(lobj, do_unlink=True)
                bpy.data.lights.remove(ldata, do_unlink=True)

    renders_pass = args.skip_render or len(rendered_views) == 6
    overall_pass = (
        density_pass
        and props_pass
        and textures_pass
        and floor_flat_pass
        and clearance_pass
        and renders_pass
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "room_id": room_id,
        "source": {"kind": source_kind, "path": str(source_path), "sha256": _sha256(source_path)},
        "overall_status": "pass" if overall_pass else "fail",
        "gates": {
            "density_pass": density_pass,
            "props_pass": props_pass,
            "textures_pass": textures_pass,
            "floor_flat_pass": floor_flat_pass,
            "clearance_pass": clearance_pass,
            "renders_pass": renders_pass,
        },
        "thresholds": {
            "min_assemblies": args.min_assemblies,
            "min_total_meshes": args.min_total_meshes,
            "min_props": args.min_props,
            "floor_max_z_m": floor_max_z,
            "clearance_xy_m": [float(args.clearance_xy[0]), float(args.clearance_xy[1])],
            "clearance_center_xy_m": [cx, cy],
            "clearance_z_max_m": c_zmax,
        },
        "counts": {
            "total_mesh_objects": total_mesh_count,
            "multipart_assembly_count": assembly_count,
            "domain_prop_count": prop_count,
            "domain_prop_roots": len(prop_roots),
            "domain_prop_meshes": len(prop_meshes),
            "file_backed_textures": file_backed_count,
            "packed_textures": len(packed_textures),
            "missing_textures": len(missing_textures),
            "ceiling_occluders_detected": len(ceiling_occluders),
            "entrance_occluders_detected": len(entrance_occluders),
        },
        "room_envelope_m": {
            "x_range": [round(r_xmin, 4), round(r_xmax, 4)],
            "y_range": [round(r_ymin, 4), round(r_ymax, 4)],
            "z_max": round(r_zmax, 4),
        },
        "violations": {
            "packed_textures": packed_textures,
            "missing_textures": missing_textures,
            "raised_floor_strips": raised_floor_strips,
            "clearance_intrusions": clearance_intrusions,
        },
        "textures": texture_records,
        "rendered_views": rendered_views,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"room gate report ({report['overall_status']}): {report_path}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

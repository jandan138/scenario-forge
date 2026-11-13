#!/usr/bin/env python3
"""Export a Blender room scene as a portable Scenario Forge room-source-v2 delivery.

Invoke with Blender 4.4.3:
  blender --background --python skills/agentic-scene-factory/scripts/export_room_source_v2.py -- \\
    --run-dir <dir> --delivery-dir <out_dir> --background-asset-id <asset_id> \\
    --source-image <reference.png> --support-reviewer <reviewer_id>

This internalized Scenario Forge exporter has zero external repo dependencies:
it imports pure-Python support geometry math from
``scenario_forge.adapters.room_support_relations`` and emits native
``producer.repo = "scenario-forge"`` metadata in ``source_manifest.json``.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.adapters.room_support_relations import (  # noqa: E402
    Box3,
    OrientedSupport,
    apply_resting_correction,
    validate_support_sidecar,
)

SCHEMA_VERSION = "room-source-v2"
SUPPORT_SCHEMA_VERSION = "room-support-relations-v1"
ZONE_ROOT_NAME = "Zone__Center_Open_Floor"
DEFAULT_WORKSPACE_CLEARANCE_M = (3.8, 4.0)
EXPORTER_RELPATH = "skills/agentic-scene-factory/scripts/export_room_source_v2.py"
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _detect_repo_commit() -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        candidate = proc.stdout.strip().lower()
        if proc.returncode == 0 and COMMIT_RE.fullmatch(candidate):
            return candidate
    except OSError:
        pass
    return "0000000"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--source-script",
        type=Path,
        help=(
            "Explicit room builder Python script (defaults to searching "
            "RUN_DIR/{stage12_render/render_output.py,provenance/render_output.py,"
            "render_output.py,render_delivery_r3.py})."
        ),
    )
    parser.add_argument("--delivery-dir", type=Path, required=True)
    parser.add_argument("--background-asset-id", required=True)
    parser.add_argument("--source-image", type=Path, required=True)
    parser.add_argument(
        "--producer-commit",
        default=None,
        help="Git commit hash in scenario-forge (defaults to `git rev-parse HEAD`).",
    )
    parser.add_argument(
        "--code-as-room-commit",
        dest="legacy_commit_alias",
        default=None,
        help="Deprecated alias for --producer-commit.",
    )
    parser.add_argument(
        "--support-reviewer",
        required=True,
        help="Reviewer identity recorded after auditing inferred support relations.",
    )
    parser.add_argument(
        "--workspace-clearance-xy",
        nargs=2,
        type=float,
        metavar=("WIDTH_M", "DEPTH_M"),
        default=list(DEFAULT_WORKSPACE_CLEARANCE_M),
        help="Open-floor central workspace clearance (width_x, depth_y) in meters.",
    )
    return parser.parse_args(argv)


def _fail(message: str) -> None:
    raise RuntimeError(f"room source v2 export failed: {message}")


def _resolve_source_script(run_dir: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        resolved = explicit.resolve()
        if not resolved.is_file():
            _fail(f"missing source script: {resolved}")
        return resolved
    candidates = (
        run_dir / "stage12_render/render_output.py",
        run_dir / "provenance/render_output.py",
        run_dir / "render_output.py",
        run_dir / "render_delivery_r3.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    _fail(f"could not locate room builder script under {run_dir}")
    raise AssertionError("unreachable")


def _resolve_producer_commit(args: argparse.Namespace) -> str:
    commit = args.producer_commit or args.legacy_commit_alias or _detect_repo_commit()
    commit = commit.strip().lower()
    if COMMIT_RE.fullmatch(commit) is None:
        _fail(f"producer commit must be a 7-40 char lowercase hex git hash: {commit!r}")
    return commit


def main() -> None:
    args = _parse_args()

    import bpy  # type: ignore[import-not-found]
    import mathutils  # type: ignore[import-not-found]
    from pxr import Sdf, Tf, Usd, UsdGeom  # type: ignore[import-not-found]

    args.run_dir = args.run_dir.resolve()
    args.delivery_dir = args.delivery_dir.resolve()
    args.source_image = args.source_image.resolve()
    source_script = _resolve_source_script(args.run_dir, args.source_script)
    if not args.source_image.is_file():
        _fail(f"missing source image: {args.source_image}")
    if not args.support_reviewer.strip():
        _fail("--support-reviewer must be non-empty")
    clearance_xy = (
        float(args.workspace_clearance_xy[0]),
        float(args.workspace_clearance_xy[1]),
    )
    if clearance_xy[0] <= 0 or clearance_xy[1] <= 0:
        _fail("--workspace-clearance-xy values must be positive")
    producer_commit = _resolve_producer_commit(args)

    delivery = args.delivery_dir
    if delivery.exists():
        _fail(f"refusing to overwrite existing delivery directory: {delivery}")
    for relative in ("textures", "provenance", "evidence/blender"):
        (delivery / relative).mkdir(parents=True, exist_ok=True)

    packaged_script = delivery / "provenance/render_output.py"
    exporter_copy = delivery / "provenance/export_room_source_v2.py"
    shutil.copy2(source_script, packaged_script)
    shutil.copy2(Path(__file__).resolve(), exporter_copy)
    shutil.copy2(args.source_image, delivery / "evidence/blender/source_reference.png")

    def _copy_texture(image: Any, textures_dir: Path) -> str | None:
        if image.source != "FILE":
            return None
        source = Path(bpy.path.abspath(image.filepath)).resolve()
        if not source.is_file():
            if image.packed_file is not None:
                _fail(f"packed texture is unsupported: {image.name}")
            _fail(f"file-backed texture is missing: {image.filepath}")
        name = source.name
        target = textures_dir / name
        if target.exists() and _sha256(target) != _sha256(source):
            name = f"{_sha256(source)[:12]}_{name}"
            target = textures_dir / name
        if not target.exists():
            shutil.copy2(source, target)
        image.filepath = f"//textures/{name}"
        image.filepath_raw = f"//textures/{name}"
        return f"textures/{name}"

    def _asset_paths(stage: Any) -> list[str]:
        paths: set[str] = set()

        def visit(value: object) -> None:
            if isinstance(value, Sdf.AssetPath) and value.path:
                paths.add(value.path)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)

        for prim in stage.TraverseAll():
            for attribute in prim.GetAttributes():
                visit(attribute.Get())
        return sorted(paths)

    def _ensure_overview_camera(scene: Any) -> bool:
        if scene.camera is not None and scene.camera.type == "CAMERA":
            return False
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            for vertex in obj.bound_box:
                world_vertex = obj.matrix_world @ mathutils.Vector(vertex)
                min_x, max_x = min(min_x, world_vertex.x), max(max_x, world_vertex.x)
                min_y, max_y = min(min_y, world_vertex.y), max(max_y, world_vertex.y)
        if min_x == float("inf"):
            center_x = center_y = 0.0
            ortho_scale = 12.0
        else:
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0
            ortho_scale = max(max_x - min_x, max_y - min_y) * 1.2
        bpy.ops.object.camera_add(location=(center_x, center_y, 15.0))
        camera = bpy.context.active_object
        camera.name = "Delivery_Evidence_Camera"
        camera.rotation_euler = (0.0, 0.0, 0.0)
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = ortho_scale
        scene.camera = camera
        return True

    def _descendants(root: Any) -> list[Any]:
        result = [root]
        for child in root.children:
            result.extend(_descendants(child))
        return result

    def _remove_tree(root: Any) -> None:
        for obj in reversed(_descendants(root)):
            bpy.data.objects.remove(obj, do_unlink=True)

    def _world_box(root: Any) -> Box3 | None:
        points: list[Any] = []
        for obj in _descendants(root):
            if obj.type != "MESH":
                continue
            points.extend(
                obj.matrix_world @ mathutils.Vector(vertex)
                for vertex in obj.bound_box
            )
        if not points:
            return None
        return Box3(
            (min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)),
            (max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)),
        )

    def _is_small_root(obj: Any) -> bool:
        return obj.parent is None and (
            obj.name.startswith("MinorPlace_")
            or obj.name.startswith("Orphan_")
            or "__top__" in obj.name
        )

    def _overlap_area(a: Box3, b: Box3) -> float:
        width = max(0.0, min(a.maximum[0], b.maximum[0]) - max(a.minimum[0], b.minimum[0]))
        depth = max(0.0, min(a.maximum[1], b.maximum[1]) - max(a.minimum[1], b.minimum[1]))
        return width * depth

    def _horizontal_gap(a: Box3, b: Box3) -> float:
        dx = max(b.minimum[0] - a.maximum[0], a.minimum[0] - b.maximum[0], 0.0)
        dy = max(b.minimum[1] - a.maximum[1], a.minimum[1] - b.maximum[1], 0.0)
        return math.hypot(dx, dy)

    def _infer_support(
        item: Any,
        item_box: Box3,
        candidates: list[tuple[Any, Box3]],
    ) -> tuple[Any, Box3, str] | None:
        if "__top__" in item.name:
            declared_name = item.name.split("__top__", 1)[0]
            declared = bpy.data.objects.get(declared_name)
            declared_box = _world_box(declared) if declared is not None else None
            if declared is not None and declared_box is not None:
                return (
                    declared,
                    declared_box,
                    "stacked_on" if _is_small_root(declared) else "rests_on",
                )

        resting: list[tuple[float, float, float, Any, Box3]] = []
        item_area = max(
            1e-12,
            (item_box.maximum[0] - item_box.minimum[0])
            * (item_box.maximum[1] - item_box.minimum[1]),
        )
        for candidate, candidate_box in candidates:
            vertical_gap = item_box.minimum[2] - candidate_box.maximum[2]
            overlap_fraction = _overlap_area(item_box, candidate_box) / item_area
            horizontal_gap = _horizontal_gap(item_box, candidate_box)
            if -0.005 <= vertical_gap <= 0.12 and horizontal_gap <= 0.25:
                resting.append(
                    (
                        overlap_fraction,
                        -horizontal_gap,
                        -abs(vertical_gap),
                        candidate,
                        candidate_box,
                    )
                )
        if resting:
            _, _, _, candidate, candidate_box = max(
                resting, key=lambda value: (value[2], value[0], value[1])
            )
            return candidate, candidate_box, "rests_on"

        center = tuple(
            (low + high) / 2.0
            for low, high in zip(item_box.minimum, item_box.maximum)
        )
        containing: list[tuple[float, Any, Box3]] = []
        for candidate, candidate_box in candidates:
            if all(
                candidate_box.minimum[i] - 0.02
                <= center[i]
                <= candidate_box.maximum[i] + 0.02
                for i in range(3)
            ):
                volume = math.prod(
                    candidate_box.maximum[i] - candidate_box.minimum[i]
                    for i in range(3)
                )
                containing.append((volume, candidate, candidate_box))
        if containing:
            _, candidate, candidate_box = min(containing, key=lambda value: value[0])
            return candidate, candidate_box, "mounted_to"
        return None

    def _audit_and_correct_supports(reviewer: str) -> list[dict[str, object]]:
        bpy.context.view_layer.update()
        small_roots = sorted(
            (obj for obj in bpy.data.objects if _is_small_root(obj)),
            key=lambda obj: obj.name,
        )
        small_names = [obj.name for obj in small_roots]
        small_set = set(small_roots)
        candidates: list[tuple[Any, Box3]] = []
        for obj in bpy.data.objects:
            if (
                obj.parent is not None
                or obj in small_set
                or obj.type in {"CAMERA", "LIGHT"}
            ):
                continue
            box = _world_box(obj)
            if box is not None:
                candidates.append((obj, box))

        relations: list[dict[str, object]] = []
        for item_name in small_names:
            item = bpy.data.objects.get(item_name)
            if item is None:
                continue
            before = _world_box(item)
            if before is None:
                continue
            inferred = _infer_support(item, before, candidates)
            if inferred is None:
                relations.append(
                    {
                        "object_name": item_name,
                        "object_prim": f"/Room/{Tf.MakeValidIdentifier(item_name)}",
                        "support_prim": None,
                        "relation_kind": "rests_on",
                        "audit_status": "removed",
                        "before_bbox_m": [list(before.minimum), list(before.maximum)],
                        "after_bbox_m": None,
                        "translation_m": [0.0, 0.0, 0.0],
                        "removal_reason": "no_declared_support_candidate",
                    }
                )
                _remove_tree(item)
                continue
            support, support_box, relation_kind = inferred
            status = "unchanged"
            translation = (0.0, 0.0, 0.0)
            after = before
            removal_reason = None
            if relation_kind in {"rests_on", "stacked_on"}:
                result = apply_resting_correction(
                    before,
                    OrientedSupport(
                        center_xy=(
                            (support_box.minimum[0] + support_box.maximum[0]) / 2.0,
                            (support_box.minimum[1] + support_box.maximum[1]) / 2.0,
                        ),
                        size_xy=(
                            support_box.maximum[0] - support_box.minimum[0],
                            support_box.maximum[1] - support_box.minimum[1],
                        ),
                        yaw_rad=0.0,
                        top_z=support_box.maximum[2],
                    ),
                    margin_m=0.02,
                    vertical_tolerance_m=0.12,
                )
                status = result.status
                translation = result.translation
                after = result.after
                removal_reason = result.removal_reason
                if result.status == "removed":
                    _remove_tree(item)
                else:
                    item.location += mathutils.Vector(translation)
                    bpy.context.view_layer.update()
                    after = _world_box(item) or after
            relations.append(
                {
                    "object_name": item_name,
                    "object_prim": (
                        f"/Room/{Tf.MakeValidIdentifier(item_name)}"
                        if status != "removed"
                        else None
                    ),
                    "support_name": support.name,
                    "support_prim": f"/Room/{Tf.MakeValidIdentifier(support.name)}",
                    "relation_kind": relation_kind,
                    "audit_status": "removed" if status == "removed" else "pass",
                    "producer_action": status,
                    "before_bbox_m": [list(before.minimum), list(before.maximum)],
                    "after_bbox_m": (
                        None
                        if status == "removed"
                        else [list(after.minimum), list(after.maximum)]
                    ),
                    "support_bbox_m": [
                        list(support_box.minimum),
                        list(support_box.maximum),
                    ],
                    "translation_m": list(translation),
                    "removal_reason": removal_reason,
                    "reviewer": reviewer,
                }
            )
        return relations

    def _validate_exported_supports(
        stage: Any, relations: list[dict[str, object]]
    ) -> None:
        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]
        )
        for relation in relations:
            if relation["audit_status"] == "removed":
                continue
            object_prim = stage.GetPrimAtPath(str(relation["object_prim"]))
            support_prim = stage.GetPrimAtPath(str(relation["support_prim"]))
            if not object_prim.IsValid() or not support_prim.IsValid():
                _fail(
                    f"support relation prim missing after USD export: {relation['object_name']}"
                )
            if relation["relation_kind"] not in {"rests_on", "stacked_on"}:
                continue
            item_range = bbox_cache.ComputeWorldBound(object_prim).ComputeAlignedRange()
            support_range = bbox_cache.ComputeWorldBound(support_prim).ComputeAlignedRange()
            item_min, item_max = item_range.GetMin(), item_range.GetMax()
            support_min, support_max = support_range.GetMin(), support_range.GetMax()
            horizontal_pass = all(
                item_min[axis] >= support_min[axis] + 0.02 - 1e-5
                and item_max[axis] <= support_max[axis] - 0.02 + 1e-5
                for axis in (0, 1)
            )
            vertical_pass = abs(float(item_min[2] - support_max[2])) <= 0.005 + 1e-5
            if not horizontal_pass or not vertical_pass:
                _fail(f"exported support geometry failed for {relation['object_name']}")

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(source_script),
    }
    code = source_script.read_text(encoding="utf-8")
    exec(compile(code, str(source_script), "exec"), namespace, namespace)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene["delivery_schema_version"] = SCHEMA_VERSION
    scene["source_run_id"] = args.run_dir.name
    scene["background_asset_id"] = args.background_asset_id
    scene["producer_repo"] = "scenario-forge"
    scene["producer_commit"] = producer_commit
    if scene.rigidbody_world is not None:
        _fail("generated scene contains a rigid body world")
    rigid_objects = [
        obj.name for obj in bpy.data.objects if obj.rigid_body is not None
    ]
    if rigid_objects:
        _fail("generated scene contains rigid bodies: " + ", ".join(rigid_objects))

    support_relations = _audit_and_correct_supports(args.support_reviewer)

    _ensure_overview_camera(scene)
    final_render = delivery / "evidence/blender/final_room_render.png"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(final_render)
    render_result = bpy.ops.render.render(write_still=True)
    if "FINISHED" not in render_result or not final_render.is_file():
        _fail(f"Blender evidence render failed: {render_result}")

    zone = bpy.data.objects.get(ZONE_ROOT_NAME)
    if zone is None:
        zone = bpy.data.objects.new(ZONE_ROOT_NAME, None)
        scene.collection.objects.link(zone)
    zone.location = (0.0, 0.0, 0.0)
    zone["semantic_zone"] = "Center Open Floor"
    zone["workspace_mode"] = "open_floor"
    zone["clearance_width_m"] = clearance_xy[0]
    zone["clearance_depth_m"] = clearance_xy[1]

    textures_dir = delivery / "textures"
    texture_paths = sorted(
        {
            path
            for image in bpy.data.images
            if (path := _copy_texture(image, textures_dir)) is not None
        }
    )
    bpy.context.preferences.filepaths.save_version = 0
    room_blend = delivery / "room.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(room_blend), check_existing=False)

    room_usdc = delivery / "room_source.usdc"
    export_parameters: dict[str, object] = {
        "filepath": str(room_usdc),
        "selected_objects_only": False,
        "visible_objects_only": False,
        "collection": "",
        "export_animation": False,
        "export_meshes": True,
        "export_materials": True,
        "export_lights": True,
        "export_cameras": False,
        "export_textures": False,
        "relative_paths": True,
        "convert_orientation": True,
        "export_global_up_selection": "Z",
        "export_global_forward_selection": "NEGATIVE_Y",
        "convert_scene_units": "METERS",
        "meters_per_unit": 1.0,
        "xform_op_mode": "TRS",
        "merge_parent_xform": False,
        "root_prim_path": "/Room",
        "export_custom_properties": True,
    }
    result = bpy.ops.wm.usd_export(**export_parameters)
    if "FINISHED" not in result or not room_usdc.is_file():
        _fail(f"USD export failed: {result}")

    stage = Usd.Stage.Open(str(room_usdc))
    if stage is None or not stage.GetPrimAtPath("/Room").IsValid():
        _fail("room_source.usdc cannot be reopened at /Room")
    if str(UsdGeom.GetStageUpAxis(stage)) != "Z":
        _fail("room_source.usdc is not Z-up")
    if abs(float(UsdGeom.GetStageMetersPerUnit(stage)) - 1.0) > 1e-9:
        _fail("room_source.usdc is not metric")
    _validate_exported_supports(stage, support_relations)
    for prim in stage.TraverseAll():
        if prim.GetTypeName() == "DomeLight":
            attribute = prim.GetAttribute("inputs:texture:format")
            if attribute:
                attribute.Set("latlong")
    if not stage.GetRootLayer().Save():
        _fail("room_source.usdc normalization did not save")
    usd_asset_paths = _asset_paths(stage)
    normalized = [path.removeprefix("./") for path in usd_asset_paths]
    invalid = [
        path
        for path in normalized
        if path.startswith("/") or path.startswith("../") or "/cpfs/" in path
    ]
    if invalid:
        _fail("USD contains non-package-relative dependencies: " + ", ".join(invalid))
    missing = [path for path in normalized if not (delivery / path).is_file()]
    if missing:
        _fail("USD references missing package files: " + ", ".join(missing))

    sidecar_path = delivery / "support_relations.json"
    support_sidecar = {
        "schema_version": SUPPORT_SCHEMA_VERSION,
        "source_usd": {"path": "room_source.usdc", "sha256": _sha256(room_usdc)},
        "margin_m": 0.02,
        "vertical_tolerance_m": 0.005,
        "inventory_policy": "all non-floor small roots named MinorPlace_*, Orphan_*, or *__top__*",
        "relations": support_relations,
        "review": {
            "status": "pass",
            "reviewer": args.support_reviewer,
            "method": "automatic geometry audit followed by engineering review",
        },
    }
    sidecar_path.write_text(
        json.dumps(support_sidecar, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validate_support_sidecar(sidecar_path, room_usdc)

    declared_texture_paths = sorted(
        str(path.relative_to(delivery).as_posix())
        for path in textures_dir.rglob("*")
        if path.is_file()
    )

    manifest_export_parameters = dict(export_parameters)
    manifest_export_parameters["filepath"] = "room_source.usdc"

    source_reference = delivery / "evidence/blender/source_reference.png"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "delivery_revision": "r2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_dir.name,
        "background_asset_id": args.background_asset_id,
        "producer": {
            "repo": "scenario-forge",
            "commit": producer_commit,
            "exporter": EXPORTER_RELPATH,
        },
        "blender": {
            "version": bpy.app.version_string,
            "version_tuple": list(bpy.app.version),
            "build_hash": str(bpy.app.build_hash),
        },
        "units": {
            "system": "METRIC",
            "scale_length": 1.0,
            "meters_per_unit": 1.0,
        },
        "assets": {
            "room_blend": {"path": "room.blend", "sha256": _sha256(room_blend)},
            "room_source_usdc": {
                "path": "room_source.usdc",
                "sha256": _sha256(room_usdc),
            },
            "support_relations": {
                "path": "support_relations.json",
                "sha256": _sha256(sidecar_path),
            },
            "source_image": {
                "path": "evidence/blender/source_reference.png",
                "sha256": _sha256(source_reference),
            },
            "blender_source_evidence": [
                {
                    "path": "evidence/blender/final_room_render.png",
                    "sha256": _sha256(final_render),
                }
            ],
            "provenance_source_script": {
                "path": "provenance/render_output.py",
                "sha256": _sha256(packaged_script),
            },
            "provenance_build_script": {
                "path": "provenance/export_room_source_v2.py",
                "sha256": _sha256(exporter_copy),
            },
            "textures": [
                {"path": path, "sha256": _sha256(delivery / path)}
                for path in declared_texture_paths
            ],
        },
        "blend_texture_paths": [f"//{path}" for path in texture_paths],
        "usd_export_parameters": manifest_export_parameters,
        "usd_asset_paths": usd_asset_paths,
        "zones": {
            "Center Open Floor": {
                "zone_root": ZONE_ROOT_NAME,
                "workspace_mode": "open_floor",
                "anchor_xyz": [0.0, 0.0, 0.772761],
                "clearance_footprint_m": [clearance_xy[0], clearance_xy[1]],
                "members": [],
            }
        },
        "excluded_content": [
            "eBench robots",
            "task objects",
            "rigid bodies, collision objects, and physics semantics",
            "delivery-added cameras",
        ],
        "support_audit": {
            "schema_version": SUPPORT_SCHEMA_VERSION,
            "overall_status": "pass",
            "relation_count": len(support_relations),
            "removed_decoration_count": sum(
                relation["audit_status"] == "removed"
                for relation in support_relations
            ),
        },
    }
    (delivery / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"room source v2 delivery complete: {delivery}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compile the scientific-workbench centrifuge and tube-rack task packages."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from copy import deepcopy
import math
from pathlib import Path
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.ebench.genmanip import (
    export_genmanip_collected_package,
)
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import (
    resolve_scenario_source_bindings,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CENTRIFUGE_SPEC = (
    REPO_ROOT
    / "examples/scientific_workbench/centrifuge_load_start/scenario.yaml"
)
RACK_INSERT_SPEC = (
    REPO_ROOT
    / "examples/scientific_workbench/bimanual_rack_insert/scenario.yaml"
)
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
TASK_SPECS = {
    "7": CENTRIFUGE_SPEC,
    "11": RACK_INSERT_SPEC,
}
EBENCH_TABLETOP_Z_M = 0.7727606155
TABLETOP_CLEARANCE_M = 0.01
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _object_by_id(spec: dict[str, Any], object_id: str) -> dict[str, Any]:
    objects = spec.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scenario objects must be a list")
    for raw_object in objects:
        item = _mapping(raw_object, "scenario object")
        if item.get("id") == object_id:
            return item
    raise ValueError(f"scenario object {object_id!r} is missing")


def _source_contract(
    sources: Mapping[str, LocalUSDAssetSource],
    asset_id: str,
    contract_name: str,
) -> dict[str, Any]:
    source = sources.get(asset_id)
    if source is None or source.upstream_package is None:
        raise ValueError(
            f"asset {asset_id!r} requires a ConvertAsset upstream package"
        )
    return _mapping(
        source.upstream_package.metadata.get(contract_name),
        f"asset {asset_id}.{contract_name}",
    )


def _place_task_object_on_tabletop(
    task_object: dict[str, Any],
    sources: Mapping[str, LocalUSDAssetSource],
) -> None:
    asset_id = str(task_object["asset_id"])
    geometry = _source_contract(
        sources,
        asset_id,
        "task_interactive_geometry",
    )
    support_matrix = geometry.get("support_frame_local_matrix")
    if (
        geometry.get("support_frame") != "support"
        or not isinstance(support_matrix, list)
        or len(support_matrix) != 4
        or any(not isinstance(row, list) or len(row) != 4 for row in support_matrix)
        or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for row in support_matrix
            for value in row
        )
    ):
        raise ValueError(
            f"asset {asset_id} requires a finite 4x4 support-frame matrix"
        )
    support_source_sha256 = geometry.get("support_frame_source_sha256")
    if (
        not isinstance(support_source_sha256, str)
        or _SHA256_HEX.fullmatch(support_source_sha256) is None
    ):
        raise ValueError(
            f"asset {asset_id} support frame must be hash-bound"
        )
    pose = _mapping(task_object.get("pose"), f"task object {task_object['id']}.pose")
    scale = pose.get("scale_xyz", [1.0, 1.0, 1.0])
    if scale != [1.0, 1.0, 1.0]:
        raise ValueError(
            f"task object {task_object['id']} must use identity task-level scale"
        )
    xyz = pose.get("xyz")
    if (
        not isinstance(xyz, list)
        or len(xyz) != 3
        or not all(isinstance(value, (int, float)) for value in xyz)
    ):
        raise ValueError(f"task object {task_object['id']}.pose.xyz must be numeric")
    quaternion = pose.get("wxyz")
    if (
        not isinstance(quaternion, list)
        or len(quaternion) != 4
        or not all(isinstance(value, (int, float)) for value in quaternion)
    ):
        raise ValueError(f"task object {task_object['id']}.pose.wxyz must be numeric")
    quaternion_values = [float(value) for value in quaternion]
    norm = math.sqrt(sum(value * value for value in quaternion_values))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"task object {task_object['id']}.pose.wxyz must be unit")
    mounting = geometry.get("mounting")
    if mounting is not None:
        mount_translation, mount_rotation = _fixed_base_mount_pose(
            mounting,
            asset_id=asset_id,
        )
        if (
            not math.isclose(quaternion_values[1], 0.0, abs_tol=1e-6)
            or not math.isclose(quaternion_values[2], 0.0, abs_tol=1e-6)
        ):
            raise ValueError(
                f"task object {task_object['id']}.pose.wxyz must be a Z yaw "
                "when applying a producer-qualified mount"
            )
        world_mount_offset = _rotate_wxyz(
            mount_translation,
            quaternion_values,
        )
        pose["xyz"] = [
            float(xyz[0]) + world_mount_offset[0],
            float(xyz[1]) + world_mount_offset[1],
            EBENCH_TABLETOP_Z_M + world_mount_offset[2],
        ]
        pose["wxyz"] = _multiply_wxyz(
            quaternion_values,
            mount_rotation,
        )
        return
    support_local = [
        float(support_matrix[3][0]),
        float(support_matrix[3][1]),
        float(support_matrix[3][2]),
    ]
    support_world_offset = _rotate_wxyz(support_local, quaternion_values)
    pose["xyz"] = [
        float(xyz[0]),
        float(xyz[1]),
        EBENCH_TABLETOP_Z_M
        + TABLETOP_CLEARANCE_M
        - support_world_offset[2],
    ]


def _fixed_base_mount_pose(
    raw_mounting: object,
    *,
    asset_id: str,
) -> tuple[list[float], list[float]]:
    mounting = _mapping(raw_mounting, f"asset {asset_id}.mounting")
    if (
        mounting.get("schema_version") != "aan.articulated_mounting.v1"
        or mounting.get("status") != "pass"
        or mounting.get("motion_mode") != "fixed_base"
    ):
        raise ValueError(
            f"asset {asset_id} requires a passed fixed-base mounting contract"
        )
    for field_name in (
        "source_sha256",
        "profile_sha256",
        "runtime_report_sha256",
    ):
        value = mounting.get(field_name)
        if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
            raise ValueError(
                f"asset {asset_id} mounting {field_name} must be hash-bound"
            )
    semantics = _mapping(
        mounting.get("coordinate_semantics"),
        f"asset {asset_id}.mounting.coordinate_semantics",
    )
    if semantics != {
        "stage_up_axis": "Z",
        "linear_units": "meter",
        "quaternion_order": "wxyz",
        "support_frame": "runtime_articulation_root_pose_local",
        "mount_pose": (
            "support_plane_to_runtime_articulation_root_pose_world_axes_"
            "at_yaw_zero"
        ),
        "qualified_extents": (
            "world_axis_aligned_at_mount_pose_after_joint_reset"
        ),
    }:
        raise ValueError(
            f"asset {asset_id} mounting coordinate semantics are unsupported"
        )
    pose = _mapping(
        mounting.get("support_plane_to_root_mount_pose"),
        f"asset {asset_id}.mounting.support_plane_to_root_mount_pose",
    )
    translation = pose.get("translation_m")
    rotation = pose.get("rotation_wxyz")
    if (
        not isinstance(translation, list)
        or len(translation) != 3
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in translation
        )
        or not isinstance(rotation, list)
        or len(rotation) != 4
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in rotation
        )
    ):
        raise ValueError(
            f"asset {asset_id} mounting pose must contain finite translation "
            "and rotation"
        )
    rotation_values = [float(value) for value in rotation]
    if not math.isclose(
        sum(value * value for value in rotation_values),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ValueError(f"asset {asset_id} mounting rotation must be unit")
    return [float(value) for value in translation], rotation_values


def _require_task_qualification(
    sources: Mapping[str, LocalUSDAssetSource],
    asset_id: str,
    qualification_id: str,
) -> None:
    source = sources.get(asset_id)
    if source is None or source.upstream_package is None:
        raise ValueError(
            f"asset {asset_id!r} requires a ConvertAsset upstream package"
        )
    value = source.upstream_package.metadata.get("task_qualifications")
    if not isinstance(value, list):
        raise ValueError(
            f"asset {asset_id} requires task qualification {qualification_id}"
        )
    matches = [
        item
        for item in value
        if isinstance(item, Mapping)
        and item.get("qualification_id") == qualification_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"asset {asset_id} requires exactly one task qualification "
            f"{qualification_id}"
        )
    qualification = matches[0]
    report_path = qualification.get("report_path")
    report_sha256 = qualification.get("report_sha256")
    normalized_report_path = (
        PurePosixPath(report_path)
        if isinstance(report_path, str)
        else None
    )
    if (
        qualification.get("status") != "pass"
        or not isinstance(report_path, str)
        or not report_path
        or normalized_report_path is None
        or normalized_report_path.is_absolute()
        or ".." in normalized_report_path.parts
        or not isinstance(report_sha256, str)
        or _SHA256_HEX.fullmatch(report_sha256) is None
    ):
        raise ValueError(
            f"asset {asset_id} task qualification {qualification_id} "
            "must be a hash-bound pass"
        )


def _frame_pose(
    raw_frame: object,
    *,
    translation_field: str,
    rotation_field: str,
    label: str,
) -> dict[str, list[float]]:
    frame = _mapping(raw_frame, label)
    translation = frame.get(translation_field)
    rotation = frame.get(rotation_field)
    if (
        not isinstance(translation, list)
        or len(translation) != 3
        or not all(isinstance(value, (int, float)) for value in translation)
        or not isinstance(rotation, list)
        or len(rotation) != 4
        or not all(isinstance(value, (int, float)) for value in rotation)
    ):
        raise ValueError(f"{label} must contain a numeric translation and rotation")
    return {
        "xyz": [float(value) for value in translation],
        "wxyz": [float(value) for value in rotation],
    }


def _rotate_wxyz(vector: list[float], quaternion: list[float]) -> list[float]:
    w, x, y, z = quaternion
    vx, vy, vz = vector
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return [
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    ]


def _multiply_wxyz(left: list[float], right: list[float]) -> list[float]:
    lw, lx, ly, lz = left
    rw, rx, ry, rz = right
    result = [
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    ]
    norm = math.sqrt(sum(value * value for value in result))
    return [value / norm for value in result]


def _set_relative_target_range(
    spec: dict[str, Any],
    *,
    predicate_id: str,
    target_object: dict[str, Any],
    target_local_xyz: list[float],
    tolerance_xyz: tuple[float, float, float],
) -> None:
    pose = _mapping(target_object.get("pose"), "target object pose")
    quaternion = pose.get("wxyz")
    if (
        not isinstance(quaternion, list)
        or len(quaternion) != 4
        or not all(isinstance(value, (int, float)) for value in quaternion)
    ):
        raise ValueError("target object pose.wxyz must contain four numbers")
    world_offset = _rotate_wxyz(
        target_local_xyz,
        [float(value) for value in quaternion],
    )
    success = _mapping(spec.get("success"), "scenario success")
    predicates = success.get("predicates")
    if not isinstance(predicates, list):
        raise ValueError("scenario success.predicates must be a list")
    for raw_predicate in predicates:
        predicate = _mapping(raw_predicate, "success predicate")
        if predicate.get("id") != predicate_id:
            continue
        parameters = _mapping(predicate.get("parameters"), f"{predicate_id}.parameters")
        parameters["xyz_range"] = {
            axis: [
                round(center - tolerance, 9),
                round(center + tolerance, 9),
            ]
            for axis, center, tolerance in zip(
                ("x", "y", "z"),
                world_offset,
                tolerance_xyz,
                strict=True,
            )
        }
        return
    raise ValueError(f"success predicate {predicate_id!r} is missing")


def _materialize_authoritative_task_geometry(
    task_id: str,
    raw_spec: dict[str, Any],
    sources: Mapping[str, LocalUSDAssetSource],
) -> dict[str, Any]:
    """Replace readable template geometry with producer-qualified named frames."""

    spec = deepcopy(raw_spec)
    if task_id == "7":
        centrifuge = _object_by_id(spec, "centrifuge")
        test_tube = _object_by_id(spec, "test_tube")
        _place_task_object_on_tabletop(centrifuge, sources)
        _place_task_object_on_tabletop(test_tube, sources)
        asset_id = str(centrifuge["asset_id"])
        contract = _source_contract(
            sources,
            asset_id,
            "articulation_contract",
        )
        root_prim = contract.get("articulation_root_prim")
        frames = _mapping(contract.get("named_frames"), f"asset {asset_id}.named_frames")
        frame_id = "tube_socket_0_inserted_bottom_parked_root"
        frame = _mapping(frames.get(frame_id), f"asset {asset_id}.{frame_id}")
        if frame.get("parent_prim") != root_prim:
            raise ValueError(
                f"asset {asset_id}.{frame_id} must be root-local at the parked rotor state"
            )
        pose = _frame_pose(
            frame,
            translation_field="translation_parent_local_m",
            rotation_field="rotation_parent_local_wxyz",
            label=f"asset {asset_id}.{frame_id}",
        )
        centrifuge["named_frames"] = {frame_id: pose}
        _set_relative_target_range(
            spec,
            predicate_id="tube_inserted_in_rotor_socket",
            target_object=centrifuge,
            target_local_xyz=pose["xyz"],
            tolerance_xyz=(0.005, 0.005, 0.01),
        )
        return spec

    rack = _object_by_id(spec, "tube_rack")
    test_tube = _object_by_id(spec, "test_tube")
    asset_id = str(rack["asset_id"])
    _require_task_qualification(sources, asset_id, "tube_insertion")
    _place_task_object_on_tabletop(rack, sources)
    _place_task_object_on_tabletop(test_tube, sources)
    contract = _source_contract(sources, asset_id, "interaction_contract")
    frames = _mapping(contract.get("named_frames"), f"asset {asset_id}.named_frames")
    frame_ids = (
        "rack_grasp",
        "socket_0_aperture",
        "socket_0_inserted_bottom",
    )
    materialized = {
        frame_id: _frame_pose(
            frames.get(frame_id),
            translation_field="translation_body_local_usd",
            rotation_field="rotation_body_local_wxyz",
            label=f"asset {asset_id}.{frame_id}",
        )
        for frame_id in frame_ids
    }
    rack["named_frames"] = materialized
    _set_relative_target_range(
        spec,
        predicate_id="tube_inserted_in_target_socket",
        target_object=rack,
        target_local_xyz=materialized["socket_0_inserted_bottom"]["xyz"],
        tolerance_xyz=(0.005, 0.005, 0.005),
    )
    return spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile task 7 (centrifuge load/start), task 11 "
            "(bimanual rack insert), or both."
        )
    )
    parser.add_argument(
        "--bindings",
        type=Path,
        required=True,
        help="Scenario source bindings for the admitted background and task assets.",
    )
    parser.add_argument(
        "--task",
        choices=("7", "11", "all"),
        default="all",
        help="Task package to generate; defaults to both.",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Compile/export without starting the Isaac Sim initial-scene preview.",
    )
    parser.add_argument(
        "--isaac-python",
        type=Path,
        help="Isaac/GenManip Python executable; required without --static-only.",
    )
    parser.add_argument(
        "--genmanip-root",
        type=Path,
        help="GenManip checkout; required without --static-only.",
    )
    parser.add_argument("--renderer-script", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.static_only:
        if args.isaac_python is None:
            raise SystemExit("--isaac-python is required unless --static-only is used")
        if args.genmanip_root is None:
            raise SystemExit("--genmanip-root is required unless --static-only is used")

    sources = resolve_scenario_source_bindings(args.bindings)
    selected = tuple(TASK_SPECS) if args.task == "all" else (args.task,)
    results: list[tuple[str, Path, Path]] = []
    for task_id in selected:
        spec_path = TASK_SPECS[task_id]
        raw_spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        if not isinstance(raw_spec, dict):
            raise ValueError(f"Scenario spec must be a mapping: {spec_path}")
        materialized_spec = _materialize_authoritative_task_geometry(
            task_id,
            raw_spec,
            sources,
        )
        spec = ScenarioSpec.from_mapping(materialized_spec)
        package_root = args.out / spec.scenario_id
        package = compile_scenario_package(spec, sources, package_root)
        export = export_genmanip_collected_package(
            package.package_root,
            legacy_v01_transport=True,
        )
        if not args.static_only:
            run_genmanip_initial_preview(
                export.output_dir,
                args.isaac_python,
                args.renderer_script,
                args.genmanip_root,
                timeout_seconds=args.preview_timeout,
            )
        results.append((spec.scenario_id, package.package_root, export.output_dir))

    for scenario_id, package_root, export_root in results:
        print(f"{scenario_id}:")
        print(f"  Portable package: {package_root}")
        print(f"  GenManip collected package: {export_root}")
        print(
            "  Initial-scene preview: "
            + ("skipped (--static-only)" if args.static_only else "validated")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

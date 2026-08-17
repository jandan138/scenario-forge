from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isfinite
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

import yaml

from scenario_forge.generation.layout.constraints import (
    TabletopPlacementConstraints,
    load_layout_constraints,
)
from scenario_forge.generation.layout.tabletop_placement import (
    TabletopBounds,
    TabletopPlacementReport,
    evaluate_tabletop_placement,
)


OFFICIAL_APPLE_XY = (-0.35, -0.22)
OFFICIAL_BOWL_XY = (-0.35, 0.24)
OFFICIAL_RELATIVE_SCALE = 0.8
OFFICIAL_OBJECT_WXYZ = (0.5, 0.5, 0.5, 0.5)

# GenManip's object placement quaternion maps asset X->world Y, asset Y->world Z,
# and asset Z->world X. This keeps the Scenario Forge canary aligned with the
# official task's tabletop placement convention without importing GenManip.
OFFICIAL_OBJECT_TO_WORLD_ROTATION = (
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
)
OFFICIAL_ADDITIONAL_HEIGHT_M = 0.01
USD_MESH_WITH_POINTS_RE = re.compile(
    r'def\s+Mesh\s+"(?P<name>[^"]+)".*?point3f\[\]\s+points\s*=\s*\[(?P<points>.*?)\]',
    re.DOTALL,
)
USD_POINT_RE = re.compile(
    r"\(\s*(?P<x>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*,"
    r"\s*(?P<y>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*,"
    r"\s*(?P<z>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*\)"
)


@dataclass(frozen=True)
class OfficialTabletopPlacement:
    apple_xyz: tuple[float, float, float]
    bowl_xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]
    scale_xyz: tuple[float, float, float]
    evidence: dict[str, object]


class TabletopPlacementValidationError(ValueError):
    """Raised after a science-workbench tabletop-policy evidence write."""

    def __init__(self, message: str, evidence_path: Path):
        super().__init__(message)
        self.evidence_path = evidence_path


@dataclass(frozen=True)
class ScientificWorkbenchTabletopPlacementResult:
    evidence_path: Path
    overall_status: str
    applicable_object_ids: tuple[str, ...]


@dataclass(frozen=True)
class _PortableUsdPrim:
    name: str
    type_name: str

    def GetName(self) -> str:
        return self.name

    def GetPath(self) -> str:
        return f"/{self.name}"

    def IsA(self, schema: object) -> bool:
        return self.type_name == "Mesh" and getattr(schema, "__name__", "") == "Mesh"


def derive_official_tabletop_placement(
    *,
    scene_path: str | Path,
    apple_path: str | Path,
    bowl_path: str | Path,
) -> OfficialTabletopPlacement:
    table_min, table_max = _combined_usd_bbox(
        scene_path,
        include_prim=lambda prim: (
            "obj_table" in str(prim.GetPath()).lower() or prim.GetName().lower() == "table"
        ),
    )
    apple_min, apple_max = _combined_usd_bbox(
        apple_path,
        include_prim=lambda prim: _is_mesh_prim(prim),
    )
    bowl_min, bowl_max = _combined_usd_bbox(
        bowl_path,
        include_prim=lambda prim: _is_mesh_prim(prim),
    )

    table_top_z = table_max[2]
    apple_origin_above_bottom = _origin_above_bottom_from_bbox(apple_min, apple_max)
    bowl_origin_above_bottom = _origin_above_bottom_from_bbox(bowl_min, bowl_max)
    apple_xyz = _round_xyz(
        (
            OFFICIAL_APPLE_XY[0],
            OFFICIAL_APPLE_XY[1],
            table_top_z + apple_origin_above_bottom + OFFICIAL_ADDITIONAL_HEIGHT_M,
        )
    )
    bowl_xyz = _round_xyz(
        (
            OFFICIAL_BOWL_XY[0],
            OFFICIAL_BOWL_XY[1],
            table_top_z + bowl_origin_above_bottom + OFFICIAL_ADDITIONAL_HEIGHT_M,
        )
    )
    scale_xyz = (
        OFFICIAL_RELATIVE_SCALE,
        OFFICIAL_RELATIVE_SCALE,
        OFFICIAL_RELATIVE_SCALE,
    )
    evidence = {
        "placement_source_kind": "official_tabletop_bbox_derived",
        "source_policy": "genmanip_random_custom_tableset_bbox_convention",
        "object_orientation_wxyz": list(OFFICIAL_OBJECT_WXYZ),
        "relative_scale": OFFICIAL_RELATIVE_SCALE,
        "additional_height_m": OFFICIAL_ADDITIONAL_HEIGHT_M,
        "table_top_z": _round_float(table_top_z),
        "apple_origin_above_bottom_m": _round_float(apple_origin_above_bottom),
        "bowl_origin_above_bottom_m": _round_float(bowl_origin_above_bottom),
        "apple_center": list(apple_xyz),
        "bowl_center": list(bowl_xyz),
        "table_bbox_min": _round_list(table_min),
        "table_bbox_max": _round_list(table_max),
        "apple_bbox_min": _round_list(apple_min),
        "apple_bbox_max": _round_list(apple_max),
        "bowl_bbox_min": _round_list(bowl_min),
        "bowl_bbox_max": _round_list(bowl_max),
    }
    return OfficialTabletopPlacement(
        apple_xyz=apple_xyz,
        bowl_xyz=bowl_xyz,
        wxyz=OFFICIAL_OBJECT_WXYZ,
        scale_xyz=scale_xyz,
        evidence=evidence,
    )


def validate_scientific_workbench_tabletop_placement(
    package_root: str | Path,
    *,
    domain_pack_dir: str | Path | None = None,
) -> ScientificWorkbenchTabletopPlacementResult:
    """Write and enforce the robot-facing tabletop policy for one package.

    This is intentionally an eBench adapter check: it opens the composed USD
    with lazy OpenUSD imports and leaves the portable package compiler free of
    simulator/runtime dependencies.
    """

    root = Path(package_root)
    evidence_path = root / "evidence" / "tabletop_placement_policy.yaml"
    scenario = _load_yaml_mapping(root / "scenario.yaml", "scenario spec")
    if scenario.get("domain") != "scientific_workbench":
        raise ValueError("tabletop placement policy applies only to scientific_workbench")
    constraints = load_layout_constraints(domain_pack_dir)
    policy = constraints.tabletop_placement
    if policy is None:
        raise ValueError("scientific_workbench domain pack does not declare tabletop_placement")
    table, task_objects = _table_and_task_objects(scenario)
    table_support_path = policy.support_surface_prim_path
    if table.get("source_prim_path") != "/World/table":
        raise ValueError(
            "scientific_workbench tabletop policy currently requires table source prim "
            "'/World/table'"
        )
    robot_xy = _robot_spawn_xy(scenario)
    stage, cache = _open_stage_with_bbox_cache(root / "scene" / "main.usda")
    table_bounds_3d = _world_bounds(stage, cache, table_support_path)
    table_bounds = TabletopBounds(
        table_bounds_3d[0][0],
        table_bounds_3d[1][0],
        table_bounds_3d[0][1],
        table_bounds_3d[1][1],
    )

    applicable_bounds: dict[str, TabletopBounds] = {}
    visual_bounds_xy: dict[str, TabletopBounds] = {}
    footprint_sources: dict[str, str] = {}
    margin_overrides: dict[str, float] = {}
    exceptions: dict[str, str] = {}
    not_applicable: list[dict[str, object]] = []
    for item in task_objects:
        object_id = _required_string(item, "id", "scenario object")
        prim_path = _required_string(item, "source_prim_path", f"object {object_id}")
        object_bounds_3d = _world_bounds(stage, cache, prim_path)
        support_gap = object_bounds_3d[0][2] - table_bounds_3d[1][2]
        if abs(support_gap) > policy.support_height_tolerance_m:
            not_applicable.append(
                {
                    "object_id": object_id,
                    "status": "not_applicable",
                    "reason": "not_initially_supported_by_declared_tabletop",
                    "support_gap_m": round(support_gap, 9),
                    "world_bounds_m": _bounds_mapping(object_bounds_3d),
                }
            )
            continue
        visual_bounds = TabletopBounds(
            object_bounds_3d[0][0],
            object_bounds_3d[1][0],
            object_bounds_3d[0][1],
            object_bounds_3d[1][1],
        )
        applicable_bounds[object_id], footprint_sources[object_id] = _placement_footprint(
            item, visual_bounds
        )
        visual_bounds_xy[object_id] = visual_bounds
        margin_override = _edge_margin_override(item)
        if margin_override is not None:
            margin_overrides[object_id] = margin_override
        reason = _robot_side_exception(item, policy)
        if reason is not None:
            exceptions[object_id] = reason

    if applicable_bounds:
        report = evaluate_tabletop_placement(
            table_bounds=table_bounds,
            robot_xy=robot_xy,
            object_bounds=applicable_bounds,
            policy=policy.policy,
            robot_side_exceptions=exceptions,
            min_edge_clearance_overrides_m=margin_overrides,
        )
        evidence = _evidence_mapping(
            report,
            policy,
            table_bounds_3d,
            not_applicable,
            visual_bounds_xy,
            footprint_sources,
        )
    else:
        evidence = {
            "schema_version": "scenario-forge-tabletop-placement-policy/v0.1",
            "overall_status": "pass",
            "policy": _policy_mapping(policy),
            "table_support_world_bounds_m": _bounds_mapping(table_bounds_3d),
            "robot_base_xy_m": [round(value, 9) for value in robot_xy],
            "objects": not_applicable,
            "claim_boundary": (
                "No task object was initially supported by the declared tabletop; "
                "the robot-side tabletop rule is not applicable to this package."
            ),
        }

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        yaml.safe_dump(evidence, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    overall_status = str(evidence["overall_status"])
    result = ScientificWorkbenchTabletopPlacementResult(
        evidence_path=evidence_path,
        overall_status=overall_status,
        applicable_object_ids=tuple(applicable_bounds),
    )
    if overall_status != "pass":
        raise TabletopPlacementValidationError(
            "scientific workbench tabletop placement is blocked: " + _blocked_summary(evidence),
            evidence_path,
        )
    return result


def _open_stage_with_bbox_cache(scene_path: Path) -> tuple[object, object]:
    try:
        from pxr import Usd, UsdGeom
    except ModuleNotFoundError as exc:
        raise RuntimeError("OpenUSD is required for eBench tabletop placement validation") from exc
    stage = Usd.Stage.Open(str(scene_path))
    if stage is None:
        raise RuntimeError(f"unable to open composed scene for tabletop policy: {scene_path}")
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        useExtentsHint=True,
    )
    return stage, cache


def _world_bounds(
    stage: object,
    cache: object,
    prim_path: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        raise ValueError(f"tabletop policy prim is missing from composed scene: {prim_path}")
    aligned_range = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    lower = _range_tuple(aligned_range.GetMin())
    upper = _range_tuple(aligned_range.GetMax())
    if not all(isfinite(value) for value in (*lower, *upper)) or any(
        upper[index] <= lower[index] for index in range(3)
    ):
        raise ValueError(f"tabletop policy prim has invalid world bounds: {prim_path}")
    return lower, upper


def _load_yaml_mapping(path: Path, field: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read {field}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping: {path}")
    return value


def _table_and_task_objects(
    scenario: Mapping[str, Any],
) -> tuple[Mapping[str, Any], tuple[Mapping[str, Any], ...]]:
    objects = scenario.get("objects")
    if not isinstance(objects, list) or not all(isinstance(item, dict) for item in objects):
        raise ValueError("scenario objects must be a list of mappings")
    tables = [item for item in objects if item.get("role") == "table"]
    if len(tables) != 1:
        raise ValueError("scientific workbench tabletop policy requires exactly one table object")
    return tables[0], tuple(
        item for item in objects if item is not tables[0] and item.get("role") != "context_prop"
    )


def _robot_spawn_xy(scenario: Mapping[str, Any]) -> tuple[float, float]:
    robot = scenario.get("robot")
    if not isinstance(robot, Mapping):
        raise ValueError("scenario robot must be a mapping")
    spawn = robot.get("spawn")
    if not isinstance(spawn, Mapping):
        raise ValueError("scenario robot.spawn must be a mapping")
    xyz = spawn.get("xyz")
    if (
        not isinstance(xyz, list)
        or len(xyz) != 3
        or not all(isinstance(value, int | float) and isfinite(value) for value in xyz)
    ):
        raise ValueError("scenario robot.spawn.xyz must contain three finite numbers")
    return (float(xyz[0]), float(xyz[1]))


def _robot_side_exception(
    item: Mapping[str, Any],
    policy: TabletopPlacementConstraints,
) -> str | None:
    metadata = item.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("scenario object metadata must be a mapping")
    value = metadata.get(policy.exception_metadata_key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"scenario object metadata.{policy.exception_metadata_key} must be a non-empty string"
        )
    return value.strip()


def _edge_margin_override(item: Mapping[str, Any]) -> float | None:
    metadata = item.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("scenario object metadata must be a mapping")
    value = metadata.get("tabletop_min_edge_clearance_m")
    if value is None:
        return None
    if not isinstance(value, int | float) or not isfinite(float(value)) or value < 0:
        raise ValueError(
            "scenario object metadata.tabletop_min_edge_clearance_m must be finite and non-negative"
        )
    return float(value)


def _placement_footprint(
    item: Mapping[str, Any], visual_bounds: TabletopBounds
) -> tuple[TabletopBounds, str]:
    metadata = item.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("scenario object metadata must be a mapping")
    declared = metadata.get("tabletop_support_footprint")
    if declared is None:
        return visual_bounds, "composed_visual_bounds"
    if metadata.get("tabletop_placement_class") != "fixed_benchtop_instrument":
        raise ValueError("tabletop_support_footprint is reserved for fixed_benchtop_instrument")
    if not isinstance(declared, Mapping):
        raise ValueError("tabletop_support_footprint must be a mapping")
    size = declared.get("size_xy_m")
    offset = declared.get("center_offset_xy_m", [0.0, 0.0])
    source = declared.get("source")
    if (
        not isinstance(size, list)
        or len(size) != 2
        or not all(isinstance(value, int | float) and value > 0 for value in size)
    ):
        raise ValueError("tabletop_support_footprint.size_xy_m must be two positive numbers")
    if (
        not isinstance(offset, list)
        or len(offset) != 2
        or not all(isinstance(value, int | float) and isfinite(value) for value in offset)
    ):
        raise ValueError("tabletop_support_footprint.center_offset_xy_m must be two finite numbers")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("tabletop_support_footprint.source must be a non-empty string")
    center_x, center_y = visual_bounds.center_xy
    half_x, half_y = float(size[0]) / 2.0, float(size[1]) / 2.0
    center_x += float(offset[0])
    center_y += float(offset[1])
    return (
        TabletopBounds(
            center_x - half_x,
            center_x + half_x,
            center_y - half_y,
            center_y + half_y,
        ),
        "declared_support_footprint",
    )


def _evidence_mapping(
    report: TabletopPlacementReport,
    constraints: TabletopPlacementConstraints,
    table_bounds_3d: tuple[tuple[float, float, float], tuple[float, float, float]],
    not_applicable: list[dict[str, object]],
    visual_bounds_xy: Mapping[str, TabletopBounds],
    footprint_sources: Mapping[str, str],
) -> dict[str, object]:
    objects = [
        {
            "object_id": item.object_id,
            "status": item.status,
            "world_bounds_xy_m": {
                "min": [round(item.bounds.x_min, 9), round(item.bounds.y_min, 9)],
                "max": [round(item.bounds.x_max, 9), round(item.bounds.y_max, 9)],
            },
            "edge_clearances_m": item.edge_clearances_m,
            "minimum_edge_clearance_m": item.minimum_edge_clearance_m,
            "required_edge_clearance_m": item.required_edge_clearance_m,
            "edge_clearance_status": item.edge_clearance_status,
            "footprint_source": footprint_sources[item.object_id],
            "visual_world_bounds_xy_m": {
                "min": [
                    round(visual_bounds_xy[item.object_id].x_min, 9),
                    round(visual_bounds_xy[item.object_id].y_min, 9),
                ],
                "max": [
                    round(visual_bounds_xy[item.object_id].x_max, 9),
                    round(visual_bounds_xy[item.object_id].y_max, 9),
                ],
            },
            "robot_facing_half": item.robot_facing_half,
            "robot_side_status": item.robot_side_status,
            "robot_side_exception_reason": item.robot_side_exception_reason,
        }
        for item in report.objects
    ]
    objects.extend(not_applicable)
    return {
        "schema_version": "scenario-forge-tabletop-placement-policy/v0.1",
        "overall_status": report.overall_status,
        "policy": _policy_mapping(constraints),
        "table_support_world_bounds_m": _bounds_mapping(table_bounds_3d),
        "robot_base_xy_m": [round(value, 9) for value in report.robot_xy],
        "objects": objects,
        "claim_boundary": (
            "This verifies initial tabletop footprint placement only. It does not "
            "prove reachability, grasping, path planning, collision-free motion, "
            "or task success."
        ),
    }


def _policy_mapping(constraints: TabletopPlacementConstraints) -> dict[str, object]:
    return {
        "policy_id": constraints.policy.policy_id,
        "preferred_region": "robot_facing_table_half",
        "min_edge_clearance_m": constraints.policy.min_edge_clearance_m,
        "support_surface_prim_path": constraints.support_surface_prim_path,
        "support_height_tolerance_m": constraints.support_height_tolerance_m,
        "exception_metadata_key": constraints.exception_metadata_key,
        "exception_scope": "robot-side preference only; never table-edge safety",
    }


def _bounds_mapping(
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> dict[str, list[float]]:
    return {
        "min": [round(value, 9) for value in bounds[0]],
        "max": [round(value, 9) for value in bounds[1]],
    }


def _required_string(value: Mapping[str, Any], key: str, field: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{field}.{key} must be a non-empty string")
    return result


def _blocked_summary(evidence: Mapping[str, Any]) -> str:
    blocked = [
        _blocked_object_summary(item)
        for item in evidence.get("objects", [])
        if isinstance(item, Mapping) and item.get("status") == "blocked"
    ]
    return ", ".join(blocked) if blocked else "unknown reason"


def _blocked_object_summary(item: Mapping[str, Any]) -> str:
    object_id = str(item.get("object_id", "<unknown>"))
    reasons: list[str] = []
    if item.get("edge_clearance_status") == "blocked":
        reasons.append("table-edge clearance")
    if item.get("robot_side_status") == "blocked":
        reasons.append("robot-facing side")
    return f"{object_id} ({'; '.join(reasons) or 'policy failure'})"


def _is_mesh_prim(prim: object) -> bool:
    if getattr(prim, "type_name", None) == "Mesh":
        return True
    try:
        from pxr import UsdGeom
    except ModuleNotFoundError:
        return False

    return bool(prim.IsA(UsdGeom.Mesh))


def _combined_usd_bbox(
    path: str | Path,
    *,
    include_prim: Callable[[object], bool],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    try:
        from pxr import Usd, UsdGeom
    except ModuleNotFoundError:
        return _combined_portable_usda_bbox(path, include_prim=include_prim)

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f"Unable to open USD stage: {path}")
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        useExtentsHint=False,
    )
    mins: list[tuple[float, float, float]] = []
    maxes: list[tuple[float, float, float]] = []
    for prim in stage.Traverse():
        if not include_prim(prim):
            continue
        bbox_range = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        low = _range_tuple(bbox_range.GetMin())
        high = _range_tuple(bbox_range.GetMax())
        if all(isfinite(value) for value in (*low, *high)) and all(
            high[index] >= low[index] for index in range(3)
        ):
            mins.append(low)
            maxes.append(high)
    if not mins:
        raise RuntimeError(f"No matching bbox prims found in USD stage: {path}")
    return (
        tuple(min(values[index] for values in mins) for index in range(3)),
        tuple(max(values[index] for values in maxes) for index in range(3)),
    )


def _combined_portable_usda_bbox(
    path: str | Path,
    *,
    include_prim: Callable[[object], bool],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    usd_path = Path(path)
    text = usd_path.read_text(encoding="utf-8", errors="ignore")
    mins: list[tuple[float, float, float]] = []
    maxes: list[tuple[float, float, float]] = []
    for match in USD_MESH_WITH_POINTS_RE.finditer(text):
        prim = _PortableUsdPrim(name=match.group("name"), type_name="Mesh")
        if not include_prim(prim):
            continue
        points = [
            (float(point.group("x")), float(point.group("y")), float(point.group("z")))
            for point in USD_POINT_RE.finditer(match.group("points"))
        ]
        if not points:
            continue
        mins.append(tuple(min(point[index] for point in points) for index in range(3)))
        maxes.append(tuple(max(point[index] for point in points) for index in range(3)))
    if not mins:
        raise RuntimeError(f"No matching bbox prims found in USD stage: {path}")
    return (
        tuple(min(values[index] for values in mins) for index in range(3)),
        tuple(max(values[index] for values in maxes) for index in range(3)),
    )


def _origin_above_bottom_from_bbox(
    bbox_min: Iterable[float],
    bbox_max: Iterable[float],
) -> float:
    low = tuple(float(value) for value in bbox_min)
    high = tuple(float(value) for value in bbox_max)
    transformed_z_values: list[float] = []
    for corner in product(*zip(low, high, strict=True)):
        rotated = tuple(
            sum(row[column] * corner[column] for column in range(3))
            for row in OFFICIAL_OBJECT_TO_WORLD_ROTATION
        )
        transformed_z_values.append(rotated[2] * OFFICIAL_RELATIVE_SCALE)
    return -min(transformed_z_values)


def _range_tuple(value: object) -> tuple[float, float, float]:
    return (float(value[0]), float(value[1]), float(value[2]))


def _round_float(value: float) -> float:
    return round(float(value), 6)


def _round_xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(_round_float(item) for item in value)


def _round_list(value: Iterable[float]) -> list[float]:
    return [_round_float(item) for item in value]

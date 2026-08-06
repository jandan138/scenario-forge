"""Portable layout gates for producer-composed interactive workcells."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from scenario_forge.generation.layout.tabletop_placement import (
    TabletopBounds,
    TabletopPlacementPolicy,
    evaluate_tabletop_placement,
)


class InteractiveWorkcellLayoutError(ValueError):
    """Raised after writing evidence for a blocked interactive layout."""

    def __init__(
        self,
        message: str,
        *,
        robot_table_evidence: Path,
        tabletop_evidence: Path,
    ) -> None:
        super().__init__(message)
        self.robot_table_evidence = robot_table_evidence
        self.tabletop_evidence = tabletop_evidence


@dataclass(frozen=True)
class InteractiveWorkcellLayoutResult:
    overall_status: str
    robot_table_evidence: Path
    tabletop_evidence: Path


def validate_interactive_workcell_layout(
    *,
    package_root: str | Path,
    scenario: Mapping[str, Any],
    handoff_manifest: Mapping[str, Any],
) -> InteractiveWorkcellLayoutResult:
    """Validate Lift2/table separation and producer-certified tabletop placement.

    The geometry authority is the qualified producer manifest.  This adapter
    intentionally does not open USD or import a simulator SDK.
    """

    root = Path(package_root)
    evidence_dir = root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    robot_path = evidence_dir / "robot_table_clearance.yaml"
    tabletop_path = evidence_dir / "tabletop_placement_policy.yaml"

    layout = _mapping(handoff_manifest.get("layout"), "handoff layout")
    workspace = _mapping(layout.get("robot_workspace"), "robot workspace")
    robot = _mapping(scenario.get("robot"), "scenario robot")
    spawn = _vector(_mapping(robot.get("spawn"), "robot spawn").get("xyz"), 3, "spawn xyz")
    expected_spawn = _vector(workspace.get("spawn_xyz_m"), 3, "workspace spawn")
    radius = _positive(workspace.get("base_footprint_radius_m"), "base footprint radius")
    required_clearance = _positive(
        workspace.get("minimum_table_clearance_m"), "minimum table clearance"
    )
    profile_matches = robot.get("profile_ref") == workspace.get("profile_ref")
    spawn_matches = all(
        math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9)
        for actual, expected in zip(spawn, expected_spawn, strict=True)
    )

    states = _mapping(
        _mapping(
            _mapping(handoff_manifest.get("entrypoints"), "entrypoints").get("genmanip"),
            "genmanip entrypoint",
        ).get("embedded_object_states"),
        "embedded object states",
    )
    table_aabb = _aabb(
        _mapping(states.get("support_table"), "support table state").get("world_aabb_m"),
        "support table",
    )
    dx = max(table_aabb[0][0] - spawn[0], 0.0, spawn[0] - table_aabb[1][0])
    dy = max(table_aabb[0][1] - spawn[1], 0.0, spawn[1] - table_aabb[1][1])
    center_inside = dx == 0.0 and dy == 0.0
    clearance = math.hypot(dx, dy) - radius
    clearance_pass = clearance >= required_clearance
    robot_status = "pass" if profile_matches and spawn_matches and clearance_pass else "blocked"
    robot_evidence = {
        "schema_version": "scenario-forge-robot-table-clearance/v0.1",
        "overall_status": robot_status,
        "layout_variant": layout.get("variant_id"),
        "robot_profile_ref": robot.get("profile_ref"),
        "expected_robot_profile_ref": workspace.get("profile_ref"),
        "profile_matches_producer_contract": profile_matches,
        "robot_base_center_xyz_m": _rounded(spawn),
        "expected_robot_base_center_xyz_m": _rounded(expected_spawn),
        "spawn_matches_producer_contract": spawn_matches,
        "robot_base_footprint_radius_m": round(radius, 10),
        "support_table_world_aabb_m": {
            "min": _rounded(table_aabb[0]),
            "max": _rounded(table_aabb[1]),
        },
        "robot_center_inside_table_xy": center_inside,
        "measured_clearance_m": round(clearance, 10),
        "required_clearance_m": round(required_clearance, 10),
        "claim_boundary": (
            "Axis-aligned table AABB versus circular Lift2 base footprint in XY; "
            "this is not whole-robot collision checking or motion-plan qualification."
        ),
    }
    _write_yaml(robot_path, robot_evidence)

    tabletop_contract = _mapping(layout.get("tabletop_placement"), "tabletop placement")
    edge_margin = _positive(
        tabletop_contract.get("hard_edge_clearance_m"), "hard edge clearance"
    )
    object_bounds = {
        role: TabletopBounds(*_xy_bounds(_aabb(_mapping(states.get(role), role).get("world_aabb_m"), role)))
        for role in ("source_container", "target_container")
    }
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(*_xy_bounds(table_aabb)),
        robot_xy=(spawn[0], spawn[1]),
        object_bounds=object_bounds,
        policy=TabletopPlacementPolicy(
            policy_id="interactive_workcell_robot_facing_edge_v1",
            min_edge_clearance_m=edge_margin,
        ),
    )
    tabletop_evidence = {
        "schema_version": "scenario-forge-tabletop-placement-policy/v0.1",
        "overall_status": report.overall_status,
        "layout_variant": layout.get("variant_id"),
        "geometry_authority": "qualified_producer_manifest.entrypoints.genmanip.embedded_object_states",
        "policy": {
            "policy_id": report.policy.policy_id,
            "minimum_edge_clearance_m": report.policy.min_edge_clearance_m,
            "robot_facing_edge": tabletop_contract.get("robot_facing_edge"),
        },
        "robot_base_xy_m": _rounded(report.robot_xy),
        "table_support_world_bounds_m": {
            "min": _rounded(table_aabb[0]),
            "max": _rounded(table_aabb[1]),
        },
        "objects": [
            {
                "object_id": item.object_id,
                "status": item.status,
                "world_bounds_xy_m": {
                    "x_min": item.bounds.x_min,
                    "x_max": item.bounds.x_max,
                    "y_min": item.bounds.y_min,
                    "y_max": item.bounds.y_max,
                },
                "edge_clearances_m": item.edge_clearances_m,
                "minimum_edge_clearance_m": item.minimum_edge_clearance_m,
                "robot_facing_half": item.robot_facing_half,
            }
            for item in report.objects
        ],
        "claim_boundary": (
            "Initial AABB placement only; this does not establish arm reachability, "
            "stable grasp, liquid transfer, or benchmark success."
        ),
    }
    _write_yaml(tabletop_path, tabletop_evidence)

    overall = "pass" if robot_status == "pass" and report.overall_status == "pass" else "blocked"
    result = InteractiveWorkcellLayoutResult(overall, robot_path, tabletop_path)
    if overall != "pass":
        raise InteractiveWorkcellLayoutError(
            "interactive workcell layout is blocked",
            robot_table_evidence=robot_path,
            tabletop_evidence=tabletop_path,
        )
    return result


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _vector(value: object, length: int, field: str) -> tuple[float, ...]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != length
        or not all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            for item in value
        )
    ):
        raise ValueError(f"{field} must contain {length} finite numbers")
    return tuple(float(item) for item in value)


def _positive(value: object, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0.0
    ):
        raise ValueError(f"{field} must be positive")
    return float(value)


def _aabb(value: object, field: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    item = _mapping(value, f"{field} AABB")
    lower = _vector(item.get("min"), 3, f"{field} AABB min")
    upper = _vector(item.get("max"), 3, f"{field} AABB max")
    if any(lo >= hi for lo, hi in zip(lower, upper, strict=True)):
        raise ValueError(f"{field} AABB is empty")
    return lower, upper


def _xy_bounds(
    aabb: tuple[tuple[float, ...], tuple[float, ...]]
) -> tuple[float, float, float, float]:
    return (aabb[0][0], aabb[1][0], aabb[0][1], aabb[1][1])


def _rounded(values: tuple[float, ...]) -> list[float]:
    return [round(value, 10) for value in values]


def _write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

"""Simulator-neutral policy evaluation for science-workbench tabletop layouts."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class TabletopBounds:
    """Axis-aligned XY bounds in the composed scene's world frame."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def __post_init__(self) -> None:
        values = (self.x_min, self.x_max, self.y_min, self.y_max)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("tabletop bounds must be finite")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("tabletop bounds must have positive area")

    @property
    def center_xy(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)


@dataclass(frozen=True)
class TabletopPlacementPolicy:
    policy_id: str
    min_edge_clearance_m: float

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("tabletop placement policy_id must not be empty")
        if not math.isfinite(self.min_edge_clearance_m) or self.min_edge_clearance_m < 0.0:
            raise ValueError("tabletop placement min_edge_clearance_m must be non-negative")


@dataclass(frozen=True)
class TabletopPlacementObjectResult:
    object_id: str
    bounds: TabletopBounds
    edge_clearances_m: dict[str, float]
    minimum_edge_clearance_m: float
    edge_clearance_status: str
    robot_facing_half: bool
    robot_side_status: str
    robot_side_exception_reason: str | None

    @property
    def status(self) -> str:
        if self.edge_clearance_status == "blocked" or self.robot_side_status == "blocked":
            return "blocked"
        if self.robot_side_status == "exception":
            return "pass_with_robot_side_exception"
        return "pass"


@dataclass(frozen=True)
class TabletopPlacementReport:
    policy: TabletopPlacementPolicy
    table_bounds: TabletopBounds
    robot_xy: tuple[float, float]
    objects: tuple[TabletopPlacementObjectResult, ...]

    @property
    def overall_status(self) -> str:
        return "blocked" if any(item.status == "blocked" for item in self.objects) else "pass"


def evaluate_tabletop_placement(
    *,
    table_bounds: TabletopBounds,
    robot_xy: tuple[float, float],
    object_bounds: Mapping[str, TabletopBounds],
    policy: TabletopPlacementPolicy,
    robot_side_exceptions: Mapping[str, str] | None = None,
) -> TabletopPlacementReport:
    """Evaluate the hard edge margin and default robot-facing-half preference.

    A far-side object is permitted only when it supplies a human-readable
    exception.  No exception can waive the physical table-edge margin.
    """

    if not object_bounds:
        raise ValueError("tabletop placement requires at least one task object")
    if not all(isinstance(object_id, str) and object_id for object_id in object_bounds):
        raise ValueError("tabletop placement object ids must be non-empty strings")
    robot = _xy(robot_xy, "robot_xy")
    exceptions = dict(robot_side_exceptions or {})
    _validate_exceptions(exceptions, object_bounds)
    robot_direction = _robot_direction(table_bounds.center_xy, robot)

    results: list[TabletopPlacementObjectResult] = []
    for object_id, bounds in object_bounds.items():
        edge_clearances = {
            "x_min": bounds.x_min - table_bounds.x_min,
            "x_max": table_bounds.x_max - bounds.x_max,
            "y_min": bounds.y_min - table_bounds.y_min,
            "y_max": table_bounds.y_max - bounds.y_max,
        }
        minimum = min(edge_clearances.values())
        edge_status = (
            "pass"
            if minimum >= policy.min_edge_clearance_m
            else "blocked"
        )
        object_center = bounds.center_xy
        robot_facing_half = _in_robot_facing_half(
            table_bounds.center_xy,
            object_center,
            robot_direction,
        )
        exception = exceptions.get(object_id)
        robot_side_status = (
            "pass"
            if robot_facing_half
            else "exception"
            if exception is not None
            else "blocked"
        )
        results.append(
            TabletopPlacementObjectResult(
                object_id=object_id,
                bounds=bounds,
                edge_clearances_m={
                    key: round(value, 9) for key, value in edge_clearances.items()
                },
                minimum_edge_clearance_m=round(minimum, 9),
                edge_clearance_status=edge_status,
                robot_facing_half=robot_facing_half,
                robot_side_status=robot_side_status,
                robot_side_exception_reason=exception,
            )
        )
    return TabletopPlacementReport(
        policy=policy,
        table_bounds=table_bounds,
        robot_xy=robot,
        objects=tuple(results),
    )


def _xy(value: tuple[float, float], field: str) -> tuple[float, float]:
    if len(value) != 2 or not all(math.isfinite(component) for component in value):
        raise ValueError(f"{field} must contain two finite coordinates")
    return (float(value[0]), float(value[1]))


def _validate_exceptions(
    exceptions: Mapping[str, str],
    object_bounds: Mapping[str, TabletopBounds],
) -> None:
    unknown = sorted(set(exceptions).difference(object_bounds))
    if unknown:
        raise ValueError(
            "tabletop placement exceptions reference unknown objects: " + ", ".join(unknown)
        )
    invalid = sorted(
        object_id
        for object_id, reason in exceptions.items()
        if not isinstance(reason, str) or not reason.strip()
    )
    if invalid:
        raise ValueError(
            "tabletop placement exceptions require non-empty reasons: " + ", ".join(invalid)
        )


def _robot_direction(
    table_center: tuple[float, float], robot_xy: tuple[float, float]
) -> tuple[float, float]:
    direction = (robot_xy[0] - table_center[0], robot_xy[1] - table_center[1])
    length = math.hypot(*direction)
    if length <= 1e-9:
        raise ValueError("robot base must not coincide with the tabletop centre")
    return (direction[0] / length, direction[1] / length)


def _in_robot_facing_half(
    table_center: tuple[float, float],
    object_center: tuple[float, float],
    robot_direction: tuple[float, float],
) -> bool:
    offset = (object_center[0] - table_center[0], object_center[1] - table_center[1])
    return offset[0] * robot_direction[0] + offset[1] * robot_direction[1] >= -1e-9

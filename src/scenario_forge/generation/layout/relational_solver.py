"""Deterministic relational and multi-DOF sweep-aware tabletop layout solver.

Pure package module: no simulator SDKs, OpenUSD, or LLM client imports.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any, Mapping

from scenario_forge.core.scenario import PoseSpec
from scenario_forge.generation.layout.constraints import LayoutConstraints
from scenario_forge.generation.layout.tabletop_placement import (
    TabletopBounds,
    TabletopPlacementPolicy,
    evaluate_tabletop_placement,
)


RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION = "relational-layout-spec/v0.1"
RELATIONAL_LAYOUT_RESULT_SCHEMA_VERSION = "relational-layout-result/v0.1"

_SUPPORTED_REGIONS = frozenset(
    {"center", "left", "right", "robot_near", "far_context", "any"}
)
_SUPPORTED_PREDICATES = frozenset(
    {"left_of", "right_of", "in_front_of", "behind", "near"}
)
_LOCAL_AXIS_VECTORS: dict[str, tuple[float, float]] = {
    "-y": (0.0, -1.0),
    "+y": (0.0, 1.0),
    "-x": (-1.0, 0.0),
    "+x": (1.0, 0.0),
}


class RelationalLayoutSpecError(ValueError):
    """Raised when a relational layout request is malformed."""


@dataclass(frozen=True)
class KinematicClearanceVolume:
    clearance_id: str
    joint: str
    local_x_range_m: tuple[float, float]
    local_y_range_m: tuple[float, float]


@dataclass(frozen=True)
class WorldClearanceVolume:
    clearance_id: str
    joint: str
    world_xy_min_m: tuple[float, float]
    world_xy_max_m: tuple[float, float]

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.clearance_id,
            "joint": self.joint,
            "world_xy_min_m": [_round6(self.world_xy_min_m[0]), _round6(self.world_xy_min_m[1])],
            "world_xy_max_m": [_round6(self.world_xy_max_m[0]), _round6(self.world_xy_max_m[1])],
        }


@dataclass(frozen=True)
class SolvedObjectPlacement:
    object_id: str
    role: str
    pose: PoseSpec
    yaw_deg: float
    world_xy_min_m: tuple[float, float]
    world_xy_max_m: tuple[float, float]
    world_clearance_volumes: tuple[WorldClearanceVolume, ...]
    stacked_on: str | None = None
    robot_side_exception: str | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.object_id,
            "role": self.role,
            "pose": self.pose.to_mapping(),
            "yaw_deg": _round6(self.yaw_deg),
            "world_xy_min_m": [_round6(self.world_xy_min_m[0]), _round6(self.world_xy_min_m[1])],
            "world_xy_max_m": [_round6(self.world_xy_max_m[0]), _round6(self.world_xy_max_m[1])],
            "world_clearance_volumes": [
                volume.to_mapping() for volume in self.world_clearance_volumes
            ],
        }
        if self.stacked_on is not None:
            payload["stacked_on"] = self.stacked_on
        if self.robot_side_exception is not None:
            payload["robot_side_exception"] = self.robot_side_exception
        return payload


@dataclass(frozen=True)
class LayoutConflict:
    conflict_type: str
    objects: tuple[str, ...]
    message: str
    remediation_hint: str
    joint: str | None = None
    clearance_id: str | None = None

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "conflict_type": self.conflict_type,
            "objects": list(self.objects),
            "message": self.message,
            "remediation_hint": self.remediation_hint,
        }
        if self.joint is not None:
            payload["joint"] = self.joint
        if self.clearance_id is not None:
            payload["clearance_id"] = self.clearance_id
        return payload


@dataclass(frozen=True)
class RelationalLayoutResult:
    status: str
    seed: int
    table_bounds: TabletopBounds
    surface_z_m: float
    min_edge_clearance_m: float
    placements: tuple[SolvedObjectPlacement, ...]
    conflicts: tuple[LayoutConflict, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": RELATIONAL_LAYOUT_RESULT_SCHEMA_VERSION,
            "status": self.status,
            "seed": self.seed,
            "table": {
                "x_range_m": [_round6(self.table_bounds.x_min), _round6(self.table_bounds.x_max)],
                "y_range_m": [_round6(self.table_bounds.y_min), _round6(self.table_bounds.y_max)],
                "surface_z_m": _round6(self.surface_z_m),
                "min_edge_clearance_m": _round6(self.min_edge_clearance_m),
            },
            "placements": [item.to_mapping() for item in self.placements],
            "conflicts": [conflict.to_mapping() for conflict in self.conflicts],
        }


@dataclass(frozen=True)
class _ParsedObjectRequest:
    object_id: str
    role: str
    footprint_xy_m: tuple[float, float]
    region: str
    facing: str
    local_front_axis: str
    yaw_offset_deg: float
    support_z_offset_m: float
    support_top_offset_z_m: float
    fixed_xy_m: tuple[float, float] | None
    stacked_on: str | None
    stack_xy_offset_m: tuple[float, float]
    robot_side_exception: str | None
    clearance_volumes: tuple[KinematicClearanceVolume, ...]


@dataclass(frozen=True)
class _ParsedRelation:
    subject: str
    predicate: str
    reference: str
    min_gap_m: float
    max_center_distance_m: float | None


def _round6(value: float) -> float:
    rounded = round(float(value), 6)
    return 0.0 if rounded == 0.0 else rounded


def solve_relational_tabletop_layout(
    spec: Mapping[str, Any],
    *,
    domain_constraints: LayoutConstraints | None = None,
) -> RelationalLayoutResult:
    """Solve a relational tabletop layout with multi-DOF sweep keep-out volumes."""

    if not isinstance(spec, Mapping):
        raise RelationalLayoutSpecError("relational layout spec must be a mapping")
    schema_version = spec.get("schema_version")
    if schema_version != RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION:
        raise RelationalLayoutSpecError(
            f"unsupported relational layout schema_version {schema_version!r}; "
            f"expected {RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION!r}"
        )

    seed = _int_value(spec.get("seed", 0), "seed")
    table_bounds, surface_z_m, min_edge_clearance_m = _parse_table_config(
        spec.get("table"),
        domain_constraints=domain_constraints,
    )
    robot_xy = _pair_floats(spec.get("robot_xy", [0.0, -1.02]), "robot_xy")
    min_object_clearance_m = _non_negative_float(
        spec.get("min_object_clearance_m", 0.03),
        "min_object_clearance_m",
    )

    objects = _parse_objects(spec.get("objects"))
    object_by_id = {obj.object_id: obj for obj in objects}
    relations = _parse_relations(spec.get("relations", []), set(object_by_id))

    forward_hat, toward_robot_hat, left_hat, right_hat = _robot_table_basis(
        table_bounds.center_xy,
        robot_xy,
    )

    base_objects = [obj for obj in objects if obj.stacked_on is None]
    stacked_objects = [obj for obj in objects if obj.stacked_on is not None]
    ordered_base = _order_base_objects(base_objects, relations)

    rng = random.Random(seed)
    candidates_by_id: dict[str, list[SolvedObjectPlacement]] = {
        obj.object_id: _generate_candidates_for_object(
            obj=obj,
            table_bounds=table_bounds,
            surface_z_m=surface_z_m,
            min_edge_clearance_m=min_edge_clearance_m,
            toward_robot_hat=toward_robot_hat,
            forward_hat=forward_hat,
            left_hat=left_hat,
            right_hat=right_hat,
            rng=rng,
        )
        for obj in ordered_base
    }

    policy = TabletopPlacementPolicy(
        policy_id="relational_solver.robot_facing_tabletop.v1",
        min_edge_clearance_m=min_edge_clearance_m,
    )

    chosen: dict[str, SolvedObjectPlacement] = {}
    search_steps = 0
    max_search_steps = 12000

    def backtrack(idx: int) -> bool:
        nonlocal search_steps
        if idx == len(ordered_base):
            return _validate_global_tabletop_policy(
                chosen=chosen,
                table_bounds=table_bounds,
                robot_xy=robot_xy,
                policy=policy,
            )
        obj = ordered_base[idx]
        for candidate in candidates_by_id[obj.object_id]:
            search_steps += 1
            if search_steps > max_search_steps:
                return False
            if _is_compatible_with_placed(
                candidate=candidate,
                placed=chosen,
                relations=relations,
                min_object_clearance_m=min_object_clearance_m,
                toward_robot_hat=toward_robot_hat,
                forward_hat=forward_hat,
                left_hat=left_hat,
                right_hat=right_hat,
            ):
                chosen[obj.object_id] = candidate
                if backtrack(idx + 1):
                    return True
                chosen.pop(obj.object_id, None)
        return False

    solved_ok = backtrack(0)
    if solved_ok:
        all_placements = dict(chosen)
        stack_conflicts: list[LayoutConflict] = []
        for stacked in _order_stacked_objects(stacked_objects, object_by_id):
            parent = all_placements.get(stacked.stacked_on or "")
            if parent is None:
                stack_conflicts.append(
                    LayoutConflict(
                        conflict_type="missing_stack_parent",
                        objects=(stacked.object_id, stacked.stacked_on or ""),
                        message=f"Stacked object {stacked.object_id!r} parent was not placed.",
                        remediation_hint="Ensure stacked_on references a non-cyclic base object.",
                    )
                )
                continue
            parent_req = object_by_id[parent.object_id]
            child_z = (
                parent.pose.xyz[2]
                + parent_req.support_top_offset_z_m
                + stacked.support_z_offset_m
            )
            child_xy = (
                parent.pose.xyz[0] + stacked.stack_xy_offset_m[0],
                parent.pose.xyz[1] + stacked.stack_xy_offset_m[1],
            )
            all_placements[stacked.object_id] = _make_placement_at_xy(
                obj=stacked,
                xy=child_xy,
                z_m=child_z,
                toward_robot_hat=toward_robot_hat,
            )

        if not stack_conflicts:
            ordered_result = tuple(
                all_placements[obj.object_id] for obj in objects if obj.object_id in all_placements
            )
            return RelationalLayoutResult(
                status="solved",
                seed=seed,
                table_bounds=table_bounds,
                surface_z_m=surface_z_m,
                min_edge_clearance_m=min_edge_clearance_m,
                placements=ordered_result,
                conflicts=(),
            )

    # Build nominal/diagnostic placement set to attribute exact conflicts
    diagnostic_placements: dict[str, SolvedObjectPlacement] = {}
    for obj in ordered_base:
        cands = candidates_by_id[obj.object_id]
        if cands:
            diagnostic_placements[obj.object_id] = cands[0]
        else:
            fallback_xy = obj.fixed_xy_m or table_bounds.center_xy
            diagnostic_placements[obj.object_id] = _make_placement_at_xy(
                obj=obj,
                xy=fallback_xy,
                z_m=surface_z_m + obj.support_z_offset_m,
                toward_robot_hat=toward_robot_hat,
            )

    conflicts = _diagnose_conflicts(
        placements=diagnostic_placements,
        objects=ordered_base,
        relations=relations,
        table_bounds=table_bounds,
        robot_xy=robot_xy,
        policy=policy,
        min_object_clearance_m=min_object_clearance_m,
        toward_robot_hat=toward_robot_hat,
        forward_hat=forward_hat,
        left_hat=left_hat,
        right_hat=right_hat,
    )
    if not conflicts:
        conflicts = (
            LayoutConflict(
                conflict_type="joint_constraint_exhausted",
                objects=tuple(obj.object_id for obj in ordered_base),
                message="Coupled footprint, clearance, and spatial relation constraints exhausted search budget.",
                remediation_hint=(
                    "Relax min_gap_m / max_center_distance_m, move context_prop items to "
                    "far_context, or reduce object count."
                ),
            ),
        )
    return RelationalLayoutResult(
        status="infeasible",
        seed=seed,
        table_bounds=table_bounds,
        surface_z_m=surface_z_m,
        min_edge_clearance_m=min_edge_clearance_m,
        placements=(),
        conflicts=conflicts,
    )


def _parse_table_config(
    raw_table: object,
    *,
    domain_constraints: LayoutConstraints | None,
) -> tuple[TabletopBounds, float, float]:
    default_surface_z = (
        domain_constraints.workspace.z if domain_constraints is not None else 0.755
    )
    default_margin = (
        domain_constraints.tabletop_placement.policy.min_edge_clearance_m
        if domain_constraints is not None and domain_constraints.tabletop_placement is not None
        else 0.10
    )
    if raw_table is None:
        return TabletopBounds(-1.0, 1.0, -0.40, 0.40), default_surface_z, default_margin
    if not isinstance(raw_table, Mapping):
        raise RelationalLayoutSpecError("table must be a mapping when provided")
    x_min, x_max = _pair_floats(raw_table.get("x_range_m", [-1.0, 1.0]), "table.x_range_m")
    y_min, y_max = _pair_floats(raw_table.get("y_range_m", [-0.40, 0.40]), "table.y_range_m")
    surface_z = _finite_float(raw_table.get("surface_z_m", default_surface_z), "table.surface_z_m")
    min_edge = _non_negative_float(
        raw_table.get("min_edge_clearance_m", default_margin),
        "table.min_edge_clearance_m",
    )
    try:
        bounds = TabletopBounds(x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max)
    except ValueError as exc:
        raise RelationalLayoutSpecError(f"table: {exc}") from exc
    return bounds, surface_z, min_edge


def _parse_objects(raw_objects: object) -> tuple[_ParsedObjectRequest, ...]:
    if not isinstance(raw_objects, list) or not raw_objects:
        raise RelationalLayoutSpecError("objects must be a non-empty list")
    parsed: list[_ParsedObjectRequest] = []
    seen: set[str] = set()
    for idx, raw_item in enumerate(raw_objects):
        field = f"objects[{idx}]"
        if not isinstance(raw_item, Mapping):
            raise RelationalLayoutSpecError(f"{field} must be a mapping")
        obj_id = _non_empty_str(raw_item.get("id"), f"{field}.id")
        if obj_id in seen:
            raise RelationalLayoutSpecError(f"duplicate object id {obj_id!r}")
        seen.add(obj_id)
        role = _non_empty_str(raw_item.get("role"), f"{field}.role")
        width_x, depth_y = _pair_floats(raw_item.get("footprint_xy_m"), f"{field}.footprint_xy_m")
        if width_x <= 0.0 or depth_y <= 0.0:
            raise RelationalLayoutSpecError(f"{field}.footprint_xy_m dimensions must be positive")
        region = str(raw_item.get("region", "any"))
        if region not in _SUPPORTED_REGIONS:
            raise RelationalLayoutSpecError(
                f"{field}.region must be one of {sorted(_SUPPORTED_REGIONS)}"
            )
        facing = str(raw_item.get("facing", "robot"))
        if facing not in {"robot", "world"}:
            raise RelationalLayoutSpecError(f"{field}.facing must be 'robot' or 'world'")
        local_front = str(raw_item.get("local_front_axis", "-y"))
        if local_front not in _LOCAL_AXIS_VECTORS:
            raise RelationalLayoutSpecError(
                f"{field}.local_front_axis must be one of {sorted(_LOCAL_AXIS_VECTORS)}"
            )
        yaw_offset_deg = _finite_float(raw_item.get("yaw_offset_deg", 0.0), f"{field}.yaw_offset_deg")
        support_z_offset_m = _finite_float(
            raw_item.get("support_z_offset_m", 0.0),
            f"{field}.support_z_offset_m",
        )
        support_top_offset_z_m = _non_negative_float(
            raw_item.get("support_top_offset_z_m", 0.0),
            f"{field}.support_top_offset_z_m",
        )
        raw_fixed = raw_item.get("fixed_xy_m")
        fixed_xy = None if raw_fixed is None else _pair_floats(raw_fixed, f"{field}.fixed_xy_m")
        raw_stacked = raw_item.get("stacked_on")
        stacked_on = (
            None if raw_stacked is None else _non_empty_str(raw_stacked, f"{field}.stacked_on")
        )
        stack_offset = _pair_floats(
            raw_item.get("stack_xy_offset_m", [0.0, 0.0]),
            f"{field}.stack_xy_offset_m",
        )
        raw_exception = raw_item.get("robot_side_exception")
        exception = (
            None
            if raw_exception is None
            else _non_empty_str(raw_exception, f"{field}.robot_side_exception")
        )
        if exception is None and region == "far_context":
            exception = "Far-side context object placed outside primary robot-facing manipulation zone."

        raw_volumes = raw_item.get("kinematic_clearance_volumes", [])
        if not isinstance(raw_volumes, list):
            raise RelationalLayoutSpecError(
                f"{field}.kinematic_clearance_volumes must be a list"
            )
        volumes: list[KinematicClearanceVolume] = []
        for v_idx, raw_vol in enumerate(raw_volumes):
            v_field = f"{field}.kinematic_clearance_volumes[{v_idx}]"
            if not isinstance(raw_vol, Mapping):
                raise RelationalLayoutSpecError(f"{v_field} must be a mapping")
            cid = _non_empty_str(raw_vol.get("id"), f"{v_field}.id")
            joint = _non_empty_str(raw_vol.get("joint"), f"{v_field}.joint")
            bounds_map = raw_vol.get("local_xy_bounds_m")
            if not isinstance(bounds_map, Mapping):
                raise RelationalLayoutSpecError(f"{v_field}.local_xy_bounds_m must be a mapping")
            lx0, lx1 = _pair_floats(bounds_map.get("x"), f"{v_field}.local_xy_bounds_m.x")
            ly0, ly1 = _pair_floats(bounds_map.get("y"), f"{v_field}.local_xy_bounds_m.y")
            if lx1 <= lx0 or ly1 <= ly0:
                raise RelationalLayoutSpecError(
                    f"{v_field}.local_xy_bounds_m ranges must have upper > lower"
                )
            volumes.append(
                KinematicClearanceVolume(
                    clearance_id=cid,
                    joint=joint,
                    local_x_range_m=(lx0, lx1),
                    local_y_range_m=(ly0, ly1),
                )
            )
        parsed.append(
            _ParsedObjectRequest(
                object_id=obj_id,
                role=role,
                footprint_xy_m=(width_x, depth_y),
                region=region,
                facing=facing,
                local_front_axis=local_front,
                yaw_offset_deg=yaw_offset_deg,
                support_z_offset_m=support_z_offset_m,
                support_top_offset_z_m=support_top_offset_z_m,
                fixed_xy_m=fixed_xy,
                stacked_on=stacked_on,
                stack_xy_offset_m=stack_offset,
                robot_side_exception=exception,
                clearance_volumes=tuple(volumes),
            )
        )
    for item in parsed:
        if item.stacked_on is not None and item.stacked_on not in seen:
            raise RelationalLayoutSpecError(
                f"object {item.object_id!r} stacked_on unknown object {item.stacked_on!r}"
            )
        if item.stacked_on == item.object_id:
            raise RelationalLayoutSpecError(
                f"object {item.object_id!r} cannot be stacked_on itself"
            )
    return tuple(parsed)


def _parse_relations(raw_relations: object, object_ids: set[str]) -> tuple[_ParsedRelation, ...]:
    if not isinstance(raw_relations, list):
        raise RelationalLayoutSpecError("relations must be a list")
    relations: list[_ParsedRelation] = []
    for idx, raw_rel in enumerate(raw_relations):
        field = f"relations[{idx}]"
        if not isinstance(raw_rel, Mapping):
            raise RelationalLayoutSpecError(f"{field} must be a mapping")
        subject = _non_empty_str(raw_rel.get("subject"), f"{field}.subject")
        predicate = _non_empty_str(raw_rel.get("predicate"), f"{field}.predicate")
        reference = _non_empty_str(raw_rel.get("reference"), f"{field}.reference")
        if subject not in object_ids:
            raise RelationalLayoutSpecError(f"{field}.subject unknown object {subject!r}")
        if reference not in object_ids:
            raise RelationalLayoutSpecError(f"{field}.reference unknown object {reference!r}")
        if subject == reference:
            raise RelationalLayoutSpecError(f"{field} cannot relate {subject!r} to itself")
        if predicate not in _SUPPORTED_PREDICATES:
            raise RelationalLayoutSpecError(
                f"{field}.predicate must be one of {sorted(_SUPPORTED_PREDICATES)}"
            )
        min_gap = _non_negative_float(raw_rel.get("min_gap_m", 0.03), f"{field}.min_gap_m")
        raw_max_dist = raw_rel.get("max_center_distance_m")
        max_dist = (
            None
            if raw_max_dist is None
            else _non_negative_float(raw_max_dist, f"{field}.max_center_distance_m")
        )
        if predicate == "near" and max_dist is None:
            max_dist = 0.50
        relations.append(
            _ParsedRelation(
                subject=subject,
                predicate=predicate,
                reference=reference,
                min_gap_m=min_gap,
                max_center_distance_m=max_dist,
            )
        )
    return tuple(relations)


def _robot_table_basis(
    table_center: tuple[float, float],
    robot_xy: tuple[float, float],
) -> tuple[
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
]:
    dx = table_center[0] - robot_xy[0]
    dy = table_center[1] - robot_xy[1]
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        forward_hat = (0.0, 1.0)
    else:
        forward_hat = (dx / norm, dy / norm)
    toward_robot_hat = (-forward_hat[0], -forward_hat[1])
    left_hat = (-forward_hat[1], forward_hat[0])
    right_hat = (forward_hat[1], -forward_hat[0])
    return forward_hat, toward_robot_hat, left_hat, right_hat


def _compute_yaw_rad(
    obj: _ParsedObjectRequest,
    toward_robot_hat: tuple[float, float],
) -> float:
    if obj.facing == "world":
        return math.radians(obj.yaw_offset_deg)
    fx, fy = _LOCAL_AXIS_VECTORS[obj.local_front_axis]
    local_angle = math.atan2(fy, fx)
    target_angle = math.atan2(toward_robot_hat[1], toward_robot_hat[0])
    return target_angle - local_angle + math.radians(obj.yaw_offset_deg)


def _rotated_world_aabb(
    center_xy: tuple[float, float],
    yaw_rad: float,
    local_x_range: tuple[float, float],
    local_y_range: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    c = math.cos(yaw_rad)
    s = math.sin(yaw_rad)
    xs: list[float] = []
    ys: list[float] = []
    for lx in local_x_range:
        for ly in local_y_range:
            wx = center_xy[0] + c * lx - s * ly
            wy = center_xy[1] + s * lx + c * ly
            xs.append(wx)
            ys.append(wy)
    return (min(xs), min(ys)), (max(xs), max(ys))


def _make_placement_at_xy(
    *,
    obj: _ParsedObjectRequest,
    xy: tuple[float, float],
    z_m: float,
    toward_robot_hat: tuple[float, float],
) -> SolvedObjectPlacement:
    yaw_rad = _compute_yaw_rad(obj, toward_robot_hat)
    half_w = obj.footprint_xy_m[0] / 2.0
    half_d = obj.footprint_xy_m[1] / 2.0
    xy_min, xy_max = _rotated_world_aabb(
        xy,
        yaw_rad,
        (-half_w, half_w),
        (-half_d, half_d),
    )
    world_vols = tuple(
        WorldClearanceVolume(
            clearance_id=vol.clearance_id,
            joint=vol.joint,
            world_xy_min_m=v_min,
            world_xy_max_m=v_max,
        )
        for vol in obj.clearance_volumes
        for v_min, v_max in [
            _rotated_world_aabb(xy, yaw_rad, vol.local_x_range_m, vol.local_y_range_m)
        ]
    )
    w = math.cos(yaw_rad / 2.0)
    z_q = math.sin(yaw_rad / 2.0)
    pose = PoseSpec(
        xyz=(_round6(xy[0]), _round6(xy[1]), _round6(z_m)),
        wxyz=(_round6(w), 0.0, 0.0, _round6(z_q)),
    )
    return SolvedObjectPlacement(
        object_id=obj.object_id,
        role=obj.role,
        pose=pose,
        yaw_deg=math.degrees(yaw_rad),
        world_xy_min_m=xy_min,
        world_xy_max_m=xy_max,
        world_clearance_volumes=world_vols,
        stacked_on=obj.stacked_on,
        robot_side_exception=obj.robot_side_exception,
    )


def _order_base_objects(
    base_objects: list[_ParsedObjectRequest],
    relations: tuple[_ParsedRelation, ...],
) -> list[_ParsedObjectRequest]:
    ref_counts: dict[str, int] = {obj.object_id: 0 for obj in base_objects}
    for rel in relations:
        if rel.reference in ref_counts:
            ref_counts[rel.reference] += 1

    def sort_key(obj: _ParsedObjectRequest) -> tuple[int, int, float, str]:
        pinned_rank = 0 if obj.fixed_xy_m is not None else 1
        role_rank = (
            0
            if obj.role in {"articulated_appliance", "articulated_device"}
            else (2 if obj.role == "context_prop" else 1)
        )
        area = obj.footprint_xy_m[0] * obj.footprint_xy_m[1]
        return (pinned_rank, role_rank, -ref_counts[obj.object_id] - area, obj.object_id)

    return sorted(base_objects, key=sort_key)


def _order_stacked_objects(
    stacked_objects: list[_ParsedObjectRequest],
    object_by_id: Mapping[str, _ParsedObjectRequest],
) -> list[_ParsedObjectRequest]:
    ordered: list[_ParsedObjectRequest] = []
    remaining = list(stacked_objects)
    placed_ids = {
        obj_id for obj_id, obj in object_by_id.items() if obj.stacked_on is None
    }
    while remaining:
        progressed = False
        for item in list(remaining):
            if item.stacked_on in placed_ids:
                ordered.append(item)
                placed_ids.add(item.object_id)
                remaining.remove(item)
                progressed = True
        if not progressed:
            ordered.extend(remaining)
            break
    return ordered


def _generate_candidates_for_object(
    *,
    obj: _ParsedObjectRequest,
    table_bounds: TabletopBounds,
    surface_z_m: float,
    min_edge_clearance_m: float,
    toward_robot_hat: tuple[float, float],
    forward_hat: tuple[float, float],
    left_hat: tuple[float, float],
    right_hat: tuple[float, float],
    rng: random.Random,
) -> list[SolvedObjectPlacement]:
    z_m = surface_z_m + obj.support_z_offset_m
    if obj.fixed_xy_m is not None:
        cand = _make_placement_at_xy(
            obj=obj,
            xy=obj.fixed_xy_m,
            z_m=z_m,
            toward_robot_hat=toward_robot_hat,
        )
        if _within_edge_margin(cand, table_bounds, min_edge_clearance_m):
            return [cand]
        return []

    probe = _make_placement_at_xy(
        obj=obj,
        xy=(0.0, 0.0),
        z_m=z_m,
        toward_robot_hat=toward_robot_hat,
    )
    half_ext_x = (probe.world_xy_max_m[0] - probe.world_xy_min_m[0]) / 2.0
    half_ext_y = (probe.world_xy_max_m[1] - probe.world_xy_min_m[1]) / 2.0

    x_lo = table_bounds.x_min + min_edge_clearance_m + half_ext_x
    x_hi = table_bounds.x_max - min_edge_clearance_m - half_ext_x
    y_lo = table_bounds.y_min + min_edge_clearance_m + half_ext_y
    y_hi = table_bounds.y_max - min_edge_clearance_m - half_ext_y
    if x_lo > x_hi or y_lo > y_hi:
        return []

    cx, cy = table_bounds.center_xy
    nx, ny = 9, 7
    raw_points: list[tuple[float, float]] = []
    for ix in range(nx):
        fx = ix / (nx - 1) if nx > 1 else 0.5
        for iy in range(ny):
            fy = iy / (ny - 1) if ny > 1 else 0.5
            jx = (rng.random() - 0.5) * 0.012
            jy = (rng.random() - 0.5) * 0.012
            px = min(max(x_lo + fx * (x_hi - x_lo) + jx, x_lo), x_hi)
            py = min(max(y_lo + fy * (y_hi - y_lo) + jy, y_lo), y_hi)
            raw_points.append((px, py))
    # Also include clean canonical anchors
    for anchor_fx in (0.5, 0.25, 0.75, 0.35, 0.65):
        for anchor_fy in (0.15, 0.30, 0.45, 0.55, 0.80):
            raw_points.append(
                (
                    x_lo + anchor_fx * (x_hi - x_lo),
                    y_lo + anchor_fy * (y_hi - y_lo),
                )
            )

    scored: list[tuple[float, SolvedObjectPlacement]] = []
    for px, py in raw_points:
        dx = px - cx
        dy = py - cy
        lat_left = dx * left_hat[0] + dy * left_hat[1]
        lat_right = dx * right_hat[0] + dy * right_hat[1]
        depth_toward = dx * toward_robot_hat[0] + dy * toward_robot_hat[1]
        depth_away = dx * forward_hat[0] + dy * forward_hat[1]

        # Enforce robot-facing half unless exception present
        if obj.robot_side_exception is None and depth_toward < -1e-9:
            continue

        if obj.region == "left" and lat_left <= 0.02:
            continue
        if obj.region == "right" and lat_right <= 0.02:
            continue
        if obj.region == "far_context" and depth_away <= 0.02:
            continue
        if obj.region == "robot_near" and depth_toward <= 0.02:
            continue

        cand = _make_placement_at_xy(
            obj=obj,
            xy=(px, py),
            z_m=z_m,
            toward_robot_hat=toward_robot_hat,
        )
        if not _within_edge_margin(cand, table_bounds, min_edge_clearance_m):
            continue

        score = _region_preference_cost(
            region=obj.region,
            lat_left=lat_left,
            lat_right=lat_right,
            depth_toward=depth_toward,
            depth_away=depth_away,
        )
        scored.append((score, cand))

    scored.sort(key=lambda item: item[0])
    return [cand for _, cand in scored[:48]]


def _region_preference_cost(
    *,
    region: str,
    lat_left: float,
    lat_right: float,
    depth_toward: float,
    depth_away: float,
) -> float:
    if region == "center":
        # Prefer centered laterally and slightly toward robot (or near centerline if deep)
        return abs(lat_left) * 3.0 + abs(depth_toward - 0.06) * 1.5
    if region == "left":
        return abs(lat_left - 0.34) * 2.0 + abs(depth_toward - 0.14) * 1.5
    if region == "right":
        return abs(lat_right - 0.34) * 2.0 + abs(depth_toward - 0.14) * 1.5
    if region == "robot_near":
        return abs(lat_left) * 1.2 + abs(depth_toward - 0.18) * 2.5
    if region == "far_context":
        return abs(depth_away - 0.20) * 2.0 + abs(abs(lat_left) - 0.50) * 0.8
    return abs(depth_toward - 0.12) + abs(lat_left) * 0.5


def _within_edge_margin(
    cand: SolvedObjectPlacement,
    table_bounds: TabletopBounds,
    min_edge_clearance_m: float,
) -> bool:
    eps = 1e-7
    return (
        cand.world_xy_min_m[0] - table_bounds.x_min >= min_edge_clearance_m - eps
        and table_bounds.x_max - cand.world_xy_max_m[0] >= min_edge_clearance_m - eps
        and cand.world_xy_min_m[1] - table_bounds.y_min >= min_edge_clearance_m - eps
        and table_bounds.y_max - cand.world_xy_max_m[1] >= min_edge_clearance_m - eps
    )


def _aabb_overlap(
    a_min: tuple[float, float],
    a_max: tuple[float, float],
    b_min: tuple[float, float],
    b_max: tuple[float, float],
    padding: float = 0.0,
) -> bool:
    return (
        a_min[0] - padding < b_max[0]
        and a_max[0] + padding > b_min[0]
        and a_min[1] - padding < b_max[1]
        and a_max[1] + padding > b_min[1]
    )


def _is_compatible_with_placed(
    *,
    candidate: SolvedObjectPlacement,
    placed: Mapping[str, SolvedObjectPlacement],
    relations: tuple[_ParsedRelation, ...],
    min_object_clearance_m: float,
    toward_robot_hat: tuple[float, float],
    forward_hat: tuple[float, float],
    left_hat: tuple[float, float],
    right_hat: tuple[float, float],
) -> bool:
    for other in placed.values():
        if _aabb_overlap(
            candidate.world_xy_min_m,
            candidate.world_xy_max_m,
            other.world_xy_min_m,
            other.world_xy_max_m,
            padding=min_object_clearance_m,
        ):
            return False
        for vol in other.world_clearance_volumes:
            if _aabb_overlap(
                candidate.world_xy_min_m,
                candidate.world_xy_max_m,
                vol.world_xy_min_m,
                vol.world_xy_max_m,
                padding=0.005,
            ):
                return False
        for vol in candidate.world_clearance_volumes:
            if _aabb_overlap(
                vol.world_xy_min_m,
                vol.world_xy_max_m,
                other.world_xy_min_m,
                other.world_xy_max_m,
                padding=0.005,
            ):
                return False

    temp_map = dict(placed)
    temp_map[candidate.object_id] = candidate
    for rel in relations:
        if rel.subject in temp_map and rel.reference in temp_map:
            if not _relation_holds(
                rel=rel,
                subj=temp_map[rel.subject],
                ref=temp_map[rel.reference],
                toward_robot_hat=toward_robot_hat,
                forward_hat=forward_hat,
                left_hat=left_hat,
                right_hat=right_hat,
            ):
                return False
    return True


def _projected_interval(
    xy_min: tuple[float, float],
    xy_max: tuple[float, float],
    axis_hat: tuple[float, float],
) -> tuple[float, float]:
    values = [
        x * axis_hat[0] + y * axis_hat[1]
        for x in (xy_min[0], xy_max[0])
        for y in (xy_min[1], xy_max[1])
    ]
    return min(values), max(values)


def _relation_holds(
    *,
    rel: _ParsedRelation,
    subj: SolvedObjectPlacement,
    ref: SolvedObjectPlacement,
    toward_robot_hat: tuple[float, float],
    forward_hat: tuple[float, float],
    left_hat: tuple[float, float],
    right_hat: tuple[float, float],
) -> bool:
    if rel.predicate == "near":
        dist = math.hypot(
            subj.pose.xyz[0] - ref.pose.xyz[0],
            subj.pose.xyz[1] - ref.pose.xyz[1],
        )
        return rel.max_center_distance_m is None or dist <= rel.max_center_distance_m + 1e-7

    axis_map = {
        "left_of": left_hat,
        "right_of": right_hat,
        "in_front_of": toward_robot_hat,
        "behind": forward_hat,
    }
    axis = axis_map[rel.predicate]
    s_min, _ = _projected_interval(subj.world_xy_min_m, subj.world_xy_max_m, axis)
    _, r_max = _projected_interval(ref.world_xy_min_m, ref.world_xy_max_m, axis)
    return s_min >= r_max + rel.min_gap_m - 1e-7


def _validate_global_tabletop_policy(
    *,
    chosen: Mapping[str, SolvedObjectPlacement],
    table_bounds: TabletopBounds,
    robot_xy: tuple[float, float],
    policy: TabletopPlacementPolicy,
) -> bool:
    object_bounds = {
        obj_id: TabletopBounds(
            x_min=item.world_xy_min_m[0],
            x_max=item.world_xy_max_m[0],
            y_min=item.world_xy_min_m[1],
            y_max=item.world_xy_max_m[1],
        )
        for obj_id, item in chosen.items()
    }
    exceptions = {
        obj_id: item.robot_side_exception
        for obj_id, item in chosen.items()
        if item.robot_side_exception is not None
    }
    report = evaluate_tabletop_placement(
        table_bounds=table_bounds,
        robot_xy=robot_xy,
        object_bounds=object_bounds,
        policy=policy,
        robot_side_exceptions=exceptions,
    )
    return report.overall_status == "pass"


def _diagnose_conflicts(
    *,
    placements: Mapping[str, SolvedObjectPlacement],
    objects: list[_ParsedObjectRequest],
    relations: tuple[_ParsedRelation, ...],
    table_bounds: TabletopBounds,
    robot_xy: tuple[float, float],
    policy: TabletopPlacementPolicy,
    min_object_clearance_m: float,
    toward_robot_hat: tuple[float, float],
    forward_hat: tuple[float, float],
    left_hat: tuple[float, float],
    right_hat: tuple[float, float],
) -> tuple[LayoutConflict, ...]:
    conflicts: list[LayoutConflict] = []

    for obj in objects:
        cand = placements[obj.object_id]
        if not _within_edge_margin(cand, table_bounds, policy.min_edge_clearance_m):
            conflicts.append(
                LayoutConflict(
                    conflict_type="table_edge_margin_violation",
                    objects=(obj.object_id,),
                    message=(
                        f"Object {obj.object_id!r} violates min_edge_clearance_m="
                        f"{policy.min_edge_clearance_m:.3f}m on table bounds."
                    ),
                    remediation_hint="Move fixed_xy_m inward or reduce object footprint.",
                )
            )

    ids = [obj.object_id for obj in objects]
    for i, id_a in enumerate(ids):
        a = placements[id_a]
        for id_b in ids[i + 1 :]:
            b = placements[id_b]
            if _aabb_overlap(
                a.world_xy_min_m,
                a.world_xy_max_m,
                b.world_xy_min_m,
                b.world_xy_max_m,
                padding=min_object_clearance_m,
            ):
                conflicts.append(
                    LayoutConflict(
                        conflict_type="static_aabb_overlap",
                        objects=(id_a, id_b),
                        message=f"Objects {id_a!r} and {id_b!r} violate min_object_clearance_m.",
                        remediation_hint=f"Separate {id_a!r} and {id_b!r} laterally or increase gap.",
                    )
                )
            for vol in a.world_clearance_volumes:
                if _aabb_overlap(
                    b.world_xy_min_m,
                    b.world_xy_max_m,
                    vol.world_xy_min_m,
                    vol.world_xy_max_m,
                    padding=0.005,
                ):
                    conflicts.append(
                        LayoutConflict(
                            conflict_type="kinematic_clearance_intrusion",
                            objects=(id_a, id_b),
                            joint=vol.joint,
                            clearance_id=vol.clearance_id,
                            message=(
                                f"Object {id_b!r} intrudes into {id_a!r} kinematic clearance "
                                f"volume {vol.clearance_id!r} (joint {vol.joint!r})."
                            ),
                            remediation_hint=(
                                f"Relocate {id_b!r} to left_of/right_of {id_a!r} outside "
                                f"the {vol.joint!r} travel corridor."
                            ),
                        )
                    )
            for vol in b.world_clearance_volumes:
                if _aabb_overlap(
                    a.world_xy_min_m,
                    a.world_xy_max_m,
                    vol.world_xy_min_m,
                    vol.world_xy_max_m,
                    padding=0.005,
                ):
                    conflicts.append(
                        LayoutConflict(
                            conflict_type="kinematic_clearance_intrusion",
                            objects=(id_b, id_a),
                            joint=vol.joint,
                            clearance_id=vol.clearance_id,
                            message=(
                                f"Object {id_a!r} intrudes into {id_b!r} kinematic clearance "
                                f"volume {vol.clearance_id!r} (joint {vol.joint!r})."
                            ),
                            remediation_hint=(
                                f"Relocate {id_a!r} to left_of/right_of {id_b!r} outside "
                                f"the {vol.joint!r} travel corridor."
                            ),
                        )
                    )

    for rel in relations:
        if not _relation_holds(
            rel=rel,
            subj=placements[rel.subject],
            ref=placements[rel.reference],
            toward_robot_hat=toward_robot_hat,
            forward_hat=forward_hat,
            left_hat=left_hat,
            right_hat=right_hat,
        ):
            conflicts.append(
                LayoutConflict(
                    conflict_type="relation_unsatisfied",
                    objects=(rel.subject, rel.reference),
                    message=(
                        f"Spatial relation {rel.subject!r} {rel.predicate} "
                        f"{rel.reference!r} could not be satisfied."
                    ),
                    remediation_hint="Relax min_gap_m or remove contradictory directional relations.",
                )
            )
    return tuple(conflicts)


def _non_empty_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelationalLayoutSpecError(f"{field} must be a non-empty string")
    return value


def _int_value(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RelationalLayoutSpecError(f"{field} must be an integer")
    return value


def _finite_float(value: object, field: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise RelationalLayoutSpecError(f"{field} must be a finite number")
    return float(value)


def _non_negative_float(value: object, field: str) -> float:
    num = _finite_float(value, field)
    if num < 0.0:
        raise RelationalLayoutSpecError(f"{field} must be non-negative")
    return num


def _pair_floats(value: object, field: str) -> tuple[float, float]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise RelationalLayoutSpecError(f"{field} must contain exactly 2 numbers")
    return (_finite_float(value[0], f"{field}[0]"), _finite_float(value[1], f"{field}[1]"))

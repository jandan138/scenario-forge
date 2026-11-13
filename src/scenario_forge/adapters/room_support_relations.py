"""Simulator-neutral room support-relation geometry and sidecar validation.

Producer scripts in Blender adapt scene objects to these lightweight value
types. Keeping the resting correction math and sidecar hash binding here keeps
the contract independently testable with zero Blender, USD, or simulator SDK
imports.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "room-support-relations-v1"
RELATION_KINDS = frozenset({"rests_on", "mounted_to", "stacked_on"})


@dataclass(frozen=True)
class Box3:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    def translated(self, translation: tuple[float, float, float]) -> Box3:
        return Box3(
            (
                self.minimum[0] + translation[0],
                self.minimum[1] + translation[1],
                self.minimum[2] + translation[2],
            ),
            (
                self.maximum[0] + translation[0],
                self.maximum[1] + translation[1],
                self.maximum[2] + translation[2],
            ),
        )


@dataclass(frozen=True)
class OrientedSupport:
    center_xy: tuple[float, float]
    size_xy: tuple[float, float]
    yaw_rad: float
    top_z: float


@dataclass(frozen=True)
class CorrectionResult:
    status: str
    before: Box3
    after: Box3
    translation: tuple[float, float, float]
    fully_supported: bool
    removal_reason: str | None = None


def _world_to_local_xy(
    point: tuple[float, float], support: OrientedSupport
) -> tuple[float, float]:
    dx = point[0] - support.center_xy[0]
    dy = point[1] - support.center_xy[1]
    cosine = math.cos(support.yaw_rad)
    sine = math.sin(support.yaw_rad)
    return cosine * dx + sine * dy, -sine * dx + cosine * dy


def _local_vector_to_world(
    vector: tuple[float, float], support: OrientedSupport
) -> tuple[float, float]:
    cosine = math.cos(support.yaw_rad)
    sine = math.sin(support.yaw_rad)
    return (
        cosine * vector[0] - sine * vector[1],
        sine * vector[0] + cosine * vector[1],
    )


def apply_resting_correction(
    item: Box3,
    support: OrientedSupport,
    *,
    margin_m: float,
    vertical_tolerance_m: float,
) -> CorrectionResult:
    """Return the minimum translation that fully supports an AABB footprint.

    The item AABB corners are conservatively projected into the support's local
    plane. An item larger than the usable plane or too far vertically from the
    declared plane is rejected instead of being moved onto unrelated furniture.
    """

    if margin_m < 0 or vertical_tolerance_m < 0:
        raise ValueError("support tolerances must be non-negative")
    corners = [
        _world_to_local_xy((x, y), support)
        for x in (item.minimum[0], item.maximum[0])
        for y in (item.minimum[1], item.maximum[1])
    ]
    local_min = (
        min(point[0] for point in corners),
        min(point[1] for point in corners),
    )
    local_max = (
        max(point[0] for point in corners),
        max(point[1] for point in corners),
    )
    half = (support.size_xy[0] / 2.0, support.size_xy[1] / 2.0)
    low = (-half[0] + margin_m, -half[1] + margin_m)
    high = (half[0] - margin_m, half[1] - margin_m)
    usable = (high[0] - low[0], high[1] - low[1])
    footprint = (local_max[0] - local_min[0], local_max[1] - local_min[1])
    zero = (0.0, 0.0, 0.0)
    if (
        usable[0] < -1e-9
        or usable[1] < -1e-9
        or footprint[0] > usable[0] + 1e-9
        or footprint[1] > usable[1] + 1e-9
    ):
        return CorrectionResult(
            status="removed",
            before=item,
            after=item,
            translation=zero,
            fully_supported=False,
            removal_reason="item_footprint_exceeds_support_margin",
        )
    vertical_delta = support.top_z - item.minimum[2]
    if abs(vertical_delta) > vertical_tolerance_m + 1e-9:
        return CorrectionResult(
            status="removed",
            before=item,
            after=item,
            translation=zero,
            fully_supported=False,
            removal_reason="item_outside_vertical_support_tolerance",
        )

    local_shift = [0.0, 0.0]
    for axis in (0, 1):
        if local_min[axis] < low[axis]:
            local_shift[axis] = low[axis] - local_min[axis]
        elif local_max[axis] > high[axis]:
            local_shift[axis] = high[axis] - local_max[axis]
    world_shift = _local_vector_to_world((local_shift[0], local_shift[1]), support)
    translation = (world_shift[0], world_shift[1], vertical_delta)
    after = item.translated(translation)
    changed = any(abs(value) > 1e-9 for value in translation)
    return CorrectionResult(
        status="corrected" if changed else "unchanged",
        before=item,
        after=after,
        translation=translation,
        fully_supported=True,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_support_sidecar(sidecar_path: Path, source_usd: Path) -> dict[str, Any]:
    """Validate producer review state and bind it to exact source USD bytes."""

    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("support sidecar root must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported support sidecar schema: {payload.get('schema_version')!r}"
        )
    source = payload.get("source_usd")
    if not isinstance(source, dict) or source.get("sha256") != _sha256(source_usd):
        raise ValueError("support sidecar source USD hash does not match")
    review = payload.get("review")
    if not isinstance(review, dict) or review.get("status") != "pass":
        raise ValueError("support sidecar engineering review is not passing")
    relations = payload.get("relations")
    if not isinstance(relations, list):
        raise ValueError("support sidecar relations must be a list")
    for index, relation in enumerate(relations):
        if not isinstance(relation, dict):
            raise ValueError(f"support relation {index} must be a mapping")
        if relation.get("relation_kind") not in RELATION_KINDS:
            raise ValueError(f"support relation {index} has an invalid relation kind")
        if relation.get("audit_status") not in {"pass", "removed"}:
            raise ValueError(f"support relation {index} is not resolved")
        if relation.get("audit_status") == "pass":
            if not str(relation.get("object_prim", "")).startswith("/Room/"):
                raise ValueError(f"support relation {index} has an invalid object prim")
            if not str(relation.get("support_prim", "")).startswith("/Room/"):
                raise ValueError(
                    f"support relation {index} has an invalid support prim"
                )
    return payload

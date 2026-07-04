from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isfinite
from pathlib import Path
from typing import Callable, Iterable


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


@dataclass(frozen=True)
class OfficialTabletopPlacement:
    apple_xyz: tuple[float, float, float]
    bowl_xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]
    scale_xyz: tuple[float, float, float]
    evidence: dict[str, object]


def derive_official_tabletop_placement(
    *,
    scene_path: str | Path,
    apple_path: str | Path,
    bowl_path: str | Path,
) -> OfficialTabletopPlacement:
    table_min, table_max = _combined_usd_bbox(
        scene_path,
        include_prim=lambda prim: "obj_table" in str(prim.GetPath()).lower()
        or prim.GetName().lower() == "table",
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


def _is_mesh_prim(prim: object) -> bool:
    from pxr import UsdGeom

    return bool(prim.IsA(UsdGeom.Mesh))


def _combined_usd_bbox(
    path: str | Path,
    *,
    include_prim: Callable[[object], bool],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    from pxr import Usd, UsdGeom

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

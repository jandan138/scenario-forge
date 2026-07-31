from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.generation.skills.skill_library import default_domain_pack_dir
from scenario_forge.generation.layout.tabletop_placement import TabletopPlacementPolicy


class LayoutConstraintError(ValueError):
    """Raised when layout constraints are missing or malformed."""


@dataclass(frozen=True)
class Workspace:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z: float


@dataclass(frozen=True)
class DifficultyProfile:
    name: str
    clutter_level: str
    target_distance_range_m: tuple[float, float]
    occlusion: str
    distractor_count: int


@dataclass(frozen=True)
class TabletopPlacementConstraints:
    policy: TabletopPlacementPolicy
    support_surface_prim_path: str
    support_height_tolerance_m: float
    exception_metadata_key: str


@dataclass(frozen=True)
class LayoutConstraints:
    workspace: Workspace
    difficulty_profiles: dict[str, DifficultyProfile]
    tabletop_placement: TabletopPlacementConstraints | None = None


def load_layout_constraints(domain_pack_dir: str | Path | None = None) -> LayoutConstraints:
    pack_dir = Path(domain_pack_dir) if domain_pack_dir is not None else default_domain_pack_dir()
    path = pack_dir / "layout_constraints.yaml"
    if not path.exists():
        raise LayoutConstraintError(f"Missing layout constraints file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LayoutConstraintError(f"Layout constraints file must be a mapping: {path}")
    schema_version = data.get("schema_version")
    if schema_version not in {"layout-constraints/v0.1", "layout-constraints/v0.2"}:
        raise LayoutConstraintError("Unsupported layout constraints schema_version")

    workspace = _workspace(data.get("workspace"))
    raw_profiles = data.get("difficulty_profiles")
    if not isinstance(raw_profiles, dict):
        raise LayoutConstraintError("Layout constraints field 'difficulty_profiles' must be a mapping")
    profiles: dict[str, DifficultyProfile] = {}
    for name, raw_profile in raw_profiles.items():
        if not isinstance(name, str) or not isinstance(raw_profile, dict):
            raise LayoutConstraintError("Each difficulty profile must be a mapping")
        profiles[name] = DifficultyProfile(
            name=name,
            clutter_level=_string(raw_profile, "clutter_level"),
            target_distance_range_m=_float_range(raw_profile, "target_distance_range_m"),
            occlusion=_string(raw_profile, "occlusion"),
            distractor_count=_int(raw_profile, "distractor_count"),
        )
    tabletop_placement = _tabletop_placement(data.get("tabletop_placement"))
    if schema_version == "layout-constraints/v0.2" and tabletop_placement is None:
        raise LayoutConstraintError(
            "layout-constraints/v0.2 requires tabletop_placement"
        )
    return LayoutConstraints(
        workspace=workspace,
        difficulty_profiles=profiles,
        tabletop_placement=tabletop_placement,
    )


def _workspace(value: Any) -> Workspace:
    if not isinstance(value, dict):
        raise LayoutConstraintError("Layout constraints field 'workspace' must be a mapping")
    x_min, x_max = _float_range(value, "x_range_m")
    y_min, y_max = _float_range(value, "y_range_m")
    z = value.get("z_m")
    if not isinstance(z, int | float):
        raise LayoutConstraintError("Layout constraints field 'workspace.z_m' must be numeric")
    return Workspace(x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max, z=float(z))


def _tabletop_placement(value: Any) -> TabletopPlacementConstraints | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise LayoutConstraintError(
            "Layout constraints field 'tabletop_placement' must be a mapping"
        )
    policy_id = _string(value, "policy_id")
    min_edge_clearance = value.get("min_edge_clearance_m")
    if not isinstance(min_edge_clearance, int | float) or min_edge_clearance < 0:
        raise LayoutConstraintError(
            "Layout constraints field 'tabletop_placement.min_edge_clearance_m' "
            "must be a non-negative number"
        )
    support_height_tolerance = value.get("support_height_tolerance_m")
    if (
        not isinstance(support_height_tolerance, int | float)
        or support_height_tolerance < 0
    ):
        raise LayoutConstraintError(
            "Layout constraints field 'tabletop_placement.support_height_tolerance_m' "
            "must be a non-negative number"
        )
    support_surface_prim_path = _string(value, "support_surface_prim_path")
    if not support_surface_prim_path.startswith("/"):
        raise LayoutConstraintError(
            "Layout constraints field 'tabletop_placement.support_surface_prim_path' "
            "must be absolute"
        )
    exception_metadata_key = _string(value, "exception_metadata_key")
    try:
        policy = TabletopPlacementPolicy(
            policy_id=policy_id,
            min_edge_clearance_m=float(min_edge_clearance),
        )
    except ValueError as exc:
        raise LayoutConstraintError(str(exc)) from exc
    return TabletopPlacementConstraints(
        policy=policy,
        support_surface_prim_path=support_surface_prim_path,
        support_height_tolerance_m=float(support_height_tolerance),
        exception_metadata_key=exception_metadata_key,
    )


def _float_range(data: dict[str, Any], key: str) -> tuple[float, float]:
    value = data.get(key)
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int | float) for item in value)
    ):
        raise LayoutConstraintError(f"Layout constraints field {key!r} must be a numeric range")
    return float(value[0]), float(value[1])


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise LayoutConstraintError(f"Layout constraints field {key!r} must be a string")
    return value


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise LayoutConstraintError(f"Layout constraints field {key!r} must be an integer")
    return value

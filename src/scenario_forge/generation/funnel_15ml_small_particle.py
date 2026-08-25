"""Dimension contract for a 15 mL-insertable small-particle funnel."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


CONTRACT_SCHEMA = "scenario_forge.funnel_15ml_small_particle_contract.v1"


def load_funnel_15ml_small_particle_contract(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("funnel contract must be a mapping")
    if payload.get("schema_version") != CONTRACT_SCHEMA:
        raise ValueError(f"unsupported funnel contract schema: {payload.get('schema_version')}")
    return dict(payload)


def _mapping(contract: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = contract.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return value


def _mm(block: Mapping[str, Any], key: str) -> float:
    value = block.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be a number")
    return float(value)


def check_funnel_15ml_small_particle_contract(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    geometry = _mapping(contract, "geometry")
    receiver = _mapping(contract, "receiver")
    liquid = _mapping(contract, "liquid")
    collision = _mapping(contract, "collision")
    constraints = _mapping(contract, "constraints")

    neck = _mm(geometry, "neck_diameter_mm")
    wall = _mm(geometry, "wall_thickness_mm")
    if neck <= 2.0 * wall:
        raise ValueError("neck_diameter_mm must leave a hollow throat")
    throat = neck - 2.0 * wall
    mouth = _mm(receiver, "mouth_inner_diameter_mm")
    margin = _mm(collision, "sdf_margin_mm")
    spacing = _mm(liquid, "particle_spacing_mm")
    rest = _mm(liquid, "rest_offset_mm")
    contact = _mm(liquid, "particle_contact_offset_mm")
    if rest >= contact:
        raise ValueError("rest_offset_mm must be smaller than particle_contact_offset_mm")

    radial = (mouth - neck) / 2.0
    radial_after = radial - 2.0 * margin
    min_radial = _mm(constraints, "min_radial_insertion_clearance_after_collision_mm")
    if radial_after < min_radial:
        raise ValueError(
            "stem does not fit the 15 mL mouth after collision margin "
            f"({radial_after:.3f} mm < {min_radial:.3f} mm)"
        )

    shrunk_throat = throat - 2.0 * margin
    widths = shrunk_throat / spacing
    min_widths = _mm(constraints, "min_particle_widths_in_throat")
    if widths < min_widths:
        raise ValueError(
            f"throat too narrow for small particles ({widths:.2f} < {min_widths:.2f} widths)"
        )

    return {
        "throat_inner_diameter_mm": throat,
        "radial_insertion_clearance_mm": radial,
        "radial_insertion_clearance_after_collision_mm": radial_after,
        "collision_shrunk_throat_mm": shrunk_throat,
        "particle_spacing_mm": spacing,
        "particle_widths_in_throat": widths,
        "task02_particle_diameter_mm": _mm(liquid, "task02_particle_diameter_mm"),
        "liquid": {
            "particle_spacing_mm": spacing,
            "particle_contact_offset_mm": contact,
            "rest_offset_mm": rest,
        },
    }


def to_ai3dgen_funnel_config(contract: Mapping[str, Any]) -> dict[str, Any]:
    geometry = _mapping(contract, "geometry")
    return {
        "name": str(contract.get("name", "funnel_15ml_small_particle")),
        "geometry": {
            "top_diameter_mm": _mm(geometry, "top_diameter_mm"),
            "neck_diameter_mm": _mm(geometry, "neck_diameter_mm"),
            "frustum_height_mm": _mm(geometry, "frustum_height_mm"),
            "stem_length_mm": _mm(geometry, "stem_length_mm"),
            "wall_thickness_mm": _mm(geometry, "wall_thickness_mm"),
            "bevel_mm": _mm(geometry, "bevel_mm"),
            "radial_segments": int(_mm(geometry, "radial_segments")),
        },
    }

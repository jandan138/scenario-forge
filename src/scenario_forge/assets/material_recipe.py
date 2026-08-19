"""Material recipe schema and rule matching for procedural asset families.

A material recipe maps semantic part names (the mesh parent Xform names used
across a procedural asset family) onto material specifications via an ordered
rule table. Two material kinds are supported:

- ``parametric``: flat PBR inputs (color, roughness, metallic, clearcoat).
  Used for powder coat, plastics, rubber, buttons, and needles.
- ``texture_set``: CC0 PBR texture files from a shared material library,
  copied next to the target USD on assignment and referenced with anchored
  relative paths.

This module is pure Python. Applying a recipe to a USD stage lives in
``scenario_forge.adapters.usd_material_assignment`` so that pure package
layers stay free of heavy SDK imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

MATERIAL_KINDS = ("parametric", "texture_set")
TEXTURE_CHANNELS = ("color", "normal", "roughness", "metallic")


class MaterialRecipeError(ValueError):
    """Raised when a material recipe fails validation."""


@dataclass(frozen=True)
class MaterialSpec:
    name: str
    kind: str
    diffuse_color: tuple[float, float, float] | None
    roughness: float | None
    metallic: float | None
    clearcoat: float | None
    textures: dict[str, str]
    source: dict[str, str]


@dataclass(frozen=True)
class AssignmentRule:
    pattern: str
    material: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class MaterialRecipe:
    name: str
    version: int
    default_material: str
    materials: dict[str, MaterialSpec]
    rules: tuple[AssignmentRule, ...]


def load_recipe(path: str | Path) -> MaterialRecipe:
    recipe_path = Path(path)
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise MaterialRecipeError(f"recipe must be a mapping: {recipe_path}")

    materials: dict[str, MaterialSpec] = {}
    for name, body in (raw.get("materials") or {}).items():
        body = body or {}
        kind = str(body.get("kind", ""))
        if kind not in MATERIAL_KINDS:
            raise MaterialRecipeError(
                f"material {name!r} has unknown kind {kind!r}; expected one of {MATERIAL_KINDS}"
            )
        textures = {str(k): str(v) for k, v in (body.get("textures") or {}).items()}
        if kind == "texture_set":
            unknown = sorted(set(textures) - set(TEXTURE_CHANNELS))
            if unknown:
                raise MaterialRecipeError(
                    f"material {name!r} uses unknown texture channels: {unknown}"
                )
            if "color" not in textures:
                raise MaterialRecipeError(f"texture_set material {name!r} requires a color texture")
        color = body.get("diffuse_color")
        materials[str(name)] = MaterialSpec(
            name=str(name),
            kind=kind,
            diffuse_color=tuple(float(c) for c in color) if color is not None else None,  # type: ignore[arg-type]
            roughness=_optional_float(body.get("roughness")),
            metallic=_optional_float(body.get("metallic")),
            clearcoat=_optional_float(body.get("clearcoat")),
            textures=textures,
            source={str(k): str(v) for k, v in (body.get("source") or {}).items()},
        )

    default_material = str(raw.get("default_material", ""))
    if default_material not in materials:
        raise MaterialRecipeError(
            f"default_material {default_material!r} is not declared in materials"
        )

    rules: list[AssignmentRule] = []
    for entry in raw.get("rules") or []:
        pattern = str(entry.get("pattern", ""))
        material = str(entry.get("material", ""))
        if material not in materials:
            raise MaterialRecipeError(
                f"rule pattern {pattern!r} references unknown material {material!r}"
            )
        rules.append(
            AssignmentRule(
                pattern=pattern,
                material=material,
                regex=re.compile(pattern, re.IGNORECASE),
            )
        )

    return MaterialRecipe(
        name=str(raw.get("name", recipe_path.stem)),
        version=int(raw.get("version", 1)),
        default_material=default_material,
        materials=materials,
        rules=tuple(rules),
    )


def matching_rule(recipe: MaterialRecipe, part_name: str) -> AssignmentRule | None:
    """Return the first rule matching a semantic part name, if any."""
    for rule in recipe.rules:
        if rule.regex.search(part_name):
            return rule
    return None


def match_material(recipe: MaterialRecipe, part_name: str) -> str:
    """Return the material name for a semantic part name (first rule wins)."""
    rule = matching_rule(recipe, part_name)
    return rule.material if rule is not None else recipe.default_material


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]

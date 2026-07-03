from __future__ import annotations

import os
from pathlib import Path
import re


def to_usd_identifier(value: str) -> str:
    """Return a conservative USDA identifier for a prim name."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned:
        return "unnamed"
    if cleaned[0].isdigit():
        return f"_{cleaned}"
    return cleaned


def quote_usda_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_usda_string_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(quote_usda_string(value) for value in values) + "]"


def format_usda_float_tuple(values: tuple[float, ...]) -> str:
    return "(" + ", ".join(_format_float(value) for value in values) + ")"


def scene_relative_reference(
    package_root: str | Path, scene_path: str | Path, package_relative_asset_path: str
) -> str:
    package_dir = Path(package_root).resolve()
    scene_file = Path(scene_path).resolve()
    asset_file = (package_dir / package_relative_asset_path).resolve()
    return os.path.relpath(asset_file, scene_file.parent).replace(os.sep, "/")


def _format_float(value: float) -> str:
    return f"{value:.12g}"

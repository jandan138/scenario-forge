#!/usr/bin/env python3
"""Derive the light powder-coat texture set used by the drying_box recipe.

ambientCG's painted-metal sets are all dark or heavily distressed, which reads
wrong for clean laboratory enclosures. This derives ``PowderCoatLight_SF``
from ambientCG Metal027 (CC0): the color map is re-leveled to a light neutral
gray while keeping the orange-peel luminance variation, the roughness map is
remapped to the powder-coat range, and the normal map is copied unchanged.

Requires pillow and numpy (dev extras). Source assets remain governed by the
material library manifest (CC0).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = (
    REPO_ROOT / "external_artifacts" / "incoming" / "drying_box" / "_material_library"
)

BASE_LEVEL = 0.66
LUMINANCE_AMPLITUDE = 0.35
ROUGHNESS_MIN = 0.38
ROUGHNESS_RANGE = 0.14


def build_powdercoat_textures(library_root: Path) -> list[Path]:
    src = library_root / "Metal027"
    dst = library_root / "PowderCoatLight_SF"
    dst.mkdir(parents=True, exist_ok=True)

    color = Image.open(src / "Metal027_1K-JPG_Color.jpg").convert("L")
    luminance = np.asarray(color, dtype=np.float32) / 255.0
    level = np.clip(
        BASE_LEVEL + (luminance - float(luminance.mean())) * LUMINANCE_AMPLITUDE, 0.0, 1.0
    )
    rgb = np.stack(
        [level * 0.985, level, np.clip(level * 1.02, 0.0, 1.0)], axis=-1
    )
    color_out = dst / "PowderCoatLight_SF_1K_Color.jpg"
    Image.fromarray((rgb * 255).astype(np.uint8)).save(color_out, quality=92)

    rough = np.asarray(
        Image.open(src / "Metal027_1K-JPG_Roughness.jpg").convert("L"), dtype=np.float32
    ) / 255.0
    rmin, rmax = float(rough.min()), float(rough.max())
    rough_out = ROUGHNESS_MIN + (rough - rmin) / max(rmax - rmin, 1e-6) * ROUGHNESS_RANGE
    roughness_out = dst / "PowderCoatLight_SF_1K_Roughness.jpg"
    Image.fromarray((np.clip(rough_out, 0, 1) * 255).astype(np.uint8)).save(
        roughness_out, quality=92
    )

    normal_out = dst / "PowderCoatLight_SF_1K_NormalGL.jpg"
    Image.open(src / "Metal027_1K-JPG_NormalGL.jpg").convert("RGB").save(
        normal_out, quality=95
    )
    return [color_out, roughness_out, normal_out]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, default=DEFAULT_LIBRARY)
    args = parser.parse_args(argv)
    for path in build_powdercoat_textures(args.library_root):
        print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

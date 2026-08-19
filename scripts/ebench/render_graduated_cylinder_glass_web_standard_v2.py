#!/usr/bin/env python3
"""Render the graduated-cylinder v1/v2 base-connector comparison in Isaac 4.1."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_RENDERER_PATH = (
    REPO_ROOT / "scripts/ebench/render_scientific_workbench_glass_web_standard.py"
)
PACKAGE_ROOT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_glass_web_standard_20260819/packages"
)
REFERENCE_PACKAGE = PACKAGE_ROOT / "graduated_cylinder_250ml_glass_web_standard_v1"
CANDIDATE_PACKAGE = PACKAGE_ROOT / "graduated_cylinder_250ml_glass_web_standard_v2"
OUTPUT = (
    REPO_ROOT
    / "outputs/scientific_workbench_glass_web_standard_v2_20260819/evidence/connector_comparison"
)
MANIFEST_SCHEMA = "scenario-forge-graduated-cylinder-connector-comparison/v1"
STANDARD = "glass-material-guide round base connector v2"
CLAIM_BOUNDARY = (
    "The reference is the admitted v1 cylinder whose round base connector retains "
    "the producer translucent-PP material. The candidate is v2 with that connector "
    "bound to the same webpage-standard ClearBorosilicate as the body and bases. "
    "Geometry, collision, physics, robot policy, and liquid transfer are outside "
    "this visual comparison."
)


def _load_base_renderer():
    spec = importlib.util.spec_from_file_location(
        "glass_web_standard_base_renderer", BASE_RENDERER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load renderer: {BASE_RENDERER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    renderer = _load_base_renderer()
    renderer.ASSETS = (
        {
            "id": "graduated_cylinder_250ml",
            "package_name": CANDIDATE_PACKAGE.name,
            "label": "250 mL 量筒（圆形连接座玻璃修复）",
            "prim": "/World/GraduatedCylinder250ml",
            "reference": REFERENCE_PACKAGE / "asset.usd",
            "candidate": CANDIDATE_PACKAGE / "asset.usd",
            "reference_overlay": False,
        },
    )
    renderer.OUTPUT = OUTPUT
    renderer.MANIFEST_SCHEMA = MANIFEST_SCHEMA
    renderer.STANDARD = STANDARD
    renderer.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    return renderer.main()


if __name__ == "__main__":
    raise SystemExit(main())

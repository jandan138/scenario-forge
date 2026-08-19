#!/usr/bin/env python3
"""Apply the drying_box material recipe to the family's USD assets.

For every ``drying_box/<asset>/usd/<asset>.usd`` this writes a sibling
``<asset>_textured.usd`` plus a shared ``textures/`` directory holding the
copied CC0 texture files, and records per-asset assignment reports under
``drying_box/_material_reports/``. Original USD files are never modified.

Requires OpenUSD (``pxr``) at runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scenario_forge.adapters.usd_material_assignment import assign_materials
from scenario_forge.assets.material_recipe import load_recipe

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAMILY_ROOT = REPO_ROOT / "external_artifacts" / "incoming" / "drying_box"
DEFAULT_RECIPE = REPO_ROOT / "configs" / "material_recipes" / "drying_box_v1.yaml"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-root", type=Path, default=DEFAULT_FAMILY_ROOT)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument(
        "--library-root",
        type=Path,
        default=None,
        help="Texture library root (default: <family-root>/_material_library)",
    )
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        help="Restrict to one asset directory name; may be repeated",
    )
    args = parser.parse_args(argv)

    family_root = args.family_root
    library_root = args.library_root or family_root / "_material_library"
    recipe = load_recipe(args.recipe)

    usd_paths = sorted(family_root.glob("*/usd/*.usd"))
    if args.asset:
        wanted = set(args.asset)
        usd_paths = [p for p in usd_paths if p.parent.parent.name in wanted]
    usd_paths = [p for p in usd_paths if not p.stem.endswith("_textured")]
    if not usd_paths:
        print("no USD assets matched")
        return 1

    report_dir = family_root / "_material_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for usd_path in usd_paths:
        asset_name = usd_path.parent.parent.name
        out_path = usd_path.with_name(f"{usd_path.stem}_textured.usd")
        try:
            report = assign_materials(usd_path, recipe, library_root, out_path)
        except Exception as exc:  # noqa: BLE001 - batch continues, failure is reported
            failures += 1
            print(f"[FAIL] {asset_name}: {exc}")
            continue
        report_path = report_dir / f"{asset_name}.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            f"[ok] {asset_name}: {len(report['assigned'])} meshes, "
            f"{len(report['materials_created'])} materials, "
            f"unmatched={len(report['unmatched'])} -> {out_path.name}"
        )
        for entry in report["unmatched"]:
            print(f"     [default-fallback] {entry['part']}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

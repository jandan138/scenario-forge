#!/usr/bin/env python3
"""Generate the golden scientific-workbench bimanual-pour package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the golden conical-flask-to-graduated-cylinder task and its "
            "GenManip collected-package export."
        )
    )
    parser.add_argument("--source-usd", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--source-uri",
        default="LabUtopia:lab_001_localized",
        help="Portable provenance identifier; do not pass a machine-local absolute path.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Generate deterministic static artifacts without starting Isaac Sim.",
    )
    parser.add_argument(
        "--isaac-python",
        type=Path,
        help="Isaac/GenManip Python executable; required unless --static-only is used.",
    )
    parser.add_argument(
        "--genmanip-root",
        type=Path,
        help="GenManip checkout root; required unless --static-only is used.",
    )
    parser.add_argument("--renderer-script", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.static_only:
        if args.isaac_python is None:
            parser.error("--isaac-python is required unless --static-only is used")
        if args.genmanip_root is None:
            parser.error("--genmanip-root is required unless --static-only is used")
    raw_spec = yaml.safe_load(args.spec.read_text(encoding="utf-8"))
    if not isinstance(raw_spec, dict):
        raise ValueError(f"Scenario spec must be a mapping: {args.spec}")
    spec = ScenarioSpec.from_mapping(raw_spec)
    source = LocalUSDAssetSource(
        asset_id=spec.scene.asset_id,
        source_usd=args.source_usd,
        role="environment",
        license="CC-BY-NC-4.0",
        source_uri=args.source_uri,
        attribution=(
            "LabUtopia data assets: CC BY-NC 4.0",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
        exclude_relative_paths=("_reports",),
    )
    package = compile_scenario_package(spec, {source.asset_id: source}, args.out)
    export = export_genmanip_collected_package(package.package_root)
    if not args.static_only:
        run_genmanip_initial_preview(
            export.output_dir,
            args.isaac_python,
            args.renderer_script,
            args.genmanip_root,
            timeout_seconds=args.preview_timeout,
        )
    print(f"Portable package: {package.package_root}")
    print(f"GenManip collected package: {export.output_dir}")
    print(
        "Initial-scene preview: "
        + ("skipped (--static-only)" if args.static_only else "validated")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

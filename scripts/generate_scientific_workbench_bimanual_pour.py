#!/usr/bin/env python3
"""Generate the golden scientific-workbench bimanual-pour package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import yaml

from scenario_forge.adapters.convert_asset import load_convert_asset_package_handoff
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
SCENE1_ENVIRONMENT_ASSET_ID = "scientific_workbench_scene1_hard_environment"
# ConvertAsset must extract this parent-layer scope so the package retains the
# paper scene's meters-per-unit, placement, and rotation for the lab_015 payload.
SCENE1_ENVIRONMENT_SCOPE = "/World/lab_015"
EBENCH_TABLE_ASSET_ID = "scientific_workbench_ebench_table"
EBENCH_TABLE_SCOPE = "/World/table"
SOURCE_VESSEL_ASSET_ID = "scientific_workbench_conical_bottle03_dynamic"
SOURCE_VESSEL_SCOPE = "/World/conical_bottle03"
TARGET_VESSEL_ASSET_ID = "scientific_workbench_graduated_cylinder_03_dynamic"
TARGET_VESSEL_SCOPE = "/World/graduated_cylinder_03"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the Scene1_hard laboratory bimanual-pour task and its "
            "GenManip collected-package export."
        )
    )
    parser.add_argument("--scene1-source-usd", type=Path, required=True)
    parser.add_argument("--table-source-usd", type=Path, required=True)
    parser.add_argument("--vessel-source-usd", type=Path, required=True)
    parser.add_argument("--scene1-environment-package", type=Path, required=True)
    parser.add_argument("--scene1-environment-manifest", type=Path, required=True)
    parser.add_argument("--table-package", type=Path, required=True)
    parser.add_argument("--table-manifest", type=Path, required=True)
    parser.add_argument("--source-vessel-package", type=Path, required=True)
    parser.add_argument("--source-vessel-manifest", type=Path, required=True)
    parser.add_argument("--target-vessel-package", type=Path, required=True)
    parser.add_argument("--target-vessel-manifest", type=Path, required=True)
    parser.add_argument(
        "--scene1-environment-revision",
        required=True,
        help=(
            "ConvertAsset revision for the source-bound Scene1_hard room delivery."
        ),
    )
    parser.add_argument(
        "--table-revision",
        required=True,
        help="ConvertAsset revision for the source-bound EBench table delivery.",
    )
    parser.add_argument(
        "--source-vessel-revision",
        required=True,
        help="ConvertAsset producer revision for the source-vessel delivery.",
    )
    parser.add_argument(
        "--target-vessel-revision",
        required=True,
        help="ConvertAsset producer revision for the target-vessel delivery.",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
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
    if spec.scene.asset_id != SCENE1_ENVIRONMENT_ASSET_ID:
        raise ValueError(
            "Golden spec must declare the source-bound Scene1_hard environment"
        )
    if spec.scene.overlay_asset_ids:
        raise ValueError("Golden Scene1_hard spec must not declare scene overlays")
    scene1_environment_handoff = load_convert_asset_package_handoff(
        args.scene1_environment_package,
        args.scene1_environment_manifest,
        args.scene1_source_usd,
        expected_scope_prims=(SCENE1_ENVIRONMENT_SCOPE,),
        producer_revision=args.scene1_environment_revision,
        usage="visual_static_environment",
    )
    table_handoff = load_convert_asset_package_handoff(
        args.table_package,
        args.table_manifest,
        args.table_source_usd,
        expected_scope_prims=(EBENCH_TABLE_SCOPE,),
        producer_revision=args.table_revision,
        usage="visual_static_object",
    )
    source_vessel_handoff = load_convert_asset_package_handoff(
        args.source_vessel_package,
        args.source_vessel_manifest,
        args.vessel_source_usd,
        expected_scope_prims=(SOURCE_VESSEL_SCOPE,),
        producer_revision=args.source_vessel_revision,
        usage="rigid_object",
    )
    target_vessel_handoff = load_convert_asset_package_handoff(
        args.target_vessel_package,
        args.target_vessel_manifest,
        args.vessel_source_usd,
        expected_scope_prims=(TARGET_VESSEL_SCOPE,),
        producer_revision=args.target_vessel_revision,
        usage="rigid_object",
    )
    object_asset_ids = {item.object_id: item.asset_id for item in spec.objects}
    if object_asset_ids.get("table") != EBENCH_TABLE_ASSET_ID:
        raise ValueError("Golden table must use the source-bound EBench table package")
    if object_asset_ids.get("obj_conical_bottle03") != SOURCE_VESSEL_ASSET_ID:
        raise ValueError("Golden source container must use its qualified object package")
    if object_asset_ids.get("obj_graduated_cylinder_03") != TARGET_VESSEL_ASSET_ID:
        raise ValueError("Golden target container must use its qualified object package")
    scene1_environment = scene1_environment_handoff.to_local_usd_asset_source(
        asset_id=SCENE1_ENVIRONMENT_ASSET_ID,
        license="CC-BY-NC-4.0",
        attribution=(
            "LabUtopia data assets: CC BY-NC 4.0",
            "Scene1_hard room scope normalized by ConvertAsset",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
        exclude_relative_paths=("_reports", "evidence"),
    )
    table = table_handoff.to_local_usd_asset_source(
        asset_id=EBENCH_TABLE_ASSET_ID,
        license="CC-BY-NC-4.0",
        attribution=(
            "LabUtopia data assets: CC BY-NC 4.0",
            "EBench task-table scope normalized by ConvertAsset",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
        exclude_relative_paths=("evidence",),
    )
    source_vessel = source_vessel_handoff.to_local_usd_asset_source(
        asset_id=SOURCE_VESSEL_ASSET_ID,
        license="CC-BY-NC-4.0",
        attribution=(
            "LabUtopia data assets: CC BY-NC 4.0",
            "Interaction-qualified package normalized by ConvertAsset",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
    )
    target_vessel = target_vessel_handoff.to_local_usd_asset_source(
        asset_id=TARGET_VESSEL_ASSET_ID,
        license="CC-BY-NC-4.0",
        attribution=(
            "LabUtopia data assets: CC BY-NC 4.0",
            "Interaction-qualified package normalized by ConvertAsset",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
    )
    package = compile_scenario_package(
        spec,
        {
            scene1_environment.asset_id: scene1_environment,
            table.asset_id: table,
            source_vessel.asset_id: source_vessel,
            target_vessel.asset_id: target_vessel,
        },
        args.out,
    )
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

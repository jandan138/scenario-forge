#!/usr/bin/env python3
"""Compile the admitted scientific-workbench asset-expansion task packages."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.ik_preflight import write_provisional_ik_preflight_request
from scenario_forge.adapters.ebench.preview import (
    run_genmanip_initial_preview,
    write_genmanip_preview_request,
)
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_SPECS = {
    4: REPO_ROOT / "examples/scientific_workbench/asset_expansion/insert_stir_bar/scenario.yaml",
    7: REPO_ROOT / "examples/scientific_workbench/asset_expansion/glass_rod_stir/scenario.yaml",
    8: REPO_ROOT / "examples/scientific_workbench/asset_expansion/tighten_centrifuge_tube_cap/scenario.yaml",
    14: REPO_ROOT / "examples/scientific_workbench/asset_expansion/funnel_pour_to_centrifuge_tube/scenario.yaml",
    15: REPO_ROOT / "examples/scientific_workbench/asset_expansion/solid_sample_weighing_layout/scenario.yaml",
}
DEFAULT_BINDINGS = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml"
)
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
DEFAULT_FIT_REPORT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_asset_library_20260810/evidence/"
    "tube_rack_k125_50ml_fit/report.json"
)
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path(
    "/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src"
)

BACKGROUND_VARIANTS = (
    {
        "id": "example4",
        "asset_id": "scientific_environment_code_room_example4_v2",
        "wxyz": [0.0, 0.0, 0.0, 1.0],
        "inactive_prim_paths": [],
    },
    {
        "id": "teaching_research",
        "asset_id": "scientific_environment_code_room_teaching_research_v2",
        "wxyz": [0.0, 0.0, 0.0, 1.0],
        "inactive_prim_paths": [],
    },
    {
        "id": "modern_wet_chemistry",
        "asset_id": "scientific_environment_code_room_wet_chemistry_v2",
        "wxyz": [0.0, 0.0, 0.0, 1.0],
        "inactive_prim_paths": [],
    },
    {
        "id": "bioclean",
        "asset_id": "scientific_environment_code_room_bioclean_v2",
        "wxyz": [-0.7071067811865475, 0.0, 0.0, 0.7071067811865476],
        "inactive_prim_paths": [],
    },
    {
        "id": "analytical_instrumentation",
        "asset_id": "scientific_environment_code_room_analytical_instrumentation_v2",
        "wxyz": [-0.7071067811865475, 0.0, 0.0, 0.7071067811865476],
        "inactive_prim_paths": [
            "/World/Lab_Stool_Left",
            "/World/Lab_Stool_Middle",
            "/World/Lab_Stool_Right",
        ],
    },
)

TASK_RELEASE = {
    4: ("prototype", 0.55, ("vessel closure asset",)),
    7: ("canonical_candidate", 1.0, ()),
    8: ("canonical_candidate", 0.70, ("threaded closure interaction",)),
    14: ("prototype", 0.65, ("liquid flow and contained-volume metrics",)),
    15: (
        "prototype",
        0.0,
        (
            "interactive tare button",
            "dynamic micro-spatula",
            "reagent bottle and solid sample",
        ),
    ),
}


@dataclass(frozen=True)
class GenerationPlan:
    task_number: int
    background_id: str
    release_status: str
    score_ceiling: float
    missing_capabilities: tuple[str, ...]
    scenario: dict[str, Any]


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"scenario spec must be a mapping: {path}")
    return value


def _with_background(
    raw_scenario: Mapping[str, Any],
    background: Mapping[str, Any],
) -> dict[str, Any]:
    scenario = deepcopy(dict(raw_scenario))
    scene = deepcopy(dict(scenario["scene"]))
    scene["asset_id"] = str(background["asset_id"])
    pose = deepcopy(dict(scene.get("pose", {})))
    pose["xyz"] = [0.2456705, -0.0069055, 0.0]
    pose["wxyz"] = list(background["wxyz"])
    pose["scale_xyz"] = [1.0, 1.0, 1.0]
    scene["pose"] = pose
    inactive = list(background.get("inactive_prim_paths", []))
    if inactive:
        scene["inactive_prim_paths"] = inactive
    else:
        scene.pop("inactive_prim_paths", None)
    scenario["scene"] = scene
    if background["id"] != "example4":
        scenario["scenario_id"] = (
            str(scenario["scenario_id"]) + "__background_" + str(background["id"])
        )
    return scenario


def load_generation_plans() -> list[GenerationPlan]:
    plans: list[GenerationPlan] = []
    task7 = _load_yaml_mapping(TASK_SPECS[7])
    release, ceiling, missing = TASK_RELEASE[7]
    for background in BACKGROUND_VARIANTS:
        plans.append(
            GenerationPlan(
                task_number=7,
                background_id=str(background["id"]),
                release_status=release,
                score_ceiling=ceiling,
                missing_capabilities=missing,
                scenario=_with_background(task7, background),
            )
        )
    default_background = BACKGROUND_VARIANTS[0]
    for task_number in (4, 8, 14, 15):
        release, ceiling, missing = TASK_RELEASE[task_number]
        plans.append(
            GenerationPlan(
                task_number=task_number,
                background_id="example4",
                release_status=release,
                score_ceiling=ceiling,
                missing_capabilities=missing,
                scenario=_with_background(
                    _load_yaml_mapping(TASK_SPECS[task_number]),
                    default_background,
                ),
            )
        )
    return plans


def _materialize_authoritative_frames(
    scenario: Mapping[str, Any],
    sources: Mapping[str, LocalUSDAssetSource],
) -> dict[str, Any]:
    result = deepcopy(dict(scenario))
    objects = result.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scenario objects must be a list")
    for raw_object in objects:
        if not isinstance(raw_object, dict):
            raise ValueError("scenario object must be a mapping")
        asset_id = raw_object.get("asset_id")
        source = sources.get(asset_id) if isinstance(asset_id, str) else None
        if source is None or source.upstream_package is None:
            continue
        metadata = source.upstream_package.metadata
        contract = metadata.get("interaction_contract")
        requested = raw_object.get("named_frames")
        if not isinstance(contract, Mapping) or not isinstance(requested, Mapping):
            continue
        authoritative = contract.get("named_frames")
        if not isinstance(authoritative, Mapping):
            continue
        materialized: dict[str, Any] = {}
        for frame_id in requested:
            frame = authoritative.get(frame_id)
            if not isinstance(frame, Mapping):
                raise ValueError(
                    f"asset {asset_id} does not author requested frame {frame_id}"
                )
            xyz = frame.get("translation_body_local_usd")
            wxyz = frame.get("rotation_body_local_wxyz")
            if not isinstance(xyz, list) or not isinstance(wxyz, list):
                raise ValueError(f"asset {asset_id}.{frame_id} frame is not body-local")
            materialized[str(frame_id)] = {"xyz": list(xyz), "wxyz": list(wxyz)}
        raw_object["named_frames"] = materialized
    return result


def _validate_fit_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("status") != "pass":
        raise ValueError("tube-rack insertion qualification must be a passing report")
    gates = value.get("gates")
    if not isinstance(gates, Mapping) or any(
        not isinstance(item, Mapping) or item.get("status") != "pass"
        for item in gates.values()
    ):
        raise ValueError("tube-rack insertion qualification gates must all pass")
    return {
        "path": str(path.resolve()),
        "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(),
        "status": "pass",
        "claim_boundary": value.get("claim_boundary"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--fit-report", type=Path, default=DEFAULT_FIT_REPORT)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--isaac-python", type=Path, default=DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--genmanip-root", type=Path, default=DEFAULT_GENMANIP_ROOT)
    parser.add_argument("--renderer-script", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--curobo-src", type=Path, default=DEFAULT_CUROBO_SRC)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = resolve_scenario_source_bindings(args.bindings)
    fit_evidence = _validate_fit_report(args.fit_report)
    records: list[dict[str, Any]] = []
    for plan in load_generation_plans():
        materialized = _materialize_authoritative_frames(plan.scenario, sources)
        spec = ScenarioSpec.from_mapping(materialized)
        package_root = args.out / "packages" / spec.scenario_id
        package = compile_scenario_package(spec, sources, package_root)
        portable = validate_package(package.package_root)
        if not portable.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(portable.messages))
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        export = export_genmanip_collected_package(package.package_root)
        write_genmanip_preview_request(export.output_dir, resolution=(1920, 1080))
        ik_request = write_provisional_ik_preflight_request(package.package_root)
        vr = export_vr_teleop_package(
            package.package_root,
            package.package_root / "adapters" / "vr_teleop",
            task_id=spec.scenario_id,
        )
        preview_status = "not_run"
        if not args.static_only:
            run_genmanip_initial_preview(
                export.output_dir,
                args.isaac_python,
                args.renderer_script,
                args.genmanip_root,
                timeout_seconds=args.preview_timeout,
                runtime_python_paths=(args.curobo_src,),
            )
            preview_status = "pass"
        records.append(
            {
                "scenario_id": spec.scenario_id,
                "task_number": plan.task_number,
                "background_id": plan.background_id,
                "release_status": plan.release_status,
                "score_ceiling": plan.score_ceiling,
                "missing_capabilities": list(plan.missing_capabilities),
                "package_root": str(package.package_root.resolve()),
                "ebench_root": str(export.output_dir.resolve()),
                "vr_root": str(vr.output_dir.resolve()),
                "portable_closure": "pass",
                "tabletop_placement": tabletop.overall_status,
                "provisional_ik_request": str(ik_request.resolve()),
                "initial_scene_preview": preview_status,
            }
        )
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-asset-expansion/v0.1",
        "status": "static_complete" if args.static_only else "runtime_preview_complete",
        "tube_rack_fit_qualification": fit_evidence,
        "packages": records,
        "claim_boundary": (
            "Package, adapter, placement, and initial-scene evidence only. Score ceilings "
            "describe active portable rubric coverage; they are not policy success rates."
        ),
    }
    (args.out / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    for record in records:
        print(f"{record['scenario_id']}: {record['package_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

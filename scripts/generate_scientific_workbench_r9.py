#!/usr/bin/env python3
"""Compile rich-tabletop r9 bases for scientific tasks 2, 7, and 8."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

import scripts.generate_scientific_workbench_r7 as r7
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import (
    run_genmanip_initial_preview,
    write_genmanip_preview_request,
)
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.dressing import apply_dressing_preset, load_dressing_presets
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_BINDINGS = r7.DEFAULT_BINDINGS
DEFAULT_CONTEXT_BINDINGS = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_r9_context_20260816.yaml"
)
DEFAULT_PRESETS = REPO_ROOT / "configs/dressing_presets/scientific_workbench_r9.yaml"
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_tasks_02_07_08_r9_20260816"
PRESETS = {
    "example4": "example4-r9",
    "teaching_research": "teaching-research-r9",
    "modern_wet_chemistry": "modern-wet-chemistry-r9",
    "bioclean": "bioclean-r9",
    "analytical_instrumentation": "analytical-instrumentation-r9",
}
R9_STABILITY_STEPS = 960


def _write_r9_preview_request(collected_root: Path) -> Path:
    request_path = write_genmanip_preview_request(collected_root, resolution=(1920, 1080))
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    request["zero_action_warmup_steps"] = R9_STABILITY_STEPS
    request["claim_boundary"] = (
        "r9 initial-scene load, reset, 960 zero-action physics steps, and multiview "
        "visual evidence only; not Task 07/08 robot or benchmark success."
    )
    request_path.write_text(
        yaml.safe_dump(request, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return request_path


@dataclass(frozen=True)
class R9Plan:
    task_number: int
    background_id: str
    release_status: str
    score_ceiling: float
    missing_capabilities: tuple[str, ...]
    scenario: dict[str, Any]


def load_r9_plans(presets_path: Path = DEFAULT_PRESETS) -> list[R9Plan]:
    presets = load_dressing_presets(presets_path)
    plans: list[R9Plan] = []
    for old in r7.load_r7_plans():
        preset_id = PRESETS[old.background_id]
        scenario = apply_dressing_preset(
            old.scenario,
            preset_id=preset_id,
            preset=presets[preset_id],
        )
        scenario["scenario_id"] = scenario["scenario_id"].replace(
            "scientific_workbench_r7_", "scientific_workbench_r9_", 1
        )
        metadata = scenario["metadata"]
        metadata["release"] = "r9"
        metadata["ik_claim"] = "No new Task 07/08 robot-success claim is made in r9."
        metadata["dressing_release"] = "r9"
        metadata["dressing_policy"] = "fixed_room_semantic_far_side_wings_not_scored"
        for item in scenario["objects"]:
            item_metadata = item.get("metadata")
            if (
                isinstance(item_metadata, dict)
                and item_metadata.get("dressing_preset_id") == preset_id
            ):
                item_metadata["dressing_release"] = "r9"
            if old.task_number == 8 and item.get("id") in {
                "context_closed_tube_s1",
                "context_closed_tube_s6",
            }:
                item["asset_id"] = "scientific_workbench_r9_context_centrifuge_tube_15ml_body"
                item["source_prim_path"] = "/World/CentrifugeTube15mlBody"
                item_metadata = item.setdefault("metadata", {})
                item_metadata["r9_context_correction"] = (
                    "body_only_tube_avoids_closed_context_child_separation"
                )
        plans.append(
            R9Plan(
                old.task_number,
                old.background_id,
                "physics_qualified_candidate" if old.task_number == 2 else old.release_status,
                old.score_ceiling,
                old.missing_capabilities,
                scenario,
            )
        )
    return plans


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-bindings", type=Path, default=DEFAULT_BASE_BINDINGS)
    parser.add_argument("--context-bindings", type=Path, default=DEFAULT_CONTEXT_BINDINGS)
    parser.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    parser.add_argument("--fit-report", type=Path, default=r7.DEFAULT_FIT_REPORT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--isaac-python", type=Path, default=r7.DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--genmanip-root", type=Path, default=r7.DEFAULT_GENMANIP_ROOT)
    parser.add_argument("--renderer-script", type=Path, default=r7.DEFAULT_RENDERER)
    parser.add_argument("--curobo-src", type=Path, default=r7.DEFAULT_CUROBO_SRC)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = resolve_scenario_source_bindings(args.base_bindings)
    context_sources = resolve_scenario_source_bindings(args.context_bindings)
    overlap = set(sources) & set(context_sources)
    if overlap:
        raise ValueError(f"duplicate source bindings: {sorted(overlap)}")
    sources.update(context_sources)
    fit = r7._fit_evidence(args.fit_report)
    records: list[dict[str, Any]] = []
    for plan in load_r9_plans(args.presets):
        populated = r7._materialize_rack_population(plan.scenario, sources)
        spec = ScenarioSpec.from_mapping(r7._materialize_frames(populated, sources))
        root = args.out / "rich_bases" / spec.scenario_id
        package = compile_scenario_package(spec, sources, root)
        closure = validate_package(package.package_root)
        if not closure.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        export = export_genmanip_collected_package(package.package_root)
        _write_r9_preview_request(export.output_dir)
        vr = export_vr_teleop_package(
            package.package_root,
            package.package_root / "adapters/vr_teleop",
            task_id=spec.scenario_id,
        )
        preview = "not_run"
        if not args.static_only:
            run_genmanip_initial_preview(
                export.output_dir,
                args.isaac_python,
                args.renderer_script,
                args.genmanip_root,
                timeout_seconds=args.preview_timeout,
                runtime_python_paths=(args.curobo_src,),
            )
            preview = "pass"
        records.append(
            {
                "scenario_id": spec.scenario_id,
                "task_number": plan.task_number,
                "background_id": plan.background_id,
                "release_status": plan.release_status,
                "score_ceiling": plan.score_ceiling,
                "package_root": str(root.resolve()),
                "ebench_root": str(export.output_dir.resolve()),
                "vr_root": str(vr.output_dir.resolve()),
                "portable_closure": "pass",
                "tabletop_placement": tabletop.overall_status,
                "initial_scene_preview": preview,
            }
        )
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r9/v0.1",
        "status": "static_complete" if args.static_only else "runtime_preview_complete",
        "release": "r9",
        "package_count": 7,
        "tube_rack_fit_qualification": fit,
        "packages": records,
        "claim_boundary": "Rich-base package, adapter, placement, and preview evidence. Task 02 liquid and robot oracle are finalized separately; Task 07/08 gain no robot-success claim.",
    }
    (args.out / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

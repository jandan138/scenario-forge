#!/usr/bin/env python3
"""Run out-of-domain scene layout, Critic repair, package compilation, and preview gates.

Pure Scenario Forge orchestration script: invokes simulator rendering behind a subprocess
boundary without importing simulator SDKs into Scenario Forge package layers.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.adapters.ebench import export_genmanip_collected_package  # noqa: E402
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview  # noqa: E402
from scenario_forge.assets.lock import check_asset_lock  # noqa: E402
from scenario_forge.generation.layout.constraints import load_layout_constraints  # noqa: E402
from scenario_forge.generation.layout.relational_solver import (  # noqa: E402
    LayoutConflict,
    solve_relational_tabletop_layout,
)
from scenario_forge.generation.package_compiler import compile_scenario_package  # noqa: E402
from scenario_forge.generation.source_resolver import (  # noqa: E402
    resolve_scenario_source_bindings,
)
from scenario_forge.generation.spec_composer import (  # noqa: E402
    compose_scenario_spec_from_solved_layout,
)
from scenario_forge.package import validate_package  # noqa: E402


DEFAULT_TASK_CONFIGS = (
    Path("configs/out_of_domain_tasks/specialty_coffee_bar_creatista_prep.yaml"),
    Path("configs/out_of_domain_tasks/electronics_qa_ingun_probe_lock.yaml"),
    Path("configs/out_of_domain_tasks/modern_office_brother_calibrate.yaml"),
)
DEFAULT_OUT_ROOT = Path("external_artifacts/out_of_domain_factory_20261112")
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path("/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile, lock, export, and preview out-of-domain tasks."
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        type=Path,
        default=list(DEFAULT_TASK_CONFIGS),
        help="Task bundle YAML paths.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUT_ROOT,
        help="Output root under external_artifacts/.",
    )
    parser.add_argument(
        "--isaac-python",
        type=Path,
        default=DEFAULT_ISAAC_PYTHON,
        help="Isaac Sim 4.1 + GenManip Python interpreter.",
    )
    parser.add_argument(
        "--genmanip-root",
        type=Path,
        default=DEFAULT_GENMANIP_ROOT,
        help="GenManip checkout directory.",
    )
    parser.add_argument(
        "--curobo-src",
        type=Path,
        default=DEFAULT_CUROBO_SRC,
        help="Optional CuRobo Python source directory added to preview PYTHONPATH.",
    )
    parser.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Skip 7-view Isaac/GenManip preview rendering.",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Render 7-view previews on existing compiled/collected packages without overwriting them.",
    )
    return parser


def _repair_layout_from_conflicts(
    layout_request: Mapping[str, Any],
    conflicts: Sequence[LayoutConflict],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Deterministically repair sweep-corridor intrusions flagged by the layout critic."""

    repaired = copy.deepcopy(dict(layout_request))
    actions: list[dict[str, Any]] = []
    objects = repaired.get("objects", [])
    relations = repaired.get("relations", [])

    for conflict in conflicts:
        if (
            conflict.conflict_type != "kinematic_clearance_intrusion"
            or len(conflict.objects) < 2
        ):
            continue
        appliance_id, intruder_id = conflict.objects[0], conflict.objects[1]
        for obj in objects:
            if isinstance(obj, dict) and obj.get("id") == intruder_id:
                removed_fixed = obj.pop("fixed_xy_m", None)
                previous_region = obj.get("region")
                obj["region"] = "left"
                actions.append(
                    {
                        "action": "relocate_out_of_kinematic_corridor",
                        "intruder_object": intruder_id,
                        "appliance_object": appliance_id,
                        "joint": conflict.joint,
                        "clearance_id": conflict.clearance_id,
                        "removed_fixed_xy_m": removed_fixed,
                        "previous_region": previous_region,
                        "new_region": "left",
                        "new_relation": {
                            "subject": intruder_id,
                            "predicate": "left_of",
                            "reference": appliance_id,
                        },
                    }
                )
        filtered_relations = [
            rel
            for rel in relations
            if not (
                isinstance(rel, Mapping)
                and rel.get("subject") == intruder_id
                and rel.get("reference") == appliance_id
                and rel.get("predicate") == "in_front_of"
            )
        ]
        filtered_relations.append(
            {
                "subject": intruder_id,
                "predicate": "left_of",
                "reference": appliance_id,
            }
        )
        repaired["relations"] = filtered_relations
        relations = filtered_relations

    return repaired, actions


def _load_domain_constraints(path: Path) -> Any:
    resolved = path.resolve()
    return load_layout_constraints(resolved.parent if resolved.is_file() else resolved)


def _run_critic_repair_demo(
    out_root: Path,
    tasks: Sequence[Path] | None = None,
) -> dict[str, Any]:
    bundle_path = REPO_ROOT / "configs/out_of_domain_tasks/modern_office_brother_calibrate.yaml"
    for candidate in tasks or ():
        resolved = candidate if candidate.is_absolute() else (REPO_ROOT / candidate)
        if resolved.name == "modern_office_brother_calibrate.yaml" and resolved.is_file():
            bundle_path = resolved.resolve()
            break
    bundle = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
    constraints = _load_domain_constraints(REPO_ROOT / bundle["domain_pack"])

    flawed_request = copy.deepcopy(bundle["layout_request"])
    for obj in flawed_request["objects"]:
        if obj["id"] == "a5_media_pack":
            # Sits inside safe table bounds [-0.30, +0.30] and outside closed printer body
            # [-0.1095, +0.2895], but intrudes into paper_cassette_pullout [-0.292, -0.1095].
            obj["region"] = "robot_near"
            obj["fixed_xy_m"] = [0.0, -0.200]
    flawed_request["relations"] = [
        (
            {
                "subject": "a5_media_pack",
                "predicate": "in_front_of",
                "reference": "brother_printer",
            }
            if rel.get("subject") == "a5_media_pack"
            else rel
        )
        for rel in flawed_request["relations"]
    ]

    iter1_result = solve_relational_tabletop_layout(
        flawed_request, domain_constraints=constraints
    )
    if iter1_result.status != "infeasible" or not any(
        item.conflict_type == "kinematic_clearance_intrusion"
        for item in iter1_result.conflicts
    ):
        raise RuntimeError(
            "expected Iteration 1 flawed draft to trigger kinematic_clearance_intrusion"
        )

    repaired_request, repair_actions = _repair_layout_from_conflicts(
        flawed_request, iter1_result.conflicts
    )
    iter2_result = solve_relational_tabletop_layout(
        repaired_request, domain_constraints=constraints
    )
    if iter2_result.status != "solved" or iter2_result.conflicts:
        raise RuntimeError(
            f"expected Iteration 2 repaired draft to solve cleanly, got {iter2_result.status}"
        )

    trace = {
        "schema_version": "agentic-critic-repair-trace/v0.1",
        "scenario_id": "modern_office_brother_calibrate",
        "failure_mode_tested": "prismatic_drawer_corridor_occlusion",
        "iteration_1_unrepaired": {
            "request": flawed_request,
            "result": iter1_result.to_mapping(),
        },
        "critic_repair_actions": repair_actions,
        "iteration_2_repaired": {
            "request": repaired_request,
            "result": iter2_result.to_mapping(),
        },
    }
    trace_path = out_root / "critic_repair_trace.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return trace


def _compile_and_export_task(
    task_path: Path,
    out_root: Path,
    *,
    isaac_python: Path,
    genmanip_root: Path,
    curobo_src: Path,
    skip_runtime: bool,
    render_only: bool = False,
) -> dict[str, Any]:
    resolved_task_path = (
        task_path if task_path.is_absolute() else (REPO_ROOT / task_path)
    ).resolve()
    bundle = yaml.safe_load(resolved_task_path.read_text(encoding="utf-8"))
    if bundle.get("schema_version") != "out-of-domain-task-bundle/v0.1":
        raise ValueError(f"unsupported task bundle schema in {resolved_task_path}")

    domain_pack_path = (REPO_ROOT / bundle["domain_pack"]).resolve()
    bindings_path = (REPO_ROOT / bundle["source_bindings"]).resolve()
    constraints = _load_domain_constraints(domain_pack_path)

    solved_layout = solve_relational_tabletop_layout(
        bundle["layout_request"],
        domain_constraints=constraints,
    )
    if solved_layout.status != "solved":
        conflict_summary = "; ".join(c.message for c in solved_layout.conflicts)
        raise RuntimeError(
            f"layout solver failed for {resolved_task_path.name}: {conflict_summary}"
        )

    spec = compose_scenario_spec_from_solved_layout(
        bundle["task_draft"],
        solved_layout,
    )
    scenario_id = spec.scenario_id
    task_out_dir = out_root / "packages" / scenario_id
    task_out_dir.mkdir(parents=True, exist_ok=True)

    solved_layout_path = task_out_dir / "solved_layout.json"
    spec_path = task_out_dir / "composed_scenario_spec.yaml"
    package_dir = task_out_dir / "scenario_package"
    collected_dir = task_out_dir / "collected_package"
    if not render_only:
        solved_layout_path.write_text(
            json.dumps(
                solved_layout.to_mapping(), ensure_ascii=False, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        spec_path.write_text(
            yaml.safe_dump(spec.to_mapping(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        sources = resolve_scenario_source_bindings(bindings_path)
        compile_scenario_package(spec, sources, package_dir)

    validation = validate_package(package_dir, require_asset_lock=True)
    if not validation.ok:
        raise RuntimeError(
            f"validate_package failed for {scenario_id}: {'; '.join(validation.messages)}"
        )
    lock_report = check_asset_lock(package_dir)
    if not lock_report.ok:
        raise RuntimeError(
            f"check_asset_lock failed for {scenario_id}: {'; '.join(lock_report.messages)}"
        )

    if not render_only:
        export_genmanip_collected_package(package_dir, collected_dir)
    elif not collected_dir.is_dir():
        raise FileNotFoundError(f"missing collected_package for --render-only: {collected_dir}")

    render_manifest_path: str | None = None
    visual_gate_status: str | None = None
    if not skip_runtime:
        preview_script = REPO_ROOT / "scripts" / "ebench" / "render_genmanip_initial_preview.py"
        runtime_paths = (curobo_src,) if curobo_src.is_dir() else ()
        preview_result = run_genmanip_initial_preview(
            collected_dir,
            isaac_python,
            preview_script,
            genmanip_root,
            timeout_seconds=900.0,
            runtime_python_paths=runtime_paths,
        )
        manifest_file = preview_result.evidence_dir / "render_manifest.json"
        if not manifest_file.is_file():
            raise RuntimeError(f"missing render_manifest.json for {scenario_id}")
        render_manifest_path = str(manifest_file)
        visual_gate_status = preview_result.status

    return {
        "scenario_id": scenario_id,
        "domain": spec.domain,
        "task_bundle": str(resolved_task_path.relative_to(REPO_ROOT)),
        "solved_layout_json": str(solved_layout_path),
        "composed_spec_yaml": str(spec_path),
        "scenario_package_dir": str(package_dir.resolve()),
        "collected_package_dir": str(collected_dir.resolve()),
        "package_validation_ok": validation.ok,
        "asset_lock_ok": lock_report.ok,
        "render_manifest_json": render_manifest_path,
        "visual_ready_gate_status": visual_gate_status,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_root = (
        args.out_root if args.out_root.is_absolute() else (REPO_ROOT / args.out_root)
    ).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    repair_trace = _run_critic_repair_demo(out_root, tasks=args.tasks)
    print(
        f"[CriticRepair] {repair_trace['scenario_id']}: "
        f"iter1={repair_trace['iteration_1_unrepaired']['result']['status']} -> "
        f"iter2={repair_trace['iteration_2_repaired']['result']['status']}"
    )

    summaries: list[dict[str, Any]] = []
    for task_path in args.tasks:
        summary = _compile_and_export_task(
            task_path,
            out_root,
            isaac_python=args.isaac_python.resolve(),
            genmanip_root=args.genmanip_root.resolve(),
            curobo_src=args.curobo_src.resolve(),
            skip_runtime=args.skip_runtime,
            render_only=args.render_only,
        )
        summaries.append(summary)
        print(
            f"[SceneGate] {summary['scenario_id']}: package_ok={summary['package_validation_ok']} "
            f"lock_ok={summary['asset_lock_ok']} collected={summary['collected_package_dir']}"
        )

    gate_summary = {
        "schema_version": "out-of-domain-scene-gate-summary/v0.1",
        "critic_repair_trace_json": str(out_root / "critic_repair_trace.json"),
        "tasks": summaries,
    }
    summary_path = out_root / "scene_gate_summary.json"
    summary_path.write_text(
        json.dumps(gate_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote scene gate summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

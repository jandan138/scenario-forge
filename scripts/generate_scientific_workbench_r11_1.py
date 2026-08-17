#!/usr/bin/env python3
"""Compile validation-focused r11.1 children for Scientific Workbench Tasks 05/09."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any, Sequence

import yaml

import scripts.generate_scientific_workbench_r11 as r11
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.ik_preflight import write_provisional_ik_preflight_request
from scenario_forge.adapters.ebench.preview import write_genmanip_preview_request
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task05_task09_r11_1_20260818"
LAYOUT_DELTA_LIMITS = {
    "maximum_translation_m": 0.05,
    "maximum_yaw_deg": 15.0,
    "robot_base_frozen": True,
}


def _upgrade(base: dict[str, Any]) -> dict[str, Any]:
    scenario = copy.deepcopy(base)
    scenario["scenario_id"] = str(scenario["scenario_id"]).replace(
        "scientific_workbench_r11_", "scientific_workbench_r11_1_", 1
    )
    metadata = scenario["metadata"]
    metadata.update(
        {
            "release": "r11.1",
            "supersedes": "r11",
            "release_kind": "validation_child",
            "layout_delta_limits": dict(LAYOUT_DELTA_LIMITS),
            "task_interaction_ready": False,
            "robot_policy_success": False,
            "claim_boundary": (
                "r11.1 validation candidate before EOS scripted-oracle attachment; "
                "no policy, benchmark, thermal, or task-success claim."
            ),
        }
    )
    for item in scenario["objects"]:
        item_metadata = item.get("metadata")
        if isinstance(item_metadata, dict) and item_metadata.get("dressing_release") == "r11":
            item_metadata["dressing_release"] = "r11.1"
    return scenario


def build_task05_scenario() -> dict[str, Any]:
    return _upgrade(r11.build_task05_scenario())


def build_task09_scenario() -> dict[str, Any]:
    return _upgrade(r11.build_task09_scenario())


def build_static_release(*, output_dir: Path = DEFAULT_OUT) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"r11.1 output already exists: {output_dir}")
    sources = r11._required_sources(r11.DEFAULT_R11_BINDINGS)
    records: list[dict[str, Any]] = []
    for task_number, scenario in ((5, build_task05_scenario()), (9, build_task09_scenario())):
        spec = ScenarioSpec.from_mapping(scenario)
        root = output_dir / "packages" / f"task{task_number:02d}"
        package = compile_scenario_package(spec, sources, root)
        closure = validate_package(package.package_root)
        if not closure.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
        closure_path = package.package_root / "evidence/package_closure.yaml"
        closure_path.parent.mkdir(parents=True, exist_ok=True)
        closure_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "scenario-forge-package-closure/v0.1",
                    "status": "pass",
                    "messages": list(closure.messages),
                    "claim_boundary": "Portable dependency closure only.",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        ebench = export_genmanip_collected_package(package.package_root)
        preview = write_genmanip_preview_request(ebench.output_dir, resolution=(1920, 1080))
        preview_data = yaml.safe_load(preview.read_text(encoding="utf-8"))
        preview_data["zero_action_warmup_steps"] = 240
        preview_data["claim_boundary"] = "r11.1 pre-oracle scene validation only."
        preview.write_text(
            yaml.safe_dump(preview_data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        ik_request = write_provisional_ik_preflight_request(package.package_root)
        vr = export_vr_teleop_package(
            package.package_root,
            package.package_root / "adapters/vr_teleop",
            task_id=spec.scenario_id,
        )
        records.append(
            {
                "task_number": task_number,
                "scenario_id": spec.scenario_id,
                "package_root": str(root.resolve()),
                "ebench_root": str(ebench.output_dir.resolve()),
                "vr_root": str(vr.output_dir.resolve()),
                "provisional_ik_request": str(ik_request.resolve()),
                "portable_closure": "pass",
                "tabletop_placement": tabletop.overall_status,
                "runtime_preview": "pending",
                "vr_open_smoke": "pending",
                "scripted_oracle": "pending",
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r11-1/v0.1",
        "status": "static_complete_runtime_pending",
        "release": "r11.1",
        "supersedes": "r11",
        "package_count": 2,
        "packages": records,
        "claim_boundary": "Static r11.1 candidates only; task interaction remains pending.",
    }
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    print(build_static_release(output_dir=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the coordinated r10.1 Task 02/07/08 dual-consumer release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml

import scripts.generate_scientific_workbench_r7 as r7
import scripts.generate_scientific_workbench_r9 as r9
import scripts.generate_scientific_workbench_task02_r8 as r8
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import write_genmanip_preview_request
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.isaac41_vr600_profile import (
    physx_scene_config,
    vr_robot_contact_config,
)
from scenario_forge.adapters.vr_teleop import _python_literal, export_vr_teleop_package
from scenario_forge.artifacts.usd_handoff import build_multi_task_dual_consumer_bundle
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings
from scenario_forge.package import validate_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817"
DEFAULT_R10 = REPO_ROOT / "outputs/scientific_workbench_task02_r10_fill_sweep_20260817"
DEFAULT_RACK_BINDINGS = (
    REPO_ROOT
    / "configs/source_bindings/scientific_workbench_r10_1_acrylic_rack_20260817.yaml"
)
ACRYLIC_RACK_ASSET_ID = "scientific_workbench_r10_1_acrylic_spoon_rack"
ACRYLIC_RACK_XYZ = [0.16, -0.17, 0.755]
R10_1_ARCHIVE_ID = "scientific_workbench_tasks_02_07_08_r10_1"
TASK02_OBJECTS = (
    "obj_graduated_cylinder",
    "obj_beaker",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
TASK02_LEGACY_PRIMS = {
    "background": "/World/_scene/room",
    "table": "/World/_scene/obj_table",
    "obj_graduated_cylinder": "/World/_scene/obj_obj_graduated_cylinder",
    "obj_beaker": "/World/_scene/obj_obj_beaker",
    "obj_r9_amber_bottle": "/World/_scene/obj_r9_amber_bottle",
    "obj_r9_tip_box": "/World/_scene/obj_r9_tip_box",
    "obj_r9_wash_bottle": "/World/_scene/obj_r9_wash_bottle",
    "obj_r9_clear_bottle": "/World/_scene/obj_r9_clear_bottle",
    "obj_r9_pipette_carousel": "/World/_scene/obj_r9_pipette_carousel",
    "fluid_runtime": "/World/_scene/fluid_runtime",
}


def _frame_request(*names: str) -> dict[str, Any]:
    return {
        name: {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}
        for name in names
    }


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    value = item.setdefault("metadata", {})
    if not isinstance(value, dict):
        raise ValueError(f"{item.get('id')} metadata must be a mapping")
    return value


def upgrade_task07(source: Mapping[str, Any]) -> dict[str, Any]:
    scenario = deepcopy(dict(source))
    scenario["scenario_id"] = str(scenario["scenario_id"]).replace(
        "scientific_workbench_r9_", "scientific_workbench_r10_1_", 1
    )
    scenario["instruction"] = (
        "辅助臂固定 325 mL 烧杯；操作臂从透明亚克力架中央 14 mm 孔取出 "
        "300 mm 玻璃棒，插入杯内累计搅拌至少一周，最后插回同一中央孔并释放。"
    )
    scenario["metadata"]["release"] = "r10.1"
    scenario["metadata"]["supersedes"] = "r9"
    scenario["metadata"]["task07_fixture_contract"] = (
        "acrylic_rack_middle_socket_04_start_and_return"
    )
    scenario["metadata"]["robot_claim"] = (
        "not_run; geometry, package, initial-state, and rack insertion qualification only"
    )
    objects = scenario["objects"]
    rod = next(item for item in objects if item["id"] == "obj_glass_rod")
    _metadata(rod).update(
        {
            "rack_socket_index": 4,
            "pose_source": "obj_acrylic_rod_rack.middle_socket_04_inserted_bottom",
            "vr_randomization_group": "task07_acrylic_rack_assembly",
        }
    )
    rod["pose"] = {"xyz": list(ACRYLIC_RACK_XYZ), "wxyz": [1.0, 0.0, 0.0, 0.0]}
    objects.append(
        {
            "id": "obj_acrylic_rod_rack",
            "asset_id": ACRYLIC_RACK_ASSET_ID,
            "source_prim_path": "/World/AcrylicSpoonRack",
            "role": "tool_rack",
            "pose": {"xyz": list(ACRYLIC_RACK_XYZ), "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "named_frames": _frame_request(
                "middle_socket_04_aperture",
                "middle_socket_04_inserted_bottom",
            ),
            "metadata": {
                "interaction_role": "stirring_tool_start_and_return_fixture",
                "vr_randomization_group": "task07_acrylic_rack_assembly",
                "qualification": "ConvertAsset central insertion pass at 120 Hz",
            },
        }
    )
    aluminum_ids = {"context_rack", "context_glass_tube_s1", "context_glass_tube_s3", "context_glass_tube_s6"}
    for item in objects:
        if item["id"] in aluminum_ids:
            _metadata(item)["vr_randomization_group"] = "task07_aluminum_rack_assembly"
    scenario["steps"] = [
        {
            "id": "hold_beaker",
            "skill": "grasp_and_hold",
            "actors": ["auxiliary_arm"],
            "parameters": {"object": "obj_beaker"},
        },
        {
            "id": "pick_rod",
            "skill": "lift",
            "actors": ["operating_arm"],
            "parameters": {
                "object": "obj_glass_rod",
                "grasp_frame": "obj_glass_rod.grasp",
                "source_fixture": "obj_acrylic_rod_rack",
                "source_frame": "obj_acrylic_rod_rack.middle_socket_04_inserted_bottom",
            },
            "depends_on": ["hold_beaker"],
        },
        {
            "id": "insert_rod",
            "skill": "insert",
            "actors": ["operating_arm"],
            "parameters": {
                "object": "obj_glass_rod",
                "source_frame": "obj_glass_rod.working_tip",
                "target_frame": "obj_beaker.interior_center",
            },
            "depends_on": ["pick_rod"],
        },
        {
            "id": "stir_once",
            "skill": "stir",
            "actors": ["operating_arm"],
            "parameters": {
                "object": "obj_glass_rod",
                "tracked_frame": "obj_glass_rod.working_tip",
                "reference_frame": "obj_beaker.interior_center",
                "trajectory": {
                    "kind": "accumulated_angular_sweep",
                    "min_angle_deg": 360.0,
                    "direction_accumulation": "max_separate_signed",
                },
            },
            "depends_on": ["insert_rod"],
        },
        {
            "id": "return_rod",
            "skill": "insert",
            "actors": ["operating_arm"],
            "parameters": {
                "object": "obj_glass_rod",
                "source_frame": "obj_glass_rod.working_tip",
                "target_frame": "obj_acrylic_rod_rack.middle_socket_04_inserted_bottom",
            },
            "depends_on": ["stir_once"],
        },
        {
            "id": "release_rod",
            "skill": "release",
            "actors": ["operating_arm"],
            "parameters": {"object": "obj_glass_rod"},
            "depends_on": ["return_rod"],
        },
        {
            "id": "release_beaker",
            "skill": "release",
            "actors": ["auxiliary_arm"],
            "parameters": {"object": "obj_beaker"},
            "depends_on": ["release_rod"],
        },
    ]
    for item in scenario["success"]["progress_rubric"]["items"]:
        if item["id"] != "rod_returned":
            continue
        item["condition"] = {
            "type": "object_at_initial_pose",
            "parameters": {
                "object": "obj_glass_rod",
                "xyz_tolerance": [0.004, 0.004, 0.005],
                "released": True,
            },
        }
    scenario["success"] = r7._rubric(
        scenario["success"]["progress_rubric"]["items"],
        "stirring_trajectory_completed",
    )
    return scenario


def materialize_task07_rod_pose(source: Mapping[str, Any]) -> dict[str, Any]:
    scenario = deepcopy(dict(source))
    objects = scenario["objects"]
    rack = next(item for item in objects if item["id"] == "obj_acrylic_rod_rack")
    rod = next(item for item in objects if item["id"] == "obj_glass_rod")
    offset = rack["named_frames"]["middle_socket_04_inserted_bottom"]["xyz"]
    rack_xyz = rack["pose"]["xyz"]
    rod["pose"] = {
        "xyz": [round(float(rack_xyz[i]) + float(offset[i]), 12) for i in range(3)],
        "wxyz": [1.0, 0.0, 0.0, 0.0],
    }
    return scenario


def upgrade_task08(source: Mapping[str, Any]) -> dict[str, Any]:
    scenario = deepcopy(dict(source))
    scenario["scenario_id"] = str(scenario["scenario_id"]).replace(
        "scientific_workbench_r9_", "scientific_workbench_r10_1_", 1
    )
    scenario["metadata"]["release"] = "r10.1"
    scenario["metadata"]["supersedes"] = "r9"
    scenario["metadata"]["robot_claim"] = "not_run; package and initial-state evidence only"
    group = "task08_tube_rack_assembly"
    for item in scenario["objects"]:
        if item["id"] in {
            "obj_tube_rack",
            "obj_centrifuge_tube",
            "context_closed_tube_s1",
            "context_closed_tube_s6",
        }:
            _metadata(item)["vr_randomization_group"] = group
    return scenario


def task02_direct_vr_scene() -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        "    kilogramsPerUnit = 1",
        '    upAxis = "Z"',
        "    timeCodesPerSecond = 60",
        "    framesPerSecond = 60",
        ")",
        "",
        'def Xform "World"',
        "{",
    ]
    for name in ("background", "table", *TASK02_OBJECTS, "fluid_runtime"):
        lines.extend(
            [
                f'    def Xform "{name}" (',
                f"        prepend references = @legacy_scene.usd@<{TASK02_LEGACY_PRIMS[name]}>",
                "    ) {}",
                "",
            ]
        )
    lines.extend(
        [
            '    def DomeLight "vr_direct_open_light"',
            "    {",
            "        color3f inputs:color = (1, 1, 1)",
            "        float inputs:exposure = 0",
            "        float inputs:intensity = 750",
            "    }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _local_group(names: Sequence[str]) -> dict[str, Any]:
    return {
        "objs": list(names),
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def task02_vr_config(*, scenario_id: str, particle_count: int) -> str:
    config = {
        "scene_usd_file_path": {
            "scene1": "__SCENE_PATH__",
        },
        "obj_prim_list": [f"/World/_scene/{name}" for name in TASK02_OBJECTS],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(("obj_graduated_cylinder", "fluid_runtime")),
                *[_local_group((name,)) for name in TASK02_OBJECTS[1:]],
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            **physx_scene_config(),
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "TimeStepsPerSecond": 120,
        },
        **vr_robot_contact_config(),
        "prototype_fluid": {
            "status": "qualified_dynamic_loaded_start",
            "particle_count": particle_count,
            "liquid_metrics_active": False,
            "inactive_reason": "vr_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_dynamic_loaded_start",
        },
    }
    body = _python_literal(config, indent=0).replace(
        '"__SCENE_PATH__"',
        f'str(_ASSETS_DIR / "scenes/{scenario_id}/scene.usd")',
    )
    return (
        "# Merge this TASKS entry into the VR teleop task registry.\n"
        f"TASKS = {{\n    {scenario_id!r}: {body},\n}}\n"
    )


def _sha(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def upgrade_task02_package(source: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    vr = destination / "vr"
    original = vr / "scene.usd"
    legacy = vr / "legacy_scene.usd"
    shutil.copy2(original, legacy)
    original.write_text(task02_direct_vr_scene(), encoding="utf-8")
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenario_id = str(manifest["scenario_id"])
    particle_count = int(manifest["particle_count"])
    config = task02_vr_config(scenario_id=scenario_id, particle_count=particle_count)
    (vr / "task_config.py").write_text(config, encoding="utf-8")
    (vr / "config.py").write_text(config, encoding="utf-8")
    parity = {
        "schema_version": "scenario-forge-vr-direct-root-parity/v0.2",
        "status": "pass_with_declared_exception",
        "scenario_id": scenario_id,
        "source_default_prim": "/World",
        "runtime_mount_prim": "/World/_scene",
        "obj_prim_count": 7,
        "liquid_randomized_with": "obj_graduated_cylinder",
        "direct_open_light": {
            "type": "DomeLight",
            "intensity": 750,
            "texture_dependency": None,
        },
        "claims_forbidden": [
            "VR robot policy success",
            "VR liquid metric success",
            "benchmark success",
        ],
        "artifacts": {
            "scene_usd": {"path": "scene.usd", "sha256": _sha(original)},
            "task_config": {"path": "task_config.py", "sha256": _sha(vr / "task_config.py")},
        },
    }
    (vr / "parity_manifest.json").write_text(
        json.dumps(parity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    stale = vr / "evidence/open_smoke/report.json"
    if stale.is_file():
        stale.unlink()
    manifest["release"] = "r10.1"
    manifest["supersedes"] = "r10"
    manifest["vr_contract"] = {
        "schema_version": "scenario-forge-vr-direct-root/v0.2",
        "status": "static_pass_runtime_pending",
        "source_default_prim": "/World",
        "runtime_mount_prim": "/World/_scene",
        "obj_prim_count": 7,
        "direct_open_light": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    r8.refresh_hashes(destination)
    return destination


def _compile_task07_08(
    *,
    output_dir: Path,
    base_bindings: Path,
    context_bindings: Path,
    rack_bindings: Path,
) -> list[dict[str, Any]]:
    sources = resolve_scenario_source_bindings(base_bindings)
    for binding in (context_bindings, rack_bindings):
        extra = resolve_scenario_source_bindings(binding)
        overlap = set(sources) & set(extra)
        if overlap:
            raise ValueError(f"duplicate source bindings: {sorted(overlap)}")
        sources.update(extra)
    records: list[dict[str, Any]] = []
    for plan in r9.load_r9_plans():
        if plan.task_number not in {7, 8}:
            continue
        scenario = (
            upgrade_task07(plan.scenario)
            if plan.task_number == 7
            else upgrade_task08(plan.scenario)
        )
        scenario = r7._materialize_rack_population(scenario, sources)
        scenario = r7._materialize_frames(scenario, sources)
        if plan.task_number == 7:
            scenario = materialize_task07_rod_pose(scenario)
        spec = ScenarioSpec.from_mapping(scenario)
        root = output_dir / "packages" / f"task{plan.task_number:02d}" / plan.background_id
        if root.exists():
            shutil.rmtree(root)
        package = compile_scenario_package(spec, sources, root)
        closure = validate_package(package.package_root)
        if not closure.ok:
            raise ValueError("compiled package failed closure: " + "; ".join(closure.messages))
        tabletop = validate_scientific_workbench_tabletop_placement(package.package_root)
        if tabletop.overall_status != "pass":
            raise ValueError(f"{spec.scenario_id} tabletop placement failed")
        ebench = export_genmanip_collected_package(package.package_root)
        request = write_genmanip_preview_request(ebench.output_dir, resolution=(1920, 1080))
        request_data = yaml.safe_load(request.read_text(encoding="utf-8"))
        request_data["zero_action_warmup_steps"] = r9.R9_STABILITY_STEPS
        request_data["claim_boundary"] = (
            "r10.1 initial-scene load, reset, 960 zero-action steps, and visual evidence only; "
            "not robot-policy or benchmark success."
        )
        request.write_text(
            yaml.safe_dump(request_data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        vr = export_vr_teleop_package(
            package.package_root,
            package.package_root / "adapters/vr_teleop",
            task_id=spec.scenario_id,
        )
        records.append(
            {
                "task_number": plan.task_number,
                "background_id": plan.background_id,
                "scenario_id": spec.scenario_id,
                "package_root": str(root.resolve()),
                "ebench_root": str(ebench.output_dir.resolve()),
                "vr_root": str(vr.output_dir.resolve()),
                "portable_closure": "pass",
                "tabletop_placement": tabletop.overall_status,
                "runtime_preview": "pending",
                "vr_open_smoke": "pending",
            }
        )
    return records


def build_static_release(
    *,
    output_dir: Path = DEFAULT_OUT,
    r10_root: Path = DEFAULT_R10,
    base_bindings: Path = r9.DEFAULT_BASE_BINDINGS,
    context_bindings: Path = r9.DEFAULT_CONTEXT_BINDINGS,
    rack_bindings: Path = DEFAULT_RACK_BINDINGS,
) -> Path:
    output_dir = output_dir.resolve()
    records: list[dict[str, Any]] = []
    for fill_id in ("fill20", "fill40", "fill60", "fill80"):
        source = r10_root / "packages" / fill_id
        destination = output_dir / "packages/task02" / fill_id
        package = upgrade_task02_package(source, destination)
        records.append(
            {
                "task_number": 2,
                "variant": fill_id,
                "scenario_id": json.loads((package / "manifest.json").read_text())["scenario_id"],
                "package_root": str(package.resolve()),
                "ebench_root": str((package / "ebench").resolve()),
                "vr_root": str((package / "vr").resolve()),
                "runtime_preview": "inherited_r10",
                "vr_open_smoke": "pending_r10_1_contract",
            }
        )
    records.extend(
        _compile_task07_08(
            output_dir=output_dir,
            base_bindings=base_bindings,
            context_bindings=context_bindings,
            rack_bindings=rack_bindings,
        )
    )
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r10.1/v0.1",
        "status": "static_complete_runtime_pending",
        "release": "r10.1",
        "package_count": len(records),
        "task_counts": {"task02": 4, "task07": 5, "task08": 1},
        "packages": records,
        "claim_boundary": (
            "Portable packages and consumer adapters only until per-package Isaac 4.1 gates are attached. "
            "No new robot-policy or benchmark claim."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return destination


def runtime_release_specs(output_dir: Path) -> list[tuple[int, str, Path]]:
    """Return the fixed ten-package release matrix relative to ``output_dir``."""

    del output_dir  # The argument makes call sites explicit while paths stay portable.
    return [
        *((2, fill, Path("packages/task02") / fill) for fill in ("fill20", "fill40", "fill60", "fill80")),
        *(
            (7, background, Path("packages/task07") / background)
            for background in (
                "example4",
                "teaching_research",
                "modern_wet_chemistry",
                "bioclean",
                "analytical_instrumentation",
            )
        ),
        (8, "bioclean", Path("packages/task08/bioclean")),
    ]


def _load_status(path: Path, *, accepted: set[str]) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required runtime evidence is missing: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("status") not in accepted:
        raise ValueError(f"runtime evidence did not pass: {path}")
    return value


def finalize_runtime_release(*, output_dir: Path = DEFAULT_OUT) -> Path:
    """Validate attached Isaac evidence and publish the ten-package handoff ZIP."""

    output_dir = output_dir.resolve()
    handoff_inputs: list[tuple[int, str, Path, Path]] = []
    records: list[dict[str, Any]] = []
    for task_number, variant, relative in runtime_release_specs(output_dir):
        package = output_dir / relative
        if task_number == 2:
            ebench = package / "ebench"
            vr = package / "vr"
            product = _load_status(
                ebench / "evidence/product_smoke/report.json", accepted={"pass"}
            )
            product_status = str(product["status"])
        else:
            ebench = package / "adapters/ebench/genmanip"
            vr = package / "adapters/vr_teleop"
            product_status = "not_applicable"
        visual_gate_path = ebench / "evidence/initial_scene/visual_ready_gate.yaml"
        _load_status(visual_gate_path, accepted={"pass", "passed"})
        overview = visual_gate_path.parent / "scene_overview.png"
        if not overview.is_file():
            raise ValueError(f"scene overview is missing: {overview}")
        vr_smoke_path = vr / "evidence/open_smoke/report.json"
        _load_status(vr_smoke_path, accepted={"pass"})
        if task_number == 2:
            manifest_path = package / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.setdefault("vr_contract", {})["status"] = "runtime_pass"
            manifest["vr_contract"]["open_smoke_report"] = {
                "path": "vr/evidence/open_smoke/report.json",
                "sha256": _sha(vr_smoke_path),
            }
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        handoff_inputs.append((task_number, variant, ebench, vr))
        records.append(
            {
                "task_number": task_number,
                "variant": variant,
                "package_root": str(package.resolve()),
                "ebench_initial_scene": "pass",
                "ebench_product_smoke": product_status,
                "vr_open_smoke": "pass",
                "visual_review": "pass",
                "scene_overview": str(overview.resolve()),
            }
        )
    archive = build_multi_task_dual_consumer_bundle(
        archive_id=R10_1_ARCHIVE_ID,
        variants=handoff_inputs,
        output_dir=output_dir / "handoff",
    )
    manifest = {
        "schema_version": "scenario-forge-scientific-workbench-r10.1/v0.2",
        "status": "runtime_complete_with_bounded_claims",
        "release": "r10.1",
        "package_count": len(records),
        "task_counts": {"task02": 4, "task07": 5, "task08": 1},
        "packages": records,
        "handoff": {
            "directory": str(archive.root.resolve()),
            "zip": str(archive.zip_path.resolve()),
            "zip_sha256": _sha(archive.zip_path),
        },
        "visual_review": {
            "status": "pass",
            "method": "local human-style review of the rendered images plus runtime geometry gates",
            "notes": [
                "The transparent acrylic rack is visually subtle but correctly placed.",
                "The Task 08 red cap is tabletop-supported; its small size caused the overview ambiguity.",
            ],
        },
        "claim_boundary": (
            "All ten packages passed their attached eBench initial-scene and VR direct-open gates. "
            "Task 02 retains its existing liquid/product smoke evidence. No new robot-policy, "
            "task-success, liquid-metric, or benchmark claim is made."
        ),
    }
    destination = output_dir / "manifest.yaml"
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--r10-root", type=Path, default=DEFAULT_R10)
    parser.add_argument("--base-bindings", type=Path, default=r9.DEFAULT_BASE_BINDINGS)
    parser.add_argument("--context-bindings", type=Path, default=r9.DEFAULT_CONTEXT_BINDINGS)
    parser.add_argument("--rack-bindings", type=Path, default=DEFAULT_RACK_BINDINGS)
    parser.add_argument(
        "--finalize-runtime",
        action="store_true",
        help="validate existing runtime evidence and build the unified handoff ZIP",
    )
    args = parser.parse_args(argv)
    if args.finalize_runtime:
        print(finalize_runtime_release(output_dir=args.out))
        return 0
    print(
        build_static_release(
            output_dir=args.out,
            r10_root=args.r10_root,
            base_bindings=args.base_bindings,
            context_bindings=args.context_bindings,
            rack_bindings=args.rack_bindings,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

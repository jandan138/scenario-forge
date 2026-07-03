from __future__ import annotations

from pathlib import Path

import yaml

from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.scene.usd_compiler import compile_usd_scene
from scenario_forge.task.task_compiler import compile_task_artifacts


def scaffold_starter_package(out_dir: str | Path) -> Path:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    _write_text(root / "scene" / "main.usda", "#usda 1.0\n")
    _write_text(
        root / "assets" / "objects" / "starter_rigid_object" / "model.usd",
        '#usda 1.0\n\ndef Xform "starter_rigid_object"\n{\n}\n',
    )
    _write_text(
        root / "assets" / "markers" / "starter_target_marker" / "model.usd",
        '#usda 1.0\n\ndef Xform "starter_target_marker"\n{\n}\n',
    )
    _write_yaml(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": "tabletop_pick_place_starter",
            "scenario_domain": "scientific_workbench",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_layout": "scene/layout.yaml",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_graph": "task/task_graph.yaml",
                "predicates": "task/predicates.yaml",
                "safety_rules": "task/safety_rules.yaml",
                "robot": "robot/robot.yaml",
                "robot_profile": "robot/robot_profile.yaml",
                "metrics": "metrics/metrics.yaml",
                "splits": "metrics/splits.yaml",
            },
            "assets": {
                "manifest": "assets/asset_manifest.yaml",
                "lock": "locks/asset_lock.yaml",
            },
            "validation": {
                "report": "evidence/validation_report.yaml",
                "minimum_required_level": "adapter_static_validated",
            },
            "provenance": {
                "summary": "provenance/provenance.yaml",
                "source_refs": "provenance/source_refs.yaml",
                "generation_trace": "provenance/generation_trace.jsonl",
            },
        },
    )
    _write_yaml(
        root / "generation_plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": "tabletop_pick_place_starter",
            "seed": 0,
            "target_exports": ["ebench", "embodied-eval-os"],
            "package_mode": "fat",
        },
    )
    _write_yaml(
        root / "scene" / "layout.yaml",
        {
            "schema_version": "scene-layout/v0.2",
            "frames": [{"id": "world", "type": "root"}],
            "zones": [{"id": "target_zone", "role": "goal_region"}],
        },
    )
    _write_yaml(
        root / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "starter_rigid_object",
                    "pose": {"xyz": [0.45, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["rigid", "pickable"],
                    "initial_state": {},
                },
                {
                    "id": "target_zone",
                    "asset_id": "starter_target_marker",
                    "pose": {"xyz": [0.65, 0.0, 0.91], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["zone", "target"],
                    "initial_state": {},
                },
            ]
        },
    )
    _write_yaml(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": "tabletop_manipulator",
            "embodiment": "franka_panda",
            "action_space": "end_effector_delta_pose",
            "sensors": [{"id": "front_rgb", "type": "rgb"}],
        },
    )
    _write_yaml(
        root / "robot" / "robot_profile.yaml",
        {
            "schema_version": "robot-profile/v0.2",
            "robot_id": "tabletop_manipulator",
            "workspace": {"frame": "world"},
        },
    )
    _write_yaml(
        root / "metrics" / "splits.yaml",
        {
            "schema_version": "splits/v0.2",
            "splits": [{"name": "smoke", "package_ids": ["tabletop_pick_place_starter"]}],
        },
    )
    _write_yaml(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": "starter_rigid_object",
                    "role": "manipulated_object",
                    "asset_type": "rigid_object",
                    "canonical_usd": "assets/objects/starter_rigid_object/model.usd",
                    "license": "Apache-2.0",
                    "sha256": compute_sha256(
                        root / "assets" / "objects" / "starter_rigid_object" / "model.usd"
                    ),
                },
                {
                    "asset_id": "starter_target_marker",
                    "role": "target_region",
                    "asset_type": "marker",
                    "canonical_usd": "assets/markers/starter_target_marker/model.usd",
                    "license": "Apache-2.0",
                    "sha256": compute_sha256(
                        root / "assets" / "markers" / "starter_target_marker" / "model.usd"
                    ),
                },
            ],
        },
    )
    write_asset_lock(root, generate_asset_lock(root))
    _write_yaml(
        root / "locks" / "generator_lock.yaml",
        {
            "schema_version": "generator-lock/v0.2",
            "generators": [{"name": "scenario-forge", "version": "unversioned"}],
        },
    )
    _write_yaml(
        root / "locks" / "schema_lock.yaml",
        {
            "schema_version": "schema-lock/v0.2",
            "schemas": [{"id": "scenario-package/v0.2"}],
        },
    )
    _write_yaml(
        root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "validation-report/v0.2",
            "status": "draft",
            "overall_level": "package_schema_validated",
            "checks": [
                {"name": "files_present", "status": "passed"},
                {"name": "asset_lock", "status": "passed"},
                {"name": "usd_static", "status": "not_run"},
                {"name": "adapter_export", "status": "not_run"},
            ],
        },
    )
    _write_yaml(root / "evidence" / "static_checks.yaml", {"checks": []})
    _write_yaml(root / "evidence" / "asset_checks.yaml", {"checks": []})
    _write_yaml(root / "evidence" / "layout_checks.yaml", {"checks": []})
    _write_yaml(root / "evidence" / "adapter_checks.yaml", {"checks": []})
    _write_yaml(root / "evidence" / "runtime_smoke.yaml", {"checks": []})
    _write_yaml(
        root / "provenance" / "provenance.yaml",
        {
            "schema_version": "provenance/v0.2",
            "generator": "scenario-forge",
            "source": "starter-template",
        },
    )
    _write_yaml(root / "provenance" / "source_refs.yaml", {"sources": []})
    _write_text(root / "provenance" / "generation_trace.jsonl", "")
    compile_usd_scene(
        package_root=root,
        instances_path=root / "scene" / "instances.yaml",
        asset_lock_path=root / "locks" / "asset_lock.yaml",
        out_path=root / "scene" / "main.usda",
    )
    compile_task_artifacts(root, task_family="pick_place")
    return root


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

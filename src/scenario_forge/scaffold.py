from __future__ import annotations

from pathlib import Path

import yaml


def scaffold_starter_package(out_dir: str | Path) -> Path:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    _write_text(root / "scene" / "main.usda", "#usda 1.0\n")
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
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": "place_object_on_target",
            "instruction": "Move the object onto the target zone.",
        },
    )
    _write_yaml(
        root / "task" / "task_graph.yaml",
        {
            "schema_version": "task-graph/v0.2",
            "nodes": [{"id": "place_object", "type": "atomic_skill"}],
            "edges": [],
        },
    )
    _write_yaml(
        root / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"type": "object_in_zone", "object": "object_001", "zone": "target_zone"}
            ],
        },
    )
    _write_yaml(
        root / "task" / "safety_rules.yaml",
        {
            "schema_version": "safety-rules/v0.2",
            "safety_rules": [{"type": "no_drop", "object": "object_001"}],
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
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [{"id": "success", "type": "predicate_satisfaction"}],
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
            "assets": [],
        },
    )
    _write_yaml(
        root / "locks" / "asset_lock.yaml",
        {
            "schema_version": "asset-lock/v0.2",
            "lock_id": "tabletop_pick_place_starter_asset_lock",
            "created_by": "scenario-forge",
            "assets": {},
        },
    )
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
    return root


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

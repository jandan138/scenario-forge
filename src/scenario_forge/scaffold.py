from __future__ import annotations

from pathlib import Path

import yaml


def scaffold_starter_package(out_dir: str | Path) -> Path:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    _write_text(root / "scene.usda", "#usda 1.0\n")
    _write_yaml(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.1",
            "scenario_id": "tabletop_pick_place_starter",
            "scenario_domain": "scientific_workbench",
            "exports": ["ebench", "embodied-eval-os"],
            "files": {
                "scene": "scene.usda",
                "instances": "scene_instances.yaml",
                "task": "task.yaml",
                "robot": "robot.yaml",
                "validation_report": "validation_report.yaml",
            },
            "provenance": {
                "generator": "scenario-forge",
                "source": "starter-template",
            },
        },
    )
    _write_yaml(
        root / "scene_instances.yaml",
        {
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
        root / "task.yaml",
        {
            "task_id": "place_object_on_target",
            "instruction": "Move the object onto the target zone.",
            "success_predicates": [
                {"type": "object_in_zone", "object": "object_001", "zone": "target_zone"}
            ],
            "safety_rules": [{"type": "no_drop", "object": "object_001"}],
        },
    )
    _write_yaml(
        root / "robot.yaml",
        {
            "robot_id": "tabletop_manipulator",
            "embodiment": "franka_panda",
            "action_space": "end_effector_delta_pose",
            "sensors": [{"id": "front_rgb", "type": "rgb"}],
        },
    )
    _write_yaml(
        root / "validation_report.yaml",
        {
            "status": "draft",
            "checks": [
                {"name": "files_present", "status": "passed"},
                {"name": "sim_load", "status": "not_run"},
                {"name": "physics_stability", "status": "not_run"},
                {"name": "evaluator_predicates", "status": "not_run"},
            ],
        },
    )
    return root


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

from pathlib import Path

import pytest
import yaml

from scenario_forge.package import PackageError, load_package_manifest, validate_package


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def make_minimal_package(root: Path) -> None:
    (root / "scene.usda").write_text("#usda 1.0\n", encoding="utf-8")
    write_yaml(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.1",
            "scenario_id": "tabletop_pick_place_smoke",
            "scenario_domain": "scientific_workbench",
            "exports": ["ebench", "embodied-eval-os"],
            "files": {
                "scene": "scene.usda",
                "instances": "scene_instances.yaml",
                "task": "task.yaml",
                "robot": "robot.yaml",
                "validation_report": "validation_report.yaml",
            },
        },
    )
    write_yaml(
        root / "scene_instances.yaml",
        {
            "instances": [
                {
                    "id": "beaker_001",
                    "asset_id": "container_beaker_small",
                    "pose": {"xyz": [0.45, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["container", "rigid"],
                    "initial_state": {"contains": []},
                }
            ]
        },
    )
    write_yaml(
        root / "task.yaml",
        {
            "task_id": "place_beaker_on_mat",
            "instruction": "Move the beaker onto the marked mat.",
            "success_predicates": [
                {"type": "object_in_zone", "object": "beaker_001", "zone": "target_mat"}
            ],
            "safety_rules": [{"type": "no_drop", "object": "beaker_001"}],
        },
    )
    write_yaml(
        root / "robot.yaml",
        {
            "robot_id": "franka_tabletop",
            "embodiment": "franka_panda",
            "action_space": "end_effector_delta_pose",
            "sensors": [{"id": "front_rgb", "type": "rgb"}],
        },
    )
    write_yaml(
        root / "validation_report.yaml",
        {
            "status": "draft",
            "checks": [
                {"name": "files_present", "status": "passed"},
                {"name": "sim_load", "status": "not_run"},
            ],
        },
    )


def test_valid_package_loads_manifest_and_reports_all_referenced_files(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)

    manifest = load_package_manifest(tmp_path)
    report = validate_package(tmp_path)

    assert manifest.scenario_id == "tabletop_pick_place_smoke"
    assert manifest.exports == ("ebench", "embodied-eval-os")
    assert report.ok
    assert report.required_files == (
        tmp_path / "scene.usda",
        tmp_path / "scene_instances.yaml",
        tmp_path / "task.yaml",
        tmp_path / "robot.yaml",
        tmp_path / "validation_report.yaml",
    )


def test_validate_package_rejects_missing_referenced_file(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)
    (tmp_path / "task.yaml").unlink()

    report = validate_package(tmp_path)

    assert not report.ok
    assert "Missing referenced file: task.yaml" in report.messages


def test_package_check_requires_asset_lock_for_ebench_package(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)

    report = validate_package(tmp_path, require_asset_lock=True)

    assert not report.ok
    assert "Missing asset lock: locks/asset_lock.yaml" in report.messages


def test_manifest_rejects_unknown_export_target(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["exports"] = ["unknown-runtime"]
    write_yaml(tmp_path / "manifest.yaml", manifest)

    with pytest.raises(PackageError, match="Unsupported export target"):
        load_package_manifest(tmp_path)

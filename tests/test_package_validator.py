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


def make_v02_package(root: Path) -> None:
    (root / "scene").mkdir(parents=True)
    (root / "task").mkdir()
    (root / "robot").mkdir()
    (root / "metrics").mkdir()
    (root / "assets").mkdir()
    (root / "locks").mkdir()
    (root / "evidence").mkdir()
    (root / "provenance").mkdir()

    (root / "scene" / "main.usda").write_text("#usda 1.0\n", encoding="utf-8")
    write_yaml(root / "generation_plan.yaml", {"schema_version": "scenario-generation-plan/v0.2"})
    write_yaml(root / "scene" / "instances.yaml", {"schema_version": "scene-instances/v0.2"})
    write_yaml(root / "task" / "task.yaml", {"schema_version": "task/v0.2"})
    write_yaml(root / "robot" / "robot.yaml", {"schema_version": "robot/v0.2"})
    write_yaml(root / "metrics" / "metrics.yaml", {"schema_version": "metrics/v0.2"})
    write_yaml(root / "assets" / "asset_manifest.yaml", {"schema_version": "asset-manifest/v0.2", "assets": []})
    write_yaml(
        root / "locks" / "asset_lock.yaml",
        {
            "schema_version": "asset-lock/v0.2",
            "lock_id": "workbench_pick_place_0001_asset_lock",
            "created_by": "scenario-forge",
            "assets": {},
        },
    )
    write_yaml(root / "evidence" / "validation_report.yaml", {"schema_version": "validation-report/v0.2"})
    write_yaml(root / "provenance" / "provenance.yaml", {"schema_version": "provenance/v0.2"})
    write_yaml(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": "workbench_pick_place_0001",
            "scenario_domain": "scientific_workbench",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
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
            },
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


def test_v02_package_loads_manifest_contract(tmp_path: Path) -> None:
    make_v02_package(tmp_path)

    manifest = load_package_manifest(tmp_path)

    assert manifest.schema_version == "scenario-package/v0.2"
    assert manifest.package_id == "workbench_pick_place_0001"
    assert manifest.scenario_id == "workbench_pick_place_0001"
    assert manifest.package_mode == "fat"
    assert manifest.targets == ("ebench", "embodied-eval-os")
    assert manifest.exports == ("ebench", "embodied-eval-os")
    assert manifest.entrypoints["scene_usd"] == "scene/main.usda"
    assert manifest.files["scene"] == "scene/main.usda"
    assert manifest.assets["lock"] == "locks/asset_lock.yaml"
    assert manifest.validation["minimum_required_level"] == "adapter_static_validated"
    assert manifest.provenance["summary"] == "provenance/provenance.yaml"
    assert manifest.scene_path == "scene/main.usda"


def test_v02_manifest_rejects_invalid_package_mode(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["package_mode"] = "thin"
    write_yaml(tmp_path / "manifest.yaml", manifest)

    with pytest.raises(PackageError, match="package_mode"):
        load_package_manifest(tmp_path)


def test_validate_package_rejects_missing_referenced_file(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)
    (tmp_path / "task.yaml").unlink()

    report = validate_package(tmp_path)

    assert not report.ok
    assert "Missing referenced file: task.yaml" in report.messages


def test_v02_validate_package_requires_entrypoint_files_and_asset_lock(tmp_path: Path) -> None:
    make_v02_package(tmp_path)

    report = validate_package(tmp_path)

    assert report.ok
    assert tmp_path / "generation_plan.yaml" in report.required_files
    assert tmp_path / "scene" / "main.usda" in report.required_files
    assert tmp_path / "locks" / "asset_lock.yaml" in report.required_files


def test_v02_validate_package_rejects_missing_metrics_file(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    (tmp_path / "metrics" / "metrics.yaml").unlink()

    report = validate_package(tmp_path)

    assert not report.ok
    assert "Missing referenced file: metrics/metrics.yaml" in report.messages


def test_v02_ebench_package_requires_known_validation_level(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["validation"]["minimum_required_level"] = "not_run"
    write_yaml(tmp_path / "manifest.yaml", manifest)

    with pytest.raises(PackageError, match="minimum_required_level"):
        load_package_manifest(tmp_path)


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

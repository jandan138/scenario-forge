from pathlib import Path

import yaml

from scenario_forge.evaluation.suite_quality_evidence import generate_suite_quality_evidence
from scenario_forge.generation.suite.suite_generator import generate_suite_from_spec


def test_suite_quality_evidence_reports_duplicates_leakage_and_asset_completeness(
    tmp_path: Path,
) -> None:
    spec_path = tmp_path / "suite_spec.yaml"
    write_yaml(
        spec_path,
        {
            "schema_version": "suite-spec/v0.2",
            "suite_id": "quality_suite",
            "domain": "scientific_workbench",
            "target": "ebench",
            "package_mode": "fat",
            "robot_profiles": ["franka_panda_tabletop_v1"],
            "num_tasks": 2,
            "task_families": {"pick_place": 2},
            "difficulties": {"easy": 1, "hard": 1},
            "splits": {"dev": 1, "test": 1},
            "variation_axes": ["layout"],
            "validation": {"require_asset_lock": True},
        },
    )
    suite_dir = tmp_path / "suite"
    generate_suite_from_spec(spec_path, suite_dir)
    suite_manifest_path = suite_dir / "suite_manifest.yaml"
    suite_manifest = load_yaml(suite_manifest_path)
    first_package = suite_manifest["packages"][0]
    suite_manifest["packages"][1]["package_id"] = first_package["package_id"]
    suite_manifest["packages"][1]["path"] = first_package["path"]
    write_yaml(suite_manifest_path, suite_manifest)

    result = generate_suite_quality_evidence(suite_dir)
    evidence = load_yaml(suite_dir / "evidence" / "suite_quality_evidence.yaml")

    assert result.overall_status == "warning"
    assert evidence["suite_id"] == "quality_suite"
    assert evidence["difficulty"] == {"easy": 1, "hard": 1}
    assert evidence["leakage"]["duplicate_scene_rate"] == 0.5
    assert evidence["leakage"]["duplicate_instruction_rate"] == 0.5
    assert evidence["leakage"]["split_leakage_package_ids"] == [first_package["package_id"]]
    assert evidence["assets"]["license_completeness"] == 1.0
    assert evidence["assets"]["checksum_completeness"] == 1.0
    assert evidence["quality_findings"][0]["id"] == "duplicate_scenes"
    assert evidence["quality_findings"][0]["status"] == "warning"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

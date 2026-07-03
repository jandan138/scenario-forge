from collections import Counter
from pathlib import Path

import yaml

from scenario_forge.generation.suite.suite_generator import generate_suite_from_spec


def test_generate_suite_from_spec_writes_packages_manifest_coverage_and_ebench(
    tmp_path: Path,
) -> None:
    spec_path = tmp_path / "suite_spec.yaml"
    write_yaml(
        spec_path,
        {
            "schema_version": "suite-spec/v0.2",
            "suite_id": "ebench_workbench_suite_v0",
            "domain": "scientific_workbench",
            "target": "ebench",
            "package_mode": "fat",
            "robot_profiles": ["franka_panda_tabletop_v1"],
            "num_tasks": 5,
            "task_families": {"pick_place": 2, "pipette_transfer_light": 3},
            "difficulties": {"easy": 2, "hard": 3},
            "splits": {"dev": 2, "test": 3},
            "variation_axes": ["layout", "instruction_language"],
            "validation": {
                "minimum_package_level": "adapter_static_validated",
                "require_asset_lock": True,
                "require_suite_coverage_report": True,
            },
        },
    )
    suite_dir = tmp_path / "suite"

    result = generate_suite_from_spec(spec_path, suite_dir)

    suite_manifest = load_yaml(suite_dir / "suite_manifest.yaml")
    coverage = load_yaml(suite_dir / "evidence" / "suite_coverage.yaml")
    validation = load_yaml(suite_dir / "evidence" / "suite_validation_report.yaml")
    first_package = Path(suite_manifest["packages"][0]["path"])

    assert result.package_count == 5
    assert len(suite_manifest["packages"]) == 5
    assert Counter(item["task_family"] for item in suite_manifest["packages"]) == {
        "pick_place": 2,
        "pipette_transfer_light": 3,
    }
    assert Counter(item["difficulty"] for item in suite_manifest["packages"]) == {
        "easy": 2,
        "hard": 3,
    }
    assert Counter(item["split"] for item in suite_manifest["packages"]) == {"dev": 2, "test": 3}
    assert (first_package / "locks" / "asset_lock.yaml").exists()
    assert (first_package / "adapters" / "ebench" / "package.yaml").exists()
    assert (suite_dir / "locks" / "suite_asset_lock.yaml").exists()
    assert (suite_dir / "adapters" / "ebench" / "task_index.yaml").exists()
    assert coverage["package_count"] == 5
    assert validation["status"] == "passed"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

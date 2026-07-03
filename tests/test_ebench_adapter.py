from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.exporter import EBenchExportError, export_ebench_package
from scenario_forge.scaffold import scaffold_starter_package


def test_export_ebench_package_writes_descriptor_and_report(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")

    result = export_ebench_package(package_dir)

    export_yaml = load_yaml(package_dir / "adapters" / "ebench" / "package.yaml")
    task_entrypoint = load_yaml(package_dir / "adapters" / "ebench" / "task_entrypoint.yaml")
    report = load_yaml(package_dir / "adapters" / "ebench" / "adapter_report.yaml")

    assert result.ok
    assert result.output_dir == package_dir / "adapters" / "ebench"
    assert package_dir / "adapters" / "ebench" / "package.yaml" in result.artifacts
    assert export_yaml["schema_version"] == "ebench-scenario-export/v0.1"
    assert export_yaml["source_package"]["package_id"] == "tabletop_pick_place_starter"
    assert export_yaml["entrypoints"]["scene_usd"] == "../../scene/main.usda"
    assert export_yaml["entrypoints"]["task"] == "../../task/task.yaml"
    assert export_yaml["entrypoints"]["metrics"] == "../../metrics/metrics.yaml"
    assert export_yaml["assets"]["asset_lock"] == "../../locks/asset_lock.yaml"
    assert export_yaml["runtime_hints"]["success_metric"] == "task_success"
    assert task_entrypoint["task_family"] == "pick_place"
    assert task_entrypoint["success_metric"] == "task_success"
    assert report["status"] == "passed"
    assert report["blockers"] == []
    assert "scene_usd" in report["entrypoints"]
    assert "asset_lock" in report["entrypoints"]


def test_export_ebench_package_fails_without_asset_lock(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    (package_dir / "locks" / "asset_lock.yaml").unlink()

    with pytest.raises(EBenchExportError, match="Missing required EBench file: locks/asset_lock.yaml"):
        export_ebench_package(package_dir)


def test_export_ebench_package_fails_without_scene_usd(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    (package_dir / "scene" / "main.usda").unlink()

    with pytest.raises(EBenchExportError, match="Missing required EBench file: scene/main.usda"):
        export_ebench_package(package_dir)


def test_export_ebench_package_fails_without_primary_success_metric(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")
    metrics = load_yaml(package_dir / "metrics" / "metrics.yaml")
    metrics["metrics"][0].pop("role")
    write_yaml(package_dir / "metrics" / "metrics.yaml", metrics)

    with pytest.raises(EBenchExportError, match="Missing primary success metric"):
        export_ebench_package(package_dir)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

from pathlib import Path

import yaml

from scenario_forge.adapters.ebench import export_ebench_package
from scenario_forge.adapters.real2sim.importer import import_real2sim_result
from scenario_forge.generation.cousins.cousin_generator import generate_cousin_packages


def test_import_real2sim_result_writes_twin_package_and_exports_ebench(tmp_path: Path) -> None:
    source_object = write_usd(tmp_path / "object.usd", "real_object")
    source_zone = write_usd(tmp_path / "target.usd", "real_target")
    result_yaml = tmp_path / "real2sim_result.yaml"
    write_yaml(
        result_yaml,
        {
            "schema_version": "real2sim-result/v0.1",
            "result_id": "real_workbench_scan_001_result",
            "source": {"type": "video", "uri": "file://inputs/workbench.mp4"},
            "package": {
                "package_id": "real_workbench_twin_001",
                "scenario_domain": "scientific_workbench",
                "robot_profile": "franka_panda_tabletop_v1",
                "task_family": "pick_place",
            },
            "assets": [
                {
                    "asset_id": "real_object_asset",
                    "role": "manipulated_object",
                    "asset_type": "reconstructed_object",
                    "source_usd": str(source_object),
                    "license": "Apache-2.0",
                },
                {
                    "asset_id": "real_target_asset",
                    "role": "target_region",
                    "asset_type": "reconstructed_marker",
                    "source_usd": str(source_zone),
                    "license": "Apache-2.0",
                },
            ],
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "real_object_asset",
                    "role": "manipulated_object",
                    "pose": {"xyz": [0.42, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["pickable"],
                },
                {
                    "id": "target_zone",
                    "asset_id": "real_target_asset",
                    "role": "target_region",
                    "pose": {"xyz": [0.62, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["zone", "target"],
                },
            ],
        },
    )

    package_dir = tmp_path / "real_workbench_twin_001"
    result = import_real2sim_result(result_yaml, package_dir)
    export = export_ebench_package(package_dir)

    manifest = load_yaml(package_dir / "manifest.yaml")
    asset_manifest = load_yaml(package_dir / "assets" / "asset_manifest.yaml")
    instances = load_yaml(package_dir / "scene" / "instances.yaml")
    provenance = load_yaml(package_dir / "provenance" / "source_refs.yaml")
    import_evidence = load_yaml(package_dir / "evidence" / "real2sim_import.yaml")

    assert result.package_id == "real_workbench_twin_001"
    assert result.imported_asset_ids == ("real_object_asset", "real_target_asset")
    assert manifest["package_id"] == "real_workbench_twin_001"
    assert asset_manifest["assets"][0]["canonical_usd"].startswith("assets/reconstructed/")
    assert instances["instances"][0]["pose"]["xyz"] == [0.42, 0.0, 0.92]
    assert provenance["sources"][0]["uri"] == "file://inputs/workbench.mp4"
    assert import_evidence["status"] == "passed"
    assert export.ok


def test_generate_cousin_packages_preserves_predicates_and_records_variation(
    tmp_path: Path,
) -> None:
    package_dir = make_real2sim_package(tmp_path)
    plan_path = tmp_path / "cousin_plan.yaml"
    write_yaml(
        plan_path,
        {
            "schema_version": "cousin-plan/v0.1",
            "base_package": str(package_dir),
            "cousins": {"count": 2},
            "variation_axes": [{"type": "pose_perturbation", "max_translation_m": 0.1}],
            "constraints": [
                {"preserve_success_predicates": True},
                {"require_asset_lock": True},
            ],
        },
    )

    suite_dir = tmp_path / "cousins"
    result = generate_cousin_packages(package_dir, plan_path, suite_dir)

    first_cousin = suite_dir / "packages" / "real_workbench_twin_001_cousin_000"
    base_predicates = load_yaml(package_dir / "task" / "predicates.yaml")
    cousin_predicates = load_yaml(first_cousin / "task" / "predicates.yaml")
    variation = load_yaml(first_cousin / "provenance" / "cousin_variation.yaml")
    suite_manifest = load_yaml(suite_dir / "suite_manifest.yaml")

    assert result.package_count == 2
    assert cousin_predicates["success_predicates"] == base_predicates["success_predicates"]
    assert variation["variation_axes"][0]["type"] == "pose_perturbation"
    assert suite_manifest["packages"][0]["package_id"] == "real_workbench_twin_001_cousin_000"


def make_real2sim_package(tmp_path: Path) -> Path:
    source_object = write_usd(tmp_path / "object.usd", "real_object")
    source_zone = write_usd(tmp_path / "target.usd", "real_target")
    result_yaml = tmp_path / "real2sim_result.yaml"
    write_yaml(
        result_yaml,
        {
            "schema_version": "real2sim-result/v0.1",
            "result_id": "real_workbench_scan_001_result",
            "source": {"type": "video", "uri": "file://inputs/workbench.mp4"},
            "package": {
                "package_id": "real_workbench_twin_001",
                "scenario_domain": "scientific_workbench",
                "robot_profile": "franka_panda_tabletop_v1",
                "task_family": "pick_place",
            },
            "assets": [
                {
                    "asset_id": "real_object_asset",
                    "role": "manipulated_object",
                    "asset_type": "reconstructed_object",
                    "source_usd": str(source_object),
                    "license": "Apache-2.0",
                },
                {
                    "asset_id": "real_target_asset",
                    "role": "target_region",
                    "asset_type": "reconstructed_marker",
                    "source_usd": str(source_zone),
                    "license": "Apache-2.0",
                },
            ],
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "real_object_asset",
                    "role": "manipulated_object",
                    "pose": {"xyz": [0.42, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["pickable"],
                },
                {
                    "id": "target_zone",
                    "asset_id": "real_target_asset",
                    "role": "target_region",
                    "pose": {"xyz": [0.62, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["zone", "target"],
                },
            ],
        },
    )
    package_dir = tmp_path / "real_workbench_twin_001"
    import_real2sim_result(result_yaml, package_dir)
    return package_dir


def write_usd(path: Path, prim_name: str) -> Path:
    path.write_text(f'#usda 1.0\n\ndef Xform "{prim_name}"\n{{\n}}\n', encoding="utf-8")
    return path


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

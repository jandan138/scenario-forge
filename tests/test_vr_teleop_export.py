from __future__ import annotations

import ast
import json
from pathlib import Path

from scenario_forge.adapters.vr_teleop import export_vr_teleop_package
from scenario_forge.adapters.convert_asset import load_convert_asset_package_handoff
from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from tests.test_scenario_package_compiler import _write_source_scene
from tests.test_scenario_spec import _scenario_mapping
from tests.test_convert_asset_adapter import _write_static_support_handoff


def _build_shared_profile_package(tmp_path: Path) -> Path:
    source = _write_source_scene(tmp_path)
    scenario = _scenario_mapping()
    scenario["robot"] = dict(scenario["robot"])  # type: ignore[arg-type]
    scenario["robot"]["profile_ref"] = "manip/lift2/R5a_isaac41_vr600_v1"  # type: ignore[index]
    objects = [dict(item) for item in scenario["objects"]]  # type: ignore[arg-type]
    objects[0]["asset_id"] = "qualified_table"
    scenario["objects"] = objects
    table_source, table_package, table_manifest, _ = _write_static_support_handoff(
        tmp_path / "table_handoff"
    )
    table = load_convert_asset_package_handoff(
        table_package,
        table_manifest,
        table_source,
        expected_scope_prims=("/World/table",),
        producer_revision="static-support-r1",
        usage="static_support_object",
    ).to_local_usd_asset_source(
        asset_id="qualified_table",
        license="CC-BY-NC-4.0",
    )
    package_root = tmp_path / "package"
    compile_scenario_package(
        ScenarioSpec.from_mapping(scenario),
        {
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=source,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://environment",
                redistributable=False,
            ),
            "qualified_table": table,
        },
        package_root,
    )
    return package_root


def _build_generic_task_package(tmp_path: Path) -> Path:
    source = _write_source_scene(tmp_path)
    scenario = _scenario_mapping()
    scenario["scenario_id"] = "scientific_workbench_generic_task"
    scenario["robot"] = dict(scenario["robot"])  # type: ignore[arg-type]
    scenario["robot"]["profile_ref"] = "manip/lift2/R5a_isaac41_vr600_v1"  # type: ignore[index]
    objects = [dict(item) for item in scenario["objects"]]  # type: ignore[arg-type]
    objects[0]["asset_id"] = "qualified_table"
    objects[1]["role"] = "target_container"
    objects[2]["role"] = "stirring_tool"
    scenario["objects"] = objects
    table_source, table_package, table_manifest, _ = _write_static_support_handoff(
        tmp_path / "table_handoff"
    )
    table = load_convert_asset_package_handoff(
        table_package,
        table_manifest,
        table_source,
        expected_scope_prims=("/World/table",),
        producer_revision="static-support-r1",
        usage="static_support_object",
    ).to_local_usd_asset_source(
        asset_id="qualified_table",
        license="CC-BY-NC-4.0",
    )
    package_root = tmp_path / "generic-package"
    compile_scenario_package(
        ScenarioSpec.from_mapping(scenario),
        {
            "scientific_workbench_environment": LocalUSDAssetSource(
                asset_id="scientific_workbench_environment",
                source_usd=source,
                role="environment",
                license="CC-BY-NC-4.0",
                source_uri="example://environment",
                redistributable=False,
            ),
            "qualified_table": table,
        },
        package_root,
    )
    return package_root


def test_vr_export_uses_same_recipe_and_never_authors_a_local_table_slab(
    tmp_path: Path,
) -> None:
    package_root = _build_shared_profile_package(tmp_path)

    result = export_vr_teleop_package(package_root, tmp_path / "vr-r2")

    scene = (result.output_dir / "scene.usd").read_text(encoding="utf-8")
    assert "__support_surface_collision" not in scene
    assert "PhysicsCollisionAPI" not in scene
    assert "@deps/table/asset.usd@</World/table>" in scene
    assert "@deps/environment/asset.usd@</World>" in scene
    assert "@deps/source_container/asset.usd@</World/conical_bottle03>" in scene
    assert "@deps/target_container/asset.usd@</World/graduated_cylinder_03>" in scene
    assert (result.output_dir / "deps/table/asset.usd").is_file()

    task_config = (result.output_dir / "task_config.py").read_text(encoding="utf-8")
    ast.parse(task_config)
    assert task_config.startswith("# Merge this TASKS entry")
    assert "TASKS = {" in task_config
    assert '"scene_usd_file_path"' in task_config
    assert '"/World/_scene/obj_conical_bottle03"' in task_config
    assert '"SolverType": "TGS"' in task_config
    assert '"TimeStepsPerSecond": 60' in task_config
    assert '"set_robot_contact_offset": 0.05' in task_config
    assert '"set_robot_rest_offset": 0.001' in task_config

    parity = json.loads((result.output_dir / "parity_manifest.json").read_text(encoding="utf-8"))
    assert parity["status"] == "pass_with_declared_exception"
    assert parity["canonical_scenario_id"] == "scientific_workbench_bimanual_pour"
    assert parity["equivalence"]["table_static_support"] == "same_asset_and_pose"
    assert parity["allowed_exceptions"] == [
        {
            "id": "robot_joint_initialization",
            "status": "accepted",
            "reason": (
                "The Feishu VR config contract exposes robot base pose but no joint-position field; "
                "the shared robot model and contact/PhysX profile remain identical."
            ),
        }
    ]


def test_vr_export_supports_generic_non_pour_task_objects(tmp_path: Path) -> None:
    package_root = _build_generic_task_package(tmp_path)

    result = export_vr_teleop_package(
        package_root,
        tmp_path / "vr-generic",
        task_id="scientific_workbench_generic_task",
    )

    scene = result.scene_usd.read_text(encoding="utf-8")
    assert "@deps/objects/obj_conical_bottle03/asset.usd@" in scene
    assert "@deps/objects/obj_graduated_cylinder_03/asset.usd@" in scene
    task_config = result.task_config.read_text(encoding="utf-8")
    ast.parse(task_config)
    assert '"/World/_scene/obj_conical_bottle03"' in task_config
    assert '"/World/_scene/obj_graduated_cylinder_03"' in task_config

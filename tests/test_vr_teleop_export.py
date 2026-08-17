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


def _build_shared_profile_package(tmp_path: Path, *, with_context: bool = False) -> Path:
    source = _write_source_scene(tmp_path)
    scenario = _scenario_mapping()
    scenario["robot"] = dict(scenario["robot"])  # type: ignore[arg-type]
    scenario["robot"]["profile_ref"] = "manip/lift2/R5a_isaac41_vr600_v1"  # type: ignore[index]
    objects = [dict(item) for item in scenario["objects"]]  # type: ignore[arg-type]
    objects[0]["asset_id"] = "qualified_table"
    context_source = source
    if with_context:
        context_dir = tmp_path / "context_source"
        context_dir.mkdir()
        context_source = context_dir / "context.usda"
        context_source.write_text(
            source.read_text(encoding="utf-8").replace(
                "conical_bottle03", "context_beaker"
            ),
            encoding="utf-8",
        )
        objects.append(
            {
                "id": "context_beaker",
                "asset_id": "context_prop_asset",
                "source_prim_path": "/World/context_beaker",
                "role": "context_prop",
                "pose": {
                    "xyz": [0.72, 0.24, 0.82],
                    "wxyz": [1.0, 0.0, 0.0, 0.0],
                    "scale_xyz": [1.0, 1.0, 1.0],
                },
                "metadata": {
                    "dressing_preset_id": "example4-default-v1",
                    "group_id": "far-right-glassware",
                    "metric_participation": "none",
                },
            }
        )
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
            **(
                {
                    "context_prop_asset": LocalUSDAssetSource(
                        asset_id="context_prop_asset",
                        source_usd=context_source,
                        role="dynamic_context_object",
                        license="CC-BY-NC-4.0",
                        source_uri="example://context-prop",
                        redistributable=False,
                    )
                }
                if with_context
                else {}
            ),
        },
        package_root,
    )
    return package_root


def test_vr_context_prop_is_a_randomizable_object(tmp_path: Path) -> None:
    package_root = _build_shared_profile_package(tmp_path, with_context=True)

    result = export_vr_teleop_package(package_root, tmp_path / "vr-context")

    scene = result.scene_usd.read_text(encoding="utf-8")
    config = result.task_config.read_text(encoding="utf-8")
    parity = json.loads(result.parity_manifest.read_text(encoding="utf-8"))
    assert "@deps/context/context_beaker/asset.usd@" in scene
    assert 'def Xform "obj_context_beaker"' in scene
    assert '"/World/_scene/obj_context_beaker"' in config
    namespace: dict[str, object] = {"_ASSETS_DIR": Path("/tmp/assets")}
    exec(config, namespace)
    task = namespace["TASKS"]["scientific_workbench_pour_flask_to_cylinder"]  # type: ignore[index]
    assert {"objs": ["obj_context_beaker"], "mode": "local", "yaw_range_degrees": [0.0, 0.0], "x_offset_range": [-0.01, 0.01], "y_offset_range": [-0.01, 0.01]} in task["layout_randomization"]["objects"]  # type: ignore[index]
    assert parity["equivalence"]["context_props"] == (
        "same_assets_poses_and_physics_in_randomizable_object_list"
    )


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
    assert 'def Xform "_scene"' not in scene
    assert 'def Xform "background"' in scene
    assert 'def Xform "table"' in scene
    assert 'def DomeLight "vr_direct_open_light"' in scene
    assert "float inputs:intensity = 750" in scene
    assert (result.output_dir / "deps/table/asset.usd").is_file()

    task_config = (result.output_dir / "task_config.py").read_text(encoding="utf-8")
    ast.parse(task_config)
    assert task_config.startswith("# Merge this TASKS entry")
    assert "TASKS = {" in task_config
    assert '"scene_usd_file_path"' in task_config
    assert '"/World/_scene/obj_conical_bottle03"' in task_config
    assert '"table": "table"' in task_config
    assert '"mode": "local"' in task_config
    namespace: dict[str, object] = {"_ASSETS_DIR": Path("/tmp/assets")}
    exec(task_config, namespace)
    randomization = namespace["TASKS"]["scientific_workbench_pour_flask_to_cylinder"]["layout_randomization"]  # type: ignore[index]
    assert randomization["table"] == "table"
    assert all(item["x_offset_range"] == [-0.01, 0.01] for item in randomization["objects"])
    assert all(item["y_offset_range"] == [-0.01, 0.01] for item in randomization["objects"])
    assert all(item["yaw_range_degrees"] == [0.0, 0.0] for item in randomization["objects"])
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
    assert "obj_obj_" not in scene


def test_vr_randomization_groups_objects_from_metadata(tmp_path: Path) -> None:
    package_root = _build_generic_task_package(tmp_path)
    recipe = package_root / "scenario.yaml"
    raw = __import__("yaml").safe_load(recipe.read_text(encoding="utf-8"))
    for item in raw["objects"]:
        if item["id"] in {"obj_conical_bottle03", "obj_graduated_cylinder_03"}:
            item.setdefault("metadata", {})["vr_randomization_group"] = "assembly"
    recipe.write_text(__import__("yaml").safe_dump(raw, sort_keys=False), encoding="utf-8")

    result = export_vr_teleop_package(
        package_root,
        tmp_path / "vr-grouped",
        task_id="scientific_workbench_generic_task",
    )

    namespace: dict[str, object] = {"_ASSETS_DIR": Path("/tmp/assets")}
    exec(result.task_config.read_text(encoding="utf-8"), namespace)
    config = namespace["TASKS"]["scientific_workbench_generic_task"]  # type: ignore[index]
    groups = config["layout_randomization"]["objects"]  # type: ignore[index]
    assert groups == [
        {
            "objs": ["obj_conical_bottle03", "obj_graduated_cylinder_03"],
            "mode": "local",
            "yaw_range_degrees": [0.0, 0.0],
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
        }
    ]

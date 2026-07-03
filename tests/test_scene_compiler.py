from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from scenario_forge.scene.instance_binding import (
    SceneInstanceError,
    load_scene_instances,
)
from scenario_forge.scene.usd_compiler import USDSceneCompilerError, compile_usd_scene
from scenario_forge.validation.usd_checks import check_usd_scene


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_asset(path: Path, source: str = "#usda 1.0\n") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return f"sha256:{sha256(path.read_bytes()).hexdigest()}"


def make_scene_package(root: Path) -> Path:
    package_dir = root / "scene_pkg"
    model = package_dir / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd"
    digest = write_asset(model)
    write_yaml(
        package_dir / "locks" / "asset_lock.yaml",
        {
            "schema_version": "asset-lock/v0.2",
            "lock_id": "scene_pkg_asset_lock",
            "created_by": "scenario-forge",
            "assets": {
                "sample_bottle_50ml_v1": {
                    "source_kind": "package_local",
                    "source_uri": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "resolved_path": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "content_sha256": digest,
                    "license": "CC-BY-4.0",
                    "resolver_version": "scenario-forge/test",
                }
            },
        },
    )
    write_yaml(
        package_dir / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "coordinate_system": {"units": "meters", "up_axis": "Z"},
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "sample_bottle_50ml_v1",
                    "role": "manipulated_object",
                    "pose": {"xyz": [0.45, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "semantic_tags": ["bottle", "pickable"],
                    "initial_state": {"upright": True},
                }
            ],
        },
    )
    write_yaml(
        package_dir / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"type": "object_at_pose", "object": "object_001"},
            ],
        },
    )
    write_yaml(
        package_dir / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": "franka_tabletop",
            "spawn": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )
    return package_dir


def test_load_scene_instances_reads_pose_and_tags(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)

    instances = load_scene_instances(package_dir / "scene" / "instances.yaml")

    assert len(instances) == 1
    assert instances[0].instance_id == "object_001"
    assert instances[0].asset_id == "sample_bottle_50ml_v1"
    assert instances[0].role == "manipulated_object"
    assert instances[0].xyz == (0.45, 0.0, 0.92)
    assert instances[0].wxyz == (1.0, 0.0, 0.0, 0.0)
    assert instances[0].semantic_tags == ("bottle", "pickable")


def test_load_scene_instances_rejects_duplicate_instance_ids(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "asset_a",
                    "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
                {
                    "id": "object_001",
                    "asset_id": "asset_b",
                    "pose": {"xyz": [1.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
            ],
        },
    )

    with pytest.raises(SceneInstanceError, match="Duplicate scene instance id: object_001"):
        load_scene_instances(tmp_path / "scene" / "instances.yaml")


def test_load_scene_instances_rejects_invalid_pose_shape(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                {
                    "id": "object_001",
                    "asset_id": "asset_a",
                    "pose": {"xyz": [0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                }
            ],
        },
    )

    with pytest.raises(SceneInstanceError, match="pose.xyz"):
        load_scene_instances(tmp_path / "scene" / "instances.yaml")


def test_compile_usd_scene_writes_locked_references_and_custom_data(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)

    result = compile_usd_scene(
        package_root=package_dir,
        instances_path=package_dir / "scene" / "instances.yaml",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        out_path=package_dir / "scene" / "main.usda",
    )

    source = result.path.read_text(encoding="utf-8")
    assert result.path == package_dir / "scene" / "main.usda"
    assert result.instance_count == 1
    assert result.references == ("assets/objects/sample_bottle_50ml_v1/model.usd",)
    assert 'def Xform "object_001"' in source
    assert "instance_id = \"object_001\"" in source
    assert "asset_id = \"sample_bottle_50ml_v1\"" in source
    assert "role = \"manipulated_object\"" in source
    assert 'semantic_tags = ["bottle", "pickable"]' in source
    assert "@../assets/objects/sample_bottle_50ml_v1/model.usd@" in source
    assert 'def Xform "RobotSpawn"' in source
    assert 'def DistantLight "KeyLight"' in source
    assert 'def Camera "Camera"' in source


def test_compile_usd_scene_rejects_unresolved_asset_id(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)
    instances = yaml.safe_load((package_dir / "scene" / "instances.yaml").read_text(encoding="utf-8"))
    instances["instances"][0]["asset_id"] = "missing_asset"
    write_yaml(package_dir / "scene" / "instances.yaml", instances)

    with pytest.raises(USDSceneCompilerError, match="Unresolved asset_id for object_001: missing_asset"):
        compile_usd_scene(
            package_root=package_dir,
            instances_path=package_dir / "scene" / "instances.yaml",
            asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
            out_path=package_dir / "scene" / "main.usda",
        )


def test_check_usd_scene_accepts_compiled_scene(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)
    compile_usd_scene(
        package_root=package_dir,
        instances_path=package_dir / "scene" / "instances.yaml",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        out_path=package_dir / "scene" / "main.usda",
    )

    report = check_usd_scene(
        package_root=package_dir,
        scene_path=package_dir / "scene" / "main.usda",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        instances_path=package_dir / "scene" / "instances.yaml",
        predicates_path=package_dir / "task" / "predicates.yaml",
    )

    assert report.ok
    assert report.messages == ()


def test_check_usd_scene_rejects_unlocked_reference(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)
    compile_usd_scene(
        package_root=package_dir,
        instances_path=package_dir / "scene" / "instances.yaml",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        out_path=package_dir / "scene" / "main.usda",
    )
    (package_dir / "scene" / "main.usda").write_text(
        '#usda 1.0\nrel references = @../assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )

    report = check_usd_scene(
        package_root=package_dir,
        scene_path=package_dir / "scene" / "main.usda",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        instances_path=package_dir / "scene" / "instances.yaml",
    )

    assert not report.ok
    assert "USD reference is not locked: assets/objects/extra/model.usd" in report.messages


def test_check_usd_scene_rejects_missing_predicate_instance_binding(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)
    compile_usd_scene(
        package_root=package_dir,
        instances_path=package_dir / "scene" / "instances.yaml",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        out_path=package_dir / "scene" / "main.usda",
    )
    write_yaml(
        package_dir / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [{"type": "object_at_pose", "object": "missing_object"}],
        },
    )

    report = check_usd_scene(
        package_root=package_dir,
        scene_path=package_dir / "scene" / "main.usda",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        instances_path=package_dir / "scene" / "instances.yaml",
        predicates_path=package_dir / "task" / "predicates.yaml",
    )

    assert not report.ok
    assert "Predicate binding references missing instance 'missing_object'" in report.messages

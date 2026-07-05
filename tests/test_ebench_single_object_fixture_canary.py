from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.generation.ebench_canary.single_object_fixture import (
    generate_single_object_fixture_canary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_mesh_usda(path: Path, *, prim_name: str) -> None:
    path.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                '    defaultPrim = "World"',
                "    metersPerUnit = 1",
                '    upAxis = "Z"',
                ")",
                "",
                'def Xform "World"',
                "{",
                f'    def Mesh "{prim_name}"',
                "    {",
                "        point3f[] points = [(0, 0, 0), (0.1, 0.1, 0.1)]",
                "        int[] faceVertexCounts = []",
                "        int[] faceVertexIndices = []",
                "    }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_fixture_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "soap": "manipulated_object",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        _write_mesh_usda(source, prim_name=f"{name}_mesh")
        assets[name] = {
            "role": role,
            "source_path": str(source),
            "license": "research-use",
        }
    camera = tmp_path / "fixed_camera_lift2_simbox.yml"
    camera.write_text("cameras: []\n", encoding="utf-8")
    assets["camera_yaml"] = {
        "role": "camera_config",
        "source_path": str(camera),
        "license": "research-use",
    }
    source_manifest = tmp_path / "soap_to_dish_asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "package_id": "ebench_soap_to_dish_canary",
                "task_id": "mobile_manip/soap_to_dish",
                "task_family": "pick_place",
                "instruction": (
                    "Pick up the bar of soap from the bathtub edge and place it "
                    "into the soap dish."
                ),
                "assets": assets,
                "fixture_task": {
                    "manipulated_asset_key": "soap",
                    "manipulated_asset_id": "official_ebench_soap",
                    "manipulated_instance_id": "soap_001",
                    "target_fixture": {
                        "instance_id": "soap_dish_fixture",
                        "source_uid": "_01",
                        "role": "target_container",
                        "semantic_label": "soap_dish",
                    },
                    "success_metric_id": "soap_in_dish",
                    "success_predicate": "object_in_container",
                    "object_pose": {
                        "xyz": [-0.35, -0.2, 0.05],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                        "scale_xyz": [1.0, 1.0, 1.0],
                    },
                    "robot_spawn": {
                        "xyz": [-1.02, 0.0, 0.31],
                        "wxyz": [1.0, 0.0, 0.0, 0.0],
                    },
                    "source_task_config": (
                        "/cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/"
                        "tasks/ebench/mobile_manip/test_mini/soap_to_dish.yml"
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_generates_single_object_scene_fixture_canary(tmp_path: Path) -> None:
    source_manifest = _write_fixture_source_manifest(tmp_path)
    package_dir = tmp_path / "out" / "ebench_soap_to_dish_canary"

    result = generate_single_object_fixture_canary(source_manifest, package_dir)

    assert result.package_root == package_dir
    assert result.scene_usd == package_dir / "scene/main.usda"

    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "official_ebench_scene" in scene
    assert "official_ebench_robot" in scene
    assert "official_ebench_soap" in scene
    assert "target_marker" not in scene

    lock = yaml.safe_load((package_dir / "locks/asset_lock.yaml").read_text(encoding="utf-8"))
    assert set(lock["assets"]) == {
        "official_ebench_scene",
        "official_ebench_robot",
        "official_ebench_soap",
    }
    assert lock["assets"]["official_ebench_soap"]["source_kind"] == "official_ebench_asset"

    instances = yaml.safe_load((package_dir / "scene/instances.yaml").read_text(encoding="utf-8"))
    assert [instance["id"] for instance in instances["instances"]] == [
        "environment_scene",
        "lift2_robot_asset",
        "soap_001",
    ]
    by_id = {instance["id"]: instance for instance in instances["instances"]}
    assert by_id["soap_001"]["asset_id"] == "official_ebench_soap"
    assert by_id["soap_001"]["pose"]["xyz"] == [-0.35, -0.2, 0.05]
    assert instances["fixture_bindings"] == {
        "target_container": {
            "instance_id": "soap_dish_fixture",
            "source_uid": "_01",
            "role": "target_container",
            "semantic_label": "soap_dish",
            "fixture_kind": "environment_fixture",
            "source_asset_id": "official_ebench_scene",
        }
    }

    task = yaml.safe_load((package_dir / "task/task.yaml").read_text(encoding="utf-8"))
    assert task["task_id"] == "mobile_manip/soap_to_dish"
    assert task["bindings"] == {
        "object": "soap_001",
        "target_container": "soap_dish_fixture",
    }
    assert task["target_fixture"]["source_uid"] == "_01"

    metrics = yaml.safe_load((package_dir / "metrics/metrics.yaml").read_text(encoding="utf-8"))
    primary_metric = metrics["metrics"][0]
    assert primary_metric["id"] == "soap_in_dish"
    assert primary_metric["predicate"] == "object_in_container"
    assert primary_metric["object"] == "soap_001"
    assert primary_metric["container"] == "soap_dish_fixture"
    assert primary_metric["adapter_hints"]["ebench"]["container"] == "soap_dish_fixture"

    contract = yaml.safe_load((package_dir / "task/task_contract.yaml").read_text(encoding="utf-8"))
    assert contract["package_id"] == "ebench_soap_to_dish_canary"
    assert contract["task_semantics"]["target_container"] == {
        "instance_id": "soap_dish_fixture",
        "asset_id": "official_ebench_scene",
        "role": "target_container",
        "source_uid": "_01",
        "semantic_label": "soap_dish",
        "fixture_kind": "environment_fixture",
    }
    assert contract["success_predicate"]["container"] == "soap_dish_fixture"
    assert contract["success_predicate"]["claim_boundary"] == (
        "portable predicate binding only; target is an environment fixture; "
        "not an executed task success result"
    )

    adapter = yaml.safe_load((package_dir / "adapters/ebench/package.yaml").read_text(encoding="utf-8"))
    task_entrypoint = yaml.safe_load(
        (package_dir / "adapters/ebench/task_entrypoint.yaml").read_text(encoding="utf-8")
    )
    assert adapter["source_package"]["package_id"] == "ebench_soap_to_dish_canary"
    assert task_entrypoint["success_metric"] == "soap_in_dish"


def test_cli_generates_single_object_fixture_canary(tmp_path: Path) -> None:
    source_manifest = _write_fixture_source_manifest(tmp_path)
    out_dir = tmp_path / "generated"

    code = main(
        [
            "ebench",
            "canary",
            "single-object-fixture",
            "--asset-sources",
            str(source_manifest),
            "--out",
            str(out_dir),
        ]
    )

    assert code == 0
    assert (out_dir / "scene/main.usda").exists()
    assert (out_dir / "task/task_contract.yaml").exists()
    assert (out_dir / "adapters/ebench/package.yaml").exists()


def test_remote_to_holder_example_preserves_genmanip_wxyz_orientation() -> None:
    source_manifest = REPO_ROOT / "examples" / "ebench_remote_to_holder_asset_sources.yaml"
    data = yaml.safe_load(source_manifest.read_text(encoding="utf-8"))

    remote_pose = data["fixture_task"]["object_pose"]

    assert remote_pose["wxyz"] == [0.11, 0.11, 0.70710677, 0.70710677]


def test_remote_to_holder_example_places_remote_on_task5_tabletop() -> None:
    source_manifest = REPO_ROOT / "examples" / "ebench_remote_to_holder_asset_sources.yaml"
    data = yaml.safe_load(source_manifest.read_text(encoding="utf-8"))

    remote_pose = data["fixture_task"]["object_pose"]

    assert remote_pose["xyz"] == [-0.25, -0.4, 0.0142]

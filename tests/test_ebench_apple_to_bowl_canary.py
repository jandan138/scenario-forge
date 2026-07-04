from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.generation.ebench_canary.apple_to_bowl import generate_apple_to_bowl_canary


def _write_mesh_usda(path: Path, *, points: list[tuple[float, float, float]], prim_name: str) -> None:
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
                "        point3f[] points = [",
                *[
                    f"            ({x}, {y}, {z}),"
                    for x, y, z in points
                ],
                "        ]",
                "        int[] faceVertexCounts = []",
                "        int[] faceVertexIndices = []",
                "    }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _bbox_points(
    bbox_min: tuple[float, float, float],
    bbox_max: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    return [
        (x, y, z)
        for x in (bbox_min[0], bbox_max[0])
        for y in (bbox_min[1], bbox_max[1])
        for z in (bbox_min[2], bbox_max[2])
    ]


def _write_tiny_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        source.write_text("#usda 1.0\n", encoding="utf-8")
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
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def _write_tiny_official_bbox_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        if name == "scene":
            _write_mesh_usda(
                source,
                points=_bbox_points((-0.45, -0.8, -0.75), (0.45, 0.8, -0.000267)),
                prim_name="obj_table",
            )
        elif name == "apple":
            _write_mesh_usda(
                source,
                points=_bbox_points((0.0, -0.0458875, 0.0), (0.1, 0.055, 0.1)),
                prim_name="apple_mesh",
            )
        elif name == "bowl":
            _write_mesh_usda(
                source,
                points=_bbox_points((0.0, -0.05079625, 0.0), (0.1, 0.07, 0.1)),
                prim_name="bowl_mesh",
            )
        else:
            source.write_text("#usda 1.0\n", encoding="utf-8")
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
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_generates_real_asset_apple_to_bowl_package(tmp_path: Path) -> None:
    source_manifest = _write_tiny_official_bbox_source_manifest(tmp_path)
    package_dir = tmp_path / "out" / "ebench_apple_to_bowl_canary"

    result = generate_apple_to_bowl_canary(source_manifest, package_dir)

    assert result.package_root == package_dir
    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "official_ebench_apple" in scene
    assert "official_ebench_bowl" in scene
    assert "official_ebench_scene" in scene
    assert "official_ebench_robot" in scene
    assert "starter_rigid_object" not in scene
    assert "target_marker" not in scene

    lock = yaml.safe_load((package_dir / "locks/asset_lock.yaml").read_text(encoding="utf-8"))
    assert set(lock["assets"]) >= {
        "official_ebench_scene",
        "official_ebench_robot",
        "official_ebench_apple",
        "official_ebench_bowl",
    }
    assert lock["assets"]["official_ebench_apple"]["source_kind"] == "official_ebench_asset"
    assert lock["assets"]["official_ebench_bowl"]["source_kind"] == "official_ebench_asset"

    adapter = yaml.safe_load((package_dir / "adapters/ebench/package.yaml").read_text(encoding="utf-8"))
    task_entrypoint = yaml.safe_load(
        (package_dir / "adapters/ebench/task_entrypoint.yaml").read_text(encoding="utf-8")
    )
    assert adapter["source_package"]["package_id"] == "ebench_apple_to_bowl_canary"
    assert adapter["entrypoints"]["scene_usd"] == "../../scene/main.usda"
    assert task_entrypoint["task_id"] == "mobile_manip/apple_to_fruit_bowl"
    assert task_entrypoint["success_metric"] == "apple_in_bowl"


def test_apple_to_bowl_canary_uses_official_tabletop_bbox_pose(tmp_path: Path) -> None:
    source_manifest = _write_tiny_official_bbox_source_manifest(tmp_path)
    package_dir = tmp_path / "out" / "ebench_apple_to_bowl_canary"

    generate_apple_to_bowl_canary(source_manifest, package_dir)

    instances = yaml.safe_load((package_dir / "scene/instances.yaml").read_text(encoding="utf-8"))
    by_id = {instance["id"]: instance for instance in instances["instances"]}
    assert by_id["apple_001"]["pose"] == {
        "xyz": [-0.35, -0.22, 0.046443],
        "wxyz": [0.5, 0.5, 0.5, 0.5],
        "scale_xyz": [0.8, 0.8, 0.8],
    }
    assert by_id["bowl_001"]["pose"] == {
        "xyz": [-0.35, 0.24, 0.05037],
        "wxyz": [0.5, 0.5, 0.5, 0.5],
        "scale_xyz": [0.8, 0.8, 0.8],
    }

    layout_checks = yaml.safe_load(
        (package_dir / "evidence/layout_checks.yaml").read_text(encoding="utf-8")
    )
    assert layout_checks["official_tabletop_placement"]["placement_source_kind"] == (
        "official_tabletop_bbox_derived"
    )

    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "xformOp:scale = (0.8, 0.8, 0.8)" in scene


def test_cli_generates_apple_to_bowl_canary(tmp_path: Path) -> None:
    source_manifest = _write_tiny_official_bbox_source_manifest(tmp_path)
    out_dir = tmp_path / "generated"

    code = main(
        [
            "ebench",
            "canary",
            "apple-to-bowl",
            "--asset-sources",
            str(source_manifest),
            "--out",
            str(out_dir),
        ]
    )

    assert code == 0
    assert (out_dir / "scene/main.usda").exists()
    assert (out_dir / "adapters/ebench/package.yaml").exists()

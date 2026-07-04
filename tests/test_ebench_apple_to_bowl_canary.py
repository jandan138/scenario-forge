from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.generation.ebench_canary.apple_to_bowl import generate_apple_to_bowl_canary


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


def test_generates_real_asset_apple_to_bowl_package(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
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


def test_cli_generates_apple_to_bowl_canary(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
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

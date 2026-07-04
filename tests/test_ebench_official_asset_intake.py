from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.official_asset_intake import (
    load_official_asset_sources,
    materialize_official_asset_bundle,
)


def test_loads_apple_to_bowl_official_asset_sources(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    apple = tmp_path / "apple_bundle"
    apple.mkdir()
    apple_usd = apple / "apple.usd"
    apple_usd.write_text("#usda 1.0\n", encoding="utf-8")
    bowl = tmp_path / "bowl_bundle"
    bowl.mkdir()
    bowl_usd = bowl / "bowl.usd"
    bowl_usd.write_text("#usda 1.0\n", encoding="utf-8")

    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {
                        "role": "manipulated_object",
                        "source_path": str(apple_usd),
                        "license": "research-use",
                    },
                    "bowl": {
                        "role": "target_container",
                        "source_path": str(bowl_usd),
                        "license": "research-use",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_official_asset_sources(source)

    assert loaded.task_id == "mobile_manip/apple_to_fruit_bowl"
    assert loaded.assets["apple"].source_path == apple_usd
    assert loaded.assets["bowl"].source_path == bowl_usd


def test_rejects_missing_official_asset_source(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {
                        "role": "manipulated_object",
                        "source_path": str(tmp_path / "missing.usd"),
                        "license": "research-use",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing official asset source"):
        load_official_asset_sources(source)


def test_materializes_usd_bundle_with_subusds(tmp_path: Path) -> None:
    source_bundle = tmp_path / "source" / "apple_uid"
    texture_dir = source_bundle / "SubUSDs" / "textures"
    texture_dir.mkdir(parents=True)
    source_usd = source_bundle / "apple.usd"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    (texture_dir / "apple_texture.png").write_bytes(b"png")
    (source_bundle / "apple_annotation.json").write_text("{}", encoding="utf-8")
    target_root = tmp_path / "package"

    result = materialize_official_asset_bundle(
        source_path=source_usd,
        package_root=target_root,
        asset_id="official_ebench_apple",
        role="manipulated_object",
        license="research-use",
    )

    assert result.canonical_usd == "assets/official_ebench_apple/apple.usd"
    assert (target_root / result.canonical_usd).exists()
    assert (target_root / "assets/official_ebench_apple/SubUSDs/textures/apple_texture.png").exists()
    assert (target_root / "assets/official_ebench_apple/apple_annotation.json").exists()
    assert result.asset_manifest_entry()["source_kind"] == "official_ebench_asset"
    assert result.asset_manifest_entry()["source_uri"] == str(source_usd)

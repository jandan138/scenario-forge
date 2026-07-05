from pathlib import Path
import builtins
import sys

import pytest
import yaml

from scenario_forge.adapters.ebench.official_asset_intake import (
    audit_mdl_texture_closure,
    load_official_asset_sources,
    materialize_official_asset_bundle,
)


def _block_pxr_imports(monkeypatch) -> None:
    real_import = builtins.__import__
    for module_name in tuple(sys.modules):
        if module_name == "pxr" or module_name.startswith("pxr."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)

    def blocked_import(name, *args, **kwargs):
        if name == "pxr" or name.startswith("pxr."):
            raise ModuleNotFoundError("No module named 'pxr'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)


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


def test_materializes_sibling_sidecar_dependencies_under_asset_root(tmp_path: Path) -> None:
    collection_root = tmp_path / "remote_control"
    source_bundle = collection_root / "ready" / "remote0"
    source_bundle.mkdir(parents=True)
    dependency_texture = (
        collection_root
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae"
        / "SubUSDs"
        / "textures"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png"
    )
    dependency_texture.parent.mkdir(parents=True)
    dependency_texture.write_bytes(b"remote-texture")
    source_usd = source_bundle / "remote0.usda"
    source_usd.write_text(
        "\n".join(
            [
                "#usda 1.0",
                "(",
                '    defaultPrim = "World"',
                ")",
                'def Xform "World"',
                "{",
                '    asset inputs:file = @../../63f5007c-eae0-4718-b760-df6c25e0e4ae/SubUSDs/textures/63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png@',
                "}",
            ]
        ),
        encoding="utf-8",
    )
    target_root = tmp_path / "package"

    result = materialize_official_asset_bundle(
        source_path=source_usd,
        package_root=target_root,
        asset_id="official_ebench_remote_control",
        role="manipulated_object",
        license="research-use",
    )

    assert result.canonical_usd == "assets/official_ebench_remote_control/ready/remote0/remote0.usda"
    assert (target_root / result.canonical_usd).exists()
    assert (
        target_root
        / "assets"
        / "official_ebench_remote_control"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae"
        / "SubUSDs"
        / "textures"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png"
    ).exists()


def test_materializes_sibling_sidecar_dependencies_without_pxr(tmp_path: Path, monkeypatch) -> None:
    _block_pxr_imports(monkeypatch)
    collection_root = tmp_path / "remote_control"
    source_bundle = collection_root / "ready" / "remote0"
    source_bundle.mkdir(parents=True)
    dependency_texture = (
        collection_root
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae"
        / "SubUSDs"
        / "textures"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png"
    )
    dependency_texture.parent.mkdir(parents=True)
    dependency_texture.write_bytes(b"remote-texture")
    source_usd = source_bundle / "remote0.usda"
    source_usd.write_text(
        "\n".join(
            [
                "#usda 1.0",
                'def Xform "World"',
                "{",
                '    asset inputs:file = @../../63f5007c-eae0-4718-b760-df6c25e0e4ae/SubUSDs/textures/63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png@',
                "}",
            ]
        ),
        encoding="utf-8",
    )
    target_root = tmp_path / "package"

    result = materialize_official_asset_bundle(
        source_path=source_usd,
        package_root=target_root,
        asset_id="official_ebench_remote_control",
        role="manipulated_object",
        license="research-use",
    )

    assert result.canonical_usd == "assets/official_ebench_remote_control/ready/remote0/remote0.usda"
    assert (target_root / result.canonical_usd).exists()
    assert (
        target_root
        / "assets"
        / "official_ebench_remote_control"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae"
        / "SubUSDs"
        / "textures"
        / "63f5007c-eae0-4718-b760-df6c25e0e4ae_texture0.png"
    ).exists()


def test_audits_mdl_texture_closure_reports_missing_relative_textures(tmp_path: Path) -> None:
    bundle_root = tmp_path / "task3"
    material_dir = bundle_root / "SubUSDs" / "materials"
    texture_dir = bundle_root / "SubUSDs" / "textures"
    material_dir.mkdir(parents=True)
    texture_dir.mkdir(parents=True)
    (texture_dir / "present.jpg").write_bytes(b"jpg")
    material = material_dir / "MI_missing_texture.mdl"
    material.write_text(
        "\n".join(
            [
                'export material Example(',
                '    color present = texture_2d("../textures/present.jpg", ::tex::gamma_srgb, ""),',
                '    color missing = texture_2d("../textures/missing.jpg", ::tex::gamma_srgb, "")',
                ") = material();",
            ]
        ),
        encoding="utf-8",
    )

    audit = audit_mdl_texture_closure(bundle_root)

    assert audit["status"] == "failed"
    assert audit["missing_texture_count"] == 1
    assert audit["missing_textures"] == [
        {
            "material": "SubUSDs/materials/MI_missing_texture.mdl",
            "texture": "../textures/missing.jpg",
            "resolved_path": "SubUSDs/textures/missing.jpg",
        }
    ]


def test_audits_mdl_texture_closure_passes_when_textures_exist(tmp_path: Path) -> None:
    bundle_root = tmp_path / "task3"
    material_dir = bundle_root / "SubUSDs" / "materials"
    texture_dir = bundle_root / "SubUSDs" / "textures"
    material_dir.mkdir(parents=True)
    texture_dir.mkdir(parents=True)
    (texture_dir / "present.jpg").write_bytes(b"jpg")
    (material_dir / "MI_present_texture.mdl").write_text(
        'export material Example(color diffuse = texture_2d("../textures/present.jpg", ::tex::gamma_srgb, "")) = material();',
        encoding="utf-8",
    )

    audit = audit_mdl_texture_closure(bundle_root)

    assert audit["status"] == "passed"
    assert audit["missing_texture_count"] == 0
    assert audit["missing_textures"] == []

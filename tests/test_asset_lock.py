from pathlib import Path

import pytest
import yaml

from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.licenses import validate_license
from scenario_forge.assets.lock import check_asset_lock, generate_asset_lock, write_asset_lock
from scenario_forge.assets.manifest import AssetManifestError, load_asset_manifest


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def make_asset_manifest_package(tmp_path: Path, content: str = "#usda 1.0\n") -> Path:
    model = tmp_path / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd"
    model.parent.mkdir(parents=True)
    model.write_text(content, encoding="utf-8")
    write_yaml(
        tmp_path / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": "sample_bottle_50ml_v1",
                    "role": "manipulated_object",
                    "asset_type": "bottle",
                    "canonical_usd": str(model.relative_to(tmp_path)),
                    "license": "CC-BY-4.0",
                    "sha256": compute_sha256(model),
                }
            ],
        },
    )
    return model


def test_compute_sha256_returns_prefixed_digest(tmp_path: Path) -> None:
    asset = tmp_path / "assets" / "objects" / "sample" / "model.usd"
    asset.parent.mkdir(parents=True)
    asset.write_text("#usda 1.0\n", encoding="utf-8")

    digest = compute_sha256(asset)

    assert digest.startswith("sha256:")
    assert digest == compute_sha256(asset)


def test_license_policy_rejects_missing_license() -> None:
    assert validate_license("CC-BY-4.0") is None
    assert validate_license("") == "Missing license"


def test_load_asset_manifest_reads_assets(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": "sample_bottle_50ml_v1",
                    "role": "manipulated_object",
                    "asset_type": "bottle",
                    "canonical_usd": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "license": "CC-BY-4.0",
                    "sha256": "sha256:" + "0" * 64,
                }
            ],
        },
    )

    manifest = load_asset_manifest(tmp_path)

    assert manifest.schema_version == "asset-manifest/v0.2"
    assert manifest.assets[0].asset_id == "sample_bottle_50ml_v1"
    assert manifest.assets[0].canonical_usd == "assets/objects/sample_bottle_50ml_v1/model.usd"


def test_load_asset_manifest_rejects_missing_license(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": "sample_bottle_50ml_v1",
                    "role": "manipulated_object",
                    "asset_type": "bottle",
                    "canonical_usd": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "sha256": "sha256:" + "0" * 64,
                }
            ],
        },
    )

    with pytest.raises(AssetManifestError, match="Missing license"):
        load_asset_manifest(tmp_path)


def test_generate_asset_lock_materializes_manifest_assets(tmp_path: Path) -> None:
    model = make_asset_manifest_package(tmp_path)

    lock = generate_asset_lock(tmp_path)

    assert lock.schema_version == "asset-lock/v0.2"
    assert lock.assets["sample_bottle_50ml_v1"].resolved_path == str(model.relative_to(tmp_path))
    assert lock.assets["sample_bottle_50ml_v1"].content_sha256 == compute_sha256(model)


def test_check_asset_lock_reports_checksum_mismatch(tmp_path: Path) -> None:
    model = make_asset_manifest_package(tmp_path)
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))
    model.write_text("changed\n", encoding="utf-8")

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert "Checksum mismatch for asset sample_bottle_50ml_v1" in report.messages


def test_check_asset_lock_rejects_manifest_path_escape_even_if_lock_is_unchanged(
    tmp_path: Path,
) -> None:
    make_asset_manifest_package(tmp_path)
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))
    manifest_path = tmp_path / "assets" / "asset_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0]["canonical_usd"] = "assets/../../outside.usd"
    write_yaml(manifest_path, manifest)

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert any("canonical" in message.lower() for message in report.messages)


def test_check_asset_lock_rejects_manifest_license_mismatch(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path)
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))
    manifest_path = tmp_path / "assets" / "asset_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0]["license"] = "Apache-2.0"
    write_yaml(manifest_path, manifest)

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert any("license" in message.lower() for message in report.messages)


def test_check_asset_lock_reports_missing_local_asset(tmp_path: Path) -> None:
    model = make_asset_manifest_package(tmp_path)
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))
    model.unlink()

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert "Missing locked asset file: assets/objects/sample_bottle_50ml_v1/model.usd" in report.messages


def test_check_asset_lock_reports_missing_license(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path)
    lock = generate_asset_lock(tmp_path)
    write_yaml(
        tmp_path / "locks" / "asset_lock.yaml",
        {
            "schema_version": lock.schema_version,
            "lock_id": lock.lock_id,
            "created_by": lock.created_by,
            "assets": {
                "sample_bottle_50ml_v1": {
                    "source_kind": "package_local",
                    "source_uri": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "resolved_path": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "content_sha256": lock.assets["sample_bottle_50ml_v1"].content_sha256,
                    "license": "",
                    "resolver_version": "scenario-forge/phase1",
                }
            },
        },
    )

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert "Missing license for asset sample_bottle_50ml_v1" in report.messages


def test_asset_lock_check_rejects_usd_reference_not_in_lock(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path)
    extra = tmp_path / "assets" / "objects" / "extra" / "model.usd"
    extra.parent.mkdir(parents=True)
    extra.write_text("#usda 1.0\n", encoding="utf-8")
    (tmp_path / "scene.usda").write_text(
        '#usda 1.0\nrel references = @assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))

    report = check_asset_lock(tmp_path, scene_paths=("scene.usda",))

    assert not report.ok
    assert "USD reference is not locked: assets/objects/extra/model.usd" in report.messages


def test_asset_lock_check_accepts_scene_relative_usd_reference(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path)
    scene = tmp_path / "scene" / "main.usda"
    scene.parent.mkdir()
    scene.write_text(
        '#usda 1.0\nrel references = @../assets/objects/sample_bottle_50ml_v1/model.usd@\n',
        encoding="utf-8",
    )
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))

    report = check_asset_lock(tmp_path, scene_paths=("scene/main.usda",))

    assert report.ok

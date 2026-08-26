from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts.generate_wangshuai_funnel_tube15_asset_set import build_asset_set


PRODUCER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "wangshuai_funnel_tube15_exact_asset_set_20260826"
)


@pytest.mark.skipif(not PRODUCER.is_dir(), reason="producer asset set unavailable")
def test_asset_set_imports_four_pass_packages_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "asset_set"
    build_asset_set(PRODUCER, output)
    manifest = json.loads((output / "asset_set_manifest.json").read_text())
    assert manifest["status"] == "pass"
    assert len(manifest["assets"]) == 4
    assert manifest["claims"]["physics_parameters_unchanged"] is True
    assert manifest["claims"]["robot_policy_success"] is False
    for item in manifest["assets"]:
        source = PRODUCER / item["producer_package"] / "asset.usda"
        copied = output / item["entry_usd"]
        assert sha256(copied.read_bytes()).hexdigest() == sha256(source.read_bytes()).hexdigest()
        producer_manifest = json.loads(
            (output / item["producer_manifest"]).read_text()
        )
        assert producer_manifest["overall_status"] == "pass"


@pytest.mark.skipif(not PRODUCER.is_dir(), reason="producer asset set unavailable")
def test_asset_entries_compose_with_identity_roots_and_local_dependencies(
    tmp_path: Path,
) -> None:
    from pxr import Gf, Usd, UsdGeom, UsdUtils

    output = tmp_path / "asset_set"
    build_asset_set(PRODUCER, output)
    manifest = json.loads((output / "asset_set_manifest.json").read_text())
    for item in manifest["assets"]:
        path = output / item["entry_usd"]
        stage = Usd.Stage.Open(str(path))
        assert stage
        assert str(stage.GetDefaultPrim().GetPath()) == item["entry_prim"]
        assert UsdGeom.Xformable(stage.GetDefaultPrim()).GetLocalTransformation() == Gf.Matrix4d(
            1.0
        )
        _layers, _assets, unresolved = UsdUtils.ComputeAllDependencies(str(path))
        assert list(unresolved) == []
    liquid = next(item for item in manifest["assets"] if item["contains_liquid"])
    stage = Usd.Stage.Open(str(output / liquid["entry_usd"]))
    assert len(
        stage.GetPrimAtPath(liquid["entry_prim"] + "/ParticleSet")
        .GetAttribute("points")
        .Get()
    ) == 1948


@pytest.mark.skipif(not PRODUCER.is_dir(), reason="producer asset set unavailable")
def test_delivery_is_directory_only_without_zip_or_demo(tmp_path: Path) -> None:
    output = tmp_path / "asset_set"
    build_asset_set(PRODUCER, output)
    assert not list(output.rglob("*.zip"))
    assert not (output / "demo.usda").exists()
    readme = (output / "README_CN.md").read_text()
    assert "不含液体" in readme
    assert "1948" in readme

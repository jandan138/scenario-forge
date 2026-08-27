from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts.generate_wangshuai_funnel_tube15_dynamic_asset_set import build_asset_set


PRODUCER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "wangshuai_funnel_tube15_dynamic_asset_set_20260827"
)


@pytest.mark.skipif(not PRODUCER.is_dir(), reason="dynamic producer set unavailable")
def test_dynamic_asset_set_is_default_and_byte_identical(tmp_path: Path) -> None:
    output = build_asset_set(PRODUCER, tmp_path / "asset_set")
    manifest = json.loads((output / "asset_set_manifest.json").read_text())
    assert manifest["status"] == "pass"
    assert manifest["default_consumption"] == "dynamic"
    assert manifest["claims"]["effective_kinematic"] is False
    assert manifest["claims"]["dynamic_runtime_qualified"] is True
    assert manifest["claims"]["dynamic_loaded_liquid_transport"] is False
    assert len(manifest["assets"]) == 4
    for item in manifest["assets"]:
        source = PRODUCER / item["producer_package"] / "asset.usda"
        copied = output / item["entry_usd"]
        assert sha256(copied.read_bytes()).hexdigest() == sha256(source.read_bytes()).hexdigest()


@pytest.mark.skipif(not PRODUCER.is_dir(), reason="dynamic producer set unavailable")
def test_dynamic_roots_are_not_authored_kinematic(tmp_path: Path) -> None:
    from pxr import Usd, UsdPhysics

    output = build_asset_set(PRODUCER, tmp_path / "asset_set")
    manifest = json.loads((output / "asset_set_manifest.json").read_text())
    for item in manifest["assets"]:
        stage = Usd.Stage.Open(str(output / item["entry_usd"]))
        root = stage.GetPrimAtPath(item["entry_prim"])
        if item["contains_liquid"]:
            continue
        assert root.HasAPI(UsdPhysics.MassAPI)
        assert not root.GetAttribute("physics:kinematicEnabled").HasAuthoredValueOpinion()

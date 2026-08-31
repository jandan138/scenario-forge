from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from pxr import Usd, UsdGeom

from scripts.generate_ika_oven_task0912_direct_scene import build_handoff


def test_direct_scene_preserves_oven_root_and_places_empty_sdf_vessels(
    tmp_path: Path,
) -> None:
    output = tmp_path / "handoff"

    result = build_handoff(output)

    assert result.archive.is_file()
    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    assert stage and stage.GetDefaultPrim().GetPath() == "/World"
    oven = stage.GetPrimAtPath("/World/Oven125")
    assert oven.IsValid()
    assert oven.GetAttribute("xformOpOrder").Get() in (None, [])
    assert not stage.GetPrimAtPath("/World/obj_oven").IsValid()
    assert stage.GetPrimAtPath("/World/table").IsValid()
    flask = stage.GetPrimAtPath("/World/obj_conical_flask")
    beaker = stage.GetPrimAtPath("/World/obj_beaker")
    assert flask.IsValid() and beaker.IsValid()
    cache = UsdGeom.XformCache()
    assert list(cache.GetLocalToWorldTransform(flask).ExtractTranslation()) == [
        -0.11,
        -0.06,
        1.038,
    ]
    assert list(cache.GetLocalToWorldTransform(beaker).ExtractTranslation()) == [
        0.11,
        -0.06,
        1.038,
    ]
    assert not stage.GetPrimAtPath("/World/fluid_runtime").IsValid()
    manifest = json.loads((result.root / "manifest.json").read_text())
    assert manifest["claims"]["task09_task12_subset"] is True
    assert manifest["claims"]["vr_scene_mount_allowed"] is False


def test_direct_scene_zip_contains_closed_and_open_entries(tmp_path: Path) -> None:
    result = build_handoff(tmp_path / "handoff")

    with ZipFile(result.archive) as bundle:
        names = set(bundle.namelist())
    root = "ika_oven_125_task0912_direct_scene_r1/"
    assert root + "scene.usd" in names
    assert root + "scene_open_preview.usd" in names
    assert root + "README_CN.md" in names
    assert root + "deps/oven/package/asset.usd" in names

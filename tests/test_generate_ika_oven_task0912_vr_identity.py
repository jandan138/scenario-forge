from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_ika_oven_task0912_vr_identity import (
    _task_scoped_runtime_checks,
    build_handoff,
)


def test_vr_scene_consumes_identity_oven_without_moving_the_table(
    tmp_path: Path,
) -> None:
    result = build_handoff(tmp_path / "handoff")

    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    assert stage and stage.GetDefaultPrim().GetPath() == "/World"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert stage.GetPrimAtPath("/World/PhysicsScene").GetAttribute(
        "physics:gravityMagnitude"
    ).Get() == pytest.approx(9.81)
    assert not stage.GetPrimAtPath("/World/Oven125").IsValid()
    oven = stage.GetPrimAtPath("/World/obj_oven")
    assert oven.IsValid()
    translation = UsdGeom.Xformable(oven).GetLocalTransformation().ExtractTranslation()
    assert list(translation) == [0.0, 0.0, 0.755]
    table = stage.GetPrimAtPath("/World/table")
    assert table.IsValid()
    assert list(UsdGeom.Xformable(table).GetLocalTransformation().ExtractTranslation()) == [
        0.0,
        0.0,
        0.0,
    ]
    joints = [
        prim
        for prim in stage.Traverse()
        if prim.IsA(UsdPhysics.Joint)
        and str(prim.GetPath()).startswith("/World/obj_oven/")
    ]
    assert len(joints) == 16
    assert sum(
        [str(path) for path in UsdPhysics.Joint(prim).GetBody0Rel().GetTargets()]
        == ["/World/obj_oven/Body"]
        for prim in joints
    ) == 15
    assert stage.GetPrimAtPath("/World/obj_conical_flask").IsValid()
    assert stage.GetPrimAtPath("/World/obj_beaker").IsValid()

    manifest = json.loads((result.root / "manifest.json").read_text())
    assert manifest["claims"]["relocatable_task_scoped"] is True
    assert manifest["claims"]["relocatable_full"] is False
    task_config = (result.root / "task_config.py").read_text()
    assert '"/World/_scene/obj_oven"' in task_config
    assert '"mode": "local"' in task_config
    assert "set_robot_physics_material" not in task_config


def test_vr_identity_handoff_zip_is_self_contained(tmp_path: Path) -> None:
    result = build_handoff(tmp_path / "handoff")

    with ZipFile(result.archive) as bundle:
        names = set(bundle.namelist())
    root = "ika_oven_125_task0912_vr_identity_r2/"
    assert root + "scene.usd" in names
    assert root + "scene_open_preview.usd" in names
    assert root + "task_config.py" in names
    assert root + "deps/oven/package/asset.usd" in names
    assert root + "deps/oven/promotion_receipt.json" in names


def test_runtime_scope_accepts_physical_motion_not_obsolete_body0_schema() -> None:
    checks = _task_scoped_runtime_checks(
        {
            "status": "FAIL",
            "results": {
                "doorDynamicLimit": {
                    "passed": False,
                    "successfulForceCalls": 1110,
                    "openingPeakDegrees": 179.99,
                    "closingFinalDegrees": 0.03,
                    "bodyTranslationDriftMeters": 0.0,
                },
                "tenButtonsTravelAndReturn": {"passed": True},
                "mainsRockerLimits": {"passed": True},
            },
        }
    )

    assert all(checks.values())

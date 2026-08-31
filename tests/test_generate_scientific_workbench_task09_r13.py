from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import yaml
from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_task09_r13 import build_handoff


def test_r13_uses_materialized_oven_compact_cart_and_two_graspable_vessels(
    tmp_path: Path,
) -> None:
    result = build_handoff(tmp_path / "handoff")

    stage = Usd.Stage.Open(str(result.root / "scene.usd"))
    assert stage and stage.GetDefaultPrim().GetPath() == "/World"
    oven = stage.GetPrimAtPath("/World/obj_oven")
    assert oven.IsValid() and not oven.GetMetadata("references")
    assert list(UsdGeom.Xformable(oven).GetLocalTransformation().ExtractTranslation()) == [
        1.51,
        0.0,
        0.755,
    ]
    assert stage.GetPrimAtPath(
        "/World/obj_oven/ControlPanel/Runtime/ControllerGraph"
    ).IsValid()
    assert stage.GetPrimAtPath("/World/obj_oven_cart").IsValid()
    assert list(
        UsdGeom.Xformable(stage.GetPrimAtPath("/World/obj_oven_cart"))
        .GetLocalTransformation()
        .ExtractTranslation()
    ) == [1.51, 0.0, 0.0]
    assert stage.GetPrimAtPath("/World/table").IsValid()
    assert stage.GetPrimAtPath("/World/obj_sample_beaker").HasAPI(
        UsdPhysics.RigidBodyAPI
    )
    assert stage.GetPrimAtPath("/World/obj_context_conical_flask").HasAPI(
        UsdPhysics.RigidBodyAPI
    )
    assert not stage.GetPrimAtPath("/World/fluid_runtime").IsValid()
    control = stage.GetPrimAtPath("/World/obj_oven/ControlPanel")
    assert control.GetAttribute("oven:mainsPower").Get() is True
    assert control.GetAttribute("oven:heatingEnabled").Get() is False
    assert control.GetAttribute("oven:temperatureSetpointC").Get() == 60.0


def test_r13_vr_config_and_metrics_follow_locked_contract(tmp_path: Path) -> None:
    result = build_handoff(tmp_path / "handoff")

    config = (result.root / "task_config.py").read_text(encoding="utf-8")
    for name in (
        "obj_oven_cart",
        "obj_oven",
        "obj_sample_beaker",
        "obj_context_conical_flask",
    ):
        assert f'"/World/_scene/{name}"' in config
    assert '"position": [0.85, -1.02, 0.31]' in config
    assert '"objs": ["obj_oven_cart", "obj_oven"]' in config
    assert "set_robot_physics_material" not in config
    assert "set_robot_contact_offset" not in config
    metrics = yaml.safe_load((result.root / "metrics.yaml").read_text(encoding="utf-8"))
    assert [item["weight"] for item in metrics["metrics"]] == [
        0.10,
        0.10,
        0.10,
        0.10,
        0.15,
        0.15,
        0.10,
        0.05,
        0.05,
        0.10,
    ]


def test_r13_zip_contains_vr_scene_config_and_convertasset_receipts(
    tmp_path: Path,
) -> None:
    result = build_handoff(tmp_path / "handoff")

    manifest = json.loads((result.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "static_built_runtime_pending"
    assert manifest["claims"]["target_vessel"] == "obj_sample_beaker"
    assert manifest["claims"]["conical_flask_graspable_context"] is True
    with ZipFile(result.archive) as bundle:
        names = set(bundle.namelist())
    prefix = "scientific_workbench_task09_r13_vr/"
    assert prefix + "scene.usd" in names
    assert prefix + "task_config.py" in names
    assert prefix + "metrics.yaml" in names
    assert prefix + "deps/oven/promotion_receipt.json" in names
    assert prefix + "deps/oven_cart/promotion_receipt.json" in names

from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics

from scripts.generate_traditional_titration_vr_r1 import build


def test_builds_materialized_vr_titration_scene(tmp_path) -> None:
    result = build(tmp_path / "handoff")
    stage = Usd.Stage.Open(str(result.scene))
    assert stage.GetDefaultPrim().GetPath() == "/World"
    assert not stage.GetPrimAtPath("/World/obj_oven")
    assert not stage.GetPrimAtPath("/World/obj_oven_cart")

    station = stage.GetPrimAtPath("/World/obj_titration_station")
    assert station.HasAPI(UsdPhysics.ArticulationRootAPI)
    assert not station.HasAuthoredReferences()
    instance = stage.GetPrimAtPath("/World/obj_titration_station/Instance")
    assert instance.IsA(UsdGeom.Xform)
    assert stage.GetPrimAtPath(
        "/World/obj_titration_station/Instance/Burette/stopcock_handle_link"
    ).HasAPI(UsdPhysics.RigidBodyAPI)

    flask = stage.GetPrimAtPath("/World/obj_receiver_flask")
    assert flask.IsA(UsdGeom.Xform)
    assert len(station.GetRelationship("titration:receiverLiquidVisuals").GetTargets()) == 4
    stir_bar = stage.GetPrimAtPath("/World/obj_receiver_flask/VisualLiquid/StirBar")
    assert stir_bar
    assert not stir_bar.HasAPI(UsdPhysics.RigidBodyAPI)
    assert not stir_bar.HasAPI(UsdPhysics.CollisionAPI)
    assert stir_bar.GetAttribute("xformOp:rotateZ").GetNumTimeSamples() > 100

    paths = [str(prim.GetPath()).lower() for prim in stage.Traverse()]
    assert not any("droplet" in path or "stream" in path for path in paths)


def test_vr_config_registers_links_but_randomizes_roots_only(tmp_path) -> None:
    result = build(tmp_path / "handoff")
    namespace: dict[str, object] = {"__file__": str(result.config)}
    exec(result.config.read_text(), namespace)
    task = namespace["TASKS"]["scientific_workbench_traditional_acid_base_titration_vr_r1"]
    registered = task["obj_prim_list"]
    assert "/World/_scene/obj_titration_station" in registered
    assert "/World/_scene/obj_titration_station/Instance/Burette/stopcock_handle_link" in registered
    groups = task["layout_randomization"]["objects"]
    assert groups[0]["objs"] == [
        "obj_titration_station",
        "obj_magnetic_stirrer",
        "obj_receiver_flask",
    ]
    assert groups[0]["x_offset_range"] == [-0.01, 0.01]
    assert groups[0]["y_offset_range"] == [-0.01, 0.01]
    assert all("/" not in name for group in groups for name in group["objs"])


def test_task_contract_encodes_endpoint_and_claim_boundary(tmp_path) -> None:
    result = build(tmp_path / "handoff")
    task = result.task.read_text()
    metrics = result.metrics.read_text()
    manifest = json.loads(result.manifest.read_text())
    assert "14.7" in task and "15.3" in task
    assert "OPEN" in task and "FINE" in task and "DRIP" in task and "CLOSED" in task
    assert "3.0" in task
    assert "endpoint_volume" in metrics
    assert manifest["claims"]["asset_functionality"] is True
    assert manifest["claims"]["scene_static_validation"] is False
    assert manifest["claims"]["robot_policy_success"] is False
    assert result.archive.is_file()


def test_r1_2_consumes_promoted_long_handle_station_without_local_patch(
    tmp_path,
) -> None:
    station = Path(
        "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
        "traditional_titration_assets_r2_long_handle_20260905"
    )
    task_id = "scientific_workbench_traditional_acid_base_titration_vr_r1_2"
    result = build(
        tmp_path / "handoff",
        station=station,
        task_id=task_id,
    )
    namespace: dict[str, object] = {"__file__": str(result.config)}
    exec(result.config.read_text(), namespace)
    assert task_id in namespace["TASKS"]
    manifest = json.loads(result.manifest.read_text())
    assert manifest["package_id"] == task_id
    assert manifest["assets"]["titration_station_package_id"] == (
        "traditional_titration_station_r2"
    )
    assert manifest["assets"]["stopcock_visible_span_m"] == 0.09
    assert "stopcock" not in manifest.get("scenario_local_physics_patches", [])

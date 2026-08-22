from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.build_labspin_x8_robot_validation_bundle import (
    CENTRIFUGE_PRIM,
    TUBE_PRIM,
    build_validation_bundle,
)


BASE_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/scenario-forge/outputs/"
    "scientific_workbench_tasks_02_07_08_r9_20260816/packages/"
    "scientific_workbench_r9_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry/ebench"
)
CENTRIFUGE_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "labspin_x8_centrifuge_r1_20260822/centrifuge/package"
)
TUBE_PACKAGE = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "labspin_x8_centrifuge_r1_20260822/native_tube_closed/package"
)


@pytest.mark.skipif(
    not all(path.is_dir() for path in (BASE_PACKAGE, CENTRIFUGE_PACKAGE, TUBE_PACKAGE)),
    reason="local validation inputs unavailable",
)
def test_bundle_composes_obj_root_assets_and_genmanip_config(tmp_path: Path) -> None:
    result = build_validation_bundle(
        base_package=BASE_PACKAGE,
        centrifuge_package=CENTRIFUGE_PACKAGE,
        tube_package=TUBE_PACKAGE,
        tube_entry_prim="/World/NativeCentrifugeTube15mlClosed",
        tube_label="native_tube",
        out=tmp_path,
    )

    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    stage = Usd.Stage.Open(str(result["scene_usd"]))
    centrifuge = stage.GetPrimAtPath(CENTRIFUGE_PRIM)
    tube = stage.GetPrimAtPath(TUBE_PRIM)
    assert centrifuge and tube
    assert UsdGeom.Xformable(centrifuge).GetLocalTransformation() != Gf.Matrix4d(1.0)
    assert UsdGeom.Xformable(tube).GetLocalTransformation() != Gf.Matrix4d(1.0)
    assert UsdPhysics.RigidBodyAPI(tube).GetKinematicEnabledAttr().Get() is True

    config = yaml.safe_load(result["config"].read_text(encoding="utf-8"))
    evaluation = config["evaluation_configs"][0]
    assert evaluation["robots"][0]["type"] == "manip/lift2/R5a"
    assert set(evaluation["object_config"]) >= {
        "obj_centrifuge",
        "obj_centrifuge_tube",
    }
    assert evaluation["object_config"]["obj_centrifuge"]["articulation_info"] == {
        "is_articulated": True,
        "part": {},
    }
    assert "labspin_x8_robot_contact_native_tube" in evaluation["task_name"]
    preprocessors = {
        item["type"] for item in evaluation.get("preprocess_config", [])
    }
    assert "set_robot_contact_offset" not in preprocessors
    assert "set_robot_rest_offset" not in preprocessors

    manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))
    assert manifest["status"] == "robot_validation_candidate"
    assert manifest["canonical_task"] is False
    assert manifest["claims"]["robot_contact_success"] is False
    assert manifest["source_assets"]["centrifuge_asset_usd_sha256"]
    assert manifest["source_assets"]["tube_asset_usd_sha256"]

    episode = json.loads(result["episode"].read_text(encoding="utf-8"))
    layout = episode["task_data"]["initial_layout"]
    assert layout["obj_centrifuge"]["position"] == pytest.approx([0.0, 0.0, 0.755])
    assert layout["obj_centrifuge_tube"]["type"] == "rigid"

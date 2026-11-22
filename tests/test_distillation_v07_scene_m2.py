"""Tests for distillation_v07 M2 OpenUSD True-Dynamic Scene Package & IK reachability."""

from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd, UsdPhysics


PKG_ROOT = Path(__file__).resolve().parents[1] / "external_artifacts" / "distillation_v07_package" / "scenario_package"


def test_distillation_v07_scene_package_and_ortho_cameras() -> None:
    scene_usd = PKG_ROOT / "scene" / "main.usda"
    spec_json = PKG_ROOT / "semantics" / "v07_scene_spec.json"
    assert scene_usd.is_file() and spec_json.is_file(), "Run scripts/build_m2_distillation_v07_scene.py first"

    spec = json.loads(spec_json.read_text(encoding="utf-8"))
    assert spec["physx_hz"] == 240
    assert "Cam_Front_Master" in spec["cameras"]
    assert "Cam_Ortho_Side_Left" in spec["cameras"]
    assert "Cam_Ortho_Side_Right" in spec["cameras"]

    stage = Usd.Stage.Open(str(scene_usd))
    pscene = stage.GetPrimAtPath("/World/PhysicsScene")
    assert pscene.IsValid() and pscene.IsA(UsdPhysics.Scene)
    assert int(pscene.GetAttribute("physxScene:timeStepsPerSecond").Get()) == 240
    assert bool(pscene.GetAttribute("physxScene:enableCCD").Get()) is True

    for mid in ("scissor_jack_blue_art001", "flask_clamp_2prong_art001", "condenser_clamp_3prong_art001"):
        assert stage.GetPrimAtPath(f"/World/Mechanisms/{mid}").IsValid()

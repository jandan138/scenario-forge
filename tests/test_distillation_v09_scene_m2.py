"""Tests for distillation_v09 M2 Full S01-S12 One-Shot Method-B OpenUSD scene package."""

from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd


PKG_DIR = Path(__file__).resolve().parents[1] / "external_artifacts" / "distillation_v09_package" / "scenario_package"


def test_distillation_v09_oneshot_scene_package() -> None:
    usda = PKG_DIR / "scene" / "main.usda"
    spec_p = PKG_DIR / "semantics" / "v09_scene_spec.json"
    assert usda.is_file() and spec_p.is_file(), "Run scripts/build_m2_distillation_v09_scene.py first"

    stage = Usd.Stage.Open(str(usda))
    required_prims = (
        "/World/Instruments/iron_stand_left",
        "/World/Instruments/bosshead_left",
        "/World/Instruments/iron_stand_right",
        "/World/Instruments/bosshead_right",
        "/World/Instruments/heating_stirrer_bath",
        "/World/Instruments/round_bottom_flask_250ml",
        "/World/Instruments/distillation_head_75deg",
        "/World/Instruments/liebig_condenser_24_29",
        "/World/Instruments/vacuum_tail_adapter",
        "/World/Instruments/erlenmeyer_flask_150ml",
        "/World/Instruments/long_stem_funnel",
        "/World/Instruments/pour_beaker_100ml",
        "/World/Instruments/thermometer_adapter_unit_v08",
        "/World/Mechanisms/scissor_jack_blue_art001/Handwheel",
        "/World/Mechanisms/scissor_jack_white_art001/Handwheel",
        "/World/Mechanisms/flask_clamp_2prong_art001/ButterflyWingnut",
        "/World/Mechanisms/condenser_clamp_3prong_art001/TopButterflyWingnut",
        "/World/CoolingHoses/Hose_Inlet_Lower",
        "/World/CoolingHoses/Hose_Outlet_Upper",
        "/World/DynamicFluids/FlaskPurplePool",
        "/World/DynamicFluids/ReceiverClearPool",
    )
    for prim_p in required_prims:
        assert stage.GetPrimAtPath(prim_p).IsValid(), f"Missing {prim_p}"
    assert not stage.GetPrimAtPath("/World/Mechanisms/keck_clip_head_cond_art001").IsValid()

    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    assert spec["physx_hz"] == 240
    assert len(spec["stages"]) == 12
    assert spec["taper_method"] == "method_b_radial_micro_spring_only"
    assert (
        abs(
            spec["taper_targets"]["joint_04_thermo_seated_world"][2]
            + spec["taper_targets"]["thermometer_bulb_top_local_z"]
            - spec["taper_targets"]["sidearm_bottom_lip_z_world"]
        )
        < 1e-5
    )


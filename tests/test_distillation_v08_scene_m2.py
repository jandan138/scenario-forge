"""Tests for distillation_v08 M2 OpenUSD 4-Taper-Joint & Articulated Keck Clip scene package."""

from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd


PKG_DIR = Path(__file__).resolve().parents[1] / "external_artifacts" / "distillation_v08_package" / "scenario_package"


def test_distillation_v08_taper_keck_scene_package() -> None:
    usda = PKG_DIR / "scene" / "main.usda"
    spec_p = PKG_DIR / "semantics" / "v08_scene_spec.json"
    assert usda.is_file() and spec_p.is_file(), "Run scripts/build_m2_distillation_v08_scene.py first"

    stage = Usd.Stage.Open(str(usda))
    for prim_p in (
        "/World/Instruments/round_bottom_flask_250ml",
        "/World/Instruments/distillation_head_75deg",
        "/World/Instruments/liebig_condenser_24_29",
        "/World/Instruments/vacuum_tail_adapter",
        "/World/Instruments/thermometer_adapter_unit_v08",
        "/World/Mechanisms/keck_clip_head_cond_art001/ClipSpine",
        "/World/Mechanisms/keck_clip_head_cond_art001/LeftSpringJaw",
        "/World/Mechanisms/keck_clip_head_cond_art001/RightSpringJaw",
        "/World/Mechanisms/keck_clip_cond_tail_art001/ClipSpine",
    ):
        assert stage.GetPrimAtPath(prim_p).IsValid(), f"Missing {prim_p}"

    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    assert spec["physx_hz"] == 240
    assert abs(spec["taper_targets"]["joint_04_thermo_seated_world"][2] + spec["taper_targets"]["thermometer_bulb_top_local_z"] - spec["taper_targets"]["sidearm_bottom_lip_z_world"]) < 1e-5


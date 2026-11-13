#!/usr/bin/env python3
"""Render 1080p lossless Canary stage keyframes + 720p H.264 physics progression videos.

Runs one clean Isaac Sim 4.1 + GenManip SimulationApp subprocess per collected package
with RayTracedLighting enabled and full Code-as-Room background visible. Produces:
- stage_00_t0.png .. stage_0K_final.png (lossless 1920x1080 RayTraced PNG keyframes)
- progression.mp4 (1280x720 30fps H.264 yuv420p looping reel with anti-aliased HUD)
- contact_sheet.png (diagnostic grid of all stage keyframes for visual QA)
- canary_media_manifest.json (per-stage scores, readouts, camera pose, and SHA-256 hashes)
"""

from __future__ import annotations

import argparse
import copy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = Path("external_artifacts/out_of_domain_factory_20261112")
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path("/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src")
TABLE_RUNTIME_ID = "00000000000000000000000000000000"

CJK_FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
MONO_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

SCENARIO_MEDIA_SPECS: dict[str, dict[str, Any]] = {
    "specialty_coffee_bar_creatista_prep": {
        "title_zh": "精品咖啡吧 · Nespresso Creatista Plus 五步萃取准备",
        "camera": {
            "target": [0.06, -0.01, 0.94],
            "distance": 1.92,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · 120帧零动作冷启动稳态（漂移 0.000 mm）",
        "t0_predicate": "5 个子阶段与全部状态谓词均为 False（t0_score = 0.00）",
        "stages": [
            {
                "stage_index": 0,
                "name": "extend_drip_tray",
                "title_zh": "Stage 1/5 · 拉出前侧滴水托盘 (-42 mm)",
                "predicate_desc": "creatista_machine.drip_tray ∈ [-0.045, -0.035 m]",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "dof_index": 1,
                "target_value": -0.042,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
            },
            {
                "stage_index": 1,
                "name": "place_espresso_cup_on_drip_tray",
                "title_zh": "Stage 2/5 · 浓缩咖啡杯竖直落座滴水盘",
                "predicate_desc": "espresso_cup rel DripTray ≤ 38mm ∧ Z-axis upright ≤ 15°",
                "kind": "rigid_relative_arc",
                "object_id": "espresso_cup",
                "relative_to": "creatista_machine",
                "offset_xyz_m": [0.0, -0.192, 0.0365],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 22,
                "arc_height_m": 0.11,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.012,
            },
            {
                "stage_index": 2,
                "name": "drop_coffee_capsule_into_chute",
                "title_zh": "Stage 3/5 · 铝制胶囊投入 46×48mm 非凸投料槽",
                "predicate_desc": "coffee_capsule seated inside 5-box open capsule chute",
                "kind": "rigid_relative_arc",
                "object_id": "coffee_capsule",
                "relative_to": "creatista_machine",
                "offset_xyz_m": [0.0, -0.1095, 0.253],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 24,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.016,
            },
            {
                "stage_index": 3,
                "name": "close_brew_lever_over_capsule",
                "title_zh": "Stage 4/5 · 下压不锈钢萃取压杆锁紧腔体",
                "predicate_desc": "creatista_machine.brew_lever ∈ [-0.087, 0.020 rad] (胶囊零弹飞)",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "dof_index": 0,
                "target_value": 0.0,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "coffee_capsule",
                "watch_relative_to": "creatista_machine",
                "watch_z_bounds_m": [0.246, 0.268],
            },
            {
                "stage_index": 4,
                "name": "turn_select_dial_to_espresso",
                "title_zh": "Stage 5/5 · 旋转饮品拨盘至浓缩档 (+78°)",
                "predicate_desc": "creatista_machine.select_dial ∈ [1.134, 1.571 rad]",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "dof_index": 2,
                "target_value": 1.361356816555577,
                "interp_steps": 24,
                "capture_every": 1,
                "settle_steps": 18,
            },
        ],
    },
    "electronics_qa_ingun_probe_lock": {
        "title_zh": "SMT 电子质检工坊 · INGUN MA 2111 针床治具装板锁紧",
        "camera": {
            "target": [-0.006, 0.008, 0.98],
            "distance": 2.34,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · 120帧零动作冷启动稳态（PCBA 初始偏航 90°，t0=0.00）",
        "t0_predicate": "4 个子阶段与全部轴对齐/区间谓词均为 False（杜绝 0.125 部分分泄露）",
        "stages": [
            {
                "stage_index": 0,
                "name": "seat_pcba_in_4rail_pin_nest",
                "title_zh": "Stage 1/4 · 取起 PCBA 旋转 90° 落入四导轨探针定位巢",
                "predicate_desc": "pcba_carrier_board rel PinNest ≤ 30mm ∧ X-axis aligned ≤ 15°",
                "kind": "rigid_relative_arc",
                "object_id": "pcba_carrier_board",
                "relative_to": "ingun_fixture",
                "offset_xyz_m": [0.0, -0.040, 0.1285],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.010,
            },
            {
                "stage_index": 1,
                "name": "close_pressure_hood_over_pcba",
                "title_zh": "Stage 2/4 · 下压压针上盖贴合载板",
                "predicate_desc": "ingun_fixture.pressure_hood ∈ [-0.087, 0.020 rad] (载板稳留巢内)",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "dof_index": 0,
                "target_value": 0.0,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "pcba_carrier_board",
                "watch_relative_to": "ingun_fixture",
                "watch_z_bounds_m": [0.122, 0.140],
            },
            {
                "stage_index": 2,
                "name": "lock_eccentric_clamp_lever",
                "title_zh": "Stage 3/4 · 压合前侧偏心锁紧手柄至死点",
                "predicate_desc": "ingun_fixture.clamp_lever ∈ [-0.105, 0.020 rad]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "dof_index": 1,
                "target_value": 0.0,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
            },
            {
                "stage_index": 3,
                "name": "flip_mode_toggle_probe_active",
                "title_zh": "Stage 4/4 · 拨动前侧模式拨杆激活探针测试 (-21°)",
                "predicate_desc": "ingun_fixture.mode_toggle ∈ [-0.436, -0.262 rad]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "dof_index": 2,
                "target_value": -0.3665191429188092,
                "interp_steps": 22,
                "capture_every": 1,
                "settle_steps": 18,
            },
        ],
    },
    "modern_office_brother_calibrate": {
        "title_zh": "现代办公文印中心 · Brother MFC-L2820DW 装纸推入与扫描校准",
        "camera": {
            "target": [0.003, 0.005, 1.03],
            "distance": 2.48,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · Critic 修场景后稳态（A5 纸包左移让出 180mm 纸盒走廊）",
        "t0_predicate": "4 个子阶段与全部轴对齐/区间谓词均为 False（t0_score = 0.00）",
        "stages": [
            {
                "stage_index": 0,
                "name": "load_a5_media_into_open_cassette",
                "title_zh": "Stage 1/4 · 取起左侧 A5 纸包旋转 90° 装入拉出态纸盒凹腔",
                "predicate_desc": "a5_media_pack inside PaperCassette cavity ∧ X-axis aligned ≤ 15°",
                "kind": "rigid_relative_arc",
                "object_id": "a5_media_pack",
                "relative_to": "brother_printer",
                "offset_xyz_m": [0.0, -0.261, 0.015],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.12,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.012,
            },
            {
                "stage_index": 1,
                "name": "push_cassette_closed_into_hollow_tunnel",
                "title_zh": "Stage 2/4 · 施加 32N 推力平滑推回纸盒（纸包随盒滑入中空隧道）",
                "predicate_desc": "brother_printer.paper_cassette ∈ [-0.012, 0.000 m] (damping=200)",
                "kind": "articulation_joint",
                "object_id": "brother_printer",
                "dof_index": 0,
                "target_value": 0.0,
                "drive_effort": 32.0,
                "interp_steps": 90,
                "capture_every": 3,
                "settle_steps": 24,
                "watch_cavity_object": "a5_media_pack",
                "watch_relative_to": "brother_printer",
                "watch_z_bounds_m": [0.008, 0.030],
            },
            {
                "stage_index": 2,
                "name": "place_calibration_sheet_on_platen",
                "title_zh": "Stage 3/4 · 取起右侧校准卡旋转 90° 平铺于扫描仪玻璃稿台",
                "predicate_desc": "calibration_sheet rel PlatenGlass ≤ 35mm ∧ X-axis aligned ≤ 15°",
                "kind": "rigid_relative_arc",
                "object_id": "calibration_sheet",
                "relative_to": "brother_printer",
                "offset_xyz_m": [0.0, -0.010, 0.283],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.14,
                "release_clearance_z_m": 0.005,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.010,
            },
            {
                "stage_index": 3,
                "name": "close_scanner_lid_over_sheet",
                "title_zh": "Stage 4/4 · 合上顶部扫描仪盖板压实校准卡",
                "predicate_desc": "brother_printer.scanner_lid ∈ [-0.087, 0.020 rad] -> Score 1.00",
                "kind": "articulation_joint",
                "object_id": "brother_printer",
                "dof_index": 1,
                "target_value": 0.0,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "calibration_sheet",
                "watch_relative_to": "brother_printer",
                "watch_z_bounds_m": [0.276, 0.292],
            },
        ],
    },
}

SCENARIO_MEDIA_SPECS_R2: dict[str, dict[str, Any]] = {
    "specialty_coffee_bar_creatista_prep": {
        "title_zh": "精品咖啡吧 · Creatista Plus r2 六步浓缩准备与复合编码按压确认",
        "camera": {
            "target": [0.06, -0.01, 0.94],
            "distance": 1.92,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · 120帧零动作冷启动稳态（8-DOF CAD 机身，t0=0.00）",
        "t0_predicate": "6 个子阶段与全部状态谓词均为 False（t0_score = 0.00）",
        "stages": [
            {
                "stage_index": 0,
                "name": "extend_drip_tray",
                "title_zh": "Stage 1/6 · 拉出穿孔不锈钢滴水托杯盘 (-42 mm)",
                "predicate_desc": "creatista_machine.drip_tray ∈ [-0.045, -0.035 m]",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "joint_name": "DripTrayJoint",
                "target_value": -0.042,
                "interp_steps": 26,
                "capture_every": 1,
                "settle_steps": 18,
            },
            {
                "stage_index": 1,
                "name": "place_espresso_cup_on_drip_tray",
                "title_zh": "Stage 2/6 · 白瓷浓缩咖啡杯正立落座滴水盘格栅",
                "predicate_desc": "espresso_cup rel DripTray ∧ Z-axis upright ≤ 12°",
                "kind": "rigid_relative_arc",
                "object_id": "espresso_cup",
                "relative_to": "creatista_machine",
                "offset_xyz_m": [0.0, -0.192, 0.0365],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 22,
                "arc_height_m": 0.11,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.014,
            },
            {
                "stage_index": 2,
                "name": "drop_coffee_capsule_into_chute",
                "title_zh": "Stage 3/6 · 旋成铝制胶囊投入 46×48mm 非凸投料槽",
                "predicate_desc": "coffee_capsule seated inside non-convex CapsuleChute",
                "kind": "rigid_relative_arc",
                "object_id": "coffee_capsule",
                "relative_to": "creatista_machine",
                "offset_xyz_m": [0.0, -0.105, 0.253],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 24,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.016,
            },
            {
                "stage_index": 3,
                "name": "close_brew_lever_over_capsule",
                "title_zh": "Stage 4/6 · 下压镀铬 U 型萃取压杆锁紧腔体",
                "predicate_desc": "creatista_machine.brew_lever ∈ [-0.087, 0.020 rad] (胶囊稳留腔内)",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "joint_name": "BrewLeverJoint",
                "target_value": 0.0,
                "interp_steps": 26,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "coffee_capsule",
                "watch_relative_to": "creatista_machine",
                "watch_z_bounds_m": [0.246, 0.268],
            },
            {
                "stage_index": 4,
                "name": "turn_select_dial_to_espresso",
                "title_zh": "Stage 5/6 · 旋转 42 齿滚花编码旋钮至 ESPRESSO (+78°)",
                "predicate_desc": "creatista_machine.select_dial ∈ [1.134, 1.571 rad]",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "joint_name": "SelectDialJoint",
                "target_value": 1.361356816555577,
                "interp_steps": 22,
                "capture_every": 1,
                "settle_steps": 16,
            },
            {
                "stage_index": 5,
                "name": "press_dial_confirm_brew",
                "title_zh": "Stage 6/6 · 按入串联复合旋钮确认萃取 (+2.4 mm) → 1.00",
                "predicate_desc": "creatista_machine.dial_press == pressed [+1.4, +3.1 mm]",
                "kind": "articulation_joint",
                "object_id": "creatista_machine",
                "joint_name": "DialPressJoint",
                "target_value": 0.0024,
                "interp_steps": 16,
                "capture_every": 1,
                "settle_steps": 16,
            },
        ],
    },
    "electronics_qa_ingun_probe_lock": {
        "title_zh": "SMT 电子质检工坊 · INGUN MA 2111 r2 五步针床锁紧与测试触发",
        "camera": {
            "target": [-0.006, 0.008, 0.98],
            "distance": 2.34,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · 120帧冷启动稳态（6-DOF 80探针 CAD 治具，t0=0.00）",
        "t0_predicate": "5 个子阶段与全部轴对齐/区间谓词均为 False（t0_score = 0.00）",
        "stages": [
            {
                "stage_index": 0,
                "name": "seat_pcba_in_4rail_pin_nest",
                "title_zh": "Stage 1/5 · 取起 PCBA 旋转 90° 落入 80 金针四导轨定位巢",
                "predicate_desc": "pcba_carrier_board rel PinNest ∧ X-axis aligned ≤ 10°",
                "kind": "rigid_relative_arc",
                "object_id": "pcba_carrier_board",
                "relative_to": "ingun_fixture",
                "offset_xyz_m": [0.0, -0.040, 0.1285],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.012,
            },
            {
                "stage_index": 1,
                "name": "close_pressure_hood_over_pcba",
                "title_zh": "Stage 2/5 · 合下烟灰亚克力透视压针上盖贴合载板",
                "predicate_desc": "ingun_fixture.pressure_hood ∈ [-0.087, 0.020 rad]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "joint_name": "PressureHoodJoint",
                "target_value": 0.0,
                "interp_steps": 26,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "pcba_carrier_board",
                "watch_relative_to": "ingun_fixture",
                "watch_z_bounds_m": [0.122, 0.140],
            },
            {
                "stage_index": 2,
                "name": "lock_u_gantry_clamp_lever",
                "title_zh": "Stage 3/5 · 压合跨双侧红色 U 型龙门偏心手柄锁止",
                "predicate_desc": "ingun_fixture.clamp_lever ∈ [-0.105, 0.020 rad]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "joint_name": "ClampLeverJoint",
                "target_value": 0.0,
                "interp_steps": 26,
                "capture_every": 1,
                "settle_steps": 18,
            },
            {
                "stage_index": 3,
                "name": "flip_mode_toggle_probe_active",
                "title_zh": "Stage 4/5 · 拨动护栏拨杆至 PROBE ACTIVE (-21°)",
                "predicate_desc": "ingun_fixture.mode_toggle ∈ [-0.436, -0.262 rad]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "joint_name": "ModeToggleJoint",
                "target_value": -0.3665191429188092,
                "interp_steps": 20,
                "capture_every": 1,
                "settle_steps": 16,
            },
            {
                "stage_index": 4,
                "name": "press_test_start_button",
                "title_zh": "Stage 5/5 · 按下绿色 TEST START 自复位键触发测试 → 1.00",
                "predicate_desc": "ingun_fixture.test_start_button == pressed [-3.1, -1.8 mm]",
                "kind": "articulation_joint",
                "object_id": "ingun_fixture",
                "joint_name": "TestStartButtonJoint",
                "target_value": -0.0024,
                "interp_steps": 16,
                "capture_every": 1,
                "settle_steps": 16,
            },
        ],
    },
    "modern_office_brother_calibrate": {
        "title_zh": "现代办公文印中心 · Brother MFC-L2820DW r2 五步装纸推轨与复印启动",
        "camera": {
            "target": [0.003, 0.005, 1.03],
            "distance": 2.48,
            "elevation": 30.0,
            "azimuth": -35.0,
            "focal_length": 10.5,
        },
        "t0_title_zh": "t=0 · Critic 修场景后稳态（7-DOF CAD 一体机，t0=0.00）",
        "t0_predicate": "5 个子阶段与全部轴对齐/区间谓词均为 False（t0_score = 0.00）",
        "stages": [
            {
                "stage_index": 0,
                "name": "load_a5_media_into_open_cassette",
                "title_zh": "Stage 1/5 · 取起左侧 A5 纸包旋转 90° 装入绿色导轨纸盒凹腔",
                "predicate_desc": "a5_media_pack inside PaperCassette ∧ X-axis aligned ≤ 10°",
                "kind": "rigid_relative_arc",
                "object_id": "a5_media_pack",
                "relative_to": "brother_printer",
                "offset_xyz_m": [0.0, -0.261, 0.015],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.12,
                "release_clearance_z_m": 0.006,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.014,
            },
            {
                "stage_index": 1,
                "name": "push_cassette_closed_into_hollow_tunnel",
                "title_zh": "Stage 2/5 · 施加 32N 推力平滑推回纸盒（携纸包滑入中空隧道）",
                "predicate_desc": "brother_printer.paper_cassette ∈ [-0.012, 0.000 m] (damping=200)",
                "kind": "articulation_joint",
                "object_id": "brother_printer",
                "joint_name": "PaperCassetteJoint",
                "target_value": 0.0,
                "drive_effort": 32.0,
                "interp_steps": 90,
                "capture_every": 3,
                "settle_steps": 24,
                "watch_cavity_object": "a5_media_pack",
                "watch_relative_to": "brother_printer",
                "watch_z_bounds_m": [0.008, 0.030],
            },
            {
                "stage_index": 2,
                "name": "place_calibration_sheet_on_platen",
                "title_zh": "Stage 3/5 · 取起右侧 IT8.7 标定卡旋转 90° 平铺于玻璃稿台",
                "predicate_desc": "calibration_sheet rel PlatenGlass ∧ X-axis aligned ≤ 10°",
                "kind": "rigid_relative_arc",
                "object_id": "calibration_sheet",
                "relative_to": "brother_printer",
                "offset_xyz_m": [0.0, -0.010, 0.283],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 26,
                "arc_height_m": 0.14,
                "release_clearance_z_m": 0.005,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.012,
            },
            {
                "stage_index": 3,
                "name": "close_scanner_lid_over_sheet",
                "title_zh": "Stage 4/5 · 合下带 ADF 输稿器的扫描仪上盖压实标定卡",
                "predicate_desc": "brother_printer.scanner_lid ∈ [-0.087, 0.020 rad]",
                "kind": "articulation_joint",
                "object_id": "brother_printer",
                "joint_name": "ScannerLidJoint",
                "target_value": 0.0,
                "interp_steps": 26,
                "capture_every": 1,
                "settle_steps": 18,
                "watch_cavity_object": "calibration_sheet",
                "watch_relative_to": "brother_printer",
                "watch_z_bounds_m": [0.276, 0.292],
            },
            {
                "stage_index": 4,
                "name": "press_copy_start_button",
                "title_zh": "Stage 5/5 · 按下 30° 操控台绿色 START 键触发扫描校准 → 1.00",
                "predicate_desc": "brother_printer.button_start == pressed [-2.3, -1.2 mm]",
                "kind": "articulation_joint",
                "object_id": "brother_printer",
                "joint_name": "ButtonStartJoint",
                "target_value": -0.0017,
                "interp_steps": 16,
                "capture_every": 1,
                "settle_steps": 16,
            },
        ],
    },
}


SCENARIO_MEDIA_SPECS_REAL2SIM: dict[str, dict[str, Any]] = {
    "real2sim_office_desk_riser_organize": {
        "title_zh": "真实工位 1:1 数字孪生 · 双抽屉增高架双物收纳与桌面整理五步推进",
        "camera": {
            "target": [0.10, 0.00, 0.86],
            "distance": 1.65,
            "elevation": 28.0,
            "azimuth": -42.0,
            "focal_length": 11.5,
        },
        "t0_title_zh": "t=0 · 120帧冷启动稳态（3-DOF 双抽屉增高架 + 11件工位刚体，t0=0.00）",
        "t0_predicate": "5 个顺序子阶段谓词在 t=0 处总体得分为 0.00（抽屉闭合待开启）",
        "stages": [
            {
                "stage_index": 0,
                "name": "pull_open_right_drawer",
                "title_zh": "Stage 1/5 · 拉出双抽屉增高架右侧圆环拉手抽屉 (+158 mm)",
                "predicate_desc": "desktop_riser_rig.drawer_right ∈ [0.120, 0.165 m]",
                "kind": "articulation_joint",
                "object_id": "desktop_riser_rig",
                "joint_name": "drawer_right",
                "target_value": 0.158,
                "interp_steps": 28,
                "capture_every": 1,
                "settle_steps": 18,
            },
            {
                "stage_index": 1,
                "name": "store_chocopie_in_right_drawer",
                "title_zh": "Stage 2/5 · 取起好丽友派包装袋落入右侧五壁抽屉左腔",
                "predicate_desc": "chocopie_pack seated inside drawer_right 5-wall cavity",
                "kind": "rigid_relative_arc",
                "object_id": "chocopie_pack",
                "relative_to": "desktop_riser_rig",
                "offset_xyz_m": [0.080, -0.205, 0.0175],
                "orientation_wxyz": [0.70710678, 0.0, 0.0, 0.70710678],
                "arc_frames": 24,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.005,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.016,
            },
            {
                "stage_index": 2,
                "name": "store_pen_in_right_drawer",
                "title_zh": "Stage 3/5 · 取起蓝色圆珠笔并列放入右侧五壁抽屉右腔",
                "predicate_desc": "blue_ballpoint_pen seated inside drawer_right 5-wall cavity",
                "kind": "rigid_relative_arc",
                "object_id": "blue_ballpoint_pen",
                "relative_to": "desktop_riser_rig",
                "offset_xyz_m": [0.172, -0.198, 0.0175],
                "orientation_wxyz": [0.8660254, 0.0, 0.0, 0.5],
                "arc_frames": 24,
                "arc_height_m": 0.13,
                "release_clearance_z_m": 0.005,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.016,
            },
            {
                "stage_index": 3,
                "name": "push_right_drawer_closed",
                "title_zh": "Stage 4/5 · 施加 36N 推力平滑推回右侧抽屉（携双物滑入腔内）",
                "predicate_desc": "desktop_riser_rig.drawer_right ∈ [0.000, 0.025 m] (零顶穿/零脱轨)",
                "kind": "articulation_joint",
                "object_id": "desktop_riser_rig",
                "joint_name": "drawer_right",
                "target_value": 0.0,
                "drive_effort": -36.0,
                "interp_steps": 80,
                "capture_every": 3,
                "settle_steps": 24,
                "watch_cavity_object": "chocopie_pack",
                "watch_relative_to": "desktop_riser_rig",
                "watch_z_bounds_m": [0.010, 0.048],
            },
            {
                "stage_index": 4,
                "name": "place_water_mug_beside_sprite",
                "title_zh": "Stage 5/5 · 将带把玻璃水杯正立归位至雪碧瓶旁饮品收纳区 → 1.00",
                "predicate_desc": "glass_water_mug rel sprite_bottle_500ml ∧ Z-axis upright ≤ 10°",
                "kind": "rigid_relative_arc",
                "object_id": "glass_water_mug",
                "relative_to": "sprite_bottle_500ml",
                "offset_xyz_m": [-0.115, 0.0, 0.002],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "arc_frames": 22,
                "arc_height_m": 0.11,
                "release_clearance_z_m": 0.005,
                "settle_steps": 36,
                "capture_every": 2,
                "max_settle_drift_m": 0.016,
            },
        ],
    },
}


def _media_specs_for_profile(
    profile: str,
    *,
    plan_file: Path | None = None,
) -> dict[str, dict[str, Any]]:
    if profile in {"r2", "r3", "r4"}:
        selected = SCENARIO_MEDIA_SPECS_R2
    elif profile == "real2sim":
        selected = SCENARIO_MEDIA_SPECS_REAL2SIM
    else:
        selected = SCENARIO_MEDIA_SPECS
    if plan_file is None:
        return selected
    base = copy.deepcopy(selected)
    loaded = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"Expected mapping in media plan file {plan_file}")
    for k, v in loaded.items():
        base[str(k)] = dict(v)
    return base


def _normalize_joint_token(name: str) -> str:
    cleaned = name.strip().lower().replace("_", "").replace("-", "")
    if cleaned.endswith("joint"):
        cleaned = cleaned[:-5]
    return cleaned


def _resolve_dof_index(art: Any, st: Mapping[str, Any], art_id: str) -> int:
    if "joint_name" not in st:
        return int(st["dof_index"])
    dof_names = [str(x) for x in art.dof_names]
    jname = str(st["joint_name"])
    if jname in dof_names:
        return dof_names.index(jname)
    norm_target = _normalize_joint_token(jname)
    for idx, cand in enumerate(dof_names):
        if _normalize_joint_token(cand) == norm_target:
            return idx
    raise ValueError(f"joint_name {jname!r} not in {art_id}.dof_names={dof_names}")


def _lookup_reference_world_pose(scene: Any, rel_id: str) -> tuple[Any, Any]:
    if rel_id in scene.articulation_list:
        return scene.articulation_list[rel_id].get_world_pose()
    if rel_id in scene.object_list:
        return scene.object_list[rel_id].get_world_pose()
    raise KeyError(
        f"reference object {rel_id!r} not found in articulation_list or object_list"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render 1080p Canary stage keyframes + 720p H.264 progression videos."
    )
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--media-root", type=Path, default=None)
    parser.add_argument("--plan-file", type=Path, default=None)
    parser.add_argument(
        "--reprojection-grounding-json",
        type=Path,
        default=None,
        help="Optional workstation_pose_grounding.json to capture a camera-matched 4:3 RTX shot at t=0.",
    )
    parser.add_argument(
        "--reprojection-out",
        type=Path,
        default=None,
        help="Output PNG path for the camera-matched 4:3 RTX shot.",
    )
    parser.add_argument(
        "--profile",
        choices=("r1", "r2", "r3", "r4", "real2sim"),
        default="r1",
    )
    parser.add_argument("--single-collected-root", type=Path)
    parser.add_argument("--single-media-out", type=Path)
    parser.add_argument("--isaac-python", type=Path, default=DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--genmanip-root", type=Path, default=DEFAULT_GENMANIP_ROOT)
    parser.add_argument("--curobo-src", type=Path, default=DEFAULT_CUROBO_SRC)
    return parser


def _isaac_environment(
    isaac_python: Path,
    *,
    curobo_src: Path | None = None,
) -> dict[str, str]:
    environment = dict(os.environ)
    if curobo_src is not None and curobo_src.is_dir():
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(curobo_src.resolve()), *([inherited] if inherited else [])]
        )
    environment["PATH"] = os.pathsep.join(
        [str(isaac_python.parent), environment.get("PATH", "")]
    )
    prefix = isaac_python.parent.parent
    libraries = (
        prefix / "lib/python3.10/site-packages/torch/lib",
        prefix / "lib/python3.10/site-packages/nvidia/cuda_runtime/lib",
        prefix / "lib/python3.10/site-packages/isaacsim/extscache/omni.cuda.libs/bin",
    )
    inherited_ld = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [
            *[str(path) for path in libraries if path.is_dir()],
            *([inherited_ld] if inherited_ld else []),
        ]
    )
    return environment


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _resolve_collected_asset_paths(
    task_data: dict[str, Any],
    collected_root: Path,
    package_id: str,
) -> None:
    initial_layout = task_data["initial_layout"]
    prefix = f"collected_packages/{package_id}/"
    resolved_root = collected_root.resolve()
    for raw_item in initial_layout.values():
        if not isinstance(raw_item, dict):
            continue
        raw_path = raw_item.get("path")
        if isinstance(raw_path, str) and raw_path.startswith(prefix):
            relative = Path(raw_path.removeprefix(prefix))
            raw_item["path"] = str((resolved_root / relative).resolve())


def _quat_slerp_wxyz(q0: Sequence[float], q1: Sequence[float], alpha: float) -> list[float]:
    n0 = math.sqrt(sum(float(v) * float(v) for v in q0)) or 1.0
    n1 = math.sqrt(sum(float(v) * float(v) for v in q1)) or 1.0
    a = [float(v) / n0 for v in q0]
    b = [float(v) / n1 for v in q1]
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = [-y for y in b]
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        out = [x + alpha * (y - x) for x, y in zip(a, b)]
    else:
        theta_0 = math.acos(dot)
        sin_theta_0 = math.sin(theta_0)
        theta = theta_0 * alpha
        s0 = math.cos(theta) - dot * math.sin(theta) / sin_theta_0
        s1 = math.sin(theta) / sin_theta_0
        out = [s0 * x + s1 * y for x, y in zip(a, b)]
    norm = math.sqrt(sum(v * v for v in out)) or 1.0
    return [v / norm for v in out]


def _pick_font(ImageFont: Any, candidates: Sequence[str], size: int) -> Any:
    for candidate in candidates:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _decorate_video_frame(
    rgb_1080p: Any,
    *,
    Image: Any,
    ImageDraw: Any,
    font_title: Any,
    font_sub: Any,
    font_mono: Any,
    badge_text: str,
    stage_title_zh: str,
    readout_text: str,
    score: float,
) -> Any:
    base = Image.fromarray(rgb_1080p[:, :, :3].astype("uint8"), mode="RGB").resize(
        (1280, 720), Image.Resampling.LANCZOS
    )
    rgba = base.convert("RGBA")
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Top-left stage status card
    draw.rounded_rectangle(
        [(22, 18), (820, 96)],
        radius=12,
        fill=(12, 31, 52, 214),
        outline=(56, 189, 178, 175),
        width=2,
    )
    draw.rounded_rectangle(
        [(36, 30), (242, 56)],
        radius=6,
        fill=(8, 127, 120, 240),
    )
    draw.text((46, 34), badge_text, fill=(255, 255, 255, 255), font=font_mono)
    draw.text((256, 31), stage_title_zh, fill=(248, 251, 253, 255), font=font_title)
    draw.text((38, 66), readout_text, fill=(184, 206, 224, 245), font=font_sub)

    # Top-right live MetricsManager score gauge
    draw.rounded_rectangle(
        [(948, 18), (1258, 96)],
        radius=12,
        fill=(12, 31, 52, 214),
        outline=(215, 224, 232, 130),
        width=1,
    )
    draw.text(
        (966, 28),
        "GenManip MetricsManager",
        fill=(172, 194, 214, 245),
        font=font_sub,
    )
    score_color = (52, 211, 153, 255) if score >= 0.999 else (251, 191, 36, 255)
    draw.text(
        (1148, 24),
        f"{score:0.2f}",
        fill=score_color,
        font=font_title,
    )
    bar_x0, bar_y0, bar_x1, bar_y1 = 966, 66, 1240, 80
    draw.rounded_rectangle(
        [(bar_x0, bar_y0), (bar_x1, bar_y1)],
        radius=7,
        fill=(36, 59, 83, 235),
    )
    fill_w = int(round((bar_x1 - bar_x0) * max(0.0, min(1.0, score))))
    if fill_w > 4:
        draw.rounded_rectangle(
            [(bar_x0, bar_y0), (bar_x0 + fill_w, bar_y1)],
            radius=7,
            fill=(20, 184, 166, 255),
        )

    # Bottom claim-boundary ribbon
    draw.rounded_rectangle(
        [(22, 676), (760, 706)],
        radius=8,
        fill=(12, 31, 52, 196),
    )
    draw.text(
        (34, 683),
        "Privileged Object/Joint State Canary + Live PhysX Cavity Settling · Arm Trajectory -> Astra",
        fill=(214, 226, 238, 240),
        font=font_sub,
    )

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def _build_contact_sheet(
    keyframe_paths: Sequence[Path],
    out_path: Path,
    *,
    Image: Any,
    ImageDraw: Any,
    font_mono: Any,
) -> None:
    cols = 3
    rows = int(math.ceil(len(keyframe_paths) / float(cols)))
    tile_w, tile_h = 640, 360
    canvas = Image.new("RGB", (cols * tile_w, rows * tile_h), (15, 23, 42))
    draw = ImageDraw.Draw(canvas)
    for idx, p in enumerate(keyframe_paths):
        r, c = divmod(idx, cols)
        tile = Image.open(p).convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        canvas.paste(tile, (c * tile_w, r * tile_h))
        draw.rectangle(
            [(c * tile_w + 8, r * tile_h + 8), (c * tile_w + 300, r * tile_h + 36)],
            fill=(12, 31, 52),
        )
        draw.text(
            (c * tile_w + 16, r * tile_h + 13),
            p.name,
            fill=(255, 255, 255),
            font=font_mono,
        )
    canvas.save(out_path, format="PNG")


def _run_single_worker(
    collected_root: Path,
    media_out_dir: Path,
    genmanip_root: Path,
    *,
    profile: str = "r1",
    plan_file: Path | None = None,
    reprojection_grounding_json: Path | None = None,
    reprojection_out: Path | None = None,
) -> int:
    collected_root = collected_root.resolve()
    media_out_dir = media_out_dir.resolve()
    genmanip_root = genmanip_root.resolve()
    media_out_dir.mkdir(parents=True, exist_ok=True)
    if str(genmanip_root) not in sys.path:
        sys.path.insert(0, str(genmanip_root))

    specs = _media_specs_for_profile(profile, plan_file=plan_file)
    manifest = json.loads((collected_root / "package_manifest.json").read_text(encoding="utf-8"))
    package_id = str(manifest["package_id"])
    if package_id not in specs:
        raise ValueError(f"Unsupported scenario_id for canary media: {package_id!r}")
    spec = specs[package_id]

    entrypoints = manifest["entrypoints"]
    task_config_path = collected_root / entrypoints["task_config"]
    episode_path = collected_root / entrypoints["episode_metadata"]
    scene_path = collected_root / entrypoints["scene_usd"]
    camera_path = collected_root / entrypoints["camera_config"]

    task_config = yaml.safe_load(task_config_path.read_text(encoding="utf-8"))
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    task_name = str(episode["task_name"])
    task_data = copy.deepcopy(episode["task_data"])
    _resolve_collected_asset_paths(task_data, collected_root, package_id)

    matches = [
        copy.deepcopy(cfg)
        for cfg in task_config["evaluation_configs"]
        if cfg.get("task_name") == task_name
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one evaluation config for {task_name!r}")
    evaluation = matches[0]
    evaluation["usd_name"] = str(scene_path.with_suffix(""))
    evaluation["domain_randomization"]["cameras"]["config_path"] = str(camera_path)

    from isaacsim import SimulationApp

    simulation_app = SimulationApp(
        {
            "headless": True,
            "renderer": "RayTracedLighting",
            "anti_aliasing": 4,
            "multi_gpu": False,
            "width": 1920,
            "height": 1080,
        }
    )
    try:
        import carb.settings
        import numpy as np
        from omni.isaac.core.utils.types import ArticulationAction
        from PIL import Image, ImageDraw, ImageFont
        from pxr import Gf, UsdLux

        from genmanip.core.scene.scene import Scene
        from genmanip.core.scene.scene_config import SceneConfig
        from genmanip.utils.loader.domain_randomization import reset_scene
        from genmanip.utils.loader.scene import (
            cleanup_camera,
            create_camera_list,
            recovery_scene,
        )
        from genmanip.utils.standalone.file_utils import load_default_config
        from genmanip.utils.usd_utils.camera_utils import get_src, set_camera_look_at
        from genmanip.utils.usd_utils.prim_utils import clean_prim_velocity
        import genmanip.extensions.metrics  # noqa: F401

        settings = carb.settings.get_settings()
        settings.set("/rtx/post/aa/autoExposureMode", 0)
        settings.set("/rtx/post/aa/exposureMultiplier", 0.8)
        settings.set("/rtx/post/histogram/enabled", False)

        default_config = load_default_config(
            str(genmanip_root), "__scenario_forge_canary_media__.json", "local"
        )
        scene_config = SceneConfig(**evaluation)
        scene = Scene(scene_config)
        scene.initialize(
            default_config,
            physics_dt=float(evaluation.get("physics_dt", 1.0 / 60.0)),
            rendering_dt=float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            is_render=True,
            only_color_rep_for_camera=True,
        )
        scene.post_initialize()
        reset_scene(scene)

        preserved_parts = tuple(scene.articulation_part_list)
        recovered_task_data = copy.deepcopy(task_data)
        for part_id in preserved_parts:
            recovered_task_data["initial_layout"].setdefault(
                part_id, {"type": "articulation_part"}
            )
        recovery_scene(scene, recovered_task_data, task_name, default_config)

        for _ in range(50):
            scene.world.step(render=False)

        # Lock articulation PD drives at reset positions for 120-step cold-reset settling
        for uid, info in task_data["initial_layout"].items():
            if (
                isinstance(info, Mapping)
                and info.get("type") == "articulation"
                and uid in scene.articulation_list
            ):
                init_q = np.asarray(
                    scene.articulation_list[uid].get_joint_positions(), dtype=float
                )
                scene.articulation_list[uid].apply_action(
                    ArticulationAction(joint_positions=init_q.tolist())
                )
        for _ in range(120):
            scene.world.step(render=False)

        goal = copy.deepcopy(task_data["goal"])
        scene.build_metrics_manager(goal)
        metrics_manager = scene.metric_manager
        live_score = float(metrics_manager.step(scene))
        if live_score != 0.0:
            raise RuntimeError(f"Expected t=0 score 0.0 for {package_id}, got {live_score}")

        # Define interior 4-softbox studio lighting array AFTER physics warmup
        stage = scene.world.stage
        dome_light = UsdLux.DomeLight.Define(
            stage, "/World/ScenarioForgeCanaryMediaLight"
        )
        dome_light.CreateIntensityAttr(1100.0)
        dome_light.CreateColorAttr(Gf.Vec3f(1.0, 0.99, 0.97))

        interior_rig = (
            ("KeyFrontRight", (0.85, -1.15, 2.60), 11500.0, 0.50, (1.0, 0.98, 0.95)),
            ("FillFrontLeft", (-0.95, -1.05, 2.65), 8500.0, 0.55, (0.96, 0.98, 1.0)),
            ("WashRearLeft", (-1.65, 2.10, 2.80), 16500.0, 0.65, (1.0, 0.98, 0.95)),
            ("WashRearRight", (1.65, 2.10, 2.80), 16500.0, 0.65, (1.0, 0.98, 0.95)),
        )
        for lname, lpos, lintensity, lradius, lrgb in interior_rig:
            slight = UsdLux.SphereLight.Define(
                stage, f"/World/ScenarioForgeCanary_{lname}"
            )
            slight.CreateIntensityAttr(float(lintensity))
            slight.CreateRadiusAttr(float(lradius))
            slight.CreateColorAttr(Gf.Vec3f(*lrgb))
            slight.AddTranslateOp().Set(Gf.Vec3d(*lpos))

        cam_spec = spec["camera"]
        cam_cfg = {
            "exists": False,
            "frequency": 60,
            "name": "scenario_forge_canary_cam",
            "position": [0.0, 0.0, 1.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
            "prim_path": "_canary_showcase_cam",
            "resolution": [1920, 1080],
            "focal_length": float(cam_spec["focal_length"]),
            "horizontal_aperture": 10.0,
            "vertical_aperture": 5.625,
            "with_distance": False,
            "with_semantic": False,
            "with_bbox2d": False,
            "with_bbox3d": False,
            "with_motion_vector": False,
        }
        cam_map = create_camera_list(
            {"canary_cam": cam_cfg},
            scene.uuid,
            float(evaluation.get("rendering_dt", 1.0 / 60.0)),
            only_color_rep_for_camera=True,
        )
        camera = cam_map["canary_cam"]
        # Ensure Camera updates on every render() call even when physics time is frozen
        camera._frequency = -1
        set_camera_look_at(
            camera,
            np.asarray(cam_spec["target"], dtype=float),
            distance=float(cam_spec["distance"]),
            elevation=float(cam_spec["elevation"]),
            azimuth=float(cam_spec["azimuth"]),
        )

        def _read_live_rgb() -> Any:
            if getattr(camera, "_rgb_annotator", None) is not None:
                ann_data = camera._rgb_annotator.get_data()
                if isinstance(ann_data, np.ndarray) and ann_data.size > 0:
                    return ann_data[:, :, :3]
            return get_src(camera, "rgb")

        def _normalize_rgb_uint8(raw_value: Any) -> Any:
            arr = np.asarray(raw_value)
            if arr.ndim != 3 or arr.shape[2] < 3:
                raise RuntimeError(f"Unexpected RGB frame shape: {arr.shape}")
            rgb_only = arr[:, :, :3]
            if rgb_only.dtype == np.uint8:
                return rgb_only.copy()
            f_arr = np.nan_to_num(
                rgb_only.astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0
            )
            if f_arr.size:
                p99 = float(np.percentile(f_arr, 99.0))
                if p99 <= 2.0:
                    f_arr = f_arr * 255.0
            return np.clip(f_arr, 0.0, 255.0).astype(np.uint8)

        # Warm up RTX RenderProduct (50 renders, matching render_genmanip_initial_preview.py)
        warmup_ok = False
        for _ in range(50):
            scene.world.render()
        probe_rgb = _read_live_rgb()
        if probe_rgb is not None:
            raw_probe = np.asarray(probe_rgb)
            u8_probe = _normalize_rgb_uint8(raw_probe)
            cam_pos_w, cam_quat_w = camera.get_world_pose()
            print(
                f"[CanaryMedia] {package_id} cam_pos={np.round(cam_pos_w, 3).tolist()} "
                f"raw_dtype={raw_probe.dtype} raw_min={float(np.min(raw_probe)):.3f} "
                f"raw_max={float(np.max(raw_probe)):.3f} u8_mean={float(u8_probe.mean()):.2f} "
                f"u8_std={float(u8_probe.std()):.2f}",
                flush=True,
            )
            warmup_ok = u8_probe.shape[0] == 1080 and float(u8_probe.std()) >= 8.0
        if not warmup_ok:
            for _ in range(30):
                scene.world.render()

        font_title = _pick_font(ImageFont, CJK_FONT_CANDIDATES, 19)
        font_sub = _pick_font(ImageFont, CJK_FONT_CANDIDATES, 14)
        font_mono = _pick_font(ImageFont, MONO_FONT_CANDIDATES, 14)

        def _grab_rgb(accum_renders: int = 2) -> Any:
            for _ in range(accum_renders):
                scene.world.render()
            rgb = _read_live_rgb()
            tries = 0
            while rgb is None and tries < 25:
                scene.world.render()
                rgb = _read_live_rgb()
                tries += 1
            if rgb is None:
                raise RuntimeError(f"Camera returned None RGB in {package_id}")
            u8 = _normalize_rgb_uint8(rgb)
            if u8.shape[0] != 1080 or u8.shape[1] != 1920:
                raise RuntimeError(f"Unexpected frame shape {u8.shape}")
            std_val = float(u8.std())
            if std_val < 6.0:
                mean_val = float(u8.mean())
                raw_arr = np.asarray(rgb)
                raise RuntimeError(
                    f"Degenerate low-variance frame in {package_id} "
                    f"(u8_mean={mean_val:.2f}, u8_std={std_val:.2f}, "
                    f"raw_dtype={raw_arr.dtype}, raw_max={float(np.max(raw_arr)):.3f})"
                )
            return u8

        frames_tmp_dir = Path(tempfile.mkdtemp(prefix=f"canary_frames_{package_id}_"))
        video_frame_idx = 0

        def _emit_video_frame(
            rgb_1080p: Any,
            *,
            badge: str,
            title_zh: str,
            readout: str,
            score_val: float,
            repeat: int = 1,
        ) -> None:
            nonlocal video_frame_idx
            decorated = _decorate_video_frame(
                rgb_1080p,
                Image=Image,
                ImageDraw=ImageDraw,
                font_title=font_title,
                font_sub=font_sub,
                font_mono=font_mono,
                badge_text=badge,
                stage_title_zh=title_zh,
                readout_text=readout,
                score=score_val,
            )
            for _ in range(repeat):
                frame_path = frames_tmp_dir / f"frame_{video_frame_idx:05d}.png"
                decorated.save(frame_path, format="PNG", compress_level=1)
                video_frame_idx += 1

        keyframes_meta: list[dict[str, Any]] = []
        keyframe_paths: list[Path] = []

        # Optional camera-matched 4:3 RTX reprojection capture at t=0 (robot temporarily hidden)
        if reprojection_grounding_json is not None and reprojection_out is not None:
            from pxr import UsdGeom

            gdoc = json.loads(
                reprojection_grounding_json.resolve().read_text(encoding="utf-8")
            )
            gcam = gdoc["camera"]
            eye_arr = np.asarray(gcam["eye_xyz"], dtype=float)
            tgt_arr = np.asarray(gcam["target_xyz"], dtype=float)
            fov_deg = float(gcam.get("fov_deg", 72.0))
            horiz_ap = 10.0
            vert_ap = 7.5
            focal_len = 0.5 * horiz_ap / math.tan(math.radians(0.5 * fov_deg))

            hidden_robot_prims = []
            for r_obj in getattr(scene, "robot_list", []):
                r_path = getattr(r_obj, "prim_path", None)
                if r_path:
                    r_prim = stage.GetPrimAtPath(str(r_path))
                    if r_prim and r_prim.IsValid():
                        UsdGeom.Imageable(r_prim).MakeInvisible()
                        hidden_robot_prims.append(r_prim)
            for prim in stage.Traverse():
                p_str = str(prim.GetPath())
                if p_str.endswith("/lift2") or "/robots/" in p_str.lower():
                    if prim not in hidden_robot_prims and prim.IsA(UsdGeom.Imageable):
                        UsdGeom.Imageable(prim).MakeInvisible()
                        hidden_robot_prims.append(prim)

            reproj_cfg = {
                "exists": False,
                "frequency": 60,
                "name": "scenario_forge_reprojection_cam",
                "position": [0.0, 0.0, 1.0],
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "prim_path": "_reprojection_match_cam",
                "resolution": [1600, 1200],
                "focal_length": float(focal_len),
                "horizontal_aperture": horiz_ap,
                "vertical_aperture": vert_ap,
                "with_distance": False,
                "with_semantic": False,
                "with_bbox2d": False,
                "with_bbox3d": False,
                "with_motion_vector": False,
            }
            reproj_map = create_camera_list(
                {"reproj_cam": reproj_cfg},
                scene.uuid,
                float(evaluation.get("rendering_dt", 1.0 / 60.0)),
                only_color_rep_for_camera=True,
            )
            reproj_cam = reproj_map["reproj_cam"]
            reproj_cam._frequency = -1
            offset_vec = eye_arr - tgt_arr
            dist_m = float(np.linalg.norm(offset_vec))
            elev_deg = math.degrees(math.asin(float(offset_vec[2]) / max(dist_m, 1e-6)))
            azim_deg = math.degrees(math.atan2(float(offset_vec[1]), float(offset_vec[0])))
            set_camera_look_at(
                reproj_cam,
                tgt_arr,
                distance=dist_m,
                elevation=elev_deg,
                azimuth=azim_deg,
            )
            for _ in range(35):
                scene.world.render()
            reproj_raw = (
                reproj_cam._rgb_annotator.get_data()[:, :, :3]
                if getattr(reproj_cam, "_rgb_annotator", None) is not None
                else get_src(reproj_cam, "rgb")
            )
            reproj_u8 = _normalize_rgb_uint8(reproj_raw)
            reprojection_out_resolved = reprojection_out.resolve()
            reprojection_out_resolved.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(reproj_u8, mode="RGB").save(
                reprojection_out_resolved, format="PNG"
            )
            cleanup_camera(reproj_cfg, reproj_cam)
            for r_prim in hidden_robot_prims:
                UsdGeom.Imageable(r_prim).MakeVisible()
            for _ in range(10):
                scene.world.render()
            print(
                f"[CanaryMedia] Saved camera-matched 4:3 RTX reprojection: {reprojection_out_resolved}",
                flush=True,
            )

        # Capture t=0 keyframe + initial hold
        t0_rgb = _grab_rgb(accum_renders=10)
        t0_png = media_out_dir / "stage_00_t0.png"
        Image.fromarray(t0_rgb, mode="RGB").save(t0_png, format="PNG")
        keyframe_paths.append(t0_png)
        keyframes_meta.append(
            {
                "stage_key": "t0",
                "stage_index": -1,
                "badge": "t = 0 · COLD RESET",
                "title_zh": spec["t0_title_zh"],
                "predicate_desc": spec["t0_predicate"],
                "physics_readout": "120-step zero-action drift ≤ 0.001 mm · t0_score = 0.00",
                "score": 0.0,
                "image_filename": t0_png.name,
                "sha256": _file_sha256(t0_png),
                "resolution": [1920, 1080],
            }
        )
        _emit_video_frame(
            t0_rgb,
            badge="CANARY · t = 0",
            title_zh=spec["t0_title_zh"],
            readout=spec["t0_predicate"],
            score_val=0.0,
            repeat=20,
        )

        stages = spec["stages"]
        total_stages = len(stages)
        for st in stages:
            idx = int(st["stage_index"])
            badge_str = f"CANARY · STAGE {idx + 1}/{total_stages}"
            kind = st["kind"]
            readout_summary = ""

            if kind == "articulation_joint":
                art_id = st["object_id"]
                art = scene.articulation_list[art_id]
                dof_index = _resolve_dof_index(art, st, art_id)
                target_val = float(st["target_value"])
                interp_steps = int(st["interp_steps"])
                capture_every = int(st.get("capture_every", 1))
                settle_steps = int(st["settle_steps"])

                current_q = np.asarray(art.get_joint_positions(), dtype=float)
                start_val = float(current_q[dof_index])
                drive_effort = st.get("drive_effort")

                if drive_effort is not None:
                    efforts = [0.0 for _ in range(len(current_q))]
                    efforts[dof_index] = float(drive_effort)
                    for step_i in range(1, interp_steps + 1):
                        art.apply_action(ArticulationAction(joint_efforts=efforts))
                        scene.world.step(render=False)
                        live_score = float(metrics_manager.step(scene))
                        if step_i % capture_every == 0:
                            q_now = float(art.get_joint_positions()[dof_index])
                            rgb_now = _grab_rgb(accum_renders=2)
                            _emit_video_frame(
                                rgb_now,
                                badge=badge_str,
                                title_zh=st["title_zh"],
                                readout=f"{st['predicate_desc']}  |  joint[{dof_index}] = {q_now:+.4f}",
                                score_val=live_score,
                            )
                    zero_efforts = [0.0 for _ in range(len(current_q))]
                    art.apply_action(ArticulationAction(joint_efforts=zero_efforts))
                    for step_s in range(1, settle_steps + 1):
                        scene.world.step(render=False)
                        live_score = float(metrics_manager.step(scene))
                        if step_s % 3 == 0:
                            q_now = float(art.get_joint_positions()[dof_index])
                            rgb_now = _grab_rgb(accum_renders=2)
                            _emit_video_frame(
                                rgb_now,
                                badge=badge_str,
                                title_zh=st["title_zh"],
                                readout=f"PhysX rail settle  |  joint[{dof_index}] = {q_now:+.4f}",
                                score_val=live_score,
                            )
                else:
                    for step_i in range(1, interp_steps + 1):
                        alpha = step_i / float(interp_steps)
                        smooth = alpha * alpha * (3.0 - 2.0 * alpha)
                        cmd_q = current_q.copy()
                        cmd_q[dof_index] = start_val + smooth * (target_val - start_val)
                        art.set_joint_positions(cmd_q.tolist())
                        art.apply_action(ArticulationAction(joint_positions=cmd_q.tolist()))
                        scene.world.step(render=False)
                        live_score = float(metrics_manager.step(scene))
                        if step_i % capture_every == 0:
                            q_now = float(art.get_joint_positions()[dof_index])
                            rgb_now = _grab_rgb(accum_renders=2)
                            _emit_video_frame(
                                rgb_now,
                                badge=badge_str,
                                title_zh=st["title_zh"],
                                readout=f"{st['predicate_desc']}  |  joint[{dof_index}] = {q_now:+.4f}",
                                score_val=live_score,
                            )
                    final_q = np.asarray(art.get_joint_positions(), dtype=float)
                    final_q[dof_index] = target_val
                    art.set_joint_positions(final_q.tolist())
                    art.apply_action(ArticulationAction(joint_positions=final_q.tolist()))
                    for step_s in range(1, settle_steps + 1):
                        scene.world.step(render=False)
                        live_score = float(metrics_manager.step(scene))
                        if step_s % 3 == 0:
                            q_now = float(art.get_joint_positions()[dof_index])
                            rgb_now = _grab_rgb(accum_renders=2)
                            _emit_video_frame(
                                rgb_now,
                                badge=badge_str,
                                title_zh=st["title_zh"],
                                readout=f"PhysX joint settle  |  joint[{dof_index}] = {q_now:+.4f}",
                                score_val=live_score,
                            )

                q_end = [round(float(x), 5) for x in art.get_joint_positions()]
                readout_summary = f"{art_id}.joints = {q_end}"
                if "watch_cavity_object" in st:
                    w_obj = st["watch_cavity_object"]
                    w_rel = st["watch_relative_to"]
                    o_pos, _ = scene.object_list[w_obj].get_world_pose()
                    r_pos, _ = _lookup_reference_world_pose(scene, w_rel)
                    delta = np.asarray(o_pos, dtype=float) - np.asarray(r_pos, dtype=float)
                    z_lo, z_hi = st["watch_z_bounds_m"]
                    if not (float(z_lo) <= float(delta[2]) <= float(z_hi)):
                        raise RuntimeError(
                            f"Cavity pop-out in {package_id} stage {idx}: {delta.tolist()}"
                        )
                    readout_summary += (
                        f" · {w_obj} retained Δz={float(delta[2]):+.4f}m"
                    )

            elif kind in {"rigid_relative_arc", "rigid_world_arc"}:
                obj_id = st["object_id"]
                target_ori = [float(v) for v in st["orientation_wxyz"]]
                arc_frames = int(st["arc_frames"])
                arc_height = float(st["arc_height_m"])
                release_clearance = float(st["release_clearance_z_m"])
                settle_steps = int(st["settle_steps"])
                capture_every = int(st.get("capture_every", 2))

                start_pos_raw, start_ori_raw = scene.object_list[obj_id].get_world_pose()
                start_pos = np.asarray(start_pos_raw, dtype=float)
                start_ori = [float(v) for v in start_ori_raw]
                if kind == "rigid_world_arc":
                    hero_pos_arr = np.zeros(3, dtype=float)
                    target_pos = np.asarray(st["world_xyz_m"], dtype=float)
                else:
                    rel_id = st["relative_to"]
                    offset = np.asarray(st["offset_xyz_m"], dtype=float)
                    hero_pos, _ = _lookup_reference_world_pose(scene, rel_id)
                    hero_pos_arr = np.asarray(hero_pos, dtype=float)
                    target_pos = hero_pos_arr + offset
                release_pos = target_pos + np.asarray([0.0, 0.0, release_clearance], dtype=float)

                # Smooth parabolic kinematic arc + quaternion slerp alignment
                peak_z = max(float(start_pos[2]), float(release_pos[2])) + arc_height
                for f_i in range(1, arc_frames + 1):
                    t = f_i / float(arc_frames)
                    u = t * t * (3.0 - 2.0 * t)
                    xy = start_pos[:2] + u * (release_pos[:2] - start_pos[:2])
                    base_z = float(start_pos[2]) + u * (
                        float(release_pos[2]) - float(start_pos[2])
                    )
                    z = base_z + (peak_z - max(float(start_pos[2]), float(release_pos[2]))) * math.sin(
                        math.pi * u
                    )
                    pos_now = [float(xy[0]), float(xy[1]), float(z)]
                    ori_now = _quat_slerp_wxyz(start_ori, target_ori, u)
                    scene.object_list[obj_id].set_world_pose(pos_now, ori_now)
                    clean_prim_velocity(scene.object_list[obj_id].prim_path)
                    rgb_now = _grab_rgb(accum_renders=2)
                    _emit_video_frame(
                        rgb_now,
                        badge=badge_str,
                        title_zh=st["title_zh"],
                        readout=(
                            f"Kinematic approach & yaw-align  |  "
                            f"{obj_id} xyz=({pos_now[0]:+.3f}, {pos_now[1]:+.3f}, {pos_now[2]:+.3f})m"
                        ),
                        score_val=live_score,
                    )

                # Place cleanly at target_pos + tiny release clearance and step live PhysX gravity
                scene.object_list[obj_id].set_world_pose(
                    release_pos.tolist(), target_ori
                )
                clean_prim_velocity(scene.object_list[obj_id].prim_path)
                for step_s in range(1, settle_steps + 1):
                    scene.world.step(render=False)
                    live_score = float(metrics_manager.step(scene))
                    if step_s % capture_every == 0:
                        s_pos, _ = scene.object_list[obj_id].get_world_pose()
                        rgb_now = _grab_rgb(accum_renders=2)
                        _emit_video_frame(
                            rgb_now,
                            badge=badge_str,
                            title_zh=st["title_zh"],
                            readout=(
                                f"Live PhysX cavity settling  |  "
                                f"{obj_id} z={float(s_pos[2]):.4f}m"
                            ),
                            score_val=live_score,
                        )

                settled_pos, _ = scene.object_list[obj_id].get_world_pose()
                settled_arr = np.asarray(settled_pos, dtype=float)
                drift = float(np.linalg.norm(settled_arr - target_pos))
                if drift > float(st.get("max_settle_drift_m", 0.015)):
                    raise RuntimeError(
                        f"Excessive settle drift {drift:.4f}m for {obj_id} in {package_id}"
                    )
                rel_after = settled_arr - hero_pos_arr
                readout_summary = (
                    f"{obj_id} settled rel=({rel_after[0]:+.3f}, {rel_after[1]:+.3f}, "
                    f"{rel_after[2]:+.3f})m · drift={drift*1000:.2f}mm"
                )
            else:
                raise ValueError(f"Unsupported stage kind: {kind!r}")

            live_score = float(metrics_manager.step(scene))
            prev_score = float(keyframes_meta[-1]["score"])
            stage_floor = (idx + 1) / float(total_stages)
            if idx == total_stages - 1:
                if not math.isclose(live_score, 1.0, rel_tol=0.0, abs_tol=1e-4):
                    raise RuntimeError(
                        f"Final stage {idx} ({st['name']}) score mismatch in {package_id}: "
                        f"expected 1.0000, got {live_score:.4f}"
                    )
            else:
                next_stage_ceil = (idx + 2) / float(total_stages)
                if not (
                    stage_floor - 1e-4 <= live_score < next_stage_ceil - 1e-4
                    and live_score > prev_score + 1e-4
                ):
                    raise RuntimeError(
                        f"Stage {idx} ({st['name']}) score out of monotonic stage band in "
                        f"{package_id}: floor={stage_floor:.4f}, ceil={next_stage_ceil:.4f}, "
                        f"prev={prev_score:.4f}, got={live_score:.4f}"
                    )

            # High-sample lossless 1080p keyframe for this completed stage
            stage_rgb = _grab_rgb(accum_renders=10)
            stage_png = media_out_dir / f"stage_{idx + 1:02d}_{st['name']}.png"
            Image.fromarray(stage_rgb, mode="RGB").save(stage_png, format="PNG")
            keyframe_paths.append(stage_png)
            keyframes_meta.append(
                {
                    "stage_key": f"s{idx + 1}",
                    "stage_index": idx,
                    "badge": f"STAGE {idx + 1}/{total_stages}",
                    "title_zh": st["title_zh"],
                    "predicate_desc": st["predicate_desc"],
                    "physics_readout": readout_summary,
                    "score": round(live_score, 4),
                    "image_filename": stage_png.name,
                    "sha256": _file_sha256(stage_png),
                    "resolution": [1920, 1080],
                }
            )
            hold_frames = 30 if idx == total_stages - 1 else 14
            _emit_video_frame(
                stage_rgb,
                badge=badge_str,
                title_zh=st["title_zh"],
                readout=readout_summary,
                score_val=live_score,
                repeat=hold_frames,
            )

        mp4_path = media_out_dir / "progression.mp4"
        ffmpeg_cmd = [
            "/usr/bin/ffmpeg",
            "-y",
            "-framerate",
            "30",
            "-i",
            str(frames_tmp_dir / "frame_%05d.png"),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(mp4_path),
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        shutil.rmtree(frames_tmp_dir, ignore_errors=True)

        probe_cmd = [
            "/usr/bin/ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=codec_name,pix_fmt,width,height,nb_read_frames",
            "-of",
            "json",
            str(mp4_path),
        ]
        probe_out = json.loads(subprocess.check_output(probe_cmd, text=True))
        stream_info = probe_out["streams"][0]
        if (
            stream_info.get("codec_name") != "h264"
            or stream_info.get("pix_fmt") != "yuv420p"
            or int(stream_info.get("nb_read_frames", 0)) < 120
        ):
            raise RuntimeError(f"Invalid encoded MP4 stream for {package_id}: {stream_info}")

        contact_sheet_path = media_out_dir / "contact_sheet.png"
        _build_contact_sheet(
            keyframe_paths,
            contact_sheet_path,
            Image=Image,
            ImageDraw=ImageDraw,
            font_mono=font_mono,
        )

        media_manifest = {
            "schema_version": "out-of-domain-canary-media/v0.1",
            "scenario_id": package_id,
            "title_zh": spec["title_zh"],
            "camera": cam_spec,
            "video": {
                "filename": mp4_path.name,
                "sha256": _file_sha256(mp4_path),
                "size_bytes": mp4_path.stat().st_size,
                "codec": stream_info["codec_name"],
                "pix_fmt": stream_info["pix_fmt"],
                "resolution": [int(stream_info["width"]), int(stream_info["height"])],
                "frame_count": int(stream_info["nb_read_frames"]),
                "fps": 30,
            },
            "contact_sheet": {
                "filename": contact_sheet_path.name,
                "sha256": _file_sha256(contact_sheet_path),
            },
            "keyframes": keyframes_meta,
        }
        (media_out_dir / "canary_media_manifest.json").write_text(
            json.dumps(media_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        cleanup_camera(cam_cfg, camera)
        scene.world.stop()
        scene.world.clear_instance()
        print(
            f"[CanaryMedia] PASS {package_id}: {len(keyframes_meta)} keyframes, "
            f"{stream_info['nb_read_frames']} video frames ({mp4_path.stat().st_size / 1048576:.2f} MB)"
        )
        return 0
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(2)
    finally:
        simulation_app.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_file = (
        (
            args.plan_file
            if args.plan_file.is_absolute()
            else (REPO_ROOT / args.plan_file)
        ).resolve()
        if args.plan_file is not None
        else None
    )
    reproj_json = (
        (
            args.reprojection_grounding_json
            if args.reprojection_grounding_json.is_absolute()
            else (REPO_ROOT / args.reprojection_grounding_json)
        ).resolve()
        if args.reprojection_grounding_json is not None
        else None
    )
    reproj_out = (
        (
            args.reprojection_out
            if args.reprojection_out.is_absolute()
            else (REPO_ROOT / args.reprojection_out)
        ).resolve()
        if args.reprojection_out is not None
        else None
    )
    if args.single_collected_root is not None:
        if args.single_media_out is None:
            raise ValueError("--single-media-out is required with --single-collected-root")
        return _run_single_worker(
            args.single_collected_root,
            args.single_media_out,
            args.genmanip_root,
            profile=args.profile,
            plan_file=plan_file,
            reprojection_grounding_json=reproj_json,
            reprojection_out=reproj_out,
        )

    specs = _media_specs_for_profile(args.profile, plan_file=plan_file)
    out_root = (
        args.out_root if args.out_root.is_absolute() else (REPO_ROOT / args.out_root)
    ).resolve()
    isaac_python = args.isaac_python.resolve()
    genmanip_root = args.genmanip_root.resolve()
    worker_env = _isaac_environment(isaac_python, curobo_src=args.curobo_src)

    media_root = (
        (
            args.media_root
            if args.media_root.is_absolute()
            else (REPO_ROOT / args.media_root)
        ).resolve()
        if args.media_root is not None
        else (out_root / "showcase_media")
    )
    media_root.mkdir(parents=True, exist_ok=True)
    summary_items: list[dict[str, Any]] = []
    for scenario_id in specs:
        collected_dir = out_root / "packages" / scenario_id / "collected_package"
        scenario_media_dir = media_root / scenario_id
        cmd = [
            str(isaac_python),
            str(Path(__file__).resolve()),
            "--profile",
            args.profile,
            "--single-collected-root",
            str(collected_dir),
            "--single-media-out",
            str(scenario_media_dir),
            "--genmanip-root",
            str(genmanip_root),
        ]
        if plan_file is not None:
            cmd.extend(["--plan-file", str(plan_file)])
        if reproj_json is not None and reproj_out is not None:
            cmd.extend(
                [
                    "--reprojection-grounding-json",
                    str(reproj_json),
                    "--reprojection-out",
                    str(reproj_out),
                ]
            )
        completed = subprocess.run(cmd, cwd=genmanip_root, env=worker_env, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Canary media render failed for {scenario_id} (exit={completed.returncode})"
            )
        manifest_path = scenario_media_dir / "canary_media_manifest.json"
        summary_items.append(json.loads(manifest_path.read_text(encoding="utf-8")))

    summary_path = media_root / "canary_media_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": "out-of-domain-canary-media-summary/v0.1",
                "status": "pass",
                "scenarios": summary_items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote canary media summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

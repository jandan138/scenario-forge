"""Declarative M2 v0.4 7-task dual-arm distillation package builder + defective v0 generator."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.deformable_v02.usd_localizer import (
    _wrap_usd_asset,
    create_robot_pedestal_usd,
    localize_usd_asset_closures,
    vendor_franka_panda_assets,
)
from scenario_forge.adapters.deformable_v03.localizer_v03 import localize_v03_deformable_asset
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock


LEFT_BASE_XYZ = [-0.32, -0.46, 0.755]
RIGHT_BASE_XYZ = [0.32, -0.46, 0.755]
ARM_BASE_WXYZ = [0.7071067812, 0.0, 0.0, 0.7071067812]

V04_TASK_SPECS: dict[str, dict[str, Any]] = {
    "distill_01_burner_ring_flask_mount": {
        "order": 1,
        "task_family": "distill_burner_ring_flask_mount",
        "m1_asset_id": "v04_clamp_pad_01",
        "deformable_prim": "clamp_cushion_pad",
        "deformable_pose": {"xyz": [0.16, -0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "staged",
            "iron_ring_gauze": "staged",
            "distillation_flask": "staged",
        },
        "pose_overrides": {
            "alcohol_lamp": {"xyz": [0.06, -0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "iron_ring_gauze": {"xyz": [-0.04, -0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "distillation_flask": {"xyz": [-0.22, -0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        "hose_mode": None,
        "instruction": "双臂遵循从下到上SOP，摆正酒精灯、校准铁圈石棉网高度(0.865m外焰区)并放置硅胶护垫双臂稳妥夹持固定圆底蒸馏烧瓶。",
    },
    "distill_02_head_taper_coaxial_mate": {
        "order": 2,
        "task_family": "distill_head_taper_coaxial_mate",
        "m1_asset_id": "v04_ptfe_taper_sleeve_01",
        "deformable_prim": "ptfe_taper_sleeve",
        "deformable_pose": {"xyz": [0.02, -0.14, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "assembled",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "assembled",
            "distillation_head": "staged",
        },
        "pose_overrides": {
            "distillation_head": {"xyz": [0.14, -0.14, 0.785], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        "hose_mode": None,
        "instruction": "将中空PTFE锥形防咬套放入蒸馏烧瓶磨口颈部，双臂同轴(偏斜<=2.5°)将75°蒸馏头旋压配合至磨口底部(F<=12N)。",
    },
    "distill_03_thermometer_septum_align": {
        "order": 3,
        "task_family": "distill_thermometer_septum_align",
        "m1_asset_id": "v04_rubber_septum_01",
        "deformable_prim": "rubber_septum_adapter",
        "deformable_pose": {"xyz": [0.02, -0.14, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "assembled",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "assembled",
            "distillation_head": "assembled",
            "mercury_thermometer": "staged",
        },
        "pose_overrides": {
            "mercury_thermometer": {"xyz": [0.14, -0.14, 0.827], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        "hose_mode": None,
        "instruction": "右臂将中空橡胶套管座入蒸馏头上口，左臂垂直插入水银温度计直至汞球上沿精确齐平蒸馏头支管下口内缘(±2.0mm)。",
    },
    "distill_04_bimanual_hose_barb_couple": {
        "order": 4,
        "task_family": "distill_bimanual_hose_barb_couple",
        "m1_asset_id": "v04_dual_cooling_hoses_01",
        "deformable_prim": "dual_cooling_hoses",
        "deformable_pose": {"xyz": [0.0, 0.0, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "assembled",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "assembled",
            "distillation_head": "assembled",
            "mercury_thermometer": "assembled",
            "liebig_condenser": "assembled",
        },
        "pose_overrides": {},
        "hose_mode": "staged",
        "instruction": "左臂在玻璃水嘴根部旁托护直形冷凝管管身(M_nozzle<=0.45N·m防掰断)，右臂依次将蓝色进水管套上斜下方水嘴、橙红出水管套上斜上方水嘴，严格执行下进上出纯摩擦防滑配合。",
    },
    "distill_05_condenser_adapter_receiver_train": {
        "order": 5,
        "task_family": "distill_condenser_adapter_receiver_train",
        "m1_asset_id": "v04_clamp_pad_01",
        "deformable_prim": "condenser_clamp_pad",
        "deformable_pose": {"xyz": [0.019722, 0.0, 0.916], "wxyz": [0.98768834, 0.0, 0.15643447, 0.0]},
        "initial_states": {
            "alcohol_lamp": "assembled",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "assembled",
            "distillation_head": "assembled",
            "mercury_thermometer": "assembled",
            "liebig_condenser": "staged",
            "tail_adapter": "staged",
            "erlenmeyer_receiver": "staged",
        },
        "pose_overrides": {
            "liebig_condenser": {"xyz": [0.02, -0.15, 0.781], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "tail_adapter": {"xyz": [0.15, -0.15, 0.813], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "erlenmeyer_receiver": {"xyz": [0.24, -0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        "hose_mode": None,
        "instruction": "双臂呈-18°斜角将直形冷凝管同轴对接蒸馏头侧支管并稳座右铁架台带垫夹具，继续连接牛角尾接管并对正接收锥形瓶口。",
    },
    "distill_06_reverse_order_disassembly": {
        "order": 6,
        "task_family": "distill_reverse_order_disassembly",
        "m1_asset_id": "v04_dual_cooling_hoses_01",
        "deformable_prim": "dual_cooling_hoses",
        "deformable_pose": {"xyz": [0.0, 0.0, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "assembled",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "assembled",
            "distillation_head": "assembled",
            "mercury_thermometer": "assembled",
            "liebig_condenser": "assembled",
            "tail_adapter": "assembled",
            "erlenmeyer_receiver": "assembled",
        },
        "pose_overrides": {},
        "hose_mode": "assembled",
        "instruction": "从完整装配好的蒸馏系统出发，严格按“先右后左、先上后下”顺序拆除锥形瓶、尾接管、防弯断双护臂拔除冷却软管与冷凝管、温度计、蒸馏头及蒸馏烧瓶至防滑整备区。",
    },
    "distill_07_full_assembly_disassembly_sop": {
        "order": 7,
        "task_family": "distill_full_assembly_disassembly_sop",
        "m1_asset_id": "v04_dual_cooling_hoses_01",
        "deformable_prim": "dual_cooling_hoses",
        "deformable_pose": {"xyz": [0.0, 0.0, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "initial_states": {
            "alcohol_lamp": "staged",
            "iron_ring_gauze": "assembled",
            "distillation_flask": "staged",
            "distillation_head": "staged",
            "mercury_thermometer": "staged",
            "liebig_condenser": "staged",
            "tail_adapter": "staged",
            "erlenmeyer_receiver": "staged",
        },
        "pose_overrides": {
            "distillation_flask": {"xyz": [-0.24, -0.09, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "distillation_head": {"xyz": [-0.10, -0.09, 0.785], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "mercury_thermometer": {"xyz": [-0.02, -0.09, 0.827], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "liebig_condenser": {"xyz": [0.08, -0.09, 0.781], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "tail_adapter": {"xyz": [0.21, -0.09, 0.813], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "alcohol_lamp": {"xyz": [-0.18, -0.22, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "erlenmeyer_receiver": {"xyz": [0.27, -0.22, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        "hose_mode": "staged",
        "instruction": "全流程长程SOP闭环测试：先“从下到上、从左到右”完成全套蒸馏装置与下进上出双水路高精装配，保持检漏驻留，再按“先右后左、先上后下”有序安全拆除。",
    },
}


@dataclass(frozen=True)
class DistillationV04PackageResult:
    package_id: str
    package_root: Path
    scene_usd: Path
    asset_count: int
    deformable_asset_id: str


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _localize_cad_component(cad_comp_dir: Path, dest_dir: Path) -> Path:
    usda_txt = (cad_comp_dir / "asset.usda").read_text(encoding="utf-8")
    return _wrap_usd_asset(dest_dir, usda_txt)


def _camera_lookat_wxyz(eye: tuple[float, float, float], target: tuple[float, float, float]) -> tuple[float, float, float, float]:
    """Return USD Camera xformOp:orient wxyz (USD cameras look down -Z with +Y up)."""
    import math
    import numpy as np

    e = np.array(eye, dtype=np.float64)
    t = np.array(target, dtype=np.float64)
    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    z_c = (e - t) / max(float(np.linalg.norm(e - t)), 1e-12)
    x_c = np.cross(up, z_c)
    x_c = x_c / max(float(np.linalg.norm(x_c)), 1e-12)
    y_c = np.cross(z_c, x_c)
    r = np.column_stack([x_c, y_c, z_c])
    tr = r[0, 0] + r[1, 1] + r[2, 2]
    if tr > 0.0:
        s = 2.0 * math.sqrt(tr + 1.0)
        qw = 0.25 * s
        qx = (r[2, 1] - r[1, 2]) / s
        qy = (r[0, 2] - r[2, 0]) / s
        qz = (r[1, 0] - r[0, 1]) / s
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
        qw = (r[2, 1] - r[1, 2]) / s
        qx = 0.25 * s
        qy = (r[0, 1] + r[1, 0]) / s
        qz = (r[0, 2] + r[2, 0]) / s
    elif r[1, 1] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
        qw = (r[0, 2] - r[2, 0]) / s
        qx = (r[0, 1] + r[1, 0]) / s
        qy = 0.25 * s
        qz = (r[1, 2] + r[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
        qw = (r[1, 0] - r[0, 1]) / s
        qx = (r[0, 2] + r[2, 0]) / s
        qy = (r[1, 2] + r[2, 1]) / s
        qz = 0.25 * s
    return (float(qw), float(qx), float(qy), float(qz))


def build_v04_task_package(
    task_id: str,
    pkg_root: Path,
    *,
    m1_bundles_root: Path,
    m1_cad_root: Path,
    lab_source_root: Path,
    layout_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    defect_flags: Mapping[str, Any] | None = None,
) -> DistillationV04PackageResult:
    """Build one self-contained v0.4 dual-arm distillation scenario_package."""
    if task_id not in V04_TASK_SPECS:
        raise ValueError(f"Unknown v0.4 task_id: {task_id!r}")
    cfg = V04_TASK_SPECS[task_id]
    overrides = dict(layout_overrides or {})
    dflags = dict(defect_flags or {})

    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    assets_root = pkg_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    # 1. Localize wet chemistry lab room & static bench (no clutter on main workbench)
    env_id = "scientific_environment_code_room_wet_chemistry_v2"
    table_id = "scientific_workbench_ebench_table_static_support"
    broken = localize_usd_asset_closures(lab_source_root, assets_root, (env_id, table_id))
    if broken:
        raise ValueError(f"Broken USD paths in {task_id}: {broken}")

    # 2. Vendor Franka Panda + Pedestal
    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")

    # 3. Localize M1 CAD specs + all 12 parametric borosilicate glassware USD components
    cad_specs_src = m1_cad_root / "glassware_cad_specs.json"
    cad_specs = json.loads(cad_specs_src.read_text(encoding="utf-8"))
    shutil.copy2(cad_specs_src, assets_root / "glassware_cad_specs.json")
    for comp_id in cad_specs["components"]:
        _localize_cad_component(m1_cad_root / comp_id, assets_root / comp_id)

    # 4. Localize task's M1 volumetric deformable PBR bundle
    m1_aid = str(cfg["m1_asset_id"])
    def_prim = str(cfg["deformable_prim"])
    def_info = localize_v03_deformable_asset(
        m1_bundles_root / m1_aid,
        assets_root / m1_aid,
        prim_name=def_prim,
    )
    m1_man = def_info["m1_manifest"]
    budget = def_info["budget"]

    # Determine component initial poses
    comp_instances: list[dict[str, Any]] = []
    comp_ref_blocks: list[str] = []
    init_states = cfg["initial_states"]
    pose_ov = cfg["pose_overrides"]

    for comp_id, cdata in cad_specs["components"].items():
        if cdata["dynamic_in_sop"] and comp_id not in init_states:
            continue
        if comp_id == "iron_stand_right" and "liebig_condenser" not in init_states:
            continue
        if comp_id == "bench_water_ports" and cfg["hose_mode"] is None:
            continue
        st_mode = init_states.get(comp_id, "assembled")
        base_pose = (
            dict(pose_ov[comp_id])
            if comp_id in pose_ov
            else {
                "xyz": list(cdata["assembled_xyz"] if st_mode == "assembled" else cdata["staged_xyz"]),
                "wxyz": list(cdata["assembled_wxyz"] if st_mode == "assembled" else cdata["staged_wxyz"]),
            }
        )
        if comp_id in overrides:
            base_pose = dict(overrides[comp_id])
        role = "apparatus_fixture" if not cdata["dynamic_in_sop"] else (
            "apparatus_assembled" if st_mode == "assembled" else "apparatus_staged"
        )
        comp_instances.append(
            {
                "id": comp_id,
                "role": role,
                "asset_id": comp_id,
                "source_prim_path": f"/World/{comp_id}",
                "pose": base_pose,
                "dynamic_in_sop": bool(cdata["dynamic_in_sop"]),
                "initial_state": st_mode,
            }
        )
        x, y, z = base_pose["xyz"]
        qw, qx, qy, qz = base_pose["wxyz"]
        comp_ref_blocks.append(
            f"""    def Xform "{comp_id}" (
        prepend references = @../assets/{comp_id}/asset.usd@</World/{comp_id}>
    )
    {{
        double3 xformOp:translate = ({x:.6f}, {y:.6f}, {z:.6f})
        quatd xformOp:orient = ({qw:.7f}, {qx:.7f}, {qy:.7f}, {qz:.7f})
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}"""
        )

    # Deformable initial pose
    def_pose = dict(overrides.get(def_prim, cfg["deformable_pose"]))
    dx, dy, dz = def_pose["xyz"]
    dqw, dqx, dqy, dqz = def_pose["wxyz"]

    # Camera framing between both Franka arms facing +Y across entire distillation train
    cam_eye = (0.02, -1.22, 1.38)
    cam_tgt = (0.00, -0.02, 0.90)
    cam_q = _camera_lookat_wxyz(cam_eye, cam_tgt)

    scene_usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [
        @../assets/{m1_aid}/asset.usd@,
        @../assets/{table_id}/asset.usd@,
        @../assets/{env_id}/asset.usd@,
    ]
)

over "World"
{{
    double3 xformOp:translate = (0, 0, 0)
    quatd xformOp:orient = (1, 0, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]

    over "table"
    {{
        double3 xformOp:translate = (0.00000, 0.00000, 0.00000)
        quatd xformOp:orient = (1.000000, 0.000000, 0.000000, 0.000000)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    over "{def_prim}"
    {{
        double3 xformOp:translate = ({dx:.6f}, {dy:.6f}, {dz:.6f})
        quatd xformOp:orient = ({dqw:.7f}, {dqx:.7f}, {dqy:.7f}, {dqz:.7f})
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    def Xform "pedestal_left" (
        prepend references = @../assets/robot_pedestal/asset.usd@</World/robot_pedestal>
    )
    {{
        double3 xformOp:translate = ({LEFT_BASE_XYZ[0]:.5f}, {LEFT_BASE_XYZ[1]:.5f}, 0.00000)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    def Xform "pedestal_right" (
        prepend references = @../assets/robot_pedestal/asset.usd@</World/robot_pedestal>
    )
    {{
        double3 xformOp:translate = ({RIGHT_BASE_XYZ[0]:.5f}, {RIGHT_BASE_XYZ[1]:.5f}, 0.00000)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    def Xform "franka_left" (
        prepend references = @../assets/franka_panda/asset.usd@</World/franka_panda>
    )
    {{
        double3 xformOp:translate = ({LEFT_BASE_XYZ[0]:.5f}, {LEFT_BASE_XYZ[1]:.5f}, {LEFT_BASE_XYZ[2]:.5f})
        quatd xformOp:orient = ({ARM_BASE_WXYZ[0]:.7f}, {ARM_BASE_WXYZ[1]:.7f}, {ARM_BASE_WXYZ[2]:.7f}, {ARM_BASE_WXYZ[3]:.7f})
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    def Xform "franka_right" (
        prepend references = @../assets/franka_panda/asset.usd@</World/franka_panda>
    )
    {{
        double3 xformOp:translate = ({RIGHT_BASE_XYZ[0]:.5f}, {RIGHT_BASE_XYZ[1]:.5f}, {RIGHT_BASE_XYZ[2]:.5f})
        quatd xformOp:orient = ({ARM_BASE_WXYZ[0]:.7f}, {ARM_BASE_WXYZ[1]:.7f}, {ARM_BASE_WXYZ[2]:.7f}, {ARM_BASE_WXYZ[3]:.7f})
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}

    def Camera "ShowcaseCamera"
    {{
        float focalLength = 18.5
        float horizontalAperture = 20.955
        float2 clippingRange = (0.05, 50.0)
        double3 xformOp:translate = ({cam_eye[0]:.5f}, {cam_eye[1]:.5f}, {cam_eye[2]:.5f})
        quatd xformOp:orient = ({cam_q[0]:.7f}, {cam_q[1]:.7f}, {cam_q[2]:.7f}, {cam_q[3]:.7f})
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
    }}

{chr(10).join(comp_ref_blocks)}
}}
"""
    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(scene_usda, encoding="utf-8")

    # Build instances.yaml (preserving load_deformable_v02_package contract + dual-arm + glassware instances)
    def_record = {
        "id": def_prim,
        "role": "manipulated_deformable",
        "asset_id": m1_aid,
        "source_prim_path": f"/World/{def_prim}",
        "pose": def_pose,
        "deformable": {
            "structural_family": str(def_info["structural_family"]),
            "youngs_modulus_pa": float(m1_man["source"]["youngs_modulus_pa"]),
            "poissons_ratio": float(m1_man["source"]["poissons_ratio"]),
            "strain_metric": str(budget["strain_metric"]),
            "strain_onset_a": float(budget["strain_onset_a"]),
            "strain_failure_b": float(budget["strain_failure_b"]),
            "damage_threshold": float(budget["damage_threshold"]),
            "max_normal_force_n": float(budget["max_normal_force_n"]),
        },
    }
    instances: list[dict[str, Any]] = [
        {"id": "table", "role": "support_surface", "asset_id": table_id, "source_prim_path": "/World/table", "pose": {"xyz": [0, 0, 0], "wxyz": [1, 0, 0, 0]}},
        {"id": "franka_left", "role": "robot", "asset_id": "franka_panda", "source_prim_path": "/World/franka_left", "pose": {"xyz": LEFT_BASE_XYZ, "wxyz": ARM_BASE_WXYZ}},
        {"id": "franka_right", "role": "robot_right", "asset_id": "franka_panda", "source_prim_path": "/World/franka_right", "pose": {"xyz": RIGHT_BASE_XYZ, "wxyz": ARM_BASE_WXYZ}},
        def_record,
        *comp_instances,
    ]

    asset_entries = [
        {
            "asset_id": aid,
            "role": "environment" if aid == env_id else ("deformable" if aid == m1_aid else ("robot" if aid == "franka_panda" else "object")),
            "asset_type": "deformable" if aid == m1_aid else ("robot_urdf_usd" if aid == "franka_panda" else "usd"),
            "canonical_usd": f"assets/{aid}/asset.usd",
            "license": "BSD-3-Clause" if aid == "franka_panda" else "internal-non-commercial",
            "sha256": compute_sha256(assets_root / aid / "asset.usd"),
        }
        for aid in sorted([p.name for p in assets_root.iterdir() if p.is_dir()])
    ]
    _write_yaml(pkg_root / "assets" / "asset_manifest.yaml", {"schema_version": "asset-manifest/v0.2", "assets": asset_entries})
    _write_yaml(pkg_root / "scene" / "instances.yaml", {"schema_version": "scene-instances/v0.4", "package_id": task_id, "instances": instances})

    _write_yaml(
        pkg_root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.4",
            "profile_ref": "manip/dual_franka_panda/tabletop_18dof_v1",
            "embodiment_id": "dual_franka_panda_bimanual",
            "urdf_path": "assets/franka_panda/panda.urdf",
            "mjcf_path": "assets/franka_panda/panda.xml",
            "usd_path": "assets/franka_panda/asset.usd",
            "action_dim": 18,
            "spawn": {"xyz": LEFT_BASE_XYZ, "wxyz": ARM_BASE_WXYZ},
            "arms": {
                "franka_left": {"xyz": LEFT_BASE_XYZ, "wxyz": ARM_BASE_WXYZ, "prim_path": "/World/franka_left"},
                "franka_right": {"xyz": RIGHT_BASE_XYZ, "wxyz": ARM_BASE_WXYZ, "prim_path": "/World/franka_right"},
            },
        },
    )
    _write_yaml(
        pkg_root / "task" / "task.yaml",
        {"schema_version": "task/v0.5", "task_id": task_id, "task_family": cfg["task_family"], "instruction": cfg["instruction"]},
    )
    _write_yaml(pkg_root / "task" / "graph.yaml", {"schema_version": "task-graph/v0.2", "nodes": [{"id": "execute_skill", "skill": cfg["task_family"]}], "edges": []})
    _write_yaml(
        pkg_root / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"id": "deformable_integrity_preserved", "type": "deformable_integrity_preserved", "sequence_index": 0, "parameters": {"object": def_prim, "max_damage_score": float(budget["damage_threshold"])}},
            ],
        },
    )
    sem_dir = pkg_root / "semantics"
    sem_dir.mkdir(parents=True, exist_ok=True)
    task_spec_doc = {
        "schema_version": "distillation_v04_task_spec/v0.1",
        "task_id": task_id,
        "order": cfg["order"],
        "embodiment_id": "dual_franka_panda_bimanual",
        "action_dim": 18,
        "deformable_asset_id": m1_aid,
        "deformable_prim": def_prim,
        "hose_mode": cfg["hose_mode"],
        "coaxial_layout": cad_specs["layout"],
        "defect_flags": dflags,
        "precision_thresholds": {
            "peak_nozzle_moment_nm": 0.45,
            "peak_taper_tilt_deg": 2.5,
            "peak_joint_force_n": 12.0,
            "bulb_align_error_mm": 2.0,
            "flow_rule": "bottom_in_top_out",
            "assembly_order": "bottom_to_top_left_to_right",
            "disassembly_order": "right_to_left_top_to_bottom",
        },
    }
    (sem_dir / "task_spec.json").write_text(json.dumps(task_spec_doc, indent=2), encoding="utf-8")

    _write_yaml(pkg_root / "scenario.yaml", {"schema_version": "scenario-spec/v0.6", "scenario_id": task_id, "domain": "scientific_workbench", "task_family": cfg["task_family"], "instruction": cfg["instruction"], "objects": instances})
    _write_yaml(
        pkg_root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": task_id,
            "scenario_domain": "scientific_workbench",
            "entrypoints": {
                "scenario_spec": "scenario.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_graph": "task/graph.yaml",
                "predicates": "task/predicates.yaml",
                "robot": "robot/robot.yaml",
                "task_spec": "semantics/task_spec.json",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
        },
    )
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id=f"{task_id}_v04_lock"))
    return DistillationV04PackageResult(
        package_id=task_id,
        package_root=pkg_root,
        scene_usd=scene_path,
        asset_count=len(asset_entries),
        deformable_asset_id=m1_aid,
    )


def build_distillation_v04_packages(
    output_root: Path | None = None,
    m1_bundles_root: Path | None = None,
    m1_cad_root: Path | None = None,
    lab_source_root: Path | None = None,
) -> dict[str, DistillationV04PackageResult]:
    """Build all 7 nominal distillation_v04 scenario packages."""
    repo_root = Path(__file__).resolve().parents[4]
    out_r = output_root or (repo_root / "external_artifacts" / "distillation_v04_packages")
    m1_b = m1_bundles_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_bundles")
    m1_c = m1_cad_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_cad")
    lab_r = lab_source_root or (repo_root / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle")

    out: dict[str, DistillationV04PackageResult] = {}
    for task_id in V04_TASK_SPECS:
        out[task_id] = build_v04_task_package(
            task_id,
            out_r / task_id / "scenario_package",
            m1_bundles_root=m1_b,
            m1_cad_root=m1_c,
            lab_source_root=lab_r,
        )
    return out


def build_distillation_v04_defective_packages(
    defective_root: Path | None = None,
    m1_bundles_root: Path | None = None,
    m1_cad_root: Path | None = None,
    lab_source_root: Path | None = None,
) -> dict[str, DistillationV04PackageResult]:
    """Build defective v0 scene packages used for live EOS self-healing closed loops."""
    import math

    repo_root = Path(__file__).resolve().parents[4]
    def_r = defective_root or (repo_root / "external_artifacts" / "distillation_v04_defective_v0")
    m1_b = m1_bundles_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_bundles")
    m1_c = m1_cad_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_cad")
    lab_r = lab_source_root or (repo_root / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle")

    tilt_rad = math.radians(5.8)
    q_tilt = [math.cos(0.5 * tilt_rad), math.sin(0.5 * tilt_rad), 0.0, 0.0]

    # Defect A: distill_02 with tilted + shifted distillation_flask & left stand (causes taper jam >2.5 deg & >12 N)
    res_d2 = build_v04_task_package(
        "distill_02_head_taper_coaxial_mate",
        def_r / "distill_02_head_taper_coaxial_mate" / "scenario_package",
        m1_bundles_root=m1_b,
        m1_cad_root=m1_c,
        lab_source_root=lab_r,
        layout_overrides={
            "distillation_flask": {"xyz": [-0.162, 0.012, 0.870], "wxyz": q_tilt},
            "iron_stand_left": {"xyz": [-0.162, 0.092, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        defect_flags={"scene_fixture_tilted": True, "flask_tilt_deg": 5.8, "flask_lateral_offset_m": 0.018},
    )

    # Defect B: distill_01 with miscalibrated iron_ring_gauze (+38mm above outer flame zone)
    res_d1 = build_v04_task_package(
        "distill_01_burner_ring_flask_mount",
        def_r / "distill_01_burner_ring_flask_mount" / "scenario_package",
        m1_bundles_root=m1_b,
        m1_cad_root=m1_c,
        lab_source_root=lab_r,
        layout_overrides={
            "iron_ring_gauze": {"xyz": [-0.04, -0.15, 0.793], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
        defect_flags={"scene_ring_height_miscalibrated": True, "ring_height_offset_m": 0.038},
    )

    return {
        "distill_02_head_taper_coaxial_mate": res_d2,
        "distill_01_burner_ring_flask_mount": res_d1,
    }

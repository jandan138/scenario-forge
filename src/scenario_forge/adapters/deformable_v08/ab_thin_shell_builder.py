"""Frozen-hash A/B thin-shell scenario package builder for HermiteTwin v0.8 (M2).

Generates paired `baseline_spring_mass` (Old) and `hermitetwin_shell` (New) scenario packages
sharing identical initial rest geometry, gripper trajectories, rigid obstacles, and MetricsManager
task goals, verified by SHA-256 invariance receipts. Pure package layer: zero simulator SDK imports.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

import yaml


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _rot_y(angle_rad: float) -> list[list[float]]:
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return [
        [c, 0.0, s],
        [0.0, 1.0, 0.0],
        [-s, 0.0, c],
    ]


def _interp_waypoints(
    waypoints: list[tuple[int, list[float], float, float]],
    total_frames: int,
) -> list[dict[str, Any]]:
    """Piecewise-smooth cosine-eased gripper trajectory [pos_xyz, rot_3x3, gap_m]."""
    traj: list[dict[str, Any]] = []
    for f in range(total_frames):
        # Find bracketing waypoints
        w0 = waypoints[0]
        w1 = waypoints[-1]
        for k in range(len(waypoints) - 1):
            if waypoints[k][0] <= f <= waypoints[k + 1][0]:
                w0 = waypoints[k]
                w1 = waypoints[k + 1]
                break
        if w1[0] == w0[0]:
            alpha = 0.0
        else:
            raw = (f - w0[0]) / float(w1[0] - w0[0])
            alpha = 0.5 * (1.0 - math.cos(math.pi * max(0.0, min(1.0, raw))))

        pos = [w0[1][i] + alpha * (w1[1][i] - w0[1][i]) for i in range(3)]
        pitch = w0[2] + alpha * (w1[2] - w0[2])
        gap = w0[3] + alpha * (w1[3] - w0[3])
        traj.append(
            {
                "frame": f,
                "pos_xyz": [round(float(v), 6) for v in pos],
                "rot_3x3": [[round(float(x), 6) for x in row] for row in _rot_y(pitch)],
                "gap_m": round(float(gap), 6),
            }
        )
    return traj


V08_THIN_SHELL_AB_TASKS: dict[str, dict[str, Any]] = {
    "v08_cloth_corner_fold": {
        "title": "Cloth Corner Diagonal Folding",
        "title_cn": "织物捏角对折（锐利折痕还原）",
        "structural_family": "cloth_sheet",
        "domain": "modern_office",
        "room_source": "r3_office",
        "table_z_m": 0.755,
        "dt_s": 1.0 / 48.0,
        "total_frames": 96,
        "train_split_frame": 58,
        "sheet": {
            "asset_id": "v08_woven_towel_01",
            "nx": 4,
            "ny": 4,
            "length_u_m": 0.30,
            "length_v_m": 0.30,
            "thickness_m": 0.0016,
            "area_density_kg_m2": 0.28,
            "youngs_modulus_pa": 95000.0,
            "poissons_ratio": 0.30,
            "bending_stiffness_scale": 1.0,
            "membrane_stiffness_scale": 1.0,
            "rayleigh_mass_damp": 1.2,
            "rayleigh_stiff_damp": 0.006,
            "base_rgb": [0.22, 0.56, 0.80],
            "pattern": "woven_grid",
        },
        "obstacles": [],
        "waypoints": [
            (0, [-0.125, -0.125, 0.758], 0.0, 0.032),
            (6, [-0.125, -0.125, 0.757], 0.0, 0.003),
            (18, [-0.090, -0.090, 0.855], 0.15, 0.003),
            (38, [0.015, 0.015, 0.885], 0.30, 0.003),
            (58, [0.090, 0.090, 0.785], 0.15, 0.003),
            (68, [0.095, 0.095, 0.766], 0.0, 0.003),
            (74, [0.095, 0.095, 0.772], 0.0, 0.028),
            (84, [0.095, 0.095, 0.840], 0.0, 0.032),
            (95, [0.095, 0.095, 0.840], 0.0, 0.032),
        ],
        "novel_action": None,
        "instruction": "捏住方形织物前左角，沿弧线提起并斜向对折至对角区域，停稳后松爪撤离并保持清晰折痕。",
    },
    "v08_stiff_foam_sheet_transfer": {
        "title": "Stiff Foam Sheet Edge-Clamped Transfer",
        "title_cn": "高刚度薄泡沫板夹边搬运（面外挺括度保持）",
        "structural_family": "shell",
        "domain": "electronics_qa_station",
        "room_source": "r3_smt",
        "table_z_m": 0.755,
        "dt_s": 1.0 / 48.0,
        "total_frames": 88,
        "train_split_frame": 52,
        "sheet": {
            "asset_id": "v08_esd_foam_sheet_01",
            "nx": 4,
            "ny": 4,
            "length_u_m": 0.26,
            "length_v_m": 0.18,
            "thickness_m": 0.0080,
            "area_density_kg_m2": 0.55,
            "youngs_modulus_pa": 480000.0,
            "poissons_ratio": 0.28,
            "bending_stiffness_scale": 1.0,
            "membrane_stiffness_scale": 1.0,
            "rayleigh_mass_damp": 1.4,
            "rayleigh_stiff_damp": 0.005,
            "base_rgb": [0.85, 0.55, 0.26],
            "pattern": "foam_speckle",
        },
        "obstacles": [],
        "waypoints": [
            (0, [-0.105, 0.0, 0.761], 0.0, 0.034),
            (6, [-0.105, 0.0, 0.760], 0.0, 0.006),
            (24, [-0.085, 0.0, 0.885], -0.34, 0.006),
            (52, [0.020, 0.0, 0.895], -0.20, 0.006),
            (68, [0.085, 0.0, 0.775], 0.0, 0.006),
            (74, [0.085, 0.0, 0.778], 0.0, 0.030),
            (87, [0.085, 0.0, 0.845], 0.0, 0.034),
        ],
        "novel_action": None,
        "instruction": "夹持 8 mm 厚高刚度 ESD 泡沫板前缘，离桌抬升 13 cm 并俯仰平移至目标区释放，保持平面挺括不塌陷。",
    },
    "v08_contact_drape_peel_novel": {
        "title": "Cover Peel + Novel Drape Over Rigid Block",
        "title_cn": "盖布揭取预测与未见覆物动作迁移（接触解析）",
        "structural_family": "cloth_sheet",
        "domain": "specialty_coffee_bar",
        "room_source": "r3_coffee",
        "table_z_m": 0.755,
        "dt_s": 1.0 / 48.0,
        "total_frames": 92,
        "train_split_frame": 54,
        "sheet": {
            "asset_id": "v08_linen_cover_01",
            "nx": 4,
            "ny": 4,
            "length_u_m": 0.32,
            "length_v_m": 0.24,
            "thickness_m": 0.0020,
            "area_density_kg_m2": 0.30,
            "youngs_modulus_pa": 115000.0,
            "poissons_ratio": 0.31,
            "bending_stiffness_scale": 1.0,
            "membrane_stiffness_scale": 1.0,
            "rayleigh_mass_damp": 1.2,
            "rayleigh_stiff_damp": 0.006,
            "base_rgb": [0.30, 0.68, 0.56],
            "pattern": "woven_grid",
        },
        "obstacles": [],
        "waypoints": [
            (0, [-0.135, -0.095, 0.758], 0.0, 0.032),
            (6, [-0.135, -0.095, 0.757], 0.0, 0.003),
            (28, [-0.040, -0.030, 0.865], 0.20, 0.003),
            (54, [0.055, 0.030, 0.860], 0.15, 0.003),
            (72, [0.095, 0.055, 0.768], 0.0, 0.003),
            (78, [0.095, 0.055, 0.774], 0.0, 0.028),
            (91, [0.095, 0.055, 0.840], 0.0, 0.032),
        ],
        "novel_action": {
            "total_frames": 84,
            "obstacles": [
                {
                    "obstacle_id": "calibration_book_block",
                    "center_xyz": [0.075, 0.0, 0.7775],
                    "half_extents_xyz": [0.065, 0.060, 0.0225],
                }
            ],
            "waypoints": [
                (0, [-0.135, 0.0, 0.758], 0.0, 0.032),
                (6, [-0.135, 0.0, 0.757], 0.0, 0.003),
                (26, [-0.030, 0.0, 0.885], 0.18, 0.003),
                (52, [0.115, 0.0, 0.875], 0.10, 0.003),
                (64, [0.135, 0.0, 0.788], 0.0, 0.003),
                (70, [0.135, 0.0, 0.794], 0.0, 0.028),
                (83, [0.135, 0.0, 0.855], 0.0, 0.032),
            ],
        },
        "instruction": "前 60% 轨迹揭角辨识织物力学与接触参数，后 40% 预测落桌过程，并将冻结孪生体零样本迁移至覆盖刚体书块新动作。",
    },
}


def build_v08_ab_scenario_package(
    task_id: str,
    out_dir: str | Path,
) -> dict[str, Any]:
    """Compile paired frozen-hash A/B scenario packages for one HermiteTwin task."""
    if task_id not in V08_THIN_SHELL_AB_TASKS:
        raise KeyError(f"Unknown v0.8 task_id {task_id!r}")
    cfg = V08_THIN_SHELL_AB_TASKS[task_id]
    root = Path(out_dir) / task_id
    root.mkdir(parents=True, exist_ok=True)

    main_traj = _interp_waypoints(cfg["waypoints"], int(cfg["total_frames"]))
    novel_spec = cfg.get("novel_action")
    novel_traj = (
        _interp_waypoints(novel_spec["waypoints"], int(novel_spec["total_frames"]))
        if novel_spec
        else None
    )

    shared_hashes = {
        "init_sheet_sha256": _canonical_sha256(cfg["sheet"]),
        "gripper_trajectory_sha256": _canonical_sha256(main_traj),
        "novel_action_trajectory_sha256": _canonical_sha256(novel_traj) if novel_traj else None,
        "obstacles_sha256": _canonical_sha256(cfg["obstacles"]),
        "task_goal_sha256": _canonical_sha256(
            {
                "task_id": task_id,
                "structural_family": cfg["structural_family"],
                "table_z_m": cfg["table_z_m"],
                "train_split_frame": cfg["train_split_frame"],
                "instruction": cfg["instruction"],
            }
        ),
    }

    variant_dirs: dict[str, str] = {}
    for arm in ("ground_truth_ref", "baseline_spring_mass", "hermitetwin_shell"):
        arm_dir = root / arm
        (arm_dir / "task").mkdir(parents=True, exist_ok=True)
        (arm_dir / "scene").mkdir(parents=True, exist_ok=True)

        manifest = {
            "schema_version": "scenario-forge-ab-thin-shell/v0.8",
            "task_id": task_id,
            "arm": arm,
            "domain": cfg["domain"],
            "room_source": cfg["room_source"],
            "structural_family": cfg["structural_family"],
            "shared_invariance_hashes": shared_hashes,
        }
        (arm_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        (arm_dir / "task" / "task.yaml").write_text(
            yaml.safe_dump(
                {
                    "task_id": task_id,
                    "instruction": cfg["instruction"],
                    "dt_s": cfg["dt_s"],
                    "total_frames": cfg["total_frames"],
                    "train_split_frame": cfg["train_split_frame"],
                    "novel_action": novel_spec,
                },
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        (arm_dir / "scene" / "instances.yaml").write_text(
            yaml.safe_dump(
                {
                    "table_z_m": cfg["table_z_m"],
                    "sheet": cfg["sheet"],
                    "obstacles": cfg["obstacles"],
                },
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        (arm_dir / "gripper_trajectory.json").write_text(
            json.dumps({"main": main_traj, "novel": novel_traj}, indent=2), encoding="utf-8"
        )
        variant_dirs[arm] = arm_dir.resolve().as_posix()

    receipt = {
        "schema_version": "scenario-forge-v08-ab-invariance/v0.1",
        "task_id": task_id,
        "geometry_and_trajectory_frozen": True,
        "shared_invariance_hashes": shared_hashes,
        "arm_dirs": variant_dirs,
    }
    receipt_path = root / "ab_invariance_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def build_all_v08_ab_packages(out_dir: str | Path) -> dict[str, Any]:
    """Compile all 3 canonical v0.8 A/B thin-shell scenario packages."""
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    results = {}
    for task_id in V08_THIN_SHELL_AB_TASKS:
        results[task_id] = build_v08_ab_scenario_package(task_id, out_root)
    summary = {
        "schema_version": "scenario-forge-v08-ab-suite/v0.1",
        "task_ids": list(V08_THIN_SHELL_AB_TASKS.keys()),
        "tasks": results,
    }
    summary_path = out_root / "v08_ab_packages_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

"""Parametric scene remediation handler for EOS v0.4 distillation closed-loop self-healing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scenario_forge.adapters.distillation_v04.package_builder_v04 import (
    V04_TASK_SPECS,
    build_v04_task_package,
)


def apply_scene_remediation_v04(
    task_id: str,
    repaired_package_dir: Path,
    eos_advice: Mapping[str, Any],
    *,
    m1_bundles_root: Path | None = None,
    m1_cad_root: Path | None = None,
    lab_source_root: Path | None = None,
) -> dict[str, Any]:
    """Repair EOS-flagged stand coaxiality, tilt, or ring height defect and rebuild a valid v1 package."""
    repo_root = Path(__file__).resolve().parents[4]
    m1_b = m1_bundles_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_bundles")
    m1_c = m1_cad_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "distillation_v04_cad")
    lab_r = lab_source_root or (repo_root / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle")

    if task_id not in V04_TASK_SPECS:
        raise ValueError(f"Unknown v0.4 task_id for remediation: {task_id!r}")
    cad_specs = json.loads((m1_c / "glassware_cad_specs.json").read_text(encoding="utf-8"))
    comps = cad_specs["components"]
    reason = str(eos_advice.get("reason_code", ""))
    actions_taken: list[str] = []
    overrides: dict[str, dict[str, Any]] = {}

    if reason in (
        "ground_joint_tilt_jam_fracture",
        "scene_stand_coaxial_misalignment",
        "scene_target_unreachable_or_misaligned",
    ):
        overrides["distillation_flask"] = {
            "xyz": list(comps["distillation_flask"]["assembled_xyz"]),
            "wxyz": list(comps["distillation_flask"]["assembled_wxyz"]),
        }
        overrides["iron_stand_left"] = {
            "xyz": list(comps["iron_stand_left"]["assembled_xyz"]),
            "wxyz": list(comps["iron_stand_left"]["assembled_wxyz"]),
        }
        actions_taken.append(
            "Re-centered iron_stand_left & distillation_flask to 0.0° coaxial vertical datum (-0.18, 0.00, 0.870)"
        )

    if reason in ("scene_ring_height_miscalibrated", "scene_clearance_or_spawn_mismatch"):
        overrides["iron_ring_gauze"] = {
            "xyz": list(comps["iron_ring_gauze"]["staged_xyz"]),
            "wxyz": list(comps["iron_ring_gauze"]["staged_wxyz"]),
        }
        actions_taken.append("Restored iron_ring_gauze staging datum for 0.865m outer-flame calibration")

    res = build_v04_task_package(
        task_id,
        repaired_package_dir,
        m1_bundles_root=m1_b,
        m1_cad_root=m1_c,
        lab_source_root=lab_r,
        layout_overrides=overrides,
        defect_flags={},
    )
    return {
        "task_id": task_id,
        "repaired_package_dir": str(res.package_root),
        "reason_code": reason,
        "actions_taken": actions_taken,
        "layout_overrides": overrides,
    }


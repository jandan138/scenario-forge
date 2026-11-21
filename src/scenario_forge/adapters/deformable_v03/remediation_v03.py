"""Parametric scene remediation handler for EOS closed-loop self-healing (scenario-forge v0.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from scenario_forge.adapters.deformable_v03.package_builder_v03 import (
    V03_TASK_SPECS,
    build_v03_task_package,
)


def apply_scene_remediation(
    task_id: str,
    repaired_package_dir: Path,
    eos_advice: Mapping[str, Any],
    *,
    m1_bundles_root: Path | None = None,
    r3_packages_root: Path | None = None,
    lab_source_root: Path | None = None,
) -> dict[str, Any]:
    """Repair an EOS-flagged scene layout defect and rebuild a valid v1 scenario_package."""
    repo_root = Path(__file__).resolve().parents[4]
    m1_r = m1_bundles_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "deformable_v03_bundles")
    r3_r = r3_packages_root or (repo_root / "external_artifacts" / "out_of_domain_factory_r3_20261113" / "packages")
    lab_r = lab_source_root or (repo_root / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle")

    reason = str(eos_advice.get("reason_code", ""))
    nominal = V03_TASK_SPECS[task_id]
    overrides: dict[str, dict[str, Any]] = {}
    actions_taken: list[str] = []

    if reason in ("scene_obstacle_blocking_target", "scene_clearance_or_spawn_mismatch"):
        # Relocate obstructing ESDTray / PCBACarrierBoard back to nominal staging zone clear of target clip
        overrides["ESDTray"] = {"xyz": [-0.42, -0.18, 0.757], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}
        overrides["PCBACarrierBoard"] = {"xyz": [-0.42, -0.18, 0.7635], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}
        actions_taken.append("Relocated obstructing prop ESDTray to (-0.42, -0.18, 0.757) clearing target workspace")

    if reason in ("scene_target_unreachable_or_misaligned", "scene_clearance_or_spawn_mismatch"):
        if "target_fixture" in nominal["fixtures"]:
            nom_pose = nominal["fixtures"]["target_fixture"][1]
            overrides["target_fixture"] = dict(nom_pose)
            actions_taken.append(f"Clamped target_fixture pose inside Franka reachable envelope: {nom_pose['xyz']}")

    res = build_v03_task_package(
        task_id,
        repaired_package_dir,
        m1_bundles_root=m1_r,
        r3_packages_root=r3_r,
        lab_source_root=lab_r,
        layout_overrides=overrides,
    )
    return {
        "task_id": task_id,
        "repaired_package_dir": str(res.package_root),
        "reason_code": reason,
        "actions_taken": actions_taken,
        "layout_overrides": overrides,
    }


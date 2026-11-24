"""Tests for scenario-forge v0.8 frozen-hash A/B thin-shell packages."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scenario_forge.adapters.deformable_v08 import (
    V08_THIN_SHELL_AB_TASKS,
    build_all_v08_ab_packages,
)


def test_v08_ab_packages_enforce_identical_geometry_and_trajectories(tmp_path: Path) -> None:
    summary = build_all_v08_ab_packages(tmp_path / "v08_pkgs")
    assert set(summary["task_ids"]) == set(V08_THIN_SHELL_AB_TASKS.keys())

    for task_id, receipt in summary["tasks"].items():
        assert receipt["geometry_and_trajectory_frozen"] is True
        hashes = receipt["shared_invariance_hashes"]
        arm_dirs = receipt["arm_dirs"]
        gt_m = yaml.safe_load((Path(arm_dirs["ground_truth_ref"]) / "manifest.yaml").read_text(encoding="utf-8"))
        base_m = yaml.safe_load((Path(arm_dirs["baseline_spring_mass"]) / "manifest.yaml").read_text(encoding="utf-8"))
        herm_m = yaml.safe_load((Path(arm_dirs["hermitetwin_shell"]) / "manifest.yaml").read_text(encoding="utf-8"))

        assert gt_m["shared_invariance_hashes"] == hashes
        assert base_m["shared_invariance_hashes"] == hashes
        assert herm_m["shared_invariance_hashes"] == hashes

        traj_base = json.loads((Path(arm_dirs["baseline_spring_mass"]) / "gripper_trajectory.json").read_text(encoding="utf-8"))
        traj_herm = json.loads((Path(arm_dirs["hermitetwin_shell"]) / "gripper_trajectory.json").read_text(encoding="utf-8"))
        assert traj_base == traj_herm, f"Trajectory mismatch in {task_id}"

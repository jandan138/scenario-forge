from __future__ import annotations

import json
from pathlib import Path

from scripts.finalize_scientific_workbench_task08_r13_1_robot import finalize


def test_blocked_robot_evidence_never_promotes_task_success(tmp_path: Path) -> None:
    root = tmp_path / "package"
    eos = tmp_path / "eos"
    (root / "adapters/ebench/genmanip").mkdir(parents=True)
    eos.mkdir()
    for name in ("probe_report.json", "cap_report.json", "grasp_report.json"):
        (eos / name).write_text(json.dumps({"status": "blocked"}))
    (eos / "final_report.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "blockers": ["cap_grasp_cold_start_consistency"],
                "claims": {
                    "robot_reachability_probe": True,
                    "core_robot_assisted_thread_success": False,
                    "task08_scripted_oracle_success": False,
                    "robot_policy_success": False,
                    "benchmark_success": False,
                },
                "claim_boundary": "blocked evidence only",
            }
        )
    )
    archive = finalize(root, eos)
    assert archive.is_file()
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["status"] == "robot_validation_blocked"
    assert manifest["claims"]["assisted_thread_non_robot_ready"] is True
    assert manifest["claims"]["task08_scripted_oracle_success"] is False

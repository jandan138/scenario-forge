from __future__ import annotations

import json
from pathlib import Path

from scripts.finalize_scientific_workbench_task08_vr_r13 import finalize


def test_finalize_promotes_only_assisted_interaction_claims(tmp_path: Path) -> None:
    root = tmp_path / "task08_r13"
    evidence = root / "vr/evidence/runtime"
    evidence.mkdir(parents=True)
    (root / "vr/scene.usd").write_text("usd")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "status": "pending",
                "claims": {
                    "thread_interaction_ready": False,
                    "task08_success": False,
                    "robot_policy_success": False,
                    "benchmark_success": False,
                },
            }
        )
    )
    for index in range(3):
        (evidence / f"run_{index:02d}.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "claims": {
                        "one_turn_assisted_thread": True,
                        "release_retention": True,
                    },
                    "terminal": {"rotation_deg": 350.0},
                    "closed_relative_z_m": 0.1074,
                }
            )
        )
    archive = finalize(root)
    assert archive.is_file()
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["claims"]["thread_interaction_ready"] is True
    assert manifest["claims"]["task08_success"] is False
    assert manifest["claims"]["robot_policy_success"] is False
    assert manifest["claims"]["benchmark_success"] is False

from pathlib import Path
import ast


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts/package_scientific_workbench_task11_vr_r4.py"
)


def test_r4_packager_requires_three_static_runs_and_preserves_claim_boundary():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    assert "cold_run_1.json" in source
    assert "cold_run_2.json" in source
    assert "cold_run_3.json" in source
    assert "retention_ratio" in source
    assert "below_floor_count" in source
    assert "robot_policy_success" in source
    assert "False" in source

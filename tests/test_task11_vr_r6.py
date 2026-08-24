from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_vr_r6.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_task11_vr_r6.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r6.py"


def test_r6_uses_rest_pose_package_and_exact_table_height():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "labspin_x8_task11_r5_rest_pose_20260824" in source
    assert "DEVICE_XYZ = (0.22, 0.09, 0.755)" in source
    assert "scientific_workbench_task11_vr_r6_20260824" in source
    assert "lid_link" not in source
    assert "localPos0" not in source


def test_r6_observer_checks_preview_support_and_no_first_step_jump():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "preview_assembled" in source
    assert "base_on_table" in source
    assert "first_step_pose_continuity" in source
    assert "particle_gate" in source
    assert "robot_policy_success" in source


def test_r6_packager_requires_three_runs_and_visual_evidence():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "run_1.json" in source and "run_3.json" in source
    assert "preview_assembled" in source
    assert "base_on_table" in source
    assert "scene_overview.png" in source
    assert "scientific_workbench_task11_vr_r6.zip" in source

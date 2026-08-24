from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
OBSERVER = ROOT / "scripts/observe_scientific_workbench_task11_vr_r5.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r5.py"


def test_r5_observer_tracks_full_object_set_and_particles():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "obj_bg_15ml_00" in source
    assert "obj_bg_50ml_01" in source
    assert "obj_primary_tube" in source
    assert "primary_liquid" in source
    assert "kinematicEnabled" not in source


def test_r5_packager_requires_three_full_scene_runs():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "run_1.json" in source and "run_3.json" in source
    assert "full_scene_static_stability" in source
    assert "background_context_static" in source
    assert "scientific_workbench_task11_vr_r5.zip" in source
    assert "robot_policy_success" in source

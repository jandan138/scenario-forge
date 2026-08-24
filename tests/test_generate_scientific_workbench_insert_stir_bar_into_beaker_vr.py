from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_insert_stir_bar_into_beaker_vr.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_insert_stir_bar_into_beaker_vr.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_insert_stir_bar_into_beaker_vr.py"


def test_generator_uses_task02_beaker_and_background_objects():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_insert_stir_bar_into_beaker" in source
    assert "scientific_workbench_task02_r10_3_fill_sweep_20260819" in source
    assert "scientific_workbench_magnetic_stir_bar_29_77_20260824" in source
    for name in (
        "obj_beaker",
        "obj_stir_bar",
        "obj_r9_amber_bottle",
        "obj_r9_tip_box",
        "obj_r9_wash_bottle",
        "obj_r9_clear_bottle",
        "obj_r9_pipette_carousel",
    ):
        assert name in source
    assert "canonical_task04_success" in source
    assert "set_robot_physics_material" not in source
    assert "set_robot_contact_offset" not in source
    assert "set_robot_rest_offset" not in source


def test_observer_supports_static_and_non_robot_drop_modes():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert 'choices=("static", "drop")' in source
    assert "/World/obj_beaker/__aan_frame_opening" in source
    assert "/World/obj_stir_bar" in source
    assert "robot_policy_success" in source


def test_packager_requires_three_runs_per_gate():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "static_run_1.json" in source
    assert "static_run_3.json" in source
    assert "drop_run_1.json" in source
    assert "drop_run_3.json" in source
    assert "canonical_task04_success" in source

from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_stir_bar_vr_r3.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_stir_bar_vr_r3.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_stir_bar_vr_r3.py"


def test_r3_generator_adds_stirrer_and_fill40_liquid():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_insert_stir_bar_into_beaker_vr_r2_20260824" in source
    assert "scientific_workbench_magnetic_stirrer_machine_20260821.zip" in source
    assert "obj_magnetic_stirrer" in source
    assert "Context" not in source
    assert "fill40" in source
    assert "816" in source
    assert "fluid_runtime" in source


def test_r3_observer_is_single_short_integration_gate():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "obj_magnetic_stirrer" in source
    assert "particle_count" in source
    assert "816" in source
    assert "robot_policy_success" in source


def test_r3_packager_keeps_claim_boundary():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_insert_stir_bar_into_beaker_vr_r3.zip" in source
    assert "gpu_pbd_loaded_start" in source
    assert "magnetic_stirring_simulated" in source
    assert "False" in source

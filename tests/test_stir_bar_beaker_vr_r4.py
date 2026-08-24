from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_stir_bar_vr_r4.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_stir_bar_vr_r4.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_stir_bar_vr_r4.py"


def test_r4_uses_admitted_sdf_beaker_and_dual_liquid_entrypoints():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_beaker_325ml_sdf_web_standard_v1" in source
    assert "scene_liquid_edit.usd" in source
    assert "PhysxParticleSamplingAPI" in source
    assert "height_z" in source
    assert "obj_magnetic_stirrer" in source


def test_r4_uses_one_physics_scene_and_transparent_blue_recipe():
    source = GENERATOR.read_text(encoding="utf-8")
    assert '"/World/physicsScene"' in source
    assert "GpuMaxParticleContacts" in source
    assert "0.32" in source and "0.72" in source and "0.95" in source
    assert "0.34" in source


def test_r4_observer_checks_frozen_and_editable_scenes():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scene_liquid_edit.usd" in source
    assert "ParticleSets" in source
    assert "duplicate_physics_scene" in source
    assert "robot_policy_success" in source


def test_r4_packager_keeps_claim_boundary():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_insert_stir_bar_into_beaker_vr_r4.zip" in source
    assert "editable_liquid_sampler" in source
    assert "robot_policy_success" in source
    assert "False" in source

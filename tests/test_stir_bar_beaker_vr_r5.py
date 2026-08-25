from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_stir_bar_vr_r5.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_stir_bar_vr_r5.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_stir_bar_vr_r5.py"
RENDERER = ROOT / "scripts/render_scientific_workbench_insert_stir_bar_into_beaker_vr.py"


def test_r5_consumes_hydra_compatible_producer_without_local_usd_patch():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_stir_bar_beaker_dual_liquid_hydra_compat_20260825" in source
    assert "scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825" in source
    assert "particle_display_primvars_authored" in source
    assert "ClearReferences" not in source
    assert "displayColor.Block" not in source


def test_r5_observer_renders_both_entries_and_blocks_hydra_primvar_errors():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scene_liquid_edit.usd" in source
    assert "rendered_steps" in source
    assert "Unrecognized primvar 'displayColor'" in source
    assert "Unrecognized primvar 'displayOpacity'" in source
    assert "HasAuthoredValueOpinion" in source
    assert "runtime_label" in source


def test_r5_packager_requires_41_and_45_render_compatibility():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "isaac41.json" in source
    assert "isaac45.json" in source
    assert "isaac45_render" in source
    assert "scientific_workbench_insert_stir_bar_into_beaker_vr_r5.zip" in source
    assert "robot_policy_success" in source


def test_stir_bar_renderer_supports_separate_runtime_evidence_directories():
    source = RENDERER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "--evidence-subdir" in source
    assert "--runtime-label" in source

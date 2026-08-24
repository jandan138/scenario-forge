from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_raw_dropin.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_task11_raw_dropin.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_raw_dropin.py"


def test_generator_preserves_and_directly_references_raw_articulated_usd():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "centrifuge_articulated.usda" in source
    assert "centrifuge.usd" in source
    assert "/LabSpinX8" in source
    assert "raw_source_unchanged" in source
    assert "convertasset_centrifuge_consumed" in source
    assert "False" in source
    assert "materialize_vr_object_subtrees" not in source
    assert "physics:jointEnabled" not in source


def test_observer_requires_expected_raw_physics_failure():
    source = OBSERVER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "expected_failure_observed" in source
    assert "Articulations with kinematic bodies are not supported" in source
    assert "cannot create a joint between static bodies" in source
    assert "robot_policy_success" in source


def test_packager_labels_negative_control_and_raw_hashes():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "negative_control" in source
    assert "expected_failure_observed" in source
    assert "scientific_workbench_task11_raw_articulated_dropin.zip" in source

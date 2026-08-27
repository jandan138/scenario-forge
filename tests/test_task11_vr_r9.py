from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_vr_r9.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r9.py"
FINALIZER = ROOT / "scripts/finalize_scientific_workbench_task11_vr_r9.py"


def test_r9_replaces_all_15ml_with_single_rigid_closed_assembly() -> None:
    source = GENERATOR.read_text()
    ast.parse(source)
    assert "threaded_tube15_red_closed_assembly_20260827" in source
    assert 'required_tube_claim="single_rigid_body_closed_assembly"' in source
    assert 'tube_entry_prim="/ThreadedTube15RedClosed"' in source
    assert 'tube_asset_filename="asset.usda"' in source
    assert "replace_all_15ml=True" in source
    assert 'release_id="r9"' in source


def test_r9_preserves_visual_liquid_and_false_success_claims() -> None:
    generator = GENERATOR.read_text()
    shared_generator = (
        ROOT / "scripts/generate_scientific_workbench_task11_vr_r8.py"
    ).read_text()
    packager = PACKAGER.read_text()
    finalizer = FINALIZER.read_text()
    for source in (packager, finalizer):
        ast.parse(source)
    assert "generate_scientific_workbench_task11_vr_r8" in generator
    assert "visual_static_liquid" in shared_generator
    assert "scientific_workbench_task11_vr_r9_candidate.zip" in packager
    assert "r9_static" in finalizer and "r9_mechanical" in finalizer
    for claim in ("task11_success", "robot_policy_success", "benchmark_success"):
        assert claim in packager

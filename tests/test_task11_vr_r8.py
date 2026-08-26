from __future__ import annotations

import ast
from pathlib import Path
import runpy


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_vr_r8.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r8.py"
OBSERVER = ROOT / "scripts/observe_scientific_workbench_task11_vr_r8.py"
MECHANICS = ROOT / "scripts/validate_scientific_workbench_task11_r8_device_mechanics.py"
FINALIZER = ROOT / "scripts/finalize_scientific_workbench_task11_vr_r8.py"
RENDERER = ROOT / "scripts/render_scientific_workbench_task11_vr_r8.py"
ADAPTER = ROOT / "scripts/build_task11_r8_genmanip_validation_bundle.py"
ADAPTER_SMOKE = ROOT / "scripts/validate_task11_r8_genmanip_bundle.py"


def _module() -> dict[str, object]:
    return runpy.run_path(str(GENERATOR))


def test_r8_consumes_visual_fitted_device_and_restores_five_context_props() -> None:
    source = GENERATOR.read_text()
    ast.parse(source)
    assert "labspin_x8_task11_r6_visual_fitted_lid_collision_20260826" in source
    assert "task11_r5_context_assets_20260824/target_tube_r2" in source
    assert "target_slot_insertion" in source
    for name in (
        "obj_r9_amber_bottle",
        "obj_r9_tip_box",
        "obj_r9_wash_bottle",
        "obj_r9_clear_bottle",
        "obj_r9_pipette_carousel",
    ):
        assert name in source
    assert '"visual_fitted_lid_collision"' in source
    assert "UsdPhysics.Material" not in source
    assert "staticFriction" not in source
    assert "dynamicFriction" not in source


def test_r8_authors_visual_only_liquid_without_particle_contract() -> None:
    source = GENERATOR.read_text()
    assert 'scenarioForge:role", Sdf.ValueTypeNames.Token' in source
    assert '"visual_static_liquid"' in source
    assert '"particle_system_count": 0' in source
    assert '"liquid_interactive": False' in source
    assert "ParticleSystem" not in source
    assert "PhysxParticle" not in source
    assert "GpuMaxParticleContacts" not in source
    assert "dynamic_sdf_rigid_container_collision_not_particles" in source


def test_r8_context_layout_is_the_task02_standard_and_root_randomized() -> None:
    module = _module()
    layout = module["CONTEXT_LAYOUT"]
    assert layout == {
        "obj_r9_amber_bottle": (-0.78, 0.18, 0.755),
        "obj_r9_tip_box": (-0.58, 0.22, 0.755),
        "obj_r9_wash_bottle": (0.78, 0.18, 0.755),
        "obj_r9_clear_bottle": (0.58, 0.22, 0.755),
        "obj_r9_pipette_carousel": (0.82, -0.04, 0.755),
    }
    assert "x_offset_range" in GENERATOR.read_text()
    assert "[-0.01, 0.01]" in GENERATOR.read_text()


def test_r8_packager_names_candidate_and_keeps_success_claims_false() -> None:
    source = PACKAGER.read_text()
    ast.parse(source)
    assert "scientific_workbench_task11_vr_r8_candidate.zip" in source
    assert ".zip.sha256" in source
    assert "scene_qualified_robot_unvalidated" in source
    for claim in ("task11_success", "robot_policy_success", "benchmark_success"):
        assert claim in source


def test_r8_runtime_checks_particle_free_static_scene_and_contact_device() -> None:
    observer = OBSERVER.read_text()
    mechanics = MECHANICS.read_text()
    ast.parse(observer)
    ast.parse(mechanics)
    assert "particle_free_scene" in observer
    assert "visual_liquid_forbidden_physics" in observer
    assert "obj_r9_pipette_carousel" in observer
    assert "kinematic_contact_pushers_no_direct_button_or_lid_joint_write" in mechanics
    assert "visual_fitted_lid_collision_composed" in mechanics
    assert "robot_free_device_mechanics" in mechanics
    assert "set_joint_positions" not in mechanics


def test_r8_finalization_requires_three_runs_render_and_visual_review() -> None:
    finalizer = FINALIZER.read_text()
    renderer = RENDERER.read_text()
    ast.parse(finalizer)
    ast.parse(renderer)
    assert "run_00.json" in finalizer and "run_02.json" in finalizer
    assert "scene_usd_sha256" in finalizer
    assert "robot_free_device_mechanics" in finalizer
    assert '"mechanical_oracle_success"] = False' in finalizer
    assert "visual_review.json" in finalizer
    assert "tabletop_wide" in renderer
    assert "after_run_" in renderer


def test_r8_genmanip_adapter_wraps_exact_scene_without_physics_patch() -> None:
    source = ADAPTER.read_text()
    ast.parse(source)
    assert "legacy.build(r8, base, out)" in source
    assert "task11_r8/scene.usda" in source
    assert "task11_r8_source" in source
    assert "ClearReferences" in source
    assert '"particle_system_count": 0' in source
    assert '"robot_policy_success": False' in source
    assert "staticFriction" not in source
    assert "dynamicFriction" not in source
    smoke = ADAPTER_SMOKE.read_text()
    ast.parse(smoke)
    assert "wrapper_has_no_absolute_cpfs_reference" in smoke
    assert "adapter_load_smoke" in smoke
    assert "particle_free" in smoke

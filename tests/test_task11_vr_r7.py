from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_vr_r7.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r7.py"


def test_r7_consumes_producer_grasp_qualified_tube_without_local_physics_patch():
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "task11_r7_target_tube_grasp_20260824" in source
    assert "target_tube=args.tube" in source
    assert "fixed_candidate_close_lift_hold" in source
    assert "DEVICE_XYZ = (0.0, -0.1, 0.755)" in source
    assert "RACK_XYZ = (-0.4, -0.3, 0.755)" in source
    assert "rack_xyz=RACK_XYZ" in source
    assert "UsdPhysics.Material" not in source
    assert "staticFriction" not in source
    assert "dynamicFriction" not in source


def test_r7_packager_requires_mechanical_and_robot_oracle_reports():
    source = PACKAGER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "mechanical_oracle_success" in source
    assert "canonical_task11_scripted_oracle_success" in source
    assert "post_initialization_object_transform_write_count" in source
    assert "direct_device_joint_target_write_count" in source
    assert "scientific_workbench_task11_vr_r7.zip" in source

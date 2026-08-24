from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/validate_scientific_workbench_task11_mechanical_oracle.py"


def test_task11_mechanical_oracle_is_contact_and_constraint_driven():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    assert "kinematic_rigid_contact_pushers" in source
    assert "kinematic_parallel_jaws" in source
    assert "slot_15ml_r00_c02_inserted_bottom" in source
    assert "post_initialization_object_transform_write_count" in source
    assert "direct_device_joint_target_write_count" in source
    assert "task11_success" in source
    assert "mechanical_oracle_success" in source
    assert "tube.set_world_pose" not in source

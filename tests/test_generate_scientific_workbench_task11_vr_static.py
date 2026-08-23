from pathlib import Path
import ast

SCRIPT = Path(__file__).parents[1] / "scripts/generate_scientific_workbench_task11_vr_static.py"


def test_task11_static_generator_is_vr_only_and_claim_bounded():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_centrifuge_unload_shutdown" in source
    assert "PRIMARY_SOCKET = 18" in source and "BALANCE_SOCKET = 6" in source
    assert source.count("2640") >= 2
    assert "object_materialization.json" in source
    assert "button_causes_lid_open" in source
    assert "robot_policy_success" in source
    assert "set_robot_contact_offset" not in source

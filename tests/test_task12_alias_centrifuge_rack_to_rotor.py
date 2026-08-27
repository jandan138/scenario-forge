from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_task12_alias_centrifuge_rack_to_rotor.py"
ADAPTER = ROOT / "scripts/build_task12_alias_genmanip_bundle.py"
ORACLE = ROOT / "scripts/validate_task12_alias_robot_free_oracle.py"
FINALIZER = ROOT / "scripts/finalize_task12_alias_centrifuge_rack_to_rotor.py"
PACKAGER = ROOT / "scripts/package_task12_alias_centrifuge_rack_to_rotor.py"


def test_alias_generator_moves_liquid_tube_from_rack_to_empty_rotor_target() -> None:
    source = GENERATOR.read_text()
    ast.parse(source)
    assert "scientific_workbench_task12_alias_centrifuge_rack_to_rotor" in source
    assert 'TARGET_RACK_SLOT = "slot_15ml_r00_c02"' in source
    assert "TARGET_ROTOR_SOCKET = 18" in source
    assert "BALANCE_ROTOR_SOCKET = 6" in source
    assert "obj_bg_50ml_00" in source and "RemovePrim" in source
    assert '"instances": ["/World/obj_primary_tube/VisualLiquid"]' in source
    assert "manual_close_and_latch" in source


def test_alias_adapter_replaces_stale_task02_contract_and_has_nonempty_goal() -> None:
    source = ADAPTER.read_text()
    ast.parse(source)
    assert "scenario-forge-genmanip-runtime-contract/v0.6" in source
    assert "alias.INSTRUCTION" in source
    assert '"goal"' in source
    assert "TARGET_ROTOR_SOCKET" in source
    assert "progress_rubric" in source
    assert "obj_bg_50ml" not in source


def test_alias_oracle_is_contact_and_carrier_driven() -> None:
    source = ORACLE.read_text()
    ast.parse(source)
    assert "FixedJoint" in source
    assert "open_pusher" in source and "stop_pusher" in source
    assert "set_joint_positions" not in source
    assert "robot_free_transfer_oracle_success" in source
    assert '"robot_policy_success": False' in source


def test_alias_finalizer_and_packager_keep_claims_bounded() -> None:
    finalizer = FINALIZER.read_text()
    packager = PACKAGER.read_text()
    for source in (finalizer, packager):
        ast.parse(source)
    assert "task12_alias_static" in finalizer
    assert "task12_alias_oracle" in finalizer
    assert "scientific_workbench_task12_alias_centrifuge_rack_to_rotor_candidate.zip" in packager
    for claim in ("task_success", "robot_policy_success", "benchmark_success"):
        assert claim in packager

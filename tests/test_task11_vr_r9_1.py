from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_task11_vr_r9_1.py"
ADAPTER = ROOT / "scripts/build_task11_r9_1_genmanip_bundle.py"
PACKAGER = ROOT / "scripts/package_scientific_workbench_task11_vr_r9_1.py"


def test_r9_1_selects_camera_horizontal_opposed_socket_pair() -> None:
    source = GENERATOR.read_text()
    ast.parse(source)
    assert "PRIMARY_SOCKET = 3" in source
    assert "BALANCE_SOCKET = 15" in source
    assert 'release_id="r9_1"' in source
    assert "left_right_camera_pair" in source


def test_r9_1_adapter_and_archive_are_versioned_without_success_promotion() -> None:
    adapter = ADAPTER.read_text()
    packager = PACKAGER.read_text()
    for source in (adapter, packager):
        ast.parse(source)
    assert "task11_r9_1" in adapter
    assert "scientific_workbench_task11_vr_r9_1_left_right_candidate.zip" in packager
    for claim in ("robot_policy_success", "task11_success", "benchmark_success"):
        assert claim in packager

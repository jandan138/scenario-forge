from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml",
    *sorted((ROOT / "examples/scientific_workbench/layout_validated").glob("*/scenario.yaml")),
    *sorted((ROOT / "examples/scientific_workbench/asset_expansion").glob("*/scenario.yaml")),
)


def test_scientific_workbench_examples_share_the_admitted_standard_table() -> None:
    assert SCENARIOS
    for path in SCENARIOS:
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        table = next(item for item in scenario["objects"] if item["role"] == "table")
        assert table["asset_id"] == "scientific_workbench_ebench_table_static_support"
        assert table["source_prim_path"] == "/World/table"
        assert table["pose"] == {
            "xyz": [0.0, 0.0, 0.0],
            "wxyz": [1.0, 0.0, 0.0, 0.0],
        }, path


def test_robot_uses_the_long_edge_center_approach_frame() -> None:
    for path in SCENARIOS:
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert scenario["robot"]["spawn"] == {
            "xyz": [0.0, -1.02, 0.31],
            "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }, path


def test_standard_table_binding_points_to_exact_convertasset_package() -> None:
    path = ROOT / "configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml"
    bindings = yaml.safe_load(path.read_text(encoding="utf-8"))["bindings"]
    table = bindings["scientific_workbench_ebench_table_static_support"]

    assert table["source_usd"].endswith(
        "/outputs/scientific_workbench_standard_table_20260819/source.usda"
    )
    assert table["package_dir"].endswith(
        "/outputs/scientific_workbench_standard_table_20260819/package"
    )
    assert table["expected_scope_prims"] == ["/World/table"]

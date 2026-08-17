from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.tabletop_placement import (
    TabletopPlacementValidationError,
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.generation.layout.tabletop_placement import (
    TabletopBounds,
    TabletopPlacementPolicy,
    evaluate_tabletop_placement,
)
from scenario_forge.generation.layout.constraints import load_layout_constraints


def _policy() -> TabletopPlacementPolicy:
    return TabletopPlacementPolicy(
        policy_id="scientific_workbench.robot_facing_tabletop.v1",
        min_edge_clearance_m=0.10,
    )


def test_robot_facing_half_and_ten_centimetre_edge_clearance_pass() -> None:
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -0.8, 0.8),
        robot_xy=(-1.5, 0.0),
        object_bounds={
            "beaker": TabletopBounds(-0.60, -0.40, -0.10, 0.10),
        },
        policy=_policy(),
    )

    assert report.overall_status == "pass"
    assert report.objects[0].robot_facing_half is True
    assert report.objects[0].minimum_edge_clearance_m == 0.40


def test_far_side_requires_a_written_exception() -> None:
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -0.8, 0.8),
        robot_xy=(-1.5, 0.0),
        object_bounds={
            "flask": TabletopBounds(0.30, 0.50, -0.10, 0.10),
        },
        policy=_policy(),
    )

    assert report.overall_status == "blocked"
    assert report.objects[0].robot_side_status == "blocked"

    waived = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -0.8, 0.8),
        robot_xy=(-1.5, 0.0),
        object_bounds={
            "flask": TabletopBounds(0.30, 0.50, -0.10, 0.10),
        },
        policy=_policy(),
        robot_side_exceptions={"flask": "Task interaction requires the far-side station."},
    )

    assert waived.overall_status == "pass"
    assert waived.objects[0].robot_side_status == "exception"


def test_robot_side_exception_never_waives_the_edge_safety_margin() -> None:
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -0.8, 0.8),
        robot_xy=(-1.5, 0.0),
        object_bounds={
            "tube": TabletopBounds(-0.95, -0.75, -0.10, 0.10),
        },
        policy=_policy(),
        robot_side_exceptions={"tube": "Illustrative exception that must not waive safety."},
    )

    assert report.overall_status == "blocked"
    assert report.objects[0].edge_clearance_status == "blocked"


def test_fixed_instrument_can_use_a_stricter_declared_per_object_margin() -> None:
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -0.4, 0.4),
        robot_xy=(0.0, -1.5),
        object_bounds={
            "oven": TabletopBounds(-0.4375, 0.4375, -0.3465, 0.3465),
        },
        policy=_policy(),
        min_edge_clearance_overrides_m={"oven": 0.04},
    )

    assert report.overall_status == "pass"
    assert report.objects[0].required_edge_clearance_m == 0.04
    assert report.objects[0].minimum_edge_clearance_m == 0.0535


def test_unknown_per_object_margin_override_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown objects"):
        evaluate_tabletop_placement(
            table_bounds=TabletopBounds(-1.0, 1.0, -0.4, 0.4),
            robot_xy=(0.0, -1.5),
            object_bounds={"oven": TabletopBounds(-0.4, 0.4, -0.3, 0.3)},
            policy=_policy(),
            min_edge_clearance_overrides_m={"not_oven": 0.04},
        )


def test_robot_facing_half_follows_the_robot_direction_not_a_fixed_x_axis() -> None:
    report = evaluate_tabletop_placement(
        table_bounds=TabletopBounds(-1.0, 1.0, -1.0, 1.0),
        robot_xy=(0.0, 2.0),
        object_bounds={
            "cylinder": TabletopBounds(-0.10, 0.10, 0.40, 0.60),
        },
        policy=_policy(),
    )

    assert report.overall_status == "pass"
    assert report.objects[0].robot_facing_half is True


def test_scientific_workbench_domain_pack_declares_the_robot_side_policy() -> None:
    constraints = load_layout_constraints()

    assert constraints.tabletop_placement is not None
    assert constraints.tabletop_placement.policy.policy_id == (
        "scientific_workbench.robot_facing_tabletop.v1"
    )
    assert constraints.tabletop_placement.policy.min_edge_clearance_m == 0.10
    assert constraints.tabletop_placement.support_surface_prim_path == ("/World/table/Surface")


def test_adapter_writes_world_bound_policy_evidence_and_blocks_far_side(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pxr.Usd", reason="world bounds require OpenUSD")
    _write_tabletop_fixture(tmp_path, object_x=0.45)

    with pytest.raises(TabletopPlacementValidationError, match="robot-facing") as error:
        validate_scientific_workbench_tabletop_placement(tmp_path)

    evidence = yaml.safe_load(error.value.evidence_path.read_text(encoding="utf-8"))
    assert evidence["overall_status"] == "blocked"
    assert evidence["objects"][0]["edge_clearance_status"] == "pass"
    assert evidence["objects"][0]["robot_side_status"] == "blocked"


def test_adapter_allows_written_far_side_exception_but_not_edge_exception(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pxr.Usd", reason="world bounds require OpenUSD")
    _write_tabletop_fixture(
        tmp_path,
        object_x=0.45,
        exception="This task needs the far-side fixed station.",
    )

    result = validate_scientific_workbench_tabletop_placement(tmp_path)

    evidence = yaml.safe_load(result.evidence_path.read_text(encoding="utf-8"))
    assert result.overall_status == "pass"
    assert evidence["objects"][0]["robot_side_status"] == "exception"
    assert evidence["objects"][0]["robot_side_exception_reason"] == (
        "This task needs the far-side fixed station."
    )


def test_adapter_uses_declared_fixed_instrument_support_footprint(tmp_path: Path) -> None:
    pytest.importorskip("pxr.Usd", reason="world bounds require OpenUSD")
    _write_tabletop_fixture(
        tmp_path,
        object_x=0.0,
        robot_xyz=(0.0, -1.5, 0.31),
        table_scale_xy=(2.0, 0.8),
        object_scale_xy=(0.875, 0.77),
        placement_metadata={
            "tabletop_placement_class": "fixed_benchtop_instrument",
            "tabletop_support_footprint": {
                "size_xy_m": [0.875, 0.693],
                "center_offset_xy_m": [0.0, 0.0],
                "source": "producer device-profile geometry audit",
            },
            "tabletop_min_edge_clearance_m": 0.04,
        },
    )

    result = validate_scientific_workbench_tabletop_placement(tmp_path)

    evidence = yaml.safe_load(result.evidence_path.read_text(encoding="utf-8"))
    oven = evidence["objects"][0]
    assert result.overall_status == "pass"
    assert oven["required_edge_clearance_m"] == 0.04
    assert oven["minimum_edge_clearance_m"] == 0.0535
    assert oven["footprint_source"] == "declared_support_footprint"
    assert oven["visual_world_bounds_xy_m"]["min"] == [-0.4375, -0.385]


def _write_tabletop_fixture(
    root: Path,
    *,
    object_x: float,
    exception: str | None = None,
    robot_xyz: tuple[float, float, float] = (-1.5, 0.0, 0.31),
    object_scale_xy: tuple[float, float] = (0.2, 0.2),
    table_scale_xy: tuple[float, float] = (2.0, 1.6),
    placement_metadata: dict[str, object] | None = None,
) -> None:
    metadata = dict(placement_metadata or {})
    if exception is not None:
        metadata["tabletop_placement_exception"] = exception
    (root / "scene").mkdir(parents=True)
    (root / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "domain": "scientific_workbench",
                "robot": {"spawn": {"xyz": list(robot_xyz)}},
                "objects": [
                    {
                        "id": "table",
                        "role": "table",
                        "source_prim_path": "/World/table",
                    },
                    {
                        "id": "beaker",
                        "role": "target_container",
                        "source_prim_path": "/World/beaker",
                        "metadata": metadata,
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "scene/main.usda").write_text(
        f"""#usda 1.0

def Xform "World"
{{
    def Xform "table"
    {{
        def Xform "Surface"
        {{
            def Cube "mesh"
            {{
                double size = 1
                double3 xformOp:scale = ({table_scale_xy[0]}, {table_scale_xy[1]}, 0.1)
                uniform token[] xformOpOrder = ["xformOp:scale"]
            }}
        }}
    }}

    def Cube "beaker"
    {{
        double size = 1
        double3 xformOp:translate = ({object_x}, 0, 0.1)
        double3 xformOp:scale = ({object_scale_xy[0]}, {object_scale_xy[1]}, 0.1)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }}
}}
""",
        encoding="utf-8",
    )

from __future__ import annotations

from pathlib import Path
import yaml
import pytest

from scenario_forge.cli import main as cli_main
from scenario_forge.generation.layout.constraints import load_layout_constraints
from scenario_forge.generation.layout.relational_solver import (
    RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
    solve_relational_tabletop_layout,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "domain",
    [
        "specialty_coffee_bar",
        "electronics_qa_station",
        "modern_office_print_hub",
    ],
)
def test_new_out_of_domain_layout_packs_load_v02_policy(domain: str) -> None:
    pack_dir = REPO_ROOT / "configs" / "domain_packs" / domain
    constraints = load_layout_constraints(pack_dir)
    assert constraints.tabletop_placement is not None
    assert constraints.tabletop_placement.policy.min_edge_clearance_m == pytest.approx(0.10)
    assert set(constraints.difficulty_profiles) == {"easy", "medium", "hard"}


def _boxes_overlap_xy(
    a_min: tuple[float, float],
    a_max: tuple[float, float],
    b_min: tuple[float, float],
    b_max: tuple[float, float],
    margin: float = 0.0,
) -> bool:
    return (
        a_min[0] - margin < b_max[0]
        and a_max[0] + margin > b_min[0]
        and a_min[1] - margin < b_max[1]
        and a_max[1] + margin > b_min[1]
    )


def test_solve_printer_layout_preserves_drawer_corridor_and_edge_margins() -> None:
    spec = {
        "schema_version": RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
        "seed": 42,
        "table": {
            "x_range_m": [-1.0, 1.0],
            "y_range_m": [-0.40, 0.40],
            "surface_z_m": 0.755,
            "min_edge_clearance_m": 0.10,
        },
        "robot_xy": [0.0, -1.02],
        "min_object_clearance_m": 0.035,
        "objects": [
            {
                "id": "printer",
                "role": "articulated_appliance",
                "footprint_xy_m": [0.41, 0.39],
                "region": "center",
                "facing": "robot",
                "yaw_offset_deg": 0.0,
                "robot_side_exception": (
                    "Large 390mm-deep printer spans table centerline so its 180mm front "
                    "paper_cassette pullout corridor stays inside the robot-facing half."
                ),
                "kinematic_clearance_volumes": [
                    {
                        "id": "paper_cassette_pullout",
                        "joint": "paper_cassette",
                        "local_xy_bounds_m": {
                            "x": [-0.16, 0.16],
                            "y": [-0.385, -0.195],
                        },
                    }
                ],
            },
            {
                "id": "a5_media_pack",
                "role": "task_object",
                "footprint_xy_m": [0.15, 0.21],
                "region": "left",
                "facing": "robot",
            },
            {
                "id": "calibration_sheet",
                "role": "task_object",
                "footprint_xy_m": [0.16, 0.22],
                "region": "right",
                "facing": "robot",
            },
            {
                "id": "pen_cup_prop",
                "role": "context_prop",
                "footprint_xy_m": [0.09, 0.09],
                "region": "far_context",
                "facing": "robot",
            },
        ],
        "relations": [
            {"subject": "a5_media_pack", "predicate": "left_of", "reference": "printer", "min_gap_m": 0.06},
            {"subject": "calibration_sheet", "predicate": "right_of", "reference": "printer", "min_gap_m": 0.06},
            {"subject": "a5_media_pack", "predicate": "near", "reference": "printer", "max_center_distance_m": 0.55},
            {"subject": "calibration_sheet", "predicate": "near", "reference": "printer", "max_center_distance_m": 0.55},
        ],
    }

    result_a = solve_relational_tabletop_layout(spec)
    result_b = solve_relational_tabletop_layout(spec)

    assert result_a.status == "solved"
    assert result_a.conflicts == ()
    # Deterministic given identical seed
    assert result_a.to_mapping() == result_b.to_mapping()

    placements = {item.object_id: item for item in result_a.placements}
    assert placements["a5_media_pack"].pose.xyz[0] < placements["printer"].pose.xyz[0]
    assert placements["calibration_sheet"].pose.xyz[0] > placements["printer"].pose.xyz[0]
    assert placements["pen_cup_prop"].robot_side_exception is not None

    # Every object respects 0.10m edge clearance
    for item in result_a.placements:
        x_min, y_min = item.world_xy_min_m
        x_max, y_max = item.world_xy_max_m
        assert x_min >= -1.0 + 0.10 - 1e-6
        assert x_max <= 1.0 - 0.10 + 1e-6
        assert y_min >= -0.40 + 0.10 - 1e-6
        assert y_max <= 0.40 - 0.10 + 1e-6

    # No non-printer object intrudes into the printer's front drawer pullout corridor
    corridor = placements["printer"].world_clearance_volumes[0]
    for obj_id, item in placements.items():
        if obj_id == "printer":
            continue
        assert not _boxes_overlap_xy(
            corridor.world_xy_min_m,
            corridor.world_xy_max_m,
            item.world_xy_min_m,
            item.world_xy_max_m,
        )


def test_solver_reports_structured_kinematic_clearance_conflict_when_blocked() -> None:
    spec = {
        "schema_version": RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
        "seed": 7,
        "table": {
            "x_range_m": [-1.0, 1.0],
            "y_range_m": [-0.40, 0.40],
            "surface_z_m": 0.755,
            "min_edge_clearance_m": 0.10,
        },
        "robot_xy": [0.0, -1.02],
        "objects": [
            {
                "id": "printer",
                "role": "articulated_appliance",
                "footprint_xy_m": [0.41, 0.39],
                "fixed_xy_m": [0.0, 0.08],
                "facing": "robot",
                "robot_side_exception": "Centered fixture spans centerline.",
                "kinematic_clearance_volumes": [
                    {
                        "id": "paper_cassette_pullout",
                        "joint": "paper_cassette",
                        "local_xy_bounds_m": {
                            "x": [-0.18, 0.18],
                            "y": [-0.395, -0.195],
                        },
                    }
                ],
            },
            {
                "id": "blocking_mug",
                "role": "context_prop",
                "footprint_xy_m": [0.09, 0.09],
                "fixed_xy_m": [0.0, -0.20],
                "facing": "robot",
            },
        ],
        "relations": [],
    }

    result = solve_relational_tabletop_layout(spec)
    assert result.status == "infeasible"
    assert any(
        conflict.conflict_type == "kinematic_clearance_intrusion"
        and "printer" in conflict.objects
        and "blocking_mug" in conflict.objects
        and conflict.joint == "paper_cassette"
        for conflict in result.conflicts
    )


def test_solver_handles_rotated_yaw_and_stacked_carrier_objects() -> None:
    spec = {
        "schema_version": RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
        "seed": 19,
        "table": {
            "x_range_m": [-1.0, 1.0],
            "y_range_m": [-0.40, 0.40],
            "surface_z_m": 0.755,
            "min_edge_clearance_m": 0.10,
        },
        "robot_xy": [0.0, -1.02],
        "objects": [
            {
                "id": "ingun_fixture",
                "role": "articulated_appliance",
                "footprint_xy_m": [0.30, 0.34],
                "region": "center",
                "facing": "robot",
                "yaw_offset_deg": -10.0,
                "kinematic_clearance_volumes": [
                    {
                        "id": "clamp_lever_swing",
                        "joint": "clamp_lever",
                        "local_xy_bounds_m": {
                            "x": [0.15, 0.24],
                            "y": [-0.20, 0.08],
                        },
                    }
                ],
            },
            {
                "id": "esd_tray",
                "role": "task_object",
                "footprint_xy_m": [0.18, 0.14],
                "support_top_offset_z_m": 0.012,
                "region": "left",
                "facing": "robot",
            },
            {
                "id": "pcba_carrier_board",
                "role": "task_object",
                "footprint_xy_m": [0.10, 0.08],
                "stacked_on": "esd_tray",
                "facing": "robot",
            },
        ],
        "relations": [
            {"subject": "esd_tray", "predicate": "left_of", "reference": "ingun_fixture", "min_gap_m": 0.05},
        ],
    }

    result = solve_relational_tabletop_layout(spec)
    assert result.status == "solved"
    placements = {item.object_id: item for item in result.placements}
    tray = placements["esd_tray"]
    board = placements["pcba_carrier_board"]
    assert board.pose.xyz[0] == pytest.approx(tray.pose.xyz[0])
    assert board.pose.xyz[1] == pytest.approx(tray.pose.xyz[1])
    assert board.pose.xyz[2] == pytest.approx(0.755 + 0.012)


def test_cli_layout_solve_relational_roundtrip(tmp_path: Path) -> None:
    spec_path = tmp_path / "layout_request.yaml"
    out_path = tmp_path / "layout_solution.yaml"
    spec_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": RELATIONAL_LAYOUT_SPEC_SCHEMA_VERSION,
                "seed": 3,
                "robot_xy": [0.0, -1.02],
                "objects": [
                    {
                        "id": "espresso_machine",
                        "role": "articulated_appliance",
                        "footprint_xy_m": [0.245, 0.36],
                        "region": "center",
                        "facing": "robot",
                        "robot_side_exception": "360mm body straddles table centerline slightly.",
                        "kinematic_clearance_volumes": [
                            {
                                "id": "drip_tray_corridor",
                                "joint": "drip_tray",
                                "local_xy_bounds_m": {"x": [-0.09, 0.09], "y": [-0.24, -0.18]},
                            }
                        ],
                    },
                    {
                        "id": "espresso_cup",
                        "role": "task_object",
                        "footprint_xy_m": [0.07, 0.07],
                        "region": "left",
                        "facing": "robot",
                    },
                    {
                        "id": "coffee_capsule",
                        "role": "task_object",
                        "footprint_xy_m": [0.04, 0.04],
                        "region": "right",
                        "facing": "robot",
                    },
                ],
                "relations": [
                    {"subject": "espresso_cup", "predicate": "left_of", "reference": "espresso_machine"},
                    {"subject": "coffee_capsule", "predicate": "right_of", "reference": "espresso_machine"},
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = cli_main(
        [
            "layout",
            "solve-relational",
            "--spec",
            str(spec_path),
            "--domain-pack",
            str(REPO_ROOT / "configs" / "domain_packs" / "specialty_coffee_bar"),
            "--out",
            str(out_path),
            "--strict",
        ]
    )
    assert rc == 0
    saved = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert saved["status"] == "solved"
    assert len(saved["placements"]) == 3

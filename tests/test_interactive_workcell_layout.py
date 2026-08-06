from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.interactive_workcell_layout import (
    InteractiveWorkcellLayoutError,
    validate_interactive_workcell_layout,
)


SOURCE_TABLE = {
    "min": [-0.9239185074460179, -1.3322193410256615, -0.3997177639585258],
    "max": [1.4210249282229273, 1.312490858408316, 0.7727606155217077],
}
STANDARD_TABLE = {
    "min": [-0.34056522074316414, -0.9325535202026369, -0.399717712402344],
    "max": [0.8319064970913086, 0.9187435913085941, 0.7727605590820317],
}


def _manifest(variant: str) -> dict[str, object]:
    source = variant == "source_workbench"
    delta = -1.0199846981 if source else -0.436631421014276
    table = SOURCE_TABLE if source else STANDARD_TABLE
    return {
        "layout": {
            "variant_id": variant,
            "robot_workspace": {
                "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
                "spawn_xyz_m": [-1.603353277085724 if source else -1.02, 0.0, 0.31],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "base_footprint_radius_m": 0.35,
                "minimum_table_clearance_m": 0.05,
            },
            "tabletop_placement": {
                "hard_edge_clearance_m": 0.1,
                "robot_facing_edge": "x_min",
            },
            "task_group_translation_xyz_m": [delta, 0.0, 0.0],
        },
        "entrypoints": {
            "genmanip": {
                "embedded_object_states": {
                    "support_table": {"world_aabb_m": table},
                    "source_container": {
                        "world_aabb_m": {
                            "min": [0.2564758473 + delta, 0.0364758581, 0.7799941122],
                            "max": [0.3671289439 + delta, 0.1471289547, 0.8703945490],
                        }
                    },
                    "target_container": {
                        "world_aabb_m": {
                            "min": [0.2010661907 + delta, -0.2989337942, 0.7799941122],
                            "max": [0.3559805131 + delta, -0.1440194718, 0.9065547133],
                        }
                    },
                }
            }
        },
    }


def _scenario(spawn_x: float) -> dict[str, object]:
    return {
        "robot": {
            "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
            "spawn": {"xyz": [spawn_x, 0.0, 0.31], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        }
    }


@pytest.mark.parametrize(
    ("variant", "spawn_x"),
    [
        ("source_workbench", -1.603353277085724),
        ("ebench_workbench", -1.02),
    ],
)
def test_qualified_workbench_variants_pass_clearance_and_tabletop_policy(
    tmp_path: Path, variant: str, spawn_x: float
) -> None:
    result = validate_interactive_workcell_layout(
        package_root=tmp_path,
        scenario=_scenario(spawn_x),
        handoff_manifest=_manifest(variant),
    )

    clearance = yaml.safe_load(result.robot_table_evidence.read_text())
    tabletop = yaml.safe_load(result.tabletop_evidence.read_text())
    assert result.overall_status == "pass"
    assert clearance["overall_status"] == "pass"
    assert clearance["measured_clearance_m"] == pytest.approx(0.3294347697)
    assert tabletop["overall_status"] == "pass"
    assert {item["object_id"] for item in tabletop["objects"]} == {
        "source_container",
        "target_container",
    }


def test_old_origin_spawn_is_rejected_as_embedded_in_source_table(
    tmp_path: Path,
) -> None:
    with pytest.raises(InteractiveWorkcellLayoutError) as error:
        validate_interactive_workcell_layout(
            package_root=tmp_path,
            scenario=_scenario(0.0),
            handoff_manifest=_manifest("source_workbench"),
        )

    evidence = yaml.safe_load(error.value.robot_table_evidence.read_text())
    assert evidence["overall_status"] == "blocked"
    assert evidence["robot_center_inside_table_xy"] is True
    assert evidence["measured_clearance_m"] == -0.35


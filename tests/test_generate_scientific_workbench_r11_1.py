from __future__ import annotations

from scenario_forge.core.scenario import ScenarioSpec
from scripts.generate_scientific_workbench_r11_1 import (
    build_task05_scenario,
    build_task09_scenario,
)


def test_r11_1_is_an_immutable_child_of_r11() -> None:
    for task_number, builder in ((5, build_task05_scenario), (9, build_task09_scenario)):
        scenario = builder()
        ScenarioSpec.from_mapping(scenario)
        assert scenario["scenario_id"].startswith(f"scientific_workbench_r11_1_task{task_number:02d}")
        assert scenario["metadata"]["release"] == "r11.1"
        assert scenario["metadata"]["supersedes"] == "r11"
        assert scenario["metadata"]["task_interaction_ready"] is False
        assert scenario["metadata"]["robot_policy_success"] is False
        assert scenario["metadata"]["layout_delta_limits"] == {
            "maximum_translation_m": 0.05,
            "maximum_yaw_deg": 15.0,
            "robot_base_frozen": True,
        }

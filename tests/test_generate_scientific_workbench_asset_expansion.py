from __future__ import annotations

from pathlib import Path

import yaml

import scripts.generate_scientific_workbench_asset_expansion as generator


def test_generation_plan_has_five_stirring_backgrounds_and_four_default_tasks() -> None:
    plans = generator.load_generation_plans()

    assert len(plans) == 9
    stirring = [plan for plan in plans if plan.task_number == 7]
    assert [plan.background_id for plan in stirring] == [
        "example4",
        "teaching_research",
        "modern_wet_chemistry",
        "bioclean",
        "analytical_instrumentation",
    ]
    assert len({plan.scenario["scenario_id"] for plan in plans}) == 9
    assert {plan.task_number for plan in plans if plan.background_id == "example4"} == {
        4,
        7,
        8,
        14,
        15,
    }


def test_generation_plan_records_canonical_and_prototype_score_ceilings() -> None:
    plans = generator.load_generation_plans()
    by_task = {}
    for plan in plans:
        by_task.setdefault(plan.task_number, plan)

    assert by_task[7].release_status == "canonical_candidate"
    assert by_task[7].score_ceiling == 1.0
    assert by_task[8].release_status == "canonical_candidate"
    assert by_task[8].score_ceiling == 0.7
    assert by_task[4].release_status == "prototype"
    assert by_task[4].score_ceiling == 0.55
    assert by_task[14].score_ceiling == 0.65
    assert by_task[15].score_ceiling == 0.0


def test_stirring_variants_preserve_task_layout_and_only_replace_scene() -> None:
    plans = [plan for plan in generator.load_generation_plans() if plan.task_number == 7]
    reference = plans[0].scenario

    for plan in plans[1:]:
        assert plan.scenario["objects"] == reference["objects"]
        assert plan.scenario["robot"] == reference["robot"]
        assert plan.scenario["steps"] == reference["steps"]
        assert plan.scenario["scene"]["asset_id"] != reference["scene"]["asset_id"]


def test_all_generation_specs_remain_valid_yaml_files() -> None:
    for path in generator.TASK_SPECS.values():
        loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)

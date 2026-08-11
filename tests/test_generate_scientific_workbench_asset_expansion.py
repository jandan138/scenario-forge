from __future__ import annotations

from pathlib import Path

import yaml

import scripts.generate_scientific_workbench_asset_expansion as generator


def test_generation_plan_has_ten_tasks_and_five_stirring_backgrounds() -> None:
    plans = generator.load_generation_plans()

    assert len(plans) == 14
    stirring = [plan for plan in plans if plan.task_number == 7]
    assert [plan.background_id for plan in stirring] == [
        "example4",
        "teaching_research",
        "modern_wet_chemistry",
        "bioclean",
        "analytical_instrumentation",
    ]
    assert len({plan.scenario["scenario_id"] for plan in plans}) == 14
    assert {plan.task_number for plan in plans} == {1, 2, 4, 5, 7, 8, 13, 14, 15, 16}
    assert {
        plan.task_number
        for plan in plans
        if plan.background_id == "modern_wet_chemistry"
    } == {1, 2, 7, 13, 16}
    assert {plan.task_number for plan in plans if plan.background_id == "teaching_research"} == {4, 5, 7}
    assert {plan.task_number for plan in plans if plan.background_id == "bioclean"} == {7, 8, 14}
    assert {plan.task_number for plan in plans if plan.background_id == "analytical_instrumentation"} == {7, 15}


def test_generation_plan_records_canonical_and_prototype_score_ceilings() -> None:
    plans = generator.load_generation_plans()
    by_task = {}
    for plan in plans:
        by_task.setdefault(plan.task_number, plan)

    assert by_task[7].release_status == "canonical_candidate"
    assert by_task[7].score_ceiling == 1.0
    assert by_task[8].release_status == "canonical_candidate"
    assert by_task[8].score_ceiling == 0.7
    assert by_task[4].release_status == "canonical_candidate"
    assert by_task[4].score_ceiling == 1.0
    assert by_task[5].release_status == "canonical_candidate"
    assert by_task[5].score_ceiling == 1.0
    assert by_task[1].score_ceiling == 0.6
    assert by_task[2].score_ceiling == 0.6
    assert by_task[13].score_ceiling == 0.6
    assert by_task[16].score_ceiling == 0.7
    assert by_task[14].score_ceiling == 0.65
    assert by_task[15].score_ceiling == 0.0


def test_task_one_uses_the_qualified_upright_conical_flask() -> None:
    plan = next(
        plan for plan in generator.load_generation_plans() if plan.task_number == 1
    )
    flask = next(
        item
        for item in plan.scenario["objects"]
        if item["id"] == "obj_conical_bottle03"
    )

    assert flask["asset_id"] == (
        "scientific_workbench_conical_flask_250ml_29_42_dynamic"
    )
    assert flask["source_prim_path"] == "/World/ConicalFlask2942"


def test_all_r5_conical_flasks_use_the_qualified_upright_asset() -> None:
    relevant = [
        plan for plan in generator.load_generation_plans() if plan.task_number in {1, 13, 16}
    ]

    for plan in relevant:
        flask_assets = {
            item["asset_id"]
            for item in plan.scenario["objects"]
            if "conical" in str(item.get("role", ""))
            or item.get("asset_id")
            == "scientific_workbench_conical_flask_250ml_29_42_dynamic"
        }
        assert flask_assets == {
            "scientific_workbench_conical_flask_250ml_29_42_dynamic"
        }


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

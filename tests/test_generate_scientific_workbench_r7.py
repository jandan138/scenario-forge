from __future__ import annotations

from copy import deepcopy

import scripts.generate_scientific_workbench_r7 as generator


def test_r7_plan_is_seven_immutable_packages_for_tasks_2_7_8() -> None:
    plans = generator.load_r7_plans()

    assert len(plans) == 7
    assert [(plan.task_number, plan.background_id) for plan in plans] == [
        (2, "modern_wet_chemistry"),
        (7, "example4"),
        (7, "teaching_research"),
        (7, "modern_wet_chemistry"),
        (7, "bioclean"),
        (7, "analytical_instrumentation"),
        (8, "bioclean"),
    ]
    assert len({plan.scenario["scenario_id"] for plan in plans}) == 7


def test_r7_main_assets_are_only_the_locked_zip_assets() -> None:
    plans = generator.load_r7_plans()
    expected = {
        2: {"scientific_workbench_r7_graduated_cylinder_250ml", "scientific_workbench_r7_beaker_325ml"},
        7: {"scientific_workbench_r7_beaker_325ml", "scientific_workbench_r7_glass_stirring_rod_300mm"},
        8: {"scientific_workbench_r7_tube_rack", "scientific_workbench_r7_centrifuge_tube_15ml_body", "scientific_workbench_r7_centrifuge_tube_15ml_cap"},
    }
    for plan in plans:
        task_assets = {
            item["asset_id"]
            for item in plan.scenario["objects"]
            if item.get("role") != "table" and item.get("role") != "context_prop"
        }
        assert task_assets == expected[plan.task_number]


def test_r7_racks_use_sockets_1_3_6_without_metric_participation() -> None:
    plans = generator.load_r7_plans()
    with_racks = [
        plan for plan in plans
        if plan.task_number == 8
        or (plan.task_number == 7 and plan.background_id in {"example4", "teaching_research", "bioclean"})
    ]
    for plan in with_racks:
        context = [item for item in plan.scenario["objects"] if item.get("role") == "context_prop"]
        sockets = sorted(item["metadata"]["rack_socket_index"] for item in context if "rack_socket_index" in item.get("metadata", {}))
        assert sockets == [1, 3, 6] if plan.task_number == 7 else [1, 6]
        assert all(item["metadata"].get("metric_participation") == "none" for item in context)


def test_r7_ik_is_explicitly_not_run() -> None:
    for plan in generator.load_r7_plans():
        assert plan.scenario["metadata"]["ik_preflight"] == "not_run"
        assert plan.scenario["success"]["predicates"]


def test_rack_population_positions_are_derived_from_authoritative_socket_frames() -> None:
    scenario = deepcopy(generator._task8())
    rack_source = type("Source", (), {
        "upstream_package": type("Package", (), {"metadata": {
            "interaction_contract": {"named_frames": {
                "medium_socket_01_inserted_bottom": {"translation_body_local_usd": [-0.08, 0.0, 0.001]},
                "medium_socket_03_inserted_bottom": {"translation_body_local_usd": [-0.02, 0.0, 0.001]},
                "medium_socket_06_inserted_bottom": {"translation_body_local_usd": [0.08, 0.0, 0.001]},
            }}
        }})()
    })()

    result = generator._materialize_rack_population(
        scenario,
        {"scientific_workbench_r7_tube_rack": rack_source},
    )

    objects = {item["id"]: item for item in result["objects"]}
    assert objects["obj_centrifuge_tube"]["pose"]["xyz"] == [-0.06, -0.16, 0.756]
    assert objects["context_closed_tube_s1"]["pose"]["xyz"] == [-0.12, -0.16, 0.756]
    assert objects["context_closed_tube_s6"]["pose"]["xyz"] == [0.04, -0.16, 0.756]
    assert objects["obj_centrifuge_tube"]["metadata"]["pose_source"] == "obj_tube_rack.medium_socket_03_inserted_bottom"

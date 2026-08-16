from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import scripts.generate_scientific_workbench_r7 as r7
import scripts.generate_scientific_workbench_r9 as r9
import scripts.export_scientific_workbench_usd_handoff as handoff


EXPECTED = [
    (2, "modern_wet_chemistry"),
    (7, "example4"),
    (7, "teaching_research"),
    (7, "modern_wet_chemistry"),
    (7, "bioclean"),
    (7, "analytical_instrumentation"),
    (8, "bioclean"),
]


def test_r9_has_seven_fixed_background_packages() -> None:
    plans = r9.load_r9_plans()
    assert [(plan.task_number, plan.background_id) for plan in plans] == EXPECTED
    assert len({plan.scenario["scenario_id"] for plan in plans}) == 7
    assert all(plan.scenario["metadata"]["release"] == "r9" for plan in plans)


def test_r9_keeps_task_core_poses_and_adds_only_non_scoring_context() -> None:
    old = r7.load_r7_plans()
    new = r9.load_r9_plans()
    for r7_plan, r9_plan in zip(old, new, strict=True):
        r7_core = {
            item["id"]: deepcopy(item["pose"])
            for item in r7_plan.scenario["objects"]
            if item.get("role") != "context_prop"
        }
        r9_core = {
            item["id"]: deepcopy(item["pose"])
            for item in r9_plan.scenario["objects"]
            if item.get("role") != "context_prop"
        }
        assert r9_core == r7_core
        assert r9_plan.scenario["robot"] == r7_plan.scenario["robot"]
        dressing = [
            item
            for item in r9_plan.scenario["objects"]
            if item.get("metadata", {}).get("dressing_release") == "r9"
        ]
        assert 4 <= len(dressing) <= 5
        assert all(item["role"] == "context_prop" for item in dressing)
        assert all(item["metadata"]["metric_participation"] == "none" for item in dressing)
        assert all(abs(float(item["pose"]["xyz"][0])) >= 0.50 for item in dressing)
        assert all(float(item["pose"]["xyz"][1]) >= -0.06 for item in dressing)


def test_r9_category_rules_avoid_task_lookalikes() -> None:
    for plan in r9.load_r9_plans():
        dressing_assets = {
            item["asset_id"]
            for item in plan.scenario["objects"]
            if item.get("metadata", {}).get("dressing_release") == "r9"
        }
        assert "scientific_workbench_r9_context_beaker" not in dressing_assets
        if plan.task_number == 2:
            assert "scientific_workbench_r9_context_graduated_cylinder_100ml" not in dressing_assets
        if plan.task_number == 8:
            assert "scientific_workbench_r9_context_graduated_cylinder_100ml" not in dressing_assets
            assert "scientific_workbench_r9_context_rack" not in dressing_assets


def test_r9_preserves_task_related_r7_rack_population() -> None:
    for plan in r9.load_r9_plans():
        if plan.task_number == 7 and plan.background_id in r7.RACKED_TASK7_BACKGROUNDS:
            ids = {item["id"] for item in plan.scenario["objects"]}
            assert {
                "context_rack",
                "context_glass_tube_s1",
                "context_glass_tube_s3",
                "context_glass_tube_s6",
            } <= ids
        if plan.task_number == 8:
            objects = {item["id"]: item for item in plan.scenario["objects"]}
            ids = set(objects)
            assert {"context_closed_tube_s1", "context_closed_tube_s6"} <= ids
            assert objects["context_closed_tube_s1"]["asset_id"] == (
                "scientific_workbench_r9_context_centrifuge_tube_15ml_body"
            )
            assert objects["context_closed_tube_s6"]["asset_id"] == (
                "scientific_workbench_r9_context_centrifuge_tube_15ml_body"
            )


def test_r9_preview_request_requires_960_stability_steps(tmp_path: Path, monkeypatch) -> None:
    request = tmp_path / "render_request.yaml"
    request.write_text("package_id: fixture\n", encoding="utf-8")
    monkeypatch.setattr(r9, "write_genmanip_preview_request", lambda *args, **kwargs: request)
    result = r9._write_r9_preview_request(tmp_path)
    payload = r9.yaml.safe_load(result.read_text(encoding="utf-8"))
    assert payload["zero_action_warmup_steps"] == 960
    assert "not Task 07/08 robot or benchmark success" in payload["claim_boundary"]


def test_r9_review_handoff_lists_all_seven_independent_packages() -> None:
    assert len(handoff.R9_PACKAGES) == 7
    assert [item[0] for item in handoff.R9_PACKAGES] == [2, 7, 7, 7, 7, 7, 8]
    assert all("r9" in relative for _, _, relative in handoff.R9_PACKAGES)

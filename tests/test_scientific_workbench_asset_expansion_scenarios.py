from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scenario_forge.core.scenario import ScenarioSpec


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "examples/scientific_workbench/asset_expansion"


def _load(name: str) -> dict[str, object]:
    raw = yaml.safe_load((SCENARIOS / name / "scenario.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    ScenarioSpec.from_mapping(raw)
    return raw


def _rubric(raw: dict[str, object]) -> dict[str, dict[str, object]]:
    success = raw["success"]
    assert isinstance(success, dict)
    progress = success["progress_rubric"]
    assert isinstance(progress, dict)
    items = progress["items"]
    assert isinstance(items, list)
    return {str(item["id"]): item for item in items if isinstance(item, dict)}


def test_task7_encodes_safe_interior_and_signed_angular_sweep() -> None:
    raw = _load("glass_rod_stir")
    assert raw["scenario_id"] == "scientific_workbench_glass_rod_stir"
    objects = {item["id"]: item for item in raw["objects"]}  # type: ignore[index]
    assert objects["obj_beaker"]["asset_id"] == "scientific_workbench_beaker_dynamic_r3"
    rubric = _rubric(raw)
    condition = rubric["stirring_trajectory_completed"]["condition"]
    assert condition["type"] == "motion_trajectory_completed"
    parameters = condition["parameters"]
    assert parameters["trajectory"]["kind"] == "accumulated_angular_sweep"
    assert parameters["trajectory"]["min_angle_deg"] == pytest.approx(360.0)
    assert parameters["trajectory"]["direction_accumulation"] == (
        "max_separate_signed"
    )
    assert parameters["containment_region"] == "obj_beaker.interior_safe"


def test_task8_keeps_twist_claim_inactive_until_thread_semantics_exist() -> None:
    raw = _load("tighten_centrifuge_tube_cap")
    rubric = _rubric(raw)
    assert rubric["cap_rotated_into_closed_state"]["active"] is False
    assert rubric["cap_rotated_into_closed_state"]["requires"] == [
        "threaded_closure.relative_rotation_and_axial_engagement"
    ]
    assert sum(float(item["weight"]) for item in rubric.values() if item.get("active", True)) == pytest.approx(0.7)


@pytest.mark.parametrize(
    ("name", "ceiling"),
    [
        ("funnel_pour_to_centrifuge_tube", 0.65),
        ("solid_sample_weighing_layout", 0.0),
    ],
)
def test_prototype_claim_ceiling_is_explicit(name: str, ceiling: float) -> None:
    raw = _load(name)
    success = raw["success"]
    assert success["claim_scope"] == "asset_layout_prototype"
    rubric = _rubric(raw)
    active = sum(
        float(item["weight"]) for item in rubric.values() if item.get("active", True)
    )
    assert active == pytest.approx(ceiling)


def test_insert_stir_bar_uses_the_geometry_qualified_closure_contract() -> None:
    raw = _load("insert_stir_bar")
    success = raw["success"]
    assert success["claim_scope"] == (
        "semantic_task_contract_with_geometry_qualified_closure"
    )
    rubric = _rubric(raw)
    assert sum(float(item["weight"]) for item in rubric.values()) == pytest.approx(1.0)

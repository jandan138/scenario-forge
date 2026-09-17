from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from scenario_forge.assets.source import LocalUSDAssetSource
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.package import validate_package

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "examples/scientific_workbench/solid_sample_weighing_r6_0/scenario.yaml"
BINDINGS = ROOT / "examples/scientific_workbench/solid_sample_weighing_r6_0/source_bindings.yaml"
SCHEMA = ROOT / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.7.schema.json"
METRICS_SCHEMA = ROOT / "src/scenario_forge/schemas/jsonschema/metrics-v0.4.schema.json"

EXPECTED_WEIGHTS = {
    "weighing_dish_on_pan": 0.08,
    "tare_button_pressed": 0.08,
    "spatula_lifted": 0.06,
    "spatula_enters_sample": 0.08,
    "spatula_carries_sample": 0.12,
    "sample_in_weighing_dish": 0.10,
    "terminal_lcd_1_00_g": 0.35,
    "spatula_returned": 0.05,
    "weighing_dish_remains_on_pan": 0.08,
}


def _load() -> dict[str, object]:
    raw = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_solid_sample_weighing_r6_0_uses_a54_pbd_scene_and_1g_rubric() -> None:
    raw = _load()
    spec = ScenarioSpec.from_mapping(raw)
    assert spec.scenario_id == "scientific_workbench_solid_sample_weighing_r6_0"
    assert spec.scene.composition_mode == "producer_entrypoint"
    assert spec.scene.asset_id == "task09_powder_bottle_r6_0"
    assert {item.asset_id for item in spec.objects} == {"task09_powder_bottle_r6_0"}
    assert {item.instance_mode for item in spec.objects} == {"embedded_scene_prim"}

    rubric = spec.success.progress_rubric
    assert rubric is not None
    assert rubric.aggregation["primary_metric_id"] == "terminal_lcd_1_00_g"
    items = {item.item_id: item for item in rubric.items}
    assert set(items) == set(EXPECTED_WEIGHTS)
    assert sum(item.weight for item in rubric.items) == pytest.approx(1.0)
    for item_id, weight in EXPECTED_WEIGHTS.items():
        item = items[item_id]
        assert item.weight == pytest.approx(weight)
        assert item.active is True

    lcd = items["terminal_lcd_1_00_g"]
    assert lcd.temporal["kind"] == "terminal"
    assert lcd.condition["type"] == "instrument_display_matches"
    assert lcd.condition["parameters"] == {
        "instrument": "obj_balance",
        "channel": "lcd_readout",
        "expected_text": "1.00 g",
        "after_tare": True,
    }

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(raw)) == []

    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    assert "task09_powder_bottle_r6_0" in bindings["bindings"]
    source_usd = Path(bindings["bindings"]["task09_powder_bottle_r6_0"]["source_usd"])
    if not source_usd.is_absolute():
        source_usd = (BINDINGS.parent / source_usd).resolve()
    assert source_usd.name == "scene.usda"
    assert "vr_a54" in source_usd.parts


def test_r6_0_a54_is_candidate_and_does_not_replace_r4() -> None:
    heads = json.loads((ROOT / "configs/artifact_retention/current_task_heads.v1.json").read_text())
    rows = [row for row in heads["entries"] if row.get("variant_key") == "isaac45_pbd_a54_vr"]
    assert len(rows) == 1
    assert rows[0]["status"] == "current_candidate"
    assert rows[0]["revision"] == "r6.0"
    assert rows[0]["handoff_zip"] == "handoff/scientific_workbench_solid_sample_weighing_r6_0_a54.zip"
    powder = [row for row in heads["entries"]
              if row.get("variant_key") == "isaac45_original_scene_powder_bottle"]
    assert powder[0]["status"] == "current_delivery"
    assert powder[0]["handoff_zip"] == "handoff/task09_powder_bottle_r4.zip"


def test_compiled_r6_0_package_transports_1g_progress_metrics(tmp_path: Path) -> None:
    source = tmp_path / "source" / "scene.usda"
    source.parent.mkdir()
    source.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World"
{
    def Xform "table" {}
    def Xform "obj_analytical_balance" {}
    def Xform "obj_weighing_boat" {}
    def Xform "obj_sampling_spoon" {}
    def Xform "obj_powder_bottle" {}
}
""",
        encoding="utf-8",
    )
    spec = ScenarioSpec.from_mapping(_load())
    package_root = tmp_path / "package"
    compile_scenario_package(
        spec,
        {
            "task09_powder_bottle_r6_0": LocalUSDAssetSource(
                asset_id="task09_powder_bottle_r6_0",
                source_usd=source,
                role="interactive_composed_scene",
                license="internal-task09-powder-r6.0",
                source_uri="outputs://task09_powder_bottle_r6_0",
                attribution=("Task09 powder bottle r6.0 a54 PBD VR candidate",),
                redistributable=False,
            )
        },
        package_root,
    )
    report = validate_package(package_root, require_asset_lock=True)
    assert report.ok, report.messages
    metrics = yaml.safe_load((package_root / "metrics" / "metrics.yaml").read_text(encoding="utf-8"))
    assert metrics["schema_version"] == "metrics/v0.4"
    assert metrics["aggregation"]["primary_metric_id"] == "terminal_lcd_1_00_g"
    by_id = {item["id"]: item for item in metrics["metrics"]}
    assert by_id["terminal_lcd_1_00_g"]["weight"] == pytest.approx(0.35)
    assert by_id["terminal_lcd_1_00_g"]["temporal"]["kind"] == "terminal"
    schema = json.loads(METRICS_SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(metrics)) == []

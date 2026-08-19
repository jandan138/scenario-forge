from __future__ import annotations

from math import isclose
from pathlib import Path
from zipfile import ZipFile

import yaml

from scenario_forge.core.scenario import ScenarioSpec
from scripts.generate_scientific_workbench_task09_r12 import (
    build_task09_r12_scenario,
    finalize_vr_release,
)


def _object(scenario: dict[str, object], object_id: str) -> dict[str, object]:
    return next(  # type: ignore[return-value]
        item
        for item in scenario["objects"]  # type: ignore[union-attr]
        if item["id"] == object_id
    )


def test_task09_r12_places_only_oven_and_scaled_glass_beaker_on_room_floor() -> None:
    scenario = build_task09_r12_scenario()

    ScenarioSpec.from_mapping(scenario)
    objects = scenario["objects"]  # type: ignore[assignment]
    assert [item["id"] for item in objects] == [  # type: ignore[index]
        "table",
        "obj_oven",
        "obj_sample_beaker",
    ]
    table = _object(scenario, "table")
    oven = _object(scenario, "obj_oven")
    beaker = _object(scenario, "obj_sample_beaker")
    assert table["asset_id"] == (
        "scientific_workbench_r12_analytical_room_floor_static_support"
    )
    assert table["metadata"]["vr_presentation_visibility"] == "invisible"  # type: ignore[index]
    assert oven["asset_id"] == "scientific_workbench_r12_analog_oven"
    assert oven["pose"]["xyz"] == [0.35, 0.0, 0.0]  # type: ignore[index]
    assert beaker["asset_id"] == "scientific_workbench_r12_beaker_dynamic_glass_v1"
    assert beaker["pose"]["xyz"] == [-0.35, -0.16, 0.0]  # type: ignore[index]
    assert beaker["pose"]["scale_xyz"] == [0.7, 0.7, 0.7]  # type: ignore[index]
    assert scenario["robot"]["spawn"]["xyz"] == [0.0, -1.02, 0.31]  # type: ignore[index]
    assert scenario["metadata"]["robot_policy_success"] is False  # type: ignore[index]
    weights = [
        item["weight"]
        for item in scenario["success"]["progress_rubric"]["items"]  # type: ignore[index]
    ]
    assert isclose(sum(weights), 1.0)


def test_finalize_vr_release_builds_relocatable_handoff_zip(tmp_path: Path) -> None:
    output = tmp_path / "r12"
    vr = output / "packages/task09/adapters/vr_teleop"
    (vr / "deps/environment").mkdir(parents=True)
    (vr / "scene.usd").write_text("#usda 1.0\n", encoding="utf-8")
    (vr / "task_config.py").write_text("TASKS = {}\n", encoding="utf-8")
    (vr / "deps/environment/asset.usd").write_text("#usda 1.0\n", encoding="utf-8")
    report = vr / "evidence/open_smoke/report.json"
    report.parent.mkdir(parents=True)
    report.write_text('{"status": "pass"}\n', encoding="utf-8")
    (output / "manifest.yaml").write_text(
        yaml.safe_dump({"status": "vr_static_complete_open_smoke_pending"}),
        encoding="utf-8",
    )

    archive = finalize_vr_release(output_dir=output)

    assert archive.is_file()
    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    root = "scientific_workbench_task09_r12_vr/"
    assert root + "scene.usd" in names
    assert root + "task_config.py" in names
    assert root + "deps/environment/asset.usd" in names
    manifest = yaml.safe_load((output / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["status"] == "vr_open_smoke_complete"

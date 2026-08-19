from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import zipfile

import pytest

from scenario_forge.adapters.liquid_autofill import (
    LiquidAutofillCommandPlan,
    LiquidAutofillHandoffError,
    build_request,
    load_producer_handoff,
    RECIPE_SHA256,
)
from scenario_forge.artifacts.liquid_alias import build_liquid_alias_package
from scenario_forge.cli import build_parser


def _write_producer(root: Path, *, status: str = "pass") -> Path:
    root.mkdir(parents=True)
    (root / "producer_overlay.usda").write_text(
        '#usda 1.0\nover "World" {}\n', encoding="utf-8"
    )
    (root / "analysis.json").write_text(
        json.dumps(
            {
                "schema_version": "aan.gpu_pbd_container_analysis.v1",
                "container_prim": "/World/Beaker",
                "scene_root_prim": "/World",
                "default_prim": "World",
                "up_axis": "Z",
                "meters_per_unit": 1.0,
                "cavity": {
                    "center_xy_m": [0, 0],
                    "radius_x_m": 0.03,
                    "radius_y_m": 0.03,
                    "floor_m": 0.01,
                    "rim_m": 0.2,
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "recipe.json").write_text(
        json.dumps({"recipe_id": "task02_r10_3_blue_gpu_pbd_v1"}),
        encoding="utf-8",
    )
    evidence = root / "evidence/runtime_qualification"
    evidence.mkdir(parents=True)
    (evidence / "report.json").write_text(
        json.dumps({"overall_status": status}), encoding="utf-8"
    )
    report_sha = sha256((evidence / "report.json").read_bytes()).hexdigest()
    manifest = {
        "schema_version": "aan.gpu_pbd_autofill_result.v1",
        "overall_status": status,
        "blocked_reasons": [] if status == "pass" else ["not_qualified"],
        "source_binding": {
            "scene": "/source/scene.usd",
            "scene_sha256": "a" * 64,
            "container_prim": "/World/Beaker",
        },
        "recipe": {
            "recipe_id": "task02_r10_3_blue_gpu_pbd_v1",
            "sha256": RECIPE_SHA256,
            "path": "recipe.json",
        },
        "entrypoints": {
            "overlay_usd": "producer_overlay.usda",
            "particle_system_prim": "/__ScenarioForgeLiquid_Beaker/ParticleSystem",
            "particle_set_prim": "/__ScenarioForgeLiquid_Beaker/ParticleSet",
        },
        "fill_profile": {
            "measurement": "live_points_target_local_up_q95",
            "target_settled_fill_ratio": 0.4,
            "tolerance": 0.05,
            "particle_count": 580,
        },
        "analysis": "analysis.json",
        "qualification": {
            "status": status,
            "report": "evidence/runtime_qualification/report.json",
            "report_sha256": report_sha,
        },
        "claim": "qualified_gpu_pbd_loaded_start" if status == "pass" else None,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _write_closure(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "asset.usd").write_text(
        '#usda 1.0\n(defaultPrim = "World")\ndef Xform "World" {}\n',
        encoding="utf-8",
    )
    (root / "usd_closure_handoff.json").write_text(
        json.dumps(
            {
                "schema_version": "aan.usd_closure_handoff.v1",
                "overall_status": "pass",
                "blocked_reasons": [],
                "root_usd": "asset.usd",
                "dependency_closure": {
                    "closure_status": "pass",
                    "remote_uris": [],
                    "missing_files": [],
                },
                "static_usd_report": {
                    "root_layer": {"default_prim": "World"}
                },
            }
        ),
        encoding="utf-8",
    )
    return root


def test_command_plan_uses_convertasset_wrapper_by_default(tmp_path: Path) -> None:
    root = tmp_path / "ConvertAsset"
    plan = LiquidAutofillCommandPlan(convert_asset_root=root)

    assert plan.inspect_command(tmp_path / "scene.usd", tmp_path / "inspect.json") == (
        str(root / "scripts/isaac_python.sh"),
        str(root / "main.py"),
        "liquid-inspect",
        str(tmp_path / "scene.usd"),
        "--out",
        str(tmp_path / "inspect.json"),
    )


def test_command_plan_pins_explicit_isaac_python_for_nested_cold_runs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ConvertAsset"
    isaac_python = tmp_path / "isaac41/bin/python"
    plan = LiquidAutofillCommandPlan(root, isaac_python)

    command = plan.autofill_command(tmp_path / "request.json", tmp_path / "out")

    assert command[:2] == (
        str(root / "scripts/isaac_python.sh"),
        str(root / "main.py"),
    )
    assert command[-2:] == ("--isaac-python", str(isaac_python))


def test_request_pins_task02_recipe_and_height_fill(tmp_path: Path) -> None:
    scene = tmp_path / "scene.usd"
    scene.write_text("#usda 1.0\n", encoding="utf-8")

    request = build_request(scene=scene, container="/World/Beaker", fill=0.6)

    assert request["schema_version"] == "aan.gpu_pbd_autofill_request.v1"
    assert request["target_settled_fill_ratio"] == 0.6
    assert request["fill_semantics"] == "live_points_target_local_up_q95_height_ratio"
    assert request["recipe_id"] == "task02_r10_3_blue_gpu_pbd_v1"


def test_loader_rejects_unqualified_candidate(tmp_path: Path) -> None:
    producer = _write_producer(tmp_path / "producer", status="candidate")

    with pytest.raises(LiquidAutofillHandoffError, match="not qualified"):
        load_producer_handoff(producer)


def test_alias_package_is_relative_self_contained_and_deterministic(tmp_path: Path) -> None:
    producer = load_producer_handoff(_write_producer(tmp_path / "producer"))
    closure = _write_closure(tmp_path / "closure")
    output = tmp_path / "delivery"

    result = build_liquid_alias_package(
        source_scene=tmp_path / "source/room.usd",
        producer=producer,
        closure_dir=closure,
        output_dir=output,
        container_slug="beaker",
        fill=0.4,
        integration_evidence=None,
    )

    assert result.alias_usd.name == "room__liquid__beaker__fill40.usd"
    text = result.alias_usd.read_text(encoding="utf-8")
    assert 'defaultPrim = "World"' in text
    assert "@room__liquid__beaker__fill40_deps/liquid/producer_overlay.usda@" in text
    assert "@room__liquid__beaker__fill40_deps/source/asset.usd@" in text
    assert "/source/room.usd" not in text
    assert result.zip_path.is_file()
    with zipfile.ZipFile(result.zip_path) as archive:
        names = set(archive.namelist())
    assert "room__liquid__beaker__fill40.usd" in names
    assert "room__liquid__beaker__fill40_deps/manifest.json" in names
    manifest = json.loads((result.dependencies / "manifest.json").read_text())
    assert manifest["claim"] == "qualified_gpu_pbd_loaded_start"
    assert manifest["robot_policy_success"] is False


def test_cli_exposes_inspect_and_add_commands() -> None:
    parser = build_parser()

    inspect = parser.parse_args(["liquid", "inspect", "--scene", "scene.usd"])
    add = parser.parse_args(
        [
            "liquid",
            "add",
            "--scene",
            "scene.usd",
            "--container",
            "/World/Beaker",
            "--fill",
            "0.4",
        ]
    )

    assert inspect.liquid_command == "inspect"
    assert add.liquid_command == "add"

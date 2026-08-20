from __future__ import annotations

import json
from pathlib import Path

import pytest

from scenario_forge.adapters.simple_sdf_liquid import (
    SimpleSdfLiquidCommandPlan,
    SimpleSdfLiquidHandoffError,
    load_multi_liquid_handoff,
)
from scenario_forge.cli import build_parser


def test_command_plan_delegates_usd_and_physx_to_convertasset(tmp_path: Path) -> None:
    root = tmp_path / "ConvertAsset"
    plan = SimpleSdfLiquidCommandPlan(root)

    assert plan.collision_build_command(tmp_path / "approved.yaml", tmp_path / "out") == (
        str(root / "scripts/isaac_python.sh"),
        str(root / "main.py"),
        "simple-sdf-build",
        "--spec",
        str(tmp_path / "approved.yaml"),
        "--out",
        str(tmp_path / "out"),
    )


def test_cli_exposes_two_separate_stages() -> None:
    parser = build_parser()
    propose = parser.parse_args(
        [
            "fluid-asset", "simple-sdf-propose", "--source", "scene.usd",
            "--container", "/World/Tube", "--visual-mesh", "/World/Tube/Visual/Mesh",
            "--particle-scale", "small_required", "--out", "review",
        ]
    )
    build = parser.parse_args(
        ["fluid-asset", "simple-sdf-build", "--spec", "approved.yaml", "--out", "asset"]
    )
    liquid = parser.parse_args(
        ["liquid", "sample-add", "--spec", "liquid.yaml", "--out", "package"]
    )

    assert propose.fluid_asset_command == "simple-sdf-propose"
    assert build.fluid_asset_command == "simple-sdf-build"
    assert liquid.liquid_command == "sample-add"


def _handoff(root: Path, *, duplicate_group: bool = False) -> Path:
    root.mkdir()
    (root / "scene.usda").write_text(
        '#usda 1.0\n(defaultPrim = "World")\ndef Xform "World" {}\n'
    )
    (root / "liquid_overlay.usda").write_text('#usda 1.0\ndef Scope "__ScenarioForgeFluid" {}\n')
    evidence = root / "evidence/runtime_validation"
    evidence.mkdir(parents=True)
    report = evidence / "report.json"
    report.write_text(json.dumps({"overall_status": "pass"}))
    from hashlib import sha256

    manifest = {
        "schema_version": "aan.multi_liquid_sample_result.v1",
        "overall_status": "pass",
        "blocked_reasons": [],
        "entrypoints": {
            "root_usd": "scene.usda",
            "overlay_usd": "liquid_overlay.usda",
            "particle_system_prim": "/__ScenarioForgeFluid/ParticleSystem",
            "particle_sets_root": "/__ScenarioForgeFluid/ParticleSets",
        },
        "sets": [
            {
                "id": "bottle",
                "particle_prim": "/__ScenarioForgeFluid/ParticleSets/bottle",
                "particle_group": 0,
                "particle_count": 50000,
            },
            {
                "id": "tube",
                "particle_prim": "/__ScenarioForgeFluid/ParticleSets/tube",
                "particle_group": 0 if duplicate_group else 1,
                "particle_count": 2251,
            },
        ],
        "validation": {
            "mode": "quick",
            "status": "pass",
            "report": "evidence/runtime_validation/report.json",
            "report_sha256": sha256(report.read_bytes()).hexdigest(),
        },
        "claim": "provisional_gpu_pbd_loaded_start",
        "robot_policy_success": False,
        "benchmark_success": False,
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


def test_handoff_accepts_independent_sets_on_one_shared_system(tmp_path: Path) -> None:
    result = load_multi_liquid_handoff(_handoff(tmp_path / "producer"))

    assert result.particle_system_prim == "/__ScenarioForgeFluid/ParticleSystem"
    assert [item["id"] for item in result.sets] == ["bottle", "tube"]


def test_handoff_rejects_reused_particle_group(tmp_path: Path) -> None:
    with pytest.raises(SimpleSdfLiquidHandoffError, match="particleGroup"):
        load_multi_liquid_handoff(_handoff(tmp_path / "producer", duplicate_group=True))

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


def test_handoff_accepts_v2_auto_sampler_evidence(tmp_path: Path) -> None:
    root = _handoff(tmp_path / "producer")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "aan.multi_liquid_sample_result.v2"
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "auto_samplers.usda").write_text(
        '#usda 1.0\ndef Scope "__ScenarioForgeAutoSamplers" {}\n'
    )
    manifest["entrypoints"]["auto_samplers_usd"] = "evidence/auto_samplers.usda"
    manifest["sets"][0].update(
        {
            "sampler_mode": "mouth_drop",
            "target_fill_ratio": 0.4,
            "sampler_mesh_prim": "/__ScenarioForgeAutoSamplers/bottle",
        }
    )
    manifest["sets"][1].update(
        {
            "sampler_mode": "inside_fill",
            "target_fill_ratio": 0.2,
            "sampler_mesh_prim": "/__ScenarioForgeAutoSamplers/tube",
        }
    )
    manifest_path.write_text(json.dumps(manifest))

    result = load_multi_liquid_handoff(root)

    assert result.manifest["schema_version"] == "aan.multi_liquid_sample_result.v2"
    assert result.sets[0]["sampler_mode"] == "mouth_drop"


def test_handoff_rejects_v2_auto_sampler_outside_canonical_scope(tmp_path: Path) -> None:
    root = _handoff(tmp_path / "producer")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "aan.multi_liquid_sample_result.v2"
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "auto_samplers.usda").write_text('#usda 1.0\n')
    manifest["entrypoints"]["auto_samplers_usd"] = "evidence/auto_samplers.usda"
    for item in manifest["sets"]:
        item.update(
            {
                "sampler_mode": "inside_fill",
                "target_fill_ratio": 0.4,
                "sampler_mesh_prim": "/World/UnscopedSampler",
            }
        )
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(SimpleSdfLiquidHandoffError, match="canonical scope"):
        load_multi_liquid_handoff(root)


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

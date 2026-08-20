from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.fluid_asset import (
    FluidAssetCommandPlan,
    FluidAssetHandoffError,
    load_fluid_asset_handoff,
)
from scenario_forge.cli import build_parser
from scenario_forge.generation.fluid_asset import (
    load_batch_qualification_request,
    load_batch_request,
)


def _producer(root: Path, *, status: str = "pass", behavior: str = "reservoir") -> Path:
    root.mkdir(parents=True)
    (root / "asset.usda").write_text(
        '#usda 1.0\n(defaultPrim = "FluidInteractionAsset")\n'
        'def Xform "FluidInteractionAsset" {}\n',
        encoding="utf-8",
    )
    interaction = root / "interaction"
    interaction.mkdir()
    profile = {
        "schema_version": "aan.fluid_interaction_asset_profile.v1",
        "behavior": behavior,
        "asset_root_prim": "/FluidInteractionAsset",
        "claim": "qualified_fluid_interaction_asset" if status == "pass" else None,
        "robot_policy_success": False,
        "benchmark_success": False,
    }
    profile_path = interaction / "fluid_profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    import hashlib

    evidence = root / "evidence/qualification"
    evidence.mkdir(parents=True)
    report_path = evidence / "report.json"
    report_path.write_text(json.dumps({"overall_status": status}), encoding="utf-8")
    manifest = {
        "schema_version": "aan.fluid_interaction_asset_result.v1",
        "overall_status": status,
        "blocked_reasons": [] if status == "pass" else ["not_qualified"],
        "entrypoints": {
            "root_usd": "asset.usda",
            "asset_entry_prim": "/FluidInteractionAsset",
        },
        "profile": {
            "path": "interaction/fluid_profile.json",
            "sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        },
        "qualification": {
            "status": status,
            "report": "evidence/qualification/report.json",
            "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        },
        "claim": "qualified_fluid_interaction_asset" if status == "pass" else None,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_command_plan_keeps_geometry_implementation_in_convertasset(tmp_path: Path) -> None:
    plan = FluidAssetCommandPlan(tmp_path / "ConvertAsset")

    assert plan.prepare_command(
        tmp_path / "source.usd", "/World/Flask", tmp_path / "review"
    ) == (
        str(tmp_path / "ConvertAsset/scripts/isaac_python.sh"),
        str(tmp_path / "ConvertAsset/main.py"),
        "fluid-interaction-propose",
        str(tmp_path / "source.usd"),
        "--prim",
        "/World/Flask",
        "--out",
        str(tmp_path / "review"),
    )


def test_handoff_rejects_unqualified_candidate(tmp_path: Path) -> None:
    with pytest.raises(FluidAssetHandoffError, match="not qualified"):
        load_fluid_asset_handoff(_producer(tmp_path / "candidate", status="candidate"))


def test_handoff_accepts_empty_qualified_asset(tmp_path: Path) -> None:
    result = load_fluid_asset_handoff(_producer(tmp_path / "package"))

    assert result.behavior == "reservoir"
    assert result.entry_usd.name == "asset.usda"
    assert result.entry_prim == "/FluidInteractionAsset"


def test_cli_exposes_fluid_asset_single_and_batch_commands() -> None:
    parser = build_parser()
    prepare = parser.parse_args(
        [
            "fluid-asset",
            "prepare",
            "--source",
            "asset.usd",
            "--prim",
            "/World/Object",
            "--out",
            "review",
        ]
    )
    qualify = parser.parse_args(
        ["fluid-asset", "qualify", "--proposal", "proposal.yaml", "--out", "package"]
    )
    batch = parser.parse_args(
        ["fluid-asset", "batch-prepare", "--request", "assets.yaml", "--out", "reviews"]
    )
    batch_qualify = parser.parse_args(
        [
            "fluid-asset",
            "batch-qualify",
            "--request",
            "approved.yaml",
            "--out",
            "packages",
        ]
    )
    derive = parser.parse_args(
        [
            "fluid-asset",
            "derive-partitions",
            "--proposal",
            "proposal.yaml",
            "--out",
            "review2",
        ]
    )

    assert prepare.fluid_asset_command == "prepare"
    assert qualify.fluid_asset_command == "qualify"
    assert batch.fluid_asset_command == "batch-prepare"
    assert batch_qualify.fluid_asset_command == "batch-qualify"
    assert derive.fluid_asset_command == "derive-partitions"


def test_batch_request_requires_unique_exact_prim_items(tmp_path: Path) -> None:
    request = tmp_path / "assets.yaml"
    request.write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-fluid-asset-batch/v0.1",
                "items": [
                    {"id": "flask", "source": "flask.usd", "prim": "/World/Flask"},
                    {"id": "funnel", "source": "funnel.usd", "prim": "/World/Funnel"},
                ],
            }
        ),
        encoding="utf-8",
    )

    items = load_batch_request(request)

    assert [item.item_id for item in items] == ["flask", "funnel"]
    assert items[0].source == (tmp_path / "flask.usd").resolve()


def test_batch_qualification_request_binds_approved_proposals(tmp_path: Path) -> None:
    request = tmp_path / "approved.yaml"
    request.write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-fluid-asset-qualification-batch/v0.1",
                "items": [
                    {"id": "flask", "proposal": "reviews/flask/proposal.yaml"},
                    {"id": "funnel", "proposal": "reviews/funnel/proposal.yaml"},
                ],
            }
        ),
        encoding="utf-8",
    )

    items = load_batch_qualification_request(request)

    assert [item.item_id for item in items] == ["flask", "funnel"]
    assert items[1].proposal == (tmp_path / "reviews/funnel/proposal.yaml").resolve()

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.ik_preflight import (
    ProvisionalIKPreflightError,
    validate_provisional_ik_result,
    write_provisional_ik_preflight_request,
)


def _package(tmp_path: Path) -> Path:
    root = tmp_path / "package"
    root.mkdir()
    (root / "scenario.yaml").write_text(
        yaml.safe_dump(
            {
                "scenario_id": "pour",
                "robot": {"spawn": {"xyz": [-1.02, 0.0, 0.31]}},
                "objects": [
                    {"id": "table", "role": "table", "pose": {"xyz": [0, 0, 0]}},
                    {
                        "id": "source",
                        "role": "source_container",
                        "source_prim_path": "/World/source",
                        "pose": {"xyz": [-0.1, 0.2, 0.8]},
                    },
                    {
                        "id": "target",
                        "role": "target_container",
                        "source_prim_path": "/World/target",
                        "pose": {"xyz": [-0.1, -0.2, 0.8]},
                    },
                ],
                "steps": [
                    {
                        "id": "hold_target",
                        "skill": "grasp_and_hold",
                        "actors": ["auxiliary_arm"],
                        "parameters": {"object": "target"},
                    },
                    {
                        "id": "lift_source",
                        "skill": "lift",
                        "actors": ["operating_arm"],
                        "parameters": {"object": "source"},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "scene").mkdir()
    (root / "scene/main.usda").write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World"
{
    def Cube "source"
    {
        double3 xformOp:translate = (-0.1, 0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        double size = 0.1
    }
    def Cube "target"
    {
        double3 xformOp:translate = (-0.1, -0.2, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        double size = 0.1
    }
}
""",
        encoding="utf-8",
    )
    return root


def test_request_derives_deterministic_fixed_base_candidates(tmp_path: Path) -> None:
    request_path = write_provisional_ik_preflight_request(_package(tmp_path))
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))

    assert request["schema_version"] == "scenario-forge-provisional-ik-request/v0.1"
    assert request["robot_base_motion"] == [0.0, 0.0, 0.0]
    assert request["candidate_generation"]["algorithm"] == "composed_bbox_top_down/v0.1"
    assert request["candidates"] == [
        {
            "candidate_id": "source.top_down",
            "object_id": "source",
            "actor": "operating_arm",
            "target_anchor_world_xyz_m": [-0.1, 0.2, 0.85],
            "pregrasp_offset_world_m": [0.0, 0.0, 0.12],
            "pregrasp_world_xyz_m": [-0.1, 0.2, 0.97],
            "approach_direction_world": [0.0, 0.0, -1.0],
            "yaw_candidates_deg": [0, 90, 180, 270],
        },
        {
            "candidate_id": "target.top_down",
            "object_id": "target",
            "actor": "auxiliary_arm",
            "target_anchor_world_xyz_m": [-0.1, -0.2, 0.85],
            "pregrasp_offset_world_m": [0.0, 0.0, 0.12],
            "pregrasp_world_xyz_m": [-0.1, -0.2, 0.97],
            "approach_direction_world": [0.0, 0.0, -1.0],
            "yaw_candidates_deg": [0, 90, 180, 270],
        },
    ]


def test_result_requires_one_passing_fixed_base_candidate_per_object(tmp_path: Path) -> None:
    request_path = write_provisional_ik_preflight_request(_package(tmp_path))
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": "ebench-provisional-ik-result/v0.1",
        "request_sha256": request["request_sha256"],
        "scenario_id": "pour",
        "runner": {"name": "GenManip/CuRobo", "revision": "runtime-commit"},
        "robot_base_motion": [0.0, 0.0, 0.0],
        "candidate_results": [
            {"candidate_id": "source.top_down", "status": "pass"},
            {"candidate_id": "target.top_down", "status": "pass"},
        ],
    }
    result_path = tmp_path / "result.yaml"
    result_path.write_text(yaml.safe_dump(result), encoding="utf-8")

    evidence_path = validate_provisional_ik_result(request_path, result_path)
    evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))

    assert evidence["overall_status"] == "pass"
    assert evidence["verified_objects"] == ["source", "target"]
    assert evidence["claim_boundary"].startswith("This verifies only")


def test_result_rejects_base_motion_and_missing_object_pass(tmp_path: Path) -> None:
    request_path = write_provisional_ik_preflight_request(_package(tmp_path))
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    result_path = tmp_path / "result.yaml"
    result_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-provisional-ik-result/v0.1",
                "request_sha256": request["request_sha256"],
                "scenario_id": "pour",
                "runner": {"name": "GenManip/CuRobo", "revision": "runtime-commit"},
                "robot_base_motion": [0.1, 0.0, 0.0],
                "candidate_results": [
                    {"candidate_id": "source.top_down", "status": "pass"},
                    {"candidate_id": "target.top_down", "status": "failed"},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProvisionalIKPreflightError, match="fixed robot base"):
        validate_provisional_ik_result(request_path, result_path)


def test_request_blocks_without_composed_geometry_instead_of_using_usd_origin(
    tmp_path: Path,
) -> None:
    root = _package(tmp_path)
    (root / "scene/main.usda").write_text(
        """#usda 1.0
ndef Xform "World"
{
    def Xform "source" {}
    def Xform "target" {}
}
""".replace("ndef", "def"),
        encoding="utf-8",
    )

    request_path = write_provisional_ik_preflight_request(root)
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))

    assert request["candidates"] == []
    assert request["candidate_generation"]["status"] == "blocked"
    assert request["unresolved_objects"][0]["object_id"] == "source"
    assert "empty bounds" in request["unresolved_objects"][0]["reason"]

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from scenario_forge.core.scenario import ScenarioSpec


REPO_ROOT = Path(__file__).resolve().parents[1]
_V01_SCHEMA_SHA256 = "958e0a9fe13ed93fc195fb54753427616705e3569adda3239b4c188c85b1a0d9"


def _scenario_mapping() -> dict[str, object]:
    return {
        "schema_version": "scenario-spec/v0.1",
        "scenario_id": "scientific_workbench_bimanual_pour",
        "domain": "scientific_workbench",
        "task_family": "bimanual_pour",
        "instruction": (
            "Hold the graduated cylinder with the auxiliary arm, pour from the "
            "conical flask with the operating arm, then return the flask."
        ),
        "scene": {
            "asset_id": "scientific_workbench_environment",
            "root_prim_path": "/World",
            "inactive_prim_paths": ["/World/Cube"],
            "world_anchored_prim_paths": ["/World/background_fixture"],
            "pose": {
                "xyz": [-1.0, 2.0, 0.0],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        },
        "objects": [
            {
                "id": "table",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/table",
                "role": "table",
                "pose": {
                    "xyz": [0.24, 0.0, 0.0],
                    "wxyz": [0.0, 1.0, 0.0, 0.0],
                    "scale_xyz": [0.006, 0.005, 0.004],
                },
                "metadata": {"material_bindings": {"surface": "TableMat"}},
            },
            {
                "id": "obj_conical_bottle03",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/conical_bottle03",
                "role": "source_container",
                "pose": {
                    "xyz": [0.32, 0.12, 0.81],
                    "wxyz": [0.6532815, 0.6532815, 0.2705981, 0.2705981],
                },
                "named_frames": {
                    "opening": {"xyz": [0.0, 0.0, 0.18], "wxyz": [1.0, 0.0, 0.0, 0.0]}
                },
                "metadata": {"material_bindings": {"mesh": "GlassFlask"}},
            },
            {
                "id": "obj_graduated_cylinder_03",
                "asset_id": "scientific_workbench_environment",
                "source_prim_path": "/World/graduated_cylinder_03",
                "role": "target_container",
                "pose": {
                    "xyz": [0.32, -0.18, 0.81],
                    "wxyz": [0.7071068, 0.7071068, 0.0, 0.0],
                },
                "named_frames": {
                    "opening": {"xyz": [0.0, 0.0, 0.20], "wxyz": [1.0, 0.0, 0.0, 0.0]}
                },
                "metadata": {"material_bindings": {"mesh": "GlassCylinder"}},
            },
        ],
        "robot": {
            "profile_ref": "manip/lift2/R5a",
            "spawn": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]},
            "actors": [
                {
                    "id": "auxiliary_arm",
                    "end_effector": "left",
                    "capabilities": ["grasp", "hold"],
                },
                {
                    "id": "operating_arm",
                    "end_effector": "right",
                    "capabilities": [
                        "grasp",
                        "lift",
                        "align",
                        "tilt",
                        "place",
                        "release",
                    ],
                },
            ],
        },
        "steps": [
            {
                "id": "grasp_target",
                "skill": "grasp_and_hold",
                "actors": ["auxiliary_arm"],
                "parameters": {"object": "obj_graduated_cylinder_03"},
            },
            {
                "id": "lift_source",
                "skill": "lift",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03"},
                "depends_on": ["grasp_target"],
            },
            {
                "id": "align_openings",
                "skill": "align_openings",
                "actors": ["auxiliary_arm", "operating_arm"],
                "parameters": {
                    "source_frame": "obj_conical_bottle03.opening",
                    "target_frame": "obj_graduated_cylinder_03.opening",
                },
                "depends_on": ["lift_source"],
            },
            {
                "id": "tilt_pour",
                "skill": "tilt_pour",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03", "min_tilt_deg": 40.0},
                "depends_on": ["align_openings"],
            },
            {
                "id": "place_source",
                "skill": "place_on_surface",
                "actors": ["operating_arm"],
                "parameters": {"object": "obj_conical_bottle03"},
                "depends_on": ["tilt_pour"],
            },
        ],
        "invariants": [
            {
                "id": "target_held_during_pour",
                "type": "maintain_grasp",
                "actor": "auxiliary_arm",
                "object": "obj_graduated_cylinder_03",
                "from_step": "grasp_target",
                "through_step": "tilt_pour",
            }
        ],
        "success": {
            "operator": "all",
            "claim_scope": "kinematic_proxy",
            "predicates": [
                {
                    "id": "pour_pose_reached",
                    "type": "relative_pose_reached",
                    "sequence_index": 0,
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "relative_to": "obj_graduated_cylinder_03",
                        "xyz_range": {
                            "x": [-0.08, 0.08],
                            "y": [-0.08, 0.08],
                            "z": [0.10, 0.30],
                        },
                        "axis_alignment": {
                            "object_axis": "y",
                            "target_axis": "y",
                            "comparison": ">=",
                            "threshold_deg": 40.0,
                        },
                    },
                },
                {
                    "id": "source_returned",
                    "type": "object_at_initial_pose",
                    "sequence_index": 1,
                    "parameters": {
                        "object": "obj_conical_bottle03",
                        "xyz_tolerance": [0.06, 0.06, 0.06],
                        "relative_axis_object": "obj_graduated_cylinder_03",
                        "object_axis": "y",
                        "target_axis": "y",
                        "max_axis_error_deg": 15.0,
                    },
                },
            ],
        },
        "max_steps": 1500,
        "seed": "000",
    }


def _scenario_mapping_v02(
    overlay_asset_ids: object = (
        "drying_box_03_dynamic_profile",
        "scientific_workbench_material_overlay",
    ),
) -> dict[str, object]:
    data = _scenario_mapping()
    data["schema_version"] = "scenario-spec/v0.2"
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = (
        list(overlay_asset_ids)
        if isinstance(overlay_asset_ids, tuple)
        else overlay_asset_ids
    )
    data["scene"] = scene
    return data


def test_scenario_spec_round_trips_bimanual_roles_and_invariant() -> None:
    spec = ScenarioSpec.from_mapping(_scenario_mapping())

    assert spec.robot.profile_ref == "manip/lift2/R5a"
    assert [actor.actor_id for actor in spec.robot.actors] == [
        "auxiliary_arm",
        "operating_arm",
    ]
    assert spec.steps[2].actors == ("auxiliary_arm", "operating_arm")
    assert spec.invariants[0].through_step == "tilt_pour"
    assert spec.success.claim_scope == "kinematic_proxy"
    assert spec.scene.inactive_prim_paths == ("/World/Cube",)
    assert spec.scene.world_anchored_prim_paths == ("/World/background_fixture",)
    assert spec.scene.pose is not None
    assert spec.scene.pose.xyz == (-1.0, 2.0, 0.0)
    assert spec.to_mapping() == _scenario_mapping()


def test_scenario_spec_v02_round_trips_scene_overlays_strongest_first() -> None:
    data = _scenario_mapping_v02()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.2"
    assert spec.scene.overlay_asset_ids == (
        "drying_box_03_dynamic_profile",
        "scientific_workbench_material_overlay",
    )
    assert spec.to_mapping() == data


def test_scenario_spec_v01_without_scene_overlays_still_round_trips() -> None:
    data = _scenario_mapping()

    spec = ScenarioSpec.from_mapping(data)

    assert spec.schema_version == "scenario-spec/v0.1"
    assert spec.scene.overlay_asset_ids == ()
    assert "overlay_asset_ids" not in spec.to_mapping()["scene"]  # type: ignore[operator]


def test_scenario_spec_v01_rejects_scene_overlays() -> None:
    data = _scenario_mapping()
    scene = dict(data["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = ["drying_box_03_dynamic_profile"]
    data["scene"] = scene

    with pytest.raises(ValueError, match="overlay_asset_ids"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    "overlay_asset_ids",
    [
        "drying_box_03_dynamic_profile",
        [],
        ["drying_box_03_dynamic_profile", "drying_box_03_dynamic_profile"],
        ["scientific_workbench_environment"],
    ],
)
def test_scenario_spec_v02_rejects_invalid_scene_overlays(
    overlay_asset_ids: object,
) -> None:
    data = _scenario_mapping_v02(overlay_asset_ids)

    with pytest.raises(ValueError, match="scene.overlay_asset_ids"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize("operator", ["all", "any"])
def test_scenario_spec_accepts_declared_success_operators(operator: str) -> None:
    data = _scenario_mapping()
    success = dict(data["success"])  # type: ignore[arg-type]
    success["operator"] = operator
    data["success"] = success

    assert ScenarioSpec.from_mapping(data).success.operator == operator


def test_scenario_spec_rejects_unknown_success_operator() -> None:
    data = _scenario_mapping()
    success = dict(data["success"])  # type: ignore[arg-type]
    success["operator"] = "xor"
    data["success"] = success

    with pytest.raises(ValueError, match="success.operator"):
        ScenarioSpec.from_mapping(data)


def test_scenario_spec_rejects_unknown_step_actor() -> None:
    data = _scenario_mapping()
    steps = list(data["steps"])  # type: ignore[arg-type]
    steps[0] = {**steps[0], "actors": ["third_arm"]}
    data["steps"] = steps

    with pytest.raises(ValueError, match="unknown actor third_arm"):
        ScenarioSpec.from_mapping(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scenario_id", "../outside"),
        ("scenario_id", "/absolute"),
        ("seed", "../../outside"),
        ("seed", "/absolute"),
        ("seed", -1),
    ],
)
def test_scenario_spec_rejects_unsafe_package_path_segments(
    field: str, value: object
) -> None:
    data = _scenario_mapping()
    data[field] = value

    with pytest.raises(ValueError, match=field):
        ScenarioSpec.from_mapping(data)


def test_scenario_spec_schema_artifact_exists_and_parses() -> None:
    path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.1.schema.json"

    schema = json.loads(path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "scenario-spec/v0.1"
    assert {"scene", "objects", "robot", "steps", "success"}.issubset(schema["required"])
    assert "inactive_prim_paths" in schema["$defs"]["sceneSource"]["properties"]
    assert "world_anchored_prim_paths" in schema["$defs"]["sceneSource"]["properties"]
    assert schema["$defs"]["sceneSource"]["properties"]["pose"] == {
        "$ref": "#/$defs/pose"
    }
    assert "liquid_transfer_claim_allowed" not in schema["$defs"]["success"]["properties"]


def test_scenario_spec_v02_schema_declares_unique_scene_overlays_without_mutating_v01() -> None:
    v01_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.1.schema.json"
    )
    v02_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-spec-v0.2.schema.json"
    )

    assert v02_path.is_file()
    v01_schema = json.loads(v01_path.read_text(encoding="utf-8"))
    v02_schema = json.loads(v02_path.read_text(encoding="utf-8"))
    overlay_schema = v02_schema["$defs"]["sceneSource"]["properties"][
        "overlay_asset_ids"
    ]

    assert v02_schema["properties"]["schema_version"]["const"] == "scenario-spec/v0.2"
    assert overlay_schema["type"] == "array"
    assert overlay_schema["minItems"] == 1
    assert overlay_schema["uniqueItems"] is True
    assert overlay_schema["items"] == {"$ref": "#/$defs/nonEmptyString"}
    assert "overlay_asset_ids" not in v01_schema["$defs"]["sceneSource"]["properties"]
    assert sha256(v01_path.read_bytes()).hexdigest() == _V01_SCHEMA_SHA256


def test_golden_bimanual_pour_example_is_a_valid_scenario_spec() -> None:
    path = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    spec = ScenarioSpec.from_mapping(data)

    assert spec.scenario_id == "scientific_workbench_bimanual_pour"
    assert len(spec.steps) == 5
    assert spec.invariants[0].invariant_type == "maintain_grasp"

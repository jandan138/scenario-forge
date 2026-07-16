import json
from hashlib import sha256
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _v03_relative_pose_predicate(sequence_index: int) -> dict[str, object]:
    return {
        "id": f"vessel_pose_{sequence_index}",
        "type": "named_frames_relative_pose_reached",
        "sequence_index": sequence_index,
        "parameters": {
            "source_frame": "source.opening",
            "target_frame": "target.opening",
            "target_frame_from_source_frame_nominal_pose": {
                "xyz": [0.0, 0.0175, 0.0425],
                "wxyz": [0.8746197071, 0.4848096202, 0.0, 0.0],
            },
            "source_origin_in_target_frame_range_m": {
                "x": [-0.005, 0.005],
                "y": [0.015, 0.020],
                "z": [0.035, 0.050],
            },
            "source_normal_axis": "z",
            "target_normal_axis": "z",
            "source_normal_polar_angle_range_deg": (
                [55.0, 60.0] if sequence_index == 0 else [70.0, 80.0]
            ),
            "source_normal_azimuth_range_deg": [-95.0, -85.0],
            "bounds": "inclusive",
            "diagnostic_compatibility_projection": {
                "type": "relative_pose_reached",
                "parameters": {
                    "object": "source",
                    "relative_to": "target",
                    "xyz_range": {
                        "x": [-0.08, 0.08],
                        "y": [-0.08, 0.08],
                        "z": [0.10, 0.30],
                    },
                },
            },
        },
    }


def _v03_return_predicate() -> dict[str, object]:
    return {
        "id": "source_returned",
        "type": "object_returned_to_post_warmup_pose",
        "sequence_index": 2,
        "parameters": {
            "object": "source",
            "translation_error_max_m": 0.06,
            "rotation_error_max_deg": 15.0,
            "bounds": "inclusive",
            "diagnostic_compatibility_projection": {
                "type": "object_at_initial_pose",
                "parameters": {
                    "object": "source",
                    "xyz_tolerance": [0.06, 0.06, 0.06],
                },
            },
        },
    }


def _v03_success() -> dict[str, object]:
    return {
        "operator": "all",
        "claim_scope": "kinematic_proxy",
        "predicates": [
            _v03_relative_pose_predicate(0),
            _v03_relative_pose_predicate(1),
            _v03_return_predicate(),
        ],
    }


def _v03_steps() -> list[dict[str, object]]:
    return [
        {
            "id": "align_openings",
            "skill": "align_openings",
            "actors": ["left", "right"],
            "parameters": {
                "source_frame": "source.opening",
                "target_frame": "target.opening",
            },
        }
    ]


def _v03_invariants() -> list[dict[str, object]]:
    return [
        {
            "id": "target_held",
            "type": "maintain_grasp",
            "actor": "right",
            "object": "target",
            "from_step": "align_openings",
            "through_step": "align_openings",
        }
    ]


def _v03_scenario() -> dict[str, object]:
    pose = {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}
    return {
        "schema_version": "scenario-spec/v0.3",
        "scenario_id": "bimanual_pour",
        "domain": "scientific_workbench",
        "task_family": "bimanual_pour",
        "instruction": "Pour from the source into the target.",
        "scene": {"asset_id": "scene", "root_prim_path": "/World"},
        "objects": [
            {
                "id": "source",
                "asset_id": "source_asset",
                "source_prim_path": "/World/source",
                "role": "source_container",
                "pose": pose,
                "named_frames": {"opening": pose},
            },
            {
                "id": "target",
                "asset_id": "target_asset",
                "source_prim_path": "/World/target",
                "role": "target_container",
                "pose": pose,
                "named_frames": {"opening": pose},
            },
        ],
        "robot": {
            "profile_ref": "manip/lift2/R5a",
            "spawn": pose,
            "actors": [
                {
                    "id": "left",
                    "end_effector": "left",
                    "capabilities": ["grasp"],
                },
                {
                    "id": "right",
                    "end_effector": "right",
                    "capabilities": ["grasp"],
                },
            ],
        },
        "steps": _v03_steps(),
        "invariants": _v03_invariants(),
        "success": _v03_success(),
        "max_steps": 1500,
        "seed": "000",
    }


def _v03_runtime_contract() -> dict[str, object]:
    pose = {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}
    return {
        "schema_version": "scenario-forge-genmanip-runtime-contract/v0.3",
        "contract_status": "transport_only",
        "scenario_id": "bimanual_pour",
        "task_name": "Bimanual pour",
        "episode_name": "000",
        "coordinate_convention": {
            "translation_unit": "meter",
            "quaternion_order": "wxyz",
            "named_frame_pose_relative_to": "state_prim_path",
            "transform_direction": "state_prim_from_named_frame",
            "frame_scale_allowed": False,
        },
        "execution": {
            "native_goal_role": "diagnostic_compatibility_projection",
            "frame_aware_metric_active": False,
            "process_invariants_evaluated": False,
        },
        "robot": {
            "profile_ref": "manip/lift2/R5a",
            "robot_index": 0,
            "actors": [
                {
                    "id": "left",
                    "end_effector": "left",
                    "capabilities": ["grasp"],
                },
                {
                    "id": "right",
                    "end_effector": "right",
                    "capabilities": ["grasp"],
                },
            ],
        },
        "objects": [
            {
                "scenario_object_id": "source",
                "role": "source_container",
                "source_prim_path": "/World/source",
                "runtime_uid": "source",
                "state_prim_path": "/World/scene/source",
                "initial_pose": pose,
                "named_frames": {"opening": pose},
            },
            {
                "scenario_object_id": "target",
                "role": "target_container",
                "source_prim_path": "/World/target",
                "runtime_uid": "target",
                "state_prim_path": "/World/scene/target",
                "initial_pose": pose,
                "named_frames": {"opening": pose},
            },
        ],
        "steps": _v03_steps(),
        "invariants": _v03_invariants(),
        "success": _v03_success(),
    }


def _v03_task() -> dict[str, object]:
    return {
        "schema_version": "task/v0.3",
        "task_id": "bimanual_pour",
        "task_family": "bimanual_pour",
        "instruction": "Pour from the source into the target.",
        "bindings": {
            "objects": {
                "source_container": "source",
                "target_container": "target",
            },
            "actors": {"operating_arm": "left", "auxiliary_arm": "right"},
        },
        "steps": _v03_steps(),
        "invariants": _v03_invariants(),
        "success": _v03_success(),
        "max_steps": 1500,
        "seed": "000",
    }


def test_asset_phase1_schema_artifacts_exist_and_parse() -> None:
    for relative_path in (
        "src/scenario_forge/schemas/jsonschema/asset-manifest-v0.2.schema.json",
        "src/scenario_forge/schemas/jsonschema/asset-lock-v0.2.schema.json",
    ):
        schema_path = REPO_ROOT / relative_path

        data = json.loads(schema_path.read_text(encoding="utf-8"))

        assert data["type"] == "object"
        assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_package_v02_artifact_exists_and_parses() -> None:
    schema_path = (
        REPO_ROOT / "src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json"
    )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == "scenario-package/v0.2"
    assert "entrypoints" in schema["required"]
    assert "assets" in schema["required"]


def test_scene_instances_v02_schema_artifact_exists_and_parses() -> None:
    schema_path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema/scene-instances-v0.2.schema.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["type"] == "object"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "scene-instances/v0.2"
    assert "instances" in schema["required"]


def test_task_phase4_schema_artifacts_exist_and_parse() -> None:
    expected = {
        "task-v0.2.schema.json": "task/v0.2",
        "task-graph-v0.2.schema.json": "task-graph/v0.2",
        "predicates-v0.2.schema.json": "predicates/v0.2",
        "metrics-v0.2.schema.json": "metrics/v0.2",
    }
    for filename, schema_version in expected.items():
        schema_path = REPO_ROOT / "src" / "scenario_forge" / "schemas" / "jsonschema" / filename

        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        assert schema["type"] == "object"
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["properties"]["schema_version"]["const"] == schema_version


def test_ebench_export_v01_schema_artifact_exists_and_parses() -> None:
    schema_path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema/ebench-export-v0.1.schema.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["type"] == "object"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "ebench-scenario-export/v0.1"
    assert "entrypoints" in schema["required"]
    assert "runtime_hints" in schema["required"]
    assert "task_contract" in schema["properties"]["entrypoints"]["properties"]


def test_phase6_to_phase10_schema_artifacts_exist_and_parse() -> None:
    expected = {
        "workflow-v0.1.schema.json": "workflow/v0.1",
        "layout-checks-v0.2.schema.json": "layout-checks/v0.2",
        "real2sim-result-v0.1.schema.json": "real2sim-result/v0.1",
        "cousin-plan-v0.1.schema.json": "cousin-plan/v0.1",
        "suite-spec-v0.2.schema.json": "suite-spec/v0.2",
        "scenario-suite-v0.2.schema.json": "scenario-suite/v0.2",
        "suite-quality-evidence-v0.1.schema.json": "suite-quality-evidence/v0.1",
    }
    for filename, schema_version in expected.items():
        schema_path = REPO_ROOT / "src" / "scenario_forge" / "schemas" / "jsonschema" / filename

        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        assert schema["type"] == "object"
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["properties"]["schema_version"]["const"] == schema_version


def test_phase11_schema_artifacts_exist_and_parse() -> None:
    expected = {
        "phase11-visual-review-v0.1.schema.json": "phase11-visual-review/v0.1",
        "phase11-visual-review-gate-v0.1.schema.json": "phase11-visual-review-gate/v0.1",
        "phase11-eos-task-execution-v0.1.schema.json": "phase11-eos-task-execution/v0.1",
        "phase11-task-execution-gate-v0.1.schema.json": "phase11-task-execution-gate/v0.1",
        "phase11-executed-episode-evidence-v0.1.schema.json": "phase11-executed-episode-evidence/v0.1",
        "phase11-executed-episode-gate-v0.1.schema.json": "phase11-executed-episode-gate/v0.1",
        "phase11-success-predicate-evaluation-v0.1.schema.json": "phase11-success-predicate-evaluation/v0.1",
        "phase11-success-predicate-gate-v0.1.schema.json": "phase11-success-predicate-gate/v0.1",
        "phase11-post-execution-visual-review-v0.1.schema.json": "phase11-post-execution-visual-review/v0.1",
        "phase11-post-execution-visual-review-gate-v0.1.schema.json": "phase11-post-execution-visual-review-gate/v0.1",
        "phase11-release-policy-v0.1.schema.json": "phase11-release-policy/v0.1",
        "phase11-single-task-release-candidate-gate-v0.1.schema.json": "phase11-single-task-release-candidate-gate/v0.1",
        "phase11-small-multi-task-canary-v0.1.schema.json": "phase11-small-multi-task-canary/v0.1",
        "phase11-small-multi-task-canary-gate-v0.1.schema.json": "phase11-small-multi-task-canary-gate/v0.1",
        "phase11-automated-release-evidence-v0.1.schema.json": "phase11-automated-release-evidence/v0.1",
        "phase11-automated-release-gate-v0.1.schema.json": "phase11-automated-release-gate/v0.1",
        "phase11-phase12-readiness-v0.1.schema.json": "phase11-phase12-readiness/v0.1",
        "phase11-phase12-readiness-gate-v0.1.schema.json": "phase11-phase12-readiness-gate/v0.1",
    }
    for filename, schema_version in expected.items():
        schema_path = REPO_ROOT / "src" / "scenario_forge" / "schemas" / "jsonschema" / filename

        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        assert schema["type"] == "object"
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["properties"]["schema_version"]["const"] == schema_version


def test_v03_bimanual_schema_artifacts_validate_exact_contracts() -> None:
    schema_dir = REPO_ROOT / "src/scenario_forge/schemas/jsonschema"
    cases = {
        "scenario-spec-v0.3.schema.json": (
            "scenario-spec/v0.3",
            _v03_scenario(),
        ),
        "scenario-forge-genmanip-runtime-contract-v0.3.schema.json": (
            "scenario-forge-genmanip-runtime-contract/v0.3",
            _v03_runtime_contract(),
        ),
        "task-v0.3.schema.json": ("task/v0.3", _v03_task()),
        "predicates-v0.3.schema.json": (
            "predicates/v0.3",
            {
                "schema_version": "predicates/v0.3",
                "success_predicates": _v03_success()["predicates"],
            },
        ),
    }

    for filename, (schema_version, instance) in cases.items():
        schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        validator.validate(instance)
        assert schema["properties"]["schema_version"]["const"] == schema_version

        invalid = {**instance, "unexpected": True}
        assert any(
            error.validator == "additionalProperties"
            for error in validator.iter_errors(invalid)
        )


def test_v03_success_schemas_reject_v02_tilt_shape_and_parameter_extras() -> None:
    schema_dir = REPO_ROOT / "src/scenario_forge/schemas/jsonschema"
    scenario = _v03_scenario()
    success = _v03_success()
    predicates = list(success["predicates"])  # type: ignore[arg-type]
    old_tilt = {
        "id": "source_tilted",
        "type": "named_frame_tilt_angle_reached",
        "sequence_index": 1,
        "parameters": {
            "object_frame": "source.opening",
            "world_axis": "z",
            "angle_range_deg": [70.0, 80.0],
            "bounds": "inclusive",
            "diagnostic_compatibility_projection": {
                "type": "relative_pose_reached",
                "parameters": {},
            },
        },
    }
    predicates[1] = old_tilt
    scenario["success"] = {**success, "predicates": predicates}
    scenario_schema = json.loads(
        (schema_dir / "scenario-spec-v0.3.schema.json").read_text(encoding="utf-8")
    )

    assert list(Draft202012Validator(scenario_schema).iter_errors(scenario))

    predicates = list(_v03_success()["predicates"])  # type: ignore[arg-type]
    first = dict(predicates[0])
    parameters = dict(first["parameters"])  # type: ignore[arg-type]
    parameters["normal_angle_max_deg"] = 10.0
    first["parameters"] = parameters
    predicates[0] = first
    predicates_document = {
        "schema_version": "predicates/v0.3",
        "success_predicates": predicates,
    }
    predicates_schema = json.loads(
        (schema_dir / "predicates-v0.3.schema.json").read_text(encoding="utf-8")
    )

    assert any(
        error.validator == "additionalProperties"
        for error in Draft202012Validator(predicates_schema).iter_errors(
            predicates_document
        )
    )


def test_v03_success_schemas_enforce_sequence_and_angle_domains() -> None:
    schema_dir = REPO_ROOT / "src/scenario_forge/schemas/jsonschema"
    predicates = list(_v03_success()["predicates"])  # type: ignore[arg-type]
    second = dict(predicates[1])
    second["sequence_index"] = 0
    parameters = dict(second["parameters"])  # type: ignore[arg-type]
    parameters["source_normal_polar_angle_range_deg"] = [70.0, 181.0]
    parameters["source_normal_azimuth_range_deg"] = [-181.0, -85.0]
    second["parameters"] = parameters
    predicates[1] = second
    contract = _v03_runtime_contract()
    contract["success"] = {
        **_v03_success(),
        "predicates": predicates,
    }
    schema = json.loads(
        (
            schema_dir
            / "scenario-forge-genmanip-runtime-contract-v0.3.schema.json"
        ).read_text(encoding="utf-8")
    )
    errors = list(Draft202012Validator(schema).iter_errors(contract))

    assert errors
    assert any(error.validator == "const" for error in errors)
    assert sum(error.validator == "maximum" for error in errors) >= 1
    assert sum(error.validator == "minimum" for error in errors) >= 1


def test_v03_addition_does_not_mutate_v02_wire_schemas() -> None:
    schema_dir = REPO_ROOT / "src/scenario_forge/schemas/jsonschema"
    expected = {
        "scenario-spec-v0.2.schema.json": (
            "77e1ec162c5b6cdbc298ee812798962b47c18b1b412ae0a2535ecef755e9c480"
        ),
        "task-v0.2.schema.json": (
            "a18e5890e4b58237e636d6616f60f30be534a461d923a89c9de8360979d38fd6"
        ),
        "predicates-v0.2.schema.json": (
            "30e3e3755c77aaf2130c30dcf5337f7a84f7e241d7fbea35cc8c75cc803ec18b"
        ),
        "scenario-forge-genmanip-runtime-contract-v0.2.schema.json": (
            "67a4a6862e6bcd11291061172ebf02035b633d5b47d081b8dd4f821028ca203b"
        ),
    }

    assert {
        filename: sha256((schema_dir / filename).read_bytes()).hexdigest()
        for filename in expected
    } == expected

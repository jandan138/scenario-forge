import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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

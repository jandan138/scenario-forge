from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = (
    REPO_ROOT / "configs/task_catalogs/scientific_workbench_phase1.yaml"
)
READINESS_PATH = (
    REPO_ROOT
    / "docs/records/evidence/2026-07-14-scientific-workbench-task-catalog/readiness.yaml"
)
SOURCE_SHA256 = "3b7ebb2592a8dd612f37e0e934aa052284de772fd0e7fb80b7359afa57d82eca"


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_task_catalog_and_readiness_schema_artifacts_exist_and_parse() -> None:
    expected = {
        "task-catalog-v0.1.schema.json": "task-catalog/v0.1",
        "task-readiness-snapshot-v0.1.schema.json": "task-readiness-snapshot/v0.1",
    }
    for filename, schema_version in expected.items():
        path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema" / filename
        schema = json.loads(path.read_text(encoding="utf-8"))

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["properties"]["schema_version"]["const"] == schema_version


def test_pdf_derived_catalog_preserves_the_declared_17_observed_19_ambiguity() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    source = catalog["source"]
    reconciliation = catalog["identity_reconciliation"]
    tasks = catalog["tasks"]

    assert catalog["schema_version"] == "task-catalog/v0.1"
    assert isinstance(source, dict)
    assert source["sha256"] == f"sha256:{SOURCE_SHA256}"
    assert isinstance(reconciliation, dict)
    assert reconciliation == {
        "status": "unresolved",
        "declared_task_count": 17,
        "observed_candidate_row_count": 19,
        "note": "The detailed table contains 1..17 plus 8a and 8b.",
    }
    assert isinstance(tasks, list)
    assert len(tasks) == 19

    task_ids = [task["task_id"] for task in tasks]
    source_ids = [task["source_id"] for task in tasks]
    assert len(task_ids) == len(set(task_ids))
    assert {"8", "8a", "8b"}.issubset(source_ids)


def test_catalog_keeps_task_one_aligned_with_the_golden_bimanual_pour() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    tasks = catalog["tasks"]
    assert isinstance(tasks, list)
    task = next(item for item in tasks if item["source_id"] == "1")

    assert task["task_id"] == "wetlab_nonquant_pour_to_cylinder"
    assert task["level"] == "basic"
    assert task["step_count"] == 5
    assert task["claim_scope"] == "kinematic_proxy"
    assert task["required_asset_roles"] == [
        "erlenmeyer_flask",
        "graduated_cylinder",
    ]
    assert task["atomic_skills"] == ["grasp", "pick", "align", "pour", "place"]


def test_readiness_snapshot_does_not_promote_unverified_tasks_or_interactions() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    readiness = _load_yaml(READINESS_PATH)
    source = readiness["catalog_source"]
    task_statuses = readiness["tasks"]
    asset_statuses = readiness["assets"]

    assert readiness["schema_version"] == "task-readiness-snapshot/v0.1"
    assert isinstance(source, dict)
    assert source["source_sha256"] == f"sha256:{SOURCE_SHA256}"
    assert isinstance(task_statuses, list)
    assert isinstance(asset_statuses, list)

    catalog_tasks = catalog["tasks"]
    assert isinstance(catalog_tasks, list)
    assert {item["task_id"] for item in task_statuses} == {
        item["task_id"] for item in catalog_tasks
    }
    required_roles = {
        role
        for item in catalog_tasks
        for role in item["required_asset_roles"]
    }
    assert required_roles.issubset(
        {item["asset_role"] for item in asset_statuses}
    )

    current = next(item for item in task_statuses if item["task_id"] == "wetlab_nonquant_pour_to_cylinder")
    assert current["compile_status"] == "passed"
    assert current["runtime_reset_status"] == "passed"
    assert current["oracle_status"] == "blocked"
    assert "wrapper" in " ".join(current["blockers"])
    assert "opening-frame" in " ".join(current["blockers"])

    assert all(
        item["compile_status"] != "passed"
        for item in task_statuses
        if item["task_id"] != "wetlab_nonquant_pour_to_cylinder"
    )

    drying_box = next(item for item in asset_statuses if item["asset_role"] == "drying_box")
    assert drying_box["context_package_status"] == "passed"
    assert drying_box["interactive_affordance_status"] == "blocked"
    assert "door" in drying_box["pending_affordances"]
    assert "start_button" in drying_box["pending_affordances"]
    assert "removes colliders" in " ".join(drying_box["blockers"])

    flask = next(item for item in asset_statuses if item["asset_role"] == "erlenmeyer_flask")
    cylinder = next(
        item for item in asset_statuses if item["asset_role"] == "graduated_cylinder"
    )
    assert flask["interactive_affordance_status"] == "blocked"
    assert cylinder["interactive_affordance_status"] == "blocked"

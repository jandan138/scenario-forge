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

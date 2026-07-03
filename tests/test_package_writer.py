from pathlib import Path

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact


def test_write_yaml_artifact_creates_parent_directories(tmp_path: Path) -> None:
    out = tmp_path / "locks" / "asset_lock.yaml"

    written = write_yaml_artifact(out, {"schema_version": "asset-lock/v0.2"})

    assert written == out
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == {
        "schema_version": "asset-lock/v0.2"
    }

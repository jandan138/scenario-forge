from __future__ import annotations

from hashlib import sha256
import importlib.util
from pathlib import Path

import pytest
import yaml

from scenario_forge.assets.external_environment import (
    build_external_environment_intake,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
INTAKE_SCRIPT = REPO_ROOT / "scripts" / "intake_external_environment.py"


def _write_extracted_environment(root: Path) -> Path:
    (root / "Assets" / "desk").mkdir(parents=True)
    (root / "world.usda").write_text(
        '#usda 1.0\ndef Xform "World" {}\n',
        encoding="utf-8",
    )
    (root / "Assets" / "desk" / "desk.usda").write_text(
        '#usda 1.0\ndef Xform "Desk" {}\n',
        encoding="utf-8",
    )
    (root / "limpopo.hdr").write_bytes(b"environment-light")
    return root / "world.usda"


def test_builds_hash_bound_restricted_intake_from_extracted_tree(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "3FO4K5C9JD44"
    source_usd = _write_extracted_environment(source_root)

    intake = build_external_environment_intake(
        asset_id="external_room_3fo4k5c9jd44",
        source_root=source_root,
        source_usd_relative_path="world.usda",
        archive_sha256="a" * 64,
        restricted_provenance_id="restricted/external-room/3FO4K5C9JD44",
        expected_source_sha256=sha256(source_usd.read_bytes()).hexdigest(),
    )

    record = intake.to_mapping()

    assert record["schema_version"] == "scenario-forge-external-environment-intake/v0.1"
    assert record["asset_id"] == "external_room_3fo4k5c9jd44"
    assert record["asset_role"] == "visual_static_environment"
    assert record["license"] == "LicenseRef-Internal-Restricted"
    assert record["redistributable"] is False
    assert record["attribution"] == [
        "Restricted external environment source; redistribution is not authorized."
    ]
    assert record["source"] == {
        "tree_kind": "extracted_archive_tree",
        "tree_sha256": intake.source_tree_sha256,
        "file_count": 3,
        "total_bytes": sum(
            path.stat().st_size for path in source_root.rglob("*") if path.is_file()
        ),
        "usd": "world.usda",
        "usd_sha256": sha256(source_usd.read_bytes()).hexdigest(),
    }
    assert record["archive"] == {"sha256": "a" * 64}
    assert record["provenance"] == {
        "visibility": "restricted",
        "kind": "external_archive",
        "internal_reference": "restricted/external-room/3FO4K5C9JD44",
    }
    serialized = yaml.safe_dump(record, sort_keys=True)
    assert str(source_root) not in serialized
    assert "://" not in serialized
    assert "q-signature" not in serialized


@pytest.mark.parametrize(
    ("asset_id", "source_usd_relative_path", "archive_sha256", "provenance_id"),
    [
        ("external room", "world.usda", "a" * 64, "restricted/source"),
        ("external_lab_room", "world.usda", "a" * 64, "restricted/source"),
        ("external_room", "../world.usda", "a" * 64, "restricted/source"),
        ("external_room", "/world.usda", "a" * 64, "restricted/source"),
        ("external_room", "world.txt", "a" * 64, "restricted/source"),
        ("external_room", "world.usda", "A" * 64, "restricted/source"),
        (
            "external_room",
            "world.usda",
            "a" * 64,
            "https://example.invalid/source?q-signature=secret",
        ),
    ],
)
def test_rejects_unsafe_public_identifiers_or_provenance(
    tmp_path: Path,
    asset_id: str,
    source_usd_relative_path: str,
    archive_sha256: str,
    provenance_id: str,
) -> None:
    source_root = tmp_path / "extracted"
    _write_extracted_environment(source_root)

    with pytest.raises(ValueError):
        build_external_environment_intake(
            asset_id=asset_id,
            source_root=source_root,
            source_usd_relative_path=source_usd_relative_path,
            archive_sha256=archive_sha256,
            restricted_provenance_id=provenance_id,
        )


def test_rejects_source_hash_mismatch_or_source_tree_symlink(tmp_path: Path) -> None:
    source_root = tmp_path / "extracted"
    _write_extracted_environment(source_root)

    with pytest.raises(ValueError, match="source USD hash"):
        build_external_environment_intake(
            asset_id="external_room",
            source_root=source_root,
            source_usd_relative_path="world.usda",
            archive_sha256="a" * 64,
            restricted_provenance_id="restricted/source",
            expected_source_sha256="b" * 64,
        )

    linked_file = source_root / "Assets" / "linked.usda"
    linked_file.symlink_to(source_root / "world.usda")
    with pytest.raises(ValueError, match="symlink"):
        build_external_environment_intake(
            asset_id="external_room",
            source_root=source_root,
            source_usd_relative_path="world.usda",
            archive_sha256="a" * 64,
            restricted_provenance_id="restricted/source",
        )


def test_cli_writes_portable_restricted_record_outside_source_tree(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "extracted"
    source_usd = _write_extracted_environment(source_root)
    output = tmp_path / "intake.yaml"

    module = _load_intake_module()
    assert (
        module.main(
            [
                "--asset-id",
                "external_room",
                "--source-root",
                str(source_root),
                "--source-usd",
                "world.usda",
                "--expected-source-sha256",
                sha256(source_usd.read_bytes()).hexdigest(),
                "--archive-sha256",
                "a" * 64,
                "--restricted-provenance-id",
                "restricted/external-room-source",
                "--out",
                str(output),
            ]
        )
        == 0
    )

    record = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert record["source"]["usd"] == "world.usda"
    assert str(source_root) not in output.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="outside source_root"):
        module.main(
            [
                "--asset-id",
                "external_room",
                "--source-root",
                str(source_root),
                "--source-usd",
                "world.usda",
                "--archive-sha256",
                "a" * 64,
                "--restricted-provenance-id",
                "restricted/external-room-source",
                "--out",
                str(source_root / "intake.yaml"),
            ]
        )


def _load_intake_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "intake_external_environment",
        INTAKE_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

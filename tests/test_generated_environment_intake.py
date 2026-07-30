from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scenario_forge.adapters.generated_environment import (
    GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION,
    build_generated_environment_intake,
)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_delivery(root: Path) -> None:
    (root / "textures").mkdir(parents=True)
    (root / "provenance").mkdir()
    (root / "room_source.usdc").write_bytes(b"PXR-USDC")
    (root / "room.blend").write_bytes(b"BLENDER")
    (root / "textures" / "floor.png").write_bytes(b"PNG")
    (root / "provenance" / "render_output.py").write_text(
        "print('room')\n",
        encoding="utf-8",
    )
    assets = {
        "room_source_usdc": {
            "path": "room_source.usdc",
            "sha256": _digest(root / "room_source.usdc"),
        },
        "room_blend": {
            "path": "room.blend",
            "sha256": _digest(root / "room.blend"),
        },
        "textures": [
            {
                "path": "textures/floor.png",
                "sha256": _digest(root / "textures" / "floor.png"),
            }
        ],
        "provenance_source_script": {
            "path": "provenance/render_output.py",
            "sha256": _digest(root / "provenance" / "render_output.py"),
        },
    }
    manifest = {
        "schema_version": "room-source-v1",
        "run_id": "run_example4",
        "code_as_room": {"commit": "a" * 40},
        "units": {"meters_per_unit": 1.0},
        "assets": assets,
        "usd_export_parameters": {
            "root_prim_path": "/Room",
            "export_global_up_selection": "Z",
        },
        "usd_asset_paths": ["./textures/floor.png"],
        "zones": {
            "North Workbench Zone": {"zone_root": "Zone__North_Workbench"},
            "East Wet-Lab Zone": {"zone_root": "Zone__East_Wet_Lab"},
        },
    }
    (root / "source_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_generated_environment_intake_hash_binds_declared_delivery(
    tmp_path: Path,
) -> None:
    _write_delivery(tmp_path)
    (tmp_path / "room.blend1").write_bytes(b"UNDECLARED BACKUP")

    intake = build_generated_environment_intake(
        asset_id="scientific_environment_code_room_example4_v1",
        delivery_root=tmp_path,
    ).to_mapping()

    assert (
        intake["schema_version"]
        == GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION
    )
    assert intake["asset_role"] == "visual_static_environment"
    assert intake["license"] == "LicenseRef-Internal-Generated"
    assert intake["redistributable"] is False
    assert intake["source"]["usd"] == "room_source.usdc"
    assert intake["source"]["default_prim"] == "/Room"
    assert intake["source"]["up_axis"] == "Z"
    assert intake["source"]["meters_per_unit"] == 1.0
    assert intake["source"]["zone_roots"] == [
        "/Room/Zone__East_Wet_Lab",
        "/Room/Zone__North_Workbench",
    ]
    assert intake["producer"]["repo"] == "Code-as-Room"
    assert intake["producer"]["revision"] == "a" * 40
    assert intake["warnings"]["unlisted_files"] == ["room.blend1"]
    assert "/tmp/" not in json.dumps(intake)


def test_generated_environment_intake_rejects_tampered_declared_asset(
    tmp_path: Path,
) -> None:
    _write_delivery(tmp_path)
    (tmp_path / "textures" / "floor.png").write_bytes(b"TAMPERED")

    with pytest.raises(ValueError, match="SHA-256"):
        build_generated_environment_intake(
            asset_id="scientific_environment_code_room_example4_v1",
            delivery_root=tmp_path,
        )


def test_generated_environment_intake_rejects_nonlocal_usd_dependency(
    tmp_path: Path,
) -> None:
    _write_delivery(tmp_path)
    manifest_path = tmp_path / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["usd_asset_paths"] = ["/absolute/floor.png"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="package-relative"):
        build_generated_environment_intake(
            asset_id="scientific_environment_code_room_example4_v1",
            delivery_root=tmp_path,
        )

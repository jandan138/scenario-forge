from __future__ import annotations

import json
from pathlib import Path
import zipfile

from scenario_forge.artifacts.asset_handoff import build_asset_handoff_archive


def _package(root: Path, name: str) -> Path:
    package = root / name
    (package / "evidence").mkdir(parents=True)
    (package / "deps/mdl").mkdir(parents=True)
    (package / "asset.usd").write_text(
        '#usda 1.0\n(def Xform "World")\n', encoding="utf-8"
    )
    (package / "deps/mdl/OmniGlass.mdl").write_text("mdl 1.6;\n", encoding="utf-8")
    (package / "evidence/manifest.json").write_text(
        json.dumps(
            {
                "package_id": name,
                "asset_id": name,
                "overall_status": "pass",
                "blocked_reasons": [],
                "entrypoints": {"root_usd": "asset.usd", "asset_entry_prim": "/World"},
                "runtime_evidence": {"status": "pass"},
                "visual_material_profile": {
                    "status": "pass",
                    "schema_version": "aan.visual_material_profile.v2",
                },
            }
        ),
        encoding="utf-8",
    )
    (package / "evidence/visual_material_only_audit.json").write_text(
        json.dumps({"status": "pass", "checks": {"physics_unchanged": True}}),
        encoding="utf-8",
    )
    return package


def test_asset_handoff_archive_preserves_independent_packages(tmp_path: Path) -> None:
    first = _package(tmp_path, "graduated_cylinder_glass_v1")
    second = _package(tmp_path, "beaker_glass_v1")

    result = build_asset_handoff_archive(
        archive_id="glass_material_v1",
        packages=[first, second],
        output_dir=tmp_path / "handoff",
    )

    manifest = json.loads((result.root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "scenario-forge-asset-handoff/v0.1"
    assert manifest["asset_count"] == 2
    assert manifest["task_packages_modified"] is False
    assert (result.root / "packages/beaker_glass_v1/asset.usd").is_file()
    assert result.zip_path.is_file()
    with zipfile.ZipFile(result.zip_path) as archive:
        assert "glass_material_v1/README_CN.md" in archive.namelist()
        assert "glass_material_v1/packages/graduated_cylinder_glass_v1/asset.usd" in archive.namelist()


def test_asset_handoff_archive_rejects_non_admitted_visual_package(tmp_path: Path) -> None:
    package = _package(tmp_path, "bad")
    audit = package / "evidence/visual_material_only_audit.json"
    audit.write_text(json.dumps({"status": "blocked"}), encoding="utf-8")

    try:
        build_asset_handoff_archive(
            archive_id="bad_bundle", packages=[package], output_dir=tmp_path / "handoff"
        )
    except ValueError as error:
        assert "visual material-only audit" in str(error)
    else:
        raise AssertionError("blocked package must not be bundled")

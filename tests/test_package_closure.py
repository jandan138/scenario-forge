from __future__ import annotations

from pathlib import Path

from scenario_forge.artifacts.package_closure import audit_package_dependency_closure


def test_dependency_closure_rejects_absolute_usd_and_remote_texture_refs(tmp_path: Path) -> None:
    scene = tmp_path / "scene/main.usda"
    scene.parent.mkdir()
    scene.write_text('@../materials.mdl@\n@/outside/room.usd@\n', encoding="utf-8")
    (tmp_path / "materials.mdl").write_text(
        'texture_2d("omniverse://server/texture.png")', encoding="utf-8"
    )

    audit = audit_package_dependency_closure(tmp_path)

    assert audit["status"] == "failed"
    assert audit["unsafe_references"] == [
        {"file": "materials.mdl", "reference": "omniverse://server/texture.png"},
        {"file": "scene/main.usda", "reference": "/outside/room.usd"},
    ]


def test_dependency_closure_accepts_existing_package_relative_references(tmp_path: Path) -> None:
    scene = tmp_path / "scene/main.usda"
    asset = tmp_path / "assets/object.usda"
    texture = tmp_path / "textures/albedo.png"
    scene.parent.mkdir()
    asset.parent.mkdir()
    texture.parent.mkdir()
    scene.write_text('@../assets/object.usda@\n', encoding="utf-8")
    asset.write_text('#usda 1.0\n', encoding="utf-8")
    texture.write_bytes(b"texture")
    (tmp_path / "materials.mdl").write_text(
        'texture_2d("textures/albedo.png")', encoding="utf-8"
    )

    audit = audit_package_dependency_closure(tmp_path)

    assert audit["status"] == "pass"
    assert audit["unsafe_references"] == []
    assert audit["missing_references"] == []


def test_dependency_closure_ignores_non_path_bytes_in_binary_usdc(tmp_path: Path) -> None:
    scene = tmp_path / "scene/main.usdc"
    scene.parent.mkdir()
    scene.write_bytes(b"binary-data@\x01#\x02A\x01#\x02B\x01#\x02C@more-data")

    audit = audit_package_dependency_closure(tmp_path)

    assert audit["status"] == "pass"
    assert audit["unsafe_references"] == []
    assert audit["missing_references"] == []


def test_dependency_closure_ignores_unreachable_provenance_usd(tmp_path: Path) -> None:
    scene = tmp_path / "scene/main.usda"
    asset = tmp_path / "assets/active.usda"
    archive = tmp_path / "assets/deps/usd/source_root.usd"
    scene.parent.mkdir()
    asset.parent.mkdir()
    archive.parent.mkdir(parents=True)
    scene.write_text('@../assets/active.usda@\n', encoding="utf-8")
    asset.write_text('#usda 1.0\n', encoding="utf-8")
    archive.write_text('@/outside/legacy.mdl@\n', encoding="utf-8")

    audit = audit_package_dependency_closure(tmp_path)

    assert audit["status"] == "pass"
    assert audit["unsafe_references"] == []
    assert audit["scanned_files"] == ["assets/active.usda", "scene/main.usda"]

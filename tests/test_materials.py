from pathlib import Path

from scenario_forge.assets.materials import audit_mdl_texture_closure


def test_material_audit_detects_binary_usd_mdl_dependency_without_asset_delimiters(
    tmp_path: Path,
) -> None:
    usd_path = tmp_path / "object.usd"
    usd_path.write_bytes(b"\x00token\x00variability\x00gltf/pbr.mdl\r\x00texture.png")

    audit = audit_mdl_texture_closure(tmp_path)

    assert audit["status"] == "failed"
    assert audit["missing_material_ref_count"] == 1
    assert audit["missing_material_refs"] == [
        {
            "usd": "object.usd",
            "material": "gltf/pbr.mdl",
            "resolved_path": "gltf/pbr.mdl",
        }
    ]

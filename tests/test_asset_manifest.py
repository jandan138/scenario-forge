from pathlib import Path

from scenario_forge.assets.manifest import AssetRef, collect_asset_refs


def test_collect_asset_refs_preserves_license_and_content_address() -> None:
    refs = collect_asset_refs(
        [
            AssetRef(
                asset_id="container_beaker_small",
                uri="hf://example/assets/beaker.usd",
                role="rigid_object",
                license="CC-BY-4.0",
                sha256="0" * 64,
            )
        ]
    )

    assert refs["container_beaker_small"].uri == "hf://example/assets/beaker.usd"
    assert refs["container_beaker_small"].license == "CC-BY-4.0"
    assert refs["container_beaker_small"].sha256 == "0" * 64


def test_asset_ref_rejects_directory_escape_for_local_refs(tmp_path: Path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    ref = AssetRef(
        asset_id="bad",
        uri="../outside.usd",
        role="rigid_object",
        license="internal-review",
    )

    assert ref.resolve_local(root) is None

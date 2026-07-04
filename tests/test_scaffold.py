from pathlib import Path

from scenario_forge.scaffold import scaffold_starter_package


def test_scaffold_starter_assets_define_default_prims(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "starter")

    object_usd = (package_dir / "assets" / "objects" / "starter_rigid_object" / "model.usd").read_text(
        encoding="utf-8"
    )
    marker_usd = (package_dir / "assets" / "markers" / "starter_target_marker" / "model.usd").read_text(
        encoding="utf-8"
    )

    assert 'defaultPrim = "starter_rigid_object"' in object_usd
    assert 'defaultPrim = "starter_target_marker"' in marker_usd

from pathlib import Path

import pytest

from scenario_forge.assets.lock import generate_asset_lock
from tests.test_asset_lock import make_asset_manifest_package


def test_generate_asset_lock_keeps_legacy_output_name_default(tmp_path: Path) -> None:
    package_root = tmp_path / "legacy-output-name"
    make_asset_manifest_package(package_root)

    lock = generate_asset_lock(package_root)

    assert lock.lock_id == "legacy-output-name_asset_lock"


def test_generate_asset_lock_accepts_stable_caller_owned_identity(tmp_path: Path) -> None:
    package_root = tmp_path / "arbitrary-build-name"
    make_asset_manifest_package(package_root)

    lock = generate_asset_lock(
        package_root,
        lock_id="scientific_workbench_bimanual_pour_asset_lock",
    )

    assert lock.lock_id == "scientific_workbench_bimanual_pour_asset_lock"


def test_generate_asset_lock_rejects_empty_explicit_identity(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path)

    with pytest.raises(ValueError, match="lock_id"):
        generate_asset_lock(tmp_path, lock_id="")

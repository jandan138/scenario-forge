import subprocess
import sys
import os
from hashlib import sha256
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "scenario_forge.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def make_asset_package_on_disk(root: Path) -> Path:
    package_dir = root / "asset_pkg"
    model = package_dir / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd"
    model.parent.mkdir(parents=True)
    model.write_text("#usda 1.0\n", encoding="utf-8")
    digest = sha256(model.read_bytes()).hexdigest()
    (package_dir / "assets" / "asset_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "asset-manifest/v0.2",
                "assets": [
                    {
                        "asset_id": "sample_bottle_50ml_v1",
                        "role": "manipulated_object",
                        "asset_type": "bottle",
                        "canonical_usd": "assets/objects/sample_bottle_50ml_v1/model.usd",
                        "license": "CC-BY-4.0",
                        "sha256": f"sha256:{digest}",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return package_dir


def add_v01_manifest_with_scene(package_dir: Path) -> None:
    (package_dir / "scene.usda").write_text("#usda 1.0\n", encoding="utf-8")
    (package_dir / "scene_instances.yaml").write_text("instances: []\n", encoding="utf-8")
    (package_dir / "task.yaml").write_text("task_id: smoke\n", encoding="utf-8")
    (package_dir / "robot.yaml").write_text("robot_id: smoke\n", encoding="utf-8")
    (package_dir / "validation_report.yaml").write_text("status: draft\n", encoding="utf-8")
    (package_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-package/v0.1",
                "scenario_id": "asset_lock_smoke",
                "exports": ["ebench"],
                "files": {
                    "scene": "scene.usda",
                    "instances": "scene_instances.yaml",
                    "task": "task.yaml",
                    "robot": "robot.yaml",
                    "validation_report": "validation_report.yaml",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_cli_scaffold_creates_checkable_starter_package(tmp_path: Path) -> None:
    out_dir = tmp_path / "starter"

    scaffold = run_cli("package", "scaffold", "--out", str(out_dir), cwd=tmp_path)
    check = run_cli("package", "check", str(out_dir), cwd=tmp_path)

    assert scaffold.returncode == 0, scaffold.stderr
    assert check.returncode == 0, check.stderr
    assert (out_dir / "manifest.yaml").exists()
    assert "Package OK" in check.stdout


def test_cli_check_returns_nonzero_for_invalid_package(tmp_path: Path) -> None:
    package_dir = tmp_path / "broken"
    package_dir.mkdir()
    (package_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-package/v0.1",
                "scenario_id": "broken",
                "exports": ["ebench"],
                "files": {"scene": "missing.usd"},
            }
        ),
        encoding="utf-8",
    )

    result = run_cli("package", "check", str(package_dir), cwd=tmp_path)

    assert result.returncode == 1
    assert "Missing referenced file: missing.usd" in result.stdout


def test_cli_package_check_require_asset_lock_returns_nonzero_when_missing(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "starter"
    scaffold = run_cli("package", "scaffold", "--out", str(package_dir), cwd=tmp_path)

    result = run_cli("package", "check", str(package_dir), "--require-asset-lock", cwd=tmp_path)

    assert scaffold.returncode == 0, scaffold.stderr
    assert result.returncode == 1
    assert "Missing asset lock: locks/asset_lock.yaml" in result.stdout


def test_cli_assets_lock_writes_asset_lock(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)

    result = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (package_dir / "locks" / "asset_lock.yaml").exists()
    assert "Asset lock written" in result.stdout


def test_cli_assets_check_reports_checksum_mismatch(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    lock = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)
    (package_dir / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd").write_text(
        "changed\n",
        encoding="utf-8",
    )

    result = run_cli("assets", "check", str(package_dir), cwd=tmp_path)

    assert lock.returncode == 0, lock.stderr
    assert result.returncode == 1
    assert "Checksum mismatch for asset sample_bottle_50ml_v1" in result.stdout


def test_cli_assets_lock_reports_missing_license(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    manifest = yaml.safe_load(
        (package_dir / "assets" / "asset_manifest.yaml").read_text(encoding="utf-8")
    )
    del manifest["assets"][0]["license"]
    (package_dir / "assets" / "asset_manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    result = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    assert result.returncode == 1
    assert "Missing license for asset sample_bottle_50ml_v1" in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_assets_check_uses_manifest_scene_for_usd_reference_check(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    add_v01_manifest_with_scene(package_dir)
    extra = package_dir / "assets" / "objects" / "extra" / "model.usd"
    extra.parent.mkdir(parents=True)
    extra.write_text("#usda 1.0\n", encoding="utf-8")
    (package_dir / "scene.usda").write_text(
        '#usda 1.0\nrel references = @assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )
    lock = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    result = run_cli("assets", "check", str(package_dir), cwd=tmp_path)

    assert lock.returncode == 0, lock.stderr
    assert result.returncode == 1
    assert "USD reference is not locked: assets/objects/extra/model.usd" in result.stdout

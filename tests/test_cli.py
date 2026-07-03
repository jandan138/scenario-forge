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


def make_scene_compile_package(root: Path) -> Path:
    package_dir = root / "scene_pkg"
    model = package_dir / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd"
    model.parent.mkdir(parents=True)
    model.write_text("#usda 1.0\n", encoding="utf-8")
    digest = sha256(model.read_bytes()).hexdigest()
    (package_dir / "locks").mkdir(parents=True)
    (package_dir / "locks" / "asset_lock.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "asset-lock/v0.2",
                "lock_id": "scene_pkg_asset_lock",
                "created_by": "scenario-forge",
                "assets": {
                    "sample_bottle_50ml_v1": {
                        "source_kind": "package_local",
                        "source_uri": "assets/objects/sample_bottle_50ml_v1/model.usd",
                        "resolved_path": "assets/objects/sample_bottle_50ml_v1/model.usd",
                        "content_sha256": f"sha256:{digest}",
                        "license": "CC-BY-4.0",
                        "resolver_version": "scenario-forge/test",
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "scene").mkdir()
    (package_dir / "scene" / "instances.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scene-instances/v0.2",
                "instances": [
                    {
                        "id": "object_001",
                        "asset_id": "sample_bottle_50ml_v1",
                        "role": "manipulated_object",
                        "pose": {"xyz": [0.45, 0.0, 0.92], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                        "semantic_tags": ["bottle", "pickable"],
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


def add_v02_manifest_with_scene(package_dir: Path) -> None:
    (package_dir / "scene").mkdir(parents=True, exist_ok=True)
    (package_dir / "task").mkdir(exist_ok=True)
    (package_dir / "robot").mkdir(exist_ok=True)
    (package_dir / "metrics").mkdir(exist_ok=True)
    (package_dir / "evidence").mkdir(exist_ok=True)
    (package_dir / "provenance").mkdir(exist_ok=True)
    (package_dir / "scene" / "main.usda").write_text("#usda 1.0\n", encoding="utf-8")
    (package_dir / "generation_plan.yaml").write_text(
        "schema_version: scenario-generation-plan/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "scene" / "instances.yaml").write_text(
        "schema_version: scene-instances/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "task" / "task.yaml").write_text("schema_version: task/v0.2\n", encoding="utf-8")
    (package_dir / "robot" / "robot.yaml").write_text(
        "schema_version: robot/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "metrics" / "metrics.yaml").write_text(
        "schema_version: metrics/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "evidence" / "validation_report.yaml").write_text(
        "schema_version: validation-report/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "provenance" / "provenance.yaml").write_text(
        "schema_version: provenance/v0.2\n",
        encoding="utf-8",
    )
    (package_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-package/v0.2",
                "package_id": "asset_lock_smoke",
                "scenario_domain": "scientific_workbench",
                "package_mode": "fat",
                "targets": ["ebench"],
                "entrypoints": {
                    "generation_plan": "generation_plan.yaml",
                    "scene_usd": "scene/main.usda",
                    "scene_instances": "scene/instances.yaml",
                    "task": "task/task.yaml",
                    "robot": "robot/robot.yaml",
                    "metrics": "metrics/metrics.yaml",
                },
                "assets": {
                    "manifest": "assets/asset_manifest.yaml",
                    "lock": "locks/asset_lock.yaml",
                },
                "validation": {
                    "report": "evidence/validation_report.yaml",
                    "minimum_required_level": "adapter_static_validated",
                },
                "provenance": {
                    "summary": "provenance/provenance.yaml",
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
    manifest = yaml.safe_load((out_dir / "manifest.yaml").read_text(encoding="utf-8"))

    assert scaffold.returncode == 0, scaffold.stderr
    assert check.returncode == 0, check.stdout + check.stderr
    assert (out_dir / "manifest.yaml").exists()
    assert manifest["schema_version"] == "scenario-package/v0.2"
    assert manifest["entrypoints"]["scene_usd"] == "scene/main.usda"
    assert (out_dir / "locks" / "asset_lock.yaml").exists()
    assert "@../assets/" in (out_dir / "scene" / "main.usda").read_text(encoding="utf-8")
    assert "Package OK" in check.stdout


def test_cli_scene_compile_writes_usda_for_locked_instances(tmp_path: Path) -> None:
    package_dir = make_scene_compile_package(tmp_path)

    result = run_cli(
        "scene",
        "compile",
        "--instances",
        str(package_dir / "scene" / "instances.yaml"),
        "--asset-lock",
        str(package_dir / "locks" / "asset_lock.yaml"),
        "--out",
        str(package_dir / "scene" / "main.usda"),
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Scene written:" in result.stdout
    assert 'def Xform "object_001"' in (package_dir / "scene" / "main.usda").read_text(
        encoding="utf-8"
    )


def test_cli_task_compile_writes_pick_place_artifacts(tmp_path: Path) -> None:
    package_dir = tmp_path / "starter"
    scaffold = run_cli("package", "scaffold", "--out", str(package_dir), cwd=tmp_path)

    result = run_cli(
        "task",
        "compile",
        "--package",
        str(package_dir),
        "--family",
        "pick_place",
        cwd=tmp_path,
    )
    metrics = yaml.safe_load((package_dir / "metrics" / "metrics.yaml").read_text(encoding="utf-8"))

    assert scaffold.returncode == 0, scaffold.stderr
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Task artifacts written:" in result.stdout
    assert metrics["metrics"][0]["role"] == "primary_success"
    assert metrics["metrics"][0]["adapter_hints"]["ebench"]["success_metric"] == "task_success"


def test_cli_export_ebench_writes_package_adapter_artifacts(tmp_path: Path) -> None:
    package_dir = tmp_path / "starter"
    scaffold = run_cli("package", "scaffold", "--out", str(package_dir), cwd=tmp_path)

    result = run_cli("export", "ebench", "--package", str(package_dir), cwd=tmp_path)

    assert scaffold.returncode == 0, scaffold.stderr
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EBench package export written:" in result.stdout
    assert (package_dir / "adapters" / "ebench" / "package.yaml").exists()
    assert (package_dir / "adapters" / "ebench" / "adapter_report.yaml").exists()


def test_cli_export_ebench_writes_suite_task_index(tmp_path: Path) -> None:
    package_dir = tmp_path / "starter"
    suite_dir = tmp_path / "suite"
    suite_dir.mkdir()
    scaffold = run_cli("package", "scaffold", "--out", str(package_dir), cwd=tmp_path)
    package_export = run_cli("export", "ebench", "--package", str(package_dir), cwd=tmp_path)
    (suite_dir / "suite_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-suite/v0.1",
                "suite_id": "starter_suite",
                "packages": [
                    {
                        "package_id": "tabletop_pick_place_starter",
                        "path": str(package_dir),
                        "split": "smoke",
                        "difficulty": "easy",
                        "task_family": "pick_place",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = run_cli("export", "ebench", "--suite", str(suite_dir), cwd=tmp_path)
    task_index = yaml.safe_load(
        (suite_dir / "adapters" / "ebench" / "task_index.yaml").read_text(encoding="utf-8")
    )

    assert scaffold.returncode == 0, scaffold.stderr
    assert package_export.returncode == 0, package_export.stdout + package_export.stderr
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EBench suite export written:" in result.stdout
    assert task_index["tasks"][0]["package_id"] == "tabletop_pick_place_starter"
    assert task_index["tasks"][0]["split"] == "smoke"


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
    package_dir.mkdir()
    add_v01_manifest_with_scene(package_dir)

    result = run_cli("package", "check", str(package_dir), "--require-asset-lock", cwd=tmp_path)

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


def test_cli_assets_check_uses_v02_manifest_scene_for_usd_reference_check(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    add_v02_manifest_with_scene(package_dir)
    extra = package_dir / "assets" / "objects" / "extra" / "model.usd"
    extra.parent.mkdir(parents=True)
    extra.write_text("#usda 1.0\n", encoding="utf-8")
    (package_dir / "scene" / "main.usda").write_text(
        '#usda 1.0\nrel references = @../assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )
    lock = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    result = run_cli("assets", "check", str(package_dir), cwd=tmp_path)

    assert lock.returncode == 0, lock.stderr
    assert result.returncode == 1
    assert "USD reference is not locked: assets/objects/extra/model.usd" in result.stdout

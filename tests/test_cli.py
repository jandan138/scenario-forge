import subprocess
import sys
import os
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

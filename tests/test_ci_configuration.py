from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_ci_installs_pinned_openusd_and_runs_portable_gate() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'usd = [\n  "usd-core==26.5",\n]' in project
    assert 'python -m pip install -e ".[dev,usd]"' in workflow
    assert "from pxr import Usd" in workflow
    assert "make ci-check" in workflow
    assert "make check" not in workflow


def test_makefile_keeps_full_local_gate_and_adds_portable_ci_gate() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'test-ci:\n\t$(CHECK_PYTHON) -m pytest -q -m "not local_artifacts"' in makefile
    assert "check: test lint package-smoke phase10x-smoke diff-check" in makefile
    assert "ci-check: test-ci lint package-smoke phase10x-smoke diff-check" in makefile


def test_local_artifact_marker_is_registered_and_documented() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    docs = (ROOT / "docs/operations/development-checks.md").read_text(
        encoding="utf-8"
    )

    assert "local_artifacts:" in project
    assert "make ci-check" in docs
    assert "python -m pytest -q -m local_artifacts" in docs

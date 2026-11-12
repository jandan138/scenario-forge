"""Skip tests that need the paper tree when it is not in the published repo."""

from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKIP_REASON = "Paper sources are withheld from the published repository."


def paper_sources_published() -> bool:
    """Return whether ``paper/`` is present and not ignored."""
    if not (ROOT / "paper").exists():
        return False
    result = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", "--", "paper"],
        check=False,
        capture_output=True,
    )
    return result.returncode != 0


def skip_unless_paper_published() -> None:
    if not paper_sources_published():
        pytest.skip(SKIP_REASON, allow_module_level=True)


paper_test = pytest.mark.skipif(not paper_sources_published(), reason=SKIP_REASON)

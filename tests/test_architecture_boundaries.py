from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PURE_MODULE_ROOTS = (
    REPO_ROOT / "src" / "scenario_forge" / "core",
    REPO_ROOT / "src" / "scenario_forge" / "schemas",
    REPO_ROOT / "src" / "scenario_forge" / "generation",
    REPO_ROOT / "src" / "scenario_forge" / "assets",
    REPO_ROOT / "src" / "scenario_forge" / "artifacts",
    REPO_ROOT / "src" / "scenario_forge" / "evaluation",
)
FORBIDDEN_IMPORT_MARKERS = (
    "import pxr",
    "from pxr",
    "import omni",
    "from omni",
    "import isaacsim",
    "from isaacsim",
    "import omniisaacgymenvs",
    "from omniisaacgymenvs",
)


def test_pure_package_layers_do_not_import_heavy_simulator_stacks() -> None:
    violations: list[str] = []
    for root in PURE_MODULE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_IMPORT_MARKERS:
                if marker in source:
                    violations.append(f"{path.relative_to(REPO_ROOT)} contains {marker!r}")

    assert violations == []

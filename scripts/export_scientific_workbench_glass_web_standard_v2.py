#!/usr/bin/env python3
"""Export the webpage-standard glass handoff with the cylinder connector fix."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.artifacts.asset_handoff import build_asset_handoff_archive  # noqa: E402


SOURCE_ROOT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_glass_web_standard_20260819/packages"
)
PACKAGES = [
    SOURCE_ROOT / "graduated_cylinder_250ml_glass_web_standard_v2",
    SOURCE_ROOT / "beaker_325ml_glass_web_standard_v1",
    SOURCE_ROOT / "flat_bottom_flask_250ml_29_42_glass_web_standard_v1",
    SOURCE_ROOT / "beaker_dynamic_glass_web_standard_v1",
    SOURCE_ROOT / "reagent_bottle_90x55_original_simready",
    SOURCE_ROOT / "erlenmeyer_flask_250ml_90x35_original_simready",
]
ARCHIVE_ID = "scientific_workbench_glass_web_standard_v2"
OUTPUT_ROOT = (
    REPO_ROOT / "outputs/scientific_workbench_glass_web_standard_v2_20260819/handoff"
)


def main() -> int:
    archive = build_asset_handoff_archive(
        archive_id=ARCHIVE_ID,
        packages=PACKAGES,
        output_dir=OUTPUT_ROOT,
    )
    print(archive.zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

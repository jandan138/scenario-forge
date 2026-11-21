"""M2 v0.3 8-task full-family deformable OpenUSD package builder and remediation API."""

from .localizer_v03 import (
    create_parametric_fixture_usd,
    localize_v03_deformable_asset,
)
from .package_builder_v03 import (
    V03_TASK_SPECS,
    DeformableV03PackageResult,
    build_deformable_v03_packages,
    build_v03_task_package,
)
from .remediation_v03 import apply_scene_remediation

__all__ = [
    "V03_TASK_SPECS",
    "DeformableV03PackageResult",
    "apply_scene_remediation",
    "build_deformable_v03_packages",
    "build_v03_task_package",
    "create_parametric_fixture_usd",
    "localize_v03_deformable_asset",
]


from __future__ import annotations

from collections import Counter
from typing import Any


def suite_coverage_yaml(packages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "suite-coverage/v0.1",
        "package_count": len(packages),
        "task_families": dict(Counter(str(item["task_family"]) for item in packages)),
        "difficulties": dict(Counter(str(item["difficulty"]) for item in packages)),
        "splits": dict(Counter(str(item["split"]) for item in packages)),
    }

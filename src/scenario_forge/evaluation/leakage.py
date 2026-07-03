from __future__ import annotations

from collections import defaultdict
from typing import Any


def split_leakage_package_ids(packages: list[dict[str, Any]]) -> list[str]:
    splits_by_package: dict[str, set[str]] = defaultdict(set)
    for item in packages:
        splits_by_package[str(item.get("package_id", ""))].add(str(item.get("split", "default")))
    return sorted(package_id for package_id, splits in splits_by_package.items() if len(splits) > 1)

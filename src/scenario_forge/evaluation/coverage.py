from __future__ import annotations

from collections import Counter
from typing import Any


def count_by_key(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(item.get(key, "unspecified")) for item in items))

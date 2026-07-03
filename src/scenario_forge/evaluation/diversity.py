from __future__ import annotations


def duplicate_rate(values: list[str]) -> float:
    if not values:
        return 0.0
    duplicate_count = len(values) - len(set(values))
    return round(duplicate_count / len(values), 4)

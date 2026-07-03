from __future__ import annotations


def expand_distribution(distribution: dict[str, int], total: int) -> tuple[str, ...]:
    values: list[str] = []
    for key, count in distribution.items():
        values.extend([key] * count)
    if not values:
        raise ValueError("distribution must not be empty")
    index = 0
    while len(values) < total:
        values.append(values[index % len(values)])
        index += 1
    return tuple(values[:total])

from __future__ import annotations

from typing import Any

from scenario_forge.evaluation.coverage import count_by_key


def difficulty_distribution(packages: list[dict[str, Any]]) -> dict[str, int]:
    return count_by_key(packages, "difficulty")

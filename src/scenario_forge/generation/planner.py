from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationPlan:
    scenario_id: str
    seed: int
    target_exports: tuple[str, ...]

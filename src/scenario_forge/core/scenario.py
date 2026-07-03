from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioPackageRef:
    scenario_id: str
    schema_version: str
    exports: tuple[str, ...]

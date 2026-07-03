from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricRef:
    metric_id: str
    family: str
    predicate: str

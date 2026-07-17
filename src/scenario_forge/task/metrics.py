from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def build_primary_success_metric(object_instance_id: str, target_zone_id: str) -> dict[str, Any]:
    return {
        "id": "task_success",
        "type": "predicate_satisfaction",
        "role": "primary_success",
        "predicate": "object_in_zone",
        "object": object_instance_id,
        "zone": target_zone_id,
        "adapter_hints": {
            "ebench": {
                "success_metric": "task_success",
                "predicate": "object_in_zone",
                "object": object_instance_id,
                "zone": target_zone_id,
            }
        },
    }


def find_primary_success_metric(metrics_path: str | Path) -> dict[str, Any] | None:
    path = Path(metrics_path)
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    raw_metrics = data.get("metrics")
    if not isinstance(raw_metrics, list):
        return None
    for metric in raw_metrics:
        if isinstance(metric, dict) and metric.get("role") == "primary_success":
            return metric
    aggregation = data.get("aggregation")
    if isinstance(aggregation, dict):
        primary_id = aggregation.get("primary_metric_id")
        if isinstance(primary_id, str):
            for metric in raw_metrics:
                if isinstance(metric, dict) and metric.get("id") == primary_id:
                    return metric
    return None

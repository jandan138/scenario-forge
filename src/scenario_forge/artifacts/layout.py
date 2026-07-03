from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageLayout:
    manifest: str = "manifest.yaml"
    scene: str = "scene.usda"
    instances: str = "scene_instances.yaml"
    task: str = "task.yaml"
    robot: str = "robot.yaml"
    validation_report: str = "validation_report.yaml"

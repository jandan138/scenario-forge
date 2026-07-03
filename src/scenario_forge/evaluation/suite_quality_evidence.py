from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.evaluation.coverage import count_by_key
from scenario_forge.evaluation.difficulty import difficulty_distribution
from scenario_forge.evaluation.diversity import duplicate_rate
from scenario_forge.evaluation.leakage import split_leakage_package_ids
from scenario_forge.evaluation.stability import asset_completeness


class SuiteQualityEvidenceError(ValueError):
    """Raised when suite quality evidence cannot be generated."""


@dataclass(frozen=True)
class SuiteQualityEvidenceResult:
    suite_root: Path
    overall_status: str
    evidence_path: Path


def generate_suite_quality_evidence(suite_dir: str | Path) -> SuiteQualityEvidenceResult:
    suite_root = Path(suite_dir)
    manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    packages = _packages(manifest)
    package_paths = [Path(str(item["path"])) for item in packages]
    instructions = [_task_instruction(path) for path in package_paths]
    scene_fingerprints = [_scene_fingerprint(path) for path in package_paths]
    duplicate_instruction_rate = duplicate_rate(instructions)
    duplicate_scene_rate = duplicate_rate(scene_fingerprints)
    leaked_ids = split_leakage_package_ids(packages)
    assets = asset_completeness(package_paths)
    findings = _findings(duplicate_scene_rate, duplicate_instruction_rate, leaked_ids, assets)
    overall_status = "warning" if any(item["status"] != "passed" for item in findings) else "passed"
    evidence = {
        "schema_version": "suite-quality-evidence/v0.1",
        "suite_id": manifest.get("suite_id", suite_root.name),
        "overall_status": overall_status,
        "coverage": {
            "task_families": count_by_key(packages, "task_family"),
            "splits": count_by_key(packages, "split"),
        },
        "difficulty": difficulty_distribution(packages),
        "leakage": {
            "duplicate_scene_rate": duplicate_scene_rate,
            "duplicate_instruction_rate": duplicate_instruction_rate,
            "split_leakage_package_ids": leaked_ids,
            "shared_asset_policy": "allowed_with_variation",
        },
        "assets": assets,
        "runtime": {
            "evidence_source": "not_run",
            "smoke_pass_rate": None,
        },
        "quality_findings": findings,
    }
    evidence_path = write_yaml_artifact(suite_root / "evidence" / "suite_quality_evidence.yaml", evidence)
    return SuiteQualityEvidenceResult(
        suite_root=suite_root,
        overall_status=overall_status,
        evidence_path=evidence_path,
    )


def _packages(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not all(isinstance(item, dict) for item in packages):
        raise SuiteQualityEvidenceError("suite_manifest.yaml field 'packages' must be a list")
    return [dict(item) for item in packages]


def _task_instruction(package_path: Path) -> str:
    task = _load_yaml(package_path / "task" / "task.yaml")
    return str(task.get("instruction", ""))


def _scene_fingerprint(package_path: Path) -> str:
    scene_path = package_path / "scene" / "instances.yaml"
    if not scene_path.exists():
        return "<missing>"
    return scene_path.read_text(encoding="utf-8")


def _findings(
    duplicate_scene_rate: float,
    duplicate_instruction_rate: float,
    leaked_ids: list[str],
    assets: dict[str, float],
) -> list[dict[str, str]]:
    return [
        {
            "id": "duplicate_scenes",
            "status": "warning" if duplicate_scene_rate > 0 else "passed",
            "evidence": f"duplicate_scene_rate={duplicate_scene_rate}",
        },
        {
            "id": "duplicate_instructions",
            "status": "warning" if duplicate_instruction_rate > 0 else "passed",
            "evidence": f"duplicate_instruction_rate={duplicate_instruction_rate}",
        },
        {
            "id": "split_leakage",
            "status": "warning" if leaked_ids else "passed",
            "evidence": ",".join(leaked_ids) if leaked_ids else "no split leakage detected",
        },
        {
            "id": "asset_reproducibility",
            "status": "passed"
            if assets["license_completeness"] == 1.0 and assets["checksum_completeness"] == 1.0
            else "warning",
            "evidence": (
                f"license={assets['license_completeness']}; "
                f"checksum={assets['checksum_completeness']}"
            ),
        },
    ]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SuiteQualityEvidenceError(f"Missing YAML artifact: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SuiteQualityEvidenceError(f"YAML artifact must be a mapping: {path}")
    return data

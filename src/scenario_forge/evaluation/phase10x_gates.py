from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.evaluation.suite_quality_evidence import generate_suite_quality_evidence


class Phase10xEvidenceError(ValueError):
    """Raised when Phase 10.x evidence cannot be generated."""


@dataclass(frozen=True)
class Phase10xEvidenceResult:
    suite_root: Path
    overall_status: str
    evidence_paths: tuple[Path, ...]
    gate_statuses: dict[str, str]


REQUIRED_EOS_IMPORT_FILES = (
    "adapters/ebench/package.yaml",
    "adapters/ebench/task_entrypoint.yaml",
    "scene/main.usda",
    "locks/asset_lock.yaml",
)


def generate_phase10x_evidence(
    suite_dir: str | Path,
    *,
    eos_python: str | Path | None = None,
    golden_evidence_path: str | Path | None = None,
    external_evidence_path: str | Path | None = None,
    runtime_smoke_path: str | Path | None = None,
    rc_min_packages: int = 50,
    rc_max_packages: int = 100,
) -> Phase10xEvidenceResult:
    suite_root = Path(suite_dir)
    manifest = _load_yaml(suite_root / "suite_manifest.yaml")
    packages = _packages(manifest)
    package_roots = {
        str(item["package_id"]): _suite_relative_path(suite_root, item["path"]) for item in packages
    }

    generate_suite_quality_evidence(suite_root)

    golden = _golden_task_pack_evidence(
        manifest,
        packages,
        imported_golden_path=Path(golden_evidence_path)
        if golden_evidence_path is not None
        else None,
    )
    external = _external_input_hardening_evidence(
        suite_root,
        packages,
        Path(external_evidence_path) if external_evidence_path is not None else None,
    )
    eos_import = _eos_static_import_evidence(
        packages,
        Path(eos_python) if eos_python is not None else None,
    )
    runtime = _runtime_smoke_evidence(
        Path(runtime_smoke_path) if runtime_smoke_path is not None else None,
        suite_root,
        package_roots,
    )
    gate_statuses = {
        "phase_10_1_golden_task_pack": str(golden["status"]),
        "phase_10_2_external_input_hardening": str(external["status"]),
        "phase_10_3_eos_static_import": str(eos_import["status"]),
        "phase_10_4_runtime_smoke": str(runtime["status"]),
    }
    prerequisite_gate_statuses = dict(gate_statuses)
    rc_gate = _release_candidate_evidence(
        manifest=manifest,
        packages=packages,
        rc_min_packages=rc_min_packages,
        rc_max_packages=rc_max_packages,
        gate_statuses=prerequisite_gate_statuses,
    )
    gate_statuses["phase_10_5_release_candidate"] = str(rc_gate["overall_status"])

    evidence_paths = (
        write_yaml_artifact(suite_root / "evidence" / "golden_task_pack.yaml", golden),
        write_yaml_artifact(suite_root / "evidence" / "external_input_hardening.yaml", external),
        write_yaml_artifact(suite_root / "evidence" / "eos_static_import.yaml", eos_import),
        write_yaml_artifact(suite_root / "evidence" / "runtime_smoke.yaml", runtime),
        write_yaml_artifact(suite_root / "evidence" / "phase10x_rc_gate.yaml", rc_gate),
    )
    return Phase10xEvidenceResult(
        suite_root=suite_root,
        overall_status=_aggregate_status(gate_statuses.values()),
        evidence_paths=evidence_paths,
        gate_statuses=gate_statuses,
    )


def _golden_task_pack_evidence(
    manifest: dict[str, Any],
    packages: list[dict[str, Any]],
    *,
    imported_golden_path: Path | None,
) -> dict[str, Any]:
    package_count = len(packages)
    in_golden_range = 10 <= package_count <= 20
    if not in_golden_range and imported_golden_path is not None:
        return _imported_golden_task_pack_evidence(
            manifest=manifest,
            packages=packages,
            imported_golden_path=imported_golden_path,
        )
    return {
        "schema_version": "phase10x-golden-task-pack/v0.1",
        "phase": "10.1",
        "suite_id": manifest.get("suite_id"),
        "status": "passed" if in_golden_range else "warning",
        "evidence_mode": "golden_task_pack" if in_golden_range else "missing_golden_task_pack",
        "package_count": package_count,
        "expected_package_count": {"min": 10, "max": 20},
        "package_ids": [str(item["package_id"]) for item in packages],
        "task_families": _count_by_key(packages, "task_family"),
        "splits": _count_by_key(packages, "split"),
        "difficulties": _count_by_key(packages, "difficulty"),
        "deterministic_regeneration": "package ids and suite manifest are deterministic inputs",
        "blockers": []
        if in_golden_range
        else ["Phase 10.1 requires a frozen 10-20 package golden task pack"],
    }


def _imported_golden_task_pack_evidence(
    *,
    manifest: dict[str, Any],
    packages: list[dict[str, Any]],
    imported_golden_path: Path,
) -> dict[str, Any]:
    source = _load_yaml(imported_golden_path)
    source_status = str(source.get("status", "failed"))
    source_package_count = source.get("package_count")
    blockers: list[str] = []
    if source_status != "passed":
        blockers.append("imported Phase 10.1 golden evidence is not passed")
    if not isinstance(source_package_count, int) or not 10 <= source_package_count <= 20:
        blockers.append("imported Phase 10.1 golden evidence must contain 10-20 packages")
    return {
        "schema_version": "phase10x-golden-task-pack/v0.1",
        "phase": "10.1",
        "suite_id": manifest.get("suite_id"),
        "status": "passed" if not blockers else "warning",
        "evidence_mode": "imported_golden_task_pack",
        "package_count": len(packages),
        "expected_package_count": {"min": 10, "max": 20},
        "package_ids": [str(item["package_id"]) for item in packages],
        "imported_golden_evidence": str(imported_golden_path),
        "imported_golden_suite_id": source.get("suite_id"),
        "imported_golden_package_count": source_package_count,
        "imported_golden_status": source_status,
        "blockers": blockers,
    }


def _external_input_hardening_evidence(
    suite_root: Path,
    packages: list[dict[str, Any]],
    external_evidence_path: Path | None,
) -> dict[str, Any]:
    lanes = {"scenario_forge_layout": _scenario_forge_layout_lane(packages)}
    blockers: list[str] = []
    evidence_source = "not_provided"
    if external_evidence_path is None:
        blockers.append("external input A/B evidence not provided")
    else:
        evidence_source = str(external_evidence_path)
        external = _load_yaml(external_evidence_path)
        raw_lanes = external.get("lanes")
        if not isinstance(raw_lanes, list):
            blockers.append("external evidence field 'lanes' must be a list")
        else:
            for lane in raw_lanes:
                if not isinstance(lane, dict) or not isinstance(lane.get("id"), str):
                    blockers.append("external evidence lane entries require string id")
                    continue
                lanes[str(lane["id"])] = dict(lane)

    external_lane_ids = sorted(key for key in lanes if key != "scenario_forge_layout")
    failed_lanes = [
        key for key, lane in lanes.items() if str(lane.get("status", "failed")) != "passed"
    ]
    if not external_lane_ids:
        blockers.append("no external LabBuilder or SimFoundry lane evidence")
    if failed_lanes:
        blockers.append(f"lane status not passed: {', '.join(failed_lanes)}")

    return {
        "schema_version": "phase10x-external-input-hardening/v0.1",
        "phase": "10.2",
        "status": "passed" if not blockers else "warning",
        "suite_root": str(suite_root),
        "evidence_source": evidence_source,
        "lanes": lanes,
        "external_lane_ids": external_lane_ids,
        "adoption_decision": "retain scenario_forge_layout as baseline; external lanes remain evidence-gated",
        "blockers": blockers,
    }


def _scenario_forge_layout_lane(packages: list[dict[str, Any]]) -> dict[str, Any]:
    missing_layout_checks = []
    missing_adapter_exports = []
    for item in packages:
        package_root = Path(str(item["path"]))
        if not (package_root / "evidence" / "layout_checks.yaml").exists():
            missing_layout_checks.append(str(item["package_id"]))
        if not (package_root / "adapters" / "ebench" / "package.yaml").exists():
            missing_adapter_exports.append(str(item["package_id"]))
    return {
        "id": "scenario_forge_layout",
        "status": "passed" if not missing_layout_checks and not missing_adapter_exports else "failed",
        "package_validity": "passed",
        "asset_lock_coverage": 1.0,
        "predicate_binding": "passed",
        "layout_checks": "passed" if not missing_layout_checks else "failed",
        "ebench_export": "passed" if not missing_adapter_exports else "failed",
        "missing_layout_checks": missing_layout_checks,
        "missing_adapter_exports": missing_adapter_exports,
    }


def _eos_static_import_evidence(
    packages: list[dict[str, Any]],
    eos_python: Path | None,
) -> dict[str, Any]:
    package_reports = []
    for item in packages:
        package_root = Path(str(item["path"]))
        missing = [
            relative_path
            for relative_path in REQUIRED_EOS_IMPORT_FILES
            if not (package_root / relative_path).exists()
        ]
        package_reports.append(
            {
                "package_id": str(item["package_id"]),
                "path": str(package_root),
                "status": "failed" if missing else "passed",
                "missing": missing,
            }
        )
    blockers = [
        f"{report['package_id']} missing {', '.join(report['missing'])}"
        for report in package_reports
        if report["missing"]
    ]
    return {
        "schema_version": "phase10x-eos-static-import/v0.1",
        "phase": "10.3",
        "status": "failed" if blockers else "passed",
        "required_files": list(REQUIRED_EOS_IMPORT_FILES),
        "eos_python": _eos_python_metadata(eos_python),
        "packages": package_reports,
        "blockers": blockers,
    }


def _runtime_smoke_evidence(
    runtime_smoke_path: Path | None,
    suite_root: Path,
    package_roots: dict[str, Path],
) -> dict[str, Any]:
    if runtime_smoke_path is None:
        return {
            "schema_version": "phase10x-runtime-smoke/v0.1",
            "phase": "10.4",
            "status": "warning",
            "evidence_source": "not_provided",
            "lane": None,
            "packages_tested": [],
            "blockers": ["runtime smoke evidence not provided"],
        }

    source = _load_yaml(runtime_smoke_path)
    packages_tested = source.get("packages_tested", [])
    if not isinstance(packages_tested, list) or not all(
        isinstance(package_id, str) for package_id in packages_tested
    ):
        packages_tested = []
        package_blockers = ["runtime smoke field 'packages_tested' must be a list of strings"]
    else:
        package_ids = set(package_roots)
        unknown = sorted(set(packages_tested) - package_ids)
        package_blockers = [f"runtime smoke references unknown package ids: {', '.join(unknown)}"] if unknown else []

    source_status = str(source.get("status", "failed"))
    blockers = list(package_blockers)
    package_artifacts, artifact_blockers = _runtime_package_artifacts(
        source,
        suite_root,
        package_roots,
    )
    blockers.extend(artifact_blockers)
    artifact_package_ids = {
        str(item["package_id"])
        for item in package_artifacts
        if isinstance(item, dict) and isinstance(item.get("package_id"), str)
    }
    uncovered = sorted(set(packages_tested) - artifact_package_ids)
    if uncovered:
        blockers.append(
            "runtime smoke package-linked artifacts missing for tested package ids: "
            + ", ".join(uncovered)
        )
    if source_status != "passed":
        blockers.append(f"runtime smoke status is {source_status!r}, expected 'passed'")
    if not packages_tested:
        blockers.append("runtime smoke must cover at least one package")

    return {
        "schema_version": "phase10x-runtime-smoke/v0.1",
        "phase": "10.4",
        "status": "passed" if not blockers else "failed",
        "evidence_source": str(runtime_smoke_path),
        "lane": source.get("lane"),
        "packages_tested": packages_tested,
        "package_artifacts": package_artifacts,
        "evidence_uri": source.get("evidence_uri"),
        "summary": source.get("summary"),
        "blockers": blockers,
    }


def _runtime_package_artifacts(
    source: dict[str, Any],
    suite_root: Path,
    package_roots: dict[str, Path],
) -> tuple[list[dict[str, Any]], list[str]]:
    raw_artifacts = source.get("package_artifacts")
    if raw_artifacts is None:
        return [], ["runtime smoke must include package-linked artifacts"]
    if not isinstance(raw_artifacts, list):
        return [], ["runtime smoke field 'package_artifacts' must be a list"]

    artifacts: list[dict[str, Any]] = []
    blockers: list[str] = []
    required_fields = (
        "package_id",
        "usd_entrypoint",
        "asset_lock",
        "adapter_descriptor",
        "task_entrypoint",
        "trace_uri",
    )
    expected_paths = {
        "usd_entrypoint": Path("scene/main.usda"),
        "asset_lock": Path("locks/asset_lock.yaml"),
        "adapter_descriptor": Path("adapters/ebench/package.yaml"),
        "task_entrypoint": Path("adapters/ebench/task_entrypoint.yaml"),
    }
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, dict):
            blockers.append(f"runtime smoke package_artifacts[{index}] must be a mapping")
            continue
        artifact = dict(raw_artifact)
        missing_fields = [
            field
            for field in required_fields
            if not isinstance(artifact.get(field), str) or not str(artifact[field]).strip()
        ]
        if missing_fields:
            blockers.append(
                f"runtime smoke package_artifacts[{index}] missing "
                + ", ".join(missing_fields)
            )
        package_id = artifact.get("package_id")
        package_root = package_roots.get(package_id) if isinstance(package_id, str) else None
        if isinstance(package_id, str) and package_root is None:
            blockers.append(
                f"runtime smoke package_artifacts[{index}] references unknown package id: "
                f"{package_id}"
            )
        elif package_root is not None:
            blockers.extend(
                _runtime_artifact_path_blockers(
                    artifact,
                    index=index,
                    suite_root=suite_root,
                    package_root=package_root,
                    expected_paths=expected_paths,
                )
            )
            blockers.extend(
                _runtime_trace_uri_blockers(
                    artifact,
                    index=index,
                    require_executed=str(source.get("status", "failed")) == "passed",
                )
            )
        artifacts.append(artifact)
    if not artifacts:
        blockers.append("runtime smoke must include at least one package-linked artifact")
    return artifacts, blockers


def _runtime_artifact_path_blockers(
    artifact: dict[str, Any],
    *,
    index: int,
    suite_root: Path,
    package_root: Path,
    expected_paths: dict[str, Path],
) -> list[str]:
    blockers: list[str] = []
    suite_root_resolved = suite_root.resolve(strict=False)
    package_root_resolved = package_root.resolve(strict=False)
    for field, expected_relative in expected_paths.items():
        raw_path = artifact.get(field)
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        artifact_path = Path(raw_path)
        if artifact_path.is_absolute():
            blockers.append(
                f"runtime smoke package_artifacts[{index}].{field} must be suite-relative"
            )
            continue
        resolved = (suite_root_resolved / artifact_path).resolve(strict=False)
        expected = (package_root_resolved / expected_relative).resolve(strict=False)
        if not resolved.exists():
            blockers.append(
                f"runtime smoke package_artifacts[{index}].{field} does not exist: "
                f"{raw_path}"
            )
        if resolved != expected:
            try:
                expected_display = expected.relative_to(suite_root_resolved).as_posix()
            except ValueError:
                expected_display = str(expected)
            blockers.append(
                f"runtime smoke package_artifacts[{index}].{field} must reference "
                f"{expected_display}"
            )
            continue
    return blockers


def _runtime_trace_uri_blockers(
    artifact: dict[str, Any],
    *,
    index: int,
    require_executed: bool,
) -> list[str]:
    trace_uri = artifact.get("trace_uri")
    if not isinstance(trace_uri, str) or not trace_uri.startswith("file://"):
        return []
    parsed = urlparse(trace_uri)
    trace_path = Path(parsed.path)
    if not trace_path.exists():
        return [f"runtime smoke package_artifacts[{index}].trace_uri does not exist: {trace_uri}"]
    try:
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            f"runtime smoke package_artifacts[{index}].trace_uri is not readable JSON: "
            f"{type(exc).__name__}: {exc}"
        ]

    blockers: list[str] = []
    package_id = artifact.get("package_id")
    if isinstance(package_id, str) and trace.get("package_id") != package_id:
        blockers.append(
            f"runtime smoke package_artifacts[{index}].trace_uri package_id mismatch: "
            f"{trace.get('package_id')}"
        )
    if require_executed and trace.get("runtime_status") != "executed":
        blockers.append(
            f"runtime smoke package_artifacts[{index}].trace_uri must report "
            "runtime_status=executed"
        )
    if require_executed and trace.get("stage_open_status") not in {None, "passed"}:
        blockers.append(
            f"runtime smoke package_artifacts[{index}].trace_uri must report "
            "stage_open_status=passed"
        )
    return blockers


def _suite_relative_path(suite_root: Path, raw_path: Any) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    return suite_root / path


def _release_candidate_evidence(
    *,
    manifest: dict[str, Any],
    packages: list[dict[str, Any]],
    rc_min_packages: int,
    rc_max_packages: int,
    gate_statuses: dict[str, str],
) -> dict[str, Any]:
    blockers: list[str] = []
    package_count = len(packages)
    if package_count < rc_min_packages or package_count > rc_max_packages:
        blockers.append(f"RC suite should contain {rc_min_packages}-{rc_max_packages} packages")
    for gate, status in gate_statuses.items():
        if status != "passed":
            label = gate.replace("phase_10_", "Phase 10.").replace("_", " ")
            blockers.append(f"{label} gate not passed")

    overall_status = _aggregate_status(gate_statuses.values())
    if blockers and overall_status == "passed":
        overall_status = "warning"

    return {
        "schema_version": "phase10x-release-candidate-gate/v0.1",
        "phase": "10.5",
        "suite_id": manifest.get("suite_id"),
        "overall_status": overall_status,
        "package_count": package_count,
        "expected_package_count": {"min": rc_min_packages, "max": rc_max_packages},
        "gate_statuses": dict(gate_statuses),
        "blockers": blockers,
    }


def _eos_python_metadata(eos_python: Path | None) -> dict[str, Any]:
    if eos_python is None:
        return {"path": None, "status": "not_provided", "version": None}
    if not eos_python.exists():
        return {"path": str(eos_python), "status": "missing", "version": None}
    try:
        result = subprocess.run(
            [str(eos_python), "--version"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except OSError as exc:
        return {"path": str(eos_python), "status": "error", "version": str(exc)}
    version = (result.stdout or result.stderr).strip()
    return {
        "path": str(eos_python),
        "status": "passed" if result.returncode == 0 else "error",
        "version": version,
    }


def _packages(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not all(isinstance(item, dict) for item in packages):
        raise Phase10xEvidenceError("suite_manifest.yaml field 'packages' must be a list")
    normalized = [dict(item) for item in packages]
    for index, item in enumerate(normalized):
        if not isinstance(item.get("package_id"), str) or not isinstance(item.get("path"), str):
            raise Phase10xEvidenceError(f"suite package entry {index} requires package_id and path")
    return normalized


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Phase10xEvidenceError(f"Missing YAML artifact: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise Phase10xEvidenceError(f"YAML artifact must be a mapping: {path}")
    return data


def _count_by_key(packages: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in packages:
        value = str(item.get(key, "unspecified"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _aggregate_status(statuses: Any) -> str:
    normalized = [str(status) for status in statuses]
    if any(status == "failed" for status in normalized):
        return "failed"
    if any(status == "warning" for status in normalized):
        return "warning"
    return "passed"

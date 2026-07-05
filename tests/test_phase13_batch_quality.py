from pathlib import Path

import yaml

from scenario_forge.cli import main


def test_image_task_batch_quality_gate_passes_for_formal_ready_batch(tmp_path: Path) -> None:
    suite_dir = tmp_path / "suite"
    evidence_dir = suite_dir / "evidence"
    package_rows = []
    report_packages = []
    for index in range(3):
        package_id = f"phase13_pkg_{index}"
        request_id = f"phase13_request_{index}"
        package_dir = suite_dir / "packages" / package_id
        current_gate_path = package_dir / "evidence" / "phase13_current_gate_index.yaml"
        _write_yaml(
            current_gate_path,
            {
                "schema_version": "phase13-current-gate-index/v0.1",
                "request_id": request_id,
                "package_id": package_id,
                "overall_status": "phase13_formal_package_ready",
                "formal_package_ready": True,
                "static_candidate_ready": True,
                "overview_visual_ready": True,
                "execution_predicate_ready": True,
                "next_required_gate": "13.9",
                "latest_gates": {
                    "13.8": {
                        "path": "evidence/phase13_8_execution_predicate_canary_gate.yaml",
                        "schema_version": "execution-predicate-canary-gate/v0.1",
                        "status": "passed",
                    }
                },
                "blockers": [
                    "13.9 batch factory quality gate is required before batch factory readiness"
                ],
            },
        )
        package_rows.append(
            {
                "package_id": package_id,
                "path": str(package_dir),
                "task_family": "object_in_container",
                "difficulty": "easy" if index == 0 else "medium",
                "split": "dev" if index < 2 else "test",
            }
        )
        report_packages.append(
            {
                "request_id": request_id,
                "package_id": package_id,
                "status": "formal_package_ready",
                "phase13_current_gate_index": str(current_gate_path),
            }
        )

    _write_yaml(
        suite_dir / "suite_manifest.yaml",
        {
            "schema_version": "suite-manifest/v0.1",
            "suite_id": "phase13_batch_suite",
            "packages": package_rows,
        },
    )
    suite_quality_path = _write_yaml(
        evidence_dir / "suite_quality_evidence.yaml",
        {
            "schema_version": "suite-quality-evidence/v0.1",
            "suite_id": "phase13_batch_suite",
            "overall_status": "passed",
            "coverage": {"task_families": {"object_in_container": 3}, "splits": {"dev": 2, "test": 1}},
            "difficulty": {"easy": 1, "medium": 2},
            "leakage": {
                "duplicate_scene_rate": 0.0,
                "duplicate_instruction_rate": 0.0,
                "split_leakage_package_ids": [],
            },
            "assets": {"license_completeness": 1.0, "checksum_completeness": 1.0},
            "quality_findings": [],
        },
    )
    quality_report_path = _write_yaml(
        evidence_dir / "phase13_batch_factory_quality_report.yaml",
        {
            "schema_version": "phase13-batch-factory-quality-report/v0.1",
            "suite_id": "phase13_batch_suite",
            "factory_mode": "image_grounded_existing_asset",
            "request_count": 3,
            "package_results": report_packages,
            "failed_or_blocked_requests": [],
            "quality_metrics": {
                "failure_rate": 0.0,
                "duplicate_request_rate": 0.0,
                "coverage_status": "passed",
                "blocker_taxonomy_status": "passed",
            },
        },
    )

    exit_code = main(
        [
            "image-task",
            "batch-quality",
            "--suite",
            str(suite_dir),
            "--quality-report",
            str(quality_report_path),
            "--suite-quality-evidence",
            str(suite_quality_path),
            "--strict",
        ]
    )

    assert exit_code == 0
    gate = _load_yaml(evidence_dir / "phase13_9_batch_factory_quality_gate.yaml")
    assert gate["schema_version"] == "batch-factory-quality-gate/v0.1"
    assert gate["phase"] == "13.9"
    assert gate["status"] == "passed"
    assert gate["suite_id"] == "phase13_batch_suite"
    assert gate["request_count"] == 3
    assert gate["formal_package_ready_count"] == 3
    assert gate["next_stage"] == "phase13_batch_factory_ready"
    assert gate["blockers"] == []


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path

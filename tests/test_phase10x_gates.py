from __future__ import annotations

import sys
from pathlib import Path

import yaml

from scenario_forge.evaluation.phase10x_gates import generate_phase10x_evidence
from scenario_forge.generation.suite.suite_generator import generate_suite_from_spec


def test_phase10x_generates_passed_gate_evidence_for_golden_suite(tmp_path: Path) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = write_runtime_smoke(
        tmp_path / "runtime.yaml",
        package_ids=["phase10x_test_suite_000", "phase10x_test_suite_001"],
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )

    golden = load_yaml(suite_dir / "evidence" / "golden_task_pack.yaml")
    external = load_yaml(suite_dir / "evidence" / "external_input_hardening.yaml")
    eos_import = load_yaml(suite_dir / "evidence" / "eos_static_import.yaml")
    runtime = load_yaml(suite_dir / "evidence" / "runtime_smoke.yaml")
    rc_gate = load_yaml(suite_dir / "evidence" / "phase10x_rc_gate.yaml")

    assert result.overall_status == "passed"
    assert result.gate_statuses == {
        "phase_10_1_golden_task_pack": "passed",
        "phase_10_2_external_input_hardening": "passed",
        "phase_10_3_eos_static_import": "passed",
        "phase_10_4_runtime_smoke": "passed",
        "phase_10_5_release_candidate": "passed",
    }
    assert len(result.evidence_paths) == 5
    assert golden["status"] == "passed"
    assert golden["package_count"] == 10
    assert golden["package_ids"][0] == "phase10x_test_suite_000"
    assert external["status"] == "passed"
    assert external["lanes"]["labuilder_layout_import"]["status"] == "passed"
    assert external["lanes"]["simfoundry_real2sim_import"]["status"] == "passed"
    assert eos_import["status"] == "passed"
    assert eos_import["eos_python"]["version"].startswith("Python ")
    assert runtime["status"] == "passed"
    assert runtime["lane"] == "eos_newton_smoke"
    assert rc_gate["overall_status"] == "passed"
    assert (suite_dir / "evidence" / "suite_quality_evidence.yaml").exists()


def test_phase10x_default_release_candidate_allows_50_task_suite(tmp_path: Path) -> None:
    suite_dir = generate_release_candidate_suite(tmp_path)
    golden_path = write_golden_task_pack_evidence(tmp_path / "golden.yaml")
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = write_runtime_smoke(
        tmp_path / "runtime.yaml",
        package_ids=["phase10x_rc_test_suite_000"],
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        golden_evidence_path=golden_path,
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
    )

    golden = load_yaml(suite_dir / "evidence" / "golden_task_pack.yaml")
    rc_gate = load_yaml(suite_dir / "evidence" / "phase10x_rc_gate.yaml")

    assert result.overall_status == "passed"
    assert result.gate_statuses["phase_10_1_golden_task_pack"] == "passed"
    assert result.gate_statuses["phase_10_5_release_candidate"] == "passed"
    assert golden["status"] == "passed"
    assert golden["evidence_mode"] == "imported_golden_task_pack"
    assert golden["imported_golden_package_count"] == 10
    assert golden["package_count"] == 50
    assert rc_gate["overall_status"] == "passed"
    assert rc_gate["package_count"] == 50
    assert "phase_10_5_release_candidate" not in rc_gate["gate_statuses"]


def test_phase10x_default_release_candidate_requires_golden_evidence(tmp_path: Path) -> None:
    suite_dir = generate_release_candidate_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = write_runtime_smoke(
        tmp_path / "runtime.yaml",
        package_ids=["phase10x_rc_test_suite_000"],
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
    )
    golden = load_yaml(suite_dir / "evidence" / "golden_task_pack.yaml")

    assert result.overall_status == "warning"
    assert result.gate_statuses["phase_10_1_golden_task_pack"] == "warning"
    assert golden["evidence_mode"] == "missing_golden_task_pack"
    assert any("10-20 package golden" in blocker for blocker in golden["blockers"])


def test_phase10x_warns_when_runtime_smoke_is_missing(tmp_path: Path) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )
    runtime = load_yaml(suite_dir / "evidence" / "runtime_smoke.yaml")
    rc_gate = load_yaml(suite_dir / "evidence" / "phase10x_rc_gate.yaml")

    assert result.overall_status == "warning"
    assert result.gate_statuses["phase_10_4_runtime_smoke"] == "warning"
    assert runtime["status"] == "warning"
    assert runtime["evidence_source"] == "not_provided"
    assert rc_gate["overall_status"] == "warning"
    assert any("runtime smoke" in blocker for blocker in rc_gate["blockers"])


def test_phase10x_runtime_smoke_requires_package_linked_artifacts(tmp_path: Path) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = tmp_path / "runtime.yaml"
    write_yaml(
        runtime_path,
        {
            "schema_version": "phase10x-runtime-smoke-evidence/v0.1",
            "lane": "eos_genmanip_native_smoke",
            "status": "passed",
            "packages_tested": ["phase10x_test_suite_000"],
            "evidence_uri": "file:///tmp/native-genmanip-trace.json",
            "summary": "Native GenManip task executed, but no Scenario Forge package artifacts were linked.",
        },
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )
    runtime = load_yaml(suite_dir / "evidence" / "runtime_smoke.yaml")

    assert result.gate_statuses["phase_10_4_runtime_smoke"] == "failed"
    assert runtime["status"] == "failed"
    assert any("package-linked" in blocker for blocker in runtime["blockers"])


def test_phase10x_runtime_smoke_requires_existing_suite_relative_package_artifacts(
    tmp_path: Path,
) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = tmp_path / "runtime.yaml"
    write_yaml(
        runtime_path,
        {
            "schema_version": "phase10x-runtime-smoke-evidence/v0.1",
            "lane": "eos_usd_stage_open_smoke",
            "status": "passed",
            "packages_tested": ["phase10x_test_suite_000"],
            "package_artifacts": [
                {
                    "package_id": "phase10x_test_suite_000",
                    "usd_entrypoint": "packages/phase10x_test_suite_000/scene/missing.usda",
                    "asset_lock": "packages/phase10x_test_suite_000/locks/asset_lock.yaml",
                    "adapter_descriptor": (
                        "packages/phase10x_test_suite_000/adapters/ebench/package.yaml"
                    ),
                    "trace_uri": "file:///tmp/phase10x-trace.json",
                }
            ],
            "evidence_uri": "file:///tmp/phase10x-runtime-evidence.json",
            "summary": "EOS runtime lane loaded Scenario Forge USD.",
        },
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )
    runtime = load_yaml(suite_dir / "evidence" / "runtime_smoke.yaml")

    assert result.gate_statuses["phase_10_4_runtime_smoke"] == "failed"
    assert runtime["status"] == "failed"
    assert any("task_entrypoint" in blocker for blocker in runtime["blockers"])
    assert any("does not exist" in blocker for blocker in runtime["blockers"])


def test_phase10x_runtime_smoke_validates_local_file_trace_content(tmp_path: Path) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        '{"package_id":"wrong_package","runtime_status":"skipped","stage_open_status":"skipped"}',
        encoding="utf-8",
    )
    runtime_path = write_runtime_smoke(
        tmp_path / "runtime.yaml",
        package_ids=["phase10x_test_suite_000"],
        trace_uri=trace_path.as_uri(),
    )

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )
    runtime = load_yaml(suite_dir / "evidence" / "runtime_smoke.yaml")

    assert result.gate_statuses["phase_10_4_runtime_smoke"] == "failed"
    assert any("package_id mismatch" in blocker for blocker in runtime["blockers"])
    assert any("runtime_status=executed" in blocker for blocker in runtime["blockers"])


def test_phase10x_static_import_fails_when_required_artifact_is_missing(
    tmp_path: Path,
) -> None:
    suite_dir = generate_golden_suite(tmp_path)
    external_path = write_external_evidence(tmp_path / "external.yaml")
    runtime_path = write_runtime_smoke(
        tmp_path / "runtime.yaml",
        package_ids=["phase10x_test_suite_000"],
    )
    missing = suite_dir / "packages" / "phase10x_test_suite_000" / "adapters" / "ebench" / "package.yaml"
    missing.unlink()

    result = generate_phase10x_evidence(
        suite_dir,
        eos_python=Path(sys.executable),
        external_evidence_path=external_path,
        runtime_smoke_path=runtime_path,
        rc_min_packages=10,
        rc_max_packages=20,
    )
    eos_import = load_yaml(suite_dir / "evidence" / "eos_static_import.yaml")

    assert result.overall_status == "failed"
    assert result.gate_statuses["phase_10_3_eos_static_import"] == "failed"
    assert eos_import["status"] == "failed"
    assert eos_import["packages"][0]["missing"] == ["adapters/ebench/package.yaml"]


def generate_golden_suite(tmp_path: Path) -> Path:
    spec_path = tmp_path / "suite_spec.yaml"
    write_yaml(
        spec_path,
        {
            "schema_version": "suite-spec/v0.2",
            "suite_id": "phase10x_test_suite",
            "domain": "scientific_workbench",
            "target": "ebench",
            "package_mode": "fat",
            "robot_profiles": ["franka_panda_tabletop_v1"],
            "num_tasks": 10,
            "task_families": {"pick_place": 5, "pipette_transfer_light": 5},
            "difficulties": {"easy": 4, "medium": 3, "hard": 3},
            "splits": {"dev": 4, "validation": 3, "test": 3},
            "variation_axes": ["layout", "instruction_language"],
            "validation": {"require_asset_lock": True},
        },
    )
    suite_dir = tmp_path / "suite"
    generate_suite_from_spec(spec_path, suite_dir)
    return suite_dir


def generate_release_candidate_suite(tmp_path: Path) -> Path:
    spec_path = tmp_path / "suite_spec_rc.yaml"
    write_yaml(
        spec_path,
        {
            "schema_version": "suite-spec/v0.2",
            "suite_id": "phase10x_rc_test_suite",
            "domain": "scientific_workbench",
            "target": "ebench",
            "package_mode": "fat",
            "robot_profiles": ["franka_panda_tabletop_v1"],
            "num_tasks": 50,
            "task_families": {"pick_place": 25, "pipette_transfer_light": 25},
            "difficulties": {"easy": 17, "medium": 17, "hard": 16},
            "splits": {"dev": 15, "validation": 15, "test": 20},
            "variation_axes": ["layout", "instruction_language"],
            "validation": {"require_asset_lock": True},
        },
    )
    suite_dir = tmp_path / "rc_suite"
    generate_suite_from_spec(spec_path, suite_dir)
    return suite_dir


def write_external_evidence(path: Path) -> Path:
    write_yaml(
        path,
        {
            "schema_version": "phase10x-external-input-evidence/v0.1",
            "lanes": [
                {
                    "id": "scenario_forge_layout",
                    "status": "passed",
                    "package_validity": "passed",
                    "asset_lock_coverage": 1.0,
                    "predicate_binding": "passed",
                    "layout_checks": "passed",
                    "ebench_export": "passed",
                },
                {
                    "id": "labuilder_layout_import",
                    "status": "passed",
                    "package_validity": "passed",
                    "asset_lock_coverage": 1.0,
                    "predicate_binding": "passed",
                    "layout_checks": "passed",
                    "ebench_export": "passed",
                },
                {
                    "id": "simfoundry_real2sim_import",
                    "status": "passed",
                    "package_validity": "passed",
                    "asset_lock_coverage": 1.0,
                    "predicate_binding": "passed",
                    "layout_checks": "passed",
                    "ebench_export": "passed",
                },
            ],
        },
    )
    return path


def write_golden_task_pack_evidence(path: Path) -> Path:
    write_yaml(
        path,
        {
            "schema_version": "phase10x-golden-task-pack/v0.1",
            "phase": "10.1",
            "suite_id": "phase10x_test_suite",
            "status": "passed",
            "evidence_mode": "golden_task_pack",
            "package_count": 10,
            "expected_package_count": {"min": 10, "max": 20},
            "package_ids": [f"phase10x_test_suite_{index:03d}" for index in range(10)],
            "blockers": [],
        },
    )
    return path


def write_runtime_smoke(
    path: Path,
    *,
    package_ids: list[str],
    trace_uri: str | None = None,
) -> Path:
    package_artifacts = [
        {
            "package_id": package_id,
            "usd_entrypoint": f"packages/{package_id}/scene/main.usda",
            "asset_lock": f"packages/{package_id}/locks/asset_lock.yaml",
            "adapter_descriptor": f"packages/{package_id}/adapters/ebench/package.yaml",
            "task_entrypoint": f"packages/{package_id}/adapters/ebench/task_entrypoint.yaml",
            "trace_uri": trace_uri or f"eos://records/phase10x/newton-smoke/{package_id}",
        }
        for package_id in package_ids
    ]
    write_yaml(
        path,
        {
            "schema_version": "phase10x-runtime-smoke-evidence/v0.1",
            "lane": "eos_newton_smoke",
            "status": "passed",
            "packages_tested": package_ids,
            "package_artifacts": package_artifacts,
            "evidence_uri": "eos://records/phase10x/newton-smoke",
            "summary": "Downstream EOS runtime smoke accepted generated USD packages.",
        },
    )
    return path


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

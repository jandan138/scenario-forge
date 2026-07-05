import json
from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.evaluation.phase11_gates import (
    generate_phase11_automated_release_gate,
    generate_phase11_executed_episode_gate,
    generate_phase11_phase12_readiness_gate,
    generate_phase11_post_execution_visual_review_gate,
    generate_phase11_single_task_release_candidate_gate,
    generate_phase11_small_multi_task_canary_gate,
    generate_phase11_success_predicate_gate,
    generate_phase11_task_execution_gate,
    generate_phase11_visual_review_gate,
)
from scenario_forge.scaffold import scaffold_starter_package


def test_phase11_visual_review_gate_passes_for_render_visual_reviewer_pass(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    image_path = package_dir / "evidence" / "tabletop_overview.png"
    image_path.write_bytes(b"fake-png-bytes")
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="PASS",
        image_path="tabletop_overview.png",
    )

    result = generate_phase11_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert result.status == "passed"
    assert result.evidence_path == package_dir / "evidence" / "phase11_visual_review_gate.yaml"
    assert gate["schema_version"] == "phase11-visual-review-gate/v0.1"
    assert gate["phase"] == "11.0"
    assert gate["status"] == "passed"
    assert gate["package_id"] == "tabletop_pick_place_starter"
    assert gate["task_id"] == "place_object_on_target"
    assert gate["visual_review"]["reviewer"] == "render-visual-reviewer"
    assert gate["visual_review"]["verdict"] == "PASS"
    assert gate["visual_review"]["image_path"] == "tabletop_overview.png"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "eos_task_execution_integration"
    assert gate["claim_boundary"] == (
        "Automated visual review gate only; not task success, not physics fidelity, "
        "not release approval, and not leaderboard evidence."
    )


def test_phase11_visual_review_gate_blocks_warn_verdict(tmp_path: Path) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    (package_dir / "evidence" / "tabletop_overview.png").write_bytes(b"fake-png-bytes")
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="WARN",
        image_path="tabletop_overview.png",
    )

    result = generate_phase11_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "visual review verdict must be PASS; got WARN" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_phase11_visual_review_gate_blocks_failed_render_material_preflight(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    (package_dir / "evidence" / "tabletop_overview.png").write_bytes(b"fake-png-bytes")
    metadata_path = package_dir / "evidence" / "tabletop_overview_render_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema": "scenario_forge_tabletop_overview_render.v0",
                "render_status": "pass",
                "material_runtime_preflight": {
                    "status": "failed",
                    "runtime_log_scan": {
                        "status": "failed",
                        "blocked_signals": ["rtx.mdltranslator"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="PASS",
        image_path="tabletop_overview.png",
        render_metadata_path="tabletop_overview_render_metadata.json",
    )

    result = generate_phase11_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "visual review render metadata material_runtime_preflight.status must be pass; got failed" in gate[
        "blockers"
    ]
    assert gate["visual_review"]["render_metadata_path"] == "tabletop_overview_render_metadata.json"


def test_phase11_visual_review_gate_blocks_runtime_log_missing_asset_signal(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    (package_dir / "evidence" / "tabletop_overview.png").write_bytes(b"fake-png-bytes")
    (package_dir / "evidence" / "tabletop_overview_runtime.log").write_text(
        "Prim '/World/object/occlusionTex' parameter 'texture': "
        "References an asset that can not be found: '../../missing_texture.png'\n",
        encoding="utf-8",
    )
    metadata_path = package_dir / "evidence" / "tabletop_overview_render_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema": "scenario_forge_tabletop_overview_render.v0",
                "render_status": "pass",
                "runtime_log_path": "tabletop_overview_runtime.log",
                "material_runtime_preflight": {
                    "status": "pass",
                    "runtime_log_scan": {
                        "status": "pass",
                        "blocked_signals": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="PASS",
        image_path="tabletop_overview.png",
        render_metadata_path="tabletop_overview_render_metadata.json",
    )

    result = generate_phase11_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert result.status == "failed"
    assert (
        "visual review render runtime log contains blocking material signal: "
        "References an asset that can not be found"
    ) in gate["blockers"]


def test_phase11_visual_review_gate_blocks_missing_or_manual_review(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="PASS",
        image_path="missing.png",
        reviewer="manual-human-review",
    )

    result = generate_phase11_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "visual review reviewer must be render-visual-reviewer" in gate["blockers"]
    assert "visual review image does not exist: missing.png" in gate["blockers"]


def test_cli_package_phase11_visual_review_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    (package_dir / "evidence" / "tabletop_overview.png").write_bytes(b"fake-png-bytes")
    review_path = write_visual_review(
        package_dir / "evidence" / "visual_review.yaml",
        verdict="FAIL",
        image_path="tabletop_overview.png",
    )

    code = main(
        [
            "package",
            "phase11-visual-review",
            "--package",
            str(package_dir),
            "--visual-review",
            str(review_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_visual_review_gate.yaml")
    assert code == 1
    assert gate["status"] == "failed"
    assert gate["next_stage"] == "blocked"


def test_cli_package_phase11_task_execution_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    execution_path = write_task_execution_evidence(
        tmp_path / "task_execution.yaml",
        package_id="wrong_package",
        task_id="wrong_task",
        runtime_log="missing.log",
        initial_keyframe="missing.png",
    )

    code = main(
        [
            "package",
            "phase11-task-execution",
            "--package",
            str(package_dir),
            "--execution-evidence",
            str(execution_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_task_execution_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-task-execution-gate/v0.1"
    assert gate["status"] == "failed"
    assert gate["next_stage"] == "blocked"


def test_phase11_task_execution_gate_passes_for_started_eos_episode(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    evidence_dir = tmp_path / "eos_evidence"
    evidence_dir.mkdir()
    (evidence_dir / "runtime.log").write_text("started\nclosed\n", encoding="utf-8")
    (evidence_dir / "initial.png").write_bytes(b"fake-png-bytes")
    execution_path = write_task_execution_evidence(
        evidence_dir / "task_execution.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        runtime_log="runtime.log",
        initial_keyframe="initial.png",
    )

    result = generate_phase11_task_execution_gate(package_dir, execution_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_task_execution_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-task-execution-gate/v0.1"
    assert gate["phase"] == "11.1"
    assert gate["status"] == "passed"
    assert gate["package_id"] == "tabletop_pick_place_starter"
    assert gate["task_id"] == "place_object_on_target"
    assert gate["execution"]["runtime_owner"] == "embodied-eval-os"
    assert gate["execution"]["contract_consumed"] is True
    assert gate["execution"]["execution_config_status"] == "generated"
    assert gate["execution"]["episode_status"] == "started"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "executed_episode_evidence_gate"
    assert gate["claim_boundary"] == (
        "EOS task execution integration gate only; not task success, not model quality, "
        "not release approval, and not leaderboard evidence."
    )


def test_phase11_task_execution_gate_blocks_mismatched_package_and_missing_files(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    execution_path = write_task_execution_evidence(
        tmp_path / "task_execution.yaml",
        package_id="wrong_package",
        task_id="wrong_task",
        runtime_log="missing.log",
        initial_keyframe="missing.png",
    )

    result = generate_phase11_task_execution_gate(package_dir, execution_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_task_execution_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "execution evidence package_id mismatch: wrong_package" in gate["blockers"]
    assert "execution evidence task_id mismatch: wrong_task" in gate["blockers"]
    assert "execution runtime_log does not exist: missing.log" in gate["blockers"]
    assert "execution initial keyframe does not exist: missing.png" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_phase11_executed_episode_gate_passes_for_completed_eos_episode(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    evidence_dir = tmp_path / "eos_episode"
    evidence_dir.mkdir()
    (evidence_dir / "runtime.log").write_text("reset\nstep\nclose\n", encoding="utf-8")
    (evidence_dir / "trace.json").write_text('{"steps": 2}\n', encoding="utf-8")
    (evidence_dir / "initial.png").write_bytes(b"initial-frame")
    (evidence_dir / "final.png").write_bytes(b"final-frame")
    episode_path = write_executed_episode_evidence(
        evidence_dir / "executed_episode.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        episode_status="completed",
        trace_uri="trace.json",
        runtime_log="runtime.log",
        initial_keyframe="initial.png",
        final_keyframe="final.png",
    )

    result = generate_phase11_executed_episode_gate(package_dir, episode_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_executed_episode_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-executed-episode-gate/v0.1"
    assert gate["phase"] == "11.2"
    assert gate["status"] == "passed"
    assert gate["package_id"] == "tabletop_pick_place_starter"
    assert gate["task_id"] == "place_object_on_target"
    assert gate["episode"]["runtime_owner"] == "embodied-eval-os"
    assert gate["episode"]["episode_status"] == "completed"
    assert gate["episode"]["trace_uri"] == "trace.json"
    assert gate["episode"]["keyframes"]["final"] == "final.png"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "success_predicate_evaluation_gate"
    assert gate["claim_boundary"] == (
        "Executed episode evidence gate only; not task success, not model quality, "
        "not release approval, and not leaderboard evidence."
    )


def test_phase11_executed_episode_gate_blocks_started_episode_and_missing_artifacts(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    evidence_dir = tmp_path / "eos_episode"
    evidence_dir.mkdir()
    (evidence_dir / "runtime.log").write_text("started\n", encoding="utf-8")
    (evidence_dir / "initial.png").write_bytes(b"initial-frame")
    episode_path = write_executed_episode_evidence(
        evidence_dir / "executed_episode.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        episode_status="started",
        trace_uri="missing_trace.json",
        runtime_log="runtime.log",
        initial_keyframe="initial.png",
        final_keyframe="missing_final.png",
        blockers=["eos_reset_timeout"],
    )

    result = generate_phase11_executed_episode_gate(package_dir, episode_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_executed_episode_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "executed episode_status must be completed; got started" in gate["blockers"]
    assert "executed episode trace artifact does not exist: missing_trace.json" in gate["blockers"]
    assert "executed episode final keyframe does not exist: missing_final.png" in gate["blockers"]
    assert "eos_reset_timeout" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_package_phase11_executed_episode_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    episode_path = write_executed_episode_evidence(
        tmp_path / "executed_episode.yaml",
        package_id="wrong_package",
        task_id="wrong_task",
        episode_status="failed",
        trace_uri="missing_trace.json",
        runtime_log="missing.log",
        initial_keyframe="missing_initial.png",
        final_keyframe="missing_final.png",
    )

    code = main(
        [
            "package",
            "phase11-executed-episode",
            "--package",
            str(package_dir),
            "--episode-evidence",
            str(episode_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_executed_episode_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-executed-episode-gate/v0.1"
    assert gate["status"] == "failed"
    assert gate["next_stage"] == "blocked"


def test_phase11_success_predicate_gate_passes_for_true_eos_predicate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    episode_gate = write_previous_gate(
        package_dir / "evidence" / "phase11_executed_episode_gate.yaml",
        schema_version="phase11-executed-episode-gate/v0.1",
        status="passed",
    )
    predicate_path = write_success_predicate_evidence(
        tmp_path / "predicate.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        predicate_status=True,
        executed_episode_gate=str(episode_gate),
    )

    result = generate_phase11_success_predicate_gate(package_dir, predicate_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_success_predicate_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-success-predicate-gate/v0.1"
    assert gate["phase"] == "11.3"
    assert gate["status"] == "passed"
    assert gate["package_id"] == "tabletop_pick_place_starter"
    assert gate["task_id"] == "place_object_on_target"
    assert gate["predicate"]["evaluator_owner"] == "embodied-eval-os-ebench-adapter"
    assert gate["predicate"]["success_metric"] == "apple_in_bowl"
    assert gate["predicate"]["predicate"] == "object_in_container"
    assert gate["predicate"]["predicate_status"] is True
    assert gate["blockers"] == []
    assert gate["next_stage"] == "post_execution_visual_review_gate"
    assert gate["claim_boundary"] == (
        "Success predicate evaluation gate only; episode-level task success is "
        "predicate-based and is not model quality, release approval, or leaderboard evidence."
    )


def test_phase11_success_predicate_gate_blocks_false_predicate_and_missing_episode_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    predicate_path = write_success_predicate_evidence(
        tmp_path / "predicate.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        predicate_status=False,
        executed_episode_gate="missing_episode_gate.yaml",
        blockers=["predicate_distance_above_threshold"],
    )

    result = generate_phase11_success_predicate_gate(package_dir, predicate_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_success_predicate_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "predicate_status must be true; got False" in gate["blockers"]
    assert "executed episode gate does not exist: missing_episode_gate.yaml" in gate["blockers"]
    assert "predicate_distance_above_threshold" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_package_phase11_success_predicate_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    predicate_path = write_success_predicate_evidence(
        tmp_path / "predicate.yaml",
        package_id="wrong_package",
        task_id="wrong_task",
        predicate_status="blocked",
        executed_episode_gate="missing_episode_gate.yaml",
    )

    code = main(
        [
            "package",
            "phase11-success-predicate",
            "--package",
            str(package_dir),
            "--predicate-evidence",
            str(predicate_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_success_predicate_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-success-predicate-gate/v0.1"
    assert gate["status"] == "failed"
    assert gate["next_stage"] == "blocked"


def test_phase11_post_execution_visual_review_gate_passes_for_clean_room_pass(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    predicate_gate = write_previous_gate(
        package_dir / "evidence" / "phase11_success_predicate_gate.yaml",
        schema_version="phase11-success-predicate-gate/v0.1",
        status="passed",
    )
    evidence_dir = tmp_path / "post_execution_review"
    evidence_dir.mkdir()
    (evidence_dir / "initial.png").write_bytes(b"initial-frame")
    (evidence_dir / "final.png").write_bytes(b"final-frame")
    review_path = write_post_execution_visual_review(
        evidence_dir / "post_execution_visual_review.yaml",
        verdict="PASS",
        initial_image_path="initial.png",
        final_image_path="final.png",
        success_predicate_gate=str(predicate_gate),
    )

    result = generate_phase11_post_execution_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_post_execution_visual_review_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-post-execution-visual-review-gate/v0.1"
    assert gate["phase"] == "11.4"
    assert gate["status"] == "passed"
    assert gate["visual_review"]["reviewer"] == "render-visual-reviewer"
    assert gate["visual_review"]["verdict"] == "PASS"
    assert gate["visual_review"]["initial_image_path"] == "initial.png"
    assert gate["visual_review"]["final_image_path"] == "final.png"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "single_task_automated_release_candidate"
    assert gate["claim_boundary"] == (
        "Post-execution visual review gate only; visual coherence supports inspection "
        "but does not replace predicate success, release approval, or leaderboard evidence."
    )


def test_phase11_post_execution_visual_review_gate_blocks_warn_and_missing_final_frame(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    evidence_dir = tmp_path / "post_execution_review"
    evidence_dir.mkdir()
    (evidence_dir / "initial.png").write_bytes(b"initial-frame")
    review_path = write_post_execution_visual_review(
        evidence_dir / "post_execution_visual_review.yaml",
        verdict="WARN",
        initial_image_path="initial.png",
        final_image_path="missing_final.png",
        success_predicate_gate="missing_predicate_gate.yaml",
    )

    result = generate_phase11_post_execution_visual_review_gate(package_dir, review_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_post_execution_visual_review_gate.yaml")
    assert result.status == "failed"
    assert gate["status"] == "failed"
    assert "post-execution visual review verdict must be PASS; got WARN" in gate["blockers"]
    assert "post-execution final image does not exist: missing_final.png" in gate["blockers"]
    assert "success predicate gate does not exist: missing_predicate_gate.yaml" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_package_phase11_post_execution_visual_review_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    review_path = write_post_execution_visual_review(
        tmp_path / "post_execution_visual_review.yaml",
        verdict="FAIL",
        initial_image_path="missing_initial.png",
        final_image_path="missing_final.png",
        success_predicate_gate="missing_predicate_gate.yaml",
    )

    code = main(
        [
            "package",
            "phase11-post-execution-visual-review",
            "--package",
            str(package_dir),
            "--visual-review",
            str(review_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_post_execution_visual_review_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-post-execution-visual-review-gate/v0.1"
    assert gate["status"] == "failed"
    assert gate["next_stage"] == "blocked"


def test_phase11_single_task_release_candidate_gate_passes_when_all_inputs_pass(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    write_task_contract(package_dir)
    write_phase11_required_gate_set(package_dir, status="passed")
    policy_path = write_release_policy_evidence(
        tmp_path / "release_policy.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        release_policy_status="pass",
    )

    result = generate_phase11_single_task_release_candidate_gate(package_dir, policy_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_single_task_release_candidate_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-single-task-release-candidate-gate/v0.1"
    assert gate["phase"] == "11.5"
    assert gate["status"] == "passed"
    assert gate["package_id"] == "tabletop_pick_place_starter"
    assert gate["task_id"] == "place_object_on_target"
    assert gate["release_policy"]["release_policy_status"] == "pass"
    assert gate["required_gates"]["phase11_visual_review_gate.yaml"]["status"] == "passed"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "small_multi_task_canary"
    assert gate["claim_boundary"] == (
        "Single-task automated release candidate gate only; not public dataset release, "
        "official score release, leaderboard comparability, or multi-task coverage evidence."
    )


def test_phase11_single_task_release_candidate_gate_blocks_research_use_policy(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    write_task_contract(package_dir)
    write_phase11_required_gate_set(package_dir, status="passed")
    policy_path = write_release_policy_evidence(
        tmp_path / "release_policy.yaml",
        package_id="tabletop_pick_place_starter",
        task_id="place_object_on_target",
        release_policy_status="blocked",
        asset_license_status="research-use",
        blockers=["research_use_license_requires_external_approval"],
    )

    result = generate_phase11_single_task_release_candidate_gate(package_dir, policy_path)

    gate = load_yaml(package_dir / "evidence" / "phase11_single_task_release_candidate_gate.yaml")
    assert result.status == "blocked"
    assert gate["status"] == "blocked"
    assert "release policy status must be pass; got blocked" in gate["blockers"]
    assert "research_use_license_requires_external_approval" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_package_phase11_single_task_release_candidate_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    package_dir = scaffold_starter_package(tmp_path / "package")
    policy_path = write_release_policy_evidence(
        tmp_path / "release_policy.yaml",
        package_id="wrong_package",
        task_id="wrong_task",
        release_policy_status="blocked",
    )

    code = main(
        [
            "package",
            "phase11-single-task-rc",
            "--package",
            str(package_dir),
            "--release-policy",
            str(policy_path),
            "--strict",
        ]
    )

    gate = load_yaml(package_dir / "evidence" / "phase11_single_task_release_candidate_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-single-task-release-candidate-gate/v0.1"
    assert gate["status"] == "blocked"
    assert gate["next_stage"] == "blocked"


def test_phase11_small_multi_task_canary_gate_passes_for_three_structured_tasks(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_canary_suite", count=3)
    rc_gate_paths = [
        write_previous_gate(
            suite_dir / "packages" / f"task_{index}" / "evidence" / "phase11_single_task_release_candidate_gate.yaml",
            schema_version="phase11-single-task-release-candidate-gate/v0.1",
            status="passed" if index == 0 else "blocked",
        )
        for index in range(3)
    ]
    canary_path = write_small_multi_task_canary_evidence(
        tmp_path / "small_canary.yaml",
        suite_id="phase11_canary_suite",
        package_rows=[
            small_canary_package_row(
                "task_0",
                rc_gate_paths[0],
                execution_lane_status="completed",
                predicate_evaluation_status="passed",
            ),
            small_canary_package_row(
                "task_1",
                rc_gate_paths[1],
                execution_lane_status="blocked",
                predicate_evaluation_status="blocked",
                blockers=["predicate_evaluator_not_available"],
            ),
            small_canary_package_row(
                "task_2",
                rc_gate_paths[2],
                execution_lane_status="started",
                predicate_evaluation_status="blocked",
                blockers=["research_use_release_blocked"],
            ),
        ],
    )

    result = generate_phase11_small_multi_task_canary_gate(suite_dir, canary_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-small-multi-task-canary-gate/v0.1"
    assert gate["phase"] == "11.6"
    assert gate["status"] == "passed"
    assert gate["suite_id"] == "phase11_canary_suite"
    assert gate["package_count"] == 3
    assert gate["blockers"] == []
    assert gate["next_stage"] == "automated_release_gate"


def test_phase11_small_multi_task_canary_gate_blocks_underfilled_or_unstarted_suite(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_too_small", count=2)
    rc_gate = write_previous_gate(
        suite_dir / "packages" / "task_0" / "evidence" / "phase11_single_task_release_candidate_gate.yaml",
        schema_version="phase11-single-task-release-candidate-gate/v0.1",
        status="passed",
    )
    canary_path = write_small_multi_task_canary_evidence(
        tmp_path / "small_canary.yaml",
        suite_id="phase11_too_small",
        package_rows=[
            small_canary_package_row(
                "task_0",
                rc_gate,
                execution_lane_status="blocked",
                predicate_evaluation_status="blocked",
                blockers=["runtime_blocked"],
            ),
            small_canary_package_row(
                "task_1",
                "missing_rc_gate.yaml",
                execution_lane_status="blocked",
                predicate_evaluation_status="missing",
            ),
        ],
    )

    result = generate_phase11_small_multi_task_canary_gate(suite_dir, canary_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml")
    assert result.status == "blocked"
    assert gate["status"] == "blocked"
    assert "small multi-task canary package_count must be between 3 and 5; got 2" in gate["blockers"]
    assert "at least one package must have execution_lane_status started or completed" in gate["blockers"]
    assert "package task_1 single_task_rc_gate does not exist: missing_rc_gate.yaml" in gate["blockers"]
    assert "package task_1 predicate_evaluation_status must be passed or blocked; got missing" in gate["blockers"]


def test_cli_suite_phase11_small_multi_task_canary_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_cli_suite", count=1)
    canary_path = write_small_multi_task_canary_evidence(
        tmp_path / "small_canary.yaml",
        suite_id="wrong_suite",
        package_rows=[],
    )

    code = main(
        [
            "suite",
            "phase11-small-canary",
            "--suite",
            str(suite_dir),
            "--canary-evidence",
            str(canary_path),
            "--strict",
        ]
    )

    gate = load_yaml(suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-small-multi-task-canary-gate/v0.1"
    assert gate["status"] == "blocked"
    assert gate["next_stage"] == "blocked"


def test_phase11_automated_release_gate_passes_when_release_critical_gates_pass(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_release_suite", count=3)
    small_canary_gate = write_previous_gate(
        suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml",
        schema_version="phase11-small-multi-task-canary-gate/v0.1",
        status="passed",
    )
    release_path = write_automated_release_evidence(
        tmp_path / "automated_release.yaml",
        suite_id="phase11_release_suite",
        small_multi_task_canary_gate=str(small_canary_gate),
        release_critical_gates=release_critical_gate_statuses("pass"),
    )

    result = generate_phase11_automated_release_gate(suite_dir, release_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_automated_release_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-automated-release-gate/v0.1"
    assert gate["phase"] == "11.7"
    assert gate["status"] == "passed"
    assert gate["release_status"] == "passed"
    assert gate["suite_id"] == "phase11_release_suite"
    assert gate["release_critical_gates"]["license_policy"] == "pass"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "release_candidate_passed"
    assert gate["claim_boundary"] == (
        "Automated release gate only; release candidate passed is not official "
        "leaderboard comparability or public dataset publication without external approval."
    )


def test_phase11_automated_release_gate_blocks_license_policy_and_known_blockers(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_release_suite", count=3)
    small_canary_gate = write_previous_gate(
        suite_dir / "evidence" / "phase11_small_multi_task_canary_gate.yaml",
        schema_version="phase11-small-multi-task-canary-gate/v0.1",
        status="blocked",
    )
    statuses = release_critical_gate_statuses("pass")
    statuses["license_policy"] = "blocked"
    release_path = write_automated_release_evidence(
        tmp_path / "automated_release.yaml",
        suite_id="phase11_release_suite",
        small_multi_task_canary_gate=str(small_canary_gate),
        release_critical_gates=statuses,
        known_blockers=["research_use_license_requires_external_approval"],
    )

    result = generate_phase11_automated_release_gate(suite_dir, release_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_automated_release_gate.yaml")
    assert result.status == "blocked"
    assert gate["status"] == "blocked"
    assert gate["release_status"] == "blocked"
    assert "small multi-task canary gate status must be passed; got blocked" in gate["blockers"]
    assert "release-critical gate license_policy must be pass; got blocked" in gate["blockers"]
    assert "known_blockers must be empty; got 1" in gate["blockers"]
    assert "research_use_license_requires_external_approval" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_suite_phase11_automated_release_strict_blocks_failed_gate(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_release_cli", count=3)
    release_path = write_automated_release_evidence(
        tmp_path / "automated_release.yaml",
        suite_id="wrong_suite",
        small_multi_task_canary_gate="missing_small_canary_gate.yaml",
        release_critical_gates=release_critical_gate_statuses("blocked"),
    )

    code = main(
        [
            "suite",
            "phase11-release",
            "--suite",
            str(suite_dir),
            "--release-evidence",
            str(release_path),
            "--strict",
        ]
    )

    gate = load_yaml(suite_dir / "evidence" / "phase11_automated_release_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-automated-release-gate/v0.1"
    assert gate["status"] == "blocked"
    assert gate["next_stage"] == "blocked"


def test_phase11_phase12_readiness_gate_passes_when_release_policy_is_clear(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_readiness_suite", count=3)
    gate_refs = write_phase11_readiness_gate_refs(suite_dir, status="passed")
    readiness_path = write_phase11_readiness_evidence(
        tmp_path / "phase11_readiness.yaml",
        suite_id="phase11_readiness_suite",
        latest_gates=gate_refs,
        phase12_allowed=True,
        policy_release_status="pass",
        redistribution_approval=True,
    )

    result = generate_phase11_phase12_readiness_gate(suite_dir, readiness_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_phase12_readiness_gate.yaml")
    assert result.status == "passed"
    assert gate["schema_version"] == "phase11-phase12-readiness-gate/v0.1"
    assert gate["phase"] == "11.8"
    assert gate["status"] == "passed"
    assert gate["phase12_allowed"] is True
    assert gate["suite_id"] == "phase11_readiness_suite"
    assert gate["blockers"] == []
    assert gate["next_stage"] == "phase12_registry_readiness"
    assert gate["claim_boundary"] == (
        "Phase 11.8 readiness gate only; it allows Phase 12 planning scope when "
        "all referenced evidence and release-policy blockers are clear, but it is "
        "not public dataset publication or leaderboard comparability."
    )


def test_phase11_phase12_readiness_gate_blocks_policy_deferred_state(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_policy_blocked", count=3)
    gate_refs = write_phase11_readiness_gate_refs(suite_dir, status="blocked")
    readiness_path = write_phase11_readiness_evidence(
        tmp_path / "phase11_readiness.yaml",
        suite_id="phase11_policy_blocked",
        latest_gates=gate_refs,
        phase12_allowed=False,
        policy_release_status="blocked",
        redistribution_approval=False,
        known_policy_blockers=[
            "ebench_assets_research_use_only",
            "redistribution_approval_missing",
        ],
    )

    result = generate_phase11_phase12_readiness_gate(suite_dir, readiness_path)

    gate = load_yaml(suite_dir / "evidence" / "phase11_phase12_readiness_gate.yaml")
    assert result.status == "blocked"
    assert gate["status"] == "blocked"
    assert gate["phase12_allowed"] is False
    assert gate["phase12_status"] == "deferred"
    assert gate["manual_blockers"] == []
    assert gate["unknown_blockers"] == []
    assert "phase12_allowed must be true before Phase 12 can start" in gate["blockers"]
    assert "release policy must be pass before Phase 12 can start; got blocked" in gate["blockers"]
    assert "redistribution_approval must be true before Phase 12 can start" in gate["blockers"]
    assert "ebench_assets_research_use_only" in gate["blockers"]
    assert "redistribution_approval_missing" in gate["blockers"]
    assert gate["next_stage"] == "blocked"


def test_cli_suite_phase11_readiness_strict_blocks_deferred_phase12(
    tmp_path: Path,
) -> None:
    suite_dir = write_suite_manifest(tmp_path / "suite", suite_id="phase11_readiness_cli", count=3)
    gate_refs = write_phase11_readiness_gate_refs(suite_dir, status="passed")
    readiness_path = write_phase11_readiness_evidence(
        tmp_path / "phase11_readiness.yaml",
        suite_id="phase11_readiness_cli",
        latest_gates=gate_refs,
        phase12_allowed=False,
        policy_release_status="blocked",
        redistribution_approval=False,
    )

    code = main(
        [
            "suite",
            "phase11-readiness",
            "--suite",
            str(suite_dir),
            "--readiness-evidence",
            str(readiness_path),
            "--strict",
        ]
    )

    gate = load_yaml(suite_dir / "evidence" / "phase11_phase12_readiness_gate.yaml")
    assert code == 1
    assert gate["schema_version"] == "phase11-phase12-readiness-gate/v0.1"
    assert gate["phase"] == "11.8"
    assert gate["status"] == "blocked"
    assert gate["next_stage"] == "blocked"


def write_visual_review(
    path: Path,
    *,
    verdict: str,
    image_path: str,
    reviewer: str = "render-visual-reviewer",
    render_metadata_path: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "phase11-visual-review/v0.1",
        "reviewer": reviewer,
        "review_mode": "clean_room_visual_skill",
        "image_path": image_path,
        "verdict": verdict,
        "visible_evidence": ["target object visible"],
        "retake_recommendation": "not_required" if verdict == "PASS" else "retake",
    }
    if render_metadata_path is not None:
        payload["render_metadata_path"] = render_metadata_path
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return path


def write_task_execution_evidence(
    path: Path,
    *,
    package_id: str,
    task_id: str,
    runtime_log: str,
    initial_keyframe: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-eos-task-execution/v0.1",
                "runtime_owner": "embodied-eval-os",
                "package_id": package_id,
                "task_id": task_id,
                "contract_consumed": True,
                "execution_config_status": "generated",
                "episode_status": "started",
                "trace_uri": "eos://phase11/tabletop_pick_place_starter/trace.json",
                "runtime_log": runtime_log,
                "lifecycle": {"reset": "passed", "step": "passed", "close": "passed"},
                "keyframes": {"initial": initial_keyframe},
                "blockers": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_executed_episode_evidence(
    path: Path,
    *,
    package_id: str,
    task_id: str,
    episode_status: str,
    trace_uri: str,
    runtime_log: str,
    initial_keyframe: str,
    final_keyframe: str,
    blockers: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-executed-episode-evidence/v0.1",
                "runtime_owner": "embodied-eval-os",
                "package_id": package_id,
                "task_id": task_id,
                "episode_status": episode_status,
                "trace_uri": trace_uri,
                "runtime_log": runtime_log,
                "keyframes": {"initial": initial_keyframe, "final": final_keyframe},
                "final_state": {"status": "captured"},
                "blockers": blockers or [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_post_execution_visual_review(
    path: Path,
    *,
    verdict: str,
    initial_image_path: str,
    final_image_path: str,
    success_predicate_gate: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-post-execution-visual-review/v0.1",
                "reviewer": "render-visual-reviewer",
                "review_mode": "clean_room_visual_skill",
                "initial_image_path": initial_image_path,
                "final_image_path": final_image_path,
                "verdict": verdict,
                "visible_evidence": [
                    "initial frame shows task setup",
                    "final frame shows task terminal state",
                ],
                "success_predicate_gate": success_predicate_gate,
                "retake_recommendation": "not_required" if verdict == "PASS" else "retake",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_automated_release_evidence(
    path: Path,
    *,
    suite_id: str,
    small_multi_task_canary_gate: str,
    release_critical_gates: dict[str, str],
    known_blockers: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-automated-release-evidence/v0.1",
                "suite_id": suite_id,
                "small_multi_task_canary_gate": small_multi_task_canary_gate,
                "release_critical_gates": release_critical_gates,
                "known_blockers": known_blockers or [],
                "blockers": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_phase11_readiness_evidence(
    path: Path,
    *,
    suite_id: str,
    latest_gates: dict[str, str],
    phase12_allowed: bool,
    policy_release_status: str,
    redistribution_approval: bool,
    known_policy_blockers: list[str] | None = None,
    manual_blockers: list[str] | None = None,
    unknown_blockers: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-phase12-readiness/v0.1",
                "phase": "11.8",
                "status": "passed" if phase12_allowed else "blocked",
                "phase12_status": "allowed" if phase12_allowed else "deferred",
                "suite_id": suite_id,
                "latest_gates": latest_gates,
                "technical_gate_summary": {
                    "package_check": "pass",
                    "asset_lock_check": "pass",
                    "adapter_contract": "pass",
                    "overview_visual_review": "pass",
                    "eos_execution": "pass",
                    "completed_episode": "pass",
                    "success_predicate": "pass",
                    "post_execution_visual_review": "pass",
                    "material_runtime_closure": "pass",
                },
                "policy_gate_summary": {
                    "release_policy": policy_release_status,
                    "asset_license_status": "redistributable"
                    if redistribution_approval
                    else "research-use",
                    "redistribution_approval": redistribution_approval,
                },
                "manual_blockers": manual_blockers or [],
                "unknown_blockers": unknown_blockers or [],
                "known_policy_blockers": known_policy_blockers or [],
                "known_non_policy_blockers": [],
                "phase12_allowed": phase12_allowed,
                "claim_boundary": "Phase 11.8 readiness evidence only.",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_phase11_readiness_gate_refs(suite_dir: Path, *, status: str) -> dict[str, str]:
    evidence_dir = suite_dir / "evidence"
    refs = {
        "apple_to_bowl_single_task_rc": (
            "apple_phase11_single_task_release_candidate_gate.yaml",
            "phase11-single-task-release-candidate-gate/v0.1",
        ),
        "soap_to_dish_single_task_rc": (
            "soap_phase11_single_task_release_candidate_gate.yaml",
            "phase11-single-task-release-candidate-gate/v0.1",
        ),
        "remote_to_holder_single_task_rc": (
            "remote_phase11_single_task_release_candidate_gate.yaml",
            "phase11-single-task-release-candidate-gate/v0.1",
        ),
        "small_multi_task_canary": (
            "phase11_small_multi_task_canary_gate.yaml",
            "phase11-small-multi-task-canary-gate/v0.1",
        ),
        "automated_release": (
            "phase11_automated_release_gate.yaml",
            "phase11-automated-release-gate/v0.1",
        ),
    }
    output: dict[str, str] = {}
    for key, (filename, schema_version) in refs.items():
        path = write_previous_gate(evidence_dir / filename, schema_version=schema_version, status=status)
        output[key] = str(path)
    return output


def release_critical_gate_statuses(status: str) -> dict[str, str]:
    return {
        "package_check": status,
        "asset_lock_check": status,
        "adapter_contract": status,
        "visual_review": status,
        "episode_execution": status,
        "predicate_evaluation": status,
        "license_policy": status,
    }


def write_small_multi_task_canary_evidence(
    path: Path,
    *,
    suite_id: str,
    package_rows: list[dict],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-small-multi-task-canary/v0.1",
                "suite_id": suite_id,
                "packages": package_rows,
                "blockers": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def small_canary_package_row(
    package_id: str,
    single_task_rc_gate: str | Path,
    *,
    execution_lane_status: str,
    predicate_evaluation_status: str,
    blockers: list[str] | None = None,
) -> dict:
    return {
        "package_id": package_id,
        "single_task_rc_gate": str(single_task_rc_gate),
        "real_asset_package": True,
        "task_contract": True,
        "overview_visual_review": "passed",
        "execution_lane_status": execution_lane_status,
        "predicate_evaluation_status": predicate_evaluation_status,
        "blockers": blockers or [],
    }


def write_suite_manifest(path: Path, *, suite_id: str, count: int) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "evidence").mkdir(exist_ok=True)
    packages = [
        {"package_id": f"task_{index}", "path": f"packages/task_{index}"}
        for index in range(count)
    ]
    (path / "suite_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-suite/v0.2",
                "suite_id": suite_id,
                "packages": packages,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_release_policy_evidence(
    path: Path,
    *,
    package_id: str,
    task_id: str,
    release_policy_status: str,
    asset_license_status: str = "redistributable",
    blockers: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-release-policy/v0.1",
                "policy_owner": "scenario-forge-policy-gate",
                "package_id": package_id,
                "task_id": task_id,
                "release_policy_status": release_policy_status,
                "asset_license_status": asset_license_status,
                "redistribution_approval": release_policy_status == "pass",
                "blockers": blockers or [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_phase11_required_gate_set(package_dir: Path, *, status: str) -> None:
    gates = {
        "phase11_visual_review_gate.yaml": "phase11-visual-review-gate/v0.1",
        "phase11_task_execution_gate.yaml": "phase11-task-execution-gate/v0.1",
        "phase11_executed_episode_gate.yaml": "phase11-executed-episode-gate/v0.1",
        "phase11_success_predicate_gate.yaml": "phase11-success-predicate-gate/v0.1",
        "phase11_post_execution_visual_review_gate.yaml": (
            "phase11-post-execution-visual-review-gate/v0.1"
        ),
    }
    for filename, schema_version in gates.items():
        write_previous_gate(package_dir / "evidence" / filename, schema_version=schema_version, status=status)


def write_task_contract(package_dir: Path) -> Path:
    path = package_dir / "task" / "task_contract.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-task-contract/v0.1",
                "task_id": "place_object_on_target",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_success_predicate_evidence(
    path: Path,
    *,
    package_id: str,
    task_id: str,
    predicate_status: bool | str,
    executed_episode_gate: str,
    blockers: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "phase11-success-predicate-evaluation/v0.1",
                "evaluator_owner": "embodied-eval-os-ebench-adapter",
                "package_id": package_id,
                "task_id": task_id,
                "success_metric": "apple_in_bowl",
                "predicate": "object_in_container",
                "object": "apple_001",
                "container": "bowl_001",
                "predicate_status": predicate_status,
                "executed_episode_gate": executed_episode_gate,
                "measurement": {"apple_container_relation": "inside"},
                "blockers": blockers or [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def write_previous_gate(
    path: Path,
    *,
    schema_version: str,
    status: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"schema_version": schema_version, "status": status},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenario_forge.assets.lock import AssetLockError, check_asset_lock, generate_asset_lock, write_asset_lock
from scenario_forge.assets.manifest import AssetManifestError
from scenario_forge.adapters.ebench import EBenchExportError, export_ebench_package, export_ebench_suite
from scenario_forge.adapters.real2sim import Real2SimImportError, import_real2sim_result
from scenario_forge.generation.layout.layout_planner import LayoutPlanError, plan_layout_artifacts
from scenario_forge.generation.cousins.cousin_generator import (
    CousinGenerationError,
    generate_cousin_packages,
)
from scenario_forge.generation.suite.suite_generator import (
    SuiteGenerationError,
    generate_suite_from_spec,
)
from scenario_forge.evaluation.suite_quality_evidence import (
    SuiteQualityEvidenceError,
    generate_suite_quality_evidence,
)
from scenario_forge.evaluation.phase10x_gates import (
    Phase10xEvidenceError,
    generate_phase10x_evidence,
)
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
from scenario_forge.artifacts.registry import (
    Phase12RegistryError,
    generate_phase12_registry_artifacts,
)
from scenario_forge.generation.ebench_canary.apple_to_bowl import generate_apple_to_bowl_canary
from scenario_forge.generation.ebench_canary.single_object_fixture import (
    generate_single_object_fixture_canary,
)
from scenario_forge.generation.image_grounded import (
    Phase13ImageTaskError,
    generate_image_grounded_task_package,
)
from scenario_forge.package import PackageError, load_package_manifest, validate_package
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import USDSceneCompilerError, compile_usd_scene
from scenario_forge.task.task_compiler import TaskCompileError, compile_task_artifacts
from scenario_forge.validation.usd_checks import check_usd_scene
from scenario_forge.generation.workflows.workflow_composer import (
    WorkflowComposeError,
    compose_workflow_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scenario-forge",
        description="Generate and validate evaluation-ready embodied scenario packages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    package_parser = subparsers.add_parser("package", help="Scenario package commands")
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)

    scaffold_parser = package_subparsers.add_parser("scaffold", help="Create a starter package")
    scaffold_parser.add_argument("--out", required=True, help="Output package directory")

    check_parser = package_subparsers.add_parser("check", help="Validate a scenario package")
    check_parser.add_argument("package_dir", help="Package directory containing manifest.yaml")
    check_parser.add_argument(
        "--require-asset-lock",
        action="store_true",
        help="Fail if locks/asset_lock.yaml is missing or invalid",
    )

    phase11_visual_parser = package_subparsers.add_parser(
        "phase11-visual-review",
        help="Generate Phase 11.0 automated visual review gate evidence",
    )
    phase11_visual_parser.add_argument("--package", required=True, help="Package directory")
    phase11_visual_parser.add_argument(
        "--visual-review",
        required=True,
        help="phase11-visual-review/v0.1 YAML emitted from render-visual-reviewer",
    )
    phase11_visual_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.0 visual review gate passes",
    )

    phase11_task_execution_parser = package_subparsers.add_parser(
        "phase11-task-execution",
        help="Generate Phase 11.1 EOS task execution integration gate evidence",
    )
    phase11_task_execution_parser.add_argument("--package", required=True, help="Package directory")
    phase11_task_execution_parser.add_argument(
        "--execution-evidence",
        required=True,
        help="phase11-eos-task-execution/v0.1 YAML emitted by EOS",
    )
    phase11_task_execution_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.1 EOS task execution gate passes",
    )

    phase11_executed_episode_parser = package_subparsers.add_parser(
        "phase11-executed-episode",
        help="Generate Phase 11.2 executed episode evidence gate",
    )
    phase11_executed_episode_parser.add_argument("--package", required=True, help="Package directory")
    phase11_executed_episode_parser.add_argument(
        "--episode-evidence",
        required=True,
        help="phase11-executed-episode-evidence/v0.1 YAML emitted by EOS",
    )
    phase11_executed_episode_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.2 executed episode gate passes",
    )

    phase11_success_predicate_parser = package_subparsers.add_parser(
        "phase11-success-predicate",
        help="Generate Phase 11.3 success predicate evaluation gate",
    )
    phase11_success_predicate_parser.add_argument("--package", required=True, help="Package directory")
    phase11_success_predicate_parser.add_argument(
        "--predicate-evidence",
        required=True,
        help="phase11-success-predicate-evaluation/v0.1 YAML emitted by EOS/EBench",
    )
    phase11_success_predicate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.3 success predicate gate passes",
    )

    phase11_post_execution_visual_parser = package_subparsers.add_parser(
        "phase11-post-execution-visual-review",
        help="Generate Phase 11.4 post-execution visual review gate",
    )
    phase11_post_execution_visual_parser.add_argument(
        "--package",
        required=True,
        help="Package directory",
    )
    phase11_post_execution_visual_parser.add_argument(
        "--visual-review",
        required=True,
        help="phase11-post-execution-visual-review/v0.1 YAML emitted by render-visual-reviewer",
    )
    phase11_post_execution_visual_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.4 post-execution visual gate passes",
    )

    phase11_single_task_rc_parser = package_subparsers.add_parser(
        "phase11-single-task-rc",
        help="Generate Phase 11.5 single-task automated release candidate gate",
    )
    phase11_single_task_rc_parser.add_argument("--package", required=True, help="Package directory")
    phase11_single_task_rc_parser.add_argument(
        "--release-policy",
        required=True,
        help="phase11-release-policy/v0.1 YAML emitted by the release policy gate",
    )
    phase11_single_task_rc_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.5 single-task RC gate passes",
    )

    assets_parser = subparsers.add_parser("assets", help="Asset manifest and lock commands")
    assets_subparsers = assets_parser.add_subparsers(dest="assets_command", required=True)

    assets_lock_parser = assets_subparsers.add_parser("lock", help="Generate asset_lock.yaml")
    assets_lock_parser.add_argument("package_dir", help="Package directory")

    assets_check_parser = assets_subparsers.add_parser("check", help="Validate asset_lock.yaml")
    assets_check_parser.add_argument("package_dir", help="Package directory")

    scene_parser = subparsers.add_parser("scene", help="USD scene compiler commands")
    scene_subparsers = scene_parser.add_subparsers(dest="scene_command", required=True)

    scene_compile_parser = scene_subparsers.add_parser(
        "compile", help="Compile scene instances to scene/main.usda"
    )
    scene_compile_parser.add_argument("--instances", required=True, help="scene/instances.yaml")
    scene_compile_parser.add_argument("--asset-lock", required=True, help="locks/asset_lock.yaml")
    scene_compile_parser.add_argument("--out", required=True, help="Output USDA scene path")

    task_parser = subparsers.add_parser("task", help="Task graph and metric compiler commands")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)

    task_compile_parser = task_subparsers.add_parser(
        "compile", help="Compile task graph, predicates, safety rules, and metrics"
    )
    task_compile_parser.add_argument("--package", required=True, help="Package directory")
    task_compile_parser.add_argument("--family", default="pick_place", help="Task family")

    workflow_parser = subparsers.add_parser("workflow", help="Workflow generation commands")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", required=True)

    workflow_compose_parser = workflow_subparsers.add_parser(
        "compose", help="Compose workflow task artifacts from a domain template"
    )
    workflow_compose_parser.add_argument("--package", required=True, help="Package directory")
    workflow_compose_parser.add_argument("--family", required=True, help="Workflow task family")
    workflow_compose_parser.add_argument(
        "--robot-profile", default="franka_panda_tabletop_v1", help="Robot profile id"
    )
    workflow_compose_parser.add_argument(
        "--binding",
        action="append",
        default=[],
        help="Workflow role binding in role=instance_id form; may be repeated",
    )

    layout_parser = subparsers.add_parser("layout", help="Layout generation commands")
    layout_subparsers = layout_parser.add_subparsers(dest="layout_command", required=True)

    layout_plan_parser = layout_subparsers.add_parser(
        "plan", help="Plan deterministic scene layout from required assets"
    )
    layout_plan_parser.add_argument("--package", required=True, help="Package directory")
    layout_plan_parser.add_argument("--difficulty", default="easy", help="Difficulty profile")

    real2sim_parser = subparsers.add_parser("real2sim", help="Real-to-sim import commands")
    real2sim_subparsers = real2sim_parser.add_subparsers(dest="real2sim_command", required=True)

    real2sim_import_parser = real2sim_subparsers.add_parser(
        "import", help="Import a real2sim-result/v0.1 YAML into a package"
    )
    real2sim_import_parser.add_argument("--result", required=True, help="real2sim result YAML")
    real2sim_import_parser.add_argument("--out", required=True, help="Output package directory")

    real2sim_cousins_parser = real2sim_subparsers.add_parser(
        "cousins", help="Generate digital cousin packages from a cousin plan"
    )
    real2sim_cousins_parser.add_argument("--package", required=True, help="Base package")
    real2sim_cousins_parser.add_argument("--plan", required=True, help="cousin-plan/v0.1 YAML")
    real2sim_cousins_parser.add_argument("--out", required=True, help="Output suite directory")

    image_task_parser = subparsers.add_parser(
        "image-task",
        help="Phase 13 image + goal existing-asset task package factory commands",
    )
    image_task_subparsers = image_task_parser.add_subparsers(
        dest="image_task_command",
        required=True,
    )
    image_task_compile_parser = image_task_subparsers.add_parser(
        "compile",
        help="Compile image-task-request and image-to-scene-result contracts into a package candidate",
    )
    image_task_compile_parser.add_argument(
        "--request",
        required=True,
        help="image-task-request/v0.1 YAML",
    )
    image_task_compile_parser.add_argument(
        "--scene-result",
        required=True,
        help="image-to-scene-result/v0.1 YAML emitted by an external grounding adapter",
    )
    image_task_compile_parser.add_argument(
        "--registry-snapshot",
        required=True,
        help="Phase 12 registry_snapshot.yaml",
    )
    image_task_compile_parser.add_argument("--out", required=True, help="Output package directory")
    image_task_compile_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless local Phase 13 static candidate gates pass",
    )

    suite_parser = subparsers.add_parser("suite", help="Benchmark suite generation commands")
    suite_subparsers = suite_parser.add_subparsers(dest="suite_command", required=True)

    suite_generate_parser = suite_subparsers.add_parser(
        "generate", help="Generate a benchmark suite from suite-spec/v0.2"
    )
    suite_generate_parser.add_argument("--spec", required=True, help="suite-spec/v0.2 YAML")
    suite_generate_parser.add_argument("--out", required=True, help="Output suite directory")

    suite_quality_parser = suite_subparsers.add_parser(
        "quality", help="Generate suite quality evidence"
    )
    suite_quality_parser.add_argument("--suite", required=True, help="Suite directory")

    suite_phase10x_parser = suite_subparsers.add_parser(
        "phase10x", help="Generate Phase 10.x EOS handoff gate evidence"
    )
    suite_phase10x_parser.add_argument("--suite", required=True, help="Suite directory")
    suite_phase10x_parser.add_argument(
        "--eos-python",
        help="EOS project Python interpreter used to record static-import environment metadata",
    )
    suite_phase10x_parser.add_argument(
        "--external-evidence",
        help="External input A/B evidence YAML for LabBuilder / SimFoundry-style lanes",
    )
    suite_phase10x_parser.add_argument(
        "--golden-evidence",
        help="Previously generated Phase 10.1 golden task pack evidence YAML for RC suites",
    )
    suite_phase10x_parser.add_argument(
        "--runtime-smoke",
        help="Downstream EOS / EBench runtime-smoke evidence YAML",
    )
    suite_phase10x_parser.add_argument("--rc-min-packages", type=int, default=50)
    suite_phase10x_parser.add_argument("--rc-max-packages", type=int, default=100)
    suite_phase10x_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless all Phase 10.x gates pass",
    )

    suite_phase11_small_canary_parser = suite_subparsers.add_parser(
        "phase11-small-canary",
        help="Generate Phase 11.6 small multi-task canary gate evidence",
    )
    suite_phase11_small_canary_parser.add_argument("--suite", required=True, help="Suite directory")
    suite_phase11_small_canary_parser.add_argument(
        "--canary-evidence",
        required=True,
        help="phase11-small-multi-task-canary/v0.1 YAML",
    )
    suite_phase11_small_canary_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.6 small multi-task canary gate passes",
    )

    suite_phase11_release_parser = suite_subparsers.add_parser(
        "phase11-release",
        help="Generate Phase 11.7 automated release gate evidence",
    )
    suite_phase11_release_parser.add_argument("--suite", required=True, help="Suite directory")
    suite_phase11_release_parser.add_argument(
        "--release-evidence",
        required=True,
        help="phase11-automated-release-evidence/v0.1 YAML",
    )
    suite_phase11_release_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.7 automated release gate passes",
    )

    suite_phase11_readiness_parser = suite_subparsers.add_parser(
        "phase11-readiness",
        help="Generate Phase 11.8 Phase-12 readiness gate evidence",
    )
    suite_phase11_readiness_parser.add_argument("--suite", required=True, help="Suite directory")
    suite_phase11_readiness_parser.add_argument(
        "--readiness-evidence",
        required=True,
        help="phase11-phase12-readiness/v0.1 YAML",
    )
    suite_phase11_readiness_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless the Phase 11.8 readiness gate passes",
    )

    suite_phase12_parser = suite_subparsers.add_parser(
        "phase12",
        help="Generate Phase 12.0-12.6 registry, viewer, handoff, and policy evidence",
    )
    suite_phase12_parser.add_argument("--suite", required=True, help="Suite directory")
    suite_phase12_parser.add_argument(
        "--gate-index",
        required=True,
        help="phase11-current-gate-index/v0.1 YAML retained from Phase 11.8",
    )
    suite_phase12_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless all Phase 12.0-12.6 gates pass",
    )

    export_parser = subparsers.add_parser("export", help="Adapter export commands")
    export_subparsers = export_parser.add_subparsers(dest="export_command", required=True)

    ebench_export_parser = export_subparsers.add_parser(
        "ebench", help="Export EBench-compatible adapter artifacts"
    )
    ebench_group = ebench_export_parser.add_mutually_exclusive_group(required=True)
    ebench_group.add_argument("--package", help="Single package directory")
    ebench_group.add_argument("--suite", help="Suite directory containing suite_manifest.yaml")

    ebench_parser = subparsers.add_parser("ebench", help="EBench-specific canary commands")
    ebench_subparsers = ebench_parser.add_subparsers(dest="ebench_command", required=True)
    ebench_canary_parser = ebench_subparsers.add_parser("canary", help="Generate EBench canary packages")
    ebench_canary_subparsers = ebench_canary_parser.add_subparsers(
        dest="ebench_canary_command", required=True
    )
    apple_to_bowl_parser = ebench_canary_subparsers.add_parser(
        "apple-to-bowl",
        help="Generate a real-asset apple-to-bowl canary package",
    )
    apple_to_bowl_parser.add_argument("--asset-sources", required=True, help="Official asset source YAML")
    apple_to_bowl_parser.add_argument("--out", required=True, help="Output package directory")
    single_object_fixture_parser = ebench_canary_subparsers.add_parser(
        "single-object-fixture",
        help="Generate a real-asset EBench canary with one object and a target scene fixture",
    )
    single_object_fixture_parser.add_argument(
        "--asset-sources",
        required=True,
        help="Official asset source YAML with fixture_task metadata",
    )
    single_object_fixture_parser.add_argument("--out", required=True, help="Output package directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "package" and args.package_command == "scaffold":
        out_dir = scaffold_starter_package(Path(args.out))
        print(f"Created starter package: {out_dir}")
        return 0

    if args.command == "package" and args.package_command == "check":
        report = validate_package(Path(args.package_dir), require_asset_lock=args.require_asset_lock)
        for message in report.messages:
            print(message)
        if report.ok:
            print("Package OK")
            return 0
        return 1

    if args.command == "package" and args.package_command == "phase11-visual-review":
        result = generate_phase11_visual_review_gate(
            Path(args.package),
            Path(args.visual_review),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.0 visual review gate written: {result.evidence_path}")
        print(f"Phase 11.0 visual review gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.0 visual review strict gate did not pass")
            return 1
        return 0

    if args.command == "package" and args.package_command == "phase11-task-execution":
        result = generate_phase11_task_execution_gate(
            Path(args.package),
            Path(args.execution_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.1 task execution gate written: {result.evidence_path}")
        print(f"Phase 11.1 task execution gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.1 task execution strict gate did not pass")
            return 1
        return 0

    if args.command == "package" and args.package_command == "phase11-executed-episode":
        result = generate_phase11_executed_episode_gate(
            Path(args.package),
            Path(args.episode_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.2 executed episode gate written: {result.evidence_path}")
        print(f"Phase 11.2 executed episode gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.2 executed episode strict gate did not pass")
            return 1
        return 0

    if args.command == "package" and args.package_command == "phase11-success-predicate":
        result = generate_phase11_success_predicate_gate(
            Path(args.package),
            Path(args.predicate_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.3 success predicate gate written: {result.evidence_path}")
        print(f"Phase 11.3 success predicate gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.3 success predicate strict gate did not pass")
            return 1
        return 0

    if (
        args.command == "package"
        and args.package_command == "phase11-post-execution-visual-review"
    ):
        result = generate_phase11_post_execution_visual_review_gate(
            Path(args.package),
            Path(args.visual_review),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.4 post-execution visual review gate written: {result.evidence_path}")
        print(f"Phase 11.4 post-execution visual review gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.4 post-execution visual review strict gate did not pass")
            return 1
        return 0

    if args.command == "package" and args.package_command == "phase11-single-task-rc":
        result = generate_phase11_single_task_release_candidate_gate(
            Path(args.package),
            Path(args.release_policy),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.5 single-task RC gate written: {result.evidence_path}")
        print(f"Phase 11.5 single-task RC gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.5 single-task RC strict gate did not pass")
            return 1
        return 0

    if args.command == "assets" and args.assets_command == "lock":
        try:
            lock_path = write_asset_lock(
                Path(args.package_dir), generate_asset_lock(Path(args.package_dir))
            )
        except (AssetLockError, AssetManifestError) as exc:
            print(exc)
            return 1
        print(f"Asset lock written: {lock_path}")
        return 0

    if args.command == "assets" and args.assets_command == "check":
        package_dir = Path(args.package_dir)
        report = check_asset_lock(package_dir, scene_paths=_package_scene_paths(package_dir))
        for message in report.messages:
            print(message)
        if report.ok:
            print("Asset lock OK")
            return 0
        return 1

    if args.command == "scene" and args.scene_command == "compile":
        instances_path = Path(args.instances)
        asset_lock_path = Path(args.asset_lock)
        out_path = Path(args.out)
        package_dir = _package_root_from_asset_lock(asset_lock_path)
        try:
            result = compile_usd_scene(
                package_root=package_dir,
                instances_path=instances_path,
                asset_lock_path=asset_lock_path,
                out_path=out_path,
            )
        except USDSceneCompilerError as exc:
            print(exc)
            return 1

        predicates_path = package_dir / "task" / "predicates.yaml"
        static_report = check_usd_scene(
            package_root=package_dir,
            scene_path=result.path,
            asset_lock_path=asset_lock_path,
            instances_path=instances_path,
            predicates_path=predicates_path if predicates_path.exists() else None,
        )
        for message in static_report.messages:
            print(message)
        if not static_report.ok:
            return 1

        print(f"Scene written: {result.path}")
        print("USD static check OK")
        return 0

    if args.command == "task" and args.task_command == "compile":
        try:
            result = compile_task_artifacts(Path(args.package), task_family=args.family)
        except TaskCompileError as exc:
            print(exc)
            return 1
        print(f"Task artifacts written: {result.package_root}")
        for artifact in result.artifacts:
            print(artifact)
        return 0

    if args.command == "workflow" and args.workflow_command == "compose":
        try:
            result = compose_workflow_artifacts(
                Path(args.package),
                task_family=args.family,
                robot_profile=args.robot_profile,
                bindings=_parse_bindings(args.binding),
            )
        except WorkflowComposeError as exc:
            print(exc)
            return 1
        print(f"Workflow artifacts written: {result.package_root}")
        for artifact in result.artifacts:
            print(artifact)
        return 0

    if args.command == "layout" and args.layout_command == "plan":
        try:
            result = plan_layout_artifacts(Path(args.package), difficulty=args.difficulty)
        except LayoutPlanError as exc:
            print(exc)
            return 1
        print(f"Layout artifacts written: {result.package_root}")
        for artifact in result.artifacts:
            print(artifact)
        return 0

    if args.command == "real2sim" and args.real2sim_command == "import":
        try:
            result = import_real2sim_result(Path(args.result), Path(args.out))
        except Real2SimImportError as exc:
            print(exc)
            return 1
        print(f"Real2Sim package imported: {result.package_root}")
        for artifact in result.artifacts:
            print(artifact)
        return 0

    if args.command == "real2sim" and args.real2sim_command == "cousins":
        try:
            result = generate_cousin_packages(Path(args.package), Path(args.plan), Path(args.out))
        except CousinGenerationError as exc:
            print(exc)
            return 1
        print(f"Real2Sim cousin suite written: {result.suite_root}")
        for package in result.packages:
            print(package)
        return 0

    if args.command == "image-task" and args.image_task_command == "compile":
        try:
            result = generate_image_grounded_task_package(
                request_path=Path(args.request),
                scene_result_path=Path(args.scene_result),
                registry_snapshot_path=Path(args.registry_snapshot),
                package_root=Path(args.out),
            )
        except Phase13ImageTaskError as exc:
            print(exc)
            return 1
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 13 image-task package candidate: {result.package_root}")
        print(f"Phase 13 status: {result.status}")
        print(f"Phase 13 current gate: {result.evidence_path}")
        if args.strict and result.status == "blocked":
            print("Phase 13 strict local static gate did not pass")
            return 1
        return 0

    if args.command == "suite" and args.suite_command == "generate":
        try:
            result = generate_suite_from_spec(Path(args.spec), Path(args.out))
        except SuiteGenerationError as exc:
            print(exc)
            return 1
        print(f"Suite generated: {result.suite_root}")
        for package in result.packages:
            print(package)
        return 0

    if args.command == "suite" and args.suite_command == "quality":
        try:
            result = generate_suite_quality_evidence(Path(args.suite))
        except SuiteQualityEvidenceError as exc:
            print(exc)
            return 1
        print(f"Suite quality evidence written: {result.evidence_path}")
        return 0

    if args.command == "suite" and args.suite_command == "phase10x":
        try:
            result = generate_phase10x_evidence(
                Path(args.suite),
                eos_python=Path(args.eos_python) if args.eos_python else None,
                golden_evidence_path=Path(args.golden_evidence)
                if args.golden_evidence
                else None,
                external_evidence_path=Path(args.external_evidence)
                if args.external_evidence
                else None,
                runtime_smoke_path=Path(args.runtime_smoke) if args.runtime_smoke else None,
                rc_min_packages=args.rc_min_packages,
                rc_max_packages=args.rc_max_packages,
            )
        except Phase10xEvidenceError as exc:
            print(exc)
            return 1
        print(f"Phase 10.x evidence written: {result.suite_root / 'evidence'}")
        print(f"Phase 10.x overall status: {result.overall_status}")
        if args.strict and result.overall_status != "passed":
            print("Phase 10.x strict gate did not pass")
            return 1
        return 0

    if args.command == "suite" and args.suite_command == "phase11-small-canary":
        result = generate_phase11_small_multi_task_canary_gate(
            Path(args.suite),
            Path(args.canary_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.6 small multi-task canary gate written: {result.evidence_path}")
        print(f"Phase 11.6 small multi-task canary gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.6 small multi-task canary strict gate did not pass")
            return 1
        return 0

    if args.command == "suite" and args.suite_command == "phase11-release":
        result = generate_phase11_automated_release_gate(
            Path(args.suite),
            Path(args.release_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.7 automated release gate written: {result.evidence_path}")
        print(f"Phase 11.7 automated release gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.7 automated release strict gate did not pass")
            return 1
        return 0

    if args.command == "suite" and args.suite_command == "phase11-readiness":
        result = generate_phase11_phase12_readiness_gate(
            Path(args.suite),
            Path(args.readiness_evidence),
        )
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 11.8 Phase-12 readiness gate written: {result.evidence_path}")
        print(f"Phase 11.8 Phase-12 readiness gate status: {result.status}")
        if args.strict and result.status != "passed":
            print("Phase 11.8 Phase-12 readiness strict gate did not pass")
            return 1
        return 0

    if args.command == "suite" and args.suite_command == "phase12":
        try:
            result = generate_phase12_registry_artifacts(
                Path(args.suite),
                Path(args.gate_index),
            )
        except Phase12RegistryError as exc:
            print(exc)
            return 1
        for blocker in result.blockers:
            print(blocker)
        print(f"Phase 12 evidence written: {result.suite_root / 'evidence'}")
        print(f"Phase 12 overall status: {result.status}")
        if args.strict and result.status != "phase13_allowed":
            print("Phase 12 strict gate did not pass")
            return 1
        return 0

    if args.command == "export" and args.export_command == "ebench":
        if args.package:
            try:
                result = export_ebench_package(Path(args.package))
            except EBenchExportError as exc:
                print(exc)
                return 1
            print(f"EBench package export written: {result.output_dir}")
            return 0
        result = export_ebench_suite(Path(args.suite))
        for blocker in result.blockers:
            print(blocker)
        if not result.ok:
            return 1
        print(f"EBench suite export written: {result.output_dir}")
        return 0

    if args.command == "ebench" and args.ebench_command == "canary":
        if args.ebench_canary_command == "apple-to-bowl":
            try:
                result = generate_apple_to_bowl_canary(Path(args.asset_sources), Path(args.out))
            except ValueError as exc:
                print(exc)
                return 1
            print(f"Package written: {result.package_root}")
            print(f"USD entrypoint: {result.scene_usd}")
            return 0
        if args.ebench_canary_command == "single-object-fixture":
            try:
                result = generate_single_object_fixture_canary(Path(args.asset_sources), Path(args.out))
            except ValueError as exc:
                print(exc)
                return 1
            print(f"Package written: {result.package_root}")
            print(f"USD entrypoint: {result.scene_usd}")
            return 0

    parser.error("unreachable command")
    return 2


def _package_scene_paths(package_dir: Path) -> tuple[str, ...]:
    try:
        manifest = load_package_manifest(package_dir)
    except PackageError:
        return ()
    scene_path = manifest.scene_path
    return (scene_path,) if scene_path is not None else ()


def _package_root_from_asset_lock(asset_lock_path: Path) -> Path:
    if asset_lock_path.parent.name == "locks":
        return asset_lock_path.parent.parent
    return asset_lock_path.parent


def _parse_bindings(raw_bindings: list[str]) -> dict[str, str] | None:
    if not raw_bindings:
        return None
    bindings: dict[str, str] = {}
    for raw_binding in raw_bindings:
        if "=" not in raw_binding:
            raise WorkflowComposeError(f"Invalid binding {raw_binding!r}; expected role=instance_id")
        key, value = raw_binding.split("=", 1)
        if not key or not value:
            raise WorkflowComposeError(f"Invalid binding {raw_binding!r}; expected role=instance_id")
        bindings[key] = value
    return bindings


if __name__ == "__main__":
    sys.exit(main())

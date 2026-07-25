#!/usr/bin/env python3
"""Generate task-package variants with one fixed eBench workspace.

The background is the only scenario input that changes between variants.  The
table, robot contract, task objects, poses, and success contract are copied from
the checked baseline package/spec.  ConvertAsset remains the owner of each
background package; this script only validates and composes delivered packages.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import yaml

from scenario_forge.adapters.convert_asset import load_convert_asset_package_handoff
from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview
from scenario_forge.assets.manifest import load_asset_manifest
from scenario_forge.assets.source import LocalUSDAssetSource, UpstreamPackageRef
from scenario_forge.core.scenario import PoseSpec, ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "examples/scientific_workbench/bimanual_pour/scenario.yaml"
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
BASE_ENVIRONMENT_ASSET_ID = "scientific_workbench_scene1_hard_environment"
TABLE_ASSET_ID = "scientific_workbench_ebench_table"
SOURCE_VESSEL_ASSET_ID = "scientific_workbench_conical_bottle03_dynamic"
TARGET_VESSEL_ASSET_ID = "scientific_workbench_graduated_cylinder_03_dynamic"
BACKGROUND_ID = re.compile(r"^scientific_environment_[0-9]{3}$")
VARIANT_SCHEMA = "scenario-forge-scientific-workbench-background-variants/v0.1"
WORKSPACE_PROFILE_SCHEMA = "scenario-forge-convertasset-workspace-integration-profile/v0.1"
WORKSPACE_PROFILE_MANIFEST_SCHEMA = (
    "scenario-forge-convertasset-workspace-integration-profile-manifest/v0.1"
)
# ConvertAsset workspace profiles express their anchor in the source-composed
# coordinate frame and must declare the calibrated metres per such unit.  A
# package stage's inherited USD ``metersPerUnit`` is not a substitute.
# The eBench workspace is about one metre across, while the reference
# Scene1_hard room is roughly 8 m x 21 m.  Backgrounds are visual-only, so the
# placement layer may fit an *unprofiled* admitted source into this visual
# envelope. Workspace-profiled rooms preserve their clearance metric instead.
BACKGROUND_EXTENT_MIN_M = 4.0
BACKGROUND_EXTENT_MAX_M = 21.0
# Measured once from the canonical eBench table package.  The background
# instance is moved to this frame; the table, robot, vessels, and task poses
# stay unchanged in the scenario contract.
EBENCH_WORKSPACE_TARGET_XYZ = (0.2456705, -0.0069055, 0.772761)
RUNTIME_WORKSPACE_OVERVIEW_ANCHORS = (
    "lift2",
    "00000000000000000000000000000000",
    "obj_conical_bottle03",
    "obj_graduated_cylinder_03",
)
RUNTIME_CONTEXT_CAMERA_DISTANCE_M = 2.8
# A room-context view needs a little more working distance than the task-only
# overview.  The direction comes from the producer's authored Perspective
# camera; only its target is moved to the fixed eBench workspace.
AUTHORED_CONTEXT_CAMERA_DISTANCE_M = 4.0
# Same high three-quarter direction as the task-only evidence view.  It is a
# task-camera policy rather than a producer-room camera, so every accepted
# room proves the same robot/table/vessel arrangement.
RUNTIME_CONTEXT_CAMERA_DIRECTION_XYZ = (
    0.6791078223508457,
    -0.4755164164672426,
    0.5591929034707469,
)


@dataclass(frozen=True)
class WorkspaceAnchor:
    """A producer-scene tabletop point used to place the fixed eBench table."""

    source_prim_path: str
    source_anchor_xyz_m: tuple[float, float, float]
    # ``source_anchor_xyz_m`` is expressed after this conversion from the
    # producer's composed coordinate values.  Built-in legacy anchors use the
    # admitted package's declared metres-per-unit; ConvertAsset profiles must
    # declare their own calibrated source-composed scale explicitly.
    source_composed_meters_per_unit: float | None = None
    # A workspace profile's clearance is calibrated for the fixed eBench
    # footprint.  Scaling that room into a generic visual envelope would make
    # the cleared footprint untrue, so such profiles preserve their metric
    # scale.  The legacy visual-only anchors retain envelope fitting.
    preserve_workspace_metric: bool = False
    target_xyz: tuple[float, float, float] = EBENCH_WORKSPACE_TARGET_XYZ
    hide_prim_paths: tuple[str, ...] = ()
    note: str = ""
    camera_mode: str = "authored"


@dataclass(frozen=True)
class WorkspaceProfile:
    """A source-bound ConvertAsset workcell replacement declaration."""

    candidate_id: str
    status: str
    profile_path: Path
    producer_revision: str
    producer_git_commit: str
    anchor: WorkspaceAnchor | None = None
    raw_anchor_xyz_m: tuple[float, float, float] | None = None
    source_composed_meters_per_unit: float | None = None
    raw_clearance_aabb_m: tuple[tuple[float, float, float], tuple[float, float, float]] | None = (
        None
    )
    optional_inactive_prim_paths: tuple[str, ...] = ()
    not_applicable_reason: str | None = None


@dataclass(frozen=True)
class BackgroundCandidate:
    candidate_id: str
    package_dir: Path
    manifest_path: Path
    source_usd: Path
    source_sha256: str
    source_scope: str
    producer_revision: str
    meters_per_unit: float
    root_scale_xyz: tuple[float, float, float]
    root_translate_xyz: tuple[float, float, float]
    physical_bounds_m: tuple[tuple[float, float, float], tuple[float, float, float]]
    authored_camera: tuple[tuple[float, float, float], tuple[float, float, float]] | None


# ConvertAsset keeps the source geometry anonymous for these visual-static
# packages. Only source-bound island replacements with a dedicated review
# record belong here; do not infer an anchor from an arbitrary horizontal mesh.
# The points are the top-surface centres measured in the admitted package frame.
_WORKSPACE_ANCHORS: dict[str, WorkspaceAnchor] = {
    "scientific_environment_059": WorkspaceAnchor(
        source_prim_path="/World/group_063/mesh_000",
        source_anchor_xyz_m=(42.592, -5.914, 26.281),
        # The source table is an assembly: leaving its shelves/appliances
        # active would put them through the fixed eBench vessels.  Hide the
        # reviewed island assembly, while the rest of the room stays visible.
        hide_prim_paths=("/World/group_063",),
        note="front-left laboratory island assembly top surface",
        camera_mode="workspace_focus",
    ),
    "scientific_environment_084": WorkspaceAnchor(
        source_prim_path="/World/group_078/mesh_027",
        # The complete group is a reviewed wet-lab island assembly.  Removing
        # it avoids leaving its cabinets, sink, or hood inside the unchanged
        # eBench workcell.
        source_anchor_xyz_m=(
            3.370354746523178,
            2.067844607496102,
            1.2252995907691615,
        ),
        hide_prim_paths=("/World/group_078",),
        note="central wet-lab island assembly top surface",
        camera_mode="workspace_focus",
    ),
}

# Review-only visual composition choices.  These are instance-layer poses,
# not producer asset edits or dynamic-placement claims.  083's source row is
# coherent after a quarter-turn around its reviewed anchor; the fixed eBench
# table and robot remain unchanged.
_WORKSPACE_COMPOSITION_YAW_DEG: dict[str, float] = {
    "scientific_environment_083": 90.0,
}


def workspace_composition_yaw_deg(candidate: BackgroundCandidate) -> float:
    """Return the clean-room-reviewed visual yaw for a background instance."""

    return _WORKSPACE_COMPOSITION_YAW_DEG.get(candidate.candidate_id, 0.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compose the fixed scientific-workbench bimanual-pour task with "
            "each admitted visual-static environment background."
        )
    )
    parser.add_argument("--base-package", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--background-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument(
        "--workspace-profiles",
        type=Path,
        help=(
            "ConvertAsset workspace_profiles_manifest.json. When supplied, only "
            "profiled or built-in-reviewed background integrations are generated."
        ),
    )
    parser.add_argument(
        "--candidate-id",
        help="Optionally regenerate one candidate in an existing output root.",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Run the native GenManip initial-scene preview for every variant.",
    )
    parser.add_argument(
        "--isaac-python",
        type=Path,
        help="Isaac/GenManip Python executable; required with --render.",
    )
    parser.add_argument(
        "--genmanip-root",
        type=Path,
        help="GenManip checkout root; required with --render.",
    )
    parser.add_argument("--renderer-script", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render and (args.isaac_python is None or args.genmanip_root is None):
        raise SystemExit("--isaac-python and --genmanip-root are required with --render")

    base_spec = load_scenario_spec(args.spec)
    admitted_candidates = load_admitted_backgrounds(args.admission, args.background_root)
    workspace_profiles: Mapping[str, WorkspaceProfile] = {}
    excluded_workspace_candidates: dict[str, str] = {}
    manifest_candidates = admitted_candidates
    if args.workspace_profiles is not None:
        workspace_profiles = load_workspace_profiles(
            args.workspace_profiles,
            admitted_candidates,
        )
        manifest_candidates, excluded_workspace_candidates = select_workspace_candidates(
            admitted_candidates,
            workspace_profiles,
        )
        if args.candidate_id is None:
            candidates = manifest_candidates
        else:
            try:
                candidates, _ = select_workspace_candidates(
                    admitted_candidates,
                    workspace_profiles,
                    candidate_id=args.candidate_id,
                )
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
    else:
        candidates = admitted_candidates
        if args.candidate_id is not None:
            candidates = tuple(
                candidate for candidate in candidates if candidate.candidate_id == args.candidate_id
            )
            if not candidates:
                raise SystemExit(f"candidate id is not present in admission: {args.candidate_id}")
    base_sources = load_existing_package_sources(args.base_package)
    _validate_base_inputs(base_spec, base_sources)

    output_root = args.out.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    existing_variants = (
        _load_existing_variants(output_root / "background_variants_manifest.json")
        if args.candidate_id is not None
        else {}
    )
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        profile = workspace_profiles.get(candidate.candidate_id)
        anchor = workspace_anchor_for(candidate, workspace_profiles)
        placement = background_placement(base_spec, candidate, anchor=anchor)
        variant = make_variant_spec(
            base_spec,
            candidate.candidate_id,
            scene_pose=placement["scene_pose"],
            inactive_prim_paths=(() if anchor is None else anchor.hide_prim_paths),
        )
        _assert_fixed_workspace(
            base_spec,
            variant,
            allowed_inactive_prim_paths=(None if anchor is None else anchor.hide_prim_paths),
        )
        background_source = _load_background_source(candidate)
        sources = {
            **base_sources,
            candidate.candidate_id: background_source,
        }
        package_root = output_root / candidate.candidate_id
        compiled = compile_scenario_package(variant, sources, package_root)
        export = export_genmanip_collected_package(compiled.package_root)
        _configure_background_preview(
            export.output_dir,
            placement,
            candidate,
            anchor=anchor,
        )
        preview: Mapping[str, Any] | None = None
        if args.render:
            assert args.isaac_python is not None
            assert args.genmanip_root is not None
            evidence = run_genmanip_initial_preview(
                export.output_dir,
                args.isaac_python,
                args.renderer_script,
                args.genmanip_root,
                timeout_seconds=args.preview_timeout,
            )
            preview = {
                "status": evidence.status,
                "evidence_dir": str(evidence.evidence_dir),
                "gate_path": str(evidence.gate_path),
            }
        results.append(
            {
                "candidate_id": candidate.candidate_id,
                "scenario_id": variant.scenario_id,
                "package_root": str(compiled.package_root),
                "genmanip_root": str(export.output_dir),
                "background_manifest": str(candidate.manifest_path),
                "background_source_sha256": candidate.source_sha256,
                "background_placement": {
                    key: value for key, value in placement.items() if key != "scene_pose"
                },
                "workspace_integration": _workspace_integration_record(
                    profile,
                    anchor,
                ),
                "fixed_workspace": {
                    "table_asset_id": TABLE_ASSET_ID,
                    "table_pose_sha256": _object_digest(variant, "table"),
                    "task_object_pose_sha256": _object_digest(variant, "obj_conical_bottle03"),
                    "robot_spawn_sha256": _json_sha256(variant.to_mapping()["robot"]["spawn"]),
                },
                **({"preview": dict(preview)} if preview is not None else {}),
            }
        )

    if args.candidate_id is None:
        variants = results
    else:
        merged_variants = {**existing_variants}
        merged_variants.update({str(result["candidate_id"]): result for result in results})
        variants = [
            merged_variants[candidate.candidate_id]
            for candidate in manifest_candidates
            if candidate.candidate_id in merged_variants
        ]

    manifest = {
        "schema_version": VARIANT_SCHEMA,
        "base_scenario_id": base_spec.scenario_id,
        "base_spec": str(args.spec.resolve()),
        "base_package": str(args.base_package.resolve()),
        "admission_request": str(args.admission.resolve()),
        **(
            {
                "workspace_profiles_manifest": str(args.workspace_profiles.resolve()),
                "excluded_workspace_candidates": excluded_workspace_candidates,
            }
            if args.workspace_profiles is not None
            else {}
        ),
        "candidate_count": len(variants),
        "variants": variants,
        "fixed_workspace_contract": {
            "table_asset_id": TABLE_ASSET_ID,
            "source_vessel_asset_id": SOURCE_VESSEL_ASSET_ID,
            "target_vessel_asset_id": TARGET_VESSEL_ASSET_ID,
            "robot_profile": base_spec.robot.profile_ref,
            "only_changed_field": (
                "scene.asset_id, visual-background scene.pose fit, and "
                "anchored background inactive_prim_paths "
                "(plus variant scenario_id)"
            ),
            "placement_note": (
                "scene.pose is an instance placement transform for the visual-static "
                "background; when a workspace anchor is recorded, only the reviewed "
                "overlapping background tabletop layer (or its source island assembly) "
                "is hidden in the composition layer; table, robot, object poses, and "
                "task semantics remain fixed"
            ),
        },
        "claim_boundary": (
            "These artifacts prove background substitution while preserving the "
            "baseline task workspace. They are visual scene evidence packages; "
            "they do not prove oracle success, policy success, liquid transfer, "
            "or dynamic behavior for visual-static backgrounds."
        ),
    }
    _write_json(output_root / "background_variants_manifest.json", manifest)
    print(f"Generated {len(results)} background variants under {output_root}")
    return 0


def load_scenario_spec(path: str | Path) -> ScenarioSpec:
    spec_path = Path(path)
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError(f"scenario spec must be a mapping: {spec_path}")
    return ScenarioSpec.from_mapping(raw)


def load_admitted_backgrounds(
    admission_path: str | Path,
    package_root: str | Path,
) -> tuple[BackgroundCandidate, ...]:
    """Load hash-bound visual-static candidates from ConvertAsset's handoff."""

    path = Path(admission_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("background admission request must be a mapping")
    target = _mapping(raw.get("target"), "admission.target")
    if target.get("runtime_profile") != "isaac41":
        raise ValueError("background admission runtime_profile must be isaac41")
    if target.get("asset_role") != "visual_static_environment":
        raise ValueError("background admission asset_role must be visual_static_environment")
    updates = _mapping(
        raw.get("producer_source_updates"),
        "admission.producer_source_updates",
    )
    producer_revision = _string(
        updates.get("revision"),
        "admission.producer_source_updates.revision",
    )
    raw_items = raw.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("background admission items must be a non-empty list")

    packages = Path(package_root).resolve()
    candidates: list[BackgroundCandidate] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(raw_items):
        item = _mapping(raw_item, f"admission.items[{index}]")
        candidate_id = _string(item.get("candidate_id"), "candidate_id")
        if BACKGROUND_ID.fullmatch(candidate_id) is None:
            raise ValueError(f"invalid background candidate_id: {candidate_id}")
        if candidate_id in seen:
            raise ValueError(f"duplicate background candidate_id: {candidate_id}")
        seen.add(candidate_id)
        source_usd = Path(_string(item.get("source_usd"), "source_usd")).resolve()
        source_sha256 = _digest_without_prefix(_string(item.get("source_sha256"), "source_sha256"))
        if file_sha256(source_usd) != f"sha256:{source_sha256}":
            raise ValueError(f"source USD hash mismatch: {candidate_id}")
        source_scope = _string(item.get("source_scope"), "source_scope")
        required_return = _mapping(
            item.get("required_return"),
            f"admission.items[{index}].required_return",
        )
        if required_return.get("overall_status") != "pass":
            raise ValueError(f"background candidate is not required to pass: {candidate_id}")

        package_dir = (packages / candidate_id).resolve()
        manifest_path = package_dir / "evidence" / "manifest.json"
        _validate_admitted_package(
            package_dir,
            manifest_path,
            candidate_id=candidate_id,
            source_sha256=source_sha256,
            source_scope=source_scope,
        )
        meters_per_unit, physical_bounds_m = _admitted_physical_frame(
            manifest_path,
            candidate_id=candidate_id,
        )
        root_scale_xyz, root_translate_xyz = _source_root_transform(
            manifest_path,
            candidate_id=candidate_id,
        )
        authored_camera = _source_authored_camera(package_dir)
        candidates.append(
            BackgroundCandidate(
                candidate_id=candidate_id,
                package_dir=package_dir,
                manifest_path=manifest_path,
                source_usd=source_usd,
                source_sha256=source_sha256,
                source_scope=source_scope,
                producer_revision=producer_revision,
                meters_per_unit=meters_per_unit,
                root_scale_xyz=root_scale_xyz,
                root_translate_xyz=root_translate_xyz,
                physical_bounds_m=physical_bounds_m,
                authored_camera=authored_camera,
            )
        )
    return tuple(candidates)


def make_variant_spec(
    spec: ScenarioSpec,
    candidate_id: str,
    *,
    scene_pose: Mapping[str, Any] | None = None,
    inactive_prim_paths: Sequence[str] | None = None,
) -> ScenarioSpec:
    """Return a variant with a background identity and optional instance pose."""

    if BACKGROUND_ID.fullmatch(candidate_id) is None:
        raise ValueError(f"invalid background candidate_id: {candidate_id}")
    suffix = candidate_id.removeprefix("scientific_environment_")
    scene = replace(
        spec.scene,
        asset_id=candidate_id,
        inactive_prim_paths=(
            spec.scene.inactive_prim_paths
            if inactive_prim_paths is None
            else tuple(inactive_prim_paths)
        ),
        pose=(
            spec.scene.pose
            if scene_pose is None
            else PoseSpec.from_mapping(scene_pose, "scene.pose")
        ),
    )
    return replace(
        spec,
        scenario_id=f"{spec.scenario_id}_env_{suffix}",
        scene=scene,
    )


def load_workspace_profiles(
    manifest_path: str | Path,
    candidates: Sequence[BackgroundCandidate],
) -> dict[str, WorkspaceProfile]:
    """Load hash-bound ConvertAsset workspace replacement profiles.

    The producer profile anchor is in source-composed coordinates.  Existing
    Scenario Forge placement expects physical metres in the admitted package
    frame, so this adapter performs the one declared unit conversion here.
    """

    path = Path(manifest_path).resolve()
    try:
        raw_manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"workspace profile manifest is invalid: {path}") from exc
    manifest = _mapping(raw_manifest, "workspace profile manifest")
    if manifest.get("schema_version") != WORKSPACE_PROFILE_MANIFEST_SCHEMA:
        raise ValueError("workspace profile manifest schema is unsupported")
    raw_candidates = _mapping(
        manifest.get("candidates"),
        "workspace profile manifest.candidates",
    )
    admitted_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    profiles: dict[str, WorkspaceProfile] = {}
    root = path.parent
    for candidate_id, raw_entry in raw_candidates.items():
        if not isinstance(candidate_id, str) or BACKGROUND_ID.fullmatch(candidate_id) is None:
            raise ValueError("workspace profile manifest has an invalid candidate id")
        candidate = admitted_by_id.get(candidate_id)
        if candidate is None:
            raise ValueError(
                f"workspace profile candidate is not present in admission: {candidate_id}"
            )
        entry = _mapping(raw_entry, f"workspace profile manifest.{candidate_id}")
        manifest_status = _string(
            entry.get("status"),
            f"workspace profile manifest.{candidate_id}.status",
        )
        profile_name = _string(
            entry.get("profile"),
            f"workspace profile manifest.{candidate_id}.profile",
        )
        profile_path = (root / profile_name).resolve()
        if root not in profile_path.parents or not profile_path.is_file():
            raise ValueError(f"workspace profile is unavailable for {candidate_id}: {profile_name}")
        try:
            raw_profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"workspace profile is invalid: {profile_path}") from exc
        profile = _mapping(raw_profile, f"workspace profile {candidate_id}")
        if profile.get("schema_version") != WORKSPACE_PROFILE_SCHEMA:
            raise ValueError(f"workspace profile schema is unsupported: {candidate_id}")
        if profile.get("candidate_id") != candidate_id:
            raise ValueError(f"workspace profile candidate id disagrees: {candidate_id}")
        status = _string(profile.get("status"), f"workspace profile {candidate_id}.status")
        if status not in {"profiled", "not_applicable"}:
            raise ValueError(f"workspace profile status is unsupported: {candidate_id}")
        if status != manifest_status:
            raise ValueError(f"workspace profile status disagrees with manifest: {candidate_id}")

        source = _mapping(profile.get("source"), f"workspace profile {candidate_id}.source")
        source_usd = Path(
            _string(source.get("source_usd"), f"workspace profile {candidate_id}.source_usd")
        ).resolve()
        if source_usd != candidate.source_usd.resolve():
            raise ValueError(f"workspace profile source USD disagrees: {candidate_id}")
        source_hash = _digest_without_prefix(
            _string(
                source.get("source_sha256"),
                f"workspace profile {candidate_id}.source_sha256",
            )
        )
        if source_hash != candidate.source_sha256:
            raise ValueError(f"workspace profile source hash disagrees: {candidate_id}")
        if source.get("scope") != candidate.source_scope:
            raise ValueError(f"workspace profile source scope disagrees: {candidate_id}")

        producer = _mapping(
            profile.get("producer"),
            f"workspace profile {candidate_id}.producer",
        )
        producer_revision = _string(
            producer.get("revision"),
            f"workspace profile {candidate_id}.producer.revision",
        )
        producer_git_commit = _string(
            producer.get("git_commit"),
            f"workspace profile {candidate_id}.producer.git_commit",
        )

        if status == "not_applicable":
            profiles[candidate_id] = WorkspaceProfile(
                candidate_id=candidate_id,
                status=status,
                profile_path=profile_path,
                producer_revision=producer_revision,
                producer_git_commit=producer_git_commit,
                not_applicable_reason=_string(
                    profile.get("not_applicable_reason"),
                    f"workspace profile {candidate_id}.not_applicable_reason",
                ),
            )
            continue

        coordinate_mapping = _mapping(
            profile.get("coordinate_mapping"),
            f"workspace profile {candidate_id}.coordinate_mapping",
        )
        if coordinate_mapping.get("frame") != "source_composed":
            raise ValueError(
                f"workspace profile coordinate_mapping.frame must be "
                f"source_composed: {candidate_id}"
            )
        source_composed_meters_per_unit = _positive_finite_number(
            coordinate_mapping.get("source_composed_meters_per_unit"),
            (
                f"workspace profile {candidate_id}.coordinate_mapping."
                "source_composed_meters_per_unit"
            ),
        )

        assembly = _mapping(
            profile.get("assembly"),
            f"workspace profile {candidate_id}.assembly",
        )
        required_roots = _prim_path_tuple(
            assembly.get("replaceable_assembly_roots"),
            f"workspace profile {candidate_id}.assembly.replaceable_assembly_roots",
            require_nonempty=True,
        )
        anchor_prim = _prim_path(
            assembly.get("anchor_prim"),
            f"workspace profile {candidate_id}.assembly.anchor_prim",
        )
        raw_anchor = _number_tuple(
            assembly.get("anchor_xyz_m"),
            f"workspace profile {candidate_id}.assembly.anchor_xyz_m",
        )
        inactivation = _mapping(
            profile.get("inactivation"),
            f"workspace profile {candidate_id}.inactivation",
        )
        inactive_roots = _prim_path_tuple(
            inactivation.get("inactive_prim_root_paths"),
            f"workspace profile {candidate_id}.inactivation.inactive_prim_root_paths",
            require_nonempty=True,
        )
        if inactive_roots != required_roots:
            raise ValueError(
                f"workspace profile replacement roots disagree with inactivation: {candidate_id}"
            )
        optional_paths = _prim_path_tuple(
            inactivation.get("optional_inactive_prim_paths", []),
            f"workspace profile {candidate_id}.inactivation.optional_inactive_prim_paths",
        )
        workspace = _mapping(
            profile.get("workspace"),
            f"workspace profile {candidate_id}.workspace",
        )
        clearance = _mapping(
            workspace.get("clearance_aabb_m"),
            f"workspace profile {candidate_id}.workspace.clearance_aabb_m",
        )
        clearance_lower = _number_tuple(
            clearance.get("min"),
            f"workspace profile {candidate_id}.workspace.clearance_aabb_m.min",
        )
        clearance_upper = _number_tuple(
            clearance.get("max"),
            f"workspace profile {candidate_id}.workspace.clearance_aabb_m.max",
        )
        if any(clearance_upper[index] <= clearance_lower[index] for index in range(3)):
            raise ValueError(f"workspace profile clearance is empty: {candidate_id}")

        # The profile anchor is expressed in source-composed coordinates.  Do
        # not substitute the package stage's ``metersPerUnit`` here: a number
        # of source laboratories have inherited metadata that is not the
        # calibrated workcell scale.  ConvertAsset supplies that exact scale
        # in the profile coordinate mapping.
        package_anchor = tuple(value * source_composed_meters_per_unit for value in raw_anchor)
        lower, upper = _raw_source_composed_bounds(candidate)
        if any(
            raw_anchor[index] < lower[index] or raw_anchor[index] > upper[index]
            for index in range(3)
        ):
            raise ValueError(
                f"workspace profile anchor is outside source-composed bounds: {candidate_id}"
            )
        anchor = WorkspaceAnchor(
            source_prim_path=anchor_prim,
            source_anchor_xyz_m=package_anchor,
            source_composed_meters_per_unit=source_composed_meters_per_unit,
            preserve_workspace_metric=True,
            hide_prim_paths=inactive_roots,
            note=(f"ConvertAsset source-bound workspace integration profile {profile_path.name}"),
            camera_mode="workspace_focus",
        )
        profiles[candidate_id] = WorkspaceProfile(
            candidate_id=candidate_id,
            status=status,
            profile_path=profile_path,
            producer_revision=producer_revision,
            producer_git_commit=producer_git_commit,
            anchor=anchor,
            raw_anchor_xyz_m=raw_anchor,
            source_composed_meters_per_unit=source_composed_meters_per_unit,
            raw_clearance_aabb_m=(clearance_lower, clearance_upper),
            optional_inactive_prim_paths=optional_paths,
        )
    return profiles


def _workspace_integration_record(
    profile: WorkspaceProfile | None,
    anchor: WorkspaceAnchor | None,
) -> dict[str, Any]:
    if profile is None:
        return {
            "status": "built_in_reviewed_anchor" if anchor is not None else "unprofiled",
            **(
                {"inactive_prim_root_paths": list(anchor.hide_prim_paths)}
                if anchor is not None
                else {}
            ),
        }
    record: dict[str, Any] = {
        "status": profile.status,
        "profile_path": str(profile.profile_path),
        "producer_revision": profile.producer_revision,
        "producer_git_commit": profile.producer_git_commit,
    }
    if profile.anchor is None:
        record["not_applicable_reason"] = profile.not_applicable_reason
        return record
    record.update(
        {
            "profile_anchor_source_composed_xyz": list(profile.raw_anchor_xyz_m or ()),
            "source_composed_meters_per_unit": (profile.source_composed_meters_per_unit),
            "profile_anchor_placement_m": list(profile.anchor.source_anchor_xyz_m),
            "workspace_metric_preserved": profile.anchor.preserve_workspace_metric,
            "inactive_prim_root_paths": list(profile.anchor.hide_prim_paths),
            "optional_inactive_prim_paths": list(profile.optional_inactive_prim_paths),
            "source_composed_clearance_aabb": {
                "min": list(profile.raw_clearance_aabb_m[0]),
                "max": list(profile.raw_clearance_aabb_m[1]),
            }
            if profile.raw_clearance_aabb_m is not None
            else None,
        }
    )
    return record


def workspace_anchor_for(
    candidate: BackgroundCandidate,
    workspace_profiles: Mapping[str, WorkspaceProfile] | None = None,
) -> WorkspaceAnchor | None:
    """Return a profile anchor first, then the small built-in reviewed set."""

    if workspace_profiles is not None:
        profile = workspace_profiles.get(candidate.candidate_id)
        if profile is not None:
            return profile.anchor
    return _WORKSPACE_ANCHORS.get(candidate.candidate_id)


def select_workspace_candidates(
    candidates: Sequence[BackgroundCandidate],
    workspace_profiles: Mapping[str, WorkspaceProfile],
    *,
    candidate_id: str | None = None,
) -> tuple[tuple[BackgroundCandidate, ...], dict[str, str]]:
    """Select only source-bound integrations from an explicit profile handoff."""

    selected: list[BackgroundCandidate] = []
    excluded: dict[str, str] = {}
    admitted_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if candidate_id is not None and candidate_id not in admitted_by_id:
        raise ValueError(f"candidate id is not present in admission: {candidate_id}")

    for candidate in candidates:
        profile = workspace_profiles.get(candidate.candidate_id)
        if profile is not None and profile.status == "not_applicable":
            excluded[candidate.candidate_id] = (
                profile.not_applicable_reason or "workspace integration is not applicable"
            )
            continue
        if workspace_anchor_for(candidate, workspace_profiles) is None:
            excluded[candidate.candidate_id] = (
                "no reviewed workspace integration profile is available"
            )
            continue
        selected.append(candidate)

    if candidate_id is not None:
        if candidate_id in excluded:
            raise ValueError(
                f"candidate {candidate_id} is not an integrated workspace variant: "
                f"{excluded[candidate_id]}"
            )
        selected = [candidate for candidate in selected if candidate.candidate_id == candidate_id]
    return tuple(selected), excluded


def _rotate_z(
    vector: tuple[float, float, float], yaw_deg: float
) -> tuple[float, float, float]:
    radians = math.radians(yaw_deg)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return (
        cosine * vector[0] - sine * vector[1],
        sine * vector[0] + cosine * vector[1],
        vector[2],
    )


def _yaw_quaternion(yaw_deg: float) -> tuple[float, float, float, float]:
    half_angle = math.radians(yaw_deg) / 2.0
    return (math.cos(half_angle), 0.0, 0.0, math.sin(half_angle))


def _quat_multiply(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    lw, lx, ly, lz = left
    rw, rx, ry, rz = right
    return (
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    )


def background_placement(
    spec: ScenarioSpec,
    candidate: BackgroundCandidate,
    *,
    anchor: WorkspaceAnchor | None = None,
) -> dict[str, Any]:
    """Compute a visual-only unit conversion and envelope-fit transform."""

    if spec.scene.pose is None:
        raise ValueError("background placement requires a baseline scene.pose")
    if anchor is None:
        anchor = workspace_anchor_for(candidate)

    source_composed_meters_per_unit = (
        None if anchor is None else anchor.source_composed_meters_per_unit
    )
    if source_composed_meters_per_unit is None:
        lower, upper = candidate.physical_bounds_m
        unit_scale = candidate.meters_per_unit
        scale_policy = "visual_envelope_fit"
    else:
        lower, upper = _source_composed_metric_bounds(
            candidate,
            source_composed_meters_per_unit,
        )
        unit_scale = source_composed_meters_per_unit
        scale_policy = (
            "preserve_profile_workspace_metric"
            if anchor.preserve_workspace_metric
            else "visual_envelope_fit"
        )
    extents = tuple(upper[index] - lower[index] for index in range(3))
    max_extent = max(extents)
    if max_extent <= 0.0:
        raise ValueError(f"background has an empty physical bound: {candidate.candidate_id}")
    if scale_policy == "preserve_profile_workspace_metric":
        # The ConvertAsset profile's source-composed scale is calibrated to
        # the fixed eBench clearance.  A generic room fit would rescale that
        # clearance and invalidate the profile's central claim.
        fit_factor = 1.0
    else:
        target_extent = min(
            BACKGROUND_EXTENT_MAX_M,
            max(BACKGROUND_EXTENT_MIN_M, max_extent),
        )
        fit_factor = target_extent / max_extent
    effective_scale = unit_scale * fit_factor
    authored_scale = tuple(effective_scale * candidate.root_scale_xyz[index] for index in range(3))
    composition_yaw_deg = workspace_composition_yaw_deg(candidate)
    center = tuple((lower[index] + upper[index]) / 2.0 for index in range(3))
    base_xyz = spec.scene.pose.xyz
    if anchor is None:
        source_offset = tuple(
            fit_factor * center[index]
            - effective_scale * candidate.root_translate_xyz[index]
            for index in range(3)
        )
        rotated_offset = _rotate_z(source_offset, composition_yaw_deg)
        scene_xyz = tuple(base_xyz[index] - rotated_offset[index] for index in range(3))
        placement_mode = "envelope_center"
        camera_origin_xyz = [
            scene_xyz[index]
            - _rotate_z(
                tuple(effective_scale * value for value in candidate.root_translate_xyz),
                composition_yaw_deg,
            )[index]
            for index in range(3)
        ]
    else:
        # ``source_anchor_xyz_m`` is the producer-composed anchor after the
        # declared source-coordinate-to-metre conversion.  The generated
        # scene layer replaces that root transform with the instance pose, so
        # fold the source-root translation back out when solving the pose.
        source_offset = tuple(
            fit_factor * anchor.source_anchor_xyz_m[index]
            - effective_scale * candidate.root_translate_xyz[index]
            for index in range(3)
        )
        rotated_offset = _rotate_z(source_offset, composition_yaw_deg)
        scene_xyz = tuple(
            anchor.target_xyz[index] - rotated_offset[index] for index in range(3)
        )
        placement_mode = "workspace_anchor"
        camera_origin_xyz = [
            scene_xyz[index]
            - _rotate_z(
                tuple(effective_scale * value for value in candidate.root_translate_xyz),
                composition_yaw_deg,
            )[index]
            for index in range(3)
        ]
    scene_wxyz = _quat_multiply(
        _yaw_quaternion(composition_yaw_deg),
        tuple(spec.scene.pose.wxyz),
    )
    scene_pose = {
        "xyz": list(scene_xyz),
        "wxyz": list(scene_wxyz),
        "scale_xyz": list(authored_scale),
    }
    return {
        "meters_per_unit": candidate.meters_per_unit,
        "source_root_scale_xyz": list(candidate.root_scale_xyz),
        "source_root_translate_xyz": list(candidate.root_translate_xyz),
        "source_bounds_m": [list(lower), list(upper)],
        "fit_factor": fit_factor,
        "effective_scale": effective_scale,
        "composition_yaw_deg": composition_yaw_deg,
        "authored_scale_xyz": list(authored_scale),
        "scale_policy": scale_policy,
        "placement_mode": placement_mode,
        "camera_origin_xyz": camera_origin_xyz,
        "scene_pose": scene_pose,
        **(
            {
                "workspace_anchor": {
                    "source_prim_path": anchor.source_prim_path,
                    "source_anchor_xyz_m": list(anchor.source_anchor_xyz_m),
                    "target_xyz": list(anchor.target_xyz),
                    "hide_prim_paths": list(anchor.hide_prim_paths),
                    "note": anchor.note,
                    "camera_mode": anchor.camera_mode,
                }
            }
            if anchor is not None
            else {}
        ),
    }


def _configure_background_preview(
    collected_root: Path,
    placement: Mapping[str, Any],
    candidate: BackgroundCandidate,
    *,
    anchor: WorkspaceAnchor | None = None,
) -> None:
    """Aim the scene overview at the candidate's authored laboratory view."""

    request_path = collected_root / "evidence" / "render_request.yaml"
    if not request_path.is_file():
        raise ValueError(f"GenManip preview request is missing: {request_path}")
    request = _mapping(
        yaml.safe_load(request_path.read_text(encoding="utf-8")),
        "render request",
    )
    views = _mapping(request.get("views"), "render request.views")
    overview = _mapping(views.get("scene_overview"), "render request.scene_overview")
    if anchor is None:
        anchor = workspace_anchor_for(candidate)
    if anchor is not None and anchor.camera_mode == "workspace_focus":
        authored_pose = _authored_workspace_camera_pose(
            candidate,
            yaw_deg=float(placement.get("composition_yaw_deg", 0.0)),
        )
        if authored_pose is not None:
            target, position = authored_pose
            overview["target_xyz"] = list(target)
            overview["position_xyz"] = list(position)
            overview.pop("runtime_target_direction_xyz", None)
            overview.pop("runtime_target_distance_m", None)
            overview.pop("azimuth_deg", None)
            overview.pop("elevation_deg", None)
            overview["camera_source"] = (
                "scenario-forge source authored Perspective direction retargeted "
                "to fixed eBench workspace"
            )
            request["camera_policy_version"] = (
                "scenario-forge/runtime-workspace-context-v8"
            )
            request_path.write_text(
                yaml.safe_dump(dict(request), sort_keys=False),
                encoding="utf-8",
            )
            return
        # GenManip creates the table and robot during post-reset recovery.  A
        # compiler-USD tabletop coordinate is therefore not a reliable camera
        # target for the runtime workcell.  Fit the evidence camera from the
        # actual recovered table, robot, and vessels instead; the room remains
        # active as visual context but does not pull the camera off the task.
        overview["anchor_runtime_ids"] = list(RUNTIME_WORKSPACE_OVERVIEW_ANCHORS)
        overview["azimuth_deg"] = -35.0
        overview["elevation_deg"] = 30.0
        overview["framing_margin"] = 1.28
        overview["minimum_distance"] = 1.8
        overview.pop("target_xyz", None)
        overview.pop("position_xyz", None)
        overview["camera_source"] = "GenManip post-reset runtime workspace bounds"
        overview["runtime_target_direction_xyz"] = list(RUNTIME_CONTEXT_CAMERA_DIRECTION_XYZ)
        overview["runtime_target_distance_m"] = RUNTIME_CONTEXT_CAMERA_DISTANCE_M
        request["camera_policy_version"] = "scenario-forge/runtime-workspace-context-v7"
        request_path.write_text(
            yaml.safe_dump(dict(request), sort_keys=False),
            encoding="utf-8",
        )
        return

    if candidate.authored_camera is None:
        return
    origin = _number_tuple(
        placement.get("camera_origin_xyz"),
        "background placement.camera_origin_xyz",
    )
    effective_scale = placement.get("effective_scale")
    if not isinstance(effective_scale, (int, float)) or isinstance(effective_scale, bool):
        raise ValueError("background placement.effective_scale is invalid")
    effective_scale = float(effective_scale)
    camera_position, camera_target = candidate.authored_camera
    if anchor is None:
        overview["target_xyz"] = [
            origin[index] + effective_scale * camera_target[index] for index in range(3)
        ]
        overview["position_xyz"] = [
            origin[index] + effective_scale * camera_position[index] for index in range(3)
        ]
        overview["camera_source"] = (
            "ConvertAsset source_root.usd customLayerData.cameraSettings.Perspective"
        )
    else:
        room_focus = [origin[index] + effective_scale * camera_target[index] for index in range(3)]
        overview["target_xyz"] = room_focus
        overview["position_xyz"] = [
            origin[index] + effective_scale * camera_position[index] for index in range(3)
        ]
        overview["camera_source"] = (
            "scenario-forge workspace_anchor with ConvertAsset authored Perspective"
        )
    request_path.write_text(
        yaml.safe_dump(dict(request), sort_keys=False),
        encoding="utf-8",
    )


def _authored_workspace_camera_pose(
    candidate: BackgroundCandidate,
    *,
    yaw_deg: float = 0.0,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Retarget a source room's authored view without moving the workspace.

    ConvertAsset's source-root camera is useful for the *direction* of a room
    view, but its target can point at a source-only object or even outside the
    admitted scope.  Preserve that direction, place the target at the fixed
    eBench anchor, and use a bounded room-context distance.  This remains a
    composition-layer camera choice; it does not edit the source USD.
    """

    if candidate.authored_camera is None:
        return None
    camera_position, camera_target = candidate.authored_camera
    direction = tuple(
        camera_target[index] - camera_position[index] for index in range(3)
    )
    norm = math.sqrt(sum(value * value for value in direction))
    if not math.isfinite(norm) or norm <= 1e-9:
        return None
    unit_direction = _rotate_z(
        tuple(value / norm for value in direction),
        yaw_deg,
    )
    target = EBENCH_WORKSPACE_TARGET_XYZ
    position = tuple(
        target[index] - AUTHORED_CONTEXT_CAMERA_DISTANCE_M * unit_direction[index]
        for index in range(3)
    )
    return target, position


def _source_authored_camera(
    package_dir: Path,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Read a source-root Perspective camera without importing USD tooling."""

    source_root = package_dir / "deps" / "usd" / "source_root.usd"
    if not source_root.is_file():
        return None
    try:
        text = source_root.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = re.search(
        r"dictionary\s+Perspective\s*=\s*\{(?P<body>.*?)\n\s*\}",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        return None
    body = match.group("body")
    position = re.search(r"double3\s+position\s*=\s*\(([^)]*)\)", body)
    target = re.search(r"double3\s+target\s*=\s*\(([^)]*)\)", body)
    if position is None or target is None:
        return None
    return (
        _number_tuple(_parse_float_tuple(position.group(1), "camera.position"), "camera.position"),
        _number_tuple(_parse_float_tuple(target.group(1), "camera.target"), "camera.target"),
    )


def _parse_float_tuple(value: str, field: str) -> list[float]:
    try:
        result = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise ValueError(f"{field} contains invalid numbers") from exc
    if len(result) != 3 or not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field} must contain three finite numbers")
    return result


def load_existing_package_sources(
    package_root: str | Path,
) -> dict[str, LocalUSDAssetSource]:
    """Re-use the baseline package's already validated non-background closures."""

    root = Path(package_root).resolve()
    manifest = load_asset_manifest(root)
    sources: dict[str, LocalUSDAssetSource] = {}
    for entry in manifest.assets:
        canonical = (root / entry.canonical_usd).resolve()
        if root not in canonical.parents or not canonical.is_file():
            raise ValueError(f"baseline asset is unavailable: {entry.asset_id}")
        metadata = entry.metadata
        upstream_raw = metadata.get("upstream_package")
        upstream = (
            None
            if not isinstance(upstream_raw, Mapping)
            else UpstreamPackageRef(
                producer=_string(upstream_raw.get("producer"), "upstream.producer"),
                schema_version=_string(
                    upstream_raw.get("schema_version"), "upstream.schema_version"
                ),
                package_id=_string(upstream_raw.get("package_id"), "upstream.package_id"),
                revision=_string(upstream_raw.get("revision"), "upstream.revision"),
                manifest_uri=_string(upstream_raw.get("manifest_uri"), "upstream.manifest_uri"),
                manifest_sha256=_string(
                    upstream_raw.get("manifest_sha256"),
                    "upstream.manifest_sha256",
                ),
                metadata=_mapping(upstream_raw.get("metadata", {}), "upstream.metadata"),
            )
        )
        sources[entry.asset_id] = LocalUSDAssetSource(
            asset_id=entry.asset_id,
            source_usd=canonical,
            role=entry.role,
            license=entry.license,
            source_uri=str(metadata.get("source_uri", "")),
            attribution=tuple(metadata.get("attribution", [])),
            redistributable=bool(metadata.get("redistributable", False)),
            exclude_relative_paths=tuple(metadata.get("excluded_relative_paths", [])),
            root_prim_path=(
                str(metadata["root_prim_path"])
                if metadata.get("root_prim_path") is not None
                else None
            ),
            expected_sha256=entry.sha256,
            upstream_package=upstream,
        )
    return sources


def _load_existing_variants(path: Path) -> dict[str, dict[str, Any]]:
    """Load prior variant records when regenerating one candidate in place."""

    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"existing variant manifest is invalid: {path}") from exc
    if not isinstance(raw, Mapping):
        raise ValueError(f"existing variant manifest must be a mapping: {path}")
    raw_variants = raw.get("variants", [])
    if not isinstance(raw_variants, list):
        raise ValueError(f"existing variant manifest variants must be a list: {path}")
    variants: dict[str, dict[str, Any]] = {}
    for index, raw_variant in enumerate(raw_variants):
        if not isinstance(raw_variant, Mapping):
            raise ValueError(f"existing variant {index} must be a mapping: {path}")
        candidate_id = raw_variant.get("candidate_id")
        if not isinstance(candidate_id, str) or BACKGROUND_ID.fullmatch(candidate_id) is None:
            raise ValueError(f"existing variant {index} has an invalid candidate_id: {path}")
        variants[candidate_id] = dict(raw_variant)
    return variants


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_background_source(candidate: BackgroundCandidate) -> LocalUSDAssetSource:
    handoff = load_convert_asset_package_handoff(
        candidate.package_dir,
        candidate.manifest_path,
        candidate.source_usd,
        expected_scope_prims=(candidate.source_scope,),
        producer_revision=candidate.producer_revision,
        usage="visual_static_environment",
    )
    return handoff.to_local_usd_asset_source(
        asset_id=candidate.candidate_id,
        license="CC-BY-NC-4.0",
        attribution=(
            "LabUtopia-Dataset scientific environment: CC BY-NC 4.0",
            "Visual-static environment package admitted by ConvertAsset",
            "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
        ),
        redistributable=False,
        exclude_relative_paths=("_reports", "evidence"),
    )


def _validate_base_inputs(
    spec: ScenarioSpec,
    sources: Mapping[str, LocalUSDAssetSource],
) -> None:
    if spec.scene.asset_id != BASE_ENVIRONMENT_ASSET_ID:
        raise ValueError(
            "base spec must use the canonical Scene1_hard environment before substitution"
        )
    expected = {
        TABLE_ASSET_ID,
        SOURCE_VESSEL_ASSET_ID,
        TARGET_VESSEL_ASSET_ID,
        BASE_ENVIRONMENT_ASSET_ID,
    }
    missing = sorted(expected.difference(sources))
    if missing:
        raise ValueError("baseline package is missing assets: " + ", ".join(missing))
    if TABLE_ASSET_ID not in {item.asset_id for item in spec.objects}:
        raise ValueError("baseline spec must contain the eBench table object")


def _assert_fixed_workspace(
    base: ScenarioSpec,
    variant: ScenarioSpec,
    *,
    allowed_inactive_prim_paths: Sequence[str] | None = None,
) -> None:
    base_mapping = base.to_mapping()
    variant_mapping = variant.to_mapping()
    base_scene = dict(base_mapping["scene"])
    variant_scene = dict(variant_mapping["scene"])
    base_scene.pop("asset_id", None)
    variant_scene.pop("asset_id", None)
    base_scene.pop("inactive_prim_paths", None)
    variant_inactive_prim_paths = tuple(variant_scene.pop("inactive_prim_paths", []))
    expected_inactive_prim_paths = (
        tuple(base.scene.inactive_prim_paths)
        if allowed_inactive_prim_paths is None
        else tuple(allowed_inactive_prim_paths)
    )
    if variant_inactive_prim_paths != expected_inactive_prim_paths:
        raise ValueError(
            "background variant changed scene.inactive_prim_paths outside the "
            "reviewed background override"
        )
    base_pose = _mapping(base_scene.pop("pose", None), "base scene.pose")
    variant_pose = _mapping(variant_scene.pop("pose", None), "variant scene.pose")
    if base_scene != variant_scene:
        raise ValueError("background variant changed a scene field other than asset_id")
    for field in ("wxyz",):
        if variant_pose.get(field) != base_pose.get(field):
            if variant_mapping["scene"].get("asset_id", "").startswith(
                "scientific_environment_"
            ):
                # A reviewed visual-static background may rotate as an
                # instance around its source anchor.  The eBench table,
                # robot, objects, and task pose remain in their fixed fields.
                continue
            raise ValueError(
                "background placement changed the baseline scene anchor "
                f"{field}; only background instance fitting is allowed"
            )
    for field in ("objects", "robot", "steps", "invariants", "success", "max_steps", "seed"):
        if variant_mapping[field] != base_mapping[field]:
            raise ValueError(f"background variant changed fixed workspace field: {field}")


def _object_digest(spec: ScenarioSpec, object_id: str) -> str:
    for item in spec.to_mapping()["objects"]:
        if isinstance(item, Mapping) and item.get("id") == object_id:
            return _json_sha256(item)
    raise ValueError(f"scenario object is missing: {object_id}")


def _validate_admitted_package(
    package_dir: Path,
    manifest_path: Path,
    *,
    candidate_id: str,
    source_sha256: str,
    source_scope: str,
) -> None:
    if not package_dir.is_dir():
        raise ValueError(f"background package is missing: {package_dir}")
    if not manifest_path.is_file():
        raise ValueError(f"background package manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"background package manifest is invalid: {manifest_path}") from exc
    if not isinstance(manifest, Mapping):
        raise ValueError(f"background package manifest must be a mapping: {candidate_id}")
    if manifest.get("overall_status") != "pass":
        raise ValueError(f"background package is not pass: {candidate_id}")
    if manifest.get("blocked_reasons") != []:
        raise ValueError(f"background package has blockers: {candidate_id}")
    if manifest.get("asset_role") != "visual_static_environment":
        raise ValueError(f"background package is not visual-static: {candidate_id}")
    source = _mapping(manifest.get("source"), f"{candidate_id}.manifest.source")
    if source.get("sha256") != source_sha256:
        raise ValueError(f"background package source hash disagrees with admission: {candidate_id}")
    entrypoints = _mapping(manifest.get("entrypoints"), f"{candidate_id}.manifest.entrypoints")
    if entrypoints.get("root_usd") != "asset.usd":
        raise ValueError(f"background package root must be asset.usd: {candidate_id}")
    if entrypoints.get("asset_entry_prim") != source_scope:
        raise ValueError(f"background package scope disagrees with admission: {candidate_id}")
    if entrypoints.get("consumer_profile") != "scenario-forge":
        raise ValueError(f"background package consumer profile is unsupported: {candidate_id}")
    asset_usd = package_dir / "asset.usd"
    if not asset_usd.is_file():
        raise ValueError(f"background package asset.usd is missing: {candidate_id}")


def _admitted_physical_frame(
    manifest_path: Path,
    *,
    candidate_id: str,
) -> tuple[float, tuple[tuple[float, float, float], tuple[float, float, float]]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"background package manifest is invalid: {manifest_path}") from exc
    physics = _mapping(manifest.get("physics_closure"), f"{candidate_id}.physics_closure")
    frame = _mapping(
        physics.get("physical_frame"),
        f"{candidate_id}.physics_closure.physical_frame",
    )
    scale = _mapping(frame.get("package"), f"{candidate_id}.physical_frame.package")
    meters_per_unit = scale.get("meters_per_unit")
    if not isinstance(meters_per_unit, (int, float)) or isinstance(meters_per_unit, bool):
        raise ValueError(f"{candidate_id}.physical_frame.package.meters_per_unit is invalid")
    meters_per_unit = float(meters_per_unit)
    if not 0.0 < meters_per_unit < 1000.0:
        raise ValueError(f"{candidate_id}.physical_frame.package.meters_per_unit is out of range")
    bounds = frame.get("scope_bounds")
    if not isinstance(bounds, list) or len(bounds) != 1:
        raise ValueError(f"{candidate_id}.physical_frame.scope_bounds must contain one scope")
    bound = _mapping(bounds[0], f"{candidate_id}.physical_frame.scope_bounds[0]")
    raw_bound = bound.get("package_world_bound_m")
    if not isinstance(raw_bound, Mapping):
        raise ValueError(f"{candidate_id}.package_world_bound_m must be a mapping")
    lower = _number_tuple(raw_bound.get("min"), f"{candidate_id}.package_world_bound_m.min")
    upper = _number_tuple(raw_bound.get("max"), f"{candidate_id}.package_world_bound_m.max")
    if any(upper[index] <= lower[index] for index in range(3)):
        raise ValueError(f"{candidate_id}.package_world_bound_m is empty")
    return meters_per_unit, (lower, upper)


def _raw_source_composed_bounds(
    candidate: BackgroundCandidate,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Recover source-composed coordinates from ConvertAsset's stage frame.

    ConvertAsset preserves source USD metadata in its visual-static package.
    Its recorded world bounds are therefore useful for locating the source
    anchor, but profile coordinates may use a separately calibrated metric
    scale.  This helper deliberately returns the raw composed coordinates
    before that profile-specific conversion.
    """

    lower, upper = candidate.physical_bounds_m
    return (
        tuple(value / candidate.meters_per_unit for value in lower),
        tuple(value / candidate.meters_per_unit for value in upper),
    )


def _source_composed_metric_bounds(
    candidate: BackgroundCandidate,
    source_composed_meters_per_unit: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    lower, upper = _raw_source_composed_bounds(candidate)
    return (
        tuple(value * source_composed_meters_per_unit for value in lower),
        tuple(value * source_composed_meters_per_unit for value in upper),
    )


def _source_root_transform(
    manifest_path: Path,
    *,
    candidate_id: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Read the source root transform recorded by ConvertAsset.

    The eBench scene layer authors a transform on the destination ``room`` prim.
    USD composition then overrides the referenced ``/World`` root transform, so
    this transform must be folded into the destination instance pose.  The
    admission evidence currently records uniform, axis-aligned roots; reject a
    rotated/sheared root rather than silently changing its appearance.
    """

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"background package manifest is invalid: {manifest_path}") from exc
    fingerprint = _mapping(
        manifest.get("visual_preservation_fingerprint"),
        f"{candidate_id}.visual_preservation_fingerprint",
    )
    raw_source = _mapping(
        fingerprint.get("raw_source"),
        f"{candidate_id}.visual_preservation_fingerprint.raw_source",
    )
    transforms = _mapping(
        raw_source.get("scope_world_transforms"),
        f"{candidate_id}.scope_world_transforms",
    )
    matrix = transforms.get("/World")
    if (
        not isinstance(matrix, list)
        or len(matrix) != 4
        or any(
            not isinstance(row, list)
            or len(row) != 4
            or not all(
                isinstance(value, (int, float)) and not isinstance(value, bool) for value in row
            )
            for row in matrix
        )
    ):
        raise ValueError(f"{candidate_id}.scope_world_transforms./World is invalid")
    values = tuple(tuple(float(value) for value in row) for row in matrix)
    if not all(math.isfinite(value) for row in values for value in row):
        raise ValueError(f"{candidate_id}.scope_world_transforms./World is non-finite")
    diagonal = tuple(values[index][index] for index in range(3))
    if any(value <= 0.0 for value in diagonal):
        raise ValueError(f"{candidate_id}.source root transform must have positive scale")
    for row in range(3):
        for column in range(3):
            expected = diagonal[row] if row == column else 0.0
            if not math.isclose(values[row][column], expected, rel_tol=1e-6, abs_tol=1e-8):
                raise ValueError(
                    f"{candidate_id}.source root transform has rotation/shear; "
                    "instance placement requires an explicit transform adapter"
                )
    if not math.isclose(values[3][3], 1.0, rel_tol=1e-6, abs_tol=1e-8):
        raise ValueError(f"{candidate_id}.source root transform has invalid homogeneous row")
    if any(abs(values[3][index]) > 1e12 for index in range(3)):
        raise ValueError(f"{candidate_id}.source root transform translation is out of range")
    for index in range(3):
        if abs(values[index][3]) > 1e-8:
            raise ValueError(f"{candidate_id}.source root transform has perspective terms")
    return diagonal, tuple(values[3][index] for index in range(3))


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _digest_without_prefix(value: str) -> str:
    return value.removeprefix("sha256:")


def _positive_finite_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return result


def _number_tuple(value: object, field: str) -> tuple[float, float, float]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        raise ValueError(f"{field} must contain three numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{field} must contain finite numbers")
    return result  # type: ignore[return-value]


def _prim_path(value: object, field: str) -> str:
    path = _string(value, field)
    if path != "/World" and not path.startswith("/World/"):
        raise ValueError(f"{field} must be inside /World")
    return path


def _prim_path_tuple(
    value: object,
    field: str,
    *,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    paths = tuple(_prim_path(item, f"{field}[{index}]") for index, item in enumerate(value))
    if require_nonempty and not paths:
        raise ValueError(f"{field} must not be empty")
    if len(set(paths)) != len(paths):
        raise ValueError(f"{field} must not contain duplicate paths")
    return paths


def _json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(payload).hexdigest()}"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())

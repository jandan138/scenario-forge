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
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.adapters.generated_environment import (
    GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION,
)
from scenario_forge.assets.external_environment import (
    EXTERNAL_ENVIRONMENT_INTAKE_SCHEMA_VERSION,
)
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
BACKGROUND_ASSET_ID = re.compile(
    r"^scientific_environment_(?!.*__)[a-z0-9](?:[a-z0-9_]*[a-z0-9])?$"
)
ZONE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9_]*[a-z0-9])?$")
SCENARIO_SUFFIX = re.compile(r"^[a-z0-9](?:[a-z0-9_]*[a-z0-9])?$")
LEGACY_BACKGROUND_ASSET_ID = re.compile(r"^scientific_environment_[0-9]+$")
VARIANT_SCHEMA = "scenario-forge-scientific-workbench-background-variants/v0.2"
WORKSPACE_PROFILE_SCHEMA = "scenario-forge-convertasset-workspace-integration-profile/v0.1"
WORKSPACE_PROFILE_MANIFEST_SCHEMA = (
    "scenario-forge-convertasset-workspace-integration-profile-manifest/v0.1"
)
WORKSPACE_ZONE_PROFILE_SCHEMA = "scenario-forge-convertasset-workspace-zone-profile/v0.2"
WORKSPACE_ZONE_PROFILE_MANIFEST_SCHEMA = (
    "scenario-forge-convertasset-workspace-zone-profile-manifest/v0.2"
)
USD_Z_UP_RIGHT_HANDED_CCW = "usd_z_up_right_handed_ccw"
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
EBENCH_BACKGROUND_CONSUMER_SCOPE = "/World"
# The target is the upper work area, so the overview camera remains below the
# delivered room's 3.3 m ceiling while looking across the robot and table.
RUNTIME_CONTEXT_CAMERA_DISTANCE_M = 2.8
# A room-context view needs a little more working distance than the task-only
# overview.  The direction comes from the producer's authored Perspective
# camera; only its target is moved to the fixed eBench workspace.
AUTHORED_CONTEXT_CAMERA_DISTANCE_M = 4.0
# High three-quarter view from the robot side of the fixed eBench workcell.
# Looking from the table's opposite side hides Lift2 behind the opaque work
# surface once a complete room is restored.
RUNTIME_CONTEXT_CAMERA_DIRECTION_XYZ = (
    -0.6791078223508457,
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
class WorkspaceZoneProfile:
    """One source-bound replacement zone within an admitted room asset."""

    background_asset_id: str
    zone_id: str
    status: str
    profile_path: Path
    producer_revision: str
    producer_git_commit: str
    anchor: WorkspaceAnchor | None = None
    raw_anchor_xyz_su: tuple[float, float, float] | None = None
    source_composed_meters_per_unit: float | None = None
    raw_clearance_aabb_su: tuple[tuple[float, float, float], tuple[float, float, float]] | None = (
        None
    )
    composition_yaw_deg: float = 0.0
    # Optional source-bound camera pose supplied by ConvertAsset profile v0.3.
    # Coordinates stay in the producer's source-composed frame until the
    # background instance placement is known.
    evidence_camera_position_xyz_su: tuple[float, float, float] | None = None
    evidence_camera_target_xyz_su: tuple[float, float, float] | None = None
    optional_inactive_prim_paths: tuple[str, ...] = ()
    not_applicable_reason: str | None = None
    consumer_exclusion_reason: str | None = None

    @property
    def variant_id(self) -> str:
        return f"{self.background_asset_id}__{self.zone_id}"


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
    root_yaw_deg: float = 0.0
    license: str = "CC-BY-NC-4.0"
    attribution: tuple[str, ...] = (
        "LabUtopia-Dataset scientific environment: CC BY-NC 4.0",
        "Visual-static environment package admitted by ConvertAsset",
        "Bundled NVIDIA/Omniverse dependencies retain their upstream terms",
    )
    redistributable: bool = False
    source_uri: str = "upstream-environment://legacy-scientific-environment"
    external_tree_sha256: str | None = None
    external_archive_sha256: str | None = None
    restricted_provenance_reference: str | None = None
    generated_closure_sha256: str | None = None
    generated_manifest_sha256: str | None = None
    generated_producer_revision: str | None = None
    generated_run_id: str | None = None
    # A producer-owned consumer facade can differ byte-for-byte from the raw
    # source that restricted intake and workspace profiles bind.  Keep both
    # identities: the raw source establishes provenance; the facade is the
    # source ConvertAsset used to make the consumable package.
    package_source_usd: Path | None = None
    package_source_sha256: str | None = None
    facade_provenance_path: Path | None = None


@dataclass(frozen=True)
class BackgroundZoneVariant:
    """A task-package variant backed by one shared room asset and one zone."""

    candidate: BackgroundCandidate
    zone: WorkspaceZoneProfile

    @property
    def variant_id(self) -> str:
        return self.zone.variant_id

    @property
    def scenario_suffix(self) -> str:
        asset_suffix = self.candidate.candidate_id.removeprefix("scientific_environment_")
        return f"{asset_suffix}_zone_{self.zone.zone_id}"

    @property
    def anchor(self) -> WorkspaceAnchor | None:
        return self.zone.anchor

    @property
    def composition_yaw_deg(self) -> float:
        return self.zone.composition_yaw_deg


@dataclass(frozen=True)
class BackgroundTaskVariant:
    """One generated task package, legacy candidate or named room zone."""

    candidate: BackgroundCandidate
    variant_id: str
    scenario_suffix: str
    anchor: WorkspaceAnchor | None
    composition_yaw_deg: float
    workspace_profile: WorkspaceProfile | None = None
    workspace_zone_profile: WorkspaceZoneProfile | None = None


def is_background_asset_id(value: str) -> bool:
    """Return whether ``value`` is a safe reusable background asset identity."""

    return BACKGROUND_ASSET_ID.fullmatch(value) is not None


def validate_generation_background_provenance(
    candidates: Sequence[BackgroundCandidate],
) -> None:
    """Require a restricted intake before compiling a non-legacy room.

    The original numeric screening set predates external-room intake records and
    retains its recorded provenance.  A named room has no such inherited
    provenance: it must have been bound by ``--external-intake`` so the output
    cannot silently inherit the legacy dataset attribution.
    """

    unbound = [
        candidate.candidate_id
        for candidate in candidates
        if LEGACY_BACKGROUND_ASSET_ID.fullmatch(candidate.candidate_id) is None
        and not (
            (
                candidate.license == "LicenseRef-Internal-Restricted"
                and candidate.redistributable is False
                and candidate.source_uri.startswith("restricted-environment://")
                and candidate.external_tree_sha256 is not None
                and candidate.external_archive_sha256 is not None
                and candidate.restricted_provenance_reference is not None
            )
            or (
                candidate.license == "LicenseRef-Internal-Generated"
                and candidate.redistributable is False
                and candidate.source_uri.startswith(
                    "generated-environment://code-as-room/"
                )
                and candidate.generated_closure_sha256 is not None
                and candidate.generated_manifest_sha256 is not None
                and candidate.generated_producer_revision is not None
                and candidate.generated_run_id is not None
            )
        )
    ]
    if unbound:
        raise ValueError(
            "non-legacy background assets require a matching external or generated intake "
            "before generation: "
            + ", ".join(sorted(unbound))
        )


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
        "--external-intake",
        type=Path,
        help=(
            "Optional restricted external-environment intake record. It supplies "
            "license and provenance for one admitted non-LabUtopia background asset."
        ),
    )
    parser.add_argument(
        "--generated-environment-intake",
        type=Path,
        help=(
            "Optional generated-environment intake. It binds a Code-as-Room "
            "producer delivery without copying local source paths."
        ),
    )
    parser.add_argument(
        "--workspace-profiles",
        type=Path,
        help=(
            "ConvertAsset workspace_profiles_manifest.json. When supplied, only "
            "profiled or built-in-reviewed background integrations are generated."
        ),
    )
    parser.add_argument(
        "--workspace-zone-profiles",
        type=Path,
        help=(
            "ConvertAsset v0.2 workspace-zone profile manifest for one admitted "
            "room asset with multiple independently selectable workcells."
        ),
    )
    parser.add_argument(
        "--candidate-id",
        help="Optionally regenerate one candidate in an existing output root.",
    )
    parser.add_argument(
        "--background-asset-id",
        help="Generate every profiled zone for one admitted background asset.",
    )
    parser.add_argument(
        "--variant-id",
        help="Optionally regenerate one named workspace-zone variant.",
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
    if (
        args.external_intake is not None
        and args.generated_environment_intake is not None
    ):
        raise SystemExit(
            "--external-intake and --generated-environment-intake are mutually exclusive"
        )
    if args.workspace_profiles is not None and args.workspace_zone_profiles is not None:
        raise SystemExit("--workspace-profiles and --workspace-zone-profiles are mutually exclusive")
    if args.workspace_zone_profiles is not None and args.candidate_id is not None:
        raise SystemExit("--candidate-id is only supported with legacy workspace profiles")
    if args.workspace_zone_profiles is None and (
        args.background_asset_id is not None or args.variant_id is not None
    ):
        raise SystemExit(
            "--background-asset-id and --variant-id require --workspace-zone-profiles"
        )

    base_spec = load_scenario_spec(args.spec)
    admitted_candidates = load_admitted_backgrounds(args.admission, args.background_root)
    if args.external_intake is not None:
        admitted_candidates = apply_external_environment_intake(
            admitted_candidates,
            args.external_intake,
        )
    if args.generated_environment_intake is not None:
        admitted_candidates = apply_generated_environment_intake(
            admitted_candidates,
            args.generated_environment_intake,
        )
    try:
        validate_generation_background_provenance(admitted_candidates)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    workspace_profiles: Mapping[str, WorkspaceProfile] = {}
    workspace_zone_profiles: Mapping[str, WorkspaceZoneProfile] = {}
    excluded_workspace_candidates: dict[str, str] = {}
    excluded_workspace_variants: dict[str, str] = {}
    manifest_task_variants: tuple[BackgroundTaskVariant, ...]
    if args.workspace_zone_profiles is not None:
        workspace_zone_profiles = load_workspace_zone_profiles(
            args.workspace_zone_profiles,
            admitted_candidates,
        )
        try:
            eligible_zone_variants, excluded_workspace_variants = select_workspace_zone_variants(
                admitted_candidates,
                workspace_zone_profiles,
                background_asset_id=args.background_asset_id,
            )
            selected_zone_variants, _ = select_workspace_zone_variants(
                admitted_candidates,
                workspace_zone_profiles,
                background_asset_id=args.background_asset_id,
                variant_id=args.variant_id,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        manifest_task_variants = tuple(
            BackgroundTaskVariant(
                candidate=item.candidate,
                variant_id=item.variant_id,
                scenario_suffix=item.scenario_suffix,
                anchor=item.anchor,
                composition_yaw_deg=item.composition_yaw_deg,
                workspace_zone_profile=item.zone,
            )
            for item in eligible_zone_variants
        )
        task_variants = tuple(
            BackgroundTaskVariant(
                candidate=item.candidate,
                variant_id=item.variant_id,
                scenario_suffix=item.scenario_suffix,
                anchor=item.anchor,
                composition_yaw_deg=item.composition_yaw_deg,
                workspace_zone_profile=item.zone,
            )
            for item in selected_zone_variants
        )
    elif args.workspace_profiles is not None:
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
        manifest_task_variants = tuple(
            BackgroundTaskVariant(
                candidate=candidate,
                variant_id=candidate.candidate_id,
                scenario_suffix=candidate.candidate_id.removeprefix("scientific_environment_"),
                anchor=workspace_anchor_for(candidate, workspace_profiles),
                composition_yaw_deg=workspace_composition_yaw_deg(candidate),
                workspace_profile=workspace_profiles.get(candidate.candidate_id),
            )
            for candidate in manifest_candidates
        )
        task_variants = tuple(
            BackgroundTaskVariant(
                candidate=candidate,
                variant_id=candidate.candidate_id,
                scenario_suffix=candidate.candidate_id.removeprefix("scientific_environment_"),
                anchor=workspace_anchor_for(candidate, workspace_profiles),
                composition_yaw_deg=workspace_composition_yaw_deg(candidate),
                workspace_profile=workspace_profiles.get(candidate.candidate_id),
            )
            for candidate in candidates
        )
    if args.workspace_profiles is None and args.workspace_zone_profiles is None:
        candidates = admitted_candidates
        if args.candidate_id is not None:
            candidates = tuple(
                candidate for candidate in candidates if candidate.candidate_id == args.candidate_id
            )
            if not candidates:
                raise SystemExit(f"candidate id is not present in admission: {args.candidate_id}")
        manifest_task_variants = tuple(
            BackgroundTaskVariant(
                candidate=candidate,
                variant_id=candidate.candidate_id,
                scenario_suffix=candidate.candidate_id.removeprefix("scientific_environment_"),
                anchor=workspace_anchor_for(candidate),
                composition_yaw_deg=workspace_composition_yaw_deg(candidate),
            )
            for candidate in admitted_candidates
        )
        task_variants = tuple(
            BackgroundTaskVariant(
                candidate=candidate,
                variant_id=candidate.candidate_id,
                scenario_suffix=candidate.candidate_id.removeprefix("scientific_environment_"),
                anchor=workspace_anchor_for(candidate),
                composition_yaw_deg=workspace_composition_yaw_deg(candidate),
            )
            for candidate in candidates
        )
    base_sources = load_existing_package_sources(args.base_package)
    _validate_base_inputs(base_spec, base_sources)

    output_root = args.out.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    existing_variants = (
        _load_existing_variants(output_root / "background_variants_manifest.json")
        if args.candidate_id is not None or args.variant_id is not None
        else {}
    )
    results: list[dict[str, Any]] = []
    for task_variant in task_variants:
        candidate = task_variant.candidate
        anchor = task_variant.anchor
        inactive_prim_paths = reviewed_workspace_inactive_prim_paths(
            anchor,
            task_variant.workspace_zone_profile,
        )
        placement = background_placement(
            base_spec,
            candidate,
            anchor=anchor,
            composition_yaw_deg=task_variant.composition_yaw_deg,
        )
        variant = make_variant_spec(
            base_spec,
            candidate.candidate_id,
            scenario_suffix=task_variant.scenario_suffix,
            scene_pose=placement["scene_pose"],
            inactive_prim_paths=inactive_prim_paths,
        )
        _assert_fixed_workspace(
            base_spec,
            variant,
            allowed_inactive_prim_paths=(None if anchor is None else inactive_prim_paths),
        )
        background_source = _load_background_source(candidate)
        sources = {
            **base_sources,
            candidate.candidate_id: background_source,
        }
        package_root = output_root / task_variant.variant_id
        compiled = compile_scenario_package(variant, sources, package_root)
        tabletop_placement = validate_scientific_workbench_tabletop_placement(
            compiled.package_root
        )
        export = export_genmanip_collected_package(compiled.package_root)
        _configure_background_preview(
            export.output_dir,
            placement,
            candidate,
            anchor=anchor,
            workspace_zone=task_variant.workspace_zone_profile,
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
                "variant_id": task_variant.variant_id,
                "background_asset_id": candidate.candidate_id,
                "candidate_id": candidate.candidate_id,
                **(
                    {"zone_id": task_variant.workspace_zone_profile.zone_id}
                    if task_variant.workspace_zone_profile is not None
                    else {}
                ),
                "scenario_id": variant.scenario_id,
                "package_root": str(compiled.package_root),
                "tabletop_placement_policy": {
                    "status": tabletop_placement.overall_status,
                    "evidence_path": str(tabletop_placement.evidence_path),
                },
                "genmanip_root": str(export.output_dir),
                "background_manifest": str(candidate.manifest_path),
                "background_source_sha256": candidate.source_sha256,
                "background_package_source_sha256": (
                    candidate.package_source_sha256 or candidate.source_sha256
                ),
                "background_provenance": {
                    "license": candidate.license,
                    "attribution": list(candidate.attribution),
                    "redistributable": candidate.redistributable,
                    "source_uri": candidate.source_uri,
                    **(
                        {
                            "restricted_source_snapshot": {
                                "tree_sha256": candidate.external_tree_sha256,
                                "archive_sha256": candidate.external_archive_sha256,
                                "internal_reference": candidate.restricted_provenance_reference,
                            }
                        }
                        if candidate.external_tree_sha256 is not None
                        else {}
                    ),
                    **(
                        {
                            "generated_source_snapshot": {
                                "declared_closure_sha256": (
                                    candidate.generated_closure_sha256
                                ),
                                "producer_manifest_sha256": (
                                    candidate.generated_manifest_sha256
                                ),
                                "producer_revision": (
                                    candidate.generated_producer_revision
                                ),
                                "run_id": candidate.generated_run_id,
                            }
                        }
                        if candidate.generated_closure_sha256 is not None
                        else {}
                    ),
                },
                "background_placement": {
                    key: value for key, value in placement.items() if key != "scene_pose"
                },
                "workspace_integration": (
                    _workspace_zone_integration_record(task_variant.workspace_zone_profile)
                    if task_variant.workspace_zone_profile is not None
                    else _workspace_integration_record(task_variant.workspace_profile, anchor)
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

    if args.candidate_id is None and args.variant_id is None:
        variants = results
    else:
        merged_variants = {**existing_variants}
        merged_variants.update({str(result["variant_id"]): result for result in results})
        variants = [
            merged_variants[item.variant_id]
            for item in manifest_task_variants
            if item.variant_id in merged_variants
        ]

    manifest = {
        "schema_version": VARIANT_SCHEMA,
        "base_scenario_id": base_spec.scenario_id,
        "base_spec": str(args.spec.resolve()),
        "base_package": str(args.base_package.resolve()),
        "admission_request": str(args.admission.resolve()),
        **(
            {"external_intake": str(args.external_intake.resolve())}
            if args.external_intake is not None
            else {}
        ),
        **(
            {
                "workspace_profiles_manifest": str(args.workspace_profiles.resolve()),
                "excluded_workspace_candidates": excluded_workspace_candidates,
            }
            if args.workspace_profiles is not None
            else {}
        ),
        **(
            {
                "workspace_zone_profiles_manifest": str(
                    args.workspace_zone_profiles.resolve()
                ),
                "excluded_workspace_variants": excluded_workspace_variants,
                "variant_selection": (
                    "Select one variants[].variant_id before starting an eBench episode; "
                    "GenManip receives one ordinary package and has no runtime zone switch."
                ),
            }
            if args.workspace_zone_profiles is not None
            else {}
        ),
        "candidate_count": len(
            {str(variant["background_asset_id"]) for variant in variants}
        ),
        "variant_count": len(variants),
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
        if not is_background_asset_id(candidate_id):
            raise ValueError(f"invalid background candidate_id: {candidate_id}")
        if candidate_id in seen:
            raise ValueError(f"duplicate background candidate_id: {candidate_id}")
        seen.add(candidate_id)
        source_usd = _resolve_declared_path(
            _string(item.get("source_usd"), "source_usd"),
            path.parent,
        )
        source_sha256 = _digest_without_prefix(_string(item.get("source_sha256"), "source_sha256"))
        if file_sha256(source_usd) != f"sha256:{source_sha256}":
            raise ValueError(f"source USD hash mismatch: {candidate_id}")
        source_scope = _string(item.get("source_scope"), "source_scope")
        if source_scope != EBENCH_BACKGROUND_CONSUMER_SCOPE:
            raise ValueError(
                "background admission must expose the eBench consumer facade scope "
                f"{EBENCH_BACKGROUND_CONSUMER_SCOPE}; ConvertAsset must adapt an "
                "authored non-/World root without modifying the source USD"
            )
        required_return = _mapping(
            item.get("required_return"),
            f"admission.items[{index}].required_return",
        )
        if required_return.get("overall_status") != "pass":
            raise ValueError(f"background candidate is not required to pass: {candidate_id}")

        package_dir_value = item.get("package_dir")
        package_dir = (
            (packages / candidate_id).resolve()
            if package_dir_value is None
            else _resolve_declared_path(
                _string(package_dir_value, f"admission.items[{index}].package_dir"),
                path.parent,
            )
        )
        if packages != package_dir and packages not in package_dir.parents:
            raise ValueError(
                "background package directory must be contained by --background-root: "
                f"{candidate_id}"
            )
        manifest_path = package_dir / "evidence" / "manifest.json"
        package_source_usd = _resolve_declared_path(
            _string(
                item.get("package_source_usd", str(source_usd)),
                f"admission.items[{index}].package_source_usd",
            ),
            path.parent,
        )
        package_source_sha256 = _digest_without_prefix(
            _string(
                item.get("package_source_sha256", source_sha256),
                f"admission.items[{index}].package_source_sha256",
            )
        )
        if file_sha256(package_source_usd) != f"sha256:{package_source_sha256}":
            raise ValueError(f"package source USD hash mismatch: {candidate_id}")
        _validate_admitted_package(
            package_dir,
            manifest_path,
            candidate_id=candidate_id,
            package_source_sha256=package_source_sha256,
            source_scope=source_scope,
        )
        facade_provenance_path: Path | None = None
        if (
            package_source_usd != source_usd
            or package_source_sha256 != source_sha256
            or item.get("facade_provenance") is not None
        ):
            facade_provenance_path = _resolve_declared_path(
                _string(
                    item.get(
                        "facade_provenance",
                        str(manifest_path.parent / "facade_provenance.json"),
                    ),
                    f"admission.items[{index}].facade_provenance",
                ),
                path.parent,
            )
            _validate_facade_provenance(
                facade_provenance_path,
                candidate_id=candidate_id,
                raw_source_usd=source_usd,
                raw_source_sha256=source_sha256,
                source_scope=source_scope,
            )
        meters_per_unit, physical_bounds_m = _admitted_physical_frame(
            manifest_path,
            candidate_id=candidate_id,
        )
        root_scale_xyz, root_translate_xyz, root_yaw_deg = _source_root_transform(
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
                root_yaw_deg=root_yaw_deg,
                package_source_usd=package_source_usd,
                package_source_sha256=package_source_sha256,
                facade_provenance_path=facade_provenance_path,
            )
        )
    return tuple(candidates)


def apply_external_environment_intake(
    candidates: Sequence[BackgroundCandidate],
    intake_path: str | Path,
) -> tuple[BackgroundCandidate, ...]:
    """Attach restricted provenance without leaking a source path or signed URL.

    ConvertAsset admission still establishes the package and source hash.  This
    adapter only replaces the legacy background-license defaults for the one
    external asset explicitly bound by the intake record.
    """

    path = Path(intake_path).resolve()
    try:
        raw_intake = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"external environment intake is invalid: {path}") from exc
    intake = _mapping(raw_intake, "external environment intake")
    if intake.get("schema_version") != EXTERNAL_ENVIRONMENT_INTAKE_SCHEMA_VERSION:
        raise ValueError("external environment intake schema is unsupported")
    background_asset_id = _string(intake.get("asset_id"), "external environment intake.asset_id")
    if not is_background_asset_id(background_asset_id):
        raise ValueError("external environment intake has an invalid background asset id")
    if intake.get("asset_role") != "visual_static_environment":
        raise ValueError("external environment intake asset_role is unsupported")
    license_name = _string(intake.get("license"), "external environment intake.license")
    if license_name != "LicenseRef-Internal-Restricted":
        raise ValueError("external environment intake license must be internal restricted")
    if intake.get("redistributable") is not False:
        raise ValueError("external environment intake must be non-redistributable")
    raw_attribution = intake.get("attribution")
    if not isinstance(raw_attribution, list) or not raw_attribution:
        raise ValueError("external environment intake.attribution must be a non-empty list")
    attribution = tuple(
        _string(item, f"external environment intake.attribution[{index}]")
        for index, item in enumerate(raw_attribution)
    )
    source = _mapping(intake.get("source"), "external environment intake.source")
    source_sha256 = _digest_without_prefix(
        _string(source.get("usd_sha256"), "external environment intake.source.usd_sha256")
    )
    source_tree_sha256 = _sha256_hex(
        _string(
            source.get("tree_sha256"),
            "external environment intake.source.tree_sha256",
        ),
        "external environment intake.source.tree_sha256",
    )
    archive = _mapping(intake.get("archive"), "external environment intake.archive")
    archive_sha256 = _sha256_hex(
        _string(archive.get("sha256"), "external environment intake.archive.sha256"),
        "external environment intake.archive.sha256",
    )
    provenance = _mapping(intake.get("provenance"), "external environment intake.provenance")
    if provenance.get("visibility") != "restricted":
        raise ValueError("external environment intake provenance must be restricted")
    internal_reference = _string(
        provenance.get("internal_reference"),
        "external environment intake.provenance.internal_reference",
    )
    if re.fullmatch(r"restricted/[A-Za-z0-9][A-Za-z0-9._/-]*", internal_reference) is None:
        raise ValueError("external environment intake provenance reference is invalid")

    matching = [
        candidate for candidate in candidates if candidate.candidate_id == background_asset_id
    ]
    if len(matching) != 1:
        raise ValueError(
            "external environment intake background asset must appear exactly once in admission: "
            f"{background_asset_id}"
        )
    candidate = matching[0]
    if candidate.source_sha256 != source_sha256:
        raise ValueError("external environment intake source hash disagrees with admission")
    return tuple(
        replace(
            item,
            license=license_name,
            attribution=(
                *attribution,
                f"Restricted extracted source tree SHA-256: {source_tree_sha256}.",
                f"Restricted source archive SHA-256: {archive_sha256}.",
            ),
            redistributable=False,
            source_uri=f"restricted-environment://{internal_reference}",
            external_tree_sha256=source_tree_sha256,
            external_archive_sha256=archive_sha256,
            restricted_provenance_reference=internal_reference,
        )
        if item.candidate_id == background_asset_id
        else item
        for item in candidates
    )


def apply_generated_environment_intake(
    candidates: Sequence[BackgroundCandidate],
    intake_path: str | Path,
) -> tuple[BackgroundCandidate, ...]:
    """Attach portable Code-as-Room provenance to one admitted background."""

    path = Path(intake_path).resolve()
    try:
        raw_intake = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"generated environment intake is invalid: {path}") from exc
    intake = _mapping(raw_intake, "generated environment intake")
    if intake.get("schema_version") != GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION:
        raise ValueError("generated environment intake schema is unsupported")
    background_asset_id = _string(
        intake.get("asset_id"),
        "generated environment intake.asset_id",
    )
    if not is_background_asset_id(background_asset_id):
        raise ValueError("generated environment intake has an invalid background asset id")
    if intake.get("asset_role") != "visual_static_environment":
        raise ValueError("generated environment intake asset_role is unsupported")
    if intake.get("license") != "LicenseRef-Internal-Generated":
        raise ValueError(
            "generated environment intake license must be internal generated"
        )
    if intake.get("redistributable") is not False:
        raise ValueError("generated environment intake must be non-redistributable")
    raw_attribution = intake.get("attribution")
    if not isinstance(raw_attribution, list) or not raw_attribution:
        raise ValueError("generated environment intake attribution must be non-empty")
    attribution = tuple(
        _string(item, f"generated environment intake.attribution[{index}]")
        for index, item in enumerate(raw_attribution)
    )

    source = _mapping(intake.get("source"), "generated environment intake.source")
    source_sha256 = _digest_without_prefix(
        _string(
            source.get("usd_sha256"),
            "generated environment intake.source.usd_sha256",
        )
    )
    closure_sha256 = _sha256_hex(
        _string(
            source.get("declared_closure_sha256"),
            "generated environment intake.source.declared_closure_sha256",
        ),
        "generated environment intake.source.declared_closure_sha256",
    )
    producer = _mapping(
        intake.get("producer"),
        "generated environment intake.producer",
    )
    if producer.get("repo") != "Code-as-Room":
        raise ValueError("generated environment intake producer must be Code-as-Room")
    revision = _string(
        producer.get("revision"),
        "generated environment intake.producer.revision",
    )
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("generated environment producer revision is invalid")
    run_id = _string(
        producer.get("run_id"),
        "generated environment intake.producer.run_id",
    )
    manifest_sha256 = _sha256_hex(
        _string(
            producer.get("manifest_sha256"),
            "generated environment intake.producer.manifest_sha256",
        ),
        "generated environment intake.producer.manifest_sha256",
    )
    provenance = _mapping(
        intake.get("provenance"),
        "generated environment intake.provenance",
    )
    if provenance.get("kind") != "generated_blender_room":
        raise ValueError("generated environment provenance kind is unsupported")
    if provenance.get("visibility") != "internal":
        raise ValueError("generated environment provenance must be internal")
    source_uri = _string(
        provenance.get("source_uri"),
        "generated environment intake.provenance.source_uri",
    )
    expected_uri = f"generated-environment://code-as-room/{revision}/{run_id}"
    if source_uri != expected_uri:
        raise ValueError("generated environment provenance URI disagrees with producer")

    matching = [
        candidate
        for candidate in candidates
        if candidate.candidate_id == background_asset_id
    ]
    if len(matching) != 1:
        raise ValueError(
            "generated environment intake background asset must appear exactly once "
            f"in admission: {background_asset_id}"
        )
    if matching[0].source_sha256 != source_sha256:
        raise ValueError("generated environment intake source hash disagrees with admission")

    return tuple(
        replace(
            candidate,
            license="LicenseRef-Internal-Generated",
            attribution=(
                *attribution,
                f"Code-as-Room revision: {revision}.",
                f"Code-as-Room run ID: {run_id}.",
            ),
            redistributable=False,
            source_uri=source_uri,
            generated_closure_sha256=closure_sha256,
            generated_manifest_sha256=manifest_sha256,
            generated_producer_revision=revision,
            generated_run_id=run_id,
        )
        if candidate.candidate_id == background_asset_id
        else candidate
        for candidate in candidates
    )


def make_variant_spec(
    spec: ScenarioSpec,
    candidate_id: str,
    *,
    scenario_suffix: str | None = None,
    scene_pose: Mapping[str, Any] | None = None,
    inactive_prim_paths: Sequence[str] | None = None,
) -> ScenarioSpec:
    """Return a variant with a background identity and optional instance pose."""

    if not is_background_asset_id(candidate_id):
        raise ValueError(f"invalid background candidate_id: {candidate_id}")
    suffix = (
        candidate_id.removeprefix("scientific_environment_")
        if scenario_suffix is None
        else scenario_suffix
    )
    if SCENARIO_SUFFIX.fullmatch(suffix) is None:
        raise ValueError(f"invalid background scenario suffix: {suffix}")
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
        if not isinstance(candidate_id, str) or not is_background_asset_id(candidate_id):
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


def load_workspace_zone_profiles(
    manifest_path: str | Path,
    candidates: Sequence[BackgroundCandidate],
) -> dict[str, WorkspaceZoneProfile]:
    """Load multiple source-bound workcell zones for one admitted room asset.

    Version 0.2 deliberately keeps the immutable background asset identity
    separate from the task-package ``variant_id``.  This lets several reviewed
    workcells share exactly one ConvertAsset visual-static package.
    """

    path = Path(manifest_path).resolve()
    try:
        raw_manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"workspace zone profile manifest is invalid: {path}") from exc
    manifest = _mapping(raw_manifest, "workspace zone profile manifest")
    if manifest.get("schema_version") != WORKSPACE_ZONE_PROFILE_MANIFEST_SCHEMA:
        raise ValueError("workspace zone profile manifest schema is unsupported")
    background_asset_id = _string(
        manifest.get("background_asset_id"),
        "workspace zone profile manifest.background_asset_id",
    )
    if not is_background_asset_id(background_asset_id):
        raise ValueError("workspace zone profile manifest has an invalid background asset id")
    admitted_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    candidate = admitted_by_id.get(background_asset_id)
    if candidate is None:
        raise ValueError(
            "workspace zone profile background asset is not present in admission: "
            f"{background_asset_id}"
        )
    root = path.parent
    # Producer v0.2 profiles bind the immutable raw room hash and point back
    # to the admitted facade manifest.  Earlier internal fixtures bind source
    # paths per profile; retain that dialect so older admitted rooms remain
    # rebuildable.
    if manifest.get("source") is not None:
        _validate_workspace_profile_source(
            {"source": manifest.get("source")},
            candidate,
            "workspace zone profile manifest",
            declaration_root=root,
            require_facade_provenance=False,
        )
    raw_zones = _mapping(manifest.get("zones"), "workspace zone profile manifest.zones")
    if not raw_zones:
        raise ValueError("workspace zone profile manifest.zones must not be empty")

    profiles: dict[str, WorkspaceZoneProfile] = {}
    for zone_id, raw_entry in raw_zones.items():
        if not isinstance(zone_id, str) or not _is_zone_id(zone_id):
            raise ValueError("workspace zone profile manifest has an invalid zone id")
        entry = _mapping(raw_entry, f"workspace zone profile manifest.{zone_id}")
        manifest_status = _string(
            entry.get("status"),
            f"workspace zone profile manifest.{zone_id}.status",
        )
        if manifest_status not in {"profiled", "not_applicable"}:
            raise ValueError(f"workspace zone profile status is unsupported: {zone_id}")
        profile_value = entry.get("profile")
        if profile_value is None:
            if manifest_status != "not_applicable":
                raise ValueError(
                    f"workspace zone profile is unavailable for {zone_id}: profile is required"
                )
            producer_revision, producer_git_commit = _workspace_profile_producer(
                manifest,
                "workspace zone profile manifest",
            )
            profiles[f"{background_asset_id}__{zone_id}"] = WorkspaceZoneProfile(
                background_asset_id=background_asset_id,
                zone_id=zone_id,
                status=manifest_status,
                profile_path=path,
                producer_revision=producer_revision,
                producer_git_commit=producer_git_commit,
                not_applicable_reason=_string(
                    entry.get("reason"),
                    f"workspace zone profile manifest.{zone_id}.reason",
                ),
            )
            continue
        profile_name = _string(profile_value, f"workspace zone profile manifest.{zone_id}.profile")
        profile_path = (root / profile_name).resolve()
        if root not in profile_path.parents or not profile_path.is_file():
            raise ValueError(f"workspace zone profile is unavailable for {zone_id}: {profile_name}")
        try:
            raw_profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"workspace zone profile is invalid: {profile_path}") from exc
        profile = _mapping(raw_profile, f"workspace zone profile {zone_id}")
        if profile.get("schema_version") != WORKSPACE_ZONE_PROFILE_SCHEMA:
            raise ValueError(f"workspace zone profile schema is unsupported: {zone_id}")
        if profile.get("background_asset_id") != background_asset_id:
            raise ValueError(f"workspace zone profile background asset disagrees: {zone_id}")
        if profile.get("zone_id") != zone_id:
            raise ValueError(f"workspace zone profile zone id disagrees: {zone_id}")
        status = _string(profile.get("status"), f"workspace zone profile {zone_id}.status")
        if status not in {"profiled", "not_applicable"}:
            raise ValueError(f"workspace zone profile status is unsupported: {zone_id}")
        if status != manifest_status:
            raise ValueError(f"workspace zone profile status disagrees with manifest: {zone_id}")

        _validate_workspace_profile_source(
            profile,
            candidate,
            f"workspace zone profile {zone_id}",
            declaration_root=profile_path.parent,
            require_facade_provenance=True,
        )
        producer_revision, producer_git_commit = _workspace_profile_producer(
            profile,
            f"workspace zone profile {zone_id}",
        )
        if status == "not_applicable":
            profiles[f"{background_asset_id}__{zone_id}"] = WorkspaceZoneProfile(
                background_asset_id=background_asset_id,
                zone_id=zone_id,
                status=status,
                profile_path=profile_path,
                producer_revision=producer_revision,
                producer_git_commit=producer_git_commit,
                not_applicable_reason=_string(
                    profile.get("not_applicable_reason"),
                    f"workspace zone profile {zone_id}.not_applicable_reason",
                ),
            )
            continue

        coordinate_mapping = _mapping(
            profile.get("coordinate_mapping"),
            f"workspace zone profile {zone_id}.coordinate_mapping",
        )
        if coordinate_mapping.get("frame") != "source_composed":
            raise ValueError(
                "workspace zone profile coordinate_mapping.frame must be "
                f"source_composed: {zone_id}"
            )
        source_composed_meters_per_unit = _positive_finite_number(
            coordinate_mapping.get("source_composed_meters_per_unit"),
            (
                f"workspace zone profile {zone_id}.coordinate_mapping."
                "source_composed_meters_per_unit"
            ),
        )
        workspace = _mapping(
            profile.get("workspace"),
            f"workspace zone profile {zone_id}.workspace",
        )
        workspace_mode = workspace.get("mode", "replace_assembly")
        if workspace_mode not in {"replace_assembly", "open_floor"}:
            raise ValueError(
                f"workspace zone profile mode is unsupported: {zone_id}"
            )
        requires_replacement = workspace_mode == "replace_assembly"
        assembly = _mapping(profile.get("assembly"), f"workspace zone profile {zone_id}.assembly")
        required_roots = _prim_path_tuple(
            assembly.get("replaceable_assembly_roots"),
            f"workspace zone profile {zone_id}.assembly.replaceable_assembly_roots",
            require_nonempty=requires_replacement,
        )
        anchor_prim = _prim_path(
            assembly.get("anchor_prim"),
            f"workspace zone profile {zone_id}.assembly.anchor_prim",
        )
        anchor_key = "anchor_xyz_su" if "anchor_xyz_su" in assembly else "anchor_xyz_m"
        raw_anchor = _number_tuple(
            assembly.get(anchor_key),
            f"workspace zone profile {zone_id}.assembly.{anchor_key}",
        )
        inactivation = _mapping(
            profile.get("inactivation"),
            f"workspace zone profile {zone_id}.inactivation",
        )
        inactive_roots = _prim_path_tuple(
            inactivation.get("inactive_prim_root_paths"),
            f"workspace zone profile {zone_id}.inactivation.inactive_prim_root_paths",
            require_nonempty=requires_replacement,
        )
        if inactive_roots != required_roots:
            raise ValueError(
                f"workspace zone replacement roots disagree with inactivation: {zone_id}"
            )
        optional_paths = _prim_path_tuple(
            inactivation.get("optional_inactive_prim_paths", []),
            f"workspace zone profile {zone_id}.inactivation.optional_inactive_prim_paths",
        )
        clearance_key = (
            "clearance_aabb_su" if "clearance_aabb_su" in workspace else "clearance_aabb_m"
        )
        clearance = _mapping(
            workspace.get(clearance_key),
            f"workspace zone profile {zone_id}.workspace.{clearance_key}",
        )
        clearance_lower = _number_tuple(
            clearance.get("min"),
            f"workspace zone profile {zone_id}.workspace.{clearance_key}.min",
        )
        clearance_upper = _number_tuple(
            clearance.get("max"),
            f"workspace zone profile {zone_id}.workspace.{clearance_key}.max",
        )
        if any(clearance_upper[index] <= clearance_lower[index] for index in range(3)):
            raise ValueError(f"workspace zone profile clearance is empty: {zone_id}")
        uses_v02_yaw = "yaw" in profile
        yaw = _mapping(
            profile.get("yaw", profile.get("composition", {})),
            f"workspace zone profile {zone_id}.yaw",
        )
        yaw_key = "reviewed_yaw_deg" if uses_v02_yaw else "yaw_deg"
        composition_yaw_deg = _finite_number(
            yaw.get(yaw_key, 0.0),
            f"workspace zone profile {zone_id}.yaw.{yaw_key}",
        )
        if abs(composition_yaw_deg) > 360.0:
            raise ValueError(f"workspace zone profile yaw is out of range: {zone_id}")
        consumer_exclusion_reason: str | None = None
        if uses_v02_yaw and abs(composition_yaw_deg) > 1e-9:
            convention = yaw.get("rotation_convention")
            if convention != USD_Z_UP_RIGHT_HANDED_CCW:
                consumer_exclusion_reason = (
                    "non-zero reviewed yaw lacks explicit USD +Z right-handed convention"
                    if convention is None
                    else "non-zero reviewed yaw has unsupported rotation convention"
                )

        evidence_camera_position_xyz_su: tuple[float, float, float] | None = None
        evidence_camera_target_xyz_su: tuple[float, float, float] | None = None
        raw_evidence_camera = profile.get("evidence_camera")
        if raw_evidence_camera is not None:
            evidence_camera = _mapping(
                raw_evidence_camera,
                f"workspace zone profile {zone_id}.evidence_camera",
            )
            if evidence_camera.get("frame_convention") != USD_Z_UP_RIGHT_HANDED_CCW:
                raise ValueError(
                    "workspace zone profile evidence camera has unsupported "
                    f"frame convention: {zone_id}"
                )
            evidence_camera_position_xyz_su = _number_tuple(
                evidence_camera.get("position_xyz"),
                f"workspace zone profile {zone_id}.evidence_camera.position_xyz",
            )
            evidence_camera_target_xyz_su = _number_tuple(
                evidence_camera.get("target_xyz"),
                f"workspace zone profile {zone_id}.evidence_camera.target_xyz",
            )

        lower, upper = _raw_source_composed_bounds(candidate)
        if any(
            raw_anchor[index] < lower[index] or raw_anchor[index] > upper[index]
            for index in range(3)
        ):
            raise ValueError(
                f"workspace zone profile anchor is outside source-composed bounds: {zone_id}"
            )
        package_anchor = tuple(
            value * source_composed_meters_per_unit for value in raw_anchor
        )
        anchor = WorkspaceAnchor(
            source_prim_path=anchor_prim,
            source_anchor_xyz_m=package_anchor,
            source_composed_meters_per_unit=source_composed_meters_per_unit,
            preserve_workspace_metric=True,
            hide_prim_paths=inactive_roots,
            note=(f"ConvertAsset source-bound workspace zone profile {profile_path.name}"),
            camera_mode="workspace_focus",
        )
        zone_profile = WorkspaceZoneProfile(
            background_asset_id=background_asset_id,
            zone_id=zone_id,
            status=status,
            profile_path=profile_path,
            producer_revision=producer_revision,
            producer_git_commit=producer_git_commit,
            anchor=anchor,
            raw_anchor_xyz_su=raw_anchor,
            source_composed_meters_per_unit=source_composed_meters_per_unit,
            raw_clearance_aabb_su=(clearance_lower, clearance_upper),
            composition_yaw_deg=composition_yaw_deg,
            evidence_camera_position_xyz_su=evidence_camera_position_xyz_su,
            evidence_camera_target_xyz_su=evidence_camera_target_xyz_su,
            optional_inactive_prim_paths=optional_paths,
            consumer_exclusion_reason=consumer_exclusion_reason,
        )
        profiles[zone_profile.variant_id] = zone_profile
    return profiles


def select_workspace_zone_variants(
    candidates: Sequence[BackgroundCandidate],
    zones: Mapping[str, WorkspaceZoneProfile],
    *,
    background_asset_id: str | None = None,
    variant_id: str | None = None,
) -> tuple[tuple[BackgroundZoneVariant, ...], dict[str, str]]:
    """Choose profiled zones without discarding other zones in the same room."""

    admitted_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if background_asset_id is not None and background_asset_id not in admitted_by_id:
        raise ValueError(f"background asset id is not present in admission: {background_asset_id}")
    if variant_id is not None and variant_id not in zones:
        raise ValueError(f"variant id is not present in workspace zone profiles: {variant_id}")
    if variant_id is not None and background_asset_id is not None:
        selected_zone = zones[variant_id]
        if selected_zone.background_asset_id != background_asset_id:
            raise ValueError(
                f"variant {variant_id} does not belong to background asset "
                f"{background_asset_id}"
            )
    if background_asset_id is not None and not any(
        zone.background_asset_id == background_asset_id for zone in zones.values()
    ):
        raise ValueError(
            "background asset id is not present in workspace zone profiles: "
            f"{background_asset_id}"
        )

    selected: list[BackgroundZoneVariant] = []
    excluded: dict[str, str] = {}
    for current_variant_id, zone in zones.items():
        if background_asset_id is not None and zone.background_asset_id != background_asset_id:
            continue
        if variant_id is not None and current_variant_id != variant_id:
            continue
        candidate = admitted_by_id.get(zone.background_asset_id)
        if candidate is None:
            raise ValueError(
                "workspace zone profile background asset is not present in admission: "
                f"{zone.background_asset_id}"
            )
        if zone.consumer_exclusion_reason is not None:
            excluded[current_variant_id] = zone.consumer_exclusion_reason
            continue
        if zone.status == "not_applicable":
            excluded[current_variant_id] = (
                zone.not_applicable_reason or "workspace integration is not applicable"
            )
            continue
        if zone.anchor is None:
            excluded[current_variant_id] = "workspace zone profile does not provide an anchor"
            continue
        selected.append(BackgroundZoneVariant(candidate=candidate, zone=zone))
    if variant_id is not None and variant_id in excluded:
        raise ValueError(
            f"variant {variant_id} is not an integrated workspace variant: "
            f"{excluded[variant_id]}"
        )
    if background_asset_id is not None and not selected:
        reasons = [
            f"{current_variant_id}: {reason}"
            for current_variant_id, reason in excluded.items()
            if current_variant_id.startswith(background_asset_id + "__")
        ]
        detail = "; ".join(sorted(reasons)) or "no profiled zone was returned"
        raise ValueError(
            f"background asset {background_asset_id} has no eligible workspace zones: {detail}"
        )
    return tuple(selected), excluded


def _validate_workspace_profile_source(
    profile: Mapping[str, Any],
    candidate: BackgroundCandidate,
    field: str,
    *,
    declaration_root: Path | None = None,
    require_facade_provenance: bool = False,
) -> None:
    source = _mapping(profile.get("source"), f"{field}.source")
    root = Path.cwd() if declaration_root is None else declaration_root
    if "source_usd_sha256" in source:
        source_hash = _digest_without_prefix(
            _string(
                source.get("source_usd_sha256"),
                f"{field}.source.source_usd_sha256",
            )
        )
        if source_hash != candidate.source_sha256:
            raise ValueError(f"{field} source hash disagrees")
        if source.get("consumer_facade_scope") != candidate.source_scope:
            raise ValueError(f"{field} consumer facade scope disagrees")
        manifest_path = _resolve_declared_path(
            _string(source.get("package_manifest"), f"{field}.source.package_manifest"),
            root,
        )
        if manifest_path != candidate.manifest_path.resolve():
            raise ValueError(f"{field} package manifest disagrees")
        facade_value = source.get("facade_provenance")
        if require_facade_provenance and facade_value is None:
            raise ValueError(f"{field} facade provenance is required")
        if facade_value is not None:
            facade_path = _resolve_declared_path(
                _string(facade_value, f"{field}.source.facade_provenance"),
                root,
            )
            if candidate.facade_provenance_path is None:
                raise ValueError(f"{field} facade provenance is not admitted")
            if facade_path != candidate.facade_provenance_path.resolve():
                raise ValueError(f"{field} facade provenance disagrees")
        return

    source_usd = _resolve_declared_path(
        _string(source.get("source_usd"), f"{field}.source.source_usd"),
        root,
    )
    if source_usd != candidate.source_usd.resolve():
        raise ValueError(f"{field} source USD disagrees")
    source_hash = _digest_without_prefix(
        _string(source.get("source_sha256"), f"{field}.source.source_sha256")
    )
    if source_hash != candidate.source_sha256:
        raise ValueError(f"{field} source hash disagrees")
    if source.get("scope") != candidate.source_scope:
        raise ValueError(f"{field} source scope disagrees")


def _workspace_profile_producer(
    profile: Mapping[str, Any],
    field: str,
) -> tuple[str, str]:
    producer = _mapping(profile.get("producer"), f"{field}.producer")
    return (
        _string(producer.get("revision"), f"{field}.producer.revision"),
        _string(producer.get("git_commit"), f"{field}.producer.git_commit"),
    )


def _workspace_zone_integration_record(zone: WorkspaceZoneProfile) -> dict[str, Any]:
    record: dict[str, Any] = {
        "status": zone.status,
        "zone_id": zone.zone_id,
        "variant_id": zone.variant_id,
        "profile_path": str(zone.profile_path),
        "producer_revision": zone.producer_revision,
        "producer_git_commit": zone.producer_git_commit,
        "composition_yaw_deg": zone.composition_yaw_deg,
    }
    if zone.anchor is None:
        record["not_applicable_reason"] = zone.not_applicable_reason
        return record
    record.update(
        {
            "profile_anchor_source_composed_su": list(zone.raw_anchor_xyz_su or ()),
            "source_composed_meters_per_unit": zone.source_composed_meters_per_unit,
            "profile_anchor_placement_m": list(zone.anchor.source_anchor_xyz_m),
            "workspace_metric_preserved": zone.anchor.preserve_workspace_metric,
            "inactive_prim_root_paths": list(zone.anchor.hide_prim_paths),
            "optional_inactive_prim_paths": list(zone.optional_inactive_prim_paths),
            "applied_inactive_prim_paths": list(
                reviewed_workspace_inactive_prim_paths(zone.anchor, zone)
            ),
            "source_composed_clearance_aabb_su": {
                "min": list(zone.raw_clearance_aabb_su[0]),
                "max": list(zone.raw_clearance_aabb_su[1]),
            }
            if zone.raw_clearance_aabb_su is not None
            else None,
            "evidence_camera_source_composed_su": (
                {
                    "position_xyz": list(zone.evidence_camera_position_xyz_su),
                    "target_xyz": list(zone.evidence_camera_target_xyz_su),
                    "frame_convention": USD_Z_UP_RIGHT_HANDED_CCW,
                }
                if zone.evidence_camera_position_xyz_su is not None
                and zone.evidence_camera_target_xyz_su is not None
                else None
            ),
        }
    )
    return record


def reviewed_workspace_inactive_prim_paths(
    anchor: WorkspaceAnchor | None,
    workspace_zone: WorkspaceZoneProfile | None = None,
) -> tuple[str, ...]:
    """Return the complete producer-reviewed visual clearance override.

    A zone's required assembly roots replace the original work surface.  Its
    optional roots are not inferred geometry: ConvertAsset lists each full
    actor after the clearance audit.  Applying that finite list keeps the
    fixed eBench table from visually intersecting source tabletop props while
    leaving every unlisted room asset intact.
    """

    if anchor is None:
        return ()
    reviewed = list(anchor.hide_prim_paths)
    if workspace_zone is not None:
        reviewed.extend(workspace_zone.optional_inactive_prim_paths)
    return tuple(dict.fromkeys(reviewed))


def _is_zone_id(value: str) -> bool:
    return ZONE_ID.fullmatch(value) is not None and "__" not in value


def _is_variant_id(value: str) -> bool:
    if "__" not in value:
        return is_background_asset_id(value)
    background_asset_id, separator, zone_id = value.partition("__")
    return separator == "__" and is_background_asset_id(background_asset_id) and _is_zone_id(
        zone_id
    )


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
    composition_yaw_deg: float | None = None,
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
    composition_yaw_deg = (
        workspace_composition_yaw_deg(candidate)
        if composition_yaw_deg is None
        else _finite_number(composition_yaw_deg, "composition_yaw_deg")
    )
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
        _yaw_quaternion(composition_yaw_deg + candidate.root_yaw_deg),
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
        "source_root_yaw_deg": candidate.root_yaw_deg,
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
    workspace_zone: WorkspaceZoneProfile | None = None,
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
        if workspace_zone is not None:
            # ConvertAsset's optional evidence_camera is source-room
            # provenance.  It does not contain the final Lift2 geometry, and
            # a source-valid ray can be hidden by the real eBench tower.
            # Reuse the first camera after GenManip has recovered the real
            # task workspace, then restore the room only for the overview.
            # The producer pose remains recorded in the package integration
            # data; it is not treated as an equivalent runtime camera.
            overview["anchor_runtime_ids"] = [
                "lift2_end_effectors",
                "obj_conical_bottle03",
                "obj_graduated_cylinder_03",
            ]
            overview["camera_reference_view"] = "workspace_closeup"
            overview["camera_distance_multiplier"] = 1.15
            overview.pop("target_xyz", None)
            overview.pop("position_xyz", None)
            overview.pop("runtime_target_direction_xyz", None)
            overview.pop("runtime_target_distance_m", None)
            overview["camera_source"] = (
                "GenManip post-reset workspace camera with room context"
            )
            request["camera_policy_version"] = (
                "scenario-forge/runtime-workspace-camera-reference-v10"
            )
            request_path.write_text(
                yaml.safe_dump(dict(request), sort_keys=False),
                encoding="utf-8",
            )
            return
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
        # Do not centre this camera on the union of the robot base and the
        # table. That union sits below the tabletop and causes the opaque
        # work surface to mask the robot and vessels. The end-effectors plus
        # vessels give a post-reset target at the actual operating height;
        # ``required_runtime_ids`` still proves that Lift2 and the table exist.
        overview["anchor_runtime_ids"] = [
            "lift2_end_effectors",
            "obj_conical_bottle03",
            "obj_graduated_cylinder_03",
        ]
        overview["azimuth_deg"] = -35.0
        overview["elevation_deg"] = 30.0
        overview["framing_margin"] = 1.35
        overview["minimum_distance"] = 2.4
        overview.pop("target_xyz", None)
        overview.pop("position_xyz", None)
        overview["camera_source"] = "GenManip post-reset runtime workspace bounds"
        # The fixed eBench robot and table do not rotate with a visual-room
        # zone. Keep the validated task-facing direction in the fixed
        # workcell frame; only the room instance carries the reviewed yaw.
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


def _source_composed_point_to_scene(
    candidate: BackgroundCandidate,
    placement: Mapping[str, Any],
    source_point_su: tuple[float, float, float],
    metres_per_unit: float,
) -> tuple[float, float, float]:
    """Apply the generated room-instance transform to one source point."""

    source_point_m = tuple(value * metres_per_unit for value in source_point_su)
    fit_factor = _finite_number(placement.get("fit_factor"), "placement.fit_factor")
    effective_scale = _finite_number(
        placement.get("effective_scale"), "placement.effective_scale"
    )
    yaw_deg = _finite_number(
        placement.get("composition_yaw_deg", 0.0),
        "placement.composition_yaw_deg",
    )
    scene_pose = _mapping(placement.get("scene_pose"), "placement.scene_pose")
    scene_xyz = _number_tuple(scene_pose.get("xyz"), "placement.scene_pose.xyz")
    local_position = tuple(
        fit_factor * source_point_m[index]
        - effective_scale * candidate.root_translate_xyz[index]
        for index in range(3)
    )
    rotated_position = _rotate_z(local_position, yaw_deg)
    return tuple(scene_xyz[index] + rotated_position[index] for index in range(3))


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
    """Load prior legacy or zone-addressed records for an incremental rebuild."""

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
        if not isinstance(candidate_id, str) or not is_background_asset_id(candidate_id):
            raise ValueError(f"existing variant {index} has an invalid candidate_id: {path}")
        variant_id = raw_variant.get("variant_id", candidate_id)
        if not isinstance(variant_id, str) or not _is_variant_id(variant_id):
            raise ValueError(f"existing variant {index} has an invalid variant_id: {path}")
        if variant_id.startswith(candidate_id + "__") or variant_id == candidate_id:
            variants[variant_id] = dict(raw_variant)
        else:
            raise ValueError(f"existing variant {index} does not belong to candidate_id: {path}")
    return variants


def _resolve_declared_path(value: str, declaration_root: Path) -> Path:
    """Resolve an operational handoff path relative to its declaration."""

    path = Path(value)
    return (path if path.is_absolute() else declaration_root / path).resolve()


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_background_source(candidate: BackgroundCandidate) -> LocalUSDAssetSource:
    package_source_usd = candidate.package_source_usd or candidate.source_usd
    handoff = load_convert_asset_package_handoff(
        candidate.package_dir,
        candidate.manifest_path,
        package_source_usd,
        expected_scope_prims=(candidate.source_scope,),
        producer_revision=candidate.producer_revision,
        usage="visual_static_environment",
    )
    return handoff.to_local_usd_asset_source(
        asset_id=candidate.candidate_id,
        license=candidate.license,
        attribution=candidate.attribution,
        redistributable=candidate.redistributable,
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


def _validate_facade_provenance(
    provenance_path: Path,
    *,
    candidate_id: str,
    raw_source_usd: Path,
    raw_source_sha256: str,
    source_scope: str,
) -> None:
    """Bind a producer-owned facade back to the immutable raw room source."""

    if not provenance_path.is_file():
        raise ValueError(f"background facade provenance is missing: {candidate_id}")
    try:
        raw = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"background facade provenance is invalid: {candidate_id}"
        ) from exc
    provenance = _mapping(raw, f"{candidate_id}.facade_provenance")
    facade_default_prim = provenance.get("facade_default_prim")
    if facade_default_prim != "World":
        raise ValueError(f"facade provenance default prim disagrees: {candidate_id}")
    if provenance.get("facade_scope") != source_scope:
        raise ValueError(f"facade provenance scope disagrees: {candidate_id}")
    raw_hash = _digest_without_prefix(
        _string(
            provenance.get("raw_source_usd_sha256"),
            f"{candidate_id}.facade_provenance.raw_source_usd_sha256",
        )
    )
    if raw_hash != raw_source_sha256:
        raise ValueError(f"facade provenance raw source hash disagrees: {candidate_id}")
    source_name = provenance.get("raw_source_usd_relative_path")
    if source_name is not None and Path(_string(source_name, "raw_source_usd_relative_path")).name != raw_source_usd.name:
        raise ValueError(f"facade provenance raw source path disagrees: {candidate_id}")


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
    package_source_sha256: str,
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
    if manifest.get("asset_id") != candidate_id:
        raise ValueError(f"background package asset id disagrees with admission: {candidate_id}")
    if manifest.get("asset_role") != "visual_static_environment":
        raise ValueError(f"background package is not visual-static: {candidate_id}")
    source = _mapping(manifest.get("source"), f"{candidate_id}.manifest.source")
    if source.get("sha256") != package_source_sha256:
        raise ValueError(f"background package source hash disagrees with admission: {candidate_id}")
    entrypoints = _mapping(manifest.get("entrypoints"), f"{candidate_id}.manifest.entrypoints")
    if entrypoints.get("root_usd") != "asset.usd":
        raise ValueError(f"background package root must be asset.usd: {candidate_id}")
    if entrypoints.get("default_prim") != "World":
        raise ValueError(
            f"background package must expose default prim World for eBench: {candidate_id}"
        )
    if entrypoints.get("asset_entry_prim") != source_scope:
        raise ValueError(f"background package scope disagrees with admission: {candidate_id}")
    if entrypoints.get("asset_scope_prims") != [source_scope]:
        raise ValueError(
            f"background package scope list disagrees with admission: {candidate_id}"
        )
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
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    float,
]:
    """Read the consumer-package root transform recorded by ConvertAsset.

    The eBench scene layer authors a transform on the destination ``room`` prim.
    USD composition then overrides the referenced ``/World`` root transform, so
    this transform must be folded into the destination instance pose.  The
    package-side transform must be folded into the destination instance pose.
    A raw source may use unrelated namespaces (for example `/world` plus
    `/Root`), so it is not a valid substitute for the admitted consumer facade.
    A Blender USD may encode its basis conversion as a proper +Z yaw on the
    root (commonly 180 degrees).  Preserve that rotation explicitly; reject
    reflections, tilt, or shear.
    """

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"background package manifest is invalid: {manifest_path}") from exc
    fingerprint = _mapping(
        manifest.get("visual_preservation_fingerprint"),
        f"{candidate_id}.visual_preservation_fingerprint",
    )
    package_after_role = _mapping(
        fingerprint.get("package_after_role"),
        f"{candidate_id}.visual_preservation_fingerprint.package_after_role",
    )
    transforms = _mapping(
        package_after_role.get("scope_world_transforms"),
        f"{candidate_id}.scope_world_transforms",
    )
    matrix = transforms.get(EBENCH_BACKGROUND_CONSUMER_SCOPE)
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
        raise ValueError(
            f"{candidate_id}.package facade scope_world_transforms./World is invalid"
        )
    values = tuple(tuple(float(value) for value in row) for row in matrix)
    if not all(math.isfinite(value) for row in values for value in row):
        raise ValueError(
            f"{candidate_id}.package facade scope_world_transforms./World is non-finite"
        )
    if any(abs(values[row][2]) > 1e-8 for row in range(2)) or any(
        abs(values[2][column]) > 1e-8 for column in range(2)
    ):
        raise ValueError(
            f"{candidate_id}.source root transform has tilt/shear; "
            "instance placement supports only a +Z yaw"
        )
    scale_x = math.hypot(values[0][0], values[0][1])
    scale_y = math.hypot(values[1][0], values[1][1])
    scale_z = values[2][2]
    if min(scale_x, scale_y, scale_z) <= 0.0:
        raise ValueError(f"{candidate_id}.source root transform must have positive scale")
    row_dot = values[0][0] * values[1][0] + values[0][1] * values[1][1]
    if not math.isclose(row_dot, 0.0, rel_tol=1e-6, abs_tol=1e-8):
        raise ValueError(
            f"{candidate_id}.source root transform has shear; "
            "instance placement requires an explicit transform adapter"
        )
    determinant_xy = (
        values[0][0] * values[1][1] - values[0][1] * values[1][0]
    )
    if determinant_xy <= 0.0 or not math.isclose(
        determinant_xy,
        scale_x * scale_y,
        rel_tol=1e-6,
        abs_tol=1e-8,
    ):
        raise ValueError(
            f"{candidate_id}.source root transform contains a reflection"
        )
    yaw_deg = math.degrees(math.atan2(values[0][1], values[0][0]))
    if not math.isclose(values[3][3], 1.0, rel_tol=1e-6, abs_tol=1e-8):
        raise ValueError(f"{candidate_id}.source root transform has invalid homogeneous row")
    if any(abs(values[3][index]) > 1e12 for index in range(3)):
        raise ValueError(f"{candidate_id}.source root transform translation is out of range")
    for index in range(3):
        if abs(values[index][3]) > 1e-8:
            raise ValueError(f"{candidate_id}.source root transform has perspective terms")
    return (
        (scale_x, scale_y, scale_z),
        tuple(values[3][index] for index in range(3)),
        yaw_deg,
    )


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


def _sha256_hex(value: str, field: str) -> str:
    digest = _digest_without_prefix(value)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def _positive_finite_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be a positive finite number")
    return result


def _finite_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
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

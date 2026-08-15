from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from scenario_forge.assets.source import LocalUSDAssetSource, UpstreamPackageRef


@dataclass(frozen=True)
class ConvertAssetCommandPlan:
    """A dry command plan for invoking ConvertAsset from an outer workflow."""

    convert_asset_root: str
    input_usd: str
    output_usd: str
    operations: tuple[str, ...]

    def commands(self) -> tuple[tuple[str, ...], ...]:
        root = Path(self.convert_asset_root)
        wrapper = str(root / "scripts" / "isaac_python.sh")
        main = str(root / "main.py")

        commands: list[tuple[str, ...]] = []
        current_input = self.input_usd
        for operation in self.operations:
            if operation == "no-mdl":
                commands.append((wrapper, main, "no-mdl", current_input))
                current_input = self.output_usd
            elif operation == "mesh-faces":
                commands.append((wrapper, main, "mesh-faces", current_input))
            else:
                raise ValueError(f"Unsupported ConvertAsset operation: {operation}")
        return tuple(commands)


@dataclass(frozen=True)
class NormalizeAssetCommandPlan:
    """A dry command plan for ConvertAsset's package-level normalization CLI."""

    convert_asset_root: str
    source_usd: str
    package_dir: str

    def command(self) -> tuple[str, ...]:
        root = Path(self.convert_asset_root)
        return (
            str(root / "scripts" / "isaac_python.sh"),
            str(root / "main.py"),
            "normalize-asset",
            self.source_usd,
            "--out",
            self.package_dir,
        )


class ConvertAssetHandoffError(ValueError):
    """Raised when a ConvertAsset package does not satisfy its handoff contract."""


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_USAGE_ROLES = {
    "scene_overlay": "scene_overlay",
    "rigid_object": "rigid_object",
    "articulated_object": "articulated_object",
    "visual_static_environment": "environment",
    "visual_static_object": "static_object",
    "static_support_object": "static_support_object",
    "dynamic_context_object": "dynamic_context_object",
}
_DYNAMIC_USAGES = frozenset(
    {"scene_overlay", "rigid_object", "articulated_object", "dynamic_context_object"}
)
_TASK_INTERACTIVE_USAGES = frozenset({"rigid_object", "articulated_object"})
_TASK_INTERACTIVE_IDENTITY_TOLERANCE = 1e-6
_VISUAL_STATIC_USAGES = frozenset(
    {"visual_static_environment", "visual_static_object"}
)
_STATIC_SUPPORT_USAGES = frozenset({"static_support_object"})
_VISUAL_STATIC_PRODUCER_ROLES = {
    "visual_static_environment": frozenset(
        {"visual_static", "visual_static_environment"}
    ),
    "visual_static_object": frozenset({"visual_static", "visual_static_object"}),
}
_ARTICULATION_PROMOTION_PATH = (
    "evidence/articulation_runtime_qualification/promotion.json"
)
@dataclass(frozen=True)
class ConvertAssetInteractionContract:
    schema_version: str
    asset_entry_prim: str
    rigid_root_prim: str
    active_rigid_body_prims: tuple[str, ...]
    collider_prims: tuple[str, ...]
    named_frames: Mapping[str, Mapping[str, Any]]
    interaction_regions: Mapping[str, Mapping[str, Any]]
    contract_payload_sha256: str
    runtime_tree_sha256: str
    qualification_report_paths: tuple[str, ...]
    task_ready: bool
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "interaction_contract")


@dataclass(frozen=True)
class ConvertAssetStaticSupportContract:
    schema_version: str
    asset_entry_prim: str
    collider_prims: tuple[str, ...]
    profile_id: str
    profile_revision: str
    profile_sha256: str
    qualification_report_path: str
    qualification_report_sha256: str
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "static_support_contract")


@dataclass(frozen=True)
class ConvertAssetDynamicContextContract:
    schema_version: str
    asset_entry_prim: str
    rigid_root_prim: str
    collider_prims: tuple[str, ...]
    support_frame: Mapping[str, Any]
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "dynamic_context_contract")


@dataclass(frozen=True)
class ConvertAssetArticulationContract:
    schema_version: str
    asset_entry_prim: str
    articulation_root_prim: str
    dof_mapping: tuple[Mapping[str, Any], ...]
    reset_values: tuple[Mapping[str, Any], ...]
    semantic_joints: Mapping[str, Mapping[str, Any]]
    named_frames: Mapping[str, Mapping[str, Any]]
    mounting: Mapping[str, Any] | None
    profile_sha256: str
    required_artifact_paths: tuple[str, ...]
    payload: Mapping[str, Any]
    closure_payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "articulation_contract")

    def closure_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(
            self.closure_payload,
            "articulation_closure",
        )


@dataclass(frozen=True)
class ConvertAssetTaskQualification:
    qualification_id: str
    status: str
    report_path: str
    report_sha256: str
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "task_qualification")


@dataclass(frozen=True)
class ConvertAssetSupportAudit:
    """Portable certificate for a generated room's reviewed support graph."""

    schema_version: str
    source_sha256: str
    relation_count: int
    removed_decoration_count: int
    report_sha256: str
    support_closure: Mapping[str, tuple[str, ...]]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": "pass",
            "source_sha256": f"sha256:{self.source_sha256}",
            "relation_count": self.relation_count,
            "removed_decoration_count": self.removed_decoration_count,
            "report_sha256": f"sha256:{self.report_sha256}",
            "support_closure": {
                key: list(values)
                for key, values in sorted(self.support_closure.items())
            },
        }


@dataclass(frozen=True)
class ConvertAssetTaskInteractiveGeometry:
    asset_entry_prim: str
    entry_world_transform: tuple[tuple[float, float, float, float], ...]
    package_world_bound_min_m: tuple[float, float, float]
    package_world_bound_max_m: tuple[float, float, float]
    support_frame_local_matrix: tuple[
        tuple[float, float, float, float], ...
    ]
    support_frame_source_sha256: str
    mounting: Mapping[str, Any] | None = None

    def to_mapping(self) -> dict[str, Any]:
        extent = [
            upper - lower
            for lower, upper in zip(
                self.package_world_bound_min_m,
                self.package_world_bound_max_m,
                strict=True,
            )
        ]
        payload = {
            "schema_version": (
                "scenario-forge-task-interactive-geometry/v0.2"
                if self.mounting is not None
                else "scenario-forge-task-interactive-geometry/v0.1"
            ),
            "asset_entry_prim": self.asset_entry_prim,
            "entry_world_transform": [
                list(row) for row in self.entry_world_transform
            ],
            "package_world_bound_m": {
                "min": list(self.package_world_bound_min_m),
                "max": list(self.package_world_bound_max_m),
            },
            "extent_m": extent,
            "identity_tolerance": _TASK_INTERACTIVE_IDENTITY_TOLERANCE,
            "support_frame": "support",
            "support_frame_local_matrix": [
                list(row) for row in self.support_frame_local_matrix
            ],
            "support_frame_source_sha256": self.support_frame_source_sha256,
        }
        if self.mounting is not None:
            payload["mounting"] = _copy_json_mapping(
                self.mounting,
                "task_interactive_geometry.mounting",
            )
        return payload


@dataclass(frozen=True)
class ConvertAssetPackageHandoff:
    package_dir: Path
    package_id: str
    producer_asset_id: str
    producer_asset_role: str
    producer_revision: str
    manifest_schema_version: str
    manifest_sha256: str
    source_sha256: str
    root_usd: Path
    root_usd_sha256: str
    root_prim_path: str
    scope_prims: tuple[str, ...]
    runtime_profile: str
    consumer_profile: str
    quality_tier: str | None
    profile_id: str | None
    profile_revision: str | None
    profile_sha256: str | None
    claim_boundary: str | None
    replacement_contract: str | None
    claims_forbidden: tuple[str, ...]
    scoped_physics_warning_count: int
    usage: str
    interaction_contract: ConvertAssetInteractionContract | None = None
    articulation_contract: ConvertAssetArticulationContract | None = None
    task_interactive_geometry: ConvertAssetTaskInteractiveGeometry | None = None
    task_qualifications: tuple[ConvertAssetTaskQualification, ...] = ()
    support_audit: ConvertAssetSupportAudit | None = None
    static_support_contract: ConvertAssetStaticSupportContract | None = None
    dynamic_context_contract: ConvertAssetDynamicContextContract | None = None

    def to_local_usd_asset_source(
        self,
        *,
        asset_id: str,
        license: str,
        attribution: tuple[str, ...] = (),
        redistributable: bool = False,
        exclude_relative_paths: tuple[str, ...] = (),
    ) -> LocalUSDAssetSource:
        required_artifact_paths: tuple[str, ...] = tuple(
            qualification.report_path
            for qualification in self.task_qualifications
        )
        if self.usage == "rigid_object" and self.interaction_contract is not None:
            required_artifact_paths += (
                self.interaction_contract.qualification_report_paths
            )
        elif (
            self.usage == "articulated_object"
            and self.articulation_contract is not None
        ):
            required_artifact_paths += (
                self.articulation_contract.required_artifact_paths
            )
        if required_artifact_paths:
            for excluded_path in exclude_relative_paths:
                normalized = PurePosixPath(excluded_path).as_posix()
                if any(
                    artifact_path == normalized
                    or artifact_path.startswith(normalized + "/")
                    for artifact_path in required_artifact_paths
                ):
                    if self.usage == "rigid_object":
                        raise ValueError(
                            "rigid_object source cannot exclude its "
                            "qualification report"
                        )
                    raise ValueError(
                        f"{self.usage} source cannot exclude a required "
                        "qualification/profile artifact"
                    )
        upstream_metadata: dict[str, Any] = {
            "producer_asset_id": self.producer_asset_id,
            "producer_asset_role": self.producer_asset_role,
            "source_sha256": f"sha256:{self.source_sha256}",
            "root_usd_sha256": f"sha256:{self.root_usd_sha256}",
            "scope_prims": list(self.scope_prims),
            "runtime_profile": self.runtime_profile,
            "consumer_profile": self.consumer_profile,
            "consumer_usage": self.usage,
            "claims_forbidden": list(self.claims_forbidden),
            "scoped_physics_warning_count": self.scoped_physics_warning_count,
        }
        if self.quality_tier is not None:
            upstream_metadata.update(
                {
                    "quality_tier": self.quality_tier,
                    "profile_id": self.profile_id,
                    "profile_revision": self.profile_revision,
                    "profile_sha256": f"sha256:{self.profile_sha256}",
                    "claim_boundary": self.claim_boundary,
                    "replacement_contract": self.replacement_contract,
                }
            )
        if self.interaction_contract is not None:
            upstream_metadata["interaction_contract"] = (
                self.interaction_contract.to_mapping()
            )
        if self.articulation_contract is not None:
            upstream_metadata["articulation_contract"] = (
                self.articulation_contract.to_mapping()
            )
            upstream_metadata["articulation_closure"] = (
                self.articulation_contract.closure_mapping()
            )
            upstream_metadata["articulation_profile_sha256"] = (
                f"sha256:{self.articulation_contract.profile_sha256}"
            )
        if self.support_audit is not None:
            upstream_metadata["support_audit"] = self.support_audit.to_mapping()
        if self.static_support_contract is not None:
            upstream_metadata["static_support_contract"] = (
                self.static_support_contract.to_mapping()
            )
        if self.dynamic_context_contract is not None:
            upstream_metadata["dynamic_context_contract"] = (
                self.dynamic_context_contract.to_mapping()
            )
        if self.task_interactive_geometry is not None:
            upstream_metadata["task_interactive_geometry"] = (
                self.task_interactive_geometry.to_mapping()
            )
        if self.task_qualifications:
            upstream_metadata["task_qualifications"] = [
                qualification.to_mapping()
                for qualification in self.task_qualifications
            ]
        upstream = UpstreamPackageRef(
            producer="ConvertAsset",
            schema_version=self.manifest_schema_version,
            package_id=self.package_id,
            revision=self.producer_revision,
            manifest_uri=(
                f"convert-asset://{self.package_id}/manifest/"
                f"sha256:{self.manifest_sha256}"
            ),
            manifest_sha256=f"sha256:{self.manifest_sha256}",
            metadata=upstream_metadata,
        )
        return LocalUSDAssetSource(
            asset_id=asset_id,
            source_usd=self.root_usd,
            role=_USAGE_ROLES[self.usage],
            license=license,
            source_uri=(
                f"convert-asset://{self.package_id}/asset/"
                f"sha256:{self.root_usd_sha256}"
            ),
            attribution=attribution,
            redistributable=redistributable,
            exclude_relative_paths=exclude_relative_paths,
            root_prim_path=self.root_prim_path,
            expected_sha256=f"sha256:{self.root_usd_sha256}",
            upstream_package=upstream,
        )


@dataclass(frozen=True)
class ConvertAssetGPUPBDStaticContainerHandoff:
    """Qualified source-bound GPU-PBD container and its bound initial state."""

    package_dir: Path
    package_id: str
    manifest_sha256: str
    root_usd: Path
    root_usd_sha256: str
    entry_prim: str
    profile_path: Path
    profile_sha256: str
    qualification_report_path: str
    qualification_report_sha256: str
    fixture_path: str
    fixture_sha256: str
    initial_particle_state_path: str
    initial_particle_state_sha256: str
    particle_count: int
    collision_strategy: str
    claim_boundary: str

    def to_local_usd_asset_source(
        self,
        *,
        asset_id: str,
        license: str,
        attribution: tuple[str, ...] = (),
        redistributable: bool = False,
    ) -> LocalUSDAssetSource:
        upstream = UpstreamPackageRef(
            producer="ConvertAsset",
            schema_version="aan.source_bound_package_manifest.v1",
            package_id=self.package_id,
            revision=f"sha256:{self.profile_sha256}",
            manifest_uri=(
                f"convert-asset://{self.package_id}/manifest/"
                f"sha256:{self.manifest_sha256}"
            ),
            manifest_sha256=f"sha256:{self.manifest_sha256}",
            metadata={
                "consumer_usage": "gpu_pbd_static_container",
                "consumer_physics_patch_allowed": False,
                "runtime_profile": "isaac41",
                "particle_count": self.particle_count,
                "collision_strategy": self.collision_strategy,
                "profile_path": self.profile_path.name,
                "profile_sha256": f"sha256:{self.profile_sha256}",
                "qualification_report_path": self.qualification_report_path,
                "qualification_report_sha256": (
                    f"sha256:{self.qualification_report_sha256}"
                ),
                "fixture_path": self.fixture_path,
                "fixture_sha256": f"sha256:{self.fixture_sha256}",
                "initial_particle_state_path": self.initial_particle_state_path,
                "initial_particle_state_sha256": (
                    f"sha256:{self.initial_particle_state_sha256}"
                ),
                "claim_boundary": self.claim_boundary,
            },
        )
        return LocalUSDAssetSource(
            asset_id=asset_id,
            source_usd=self.root_usd,
            role="rigid_object",
            license=license,
            source_uri=(
                f"convert-asset://{self.package_id}/asset/"
                f"sha256:{self.root_usd_sha256}"
            ),
            attribution=attribution,
            redistributable=redistributable,
            root_prim_path=self.entry_prim,
            expected_sha256=f"sha256:{self.root_usd_sha256}",
            upstream_package=upstream,
        )


@dataclass(frozen=True)
class ConvertAssetGPUPBDTransferPairHandoff:
    """Qualified package-local prescribed GPU-PBD transfer pair."""

    package_dir: Path
    package_id: str
    manifest_sha256: str
    component_usd: Path
    component_sha256: str
    entry_prim: str
    profile_path: Path
    profile_sha256: str
    qualification_report_path: str
    qualification_report_sha256: str
    dependency_tree_sha256: str
    particle_count: int
    selected_candidate: Mapping[str, Any]
    claim_boundary: str


def load_convert_asset_package_handoff(
    package_dir: str | Path,
    manifest_path: str | Path,
    source_usd: str | Path,
    *,
    expected_scope_prims: tuple[str, ...],
    producer_revision: str,
    expected_consumer_profile: str = "scenario-forge",
    expected_runtime_profile: str = "isaac41",
    usage: str = "scene_overlay",
) -> ConvertAssetPackageHandoff:
    """Validate a source-bound ConvertAsset package without importing its internals."""

    package_root = Path(package_dir)
    external_manifest = Path(manifest_path)
    source_path = Path(source_usd)
    if not package_root.is_dir():
        raise ConvertAssetHandoffError(
            f"ConvertAsset package directory is missing: {package_root}"
        )
    if not external_manifest.is_file():
        raise ConvertAssetHandoffError(
            f"ConvertAsset manifest is missing: {external_manifest}"
        )
    if not source_path.is_file():
        raise ConvertAssetHandoffError(f"source USD is missing: {source_path}")
    if not producer_revision:
        raise ConvertAssetHandoffError("producer_revision must be a non-empty string")
    if not expected_scope_prims:
        raise ConvertAssetHandoffError("expected_scope_prims must not be empty")
    if usage not in _USAGE_ROLES:
        raise ConvertAssetHandoffError(
            "usage must be 'scene_overlay', 'rigid_object', 'articulated_object', "
            "'visual_static_environment', 'visual_static_object', or "
            "'static_support_object', or 'dynamic_context_object'"
        )

    manifest_bytes = external_manifest.read_bytes()
    embedded_manifest = package_root / "evidence" / "manifest.json"
    if not embedded_manifest.is_file():
        raise ConvertAssetHandoffError(
            "ConvertAsset package embedded manifest is missing: evidence/manifest.json"
        )
    if embedded_manifest.read_bytes() != manifest_bytes:
        raise ConvertAssetHandoffError(
            "external and embedded manifest bytes do not match"
        )
    manifest = _load_strict_json_mapping(manifest_bytes, "ConvertAsset manifest")
    manifest_digest = sha256(manifest_bytes).hexdigest()

    schema_version = _required_string(manifest, "schema_version", "manifest")
    if schema_version != "asset_application_normalizer.v1":
        raise ConvertAssetHandoffError(
            f"unsupported ConvertAsset manifest schema_version: {schema_version}"
        )
    _require_value(manifest, "overall_status", "pass", "manifest")
    package_id = _required_string(manifest, "package_id", "manifest")
    producer_asset_id = _required_string(manifest, "asset_id", "manifest")
    producer_asset_role = _required_string(manifest, "asset_role", "manifest")
    if usage in _DYNAMIC_USAGES:
        accepted_asset_roles = frozenset({"dynamic"})
    elif usage in _STATIC_SUPPORT_USAGES:
        accepted_asset_roles = frozenset({"static_support"})
    else:
        accepted_asset_roles = _VISUAL_STATIC_PRODUCER_ROLES[usage]
    if producer_asset_role not in accepted_asset_roles:
        accepted = ", ".join(sorted(accepted_asset_roles))
        raise ConvertAssetHandoffError(
            f"manifest.asset_role must be one of {{{accepted}}} for usage {usage!r}"
        )

    expected_scopes = _validated_scope_tuple(
        expected_scope_prims,
        "expected_scope_prims",
    )
    source_digest = _file_sha256(source_path)
    source = _required_mapping(manifest, "source", "manifest")
    source_integrity = _required_mapping(manifest, "source_integrity", "manifest")
    if source_integrity.get("unchanged") is not True:
        raise ConvertAssetHandoffError("manifest.source_integrity.unchanged must be true")
    source_hash_fields = {
        "manifest.source.sha256": _required_string(source, "sha256", "manifest.source"),
        "manifest.source_integrity.sha256_before": _required_string(
            source_integrity,
            "sha256_before",
            "manifest.source_integrity",
        ),
        "manifest.source_integrity.sha256_after": _required_string(
            source_integrity,
            "sha256_after",
            "manifest.source_integrity",
        ),
    }

    target = _required_mapping(manifest, "target", "manifest")
    runtime_profile = _required_string(
        target,
        "target_runtime_profile",
        "manifest.target",
    )
    if runtime_profile != expected_runtime_profile:
        raise ConvertAssetHandoffError(
            "manifest target runtime does not match expected runtime profile"
        )
    _require_value(
        target,
        "target_benchmark_profile",
        expected_consumer_profile,
        "manifest.target",
    )

    entrypoints = _required_mapping(manifest, "entrypoints", "manifest")
    consumer_profile = _required_string(
        entrypoints,
        "consumer_profile",
        "manifest.entrypoints",
    )
    if consumer_profile != expected_consumer_profile:
        raise ConvertAssetHandoffError(
            "manifest consumer profile does not match expected consumer profile"
        )
    root_usd = _safe_package_file(
        package_root,
        _required_string(entrypoints, "root_usd", "manifest.entrypoints"),
        "root_usd",
    )
    root_sha = _file_sha256(root_usd)
    default_prim = _required_string(
        entrypoints,
        "default_prim",
        "manifest.entrypoints",
    )
    root_prim_path = f"/{default_prim}"
    entry_scope = _required_string(
        entrypoints,
        "asset_entry_prim",
        "manifest.entrypoints",
    )
    if entry_scope not in expected_scopes:
        raise ConvertAssetHandoffError(
            "manifest asset_entry_prim is outside expected scope"
        )
    _require_scopes(entrypoints, "asset_scope_prims", expected_scopes, "entrypoints")
    _require_scopes(manifest, "asset_scope_prim_paths", expected_scopes, "manifest")
    for scope in expected_scopes:
        if scope != root_prim_path and not scope.startswith(root_prim_path + "/"):
            raise ConvertAssetHandoffError(
                "manifest asset scope is not below the package default prim"
            )

    physics = _required_mapping(manifest, "physics_closure", "manifest")
    _require_value(physics, "status", "pass", "manifest.physics_closure")
    physics_scope = _required_mapping(
        physics,
        "scope",
        "manifest.physics_closure",
    )
    _require_scopes(
        physics_scope,
        "asset_scope_prims",
        expected_scopes,
        "physics_closure.scope",
    )

    quality_tier: str | None = None
    profile_id: str | None = None
    profile_revision: str | None = None
    profile_sha: str | None = None
    claim_boundary: str | None = None
    replacement_contract: str | None = None
    source_binding: Mapping[str, Any] | None = None
    interaction_contract: ConvertAssetInteractionContract | None = None
    articulation_contract: ConvertAssetArticulationContract | None = None
    task_interactive_geometry: ConvertAssetTaskInteractiveGeometry | None = None
    task_qualifications = _load_task_qualifications(
        manifest.get("task_qualifications"),
        package_root=package_root,
    )
    support_audit = _load_support_audit(
        manifest.get("support_audit"),
        package_root=package_root,
    )
    static_support_contract: ConvertAssetStaticSupportContract | None = None
    dynamic_context_contract: ConvertAssetDynamicContextContract | None = None

    if usage in _DYNAMIC_USAGES:
        _require_value(physics, "role", "dynamic", "manifest.physics_closure")
        admission = _required_mapping(
            physics,
            "profile_admission",
            "manifest.physics_closure",
        )
        _require_value(admission, "status", "pass", "profile_admission")
        source_binding = _required_mapping(
            admission,
            "source_binding",
            "profile_admission",
        )
        source_hash_fields.update(
            {
                "profile_admission.source_binding.sha256": _required_string(
                    source_binding,
                    "sha256",
                    "profile_admission.source_binding",
                ),
                "profile_admission.source_sha256": _required_string(
                    admission,
                    "source_sha256",
                    "profile_admission",
                ),
            }
        )
        for field_name in (
            "unmatched_rigid_bodies",
            "ambiguous_rigid_bodies",
            "invalid_body_rules",
            "errors",
        ):
            if admission.get(field_name) != []:
                raise ConvertAssetHandoffError(
                    f"profile_admission.{field_name} must be empty"
                )
        resolved_body_count = admission.get("resolved_body_count")
        if (
            not isinstance(resolved_body_count, int)
            or isinstance(resolved_body_count, bool)
            or resolved_body_count <= 0
        ):
            raise ConvertAssetHandoffError(
                "profile_admission.resolved_body_count must be positive"
            )
        profile_path = _safe_package_file(
            package_root,
            _required_string(admission, "package_profile_path", "profile_admission"),
            "package_profile_path",
        )
        _safe_package_file(
            package_root,
            _required_string(admission, "overlay_path", "profile_admission"),
            "overlay_path",
        )
        profile_sha = _required_string(
            admission,
            "profile_sha256",
            "profile_admission",
        )
        packaged_profile_sha = _required_string(
            admission,
            "packaged_profile_sha256",
            "profile_admission",
        )
        if (
            profile_sha != packaged_profile_sha
            or _file_sha256(profile_path) != profile_sha
        ):
            raise ConvertAssetHandoffError(
                "profile SHA-256 does not match packaged profile"
            )
        quality_tier = _required_string(
            admission,
            "quality_tier",
            "profile_admission",
        )
        profile_id = _required_string(admission, "profile_id", "profile_admission")
        profile_revision = _required_string(
            admission,
            "revision",
            "profile_admission",
        )
        profile_evidence = _required_mapping(
            admission,
            "evidence",
            "profile_admission",
        )
        claim_boundary = _required_string(
            profile_evidence,
            "claim_boundary",
            "profile_admission.evidence",
        )
        replacement_contract = _required_string(
            profile_evidence,
            "replacement_contract",
            "profile_admission.evidence",
        )
        interaction_contract = _load_interaction_contract(
            manifest.get("interaction_contract"),
            package_root=package_root,
            source_sha256=source_digest,
            asset_entry_prim=entry_scope,
            required=usage == "rigid_object",
        )
        if usage == "dynamic_context_object" and interaction_contract is None:
            dynamic_context_contract = _load_dynamic_context_contract(
                manifest.get("dynamic_context_contract"),
                package_root=package_root,
                source_sha256=source_digest,
                asset_entry_prim=entry_scope,
            )
        if usage == "articulated_object":
            articulation_contract = _load_articulation_contract(
                manifest.get("articulation_contract"),
                manifest.get("articulation_closure"),
                package_root=package_root,
                source_sha256=source_digest,
                asset_entry_prim=entry_scope,
                expected_scopes=expected_scopes,
                runtime_profile=runtime_profile,
                manifest_sha256=manifest_digest,
                asset_sha256=root_sha,
            )
    elif usage in _STATIC_SUPPORT_USAGES:
        _require_value(
            physics,
            "role",
            "static_support",
            "manifest.physics_closure",
        )
        static_support_contract = _load_static_support_contract(
            manifest.get("static_support_contract"),
            package_root=package_root,
            source_sha256=source_digest,
            asset_entry_prim=entry_scope,
        )
        nested_contract = _required_mapping(
            physics,
            "static_support_contract",
            "manifest.physics_closure",
        )
        _validate_nested_static_support_contract(
            nested_contract,
            static_support_contract.payload,
        )
        output_admission = _required_mapping(
            manifest,
            "output_role_admission",
            "manifest",
        )
        _require_value(output_admission, "status", "pass", "output_role_admission")
        if output_admission.get("zero_dynamic_semantics") is not True:
            raise ConvertAssetHandoffError(
                "static support output admission must prove zero_dynamic_semantics"
            )
    else:
        physics_role = _required_string(
            physics,
            "role",
            "manifest.physics_closure",
        )
        accepted_physics_roles = frozenset({"visual_static", usage})
        if physics_role not in accepted_physics_roles:
            accepted = ", ".join(sorted(accepted_physics_roles))
            raise ConvertAssetHandoffError(
                "manifest.physics_closure.role must be one of "
                f"{{{accepted}}} for usage {usage!r}"
            )
        _validate_visual_static_admission(manifest, expected_scopes)
        _validate_visual_static_physical_frame(physics, expected_scopes)

    if usage in _TASK_INTERACTIVE_USAGES:
        if usage == "rigid_object" and interaction_contract is not None:
            support_frame = interaction_contract.named_frames.get("support")
            support_frame_source_sha256 = (
                interaction_contract.contract_payload_sha256
            )
            translation_field = "translation_body_local_usd"
            rotation_field = "rotation_body_local_wxyz"
            parent_field = "parent_prim"
        elif usage == "articulated_object" and articulation_contract is not None:
            mounting = articulation_contract.mounting
            if mounting is not None:
                support_frame = _required_mapping(
                    mounting,
                    "support_frame_root_local",
                    "articulation_contract.mounting",
                )
                support_frame_source_sha256 = _required_sha256(
                    mounting,
                    "runtime_report_sha256",
                    "articulation_contract.mounting",
                )
                translation_field = "translation_m"
                rotation_field = "rotation_wxyz"
                parent_field = None
            else:
                support_frame = articulation_contract.named_frames.get("support")
                support_frame_source_sha256 = articulation_contract.profile_sha256
                translation_field = "translation_parent_local_m"
                rotation_field = "rotation_parent_local_wxyz"
                parent_field = "parent_prim"
        else:
            raise ConvertAssetHandoffError(
                "task-interactive package is missing its validated producer contract"
            )
        if (
            not isinstance(support_frame, Mapping)
            or (
                parent_field is not None
                and (
                    support_frame.get(parent_field) != entry_scope
                    or support_frame.get("authoritative") is not True
                )
            )
        ):
            raise ConvertAssetHandoffError(
                "task-interactive package requires an authoritative root-local "
                "support frame"
            )
        task_interactive_geometry = _load_task_interactive_geometry(
            manifest,
            physics,
            asset_entry_prim=entry_scope,
            support_frame=support_frame,
            support_translation_field=translation_field,
            support_rotation_field=rotation_field,
            support_frame_source_sha256=support_frame_source_sha256,
            mounting=(
                articulation_contract.mounting
                if usage == "articulated_object"
                and articulation_contract is not None
                else None
            ),
        )

    for field_name, digest in source_hash_fields.items():
        if digest != source_digest:
            raise ConvertAssetHandoffError(
                f"source SHA-256 mismatch at {field_name}"
            )

    runtime = _required_mapping(manifest, "runtime_evidence", "manifest")
    _require_value(runtime, "status", "pass", "runtime_evidence")
    _require_value(
        runtime,
        "runtime_profile",
        expected_runtime_profile,
        "runtime_evidence",
    )
    runtime_gate_names = ["cold_load", "physics_step", "reset"]
    if usage in _VISUAL_STATIC_USAGES or usage in _STATIC_SUPPORT_USAGES:
        runtime_gate_names.append("render_readback")
    for gate_name in runtime_gate_names:
        gate = _required_mapping(runtime, gate_name, "runtime_evidence")
        _require_value(gate, "status", "pass", f"runtime_evidence.{gate_name}")
    if usage in _STATIC_SUPPORT_USAGES:
        qualification = _required_mapping(
            runtime,
            "static_support_qualification",
            "runtime_evidence",
        )
        _require_value(
            qualification,
            "status",
            "pass",
            "runtime_evidence.static_support_qualification",
        )
    for field_name in ("expected_root_usd_sha256", "root_usd_sha256"):
        if _required_string(runtime, field_name, "runtime_evidence") != root_sha:
            raise ConvertAssetHandoffError(
                f"root USD SHA-256 mismatch at runtime_evidence.{field_name}"
            )
    warning_gate = _required_mapping(
        runtime,
        "physics_warning_gate",
        "runtime_evidence",
    )
    _require_value(warning_gate, "status", "pass", "physics_warning_gate")
    _require_scopes(
        warning_gate,
        "scope_prims",
        expected_scopes,
        "physics_warning_gate",
    )
    scope_validation = _required_mapping(
        warning_gate,
        "scope_validation",
        "physics_warning_gate",
    )
    _require_value(scope_validation, "status", "pass", "scope_validation")
    _require_scopes(
        scope_validation,
        "scope_prims",
        expected_scopes,
        "scope_validation",
    )
    binding_validation = _required_mapping(
        warning_gate,
        "binding_validation",
        "physics_warning_gate",
    )
    _require_value(binding_validation, "status", "pass", "binding_validation")
    summary = _required_mapping(warning_gate, "summary", "physics_warning_gate")
    scoped_count = summary.get("scoped_event_count")
    if scoped_count != 0:
        raise ConvertAssetHandoffError(
            "physics_warning_gate.summary.scoped_event_count must be 0"
        )
    if (
        usage in _VISUAL_STATIC_USAGES
        and summary.get("unattributed_event_count") != 0
    ):
        raise ConvertAssetHandoffError(
            "physics_warning_gate.summary.unattributed_event_count must be 0"
        )

    _validate_retained_scope(manifest, expected_scopes)
    if source_binding is not None:
        _validate_stage_metrics(manifest, source_binding)
    claims_forbidden = _required_string_tuple(
        manifest,
        "claims_forbidden",
        "manifest",
    )
    return ConvertAssetPackageHandoff(
        package_dir=package_root,
        package_id=package_id,
        producer_asset_id=producer_asset_id,
        producer_asset_role=producer_asset_role,
        producer_revision=producer_revision,
        manifest_schema_version=schema_version,
        manifest_sha256=manifest_digest,
        source_sha256=source_digest,
        root_usd=root_usd,
        root_usd_sha256=root_sha,
        root_prim_path=root_prim_path,
        scope_prims=expected_scopes,
        runtime_profile=runtime_profile,
        consumer_profile=consumer_profile,
        quality_tier=quality_tier,
        profile_id=profile_id,
        profile_revision=profile_revision,
        profile_sha256=profile_sha,
        claim_boundary=claim_boundary,
        replacement_contract=replacement_contract,
        claims_forbidden=claims_forbidden,
        scoped_physics_warning_count=scoped_count,
        usage=usage,
        interaction_contract=interaction_contract,
        articulation_contract=articulation_contract,
        task_interactive_geometry=task_interactive_geometry,
        task_qualifications=task_qualifications,
        support_audit=support_audit,
        static_support_contract=static_support_contract,
        dynamic_context_contract=dynamic_context_contract,
    )


def _load_dynamic_context_contract(
    value: object,
    *,
    package_root: Path,
    source_sha256: str,
    asset_entry_prim: str,
) -> ConvertAssetDynamicContextContract:
    contract = _mapping(value, "manifest.dynamic_context_contract")
    _require_exact_fields(
        contract,
        {
            "schema_version",
            "status",
            "profile",
            "asset_entry_prim",
            "runtime_identity",
            "collider_prims",
            "support_frame",
            "stable_support_gate",
            "closure",
            "claim_boundary",
        },
        "manifest.dynamic_context_contract",
    )
    _require_value(
        contract,
        "schema_version",
        "aan.dynamic_context_contract.v1",
        "manifest.dynamic_context_contract",
    )
    _require_value(contract, "status", "pass", "manifest.dynamic_context_contract")
    profile = _required_mapping(
        contract, "profile", "manifest.dynamic_context_contract"
    )
    _require_value(
        profile,
        "schema_version",
        "aan.dynamic_context_profile.v1",
        "dynamic_context_contract.profile",
    )
    if _required_sha256(
        profile, "source_sha256", "dynamic_context_contract.profile"
    ) != source_sha256:
        raise ConvertAssetHandoffError(
            "dynamic_context_contract.profile.source_sha256 does not match source USD"
        )
    profile_path = _safe_package_file(
        package_root,
        _required_string(
            profile, "package_path", "dynamic_context_contract.profile"
        ),
        "dynamic_context_contract.profile.package_path",
    )
    if _file_sha256(profile_path) != _required_sha256(
        profile, "profile_sha256", "dynamic_context_contract.profile"
    ):
        raise ConvertAssetHandoffError(
            "dynamic_context_contract profile SHA-256 does not match packaged profile"
        )
    _safe_package_file(
        package_root,
        _required_string(
            profile, "overlay_path", "dynamic_context_contract.profile"
        ),
        "dynamic_context_contract.profile.overlay_path",
    )
    entry = _required_string(
        contract, "asset_entry_prim", "manifest.dynamic_context_contract"
    )
    if entry != asset_entry_prim:
        raise ConvertAssetHandoffError(
            "dynamic_context_contract.asset_entry_prim must match manifest asset_entry_prim"
        )
    identity = _required_mapping(
        contract, "runtime_identity", "manifest.dynamic_context_contract"
    )
    rigid_root = _required_string(
        identity, "rigid_root_prim", "dynamic_context_contract.runtime_identity"
    )
    if rigid_root != entry or identity.get("exactly_one_active_rigid_body") is not True:
        raise ConvertAssetHandoffError(
            "dynamic_context_contract requires one active rigid root at asset_entry_prim"
        )
    active = _required_string_tuple(
        identity,
        "active_rigid_body_prims",
        "dynamic_context_contract.runtime_identity",
    )
    if active != (rigid_root,):
        raise ConvertAssetHandoffError(
            "dynamic_context_contract active rigid body must equal its entry prim"
        )
    colliders = tuple(
        _required_string(item, "prim_path", f"dynamic_context_contract.collider_prims[{index}]")
        for index, item in enumerate(
            _required_mapping_list(
                contract.get("collider_prims"),
                "dynamic_context_contract.collider_prims",
            )
        )
    )
    if not colliders:
        raise ConvertAssetHandoffError(
            "dynamic_context_contract.collider_prims must not be empty"
        )
    support = _required_mapping(
        contract, "support_frame", "manifest.dynamic_context_contract"
    )
    if support.get("parent_prim") != entry or support.get("authoritative") is not True:
        raise ConvertAssetHandoffError(
            "dynamic_context_contract requires an authoritative root-local support frame"
        )
    closure = _required_mapping(
        contract, "closure", "manifest.dynamic_context_contract"
    )
    _require_value(closure, "status", "pass", "dynamic_context_contract.closure")
    _required_string(
        contract, "claim_boundary", "manifest.dynamic_context_contract"
    )
    return ConvertAssetDynamicContextContract(
        schema_version="aan.dynamic_context_contract.v1",
        asset_entry_prim=entry,
        rigid_root_prim=rigid_root,
        collider_prims=colliders,
        support_frame=_copy_json_mapping(support, "dynamic_context_contract.support_frame"),
        payload=_copy_json_mapping(contract, "dynamic_context_contract"),
    )


def _load_support_audit(
    value: Any,
    *,
    package_root: Path,
) -> ConvertAssetSupportAudit | None:
    if value is None:
        return None
    audit = _required_mapping({"support_audit": value}, "support_audit", "manifest")
    if audit.get("overall_status") == "not_requested":
        if audit.get("blocked_reasons") != [] or audit.get("support_closure") != {}:
            raise ConvertAssetHandoffError(
                "manifest.support_audit not_requested marker must have no blockers or closure"
            )
        return None
    _require_value(
        audit,
        "schema_version",
        "aan.generated_room_support_audit.v1",
        "manifest.support_audit",
    )
    _require_value(audit, "overall_status", "pass", "manifest.support_audit")
    if audit.get("blocked_reasons") != []:
        raise ConvertAssetHandoffError(
            "manifest.support_audit.blocked_reasons must be empty"
        )
    source_sha256 = _required_sha256(
        audit,
        "source_sha256",
        "manifest.support_audit",
    )
    review = _required_mapping(
        audit,
        "producer_review",
        "manifest.support_audit",
    )
    _require_value(review, "status", "pass", "manifest.support_audit.producer_review")
    _required_string(review, "reviewer", "manifest.support_audit.producer_review")
    raw_relations = audit.get("relations")
    if not isinstance(raw_relations, list):
        raise ConvertAssetHandoffError("manifest.support_audit.relations must be a list")
    removed_count = 0
    for index, raw_relation in enumerate(raw_relations):
        relation = _mapping(raw_relation, f"manifest.support_audit.relations[{index}]")
        _require_value(
            relation,
            "independent_status",
            "pass",
            f"manifest.support_audit.relations[{index}]",
        )
        if relation.get("producer_status") == "removed":
            removed_count += 1
    raw_closure = _required_mapping(
        audit,
        "support_closure",
        "manifest.support_audit",
    )
    closure: dict[str, tuple[str, ...]] = {}
    for support_prim, raw_objects in raw_closure.items():
        if not isinstance(support_prim, str) or not support_prim.startswith("/Room/"):
            raise ConvertAssetHandoffError(
                "manifest.support_audit.support_closure has an invalid support prim"
            )
        if not isinstance(raw_objects, list) or not all(
            isinstance(item, str) and item.startswith("/Room/")
            for item in raw_objects
        ):
            raise ConvertAssetHandoffError(
                "manifest.support_audit.support_closure has invalid object prims"
            )
        closure[support_prim] = tuple(raw_objects)
    report_path = package_root / "evidence" / "support_audit" / "report.json"
    if not report_path.is_file():
        raise ConvertAssetHandoffError(
            "ConvertAsset support_audit report is missing: evidence/support_audit/report.json"
        )
    report = _load_strict_json_mapping(
        report_path.read_bytes(),
        "ConvertAsset support_audit report",
    )
    if report != audit:
        raise ConvertAssetHandoffError(
            "ConvertAsset support_audit report disagrees with embedded manifest evidence"
        )
    return ConvertAssetSupportAudit(
        schema_version="aan.generated_room_support_audit.v1",
        source_sha256=source_sha256,
        relation_count=len(raw_relations),
        removed_decoration_count=removed_count,
        report_sha256=_file_sha256(report_path),
        support_closure=closure,
    )


def _load_static_support_contract(
    value: Any,
    *,
    package_root: Path,
    source_sha256: str,
    asset_entry_prim: str,
) -> ConvertAssetStaticSupportContract:
    contract = _required_mapping(
        {"static_support_contract": value},
        "static_support_contract",
        "manifest",
    )
    _require_value(
        contract,
        "schema_version",
        "aan.static_support_contract.v1",
        "manifest.static_support_contract",
    )
    _require_value(contract, "status", "pass", "manifest.static_support_contract")
    _require_value(
        contract,
        "asset_entry_prim",
        asset_entry_prim,
        "manifest.static_support_contract",
    )
    _require_value(
        contract,
        "collider_policy",
        "prefer_source_then_proxy",
        "manifest.static_support_contract",
    )
    selection = _required_string(
        contract,
        "collider_selection",
        "manifest.static_support_contract",
    )
    if selection not in {"preserved_source", "authored_proxy"}:
        raise ConvertAssetHandoffError(
            "static_support_contract.collider_selection is unsupported"
        )
    raw_colliders = contract.get("colliders")
    if not isinstance(raw_colliders, list) or not raw_colliders:
        raise ConvertAssetHandoffError(
            "static_support_contract.colliders must be a non-empty list"
        )
    collider_prims: list[str] = []
    for index, raw in enumerate(raw_colliders):
        collider = _mapping(
            raw,
            f"manifest.static_support_contract.colliders[{index}]",
        )
        prim_path = _required_string(
            collider,
            "prim_path",
            f"manifest.static_support_contract.colliders[{index}]",
        )
        if not (
            prim_path == asset_entry_prim
            or prim_path.startswith(asset_entry_prim.rstrip("/") + "/")
        ):
            raise ConvertAssetHandoffError(
                "static support collider is outside asset_entry_prim"
            )
        if collider.get("collision_enabled") is not True:
            raise ConvertAssetHandoffError(
                "static support collider must be explicitly enabled"
            )
        collider_prims.append(prim_path)
    if len(set(collider_prims)) != len(collider_prims):
        raise ConvertAssetHandoffError("static support collider paths must be unique")

    material = _required_mapping(
        contract,
        "physics_material",
        "manifest.static_support_contract",
    )
    expected_material = {
        "static_friction": 0.5,
        "dynamic_friction": 0.5,
        "restitution": 0.0,
        "friction_combine_mode": "max",
        "restitution_combine_mode": "multiply",
        "calibration_status": "provisional_unmeasured",
    }
    for key, expected in expected_material.items():
        if material.get(key) != expected:
            raise ConvertAssetHandoffError(
                f"static_support_contract.physics_material.{key} must be {expected!r}"
            )

    profile = _required_mapping(
        contract,
        "profile",
        "manifest.static_support_contract",
    )
    profile_path = _safe_package_file(
        package_root,
        _required_string(profile, "package_path", "static_support_contract.profile"),
        "static_support_contract.profile.package_path",
    )
    profile_sha = _required_sha256(
        profile,
        "sha256",
        "static_support_contract.profile",
    )
    if _file_sha256(profile_path) != profile_sha:
        raise ConvertAssetHandoffError(
            "static support packaged profile SHA-256 does not match"
        )
    if _required_sha256(
        profile,
        "source_usd_sha256",
        "static_support_contract.profile",
    ) != source_sha256:
        raise ConvertAssetHandoffError(
            "static support profile source SHA-256 does not match"
        )
    _safe_package_file(
        package_root,
        _required_string(
            contract,
            "overlay_path",
            "manifest.static_support_contract",
        ),
        "static_support_contract.overlay_path",
    )

    qualification = _required_mapping(
        contract,
        "qualification",
        "manifest.static_support_contract",
    )
    _require_value(
        qualification,
        "status",
        "pass",
        "static_support_contract.qualification",
    )
    _require_value(
        qualification,
        "schema_version",
        "aan.static_support_runtime_qualification.v1",
        "static_support_contract.qualification",
    )
    report_relative = _required_string(
        qualification,
        "report_path",
        "static_support_contract.qualification",
    )
    report_path = _safe_package_file(
        package_root,
        report_relative,
        "static_support_contract.qualification.report_path",
    )
    report_sha = _required_sha256(
        qualification,
        "report_sha256",
        "static_support_contract.qualification",
    )
    if _file_sha256(report_path) != report_sha:
        raise ConvertAssetHandoffError(
            "static support qualification report SHA-256 does not match"
        )
    report = _load_strict_json_mapping(
        report_path.read_bytes(),
        "static support qualification report",
    )
    _require_value(report, "status", "pass", "static support qualification report")
    required_probes = (
        "center_drop",
        "north_edge_drop",
        "south_edge_drop",
        "east_edge_drop",
        "west_edge_drop",
        "side_impact",
    )
    if tuple(qualification.get("required_probes", [])) != required_probes:
        raise ConvertAssetHandoffError(
            "static support qualification must declare the six v1 probes"
        )
    if qualification.get("probe_count") != 6 or report.get("probe_count") != 6:
        raise ConvertAssetHandoffError(
            "static support qualification probe_count must be 6"
        )
    raw_results = report.get("probe_results")
    if not isinstance(raw_results, list) or {
        item.get("probe")
        for item in raw_results
        if isinstance(item, Mapping) and item.get("status") == "pass"
    } != set(required_probes):
        raise ConvertAssetHandoffError(
            "static support qualification report must pass every v1 probe"
        )
    return ConvertAssetStaticSupportContract(
        schema_version="aan.static_support_contract.v1",
        asset_entry_prim=asset_entry_prim,
        collider_prims=tuple(collider_prims),
        profile_id=_required_string(
            contract,
            "profile_id",
            "manifest.static_support_contract",
        ),
        profile_revision=_required_string(
            contract,
            "profile_revision",
            "manifest.static_support_contract",
        ),
        profile_sha256=profile_sha,
        qualification_report_path=report_relative,
        qualification_report_sha256=report_sha,
        payload=_copy_json_mapping(contract, "static_support_contract"),
    )


def _validate_nested_static_support_contract(
    nested: Mapping[str, Any],
    final: Mapping[str, Any],
) -> None:
    """Accept ConvertAsset's pre-runtime snapshot plus final qualification.

    ``physics_closure`` records the authoring-time contract, where the runtime
    qualification is intentionally pending.  The top-level contract is the
    promoted, hash-bound result after the isolated Isaac worker succeeds.
    Every non-qualification field must remain byte-for-byte equivalent.
    """

    if nested == final:
        return
    nested_without_qualification = dict(nested)
    final_without_qualification = dict(final)
    nested_qualification = _mapping(
        nested_without_qualification.pop("qualification", None),
        "manifest.physics_closure.static_support_contract.qualification",
    )
    final_qualification = _mapping(
        final_without_qualification.pop("qualification", None),
        "manifest.static_support_contract.qualification",
    )
    if nested_without_qualification != final_without_qualification:
        raise ConvertAssetHandoffError(
            "physics_closure.static_support_contract disagrees with the top-level contract"
        )
    _require_value(
        nested_qualification,
        "status",
        "pending_runtime",
        "manifest.physics_closure.static_support_contract.qualification",
    )
    if nested_qualification.get("required_probes") != final_qualification.get(
        "required_probes"
    ):
        raise ConvertAssetHandoffError(
            "static support authoring and final qualification probe sets disagree"
        )


def _load_task_interactive_geometry(
    manifest: Mapping[str, Any],
    physics: Mapping[str, Any],
    *,
    asset_entry_prim: str,
    support_frame: Mapping[str, Any],
    support_translation_field: str,
    support_rotation_field: str,
    support_frame_source_sha256: str,
    mounting: Mapping[str, Any] | None,
) -> ConvertAssetTaskInteractiveGeometry:
    """Validate the producer frame used by task-level USD reference composition."""

    fingerprint = _required_mapping(
        manifest,
        "visual_preservation_fingerprint",
        "manifest",
    )
    _require_value(
        fingerprint,
        "status",
        "pass",
        "visual_preservation_fingerprint",
    )
    package_fingerprint = _required_mapping(
        fingerprint,
        "package_before_physics_profile",
        "visual_preservation_fingerprint",
    )
    transforms = _required_mapping(
        package_fingerprint,
        "scope_world_transforms",
        "visual_preservation_fingerprint.package_before_physics_profile",
    )
    raw_transform = transforms.get(asset_entry_prim)
    if not isinstance(raw_transform, list) or len(raw_transform) != 4:
        raise ConvertAssetHandoffError(
            "task-interactive asset entry transform must be a 4x4 matrix at "
            f"{asset_entry_prim}"
        )
    rows: list[tuple[float, float, float, float]] = []
    for row_index, raw_row in enumerate(raw_transform):
        row = _finite_number_list(
            raw_row,
            4,
            "visual_preservation_fingerprint."
            "package_before_physics_profile.scope_world_transforms"
            f"[{asset_entry_prim}][{row_index}]",
        )
        rows.append((row[0], row[1], row[2], row[3]))
    identity = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    if any(
        not math.isclose(
            value,
            expected,
            rel_tol=0.0,
            abs_tol=_TASK_INTERACTIVE_IDENTITY_TOLERANCE,
        )
        for row, expected_row in zip(rows, identity, strict=True)
        for value, expected in zip(row, expected_row, strict=True)
    ):
        raise ConvertAssetHandoffError(
            "task-interactive asset entry transform must be identity within "
            f"{_TASK_INTERACTIVE_IDENTITY_TOLERANCE:g} at {asset_entry_prim}"
        )

    frame = _required_mapping(
        physics,
        "physical_frame",
        "manifest.physics_closure",
    )
    _require_value(
        frame,
        "status",
        "pass",
        "physics_closure.physical_frame",
    )
    if frame.get("metric_mismatches") != []:
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.metric_mismatches must be empty"
        )
    if frame.get("blocked_scope_prims") != []:
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.blocked_scope_prims must be empty"
        )
    raw_scope_bounds = frame.get("scope_bounds")
    if not isinstance(raw_scope_bounds, list):
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.scope_bounds must be a list"
        )
    matching_bounds = [
        _mapping(item, "physics_closure.physical_frame.scope_bounds")
        for item in raw_scope_bounds
        if isinstance(item, Mapping) and item.get("path") == asset_entry_prim
    ]
    if len(matching_bounds) != 1:
        raise ConvertAssetHandoffError(
            "task-interactive asset requires exactly one physical-frame bound for "
            f"{asset_entry_prim}"
        )
    bound = matching_bounds[0]
    _require_value(
        bound,
        "status",
        "pass",
        f"physics_closure.physical_frame.scope_bounds[{asset_entry_prim}]",
    )
    package_bound = _required_mapping(
        bound,
        "package_world_bound_m",
        f"physics_closure.physical_frame.scope_bounds[{asset_entry_prim}]",
    )
    lower = _finite_number_list(
        package_bound.get("min"),
        3,
        "task-interactive package_world_bound_m.min",
    )
    upper = _finite_number_list(
        package_bound.get("max"),
        3,
        "task-interactive package_world_bound_m.max",
    )
    if any(
        maximum <= minimum
        for minimum, maximum in zip(lower, upper, strict=True)
    ):
        raise ConvertAssetHandoffError(
            "task-interactive package world bound must have positive extent"
        )
    support_translation = _finite_number_list(
        support_frame.get(support_translation_field),
        3,
        f"task-interactive support frame.{support_translation_field}",
    )
    support_rotation = _finite_number_list(
        support_frame.get(support_rotation_field),
        4,
        f"task-interactive support frame.{support_rotation_field}",
    )
    if not math.isclose(
        sum(component * component for component in support_rotation),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ConvertAssetHandoffError(
            "task-interactive support frame rotation must be a unit quaternion"
        )
    source_digest = support_frame_source_sha256
    if _SHA256_HEX.fullmatch(source_digest) is None:
        raise ConvertAssetHandoffError(
            "task-interactive support frame source must be a lowercase "
            "SHA-256 digest"
        )
    return ConvertAssetTaskInteractiveGeometry(
        asset_entry_prim=asset_entry_prim,
        entry_world_transform=tuple(rows),
        package_world_bound_min_m=(lower[0], lower[1], lower[2]),
        package_world_bound_max_m=(upper[0], upper[1], upper[2]),
        support_frame_local_matrix=_pose_matrix_row_major(
            support_translation,
            support_rotation,
        ),
        support_frame_source_sha256=source_digest,
        mounting=(
            _copy_json_mapping(
                mounting,
                "task_interactive_geometry.mounting",
            )
            if mounting is not None
            else None
        ),
    )


def _pose_matrix_row_major(
    translation: list[float],
    rotation_wxyz: list[float],
) -> tuple[tuple[float, float, float, float], ...]:
    """Return a USD/Gf row-vector transform matrix for a local frame pose."""

    w, x, y, z = rotation_wxyz
    column_rotation = (
        (
            1.0 - 2.0 * (y * y + z * z),
            2.0 * (x * y - w * z),
            2.0 * (x * z + w * y),
        ),
        (
            2.0 * (x * y + w * z),
            1.0 - 2.0 * (x * x + z * z),
            2.0 * (y * z - w * x),
        ),
        (
            2.0 * (x * z - w * y),
            2.0 * (y * z + w * x),
            1.0 - 2.0 * (x * x + y * y),
        ),
    )
    return (
        (
            column_rotation[0][0],
            column_rotation[1][0],
            column_rotation[2][0],
            0.0,
        ),
        (
            column_rotation[0][1],
            column_rotation[1][1],
            column_rotation[2][1],
            0.0,
        ),
        (
            column_rotation[0][2],
            column_rotation[1][2],
            column_rotation[2][2],
            0.0,
        ),
        (translation[0], translation[1], translation[2], 1.0),
    )


def _load_task_qualifications(
    value: object,
    *,
    package_root: Path,
) -> tuple[ConvertAssetTaskQualification, ...]:
    if value is None:
        return ()
    raw_items = _required_mapping_list(value, "manifest.task_qualifications")
    qualifications: list[ConvertAssetTaskQualification] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_items):
        field = f"manifest.task_qualifications[{index}]"
        qualification_id = _required_string(item, "qualification_id", field)
        if qualification_id in seen_ids:
            raise ConvertAssetHandoffError(
                "manifest.task_qualifications qualification_id values "
                "must be unique"
            )
        seen_ids.add(qualification_id)
        status = _required_string(item, "status", field)
        if status != "pass":
            raise ConvertAssetHandoffError(
                f"{field}.status must be pass"
            )
        report_relative_path = _required_string(item, "report_path", field)
        report_path = _safe_package_file(
            package_root,
            report_relative_path,
            f"{field}.report_path",
        )
        report_sha256 = _required_sha256(item, "report_sha256", field)
        if _file_sha256(report_path) != report_sha256:
            raise ConvertAssetHandoffError(
                f"{field}.report_sha256 does not match qualification report"
            )
        qualifications.append(
            ConvertAssetTaskQualification(
                qualification_id=qualification_id,
                status=status,
                report_path=report_relative_path,
                report_sha256=report_sha256,
                payload=_copy_json_mapping(item, field),
            )
        )
    return tuple(qualifications)


def _load_articulation_contract(
    value: object,
    closure_value: object,
    *,
    package_root: Path,
    source_sha256: str,
    asset_entry_prim: str,
    expected_scopes: tuple[str, ...],
    runtime_profile: str,
    manifest_sha256: str,
    asset_sha256: str,
) -> ConvertAssetArticulationContract:
    contract = _mapping(value, "manifest.articulation_contract")
    contract_fields = {
        "schema_version",
        "status",
        "profile",
        "runtime_qualification",
    }
    if "mounting" in contract:
        contract_fields.add("mounting")
    _require_exact_fields(
        contract,
        contract_fields,
        "manifest.articulation_contract",
    )
    _require_value(
        contract,
        "schema_version",
        "aan.articulation_contract.v1",
        "manifest.articulation_contract",
    )
    _require_value(
        contract,
        "status",
        "pass",
        "manifest.articulation_contract",
    )

    profile_metadata = _required_mapping(
        contract,
        "profile",
        "manifest.articulation_contract",
    )
    _require_exact_fields(
        profile_metadata,
        {
            "schema_version",
            "profile_id",
            "revision",
            "source_sha256",
            "profile_sha256",
            "package_path",
        },
        "articulation_contract.profile",
    )
    _require_value(
        profile_metadata,
        "schema_version",
        "aan.articulated_device_profile.v1",
        "articulation_contract.profile",
    )
    profile_id = _required_string(
        profile_metadata,
        "profile_id",
        "articulation_contract.profile",
    )
    profile_revision = _required_string(
        profile_metadata,
        "revision",
        "articulation_contract.profile",
    )
    if (
        _required_sha256(
            profile_metadata,
            "source_sha256",
            "articulation_contract.profile",
        )
        != source_sha256
    ):
        raise ConvertAssetHandoffError(
            "articulation_contract.profile.source_sha256 does not match source USD"
        )
    profile_relative_path = _required_string(
        profile_metadata,
        "package_path",
        "articulation_contract.profile",
    )
    profile_path = _safe_package_file(
        package_root,
        profile_relative_path,
        "articulation_contract.profile.package_path",
    )
    profile_sha = _required_sha256(
        profile_metadata,
        "profile_sha256",
        "articulation_contract.profile",
    )
    if _file_sha256(profile_path) != profile_sha:
        raise ConvertAssetHandoffError(
            "articulation_contract.profile.profile_sha256 does not match "
            "packaged device profile"
        )
    profile = _load_strict_json_mapping(
        profile_path.read_bytes(),
        "articulation_contract device profile",
    )
    profile_fields = {
        "schema_version",
        "profile_id",
        "revision",
        "source_sha256",
        "asset_entry_prim",
        "articulation_root_prim",
        "runtime_units",
        "semantic_joints",
        "named_frames",
        "required_runtime_task_gates",
    }
    if "mounting" in profile:
        profile_fields.add("mounting")
    _require_exact_fields(
        profile,
        profile_fields,
        "articulation_contract.device_profile",
    )
    _require_value(
        profile,
        "schema_version",
        "aan.articulated_device_profile.v1",
        "articulation_contract.device_profile",
    )
    _require_value(
        profile,
        "profile_id",
        profile_id,
        "articulation_contract.device_profile",
    )
    _require_value(
        profile,
        "revision",
        profile_revision,
        "articulation_contract.device_profile",
    )
    if (
        _required_sha256(
            profile,
            "source_sha256",
            "articulation_contract.device_profile",
        )
        != source_sha256
    ):
        raise ConvertAssetHandoffError(
            "articulation_contract.device_profile.source_sha256 does not "
            "match source USD"
        )
    _require_value(
        profile,
        "asset_entry_prim",
        asset_entry_prim,
        "articulation_contract.device_profile",
    )
    articulation_root = _required_string(
        profile,
        "articulation_root_prim",
        "articulation_contract.device_profile",
    )
    _require_prim_within(
        articulation_root,
        asset_entry_prim,
        "articulation_contract.device_profile.articulation_root_prim",
        allow_root=True,
    )
    runtime_units = _required_mapping(
        profile,
        "runtime_units",
        "articulation_contract.device_profile",
    )
    _require_exact_fields(
        runtime_units,
        {"revolute", "prismatic"},
        "articulation_contract.device_profile.runtime_units",
    )
    _require_value(
        runtime_units,
        "revolute",
        "radian",
        "articulation_contract.device_profile.runtime_units",
    )
    _require_value(
        runtime_units,
        "prismatic",
        "meter",
        "articulation_contract.device_profile.runtime_units",
    )
    required_runtime_task_gates = _string_list(
        profile.get("required_runtime_task_gates"),
        (
            "articulation_contract.device_profile."
            "required_runtime_task_gates"
        ),
    )
    if not required_runtime_task_gates:
        raise ConvertAssetHandoffError(
            "articulation_contract.device_profile.required_runtime_task_gates "
            "must not be empty"
        )

    closure = _mapping(closure_value, "manifest.articulation_closure")
    _require_value(
        closure,
        "status",
        "pass",
        "manifest.articulation_closure",
    )
    closure_scope = _required_mapping(
        closure,
        "scope",
        "manifest.articulation_closure",
    )
    _require_scopes(
        closure_scope,
        "asset_scope_prims",
        expected_scopes,
        "articulation_closure.scope",
    )
    roots = _required_mapping_list(
        closure.get("articulation_roots"),
        "articulation_closure.articulation_roots",
    )
    if len(roots) != 1:
        raise ConvertAssetHandoffError(
            "articulation_closure must contain exactly one articulation root"
        )
    closure_root = _required_string(
        roots[0],
        "prim_path",
        "articulation_closure.articulation_roots[0]",
    )
    if closure_root != articulation_root:
        raise ConvertAssetHandoffError(
            "device profile articulation_root_prim does not match "
            "articulation_closure"
        )

    raw_joints = _required_mapping_list(
        closure.get("joints"),
        "articulation_closure.joints",
    )
    joints_by_prim: dict[str, Mapping[str, Any]] = {}
    joint_types: dict[str, str] = {}
    joint_limits: dict[str, tuple[float, float]] = {}
    joint_resets: dict[str, float] = {}
    for index, joint in enumerate(raw_joints):
        field = f"articulation_closure.joints[{index}]"
        joint_prim = _required_string(joint, "prim_path", field)
        _require_prim_within(
            joint_prim,
            articulation_root,
            f"{field}.prim_path",
            allow_root=False,
        )
        if joint_prim in joints_by_prim:
            raise ConvertAssetHandoffError(
                "articulation_closure.joints prim_path entries must be unique"
            )
        joints_by_prim[joint_prim] = joint
        joint_type = _required_string(joint, "joint_type", field)
        if joint_type not in {
            "PhysicsRevoluteJoint",
            "PhysicsPrismaticJoint",
        }:
            continue
        axis = _required_mapping(joint, "axis", field)
        _require_value(axis, "status", "pass", f"{field}.axis")
        _required_string(axis, "value", f"{field}.axis")
        limits = _required_mapping(joint, "limits", field)
        _require_value(limits, "status", "pass", f"{field}.limits")
        lower_record = _required_mapping(limits, "lower", f"{field}.limits")
        upper_record = _required_mapping(limits, "upper", f"{field}.limits")
        _require_value(
            lower_record,
            "status",
            "pass",
            f"{field}.limits.lower",
        )
        _require_value(
            upper_record,
            "status",
            "pass",
            f"{field}.limits.upper",
        )
        lower = _finite_number(
            lower_record.get("value"),
            f"{field}.limits.lower.value",
        )
        upper = _finite_number(
            upper_record.get("value"),
            f"{field}.limits.upper.value",
        )
        if lower >= upper:
            raise ConvertAssetHandoffError(
                f"{field}.limits must have lower.value < upper.value"
            )
        enabled = _required_mapping(joint, "enabled", field)
        _require_value(enabled, "status", "pass", f"{field}.enabled")
        _require_value(enabled, "value", True, f"{field}.enabled")
        reset_record = _required_mapping(joint, "reset_value", field)
        _require_value(
            reset_record,
            "status",
            "pass",
            f"{field}.reset_value",
        )
        reset = _finite_number(
            reset_record.get("value"),
            f"{field}.reset_value.value",
        )
        if not lower <= reset <= upper:
            raise ConvertAssetHandoffError(
                f"{field}.reset_value must be within joint limits"
            )
        joint_limits[joint_prim] = (lower, upper)
        joint_resets[joint_prim] = reset
        joint_types[joint_prim] = joint_type

    raw_dof_mapping = _required_mapping_list(
        closure.get("dof_mapping"),
        "articulation_closure.dof_mapping",
    )
    if not raw_dof_mapping:
        raise ConvertAssetHandoffError(
            "articulation_closure.dof_mapping must contain a positive DOF count"
        )
    mapping_by_index: dict[int, Mapping[str, Any]] = {}
    mapping_by_prim: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(raw_dof_mapping):
        field = f"articulation_closure.dof_mapping[{index}]"
        dof_index = item.get("dof_index")
        if (
            not isinstance(dof_index, int)
            or isinstance(dof_index, bool)
            or dof_index < 0
        ):
            raise ConvertAssetHandoffError(
                f"{field}.dof_index must be a non-negative integer"
            )
        if dof_index in mapping_by_index:
            raise ConvertAssetHandoffError(
                "articulation_closure.dof_mapping dof_index values must be unique"
            )
        joint_prim = _required_string(item, "joint_prim", field)
        if joint_prim in mapping_by_prim:
            raise ConvertAssetHandoffError(
                "articulation_closure.dof_mapping joint_prim values must be unique"
            )
        mapped_joint = joints_by_prim.get(joint_prim)
        if mapped_joint is None or joint_prim not in joint_limits:
            raise ConvertAssetHandoffError(
                f"{field}.joint_prim must identify one controllable joint"
            )
        for key in ("joint_type",):
            if item.get(key) != mapped_joint.get(key):
                raise ConvertAssetHandoffError(
                    f"{field}.{key} must match articulation_closure.joints"
                )
        axis = _required_mapping(mapped_joint, "axis", field)
        if item.get("axis") != axis.get("value"):
            raise ConvertAssetHandoffError(
                f"{field}.axis must match articulation_closure.joints"
            )
        mapping_by_index[dof_index] = item
        mapping_by_prim[joint_prim] = item
    if sorted(mapping_by_index) != list(range(len(mapping_by_index))):
        raise ConvertAssetHandoffError(
            "articulation_closure.dof_mapping dof_index values must be "
            "contiguous from 0"
        )

    raw_reset_values = _required_mapping_list(
        closure.get("reset_values"),
        "articulation_closure.reset_values",
    )
    reset_by_prim: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(raw_reset_values):
        field = f"articulation_closure.reset_values[{index}]"
        joint_prim = _required_string(item, "joint_prim", field)
        if joint_prim in reset_by_prim:
            raise ConvertAssetHandoffError(
                "articulation_closure.reset_values joint_prim entries must be unique"
            )
        mapping = mapping_by_prim.get(joint_prim)
        if mapping is None:
            raise ConvertAssetHandoffError(
                f"{field}.joint_prim must identify one mapped DOF"
            )
        if item.get("joint_type") != mapping.get("joint_type"):
            raise ConvertAssetHandoffError(
                f"{field}.joint_type must match the mapped DOF"
            )
        reset_record = _required_mapping(item, "reset_value", field)
        _require_value(
            reset_record,
            "status",
            "pass",
            f"{field}.reset_value",
        )
        reset = _finite_number(
            reset_record.get("value"),
            f"{field}.reset_value.value",
        )
        if reset != joint_resets[joint_prim]:
            raise ConvertAssetHandoffError(
                f"{field}.reset_value must match articulation_closure.joints"
            )
        lower, upper = joint_limits[joint_prim]
        if not lower <= reset <= upper:
            raise ConvertAssetHandoffError(
                f"{field}.reset_value must be within joint limits"
            )
        reset_by_prim[joint_prim] = item
    if set(reset_by_prim) != set(mapping_by_prim):
        raise ConvertAssetHandoffError(
            "articulation_closure.reset_values must cover every mapped DOF"
        )

    summary = _required_mapping(
        closure,
        "summary",
        "manifest.articulation_closure",
    )
    _require_value(
        summary,
        "articulation_root_count",
        1,
        "articulation_closure.summary",
    )
    _require_value(
        summary,
        "joint_count",
        len(raw_joints),
        "articulation_closure.summary",
    )
    _require_value(
        summary,
        "controllable_dof_count",
        len(raw_dof_mapping),
        "articulation_closure.summary",
    )

    raw_semantic_joints = _mapping(
        profile.get("semantic_joints"),
        "articulation_contract.device_profile.semantic_joints",
    )
    if not raw_semantic_joints:
        raise ConvertAssetHandoffError(
            "articulation_contract.device_profile.semantic_joints must not be empty"
        )
    semantic_joints: dict[str, Mapping[str, Any]] = {}
    seen_semantic_dofs: set[int] = set()
    wire_joints: dict[str, dict[str, Any]] = {}
    for semantic_name, raw_semantic in raw_semantic_joints.items():
        if (
            not isinstance(semantic_name, str)
            or not semantic_name
            or "." in semantic_name
        ):
            raise ConvertAssetHandoffError(
                "articulation_contract.device_profile.semantic_joints keys "
                "must be non-empty and contain no '.'"
            )
        field = (
            "articulation_contract.device_profile.semantic_joints."
            f"{semantic_name}"
        )
        semantic = _mapping(raw_semantic, field)
        _require_exact_fields(
            semantic,
            {
                "joint_prim",
                "part_prim",
                "dof_index",
                "runtime_reset_value",
                "reset_state",
                "states",
            },
            field,
        )
        joint_prim = _required_string(semantic, "joint_prim", field)
        part_prim = _required_string(semantic, "part_prim", field)
        _require_prim_within(
            part_prim,
            articulation_root,
            f"{field}.part_prim",
            allow_root=False,
        )
        dof_index = semantic.get("dof_index")
        if (
            not isinstance(dof_index, int)
            or isinstance(dof_index, bool)
            or mapping_by_index.get(dof_index, {}).get("joint_prim") != joint_prim
        ):
            raise ConvertAssetHandoffError(
                f"{field}.dof_index and joint_prim must identify the same DOF"
            )
        if dof_index in seen_semantic_dofs:
            raise ConvertAssetHandoffError(
                f"{field}.dof_index must be unique across semantic_joints"
            )
        seen_semantic_dofs.add(dof_index)
        joint_type = joint_types[joint_prim]
        raw_lower_limit, raw_upper_limit = joint_limits[joint_prim]
        runtime_lower_limit = (
            math.radians(raw_lower_limit)
            if joint_type == "PhysicsRevoluteJoint"
            else raw_lower_limit
        )
        runtime_upper_limit = (
            math.radians(raw_upper_limit)
            if joint_type == "PhysicsRevoluteJoint"
            else raw_upper_limit
        )
        expected_runtime_reset = (
            math.radians(joint_resets[joint_prim])
            if joint_type == "PhysicsRevoluteJoint"
            else joint_resets[joint_prim]
        )
        runtime_reset = _finite_number(
            semantic.get("runtime_reset_value"),
            f"{field}.runtime_reset_value",
        )
        if not math.isclose(
            runtime_reset,
            expected_runtime_reset,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ConvertAssetHandoffError(
                f"{field}.runtime_reset_value must match the normalized "
                "runtime value of articulation_closure reset"
            )
        raw_states = _mapping(semantic.get("states"), f"{field}.states")
        if not raw_states:
            raise ConvertAssetHandoffError(f"{field}.states must not be empty")
        states: dict[str, list[float]] = {}
        for state_name, raw_interval in raw_states.items():
            if (
                not isinstance(state_name, str)
                or not state_name
                or "." in state_name
            ):
                raise ConvertAssetHandoffError(
                    f"{field}.states keys must be non-empty and contain no '.'"
                )
            interval = _finite_number_list(
                raw_interval,
                2,
                f"{field}.states.{state_name}",
            )
            if interval[0] > interval[1]:
                raise ConvertAssetHandoffError(
                    f"{field}.states.{state_name} lower bound must not "
                    "exceed upper bound"
                )
            if (
                interval[0] < runtime_lower_limit - 1e-6
                or interval[1] > runtime_upper_limit + 1e-6
            ):
                raise ConvertAssetHandoffError(
                    f"{field}.states.{state_name} must remain within joint limits"
                )
            states[state_name] = interval
        reset_state = _required_string(semantic, "reset_state", field)
        if reset_state not in states:
            raise ConvertAssetHandoffError(
                f"{field}.reset_state must name one declared state"
            )
        reset_interval = states[reset_state]
        if not reset_interval[0] <= runtime_reset <= reset_interval[1]:
            raise ConvertAssetHandoffError(
                f"{field}.reset_state must contain the joint reset value"
            )
        semantic_joints[semantic_name] = semantic
        wire_joints[semantic_name] = {
            "joint_prim": joint_prim,
            "part_prim": part_prim,
            "runtime_reset_value": runtime_reset,
            "states": states,
        }
    if seen_semantic_dofs != set(mapping_by_index):
        raise ConvertAssetHandoffError(
            "articulation_contract.device_profile.semantic_joints must cover "
            "every mapped DOF"
        )

    raw_frames = _mapping(
        profile.get("named_frames"),
        "articulation_contract.device_profile.named_frames",
    )
    if not raw_frames:
        raise ConvertAssetHandoffError(
            "articulation_contract.device_profile.named_frames must not be empty"
        )
    named_frames: dict[str, Mapping[str, Any]] = {}
    for frame_name, raw_frame in raw_frames.items():
        if (
            not isinstance(frame_name, str)
            or not frame_name
            or "." in frame_name
        ):
            raise ConvertAssetHandoffError(
                "articulation_contract.device_profile.named_frames keys "
                "must be non-empty and contain no '.'"
            )
        field = (
            "articulation_contract.device_profile.named_frames."
            f"{frame_name}"
        )
        frame = _mapping(raw_frame, field)
        _require_exact_fields(
            frame,
            {
                "parent_prim",
                "translation_parent_local_m",
                "rotation_parent_local_wxyz",
                "authoritative",
            },
            field,
        )
        _require_prim_within(
            _required_string(frame, "parent_prim", field),
            articulation_root,
            f"{field}.parent_prim",
            allow_root=True,
        )
        _finite_number_list(
            frame.get("translation_parent_local_m"),
            3,
            f"{field}.translation_parent_local_m",
        )
        rotation = _finite_number_list(
            frame.get("rotation_parent_local_wxyz"),
            4,
            f"{field}.rotation_parent_local_wxyz",
        )
        if not math.isclose(
            sum(component * component for component in rotation),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ConvertAssetHandoffError(
                f"{field}.rotation_parent_local_wxyz must be a unit quaternion"
            )
        _require_value(frame, "authoritative", True, field)
        named_frames[frame_name] = frame

    runtime = _required_mapping(
        contract,
        "runtime_qualification",
        "manifest.articulation_contract",
    )
    _require_exact_fields(
        runtime,
        {"status", "report_path", "report_sha256"},
        "articulation_contract.runtime_qualification",
    )
    _require_value(
        runtime,
        "status",
        "pass",
        "articulation_contract.runtime_qualification",
    )
    report_relative_path = _required_string(
        runtime,
        "report_path",
        "articulation_contract.runtime_qualification",
    )
    report_path = _safe_package_file(
        package_root,
        report_relative_path,
        "articulation_contract.runtime_qualification.report_path",
    )
    report_sha = _required_sha256(
        runtime,
        "report_sha256",
        "articulation_contract.runtime_qualification",
    )
    if _file_sha256(report_path) != report_sha:
        raise ConvertAssetHandoffError(
            "articulation_contract.runtime_qualification.report_sha256 "
            "does not match qualification report"
        )
    report = _load_strict_json_mapping(
        report_path.read_bytes(),
        "articulation_contract.runtime_qualification.report",
    )
    _require_value(
        report,
        "schema_version",
        "aan.articulation_runtime_qualification.v1",
        "articulation_contract.runtime_qualification.report",
    )
    _require_value(
        report,
        "status",
        "pass",
        "articulation_contract.runtime_qualification.report",
    )
    report_inputs = _required_mapping(
        report,
        "inputs",
        "articulation_contract.runtime_qualification.report",
    )
    report_profile = _required_mapping(
        report_inputs,
        "device_profile",
        "articulation_contract.runtime_qualification.report.inputs",
    )
    _require_exact_fields(
        report_profile,
        {"schema_version", "profile_sha256", "source_sha256"},
        "articulation runtime report.inputs.device_profile",
    )
    _require_value(
        report_profile,
        "schema_version",
        "aan.articulated_device_profile.v1",
        "articulation runtime report.inputs.device_profile",
    )
    if (
        _required_sha256(
            report_profile,
            "profile_sha256",
            "articulation runtime report.inputs.device_profile",
        )
        != profile_sha
    ):
        raise ConvertAssetHandoffError(
            "articulation runtime report.inputs.device_profile.profile_sha256 "
            "does not match the packaged device profile"
        )
    if (
        _required_sha256(
            report_profile,
            "source_sha256",
            "articulation runtime report.inputs.device_profile",
        )
        != source_sha256
    ):
        raise ConvertAssetHandoffError(
            "articulation runtime report.inputs.device_profile.source_sha256 "
            "does not match source USD"
        )
    runtime_dof_mapping = _required_mapping_list(
        report.get("runtime_dof_mapping"),
        (
            "articulation_contract.runtime_qualification.report."
            "runtime_dof_mapping"
        ),
    )
    runtime_dofs_by_index: dict[int, Mapping[str, Any]] = {}
    for index, item in enumerate(runtime_dof_mapping):
        field = (
            "articulation_contract.runtime_qualification.report."
            f"runtime_dof_mapping[{index}]"
        )
        _require_exact_fields(
            item,
            {"dof_index", "dof_name", "joint_prim"},
            field,
        )
        dof_index = item.get("dof_index")
        if (
            not isinstance(dof_index, int)
            or isinstance(dof_index, bool)
            or dof_index < 0
            or dof_index in runtime_dofs_by_index
        ):
            raise ConvertAssetHandoffError(
                f"{field}.dof_index must be a unique non-negative integer"
            )
        _required_string(item, "dof_name", field)
        joint_prim = _required_string(item, "joint_prim", field)
        closure_joint = mapping_by_index.get(dof_index)
        if (
            closure_joint is None
            or closure_joint.get("joint_prim") != joint_prim
        ):
            raise ConvertAssetHandoffError(
                f"{field} must match articulation_closure.dof_mapping at "
                "the same runtime DOF index"
            )
        runtime_dofs_by_index[dof_index] = item
    if set(runtime_dofs_by_index) != set(mapping_by_index):
        raise ConvertAssetHandoffError(
            "articulation runtime_dof_mapping must cover every mapped DOF"
        )
    task_gates = _required_mapping(
        report,
        "task_gates",
        "articulation_contract.runtime_qualification.report",
    )
    for gate_name in required_runtime_task_gates:
        gate = _required_mapping(
            task_gates,
            gate_name,
            "articulation runtime task_gates",
        )
        _require_value(
            gate,
            "status",
            "pass",
            f"articulation runtime task_gates.{gate_name}",
        )
    mounting = _load_articulated_mounting(
        manifest_value=contract.get("mounting"),
        profile_value=profile.get("mounting"),
        report_value=report.get("qualified_consumer_placement"),
        asset_entry_prim=asset_entry_prim,
        source_sha256=source_sha256,
        profile_sha256=profile_sha,
        runtime_report_sha256=report_sha,
        required_runtime_task_gates=required_runtime_task_gates,
        runtime_reset_by_dof={
            int(item["dof_index"]): _finite_number(
                item["runtime_reset_value"],
                "articulation semantic joint runtime_reset_value",
            )
            for item in semantic_joints.values()
        },
    )
    promotion_relative_path = _validate_articulation_promotion(
        package_root=package_root,
        manifest_sha256=manifest_sha256,
        asset_sha256=asset_sha256,
        asset_entry_prim=asset_entry_prim,
        runtime_profile=runtime_profile,
        profile_relative_path=profile_relative_path,
        profile_sha256=profile_sha,
        report_relative_path=report_relative_path,
        report_sha256=report_sha,
        report=report,
    )

    wire_closure = {
        "articulation_roots": _copy_json_value(
            roots,
            "articulation_closure.articulation_roots",
        ),
        "dof_mapping": _copy_json_value(
            raw_dof_mapping,
            "articulation_closure.dof_mapping",
        ),
        "reset_values": _copy_json_value(
            raw_reset_values,
            "articulation_closure.reset_values",
        ),
    }
    wire_contract = {
        "schema_version": "scenario-forge-articulation-contract/v0.1",
        "asset_entry_prim": asset_entry_prim,
        "articulation_root_prim": articulation_root,
        "runtime_units": {
            "revolute": "radian",
            "prismatic": "meter",
        },
        "joints": wire_joints,
        "named_frames": _copy_json_mapping(
            named_frames,
            "articulation_contract.named_frames",
        ),
        "required_runtime_task_gates": list(required_runtime_task_gates),
        "closure": wire_closure,
    }
    return ConvertAssetArticulationContract(
        schema_version="scenario-forge-articulation-contract/v0.1",
        asset_entry_prim=asset_entry_prim,
        articulation_root_prim=articulation_root,
        dof_mapping=tuple(
            _copy_json_mapping(item, "articulation_closure.dof_mapping")
            for item in raw_dof_mapping
        ),
        reset_values=tuple(
            _copy_json_mapping(item, "articulation_closure.reset_values")
            for item in raw_reset_values
        ),
        semantic_joints={
            name: _copy_json_mapping(
                item,
                f"articulation_contract.semantic_joints.{name}",
            )
            for name, item in semantic_joints.items()
        },
        named_frames={
            name: _copy_json_mapping(
                item,
                f"articulation_contract.named_frames.{name}",
            )
            for name, item in named_frames.items()
        },
        mounting=mounting,
        profile_sha256=profile_sha,
        required_artifact_paths=(
            profile_relative_path,
            report_relative_path,
            promotion_relative_path,
        ),
        payload=wire_contract,
        closure_payload=_copy_json_mapping(
            closure,
            "articulation_closure",
        ),
    )


def _load_articulated_mounting(
    *,
    manifest_value: object,
    profile_value: object,
    report_value: object,
    asset_entry_prim: str,
    source_sha256: str,
    profile_sha256: str,
    runtime_report_sha256: str,
    required_runtime_task_gates: list[str],
    runtime_reset_by_dof: Mapping[int, float],
) -> Mapping[str, Any] | None:
    """Validate the producer-qualified fixed-base mounting ABI as one unit."""

    values = (manifest_value, profile_value, report_value)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ConvertAssetHandoffError(
            "articulation mounting must be present in the final manifest, "
            "packaged device profile, and runtime qualification report"
        )
    manifest_mounting = _mapping(
        manifest_value,
        "manifest.articulation_contract.mounting",
    )
    profile_mounting = _mapping(
        profile_value,
        "articulation_contract.device_profile.mounting",
    )
    report_mounting = _mapping(
        report_value,
        "articulation runtime report.qualified_consumer_placement",
    )
    candidate_fields = {
        "schema_version",
        "motion_mode",
        "asset_entry_prim",
        "coordinate_semantics",
        "support_frame_root_local",
        "support_plane_to_root_mount_pose",
        "initial_joint_reset_positions",
        "qualified_reset_geometry",
        "verification_required",
    }
    _require_exact_fields(
        profile_mounting,
        candidate_fields,
        "articulation_contract.device_profile.mounting",
    )
    _require_exact_fields(
        report_mounting,
        candidate_fields
        | {
            "status",
            "profile_sha256",
            "source_sha256",
        },
        "articulation runtime report.qualified_consumer_placement",
    )
    _require_exact_fields(
        manifest_mounting,
        candidate_fields
        | {
            "status",
            "profile_sha256",
            "runtime_report_sha256",
            "source_sha256",
        },
        "manifest.articulation_contract.mounting",
    )
    report_candidate = {
        key: report_mounting[key] for key in candidate_fields
    }
    manifest_candidate = {
        key: manifest_mounting[key] for key in candidate_fields
    }
    if profile_mounting != report_candidate:
        raise ConvertAssetHandoffError(
            "articulation mounting in the runtime report does not match the "
            "packaged device profile"
        )
    if profile_mounting != manifest_candidate:
        raise ConvertAssetHandoffError(
            "articulation mounting in the final manifest does not match the "
            "packaged device profile"
        )
    _require_value(
        report_mounting,
        "status",
        "pass",
        "articulation runtime report.qualified_consumer_placement",
    )
    _require_value(
        manifest_mounting,
        "status",
        "pass",
        "manifest.articulation_contract.mounting",
    )
    for value, field_name, expected in (
        (
            report_mounting,
            "articulation runtime report.qualified_consumer_placement",
            profile_sha256,
        ),
        (
            manifest_mounting,
            "manifest.articulation_contract.mounting",
            profile_sha256,
        ),
    ):
        if _required_sha256(value, "profile_sha256", field_name) != expected:
            raise ConvertAssetHandoffError(
                f"{field_name}.profile_sha256 does not match the packaged profile"
            )
    for value, field_name in (
        (
            report_mounting,
            "articulation runtime report.qualified_consumer_placement",
        ),
        (
            manifest_mounting,
            "manifest.articulation_contract.mounting",
        ),
    ):
        if (
            _required_sha256(value, "source_sha256", field_name)
            != source_sha256
        ):
            raise ConvertAssetHandoffError(
                f"{field_name}.source_sha256 does not match source USD"
            )
    if (
        _required_sha256(
            manifest_mounting,
            "runtime_report_sha256",
            "manifest.articulation_contract.mounting",
        )
        != runtime_report_sha256
    ):
        raise ConvertAssetHandoffError(
            "articulation mounting runtime_report_sha256 does not match the "
            "qualified runtime report"
        )

    _require_value(
        profile_mounting,
        "schema_version",
        "aan.articulated_mounting.v1",
        "articulation_contract.device_profile.mounting",
    )
    _require_value(
        profile_mounting,
        "motion_mode",
        "fixed_base",
        "articulation_contract.device_profile.mounting",
    )
    _require_value(
        profile_mounting,
        "asset_entry_prim",
        asset_entry_prim,
        "articulation_contract.device_profile.mounting",
    )
    semantics = _required_mapping(
        profile_mounting,
        "coordinate_semantics",
        "articulation_contract.device_profile.mounting",
    )
    expected_semantics = {
        "stage_up_axis": "Z",
        "linear_units": "meter",
        "quaternion_order": "wxyz",
        "support_frame": "runtime_articulation_root_pose_local",
        "mount_pose": (
            "support_plane_to_runtime_articulation_root_pose_world_axes_"
            "at_yaw_zero"
        ),
        "qualified_extents": (
            "world_axis_aligned_at_mount_pose_after_joint_reset"
        ),
    }
    _require_exact_fields(
        semantics,
        set(expected_semantics),
        "articulation mounting.coordinate_semantics",
    )
    if semantics != expected_semantics:
        raise ConvertAssetHandoffError(
            "articulation mounting.coordinate_semantics is unsupported"
        )
    support_translation, _ = _mounting_pose(
        profile_mounting.get("support_frame_root_local"),
        "articulation mounting.support_frame_root_local",
    )
    mount_translation, mount_rotation = _mounting_pose(
        profile_mounting.get("support_plane_to_root_mount_pose"),
        "articulation mounting.support_plane_to_root_mount_pose",
    )
    rotated_support = _rotate_vector_wxyz(
        support_translation,
        mount_rotation,
    )
    mounted_support = [
        translation + offset
        for translation, offset in zip(
            mount_translation,
            rotated_support,
            strict=True,
        )
    ]
    if any(abs(value) > 1e-6 for value in mounted_support):
        raise ConvertAssetHandoffError(
            "articulation mounting support frame and mount pose do not place "
            "the qualified support point on the support plane"
        )

    reset_positions = profile_mounting.get("initial_joint_reset_positions")
    if not isinstance(reset_positions, list) or not reset_positions:
        raise ConvertAssetHandoffError(
            "articulation mounting.initial_joint_reset_positions must be "
            "a non-empty list"
        )
    reset_by_dof: dict[int, float] = {}
    for index, raw_reset in enumerate(reset_positions):
        field = f"articulation mounting.initial_joint_reset_positions[{index}]"
        reset = _mapping(raw_reset, field)
        _require_exact_fields(reset, {"dof_index", "position"}, field)
        dof_index = reset.get("dof_index")
        if (
            not isinstance(dof_index, int)
            or isinstance(dof_index, bool)
            or dof_index < 0
            or dof_index in reset_by_dof
        ):
            raise ConvertAssetHandoffError(
                f"{field}.dof_index must be a unique non-negative integer"
            )
        reset_by_dof[dof_index] = _finite_number(
            reset.get("position"),
            f"{field}.position",
        )
    if set(reset_by_dof) != set(runtime_reset_by_dof):
        raise ConvertAssetHandoffError(
            "articulation mounting initial joint resets must cover every "
            "runtime DOF"
        )
    for dof_index, expected_reset in runtime_reset_by_dof.items():
        if not math.isclose(
            reset_by_dof[dof_index],
            expected_reset,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ConvertAssetHandoffError(
                "articulation mounting initial joint reset does not match "
                f"semantic runtime reset at DOF {dof_index}"
            )

    reset_geometry = _required_mapping(
        profile_mounting,
        "qualified_reset_geometry",
        "articulation_contract.device_profile.mounting",
    )
    _require_exact_fields(
        reset_geometry,
        {
            "warmup_frames",
            "warmup_extent_world_aabb_m",
            "settle_frames",
            "final_extent_world_aabb_m",
        },
        "articulation mounting.qualified_reset_geometry",
    )
    for field_name in ("warmup_frames", "settle_frames"):
        frames = reset_geometry.get(field_name)
        if (
            not isinstance(frames, int)
            or isinstance(frames, bool)
            or frames <= 0
        ):
            raise ConvertAssetHandoffError(
                "articulation mounting.qualified_reset_geometry."
                f"{field_name} must be a positive integer"
            )
    for field_name in (
        "warmup_extent_world_aabb_m",
        "final_extent_world_aabb_m",
    ):
        extent = _finite_number_list(
            reset_geometry.get(field_name),
            3,
            f"articulation mounting.qualified_reset_geometry.{field_name}",
        )
        if any(value <= 0.0 for value in extent):
            raise ConvertAssetHandoffError(
                "articulation mounting qualified extents must be positive"
            )
    verification_required = _required_string(
        profile_mounting,
        "verification_required",
        "articulation_contract.device_profile.mounting",
    )
    if (
        verification_required != "benchtop_stability"
        or verification_required not in required_runtime_task_gates
    ):
        raise ConvertAssetHandoffError(
            "articulation mounting requires a passed benchtop_stability gate"
        )
    return _copy_json_mapping(
        manifest_mounting,
        "manifest.articulation_contract.mounting",
    )


def _mounting_pose(
    value: object,
    field_name: str,
) -> tuple[list[float], list[float]]:
    pose = _mapping(value, field_name)
    _require_exact_fields(
        pose,
        {"translation_m", "rotation_wxyz"},
        field_name,
    )
    translation = _finite_number_list(
        pose.get("translation_m"),
        3,
        f"{field_name}.translation_m",
    )
    rotation = _finite_number_list(
        pose.get("rotation_wxyz"),
        4,
        f"{field_name}.rotation_wxyz",
    )
    if not math.isclose(
        sum(component * component for component in rotation),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ConvertAssetHandoffError(
            f"{field_name}.rotation_wxyz must be a unit quaternion"
        )
    return translation, rotation


def _rotate_vector_wxyz(
    vector: list[float],
    quaternion: list[float],
) -> list[float]:
    w, x, y, z = quaternion
    vx, vy, vz = vector
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return [
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    ]


def _validate_articulation_promotion(
    *,
    package_root: Path,
    manifest_sha256: str,
    asset_sha256: str,
    asset_entry_prim: str,
    runtime_profile: str,
    profile_relative_path: str,
    profile_sha256: str,
    report_relative_path: str,
    report_sha256: str,
    report: Mapping[str, Any],
) -> str:
    promotion_path = _safe_package_file(
        package_root,
        _ARTICULATION_PROMOTION_PATH,
        "articulation promotion path",
    )
    promotion = _load_strict_json_mapping(
        promotion_path.read_bytes(),
        "articulation package promotion",
    )
    _require_exact_fields(
        promotion,
        {
            "schema_version",
            "status",
            "prequalification_manifest_sha256",
            "final_manifest_sha256",
            "asset_usd_sha256",
            "profile_path",
            "profile_sha256",
            "runtime_report_path",
            "runtime_report_sha256",
            "claim_boundary",
        },
        "articulation package promotion",
    )
    _require_value(
        promotion,
        "schema_version",
        "aan.articulation_package_promotion.v1",
        "articulation package promotion",
    )
    _require_value(
        promotion,
        "status",
        "pass",
        "articulation package promotion",
    )
    prequalification_manifest_sha256 = _required_sha256(
        promotion,
        "prequalification_manifest_sha256",
        "articulation package promotion",
    )
    if _required_sha256(
        promotion,
        "final_manifest_sha256",
        "articulation package promotion",
    ) != manifest_sha256:
        raise ConvertAssetHandoffError(
            "articulation package promotion.final_manifest_sha256 does not match manifest"
        )
    if _required_sha256(
        promotion,
        "asset_usd_sha256",
        "articulation package promotion",
    ) != asset_sha256:
        raise ConvertAssetHandoffError(
            "articulation package promotion.asset_usd_sha256 does not match package asset"
        )
    _require_value(
        promotion,
        "profile_path",
        profile_relative_path,
        "articulation package promotion",
    )
    if _required_sha256(
        promotion,
        "profile_sha256",
        "articulation package promotion",
    ) != profile_sha256:
        raise ConvertAssetHandoffError(
            "articulation package promotion.profile_sha256 does not match contract"
        )
    _require_value(
        promotion,
        "runtime_report_path",
        report_relative_path,
        "articulation package promotion",
    )
    if _required_sha256(
        promotion,
        "runtime_report_sha256",
        "articulation package promotion",
    ) != report_sha256:
        raise ConvertAssetHandoffError(
            "articulation package promotion.runtime_report_sha256 does not match contract"
        )
    _required_string(promotion, "claim_boundary", "articulation package promotion")

    inputs = _required_mapping(
        report,
        "inputs",
        "articulation runtime qualification report",
    )
    integrity = _required_mapping(
        inputs,
        "integrity",
        "articulation runtime qualification report.inputs",
    )
    _require_value(
        integrity,
        "status",
        "pass",
        "articulation runtime qualification report.inputs.integrity",
    )
    qualified_package = _required_mapping(
        inputs,
        "qualified_package",
        "articulation runtime qualification report.inputs",
    )
    _require_exact_fields(
        qualified_package,
        {
            "asset_path",
            "asset_entry_prim",
            "runtime_profile",
            "prequalification_manifest_sha256",
            "asset_usd_sha256_before",
            "asset_usd_sha256_after",
        },
        "articulation runtime qualification report.inputs.qualified_package",
    )
    _require_value(
        qualified_package,
        "asset_path",
        "asset.usd",
        "articulation runtime qualified package",
    )
    _require_value(
        qualified_package,
        "asset_entry_prim",
        asset_entry_prim,
        "articulation runtime qualified package",
    )
    _require_value(
        qualified_package,
        "runtime_profile",
        runtime_profile,
        "articulation runtime qualified package",
    )
    if _required_sha256(
        qualified_package,
        "prequalification_manifest_sha256",
        "articulation runtime qualified package",
    ) != prequalification_manifest_sha256:
        raise ConvertAssetHandoffError(
            "articulation runtime report is not bound to the prequalification manifest"
        )
    if (
        _required_sha256(
            qualified_package,
            "asset_usd_sha256_before",
            "articulation runtime qualified package",
        )
        != asset_sha256
        or _required_sha256(
            qualified_package,
            "asset_usd_sha256_after",
            "articulation runtime qualified package",
        )
        != asset_sha256
    ):
        raise ConvertAssetHandoffError(
            "articulation runtime report does not bind an unchanged package asset"
        )
    runtime = _required_mapping(
        report,
        "runtime",
        "articulation runtime qualification report",
    )
    _require_value(
        runtime,
        "runtime_profile",
        runtime_profile,
        "articulation runtime qualification report.runtime",
    )
    drive_integrity = _required_mapping(
        report,
        "drive_integrity",
        "articulation runtime qualification report",
    )
    _require_value(
        drive_integrity,
        "status",
        "pass",
        "articulation runtime qualification report.drive_integrity",
    )
    return _ARTICULATION_PROMOTION_PATH


def _load_interaction_contract(
    value: object,
    *,
    package_root: Path,
    source_sha256: str,
    asset_entry_prim: str,
    required: bool,
) -> ConvertAssetInteractionContract | None:
    if value is None:
        if required:
            raise ConvertAssetHandoffError(
                "rigid_object usage requires manifest.interaction_contract"
            )
        return None
    contract = _mapping(value, "manifest.interaction_contract")
    status = contract.get("status")
    sentinel_fields = {
        "schema_version",
        "status",
    }
    if status == "not_run":
        sentinel_fields.add("reason")
    if (
        contract.get("schema_version") == "aan.interaction_contract.v1"
        and status in {"not_requested", "not_run"}
        and set(contract) == sentinel_fields
    ):
        if required:
            raise ConvertAssetHandoffError(
                "rigid_object usage requires a passing manifest.interaction_contract"
            )
        return None
    contract_fields = {
        "schema_version",
        "status",
        "profile",
        "asset_entry_prim",
        "runtime_identity",
        "disabled_source_rigid_bodies",
        "collider_prims",
        "open_top",
        "named_frames",
        "closure",
        "root_motion_gate",
        "stable_support_gate",
        "gripper_collision_gate",
    }
    if "interaction_regions" in contract:
        contract_fields.add("interaction_regions")
    _require_exact_fields(
        contract,
        contract_fields,
        "manifest.interaction_contract",
    )
    _require_value(
        contract,
        "schema_version",
        "aan.interaction_contract.v1",
        "manifest.interaction_contract",
    )
    _require_value(contract, "status", "pass", "manifest.interaction_contract")

    profile = _required_mapping(contract, "profile", "manifest.interaction_contract")
    _require_exact_fields(
        profile,
        {
            "schema_version",
            "profile_id",
            "revision",
            "source_sha256",
            "profile_sha256",
            "package_path",
            "overlay_path",
        },
        "interaction_contract.profile",
    )
    profile_schema_version = _required_string(
        profile,
        "schema_version",
        "interaction_contract.profile",
    )
    if profile_schema_version not in {
        "aan.object_interaction_profile.v1",
        "aan.object_interaction_profile.v2",
    }:
        raise ConvertAssetHandoffError(
            "interaction_contract.profile.schema_version must be "
            "'aan.object_interaction_profile.v1' or "
            "'aan.object_interaction_profile.v2'"
        )
    _required_string(profile, "profile_id", "interaction_contract.profile")
    _required_string(profile, "revision", "interaction_contract.profile")
    if _required_sha256(profile, "source_sha256", "interaction_contract.profile") != source_sha256:
        raise ConvertAssetHandoffError(
            "interaction_contract.profile.source_sha256 does not match source USD"
        )
    profile_path = _safe_package_file(
        package_root,
        _required_string(profile, "package_path", "interaction_contract.profile"),
        "interaction_contract.profile.package_path",
    )
    profile_sha = _required_sha256(
        profile,
        "profile_sha256",
        "interaction_contract.profile",
    )
    if _file_sha256(profile_path) != profile_sha:
        raise ConvertAssetHandoffError(
            "interaction_contract.profile.profile_sha256 does not match packaged profile"
        )
    _safe_package_file(
        package_root,
        _required_string(profile, "overlay_path", "interaction_contract.profile"),
        "interaction_contract.profile.overlay_path",
    )

    contract_entry = _required_string(
        contract,
        "asset_entry_prim",
        "manifest.interaction_contract",
    )
    if contract_entry != asset_entry_prim:
        raise ConvertAssetHandoffError(
            "interaction_contract.asset_entry_prim must match manifest asset_entry_prim"
        )
    runtime_identity = _required_mapping(
        contract,
        "runtime_identity",
        "manifest.interaction_contract",
    )
    _require_exact_fields(
        runtime_identity,
        {
            "rigid_root_prim",
            "exactly_one_active_rigid_body",
            "active_rigid_body_prims",
        },
        "interaction_contract.runtime_identity",
    )
    rigid_root = _required_string(
        runtime_identity,
        "rigid_root_prim",
        "interaction_contract.runtime_identity",
    )
    if contract_entry != rigid_root:
        raise ConvertAssetHandoffError(
            "interaction_contract.asset_entry_prim must equal rigid_root_prim"
        )
    _require_value(
        runtime_identity,
        "exactly_one_active_rigid_body",
        True,
        "interaction_contract.runtime_identity",
    )
    active_rigid_bodies = _required_string_tuple(
        runtime_identity,
        "active_rigid_body_prims",
        "interaction_contract.runtime_identity",
    )
    if active_rigid_bodies != (rigid_root,):
        raise ConvertAssetHandoffError(
            "interaction_contract.runtime_identity must contain exactly one "
            "active_rigid_body_prims entry equal to rigid_root_prim"
        )

    disabled = _required_mapping_list(
        contract.get("disabled_source_rigid_bodies"),
        "interaction_contract.disabled_source_rigid_bodies",
    )
    seen_disabled: set[str] = set()
    for index, item in enumerate(disabled):
        field = f"interaction_contract.disabled_source_rigid_bodies[{index}]"
        _require_exact_fields(
            item,
            {
                "prim_path",
                "rigid_body_api_removed",
                "rigid_body_disabled",
                "mass_api_removed",
            },
            field,
        )
        prim_path = _required_string(item, "prim_path", field)
        _require_descendant_prim(prim_path, rigid_root, field, allow_root=False)
        if prim_path in seen_disabled:
            raise ConvertAssetHandoffError(f"{field}.prim_path must be unique")
        seen_disabled.add(prim_path)
        for key in ("rigid_body_api_removed", "rigid_body_disabled"):
            _require_value(item, key, True, field)
        _required_bool(item, "mass_api_removed", field)

    colliders = _required_mapping_list(
        contract.get("collider_prims"),
        "interaction_contract.collider_prims",
    )
    if not colliders:
        raise ConvertAssetHandoffError(
            "interaction_contract.collider_prims must not be empty"
        )
    collider_paths: list[str] = []
    for index, item in enumerate(colliders):
        field = f"interaction_contract.collider_prims[{index}]"
        _require_exact_fields(
            item,
            {
                "prim_path",
                "mode",
                "collision_enabled",
                "purpose",
                "requested_approximation",
                "observed_approximation",
            },
            field,
        )
        prim_path = _required_string(item, "prim_path", field)
        _require_descendant_prim(prim_path, rigid_root, field, allow_root=True)
        if prim_path in collider_paths:
            raise ConvertAssetHandoffError(f"{field}.prim_path must be unique")
        collider_paths.append(prim_path)
        mode = _required_string(item, "mode", field)
        if mode not in {"preserve", "author", "disable"}:
            raise ConvertAssetHandoffError(
                f"{field}.mode must be 'preserve', 'author', or 'disable'"
            )
        collision_enabled = _required_bool(item, "collision_enabled", field)
        if collision_enabled != (mode != "disable"):
            raise ConvertAssetHandoffError(
                f"{field}.collision_enabled must be false only when mode is 'disable'"
            )
        _string_list(item.get("purpose"), f"{field}.purpose")
        for key in ("requested_approximation", "observed_approximation"):
            approximation = item.get(key)
            if approximation is not None and (
                not isinstance(approximation, str) or not approximation
            ):
                raise ConvertAssetHandoffError(
                    f"{field}.{key} must be null or a non-empty string"
                )

    frames = _mapping(contract.get("named_frames"), "interaction_contract.named_frames")
    if not frames:
        raise ConvertAssetHandoffError(
            "interaction_contract.named_frames must not be empty"
        )
    normalized_frames: dict[str, Mapping[str, Any]] = {}
    for frame_name, raw_frame in frames.items():
        if not isinstance(frame_name, str) or not frame_name or "." in frame_name:
            raise ConvertAssetHandoffError(
                "interaction_contract.named_frames keys must be non-empty and contain no '.'"
            )
        field = f"interaction_contract.named_frames.{frame_name}"
        frame = _mapping(raw_frame, field)
        _require_exact_fields(
            frame,
            {
                "prim_path",
                "parent_prim",
                "translation_body_local_usd",
                "rotation_body_local_wxyz",
                "authoritative",
            },
            field,
        )
        _require_descendant_prim(
            _required_string(frame, "prim_path", field),
            rigid_root,
            field,
            allow_root=False,
        )
        _require_value(frame, "parent_prim", rigid_root, field)
        _finite_number_list(frame.get("translation_body_local_usd"), 3, f"{field}.translation_body_local_usd")
        rotation = _finite_number_list(
            frame.get("rotation_body_local_wxyz"),
            4,
            f"{field}.rotation_body_local_wxyz",
        )
        norm_squared = sum(component * component for component in rotation)
        if not math.isclose(norm_squared, 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ConvertAssetHandoffError(
                f"{field}.rotation_body_local_wxyz must be a unit quaternion"
            )
        _require_value(frame, "authoritative", True, field)
        normalized_frames[frame_name] = frame

    normalized_regions: dict[str, Mapping[str, Any]] = {}
    if "interaction_regions" in contract:
        if profile_schema_version != "aan.object_interaction_profile.v2":
            raise ConvertAssetHandoffError(
                "interaction_contract.interaction_regions requires profile v2"
            )
        regions = _mapping(
            contract.get("interaction_regions"),
            "interaction_contract.interaction_regions",
        )
        if not regions:
            raise ConvertAssetHandoffError(
                "interaction_contract.interaction_regions must not be empty"
            )
        for region_name, raw_region in regions.items():
            if (
                not isinstance(region_name, str)
                or not region_name
                or "." in region_name
                or "/" in region_name
            ):
                raise ConvertAssetHandoffError(
                    "interaction_contract.interaction_regions keys must be path-safe"
                )
            field = f"interaction_contract.interaction_regions.{region_name}"
            region = _mapping(raw_region, field)
            _require_exact_fields(
                region,
                {
                    "shape",
                    "frame",
                    "axis_frame_local",
                    "radius_body_local_usd",
                    "half_height_body_local_usd",
                    "purpose",
                    "authoritative",
                },
                field,
            )
            _require_value(region, "shape", "cylinder", field)
            frame_name = _required_string(region, "frame", field)
            if frame_name not in normalized_frames:
                raise ConvertAssetHandoffError(
                    f"{field}.frame must name an authoritative named frame"
                )
            axis = _finite_number_list(
                region.get("axis_frame_local"), 3, f"{field}.axis_frame_local"
            )
            if not math.isclose(
                sum(component * component for component in axis),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise ConvertAssetHandoffError(
                    f"{field}.axis_frame_local must be a unit vector"
                )
            for size_field in (
                "radius_body_local_usd",
                "half_height_body_local_usd",
            ):
                if _finite_number(region.get(size_field), f"{field}.{size_field}") <= 0:
                    raise ConvertAssetHandoffError(
                        f"{field}.{size_field} must be positive"
                    )
            purpose = _string_list(region.get("purpose"), f"{field}.purpose")
            if (
                not purpose
                or len(purpose) != len(set(purpose))
                or not set(purpose).issubset({"containment", "tool_motion"})
            ):
                raise ConvertAssetHandoffError(
                    f"{field}.purpose is not a supported unique non-empty set"
                )
            _require_value(region, "authoritative", True, field)
            normalized_regions[region_name] = region

    open_top = _required_mapping(contract, "open_top", "manifest.interaction_contract")
    _require_exact_fields(
        open_top,
        {"required", "axis_body_local", "aperture_frame", "status", "evidence"},
        "interaction_contract.open_top",
    )
    open_top_required = _required_bool(open_top, "required", "interaction_contract.open_top")
    axis_value = open_top.get("axis_body_local")
    if open_top_required or axis_value is not None:
        axis = _finite_number_list(
            axis_value,
            3,
            "interaction_contract.open_top.axis_body_local",
        )
        if sum(component * component for component in axis) == 0.0:
            raise ConvertAssetHandoffError(
                "interaction_contract.open_top.axis_body_local must be non-zero"
            )
    aperture_frame = open_top.get("aperture_frame")
    if open_top_required or aperture_frame is not None:
        if not isinstance(aperture_frame, str) or not aperture_frame:
            raise ConvertAssetHandoffError(
                "interaction_contract.open_top.aperture_frame must be a "
                "non-empty string"
            )
        if aperture_frame not in normalized_frames:
            raise ConvertAssetHandoffError(
                "interaction_contract.open_top.aperture_frame must name an "
                "authoritative frame"
            )
    open_top_status = _required_string(
        open_top,
        "status",
        "interaction_contract.open_top",
    )
    _require_json_evidence(open_top.get("evidence"), "interaction_contract.open_top.evidence")
    qualification_report_paths: set[str] = set()
    if open_top_status == "pass":
        qualification_report_paths.add(
            _verify_qualification_evidence(
                open_top.get("evidence"),
                package_root=package_root,
                field_name="interaction_contract.open_top.evidence",
            )
        )

    closure = _required_mapping(contract, "closure", "manifest.interaction_contract")
    _validate_interaction_closure(contract, closure, package_root)

    gate_statuses: dict[str, tuple[bool, str]] = {}
    for gate_name in (
        "root_motion_gate",
        "stable_support_gate",
        "gripper_collision_gate",
    ):
        gate = _required_mapping(contract, gate_name, "manifest.interaction_contract")
        expected_fields = {"status", "required", "evidence"}
        if gate_name == "root_motion_gate":
            expected_fields.add("min_translation_m")
        _require_exact_fields(gate, expected_fields, f"interaction_contract.{gate_name}")
        gate_required = _required_bool(gate, "required", f"interaction_contract.{gate_name}")
        gate_status = _required_string(gate, "status", f"interaction_contract.{gate_name}")
        _require_json_evidence(gate.get("evidence"), f"interaction_contract.{gate_name}.evidence")
        if gate_status == "pass":
            qualification_report_paths.add(
                _verify_qualification_evidence(
                    gate.get("evidence"),
                    package_root=package_root,
                    field_name=f"interaction_contract.{gate_name}.evidence",
                    claim_boundary_required=gate_name == "gripper_collision_gate",
                )
            )
        if gate_name == "root_motion_gate":
            minimum = _finite_number(
                gate.get("min_translation_m"),
                "interaction_contract.root_motion_gate.min_translation_m",
            )
            if gate_required and minimum <= 0.0:
                raise ConvertAssetHandoffError(
                    "interaction_contract.root_motion_gate.min_translation_m must be positive"
                )
        gate_statuses[gate_name] = (gate_required, gate_status)

    not_ready = [
        name
        for name, (gate_required, status) in gate_statuses.items()
        if gate_required and status != "pass"
    ]
    if open_top_required and open_top_status != "pass":
        not_ready.append("open_top")
    task_ready = not not_ready
    if required and not task_ready:
        raise ConvertAssetHandoffError(
            "interaction_contract is not task-ready; required runtime gate(s) "
            "did not pass: " + ", ".join(not_ready)
        )

    closure_payload = _required_mapping(
        contract,
        "closure",
        "manifest.interaction_contract",
    )
    return ConvertAssetInteractionContract(
        schema_version="aan.interaction_contract.v1",
        asset_entry_prim=contract_entry,
        rigid_root_prim=rigid_root,
        active_rigid_body_prims=active_rigid_bodies,
        collider_prims=tuple(collider_paths),
        named_frames=normalized_frames,
        interaction_regions=normalized_regions,
        contract_payload_sha256=_required_string(
            closure_payload,
            "contract_payload_sha256",
            "interaction_contract.closure",
        ),
        runtime_tree_sha256=_required_string(
            closure_payload,
            "runtime_tree_sha256",
            "interaction_contract.closure",
        ),
        qualification_report_paths=tuple(sorted(qualification_report_paths)),
        task_ready=task_ready,
        payload=_copy_json_mapping(contract, "interaction_contract"),
    )


def _validate_interaction_closure(
    contract: Mapping[str, Any],
    closure: Mapping[str, Any],
    package_root: Path,
) -> None:
    _require_exact_fields(
        closure,
        {
            "status",
            "digest_algorithm",
            "contract_encoding",
            "contract_payload_sha256",
            "tree_encoding",
            "runtime_tree_sha256",
            "artifacts",
        },
        "interaction_contract.closure",
    )
    _require_value(closure, "status", "pass", "interaction_contract.closure")
    _require_value(
        closure,
        "digest_algorithm",
        "sha256",
        "interaction_contract.closure",
    )
    _require_value(
        closure,
        "contract_encoding",
        "canonical_json_interaction_payload_v1",
        "interaction_contract.closure",
    )
    _require_value(
        closure,
        "tree_encoding",
        "canonical_json_artifact_list_v1",
        "interaction_contract.closure",
    )
    expected_payload = {
        key: contract[key]
        for key in (
            "schema_version",
            "asset_entry_prim",
            "runtime_identity",
            "disabled_source_rigid_bodies",
            "collider_prims",
            "open_top",
            "named_frames",
        )
    }
    if "interaction_regions" in contract:
        expected_payload["interaction_regions"] = contract["interaction_regions"]
    expected_payload_sha = _canonical_json_sha256(expected_payload)
    if _required_sha256(
        closure,
        "contract_payload_sha256",
        "interaction_contract.closure",
    ) != expected_payload_sha:
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.contract_payload_sha256 mismatch"
        )

    raw_artifacts = _required_mapping_list(
        closure.get("artifacts"),
        "interaction_contract.closure.artifacts",
    )
    if not raw_artifacts:
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.artifacts must not be empty"
        )
    artifacts: list[dict[str, str]] = []
    for index, item in enumerate(raw_artifacts):
        field = f"interaction_contract.closure.artifacts[{index}]"
        _require_exact_fields(item, {"path", "sha256"}, field)
        relative_path = _required_string(item, "path", field)
        artifact_path = _safe_package_file(package_root, relative_path, f"{field}.path")
        artifact_sha = _required_sha256(item, "sha256", field)
        if _file_sha256(artifact_path) != artifact_sha:
            raise ConvertAssetHandoffError(f"{field}.sha256 does not match artifact")
        artifacts.append({"path": relative_path, "sha256": artifact_sha})
    if artifacts != sorted(artifacts, key=lambda item: item["path"]):
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.artifacts must be sorted by path"
        )
    if len({item["path"] for item in artifacts}) != len(artifacts):
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.artifacts paths must be unique"
        )
    expected_paths = _runtime_closure_paths(package_root)
    actual_paths = [item["path"] for item in artifacts]
    if actual_paths != expected_paths:
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.artifacts must cover the complete runtime tree"
        )
    expected_tree_sha = _canonical_json_sha256(artifacts)
    if _required_sha256(
        closure,
        "runtime_tree_sha256",
        "interaction_contract.closure",
    ) != expected_tree_sha:
        raise ConvertAssetHandoffError(
            "interaction_contract.closure.runtime_tree_sha256 mismatch"
        )


def _runtime_closure_paths(package_root: Path) -> list[str]:
    roots = {"deps", "overlays", "interaction", "physics"}
    paths = []
    for path in package_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        if relative == "asset.usd" or relative.split("/", 1)[0] in roots:
            paths.append(relative)
    return sorted(paths)


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConvertAssetHandoffError(f"{field_name} must be a mapping")
    return value


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _load_strict_json_mapping(value: bytes, field_name: str) -> Mapping[str, Any]:
    try:
        decoded = json.loads(
            value.decode("utf-8"),
            parse_constant=_reject_nonstandard_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ConvertAssetHandoffError(f"{field_name} is not valid JSON") from exc
    return _mapping(decoded, field_name)


def _required_mapping(
    data: Mapping[str, Any], key: str, field_name: str
) -> Mapping[str, Any]:
    return _mapping(data.get(key), f"{field_name}.{key}")


def _required_string(data: Mapping[str, Any], key: str, field_name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConvertAssetHandoffError(
            f"{field_name}.{key} must be a non-empty string"
        )
    return value


def _required_string_tuple(
    data: Mapping[str, Any], key: str, field_name: str
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ConvertAssetHandoffError(
            f"{field_name}.{key} must be a list of non-empty strings"
        )
    return tuple(value)


def _required_mapping_list(value: object, field_name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ConvertAssetHandoffError(f"{field_name} must be a list")
    return [
        _mapping(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    ]


def _required_bool(
    data: Mapping[str, Any], key: str, field_name: str
) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ConvertAssetHandoffError(f"{field_name}.{key} must be a boolean")
    return value


def _required_sha256(
    data: Mapping[str, Any], key: str, field_name: str
) -> str:
    value = _required_string(data, key, field_name)
    if _SHA256_HEX.fullmatch(value) is None:
        raise ConvertAssetHandoffError(
            f"{field_name}.{key} must be a lowercase SHA-256 digest"
        )
    return value


def _require_exact_fields(
    data: Mapping[str, Any], expected: set[str], field_name: str
) -> None:
    actual = set(data)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        raise ConvertAssetHandoffError(
            f"{field_name} is missing field(s): {', '.join(missing)}"
        )
    if unexpected:
        raise ConvertAssetHandoffError(
            f"{field_name} contains unexpected field(s): {', '.join(unexpected)}"
        )


def _require_descendant_prim(
    prim_path: str,
    root_prim: str,
    field_name: str,
    *,
    allow_root: bool,
) -> None:
    if not prim_path.startswith("/") or "//" in prim_path:
        raise ConvertAssetHandoffError(f"{field_name} must use an absolute USD prim path")
    if prim_path == root_prim:
        if allow_root:
            return
        raise ConvertAssetHandoffError(f"{field_name} must be below rigid_root_prim")
    if not prim_path.startswith(root_prim + "/"):
        raise ConvertAssetHandoffError(f"{field_name} must be below rigid_root_prim")


def _require_prim_within(
    prim_path: str,
    root_prim: str,
    field_name: str,
    *,
    allow_root: bool,
) -> None:
    if not prim_path.startswith("/") or "//" in prim_path:
        raise ConvertAssetHandoffError(
            f"{field_name} must use an absolute USD prim path"
        )
    if prim_path == root_prim:
        if allow_root:
            return
        raise ConvertAssetHandoffError(f"{field_name} must be below {root_prim}")
    if not prim_path.startswith(root_prim + "/"):
        raise ConvertAssetHandoffError(
            f"{field_name} must be within {root_prim}"
        )


def _finite_number(value: object, field_name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ConvertAssetHandoffError(f"{field_name} must be a finite number")
    return float(value)


def _finite_number_list(value: object, length: int, field_name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ConvertAssetHandoffError(
            f"{field_name} must contain {length} finite numbers"
        )
    return [_finite_number(item, field_name) for item in value]


def _string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ConvertAssetHandoffError(
            f"{field_name} must be a list of non-empty strings"
        )
    if len(set(value)) != len(value):
        raise ConvertAssetHandoffError(f"{field_name} entries must be unique")
    return list(value)


def _require_json_evidence(value: object, field_name: str) -> None:
    if value is None:
        raise ConvertAssetHandoffError(f"{field_name} must be present")
    _copy_json_value(value, field_name)


def _verify_qualification_evidence(
    value: object,
    *,
    package_root: Path,
    field_name: str,
    claim_boundary_required: bool = False,
) -> str:
    evidence = _mapping(value, field_name)
    expected_fields = {
        "status",
        "probe_id",
        "report_path",
        "report_sha256",
        "observations",
        "errors",
        "prequalification_contract_payload_sha256",
    }
    if claim_boundary_required:
        expected_fields.add("claim_boundary")
    _require_exact_fields(evidence, expected_fields, field_name)
    _require_value(evidence, "status", "pass", field_name)
    _required_string(evidence, "probe_id", field_name)
    report_relative_path = _required_string(evidence, "report_path", field_name)
    report_path = _safe_package_file(
        package_root,
        report_relative_path,
        f"{field_name}.report_path",
    )
    report_sha256 = _required_sha256(evidence, "report_sha256", field_name)
    if _file_sha256(report_path) != report_sha256:
        raise ConvertAssetHandoffError(
            f"{field_name}.report_sha256 does not match qualification report"
        )
    observations = evidence.get("observations")
    if not isinstance(observations, list):
        raise ConvertAssetHandoffError(f"{field_name}.observations must be a list")
    _copy_json_value(observations, f"{field_name}.observations")
    if evidence.get("errors") != []:
        raise ConvertAssetHandoffError(f"{field_name}.errors must be empty for pass")
    _required_sha256(
        evidence,
        "prequalification_contract_payload_sha256",
        field_name,
    )
    if claim_boundary_required:
        _required_string(evidence, "claim_boundary", field_name)
    return report_relative_path


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _copy_json_mapping(
    value: Mapping[str, Any], field_name: str
) -> dict[str, Any]:
    return {
        str(key): _copy_json_value(item, f"{field_name}.{key}")
        for key, item in value.items()
    }


def _copy_json_value(value: object, field_name: str) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list) or isinstance(value, tuple):
        return [_copy_json_value(item, field_name) for item in value]
    if isinstance(value, Mapping):
        return _copy_json_mapping(value, field_name)
    raise ConvertAssetHandoffError(
        f"{field_name} must contain JSON-compatible values"
    )


def _require_value(
    data: Mapping[str, Any],
    key: str,
    expected: object,
    field_name: str,
) -> None:
    if data.get(key) != expected:
        raise ConvertAssetHandoffError(
            f"{field_name}.{key} must be {expected!r}"
        )


def _validated_scope_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if len(set(value)) != len(value) or not all(
        isinstance(item, str) and item.startswith("/") and "//" not in item
        for item in value
    ):
        raise ConvertAssetHandoffError(
            f"{field_name} must contain unique absolute USD prim paths"
        )
    return value


def _require_scopes(
    data: Mapping[str, Any],
    key: str,
    expected: tuple[str, ...],
    field_name: str,
) -> None:
    value = data.get(key)
    if not isinstance(value, list) or tuple(value) != expected:
        raise ConvertAssetHandoffError(
            f"{field_name}.{key} must exactly match expected scope prims"
        )


def _safe_package_file(package_root: Path, value: str, field_name: str) -> Path:
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.as_posix() != value
    ):
        raise ConvertAssetHandoffError(
            f"{field_name} must be a safe package-relative path"
        )
    root = package_root.resolve()
    candidate = (root / Path(*relative.parts)).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise ConvertAssetHandoffError(
            f"{field_name} escapes the package or is missing: {value}"
        )
    return candidate


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_retained_scope(
    manifest: Mapping[str, Any], expected_scopes: tuple[str, ...]
) -> None:
    dependency = _required_mapping(manifest, "dependency_closure", "manifest")
    extraction = _required_mapping(
        dependency,
        "scope_extraction",
        "manifest.dependency_closure",
    )
    _require_value(extraction, "status", "pass", "scope_extraction")
    retained = _required_string_tuple(
        extraction,
        "retained_subtree_prims",
        "scope_extraction",
    )
    materials = set(
        _required_string_tuple(
            extraction,
            "retained_material_prims",
            "scope_extraction",
        )
    )
    unexpected = [
        prim
        for prim in retained
        if prim not in materials
        and not any(prim == scope or prim.startswith(scope + "/") for scope in expected_scopes)
    ]
    if unexpected:
        raise ConvertAssetHandoffError(
            "scope_extraction.retained_subtree_prims contains undeclared scene prims: "
            + ", ".join(unexpected)
        )


def _validate_visual_static_admission(
    manifest: Mapping[str, Any], expected_scopes: tuple[str, ...]
) -> None:
    admission = _required_mapping(manifest, "output_role_admission", "manifest")
    _require_value(admission, "status", "pass", "output_role_admission")
    _require_scopes(admission, "scope", expected_scopes, "output_role_admission")
    if admission.get("residue") != []:
        raise ConvertAssetHandoffError(
            "output_role_admission.residue must be empty"
        )
    summary = _required_mapping(
        admission,
        "summary",
        "output_role_admission",
    )
    for count_name in (
        "active_articulation_root_count",
        "active_collision_count",
        "active_joint_count",
        "active_rigid_body_count",
    ):
        if summary.get(count_name) != 0:
            raise ConvertAssetHandoffError(
                f"output_role_admission.summary.{count_name} must be 0"
            )
    fingerprint = _required_mapping(
        manifest,
        "visual_preservation_fingerprint",
        "manifest",
    )
    _require_value(
        fingerprint,
        "status",
        "pass",
        "visual_preservation_fingerprint",
    )


def _validate_visual_static_physical_frame(
    physics: Mapping[str, Any], expected_scopes: tuple[str, ...]
) -> None:
    """Require the producer to preserve the source's composed spatial frame."""

    frame = _required_mapping(
        physics,
        "physical_frame",
        "manifest.physics_closure",
    )
    _require_value(frame, "status", "pass", "physics_closure.physical_frame")
    source_frame = _required_mapping(
        frame,
        "source",
        "physics_closure.physical_frame",
    )
    package_frame = _required_mapping(
        frame,
        "package",
        "physics_closure.physical_frame",
    )
    for field_name in (
        "meters_per_unit",
        "kilograms_per_unit",
        "up_axis",
        "time_codes_per_second",
        "frames_per_second",
        "start_time_code",
        "end_time_code",
    ):
        if source_frame.get(field_name) != package_frame.get(field_name):
            raise ConvertAssetHandoffError(
                "physics_closure.physical_frame "
                f"{field_name} must match between source and package"
            )
    if frame.get("metric_mismatches") != []:
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.metric_mismatches must be empty"
        )
    if frame.get("blocked_scope_prims") != []:
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.blocked_scope_prims must be empty"
        )
    raw_scope_bounds = frame.get("scope_bounds")
    if not isinstance(raw_scope_bounds, list):
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.scope_bounds must be a list"
        )
    bounds_by_path: dict[str, Mapping[str, Any]] = {}
    for raw_bound in raw_scope_bounds:
        bound = _mapping(raw_bound, "physics_closure.physical_frame.scope_bounds")
        path = _required_string(
            bound,
            "path",
            "physics_closure.physical_frame.scope_bounds",
        )
        if path in bounds_by_path:
            raise ConvertAssetHandoffError(
                "physics_closure.physical_frame.scope_bounds must not repeat paths"
            )
        bounds_by_path[path] = bound
    if set(bounds_by_path) != set(expected_scopes):
        raise ConvertAssetHandoffError(
            "physics_closure.physical_frame.scope_bounds must match expected scopes"
        )
    for path in expected_scopes:
        bound = bounds_by_path[path]
        _require_value(
            bound,
            "status",
            "pass",
            f"physics_closure.physical_frame.scope_bounds[{path}]",
        )
        source_bounds = _required_mapping(
            bound,
            "source_world_bound_m",
            f"physics_closure.physical_frame.scope_bounds[{path}]",
        )
        package_bounds = _required_mapping(
            bound,
            "package_world_bound_m",
            f"physics_closure.physical_frame.scope_bounds[{path}]",
        )
        if source_bounds != package_bounds:
            raise ConvertAssetHandoffError(
                "physics_closure.physical_frame source and package bounds must match"
            )


def _validate_stage_metrics(
    manifest: Mapping[str, Any], source_binding: Mapping[str, Any]
) -> None:
    dependency = _required_mapping(manifest, "dependency_closure", "manifest")
    extraction = _required_mapping(
        dependency,
        "scope_extraction",
        "manifest.dependency_closure",
    )
    preserved = _required_mapping(
        extraction,
        "preserved_stage_metadata",
        "scope_extraction",
    )
    bound = _required_mapping(
        source_binding,
        "stage_metrics",
        "profile_admission.source_binding",
    )
    required_fields = {
        "meters_per_unit",
        "kilograms_per_unit",
        "up_axis",
        "time_codes_per_second",
        "frames_per_second",
    }
    if any(field not in bound for field in required_fields) or any(
        field not in preserved for field in required_fields
    ):
        raise ConvertAssetHandoffError(
            "source-bound stage metrics are incomplete"
        )
    if any(bound[field] != preserved[field] for field in required_fields):
        raise ConvertAssetHandoffError(
            "source-bound and preserved stage metrics do not match"
        )


def load_gpu_pbd_static_container_handoff(
    package_dir: str | Path,
    manifest_path: str | Path,
) -> ConvertAssetGPUPBDStaticContainerHandoff:
    """Fail closed on the narrow ConvertAsset GPU-PBD container claim."""

    package = Path(package_dir).resolve()
    external_manifest = Path(manifest_path).resolve()
    embedded_manifest = package / "evidence" / "manifest.json"
    if not package.is_dir() or not embedded_manifest.is_file():
        raise ConvertAssetHandoffError("GPU-PBD container package is incomplete")
    if not external_manifest.is_file():
        raise ConvertAssetHandoffError("GPU-PBD container manifest is missing")
    if external_manifest.read_bytes() != embedded_manifest.read_bytes():
        raise ConvertAssetHandoffError(
            "external and embedded GPU-PBD manifests do not match"
        )
    manifest = _load_strict_json_mapping(
        embedded_manifest.read_bytes(), "GPU-PBD container manifest"
    )
    _require_value(
        manifest,
        "schema_version",
        "aan.source_bound_package_manifest.v1",
        "manifest",
    )
    _require_value(manifest, "overall_status", "pass", "manifest")
    promotion = _required_mapping(manifest, "promotion", "manifest")
    if promotion.get("allowed") is not True:
        raise ConvertAssetHandoffError("GPU-PBD container promotion is not allowed")
    _require_value(
        promotion,
        "claim",
        "gpu_pbd_static_container",
        "manifest.promotion",
    )
    package_id = _required_string(manifest, "package_id", "manifest")
    entrypoints = _required_mapping(manifest, "entrypoints", "manifest")
    root_usd = _safe_package_file(
        package,
        _required_string(entrypoints, "root_usd", "manifest.entrypoints"),
        "root_usd",
    )
    entry_prim = _required_string(
        entrypoints, "asset_entry_prim", "manifest.entrypoints"
    )
    if not entry_prim.startswith("/"):
        raise ConvertAssetHandoffError("asset_entry_prim must be absolute")

    contract = _required_mapping(
        manifest, "gpu_pbd_static_container", "manifest"
    )
    _require_value(contract, "status", "qualified", "gpu_pbd_static_container")
    profile_path = _safe_package_file(
        package,
        _required_string(contract, "profile", "gpu_pbd_static_container"),
        "profile",
    )
    profile = _load_strict_json_mapping(
        profile_path.read_bytes(), "GPU-PBD container profile"
    )
    profile_schema = _required_string(profile, "schema_version", "profile")
    if profile_schema not in {
        "aan.gpu_pbd_static_container_profile.v1",
        "aan.gpu_pbd_static_container_profile.v2",
    }:
        raise ConvertAssetHandoffError(
            "profile.schema_version is not a supported GPU-PBD container profile"
        )
    _require_value(profile, "role", "gpu_pbd_static_container", "profile")
    _require_value(profile, "claim", "gpu_pbd_static_container", "profile")
    _require_value(profile, "entrypoint", root_usd.name, "profile")
    _require_value(profile, "entry_prim", entry_prim, "profile")
    profile_promotion = _required_mapping(profile, "promotion", "profile")
    _require_value(profile_promotion, "status", "qualified", "profile.promotion")
    collision = _required_mapping(profile, "collision", "profile")
    if collision.get("source_derived_not_primitive_proxy") is not True:
        raise ConvertAssetHandoffError(
            "GPU-PBD collision must be source-derived, not a primitive proxy"
        )
    _require_value(
        collision,
        "piece_approximation",
        "convexDecomposition",
        "profile.collision",
    )
    collision_strategy = _required_string(
        collision, "strategy", "profile.collision"
    )

    resolved_artifacts: dict[str, tuple[Path, str]] = {}
    for path_key, sha_key in (
        ("report", "report_sha256"),
        ("fixture", "fixture_sha256"),
        ("initial_particle_state", "initial_particle_state_sha256"),
    ):
        relative = _required_string(contract, path_key, "gpu_pbd_static_container")
        expected_sha = _required_sha256(
            contract, sha_key, "gpu_pbd_static_container"
        )
        path = _safe_package_file(package, relative, path_key)
        if _file_sha256(path) != expected_sha:
            raise ConvertAssetHandoffError(
                f"GPU-PBD {path_key} SHA-256 does not match manifest"
            )
        if profile_promotion.get(path_key) != relative or profile_promotion.get(
            sha_key
        ) != expected_sha:
            raise ConvertAssetHandoffError(
                f"GPU-PBD {path_key} binding differs between profile and manifest"
            )
        resolved_artifacts[path_key] = (path, expected_sha)

    report = _load_strict_json_mapping(
        resolved_artifacts["report"][0].read_bytes(), "GPU-PBD report"
    )
    runs = report.get("runs")
    if (
        report.get("overall_status") != "pass"
        or report.get("required_cold_runs") != 3
        or not isinstance(runs, list)
        or len(runs) != 3
    ):
        raise ConvertAssetHandoffError("GPU-PBD report must contain three cold passes")
    for run in runs:
        if not isinstance(run, Mapping):
            raise ConvertAssetHandoffError("GPU-PBD run must be a mapping")
        semantics = run.get("resolved_particle_semantics")
        hold = run.get("static_hold")
        performance = run.get("performance")
        if not all(isinstance(value, Mapping) for value in (semantics, hold, performance)):
            raise ConvertAssetHandoffError("GPU-PBD run evidence is incomplete")
        assert isinstance(semantics, Mapping)
        assert isinstance(hold, Mapping)
        assert isinstance(performance, Mapping)
        final = hold.get("final")
        hold_gate = (
            hold.get("maximum_outside", 11) <= 10
            if profile_schema == "aan.gpu_pbd_static_container_profile.v2"
            else hold.get("maximum_below_support") == 0
        )
        valid = (
            run.get("overall_status") == "pass"
            and run.get("particle_readback_attribute") == "points"
            and semantics.get("fluid") is True
            and semantics.get("self_collision") is True
            and hold.get("minimum_inside_ratio", 0.0) >= 0.95
            and hold_gate
            and isinstance(final, Mapping)
            and final.get("particle_count") == 548
            and performance.get("mean_rtx_fps", 0.0) >= 40.0
            and run.get("hard_runtime_errors") == []
        )
        if not valid:
            raise ConvertAssetHandoffError("GPU-PBD cold run failed a required gate")
    fixture = _load_strict_json_mapping(
        resolved_artifacts["fixture"][0].read_bytes(), "GPU-PBD fixture"
    )
    particle_count = fixture.get("particle_count")
    if particle_count != 548:
        raise ConvertAssetHandoffError("GPU-PBD fixture particle_count must be 548")
    particle_parameters = _required_mapping(
        fixture, "particle_parameters", "GPU-PBD fixture"
    )
    initial_state = _required_mapping(
        particle_parameters, "initial_state", "GPU-PBD fixture.particle_parameters"
    )
    _require_value(
        initial_state,
        "kind",
        "normalized_reference_particle_cloud",
        "GPU-PBD fixture initial state",
    )
    return ConvertAssetGPUPBDStaticContainerHandoff(
        package_dir=package,
        package_id=package_id,
        manifest_sha256=_file_sha256(embedded_manifest),
        root_usd=root_usd,
        root_usd_sha256=_file_sha256(root_usd),
        entry_prim=entry_prim,
        profile_path=profile_path,
        profile_sha256=_file_sha256(profile_path),
        qualification_report_path=resolved_artifacts["report"][0].relative_to(package).as_posix(),
        qualification_report_sha256=resolved_artifacts["report"][1],
        fixture_path=resolved_artifacts["fixture"][0].relative_to(package).as_posix(),
        fixture_sha256=resolved_artifacts["fixture"][1],
        initial_particle_state_path=resolved_artifacts["initial_particle_state"][0].relative_to(package).as_posix(),
        initial_particle_state_sha256=resolved_artifacts["initial_particle_state"][1],
        particle_count=particle_count,
        collision_strategy=collision_strategy,
        claim_boundary=_required_string(profile, "claim_boundary", "profile"),
    )


def load_gpu_pbd_transfer_pair_handoff(
    package_dir: str | Path,
    manifest_path: str | Path,
) -> ConvertAssetGPUPBDTransferPairHandoff:
    """Validate a ConvertAsset prescribed-transfer pair without simulator imports."""

    package = Path(package_dir).resolve()
    external_manifest = Path(manifest_path).resolve()
    embedded_manifest = package / "evidence/manifest.json"
    if not package.is_dir() or not embedded_manifest.is_file():
        raise ConvertAssetHandoffError("GPU-PBD transfer package is incomplete")
    if not external_manifest.is_file():
        raise ConvertAssetHandoffError("GPU-PBD transfer manifest is missing")
    if external_manifest.read_bytes() != embedded_manifest.read_bytes():
        raise ConvertAssetHandoffError(
            "external and embedded GPU-PBD transfer manifests do not match"
        )
    manifest = _load_strict_json_mapping(
        embedded_manifest.read_bytes(), "GPU-PBD transfer manifest"
    )
    _require_value(
        manifest,
        "schema_version",
        "aan.gpu_pbd_transfer_pair_manifest.v1",
        "manifest",
    )
    _require_value(manifest, "overall_status", "pass", "manifest")
    promotion = _required_mapping(manifest, "promotion", "manifest")
    if promotion.get("allowed") is not True:
        raise ConvertAssetHandoffError("GPU-PBD transfer promotion is not allowed")
    _require_value(
        promotion,
        "claim",
        "gpu_pbd_prescribed_transfer_pair",
        "manifest.promotion",
    )
    package_id = _required_string(manifest, "package_id", "manifest")
    entrypoints = _required_mapping(manifest, "entrypoints", "manifest")
    component = _safe_package_file(
        package,
        _required_string(entrypoints, "root_usd", "manifest.entrypoints"),
        "root_usd",
    )
    entry_prim = _required_string(
        entrypoints, "asset_entry_prim", "manifest.entrypoints"
    )
    if entry_prim != "/World/Transfer":
        raise ConvertAssetHandoffError("GPU-PBD transfer entry prim must be /World/Transfer")

    contract = _required_mapping(manifest, "gpu_pbd_transfer_pair", "manifest")
    _require_value(contract, "status", "qualified", "gpu_pbd_transfer_pair")
    if contract.get("particle_count") != 548 or contract.get("cold_runs") != 3:
        raise ConvertAssetHandoffError(
            "GPU-PBD transfer contract must bind 548 particles and three cold runs"
        )
    component_sha = _required_sha256(
        contract, "component_sha256", "gpu_pbd_transfer_pair"
    )
    if _file_sha256(component) != component_sha:
        raise ConvertAssetHandoffError("GPU-PBD component SHA-256 does not match manifest")
    profile_path = _safe_package_file(
        package,
        _required_string(contract, "profile", "gpu_pbd_transfer_pair"),
        "profile",
    )
    profile_sha = _required_sha256(
        contract, "profile_sha256", "gpu_pbd_transfer_pair"
    )
    if _file_sha256(profile_path) != profile_sha:
        raise ConvertAssetHandoffError("GPU-PBD profile SHA-256 does not match manifest")
    report_path = _safe_package_file(
        package,
        _required_string(contract, "report", "gpu_pbd_transfer_pair"),
        "report",
    )
    report_sha = _required_sha256(
        contract, "report_sha256", "gpu_pbd_transfer_pair"
    )
    if _file_sha256(report_path) != report_sha:
        raise ConvertAssetHandoffError("GPU-PBD report SHA-256 does not match manifest")

    deps = package / "deps"
    if not deps.is_dir():
        raise ConvertAssetHandoffError("GPU-PBD transfer dependency closure is missing")
    digest = sha256()
    for item in sorted(candidate for candidate in deps.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(deps).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_file_sha256(item)))
    dependency_sha = _required_sha256(
        contract, "dependency_tree_sha256", "gpu_pbd_transfer_pair"
    )
    if digest.hexdigest() != dependency_sha:
        raise ConvertAssetHandoffError(
            "GPU-PBD dependency tree SHA-256 does not match manifest"
        )

    profile = _load_strict_json_mapping(
        profile_path.read_bytes(), "GPU-PBD transfer profile"
    )
    _require_value(
        profile,
        "schema_version",
        "aan.gpu_pbd_transfer_fixture.v1",
        "profile",
    )
    if profile.get("liquid_parameters", {}).get("particle_count") != 548:
        raise ConvertAssetHandoffError("GPU-PBD transfer profile particle_count must be 548")
    qualification = _required_mapping(profile, "qualification", "profile")
    if (
        qualification.get("minimum_target_reception_ratio") != 0.5
        or qualification.get("required_cold_runs") != 3
        or qualification.get("spill_is_blocking") is not False
    ):
        raise ConvertAssetHandoffError("GPU-PBD transfer qualification contract differs")
    selected = _required_mapping(
        contract, "selected_candidate", "gpu_pbd_transfer_pair"
    )
    candidates = profile.get("bounded_search", {}).get("candidates", [])
    if selected not in candidates:
        raise ConvertAssetHandoffError("selected transfer candidate is not in the profile")

    report = _load_strict_json_mapping(
        report_path.read_bytes(), "GPU-PBD transfer report"
    )
    cold_runs = report.get("cold_runs")
    report_promotion = report.get("promotion")
    if (
        report.get("overall_status") != "pass"
        or not isinstance(report_promotion, Mapping)
        or report_promotion.get("allowed") is not True
        or report_promotion.get("claim") != "gpu_pbd_prescribed_transfer_pair"
        or report.get("selected_candidate") != dict(selected)
        or not isinstance(cold_runs, list)
        or len(cold_runs) != 3
    ):
        raise ConvertAssetHandoffError("GPU-PBD transfer report is not promotable")
    for run in cold_runs:
        if not isinstance(run, Mapping):
            raise ConvertAssetHandoffError("GPU-PBD transfer cold run is incomplete")
        hold = run.get("static_hold")
        pour = run.get("pour")
        performance = run.get("performance")
        valid = (
            run.get("overall_status") == "pass"
            and run.get("particle_readback_attribute") == "points"
            and isinstance(hold, Mapping)
            and hold.get("minimum_source_ratio", 0.0) >= 0.95
            and isinstance(pour, Mapping)
            and pour.get("particle_count") == 548
            and pour.get("target_ratio", 0.0) >= 0.5
            and isinstance(performance, Mapping)
            and performance.get("mean_rtx_fps", 0.0) >= 40.0
            and run.get("hard_runtime_errors") == []
        )
        if not valid:
            raise ConvertAssetHandoffError("GPU-PBD transfer cold run failed a required gate")

    return ConvertAssetGPUPBDTransferPairHandoff(
        package_dir=package,
        package_id=package_id,
        manifest_sha256=_file_sha256(embedded_manifest),
        component_usd=component,
        component_sha256=component_sha,
        entry_prim=entry_prim,
        profile_path=profile_path,
        profile_sha256=profile_sha,
        qualification_report_path=report_path.relative_to(package).as_posix(),
        qualification_report_sha256=report_sha,
        dependency_tree_sha256=dependency_sha,
        particle_count=548,
        selected_candidate=dict(selected),
        claim_boundary=_required_string(
            promotion, "claim_boundary", "manifest.promotion"
        ),
    )

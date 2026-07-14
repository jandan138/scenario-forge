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
            "--package-dir",
            self.package_dir,
        )


class ConvertAssetHandoffError(ValueError):
    """Raised when a ConvertAsset package does not satisfy its handoff contract."""


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_INTERACTION_USAGE_ROLES = {
    "scene_overlay": "scene_overlay",
    "rigid_object": "rigid_object",
}


@dataclass(frozen=True)
class ConvertAssetInteractionContract:
    schema_version: str
    asset_entry_prim: str
    rigid_root_prim: str
    active_rigid_body_prims: tuple[str, ...]
    collider_prims: tuple[str, ...]
    named_frames: Mapping[str, Mapping[str, Any]]
    contract_payload_sha256: str
    runtime_tree_sha256: str
    qualification_report_paths: tuple[str, ...]
    task_ready: bool
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return _copy_json_mapping(self.payload, "interaction_contract")


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
    quality_tier: str
    profile_id: str
    profile_revision: str
    profile_sha256: str
    claim_boundary: str
    replacement_contract: str
    claims_forbidden: tuple[str, ...]
    scoped_physics_warning_count: int
    usage: str
    interaction_contract: ConvertAssetInteractionContract | None = None

    def to_local_usd_asset_source(
        self,
        *,
        asset_id: str,
        license: str,
        attribution: tuple[str, ...] = (),
        redistributable: bool = False,
        exclude_relative_paths: tuple[str, ...] = (),
    ) -> LocalUSDAssetSource:
        if self.usage == "rigid_object" and self.interaction_contract is not None:
            for excluded_path in exclude_relative_paths:
                normalized = PurePosixPath(excluded_path).as_posix()
                if any(
                    report_path == normalized
                    or report_path.startswith(normalized + "/")
                    for report_path in self.interaction_contract.qualification_report_paths
                ):
                    raise ValueError(
                        "rigid_object source cannot exclude its qualification report"
                    )
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
            metadata={
                "producer_asset_id": self.producer_asset_id,
                "producer_asset_role": self.producer_asset_role,
                "source_sha256": f"sha256:{self.source_sha256}",
                "root_usd_sha256": f"sha256:{self.root_usd_sha256}",
                "scope_prims": list(self.scope_prims),
                "runtime_profile": self.runtime_profile,
                "consumer_profile": self.consumer_profile,
                "quality_tier": self.quality_tier,
                "profile_id": self.profile_id,
                "profile_revision": self.profile_revision,
                "profile_sha256": f"sha256:{self.profile_sha256}",
                "claim_boundary": self.claim_boundary,
                "replacement_contract": self.replacement_contract,
                "claims_forbidden": list(self.claims_forbidden),
                "scoped_physics_warning_count": self.scoped_physics_warning_count,
                **(
                    {"interaction_contract": self.interaction_contract.to_mapping()}
                    if self.interaction_contract is not None
                    else {}
                ),
            },
        )
        return LocalUSDAssetSource(
            asset_id=asset_id,
            source_usd=self.root_usd,
            role=_INTERACTION_USAGE_ROLES[self.usage],
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
    if usage not in _INTERACTION_USAGE_ROLES:
        raise ConvertAssetHandoffError(
            "usage must be 'scene_overlay' or 'rigid_object'"
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
    try:
        raw_manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConvertAssetHandoffError("ConvertAsset manifest is not valid JSON") from exc
    manifest = _mapping(raw_manifest, "manifest")

    schema_version = _required_string(manifest, "schema_version", "manifest")
    if schema_version != "asset_application_normalizer.v1":
        raise ConvertAssetHandoffError(
            f"unsupported ConvertAsset manifest schema_version: {schema_version}"
        )
    _require_value(manifest, "overall_status", "pass", "manifest")
    package_id = _required_string(manifest, "package_id", "manifest")
    producer_asset_id = _required_string(manifest, "asset_id", "manifest")
    producer_asset_role = _required_string(manifest, "asset_role", "manifest")
    if producer_asset_role != "dynamic":
        raise ConvertAssetHandoffError("manifest.asset_role must be 'dynamic'")

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
    _require_value(physics, "role", "dynamic", "manifest.physics_closure")
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
    for field_name, digest in source_hash_fields.items():
        if digest != source_digest:
            raise ConvertAssetHandoffError(
                f"source SHA-256 mismatch at {field_name}"
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
    profile_sha = _required_string(admission, "profile_sha256", "profile_admission")
    packaged_profile_sha = _required_string(
        admission,
        "packaged_profile_sha256",
        "profile_admission",
    )
    if profile_sha != packaged_profile_sha or _file_sha256(profile_path) != profile_sha:
        raise ConvertAssetHandoffError("profile SHA-256 does not match packaged profile")
    quality_tier = _required_string(admission, "quality_tier", "profile_admission")
    profile_evidence = _required_mapping(admission, "evidence", "profile_admission")
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

    runtime = _required_mapping(manifest, "runtime_evidence", "manifest")
    _require_value(runtime, "status", "pass", "runtime_evidence")
    _require_value(
        runtime,
        "runtime_profile",
        expected_runtime_profile,
        "runtime_evidence",
    )
    for gate_name in ("cold_load", "physics_step", "reset"):
        gate = _required_mapping(runtime, gate_name, "runtime_evidence")
        _require_value(gate, "status", "pass", f"runtime_evidence.{gate_name}")
    root_sha = _file_sha256(root_usd)
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

    _validate_retained_scope(manifest, expected_scopes)
    _validate_stage_metrics(manifest, source_binding)
    claims_forbidden = _required_string_tuple(
        manifest,
        "claims_forbidden",
        "manifest",
    )
    manifest_digest = sha256(manifest_bytes).hexdigest()
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
        profile_id=_required_string(admission, "profile_id", "profile_admission"),
        profile_revision=_required_string(admission, "revision", "profile_admission"),
        profile_sha256=profile_sha,
        claim_boundary=claim_boundary,
        replacement_contract=replacement_contract,
        claims_forbidden=claims_forbidden,
        scoped_physics_warning_count=scoped_count,
        usage=usage,
        interaction_contract=interaction_contract,
    )


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
    _require_exact_fields(
        contract,
        {
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
        },
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
    _require_value(
        profile,
        "schema_version",
        "aan.object_interaction_profile.v1",
        "interaction_contract.profile",
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

    open_top = _required_mapping(contract, "open_top", "manifest.interaction_contract")
    _require_exact_fields(
        open_top,
        {"required", "axis_body_local", "aperture_frame", "status", "evidence"},
        "interaction_contract.open_top",
    )
    open_top_required = _required_bool(open_top, "required", "interaction_contract.open_top")
    axis = _finite_number_list(
        open_top.get("axis_body_local"),
        3,
        "interaction_contract.open_top.axis_body_local",
    )
    if sum(component * component for component in axis) == 0.0:
        raise ConvertAssetHandoffError(
            "interaction_contract.open_top.axis_body_local must be non-zero"
        )
    aperture_frame = _required_string(
        open_top,
        "aperture_frame",
        "interaction_contract.open_top",
    )
    if aperture_frame not in normalized_frames:
        raise ConvertAssetHandoffError(
            "interaction_contract.open_top.aperture_frame must name an authoritative frame"
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

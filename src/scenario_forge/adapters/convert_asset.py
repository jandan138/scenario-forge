from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from pathlib import PurePosixPath
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

    def to_local_usd_asset_source(
        self,
        *,
        asset_id: str,
        license: str,
        attribution: tuple[str, ...] = (),
        redistributable: bool = False,
        exclude_relative_paths: tuple[str, ...] = (),
    ) -> LocalUSDAssetSource:
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
            },
        )
        return LocalUSDAssetSource(
            asset_id=asset_id,
            source_usd=self.root_usd,
            role="scene_overlay",
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
    )


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

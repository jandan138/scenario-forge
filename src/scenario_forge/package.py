from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.assets.lock import check_asset_lock

SCENARIO_PACKAGE_V01 = "scenario-package/v0.1"
SCENARIO_PACKAGE_V02 = "scenario-package/v0.2"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCENARIO_PACKAGE_V01, SCENARIO_PACKAGE_V02})
SUPPORTED_TARGETS = frozenset({"ebench", "embodied-eval-os"})
SUPPORTED_PACKAGE_MODES = frozenset({"fat", "locked"})
VALIDATION_LEVELS = frozenset(
    {
        "generated",
        "package_schema_validated",
        "asset_locked",
        "usd_static_validated",
        "semantic_validated",
        "layout_static_validated",
        "adapter_static_validated",
        "simulator_smoke_validated",
        "runtime_evidence_validated",
        "benchmark_quality_validated",
    }
)
V01_REQUIRED_FILE_KEYS = ("scene", "instances", "task", "robot", "validation_report")
V02_REQUIRED_ENTRYPOINT_KEYS = (
    "generation_plan",
    "scene_usd",
    "scene_instances",
    "task",
    "robot",
    "metrics",
)
V02_REQUIRED_ASSET_KEYS = ("manifest", "lock")
V02_REQUIRED_VALIDATION_KEYS = ("report", "minimum_required_level")
V02_REQUIRED_PROVENANCE_KEYS = ("summary",)


class PackageError(ValueError):
    """Raised when a scenario package manifest is malformed."""


@dataclass(frozen=True)
class PackageManifest:
    schema_version: str
    package_id: str
    scenario_domain: str
    package_mode: str
    targets: tuple[str, ...]
    entrypoints: dict[str, str]
    assets: dict[str, str]
    validation: dict[str, str]
    provenance: dict[str, str]

    @property
    def scenario_id(self) -> str:
        """Backward-compatible name for v0.1 callers."""
        return self.package_id

    @property
    def exports(self) -> tuple[str, ...]:
        """Backward-compatible name for target exports."""
        return self.targets

    @property
    def files(self) -> dict[str, str]:
        """Backward-compatible logical file map for existing callers."""
        files = dict(self.entrypoints)
        if self.schema_version == SCENARIO_PACKAGE_V02:
            _copy_alias(files, "scene_usd", "scene")
            _copy_alias(files, "scene_instances", "instances")
            validation_report = self.validation.get("report")
            if validation_report is not None:
                files["validation_report"] = validation_report
        return files

    @property
    def scene_path(self) -> str | None:
        if self.schema_version == SCENARIO_PACKAGE_V02:
            return self.entrypoints.get("scene_usd")
        return self.entrypoints.get("scene")


@dataclass(frozen=True)
class PackageValidationReport:
    ok: bool
    root: Path
    required_files: tuple[Path, ...]
    messages: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PackageError(f"Missing manifest: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PackageError(f"Manifest must be a mapping: {path}")
    return data


def load_package_manifest(root: str | Path) -> PackageManifest:
    package_root = Path(root)
    data = _load_yaml(package_root / "manifest.yaml")

    schema_version = _require_string(data, "schema_version")
    if schema_version == SCENARIO_PACKAGE_V01:
        return _load_v01_manifest(data)
    if schema_version == SCENARIO_PACKAGE_V02:
        return _load_v02_manifest(data)
    expected = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
    raise PackageError(f"Unsupported schema_version {schema_version!r}; expected one of: {expected}")


def _load_v01_manifest(data: dict[str, Any]) -> PackageManifest:
    scenario_id = _require_string(data, "scenario_id")
    scenario_domain = str(data.get("scenario_domain", "unspecified"))
    exports = _require_string_list(data, "exports")
    _reject_unsupported_targets(exports, label="export target")

    files = _require_string_mapping(data, "files")

    return PackageManifest(
        schema_version=SCENARIO_PACKAGE_V01,
        package_id=scenario_id,
        scenario_domain=scenario_domain,
        package_mode="bootstrap",
        targets=tuple(exports),
        entrypoints=files,
        assets={},
        validation={},
        provenance={},
    )


def _load_v02_manifest(data: dict[str, Any]) -> PackageManifest:
    package_id = _require_string(data, "package_id")
    scenario_domain = _require_string(data, "scenario_domain")
    package_mode = _require_string(data, "package_mode")
    if package_mode not in SUPPORTED_PACKAGE_MODES:
        raise PackageError(
            "Manifest field 'package_mode' must be one of: "
            f"{', '.join(sorted(SUPPORTED_PACKAGE_MODES))}"
        )

    targets = _require_string_list(data, "targets")
    _reject_unsupported_targets(targets, label="target")
    entrypoints = _require_string_mapping(data, "entrypoints")
    assets = _require_string_mapping(data, "assets")
    validation = _require_string_mapping(data, "validation")
    provenance = _require_string_mapping(data, "provenance")

    _require_keys(entrypoints, "entrypoints", V02_REQUIRED_ENTRYPOINT_KEYS)
    _require_keys(assets, "assets", V02_REQUIRED_ASSET_KEYS)
    _require_keys(validation, "validation", V02_REQUIRED_VALIDATION_KEYS)
    _require_keys(provenance, "provenance", V02_REQUIRED_PROVENANCE_KEYS)

    minimum_level = validation["minimum_required_level"]
    if minimum_level not in VALIDATION_LEVELS:
        raise PackageError(
            "Manifest field 'validation.minimum_required_level' must be one of: "
            f"{', '.join(sorted(VALIDATION_LEVELS))}"
        )

    return PackageManifest(
        schema_version=SCENARIO_PACKAGE_V02,
        package_id=package_id,
        scenario_domain=scenario_domain,
        package_mode=package_mode,
        targets=tuple(targets),
        entrypoints=entrypoints,
        assets=assets,
        validation=validation,
        provenance=provenance,
    )


def validate_package(root: str | Path, require_asset_lock: bool = False) -> PackageValidationReport:
    package_root = Path(root)
    try:
        manifest = load_package_manifest(package_root)
    except PackageError as exc:
        return PackageValidationReport(
            ok=False,
            root=package_root,
            required_files=(),
            messages=(str(exc),),
        )

    messages: list[str] = []
    required_paths = _required_paths_for_manifest(package_root, manifest, messages)
    for relative_path, required_path in required_paths:
        if not required_path.exists():
            messages.append(f"Missing referenced file: {relative_path}")

    if require_asset_lock or manifest.schema_version == SCENARIO_PACKAGE_V02:
        scene_path = manifest.scene_path
        scene_paths = (scene_path,) if scene_path is not None else ()
        asset_report = check_asset_lock(package_root, scene_paths=scene_paths)
        messages.extend(asset_report.messages)

    return PackageValidationReport(
        ok=not messages,
        root=package_root,
        required_files=tuple(path for _, path in required_paths),
        messages=tuple(messages),
    )


def _required_paths_for_manifest(
    package_root: Path, manifest: PackageManifest, messages: list[str]
) -> list[tuple[str, Path]]:
    if manifest.schema_version == SCENARIO_PACKAGE_V02:
        entries: list[tuple[str, str]] = []
        for key in V02_REQUIRED_ENTRYPOINT_KEYS:
            entries.append((key, manifest.entrypoints[key]))
        entries.append(("assets.manifest", manifest.assets["manifest"]))
        entries.append(("assets.lock", manifest.assets["lock"]))
        entries.append(("validation.report", manifest.validation["report"]))
        entries.append(("provenance.summary", manifest.provenance["summary"]))
        return [(relative_path, package_root / relative_path) for _, relative_path in entries]

    required_paths: list[tuple[str, Path]] = []
    for file_key in V01_REQUIRED_FILE_KEYS:
        relative_path = manifest.files.get(file_key)
        if relative_path is None:
            messages.append(f"Missing manifest file entry: {file_key}")
            continue
        required_paths.append((relative_path, package_root / relative_path))
    return required_paths


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise PackageError(f"Manifest field {key!r} must be a non-empty string")
    return value


def _require_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PackageError(f"Manifest field {key!r} must be a list of strings")
    if not value:
        raise PackageError(f"Manifest field {key!r} must not be empty")
    return value


def _require_string_mapping(data: dict[str, Any], key: str) -> dict[str, str]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PackageError(f"Manifest field {key!r} must be a mapping")
    result: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise PackageError(f"Manifest field {key!r} must map strings to strings")
        result[raw_key] = raw_value
    return result


def _reject_unsupported_targets(targets: list[str], label: str) -> None:
    unsupported_targets = sorted(set(targets) - SUPPORTED_TARGETS)
    if unsupported_targets:
        raise PackageError(f"Unsupported {label}(s): {', '.join(unsupported_targets)}")


def _require_keys(mapping: dict[str, str], field_name: str, required_keys: tuple[str, ...]) -> None:
    missing = [key for key in required_keys if key not in mapping]
    if missing:
        raise PackageError(f"Manifest field {field_name!r} is missing key(s): {', '.join(missing)}")


def _copy_alias(files: dict[str, str], source_key: str, alias_key: str) -> None:
    source = files.get(source_key)
    if source is not None:
        files[alias_key] = source

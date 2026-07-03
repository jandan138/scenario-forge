from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.assets.lock import check_asset_lock

SUPPORTED_SCHEMA_VERSION = "scenario-package/v0.1"
SUPPORTED_EXPORTS = frozenset({"ebench", "embodied-eval-os"})
REQUIRED_FILE_KEYS = ("scene", "instances", "task", "robot", "validation_report")


class PackageError(ValueError):
    """Raised when a scenario package manifest is malformed."""


@dataclass(frozen=True)
class PackageManifest:
    schema_version: str
    scenario_id: str
    scenario_domain: str
    exports: tuple[str, ...]
    files: dict[str, str]


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
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise PackageError(
            f"Unsupported schema_version {schema_version!r}; expected {SUPPORTED_SCHEMA_VERSION!r}"
        )

    scenario_id = _require_string(data, "scenario_id")
    scenario_domain = str(data.get("scenario_domain", "unspecified"))
    exports = _require_string_list(data, "exports")
    unsupported_exports = sorted(set(exports) - SUPPORTED_EXPORTS)
    if unsupported_exports:
        raise PackageError(f"Unsupported export target(s): {', '.join(unsupported_exports)}")

    raw_files = data.get("files")
    if not isinstance(raw_files, dict):
        raise PackageError("Manifest field 'files' must be a mapping")
    files: dict[str, str] = {}
    for key, value in raw_files.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise PackageError("Manifest field 'files' must map strings to strings")
        files[key] = value

    return PackageManifest(
        schema_version=schema_version,
        scenario_id=scenario_id,
        scenario_domain=scenario_domain,
        exports=tuple(exports),
        files=files,
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

    required_paths: list[Path] = []
    messages: list[str] = []
    for file_key in REQUIRED_FILE_KEYS:
        relative_path = manifest.files.get(file_key)
        if relative_path is None:
            messages.append(f"Missing manifest file entry: {file_key}")
            continue
        required_path = package_root / relative_path
        required_paths.append(required_path)
        if not required_path.exists():
            messages.append(f"Missing referenced file: {relative_path}")

    if require_asset_lock:
        scene_path = manifest.files.get("scene")
        scene_paths = (scene_path,) if scene_path is not None else ()
        asset_report = check_asset_lock(package_root, scene_paths=scene_paths)
        messages.extend(asset_report.messages)

    return PackageValidationReport(
        ok=not messages,
        root=package_root,
        required_files=tuple(required_paths),
        messages=tuple(messages),
    )


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

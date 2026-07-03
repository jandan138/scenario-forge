from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.licenses import validate_license
from scenario_forge.assets.manifest import load_asset_manifest

ASSET_LOCK_SCHEMA_VERSION = "asset-lock/v0.2"


class AssetLockError(ValueError):
    """Raised when an asset lock is malformed."""


@dataclass(frozen=True)
class AssetLockEntry:
    asset_id: str
    source_kind: str
    source_uri: str
    resolved_path: str
    content_sha256: str
    license: str
    resolver_version: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AssetLock:
    schema_version: str
    lock_id: str
    created_by: str
    assets: dict[str, AssetLockEntry]


@dataclass(frozen=True)
class AssetLockReport:
    ok: bool
    root: Path
    messages: tuple[str, ...]


def generate_asset_lock(root: str | Path) -> AssetLock:
    package_root = Path(root)
    manifest = load_asset_manifest(package_root)
    assets: dict[str, AssetLockEntry] = {}

    for asset in manifest.assets:
        resolved_path = _resolve_package_path(package_root, asset.canonical_usd)
        content_sha256 = compute_sha256(resolved_path)
        assets[asset.asset_id] = AssetLockEntry(
            asset_id=asset.asset_id,
            source_kind=str(asset.metadata.get("source_kind", "package_local")),
            source_uri=str(asset.metadata.get("source_uri", asset.canonical_usd)),
            resolved_path=asset.canonical_usd,
            content_sha256=content_sha256,
            license=asset.license,
            resolver_version=str(asset.metadata.get("resolver_version", "scenario-forge/phase1")),
            metadata={},
        )

    lock_id = f"{package_root.name or 'scenario_package'}_asset_lock"
    return AssetLock(
        schema_version=ASSET_LOCK_SCHEMA_VERSION,
        lock_id=lock_id,
        created_by="scenario-forge",
        assets=assets,
    )


def write_asset_lock(root: str | Path, lock: AssetLock) -> Path:
    package_root = Path(root)
    path = package_root / "locks" / "asset_lock.yaml"
    return write_yaml_artifact(path, _lock_to_yaml(lock))


def load_asset_lock(root: str | Path) -> AssetLock:
    package_root = Path(root)
    path = package_root / "locks" / "asset_lock.yaml"
    return load_asset_lock_file(path)


def load_asset_lock_file(path: str | Path) -> AssetLock:
    lock_path = Path(path)
    if not lock_path.exists():
        raise AssetLockError("Missing asset lock: locks/asset_lock.yaml")

    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssetLockError(f"Asset lock must be a mapping: {lock_path}")

    schema_version = _require_string(data, "schema_version")
    if schema_version != ASSET_LOCK_SCHEMA_VERSION:
        raise AssetLockError(
            f"Unsupported asset lock schema_version {schema_version!r}; "
            f"expected {ASSET_LOCK_SCHEMA_VERSION!r}"
        )

    raw_assets = data.get("assets")
    if not isinstance(raw_assets, dict):
        raise AssetLockError("Asset lock field 'assets' must be a mapping")

    assets: dict[str, AssetLockEntry] = {}
    for asset_id, raw_entry in raw_assets.items():
        if not isinstance(asset_id, str) or not isinstance(raw_entry, dict):
            raise AssetLockError("Asset lock field 'assets' must map strings to mappings")
        raw_license = raw_entry.get("license")
        license_value = raw_license if isinstance(raw_license, str) else None
        license_error = validate_license(license_value)
        if license_error is not None:
            raise AssetLockError(f"{license_error} for asset {asset_id}")
        assert license_value is not None
        assets[asset_id] = AssetLockEntry(
            asset_id=asset_id,
            source_kind=_require_string(raw_entry, "source_kind"),
            source_uri=_require_string(raw_entry, "source_uri"),
            resolved_path=_require_string(raw_entry, "resolved_path"),
            content_sha256=_require_string(raw_entry, "content_sha256"),
            license=license_value,
            resolver_version=_require_string(raw_entry, "resolver_version"),
            metadata={
                key: value
                for key, value in raw_entry.items()
                if key
                not in {
                    "source_kind",
                    "source_uri",
                    "resolved_path",
                    "content_sha256",
                    "license",
                    "resolver_version",
                }
            },
        )

    return AssetLock(
        schema_version=schema_version,
        lock_id=_require_string(data, "lock_id"),
        created_by=_require_string(data, "created_by"),
        assets=assets,
    )


def check_asset_lock(root: str | Path, scene_paths: tuple[str, ...] = ()) -> AssetLockReport:
    package_root = Path(root)
    messages: list[str] = []
    try:
        lock = load_asset_lock(package_root)
    except AssetLockError as exc:
        return AssetLockReport(ok=False, root=package_root, messages=(str(exc),))

    for asset in lock.assets.values():
        license_error = validate_license(asset.license)
        if license_error is not None:
            messages.append(f"{license_error} for asset {asset.asset_id}")

        resolved_path = _resolve_package_path_or_none(package_root, asset.resolved_path)
        if resolved_path is None:
            messages.append(f"Locked asset path escapes package root: {asset.resolved_path}")
            continue
        if not resolved_path.exists():
            messages.append(f"Missing locked asset file: {asset.resolved_path}")
            continue
        actual_sha256 = compute_sha256(resolved_path)
        if actual_sha256 != asset.content_sha256:
            messages.append(f"Checksum mismatch for asset {asset.asset_id}")

    locked_paths = {asset.resolved_path for asset in lock.assets.values()}
    for scene_path in scene_paths:
        scene_file = _resolve_package_path_or_none(package_root, scene_path)
        if scene_file is None or not scene_file.exists():
            continue
        for reference in _scan_usd_references(package_root, scene_file):
            if reference not in locked_paths:
                messages.append(f"USD reference is not locked: {reference}")

    return AssetLockReport(ok=not messages, root=package_root, messages=tuple(messages))


def _lock_to_yaml(lock: AssetLock) -> dict[str, Any]:
    return {
        "schema_version": lock.schema_version,
        "lock_id": lock.lock_id,
        "created_by": lock.created_by,
        "assets": {
            asset_id: {
                "source_kind": entry.source_kind,
                "source_uri": entry.source_uri,
                "resolved_path": entry.resolved_path,
                "content_sha256": entry.content_sha256,
                "license": entry.license,
                "resolver_version": entry.resolver_version,
                **entry.metadata,
            }
            for asset_id, entry in lock.assets.items()
        },
    }


def _resolve_package_path(root: Path, relative_path: str) -> Path:
    resolved = _resolve_package_path_or_none(root, relative_path)
    if resolved is None:
        raise AssetLockError(f"Asset path escapes package root: {relative_path}")
    if not resolved.exists():
        raise AssetLockError(f"Missing asset file: {relative_path}")
    return resolved


def _resolve_package_path_or_none(root: Path, relative_path: str) -> Path | None:
    if "://" in relative_path:
        return None
    package_root = root.resolve()
    resolved = (package_root / relative_path).resolve()
    if resolved == package_root or package_root in resolved.parents:
        return resolved
    return None


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise AssetLockError(f"Asset lock field {key!r} must be a non-empty string")
    return value


def _scan_usd_references(package_root: Path, path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    references: list[str] = []
    for match in re.finditer(r"@([^@]+)@", source):
        reference = match.group(1)
        if "://" in reference:
            continue
        if reference.endswith((".usd", ".usda")):
            resolved = (path.parent / reference).resolve()
            package_root_resolved = package_root.resolve()
            if resolved == package_root_resolved or package_root_resolved in resolved.parents:
                references.append(str(resolved.relative_to(package_root_resolved)))
            else:
                references.append(reference)
    return tuple(references)

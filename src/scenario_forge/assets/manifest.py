from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.assets.licenses import validate_license

ASSET_MANIFEST_SCHEMA_VERSION = "asset-manifest/v0.2"


@dataclass(frozen=True)
class AssetRef:
    asset_id: str
    uri: str
    role: str
    license: str
    sha256: str | None = None
    size_bytes: int | None = None

    def resolve_local(self, asset_root: str | Path) -> Path | None:
        if "://" in self.uri:
            return None

        root = Path(asset_root).resolve()
        candidate = (root / self.uri).resolve()
        if candidate == root or root in candidate.parents:
            return candidate
        return None


class AssetManifestError(ValueError):
    """Raised when an asset manifest is malformed."""


@dataclass(frozen=True)
class AssetManifestEntry:
    asset_id: str
    role: str
    asset_type: str
    canonical_usd: str
    license: str
    sha256: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class AssetManifest:
    schema_version: str
    assets: tuple[AssetManifestEntry, ...]


def collect_asset_refs(refs: list[AssetRef]) -> dict[str, AssetRef]:
    by_id: dict[str, AssetRef] = {}
    for ref in refs:
        if ref.asset_id in by_id:
            raise ValueError(f"Duplicate asset_id: {ref.asset_id}")
        by_id[ref.asset_id] = ref
    return by_id


def load_asset_manifest(root: str | Path) -> AssetManifest:
    manifest_path = Path(root) / "assets" / "asset_manifest.yaml"
    if not manifest_path.exists():
        raise AssetManifestError(f"Missing asset manifest: {manifest_path}")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssetManifestError(f"Asset manifest must be a mapping: {manifest_path}")

    schema_version = _require_string(data, "schema_version")
    if schema_version != ASSET_MANIFEST_SCHEMA_VERSION:
        raise AssetManifestError(
            f"Unsupported asset manifest schema_version {schema_version!r}; "
            f"expected {ASSET_MANIFEST_SCHEMA_VERSION!r}"
        )

    raw_assets = data.get("assets")
    if not isinstance(raw_assets, list):
        raise AssetManifestError("Asset manifest field 'assets' must be a list")

    seen: set[str] = set()
    assets: list[AssetManifestEntry] = []
    for index, raw_asset in enumerate(raw_assets):
        if not isinstance(raw_asset, dict):
            raise AssetManifestError(f"Asset manifest entry {index} must be a mapping")
        asset_id = _require_string(raw_asset, "asset_id")
        if asset_id in seen:
            raise AssetManifestError(f"Duplicate asset_id: {asset_id}")
        seen.add(asset_id)

        raw_license = raw_asset.get("license")
        license_value = raw_license if isinstance(raw_license, str) else None
        license_error = validate_license(license_value)
        if license_error is not None:
            raise AssetManifestError(f"{license_error} for asset {asset_id}")
        assert license_value is not None

        assets.append(
            AssetManifestEntry(
                asset_id=asset_id,
                role=_require_string(raw_asset, "role"),
                asset_type=_require_string(raw_asset, "asset_type"),
                canonical_usd=_require_string(raw_asset, "canonical_usd"),
                license=license_value,
                sha256=_require_string(raw_asset, "sha256"),
                metadata={
                    key: value
                    for key, value in raw_asset.items()
                    if key
                    not in {
                        "asset_id",
                        "role",
                        "asset_type",
                        "canonical_usd",
                        "license",
                        "sha256",
                    }
                },
            )
        )

    return AssetManifest(schema_version=schema_version, assets=tuple(assets))


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise AssetManifestError(f"Asset manifest field {key!r} must be a non-empty string")
    return value

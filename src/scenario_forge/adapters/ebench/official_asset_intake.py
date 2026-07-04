from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any

import yaml

from scenario_forge.assets.checksum import compute_sha256


OFFICIAL_ASSET_SOURCES_SCHEMA_VERSION = "ebench-official-asset-sources/v0.1"
OFFICIAL_ASSET_INTAKE_RESOLVER = "scenario-forge-ebench-official-asset-intake/v0.1"


@dataclass(frozen=True)
class OfficialAssetSource:
    asset_id: str
    role: str
    source_path: Path
    license: str


@dataclass(frozen=True)
class OfficialAssetSources:
    task_id: str
    instruction: str
    assets: dict[str, OfficialAssetSource]


@dataclass(frozen=True)
class MaterializedOfficialAsset:
    asset_id: str
    role: str
    canonical_usd: str
    sha256: str
    license: str
    source_path: str

    def asset_manifest_entry(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "role": self.role,
            "asset_type": "usd_bundle",
            "canonical_usd": self.canonical_usd,
            "license": self.license,
            "sha256": self.sha256,
            "source_kind": "official_ebench_asset",
            "source_uri": self.source_path,
            "resolver_version": OFFICIAL_ASSET_INTAKE_RESOLVER,
        }


def load_official_asset_sources(path: str | Path) -> OfficialAssetSources:
    manifest_path = Path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Official asset source manifest must be a mapping: {manifest_path}")
    if data.get("schema_version") != OFFICIAL_ASSET_SOURCES_SCHEMA_VERSION:
        raise ValueError("Unsupported official asset source schema_version")

    task_id = _required_string(data, "task_id")
    instruction = _required_string(data, "instruction")
    raw_assets = data.get("assets")
    if not isinstance(raw_assets, dict):
        raise ValueError("Official asset source manifest field 'assets' must be a mapping")

    assets: dict[str, OfficialAssetSource] = {}
    for asset_id, raw_asset in raw_assets.items():
        if not isinstance(asset_id, str) or not isinstance(raw_asset, dict):
            raise ValueError("Official asset entries must map asset IDs to mappings")
        source_path = Path(_required_string(raw_asset, "source_path"))
        if not source_path.exists():
            raise ValueError(f"Missing official asset source: {source_path}")
        assets[asset_id] = OfficialAssetSource(
            asset_id=asset_id,
            role=_required_string(raw_asset, "role"),
            source_path=source_path,
            license=_required_string(raw_asset, "license"),
        )

    return OfficialAssetSources(task_id=task_id, instruction=instruction, assets=assets)


def materialize_official_asset_bundle(
    *,
    source_path: str | Path,
    package_root: str | Path,
    asset_id: str,
    role: str,
    license: str,
) -> MaterializedOfficialAsset:
    source_usd = Path(source_path)
    if not source_usd.exists():
        raise ValueError(f"Missing official asset source: {source_usd}")

    root = Path(package_root)
    target_dir = root / "assets" / asset_id
    root_resolved = root.resolve()
    target_resolved = target_dir.resolve()
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise ValueError(f"Materialized asset target escapes package root: {target_dir}")

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_usd.parent, target_dir)

    target_usd = target_dir / source_usd.name
    canonical_usd = target_usd.relative_to(root).as_posix()
    return MaterializedOfficialAsset(
        asset_id=asset_id,
        role=role,
        canonical_usd=canonical_usd,
        sha256=compute_sha256(target_usd),
        license=license,
        source_path=str(source_usd),
    )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string field: {key}")
    return value

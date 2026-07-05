from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
from typing import Any

import yaml

from scenario_forge.assets.checksum import compute_sha256


OFFICIAL_ASSET_SOURCES_SCHEMA_VERSION = "ebench-official-asset-sources/v0.1"
OFFICIAL_ASSET_INTAKE_RESOLVER = "scenario-forge-ebench-official-asset-intake/v0.1"
MDL_TEXTURE_2D_RE = re.compile(r"texture_2d\(\s*\"([^\"]+)\"")
USD_ASSET_REF_RE = re.compile(r"@([^@\n]+)@")


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
    materialization_root = _materialization_root_for_source(source_usd)
    if materialization_root == source_usd.parent:
        shutil.copytree(source_usd.parent, target_dir)
        target_usd = target_dir / source_usd.name
    else:
        source_bundle_target = target_dir / source_usd.parent.relative_to(materialization_root)
        shutil.copytree(source_usd.parent, source_bundle_target)
        for sidecar_root in _external_sidecar_roots(source_usd, materialization_root):
            source_sidecar = materialization_root / sidecar_root
            target_sidecar = target_dir / sidecar_root
            if source_sidecar.is_dir():
                shutil.copytree(source_sidecar, target_sidecar, dirs_exist_ok=True)
            elif source_sidecar.is_file():
                target_sidecar.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_sidecar, target_sidecar)
        target_usd = source_bundle_target / source_usd.name
    canonical_usd = target_usd.relative_to(root).as_posix()
    return MaterializedOfficialAsset(
        asset_id=asset_id,
        role=role,
        canonical_usd=canonical_usd,
        sha256=compute_sha256(target_usd),
        license=license,
        source_path=str(source_usd),
    )


def audit_mdl_texture_closure(root: str | Path) -> dict[str, object]:
    bundle_root = Path(root)
    missing_textures: list[dict[str, str]] = []
    for material_path in sorted(bundle_root.rglob("*.mdl")):
        material_text = material_path.read_text(encoding="utf-8", errors="ignore")
        for texture_ref in MDL_TEXTURE_2D_RE.findall(material_text):
            if _is_external_texture_reference(texture_ref):
                continue
            texture_path = (material_path.parent / texture_ref).resolve()
            if texture_path.exists():
                continue
            missing_textures.append(
                {
                    "material": _display_path(material_path, bundle_root),
                    "texture": texture_ref,
                    "resolved_path": _display_path(texture_path, bundle_root),
                }
            )
    return {
        "status": "passed" if not missing_textures else "failed",
        "root": str(bundle_root),
        "missing_texture_count": len(missing_textures),
        "missing_textures": missing_textures,
    }


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string field: {key}")
    return value


def _materialization_root_for_source(source_usd: Path) -> Path:
    external_dependencies = [
        path for path in _existing_usd_asset_dependencies(source_usd) if not _is_relative_to(path, source_usd.parent)
    ]
    if not external_dependencies:
        return source_usd.parent

    candidates = [
        source_usd.parent,
        source_usd.parent.parent,
        source_usd.parent.parent.parent,
    ]
    for candidate in candidates:
        if _is_relative_to(source_usd, candidate) and all(
            _is_relative_to(dependency, candidate) for dependency in external_dependencies
        ):
            return candidate
    return source_usd.parent


def _external_sidecar_roots(source_usd: Path, materialization_root: Path) -> tuple[Path, ...]:
    roots: set[Path] = set()
    for dependency in _existing_usd_asset_dependencies(source_usd):
        if _is_relative_to(dependency, source_usd.parent) or not _is_relative_to(
            dependency, materialization_root
        ):
            continue
        relative = dependency.relative_to(materialization_root)
        if relative.parts:
            roots.add(Path(relative.parts[0]))
    return tuple(sorted(roots))


def _existing_usd_asset_dependencies(source_usd: Path) -> tuple[Path, ...]:
    try:
        from pxr import UsdUtils
    except Exception:
        return _portable_usda_asset_dependencies(source_usd)

    try:
        _layers, assets, _unresolved = UsdUtils.ComputeAllDependencies(str(source_usd))
    except Exception:
        return _portable_usda_asset_dependencies(source_usd)

    dependencies: list[Path] = []
    for raw_asset in assets:
        path = Path(str(raw_asset))
        if path.exists():
            dependencies.append(path.resolve())
    return tuple(dependencies)


def _portable_usda_asset_dependencies(source_usd: Path) -> tuple[Path, ...]:
    text = source_usd.read_text(encoding="utf-8", errors="ignore")
    dependencies: list[Path] = []
    seen: set[Path] = set()
    for raw_ref in USD_ASSET_REF_RE.findall(text):
        if _is_external_usd_asset_reference(raw_ref):
            continue
        dependency = (source_usd.parent / raw_ref).resolve()
        if not dependency.exists() or dependency in seen:
            continue
        dependencies.append(dependency)
        seen.add(dependency)
    return tuple(dependencies)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_external_texture_reference(texture_ref: str) -> bool:
    return "://" in texture_ref or texture_ref.startswith(("/", "omniverse:", "mdl:"))


def _is_external_usd_asset_reference(asset_ref: str) -> bool:
    return "://" in asset_ref or asset_ref.startswith(("/", "omniverse:", "mdl:"))

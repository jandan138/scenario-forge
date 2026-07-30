"""Portable intake for a generated Blender room source delivery.

The producer owns Blender execution and USD export.  This adapter validates
the producer-declared artifact closure and emits only portable provenance for
the ConvertAsset/Scenario Forge handoff; it never imports Blender or a
simulator SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping


GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION = (
    "scenario-forge-generated-environment-intake/v0.1"
)

_PRODUCER_SCHEMA_VERSION = "room-source-v1"
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_ASSET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class GeneratedEnvironmentIntake:
    asset_id: str
    producer_revision: str
    run_id: str
    producer_manifest_sha256: str
    source_usd_relative_path: str
    source_usd_sha256: str
    declared_closure_sha256: str
    declared_file_count: int
    declared_total_bytes: int
    default_prim: str
    up_axis: str
    meters_per_unit: float
    zone_roots: tuple[str, ...]
    unlisted_files: tuple[str, ...]

    def to_mapping(self) -> dict[str, object]:
        source_uri = (
            "generated-environment://code-as-room/"
            f"{self.producer_revision}/{self.run_id}"
        )
        return {
            "schema_version": GENERATED_ENVIRONMENT_INTAKE_SCHEMA_VERSION,
            "asset_id": self.asset_id,
            "asset_role": "visual_static_environment",
            "license": "LicenseRef-Internal-Generated",
            "redistributable": False,
            "attribution": [
                "Code-as-Room generated environment; internal use only.",
                (
                    "Source delivery declared closure SHA-256: "
                    f"{self.declared_closure_sha256}."
                ),
            ],
            "producer": {
                "repo": "Code-as-Room",
                "revision": self.producer_revision,
                "run_id": self.run_id,
                "source_schema_version": _PRODUCER_SCHEMA_VERSION,
                "manifest_sha256": self.producer_manifest_sha256,
            },
            "source": {
                "usd": self.source_usd_relative_path,
                "usd_sha256": self.source_usd_sha256,
                "declared_closure_sha256": self.declared_closure_sha256,
                "declared_file_count": self.declared_file_count,
                "declared_total_bytes": self.declared_total_bytes,
                "default_prim": self.default_prim,
                "up_axis": self.up_axis,
                "meters_per_unit": self.meters_per_unit,
                "zone_roots": list(self.zone_roots),
            },
            "provenance": {
                "kind": "generated_blender_room",
                "visibility": "internal",
                "source_uri": source_uri,
            },
            "warnings": {"unlisted_files": list(self.unlisted_files)},
            "claim_boundary": (
                "This intake binds one producer-declared generated-room source "
                "closure. ConvertAsset still owns USD/material closure, Isaac "
                "runtime admission, and workspace-zone profiling."
            ),
        }


def build_generated_environment_intake(
    *,
    asset_id: str,
    delivery_root: str | Path,
) -> GeneratedEnvironmentIntake:
    """Validate one ``room-source-v1`` delivery and bind its declared closure."""

    _validate_asset_id(asset_id)
    root = Path(delivery_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("delivery_root must be an existing non-symlink directory")
    root = root.resolve()
    manifest_path = root / "source_manifest.json"
    manifest = _load_manifest(manifest_path)

    if manifest.get("schema_version") != _PRODUCER_SCHEMA_VERSION:
        raise ValueError("generated room source manifest schema is unsupported")
    run_id = _required_string(manifest, "run_id", "source manifest")
    producer = _required_mapping(manifest, "code_as_room", "source manifest")
    revision = _required_string(producer, "commit", "source manifest.code_as_room")
    if _COMMIT.fullmatch(revision) is None:
        raise ValueError("source manifest Code-as-Room commit must be a 40-character hash")

    assets = _required_mapping(manifest, "assets", "source manifest")
    declared = _declared_assets(assets)
    if not declared:
        raise ValueError("source manifest declares no artifacts")
    for relative_path, expected_digest in declared.items():
        candidate = _safe_delivery_file(root, relative_path)
        if _file_sha256(candidate) != expected_digest:
            raise ValueError(
                f"declared asset SHA-256 does not match: {relative_path}"
            )

    source_entry = _required_mapping(
        assets,
        "room_source_usdc",
        "source manifest.assets",
    )
    source_usd = _safe_relative_path(
        _required_string(source_entry, "path", "assets.room_source_usdc")
    )
    if PurePosixPath(source_usd).suffix.lower() not in {".usd", ".usda", ".usdc"}:
        raise ValueError("generated environment source entry must be USD")
    source_sha256 = _required_sha256(
        source_entry,
        "sha256",
        "assets.room_source_usdc",
    )

    export = _required_mapping(
        manifest,
        "usd_export_parameters",
        "source manifest",
    )
    default_prim = _required_string(
        export,
        "root_prim_path",
        "source manifest.usd_export_parameters",
    )
    if not default_prim.startswith("/") or default_prim == "/":
        raise ValueError("generated environment root prim must be an absolute prim path")
    up_axis = _required_string(
        export,
        "export_global_up_selection",
        "source manifest.usd_export_parameters",
    )
    if up_axis != "Z":
        raise ValueError("generated environment must be Z-up")

    units = _required_mapping(manifest, "units", "source manifest")
    meters_per_unit = units.get("meters_per_unit")
    if (
        not isinstance(meters_per_unit, (int, float))
        or isinstance(meters_per_unit, bool)
        or float(meters_per_unit) <= 0
    ):
        raise ValueError("source manifest meters_per_unit must be positive")

    usd_asset_paths = manifest.get("usd_asset_paths")
    if not isinstance(usd_asset_paths, list):
        raise ValueError("source manifest.usd_asset_paths must be a list")
    for index, value in enumerate(usd_asset_paths):
        if not isinstance(value, str):
            raise ValueError(f"usd_asset_paths[{index}] must be a string")
        relative = _safe_relative_path(value.removeprefix("./"))
        _safe_delivery_file(root, relative)

    zones = _required_mapping(manifest, "zones", "source manifest")
    zone_roots: list[str] = []
    for zone_name, raw_zone in zones.items():
        zone = _as_mapping(raw_zone, f"source manifest.zones.{zone_name}")
        root_name = _required_string(
            zone,
            "zone_root",
            f"source manifest.zones.{zone_name}",
        )
        if "/" in root_name or not root_name:
            raise ValueError(f"zone root must be one prim name: {root_name}")
        zone_roots.append(f"{default_prim.rstrip('/')}/{root_name}")
    if not zone_roots:
        raise ValueError("generated environment must declare at least one semantic zone")

    manifest_sha256 = _file_sha256(manifest_path)
    closure_sha256, total_bytes = _declared_closure_digest(root, declared)
    declared_paths = set(declared)
    declared_paths.add("source_manifest.json")
    unlisted = tuple(
        relative
        for relative in _all_regular_files(root)
        if relative not in declared_paths
    )
    return GeneratedEnvironmentIntake(
        asset_id=asset_id,
        producer_revision=revision,
        run_id=run_id,
        producer_manifest_sha256=manifest_sha256,
        source_usd_relative_path=source_usd,
        source_usd_sha256=source_sha256,
        declared_closure_sha256=closure_sha256,
        declared_file_count=len(declared),
        declared_total_bytes=total_bytes,
        default_prim=default_prim,
        up_axis=up_axis,
        meters_per_unit=float(meters_per_unit),
        zone_roots=tuple(sorted(zone_roots)),
        unlisted_files=unlisted,
    )


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"generated room source manifest is invalid: {path}") from exc
    return dict(_as_mapping(raw, "source manifest"))


def _declared_assets(assets: Mapping[str, object]) -> dict[str, str]:
    declared: dict[str, str] = {}
    for name, value in assets.items():
        entries = value if isinstance(value, list) else [value]
        for index, raw_entry in enumerate(entries):
            entry = _as_mapping(raw_entry, f"source manifest.assets.{name}[{index}]")
            relative = _safe_relative_path(
                _required_string(entry, "path", f"source manifest.assets.{name}")
            )
            digest = _required_sha256(
                entry,
                "sha256",
                f"source manifest.assets.{name}",
            )
            if relative in declared and declared[relative] != digest:
                raise ValueError(f"source manifest declares conflicting hashes: {relative}")
            declared[relative] = digest
    return declared


def _declared_closure_digest(
    root: Path,
    declared: Mapping[str, str],
) -> tuple[str, int]:
    digest = sha256()
    digest.update(b"scenario-forge-generated-environment-closure/v0.1\0")
    total_bytes = 0
    for relative, file_digest in sorted(declared.items()):
        size = _safe_delivery_file(root, relative).stat().st_size
        total_bytes += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), total_bytes


def _all_regular_files(root: Path) -> tuple[str, ...]:
    result: list[str] = []
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink():
            raise ValueError(f"delivery_root must not contain symlinks: {candidate}")
        if candidate.is_file():
            result.append(candidate.relative_to(root).as_posix())
    return tuple(result)


def _safe_delivery_file(root: Path, relative: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"declared delivery artifact is unavailable: {relative}")
    return candidate


def _safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("delivery artifact paths must be package-relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("delivery artifact paths must be package-relative POSIX paths")
    return path.as_posix()


def _validate_asset_id(value: str) -> None:
    if _ASSET_ID.fullmatch(value) is None or "lab" in value.lower():
        raise ValueError(
            "asset_id must be package-safe and must not contain 'lab'"
        )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _required_mapping(
    value: Mapping[str, object],
    key: str,
    field: str,
) -> Mapping[str, object]:
    return _as_mapping(value.get(key), f"{field}.{key}")


def _required_string(
    value: Mapping[str, object],
    key: str,
    field: str,
) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{field}.{key} must be a non-empty string")
    return raw


def _required_sha256(
    value: Mapping[str, object],
    key: str,
    field: str,
) -> str:
    raw = _required_string(value, key, field)
    if _SHA256_HEX.fullmatch(raw) is None:
        raise ValueError(f"{field}.{key} must be a lowercase SHA-256")
    return raw

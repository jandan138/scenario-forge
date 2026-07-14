from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from pathlib import PurePosixPath
import re
from typing import Any, Mapping


_SAFE_ASSET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_USD_SUFFIXES = frozenset({".usd", ".usda", ".usdc"})
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_USD_PRIM_PATH = re.compile(r"^/[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)*$")


@dataclass(frozen=True)
class UpstreamPackageRef:
    """Portable provenance for an externally produced package manifest."""

    producer: str
    schema_version: str
    package_id: str
    revision: str
    manifest_uri: str
    manifest_sha256: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("producer", "schema_version", "package_id", "revision"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a non-empty string")
        if (
            not isinstance(self.manifest_uri, str)
            or not self.manifest_uri
            or Path(self.manifest_uri).is_absolute()
            or self.manifest_uri.startswith("file:///")
        ):
            raise ValueError("manifest_uri must be a portable non-empty URI")
        if _SHA256.fullmatch(self.manifest_sha256) is None:
            raise ValueError("manifest_sha256 must be a lowercase sha256 digest")
        object.__setattr__(
            self,
            "metadata",
            _copy_json_mapping(self.metadata, "metadata"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "producer": self.producer,
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "revision": self.revision,
            "manifest_uri": self.manifest_uri,
            "manifest_sha256": self.manifest_sha256,
            "metadata": _copy_json_mapping(self.metadata, "metadata"),
        }


@dataclass(frozen=True)
class LocalUSDAssetSource:
    """A package input whose USD dependency closure lives in one local directory.

    ``source_usd`` identifies the canonical layer.  Package generation copies its
    containing directory as a unit so that relative USD, material, and texture
    references remain intact without teaching the neutral package layer how to
    convert those formats.
    """

    asset_id: str
    source_usd: Path
    role: str
    license: str
    source_uri: str
    attribution: tuple[str, ...] = ()
    redistributable: bool = True
    exclude_relative_paths: tuple[str, ...] = ()
    root_prim_path: str | None = None
    expected_sha256: str | None = None
    upstream_package: UpstreamPackageRef | None = None

    def __post_init__(self) -> None:
        source_usd = Path(self.source_usd)
        object.__setattr__(self, "source_usd", source_usd)

        if not _SAFE_ASSET_ID.fullmatch(self.asset_id) or self.asset_id in {".", ".."}:
            raise ValueError(
                "asset_id must be a package-safe identifier containing only letters, "
                "numbers, '.', '_', and '-'"
            )
        if not self.role:
            raise ValueError("role must be a non-empty string")
        if not self.license:
            raise ValueError("license must be a non-empty string")
        if not source_usd.is_file():
            raise ValueError(f"source_usd must be an existing file: {source_usd}")
        if source_usd.suffix.lower() not in _USD_SUFFIXES:
            raise ValueError(f"source_usd must be a USD file: {source_usd}")
        if any(not value for value in self.attribution):
            raise ValueError("attribution entries must be non-empty strings")
        if (
            self.root_prim_path is not None
            and _USD_PRIM_PATH.fullmatch(self.root_prim_path) is None
        ):
            raise ValueError("root_prim_path must be an absolute USD prim path")
        if self.expected_sha256 is not None and _SHA256.fullmatch(self.expected_sha256) is None:
            raise ValueError("expected_sha256 must be a lowercase sha256 digest")

        normalized_exclusions: list[str] = []
        for value in self.exclude_relative_paths:
            if not isinstance(value, str) or not value:
                raise ValueError("exclude_relative_paths entries must be non-empty strings")
            if any(marker in value for marker in ("*", "?", "[", "]")):
                raise ValueError("exclude_relative_paths does not accept glob patterns")
            candidate = PurePosixPath(value)
            if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
                raise ValueError("exclude_relative_paths entries must be safe relative paths")
            normalized = candidate.as_posix()
            if normalized == source_usd.name:
                raise ValueError("exclude_relative_paths cannot exclude the canonical USD")
            if normalized not in normalized_exclusions:
                normalized_exclusions.append(normalized)
        object.__setattr__(self, "exclude_relative_paths", tuple(normalized_exclusions))

    def portable_source_uri(self) -> str:
        """Return provenance that never embeds an absolute local build path."""

        value = self.source_uri.strip()
        if (
            value
            and not Path(value).is_absolute()
            and not value.lower().startswith("file:")
        ):
            return value
        return f"local-source://{self.asset_id}/{self.source_usd.name}"


def _copy_json_mapping(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
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
    raise ValueError(f"{field_name} must contain JSON-compatible values")

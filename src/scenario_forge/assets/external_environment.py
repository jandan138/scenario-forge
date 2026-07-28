"""Hash-bound intake records for externally delivered environment source trees.

This module deliberately validates only an extracted source snapshot.  USD
dependency closure, material conversion, and runtime qualification remain
producer-owned ConvertAsset work.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import re
import stat


EXTERNAL_ENVIRONMENT_INTAKE_SCHEMA_VERSION = (
    "scenario-forge-external-environment-intake/v0.1"
)

_SAFE_PUBLIC_ASSET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_USD_SUFFIXES = frozenset({".usd", ".usda", ".usdc"})
_RESTRICTED_PROVENANCE_ID = re.compile(
    r"^restricted/[A-Za-z0-9][A-Za-z0-9._/-]*$"
)


@dataclass(frozen=True)
class ExternalEnvironmentIntake:
    """Portable record for an immutable extracted environment source snapshot."""

    asset_id: str
    source_usd_relative_path: str
    source_usd_sha256: str
    source_tree_sha256: str
    source_tree_file_count: int
    source_tree_total_bytes: int
    archive_sha256: str
    restricted_provenance_id: str

    def to_mapping(self) -> dict[str, object]:
        """Return a portable record without a local path or source URL."""

        return {
            "schema_version": EXTERNAL_ENVIRONMENT_INTAKE_SCHEMA_VERSION,
            "asset_id": self.asset_id,
            "asset_role": "visual_static_environment",
            "license": "LicenseRef-Internal-Restricted",
            "redistributable": False,
            "attribution": [
                "Restricted external environment source; redistribution is not authorized."
            ],
            "source": {
                "tree_kind": "extracted_archive_tree",
                "tree_sha256": self.source_tree_sha256,
                "file_count": self.source_tree_file_count,
                "total_bytes": self.source_tree_total_bytes,
                "usd": self.source_usd_relative_path,
                "usd_sha256": self.source_usd_sha256,
            },
            "archive": {"sha256": self.archive_sha256},
            "provenance": {
                "visibility": "restricted",
                "kind": "external_archive",
                "internal_reference": self.restricted_provenance_id,
            },
            "claim_boundary": (
                "This record binds one extracted source-tree snapshot. It does not "
                "establish USD dependency closure, material correctness, runtime "
                "compatibility, license clearance, physics behavior, or task success."
            ),
        }


def build_external_environment_intake(
    *,
    asset_id: str,
    source_root: str | Path,
    source_usd_relative_path: str,
    archive_sha256: str,
    restricted_provenance_id: str,
    expected_source_sha256: str | None = None,
) -> ExternalEnvironmentIntake:
    """Validate an extracted source tree and create a portable intake record.

    ``source_usd_relative_path`` is deliberately relative to ``source_root`` so
    that the emitted record never exposes an absolute filesystem location.  The
    complete tree is hashed deterministically and symlinks are rejected: callers
    can safely treat the resulting record as a source-bound immutable snapshot.
    """

    _validate_asset_id(asset_id)
    normalized_archive_sha256 = _validated_sha256(archive_sha256, "archive_sha256")
    normalized_provenance_id = _validated_restricted_provenance_id(
        restricted_provenance_id
    )
    relative_usd = _validated_relative_usd_path(source_usd_relative_path)
    root = _validated_source_root(source_root)
    source_tree = _snapshot_source_tree(root)

    source_usd = root.joinpath(*PurePosixPath(relative_usd).parts)
    if not source_usd.is_file() or source_usd.is_symlink():
        raise ValueError(f"source USD must be a regular file inside source_root: {relative_usd}")
    source_usd_sha256 = _file_sha256(source_usd)
    if expected_source_sha256 is not None:
        expected = _validated_sha256(
            expected_source_sha256,
            "expected_source_sha256",
        )
        if expected != source_usd_sha256:
            raise ValueError("source USD hash does not match expected_source_sha256")

    return ExternalEnvironmentIntake(
        asset_id=asset_id,
        source_usd_relative_path=relative_usd,
        source_usd_sha256=source_usd_sha256,
        source_tree_sha256=source_tree.sha256,
        source_tree_file_count=source_tree.file_count,
        source_tree_total_bytes=source_tree.total_bytes,
        archive_sha256=normalized_archive_sha256,
        restricted_provenance_id=normalized_provenance_id,
    )


@dataclass(frozen=True)
class _SourceTreeSnapshot:
    sha256: str
    file_count: int
    total_bytes: int


def _validated_source_root(source_root: str | Path) -> Path:
    root = Path(source_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("source_root must be an existing non-symlink directory")
    return root.resolve()


def _validated_relative_usd_path(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise ValueError("source_usd_relative_path must be a non-empty POSIX relative path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ValueError("source_usd_relative_path must stay inside source_root")
    normalized = candidate.as_posix()
    if PurePosixPath(normalized).suffix.lower() not in _USD_SUFFIXES:
        raise ValueError("source_usd_relative_path must identify a USD file")
    return normalized


def _validate_asset_id(asset_id: str) -> None:
    if not isinstance(asset_id, str) or not _SAFE_PUBLIC_ASSET_ID.fullmatch(asset_id):
        raise ValueError(
            "asset_id must be a package-safe public identifier containing only "
            "letters, numbers, '.', '_', and '-'"
        )
    if asset_id in {".", ".."}:
        raise ValueError("asset_id must not be '.' or '..'")
    if "lab" in asset_id.lower():
        raise ValueError("asset_id must not use 'lab' in a public package identity")


def _validated_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return value


def _validated_restricted_provenance_id(value: str) -> str:
    if (
        not isinstance(value, str)
        or _RESTRICTED_PROVENANCE_ID.fullmatch(value) is None
    ):
        raise ValueError(
            "restricted_provenance_id must be a URL-free opaque reference "
            "beginning with 'restricted/'"
        )
    return value


def _snapshot_source_tree(root: Path) -> _SourceTreeSnapshot:
    hasher = sha256()
    hasher.update(b"scenario-forge-extracted-source-tree/v0.1\0")
    file_count = 0
    total_bytes = 0

    for current_root, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(current_root)
        directory_names.sort()
        file_names.sort()
        for directory_name in directory_names:
            candidate = current / directory_name
            if candidate.is_symlink():
                raise ValueError(f"source_root must not contain symlinks: {candidate}")
        for file_name in file_names:
            candidate = current / file_name
            before = candidate.lstat()
            if stat.S_ISLNK(before.st_mode):
                raise ValueError(f"source_root must not contain symlinks: {candidate}")
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"source_root must contain regular files only: {candidate}")
            relative = candidate.relative_to(root).as_posix()
            file_sha256 = _file_sha256(candidate)
            after = candidate.lstat()
            if _stat_identity(before) != _stat_identity(after):
                raise ValueError(f"source tree changed while hashing: {candidate}")
            hasher.update(relative.encode("utf-8"))
            hasher.update(b"\0")
            hasher.update(str(before.st_size).encode("ascii"))
            hasher.update(b"\0")
            hasher.update(file_sha256.encode("ascii"))
            hasher.update(b"\n")
            file_count += 1
            total_bytes += before.st_size

    if file_count == 0:
        raise ValueError("source_root must contain at least one regular file")
    return _SourceTreeSnapshot(
        sha256=hasher.hexdigest(),
        file_count=file_count,
        total_bytes=total_bytes,
    )


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_mode,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _file_sha256(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()

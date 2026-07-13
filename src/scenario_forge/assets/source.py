from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
import re


_SAFE_ASSET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_USD_SUFFIXES = frozenset({".usd", ".usda", ".usdc"})


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
        if value and not Path(value).is_absolute() and not value.startswith("file:///"):
            return value
        return f"local-source://{self.asset_id}/{self.source_usd.name}"

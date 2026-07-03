from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


def collect_asset_refs(refs: list[AssetRef]) -> dict[str, AssetRef]:
    by_id: dict[str, AssetRef] = {}
    for ref in refs:
        if ref.asset_id in by_id:
            raise ValueError(f"Duplicate asset_id: {ref.asset_id}")
        by_id[ref.asset_id] = ref
    return by_id

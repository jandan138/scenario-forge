from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def asset_completeness(package_paths: list[Path]) -> dict[str, float]:
    total = 0
    with_license = 0
    with_checksum = 0
    for package_path in package_paths:
        manifest_path = package_path / "assets" / "asset_manifest.yaml"
        if not manifest_path.exists():
            continue
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            continue
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            total += 1
            if _has_string(asset, "license"):
                with_license += 1
            if _has_string(asset, "sha256"):
                with_checksum += 1
    if total == 0:
        return {"license_completeness": 0.0, "checksum_completeness": 0.0}
    return {
        "license_completeness": round(with_license / total, 4),
        "checksum_completeness": round(with_checksum / total, 4),
    }


def _has_string(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    return isinstance(value, str) and bool(value)

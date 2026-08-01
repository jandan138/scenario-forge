"""Portable package dependency-closure evidence."""

from __future__ import annotations

from pathlib import Path
import re

from scenario_forge.assets.materials import MDL_TEXTURE_2D_RE
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.package import validate_package


PACKAGE_CLOSURE_SCHEMA_VERSION = "scenario-forge-package-closure/v0.1"
_USD_EXTENSIONS = {".usd", ".usda", ".usdc"}
_ASSET_EXTENSIONS = _USD_EXTENSIONS | {".mdl", ".png", ".jpg", ".jpeg", ".exr", ".hdr"}
_USD_ASSET_REFERENCE_RE = re.compile(rb"@([^@\r\n\x00]+)@")


def audit_package_dependency_closure(package_root: str | Path) -> dict[str, object]:
    """Check runtime-reachable USD and MDL dependencies stay inside one package root."""

    root = Path(package_root).resolve()
    unsafe: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    pending = list(_entry_layers(root))
    scanned: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in scanned:
            continue
        scanned.add(path)
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in _USD_EXTENSIONS:
            references = _usd_asset_references(path)
        elif path.suffix.lower() == ".mdl":
            contents = path.read_text(encoding="utf-8", errors="ignore")
            references = sorted(set(MDL_TEXTURE_2D_RE.findall(contents)))
        else:
            references = []
        for reference in references:
            target = _classify_reference(root, path, relative, reference, unsafe, missing)
            if target is not None and target.is_file() and target.suffix.lower() in (
                _USD_EXTENSIONS | {".mdl"}
            ):
                pending.append(target)
    return {
        "schema_version": PACKAGE_CLOSURE_SCHEMA_VERSION,
        "status": "pass" if not unsafe and not missing else "failed",
        "unsafe_references": sorted(unsafe, key=lambda item: (item["file"], item["reference"])),
        "missing_references": sorted(missing, key=lambda item: (item["file"], item["reference"])),
        "scanned_files": sorted(path.relative_to(root).as_posix() for path in scanned),
    }


def write_package_closure_evidence(package_root: str | Path) -> Path:
    """Write a closure gate that combines package validation and dependency locality."""

    root = Path(package_root)
    audit = audit_package_dependency_closure(root)
    package_validation = validate_package(root, require_asset_lock=True)
    status = "pass" if audit["status"] == "pass" and package_validation.ok else "failed"
    payload = {
        **audit,
        "status": status,
        "package_validation": {
            "status": "pass" if package_validation.ok else "failed",
            "messages": list(package_validation.messages),
        },
        "claim_boundary": (
            "This verifies package-local USD and MDL dependency references plus the "
            "Scenario Forge package manifest. It does not prove simulator load, "
            "materials rendered correctly, physics, robot reachability, or task success."
        ),
    }
    return write_yaml_artifact(root / "evidence/package_closure.yaml", payload)


def _usd_asset_references(path: Path) -> list[str]:
    raw = path.read_bytes()
    return sorted(
        {
            item.decode("utf-8", errors="ignore").strip()
            for item in _USD_ASSET_REFERENCE_RE.findall(raw)
            if _looks_like_asset_reference(item.decode("utf-8", errors="ignore").strip())
        }
    )


def _classify_reference(
    root: Path,
    source_path: Path,
    source_relative: str,
    reference: str,
    unsafe: list[dict[str, str]],
    missing: list[dict[str, str]],
) -> Path | None:
    record = {"file": source_relative, "reference": reference}
    if _is_external_reference(reference):
        unsafe.append(record)
        return None
    target = (source_path.parent / reference).resolve()
    if not _inside_root(target, root):
        unsafe.append(record)
        return None
    else:
        try:
            exists = target.exists()
        except OSError:
            exists = False
        if not exists:
            missing.append(record)
            return None
    return target


def _entry_layers(root: Path) -> tuple[Path, ...]:
    """Return runtime entry layers, falling back to all USD files for generic trees."""

    for relative in ("scene/main.usda", "asset.usd"):
        candidate = root / relative
        if candidate.is_file():
            return (candidate.resolve(),)
    return tuple(sorted(path.resolve() for path in root.rglob("*") if path.suffix.lower() in _USD_EXTENSIONS))


def _is_external_reference(reference: str) -> bool:
    lowered = reference.lower()
    return (
        reference.startswith(("/", "\\"))
        or "://" in reference
        or lowered.startswith(("file:", "omniverse:", "mdl:", "package:"))
    )


def _looks_like_asset_reference(reference: str) -> bool:
    if not reference or len(reference) > 512 or any(ord(char) < 32 for char in reference):
        return False
    path_part = reference.split("?", maxsplit=1)[0]
    return Path(path_part).suffix.lower() in _ASSET_EXTENSIONS


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

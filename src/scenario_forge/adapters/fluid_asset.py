"""Strict subprocess and handoff contract for ConvertAsset fluid assets."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


RESULT_SCHEMA = "aan.fluid_interaction_asset_result.v1"
PROFILE_SCHEMA = "aan.fluid_interaction_asset_profile.v1"
BEHAVIORS = frozenset({"reservoir", "conduit", "surface_guide"})


class FluidAssetHandoffError(ValueError):
    """Raised when a producer result is incomplete or overclaimed."""


@dataclass(frozen=True)
class FluidAssetCommandPlan:
    convert_asset_root: Path
    isaac_python: Path | None = None

    def _entry(self) -> tuple[str, str]:
        root = Path(self.convert_asset_root)
        return str(root / "scripts/isaac_python.sh"), str(root / "main.py")

    def prepare_command(self, source: Path, prim: str, output: Path) -> tuple[str, ...]:
        return (
            *self._entry(),
            "fluid-interaction-propose",
            str(source),
            "--prim",
            prim,
            "--out",
            str(output),
        )

    def qualify_command(self, proposal: Path, output: Path) -> tuple[str, ...]:
        command = (
            *self._entry(),
            "fluid-interaction-qualify",
            "--proposal",
            str(proposal),
            "--out",
            str(output),
        )
        if self.isaac_python is not None:
            command += ("--isaac-python", str(self.isaac_python))
        return command

    def derive_command(self, proposal: Path, output: Path) -> tuple[str, ...]:
        return (
            *self._entry(),
            "fluid-interaction-derive-partitions",
            "--proposal",
            str(proposal),
            "--out",
            str(output),
        )


@dataclass(frozen=True)
class FluidAssetHandoff:
    root: Path
    manifest_path: Path
    profile_path: Path
    entry_usd: Path
    entry_prim: str
    behavior: str
    manifest: Mapping[str, Any]
    profile: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FluidAssetHandoffError(f"{label} must be a mapping")
    return value


def _load(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FluidAssetHandoffError(f"cannot read {label}: {path}") from error
    return _mapping(value, label)


def _relative_file(root: Path, value: object, label: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts:
        raise FluidAssetHandoffError(f"{label} must be package-relative")
    path = root / relative
    if not path.is_file():
        raise FluidAssetHandoffError(f"missing {label}: {path}")
    return path


def load_fluid_asset_handoff(root: Path) -> FluidAssetHandoff:
    package = Path(root).resolve()
    manifest_path = package / "manifest.json"
    manifest = _load(manifest_path, "fluid asset manifest")
    if manifest.get("schema_version") != RESULT_SCHEMA:
        raise FluidAssetHandoffError("unsupported fluid asset result schema")
    if manifest.get("overall_status") != "pass" or manifest.get("blocked_reasons"):
        raise FluidAssetHandoffError("fluid asset is not qualified")
    if manifest.get("claim") != "qualified_fluid_interaction_asset":
        raise FluidAssetHandoffError("fluid asset claim is missing")
    entrypoints = _mapping(manifest.get("entrypoints"), "entrypoints")
    entry_usd = _relative_file(package, entrypoints.get("root_usd"), "root USD")
    entry_prim = str(entrypoints.get("asset_entry_prim", ""))
    if not entry_prim.startswith("/"):
        raise FluidAssetHandoffError("asset entry prim must be absolute")
    profile_record = _mapping(manifest.get("profile"), "profile")
    profile_path = _relative_file(package, profile_record.get("path"), "fluid profile")
    if sha256(profile_path.read_bytes()).hexdigest() != profile_record.get("sha256"):
        raise FluidAssetHandoffError("fluid profile hash mismatch")
    profile = _load(profile_path, "fluid profile")
    if profile.get("schema_version") != PROFILE_SCHEMA:
        raise FluidAssetHandoffError("unsupported fluid profile schema")
    behavior = str(profile.get("behavior", ""))
    if behavior not in BEHAVIORS:
        raise FluidAssetHandoffError("unsupported fluid behavior")
    if profile.get("claim") != "qualified_fluid_interaction_asset":
        raise FluidAssetHandoffError("profile qualification claim is missing")
    if profile.get("robot_policy_success") is not False:
        raise FluidAssetHandoffError("fluid asset must not claim robot policy success")
    qualification = _mapping(manifest.get("qualification"), "qualification")
    if qualification.get("status") != "pass":
        raise FluidAssetHandoffError("fluid asset qualification is not pass")
    report = _relative_file(package, qualification.get("report"), "qualification report")
    if sha256(report.read_bytes()).hexdigest() != qualification.get("report_sha256"):
        raise FluidAssetHandoffError("qualification report hash mismatch")
    return FluidAssetHandoff(
        root=package,
        manifest_path=manifest_path,
        profile_path=profile_path,
        entry_usd=entry_usd,
        entry_prim=entry_prim,
        behavior=behavior,
        manifest=manifest,
        profile=profile,
    )

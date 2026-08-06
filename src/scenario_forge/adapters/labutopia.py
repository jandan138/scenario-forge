from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from scenario_forge.assets.source import LocalUSDAssetSource, UpstreamPackageRef


_SCHEMA_VERSION = "labutopia.interactive_scene_handoff/v0.1"
_EXPECTED_RATES = {"native": 600, "genmanip": 600, "vr": 60}


class LabUtopiaInteractiveSceneHandoffError(ValueError):
    """Raised when a LabUtopia composed-scene package is not consumable."""


@dataclass(frozen=True)
class LabUtopiaInteractiveSceneHandoff:
    package_dir: Path
    manifest_path: Path
    manifest: Mapping[str, Any]

    def to_local_usd_asset_source(
        self,
        *,
        asset_id: str,
        attribution: tuple[str, ...] = (),
    ) -> LocalUSDAssetSource:
        native = self.manifest["entrypoints"]["native"]
        manifest_digest = _digest(self.manifest_path)
        return LocalUSDAssetSource(
            asset_id=asset_id,
            source_usd=self.package_dir / native["path"],
            role="interactive_composed_scene",
            license=str(self.manifest["license"]["identifier"]),
            source_uri=f"LabUtopia:{self.manifest['package_id']}",
            attribution=attribution,
            redistributable=False,
            root_prim_path=str(native["root_prim"]),
            expected_sha256=str(native["sha256"]),
            upstream_package=UpstreamPackageRef(
                producer="LabUtopia",
                schema_version=str(self.manifest["schema_version"]),
                package_id=str(self.manifest["package_id"]),
                revision=str(self.manifest["producer_revision"]),
                manifest_uri="manifest.json",
                manifest_sha256=manifest_digest,
                metadata={
                    "usage": "interactive_composed_scene",
                    "entrypoints": dict(self.manifest["entrypoints"]),
                    "particle_system": dict(self.manifest["particle_system"]),
                    "required_overlay": dict(self.manifest["required_overlay"]),
                    "runtime_qualification": dict(
                        self.manifest["runtime_qualification"]
                    ),
                    "claims": dict(self.manifest["claims"]),
                },
            ),
        )


def load_labutopia_interactive_scene_handoff(
    package_dir: str | Path,
    manifest_path: str | Path,
    *,
    producer_revision: str,
    expected_package_id: str,
    expected_entrypoints: tuple[str, ...] = ("native", "genmanip", "vr"),
) -> LabUtopiaInteractiveSceneHandoff:
    package = Path(package_dir).resolve()
    manifest_file = Path(manifest_path).resolve()
    if package not in manifest_file.parents:
        raise LabUtopiaInteractiveSceneHandoffError(
            "manifest_path must be inside package_dir"
        )
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabUtopiaInteractiveSceneHandoffError(
            "cannot read LabUtopia handoff manifest"
        ) from exc
    if not isinstance(manifest, Mapping):
        raise LabUtopiaInteractiveSceneHandoffError("manifest must be a mapping")
    if manifest.get("schema_version") != _SCHEMA_VERSION:
        raise LabUtopiaInteractiveSceneHandoffError("unsupported manifest schema")
    if manifest.get("producer") != "LabUtopia":
        raise LabUtopiaInteractiveSceneHandoffError("producer must be LabUtopia")
    if manifest.get("producer_revision") != producer_revision:
        raise LabUtopiaInteractiveSceneHandoffError("producer revision mismatch")
    if manifest.get("package_id") != expected_package_id:
        raise LabUtopiaInteractiveSceneHandoffError("package id mismatch")
    particle = _mapping(manifest.get("particle_system"), "particle_system")
    if particle.get("kind") != "PhysX_PBD" or particle.get("expected_particle_count") != 3600:
        raise LabUtopiaInteractiveSceneHandoffError("expected qualified 3600-particle PBD scene")
    license_data = _mapping(manifest.get("license"), "license")
    if license_data.get("redistributable") is not False:
        raise LabUtopiaInteractiveSceneHandoffError("handoff must remain non-redistributable")
    claims = _mapping(manifest.get("claims"), "claims")
    for claim in (
        "contact_grasp_success",
        "robot_policy_success",
        "liquid_transfer_success",
        "benchmark_success",
    ):
        if claims.get(claim) is not False:
            raise LabUtopiaInteractiveSceneHandoffError(f"unsupported positive claim: {claim}")

    closure = _mapping(manifest.get("closure"), "closure")
    raw_files = closure.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise LabUtopiaInteractiveSceneHandoffError("closure.files must not be empty")
    hashes: dict[str, str] = {}
    for index, raw in enumerate(raw_files):
        item = _mapping(raw, f"closure.files[{index}]")
        relative = _relative_path(item.get("path"), f"closure.files[{index}].path")
        digest = _sha(item.get("sha256"), f"closure.files[{index}].sha256")
        if relative in hashes:
            raise LabUtopiaInteractiveSceneHandoffError(f"duplicate closure path: {relative}")
        path = package / relative
        if not path.is_file() or _digest(path) != digest:
            raise LabUtopiaInteractiveSceneHandoffError(f"closure hash mismatch: {relative}")
        hashes[relative] = digest

    for owner in ("source", "required_overlay"):
        item = _mapping(manifest.get(owner), owner)
        relative = _relative_path(item.get("path"), f"{owner}.path")
        digest = _sha(item.get("sha256"), f"{owner}.sha256")
        if hashes.get(relative) != digest:
            raise LabUtopiaInteractiveSceneHandoffError(f"{owner} is not closure-bound")
    overlay = _mapping(manifest.get("required_overlay"), "required_overlay")
    if overlay.get("effect") != "disable_collision_on_/World/Cube":
        raise LabUtopiaInteractiveSceneHandoffError("required hidden-cube overlay is missing")

    entrypoints = _mapping(manifest.get("entrypoints"), "entrypoints")
    if set(entrypoints) != set(expected_entrypoints):
        raise LabUtopiaInteractiveSceneHandoffError("entrypoint set mismatch")
    for name in expected_entrypoints:
        item = _mapping(entrypoints[name], f"entrypoints.{name}")
        relative = _relative_path(item.get("path"), f"entrypoints.{name}.path")
        digest = _sha(item.get("sha256"), f"entrypoints.{name}.sha256")
        if hashes.get(relative) != digest:
            raise LabUtopiaInteractiveSceneHandoffError(f"entrypoint hash mismatch: {name}")
        if item.get("physics_hz") != _EXPECTED_RATES[name]:
            raise LabUtopiaInteractiveSceneHandoffError(f"entrypoint rate mismatch: {name}")
        if item.get("status") != "qualified":
            raise LabUtopiaInteractiveSceneHandoffError(f"entrypoint is not qualified: {name}")
        if item.get("hidden_cube_overlay_applied") is not True:
            raise LabUtopiaInteractiveSceneHandoffError(f"overlay not applied: {name}")
    qualification = _mapping(manifest.get("runtime_qualification"), "runtime_qualification")
    if qualification.get("status") != "qualified":
        raise LabUtopiaInteractiveSceneHandoffError("runtime qualification is not complete")
    return LabUtopiaInteractiveSceneHandoff(package, manifest_file, dict(manifest))


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LabUtopiaInteractiveSceneHandoffError(f"{field} must be a mapping")
    return value


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LabUtopiaInteractiveSceneHandoffError(f"{field} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise LabUtopiaInteractiveSceneHandoffError(f"{field} must be a safe relative path")
    return path.as_posix()


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise LabUtopiaInteractiveSceneHandoffError(f"{field} must be sha256-prefixed")
    return value


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import math

from scenario_forge.assets.source import LocalUSDAssetSource, UpstreamPackageRef


_SCHEMA_VERSIONS = {
    "labutopia.interactive_scene_handoff/v0.2",
    "labutopia.interactive_scene_handoff/v0.3",
}
_EXPECTED_RATES = {"native": 600, "genmanip": 600, "vr": 60}
_EMBEDDED_ROLES = {"source_container", "target_container", "support_table"}


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
                    **(
                        {"layout": dict(self.manifest["layout"])}
                        if "layout" in self.manifest
                        else {}
                    ),
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
    if manifest.get("schema_version") not in _SCHEMA_VERSIONS:
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
        object_prims = _mapping(
            item.get("object_prims"), f"entrypoints.{name}.object_prims"
        )
        states = _mapping(
            item.get("embedded_object_states"),
            f"entrypoints.{name}.embedded_object_states",
        )
        if set(object_prims) != _EMBEDDED_ROLES or set(states) != _EMBEDDED_ROLES:
            raise LabUtopiaInteractiveSceneHandoffError(
                f"entrypoint embedded role set mismatch: {name}"
            )
        for role in sorted(_EMBEDDED_ROLES):
            state = _mapping(
                states[role], f"entrypoints.{name}.embedded_object_states.{role}"
            )
            if state.get("prim_path") != object_prims[role]:
                raise LabUtopiaInteractiveSceneHandoffError(
                    f"entrypoint embedded prim mismatch: {name}.{role}"
                )
            _finite_vector(state.get("position_xyz_m"), 3, f"{name}.{role}.position")
            quaternion = _finite_vector(
                state.get("orientation_wxyz"), 4, f"{name}.{role}.orientation"
            )
            if not math.isclose(
                sum(value * value for value in quaternion),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-5,
            ):
                raise LabUtopiaInteractiveSceneHandoffError(
                    f"entrypoint embedded quaternion is not unit: {name}.{role}"
                )
            scale = _finite_vector(
                state.get("local_scale_xyz"), 3, f"{name}.{role}.scale"
            )
            if any(value <= 0.0 for value in scale):
                raise LabUtopiaInteractiveSceneHandoffError(
                    f"entrypoint embedded scale must be positive: {name}.{role}"
                )
            bound = _mapping(state.get("world_aabb_m"), f"{name}.{role}.world_aabb")
            lower = _finite_vector(bound.get("min"), 3, f"{name}.{role}.world_aabb.min")
            upper = _finite_vector(bound.get("max"), 3, f"{name}.{role}.world_aabb.max")
            if any(lo >= hi for lo, hi in zip(lower, upper, strict=True)):
                raise LabUtopiaInteractiveSceneHandoffError(
                    f"entrypoint embedded world AABB is empty: {name}.{role}"
                )
    qualification = _mapping(manifest.get("runtime_qualification"), "runtime_qualification")
    if qualification.get("status") != "qualified":
        raise LabUtopiaInteractiveSceneHandoffError("runtime qualification is not complete")
    if manifest.get("schema_version") == "labutopia.interactive_scene_handoff/v0.3":
        _validate_v03_layout(manifest, package, hashes)
    return LabUtopiaInteractiveSceneHandoff(package, manifest_file, dict(manifest))


def _validate_v03_layout(
    manifest: Mapping[str, Any], package: Path, hashes: Mapping[str, str]
) -> None:
    layout = _mapping(manifest.get("layout"), "layout")
    variant = layout.get("variant_id")
    expected_package_ids = {
        "source_workbench": "lab001_pbd_beaker_to_beaker_source_workbench_v3",
        "ebench_workbench": "lab001_pbd_beaker_to_beaker_ebench_workbench_v3",
    }
    if variant not in expected_package_ids:
        raise LabUtopiaInteractiveSceneHandoffError("unsupported workbench variant")
    if manifest.get("package_id") != expected_package_ids[variant]:
        raise LabUtopiaInteractiveSceneHandoffError("workbench variant package id mismatch")

    translation = _finite_vector(
        layout.get("task_group_translation_xyz_m"), 3, "layout.task_group_translation_xyz_m"
    )
    members = _mapping(layout.get("translated_members"), "layout.translated_members")
    if set(members) != {"source_container", "target_container", "particles"}:
        raise LabUtopiaInteractiveSceneHandoffError("translated member set mismatch")
    for role in sorted(members):
        item = _mapping(members[role], f"layout.translated_members.{role}")
        member_translation = _finite_vector(
            item.get("translation_xyz_m"),
            3,
            f"layout.translated_members.{role}.translation_xyz_m",
        )
        if member_translation != translation:
            raise LabUtopiaInteractiveSceneHandoffError(
                f"translated member does not follow task group: {role}"
            )

    workspace = _mapping(layout.get("robot_workspace"), "layout.robot_workspace")
    if workspace.get("profile_ref") != "manip/lift2/R5a_isaac41_vr600_v1":
        raise LabUtopiaInteractiveSceneHandoffError("unsupported robot workspace profile")
    _finite_vector(workspace.get("spawn_xyz_m"), 3, "layout.robot_workspace.spawn_xyz_m")
    _finite_vector(
        workspace.get("orientation_wxyz"), 4, "layout.robot_workspace.orientation_wxyz"
    )
    for field in ("base_footprint_radius_m", "minimum_table_clearance_m"):
        value = workspace.get(field)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) <= 0.0
        ):
            raise LabUtopiaInteractiveSceneHandoffError(
                f"layout.robot_workspace.{field} must be positive"
            )
    tabletop = _mapping(layout.get("tabletop_placement"), "layout.tabletop_placement")
    if tabletop.get("robot_facing_edge") != "x_min":
        raise LabUtopiaInteractiveSceneHandoffError("unsupported robot-facing edge")
    hard_clearance = tabletop.get("hard_edge_clearance_m")
    if (
        not isinstance(hard_clearance, (int, float))
        or isinstance(hard_clearance, bool)
        or not math.isfinite(float(hard_clearance))
        or float(hard_clearance) < 0.1
    ):
        raise LabUtopiaInteractiveSceneHandoffError("tabletop hard edge clearance is too small")

    support = _mapping(layout.get("support_table"), "layout.support_table")
    if variant == "source_workbench":
        if support.get("mode") != "embedded_source":
            raise LabUtopiaInteractiveSceneHandoffError("source workbench mode mismatch")
        return
    if support.get("mode") != "external_static_support":
        raise LabUtopiaInteractiveSceneHandoffError("eBench workbench mode mismatch")
    package_ref = _mapping(support.get("package"), "layout.support_table.package")
    required_profile = support.get("required_profile_id")
    if package_ref.get("profile_id") != required_profile:
        raise LabUtopiaInteractiveSceneHandoffError("static support profile mismatch")
    for name in ("asset", "manifest"):
        relative = _relative_path(
            package_ref.get(f"{name}_path"),
            f"layout.support_table.package.{name}_path",
        )
        digest = _sha(
            package_ref.get(f"{name}_sha256"),
            f"layout.support_table.package.{name}_sha256",
        )
        actual_digest = hashes.get(relative)
        if name == "manifest" and actual_digest is None:
            manifest_candidate = package / relative
            actual_digest = _digest(manifest_candidate) if manifest_candidate.is_file() else None
        if actual_digest != digest:
            raise LabUtopiaInteractiveSceneHandoffError(
                f"static support {name} is not closure-bound"
            )
    support_manifest_path = package / str(package_ref["manifest_path"])
    try:
        support_manifest = json.loads(support_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabUtopiaInteractiveSceneHandoffError(
            "cannot read static support manifest"
        ) from exc
    if support_manifest.get("overall_status") != "pass":
        raise LabUtopiaInteractiveSceneHandoffError("static support is not qualified")
    raw_profile = support_manifest.get("static_support_contract")
    if raw_profile is None:
        raw_profile = support_manifest.get("asset_profile")
    profile = _mapping(raw_profile, "static support profile")
    if profile.get("profile_id") != required_profile:
        raise LabUtopiaInteractiveSceneHandoffError("static support manifest profile mismatch")


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


def _finite_vector(value: object, length: int, field: str) -> tuple[float, ...]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or not all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            for item in value
        )
    ):
        raise LabUtopiaInteractiveSceneHandoffError(
            f"{field} must contain {length} finite numbers"
        )
    return tuple(float(item) for item in value)


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()

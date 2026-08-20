"""Strict subprocess and handoff contracts for ConvertAsset's simple liquid route."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


RESULT_SCHEMAS = {
    "aan.multi_liquid_sample_result.v1",
    "aan.multi_liquid_sample_result.v2",
}
FLUID_ROOT = "/__ScenarioForgeFluid"


class SimpleSdfLiquidHandoffError(ValueError):
    """Raised when a producer package is incomplete or overclaims evidence."""


@dataclass(frozen=True)
class SimpleSdfLiquidCommandPlan:
    convert_asset_root: Path
    isaac_python: Path | None = None

    def _entry(self) -> tuple[str, str]:
        root = Path(self.convert_asset_root)
        return str(root / "scripts/isaac_python.sh"), str(root / "main.py")

    def collision_propose_command(
        self, source: Path, container: str, visual_mesh: str,
        particle_scale: str, output: Path,
    ) -> tuple[str, ...]:
        return (
            *self._entry(), "simple-sdf-propose", str(source),
            "--container", container, "--visual-mesh", visual_mesh,
            "--particle-scale", particle_scale, "--out", str(output),
        )

    def collision_build_command(self, spec: Path, output: Path) -> tuple[str, ...]:
        return (
            *self._entry(), "simple-sdf-build", "--spec", str(spec),
            "--out", str(output),
        )

    def liquid_command(self, spec: Path, output: Path) -> tuple[str, ...]:
        command = (
            *self._entry(), "multi-liquid-sample", "--request", str(spec),
            "--out", str(output),
        )
        if self.isaac_python is not None:
            command += ("--isaac-python", str(self.isaac_python))
        return command


@dataclass(frozen=True)
class MultiLiquidHandoff:
    root: Path
    root_usd: Path
    overlay_usd: Path
    manifest_path: Path
    particle_system_prim: str
    sets: tuple[Mapping[str, Any], ...]
    claim: str
    manifest: Mapping[str, Any]


def _relative_file(root: Path, value: object, label: str) -> Path:
    relative = Path(str(value or ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise SimpleSdfLiquidHandoffError(f"{label} must be package-relative")
    result = root / relative
    if not result.is_file():
        raise SimpleSdfLiquidHandoffError(f"missing {label}: {result}")
    return result


def load_multi_liquid_handoff(root: Path) -> MultiLiquidHandoff:
    package = Path(root).expanduser().resolve()
    manifest_path = package / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SimpleSdfLiquidHandoffError(f"cannot read producer manifest: {manifest_path}") from error
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") not in RESULT_SCHEMAS:
        raise SimpleSdfLiquidHandoffError("unsupported multi-liquid producer schema")
    if manifest.get("overall_status") != "pass" or manifest.get("blocked_reasons"):
        raise SimpleSdfLiquidHandoffError("multi-liquid producer has not passed validation")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, Mapping):
        raise SimpleSdfLiquidHandoffError("producer entrypoints are missing")
    root_usd = _relative_file(package, entrypoints.get("root_usd"), "root USD")
    overlay = _relative_file(package, entrypoints.get("overlay_usd"), "liquid overlay")
    if manifest.get("schema_version") == "aan.multi_liquid_sample_result.v2":
        auto_samplers = entrypoints.get("auto_samplers_usd")
        if auto_samplers is not None:
            _relative_file(package, auto_samplers, "automatic sampler evidence")
    system = str(entrypoints.get("particle_system_prim", ""))
    if system != FLUID_ROOT + "/ParticleSystem":
        raise SimpleSdfLiquidHandoffError("producer must expose the one canonical ParticleSystem")
    if entrypoints.get("particle_sets_root") != FLUID_ROOT + "/ParticleSets":
        raise SimpleSdfLiquidHandoffError("producer ParticleSets root is not canonical")
    values = manifest.get("sets")
    if not isinstance(values, list) or not values:
        raise SimpleSdfLiquidHandoffError("producer sets must not be empty")
    ids: set[str] = set()
    groups: set[int] = set()
    sets: list[Mapping[str, Any]] = []
    is_v2 = manifest.get("schema_version") == "aan.multi_liquid_sample_result.v2"
    for value in values:
        if not isinstance(value, Mapping):
            raise SimpleSdfLiquidHandoffError("set record must be a mapping")
        set_id = str(value.get("id", ""))
        group = int(value.get("particle_group", -1))
        if not set_id or set_id in ids:
            raise SimpleSdfLiquidHandoffError("ParticleSet ids must be non-empty and unique")
        if group < 0 or group in groups:
            raise SimpleSdfLiquidHandoffError("each ParticleSet needs a unique particleGroup")
        if value.get("particle_prim") != f"{FLUID_ROOT}/ParticleSets/{set_id}":
            raise SimpleSdfLiquidHandoffError("ParticleSet prim does not match its id")
        if int(value.get("particle_count", 0)) <= 0:
            raise SimpleSdfLiquidHandoffError("ParticleSet must contain baked particles")
        if is_v2:
            sampler_mode = value.get("sampler_mode")
            if sampler_mode not in {"explicit_mesh", "inside_fill", "mouth_drop"}:
                raise SimpleSdfLiquidHandoffError("v2 set has an unsupported sampler mode")
            if sampler_mode != "explicit_mesh":
                ratio = float(value.get("target_fill_ratio", 0.0))
                if not 0.10 <= ratio <= 0.80:
                    raise SimpleSdfLiquidHandoffError(
                        "automatic sampler target fill ratio is outside 0.10 through 0.80"
                    )
                sampler_prim = str(value.get("sampler_mesh_prim", ""))
                if not sampler_prim.startswith("/__ScenarioForgeAutoSamplers/"):
                    raise SimpleSdfLiquidHandoffError(
                        "automatic sampler evidence prim is outside its canonical scope"
                    )
        ids.add(set_id)
        groups.add(group)
        sets.append(value)
    if is_v2 and any(item.get("sampler_mode") != "explicit_mesh" for item in sets):
        if entrypoints.get("auto_samplers_usd") is None:
            raise SimpleSdfLiquidHandoffError("automatic sampler evidence entrypoint is missing")
    validation = manifest.get("validation")
    if not isinstance(validation, Mapping) or validation.get("status") != "pass":
        raise SimpleSdfLiquidHandoffError("runtime validation is not pass")
    report = _relative_file(package, validation.get("report"), "validation report")
    if sha256(report.read_bytes()).hexdigest() != validation.get("report_sha256"):
        raise SimpleSdfLiquidHandoffError("validation report hash mismatch")
    mode = validation.get("mode")
    expected = (
        "qualified_gpu_pbd_loaded_start"
        if mode == "qualified"
        else "provisional_gpu_pbd_loaded_start"
        if mode == "quick"
        else None
    )
    if manifest.get("claim") != expected:
        raise SimpleSdfLiquidHandoffError("claim does not match validation mode")
    if manifest.get("robot_policy_success") is not False or manifest.get("benchmark_success") is not False:
        raise SimpleSdfLiquidHandoffError("producer must not claim robot or benchmark success")
    return MultiLiquidHandoff(
        package, root_usd, overlay, manifest_path, system, tuple(sets), expected, manifest
    )

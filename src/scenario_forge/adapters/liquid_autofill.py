"""Strict subprocess contract for ConvertAsset-owned liquid autofill."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping


REQUEST_SCHEMA = "aan.gpu_pbd_autofill_request.v1"
RESULT_SCHEMA = "aan.gpu_pbd_autofill_result.v1"
RECIPE_ID = "task02_r10_3_blue_gpu_pbd_v1"
RECIPE_SHA256 = "d5eec1a68cc1abf8b65bf0ae4d0adf80c2908b7a7400a2cefb9f8061e0e7b1c6"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class LiquidAutofillHandoffError(ValueError):
    """Raised when producer evidence is incomplete or overclaimed."""


@dataclass(frozen=True)
class LiquidAutofillCommandPlan:
    convert_asset_root: Path
    isaac_python: Path | None = None

    def _entry(self) -> tuple[str, str]:
        root = Path(self.convert_asset_root)
        # Static USD inspection and closure production use ConvertAsset's own
        # wrapper.  A wheel-based Isaac 4.1 Python does not expose pxr until a
        # SimulationApp exists; it is passed separately to the actual runtime
        # cold-run worker below.
        return str(root / "scripts/isaac_python.sh"), str(root / "main.py")

    def inspect_command(self, scene: Path, output: Path) -> tuple[str, ...]:
        return (
            *self._entry(),
            "liquid-inspect",
            str(scene),
            "--out",
            str(output),
        )

    def autofill_command(self, request: Path, output: Path) -> tuple[str, ...]:
        command = (
            *self._entry(),
            "liquid-autofill",
            "--request",
            str(request),
            "--out",
            str(output),
        )
        if self.isaac_python is not None:
            command += ("--isaac-python", str(self.isaac_python))
        return command

    def closure_command(
        self, scene: Path, output: Path, *, scope: str
    ) -> tuple[str, ...]:
        return (
            *self._entry(),
            "package-usd-closure",
            str(scene),
            "--out",
            str(output),
            "--scope",
            scope,
        )

    def integration_command(
        self,
        *,
        scene: Path,
        analysis: Path,
        manifest: Path,
        output: Path,
    ) -> tuple[str, ...]:
        root = Path(self.convert_asset_root)
        executable = (
            str(self.isaac_python)
            if self.isaac_python is not None
            else str(root / "scripts/isaac_python.sh")
        )
        return (
            executable,
            str(root / "scripts/observe_gpu_pbd_autofill.py"),
            "--scene",
            str(scene),
            "--analysis",
            str(analysis),
            "--manifest",
            str(manifest),
            "--run-index",
            "0",
            "--out",
            str(output),
        )


@dataclass(frozen=True)
class LiquidAutofillProducerHandoff:
    root: Path
    overlay_usd: Path
    analysis_path: Path
    recipe_path: Path
    qualification_report: Path
    manifest_path: Path
    manifest: Mapping[str, Any]
    analysis: Mapping[str, Any]

    @property
    def default_prim(self) -> str:
        return str(self.analysis["default_prim"])

    @property
    def scene_root_prim(self) -> str:
        return str(self.analysis["scene_root_prim"])


def build_request(*, scene: Path, container: str, fill: float) -> dict[str, Any]:
    source = Path(scene).resolve()
    if not source.is_file():
        raise LiquidAutofillHandoffError(f"source scene does not exist: {source}")
    if not container.startswith("/") or container == "/" or "//" in container:
        raise LiquidAutofillHandoffError("container must be an absolute USD prim path")
    fill = float(fill)
    if not 0.10 <= fill <= 0.80:
        raise LiquidAutofillHandoffError("fill must be 0.10 through 0.80")
    return {
        "schema_version": REQUEST_SCHEMA,
        "scene": str(source),
        "container_prim": container,
        "target_settled_fill_ratio": fill,
        "fill_semantics": "live_points_target_local_up_q95_height_ratio",
        "recipe_id": RECIPE_ID,
        "recipe_sha256": RECIPE_SHA256,
        "runtime": "isaac41",
        "limits": {
            "maximum_upright_error_deg": 15.0,
            "minimum_dominant_cavity_volume_ratio": 2.0,
            "maximum_particle_count": 10_000,
        },
    }


def _load_mapping(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LiquidAutofillHandoffError(f"cannot read {label}: {path}") from error
    if not isinstance(value, dict):
        raise LiquidAutofillHandoffError(f"{label} must be a JSON mapping")
    return value


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _relative_file(root: Path, value: object, label: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts:
        raise LiquidAutofillHandoffError(f"{label} must be package-relative")
    path = root / relative
    if not path.is_file():
        raise LiquidAutofillHandoffError(f"missing {label}: {path}")
    return path


def load_producer_handoff(root: Path) -> LiquidAutofillProducerHandoff:
    package = Path(root).resolve()
    manifest_path = package / "manifest.json"
    manifest = _load_mapping(manifest_path, "producer manifest")
    if manifest.get("schema_version") != RESULT_SCHEMA:
        raise LiquidAutofillHandoffError("unsupported liquid producer schema")
    if manifest.get("overall_status") != "pass" or manifest.get("blocked_reasons"):
        raise LiquidAutofillHandoffError("liquid producer candidate is not qualified")
    recipe = manifest.get("recipe")
    if not isinstance(recipe, Mapping):
        raise LiquidAutofillHandoffError("producer recipe binding is missing")
    if recipe.get("recipe_id") != RECIPE_ID or recipe.get("sha256") != RECIPE_SHA256:
        raise LiquidAutofillHandoffError("producer recipe does not match pinned Task 02 r10.3")
    qualification = manifest.get("qualification")
    if not isinstance(qualification, Mapping) or qualification.get("status") != "pass":
        raise LiquidAutofillHandoffError("producer qualification is not pass")
    report_sha = str(qualification.get("report_sha256", ""))
    if not _SHA256.fullmatch(report_sha):
        raise LiquidAutofillHandoffError("qualification report SHA-256 is invalid")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, Mapping):
        raise LiquidAutofillHandoffError("producer entrypoints are missing")
    overlay = _relative_file(package, entrypoints.get("overlay_usd"), "producer overlay")
    analysis_path = _relative_file(package, manifest.get("analysis"), "container analysis")
    recipe_path = _relative_file(package, recipe.get("path"), "liquid recipe")
    report = _relative_file(
        package, qualification.get("report"), "qualification report"
    )
    if _sha(report) != report_sha:
        raise LiquidAutofillHandoffError("qualification report hash mismatch")
    overlay_text = overlay.read_text(encoding="utf-8")
    if "@/" in overlay_text or "@file:" in overlay_text:
        raise LiquidAutofillHandoffError("producer overlay contains an absolute dependency")
    analysis = _load_mapping(analysis_path, "container analysis")
    if analysis.get("schema_version") != "aan.gpu_pbd_container_analysis.v1":
        raise LiquidAutofillHandoffError("unsupported container analysis schema")
    if not str(analysis.get("scene_root_prim", "")).startswith("/"):
        raise LiquidAutofillHandoffError("analysis lacks an absolute scene root prim")
    if not str(analysis.get("default_prim", "")):
        raise LiquidAutofillHandoffError("analysis lacks the source defaultPrim")
    return LiquidAutofillProducerHandoff(
        root=package,
        overlay_usd=overlay,
        analysis_path=analysis_path,
        recipe_path=recipe_path,
        qualification_report=report,
        manifest_path=manifest_path,
        manifest=manifest,
        analysis=analysis,
    )

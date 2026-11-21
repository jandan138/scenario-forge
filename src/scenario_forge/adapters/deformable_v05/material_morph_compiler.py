"""Portable scenario-forge v0.5 material-morph package & suite compiler (M3).

Consumes ConvertAsset `multi_engine_deformable_bundle/v0.2` manifests, applies zero-retrain
delta_q morphs or cross-object transfers via per-engine Jacobians, freezes room geometry,
object poses, and MetricsManager task goals, and emits synchronized four-engine + optional
`morphtwin_spring_3dgs` sidecar overlays.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from convert_asset.deformable_v05.contracts_v05 import MultiEngineDeformableBundleV02
from convert_asset.deformable_v05.morph_compiler import (
    apply_material_morph,
    transfer_material_response,
)


ALLOWED_MORPH_MODES: frozenset[str] = frozenset(
    {"none", "relative_delta_q", "transfer_from_asset"}
)

DEFAULT_MORPH_SWEEP_VARIANTS: dict[str, tuple[float, float]] = {
    "nominal": (0.0, 0.0),
    "soften_2x": (-math.log(2.0), -math.log(2.0)),
    "stiffen_2x": (math.log(2.0), math.log(2.0)),
    "poisson_low": (-0.35, 0.25),
    "poisson_high": (0.45, -0.20),
}


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


@dataclass(frozen=True)
class MaterialMorphSpec:
    """Declarative material morphing block inside ScenarioSpec / asset_manifest."""

    variant_id: str = "nominal"
    mode: str = "none"  # none | relative_delta_q | transfer_from_asset
    delta_q: tuple[float, float] = (0.0, 0.0)
    transfer_from_bundle_id: str | None = None
    clamp_to_trust_region: bool = True

    def __post_init__(self) -> None:
        if self.mode not in ALLOWED_MORPH_MODES:
            raise ValueError(f"Unsupported material_morph mode {self.mode!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "mode": self.mode,
            "delta_q": [float(self.delta_q[0]), float(self.delta_q[1])],
            "transfer_from_bundle_id": self.transfer_from_bundle_id,
            "clamp_to_trust_region": bool(self.clamp_to_trust_region),
        }


def _write_yaml(path: Path, data: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_scene_main_usda(
    path: Path,
    *,
    task_id: str,
    asset_id: str,
    spawn_xyz: tuple[float, float, float],
    target_xyz: tuple[float, float, float],
    variant_id: str,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    usda = f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    custom string scenarioForge:taskId = "{task_id}"
    custom string scenarioForge:materialMorphVariant = "{variant_id}"
    def Xform "{asset_id}"
    {{
        double3 xformOp:translate = ({spawn_xyz[0]:.6f}, {spawn_xyz[1]:.6f}, {spawn_xyz[2]:.6f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}
    def Xform "TargetZone"
    {{
        double3 xformOp:translate = ({target_xyz[0]:.6f}, {target_xyz[1]:.6f}, {target_xyz[2]:.6f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}
}}
'''
    path.write_text(usda, encoding="utf-8")
    return _sha256_file(path)


def build_morphed_scenario_package(
    *,
    task_id: str,
    bundle: MultiEngineDeformableBundleV02,
    bundle_manifest_path: str | Path,
    out_package_dir: str | Path,
    morph: MaterialMorphSpec | None = None,
    donor_bundle: MultiEngineDeformableBundleV02 | None = None,
    spawn_xyz: tuple[float, float, float] = (0.42, -0.06, 0.82),
    target_xyz: tuple[float, float, float] = (0.42, 0.14, 0.82),
    robot_embodiment: str = "lift2_r5a_bimanual",
) -> dict[str, Any]:
    """Compile one portable scenario-forge v0.5 package with morphed multi-engine overlays."""
    pkg = Path(out_package_dir)
    pkg.mkdir(parents=True, exist_ok=True)
    m_spec = morph or MaterialMorphSpec()
    b_manifest = Path(bundle_manifest_path)

    adapters_dir = pkg / "adapters"
    if m_spec.mode == "transfer_from_asset":
        if donor_bundle is None:
            raise ValueError("donor_bundle is required when mode == 'transfer_from_asset'")
        morph_result = transfer_material_response(
            donor_bundle=donor_bundle,
            target_bundle=bundle,
            clamp_to_trust_region=m_spec.clamp_to_trust_region,
            out_overlay_dir=adapters_dir,
        )
    elif m_spec.mode == "relative_delta_q":
        morph_result = apply_material_morph(
            bundle=bundle,
            delta_q=m_spec.delta_q,
            clamp_to_trust_region=m_spec.clamp_to_trust_region,
            out_overlay_dir=adapters_dir,
        )
    else:
        morph_result = apply_material_morph(
            bundle=bundle,
            delta_q=(0.0, 0.0),
            clamp_to_trust_region=True,
            out_overlay_dir=adapters_dir,
        )

    # Emit sidecar morph config if present
    sidecar_rel: str | None = None
    if "morphtwin_spring_3dgs" in morph_result.get("optional_sidecars", {}):
        sc_path = adapters_dir / "morphtwin_spring_3dgs" / "morphed_carrier.json"
        sc_path.parent.mkdir(parents=True, exist_ok=True)
        sc_path.write_text(
            json.dumps(
                {
                    "asset_id": bundle.asset_id,
                    "variant_id": m_spec.variant_id,
                    "source_sidecar": bundle.optional_sidecars["morphtwin_spring_3dgs"],
                    "morph_controls": morph_result["optional_sidecars"]["morphtwin_spring_3dgs"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        sidecar_rel = sc_path.relative_to(pkg).as_posix()

    physics_kind = (
        "deformable_video_twin" if bundle.video_provenance is not None else "deformable_v05"
    )

    scene_sha = _write_scene_main_usda(
        pkg / "scene" / "main.usda",
        task_id=task_id,
        asset_id=bundle.asset_id,
        spawn_xyz=spawn_xyz,
        target_xyz=target_xyz,
        variant_id=m_spec.variant_id,
    )
    instances_sha = _write_yaml(
        pkg / "scene" / "instances.yaml",
        {
            "schema_version": "scenario-instances/v0.2",
            "instances": [
                {
                    "instance_id": bundle.asset_id,
                    "physics_kind": physics_kind,
                    "structural_family": bundle.source.structural_family,
                    "spawn_xyz_m": [float(v) for v in spawn_xyz],
                    "target_xyz_m": [float(v) for v in target_xyz],
                }
            ],
        },
    )
    task_sha = _write_yaml(
        pkg / "task" / "task.yaml",
        {
            "schema_version": "scenario-task/v0.2",
            "task_id": task_id,
            "robot_embodiment": robot_embodiment,
            "primary_object": bundle.asset_id,
            "target_xyz_m": [float(v) for v in target_xyz],
            "goal_tolerance_m": 0.035,
            "primary_metric": "intact_task_success",
        },
    )
    _write_yaml(
        pkg / "task" / "safety_rules.yaml",
        {
            "schema_version": "scenario-safety-rules/v0.2",
            "objects": {
                bundle.asset_id: bundle.integrity_budget.to_dict(),
            },
        },
    )
    _write_yaml(
        pkg / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": bundle.asset_id,
                    "physics_kind": physics_kind,
                    "structural_family": bundle.source.structural_family,
                    "multi_engine_bundle_schema": bundle.schema_version,
                    "multi_engine_bundle_manifest": b_manifest.as_posix(),
                    "material_morph": m_spec.to_dict(),
                    "morphed_target_continuum": morph_result["target_continuum"],
                    "optional_sidecar_relpath": sidecar_rel,
                }
            ],
        },
    )
    _write_yaml(
        pkg / "locks" / "asset_lock.yaml",
        {
            "schema_version": "asset-lock/v0.2",
            "locks": {
                bundle.asset_id: {
                    "bundle_manifest_sha256": _sha256_file(b_manifest) if b_manifest.exists() else "",
                    "source_asset_sha256": bundle.source.source_asset_sha256,
                    "instances_sha256": instances_sha,
                    "task_sha256": task_sha,
                    "scene_main_sha256": scene_sha,
                }
            },
        },
    )
    _write_yaml(
        pkg / "metrics" / "metrics.yaml",
        {
            "schema_version": "scenario-metrics/v0.2",
            "primary_metric": "intact_task_success",
            "protocols": ["protocol_a", "protocol_b", "protocol_c1"]
            + (["protocol_c2"] if bundle.video_provenance is not None else []),
        },
    )
    _write_yaml(
        pkg / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "task_id": task_id,
            "variant_id": m_spec.variant_id,
            "physics_kind": physics_kind,
            "material_morph": m_spec.to_dict(),
            "engines": sorted(morph_result["engines"].keys()),
            "sidecars": sorted(morph_result.get("optional_sidecars", {}).keys()),
        },
    )

    real2sim_path: str | None = None
    if bundle.video_provenance is not None:
        r2s_payload = {
            "schema_version": "real2sim-result/v0.1",
            "result_id": f"r2s_{task_id}_{m_spec.variant_id}",
            "source": {
                "modality": bundle.video_provenance.get("observation_manifest", {}).get(
                    "modality", "video"
                ),
                "video_provenance": bundle.video_provenance,
            },
            "package": {
                "package_dir": pkg.as_posix(),
                "task_id": task_id,
                "variant_id": m_spec.variant_id,
            },
            "assets": [
                {
                    "asset_id": bundle.asset_id,
                    "physics_kind": physics_kind,
                    "deformable_bundle_manifest": b_manifest.as_posix(),
                }
            ],
            "instances": [
                {
                    "instance_id": bundle.asset_id,
                    "spawn_xyz_m": [float(v) for v in spawn_xyz],
                }
            ],
        }
        r2s_file = pkg / "real2sim_result.json"
        r2s_file.write_text(json.dumps(r2s_payload, indent=2), encoding="utf-8")
        real2sim_path = r2s_file.as_posix()

    return {
        "task_id": task_id,
        "variant_id": m_spec.variant_id,
        "package_dir": pkg.as_posix(),
        "instances_sha256": instances_sha,
        "task_sha256": task_sha,
        "morph_result": morph_result,
        "real2sim_result_path": real2sim_path,
    }


def build_material_morph_suite(
    *,
    task_id: str,
    bundle: MultiEngineDeformableBundleV02,
    bundle_manifest_path: str | Path,
    out_suite_dir: str | Path,
    variants: Mapping[str, tuple[float, float]] = DEFAULT_MORPH_SWEEP_VARIANTS,
    donor_bundle: MultiEngineDeformableBundleV02 | None = None,
    spawn_xyz: tuple[float, float, float] = (0.42, -0.06, 0.82),
    target_xyz: tuple[float, float, float] = (0.42, 0.14, 0.82),
) -> dict[str, Any]:
    """Compile a full frozen-geometry material-morph sweep suite (+ optional donor transfer)."""
    suite_dir = Path(out_suite_dir)
    suite_dir.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict[str, Any]] = {}

    for var_id, dq in variants.items():
        mode = "none" if var_id == "nominal" else "relative_delta_q"
        spec = MaterialMorphSpec(variant_id=var_id, mode=mode, delta_q=(float(dq[0]), float(dq[1])))
        entries[var_id] = build_morphed_scenario_package(
            task_id=task_id,
            bundle=bundle,
            bundle_manifest_path=bundle_manifest_path,
            out_package_dir=suite_dir / var_id,
            morph=spec,
            spawn_xyz=spawn_xyz,
            target_xyz=target_xyz,
        )

    if donor_bundle is not None:
        t_id = f"transfer_{donor_bundle.asset_id}"
        t_spec = MaterialMorphSpec(
            variant_id=t_id,
            mode="transfer_from_asset",
            transfer_from_bundle_id=donor_bundle.asset_id,
        )
        entries[t_id] = build_morphed_scenario_package(
            task_id=task_id,
            bundle=bundle,
            bundle_manifest_path=bundle_manifest_path,
            out_package_dir=suite_dir / t_id,
            morph=t_spec,
            donor_bundle=donor_bundle,
            spawn_xyz=spawn_xyz,
            target_xyz=target_xyz,
        )

    # Verify geometry/layout/task freeze invariance across every variant in the suite
    instance_shas = {e["instances_sha256"] for e in entries.values()}
    task_shas = {e["task_sha256"] for e in entries.values()}
    geometry_and_task_frozen = len(instance_shas) == 1 and len(task_shas) == 1

    suite_manifest = {
        "schema_version": "scenario-material-morph-suite/v0.5",
        "task_id": task_id,
        "asset_id": bundle.asset_id,
        "geometry_and_task_frozen": geometry_and_task_frozen,
        "variant_ids": list(entries.keys()),
        "variants": entries,
    }
    manifest_path = suite_dir / "suite_manifest.json"
    manifest_path.write_text(json.dumps(suite_manifest, indent=2), encoding="utf-8")
    return suite_manifest


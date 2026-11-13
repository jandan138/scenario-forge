#!/usr/bin/env python3
"""IKA-OVEN-125-Grade 10-Gate Acceptance Suite for Multi-DOF Articulated Hero Assets.

Codifies `GEN-008` (`docs/standards/asset-generation.md`) and
`skills/hunyuan-isaac-articulation-assets/references/ika-grade-acceptance-and-visual-critic.md`:
  G1:  Static single-root articulation contract, explicit PhysX applied schemas & BFS joint order
  G2:  Fresh-process reopen, self-containment, CAD density & frozen E-grade WxDxH bounds
  G3:  Pairwise button/control rest+pressed clearance & closed-seal/lid non-occlusion
  G4:  Isaac Sim single Articulation discovery, JointStateAPI init & 120-step zero-drift settle
  G5:  All-DOF bidirectional travel, simultaneous composite Press+Rotate knob & spring-return keys
  G6:  Direct handle/drawer world-force smoke (`physics_smoke`) & fixed-base zero drift
  G7:  600-frame gravity load-bearing stability with companion rigid workpieces (`USD-008`)
  G8:  Loaded rail extraction & hollow-tunnel transport under live PhysX contact
  G9a: Automated objective appearance floor (non-box primary meshes, >=3 PBR classes, UI & exposure)
  G9b: Independent blind-review visual critic loop (`author != critic`, 5 dims >= 8.0, SHA-256 bound)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FACTORY_ROOT = Path("external_artifacts/out_of_domain_factory_r2_20261113")
DEFAULT_EVIDENCE_ROOT = Path("external_artifacts/asset_evidence")
DEFAULT_CRITIQUE_DIR = Path(
    "external_artifacts/out_of_domain_factory_r3_20261113/hero_g9b_acceptance"
)
CHECK_ART_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "hunyuan-isaac-articulation-assets"
    / "scripts"
    / "check_articulation_usd.py"
)
ISAAC_KIT_PYTHON = Path("/isaac-sim/python.sh")
ISAAC41_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python3.10"
)


def resolve_isaac_python(explicit: Path | None = None) -> Path:
    """Resolve the Isaac Sim Python executable from CLI arg, ISAAC_PYTHON env, or host defaults."""
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env_py = os.environ.get("ISAAC_PYTHON", "").strip()
    if env_py:
        candidates.append(Path(env_py))
    candidates.extend((ISAAC41_PYTHON, ISAAC_KIT_PYTHON))
    for cand in candidates:
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        "Isaac Sim Python executable not found. Set ISAAC_PYTHON=/path/to/isaac/python "
        "or pass --static-only to run standalone OpenUSD + Blender Cycles verification."
    )


def _resolve_usd_python() -> str:
    """Return a Python interpreter with `pxr` (`usd-core`) available."""
    env_usd_py = os.environ.get("SCENARIO_FORGE_PYTHON", "").strip()
    for cand in (env_usd_py, sys.executable, str(ISAAC_KIT_PYTHON)):
        if not cand or not Path(cand).is_file():
            continue
        probe = subprocess.run(
            [cand, "-c", "import pxr"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0:
            return cand
    return sys.executable


def _inspect_stage_static_usd_core(usd_path: Path, hspec: Mapping[str, Any]) -> dict[str, Any]:
    """Compute counts, closed visual bounds, and control AABBs via pure `usd-core` (`pxr`)."""
    from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"Failed to open USD stage: {usd_path}")

    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
        useExtentsHint=False,
    )
    root_prim = stage.GetPrimAtPath("/AssetRoot")
    if not root_prim.IsValid():
        raise RuntimeError(f"Missing /AssetRoot prim in {usd_path}")

    root_range = bbox_cache.ComputeWorldBound(root_prim).ComputeAlignedRange()
    mn, mx = root_range.GetMin(), root_range.GetMax()
    closed_visual_bounds = {
        "min": [float(mn[0]), float(mn[1]), float(mn[2])],
        "max": [float(mx[0]), float(mx[1]), float(mx[2])],
    }

    control_rest_aabbs: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {}
    for link_name in hspec.get("control_links", ()):
        lprim = stage.GetPrimAtPath(f"/AssetRoot/Links/{link_name}")
        if lprim.IsValid():
            cr = bbox_cache.ComputeWorldBound(lprim).ComputeAlignedRange()
            cmn, cmx = cr.GetMin(), cr.GetMax()
            control_rest_aabbs[str(link_name)] = (
                (float(cmn[0]), float(cmn[1]), float(cmn[2])),
                (float(cmx[0]), float(cmx[1]), float(cmx[2])),
            )

    links = 0
    revolute = 0
    prismatic = 0
    fixed = 0
    colliders = 0
    visual_prims = 0
    meshes = 0
    materials = 0
    bad_asset_paths: list[str] = []

    for prim in stage.Traverse():
        pstr = str(prim.GetPath())
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            links += 1
        if prim.IsA(UsdPhysics.RevoluteJoint):
            revolute += 1
        elif prim.IsA(UsdPhysics.PrismaticJoint):
            prismatic += 1
        elif prim.IsA(UsdPhysics.FixedJoint):
            fixed += 1
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            colliders += 1
        if prim.IsA(UsdShade.Material):
            materials += 1
        if "/Visual/" in pstr and prim.IsA(UsdGeom.Gprim):
            purpose = UsdGeom.Imageable(prim).ComputePurpose()
            if purpose != UsdGeom.Tokens.guide:
                visual_prims += 1
                if prim.IsA(UsdGeom.Mesh):
                    meshes += 1

        for attr in prim.GetAttributes():
            val = attr.Get()
            if isinstance(val, Sdf.AssetPath) and val.path:
                raw_ap = str(val.path)
                if raw_ap.startswith("/") or "/cpfs/" in raw_ap:
                    bad_asset_paths.append(raw_ap)
                elif not (usd_path.parent / raw_ap).is_file():
                    bad_asset_paths.append(raw_ap)

    return {
        "counts": {
            "links": links,
            "revolute": revolute,
            "prismatic": prismatic,
            "fixed": fixed,
            "colliders": colliders,
            "visual_prims": visual_prims,
            "meshes": meshes,
            "materials": materials,
            "usd_size_bytes": usd_path.stat().st_size,
        },
        "closed_visual_bounds": closed_visual_bounds,
        "control_rest_aabbs": control_rest_aabbs,
        "bad_asset_paths": bad_asset_paths,
        "g9_rtx_render": {},
    }

REQUIRED_CRITIQUE_DIMENSIONS = (
    "silhouette_and_proportion",
    "secondary_mechanism_craft",
    "pbr_material_hierarchy",
    "ui_silkscreen_legibility",
    "artifact_free_integrity",
)

DEFAULT_PRIMARY_MESH_KEYWORDS = (
    "shell",
    "housing",
    "plinth",
    "chassis",
    "body",
    "lid",
    "hood",
    "cassette",
    "tray",
    "lever",
    "dial",
    "rotor",
    "nose",
    "flap",
)

DEFAULT_UI_EXCLUDE_KEYWORDS = (
    "legend",
    "label",
    "text",
    "monogram",
    "badge",
    "mark",
    "tick",
    "lcd",
    "oled",
    "tft",
    "seg",
)


# ---------------------------------------------------------------------------
# Pure-Python Spec Loading, Geometry, Appearance & Critique Evaluators
# ---------------------------------------------------------------------------

def _sha256_prefixed(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _resolve_repo_path(raw_path: str | Path, base_root: Path) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else (base_root / p)


def _normalize_hero_spec(raw: Mapping[str, Any]) -> dict[str, Any]:
    required_keys = (
        "slug",
        "asset_id",
        "expected_wdh_m",
        "closed_joint_targets_rad_or_m",
        "control_links",
        "spring_buttons",
        "force_smoke",
        "load_tests",
        "rtx_camera",
    )
    missing = [k for k in required_keys if k not in raw]
    if missing:
        raise ValueError(f"Hero spec missing required fields: {missing}")

    spec = dict(raw)
    spec.setdefault("evidence_slug", spec["slug"])
    spec.setdefault("envelope_tol_m", 0.0025)
    spec.setdefault("min_control_gap_m", 0.003)
    spec.setdefault("composite_knob", None)
    spec.setdefault("rail_transport_test", None)
    spec.setdefault("g9a_appearance", {})
    spec.setdefault("g9b_visual_critic", {})
    return spec


def load_hero_acceptance_specs(
    spec_config: Path | Sequence[Path] | None = None,
) -> list[dict[str, Any]]:
    """Load declarative hero specs from YAML/JSON file(s) or a directory, or default specs."""
    if spec_config is None:
        return [dict(s) for s in HERO_ACCEPTANCE_SPECS]

    paths: list[Path] = []
    raw_items = [spec_config] if isinstance(spec_config, (str, Path)) else list(spec_config)
    for item in raw_items:
        p = Path(item)
        if p.is_dir():
            files = sorted(
                [
                    *p.glob("*.yaml"),
                    *p.glob("*.yml"),
                    *p.glob("*.json"),
                ]
            )
            if not files:
                raise FileNotFoundError(f"No spec YAML/JSON files found in directory: {p}")
            paths.extend(files)
        else:
            if not p.is_file():
                raise FileNotFoundError(f"Spec config file not found: {p}")
            paths.append(p)

    specs: list[dict[str, Any]] = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        data = json.loads(text) if p.suffix.lower() == ".json" else yaml.safe_load(text)
        if not isinstance(data, Mapping):
            raise ValueError(f"Spec config must be a mapping in {p}")
        if "heroes" in data:
            heroes = data["heroes"]
            if not isinstance(heroes, list):
                raise ValueError(f"`heroes` must be a list in {p}")
            for h in heroes:
                specs.append(_normalize_hero_spec(h))
        else:
            specs.append(_normalize_hero_spec(data))
    return specs


def aabb_axis_gap(
    box_a: tuple[Sequence[float], Sequence[float]],
    box_b: tuple[Sequence[float], Sequence[float]],
) -> float:
    """Signed separation between two 3D AABBs: >0 means separated, <0 means penetrating."""
    amin, amax = box_a
    bmin, bmax = box_b
    axis_seps = [
        max(float(bmin[i]) - float(amax[i]), float(amin[i]) - float(bmax[i]))
        for i in range(3)
    ]
    if any(sep > 0.0 for sep in axis_seps):
        pos = [max(0.0, sep) for sep in axis_seps]
        return math.sqrt(sum(d * d for d in pos))
    return max(axis_seps)


def evaluate_pairwise_control_clearances(
    control_aabbs: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    *,
    min_gap_m: float = 0.003,
) -> dict[str, Any]:
    names = sorted(control_aabbs.keys())
    pairs: list[dict[str, Any]] = []
    overlap_count = 0
    min_observed = float("inf")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            gap = aabb_axis_gap(control_aabbs[na], control_aabbs[nb])
            min_observed = min(min_observed, gap)
            if gap < 0.0:
                overlap_count += 1
            pairs.append(
                {
                    "pair": f"{na} <-> {nb}",
                    "gap_m": round(gap, 6),
                    "passed": gap >= min_gap_m,
                }
            )
    if not pairs:
        min_observed = 0.0
    passed = overlap_count == 0 and (not pairs or min_observed >= min_gap_m)
    return {
        "passed": passed,
        "pair_count": len(pairs),
        "overlap_count": overlap_count,
        "min_gap_m": round(min_observed, 6),
        "required_min_gap_m": float(min_gap_m),
        "pairs": pairs,
    }


def evaluate_frozen_envelope_bounds(
    *,
    measured_min: Sequence[float],
    measured_max: Sequence[float],
    expected_wdh_m: Sequence[float],
    tol_m: float = 0.0025,
) -> dict[str, Any]:
    dims = [float(measured_max[i]) - float(measured_min[i]) for i in range(3)]
    errs = [abs(dims[i] - float(expected_wdh_m[i])) for i in range(3)]
    z_floor_err = abs(float(measured_min[2]) - 0.0)
    max_err = max([*errs, z_floor_err])
    return {
        "passed": max_err <= float(tol_m),
        "measured_wdh_m": [round(v, 5) for v in dims],
        "expected_wdh_m": [round(float(v), 5) for v in expected_wdh_m],
        "axis_abs_errors_mm": [round(e * 1000.0, 3) for e in errs],
        "z_floor_abs_error_mm": round(z_floor_err * 1000.0, 3),
        "max_abs_error_mm": round(max_err * 1000.0, 3),
        "tolerance_mm": round(float(tol_m) * 1000.0, 3),
    }


def evaluate_g1_bfs_and_physx_schemas(
    *,
    link_count: int,
    physx_rigid_body_count: int,
    physx_articulation_count: int,
    joints_ordered: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify explicit PhysX applied schemas and monotonic BFS joint depth ordering (`ART-005`/`GEN-008`)."""
    link_depth: dict[str, int] = {}
    joint_depths: list[dict[str, Any]] = []
    unresolved: list[str] = []

    remaining = list(joints_ordered)
    # Resolve root and depth levels iteratively so depth lookup does not depend on input order
    for j in remaining:
        b0 = j.get("body0")
        b1 = j.get("body1")
        if b0 is None and b1:
            link_depth[str(b1)] = 0

    for _ in range(len(remaining) + 1):
        progressed = False
        for j in remaining:
            b0 = j.get("body0")
            b1 = j.get("body1")
            if b0 and str(b0) in link_depth and b1 and str(b1) not in link_depth:
                link_depth[str(b1)] = link_depth[str(b0)] + 1
                progressed = True
        if not progressed:
            break

    depths_seq: list[int] = []
    for j in joints_ordered:
        name = str(j.get("name", ""))
        b0 = j.get("body0")
        b1 = j.get("body1")
        if b0 is None and b1 and str(b1) in link_depth:
            d = 0
        elif b0 and str(b0) in link_depth:
            d = link_depth[str(b0)] + 1
        else:
            d = -1
            unresolved.append(name)
        depths_seq.append(d)
        joint_depths.append({"name": name, "depth": d, "body0": b0, "body1": b1})

    bfs_order_valid = (
        len(unresolved) == 0
        and len(depths_seq) > 0
        and all(depths_seq[i] >= depths_seq[i - 1] for i in range(1, len(depths_seq)))
    )
    physx_schemas_valid = (
        physx_articulation_count == 1 and physx_rigid_body_count >= max(1, link_count)
    )
    return {
        "passed": bfs_order_valid and physx_schemas_valid,
        "bfs_order_valid": bfs_order_valid,
        "physx_schemas_valid": physx_schemas_valid,
        "physx_rigid_body_count": int(physx_rigid_body_count),
        "expected_min_rigid_bodies": int(link_count),
        "physx_articulation_count": int(physx_articulation_count),
        "unresolved_joints": unresolved,
        "joint_depths": joint_depths,
    }


def _classify_pbr_material(mat: Mapping[str, Any]) -> str:
    metallic = float(mat.get("metallic", 0.0))
    roughness = float(mat.get("roughness", 0.5))
    opacity = float(mat.get("opacity", 1.0))
    emissive = mat.get("emissive") or (0.0, 0.0, 0.0)
    max_emissive = max(float(c) for c in emissive)
    if max_emissive > 0.01:
        return "emissive_display_or_indicator"
    if opacity < 0.99:
        return "translucent_glass_or_acrylic"
    if metallic >= 0.5:
        return "metallic"
    if metallic < 0.3 and roughness >= 0.30:
        return "matte_polymer_or_elastomer"
    return "glossy_coated_or_painted"


def _compute_png_luma_stats(png_path: Path) -> tuple[float, float]:
    with Image.open(png_path) as img:
        arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return float(luma.mean()), float(luma.std())


def evaluate_g9a_objective_appearance(
    *,
    appearance_meta: Mapping[str, Any],
    studio_dir: Path,
    rtx_info: Mapping[str, Any],
    g9a_config: Mapping[str, Any] | None = None,
    usd_dir: Path | None = None,
    require_rtx: bool = True,
) -> dict[str, Any]:
    """Evaluate `GEN-008` `G9a` automated objective appearance floor."""
    cfg = dict(g9a_config or {})
    keywords = tuple(
        str(k).lower()
        for k in cfg.get("primary_mesh_keywords", DEFAULT_PRIMARY_MESH_KEYWORDS)
    )
    min_mat_classes = int(cfg.get("min_material_classes", 3))
    ui_mode = str(cfg.get("ui_representation", "uv_texture")).lower()
    min_tex_std = float(cfg.get("min_texture_std", 8.0))
    min_ui_vector_meshes = int(cfg.get("min_ui_vector_meshes", 3))
    min_cycles_bytes = int(cfg.get("min_cycles_png_bytes", 40_000))
    min_rtx_mean = float(cfg.get("min_rtx_mean_luma", 14.0))
    min_rtx_std = float(cfg.get("min_rtx_std_luma", 10.0))

    # 1. Non-box primary shell/lid/knob meshes (excluding UI silkscreen/label micro-geometry)
    visual_meshes = list(appearance_meta.get("visual_meshes", ()))
    ui_exclude = tuple(
        str(k).lower()
        for k in cfg.get("ui_exclude_keywords", DEFAULT_UI_EXCLUDE_KEYWORDS)
    )
    primary_meshes = [
        m
        for m in visual_meshes
        if any(kw in str(m.get("name", "")).lower() for kw in keywords)
        and not any(ex in str(m.get("name", "")).lower() for ex in ui_exclude)
    ]
    if not primary_meshes:
        primary_meshes = [m for m in visual_meshes if str(m.get("prim_type", "")) in ("Mesh", "Cube")]

    box_violations: list[str] = []
    for m in primary_meshes:
        ptype = str(m.get("prim_type", "Mesh"))
        verts = int(m.get("vertices", 0))
        faces = int(m.get("faces", 0))
        unorm = int(m.get("unique_normals", 0))
        if ptype == "Cube" or verts < 10 or faces < 10 or unorm < 8:
            box_violations.append(str(m.get("name", "unknown")))
    non_box_ok = len(primary_meshes) > 0 and len(box_violations) == 0

    # 2. >= 3 differentiated UsdPreviewSurface material classes
    materials = list(appearance_meta.get("materials", ()))
    mat_classes = sorted({_classify_pbr_material(m) for m in materials})
    materials_ok = len(mat_classes) >= min_mat_classes

    # 3. UI / screen / silkscreen backing check
    ui_details: dict[str, Any] = {"mode": ui_mode}
    if ui_mode == "none":
        ui_ok = True
    elif ui_mode == "uv_texture":
        tex_entries = list(appearance_meta.get("texture_files", ()))
        tex_checks: list[dict[str, Any]] = []
        base_dir = usd_dir or studio_dir
        for raw_tex in tex_entries:
            tpath = _resolve_repo_path(str(raw_tex), base_dir)
            if not tpath.is_file():
                tex_checks.append({"path": str(tpath), "exists": False, "std_luma": 0.0})
                continue
            mean_l, std_l = _compute_png_luma_stats(tpath)
            tex_checks.append(
                {
                    "path": str(tpath),
                    "exists": True,
                    "mean_luma": round(mean_l, 2),
                    "std_luma": round(std_l, 2),
                }
            )
        ui_ok = any(c["exists"] and c["std_luma"] > min_tex_std for c in tex_checks)
        ui_details["textures"] = tex_checks
        ui_details["min_texture_std"] = min_tex_std
    elif ui_mode == "vector_3d":
        vector_ui_meshes = [
            m
            for m in visual_meshes
            if str(m.get("prim_type", "Mesh")) == "Mesh"
            and int(m.get("faces", 0)) >= 20
            and int(m.get("vertices", 0)) >= 24
        ]
        has_ui_shader = (
            "emissive_display_or_indicator" in mat_classes or len(materials) >= 6
        )
        ui_ok = len(vector_ui_meshes) >= min_ui_vector_meshes and has_ui_shader
        ui_details["vector_ui_mesh_count"] = len(vector_ui_meshes)
        ui_details["min_ui_vector_meshes"] = min_ui_vector_meshes
        ui_details["has_ui_shader"] = has_ui_shader
    else:
        raise ValueError(f"Unsupported g9a ui_representation: {ui_mode}")

    # 4. Dual-renderer (Blender Cycles AgX 4-view + Isaac RTX) exposure/contrast
    studio_names = ("preview_iso.png", "preview_front.png", "preview_detail.png", "preview_ui.png")
    studio_checks: list[dict[str, Any]] = []
    for fname in studio_names:
        fpath = studio_dir / fname
        if not fpath.is_file():
            studio_checks.append({"file": fname, "exists": False, "passed": False})
            continue
        size_b = fpath.stat().st_size
        mean_l, std_l = _compute_png_luma_stats(fpath)
        ok_view = (
            size_b >= min_cycles_bytes
            and 10.0 <= mean_l <= 245.0
            and std_l >= 10.0
        )
        studio_checks.append(
            {
                "file": fname,
                "exists": True,
                "size_bytes": size_b,
                "mean_luma": round(mean_l, 2),
                "std_luma": round(std_l, 2),
                "passed": ok_view,
            }
        )
    cycles_ok = len(studio_checks) == 4 and all(c["passed"] for c in studio_checks)

    rtx_mean = float(rtx_info.get("mean_luma", 0.0))
    rtx_std = float(rtx_info.get("std_luma", 0.0))
    if require_rtx:
        rtx_ok: bool | None = (min_rtx_mean <= rtx_mean <= 245.0) and (rtx_std >= min_rtx_std)
        passed = non_box_ok and materials_ok and ui_ok and cycles_ok and bool(rtx_ok)
        rtx_block: dict[str, Any] = {
            "passed": bool(rtx_ok),
            "mean_luma": round(rtx_mean, 2),
            "std_luma": round(rtx_std, 2),
        }
    else:
        passed = non_box_ok and materials_ok and ui_ok and cycles_ok
        rtx_block = {
            "passed": None,
            "status": "NOT_RUN_STATIC_ONLY",
        }
    return {
        "passed": passed,
        "primary_mesh_count": len(primary_meshes),
        "box_primary_mesh_violations": box_violations,
        "material_classes": mat_classes,
        "material_class_count": len(mat_classes),
        "ui_check": {"passed": ui_ok, **ui_details},
        "cycles_4view": {"passed": cycles_ok, "views": studio_checks},
        "isaac_rtx": rtx_block,
    }


def evaluate_g9b_visual_critique_report(
    report: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    expected_slug: str | None = None,
    min_dimension_score: float = 8.0,
    max_repair_rounds: int = 3,
    verify_hashes_on_disk: bool = True,
) -> dict[str, Any]:
    """Validate `GEN-008` `G9b` independent critic report, rubric, isolation & SHA-256 bindings."""
    errors: list[str] = []

    if report.get("schema_version") != "ika-grade-visual-critique/v1.0":
        errors.append(f"Invalid schema_version: {report.get('schema_version')!r}")

    if expected_slug and report.get("slug") != expected_slug:
        errors.append(f"Slug mismatch: {report.get('slug')!r} != {expected_slug!r}")

    author_agent = str(report.get("author_agent", "")).strip()
    critic_agent = str(report.get("critic_agent", "")).strip()
    if not author_agent or not critic_agent:
        errors.append("Missing author_agent or critic_agent")
    elif author_agent == critic_agent:
        errors.append(f"Role isolation violated: author_agent == critic_agent ({author_agent!r})")

    round_num = int(report.get("round", 0))
    if round_num < 1 or round_num > int(max_repair_rounds):
        errors.append(f"Round {round_num} outside allowed [1, {max_repair_rounds}]")

    dims = report.get("dimensions")
    dim_scores: dict[str, float] = {}
    if not isinstance(dims, Mapping):
        errors.append("Missing dimensions mapping")
    else:
        for key in REQUIRED_CRITIQUE_DIMENSIONS:
            if key not in dims:
                errors.append(f"Missing critique dimension: {key}")
            else:
                val = float(dims[key])
                dim_scores[key] = val
                if val < float(min_dimension_score):
                    errors.append(f"Dimension {key}={val:.2f} < {min_dimension_score:.2f}")

    if str(report.get("verdict", "")).upper() != "PASS":
        errors.append(f"Critic verdict is not PASS: {report.get('verdict')!r}")

    ev_pack = report.get("evidence_pack")
    if not isinstance(ev_pack, Mapping):
        errors.append("Missing evidence_pack")
    else:
        for req_key in (
            "manufacturer_evidence_paths",
            "frozen_spec_path",
            "positive_anchor_paths",
            "negative_anchor_paths",
        ):
            val = ev_pack.get(req_key)
            if not val:
                errors.append(f"Missing or empty evidence_pack.{req_key}")

    src_usd = report.get("source_usd")
    if not isinstance(src_usd, Mapping) or not src_usd.get("path") or not src_usd.get("sha256"):
        errors.append("Missing source_usd path/sha256 binding")
    elif verify_hashes_on_disk:
        src_path = _resolve_repo_path(str(src_usd["path"]), repo_root)
        if not src_path.is_file():
            errors.append(f"Bound source_usd file missing on disk: {src_path}")
        else:
            actual_sha = _sha256_prefixed(src_path)
            if actual_sha != str(src_usd["sha256"]):
                errors.append(
                    f"source_usd sha256 mismatch: {src_usd['sha256']} != {actual_sha}"
                )

    reviewed_renders = report.get("reviewed_renders")
    if not isinstance(reviewed_renders, Sequence) or len(reviewed_renders) < 4:
        errors.append("reviewed_renders must list >= 4 reviewed PNG renders")
    elif verify_hashes_on_disk:
        for item in reviewed_renders:
            if not isinstance(item, Mapping) or not item.get("path") or not item.get("sha256"):
                errors.append("reviewed_renders entry missing path/sha256")
                continue
            rpath = _resolve_repo_path(str(item["path"]), repo_root)
            if not rpath.is_file():
                errors.append(f"Reviewed render missing on disk: {rpath}")
            else:
                actual_sha = _sha256_prefixed(rpath)
                if actual_sha != str(item["sha256"]):
                    errors.append(
                        f"Render sha256 mismatch for {rpath.name}: {item['sha256']} != {actual_sha}"
                    )

    min_dim = min(dim_scores.values()) if dim_scores else 0.0
    return {
        "passed": len(errors) == 0,
        "author_agent": author_agent,
        "critic_agent": critic_agent,
        "round": round_num,
        "verdict": report.get("verdict"),
        "min_dimension_score": round(min_dim, 3),
        "required_min_score": float(min_dimension_score),
        "dimensions": dim_scores,
        "errors": errors,
    }


def build_ika_grade_asset_report(
    *,
    slug: str,
    asset_id: str,
    articulation_root: str,
    isaac_runtime: str,
    counts: Mapping[str, int],
    gates: Sequence[Mapping[str, Any]],
    source_usd_sha256: str = "",
    exceptions: Sequence[str] = (),
    static_only: bool = False,
) -> dict[str, Any]:
    all_pass = all(bool(g.get("passed")) for g in gates)
    has_g9_split = any(
        str(g.get("id", "")).startswith(("G9a_", "G9b_")) for g in gates
    )
    physics_gates = [
        g for g in gates
        if str(g.get("category", "")).startswith("runtime")
    ]
    visual_gates = [
        g for g in gates
        if str(g.get("category", "")).startswith("visual")
    ]
    physics_ok = bool(physics_gates) and all(bool(g.get("passed")) for g in physics_gates)
    visual_ok = bool(visual_gates) and all(bool(g.get("passed")) for g in visual_gates)
    if static_only:
        physics_status = "NOT_RUN_STATIC_ONLY"
        impl_status = "PASS_STATIC_ONLY" if all_pass else "FAIL"
    else:
        physics_status = "PASS" if (physics_ok if has_g9_split else all_pass) else "FAIL"
        impl_status = "PASS" if all_pass else "FAIL"
    evidence_sep: dict[str, str] = {
        "static_contract": "PASS" if gates and gates[0].get("passed") else "FAIL",
        "reopen_and_bounds": "PASS" if len(gates) > 1 and gates[1].get("passed") else "FAIL",
        "physics_smoke": physics_status,
        "robot_integration": "NOT_TESTED_DELEGATED_TO_ASTRA",
    }
    if has_g9_split:
        evidence_sep["visual_acceptance"] = "PASS" if visual_ok else "FAIL"
    return {
        "schema_version": (
            "ika-grade-hero-acceptance/v2.0"
            if has_g9_split
            else "ika-grade-hero-acceptance/v1.0"
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "assetId": asset_id,
        "assetRoot": "/AssetRoot",
        "mode": "fixed",
        "articulationRoot": articulation_root,
        "implementationStatus": impl_status,
        "isaacRuntime": isaac_runtime,
        "staticAudit": "PASS" if gates and gates[0].get("passed") else "FAIL",
        "sourceUsdSha256": source_usd_sha256,
        "counts": dict(counts),
        "evidenceSeparation": evidence_sep,
        "checks": list(gates),
        "exceptions": list(exceptions),
        "limitations": [
            "Direct handle/drawer forces and cavity load tests establish physical articulation "
            "and non-convex support validity (GEN-007 physics_smoke); bimanual lift2 grasp and "
            "collision-free arm trajectories are delegated to downstream Astra."
        ],
    }


def inspect_usda_appearance_and_topology(usd_path: Path) -> dict[str, Any]:
    """Pure-Python USDA parser extracting visual mesh, material, texture, and BFS joint metadata."""
    txt = usd_path.read_text(encoding="utf-8", errors="ignore")

    physx_rb_count = txt.count("PhysxRigidBodyAPI")
    physx_art_count = txt.count("PhysxArticulationAPI")

    # Joint ordering inside Joints scope
    jstart = txt.find('def Xform "Joints"')
    joints_ordered: list[dict[str, Any]] = []
    if jstart != -1:
        jtxt = txt[jstart:]
        jmatches = list(re.finditer(r'def (Physics\w+Joint) "([^"]+)"', jtxt))
        for idx, m in enumerate(jmatches):
            end_pos = jmatches[idx + 1].start() if idx + 1 < len(jmatches) else len(jtxt)
            seg = jtxt[m.start() : end_pos]
            b0_m = re.search(r"rel physics:body0 = <([^>]+)>", seg)
            b1_m = re.search(r"rel physics:body1 = <([^>]+)>", seg)
            joints_ordered.append(
                {
                    "name": m.group(2),
                    "type": m.group(1),
                    "body0": b0_m.group(1) if b0_m else None,
                    "body1": b1_m.group(1) if b1_m else None,
                }
            )

    # Materials
    materials: list[dict[str, Any]] = []
    for m in re.finditer(r'def Material "([^"]+)"\s*\{(.*?)\n\s*\}', txt, re.S):
        name, body = m.group(1), m.group(2)
        met = re.search(r"float inputs:metallic = ([0-9.eE+-]+)", body)
        rough = re.search(r"float inputs:roughness = ([0-9.eE+-]+)", body)
        op = re.search(r"float inputs:opacity = ([0-9.eE+-]+)", body)
        em = re.search(r"color3f inputs:emissiveColor = \(([^)]+)\)", body)
        em_vals = [float(x.strip()) for x in em.group(1).split(",")] if em else [0.0, 0.0, 0.0]
        materials.append(
            {
                "name": name,
                "metallic": float(met.group(1)) if met else 0.0,
                "roughness": float(rough.group(1)) if rough else 0.5,
                "opacity": float(op.group(1)) if op else 1.0,
                "emissive": em_vals,
            }
        )

    # File-backed UsdUVTexture references
    texture_files = re.findall(r'asset inputs:file = @([^@]+)@', txt)

    # Visual meshes & cubes (excluding Collision / purpose = "guide") via indent-matched block scan
    visual_meshes: list[dict[str, Any]] = []
    prim_stack: list[tuple[int, str]] = []
    lines = txt.splitlines()
    i = 0
    n_lines = len(lines)
    while i < n_lines:
        line = lines[i]
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        while prim_stack and indent <= prim_stack[-1][0] and stripped.startswith("}"):
            prim_stack.pop()

        scope_m = re.match(r'^def \w+ "([^"]+)"', stripped)
        if scope_m and not re.match(r'^def (Mesh|Cube) "', stripped):
            prim_stack.append((indent, scope_m.group(1)))

        mc_m = re.match(r'^def (Mesh|Cube) "([^"]+)"', stripped)
        if mc_m:
            ptype, name = mc_m.group(1), mc_m.group(2)
            # Collect lines until matching closing brace at the same indent
            block_lines = [line]
            j = i + 1
            seen_open = "{" in line
            brace_depth = line.count("{") - line.count("}")
            while j < n_lines:
                bl = lines[j]
                block_lines.append(bl)
                if "{" in bl:
                    seen_open = True
                brace_depth += bl.count("{") - bl.count("}")
                if seen_open and brace_depth <= 0:
                    break
                j += 1
            body = "\n".join(block_lines)
            in_collision = any(pname == "Collision" for _, pname in prim_stack)
            if not in_collision and 'purpose = "guide"' not in body:
                if ptype == "Cube":
                    visual_meshes.append(
                        {
                            "name": name,
                            "prim_type": "Cube",
                            "vertices": 8,
                            "faces": 6,
                            "unique_normals": 6,
                        }
                    )
                else:
                    fvc = re.search(r"int\[\] faceVertexCounts = \[([^\]]+)\]", body)
                    pts = re.search(r"point3f\[\] points = \[([^\]]+)\]", body)
                    nrm = re.search(r"normal3f\[\] normals = \[([^\]]+)\]", body)
                    nf = len(fvc.group(1).split(",")) if fvc else 0
                    nv = pts.group(1).count("(") if pts else 0
                    nn = len(set(re.findall(r"\([^)]+\)", nrm.group(1)))) if nrm else 0
                    visual_meshes.append(
                        {
                            "name": name,
                            "prim_type": "Mesh",
                            "vertices": nv,
                            "faces": nf,
                            "unique_normals": nn,
                        }
                    )
            i = j + 1
            continue
        i += 1

    return {
        "physx_rigid_body_count": physx_rb_count,
        "physx_articulation_count": physx_art_count,
        "joints_ordered": joints_ordered,
        "appearance_meta": {
            "visual_meshes": visual_meshes,
            "materials": materials,
            "texture_files": texture_files,
        },
    }


# ---------------------------------------------------------------------------
# Hero Specifications for the 3 `r2` Out-of-Domain Machines (Backward Compat)
# ---------------------------------------------------------------------------

HERO_ACCEPTANCE_SPECS: list[dict[str, Any]] = [
    {
        "slug": "nespresso-creatista-plus-bne800",
        "evidence_slug": "nespresso-creatista-plus-bne800-r2",
        "asset_id": "NespressoCreatistaPlus",
        "expected_wdh_m": [0.171, 0.393, 0.308],
        "closed_joint_targets_rad_or_m": {
            "BrewLeverJoint": 0.0,
            "DripTrayJoint": 0.0,
            "DialPressJoint": 0.0,
            "SelectDialJoint": 0.0,
            "SteamWandJoint": 0.0,
            "ButtonDrinkJoint": 0.0,
            "ButtonTempJoint": 0.0,
            "ButtonFrothJoint": 0.0,
        },
        "control_links": ["ButtonDrink", "ButtonTemp", "ButtonFroth", "SelectDialRotor"],
        "spring_buttons": {
            "ButtonDrinkJoint": -0.0018,
            "ButtonTempJoint": -0.0018,
            "ButtonFrothJoint": -0.0018,
            "DialPressJoint": 0.0026,
        },
        "composite_knob": {
            "press_joint": "DialPressJoint",
            "press_target_m": 0.0026,
            "rot_joint": "SelectDialJoint",
            "rot_target_rad": math.radians(78.0),
        },
        "force_smoke": {
            "joint": "DripTrayJoint",
            "link": "DripTray",
            "force_world_xyz": [0.0, -28.0, 0.0],
            "force_pos_world_xyz": [0.0, -0.195, 0.015],
            "expected_sign": -1,
            "min_travel": 0.025,
        },
        "load_tests": [
            {
                "name": "espresso_cup_on_extended_drip_tray",
                "workpiece_slug": "espresso_cup",
                "workpiece_mass_kg": 0.135,
                "pre_joint_targets": {"DripTrayJoint": -0.042, "BrewLeverJoint": math.radians(-70.0)},
                "spawn_xyz": [0.0, -0.192, 0.040],
                "max_drop_m": 0.008,
                "max_post_settle_drift_m": 0.0015,
            },
            {
                "name": "coffee_capsule_in_5box_chute",
                "workpiece_slug": "coffee_capsule",
                "workpiece_mass_kg": 0.012,
                "pre_joint_targets": {"DripTrayJoint": -0.042, "BrewLeverJoint": math.radians(-70.0)},
                "spawn_xyz": [0.0, -0.1095, 0.256],
                "max_drop_m": 0.008,
                "max_post_settle_drift_m": 0.0015,
            },
        ],
        "rail_transport_test": {
            "workpiece_slug": "espresso_cup",
            "workpiece_mass_kg": 0.135,
            "joint": "DripTrayJoint",
            "start_pos": 0.0,
            "end_pos": -0.042,
            "spawn_xyz": [0.0, -0.150, 0.040],
            "expected_delta_y": -0.042,
            "max_tracking_err_m": 0.012,
        },
        "rtx_camera": {"eye": [0.42, -0.56, 0.42], "target": [0.0, -0.04, 0.17]},
        "g9a_appearance": {"ui_representation": "vector_3d"},
        "g9b_visual_critic": {"min_dimension_score": 8.0, "max_repair_rounds": 3},
    },
    {
        "slug": "ingun-ma-2111-pcba-fixture",
        "evidence_slug": "ingun-ma-2111-pcba-fixture-r2",
        "asset_id": "IngunMA2111Fixture",
        "expected_wdh_m": [0.320, 0.515, 0.270],
        "closed_joint_targets_rad_or_m": {
            "PressureHoodJoint": 0.0,
            "ClampLeverJoint": 0.0,
            "ModeToggleJoint": math.radians(21.0),
            "TestStartButtonJoint": 0.0,
            "AbortStopButtonJoint": 0.0,
            "MainsRockerJoint": math.radians(16.0),
        },
        "control_links": ["ModeToggle", "TestStartButton", "AbortStopButton", "MainsRocker"],
        "spring_buttons": {
            "TestStartButtonJoint": -0.0024,
            "AbortStopButtonJoint": -0.0024,
        },
        "composite_knob": None,
        "force_smoke": {
            "joint": "PressureHoodJoint",
            "link": "PressureHood",
            "force_world_xyz": [0.0, -45.0, -35.0],
            "force_pos_world_xyz": [0.0, 0.010, 0.450],
            "expected_sign": 1,
            "min_travel": 0.35,
        },
        "load_tests": [
            {
                "name": "pcba_seated_in_4rail_gold_pin_nest",
                "workpiece_slug": "pcba_carrier_board",
                "workpiece_mass_kg": 0.085,
                "pre_joint_targets": {
                    "PressureHoodJoint": math.radians(-62.0),
                    "ClampLeverJoint": math.radians(-78.0),
                },
                "spawn_xyz": [0.0, -0.040, 0.130],
                "max_drop_m": 0.006,
                "max_post_settle_drift_m": 0.0015,
            },
        ],
        "rail_transport_test": None,
        "rtx_camera": {"eye": [0.64, -0.78, 0.56], "target": [0.0, -0.02, 0.21]},
        "g9a_appearance": {"ui_representation": "vector_3d"},
        "g9b_visual_critic": {"min_dimension_score": 8.0, "max_repair_rounds": 3},
    },
    {
        "slug": "brother-mfc-l2820dw-printer",
        "evidence_slug": "brother-mfc-l2820dw-printer-r2",
        "asset_id": "BrotherMFCL2820DW",
        "expected_wdh_m": [0.410, 0.399, 0.319],
        "closed_joint_targets_rad_or_m": {
            "PaperCassetteJoint": 0.0,
            "ScannerLidJoint": 0.0,
            "OutputFlapJoint": 0.0,
            "ButtonStartJoint": 0.0,
            "ButtonStopJoint": 0.0,
            "ButtonClearJoint": 0.0,
            "ButtonPowerJoint": 0.0,
        },
        "control_links": ["ButtonStart", "ButtonStop", "ButtonClear", "ButtonPower"],
        "spring_buttons": {
            "ButtonStartJoint": -0.0020,
            "ButtonStopJoint": -0.0020,
            "ButtonClearJoint": -0.0020,
            "ButtonPowerJoint": -0.0020,
        },
        "composite_knob": None,
        "force_smoke": {
            "joint": "PaperCassetteJoint",
            "link": "PaperCassette",
            "force_world_xyz": [0.0, 38.0, 0.0],
            "force_pos_world_xyz": [0.0, -0.360, 0.035],
            "expected_sign": 1,
            "min_travel": 0.12,
        },
        "load_tests": [
            {
                "name": "a5_media_pack_in_extended_cassette",
                "workpiece_slug": "a5_media_pack",
                "workpiece_mass_kg": 0.280,
                "pre_joint_targets": {
                    "PaperCassetteJoint": -0.165,
                    "ScannerLidJoint": math.radians(-62.0),
                },
                "spawn_xyz": [0.0, -0.261, 0.017],
                "max_drop_m": 0.006,
                "max_post_settle_drift_m": 0.0015,
            },
            {
                "name": "calibration_sheet_on_platen_glass",
                "workpiece_slug": "calibration_sheet",
                "workpiece_mass_kg": 0.065,
                "pre_joint_targets": {
                    "PaperCassetteJoint": 0.0,
                    "ScannerLidJoint": math.radians(-62.0),
                },
                "spawn_xyz": [0.0, 0.0, 0.282],
                "max_drop_m": 0.005,
                "max_post_settle_drift_m": 0.0015,
            },
        ],
        "rail_transport_test": {
            "workpiece_slug": "a5_media_pack",
            "workpiece_mass_kg": 0.280,
            "joint": "PaperCassetteJoint",
            "start_pos": -0.165,
            "end_pos": 0.0,
            "spawn_xyz": [0.0, -0.261, 0.017],
            "expected_delta_y": 0.165,
            "max_tracking_err_m": 0.018,
        },
        "rtx_camera": {"eye": [0.68, -0.84, 0.58], "target": [0.0, -0.06, 0.23]},
        "g9a_appearance": {"ui_representation": "vector_3d"},
        "g9b_visual_critic": {"min_dimension_score": 8.0, "max_repair_rounds": 3},
    },
]


# ---------------------------------------------------------------------------
# Subprocess Isaac Sim 4.1 Runtime Probe (G2..G9)
# ---------------------------------------------------------------------------

_ISAAC_RUNTIME_WORKER = r"""
import json
import math
from pathlib import Path
import sys

cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_json = Path(sys.argv[2])

from isaacsim import SimulationApp
app = SimulationApp({
    "headless": True,
    "renderer": "RayTracedLighting",
    "anti_aliasing": 4,
    "width": 1280,
    "height": 960,
})

import carb.settings
import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade
import omni.kit.app
import omni.replicator.core as rep
import omni.usd
from omni.isaac.core import World
from omni.isaac.core.articulations import Articulation
from omni.isaac.core.prims import RigidPrim, RigidPrimView

settings = carb.settings.get_settings()
settings.set("/rtx/post/aa/autoExposureMode", 0)
settings.set("/rtx/post/aa/exposureMultiplier", 0.85)
settings.set("/rtx/post/histogram/enabled", False)

kit_version = str(omni.kit.app.get_app().get_app_version())

def compute_prim_guide_aabb(stage, prim_path):
    bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.guide, UsdGeom.Tokens.default_])
    prim = stage.GetPrimAtPath(prim_path)
    rng = bc.ComputeWorldBound(prim).ComputeAlignedRange()
    mn, mx = rng.GetMin(), rng.GetMax()
    return ([float(mn[0]), float(mn[1]), float(mn[2])], [float(mx[0]), float(mx[1]), float(mx[2])])

def compute_prim_visual_aabb(stage, prim_path):
    bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    prim = stage.GetPrimAtPath(prim_path)
    rng = bc.ComputeWorldBound(prim).ComputeAlignedRange()
    mn, mx = rng.GetMin(), rng.GetMax()
    return ([float(mn[0]), float(mn[1]), float(mn[2])], [float(mx[0]), float(mx[1]), float(mx[2])])

results = {"kit_version": kit_version, "heroes": {}}

for hspec in cfg["heroes"]:
    slug = hspec["slug"]
    usd_path = Path(cfg["source_root"]) / slug / "asset.usda"
    ev_dir = Path(cfg["evidence_root"]) / hspec["evidence_slug"]
    ev_dir.mkdir(parents=True, exist_ok=True)

    World.clear_instance()
    ctx = omni.usd.get_context()
    ctx.new_stage()
    for _ in range(5):
        app.update()

    stage = ctx.get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)

    raw_stage = Usd.Stage.Open(str(usd_path))
    all_prims = list(raw_stage.Traverse())
    meshes = [p for p in all_prims if p.IsA(UsdGeom.Mesh)]
    mats = [p for p in all_prims if p.IsA(UsdShade.Material)]
    rbs = [p for p in all_prims if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    cols = [p for p in all_prims if p.HasAPI(UsdPhysics.CollisionAPI)]
    joints = [p for p in all_prims if p.IsA(UsdPhysics.Joint)]
    rev_joints = [p for p in all_prims if p.IsA(UsdPhysics.RevoluteJoint)]
    pris_joints = [p for p in all_prims if p.IsA(UsdPhysics.PrismaticJoint)]
    vis_prims = [
        p for p in all_prims
        if "/Visual/" in str(p.GetPath()) and p.IsA(UsdGeom.Gprim)
    ]
    bad_asset_paths = []
    ignored_friction_attrs = []
    for p in all_prims:
        for attr in p.GetAttributes():
            aname = attr.GetName()
            if "jointFriction" in aname:
                ignored_friction_attrs.append(str(attr.GetPath()))
            val = attr.Get()
            if isinstance(val, Sdf.AssetPath) and val.path:
                if val.path.startswith("/") or "://" in val.path:
                    bad_asset_paths.append(f"{attr.GetPath()}={val.path}")

    hero_xf = UsdGeom.Xform.Define(stage, "/World/Hero")
    hero_xf.GetPrim().GetReferences().AddReference(str(usd_path))
    world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 60.0, rendering_dt=1.0 / 60.0)
    world.scene.add_default_ground_plane(z_position=-0.50)

    base_to_world = stage.GetPrimAtPath("/World/Hero/Joints/BaseToWorld")
    if base_to_world.IsValid() and base_to_world.HasAPI(UsdPhysics.ArticulationRootAPI):
        base_to_world.RemoveAPI(UsdPhysics.ArticulationRootAPI)
    UsdPhysics.ArticulationRootAPI.Apply(hero_xf.GetPrim())
    hero_xf.GetPrim().CreateAttribute("physxArticulation:articulationEnabled", Sdf.ValueTypeNames.Bool).Set(True)
    hero_xf.GetPrim().CreateAttribute("physxArticulation:enabledSelfCollisions", Sdf.ValueTypeNames.Bool).Set(False)

    art = world.scene.add(Articulation(prim_path="/World/Hero", name=f"hero_{slug.replace('-', '_')}"))
    base_rb = RigidPrim(prim_path="/World/Hero/Links/Base", name=f"base_{slug.replace('-', '_')}")

    wp_rbs = []
    for lt_i, lt in enumerate(hspec["load_tests"]):
        wp_usd = Path(cfg["source_root"]) / lt["workpiece_slug"] / "asset.usda"
        wp_path = f"/World/Workpiece_{lt_i}"
        wp_xf = UsdGeom.Xform.Define(stage, wp_path)
        wp_xf.GetPrim().GetReferences().AddReference(str(wp_usd))
        wp_prim = wp_xf.GetPrim()
        if not wp_prim.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI.Apply(wp_prim).CreateRigidBodyEnabledAttr(True)
            UsdPhysics.MassAPI.Apply(wp_prim).CreateMassAttr(float(lt["workpiece_mass_kg"]))
        wp_rbs.append(world.scene.add(RigidPrim(prim_path=wp_path, name=f"wp_{slug.replace('-', '_')}_{lt_i}")))

    rt_rb = None
    if hspec["rail_transport_test"] is not None:
        rt = hspec["rail_transport_test"]
        wp_usd = Path(cfg["source_root"]) / rt["workpiece_slug"] / "asset.usda"
        rt_path = "/World/RailWorkpiece"
        rt_xf = UsdGeom.Xform.Define(stage, rt_path)
        rt_xf.GetPrim().GetReferences().AddReference(str(wp_usd))
        rt_prim = rt_xf.GetPrim()
        if not rt_prim.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI.Apply(rt_prim).CreateRigidBodyEnabledAttr(True)
            UsdPhysics.MassAPI.Apply(rt_prim).CreateMassAttr(float(rt["workpiece_mass_kg"]))
        rt_rb = world.scene.add(RigidPrim(prim_path=rt_path, name=f"rt_{slug.replace('-', '_')}"))

    world.reset()
    base_rb.initialize()
    for lt_i, wp_rb in enumerate(wp_rbs):
        wp_rb.set_world_pose(position=np.array([2.5 + lt_i * 0.5, 2.5, -0.45]), orientation=np.array([1.0, 0.0, 0.0, 0.0]))
    if rt_rb is not None:
        rt_rb.set_world_pose(position=np.array([3.5, 2.5, -0.45]), orientation=np.array([1.0, 0.0, 0.0, 0.0]))
    for _ in range(15):
        world.step(render=False)

    dof_names = list(art.dof_names)
    dof_limits = art.dof_properties
    q_init = np.array(art.get_joint_positions(), dtype=float).reshape(-1)
    base_pos_0, _ = base_rb.get_world_pose()

    for _ in range(120):
        world.step(render=False)
    q_after_120 = np.array(art.get_joint_positions(), dtype=float).reshape(-1)
    base_pos_120, _ = base_rb.get_world_pose()
    base_drift_120_mm = float(np.linalg.norm(base_pos_120 - base_pos_0) * 1000.0)
    max_joint_drift_120 = float(np.max(np.abs(q_after_120 - q_init)))

    ctrl_rest_aabbs = {}
    for clink in hspec["control_links"]:
        cpath = f"/World/Hero/Links/{clink}/Collision"
        ctrl_rest_aabbs[clink] = compute_prim_guide_aabb(stage, cpath)

    q_closed = q_after_120.copy()
    for jn, target_v in hspec["closed_joint_targets_rad_or_m"].items():
        if jn in dof_names:
            q_closed[dof_names.index(jn)] = float(target_v)
    art.set_joint_positions(q_closed)
    art.set_joint_velocities(np.zeros_like(q_closed))
    for _ in range(10):
        world.step(render=True)
    closed_vmin, closed_vmax = compute_prim_visual_aabb(stage, "/World/Hero/Links")

    dof_sweep_records = []
    for idx, jn in enumerate(dof_names):
        low = float(dof_limits["lower"][idx])
        high = float(dof_limits["upper"][idx])
        q_test = q_closed.copy()
        q_test[idx] = low
        art.set_joint_positions(q_test)
        for _ in range(8):
            world.step(render=False)
        obs_low = float(art.get_joint_positions()[idx])

        q_test[idx] = high
        art.set_joint_positions(q_test)
        for _ in range(8):
            world.step(render=False)
        obs_high = float(art.get_joint_positions()[idx])
        span = abs(obs_high - obs_low)
        expected_span = abs(high - low)
        dof_sweep_records.append({
            "joint": jn,
            "lower": round(low, 5),
            "upper": round(high, 5),
            "obs_low": round(obs_low, 5),
            "obs_high": round(obs_high, 5),
            "passed": span >= expected_span * 0.88,
        })

    spring_records = []
    art.set_joint_positions(q_closed)
    for _ in range(10):
        world.step(render=False)
    for bjoint, press_val in hspec["spring_buttons"].items():
        bidx = dof_names.index(bjoint)
        q_press = q_closed.copy()
        q_press[bidx] = float(press_val)
        art.set_joint_positions(q_press)
        world.step(render=False)
        pressed_pos = float(art.get_joint_positions()[bidx])
        art._articulation_view.set_joint_position_targets(q_closed.reshape(1, -1))
        for _ in range(45):
            world.step(render=False)
        returned_pos = float(art.get_joint_positions()[bidx])
        spring_records.append({
            "joint": bjoint,
            "pressed_m": round(pressed_pos, 5),
            "returned_m": round(returned_pos, 5),
            "passed": abs(returned_pos) <= 0.0006,
        })

    composite_result = {"applicable": False, "passed": True}
    if hspec["composite_knob"] is not None:
        ck = hspec["composite_knob"]
        p_idx = dof_names.index(ck["press_joint"])
        r_idx = dof_names.index(ck["rot_joint"])
        q_comp = q_closed.copy()
        q_comp[p_idx] = float(ck["press_target_m"])
        q_comp[r_idx] = float(ck["rot_target_rad"])
        art.set_joint_positions(q_comp)
        stage.GetPrimAtPath(f"/World/Hero/Joints/{ck['press_joint']}").GetAttribute("drive:linear:physics:targetPosition").Set(float(ck["press_target_m"]))
        stage.GetPrimAtPath(f"/World/Hero/Joints/{ck['rot_joint']}").GetAttribute("drive:angular:physics:targetPosition").Set(math.degrees(float(ck["rot_target_rad"])))
        stage.GetPrimAtPath(f"/World/Hero/Joints/{ck['rot_joint']}").GetAttribute("drive:angular:physics:stiffness").Set(40.0)
        for _ in range(30):
            world.step(render=False)
        q_obs = art.get_joint_positions()
        obs_p = float(q_obs[p_idx])
        obs_r = float(q_obs[r_idx])
        stage.GetPrimAtPath(f"/World/Hero/Joints/{ck['press_joint']}").GetAttribute("drive:linear:physics:targetPosition").Set(0.0)
        stage.GetPrimAtPath(f"/World/Hero/Joints/{ck['rot_joint']}").GetAttribute("drive:angular:physics:stiffness").Set(0.0)
        composite_result = {
            "applicable": True,
            "obs_press_m": round(obs_p, 5),
            "obs_rot_rad": round(obs_r, 5),
            "passed": abs(obs_p - ck["press_target_m"]) <= 0.0008 and abs(obs_r - ck["rot_target_rad"]) <= 0.08,
        }

    fs = hspec["force_smoke"]
    art.set_joint_positions(q_init)
    art.set_joint_velocities(np.zeros_like(q_init))
    for _ in range(10):
        world.step(render=False)
    fs_idx = dof_names.index(fs["joint"])
    q_before_force = float(art.get_joint_positions()[fs_idx])
    target_rbv = RigidPrimView(
        prim_paths_expr=f"/World/Hero/Links/{fs['link']}",
        name=f"fsv_{slug.replace('-', '_')}",
        reset_xform_properties=False,
    )
    target_rbv.initialize()
    f_vec = np.array([fs["force_world_xyz"]], dtype=np.float32)
    f_pos = np.array([fs["force_pos_world_xyz"]], dtype=np.float32)
    for _ in range(90):
        target_rbv.apply_forces_and_torques_at_pos(
            forces=f_vec, positions=f_pos, is_global=True
        )
        world.step(render=False)
    q_after_force = float(art.get_joint_positions()[fs_idx])
    base_after_force, _ = base_rb.get_world_pose()
    base_force_drift_mm = float(np.linalg.norm(base_after_force - base_pos_0) * 1000.0)
    signed_travel = (q_after_force - q_before_force) * float(fs["expected_sign"])
    force_smoke_res = {
        "joint": fs["joint"],
        "q_before": round(q_before_force, 5),
        "q_after": round(q_after_force, 5),
        "signed_travel": round(signed_travel, 5),
        "base_drift_mm": round(base_force_drift_mm, 5),
        "passed": signed_travel >= float(fs["min_travel"]) and base_force_drift_mm <= 0.05,
    }

    load_results = []
    for lt_i, lt in enumerate(hspec["load_tests"]):
        wp_rb = wp_rbs[lt_i]
        q_lt = q_init.copy()
        for jn, jv in lt["pre_joint_targets"].items():
            q_lt[dof_names.index(jn)] = float(jv)
        art.set_joint_positions(q_lt)
        art.set_joint_velocities(np.zeros_like(q_lt))
        spawn_pos = np.array(lt["spawn_xyz"], dtype=float)
        wp_rb.set_world_pose(position=spawn_pos, orientation=np.array([1.0, 0.0, 0.0, 0.0]))
        wp_rb.set_linear_velocity(np.zeros(3))
        wp_rb.set_angular_velocity(np.zeros(3))

        for _ in range(60):
            world.step(render=False)
        pos_60, _ = wp_rb.get_world_pose()
        for _ in range(600):
            world.step(render=False)
        pos_660, _ = wp_rb.get_world_pose()
        initial_drop = float(spawn_pos[2] - pos_60[2])
        sustained_drift = float(np.linalg.norm(pos_660 - pos_60))
        load_results.append({
            "name": lt["name"],
            "settled_xyz": [round(float(v), 5) for v in pos_660],
            "initial_drop_mm": round(initial_drop * 1000.0, 3),
            "sustained_600_frame_drift_mm": round(sustained_drift * 1000.0, 4),
            "passed": (
                -0.002 <= initial_drop <= float(lt["max_drop_m"])
                and sustained_drift <= float(lt["max_post_settle_drift_m"])
                and pos_660[2] > 0.005
            ),
        })
        wp_rb.set_world_pose(position=np.array([2.5 + lt_i * 0.5, 2.5, -0.40]))

    rail_result = {"applicable": False, "passed": True}
    if hspec["rail_transport_test"] is not None:
        rt = hspec["rail_transport_test"]
        r_idx = dof_names.index(rt["joint"])
        q_rt = q_init.copy()
        q_rt[r_idx] = float(rt["start_pos"])
        art.set_joint_positions(q_rt)
        art.set_joint_velocities(np.zeros_like(q_rt))

        rt_rb.set_world_pose(position=np.array(rt["spawn_xyz"], dtype=float), orientation=np.array([1.0, 0.0, 0.0, 0.0]))
        rt_rb.set_linear_velocity(np.zeros(3))
        rt_rb.set_angular_velocity(np.zeros(3))
        for _ in range(45):
            world.step(render=False)
        p_start, _ = rt_rb.get_world_pose()

        jprim = stage.GetPrimAtPath(f"/World/Hero/Joints/{rt['joint']}")
        jprim.GetAttribute("drive:linear:physics:stiffness").Set(900.0)
        for step_i in range(1, 91):
            alpha = step_i / 90.0
            target_p = float(rt["start_pos"]) * (1.0 - alpha) + float(rt["end_pos"]) * alpha
            jprim.GetAttribute("drive:linear:physics:targetPosition").Set(target_p)
            world.step(render=False)
        for _ in range(45):
            world.step(render=False)
        p_end, _ = rt_rb.get_world_pose()
        jprim.GetAttribute("drive:linear:physics:stiffness").Set(0.0)
        obs_dy = float(p_end[1] - p_start[1])
        obs_dz = float(p_end[2] - p_start[2])
        track_err = abs(obs_dy - float(rt["expected_delta_y"]))
        rail_result = {
            "applicable": True,
            "joint": rt["joint"],
            "obs_delta_y_m": round(obs_dy, 5),
            "expected_delta_y_m": round(float(rt["expected_delta_y"]), 5),
            "vertical_shift_mm": round(obs_dz * 1000.0, 3),
            "tracking_err_mm": round(track_err * 1000.0, 3),
            "passed": track_err <= float(rt["max_tracking_err_m"]) and abs(obs_dz) <= 0.004,
        }
        rt_rb.set_world_pose(position=np.array([3.5, 2.5, -0.40]))

    dome = UsdLux.DomeLight.Define(stage, "/World/InspectionDomeLight")
    dome.CreateIntensityAttr(1050.0)
    dome.CreateColorAttr(Gf.Vec3f(0.95, 0.97, 1.0))

    for li, (lpos, lint, lrad, lrgb) in enumerate([
        ((0.75, -0.95, 1.05), 13500.0, 0.28, (1.0, 0.98, 0.95)),
        ((-0.75, -0.85, 0.95), 10000.0, 0.28, (0.95, 0.98, 1.0)),
        ((0.0, 0.70, 1.15), 9500.0, 0.30, (1.0, 0.99, 0.97)),
    ]):
        sl = UsdLux.SphereLight.Define(stage, f"/World/KeyLight_{li}")
        sl.CreateRadiusAttr(float(lrad))
        sl.CreateIntensityAttr(float(lint))
        sl.CreateColorAttr(Gf.Vec3f(*lrgb))
        UsdGeom.Xformable(sl.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*lpos))

    def _bind_studio_mat(prim, name, rgb, rough=0.72, metal=0.04):
        mat = UsdShade.Material.Define(stage, f"/World/{name}")
        shd = UsdShade.Shader.Define(stage, f"/World/{name}/Shader")
        shd.CreateIdAttr("UsdPreviewSurface")
        shd.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        shd.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(rough))
        shd.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metal))
        mat.CreateSurfaceOutput().ConnectToSource(shd.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)

    ped = UsdGeom.Cube.Define(stage, "/World/Pedestal")
    ped.CreateSizeAttr(1.0)
    ped_xf = UsdGeom.Xformable(ped.GetPrim())
    ped_xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.015))
    ped_xf.AddScaleOp().Set(Gf.Vec3f(1.8, 1.8, 0.03))
    _bind_studio_mat(ped.GetPrim(), "StudioPedestalMat", (0.24, 0.26, 0.30), rough=0.62, metal=0.06)

    cyc_back = UsdGeom.Cube.Define(stage, "/World/CycloramaBack")
    cyc_back.CreateSizeAttr(1.0)
    cb_xf = UsdGeom.Xformable(cyc_back.GetPrim())
    cb_xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.88, 0.65))
    cb_xf.AddScaleOp().Set(Gf.Vec3f(2.6, 0.03, 1.6))
    _bind_studio_mat(cyc_back.GetPrim(), "StudioCycBackMat", (0.18, 0.20, 0.24), rough=0.82, metal=0.02)

    cyc_side = UsdGeom.Cube.Define(stage, "/World/CycloramaLeft")
    cyc_side.CreateSizeAttr(1.0)
    cs_xf = UsdGeom.Xformable(cyc_side.GetPrim())
    cs_xf.AddTranslateOp().Set(Gf.Vec3d(-0.88, 0.0, 0.65))
    cs_xf.AddScaleOp().Set(Gf.Vec3f(0.03, 2.2, 1.6))
    _bind_studio_mat(cyc_side.GetPrim(), "StudioCycSideMat", (0.18, 0.20, 0.24), rough=0.82, metal=0.02)

    art.set_joint_positions(q_init)
    for _ in range(10):
        world.step(render=True)

    eye = np.array(hspec["rtx_camera"]["eye"], dtype=float)
    tgt = np.array(hspec["rtx_camera"]["target"], dtype=float)
    fwd = tgt - eye
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right = right / np.linalg.norm(right)
    up = np.cross(right, fwd)
    cam_prim_path = "/World/InspectionCam"
    usd_cam = UsdGeom.Camera.Define(stage, cam_prim_path)
    usd_cam.CreateFocalLengthAttr(34.0)
    usd_cam.CreateHorizontalApertureAttr(36.0)
    usd_cam.CreateVerticalApertureAttr(27.0)
    usd_cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 50.0))
    mat4 = Gf.Matrix4d(1.0)
    mat4.SetRow(0, Gf.Vec4d(float(right[0]), float(right[1]), float(right[2]), 0.0))
    mat4.SetRow(1, Gf.Vec4d(float(up[0]), float(up[1]), float(up[2]), 0.0))
    mat4.SetRow(2, Gf.Vec4d(float(-fwd[0]), float(-fwd[1]), float(-fwd[2]), 0.0))
    mat4.SetRow(3, Gf.Vec4d(float(eye[0]), float(eye[1]), float(eye[2]), 1.0))
    UsdGeom.Xformable(usd_cam.GetPrim()).MakeMatrixXform().Set(mat4)

    rp = rep.create.render_product(cam_prim_path, (1280, 960))
    rgb_annot = rep.AnnotatorRegistry.get_annotator("rgb")
    rgb_annot.attach([rp])
    for _ in range(32):
        world.step(render=True)
    raw_rgb = rgb_annot.get_data()
    arr = np.asarray(raw_rgb)[..., :3].astype(np.uint8)
    rtx_png = ev_dir / "isaac_rtx_inspection.png"
    if rtx_png.exists() and cfg.get("rtx_probe_dir"):
        probe_dir = Path(cfg["rtx_probe_dir"])
        probe_dir.mkdir(parents=True, exist_ok=True)
        rtx_png = probe_dir / f"{slug}_isaac_rtx_inspection.png"
    Image.fromarray(arr, mode="RGB").save(rtx_png)
    rgb_annot.detach([rp.path])
    rp.destroy()

    results["heroes"][slug] = {
        "counts": {
            "total_prims": len(all_prims),
            "visual_prims": len(vis_prims),
            "meshes": len(meshes),
            "materials": len(mats),
            "links": len(rbs),
            "joints_total": len(joints),
            "revolute": len(rev_joints),
            "prismatic": len(pris_joints),
            "fixed": len(joints) - len(rev_joints) - len(pris_joints),
            "colliders": len(cols),
            "usd_size_bytes": usd_path.stat().st_size,
        },
        "bad_asset_paths": bad_asset_paths,
        "ignored_friction_attrs": ignored_friction_attrs,
        "closed_visual_bounds": {"min": closed_vmin, "max": closed_vmax},
        "control_rest_aabbs": ctrl_rest_aabbs,
        "g4_init": {
            "dof_count": len(dof_names),
            "dof_names": dof_names,
            "base_drift_120_mm": round(base_drift_120_mm, 5),
            "max_joint_drift_120": round(max_joint_drift_120, 6),
        },
        "g5_motion": {
            "dof_sweeps": dof_sweep_records,
            "spring_buttons": spring_records,
            "composite_knob": composite_result,
        },
        "g6_force_smoke": force_smoke_res,
        "g7_load_600_frames": load_results,
        "g8_rail_transport": rail_result,
        "g9_rtx_render": {
            "path": str(rtx_png),
            "mean_luma": round(float(arr.mean()), 2),
            "std_luma": round(float(arr.std()), 2),
        },
    }

def _json_default(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(f"Unserializable {type(o)}")

out_json.write_text(json.dumps(results, indent=2, default=_json_default), encoding="utf-8")
sys.stdout.flush()
import os
os._exit(0)
"""


def run_9_gate_acceptance(
    *,
    factory_root: Path,
    evidence_root: Path,
    spec_config: Path | Sequence[Path] | None = None,
    critique_dir: Path | None = None,
    out_summary: Path | None = None,
    static_only: bool = False,
    isaac_python: Path | None = None,
) -> dict[str, Any]:
    hero_specs = load_hero_acceptance_specs(spec_config)
    source_root = factory_root / "assets" / "source"
    accept_dir = factory_root / "assets" / "ika_grade_acceptance"
    accept_dir.mkdir(parents=True, exist_ok=True)
    resolved_critique_dir = critique_dir or (REPO_ROOT / DEFAULT_CRITIQUE_DIR)
    summary_path = out_summary or (accept_dir / "ika_acceptance_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    usd_python = _resolve_usd_python()

    # 1. Run G1 static contract on each hero via check_articulation_usd.py
    static_reports: dict[str, dict[str, Any]] = {}
    for hspec in hero_specs:
        slug = hspec["slug"]
        usd_file = source_root / slug / "asset.usda"
        out_static = accept_dir / f"{slug}_static_gate.json"
        proc = subprocess.run(
            [
                usd_python,
                str(CHECK_ART_SCRIPT),
                "--usd",
                str(usd_file),
                "--asset-root",
                "/AssetRoot",
                "--mode",
                "fixed",
                "--json-out",
                str(out_static),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not out_static.is_file():
            raise RuntimeError(
                f"Static gate failed for {slug}: {proc.stdout}\n{proc.stderr}"
            )
        static_reports[slug] = json.loads(out_static.read_text(encoding="utf-8"))

    # 2. Either inspect via pure `usd-core` (`--static-only`) or run headless Isaac Sim 4.1 batch session
    if static_only:
        rt_all: dict[str, Any] = {
            "kit_version": "static_only_usd_core",
            "heroes": {
                hspec["slug"]: _inspect_stage_static_usd_core(
                    source_root / hspec["slug"] / "asset.usda", hspec
                )
                for hspec in hero_specs
            },
        }
    else:
        resolved_isaac_py = resolve_isaac_python(isaac_python)
        worker_cfg = accept_dir / "_runtime_worker_cfg.json"
        worker_py = accept_dir / "_runtime_worker.py"
        worker_out = accept_dir / "_runtime_worker_results.json"
        worker_out.unlink(missing_ok=True)
        worker_cfg.write_text(
            json.dumps(
                {
                    "source_root": str(source_root.resolve()),
                    "evidence_root": str(evidence_root.resolve()),
                    "rtx_probe_dir": str((summary_path.parent / "rtx_probe_renders").resolve()),
                    "heroes": hero_specs,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        worker_py.write_text(_ISAAC_RUNTIME_WORKER, encoding="utf-8")

        proc = subprocess.run(
            [str(resolved_isaac_py), str(worker_py), str(worker_cfg), str(worker_out)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not worker_out.is_file():
            sys.stderr.write(proc.stdout[-4000:] + "\n" + proc.stderr[-4000:] + "\n")
            raise RuntimeError(f"Isaac 4.1 runtime acceptance worker failed (rc={proc.returncode})")

        rt_all = json.loads(worker_out.read_text(encoding="utf-8"))
        worker_cfg.unlink(missing_ok=True)
        worker_py.unlink(missing_ok=True)

    hero_reports: list[dict[str, Any]] = []
    for hspec in hero_specs:
        slug = hspec["slug"]
        usd_file = source_root / slug / "asset.usda"
        usd_sha = _sha256_prefixed(usd_file)
        usda_meta = inspect_usda_appearance_and_topology(usd_file)
        srep = static_reports[slug]
        rrep = rt_all["heroes"][slug]
        counts = rrep["counts"]

        # Gate 1: Static contract + explicit PhysX applied schemas + BFS joint depth order
        g1_bfs = evaluate_g1_bfs_and_physx_schemas(
            link_count=counts["links"],
            physx_rigid_body_count=usda_meta["physx_rigid_body_count"],
            physx_articulation_count=usda_meta["physx_articulation_count"],
            joints_ordered=usda_meta["joints_ordered"],
        )
        g1_ok = (
            srep.get("status") == "PASS"
            and int(srep.get("articulation_root_count", 0)) == 1
            and g1_bfs["passed"]
        )

        # Gate 2: Reopen, self-containment, CAD richness & frozen bounds
        env_eval = evaluate_frozen_envelope_bounds(
            measured_min=rrep["closed_visual_bounds"]["min"],
            measured_max=rrep["closed_visual_bounds"]["max"],
            expected_wdh_m=hspec["expected_wdh_m"],
            tol_m=float(hspec.get("envelope_tol_m", 0.0025)),
        )
        g2_ok = (
            len(rrep["bad_asset_paths"]) == 0
            and counts["visual_prims"] >= 60
            and counts["meshes"] >= 10
            and counts["materials"] >= 8
            and counts["usd_size_bytes"] >= 150_000
            and env_eval["passed"]
        )

        # Gate 3: Pairwise button/control clearances
        clr_eval = evaluate_pairwise_control_clearances(
            rrep["control_rest_aabbs"],
            min_gap_m=float(hspec.get("min_control_gap_m", 0.003)),
        )
        g3_ok = clr_eval["passed"]

        # Gate 4..8: Isaac Sim 4.1 runtime gates (skipped cleanly when static_only=True)
        runtime_gates: list[dict[str, Any]] = []
        if not static_only:
            g4 = rrep["g4_init"]
            g4_ok = (
                g4["dof_count"] == len(hspec["closed_joint_targets_rad_or_m"])
                and g4["base_drift_120_mm"] <= 0.02
                and g4["max_joint_drift_120"] <= 0.01
            )
            g5 = rrep["g5_motion"]
            g5_ok = (
                all(x["passed"] for x in g5["dof_sweeps"])
                and all(x["passed"] for x in g5["spring_buttons"])
                and bool(g5["composite_knob"]["passed"])
                and len(rrep["ignored_friction_attrs"]) == 0
            )
            g6 = rrep["g6_force_smoke"]
            g6_ok = bool(g6["passed"])
            g7 = rrep["g7_load_600_frames"]
            g7_ok = len(g7) > 0 and all(x["passed"] for x in g7)
            g8 = rrep["g8_rail_transport"]
            g8_ok = bool(g8["passed"])
            runtime_gates = [
                {
                    "id": "G4_isaac_discovery_and_120_settle",
                    "category": "runtime",
                    "passed": g4_ok,
                    "details": g4,
                },
                {
                    "id": "G5_all_dof_spring_and_composite_knob",
                    "category": "runtime",
                    "passed": g5_ok,
                    "details": g5,
                },
                {
                    "id": "G6_direct_force_handle_drawer_smoke",
                    "category": "runtime_physics_smoke",
                    "passed": g6_ok,
                    "details": g6,
                },
                {
                    "id": "G7_600_frame_cavity_load_bearing",
                    "category": "runtime_physics_smoke",
                    "passed": g7_ok,
                    "details": g7,
                },
                {
                    "id": "G8_loaded_rail_tunnel_transport",
                    "category": "runtime_physics_smoke",
                    "passed": g8_ok,
                    "details": g8,
                },
            ]

        # Gate 9a: Automated Objective Appearance Floor
        ev_dir = evidence_root / hspec["evidence_slug"]
        rtx_info = rrep.get("g9_rtx_render") or {}
        g9a_eval = evaluate_g9a_objective_appearance(
            appearance_meta=usda_meta["appearance_meta"],
            studio_dir=ev_dir,
            rtx_info=rtx_info,
            g9a_config=hspec.get("g9a_appearance"),
            usd_dir=usd_file.parent,
            require_rtx=not static_only,
        )

        # Gate 9b: Independent Blind-Review Visual Critic Loop
        critique_path = resolved_critique_dir / f"{slug}_visual_critique_report.json"
        g9b_cfg = dict(hspec.get("g9b_visual_critic") or {})
        if critique_path.is_file():
            critique_payload = json.loads(critique_path.read_text(encoding="utf-8"))
            g9b_eval = evaluate_g9b_visual_critique_report(
                critique_payload,
                repo_root=REPO_ROOT,
                expected_slug=slug,
                min_dimension_score=float(g9b_cfg.get("min_dimension_score", 8.0)),
                max_repair_rounds=int(g9b_cfg.get("max_repair_rounds", 3)),
            )
            g9b_eval["report_path"] = str(critique_path)
        else:
            g9b_eval = {
                "passed": False,
                "report_path": str(critique_path),
                "errors": [f"Missing independent critique report: {critique_path}"],
            }

        gates = [
            {
                "id": "G1_static_contract",
                "category": "static",
                "passed": g1_ok,
                "details": {"status": srep.get("status"), "bfs_and_physx": g1_bfs},
            },
            {
                "id": "G2_reopen_bounds_and_cad_density",
                "category": "reopen",
                "passed": g2_ok,
                "details": {"envelope": env_eval, "counts": counts},
            },
            {
                "id": "G3_pairwise_control_clearance",
                "category": "reopen",
                "passed": g3_ok,
                "details": clr_eval,
            },
            *runtime_gates,
            {
                "id": "G9a_objective_appearance_floor",
                "category": "visual_objective",
                "passed": bool(g9a_eval["passed"]),
                "details": g9a_eval,
            },
            {
                "id": "G9b_independent_visual_critic",
                "category": "visual_critic",
                "passed": bool(g9b_eval["passed"]),
                "details": g9b_eval,
            },
        ]

        asset_rep = build_ika_grade_asset_report(
            slug=slug,
            asset_id=hspec["asset_id"],
            articulation_root="/AssetRoot/Joints/BaseToWorld",
            isaac_runtime=str(rt_all["kit_version"]),
            counts=counts,
            gates=gates,
            source_usd_sha256=usd_sha,
            static_only=static_only,
        )
        out_rep_path = summary_path.parent / f"{slug}_ika_acceptance_report.json"
        out_rep_path.write_text(json.dumps(asset_rep, indent=2) + "\n", encoding="utf-8")
        hero_reports.append(asset_rep)

    expected_pass_token = "PASS_STATIC_ONLY" if static_only else "PASS"
    overall_pass = all(r["implementationStatus"] == expected_pass_token for r in hero_reports)
    total_gates = sum(len(r["checks"]) for r in hero_reports)
    passed_gates = sum(
        sum(1 for g in r["checks"] if g.get("passed")) for r in hero_reports
    )
    summary = {
        "schema_version": "ika-grade-hero-acceptance-summary/v2.0",
        "overall_status": expected_pass_token if overall_pass else "FAIL",
        "passed_gates": passed_gates,
        "total_gates": total_gates,
        "isaac_runtime": str(rt_all["kit_version"]),
        "heroes": hero_reports,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if not overall_pass:
        for r in hero_reports:
            for c in r["checks"]:
                if not c["passed"]:
                    sys.stderr.write(f"[FAIL] {r['slug']} {c['id']}: {json.dumps(c['details'])}\n")
        raise RuntimeError(f"One or more heroes failed IKA-grade acceptance: {summary_path}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Run 10-gate IKA-OVEN-125-grade hero asset acceptance (`GEN-008`)."
    )
    ap.add_argument("--factory-root", type=Path, default=DEFAULT_FACTORY_ROOT)
    ap.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    ap.add_argument(
        "--spec-config",
        type=Path,
        action="append",
        default=None,
        help="Optional YAML/JSON hero spec file or directory (repeatable).",
    )
    ap.add_argument(
        "--critique-dir",
        type=Path,
        default=DEFAULT_CRITIQUE_DIR,
        help="Directory containing <slug>_visual_critique_report.json (`G9b`).",
    )
    ap.add_argument(
        "--out-summary",
        type=Path,
        default=None,
        help="Optional output path for acceptance summary JSON.",
    )
    ap.add_argument(
        "--isaac-python",
        type=Path,
        default=None,
        help="Optional path to Isaac Sim Python executable (overrides ISAAC_PYTHON env).",
    )
    ap.add_argument(
        "--static-only",
        action="store_true",
        help="Run standalone OpenUSD + Blender Cycles verification (G1..G3, G9a, G9b) without Isaac Sim.",
    )
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    froot = args.factory_root if args.factory_root.is_absolute() else (REPO_ROOT / args.factory_root)
    eroot = args.evidence_root if args.evidence_root.is_absolute() else (REPO_ROOT / args.evidence_root)
    cdir = args.critique_dir if args.critique_dir.is_absolute() else (REPO_ROOT / args.critique_dir)
    out_sum = None
    if args.out_summary is not None:
        out_sum = (
            args.out_summary
            if args.out_summary.is_absolute()
            else (REPO_ROOT / args.out_summary)
        )
    spec_cfgs = None
    if args.spec_config:
        spec_cfgs = [
            p if p.is_absolute() else (REPO_ROOT / p) for p in args.spec_config
        ]
    summary = run_9_gate_acceptance(
        factory_root=froot,
        evidence_root=eroot,
        spec_config=spec_cfgs,
        critique_dir=cdir,
        out_summary=out_sum,
        static_only=bool(args.static_only),
        isaac_python=args.isaac_python,
    )
    print(
        f"IKA-Grade 10-Gate Acceptance: {summary['overall_status']} "
        f"({summary['passed_gates']}/{summary['total_gates']} gates) "
        f"across {len(summary['heroes'])} hero machines (runtime={summary['isaac_runtime']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

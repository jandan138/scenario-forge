"""Unit tests for M2 distillation_v06 OpenUSD scene, rear-standing 0%-occlusion camera layout, and 64-ring hoses."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from pxr import Usd, UsdGeom

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from scenario_forge.adapters.distillation_v06.package_builder_v06 import V06_CAMERAS  # noqa: E402


PKG_ROOT = _REPO_ROOT / "external_artifacts" / "distillation_v06_package" / "scenario_package"


def test_v06_scene_usd_loads_with_20_instruments_rear_arms_and_5_cameras() -> None:
    scene_p = PKG_ROOT / "scene" / "main.usda"
    assert scene_p.is_file(), "Run scripts/build_m2_distillation_v06_scene.py first"
    stage = Usd.Stage.Open(str(scene_p))
    assert stage is not None

    for cname in V06_CAMERAS:
        cprim = stage.GetPrimAtPath(f"/World/Cameras/{cname}")
        assert cprim.IsValid() and cprim.IsA(UsdGeom.Camera)

    for hname in ("Hose_Inlet_Lower", "Hose_Outlet_Upper"):
        hprim = stage.GetPrimAtPath(f"/World/CoolingHoses/{hname}")
        assert hprim.IsValid() and hprim.IsA(UsdGeom.Mesh)
        pts = UsdGeom.Mesh(hprim).GetPointsAttr().Get()
        assert len(pts) == 64 * 24

    spec = json.loads((PKG_ROOT / "semantics" / "v06_scene_spec.json").read_text(encoding="utf-8"))
    assert len(spec["cad_specs"]["components"]) == 20


def test_v06_rear_robot_bases_have_zero_foreground_camera_occlusion() -> None:
    spec = json.loads((PKG_ROOT / "semantics" / "v06_scene_spec.json").read_text(encoding="utf-8"))
    cam_eye = np.asarray(V06_CAMERAS["Cam_Master_Front"]["eye"], dtype=np.float64)
    rear_bases = spec["cad_specs"]["layout"]["rear_robot_bases"]

    # Apparatus plane is at y = 0.000; camera is at y = -1.120; robot bases MUST be behind y = +0.350!
    assert cam_eye[1] < -0.90
    for rname, rpose in rear_bases.items():
        by = float(rpose["xyz"][1])
        assert by >= 0.40, f"{rname} base y={by} is not behind the apparatus plane!"

    # Verify line-of-sight from Cam_Master_Front to every assembled instrument is 100% unoccluded by rear robot bases
    for aid, cinfo in spec["cad_specs"]["components"].items():
        tgt = np.asarray(cinfo["assembled_xyz"], dtype=np.float64)
        ray = tgt - cam_eye
        ray_len = float(np.linalg.norm(ray[:2]))
        u2 = ray[:2] / max(ray_len, 1e-9)
        for rname, rpose in rear_bases.items():
            b2 = np.asarray(rpose["xyz"][:2], dtype=np.float64)
            assert b2[1] >= tgt[1] + 0.35, f"{rname} is not >=35cm behind {aid} in +Y!"
            proj = float(np.dot(b2 - cam_eye[:2], u2))
            # Base is strictly FURTHER along camera ray than the assembled instrument!
            assert proj > ray_len + 0.20, f"{rname} occludes sightline to {aid}!"

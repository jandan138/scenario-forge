"""Verification tests for M2 v0.4 7-task dual-arm OpenUSD packages and remediation handler."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_SRC_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

from scenario_forge.adapters.distillation_v04 import (  # noqa: E402
    V04_TASK_SPECS,
    apply_scene_remediation_v04,
)


def test_v04_packages_compose_cleanly_in_usd_with_dual_franka_and_glassware() -> None:
    from pxr import Usd

    pkg_root = _REPO_ROOT / "external_artifacts" / "distillation_v04_packages"
    assert len(V04_TASK_SPECS) == 7

    for task_id, cfg in V04_TASK_SPECS.items():
        pkg = pkg_root / task_id / "scenario_package"
        assert (pkg / "manifest.yaml").is_file()
        assert (pkg / "locks" / "asset_lock.yaml").is_file()
        assert (pkg / "assets" / "glassware_cad_specs.json").is_file()
        assert (pkg / "semantics" / "task_spec.json").is_file()
        scene_path = pkg / "scene" / "main.usda"
        assert scene_path.is_file()
        usda_txt = scene_path.read_text(encoding="utf-8")
        assert "/cpfs/" not in usda_txt and "C:" not in usda_txt and "I:" not in usda_txt

        robot_doc = yaml.safe_load((pkg / "robot" / "robot.yaml").read_text(encoding="utf-8"))
        assert robot_doc["embodiment_id"] == "dual_franka_panda_bimanual"
        assert robot_doc["action_dim"] == 18

        stage = Usd.Stage.Open(str(scene_path))
        assert stage is not None
        assert stage.GetPrimAtPath("/World/franka_left").IsValid()
        assert stage.GetPrimAtPath("/World/franka_right").IsValid()
        assert stage.GetPrimAtPath("/World/pedestal_left").IsValid()
        assert stage.GetPrimAtPath("/World/pedestal_right").IsValid()
        assert stage.GetPrimAtPath("/World/ShowcaseCamera").IsValid()
        assert stage.GetPrimAtPath(f"/World/{cfg['deformable_prim']}").IsValid()
        for comp_id in cfg["initial_states"]:
            assert stage.GetPrimAtPath(f"/World/{comp_id}").IsValid(), f"Missing {comp_id} in {task_id}"

        aid = cfg["m1_asset_id"]
        asset_dir = pkg / "assets" / aid
        assert (asset_dir / "physics_proxy.npz").is_file()
        assert (asset_dir / "skinning.npz").is_file()
        for tex in ("albedo.png", "normal.png", "roughness.png"):
            assert (asset_dir / "textures" / tex).is_file()


def test_v04_scene_remediation_fixes_coaxial_tilt_and_ring_height(tmp_path: Path) -> None:
    def_root = _REPO_ROOT / "external_artifacts" / "distillation_v04_defective_v0"
    v0_d2 = def_root / "distill_02_head_taper_coaxial_mate" / "scenario_package"
    ts_v0 = json.loads((v0_d2 / "semantics" / "task_spec.json").read_text(encoding="utf-8"))
    assert ts_v0["defect_flags"]["scene_fixture_tilted"] is True

    rep_d2 = apply_scene_remediation_v04(
        "distill_02_head_taper_coaxial_mate",
        tmp_path / "repaired_d2" / "scenario_package",
        {"reason_code": "ground_joint_tilt_jam_fracture"},
    )
    rep_dir = Path(rep_d2["repaired_package_dir"])
    inst_v1 = yaml.safe_load((rep_dir / "scene" / "instances.yaml").read_text(encoding="utf-8"))["instances"]
    flask_v1 = [x for x in inst_v1 if x["id"] == "distillation_flask"][0]
    assert abs(float(flask_v1["pose"]["xyz"][0]) + 0.18) < 1e-5
    assert abs(float(flask_v1["pose"]["wxyz"][0]) - 1.0) < 1e-5
    ts_v1 = json.loads((rep_dir / "semantics" / "task_spec.json").read_text(encoding="utf-8"))
    assert ts_v1["defect_flags"] == {}

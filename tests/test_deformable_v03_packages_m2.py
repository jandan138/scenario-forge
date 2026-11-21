"""Verification tests for M2 v0.3 8-task OpenUSD packages and remediation handler."""

from __future__ import annotations

from pathlib import Path
import sys
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
for _p in (str(_SRC_ROOT), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scenario_forge.adapters.deformable_v03 import (  # noqa: E402
    V03_TASK_SPECS,
    apply_scene_remediation,
)


def test_v03_packages_open_cleanly_in_usd_with_pbr_textures() -> None:
    from pxr import Usd

    pkg_root = _REPO_ROOT / "external_artifacts" / "deformable_v03_packages"
    assert len(V03_TASK_SPECS) == 8

    for task_id, cfg in V03_TASK_SPECS.items():
        pkg = pkg_root / task_id / "scenario_package"
        assert (pkg / "manifest.yaml").is_file()
        assert (pkg / "locks" / "asset_lock.yaml").is_file()
        scene_path = pkg / "scene" / "main.usda"
        assert scene_path.is_file()

        stage = Usd.Stage.Open(str(scene_path))
        assert stage is not None
        def_prim = stage.GetPrimAtPath(f"/World/{cfg['deformable_prim']}")
        assert def_prim and def_prim.IsValid(), f"Missing deformable prim in {task_id}"
        robot_prim = stage.GetPrimAtPath("/World/franka_panda")
        assert robot_prim and robot_prim.IsValid(), f"Missing Franka Panda in {task_id}"

        # Confirm high-poly PBR textures + skinning files exist inside package closure
        aid = cfg["m1_asset_id"]
        asset_dir = pkg / "assets" / aid
        assert (asset_dir / "physics_proxy.npz").is_file()
        assert (asset_dir / "skinning.npz").is_file()
        for tex_name in ("albedo.png", "normal.png", "roughness.png"):
            assert (asset_dir / "textures" / tex_name).is_file()


def test_scene_remediation_fixes_obstacle_and_unreachable_defects(tmp_path: Path) -> None:
    def_root = _REPO_ROOT / "external_artifacts" / "deformable_v03_defective_v0"
    v0_smt = def_root / "smt_ribbon_cable_clip_route" / "scenario_package"
    inst_v0 = yaml.safe_load((v0_smt / "scene" / "instances.yaml").read_text(encoding="utf-8"))["instances"]
    esd_v0 = [x for x in inst_v0 if x["id"] == "ESDTray"][0]
    assert abs(float(esd_v0["pose"]["xyz"][0]) - 0.14) < 1e-4

    rep_smt = apply_scene_remediation(
        "smt_ribbon_cable_clip_route",
        tmp_path / "repaired_smt" / "scenario_package",
        {"reason_code": "scene_obstacle_blocking_target"},
    )
    inst_v1 = yaml.safe_load((Path(rep_smt["repaired_package_dir"]) / "scene" / "instances.yaml").read_text(encoding="utf-8"))["instances"]
    esd_v1 = [x for x in inst_v1 if x["id"] == "ESDTray"][0]
    assert float(esd_v1["pose"]["xyz"][0]) < -0.35

    rep_lab = apply_scene_remediation(
        "lab_silicone_tube_manifold_insert",
        tmp_path / "repaired_lab" / "scenario_package",
        {"reason_code": "scene_target_unreachable_or_misaligned"},
    )
    inst_lab_v1 = yaml.safe_load((Path(rep_lab["repaired_package_dir"]) / "scene" / "instances.yaml").read_text(encoding="utf-8"))["instances"]
    saddle_v1 = [x for x in inst_lab_v1 if x["id"] == "manifold_fork_saddle"][0]
    assert abs(float(saddle_v1["pose"]["xyz"][0]) - 0.16) < 1e-4


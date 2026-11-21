"""Unit & OpenUSD integration tests for M2 deformable v0.2 pilot packages."""

from __future__ import annotations

from pathlib import Path

from pxr import Usd, UsdGeom
import yaml

from scenario_forge.adapters.deformable_v02 import build_deformable_v02_pilots
from scenario_forge.package import validate_package


def test_build_and_validate_deformable_v02_pilots(tmp_path: Path) -> None:
    results = build_deformable_v02_pilots(output_root=tmp_path)
    assert set(results.keys()) == {
        "coffee_bar_fragile_pastry_plate",
        "office_desk_wiping_cloth_clean_and_park",
    }

    for pkg_id, res in results.items():
        report = validate_package(res.package_root, require_asset_lock=True)
        assert report.ok, f"{pkg_id} validation failed: {report.messages}"

        stage = Usd.Stage.Open(str(res.scene_usd))
        assert stage is not None
        assert stage.GetPrimAtPath("/World").IsValid()
        assert stage.GetPrimAtPath("/World/table").IsValid()
        assert stage.GetPrimAtPath("/World/franka_panda").IsValid()
        assert stage.GetPrimAtPath("/World/robot_pedestal").IsValid()

        if pkg_id == "coffee_bar_fragile_pastry_plate":
            pastry = stage.GetPrimAtPath("/World/fragile_pastry")
            assert pastry.IsValid()
            assert pastry.GetAttribute("deformable:strainOnsetA").Get() == 0.15
            assert stage.GetPrimAtPath("/World/fragile_pastry/CollisionVolume").HasAttribute("omniphysics:restTetVtxIndices")
            assert stage.GetPrimAtPath("/World/pastry_box_hinged/lid_hinge").IsValid()
            assert stage.GetPrimAtPath("/World/serving_plate").IsValid()
        else:
            cloth = stage.GetPrimAtPath("/World/wiping_cloth")
            assert cloth.IsValid()
            assert cloth.GetAttribute("deformable:strainOnsetA").Get() == 0.20
            assert cloth.HasAttribute("omniphysics:restTriVtxIndices")
            assert stage.GetPrimAtPath("/World/wipe_zone_mat").IsValid()
            assert stage.GetPrimAtPath("/World/cloth_caddy_tray").IsValid()

        # Ensure Franka Panda URDF & MJCF are self-contained without package:// URIs
        panda_urdf = (res.package_root / "assets" / "franka_panda" / "panda.urdf").read_text(encoding="utf-8")
        assert "package://" not in panda_urdf
        assert "meshes/visual/" in panda_urdf
        assert (res.package_root / "assets" / "franka_panda" / "panda.xml").is_file()

        # Verify MuJoCo 4 asset config contains zero Temp paths
        mj4_cfg = res.package_root / "assets" / res.deformable_asset_id / "engines" / "mujoco4" / "mujoco4_asset.json"
        mj4_txt = mj4_cfg.read_text(encoding="utf-8")
        assert "Temp" not in mj4_txt
        assert "/cpfs/" not in mj4_txt
        assert (mj4_cfg.parent / "mesh.obj").is_file()

        # Check mesh point count in OpenUSD
        deform_prim = stage.GetPrimAtPath(
            "/World/fragile_pastry" if pkg_id == "coffee_bar_fragile_pastry_plate" else "/World/wiping_cloth"
        )
        mesh_pts = UsdGeom.Mesh(deform_prim).GetPointsAttr().Get()
        assert len(mesh_pts) > 20

        # Confirm robot YAML specifies 9-DOF Franka Panda
        robot_yaml = yaml.safe_load((res.package_root / "robot" / "robot.yaml").read_text(encoding="utf-8"))
        assert robot_yaml["action_dim"] == 9


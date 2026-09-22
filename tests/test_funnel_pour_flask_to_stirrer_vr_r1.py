from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pxr import Gf, Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_funnel_pour_flask_to_stirrer_vr import (
    FLASK_XYZ,
    STIRRER_XYZ,
    TABLE_HEIGHT_M,
    TASK_ID,
    build_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT / "scripts/generate_scientific_workbench_funnel_pour_flask_to_stirrer_vr.py"
)
REMOVED = (
    "obj_beaker",
    "obj_plate",
    "obj_glass_rod",
    "obj_acrylic_rod_rack",
    "obj_target_reagent_bottle",
    "obj_flask_base",
)
REQUIRED = (
    "obj_funnel",
    "obj_funnel_rack",
    "obj_graduated_cylinder",
    "obj_conical_flask",
    "obj_magnetic_stirrer",
)
CONTEXT = (
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


def test_generator_declares_task04_sources_and_tabletop_flask() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "task_04_pour_liquid_with_funnel" in source
    assert "task_01_pour_flask_to_cylinder" in source
    assert "task_10_titration_experiment" in source
    assert "ConicalFlask90x35Warp" in source
    assert "_author_flask_base" not in source
    assert "canonical_task13_success" in source
    assert "apply_standard_workbench_vr_presentation" not in source or (
        "obj_table/table/Surface/Source/mesh" in source
    )
    assert FLASK_XYZ == (-0.11, -0.16, TABLE_HEIGHT_M)
    assert TABLE_HEIGHT_M == pytest.approx(0.755)
    assert TASK_ID == "scientific_workbench_funnel_pour_flask_to_stirrer"


@pytest.fixture(scope="module")
def handoff(tmp_path_factory, verified_colleague_inputs):
    from scripts import generate_scientific_workbench_funnel_pour_flask_to_stirrer_vr as generator

    manifest = ROOT / "outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_2_20260920/manifest.json"
    with verified_colleague_inputs(generator, manifest):
        return build_handoff(tmp_path_factory.mktemp("funnel_pour") / "package")


@pytest.mark.local_artifacts
def test_handoff_keeps_funnel_rack_and_replaces_reagent_bottle(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    assert stage is not None
    assert stage.GetDefaultPrim().GetPath() == "/World"
    for name in REQUIRED + CONTEXT:
        prim = stage.GetPrimAtPath(f"/World/{name}")
        assert prim.IsValid(), name
        assert prim.IsA(UsdGeom.Xform)
    for name in REMOVED:
        assert not stage.GetPrimAtPath(f"/World/{name}").IsValid(), name
    assert not stage.GetPrimAtPath("/World/obj_stopper").IsValid()
    flask = stage.GetPrimAtPath("/World/obj_conical_flask")
    assert stage.GetPrimAtPath(
        "/World/obj_conical_flask/ConicalFlask90x35Warp"
    ).IsValid()
    assert flask.HasAPI(UsdPhysics.RigidBodyAPI)
    assert not flask.HasAuthoredReferences()
    assert not stage.GetPrimAtPath("/World/obj_funnel").HasAuthoredReferences()
    assert not stage.GetPrimAtPath("/World/obj_magnetic_stirrer").HasAuthoredReferences()
    preview = stage.GetPrimAtPath("/World/obj_funnel_rack/Preview")
    if preview.IsValid():
        assert not preview.IsActive()


@pytest.mark.local_artifacts
def test_handoff_copies_task04_pbd_into_cylinder(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    particle_set = stage.GetPrimAtPath("/World/ParticleSet")
    points = particle_set.GetAttribute("points").Get()
    assert points is not None
    assert len(points) == 986
    widths = particle_set.GetAttribute("widths").Get()
    assert widths is not None
    assert widths[0] == pytest.approx(0.003564, abs=1e-6)
    system = stage.GetPrimAtPath("/World/ParticleSystem")
    assert system.GetAttribute("particleContactOffset").Get() == pytest.approx(0.003)
    assert system.GetAttribute("restOffset").Get() == pytest.approx(0.003)
    shader = stage.GetPrimAtPath("/World/fluid_runtime/LiquidMaterial/PreviewSurface")
    assert list(shader.GetAttribute("inputs:diffuseColor").Get()) == pytest.approx(
        [0.28487948, 0.91, 0.86], abs=1e-5
    )
    cylinder = stage.GetPrimAtPath("/World/obj_graduated_cylinder")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    bounds = cache.ComputeWorldBound(cylinder).ComputeAlignedBox()
    inside = 0
    for point in points:
        if bounds.Contains(Gf.Vec3d(float(point[0]), float(point[1]), float(point[2]))):
            inside += 1
    assert inside >= 900


@pytest.mark.local_artifacts
def test_handoff_sits_flask_on_table_and_leaves_stirrer_empty(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])

    flask = stage.GetPrimAtPath("/World/obj_conical_flask")
    funnel = stage.GetPrimAtPath("/World/obj_funnel")
    rack = stage.GetPrimAtPath("/World/obj_funnel_rack")
    stirrer = stage.GetPrimAtPath("/World/obj_magnetic_stirrer")
    assert list(flask.GetAttribute("xformOp:translate").Get()) == pytest.approx(
        list(FLASK_XYZ)
    )
    assert list(stirrer.GetAttribute("xformOp:translate").Get()) == pytest.approx(
        list(STIRRER_XYZ)
    )

    flask_box = cache.ComputeWorldBound(flask).ComputeAlignedBox()
    assert flask_box.GetMin()[2] == pytest.approx(TABLE_HEIGHT_M, abs=2e-3)

    funnel_box = cache.ComputeWorldBound(funnel).ComputeAlignedBox()
    rack_geom = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/obj_funnel_rack/FunnelRack")
    ).ComputeAlignedBox()
    assert funnel_box.GetMin()[2] >= rack_geom.GetMin()[2] + 0.10
    assert rack_geom.GetMin()[0] <= funnel_box.GetMidpoint()[0] <= rack_geom.GetMax()[0]
    preview = rack.GetChild("Preview")
    if preview.IsValid():
        assert not preview.IsActive()

    stirrer_box = cache.ComputeWorldBound(stirrer).ComputeAlignedBox()
    assert stirrer_box.GetMax()[2] == pytest.approx(0.8267, abs=5e-3)
    assert flask_box.GetMin()[2] < 0.80
    surface = stage.GetPrimAtPath("/World/table/obj_table/table/Surface/Source/mesh")
    assert surface.IsValid()
    assert UsdGeom.Imageable(surface).ComputeVisibility() == UsdGeom.Tokens.invisible


@pytest.mark.local_artifacts
def test_handoff_vr_config_groups_claims_and_closure(handoff) -> None:
    namespace: dict[str, object] = {"__file__": str(handoff.config)}
    exec(handoff.config.read_text(encoding="utf-8"), namespace)
    task = namespace["TASKS"][TASK_ID]
    registered = task["obj_prim_list"]
    for name in REQUIRED + CONTEXT:
        assert f"/World/_scene/{name}" in registered
    assert "/World/_scene/obj_flask_base" not in registered
    groups = {tuple(group["objs"]): group for group in task["layout_randomization"]["objects"]}
    assert ("obj_funnel", "obj_funnel_rack") in groups or (
        "obj_funnel_rack",
        "obj_funnel",
    ) in groups
    flask_group = next(
        group
        for group in task["layout_randomization"]["objects"]
        if "obj_conical_flask" in group["objs"]
    )
    assert flask_group["objs"] == ["obj_conical_flask"]
    cylinder_group = next(
        group
        for group in task["layout_randomization"]["objects"]
        if group["objs"] == ["obj_graduated_cylinder"]
    )
    assert cylinder_group["x_offset_range"] == [0.0, 0.0]
    assert cylinder_group["y_offset_range"] == [0.0, 0.0]
    stirrer_group = next(
        group
        for group in task["layout_randomization"]["objects"]
        if group["objs"] == ["obj_magnetic_stirrer"]
    )
    assert stirrer_group["x_offset_range"] == [-0.01, 0.01]

    manifest = json.loads(handoff.manifest.read_text(encoding="utf-8"))
    claims = manifest["claims"]
    assert claims["authored_pbd_at_rest"] is True
    assert claims["layout_authored"] is True
    assert claims["flask_starts_on_table"] is True
    assert claims["flask_starts_on_task_local_base"] is False
    assert claims["robot_policy_success"] is False
    assert claims["liquid_transfer_verified"] is False
    assert claims["funnel_conduit_qualified"] is False
    assert claims["canonical_task13_success"] is False
    assert claims.get("isaac41_pour_run") in (False, "not_run", None)
    text = json.dumps(claims) + handoff.manifest.read_text(encoding="utf-8")
    assert "pour-success" not in text
    assert "robot success" not in text.lower() or claims["robot_policy_success"] is False

    materialization = json.loads(
        (handoff.root / "object_materialization.json").read_text(encoding="utf-8")
    )
    names = [item["object_name"] for item in materialization["objects"]]
    assert names
    assert "obj_flask_base" not in names
    closure = json.loads(
        (handoff.root / "evidence/package_closure.json").read_text(encoding="utf-8")
    )
    assert closure["unresolved"] == []
    assert handoff.archive.is_file()
    assert (handoff.root / "parity_manifest.json").is_file()
    assert (handoff.root / "README_CN.md").is_file()

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pxr import Gf, Usd, UsdGeom, UsdPhysics

from scripts.generate_scientific_workbench_boat_pour_stir_vr import (
    BOAT_PAN_GAP_M,
    GRAIN_COUNT,
    GRAIN_MASS_KG,
    HANDOFF_ID,
    INSTRUMENT_TARGET_G,
    PLATE_XYZ,
    PROXY_CONTACT_OFFSET_M,
    PROXY_REST_OFFSET_M,
    TARE_G,
    TASK_ID,
    build_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate_scientific_workbench_boat_pour_stir_vr.py"
TASK14_OBJECTS = (
    "obj_analytical_balance",
    "obj_weighing_boat",
    "obj_beaker",
    "obj_graduated_cylinder",
    "obj_glass_rod",
    "obj_acrylic_rod_rack",
    "obj_sampling_spoon",
    "obj_weighing_bottle_body",
    "obj_powder_bottle",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)
BALANCE_LINKS = (
    "obj_analytical_balance/Instance/RightTare",
    "obj_analytical_balance/Instance/Body",
    "obj_analytical_balance/Instance/WeighingPan",
)
RANDOMIZED_ALONE = (
    "obj_beaker",
    "obj_sampling_spoon",
    "obj_weighing_bottle_body",
    "obj_powder_bottle",
    "obj_plate",
    "obj_r9_amber_bottle",
    "obj_r9_tip_box",
    "obj_r9_wash_bottle",
    "obj_r9_clear_bottle",
    "obj_r9_pipette_carousel",
)


def test_generator_declares_task14_sources_and_ids() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    ast.parse(source)
    assert "task_14_fixed_weight_weighing" in source
    assert "task_04_pour_liquid_with_funnel" in source
    assert "task_02_pour_liquid_and_stir" in source
    assert "task09_powder_bottle_r5_7" in source
    assert "powder_pbd" in source
    assert "obj_powder_grain_" in source
    assert "layout_authored_pbd_and_rigid_grains_at_rest" in source
    assert TASK_ID == "scientific_workbench_boat_pour_stir"
    assert HANDOFF_ID == "scientific_workbench_boat_pour_stir_vr_r1"
    assert GRAIN_COUNT == 30
    assert GRAIN_MASS_KG == pytest.approx(2.155132560362598e-6)
    assert TARE_G == pytest.approx(10.0)
    assert INSTRUMENT_TARGET_G == pytest.approx(1.0)
    assert PLATE_XYZ == (-0.34, -0.20, 0.755)
    assert "PhysicsScene" in source
    assert "simulationOwner" in source


@pytest.fixture(scope="module")
def handoff(tmp_path_factory, verified_colleague_inputs):
    from scripts import generate_scientific_workbench_boat_pour_stir_vr as generator

    manifest = ROOT / "outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920/manifest.json"
    with verified_colleague_inputs(generator, manifest):
        return build_handoff(tmp_path_factory.mktemp("boat_pour_stir") / "package")


@pytest.mark.local_artifacts
def test_handoff_keeps_task14_objects_and_adds_plate(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    assert stage is not None
    assert stage.GetDefaultPrim().GetPath() == "/World"
    for name in TASK14_OBJECTS + ("obj_plate",):
        prim = stage.GetPrimAtPath(f"/World/{name}")
        assert prim.IsValid(), name
        assert prim.IsA(UsdGeom.Xform)
    plate = stage.GetPrimAtPath("/World/obj_plate")
    assert list(plate.GetAttribute("xformOp:translate").Get()) == pytest.approx(
        list(PLATE_XYZ), abs=1e-3
    )
    surface = stage.GetPrimAtPath("/World/table/obj_table/table/Surface/Source/mesh")
    assert surface.IsValid()
    assert UsdGeom.Imageable(surface).ComputeVisibility() == UsdGeom.Tokens.invisible
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), [UsdGeom.Tokens.default_], False, True
    )
    plate_box = cache.ComputeWorldBound(plate).ComputeAlignedBox()
    table_box = cache.ComputeWorldBound(surface).ComputeAlignedBox()
    assert plate_box.GetMin()[0] >= table_box.GetMin()[0] + 0.10
    assert plate_box.GetMax()[0] <= table_box.GetMax()[0] - 0.10
    assert plate_box.GetMin()[1] >= table_box.GetMin()[1] + 0.10
    assert plate_box.GetMax()[1] <= table_box.GetMax()[1] - 0.10


@pytest.mark.local_artifacts
def test_handoff_replaces_dry_pbd_with_thirty_r57_grains(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    assert not stage.GetPrimAtPath("/World/powder_pbd").IsValid()
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    boat_box = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/obj_weighing_boat")
    ).ComputeAlignedBox()
    for index in range(GRAIN_COUNT):
        path = f"/World/obj_powder_grain_{index:05d}"
        grain = stage.GetPrimAtPath(path)
        assert grain.IsValid(), path
        assert grain.HasAPI(UsdPhysics.RigidBodyAPI)
        assert grain.GetAttribute("physics:mass").Get() == pytest.approx(
            GRAIN_MASS_KG, rel=1e-6
        )
        mesh = stage.GetPrimAtPath(f"{path}/Mesh")
        assert mesh.IsValid()
        assert mesh.GetAttribute("physxCollision:contactOffset").Get() == pytest.approx(
            0.00025, abs=1e-6
        )
        assert mesh.GetAttribute("physxCollision:restOffset").Get() == pytest.approx(
            0.00015, abs=1e-6
        )
        grain_box = cache.ComputeWorldBound(grain).ComputeAlignedBox()
        assert boat_box.Contains(grain_box.GetMidpoint()), path
    assert not stage.GetPrimAtPath("/World/obj_powder_grain_00030").IsValid()


@pytest.mark.local_artifacts
def test_handoff_places_boat_on_pan_and_pretare(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    boat_box = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/obj_weighing_boat")
    ).ComputeAlignedBox()
    pan_box = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/obj_analytical_balance/Instance/WeighingPan")
    ).ComputeAlignedBox()
    boat_mid = boat_box.GetMidpoint()
    assert pan_box.GetMin()[0] <= boat_mid[0] <= pan_box.GetMax()[0]
    assert pan_box.GetMin()[1] <= boat_mid[1] <= pan_box.GetMax()[1]
    assert boat_box.GetMin()[2] == pytest.approx(
        pan_box.GetMax()[2] + BOAT_PAN_GAP_M, abs=1e-3
    )
    floor = stage.GetPrimAtPath("/World/obj_weighing_boat/PowderProxy/Floor")
    assert floor.GetAttribute("physxCollision:contactOffset").Get() == pytest.approx(
        PROXY_CONTACT_OFFSET_M, abs=1e-6
    )
    assert floor.GetAttribute("physxCollision:restOffset").Get() == pytest.approx(
        PROXY_REST_OFFSET_M, abs=1e-6
    )
    balance = stage.GetPrimAtPath("/World/obj_analytical_balance")
    assert balance.GetAttribute("balance:tare_g").Get() == pytest.approx(TARE_G)
    assert balance.GetAttribute("balance:tared").Get() is True
    assert balance.GetAttribute("balance:lcd_readout").Get() == "0.06 g"
    assert balance.GetAttribute("balance:resolution_g").Get() == pytest.approx(0.01)
    assert balance.GetAttribute("balance:measurement_source").Get() == (
        "pan_contact_force"
    )
    assert balance.GetAttribute("balance:target_g").Get() == pytest.approx(
        INSTRUMENT_TARGET_G
    )
    assert INSTRUMENT_TARGET_G != 30
    physics = stage.GetPrimAtPath("/World/PhysicsScene")
    assert physics.IsValid()
    assert physics.GetAttribute("physxScene:enableGPUDynamics").Get() is True
    assert physics.GetAttribute("physxScene:broadphaseType").Get() == "GPU"
    assert physics.GetAttribute("physxScene:solverType").Get() == "TGS"
    assert physics.GetAttribute("physxScene:timeStepsPerSecond").Get() == 120
    owners = (
        stage.GetPrimAtPath("/World/ParticleSystem")
        .GetRelationship("simulationOwner")
        .GetTargets()
    )
    assert [str(path) for path in owners] == ["/World/PhysicsScene"]


@pytest.mark.local_artifacts
def test_handoff_translates_task04_pbd_into_cylinder(handoff) -> None:
    stage = Usd.Stage.Open(str(handoff.scene), Usd.Stage.LoadAll)
    particle_set = stage.GetPrimAtPath("/World/ParticleSet")
    points = particle_set.GetAttribute("points").Get()
    assert points is not None
    assert len(points) == 986
    widths = particle_set.GetAttribute("widths").Get()
    assert widths is not None
    assert widths[0] == pytest.approx(0.003564, abs=1e-6)
    assert not particle_set.GetAttribute("primvars:displayColor").HasAuthoredValue()
    assert not particle_set.GetAttribute("primvars:displayOpacity").HasAuthoredValue()
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
def test_handoff_vr_config_groups_claims_and_closure(handoff) -> None:
    namespace: dict[str, object] = {"__file__": str(handoff.config)}
    exec(handoff.config.read_text(encoding="utf-8"), namespace)
    task = namespace["TASKS"][TASK_ID]
    registered = task["obj_prim_list"]
    for name in TASK14_OBJECTS + ("obj_plate",) + BALANCE_LINKS:
        assert f"/World/_scene/{name}" in registered
    assert all("obj_powder_grain_" not in path for path in registered)
    groups = task["layout_randomization"]["objects"]
    cylinder_group = next(group for group in groups if group["objs"] == ["obj_graduated_cylinder"])
    assert cylinder_group["x_offset_range"] == [0.0, 0.0]
    assert cylinder_group["y_offset_range"] == [0.0, 0.0]
    boat_group = next(group for group in groups if "obj_weighing_boat" in group["objs"])
    assert "obj_analytical_balance" in boat_group["objs"]
    assert boat_group["x_offset_range"] == [0.0, 0.0]
    assert boat_group["y_offset_range"] == [0.0, 0.0]
    rod_group = next(group for group in groups if "obj_glass_rod" in group["objs"])
    assert "obj_acrylic_rod_rack" in rod_group["objs"]
    for name in RANDOMIZED_ALONE:
        group = next(item for item in groups if item["objs"] == [name])
        assert group["x_offset_range"] == [-0.01, 0.01]
        assert group["y_offset_range"] == [-0.01, 0.01]
    assert task["physx_scene_cfg"]["SolverType"] == "TGS"
    assert task["physx_scene_cfg"]["TimeStepsPerSecond"] == 120
    assert task["physx_scene_cfg"]["EnableGPUDynamics"] is True
    assert task["claim_scope"] == "layout_authored_pbd_and_rigid_grains_at_rest"

    manifest = json.loads(handoff.manifest.read_text(encoding="utf-8"))
    claims = manifest["claims"]
    assert claims["layout_authored"] is True
    assert claims["authored_pbd_at_rest"] is True
    assert claims["authored_rigid_grains_at_rest"] is True
    assert claims["pbd_particle_count"] == 986
    assert claims["rigid_grain_count"] == 30
    assert claims["liquid_transfer_verified"] is False
    assert claims["dissolve_verified"] is False
    assert claims["robot_policy_success"] is False
    assert claims["benchmark_success"] is False
    assert claims["scene_fixture_verified"] is False
    assert claims.get("isaac45_runtime_smoke") in (False, "not_run", None)

    materialization = json.loads(
        (handoff.root / "object_materialization.json").read_text(encoding="utf-8")
    )
    assert materialization["objects"]
    closure = json.loads(
        (handoff.root / "evidence/package_closure.json").read_text(encoding="utf-8")
    )
    assert closure["unresolved"] == []
    assert handoff.archive.is_file()
    assert (handoff.root / "parity_manifest.json").is_file()
    assert (handoff.root / "README_CN.md").is_file()
    metrics = (handoff.root / "metrics.yaml").read_text(encoding="utf-8")
    assert "0.25" in metrics
    assert "boat_poured_toward_beaker" in metrics

from __future__ import annotations

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from scenario_forge.validation.articulated_instance_layout import (
    ArticulatedInstanceLayoutError,
    validate_fixed_base_articulation_layout,
    validate_articulated_instance_layout,
)


def _scene(path: Path, *, compliant: bool) -> Path:
    stage = Usd.Stage.CreateNew(str(path))
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    root = UsdGeom.Xform.Define(stage, "/World/obj_device")
    parent = "/World/obj_device/Instance" if compliant else "/World/obj_device"
    if compliant:
        UsdGeom.Scope.Define(stage, parent)
    body = UsdGeom.Xform.Define(stage, parent + "/Body").GetPrim()
    door = UsdGeom.Xform.Define(stage, parent + "/Door").GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(body)
    UsdPhysics.RigidBodyAPI.Apply(door)
    joint = UsdPhysics.RevoluteJoint.Define(stage, parent + "/Joints/Door")
    joint.CreateBody0Rel().SetTargets([body.GetPath()])
    joint.CreateBody1Rel().SetTargets([door.GetPath()])
    root.GetPrim().SetCustomDataByKey("scenario_forge:objectRole", "articulated_object")
    stage.GetRootLayer().Save()
    return path


def test_validator_accepts_scope_instance_and_all_links_below_it(tmp_path: Path) -> None:
    report = validate_articulated_instance_layout(
        _scene(tmp_path / "pass.usda", compliant=True), ["/World/obj_device"]
    )
    assert report["status"] == "pass"
    assert report["objects"][0]["instance_type"] == "Scope"


def test_validator_rejects_link_outside_instance(tmp_path: Path) -> None:
    with pytest.raises(ArticulatedInstanceLayoutError, match="outside /Instance"):
        validate_articulated_instance_layout(
            _scene(tmp_path / "blocked.usda", compliant=False),
            ["/World/obj_device"],
        )


def _fixed_articulation_scene(
    path: Path, *, instance_type: str = "Xform", base_kinematic: bool = False
) -> Path:
    stage = Usd.Stage.CreateNew(str(path))
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    root = UsdGeom.Xform.Define(stage, "/World/obj_device").GetPrim()
    UsdPhysics.ArticulationRootAPI.Apply(root)
    root.CreateAttribute("physxArticulation:articulationEnabled", Sdf.ValueTypeNames.Bool).Set(True)
    if instance_type == "Xform":
        UsdGeom.Xform.Define(stage, "/World/obj_device/Instance")
    else:
        UsdGeom.Scope.Define(stage, "/World/obj_device/Instance")
    body = UsdGeom.Xform.Define(stage, "/World/obj_device/Instance/Body").GetPrim()
    door = UsdGeom.Xform.Define(stage, "/World/obj_device/Instance/Door").GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(body).CreateKinematicEnabledAttr(base_kinematic)
    UsdPhysics.RigidBodyAPI.Apply(door).CreateKinematicEnabledAttr(False)
    hinge = UsdPhysics.RevoluteJoint.Define(stage, "/World/obj_device/Instance/Joints/Door")
    hinge.CreateBody0Rel().SetTargets([body.GetPath()])
    hinge.CreateBody1Rel().SetTargets([door.GetPath()])
    fixed = UsdPhysics.FixedJoint.Define(stage, "/World/obj_device/Instance/Joints/BaseFixed")
    fixed.CreateBody0Rel().SetTargets([root.GetPath()])
    fixed.CreateBody1Rel().SetTargets([body.GetPath()])
    stage.GetRootLayer().Save()
    return path


def test_v2_validator_accepts_identity_xform_fixed_base_articulation(
    tmp_path: Path,
) -> None:
    report = validate_fixed_base_articulation_layout(
        _fixed_articulation_scene(tmp_path / "fixed.usda"),
        ["/World/obj_device"],
    )
    assert report["status"] == "pass"
    assert report["schema_version"].endswith("/v2")
    assert report["objects"][0]["dof_joint_count"] == 1


@pytest.mark.parametrize(
    ("instance_type", "base_kinematic", "message"),
    [("Scope", False, "identity Xform"), ("Xform", True, "kinematic")],
)
def test_v2_validator_blocks_scope_or_kinematic_links(
    tmp_path: Path,
    instance_type: str,
    base_kinematic: bool,
    message: str,
) -> None:
    with pytest.raises(ArticulatedInstanceLayoutError, match=message):
        validate_fixed_base_articulation_layout(
            _fixed_articulation_scene(
                tmp_path / f"blocked-{instance_type}-{base_kinematic}.usda",
                instance_type=instance_type,
                base_kinematic=base_kinematic,
            ),
            ["/World/obj_device"],
        )

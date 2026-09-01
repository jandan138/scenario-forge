from __future__ import annotations

from pathlib import Path

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from scenario_forge.validation.articulated_instance_layout import (
    ArticulatedInstanceLayoutError,
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

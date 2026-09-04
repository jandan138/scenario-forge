from __future__ import annotations

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from scenario_forge.adapters.vr_teleop import (
    VRTeleopExportError,
    _task_config_python,
    articulated_vr_registration_paths,
)


def _fixed_base_articulation_scene(
    path: Path, *, scope_instance: bool = False
) -> Path:
    stage = Usd.Stage.CreateNew(str(path))
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    root = UsdGeom.Xform.Define(stage, "/World/obj_device").GetPrim()
    UsdPhysics.ArticulationRootAPI.Apply(root)
    root.CreateAttribute(
        "physxArticulation:articulationEnabled", Sdf.ValueTypeNames.Bool
    ).Set(True)
    if scope_instance:
        UsdGeom.Scope.Define(stage, "/World/obj_device/Instance")
    else:
        UsdGeom.Xform.Define(stage, "/World/obj_device/Instance")
    body = UsdGeom.Xform.Define(stage, "/World/obj_device/Instance/Body").GetPrim()
    door = UsdGeom.Xform.Define(stage, "/World/obj_device/Instance/Door").GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(body).CreateKinematicEnabledAttr(False)
    UsdPhysics.RigidBodyAPI.Apply(door).CreateKinematicEnabledAttr(False)
    hinge = UsdPhysics.RevoluteJoint.Define(
        stage, "/World/obj_device/Instance/Joints/Door"
    )
    hinge.CreateBody0Rel().SetTargets([body.GetPath()])
    hinge.CreateBody1Rel().SetTargets([door.GetPath()])
    fixed = UsdPhysics.FixedJoint.Define(
        stage, "/World/obj_device/Instance/Joints/BaseFixed"
    )
    fixed.CreateBody0Rel().SetTargets([root.GetPath()])
    fixed.CreateBody1Rel().SetTargets([body.GetPath()])
    stage.GetRootLayer().Save()
    return path


def test_vr_articulation_registers_root_and_every_rigid_link(tmp_path: Path) -> None:
    registered = articulated_vr_registration_paths(
        _fixed_base_articulation_scene(tmp_path / "device.usda"),
        scene_root="/World/obj_device",
        runtime_root="/World/_scene/obj_device",
    )
    assert registered == [
        "/World/_scene/obj_device",
        "/World/_scene/obj_device/Instance/Body",
        "/World/_scene/obj_device/Instance/Door",
    ]


def test_vr_articulation_rejects_legacy_scope_instance(tmp_path: Path) -> None:
    with pytest.raises(VRTeleopExportError, match="identity Xform"):
        articulated_vr_registration_paths(
            _fixed_base_articulation_scene(
                tmp_path / "legacy.usda", scope_instance=True
            ),
            scene_root="/World/obj_device",
            runtime_root="/World/_scene/obj_device",
        )


def test_registered_articulation_links_are_not_randomized_independently(
    tmp_path: Path,
) -> None:
    registered = articulated_vr_registration_paths(
        _fixed_base_articulation_scene(tmp_path / "device.usda"),
        scene_root="/World/obj_device",
        runtime_root="/World/_scene/obj_device",
    )
    config_text = _task_config_python(
        task_id="future_articulated_task",
        robot={
            "spawn": {
                "xyz": [0.0, 0.0, 0.0],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            }
        },
        objects=[{"id": "obj_device", "metadata": {}}],
        object_prim_paths=registered,
    )
    namespace: dict[str, object] = {"_ASSETS_DIR": Path("/tmp/assets")}
    exec(config_text, namespace)
    task = namespace["TASKS"]["future_articulated_task"]  # type: ignore[index]
    assert task["obj_prim_list"] == registered  # type: ignore[index]
    assert task["layout_randomization"]["objects"] == [  # type: ignore[index]
        {
            "objs": ["obj_device"],
            "mode": "local",
            "yaw_range_degrees": [0.0, 0.0],
            "x_offset_range": [-0.01, 0.01],
            "y_offset_range": [-0.01, 0.01],
        }
    ]

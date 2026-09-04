"""Final-scene contract for articulated objects mounted below `/Instance`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


class ArticulatedInstanceLayoutError(ValueError):
    """Raised when a generated articulated scene violates the Instance contract."""


def validate_articulated_instance_layout(
    scene: str | Path,
    object_roots: Iterable[str],
) -> dict[str, Any]:
    from pxr import Usd, UsdGeom, UsdPhysics

    stage = Usd.Stage.Open(str(Path(scene).resolve()))
    if stage is None:
        raise ArticulatedInstanceLayoutError(f"cannot open articulated scene: {scene}")
    reports = []
    blockers = []
    for raw_root in object_roots:
        root = stage.GetPrimAtPath(raw_root)
        instance_path = raw_root.rstrip("/") + "/Instance"
        instance = stage.GetPrimAtPath(instance_path)
        links = (
            [
                str(prim.GetPath())
                for prim in Usd.PrimRange(root)
                if prim.HasAPI(UsdPhysics.RigidBodyAPI)
            ]
            if root
            else []
        )
        outside = [path for path in links if not path.startswith(instance_path + "/")]
        invalid_targets = []
        if root:
            for prim in Usd.PrimRange(root):
                if not prim.IsA(UsdPhysics.Joint):
                    continue
                for name in ("physics:body0", "physics:body1"):
                    for target in prim.GetRelationship(name).GetTargets():
                        if str(target).startswith(raw_root.rstrip("/") + "/") and (
                            not str(target).startswith(instance_path + "/")
                            or not stage.GetPrimAtPath(target)
                        ):
                            invalid_targets.append(
                                {
                                    "joint": str(prim.GetPath()),
                                    "relationship": name,
                                    "target": str(target),
                                }
                            )
        if not instance:
            blockers.append(f"articulated object {raw_root} is missing /Instance")
        elif not instance.IsA(UsdGeom.Scope):
            blockers.append(f"articulated object {raw_root}/Instance must be a Scope")
        if not links:
            blockers.append(f"articulated object {raw_root} has no rigid links")
        if outside:
            blockers.append(f"articulated object {raw_root} has links outside /Instance: {outside}")
        if invalid_targets:
            blockers.append(
                f"articulated object {raw_root} has invalid joint targets: {invalid_targets}"
            )
        reports.append(
            {
                "object_root": raw_root,
                "instance_prim_path": instance_path,
                "instance_type": instance.GetTypeName() if instance else None,
                "link_prim_paths": links,
                "links_outside_instance": outside,
                "invalid_joint_targets": invalid_targets,
            }
        )
    if blockers:
        raise ArticulatedInstanceLayoutError("; ".join(blockers))
    return {
        "schema_version": "scenario-forge.articulated-instance-layout/v1",
        "status": "pass",
        "objects": reports,
    }


def validate_fixed_base_articulation_layout(
    scene: str | Path,
    object_roots: Iterable[str],
) -> dict[str, Any]:
    """Validate the v2 transformable Instance and fixed-base articulation contract."""

    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    stage = Usd.Stage.Open(str(Path(scene).resolve()))
    if stage is None:
        raise ArticulatedInstanceLayoutError(f"cannot open articulated scene: {scene}")
    reports = []
    blockers = []
    for raw_root in object_roots:
        root_path = raw_root.rstrip("/")
        instance_path = root_path + "/Instance"
        base_path = instance_path + "/Body"
        fixed_path = instance_path + "/Joints/BaseFixed"
        root = stage.GetPrimAtPath(root_path)
        instance = stage.GetPrimAtPath(instance_path)
        base = stage.GetPrimAtPath(base_path)
        fixed = stage.GetPrimAtPath(fixed_path)
        links = (
            [prim for prim in Usd.PrimRange(root) if prim.HasAPI(UsdPhysics.RigidBodyAPI)]
            if root
            else []
        )
        link_paths = [str(prim.GetPath()) for prim in links]
        outside = [path for path in link_paths if not path.startswith(instance_path + "/")]
        kinematic = [
            str(prim.GetPath())
            for prim in links
            if bool(prim.GetAttribute("physics:kinematicEnabled").Get())
        ]
        identity_xform = (
            bool(instance)
            and instance.IsA(UsdGeom.Xform)
            and Gf.IsClose(
                UsdGeom.Xformable(instance).GetLocalTransformation(),
                Gf.Matrix4d(1.0),
                1.0e-9,
            )
        )
        fixed_body0 = (
            [str(path) for path in fixed.GetRelationship("physics:body0").GetTargets()]
            if fixed
            else []
        )
        fixed_body1 = (
            [str(path) for path in fixed.GetRelationship("physics:body1").GetTargets()]
            if fixed
            else []
        )
        invalid_targets = []
        dof_joint_count = 0
        if root:
            for prim in Usd.PrimRange(root):
                if not prim.IsA(UsdPhysics.Joint):
                    continue
                if prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.PrismaticJoint):
                    dof_joint_count += 1
                for name in ("physics:body0", "physics:body1"):
                    for target in prim.GetRelationship(name).GetTargets():
                        target_text = str(target)
                        allowed_root_anchor = (
                            str(prim.GetPath()) == fixed_path
                            and name == "physics:body0"
                            and target_text == root_path
                        )
                        if target_text.startswith(root_path + "/") and (
                            (
                                not target_text.startswith(instance_path + "/")
                                and not allowed_root_anchor
                            )
                            or not stage.GetPrimAtPath(target)
                        ):
                            invalid_targets.append(
                                {
                                    "joint": str(prim.GetPath()),
                                    "relationship": name,
                                    "target": target_text,
                                }
                            )
        checks = {
            "articulation_root_api": bool(root) and root.HasAPI(UsdPhysics.ArticulationRootAPI),
            "articulation_enabled": bool(root)
            and root.GetAttribute("physxArticulation:articulationEnabled").Get() is True,
            "instance_identity_xform": identity_xform,
            "rigid_links_present": bool(links),
            "all_links_under_instance": not outside,
            "all_links_nonkinematic": not kinematic,
            "base_rigid_link": bool(base) and base.HasAPI(UsdPhysics.RigidBodyAPI),
            "base_fixed_joint": bool(fixed) and fixed.IsA(UsdPhysics.FixedJoint),
            "base_fixed_body0": fixed_body0 == [root_path],
            "base_fixed_body1": fixed_body1 == [base_path],
            "joint_targets_valid": not invalid_targets,
        }
        if not checks["articulation_root_api"]:
            blockers.append(f"articulated object {raw_root} has no Articulation Root API")
        if not checks["articulation_enabled"]:
            blockers.append(f"articulated object {raw_root} has articulation disabled")
        if not checks["instance_identity_xform"]:
            blockers.append(f"articulated object {raw_root}/Instance must be an identity Xform")
        if not checks["rigid_links_present"]:
            blockers.append(f"articulated object {raw_root} has no rigid links")
        if outside:
            blockers.append(f"articulated object {raw_root} has links outside /Instance: {outside}")
        if kinematic:
            blockers.append(f"articulated object {raw_root} has kinematic links: {kinematic}")
        if not checks["base_rigid_link"]:
            blockers.append(f"articulated object {raw_root} has no rigid base link at {base_path}")
        if not all(
            checks[name] for name in ("base_fixed_joint", "base_fixed_body0", "base_fixed_body1")
        ):
            blockers.append(f"articulated object {raw_root} has an invalid BaseFixed joint")
        if invalid_targets:
            blockers.append(
                f"articulated object {raw_root} has invalid joint targets: {invalid_targets}"
            )
        reports.append(
            {
                "object_root": root_path,
                "instance_prim_path": instance_path,
                "instance_type": instance.GetTypeName() if instance else None,
                "base_link_prim_path": base_path,
                "base_fixed_joint_prim_path": fixed_path,
                "link_prim_paths": link_paths,
                "links_outside_instance": outside,
                "kinematic_link_prim_paths": kinematic,
                "invalid_joint_targets": invalid_targets,
                "dof_joint_count": dof_joint_count,
                "checks": checks,
            }
        )
    if blockers:
        raise ArticulatedInstanceLayoutError("; ".join(blockers))
    return {
        "schema_version": "scenario-forge.articulated-instance-layout/v2",
        "status": "pass",
        "objects": reports,
    }

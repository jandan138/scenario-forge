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
        links = [
            str(prim.GetPath())
            for prim in Usd.PrimRange(root)
            if prim.HasAPI(UsdPhysics.RigidBodyAPI)
        ] if root else []
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
                                {"joint": str(prim.GetPath()), "relationship": name, "target": str(target)}
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
            blockers.append(f"articulated object {raw_root} has invalid joint targets: {invalid_targets}")
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

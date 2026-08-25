"""VR-only presentation policies for composed scenario scenes."""

from __future__ import annotations

from pathlib import Path
from typing import Any


STANDARD_WORKBENCH_ASSET_ID = "scientific_workbench_ebench_table_static_support"
_STANDARD_WORKBENCH_SURFACE_PATHS = (
    "/World/table/Surface/Source/mesh",
    "/World/table/table/Surface/Source/mesh",
)


class VRPresentationPolicyError(ValueError):
    """Raised when a required VR presentation policy cannot be applied."""


def apply_standard_workbench_vr_presentation(
    scene_path: str | Path, *, table_asset_id: str
) -> dict[str, Any]:
    """Hide the standard workbench surface visually while retaining physics."""

    if table_asset_id != STANDARD_WORKBENCH_ASSET_ID:
        return {
            "policy": "standard_workbench_surface_hidden",
            "status": "not_applicable",
            "table_asset_id": table_asset_id,
        }
    try:
        from pxr import Usd, UsdGeom  # type: ignore
    except ImportError as exc:
        raise VRPresentationPolicyError(
            "VR presentation finalization requires the USD Python runtime"
        ) from exc

    scene = Path(scene_path).resolve()
    stage = Usd.Stage.Open(str(scene), Usd.Stage.LoadAll)
    if stage is None:
        raise VRPresentationPolicyError(f"cannot open VR scene: {scene}")
    matches = [
        path
        for path in _STANDARD_WORKBENCH_SURFACE_PATHS
        if stage.GetPrimAtPath(path).IsValid()
    ]
    if len(matches) != 1:
        detail = "missing" if not matches else "ambiguous"
        raise VRPresentationPolicyError(
            f"standard workbench surface mesh is {detail}: {scene}"
        )

    prim_path = matches[0]
    prim = stage.GetPrimAtPath(prim_path)
    imageable = UsdGeom.Imageable(prim)
    if not imageable:
        raise VRPresentationPolicyError(
            f"standard workbench surface mesh is not imageable: {prim_path}"
        )
    active_before = prim.IsActive()
    collision_before = prim.GetAttribute("physics:collisionEnabled").Get()
    stage.SetEditTarget(stage.GetRootLayer())
    imageable.MakeInvisible()
    stage.GetRootLayer().Save()

    if not prim.IsActive() or prim.IsActive() != active_before:
        raise VRPresentationPolicyError(
            f"VR presentation policy changed active state: {prim_path}"
        )
    if prim.GetAttribute("physics:collisionEnabled").Get() != collision_before:
        raise VRPresentationPolicyError(
            f"VR presentation policy changed collision state: {prim_path}"
        )
    if imageable.ComputeVisibility() != UsdGeom.Tokens.invisible:
        raise VRPresentationPolicyError(
            f"VR presentation policy did not hide surface mesh: {prim_path}"
        )
    return {
        "policy": "standard_workbench_surface_hidden",
        "status": "applied",
        "table_asset_id": table_asset_id,
        "prim_path": prim_path,
        "visibility": "invisible",
        "collision_preserved": True,
    }

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scenario_forge.adapters.vr_object_materialization import (
    VRObjectMaterializationError,
    materialize_vr_object_subtrees,
    validate_vr_variant_object_parity,
)


def _write_payload_scene(
    root: Path,
    *,
    root_x: float = 0.1,
    visual_z: float | None = 0.02,
    collider_size: float = 0.3,
    asset_dependency: str | None = None,
) -> tuple[Path, Path]:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

    dependency = root / "deps/objects/plate"
    dependency.mkdir(parents=True)
    if asset_dependency == "./textures/albedo.png":
        (dependency / "textures").mkdir()
        (dependency / "textures/albedo.png").write_bytes(b"same-texture")
    asset_path = dependency / "asset.usda"
    asset = Usd.Stage.CreateNew(str(asset_path))
    asset_root = UsdGeom.Xform.Define(asset, "/Plate").GetPrim()
    asset.SetDefaultPrim(asset_root)
    visual = UsdGeom.Xform.Define(asset, "/Plate/Visual")
    if visual_z is not None:
        visual.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, visual_z))
    mesh = UsdGeom.Cube.Define(asset, "/Plate/Visual/Mesh")
    mesh.CreateSizeAttr(collider_size)
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    if asset_dependency is not None:
        mesh.GetPrim().CreateAttribute(
            "inputs:file", Sdf.ValueTypeNames.Asset
        ).Set(Sdf.AssetPath(asset_dependency))
    asset.GetRootLayer().Save()

    scene_path = root / "scene.usd"
    scene = Usd.Stage.CreateNew(str(scene_path))
    world = UsdGeom.Xform.Define(scene, "/World").GetPrim()
    scene.SetDefaultPrim(world)
    plate = UsdGeom.Xform.Define(scene, "/World/obj_plate")
    plate.AddTranslateOp().Set(Gf.Vec3d(root_x, -0.2, 0.8))
    plate.GetPrim().GetPayloads().AddPayload(
        "./deps/objects/plate/asset.usda", "/Plate"
    )
    scene.GetRootLayer().Save()
    return scene_path, dependency


def _materialize(root: Path, **kwargs: Any) -> Path:
    scene, dependency = _write_payload_scene(root, **kwargs)
    evidence = root / "object_materialization.json"
    materialize_vr_object_subtrees(
        scene_path=scene,
        scene_prim_paths=["/World/obj_plate"],
        runtime_prim_paths=["/World/_scene/obj_plate"],
        evidence_path=evidence,
        prunable_dependency_roots=[dependency],
    )
    return evidence


def test_materializes_payload_object_without_lifting_transforms(tmp_path: Path) -> None:
    evidence_path = _materialize(tmp_path)

    scene_text = (tmp_path / "scene.usd").read_text(encoding="utf-8")
    assert "payload" not in scene_text
    assert 'def Cube "Mesh"' in scene_text
    assert "PhysicsCollisionAPI" in scene_text
    assert not (tmp_path / "deps/objects/plate/asset.usda").exists()

    from pxr import Usd

    stage = Usd.Stage.Open(str(tmp_path / "scene.usd"))
    assert stage is not None
    assert tuple(
        stage.GetPrimAtPath("/World/obj_plate")
        .GetAttribute("xformOp:translate")
        .Get()
    ) == (0.1, -0.2, 0.8)
    assert tuple(
        stage.GetPrimAtPath("/World/obj_plate/Visual")
        .GetAttribute("xformOp:translate")
        .Get()
    ) == (0.0, 0.0, 0.02)

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == (
        "scenario-forge-vr-object-materialization/v0.1"
    )
    assert evidence["status"] == "pass"
    assert evidence["objects"][0]["composition_arcs_after"] == 0
    assert evidence["objects"][0]["transform_equivalent"] is True


def test_allows_partial_root_trs_and_child_only_transform(tmp_path: Path) -> None:
    evidence = _materialize(tmp_path, root_x=0.0, visual_z=0.81)

    report = json.loads(evidence.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["objects"][0]["transform_equivalent"] is True


def test_rejects_non_xform_object_root(tmp_path: Path) -> None:
    from pxr import Usd, UsdGeom

    scene = Usd.Stage.CreateNew(str(tmp_path / "scene.usd"))
    world = UsdGeom.Xform.Define(scene, "/World").GetPrim()
    scene.SetDefaultPrim(world)
    UsdGeom.Cube.Define(scene, "/World/obj_plate")
    scene.GetRootLayer().Save()

    with pytest.raises(VRObjectMaterializationError, match="must be an Xform"):
        materialize_vr_object_subtrees(
            scene_path=tmp_path / "scene.usd",
            scene_prim_paths=["/World/obj_plate"],
            runtime_prim_paths=["/World/_scene/obj_plate"],
            evidence_path=tmp_path / "object_materialization.json",
        )


def test_rejects_missing_or_remote_object_dependencies(tmp_path: Path) -> None:
    for label, dependency in (
        ("missing", "./missing_texture.png"),
        ("remote", "https://example.invalid/texture.png"),
    ):
        root = tmp_path / label
        scene, dependency_root = _write_payload_scene(
            root, asset_dependency=dependency
        )
        with pytest.raises(VRObjectMaterializationError, match="dependenc"):
            materialize_vr_object_subtrees(
                scene_path=scene,
                scene_prim_paths=["/World/obj_plate"],
                runtime_prim_paths=["/World/_scene/obj_plate"],
                evidence_path=root / "object_materialization.json",
                prunable_dependency_roots=[dependency_root],
            )


def test_variant_parity_ignores_all_transform_opinions(tmp_path: Path) -> None:
    fill20 = _materialize(
        tmp_path / "fill20",
        root_x=0.1,
        visual_z=None,
        asset_dependency="./textures/albedo.png",
    )
    fill80 = _materialize(
        tmp_path / "fill80",
        root_x=0.3,
        visual_z=0.02,
        asset_dependency="./textures/albedo.png",
    )
    parity = tmp_path / "variant_object_parity.json"

    report = validate_vr_variant_object_parity(
        {"fill20": fill20, "fill80": fill80}, evidence_path=parity
    )

    assert report["status"] == "pass"
    assert report["objects"][0]["object_name"] == "obj_plate"
    assert parity.is_file()


def test_variant_parity_rejects_non_transform_physics_drift(tmp_path: Path) -> None:
    fill20 = _materialize(tmp_path / "fill20", collider_size=0.3)
    fill80 = _materialize(tmp_path / "fill80", collider_size=0.4)

    with pytest.raises(
        VRObjectMaterializationError, match="non-transform content differs"
    ):
        validate_vr_variant_object_parity(
            {"fill20": fill20, "fill80": fill80},
            evidence_path=tmp_path / "variant_object_parity.json",
        )

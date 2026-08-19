from __future__ import annotations

from pathlib import Path

import pytest

import scripts.generate_scientific_workbench_task02_r10_3_colleague_collision as exp


def test_colleague_collision_override_contains_the_complete_profile() -> None:
    text = exp.collision_override_usda(ebench=True)

    assert 'float restOffset = 0.009' in text
    assert 'float physxParticleIsosurface:gridSmoothingRadius = 0.005' in text
    assert text.count('uniform token physics:approximation = "sdf"') == 4
    assert text.count('uniform token physics:approximation = "convexHull"') == 5
    assert text.count('uint physxSDFMeshCollision:sdfResolution = 256') == 4
    assert text.count('uint physxConvexHullCollision:hullVertexLimit = 64') == 5
    assert text.count('bool physics:collisionEnabled = 0') == 2
    assert 'over "obj_obj_graduated_cylinder"' in text
    assert 'over "obj_obj_beaker"' in text


def test_vr_override_uses_direct_open_object_paths() -> None:
    text = exp.collision_override_usda(ebench=False)

    assert 'over "obj_graduated_cylinder"' in text
    assert 'over "obj_beaker"' in text
    assert 'over "obj_obj_graduated_cylinder"' not in text
    assert 'over "fluid_runtime"' in text


def test_left_edge_position_preserves_randomization_margin() -> None:
    assert exp.RACK_XYZ == (-0.8845, -0.17, 0.755)
    assert exp.ROD_XYZ == (-0.8845, -0.17, 0.77243)
    rack_half_width = 0.10509
    randomized_left_edge = exp.RACK_XYZ[0] - 0.01 - rack_half_width
    assert randomized_left_edge >= -1.0


def test_collision_profile_is_composed_as_a_separate_layer(tmp_path: Path) -> None:
    pytest.importorskip("pxr")
    from pxr import Sdf, Usd

    scene = tmp_path / "scene.usda"
    scene.write_text(
        '''#usda 1.0
(
    defaultPrim = "World"
)
def Xform "World" {}
''',
        encoding="utf-8",
    )

    exp._install_overlay(scene, ebench=False)

    scene_text = scene.read_text(encoding="utf-8")
    overlay = tmp_path / exp.OVERLAY_NAME
    assert scene_text.count('def Xform "World"') == 1
    assert scene_text.count('over "World"') == 0
    assert f"@{exp.OVERLAY_NAME}@" in scene_text
    assert overlay.is_file()
    assert overlay.read_text(encoding="utf-8").count('over "World"') == 1
    assert Sdf.Layer.FindOrOpen(str(scene)) is not None
    assert Sdf.Layer.FindOrOpen(str(overlay)) is not None
    stage = Usd.Stage.Open(str(scene))
    assert stage is not None
    assert stage.GetPrimAtPath("/World/obj_graduated_cylinder").IsValid()

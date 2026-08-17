from __future__ import annotations

from pathlib import Path
import runpy

import pytest


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts/generate_visual_static_liquid_prototype.py"
)
RENDERER = (
    Path(__file__).parents[1]
    / "scripts/ebench/render_visual_static_liquid_prototype.py"
)


def _module() -> dict[str, object]:
    return runpy.run_path(str(SCRIPT))


def _renderer_module() -> dict[str, object]:
    return runpy.run_path(str(RENDERER))


def test_volume_fraction_height_is_linear_for_cylinder() -> None:
    height_for_volume_fraction = _module()["height_for_volume_fraction"]

    assert height_for_volume_fraction(
        [(0.004, 0.0335), (0.109, 0.0335)], 0.60
    ) == pytest.approx(0.067, abs=1e-6)


def test_volume_fraction_height_accounts_for_conical_cross_section() -> None:
    height_for_volume_fraction = _module()["height_for_volume_fraction"]
    height = height_for_volume_fraction(
        [(0.004, 0.0602), (0.110, 0.0005)], 0.70
    )

    assert 0.035 < height < 0.045


def test_config_validation_rejects_invalid_fill_fraction() -> None:
    validate_config = _module()["validate_config"]
    config = {
        "schema_version": "scenario-forge-visual-static-liquid-prototype/v0.1",
        "vessel_profiles": {
            "beaker": {
                "source_id": "beaker",
                "package_dir": "/tmp/beaker",
                "entry_prim": "/World/Beaker",
                "axial_profile_m": [[0.004, 0.0335], [0.109, 0.0335]],
            }
        },
        "instances": [
            {
                "id": "bad",
                "profile": "beaker",
                "fill_fraction": 1.1,
                "color": [0.2, 0.4, 0.8],
                "pose": {"xyz": [0, 0, 0.755], "wxyz": [1, 0, 0, 0]},
            }
        ],
    }

    with pytest.raises(ValueError, match="fill_fraction"):
        validate_config(config)


def test_scene_authors_visual_only_liquid_with_relative_references() -> None:
    module = _module()
    scene_usda = module["prototype_scene_usda"]
    mesh = module["build_liquid_mesh"](
        [(0.004, 0.0335), (0.109, 0.0335)], 0.30, radial_segments=16
    )
    text = scene_usda(
        instances=[
            {
                "id": "blue_beaker",
                "entry_prim": "/World/Beaker325ml",
                "asset_reference": "deps/containers/beaker_325ml/asset.usd",
                "fill_fraction": 0.30,
                "color": [0.20, 0.58, 0.90],
                "pose": {"xyz": [-0.18, -0.10, 0.755], "wxyz": [1, 0, 0, 0]},
                "mesh": mesh,
            }
        ],
        table_reference="deps/table/asset.usd",
        room_reference=None,
    )

    assert "VisualLiquid" in text
    assert 'scenarioForge:role = "visual_static_liquid"' in text
    assert "scenarioForge:interactive = 0" in text
    assert "UsdPreviewSurface" in text
    assert "inputs:emissiveColor" in text
    assert "deps/containers/beaker_325ml/asset.usd" in text
    assert "@deps/table/asset.usd@</World>" in text
    assert "@deps/table/asset.usd@</World/table>" not in text
    assert "/tmp/" not in text
    liquid_text = text.split('def Xform "VisualLiquid"', 1)[1]
    body_text = liquid_text.split('def Mesh "Body"', 1)[1].split('def Mesh "Surface"', 1)[0]
    assert "bool doubleSided = false" in body_text
    for forbidden in (
        "PhysicsRigidBodyAPI",
        "PhysicsCollisionAPI",
        "PhysicsMassAPI",
        "PhysxParticle",
        "ParticleSystem",
    ):
        assert forbidden not in liquid_text


def test_generated_manifest_declares_visual_only_claim_boundary(tmp_path: Path) -> None:
    build_manifest = _module()["build_manifest"]
    output = tmp_path / "prototype"
    output.mkdir()
    scene = output / "scene_neutral.usda"
    scene.write_text("#usda 1.0\n", encoding="utf-8")

    manifest = build_manifest(
        output_dir=output,
        config_sha256="a" * 64,
        source_packages=[],
        generated_files=[scene],
    )

    assert manifest["status"] == "static_complete"
    assert manifest["physics_contract"]["liquid_interactive"] is False
    assert "not fluid physics" in manifest["claim_boundary"]


def test_video_tilt_schedule_is_sequential_and_returns_to_rest() -> None:
    tilt_degrees_at_time = _renderer_module()["tilt_degrees_at_time"]

    assert tilt_degrees_at_time(0.0, instance_index=0, tilt_degrees=55.0) == 0.0
    assert 0.0 < tilt_degrees_at_time(1.5, instance_index=0, tilt_degrees=55.0) < 55.0
    assert tilt_degrees_at_time(2.5, instance_index=0, tilt_degrees=55.0) == 55.0
    assert 0.0 < tilt_degrees_at_time(3.5, instance_index=0, tilt_degrees=55.0) < 55.0
    assert tilt_degrees_at_time(4.0, instance_index=0, tilt_degrees=55.0) == 0.0
    assert tilt_degrees_at_time(5.5, instance_index=1, tilt_degrees=55.0) == 55.0
    assert tilt_degrees_at_time(7.0, instance_index=1, tilt_degrees=55.0) == 0.0

from __future__ import annotations

import json
from pathlib import Path
import pytest

import scripts.generate_scientific_workbench_task02_r10_2 as r10_2


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_visual_package(path: Path, *, asset_id: str, package_id: str) -> None:
    _write(path / "overlays/visual_material.usda", '#usda 1.0\nover "World" {}\n')
    _write(path / "deps/mdl/OmniGlass.mdl", "mdl 1.6;\n")
    _write(
        path / "evidence/manifest.json",
        json.dumps(
            {
                "asset_id": asset_id,
                "package_id": package_id,
                "overall_status": "pass",
                "blocked_reasons": [],
                "runtime_evidence": {"status": "pass"},
                "visual_material_profile": {
                    "schema_version": "aan.visual_material_profile.v2",
                    "status": "pass",
                },
                "entrypoints": {
                    "root_usd": "asset.usd",
                    "asset_entry_prim": "/World/Object",
                },
            }
        ),
    )
    _write(
        path / "evidence/visual_material_only_audit.json",
        json.dumps({"status": "pass"}),
    )


def _fake_r10_1_package(path: Path) -> None:
    scenario_id = "scientific_workbench_r10_task02_fill40"
    _write(
        path / "manifest.json",
        json.dumps(
            {
                "scenario_id": scenario_id,
                "release": "r10.1",
                "particle_count": 580,
                "liquid_profile": {"target_settled_fill_ratio": 0.4},
                "claims": {"robot_policy_success": False},
                "vr_contract": {"status": "runtime_pass"},
            }
        ),
    )
    _write(path / "vr/scene.usd", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _write(path / "vr/legacy_scene.usd", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _write(path / "vr/task_config.py", "TASKS = {}\n")
    _write(path / "vr/config.py", "TASKS = {}\n")
    _write(
        path / "vr/parity_manifest.json",
        json.dumps({"status": "pass_with_declared_exception", "artifacts": {}}),
    )
    _write(
        path / "ebench/package_manifest.json",
        json.dumps({"package_id": scenario_id, "source_assets": []}),
    )
    component = '''#usda 1.0
def Xform "World"
{
    def Xform "Transfer"
    {
        def Xform "Source" (
            prepend references = @deps/source/asset.usd@</World/GraduatedCylinder250ml>
        ) {}
        def Xform "Target" (
            prepend references = @deps/target/asset.usd@</World/Beaker325ml>
        ) {}
    }
}
'''
    roots = (
        path / "vr/deps/transfer",
        path
        / "ebench/assets/scene_usds/scenario_forge"
        / scenario_id
        / "source_bundle/transfer",
    )
    for root in roots:
        _write(root / "component.usda", component)
        _write(root / "deps/source/asset.usd", "pbd-source\n")
        _write(root / "deps/target/asset.usd", "pbd-target\n")


def test_visual_references_are_stronger_than_unchanged_pbd_packages() -> None:
    source = '''prepend references = @deps/source/asset.usd@</World/GraduatedCylinder250ml>
prepend references = @deps/target/asset.usd@</World/Beaker325ml>
'''

    result = r10_2.compose_visual_material_references(source)

    assert result.index("deps/source_visual/overlays/visual_material.usda") < result.index(
        "deps/source/asset.usd"
    )
    assert result.index("deps/target_visual/overlays/visual_material.usda") < result.index(
        "deps/target/asset.usd"
    )


@pytest.mark.parametrize('in_place', [False, True])
def test_upgrade_variant_preserves_liquid_and_pbd_bytes(tmp_path: Path, in_place: bool) -> None:
    source = tmp_path / "source"
    destination = source if in_place else tmp_path / "destination"
    cylinder = tmp_path / "cylinder_visual"
    beaker = tmp_path / "beaker_visual"
    _fake_r10_1_package(source)
    _fake_visual_package(
        cylinder,
        asset_id="cylinder_glass_v2",
        package_id="cylinder_glass_v2_isaac41",
    )
    _fake_visual_package(
        beaker,
        asset_id="beaker_glass_v1",
        package_id="beaker_glass_v1_isaac41",
    )
    old_pbd = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("deps/source/asset.usd")
    } | {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("deps/target/asset.usd")
    }

    r10_2.upgrade_variant(
        source,
        destination,
        cylinder_visual_package=cylinder,
        beaker_visual_package=beaker,
        refresh_preview_request=False,
    )

    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["release"] == "r10.2"
    assert manifest["supersedes"] == "r10.1"
    assert manifest["particle_count"] == 580
    assert manifest["liquid_profile"] == {"target_settled_fill_ratio": 0.4}
    assert manifest["visual_materials"]["graduated_cylinder"]["package_id"] == (
        "cylinder_glass_v2_isaac41"
    )
    for relative, expected in old_pbd.items():
        assert (destination / relative).read_bytes() == expected
    for component in destination.rglob("component.usda"):
        text = component.read_text()
        assert "deps/source_visual/overlays/visual_material.usda" in text
        assert "deps/target_visual/overlays/visual_material.usda" in text
    task_config = (destination / "vr/task_config.py").read_text()
    assert "set_robot_physics_material" not in task_config
    assert "set_robot_contact_offset" not in task_config
    assert "set_robot_rest_offset" not in task_config

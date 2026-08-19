from __future__ import annotations

import json
from pathlib import Path

import yaml

import scripts.generate_scientific_workbench_task02_r10_3 as r10_3


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_source_package(path: Path) -> None:
    scenario_id = "scientific_workbench_r10_task02_fill40"
    _write(
        path / "manifest.json",
        json.dumps(
            {
                "scenario_id": scenario_id,
                "release": "r10.2",
                "particle_count": 580,
                "claims": {"robot_policy_success": False},
                "vr_contract": {"status": "runtime_pass"},
            }
        ),
    )
    _write(
        path / "scenario_r7_semantics.yaml",
        yaml.safe_dump({"objects": [{"id": "obj_beaker"}]}, sort_keys=False),
    )
    direct_scene = '''#usda 1.0
(defaultPrim = "World")
def Xform "World"
{
    def Xform "obj_beaker" {}
    def DomeLight "vr_direct_open_light" {}
}
'''
    _write(path / "vr/scene.usd", direct_scene)
    _write(path / "vr/legacy_scene.usd", direct_scene)
    _write(path / "vr/task_config.py", "TASKS = {}\n")
    _write(path / "vr/config.py", "TASKS = {}\n")
    _write(path / "vr/parity_manifest.json", json.dumps({"artifacts": {}}))
    _write(
        path / "ebench/package_manifest.json",
        json.dumps({"source_assets": [], "release_status": "pass"}),
    )
    _write(
        path / "ebench/tasks/config.yaml",
        yaml.safe_dump(
            {"evaluation_configs": [{"object_config": {"obj_beaker": {}}}]},
            sort_keys=False,
        ),
    )
    _write(
        path / "ebench/config.yaml",
        yaml.safe_dump(
            {"evaluation_configs": [{"object_config": {"obj_beaker": {}}}]},
            sort_keys=False,
        ),
    )
    _write(
        path
        / "ebench/assets/scene_usds/scenario_forge"
        / scenario_id
        / "source_bundle/r7_scene/scene.usda",
        '''#usda 1.0
def Xform "World"
{
    def Xform "_scene"
    {
        def Xform "obj_obj_beaker" {}
    }
}
def PhysicsScene "physicsScene" {}
''',
    )
    _write(
        path
        / "ebench/assets/scene_usds/scenario_forge"
        / scenario_id
        / "source_bundle/r7_scene/source_bundle/existing/asset.usd",
        "existing",
    )
    _write(path / "ebench/scene.usd", '#usda 1.0\n(defaultPrim="World")\n')
    _write(path / "pbd_sentinel.bin", "unchanged-pbd")


def _fake_fixture_package(path: Path) -> None:
    vr = path / "adapters/vr_teleop/deps/objects"
    _write(vr / "obj_glass_rod/asset.usd", "rod")
    _write(vr / "obj_acrylic_rod_rack/asset.usd", "rack")
    scene_root = (
        path
        / "adapters/ebench/genmanip/assets/scene_usds/scenario_forge/task07"
        / "source_bundle"
    )
    _write(
        scene_root / "scientific_workbench_r7_glass_stirring_rod_300mm/asset.usd",
        "rod",
    )
    _write(
        scene_root / "scientific_workbench_r10_1_acrylic_spoon_rack/asset.usd",
        "rack",
    )
    _write(
        path / "adapters/ebench/genmanip/package_manifest.json",
        json.dumps(
            {
                "source_assets": [
                    {
                        "asset_id": "scientific_workbench_r7_glass_stirring_rod_300mm",
                        "canonical_usd": "source_bundle/scientific_workbench_r7_glass_stirring_rod_300mm/asset.usd",
                    },
                    {
                        "asset_id": "scientific_workbench_r10_1_acrylic_spoon_rack",
                        "canonical_usd": "source_bundle/scientific_workbench_r10_1_acrylic_spoon_rack/asset.usd",
                    },
                ]
            }
        ),
    )


def test_upgrade_adds_grouped_rod_rack_without_changing_pbd(tmp_path: Path) -> None:
    source = tmp_path / "source"
    fixture = tmp_path / "fixture"
    destination = tmp_path / "destination"
    _fake_source_package(source)
    _fake_fixture_package(fixture)

    r10_3.upgrade_variant(
        source,
        destination,
        fixture_package=fixture,
        refresh_preview_request=False,
    )

    assert (destination / "pbd_sentinel.bin").read_text() == "unchanged-pbd"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["release"] == "r10.3"
    assert manifest["supersedes"] == "r10.2"
    assert manifest["particle_count"] == 580
    scene = (destination / "vr/scene.usd").read_text()
    assert 'def Xform "obj_glass_rod"' in scene
    assert 'def Xform "obj_acrylic_rod_rack"' in scene
    assert "(-0.42, -0.17, 0.755)" in scene
    config = (destination / "vr/task_config.py").read_text()
    assert '"/World/_scene/obj_glass_rod"' in config
    assert '"/World/_scene/obj_acrylic_rod_rack"' in config
    assert config.index('"obj_glass_rod"') < config.index('"obj_acrylic_rod_rack"')
    assert "set_robot_physics_material" not in config
    assert "set_robot_contact_offset" not in config
    assert "set_robot_rest_offset" not in config


def test_context_objects_are_metric_neutral_and_left_of_beaker(tmp_path: Path) -> None:
    source = tmp_path / "source"
    fixture = tmp_path / "fixture"
    destination = tmp_path / "destination"
    _fake_source_package(source)
    _fake_fixture_package(fixture)

    r10_3.upgrade_variant(
        source,
        destination,
        fixture_package=fixture,
        refresh_preview_request=False,
    )

    semantics = yaml.safe_load((destination / "scenario_r7_semantics.yaml").read_text())
    objects = {item["id"]: item for item in semantics["objects"]}
    assert objects["obj_acrylic_rod_rack"]["pose"]["xyz"] == [-0.42, -0.17, 0.755]
    assert objects["obj_glass_rod"]["pose"]["xyz"] == [-0.42, -0.17, 0.77243]
    assert objects["obj_glass_rod"]["metadata"]["metric_participation"] == "none"
    assert objects["obj_acrylic_rod_rack"]["metadata"]["metric_participation"] == "none"
    task = yaml.safe_load((destination / "ebench/tasks/config.yaml").read_text())
    object_config = task["evaluation_configs"][0]["object_config"]
    assert object_config["obj_glass_rod"]["uid_list"] == ["obj_glass_rod"]
    assert object_config["obj_acrylic_rod_rack"]["uid_list"] == [
        "obj_acrylic_rod_rack"
    ]

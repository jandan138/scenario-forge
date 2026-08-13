from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_scientific_workbench_task02_r8.py"


def _module() -> object:
    spec = importlib.util.spec_from_file_location("generate_task02_r8", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_r8_handoff_is_self_contained_and_keeps_liquid_metrics_inactive(tmp_path: Path) -> None:
    module = _module()
    r7 = tmp_path / "r7"
    ebench = r7 / "adapters/ebench/genmanip"
    vr = r7 / "adapters/vr_teleop"
    scene_rel = Path("assets/scene_usds/scenario_forge/r7/scene.usda")
    _file(ebench / scene_rel, '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(
        ebench / "tasks/config.yaml",
        "evaluation_configs:\n"
        "- task_name: old\n"
        "  domain_randomization:\n"
        "    cameras:\n"
        "      config_path: collected_packages/old/cameras/fixed_camera_lift2.yml\n",
    )
    _file(ebench / "cameras/fixed_camera_lift2.yml", "cameras: []\n")
    _file(
        ebench / "tasks/scenario_forge/r7/002/episode_metadata.json",
        json.dumps({"episode_name": "002", "task_data": {"initial_layout": {}}}),
    )
    request = (
        Path(__file__).resolve().parents[1]
        / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages/"
        "scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry/"
        "adapters/ebench/genmanip/evidence/render_request.yaml"
    )
    _file(ebench / "evidence/render_request.yaml", request.read_text())
    _file(vr / "scene.usd", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(vr / "task_config.py", "TASKS = {}\n")
    _file(r7 / "scenario.yaml", "scenario_id: r7\n")
    fluid = tmp_path / "fluid"
    _file(fluid / "consumer_60hz.usda", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(fluid / "component.usda", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(fluid / "interactive_fluid_scene_profile.json", json.dumps({"claim_boundary": {"prototype": True}}))
    _file(fluid / "evidence/manifest.json", json.dumps({"overall_status": "blocked"}))
    _file(fluid / "authored_particle_points.json", "[]\n")

    result = module.build(r7_package=r7, fluid_package=fluid, out=tmp_path / "out")

    manifest = json.loads((result / "manifest.json").read_text())
    assert manifest["release_status"] == "prototype_blocked"
    assert manifest["score_ceiling"] == 0.6
    assert manifest["liquid_metrics_active"] is False
    assert manifest["particle_count"] == 548
    assert (result / "ebench/scene.usd").is_file()
    assert (result / "ebench/config.yaml").is_file()
    assert (
        result
        / f"ebench/assets/scene_usds/scenario_forge/{module.SCENARIO_ID}/scene.usda"
    ).is_file()
    assert (
        result
        / f"ebench/assets/scene_usds/scenario_forge/{module.SCENARIO_ID}/scene_static_preview.usda"
    ).is_file()
    assert (
        result
        / f"ebench/tasks/scenario_forge/{module.SCENARIO_ID}/002/episode_metadata.json"
    ).is_file()
    assert (result / "ebench/evidence/render_request.yaml").is_file()
    assert (result / "vr/scene.usd").is_file()
    assert (result / "vr/config.py").is_file()
    assert "@deps/r7_scene/scene.usda@" in (result / "ebench/scene.usd").read_text()
    assert "@deps/fluid/component.usda@" in (result / "ebench/scene.usd").read_text()
    scene_text = (result / "ebench/scene.usd").read_text()
    assert 'def Xform "obj_obj_graduated_cylinder"' in scene_text
    assert 'def Xform "obj_obj_beaker"' in scene_text
    assert "double3 xformOp:translate = (0.16, -0.15, 0.755)" in scene_text
    assert "double3 xformOp:translate = (-0.16, -0.17, 0.755)" in scene_text
    assert 'def Xform "fluid_runtime"' in scene_text
    assert 'over "SourceContainer" (active = false)' in scene_text
    assert 'over "TargetContainer" (active = false)' in scene_text
    assert 'def Xform "FluidWorkcell"' not in scene_text
    assert str(tmp_path) not in (result / "ebench/scene.usd").read_text()
    config_text = (result / "ebench/config.yaml").read_text()
    assert f"collected_packages/{module.SCENARIO_ID}/cameras/fixed_camera_lift2.yml" in config_text
    assert "scientific_workbench_r7_task02" not in config_text


def test_r8_composition_places_component_on_755mm_table(tmp_path: Path) -> None:
    module = _module()
    text = module._composed_scene_usda("deps/r7_scene/scene.usda")
    assert "double3 xformOp:translate = (0, 0, 0.755)" in text
    assert "fluid_runtime" in text
    assert "obj_obj_graduated_cylinder" in text
    assert "obj_obj_beaker" in text
    world_block, physics_block = text.split('\nover "physicsScene"', maxsplit=1)
    assert 'over "physicsScene"' not in world_block
    assert 'physxScene:enableGPUDynamics' in physics_block
    assert 'over "PhysicsScene"' not in text

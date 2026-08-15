from __future__ import annotations

import importlib.util
from hashlib import sha256
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


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _transfer_package(root: Path) -> Path:
    package = root / "transfer"
    evidence = package / "evidence"
    (package / "deps/source").mkdir(parents=True)
    (package / "deps/target").mkdir(parents=True)
    evidence.mkdir()
    _file(package / "component.usda", '#usda 1.0\ndef Xform "World" {}\n')
    _file(package / "deps/source/asset.usd", "source")
    _file(package / "deps/target/asset.usd", "target")
    candidate = {"candidate_id": "c03", "dwell_seconds": 3.0, "rim_gap_m": 0.01, "rim_offset_x_m": 0.0, "tilt_deg": -115.0}
    profile = package / "transfer_fixture_profile.json"
    _file(profile, json.dumps({
        "schema_version": "aan.gpu_pbd_transfer_fixture.v1",
        "members": {"source": "/World/Transfer/Source", "target": "/World/Transfer/Target", "particles": "/World/Transfer/ParticleSet", "particle_system": "/World/Transfer/ParticleSystem"},
        "liquid_parameters": {"particle_count": 548},
        "bounded_search": {"candidates": [candidate]},
        "qualification": {"minimum_target_reception_ratio": 0.5, "required_cold_runs": 3, "spill_is_blocking": False},
        "claim_boundary": "Prescribed transfer only; no robot claim.",
    }))
    cold = {"overall_status": "pass", "particle_readback_attribute": "points", "static_hold": {"minimum_source_ratio": 1.0}, "pour": {"particle_count": 548, "target_ratio": 0.95}, "performance": {"mean_rtx_fps": 80.0}, "hard_runtime_errors": []}
    report = evidence / "gpu_pbd_transfer_admission_report.json"
    _file(report, json.dumps({"overall_status": "pass", "selected_candidate": candidate, "cold_runs": [cold, cold, cold], "promotion": {"allowed": True, "claim": "gpu_pbd_prescribed_transfer_pair"}}))
    digest = sha256()
    for item in sorted(p for p in (package / "deps").rglob("*") if p.is_file()):
        digest.update(item.relative_to(package / "deps").as_posix().encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(_digest(item)))
    _file(evidence / "manifest.json", json.dumps({
        "schema_version": "aan.gpu_pbd_transfer_pair_manifest.v1",
        "package_id": "task02-transfer.r1",
        "overall_status": "pass",
        "entrypoints": {"root_usd": "component.usda", "asset_entry_prim": "/World/Transfer"},
        "gpu_pbd_transfer_pair": {"status": "qualified", "profile": profile.name, "profile_sha256": _digest(profile), "report": str(report.relative_to(package)), "report_sha256": _digest(report), "component_sha256": _digest(package / "component.usda"), "dependency_tree_sha256": digest.hexdigest(), "particle_count": 548, "cold_runs": 3, "runtime": "isaac41", "selected_candidate": candidate},
        "promotion": {"allowed": True, "claim": "gpu_pbd_prescribed_transfer_pair", "claim_boundary": "Prescribed transfer only; no robot claim."},
    }))
    return package


def test_r83_handoff_is_self_contained_and_keeps_liquid_metrics_inactive(tmp_path: Path) -> None:
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
    _file(ebench / "package_manifest.json", json.dumps({"source_assets": []}))
    _file(vr / "scene.usd", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(vr / "task_config.py", "TASKS = {}\n")
    _file(r7 / "scenario.yaml", "scenario_id: r7\n")
    transfer = _transfer_package(tmp_path)

    result = module.build(r7_package=r7, transfer_package=transfer, out=tmp_path / "out")

    manifest = json.loads((result / "manifest.json").read_text())
    assert manifest["release_status"] == "physics_qualified_candidate"
    assert manifest["score_ceiling"] == 0.6
    assert manifest["liquid_metrics_active"] is False
    assert manifest["particle_count"] == 548
    assert manifest["claims"]["prescribed_transfer_producer"] is True
    assert manifest["claims"]["robot_policy_success"] is False
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
    assert "/source_bundle/r7_scene/scene.usda@" in (result / "ebench/scene.usd").read_text()
    assert "/source_bundle/transfer/component.usda@</World/Transfer>" in (result / "ebench/scene.usd").read_text()
    scene_text = (result / "ebench/scene.usd").read_text()
    assert 'over "obj_obj_graduated_cylinder" (active = false)' in scene_text
    assert 'over "obj_obj_beaker" (active = false)' in scene_text
    assert "double3 xformOp:translate = (-0.16, -0.17, 0.755)" in scene_text
    assert 'def Xform "fluid_runtime"' in scene_text
    assert 'over "Source"' in scene_text
    assert 'over "Target"' in scene_text
    assert scene_text.count("bool physics:kinematicEnabled = 0") == 2
    assert str(tmp_path) not in (result / "ebench/scene.usd").read_text()
    config_text = (result / "ebench/config.yaml").read_text()
    assert f"collected_packages/{module.SCENARIO_ID}/cameras/fixed_camera_lift2.yml" in config_text
    assert "scientific_workbench_r7_task02" not in config_text


def test_r83_composition_places_component_on_755mm_table(tmp_path: Path) -> None:
    module = _module()
    text = module._composed_scene_usda("deps/r7_scene/scene.usda")
    assert "double3 xformOp:translate = (-0.16, -0.17, 0.755)" in text
    assert "fluid_runtime" in text
    assert "obj_obj_graduated_cylinder" in text
    assert "obj_obj_beaker" in text
    world_block, physics_block = text.split('\nover "physicsScene"', maxsplit=1)
    assert 'over "physicsScene"' not in world_block
    assert 'physxScene:enableGPUDynamics' in physics_block
    assert 'over "PhysicsScene"' not in text


def test_r83_render_request_keeps_entrance_camera_inside_the_room(tmp_path: Path) -> None:
    module = _module()
    source = Path(__file__).resolve().parents[1] / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages/scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry/adapters/ebench/genmanip/evidence/render_request.yaml"
    root = tmp_path / "package"
    paths = {name: _file(root / name) for name in ("manifest.json", "config.yaml", "episode.json", "scene.usd", "camera.yml")}
    bundle = root / "source_bundle"
    _file(bundle / "asset.usd")

    request = module._render_request(
        source,
        package_manifest=paths["manifest.json"],
        task_config=paths["config.yaml"],
        episode=paths["episode.json"],
        scene=paths["scene.usd"],
        camera=paths["camera.yml"],
        source_bundle=bundle,
    )

    entrance = request["views"]["room_entrance_eye_level"]
    assert entrance["position_xyz"] == [0.0, -2.5, 1.65]
    assert entrance["target_xyz"] == [0.0, -0.35, 0.55]


def test_finalizes_only_the_ebench_load_reset_eight_second_claim(tmp_path: Path) -> None:
    module = _module()
    out = tmp_path / "out"
    _file(
        out / "manifest.json",
        json.dumps(
            {
                "claims": {
                    "ebench_load_reset_8s": "pending",
                    "robot_policy_success": False,
                    "benchmark_success": False,
                }
            }
        ),
    )
    evidence = out / "ebench/evidence/initial_scene"
    _file(
        evidence / "render_manifest.json",
        json.dumps(
            {
                "runtime": {
                    "warmup_steps": 960,
                    "action_count": 0,
                    "isaac_sim_version": "4.1.0.0",
                    "genmanip_revision": "abc123",
                }
            }
        ),
    )
    _file(evidence / "visual_ready_gate.yaml", "status: passed\n")
    _file(
        evidence / "runtime.log",
        "genmanip_reset_scene=true\n"
        "genmanip_recovery_scene=true\n"
        "zero_action_warmup_steps=960\n"
        "[Error] Collision contact offset must be positive, prim: /World/_scene/lift2/link7\n",
    )

    report = module.finalize_product_smoke(out)

    assert report["status"] == "pass"
    assert report["physics_duration_s"] == 8.0
    assert report["claims"]["ebench_load_reset_8s"] == "pass"
    assert report["nonblocking_observations"]["genmanip_robot_offset_warning_count"] == 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["claims"]["ebench_load_reset_8s"] is True
    assert manifest["claims"]["robot_policy_success"] is False

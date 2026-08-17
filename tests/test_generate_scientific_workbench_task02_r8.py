from __future__ import annotations

import importlib.util
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml


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


def _render_request_fixture(root: Path) -> Path:
    return _file(
        root / "render_request.yaml",
        "schema_version: scenario-forge-genmanip-preview-request/v0.3\n"
        "package_id: fixture\n"
        "task_name: scenario_forge/fixture\n"
        "episode_name: '002'\n"
        "views:\n"
        "  room_entrance_eye_level:\n"
        "    position_xyz: [9.0, 9.0, 9.0]\n"
        "    target_xyz: [8.0, 8.0, 8.0]\n"
        "output:\n"
        "  directory: evidence/initial_scene\n"
        "  manifest: evidence/initial_scene/render_manifest.json\n",
    )


def _rich_base_package(root: Path) -> Path:
    r7 = root / "rich_base"
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
        "      config_path: collected_packages/old/cameras/fixed_camera_lift2.yml\n"
        "  preprocess_config:\n"
        "  - type: set_robot_physics_material\n"
        "    config: {}\n"
        "  - type: set_robot_contact_offset\n"
        "    config: 0.05\n"
        "  - type: set_robot_rest_offset\n"
        "    config: 0.001\n",
    )
    _file(ebench / "cameras/fixed_camera_lift2.yml", "cameras: []\n")
    _file(
        ebench / "tasks/scenario_forge/r7/002/episode_metadata.json",
        json.dumps({"episode_name": "002", "task_data": {"initial_layout": {}}}),
    )
    request = _render_request_fixture(root)
    _file(ebench / "evidence/render_request.yaml", request.read_text())
    _file(ebench / "package_manifest.json", json.dumps({"source_assets": []}))
    _file(vr / "scene.usd", '#usda 1.0\n(defaultPrim="World")\ndef Xform "World" {}\n')
    _file(vr / "task_config.py", "TASKS = {}\n")
    _file(r7 / "scenario.yaml", "scenario_id: r7\n")
    return r7


def _transfer_package(
    root: Path,
    *,
    particle_count: int = 548,
    fill_level_id: str | None = None,
    target_settled_fill_ratio: float | None = None,
    measured_settled_fill_ratio: float | None = None,
) -> Path:
    is_v2 = fill_level_id is not None
    if is_v2:
        if target_settled_fill_ratio is None or measured_settled_fill_ratio is None:
            raise ValueError("v2 fill packages require target and measured ratios")
    fill_profile = (
        {
            "fill_level_id": fill_level_id,
            "measurement": "live_points_source_local_z_q95",
            "target_settled_fill_ratio": target_settled_fill_ratio,
            "settled_fill_ratio_tolerance": 0.05,
        }
        if is_v2
        else None
    )
    package = root / f"transfer_{fill_level_id or particle_count}"
    evidence = package / "evidence"
    (package / "deps/source").mkdir(parents=True)
    (package / "deps/target").mkdir(parents=True)
    evidence.mkdir()
    _file(package / "component.usda", '#usda 1.0\ndef Xform "World" {}\n')
    _file(
        package / "initial_particle_state.json",
        json.dumps([[0.25, 0.0, 0.02] for _ in range(particle_count)]),
    )
    _file(package / "deps/source/asset.usd", "source")
    _file(package / "deps/target/asset.usd", "target")
    candidate = {
        "candidate_id": "c03",
        "dwell_seconds": 3.0,
        "rim_gap_m": 0.01,
        "rim_offset_x_m": 0.0,
        "tilt_deg": -115.0,
    }
    profile = package / "transfer_fixture_profile.json"
    _file(
        profile,
        json.dumps(
            {
                "schema_version": (
                    "aan.gpu_pbd_transfer_fixture.v1"
                    if particle_count == 548
                    else "aan.gpu_pbd_transfer_fixture.v2"
                ),
                "source": {"initial_xyz_m": [0.25, 0.0, 0.0]},
                "members": {
                    "source": "/World/Transfer/Source",
                    "target": "/World/Transfer/Target",
                    "particles": "/World/Transfer/ParticleSet",
                    "particle_system": "/World/Transfer/ParticleSystem",
                },
                "liquid_parameters": {"particle_count": particle_count},
                "bounded_search": {"candidates": [candidate]},
                "qualification": {
                    "minimum_target_reception_ratio": 0.5,
                    "required_cold_runs": 3,
                    "spill_is_blocking": False,
                },
                "claim_boundary": "Prescribed transfer only; no robot claim.",
            }
        ),
    )
    cold = {
        "overall_status": "pass",
        "particle_readback_attribute": "points",
        "static_hold": {"minimum_source_ratio": 1.0},
        "pour": {"particle_count": particle_count, "target_ratio": 0.95},
        "performance": {"mean_rtx_fps": 80.0},
        "hard_runtime_errors": [],
    }
    report = evidence / "gpu_pbd_transfer_admission_report.json"
    _file(
        report,
        json.dumps(
            {
                "overall_status": "pass",
                "selected_candidate": candidate,
                "cold_runs": [cold, cold, cold],
                "promotion": {"allowed": True, "claim": "gpu_pbd_prescribed_transfer_pair"},
            }
        ),
    )
    digest = sha256()
    for item in sorted(p for p in (package / "deps").rglob("*") if p.is_file()):
        digest.update(item.relative_to(package / "deps").as_posix().encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(_digest(item)))
    manifest = evidence / "manifest.json"
    _file(
        manifest,
        json.dumps(
            {
                "schema_version": "aan.gpu_pbd_transfer_pair_manifest.v1",
                "package_id": "task02-transfer.r1",
                "overall_status": "pass",
                "entrypoints": {
                    "root_usd": "component.usda",
                    "asset_entry_prim": "/World/Transfer",
                },
                "gpu_pbd_transfer_pair": {
                    "status": "qualified",
                    "profile": profile.name,
                    "profile_sha256": _digest(profile),
                    "report": str(report.relative_to(package)),
                    "report_sha256": _digest(report),
                    "component_sha256": _digest(package / "component.usda"),
                    "dependency_tree_sha256": digest.hexdigest(),
                    "particle_count": particle_count,
                    "cold_runs": 3,
                    "runtime": "isaac41",
                    "selected_candidate": candidate,
                },
                "promotion": {
                    "allowed": True,
                    "claim": "gpu_pbd_prescribed_transfer_pair",
                    "claim_boundary": "Prescribed transfer only; no robot claim.",
                },
            }
        ),
    )
    dynamic_evidence = evidence / "dynamic_loaded_start"
    state = _file(
        dynamic_evidence / "dynamic_loaded_particle_state.json",
        json.dumps(
            {
                "schema_version": "aan.gpu_pbd_source_local_particle_state.v1",
                "coordinate_space": "source_entry_root_local",
                "particle_count": particle_count,
                "positions": [[0.0, 0.0, 0.02] for _ in range(particle_count)],
                "outside_source_count": 0,
            }
        ),
    )
    qualification = {
        "required_cold_runs": 3,
        "maximum_outside_source_before_lift": 2,
        "maximum_entry_root_tail_drift_m": 0.001,
        "maximum_entry_root_tilt_deg": 2.0,
    }
    if is_v2:
        qualification.update(
            {
                "maximum_below_source_floor_count": 0,
                "target_settled_fill_ratio": target_settled_fill_ratio,
                "settled_fill_ratio_tolerance": 0.05,
            }
        )
    contract_payload = {
        "schema_version": (
            "aan.gpu_pbd_dynamic_loaded_start.v2"
            if is_v2
            else "aan.gpu_pbd_dynamic_loaded_start.v1"
        ),
        "support_plane_z_m": 0.755,
        "support_plane_to_entry_root": {
            "xyz_m": [0.25, 0.0, -0.0069],
            "wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "particle_state": state.name,
        "particle_state_sha256": _digest(state),
        "particle_count": particle_count,
        "qualification": qualification,
    }
    if is_v2:
        contract_payload["fill_profile"] = fill_profile
    contract = _file(
        dynamic_evidence / "dynamic_loaded_start_contract.json",
        json.dumps(contract_payload),
    )
    dynamic_run = {
        "overall_status": "pass",
        "particle_count": particle_count,
        "maximum_outside_source_count": 0,
        "entry_root_tail_drift_m": 0.0001,
        "maximum_entry_root_tilt_deg": 0.1,
        "hard_runtime_errors": [],
    }
    if is_v2:
        dynamic_run["maximum_below_source_floor_count"] = 0
        dynamic_run["settled_fill_ratio"] = measured_settled_fill_ratio
    dynamic_report = _file(
        dynamic_evidence / "dynamic_loaded_start_report.json",
        json.dumps(
            {
                "schema_version": (
                    "aan.gpu_pbd_dynamic_loaded_start_report.v2"
                    if is_v2
                    else "aan.gpu_pbd_dynamic_loaded_start_report.v1"
                ),
                "overall_status": "pass",
                "contract_sha256": _digest(contract),
                "particle_state_sha256": _digest(state),
                "cold_runs": [dynamic_run, dynamic_run, dynamic_run],
                "promotion": {
                    "allowed": True,
                    "claim": "gpu_pbd_dynamic_loaded_start",
                },
            }
        ),
    )
    payload = json.loads(manifest.read_text())
    payload["gpu_pbd_dynamic_loaded_start"] = {
        "status": "qualified",
        "contract": contract.relative_to(package).as_posix(),
        "contract_sha256": _digest(contract),
        "particle_state": state.relative_to(package).as_posix(),
        "particle_state_sha256": _digest(state),
        "report": dynamic_report.relative_to(package).as_posix(),
        "report_sha256": _digest(dynamic_report),
        "particle_count": particle_count,
        "cold_runs": 3,
        "maximum_outside_source_before_lift": 2,
        "support_plane_to_entry_root": {
            "xyz_m": [0.25, 0.0, -0.0069],
            "wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "runtime": "isaac41",
    }
    if is_v2:
        payload["gpu_pbd_dynamic_loaded_start"]["fill_profile"] = fill_profile
        payload["gpu_pbd_dynamic_loaded_start"]["measured_settled_fill_ratio_range"] = [
            measured_settled_fill_ratio,
            measured_settled_fill_ratio,
        ]
        payload["gpu_pbd_dynamic_loaded_start"]["maximum_below_source_floor_count"] = 0
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return package


def test_r83_handoff_is_self_contained_and_keeps_liquid_metrics_inactive(tmp_path: Path) -> None:
    module = _module()
    r7 = _rich_base_package(tmp_path)
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
        result / f"ebench/assets/scene_usds/scenario_forge/{module.SCENARIO_ID}/scene.usda"
    ).is_file()
    assert (
        result
        / f"ebench/assets/scene_usds/scenario_forge/{module.SCENARIO_ID}/scene_static_preview.usda"
    ).is_file()
    assert (
        result / f"ebench/tasks/scenario_forge/{module.SCENARIO_ID}/002/episode_metadata.json"
    ).is_file()
    assert (result / "ebench/evidence/render_request.yaml").is_file()
    assert (result / "vr/scene.usd").is_file()
    assert (result / "vr/config.py").is_file()
    assert (result / "vr/task_config.py").is_file()
    assert (result / "vr/parity_manifest.json").is_file()
    assert (result / "vr/deps/r7_scene/scene.usda").is_file()
    assert (result / "vr/deps/transfer/component.usda").is_file()
    assert "@../ebench/" not in (result / "vr/scene.usd").read_text()
    assert "/source_bundle/r7_scene/scene.usda@" in (result / "ebench/scene.usd").read_text()
    assert (
        "/source_bundle/transfer/component.usda@</World/Transfer>"
        in (result / "ebench/scene.usd").read_text()
    )
    scene_text = (result / "ebench/scene.usd").read_text()
    assert 'over "obj_obj_graduated_cylinder" (' in scene_text
    assert "source_bundle/transfer/component.usda@</World/Transfer/Source>" in scene_text
    assert 'over "obj_obj_beaker" (' in scene_text
    assert "source_bundle/transfer/component.usda@</World/Transfer/Target>" in scene_text
    assert scene_text.count("active = false") == 2
    assert 'def Xform "obj_table"' in scene_text
    assert (
        "/source_bundle/r7_scene/source_bundle/scenario_forge_runtime/table.usd@</Asset>"
        in scene_text
    )
    assert "double3 xformOp:translate = (0.09, -0.17, 0.7481)" in scene_text
    assert "double3 xformOp:translate = (-0.16, -0.17, 0.755)" in scene_text
    assert scene_text.count("point3f[] physxParticle:simulationPoints") == 1
    assert scene_text.count("point3f[] points") == 1
    assert scene_text.count("(0.09, -0.17, 0.7681)") == 1096
    assert 'def Xform "fluid_runtime"' in scene_text
    assert 'over "Source" (active = false)' in scene_text
    assert 'over "Target" (active = false)' in scene_text
    assert scene_text.count("bool physics:kinematicEnabled = 0") == 2
    assert str(tmp_path) not in (result / "ebench/scene.usd").read_text()
    config_text = (result / "ebench/config.yaml").read_text()
    assert f"collected_packages/{module.SCENARIO_ID}/cameras/fixed_camera_lift2.yml" in config_text
    assert "scientific_workbench_r7_task02" not in config_text
    assert "set_robot_physics_material" in config_text
    assert "set_robot_contact_offset" not in config_text
    assert "set_robot_rest_offset" not in config_text


def test_r87_composition_bakes_one_measured_pose_for_container_and_particles(
    tmp_path: Path,
) -> None:
    module = _module()
    text = module._composed_scene_usda(
        "deps/r7_scene/scene.usda",
        [[0.0, 0.0, 0.02]],
        source_xyz=[0.09, -0.17, 0.7481],
        source_wxyz=[1.0, 0.0, 0.0, 0.0],
    )
    assert "double3 xformOp:translate = (0.09, -0.17, 0.7481)" in text
    assert "double3 xformOp:translate = (-0.16, -0.17, 0.755)" in text
    assert "point3f[] physxParticle:simulationPoints = [(0.09, -0.17, 0.7681)]" in text
    assert "point3f[] points = [(0.09, -0.17, 0.7681)]" in text
    assert 'uniform token[] xformOpOrder = ["!resetXformStack!"]' in text
    assert "fluid_runtime" in text
    assert "obj_obj_graduated_cylinder" in text
    assert "obj_obj_beaker" in text
    world_block, physics_block = text.split('\nover "physicsScene"', maxsplit=1)
    assert 'over "physicsScene"' not in world_block
    assert "physxScene:enableGPUDynamics" in physics_block
    assert 'over "PhysicsScene"' not in text


def test_r87_particle_transform_uses_usd_wxyz_rotation_convention() -> None:
    module = _module()

    transformed = module._world_particle_points(
        [[1.0, 0.0, 0.0]],
        source_xyz=[0.0, 0.0, 0.0],
        source_wxyz=[0.7071067812, 0.0, 0.0, 0.7071067812],
    )

    assert transformed[0] == pytest.approx([0.0, 1.0, 0.0], abs=1e-8)


def test_r85_package_uses_transfer_handoff_particle_count(tmp_path: Path) -> None:
    module = _module()
    transfer = _transfer_package(tmp_path, particle_count=580)
    assert (
        module.load_gpu_pbd_transfer_pair_handoff(
            transfer, transfer / "evidence/manifest.json"
        ).particle_count
        == 580
    )


def test_r87_build_fails_closed_without_dynamic_loaded_start(tmp_path: Path) -> None:
    module = _module()
    transfer = _transfer_package(tmp_path, particle_count=580)
    manifest = transfer / "evidence/manifest.json"
    payload = json.loads(manifest.read_text())
    del payload["gpu_pbd_dynamic_loaded_start"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="gpu_pbd_dynamic_loaded_start"):
        module.load_gpu_pbd_dynamic_loaded_start_handoff(transfer, manifest)


def test_r83_render_request_keeps_entrance_camera_inside_the_room(tmp_path: Path) -> None:
    module = _module()
    source = _render_request_fixture(tmp_path)
    root = tmp_path / "package"
    paths = {
        name: _file(root / name)
        for name in ("manifest.json", "config.yaml", "episode.json", "scene.usd", "camera.yml")
    }
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
    evidence = out / "ebench/evidence/product_smoke"
    _file(
        evidence / "report.json",
        json.dumps(
            {
                "schema_version": "scenario-forge-genmanip-zero-action-physics-smoke/v0.1",
                "status": "pass",
                "physics_steps": 960,
                "action_count": 0,
                "runtime": {
                    "isaac_sim_version": "4.1.0.0",
                    "genmanip_revision": "abc123",
                    "render_without_physics": False,
                },
                "phases": {
                    "genmanip_scene_constructed": "pass",
                    "physics_initialized": "pass",
                    "reset_and_recovery": "pass",
                    "zero_action_physics": "pass",
                },
            }
        ),
    )
    _file(
        evidence / "runtime.log",
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


def test_product_smoke_rejects_visual_only_960_step_metadata(tmp_path: Path) -> None:
    module = _module()
    out = tmp_path / "out"
    _file(out / "manifest.json", json.dumps({"claims": {"ebench_load_reset_8s": "pending"}}))
    evidence = out / "ebench/evidence/product_smoke"
    _file(
        evidence / "report.json",
        json.dumps(
            {
                "schema_version": "scenario-forge-genmanip-zero-action-physics-smoke/v0.1",
                "status": "pass",
                "physics_steps": 960,
                "action_count": 0,
                "runtime": {"render_without_physics": True},
                "phases": {
                    "genmanip_scene_constructed": "pass",
                    "physics_initialized": "pass",
                    "reset_and_recovery": "pass",
                    "zero_action_physics": "pass",
                },
            }
        ),
    )

    with pytest.raises(ValueError, match="physical smoke"):
        module.finalize_product_smoke(out)


def test_attaches_validated_scripted_robot_evidence_without_policy_claim(
    tmp_path: Path,
) -> None:
    module = _module()
    scenario_id = "scientific_workbench_r9_task02_fixture"
    out = tmp_path / "package"
    _file(
        out / "manifest.json",
        json.dumps(
            {
                "scenario_id": scenario_id,
                "release": "r9",
                "liquid_metrics_active": False,
                "claims": {
                    "visible_robot_transfer": False,
                    "robot_policy_success": False,
                    "benchmark_success": False,
                },
            }
        ),
    )
    evidence = tmp_path / "oracle"
    _file(
        evidence / "robot_oracle_evidence.json",
        json.dumps(
            {
                "schema_id": "eeos.task02_robot_oracle_evidence.v2",
                "scenario_id": scenario_id,
                "release": "r9",
                "execution_mode": "scripted_robot_oracle",
                "policy_claim": False,
                "benchmark_claim": False,
                "liquid_metric_active": False,
                "runs": [{"run_index": index} for index in range(1, 4)],
            }
        ),
    )
    _file(
        evidence / "validation_report.json",
        json.dumps({"overall_status": "pass", "robot_transfer_success": True}),
    )

    receipt = module.attach_robot_oracle_evidence(out, evidence)

    assert receipt["status"] == "pass"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["claims"]["visible_scripted_robot_transfer"] is True
    assert manifest["claims"]["robot_policy_success"] is False
    assert manifest["claims"]["benchmark_success"] is False
    assert manifest["liquid_metrics_active"] is False
    assert (out / "evidence/robot_oracle/robot_oracle_evidence.json").is_file()


R10_SCRIPT = Path(__file__).resolve().parents[1] / (
    "scripts/generate_scientific_workbench_task02_r10_fill_sweep.py"
)


def _r10_module() -> object:
    spec = importlib.util.spec_from_file_location("generate_task02_r10", R10_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r10_fill_sweep_builds_independent_dual_consumer_variants(tmp_path: Path) -> None:
    module = _r10_module()

    def fake_runtime_gates(packages, **_kwargs):
        for package in packages.values():
            physics = package / "ebench/evidence/product_smoke/report.json"
            physics.parent.mkdir(parents=True)
            physics.write_text(
                json.dumps(
                    {
                        "schema_version": "scenario-forge-genmanip-zero-action-physics-smoke/v0.1",
                        "status": "pass",
                        "physics_steps": 960,
                        "action_count": 0,
                        "runtime": {"render_without_physics": False},
                        "phases": {"zero_action_physics": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            vr = package / "vr/evidence/open_smoke/report.json"
            vr.parent.mkdir(parents=True)
            vr.write_text(
                json.dumps(
                    {
                        "schema_version": "scenario-forge-vr-usd-open-smoke/v0.1",
                        "status": "pass",
                        "physics_steps": 0,
                        "default_prim": "/World",
                    }
                ),
                encoding="utf-8",
            )
            module.finalize_runtime_gates(package)

    module.run_runtime_gates = fake_runtime_gates
    rich_base = _rich_base_package(tmp_path)
    fill20 = _transfer_package(
        tmp_path,
        particle_count=290,
        fill_level_id="fill20",
        target_settled_fill_ratio=0.2,
        measured_settled_fill_ratio=0.216,
    )
    fill40 = _transfer_package(
        tmp_path,
        particle_count=580,
        fill_level_id="fill40",
        target_settled_fill_ratio=0.4,
        measured_settled_fill_ratio=0.389,
    )
    result = module.build_r10_fill_sweep(
        r9_package=rich_base,
        transfer_packages={"fill20": fill20, "fill40": fill40},
        output_dir=tmp_path / "r10",
        fill_level_ids=("fill20", "fill40"),
        default_variant="fill40",
        base_scenario_id="r7",
    )

    fill20_manifest = json.loads(
        (result.root / "variants/fill20/manifest.json").read_text()
    )
    fill40_manifest = json.loads(
        (result.root / "variants/fill40/manifest.json").read_text()
    )
    assert fill20_manifest["release"] == "r10"
    assert fill40_manifest["release"] == "r10"
    assert fill20_manifest["liquid_profile"]["fill_level_id"] == "fill20"
    assert fill40_manifest["liquid_profile"]["fill_level_id"] == "fill40"
    assert fill20_manifest["particle_count"] == 290
    assert fill40_manifest["particle_count"] == 580
    assert fill20_manifest["claims"]["robot_policy_success"] is False
    assert not list((tmp_path / "r10").rglob("robot_oracle"))
    assert (result.root / "variants/fill20/vr/task_config.py").is_file()
    assert (result.root / "variants/fill40/vr/task_config.py").is_file()
    archive = yaml.safe_load((result.root / "manifest.yaml").read_text())
    assert archive["default_variant"] == "fill40"
    assert "960-step zero-action physics smoke" in archive["claim_boundary"]

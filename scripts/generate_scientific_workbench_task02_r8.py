#!/usr/bin/env python3
"""Build Task 02 r8.7 from r7 semantics and a dynamic-loaded PBD handoff."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml

from scenario_forge.adapters.convert_asset import (
    load_gpu_pbd_dynamic_loaded_start_handoff,
    load_gpu_pbd_transfer_pair_handoff as load_gpu_pbd_transfer_pair_handoff,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R7 = (
    REPO_ROOT
    / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages/scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
)
DEFAULT_TRANSFER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task02_gpu_pbd_dynamic_loaded_start_20260816_r59/final_package/task02_cylinder_to_beaker_gpu_pbd_transfer_pair_r5"
)
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task02_r87_20260816"
SCENARIO_ID = (
    "scientific_workbench_r87_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
)
R7_SCENARIO_ID = (
    "scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_sha(path: Path) -> str:
    digest = sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha(item)))
    return digest.hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def _json(path: Path, value: Any) -> Path:
    return _write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _yaml(path: Path, value: Any) -> Path:
    return _write(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False))


def _copy(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _r7_ebench_scene(r7_package: Path) -> Path:
    candidates = list(
        (r7_package / "adapters/ebench/genmanip/assets/scene_usds").glob(
            "scenario_forge/*/scene.usda"
        )
    )
    if len(candidates) != 1:
        raise ValueError("expected exactly one r7 GenManip scene")
    return candidates[0]


def _number(value: float) -> str:
    return f"{value:.9g}"


def _source_matrix(xyz: list[float], wxyz: list[float]) -> list[list[float]]:
    w, x, y, z = wxyz
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
        [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
        [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)],
        xyz,
    ]


def _world_particle_points(
    local_points: list[list[float]],
    *,
    source_xyz: list[float],
    source_wxyz: list[float],
) -> list[list[float]]:
    matrix = _source_matrix(source_xyz, source_wxyz)
    return [
        [
            point[0] * matrix[0][axis]
            + point[1] * matrix[1][axis]
            + point[2] * matrix[2][axis]
            + matrix[3][axis]
            for axis in range(3)
        ]
        for point in local_points
    ]


def _composed_scene_usda(
    r7_reference: str,
    local_particle_points: list[list[float]],
    *,
    source_xyz: list[float],
    source_wxyz: list[float],
) -> str:
    r7_bundle = r7_reference.rsplit("/", 1)[0]
    table_reference = f"{r7_bundle}/source_bundle/scenario_forge_runtime/table.usd"
    translated = _world_particle_points(
        local_particle_points,
        source_xyz=source_xyz,
        source_wxyz=source_wxyz,
    )
    point_text = ", ".join(
        f"({_number(point[0])}, {_number(point[1])}, {_number(point[2])})" for point in translated
    )
    return f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    kilogramsPerUnit = 1
    upAxis = "Z"
    framesPerSecond = 60
    timeCodesPerSecond = 60
    subLayers = [@{r7_reference}@]
)

over "World"
{{
    over "_scene"
    {{
        def Xform "obj_table" (
            prepend references = @{table_reference}@</Asset>
        )
        {{
            uniform token[] xformOpOrder = ["!resetXformStack!"]
        }}
        over "obj_obj_graduated_cylinder" (
            active = true
            references = @deps/transfer/component.usda@</World/Transfer/Source>
        )
        {{
            bool physics:kinematicEnabled = 0
            double3 xformOp:translate = ({_number(source_xyz[0])}, {_number(source_xyz[1])}, {_number(source_xyz[2])})
            quatf xformOp:orient = ({_number(source_wxyz[0])}, {_number(source_wxyz[1])}, {_number(source_wxyz[2])}, {_number(source_wxyz[3])})
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
        }}
        over "obj_obj_beaker" (
            active = true
            references = @deps/transfer/component.usda@</World/Transfer/Target>
        )
        {{
            bool physics:kinematicEnabled = 0
            double3 xformOp:translate = (-0.16, -0.17, 0.755)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}
        def Xform "fluid_runtime" (
            prepend references = @deps/transfer/component.usda@</World/Transfer>
        )
        {{
            uniform token[] xformOpOrder = ["!resetXformStack!"]
            over "Source" (active = false) {{}}
            over "Target" (active = false) {{}}
            over "ParticleSet"
            {{
                point3f[] physxParticle:simulationPoints = [{point_text}]
                point3f[] points = [{point_text}]
            }}
        }}
    }}

}}

over "physicsScene"
{{
    token physxScene:broadphaseType = "GPU"
    bool physxScene:enableGPUDynamics = 1
    uint physxScene:gpuMaxParticleContacts = 1048576
    token physxScene:solverType = "TGS"
    uint physxScene:timeStepsPerSecond = 120
}}
"""


def _rewrite_ebench_config(
    source: Path, *, particle_count: int, scenario_id: str = SCENARIO_ID
) -> dict[str, Any]:
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    evaluations = config.get("evaluation_configs", [])
    if not evaluations:
        evaluations = [{"task_name": f"scenario_forge/{scenario_id}"}]
        config["evaluation_configs"] = evaluations
    for item in evaluations:
        item["task_name"] = f"scenario_forge/{scenario_id}"
        item["usd_name"] = (
            f"collected_packages/{scenario_id}/assets/scene_usds/scenario_forge/{scenario_id}/scene"
        )
        item["physics_dt"] = 1.0 / 120.0
        item["rendering_dt"] = 1.0 / 60.0
        item.setdefault("physics_scene_config", {})["EnableGPUDynamics"] = True
        item["physics_scene_config"]["GpuMaxParticleContacts"] = 1048576
        item["physics_scene_config"]["TimeStepsPerSecond"] = 120
        cameras = item.get("domain_randomization", {}).get("cameras")
        if isinstance(cameras, dict):
            cameras["config_path"] = (
                f"collected_packages/{scenario_id}/cameras/fixed_camera_lift2.yml"
            )
        item["prototype_fluid"] = {
            "status": "qualified_dynamic_loaded_start",
            "particle_count": particle_count,
            "liquid_metrics_active": False,
            "inactive_reason": "ebench_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_dynamic_loaded_start",
        }
        item["preprocess_config"] = [
            entry
            for entry in item.get("preprocess_config", [])
            if entry.get("type") not in {"set_robot_contact_offset", "set_robot_rest_offset"}
        ]
        goal = item.get("generation_config", {}).get("goal", [])
        for level1 in goal:
            for level2 in level1 if isinstance(level1, list) else []:
                for predicate in level2 if isinstance(level2, list) else []:
                    if (
                        isinstance(predicate, dict)
                        and predicate.get("obj1_uid") == "obj_graduated_cylinder"
                    ):
                        predicate["x_range"] = [0.05, 0.13]
                        predicate["y_range"] = [-0.21, -0.13]
    return config


def _rewrite_episode(
    source: Path,
    *,
    source_xyz: list[float],
    source_wxyz: list[float],
    scenario_id: str = SCENARIO_ID,
    base_scenario_id: str = R7_SCENARIO_ID,
) -> dict[str, Any]:
    episode = json.loads(source.read_text(encoding="utf-8"))

    def replace(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(base_scenario_id, scenario_id).replace(
                f"/World/{scenario_id}/", "/World/_scene/"
            )
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    episode = replace(episode)
    episode["episode_name"] = "002"
    task_data = episode.get("task_data", {})
    layout = task_data.get("initial_layout", {})
    task_poses = {
        "obj_graduated_cylinder": (source_xyz, "/World/_scene/obj_obj_graduated_cylinder"),
        "obj_beaker": ([-0.16, -0.17, 0.755], "/World/_scene/obj_obj_beaker"),
    }
    for object_id, item in layout.items():
        if not isinstance(item, dict):
            continue
        if object_id in task_poses:
            item["position"], item["prim_path"] = task_poses[object_id]
            if object_id == "obj_graduated_cylinder":
                item["orientation"] = source_wxyz
            item["path"] = ""
            continue
        prim_path = item.get("prim_path")
        if isinstance(prim_path, str) and "/obj_" in prim_path:
            item["prim_path"] = "/World/_scene/" + prim_path.rsplit("/", 1)[-1]
        asset_path = item.get("path")
        if isinstance(asset_path, str) and asset_path:
            rewritten = asset_path
            item["path"] = rewritten.replace(
                f"assets/scene_usds/scenario_forge/{scenario_id}/source_bundle/",
                f"assets/scene_usds/scenario_forge/{scenario_id}/source_bundle/r7_scene/source_bundle/",
            )
    for predicate_group in task_data.get("goal", []):
        for predicates in predicate_group if isinstance(predicate_group, list) else []:
            for predicate in predicates if isinstance(predicates, list) else []:
                if (
                    isinstance(predicate, dict)
                    and predicate.get("obj1_uid") == "obj_graduated_cylinder"
                ):
                    predicate["x_range"] = [0.05, 0.13]
                    predicate["y_range"] = [-0.21, -0.13]
    contract = task_data.get("scenario_forge_runtime_contract", {})
    for item in contract.get("objects", []) if isinstance(contract, dict) else []:
        object_id = item.get("scenario_object_id") if isinstance(item, dict) else None
        if object_id in task_poses:
            position, prim_path = task_poses[object_id]
            item["initial_pose"]["xyz"] = position
            if object_id == "obj_graduated_cylinder":
                item["initial_pose"]["wxyz"] = source_wxyz
            item["state_prim_path"] = prim_path
    return episode


def _render_request(
    source: Path,
    *,
    package_manifest: Path,
    task_config: Path,
    episode: Path,
    scene: Path,
    camera: Path,
    source_bundle: Path,
    scenario_id: str = SCENARIO_ID,
    release: str = "r8.7",
) -> dict[str, Any]:
    request = yaml.safe_load(source.read_text(encoding="utf-8"))
    request["package_id"] = scenario_id
    request["task_name"] = f"scenario_forge/{scenario_id}"
    request["episode_name"] = "002"
    request["zero_action_warmup_steps"] = 960
    entrance_view = request.get("views", {}).get("room_entrance_eye_level")
    if isinstance(entrance_view, dict):
        entrance_view["position_xyz"] = [0.0, -2.5, 1.65]
        entrance_view["target_xyz"] = [0.0, -0.35, 0.55]
    paths = {
        "package_manifest": package_manifest,
        "task_config": task_config,
        "episode_metadata": episode,
        "scene_usd": scene,
        "evaluation_camera": camera,
        "source_bundle": source_bundle,
    }
    inputs = {}
    root = package_manifest.parent
    for role, path in paths.items():
        digest = _tree_sha(path) if path.is_dir() else _sha(path)
        inputs[role] = {
            "path": path.relative_to(root).as_posix(),
            "sha256": "sha256:" + digest,
        }
    request["inputs"] = inputs
    digest_payload = json.dumps(
        {"package_id": scenario_id, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    request["input_digest"] = "sha256:" + sha256(digest_payload).hexdigest()
    request["claim_boundary"] = (
        f"{release} initial-scene visual evidence only; not robot transfer, "
        "FPS, policy, or benchmark success."
    )
    return request


def _vr_config(*, particle_count: int, scenario_id: str = SCENARIO_ID) -> str:
    return f'''# Merge this TASKS entry into the VR teleop task registry.
TASKS = {{
    "{scenario_id}": {{
        "scene_usd_file_path": {{"scene1": str(_ASSETS_DIR / "scenes/{scenario_id}/scene.usd")}},
        "obj_prim_list": [
            "/World/_scene/fluid_runtime/Source",
            "/World/_scene/fluid_runtime/Target",
        ],
        "robot_cfg": {{
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }},
        "physx_scene_cfg": {{
            "BroadphaseType": "GPU",
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "SolverType": "TGS",
            "TimeStepsPerSecond": 120,
        }},
        "prototype_fluid": {{
            "status": "qualified_dynamic_loaded_start",
            "particle_count": {particle_count},
            "liquid_metrics_active": False,
            "inactive_reason": "vr_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_dynamic_loaded_start",
        }},
    }},
}}
'''


def build(
    *,
    r7_package: Path,
    transfer_package: Path,
    out: Path,
    scenario_id: str = SCENARIO_ID,
    base_scenario_id: str = R7_SCENARIO_ID,
    release: str = "r8.7",
    supersedes: str = "r8.6",
) -> Path:
    r7_package = r7_package.resolve()
    transfer_package = transfer_package.resolve()
    out = out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    transfer_manifest_path = transfer_package / "evidence/manifest.json"
    dynamic_handoff = load_gpu_pbd_dynamic_loaded_start_handoff(
        transfer_package, transfer_manifest_path
    )
    transfer_handoff = dynamic_handoff.transfer
    transfer_profile = json.loads(transfer_handoff.profile_path.read_text(encoding="utf-8"))
    liquid_profile = transfer_profile["liquid_parameters"]
    particle_state = json.loads(dynamic_handoff.particle_state_path.read_text(encoding="utf-8"))
    particle_points = particle_state["positions"]
    if len(particle_points) != transfer_handoff.particle_count:
        raise ValueError("source-local particle state does not match qualified particle count")
    reference_xyz = transfer_profile["source"]["initial_xyz_m"]
    support_pose = dynamic_handoff.support_plane_to_entry_root
    support_xyz = support_pose["xyz_m"]
    source_xyz = [
        0.09 + float(support_xyz[0]) - float(reference_xyz[0]),
        -0.17 + float(support_xyz[1]) - float(reference_xyz[1]),
        0.755 + float(support_xyz[2]) - float(reference_xyz[2]),
    ]
    source_wxyz = [float(value) for value in support_pose["wxyz"]]
    r7_scene = _r7_ebench_scene(r7_package)
    collected_scene_dir = out / "ebench/assets/scene_usds/scenario_forge" / scenario_id
    source_bundle = collected_scene_dir / "source_bundle"
    _copy(r7_scene.parent, source_bundle / "r7_scene")
    _copy(transfer_package, source_bundle / "transfer")
    ebench_bundle = f"assets/scene_usds/scenario_forge/{scenario_id}/source_bundle"
    _write(
        out / "ebench/scene.usd",
        _composed_scene_usda(
            f"{ebench_bundle}/r7_scene/scene.usda",
            particle_points,
            source_xyz=source_xyz,
            source_wxyz=source_wxyz,
        ).replace("@deps/transfer/", f"@{ebench_bundle}/transfer/"),
    )
    _write(
        out / "vr/scene.usd",
        _composed_scene_usda(
            f"../ebench/{ebench_bundle}/r7_scene/scene.usda",
            particle_points,
            source_xyz=source_xyz,
            source_wxyz=source_wxyz,
        ).replace("@deps/transfer/", f"@../ebench/{ebench_bundle}/transfer/"),
    )

    r7_ebench = r7_package / "adapters/ebench/genmanip"
    config = _rewrite_ebench_config(
        r7_ebench / "tasks/config.yaml",
        particle_count=transfer_handoff.particle_count,
        scenario_id=scenario_id,
    )
    _yaml(out / "ebench/config.yaml", config)
    _yaml(out / "ebench/tasks/config.yaml", config)
    _copy(r7_ebench / "cameras", out / "ebench/cameras")
    _write(
        collected_scene_dir / "scene.usda",
        _composed_scene_usda(
            "source_bundle/r7_scene/scene.usda",
            particle_points,
            source_xyz=source_xyz,
            source_wxyz=source_wxyz,
        ).replace("@deps/transfer/", "@source_bundle/transfer/"),
    )
    _write(
        collected_scene_dir / "scene_static_preview.usda",
        _composed_scene_usda(
            "source_bundle/r7_scene/scene.usda",
            particle_points,
            source_xyz=source_xyz,
            source_wxyz=source_wxyz,
        ).replace("@deps/transfer/", "@source_bundle/transfer/"),
    )
    r7_episode = next((r7_ebench / "tasks/scenario_forge").glob("*/002/episode_metadata.json"))
    episode_path = out / "ebench/tasks/scenario_forge" / scenario_id / "002/episode_metadata.json"
    _json(
        episode_path,
        _rewrite_episode(
            r7_episode,
            source_xyz=source_xyz,
            source_wxyz=source_wxyz,
            scenario_id=scenario_id,
            base_scenario_id=base_scenario_id,
        ),
    )
    r7_collected_manifest = json.loads(
        (r7_ebench / "package_manifest.json").read_text(encoding="utf-8")
    )
    source_assets = json.loads(json.dumps(r7_collected_manifest.get("source_assets", [])))
    for asset in source_assets:
        canonical = asset.get("canonical_usd") if isinstance(asset, dict) else None
        if isinstance(canonical, str) and canonical.startswith("source_bundle/"):
            asset["canonical_usd"] = "source_bundle/r7_scene/" + canonical
    source_assets.append(
        {
            "asset_id": "task02_cylinder_to_beaker_gpu_pbd_transfer_pair",
            "canonical_usd": "source_bundle/transfer/component.usda",
            "license": "LicenseRef-Internal-Restricted",
            "redistributable": False,
            "sha256": "sha256:" + transfer_handoff.component_sha256,
            "upstream_package": {
                "producer": "ConvertAsset",
                "schema_version": "aan.gpu_pbd_transfer_pair_manifest.v1",
                "package_id": transfer_handoff.package_id,
                "revision": "sha256:" + transfer_handoff.profile_sha256,
                "manifest_uri": (
                    f"convert-asset://{transfer_handoff.package_id}/manifest/"
                    f"sha256:{transfer_handoff.manifest_sha256}"
                ),
                "manifest_sha256": "sha256:" + transfer_handoff.manifest_sha256,
                "metadata": {
                    "consumer_usage": "gpu_pbd_dynamic_loaded_start",
                    "consumer_physics_patch_allowed": False,
                    "particle_count": transfer_handoff.particle_count,
                    "qualification_report_path": transfer_handoff.qualification_report_path,
                    "qualification_report_sha256": (
                        "sha256:" + transfer_handoff.qualification_report_sha256
                    ),
                    "claim_boundary": transfer_handoff.claim_boundary,
                    "dynamic_loaded_start_contract_sha256": (
                        "sha256:" + dynamic_handoff.contract_sha256
                    ),
                    "dynamic_loaded_particle_state_sha256": (
                        "sha256:" + dynamic_handoff.particle_state_sha256
                    ),
                    "maximum_outside_source_before_lift": (
                        dynamic_handoff.maximum_outside_source_before_lift
                    ),
                },
            },
        }
    )
    package_manifest = out / "ebench/package_manifest.json"
    _json(
        package_manifest,
        {
            "schema_version": "scenario-forge-genmanip-collected-package/v0.1",
            "package_id": scenario_id,
            "claim_scope": f"{release.replace('.', '')}_dynamic_loaded_start_candidate",
            "entrypoints": {
                "scene_usd": (f"assets/scene_usds/scenario_forge/{scenario_id}/scene.usda"),
                "task_config": "tasks/config.yaml",
                "episode_metadata": (
                    f"tasks/scenario_forge/{scenario_id}/002/episode_metadata.json"
                ),
                "camera_config": "cameras/fixed_camera_lift2.yml",
                "render_request": "evidence/render_request.yaml",
            },
            "release_status": "physics_qualified_candidate",
            "blocked_reasons": [],
            "source_assets": source_assets,
        },
    )
    source_request = r7_ebench / "evidence/render_request.yaml"
    render_request_path = out / "ebench/evidence/render_request.yaml"
    _yaml(
        render_request_path,
        _render_request(
            source_request,
            package_manifest=package_manifest,
            task_config=out / "ebench/tasks/config.yaml",
            episode=episode_path,
            scene=collected_scene_dir / "scene.usda",
            camera=out / "ebench/cameras/fixed_camera_lift2.yml",
            source_bundle=source_bundle,
            scenario_id=scenario_id,
            release=release,
        ),
    )
    _write(
        out / "vr/config.py",
        _vr_config(
            particle_count=transfer_handoff.particle_count,
            scenario_id=scenario_id,
        ),
    )
    finalize_vr_review_adapter(out, scenario_id=scenario_id, release=release)
    _copy(r7_package / "scenario.yaml", out / "scenario_r7_semantics.yaml")

    manifest = {
        "schema_version": "scenario-forge-task02-dynamic-loaded-handoff/v0.2",
        "scenario_id": scenario_id,
        "release": release,
        "supersedes": supersedes,
        "release_status": "physics_qualified_candidate",
        "score_ceiling": 0.60,
        "liquid_metrics_active": False,
        "particle_count": transfer_handoff.particle_count,
        "liquid_profile": {
            "target_settled_fill_ratio": liquid_profile.get("target_settled_fill_ratio"),
            "settled_fill_ratio_tolerance": liquid_profile.get("settled_fill_ratio_tolerance"),
            "particle_parameter_selection": liquid_profile.get("particle_parameter_selection"),
            "appearance": liquid_profile.get("appearance"),
        },
        "transfer_package_id": transfer_handoff.package_id,
        "transfer_manifest_sha256": transfer_handoff.manifest_sha256,
        "transfer_selected_candidate": dict(transfer_handoff.selected_candidate),
        "dynamic_loaded_start": {
            "contract_sha256": dynamic_handoff.contract_sha256,
            "particle_state_sha256": dynamic_handoff.particle_state_sha256,
            "qualification_report_sha256": (dynamic_handoff.qualification_report_sha256),
            "support_plane_to_entry_root": dict(dynamic_handoff.support_plane_to_entry_root),
            "maximum_outside_source_before_lift": (
                dynamic_handoff.maximum_outside_source_before_lift
            ),
        },
        "blocked_reasons": [],
        "entrypoints": {"ebench": "ebench/scene.usd", "vr": "vr/scene.usd"},
        "configs": {"ebench": "ebench/config.yaml", "vr": "vr/config.py"},
        "composition": {
            "background": f"{release} modern wet chemistry Code-as-Room rich tabletop",
            "table_m": [2.0, 0.8, 0.755],
            "robot": "manip/lift2/R5a_isaac41_vr600_v1",
            "transfer_component_translation_xyz_m": [-0.16, -0.17, 0.755],
            "source_initial_xyz_m": source_xyz,
            "source_initial_wxyz": source_wxyz,
            "target_initial_xyz_m": [-0.16, -0.17, 0.755],
        },
        "claims": {
            "usd_dependency_closure": "package-relative",
            "producer_static_hold_8s": True,
            "prescribed_transfer_producer": True,
            "producer_dynamic_loaded_start_3x": True,
            "ebench_load_reset_8s": "pending",
            "visible_robot_transfer": False,
            "product_fps_40_plus": False,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
    }
    _json(out / "manifest.json", manifest)
    _json(
        out / "evidence/product_smoke/report.json",
        {
            "schema_version": "scenario-forge-product-smoke-observation/v0.1",
            "scenario_id": scenario_id,
            "runtime": "Isaac Sim 4.1 + GenManip 6ff55ed",
            "gpu": "NVIDIA GeForce RTX 4090",
            "requested_physics_rate_hz": 120,
            "status": "pending",
            "last_completed_phase": "package_generated",
            "exception": None,
            "physics_duration_s": 0.0,
            "claims": {
                "usd_open": "not_run",
                "genmanip_scene_constructed": "not_run",
                "physics_initialized": "not_run",
                "static_hold_8s": "not_run",
                "robot_transfer": "not_run",
            },
            "claim_boundary": (
                "Pending eBench load/reset and eight-second zero-action smoke; "
                "never robot, policy, or benchmark success evidence."
            ),
        },
    )
    _write(
        out / "README_zh.md",
        f"""# Task 02 {release} 动态装液起始任务包

这是“250 mL 量筒 → 325 mL 烧杯”的 {release} 候选包。它包含现代湿化学房间、标准工作台、eBench 双臂配置、远侧两翼动态桌面道具，以及由 ConvertAsset 交付的 {transfer_handoff.particle_count} 个 GPU-PBD 粒子和两个 source-derived convexDecomposition 容器。液体沿用 0812 的轻量粒子参数和蓝色 PreviewSurface。量筒先在 755 mm 支撑面自然落稳，液体再以量筒入口根局部坐标预沉降；Scenario Forge 用同一实测姿态烘焙容器与粒子世界坐标，不再使用旧版硬编码高度补偿。

- eBench：打开 `ebench/scene.usd`，使用 `ebench/config.yaml`。
- VR：打开 `vr/scene.usd`，合并 `vr/config.py`。
- ConvertAsset 已证明三次动态带液冷启动均为 580/580 粒子留在量筒内，并保留原固定运动轨迹转移证据；具体数值以随包 manifest/report 为准。
- 旧版本仍保留作历史证据；{release} 不删除或篡改既有证据。
- 这不等于机器人已经成功抓取和倒液；eBench 液体 metric 尚未资格化，因此液体指标仍不计分，任务可计分上限保持 60%。
- `evidence/product_smoke/report.json` 只记录 eBench 加载、复位和零动作 8 秒检查，不扩展为策略或 benchmark 结论。
""",
    )
    refresh_hashes(out)
    return out


def refresh_hashes(out: Path) -> None:
    closure = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        closure.append(f"{_sha(path)}  {path.relative_to(out).as_posix()}")
    _write(out / "SHA256SUMS", "\n".join(closure))


def finalize_vr_review_adapter(
    out: Path,
    *,
    scenario_id: str | None = None,
    release: str | None = None,
) -> dict[str, Any]:
    """Make the custom liquid VR scene a self-contained USD+config review adapter."""

    out = out.resolve()
    if scenario_id is None or release is None:
        package_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        scenario_id = str(package_manifest["scenario_id"])
        release = str(package_manifest["release"])
    source_bundle = out / "ebench/assets/scene_usds/scenario_forge" / scenario_id / "source_bundle"
    destination = out / "vr/deps"
    _copy(source_bundle, destination)
    scene_path = out / "vr/scene.usd"
    scene = scene_path.read_text(encoding="utf-8")
    old_prefix = f"@../ebench/assets/scene_usds/scenario_forge/{scenario_id}/source_bundle/"
    scene = scene.replace(old_prefix, "@deps/")
    if "@../ebench/" in scene or "@/" in scene or "@file:" in scene:
        raise ValueError("VR review scene retains a non-package asset reference")
    _write(scene_path, scene)
    _copy(out / "vr/config.py", out / "vr/task_config.py")
    parity = {
        "schema_version": "scenario-forge-vr-ebench-parity/v0.1",
        "status": "pass_with_declared_exception",
        "canonical_scenario_id": scenario_id,
        "vr_task_id": scenario_id,
        "release": release,
        "equivalence": {
            "environment": "same_asset_and_pose",
            "table_static_support": "same_asset_and_pose",
            "task_objects": "same_assets_poses_and_physics",
            "context_props": "same_assets_poses_and_physics_not_in_task_object_list",
        },
        "allowed_exceptions": [
            {
                "id": "robot_not_embedded",
                "status": "accepted",
                "reason": "VR review handoff supplies scene USD and config; the runtime inserts the robot.",
            }
        ],
        "claims_forbidden": [
            "The review adapter proves policy or benchmark success.",
            "The review adapter activates the liquid metric.",
        ],
        "artifacts": {
            "scene_usd": {"path": "scene.usd", "sha256": "sha256:" + _sha(scene_path)},
            "task_config": {
                "path": "task_config.py",
                "sha256": "sha256:" + _sha(out / "vr/task_config.py"),
            },
        },
    }
    _json(out / "vr/parity_manifest.json", parity)
    if (out / "manifest.json").is_file():
        refresh_hashes(out)
    return parity


def finalize_product_smoke(out: Path, *, scenario_id: str = SCENARIO_ID) -> dict[str, Any]:
    out = out.resolve()
    evidence = out / "ebench/evidence/initial_scene"
    render_manifest = json.loads((evidence / "render_manifest.json").read_text(encoding="utf-8"))
    gate = yaml.safe_load((evidence / "visual_ready_gate.yaml").read_text(encoding="utf-8"))
    runtime_log = (evidence / "runtime.log").read_text(encoding="utf-8", errors="replace")
    runtime = render_manifest.get("runtime", {})
    required_log_facts = (
        "genmanip_reset_scene=true",
        "genmanip_recovery_scene=true",
        "zero_action_warmup_steps=960",
    )
    hard_markers = (
        "CUDA error",
        "illegal memory access",
        "failed to cook GPU-compatible mesh",
        "Non-GPU-compatible convex mesh",
        "Particles feature is only supported on GPU",
    )
    hard_errors = [
        line for line in runtime_log.splitlines() if any(marker in line for marker in hard_markers)
    ]
    passed = bool(
        isinstance(gate, dict)
        and gate.get("status") == "passed"
        and runtime.get("warmup_steps") == 960
        and runtime.get("action_count") == 0
        and all(fact in runtime_log for fact in required_log_facts)
        and not hard_errors
    )
    if not passed:
        raise ValueError("eBench load/reset eight-second smoke evidence is incomplete")
    robot_offset_warnings = [
        line
        for line in runtime_log.splitlines()
        if "/lift2/" in line
        and ("Collision contact offset" in line or "Collision rest offset" in line)
    ]
    report = {
        "schema_version": "scenario-forge-product-smoke-observation/v0.2",
        "scenario_id": scenario_id,
        "runtime": {
            "isaac_sim_version": runtime.get("isaac_sim_version"),
            "genmanip_revision": runtime.get("genmanip_revision"),
            "physics_rate_hz": 120,
        },
        "status": "pass",
        "last_completed_phase": "zero_action_eight_second_warmup",
        "physics_duration_s": 8.0,
        "physics_steps": 960,
        "action_count": 0,
        "hard_runtime_errors": hard_errors,
        "claims": {
            "usd_open": "pass",
            "genmanip_scene_constructed": "pass",
            "reset_and_recovery": "pass",
            "ebench_load_reset_8s": "pass",
            "robot_transfer": "not_run",
            "liquid_metric": "inactive",
            "benchmark_success": "not_run",
        },
        "nonblocking_observations": {
            "genmanip_robot_offset_warning_count": len(robot_offset_warnings),
            "ownership": "GenManip robot link preprocessing; no Scenario Forge patch applied",
        },
        "claim_boundary": (
            "eBench scene load, reset/recovery, and eight seconds of zero-action "
            "physics only; not robot, policy, liquid-metric, or benchmark success."
        ),
    }
    _json(out / "evidence/product_smoke/report.json", report)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["claims"]["ebench_load_reset_8s"] = True
    manifest["product_smoke"] = {
        "status": "pass",
        "report": "evidence/product_smoke/report.json",
        "visual_gate": "ebench/evidence/initial_scene/visual_ready_gate.yaml",
    }
    _json(manifest_path, manifest)
    refresh_hashes(out)
    return report


def attach_robot_oracle_evidence(out: Path, evidence: Path) -> dict[str, Any]:
    """Bind validated EOS scripted-oracle evidence without widening claims."""

    out = out.resolve()
    evidence = evidence.resolve()
    source_manifest_path = evidence / "robot_oracle_evidence.json"
    validation_path = evidence / "validation_report.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    package_manifest_path = out / "manifest.json"
    package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))

    if validation.get("overall_status") != "pass" or not validation.get("robot_transfer_success"):
        raise ValueError("EOS scripted robot oracle evidence is not validated")
    if source_manifest.get("scenario_id") != package_manifest.get("scenario_id"):
        raise ValueError("EOS robot evidence scenario_id does not match the package")
    if source_manifest.get("release") != package_manifest.get("release"):
        raise ValueError("EOS robot evidence release does not match the package")
    if source_manifest.get("execution_mode") != "scripted_robot_oracle":
        raise ValueError("EOS robot evidence is not a scripted oracle")
    if source_manifest.get("policy_claim") or source_manifest.get("benchmark_claim"):
        raise ValueError("EOS robot evidence improperly claims policy or benchmark success")
    if source_manifest.get("liquid_metric_active"):
        raise ValueError("EOS robot evidence improperly activates the liquid metric")
    runs = source_manifest.get("runs")
    if not isinstance(runs, list) or len(runs) != 3:
        raise ValueError("EOS robot evidence must contain exactly three cold runs")

    destination = out / "evidence/robot_oracle"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(evidence, destination)
    receipt = {
        "schema_version": "scenario-forge-external-oracle-binding/v0.1",
        "status": "pass",
        "producer": "embodied-eval-os",
        "execution_mode": "scripted_robot_oracle",
        "cold_runs": len(runs),
        "manifest": "evidence/robot_oracle/robot_oracle_evidence.json",
        "manifest_sha256": _sha(destination / "robot_oracle_evidence.json"),
        "validation": "evidence/robot_oracle/validation_report.json",
        "validation_sha256": _sha(destination / "validation_report.json"),
        "evidence_tree_sha256": _tree_sha(destination),
        "claim_boundary": (
            "Scripted robot contact transfer only; not a learned policy, benchmark "
            "result, or active liquid metric."
        ),
    }
    _json(destination / "binding_receipt.json", receipt)
    package_manifest["claims"]["visible_robot_transfer"] = True
    package_manifest["claims"]["visible_scripted_robot_transfer"] = True
    package_manifest["claims"]["robot_policy_success"] = False
    package_manifest["claims"]["benchmark_success"] = False
    package_manifest["liquid_metrics_active"] = False
    package_manifest["scripted_robot_oracle"] = receipt
    _json(package_manifest_path, package_manifest)
    refresh_hashes(out)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7-package", type=Path, default=DEFAULT_R7)
    parser.add_argument("--transfer-package", type=Path, default=DEFAULT_TRANSFER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--refresh-hashes", action="store_true")
    parser.add_argument("--finalize-product-smoke", action="store_true")
    parser.add_argument("--attach-robot-evidence", type=Path)
    parser.add_argument("--finalize-vr-review-adapter", action="store_true")
    args = parser.parse_args()
    if args.refresh_hashes:
        refresh_hashes(args.out.resolve())
        print(args.out.resolve())
        return 0
    if args.finalize_product_smoke:
        print(json.dumps(finalize_product_smoke(args.out), ensure_ascii=False))
        return 0
    if args.attach_robot_evidence is not None:
        print(
            json.dumps(
                attach_robot_oracle_evidence(args.out, args.attach_robot_evidence),
                ensure_ascii=False,
            )
        )
        return 0
    if args.finalize_vr_review_adapter:
        print(json.dumps(finalize_vr_review_adapter(args.out), ensure_ascii=False))
        return 0
    print(
        build(
            r7_package=args.r7_package,
            transfer_package=args.transfer_package,
            out=args.out,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

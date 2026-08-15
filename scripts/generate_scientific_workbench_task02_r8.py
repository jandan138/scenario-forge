#!/usr/bin/env python3
"""Build Task 02 r8.3 from r7 semantics and a qualified transfer-pair handoff."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml

from scenario_forge.adapters.convert_asset import load_gpu_pbd_transfer_pair_handoff


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R7 = REPO_ROOT / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages/scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
DEFAULT_TRANSFER = Path("/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task02_cylinder_to_beaker_gpu_pbd_transfer_20260815_r6/final_package/task02_cylinder_to_beaker_gpu_pbd_transfer_pair_r1")
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task02_r83_20260815"
SCENARIO_ID = "scientific_workbench_r83_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
R7_SCENARIO_ID = "scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"


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


def _composed_scene_usda(r7_reference: str) -> str:
    return f'''#usda 1.0
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
        over "obj_obj_graduated_cylinder" (active = false) {{}}
        over "obj_obj_beaker" (active = false) {{}}
        def Xform "fluid_runtime" (
            prepend references = @deps/transfer/component.usda@</World/Transfer>
        )
        {{
            double3 xformOp:translate = (-0.16, -0.17, 0.755)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
            over "Source"
            {{
                bool physics:kinematicEnabled = 0
            }}
            over "Target"
            {{
                bool physics:kinematicEnabled = 0
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
'''


def _rewrite_ebench_config(source: Path) -> dict[str, Any]:
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    evaluations = config.get("evaluation_configs", [])
    if not evaluations:
        evaluations = [{"task_name": f"scenario_forge/{SCENARIO_ID}"}]
        config["evaluation_configs"] = evaluations
    for item in evaluations:
        item["task_name"] = f"scenario_forge/{SCENARIO_ID}"
        item["usd_name"] = (
            f"collected_packages/{SCENARIO_ID}/assets/scene_usds/"
            f"scenario_forge/{SCENARIO_ID}/scene"
        )
        item["physics_dt"] = 1.0 / 120.0
        item["rendering_dt"] = 1.0 / 60.0
        item.setdefault("physics_scene_config", {})["EnableGPUDynamics"] = True
        item["physics_scene_config"]["GpuMaxParticleContacts"] = 1048576
        item["physics_scene_config"]["TimeStepsPerSecond"] = 120
        cameras = item.get("domain_randomization", {}).get("cameras")
        if isinstance(cameras, dict):
            cameras["config_path"] = (
                f"collected_packages/{SCENARIO_ID}/cameras/fixed_camera_lift2.yml"
            )
        item["prototype_fluid"] = {
            "status": "qualified_prescribed_transfer",
            "particle_count": 548,
            "liquid_metrics_active": False,
            "inactive_reason": "ebench_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_prescribed_transfer_pair",
        }
        goal = item.get("generation_config", {}).get("goal", [])
        for level1 in goal:
            for level2 in level1 if isinstance(level1, list) else []:
                for predicate in level2 if isinstance(level2, list) else []:
                    if isinstance(predicate, dict) and predicate.get("obj1_uid") == "obj_graduated_cylinder":
                        predicate["x_range"] = [0.05, 0.13]
                        predicate["y_range"] = [-0.21, -0.13]
    return config


def _rewrite_episode(source: Path) -> dict[str, Any]:
    episode = json.loads(source.read_text(encoding="utf-8"))
    def replace(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(R7_SCENARIO_ID, SCENARIO_ID).replace(
                f"/World/{SCENARIO_ID}/", "/World/_scene/"
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
        "obj_graduated_cylinder": ([0.09, -0.17, 0.755], "/World/_scene/fluid_runtime/Source"),
        "obj_beaker": ([-0.16, -0.17, 0.755], "/World/_scene/fluid_runtime/Target"),
    }
    for object_id, item in layout.items():
        if not isinstance(item, dict):
            continue
        if object_id in task_poses:
            item["position"], item["prim_path"] = task_poses[object_id]
            item["path"] = ""
            continue
        prim_path = item.get("prim_path")
        if isinstance(prim_path, str) and "/obj_" in prim_path:
            item["prim_path"] = "/World/_scene/" + prim_path.rsplit("/", 1)[-1]
        asset_path = item.get("path")
        if isinstance(asset_path, str) and asset_path:
            rewritten = asset_path
            item["path"] = rewritten.replace(
                f"assets/scene_usds/scenario_forge/{SCENARIO_ID}/source_bundle/",
                f"assets/scene_usds/scenario_forge/{SCENARIO_ID}/source_bundle/r7_scene/source_bundle/",
            )
    for predicate_group in task_data.get("goal", []):
        for predicates in predicate_group if isinstance(predicate_group, list) else []:
            for predicate in predicates if isinstance(predicates, list) else []:
                if isinstance(predicate, dict) and predicate.get("obj1_uid") == "obj_graduated_cylinder":
                    predicate["x_range"] = [0.05, 0.13]
                    predicate["y_range"] = [-0.21, -0.13]
    contract = task_data.get("scenario_forge_runtime_contract", {})
    for item in contract.get("objects", []) if isinstance(contract, dict) else []:
        object_id = item.get("scenario_object_id") if isinstance(item, dict) else None
        if object_id in task_poses:
            position, prim_path = task_poses[object_id]
            item["initial_pose"]["xyz"] = position
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
) -> dict[str, Any]:
    request = yaml.safe_load(source.read_text(encoding="utf-8"))
    request["package_id"] = SCENARIO_ID
    request["task_name"] = f"scenario_forge/{SCENARIO_ID}"
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
        {"package_id": SCENARIO_ID, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    request["input_digest"] = "sha256:" + sha256(digest_payload).hexdigest()
    request["claim_boundary"] = (
        "r8.3 initial-scene visual evidence only; not robot transfer, "
        "FPS, policy, or benchmark success."
    )
    return request


def _vr_config() -> str:
    return f'''# Merge this TASKS entry into the VR teleop task registry.
TASKS = {{
    "{SCENARIO_ID}": {{
        "scene_usd_file_path": {{"scene1": str(_ASSETS_DIR / "scenes/{SCENARIO_ID}/scene.usd")}},
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
            "status": "qualified_prescribed_transfer",
            "particle_count": 548,
            "liquid_metrics_active": False,
            "inactive_reason": "vr_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_prescribed_transfer_pair",
        }},
    }},
}}
'''


def build(*, r7_package: Path, transfer_package: Path, out: Path) -> Path:
    r7_package = r7_package.resolve()
    transfer_package = transfer_package.resolve()
    out = out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    transfer_manifest_path = transfer_package / "evidence/manifest.json"
    transfer_handoff = load_gpu_pbd_transfer_pair_handoff(
        transfer_package, transfer_manifest_path
    )
    r7_scene = _r7_ebench_scene(r7_package)
    collected_scene_dir = (
        out
        / "ebench/assets/scene_usds/scenario_forge"
        / SCENARIO_ID
    )
    source_bundle = collected_scene_dir / "source_bundle"
    _copy(r7_scene.parent, source_bundle / "r7_scene")
    _copy(transfer_package, source_bundle / "transfer")
    ebench_bundle = (
        f"assets/scene_usds/scenario_forge/{SCENARIO_ID}/source_bundle"
    )
    _write(
        out / "ebench/scene.usd",
        _composed_scene_usda(f"{ebench_bundle}/r7_scene/scene.usda").replace(
            "@deps/transfer/", f"@{ebench_bundle}/transfer/"
        ),
    )
    _write(
        out / "vr/scene.usd",
        _composed_scene_usda(
            f"../ebench/{ebench_bundle}/r7_scene/scene.usda"
        ).replace(
            "@deps/transfer/", f"@../ebench/{ebench_bundle}/transfer/"
        ),
    )

    r7_ebench = r7_package / "adapters/ebench/genmanip"
    config = _rewrite_ebench_config(r7_ebench / "tasks/config.yaml")
    _yaml(out / "ebench/config.yaml", config)
    _yaml(out / "ebench/tasks/config.yaml", config)
    _copy(r7_ebench / "cameras", out / "ebench/cameras")
    _write(
        collected_scene_dir / "scene.usda",
        _composed_scene_usda("source_bundle/r7_scene/scene.usda").replace(
            "@deps/transfer/", "@source_bundle/transfer/"
        ),
    )
    _write(
        collected_scene_dir / "scene_static_preview.usda",
        _composed_scene_usda("source_bundle/r7_scene/scene.usda")
        .replace("@deps/transfer/", "@source_bundle/transfer/"),
    )
    r7_episode = next(
        (r7_ebench / "tasks/scenario_forge").glob("*/002/episode_metadata.json")
    )
    episode_path = (
        out
        / "ebench/tasks/scenario_forge"
        / SCENARIO_ID
        / "002/episode_metadata.json"
    )
    _json(episode_path, _rewrite_episode(r7_episode))
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
                    "consumer_usage": "gpu_pbd_prescribed_transfer_pair",
                    "consumer_physics_patch_allowed": False,
                    "particle_count": transfer_handoff.particle_count,
                    "qualification_report_path": transfer_handoff.qualification_report_path,
                    "qualification_report_sha256": (
                        "sha256:" + transfer_handoff.qualification_report_sha256
                    ),
                    "claim_boundary": transfer_handoff.claim_boundary,
                },
            },
        }
    )
    package_manifest = out / "ebench/package_manifest.json"
    _json(
        package_manifest,
        {
            "schema_version": "scenario-forge-genmanip-collected-package/v0.1",
            "package_id": SCENARIO_ID,
            "claim_scope": "r83_physics_qualified_candidate",
            "entrypoints": {
                "scene_usd": (
                    f"assets/scene_usds/scenario_forge/{SCENARIO_ID}/scene.usda"
                ),
                "task_config": "tasks/config.yaml",
                "episode_metadata": (
                    f"tasks/scenario_forge/{SCENARIO_ID}/002/episode_metadata.json"
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
        ),
    )
    _write(out / "vr/config.py", _vr_config())
    _copy(r7_package / "scenario.yaml", out / "scenario_r7_semantics.yaml")

    manifest = {
        "schema_version": "scenario-forge-task02-r83-handoff/v0.1",
        "scenario_id": SCENARIO_ID,
        "release": "r8.3",
        "release_status": "physics_qualified_candidate",
        "score_ceiling": 0.60,
        "liquid_metrics_active": False,
        "particle_count": 548,
        "transfer_package_id": transfer_handoff.package_id,
        "transfer_manifest_sha256": transfer_handoff.manifest_sha256,
        "transfer_selected_candidate": dict(transfer_handoff.selected_candidate),
        "blocked_reasons": [],
        "entrypoints": {"ebench": "ebench/scene.usd", "vr": "vr/scene.usd"},
        "configs": {"ebench": "ebench/config.yaml", "vr": "vr/config.py"},
        "composition": {
            "background": "r7 modern wet chemistry Code-as-Room",
            "table_m": [2.0, 0.8, 0.755],
            "robot": "manip/lift2/R5a_isaac41_vr600_v1",
            "transfer_component_translation_xyz_m": [-0.16, -0.17, 0.755],
            "source_initial_xyz_m": [0.09, -0.17, 0.755],
            "target_initial_xyz_m": [-0.16, -0.17, 0.755],
        },
        "claims": {
            "usd_dependency_closure": "package-relative",
            "producer_static_hold_8s": True,
            "prescribed_transfer_producer": True,
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
            "scenario_id": SCENARIO_ID,
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
        """# Task 02 r8.3 物理候选任务包

这是“250 mL 量筒 → 325 mL 烧杯”的 r8.3 候选包。它包含 r7 现代湿化学房间、标准工作台、eBench 双臂配置，以及由 ConvertAsset 0812 recipe 交付的 548 个 GPU-PBD 粒子和两个 source-derived convexDecomposition 容器。

- eBench：打开 `ebench/scene.usd`，使用 `ebench/config.yaml`。
- VR：打开 `vr/scene.usd`，合并 `vr/config.py`。
- ConvertAsset 已证明量筒/烧杯分别静置 8 秒，并证明固定运动轨迹的量筒→烧杯转移三次冷启动达到 94.5%–96.0%。
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


def finalize_product_smoke(out: Path) -> dict[str, Any]:
    out = out.resolve()
    evidence = out / "ebench/evidence/initial_scene"
    render_manifest = json.loads(
        (evidence / "render_manifest.json").read_text(encoding="utf-8")
    )
    gate = yaml.safe_load(
        (evidence / "visual_ready_gate.yaml").read_text(encoding="utf-8")
    )
    runtime_log = (evidence / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
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
    hard_errors = [line for line in runtime_log.splitlines() if any(marker in line for marker in hard_markers)]
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
        "scenario_id": SCENARIO_ID,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7-package", type=Path, default=DEFAULT_R7)
    parser.add_argument("--transfer-package", type=Path, default=DEFAULT_TRANSFER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--refresh-hashes", action="store_true")
    parser.add_argument("--finalize-product-smoke", action="store_true")
    args = parser.parse_args()
    if args.refresh_hashes:
        refresh_hashes(args.out.resolve())
        print(args.out.resolve())
        return 0
    if args.finalize_product_smoke:
        print(json.dumps(finalize_product_smoke(args.out), ensure_ascii=False))
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

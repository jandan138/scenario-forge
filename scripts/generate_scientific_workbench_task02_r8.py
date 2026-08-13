#!/usr/bin/env python3
"""Build the Task 02 r8 diagnostic handoff from an r7 package and fluid component."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R7 = REPO_ROOT / "outputs/scientific_workbench_asset_expansion_20260813_r7_full/packages/scientific_workbench_r7_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
DEFAULT_FLUID = Path("/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_task02_fluid_component_r8_20260813")
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task02_r8_20260813"
SCENARIO_ID = "scientific_workbench_r8_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
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
        def Xform "obj_obj_graduated_cylinder" (
            active = true
            prepend references = @deps/fluid/component.usda@</World/FluidWorkcell/SourceContainer>
        )
        {{
            double3 xformOp:translate = (0.16, -0.15, 0.755)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
        }}
        def Xform "obj_obj_beaker" (
            active = true
            prepend references = @deps/fluid/component.usda@</World/FluidWorkcell/TargetContainer>
        )
        {{
            double3 xformOp:translate = (-0.16, -0.17, 0.755)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
        }}
        def Xform "fluid_runtime" (
            prepend references = @deps/fluid/component.usda@</World/FluidWorkcell>
        )
        {{
            double3 xformOp:translate = (0, 0, 0.755)
            uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate"]
            over "SourceContainer" (active = false) {{}}
            over "TargetContainer" (active = false) {{}}
        }}
    }}

}}

over "physicsScene"
{{
    token physxScene:broadphaseType = "GPU"
    bool physxScene:enableGPUDynamics = 1
    uint physxScene:gpuMaxParticleContacts = 1048576
    token physxScene:solverType = "TGS"
    uint physxScene:timeStepsPerSecond = 60
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
        item["physics_dt"] = 1.0 / 60.0
        item["rendering_dt"] = 1.0 / 60.0
        item.setdefault("physics_scene_config", {})["EnableGPUDynamics"] = True
        item["physics_scene_config"]["GpuMaxParticleContacts"] = 1048576
        item["physics_scene_config"]["TimeStepsPerSecond"] = 60
        cameras = item.get("domain_randomization", {}).get("cameras")
        if isinstance(cameras, dict):
            cameras["config_path"] = (
                f"collected_packages/{SCENARIO_ID}/cameras/fixed_camera_lift2.yml"
            )
        item["prototype_fluid"] = {
            "status": "blocked",
            "particle_count": 548,
            "liquid_metrics_active": False,
            "blocker": "gpu_incompatible_visual_mesh_convex_decomposition",
        }
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
    for item in layout.values():
        if not isinstance(item, dict):
            continue
        prim_path = item.get("prim_path")
        if isinstance(prim_path, str) and "/obj_" in prim_path:
            item["prim_path"] = "/World/_scene/" + prim_path.rsplit("/", 1)[-1]
        asset_path = item.get("path")
        if isinstance(asset_path, str) and asset_path:
            rewritten = asset_path
            item["path"] = rewritten.replace(
                f"assets/scene_usds/scenario_forge/{SCENARIO_ID}/source_bundle/",
                "deps/r7_scene/source_bundle/",
            )
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
        "r8 initial-scene visual evidence only; not liquid retention, transfer, "
        "FPS, policy, or benchmark success."
    )
    return request


def _vr_config() -> str:
    return f'''# Merge this TASKS entry into the VR teleop task registry.
TASKS = {{
    "{SCENARIO_ID}": {{
        "scene_usd_file_path": {{"scene1": str(_ASSETS_DIR / "scenes/{SCENARIO_ID}/scene.usd")}},
        "obj_prim_list": [
            "/World/_scene/obj_obj_graduated_cylinder",
            "/World/_scene/obj_obj_beaker",
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
            "TimeStepsPerSecond": 60,
        }},
        "prototype_fluid": {{
            "status": "blocked",
            "particle_count": 548,
            "liquid_metrics_active": False,
            "blocker": "gpu_incompatible_visual_mesh_convex_decomposition",
        }},
    }},
}}
'''


def build(*, r7_package: Path, fluid_package: Path, out: Path) -> Path:
    r7_package = r7_package.resolve()
    fluid_package = fluid_package.resolve()
    out = out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    fluid_manifest = json.loads((fluid_package / "evidence/manifest.json").read_text())
    fluid_profile = json.loads((fluid_package / "interactive_fluid_scene_profile.json").read_text())

    r7_scene = _r7_ebench_scene(r7_package)
    _copy(r7_scene.parent, out / "ebench/deps/r7_scene")
    _copy(fluid_package, out / "ebench/deps/fluid")
    _write(
        out / "ebench/scene.usd",
        _composed_scene_usda("deps/r7_scene/scene.usda"),
    )
    _write(
        out / "vr/scene.usd",
        _composed_scene_usda("../ebench/deps/r7_scene/scene.usda").replace(
            "@deps/fluid/", "@../ebench/deps/fluid/"
        ),
    )

    r7_ebench = r7_package / "adapters/ebench/genmanip"
    config = _rewrite_ebench_config(r7_ebench / "tasks/config.yaml")
    _yaml(out / "ebench/config.yaml", config)
    _yaml(out / "ebench/tasks/config.yaml", config)
    _copy(r7_ebench / "cameras", out / "ebench/cameras")
    collected_scene_dir = (
        out
        / "ebench/assets/scene_usds/scenario_forge"
        / SCENARIO_ID
    )
    _write(
        collected_scene_dir / "scene.usda",
        _composed_scene_usda("../../../../deps/r7_scene/scene.usda").replace(
            "@deps/fluid/", "@../../../../deps/fluid/"
        ),
    )
    _write(
        collected_scene_dir / "scene_static_preview.usda",
        _composed_scene_usda("../../../../deps/r7_scene/scene.usda")
        .replace("@deps/fluid/", "@../../../../deps/fluid/")
        .replace(
            'def Xform "fluid_runtime" (',
            'def Xform "fluid_runtime" (\n            active = false',
        ),
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
    package_manifest = out / "ebench/package_manifest.json"
    _json(
        package_manifest,
        {
            "schema_version": "scenario-forge-genmanip-collected-package/v0.1",
            "package_id": SCENARIO_ID,
            "claim_scope": "r8_fluid_prototype_blocked",
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
            "release_status": "prototype_blocked",
            "blocked_reasons": [
                "gpu_incompatible_visual_mesh_convex_decomposition"
            ],
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
            source_bundle=out / "ebench/deps",
        ),
    )
    _write(out / "vr/config.py", _vr_config())
    _copy(r7_package / "scenario.yaml", out / "scenario_r7_semantics.yaml")

    manifest = {
        "schema_version": "scenario-forge-task02-r8-diagnostic-handoff/v0.1",
        "scenario_id": SCENARIO_ID,
        "release": "r8",
        "release_status": "prototype_blocked",
        "score_ceiling": 0.60,
        "liquid_metrics_active": False,
        "particle_count": 548,
        "fluid_profile_id": fluid_profile.get("profile_id"),
        "fluid_component_status": fluid_manifest.get("overall_status"),
        "blocked_reasons": fluid_manifest.get("blocked_reasons", []),
        "entrypoints": {"ebench": "ebench/scene.usd", "vr": "vr/scene.usd"},
        "configs": {"ebench": "ebench/config.yaml", "vr": "vr/config.py"},
        "composition": {
            "background": "r7 modern wet chemistry Code-as-Room",
            "table_m": [2.0, 0.8, 0.755],
            "robot": "manip/lift2/R5a_isaac41_vr600_v1",
            "fluid_component_translation_xyz_m": [0.0, 0.0, 0.755],
        },
        "claims": {
            "usd_dependency_closure": "package-relative",
            "static_hold_8s": False,
            "visible_transfer": False,
            "fps_40_plus": False,
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
            "requested_rate_hz": 60,
            "status": "blocked",
            "last_completed_phase": "scene_constructed",
            "exception": "CUDA error: an illegal memory access was encountered",
            "correlated_upstream_blocker": (
                "gpu_incompatible_visual_mesh_convex_decomposition"
            ),
            "physics_duration_s": 0.0,
            "claims": {
                "usd_open": "pass",
                "genmanip_scene_constructed": "pass",
                "physics_initialized": "fail",
                "static_hold_8s": "not_run",
                "visible_transfer": "not_run",
                "fps_40_plus": "not_measured",
            },
            "claim_boundary": (
                "This is a negative product-composition smoke observation, not "
                "task, policy, benchmark, or liquid-transfer success evidence."
            ),
        },
    )
    _write(
        out / "README_zh.md",
        """# Task 02 r8 诊断任务包

这是“250 mL 量筒 → 325 mL 烧杯”的 r8 液体原型。它包含 r7 现代湿化学房间、标准工作台、eBench 双臂配置和 548 个 PhysX PBD 粒子。

- eBench：打开 `ebench/scene.usd`，使用 `ebench/config.yaml`。
- VR：打开 `vr/scene.usd`，合并 `vr/config.py`。
- 当前状态：blocked。Isaac 4.1 无法把源量筒视觉网格的 convexDecomposition cook 成可与 GPU 粒子碰撞的网格。
- 因此液体指标仍不计分，任务可计分上限保持 60%，不声明静置、倒液、FPS、机器人策略或 benchmark 成功。
""",
    )
    refresh_hashes(out)
    return out


def refresh_hashes(out: Path) -> None:
    closure = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        closure.append(f"{_sha(path)}  {path.relative_to(out).as_posix()}")
    _write(out / "SHA256SUMS", "\n".join(closure))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7-package", type=Path, default=DEFAULT_R7)
    parser.add_argument("--fluid-package", type=Path, default=DEFAULT_FLUID)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--refresh-hashes", action="store_true")
    args = parser.parse_args()
    if args.refresh_hashes:
        refresh_hashes(args.out.resolve())
        print(args.out.resolve())
        return 0
    print(build(r7_package=args.r7_package, fluid_package=args.fluid_package, out=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

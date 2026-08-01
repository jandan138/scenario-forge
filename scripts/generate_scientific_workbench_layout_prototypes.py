#!/usr/bin/env python3
"""Compile Feishu-aligned layout prototypes and authored key-state previews."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import subprocess
from typing import Any, Mapping, Sequence

import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.ik_preflight import (
    write_provisional_ik_preflight_request,
)
from scenario_forge.adapters.ebench.preview import (
    run_genmanip_initial_preview,
    write_genmanip_preview_request,
)
from scenario_forge.adapters.ebench.tabletop_placement import (
    validate_scientific_workbench_tabletop_placement,
)
from scenario_forge.artifacts.package_closure import write_package_closure_evidence
from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.package_compiler import compile_scenario_package
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_scientific_environment_previews.py"
DEFAULT_RUNTIME_RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
SPEC_ROOT = REPO_ROOT / "examples/scientific_workbench/layout_validated"
TASK_SPECS = {
    "task2": SPEC_ROOT / "pour_cylinder_to_beaker/scenario.yaml",
    "task13": SPEC_ROOT / "funnel_pour_cylinder_to_flask/scenario.yaml",
    "task16": SPEC_ROOT / "two_sample_mix/scenario.yaml",
}
CAMERA_POSITION = [-0.48, -0.66, 1.16]
CAMERA_TARGET = [0.28, 0.0, 0.92]
OVERVIEW_CAMERA_POSITION = [-1.55, -1.20, 1.45]
OVERVIEW_CAMERA_TARGET = [0.24, 0.0, 0.88]
CLAIM_BOUNDARY = (
    "Authored static visualization only. No robot motion, collision-free path, "
    "policy, liquid transfer, benchmark success, or task completion was executed."
)
FINAL_STATIC_RENDER_WIDTH = 1920
FINAL_STATIC_RENDER_HEIGHT = 1080
FINAL_STATIC_WARMUP_FRAMES = 40
FINAL_RUNTIME_RENDER_RESOLUTION = (1920, 1080)


KEY_STATES: dict[str, tuple[dict[str, Any], ...]] = {
    "task2": (
        {"id": "initial_layout", "description_zh": "初始桌面摆放", "poses": {}},
        {
            "id": "cylinder_aligned_over_beaker",
            "description_zh": "量筒静态摆到烧杯上方的对准示意",
            "poses": {
                "/World/graduated_cylinder_03": {
                    "xyz": [0.10, 0.05304, 1.00],
                    "wxyz": [0.8870108332, 0.4617486132, 0.0, 0.0],
                }
            },
        },
        {"id": "cylinder_returned", "description_zh": "量筒正立归还示意", "poses": {}},
    ),
    "task13": (
        {"id": "initial_layout", "description_zh": "初始桌面摆放", "poses": {}},
        {
            "id": "funnel_inserted",
            "description_zh": "漏斗出口静态插入锥形瓶口的示意",
            "poses": {
                "/World/Funnel": {
                    "xyz": [0.10, -0.20, 0.965],
                    "wxyz": [1.0, 0.0, 0.0, 0.0],
                }
            },
        },
        {
            "id": "cylinder_aligned_to_funnel",
            "description_zh": "量筒静态摆到已插入漏斗上方的示意",
            "poses": {
                "/World/Funnel": {
                    "xyz": [0.10, -0.20, 0.965],
                    "wxyz": [1.0, 0.0, 0.0, 0.0],
                },
                "/World/graduated_cylinder_03": {
                    "xyz": [0.10, 0.02304, 1.18],
                    "wxyz": [0.8870108332, 0.4617486132, 0.0, 0.0],
                },
            },
        },
    ),
    "task16": (
        {"id": "initial_layout", "description_zh": "初始桌面摆放", "poses": {}},
        {
            "id": "sample_a_aligned",
            "description_zh": "样品 A 容器静态对准烧杯的示意",
            "poses": {
                "/World/graduated_cylinder_03": {
                    "xyz": [0.10, 0.02304, 1.00],
                    "wxyz": [0.8870108332, 0.4617486132, 0.0, 0.0],
                }
            },
        },
        {
            "id": "sample_b_aligned",
            "description_zh": "样品 B 容器静态对准烧杯的示意",
            "poses": {
                "/World/conical_bottle03": {
                    "xyz": [0.10, -0.03898, 0.98],
                    "wxyz": [0.8870108332, 0.4617486132, 0.0, 0.0],
                }
            },
        },
        {
            "id": "beaker_shake_pose",
            "description_zh": "烧杯离台并倾斜的晃匀关键姿态示意",
            "poses": {
                "/World/Beaker": {
                    "xyz": [0.10, -0.16, 1.02],
                    "wxyz": [0.984807753, 0.1736481777, 0.0, 0.0],
                }
            },
        },
    ),
}


def authored_state_layer_text(
    *,
    base_scene: Path,
    layer_path: Path,
    poses: Mapping[str, Mapping[str, Sequence[float]]],
) -> str:
    relative_scene = os.path.relpath(base_scene.resolve(), layer_path.parent.resolve())
    lines = [
        "#usda 1.0",
        "(",
        '    metersPerUnit = 1',
        '    upAxis = "Z"',
        "    subLayers = [",
        f"        @{relative_scene}@,",
        "    ]",
        "    customLayerData = {",
        "        bool scenarioForgeAuthoredStaticPreview = true",
        "        dictionary cameraSettings = {",
        "            dictionary Perspective = {",
        f"                double3 position = ({', '.join(map(str, CAMERA_POSITION))})",
        f"                double3 target = ({', '.join(map(str, CAMERA_TARGET))})",
        (
            "                double3 orbitPosition = "
            f"({', '.join(map(str, OVERVIEW_CAMERA_POSITION))})"
        ),
        (
            "                double3 orbitTarget = "
            f"({', '.join(map(str, OVERVIEW_CAMERA_TARGET))})"
        ),
        "            }",
        "        }",
        "    }",
        ")",
        "",
        'def DomeLight "ScenarioForgePreviewDomeLight"',
        "{",
        "    color3f inputs:color = (0.92, 0.95, 1)",
        "    float inputs:intensity = 1000",
        "}",
        "",
    ]
    tree: dict[str, Any] = {}
    for path, pose in sorted(poses.items()):
        if not path.startswith("/World/"):
            raise ValueError(f"authored pose path must be under /World: {path}")
        node = tree
        for segment in path.strip("/").split("/"):
            node = node.setdefault(segment, {})

        xyz = pose.get("xyz")
        wxyz = pose.get("wxyz")
        if xyz is None or len(xyz) != 3 or wxyz is None or len(wxyz) != 4:
            raise ValueError(f"authored pose must contain xyz and wxyz: {path}")
        node["__pose__"] = {
            "xyz": [float(value) for value in xyz],
            "wxyz": [float(value) for value in wxyz],
        }

    def emit(children: Mapping[str, Any], depth: int) -> None:
        indent = "    " * depth
        for name, child in children.items():
            if name == "__pose__":
                continue
            lines.append(f'{indent}over "{name}"')
            lines.append(f"{indent}{{")
            pose = child.get("__pose__")
            if pose is not None:
                xyz = ", ".join(f"{value:.12g}" for value in pose["xyz"])
                wxyz = pose["wxyz"]
                vector = ", ".join(f"{value:.12g}" for value in wxyz[1:])
                lines.extend(
                    [
                        f"{indent}    double3 xformOp:translate = ({xyz})",
                        f"{indent}    quatd xformOp:orient = ({wxyz[0]:.12g}, {vector})",
                        (
                            f'{indent}    uniform token[] xformOpOrder = '
                            '["!resetXformStack!", "xformOp:translate", "xformOp:orient"]'
                        ),
                    ]
                )
            emit(child, depth + 1)
            lines.append(f"{indent}}}")
            lines.append("")

    emit(tree, 0)
    return "\n".join(lines).rstrip() + "\n"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def static_render_command(
    *,
    isaac_python: Path,
    renderer: Path,
    state_id: str,
    scene_path: Path,
    output_dir: Path,
) -> list[str]:
    """Build the audited high-quality static storyboard render command."""
    return [
        str(isaac_python.resolve()),
        str(renderer.resolve()),
        "worker",
        "--candidate-id",
        state_id,
        "--source-usd",
        str(scene_path.resolve()),
        "--source-sha256",
        _digest(scene_path),
        "--out",
        str(output_dir.resolve()),
        "--width",
        str(FINAL_STATIC_RENDER_WIDTH),
        "--height",
        str(FINAL_STATIC_RENDER_HEIGHT),
        "--warmup-frames",
        str(FINAL_STATIC_WARMUP_FRAMES),
        "--exposure-mode",
        "fixed",
        "--exposure-multiplier",
        "0.8",
    ]


def _render_state(
    *,
    isaac_python: Path,
    renderer: Path,
    state_id: str,
    scene_path: Path,
    output_dir: Path,
    timeout_seconds: float,
) -> None:
    command = static_render_command(
        isaac_python=isaac_python,
        renderer=renderer,
        state_id=state_id,
        scene_path=scene_path,
        output_dir=output_dir,
    )
    environment = dict(os.environ)
    for name in (
        "ISAAC_SIM_ROOT",
        "ISAAC_PATH",
        "ISAACSIM_PATH",
        "CARB_APP_PATH",
        "EXP_PATH",
        "KIT_APP_NAME",
        "OMNI_KIT_ROOT",
        "OMNI_EXTENSIONS_PATH",
        "PYTHONPATH",
        "PYTHONHOME",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "ACCEPT_EULA": "Y",
            "OMNI_KIT_ACCEPT_EULA": "YES",
            "PYTHONUNBUFFERED": "1",
        }
    )
    prefix = isaac_python.resolve().parents[1]
    libs = [
        prefix / "lib/python3.10/site-packages/torch/lib",
        prefix / "lib/python3.10/site-packages/nvidia/cuda_runtime/lib",
    ]
    old_ld = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = ":".join(
        [str(path) for path in libs if path.is_dir()] + ([old_ld] if old_ld else [])
    )
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        tail, _ = process.communicate(timeout=30.0)
        partial = exc.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        output = partial + (tail or "")
        (output_dir / "runtime.log").write_text(output, encoding="utf-8")
        raise RuntimeError(
            f"Isaac authored-state render timed out after {timeout_seconds:.1f}s "
            f"for {state_id}"
        ) from exc
    (output_dir / "runtime.log").write_text(output, encoding="utf-8")
    if process.returncode != 0:
        raise RuntimeError(
            f"Isaac authored-state render failed for {state_id}: "
            f"{process.returncode}; see {output_dir / 'runtime.log'}"
        )


def _write_key_states(
    *,
    task_key: str,
    package_root: Path,
    render: bool,
    isaac_python: Path | None,
    renderer: Path,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    evidence_root = (
        package_root
        / "adapters/ebench/genmanip/evidence/authored_key_states"
    )
    evidence_root.mkdir(parents=True, exist_ok=True)
    base_scene = package_root / "scene/main.usda"
    records: list[dict[str, Any]] = []
    for state in KEY_STATES[task_key]:
        state_dir = evidence_root / str(state["id"])
        state_dir.mkdir(parents=True, exist_ok=True)
        scene_path = state_dir / "scene.usda"
        scene_path.write_text(
            authored_state_layer_text(
                base_scene=base_scene,
                layer_path=scene_path,
                poses=state["poses"],
            ),
            encoding="utf-8",
        )
        render_status = "not_run"
        render_error = None
        if render:
            assert isaac_python is not None
            render_manifest = state_dir / "render_manifest.json"
            reusable = False
            if render_manifest.is_file():
                try:
                    previous = json.loads(render_manifest.read_text(encoding="utf-8"))
                    views = previous.get("views")
                    reusable = (
                        previous.get("render_status") == "pass"
                        and previous.get("source_sha256") == _digest(scene_path)
                        and isinstance(views, Mapping)
                        and all(
                            isinstance(views.get(view_name), Mapping)
                            and views[view_name].get("resolution")
                            == [FINAL_STATIC_RENDER_WIDTH, FINAL_STATIC_RENDER_HEIGHT]
                            for view_name in ("authored", "eye_left", "eye_right")
                        )
                        and previous.get("runtime", {}).get("exposure_mode") == "fixed"
                        and (state_dir / "contact_sheet.png").is_file()
                    )
                except (OSError, json.JSONDecodeError):
                    reusable = False
            if reusable:
                render_status = "pass"
            else:
                try:
                    _render_state(
                        isaac_python=isaac_python,
                        renderer=renderer,
                        state_id=f"{task_key}.{state['id']}",
                        scene_path=scene_path,
                        output_dir=state_dir,
                        timeout_seconds=timeout_seconds,
                    )
                    render_status = "pass"
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    render_status = "failed"
                    render_error = str(exc)
        records.append(
            {
                "state_id": state["id"],
                "description_zh": state["description_zh"],
                "execution_status": "not_executed",
                "scene_path": str(scene_path.relative_to(evidence_root)),
                "scene_sha256": _digest(scene_path),
                "render_status": render_status,
                **({"render_error": render_error} if render_error else {}),
                "contact_sheet": (
                    str((state_dir / "contact_sheet.png").relative_to(evidence_root))
                    if render_status == "pass"
                    else None
                ),
            }
        )
    manifest = {
        "schema_version": "scenario-forge-authored-key-state-preview/v0.1",
        "scenario_id": package_root.name,
        "claim": "authored_static_visualization",
        "execution_status": "not_executed",
        "states": records,
        "not_evidence_of": [
            "robot_reachability",
            "collision_free_motion",
            "policy_success",
            "benchmark_success",
            "liquid_transfer",
            "task_completion",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    (evidence_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile Feishu Tasks 2/13/16 as layout-validated eBench prototypes."
    )
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--task", choices=(*TASK_SPECS, "all"), default="all")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--isaac-python", type=Path)
    parser.add_argument("--renderer", type=Path, default=DEFAULT_RENDERER)
    parser.add_argument("--render-timeout", type=float, default=600.0)
    parser.add_argument(
        "--render-runtime-preview",
        action="store_true",
        help="Render 1080p post-reset, pre-action GenManip evidence with Lift2 visible.",
    )
    parser.add_argument("--genmanip-root", type=Path)
    parser.add_argument(
        "--runtime-renderer", type=Path, default=DEFAULT_RUNTIME_RENDERER
    )
    parser.add_argument("--runtime-preview-timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render and args.isaac_python is None:
        raise SystemExit("--isaac-python is required with --render")
    if args.render_runtime_preview and args.isaac_python is None:
        raise SystemExit("--isaac-python is required with --render-runtime-preview")
    if args.render_runtime_preview and args.genmanip_root is None:
        raise SystemExit("--genmanip-root is required with --render-runtime-preview")
    sources = resolve_scenario_source_bindings(args.bindings)
    selected = tuple(TASK_SPECS) if args.task == "all" else (args.task,)
    results: list[dict[str, Any]] = []
    for task_key in selected:
        spec_path = TASK_SPECS[task_key]
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"scenario spec must be a mapping: {spec_path}")
        spec = ScenarioSpec.from_mapping(raw)
        package = compile_scenario_package(spec, sources, args.out / spec.scenario_id)
        tabletop_placement = validate_scientific_workbench_tabletop_placement(
            package.package_root
        )
        export = export_genmanip_collected_package(package.package_root)
        ik_preflight_request = write_provisional_ik_preflight_request(package.package_root)
        package_closure = write_package_closure_evidence(package.package_root)
        states = _write_key_states(
            task_key=task_key,
            package_root=package.package_root,
            render=args.render,
            isaac_python=args.isaac_python,
            renderer=args.renderer,
            timeout_seconds=args.render_timeout,
        )
        if args.render_runtime_preview:
            # This is evidence only: overwrite the exported default request
            # with a hash-bound 1080p request, then let the native GenManip
            # renderer reset the scene and inject the standard Lift2 robot.
            write_genmanip_preview_request(
                export.output_dir, resolution=FINAL_RUNTIME_RENDER_RESOLUTION
            )
            run_genmanip_initial_preview(
                export.output_dir,
                args.isaac_python,
                args.runtime_renderer,
                args.genmanip_root,
                timeout_seconds=args.runtime_preview_timeout,
            )
        results.append(
            {
                "task_key": task_key,
                "scenario_id": spec.scenario_id,
                "status": "layout_validated_prototype",
                "package_root": str(package.package_root.resolve()),
                "genmanip_root": str(export.output_dir.resolve()),
                "active_score_ceiling": round(
                    sum(
                        item.weight
                        for item in spec.success.progress_rubric.items
                        if item.active
                    ),
                    6,
                ),
                "authored_key_states": len(states),
                "tabletop_placement_policy": tabletop_placement.overall_status,
                "package_closure": {
                    "status": "recorded",
                    "evidence_path": str(package_closure.resolve()),
                },
                "provisional_ik_preflight": {
                    "status": "requested",
                    "request_path": str(ik_preflight_request.resolve()),
                },
                "runtime_preview": (
                    "post_reset_pre_action_1080p"
                    if args.render_runtime_preview
                    else "not_run"
                ),
                "execution_status": "not_executed",
            }
        )

    readiness = {
        "schema_version": "scenario-forge-layout-prototype-readiness/v0.1",
        "source_catalog": "configs/task_catalogs/scientific_workbench_phase1.yaml",
        "source_document_revision": 1576,
        "source_sheet_revision": 564,
        "completed": results,
        "blocked": [
            {
                "task_key": "task6",
                "scenario_id": "scientific_workbench_place_vessel_on_stirrer",
                "status": "blocked_asset_identity",
                "reason": (
                    "The archive candidates labelled magnetic stirrer are visually "
                    "a laboratory scale and a stand-mounted heating apparatus, not "
                    "a qualified magnetic stirrer work surface."
                ),
                "required_resolution": (
                    "Provide a source-identifiable magnetic stirrer asset; do not "
                    "rename or reshape the rejected candidates in Scenario Forge."
                ),
            }
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "readiness.yaml").write_text(
        yaml.safe_dump(readiness, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    for result in results:
        print(f"{result['scenario_id']}: {result['package_root']}")
    print(f"readiness: {(args.out / 'readiness.yaml').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

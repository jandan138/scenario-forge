#!/usr/bin/env python3
"""Build Task 02 r10 four-fill dual-consumer packages from r9 rich_base."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview
from scenario_forge.artifacts.usd_handoff import (
    USDHandoffArchive,
    build_dual_consumer_variant_bundle,
    refresh_usd_handoff_archive,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
R8_SCRIPT = REPO_ROOT / "scripts/generate_scientific_workbench_task02_r8.py"
RENDERER_SCRIPT = REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
PHYSICS_SMOKE_SCRIPT = REPO_ROOT / "scripts/ebench/run_genmanip_zero_action_physics_smoke.py"
VR_OPEN_SMOKE_SCRIPT = REPO_ROOT / "scripts/ebench/open_vr_scene_smoke.py"
DEFAULT_R9 = (
    REPO_ROOT
    / "outputs/scientific_workbench_tasks_02_07_08_r9_20260816/rich_bases/"
    / "scientific_workbench_r9_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
)
DEFAULT_TRANSFER_ROOT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "task02_gpu_pbd_fill_sweep_20260817_r60/final_packages"
)
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task02_r10_fill_sweep_20260817"
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_GENMANIP_ROOT = Path("/cpfs/shared/simulation/zhuzihou/dev/GenManip")
DEFAULT_CUROBO_SRC = Path("/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src")
R9_SCENARIO_ID = (
    "scientific_workbench_r9_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry"
)
FILL_LEVEL_IDS = ("fill20", "fill40", "fill60", "fill80")
ARCHIVE_ID = "task02_r10_fill_sweep"
DEFAULT_VARIANT = "fill40"
HARD_RUNTIME_MARKERS = (
    "CUDA error",
    "illegal memory access",
    "failed to cook GPU-compatible mesh",
    "Non-GPU-compatible convex mesh",
    "Particles feature is only supported on GPU",
)


def _r8_module() -> Any:
    spec = importlib.util.spec_from_file_location("generate_task02_r8", R8_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {R8_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def r10_scenario_id(fill_level_id: str) -> str:
    return (
        "scientific_workbench_r10_task02_"
        f"{fill_level_id}_pour_cylinder_to_beaker__background_modern_wet_chemistry"
    )


def _percent_range(values: Sequence[float] | None) -> str:
    if not values:
        return "n/a"
    low = min(values) * 100.0
    high = max(values) * 100.0
    if abs(high - low) < 0.05:
        return f"{low:.1f}%"
    return f"{low:.2f}–{high:.2f}%"


def _package_readme_rows(packages: Mapping[str, Path]) -> list[str]:
    rows = [
        "| 液位 | 目标 | 实测 q95 | 粒子数 |",
        "| --- | ---: | --- | ---: |",
    ]
    for fill_id, package in packages.items():
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        profile = manifest.get("liquid_profile") or {}
        target = profile.get("target_settled_fill_ratio")
        measured = profile.get("measured_settled_fill_ratio_range")
        target_text = f"{float(target) * 100:.0f}%" if target is not None else "n/a"
        rows.append(
            f"| `{fill_id}` | {target_text} | {_percent_range(measured)} | "
            f"{manifest.get('particle_count')} |"
        )
    return rows


def _write_zip_readme(
    root: Path,
    *,
    packages: Mapping[str, Path],
    default_variant: str,
    visual_ready: str,
) -> None:
    fill80 = json.loads((packages["fill80"] / "manifest.json").read_text(encoding="utf-8")) if "fill80" in packages else {}
    fill80_range = _percent_range(
        (fill80.get("liquid_profile") or {}).get("measured_settled_fill_ratio_range")
    )
    lines = [
        f"# {ARCHIVE_ID}",
        "",
        "Task 02 r10 四档液位双端交付。每个 `variants/fillXX/` 都是独立目录，不能混用依赖。",
        f"默认打开 `{default_variant}`。",
        "",
        "Runtime: Isaac Sim 4.1 only.",
        f"`visual_ready={visual_ready}`。未跑四档固定机位时不要复用 r9 有机器人或 40% 液面的旧图。",
        "",
        "## 实测液面（ConvertAsset live_points_source_local_z_q95）",
        "",
        *_package_readme_rows(packages),
        "",
        f"fill80 目标 80%（±5%），实测 q95 为 {fill80_range or '75.09–75.16%'}，贴合格下限。",
        "",
        "## Claim 边界",
        "",
        "生产者 claim 只到 `gpu_pbd_dynamic_loaded_start` 与规定轨迹转移 50% 接收。",
        "不继承 r9 机器人 3/3，不声明 `robot_policy_success`、液体 metric 或 benchmark。",
        "`robot_policy_success=False`，`liquid_metrics_active=False`，`score_ceiling=0.60`。",
        "",
        "USD 不内嵌机器人；eBench/VR 运行时按各自 config 插入机器人。",
        "",
        "## 预览证据",
        "",
        "- 液位对比主图：`evidence/fill_sweep_closeup_quad.png`",
        "- 房间整体对比：`evidence/fill_sweep_overview_quad.png`",
        "",
        "| 液位 | eBench | VR |",
        "| --- | --- | --- |",
    ]
    for fill_id in packages:
        lines.append(
            f"| `{fill_id}` | `variants/{fill_id}/ebench/scene.usd` + "
            f"`variants/{fill_id}/ebench/config.yaml` | "
            f"`variants/{fill_id}/vr/scene.usd` + "
            f"`variants/{fill_id}/vr/task_config.py` |"
        )
    lines.append("")
    text = "\n".join(lines) + "\n"
    (root / "README_CN.md").write_text(text, encoding="utf-8")
    (root / "README.md").write_text(text, encoding="utf-8")


def _write_fill_sweep_quad(
    overviews: Mapping[str, Path],
    destination: Path,
    *,
    labels: Mapping[str, str],
    normalized_crop: tuple[float, float, float, float] | None = None,
) -> Path:
    from PIL import Image, ImageDraw

    ordered = [fill_id for fill_id in FILL_LEVEL_IDS if fill_id in overviews]
    images = [Image.open(overviews[fill_id]).convert("RGB") for fill_id in ordered]
    if normalized_crop is not None:
        left, top, right, bottom = normalized_crop
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError("normalized_crop must be within the unit image extent")
        images = [
            image.crop(
                (
                    round(image.width * left),
                    round(image.height * top),
                    round(image.width * right),
                    round(image.height * bottom),
                )
            )
            for image in images
        ]
    thumb_width = min(image.width for image in images)
    thumb_height = min(image.height for image in images)
    label_height = 48
    cols = 2
    rows = (len(images) + 1) // 2
    sheet = Image.new(
        "RGB",
        (thumb_width * cols, (thumb_height + label_height) * rows),
        (20, 20, 20),
    )
    draw = ImageDraw.Draw(sheet)
    for index, (fill_id, image) in enumerate(zip(ordered, images)):
        column = index % cols
        row = index // cols
        resized = image.resize((thumb_width, thumb_height))
        origin_x = column * thumb_width
        origin_y = row * (thumb_height + label_height)
        sheet.paste(resized, (origin_x, origin_y + label_height))
        draw.text(
            (origin_x + 16, origin_y + 12),
            labels.get(fill_id, fill_id),
            fill=(240, 240, 240),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    return destination


def maybe_render_overviews(
    packages: Mapping[str, Path],
    *,
    isaac_python: Path,
    genmanip_root: Path,
    curobo_src: Path,
    timeout_seconds: float = 900.0,
) -> dict[str, Path]:
    overviews: dict[str, Path] = {}
    if not isaac_python.is_file() or not genmanip_root.is_dir():
        return overviews
    r8 = _r8_module()
    runtime_paths = (curobo_src,) if curobo_src.is_dir() else ()
    for fill_id, package in packages.items():
        collected = package / "ebench"
        print(f"RENDER_START {fill_id}", flush=True)
        try:
            run_genmanip_initial_preview(
                collected,
                isaac_python,
                RENDERER_SCRIPT,
                genmanip_root,
                timeout_seconds=timeout_seconds,
                runtime_python_paths=runtime_paths,
            )
        except Exception as exc:
            print(f"RENDER_FAIL {fill_id}: {exc}", flush=True)
            continue
        overview = collected / "evidence/initial_scene/scene_overview.png"
        if overview.is_file():
            overviews[fill_id] = overview
            print(f"RENDER_OK {fill_id} {overview}", flush=True)
        else:
            print(f"RENDER_FAIL {fill_id}: missing scene_overview.png", flush=True)
        r8.refresh_hashes(package)
    return overviews


def _isaac_environment(
    isaac_python: Path, *, curobo_src: Path | None = None
) -> dict[str, str]:
    environment = dict(os.environ)
    if curobo_src is not None and curobo_src.is_dir():
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(curobo_src), *([inherited] if inherited else [])]
        )
    environment["PATH"] = os.pathsep.join(
        [str(isaac_python.parent), environment.get("PATH", "")]
    )
    prefix = isaac_python.parent.parent
    libraries = (
        prefix / "lib/python3.10/site-packages/torch/lib",
        prefix / "lib/python3.10/site-packages/nvidia/cuda_runtime/lib",
        prefix / "lib/python3.10/site-packages/isaacsim/extscache/omni.cuda.libs/bin",
    )
    inherited_ld = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [
            *[str(path) for path in libraries if path.is_dir()],
            *([inherited_ld] if inherited_ld else []),
        ]
    )
    return environment


def _run_worker(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    log_path: Path,
    timeout_seconds: float,
) -> None:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        shell=False,
    )
    combined = (completed.stdout or "") + (completed.stderr or "")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(combined, encoding="utf-8")
    blocking = [line for line in combined.splitlines() if any(item in line for item in HARD_RUNTIME_MARKERS)]
    if completed.returncode != 0 or blocking:
        detail = "\n".join(blocking[-10:]) if blocking else combined[-4000:]
        raise RuntimeError(
            f"runtime validation worker failed ({completed.returncode}): {detail}"
        )


def finalize_runtime_gates(package: Path) -> dict[str, Any]:
    package = package.resolve()
    physics_path = package / "ebench/evidence/product_smoke/report.json"
    vr_path = package / "vr/evidence/open_smoke/report.json"
    physics = json.loads(physics_path.read_text(encoding="utf-8"))
    vr = json.loads(vr_path.read_text(encoding="utf-8"))
    physics_pass = bool(
        physics.get("schema_version")
        == "scenario-forge-genmanip-zero-action-physics-smoke/v0.1"
        and physics.get("status") == "pass"
        and physics.get("physics_steps") == 960
        and physics.get("action_count") == 0
        and physics.get("runtime", {}).get("render_without_physics") is False
        and all(
            value == "pass"
            for value in physics.get("phases", {}).values()
        )
    )
    vr_pass = bool(
        vr.get("schema_version")
        in {
            "scenario-forge-vr-usd-open-smoke/v0.1",
            "scenario-forge-vr-usd-open-smoke/v0.2",
        }
        and vr.get("status") == "pass"
        and vr.get("physics_steps") == 0
        and vr.get("default_prim") == "/World"
    )
    if not physics_pass or not vr_pass:
        raise ValueError("runtime release gates are incomplete")
    evidence = package / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "product_smoke").mkdir(exist_ok=True)
    (evidence / "vr_open_smoke").mkdir(exist_ok=True)
    (evidence / "product_smoke/report.json").write_bytes(physics_path.read_bytes())
    (evidence / "vr_open_smoke/report.json").write_bytes(vr_path.read_bytes())
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["claims"]["ebench_load_reset_8s"] = True
    manifest["runtime_gates"] = {
        "ebench_zero_action_physics_8s": "pass",
        "vr_usd_open_isaac41": "pass",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _r8_module().refresh_hashes(package)
    return manifest["runtime_gates"]


def run_runtime_gates(
    packages: Mapping[str, Path],
    *,
    isaac_python: Path,
    genmanip_root: Path,
    curobo_src: Path,
    timeout_seconds: float = 900.0,
) -> None:
    environment = _isaac_environment(isaac_python, curobo_src=curobo_src)
    for fill_id, package in packages.items():
        physics_root = package / "ebench/evidence/product_smoke"
        print(f"PHYSICS_GATE_START {fill_id}", flush=True)
        _run_worker(
            (
                str(isaac_python),
                str(PHYSICS_SMOKE_SCRIPT),
                "--collected-root",
                str(package / "ebench"),
                "--genmanip-root",
                str(genmanip_root),
            ),
            cwd=REPO_ROOT,
            environment=environment,
            log_path=physics_root / "runtime.log",
            timeout_seconds=timeout_seconds,
        )
        print(f"VR_GATE_START {fill_id}", flush=True)
        _run_worker(
            (
                str(isaac_python),
                str(VR_OPEN_SMOKE_SCRIPT),
                "--vr-root",
                str(package / "vr"),
            ),
            cwd=REPO_ROOT,
            environment=environment,
            log_path=package / "vr/evidence/open_smoke/runtime.log",
            timeout_seconds=timeout_seconds,
        )
        finalize_runtime_gates(package)
        print(f"RUNTIME_GATES_OK {fill_id}", flush=True)


def finalize_r10_handoff(
    *,
    packages: Mapping[str, Path],
    output_dir: Path,
    fill_level_ids: Sequence[str],
    default_variant: str,
    archive_id: str,
    visual_ready: str,
    overviews: Mapping[str, Path] | None = None,
) -> USDHandoffArchive:
    overviews = dict(overviews or {})
    handoff_dir = output_dir / "handoff"
    archive = build_dual_consumer_variant_bundle(
        archive_id=archive_id,
        variants=tuple((fill_id, packages[fill_id]) for fill_id in fill_level_ids),
        default_variant=default_variant,
        output_dir=handoff_dir,
    )
    _write_zip_readme(
        archive.root,
        packages=packages,
        default_variant=default_variant,
        visual_ready=visual_ready,
    )
    closeups = {
        fill_id: package / "ebench/evidence/initial_scene/task_object_closeup.png"
        for fill_id, package in packages.items()
        if (package / "ebench/evidence/initial_scene/task_object_closeup.png").is_file()
    }
    if overviews or closeups:
        labels = {}
        for fill_id, package in packages.items():
            manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
            profile = manifest.get("liquid_profile") or {}
            target = profile.get("target_settled_fill_ratio")
            measured = _percent_range(profile.get("measured_settled_fill_ratio_range"))
            target_text = f"{float(target) * 100:.0f}%" if target is not None else "?"
            note = f"{fill_id}  target {target_text}  measured {measured}"
            if fill_id == "fill80":
                note += " (~75%)"
            labels[fill_id] = note
        evidence_dir = handoff_dir / "evidence"
        bundled_evidence = archive.root / "evidence"
        bundled_evidence.mkdir(parents=True, exist_ok=True)
        if closeups:
            closeup_quad = _write_fill_sweep_quad(
                closeups,
                evidence_dir / "fill_sweep_closeup_quad.png",
                labels=labels,
                normalized_crop=(0.33, 0.24, 0.60, 0.82),
            )
            (bundled_evidence / "fill_sweep_closeup_quad.png").write_bytes(
                closeup_quad.read_bytes()
            )
            # Compatibility alias: the primary quad is now the liquid-readable
            # closeup, not the room overview.
            (bundled_evidence / "fill_sweep_quad.png").write_bytes(
                closeup_quad.read_bytes()
            )
        if overviews:
            overview_quad = _write_fill_sweep_quad(
                overviews,
                evidence_dir / "fill_sweep_overview_quad.png",
                labels=labels,
            )
            (bundled_evidence / "fill_sweep_overview_quad.png").write_bytes(
                overview_quad.read_bytes()
            )
    refresh_usd_handoff_archive(archive)
    return archive


def build_r10_fill_sweep(
    *,
    r9_package: Path,
    transfer_packages: Mapping[str, Path],
    output_dir: Path,
    fill_level_ids: Sequence[str] = FILL_LEVEL_IDS,
    default_variant: str = DEFAULT_VARIANT,
    base_scenario_id: str = R9_SCENARIO_ID,
    archive_id: str = ARCHIVE_ID,
    supersedes: str = "r8.7",
    render_overviews: bool = False,
    isaac_python: Path = DEFAULT_ISAAC_PYTHON,
    genmanip_root: Path = DEFAULT_GENMANIP_ROOT,
    curobo_src: Path = DEFAULT_CUROBO_SRC,
    preview_timeout: float = 900.0,
    run_consumer_gates: bool = True,
) -> USDHandoffArchive:
    if default_variant not in fill_level_ids:
        raise ValueError("default_variant must be one of the fill-level ids")
    missing = [fill_id for fill_id in fill_level_ids if fill_id not in transfer_packages]
    if missing:
        raise ValueError("missing transfer packages: " + ", ".join(missing))

    r8 = _r8_module()
    output_dir = output_dir.resolve()
    packages_root = output_dir / "packages"
    packages: dict[str, Path] = {}
    for fill_id in fill_level_ids:
        package = r8.build(
            r7_package=r9_package,
            transfer_package=transfer_packages[fill_id],
            out=packages_root / fill_id,
            scenario_id=r10_scenario_id(fill_id),
            base_scenario_id=base_scenario_id,
            release="r10",
            supersedes=supersedes,
        )
        packages[fill_id] = package

    if run_consumer_gates:
        run_runtime_gates(
            packages,
            isaac_python=isaac_python,
            genmanip_root=genmanip_root,
            curobo_src=curobo_src,
            timeout_seconds=preview_timeout,
        )

    visual_ready = "not_run"
    overviews: dict[str, Path] = {}
    if render_overviews:
        try:
            overviews = maybe_render_overviews(
                packages,
                isaac_python=isaac_python,
                genmanip_root=genmanip_root,
                curobo_src=curobo_src,
                timeout_seconds=preview_timeout,
            )
            visual_ready = "pass" if len(overviews) == len(packages) else "not_run"
        except Exception as exc:
            visual_ready = "not_run"
            print(f"initial-scene preview skipped: {exc}")

    return finalize_r10_handoff(
        packages=packages,
        output_dir=output_dir,
        fill_level_ids=fill_level_ids,
        default_variant=default_variant,
        archive_id=archive_id,
        visual_ready=visual_ready,
        overviews=overviews,
    )


def _default_transfer_packages(root: Path) -> dict[str, Path]:
    return {fill_id: root / fill_id for fill_id in FILL_LEVEL_IDS}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7-package", "--r9-package", dest="r9_package", type=Path, default=DEFAULT_R9)
    parser.add_argument("--transfer-root", type=Path, default=DEFAULT_TRANSFER_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-scenario-id", default=R9_SCENARIO_ID)
    parser.add_argument("--release", default="r10")
    parser.add_argument("--supersedes", default="r8.7")
    parser.add_argument("--default-variant", default=DEFAULT_VARIANT)
    parser.add_argument("--isaac-python", type=Path, default=DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--genmanip-root", type=Path, default=DEFAULT_GENMANIP_ROOT)
    parser.add_argument("--curobo-src", type=Path, default=DEFAULT_CUROBO_SRC)
    parser.add_argument("--preview-timeout", type=float, default=900.0)
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--render-overviews", action="store_true")
    parser.add_argument("--render-existing", action="store_true")
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    if args.release != "r10":
        raise ValueError("r10 fill-sweep driver only emits release r10")
    render = args.render_overviews or (
        not args.skip_render and args.isaac_python.is_file() and args.genmanip_root.is_dir()
    )
    if args.render_existing or args.finalize_existing:
        packages = {
            fill_id: (args.out / "packages" / fill_id).resolve()
            for fill_id in FILL_LEVEL_IDS
        }
        missing = [fill_id for fill_id, path in packages.items() if not path.is_dir()]
        if missing:
            raise FileNotFoundError("missing generated packages: " + ", ".join(missing))
        run_runtime_gates(
            packages,
            isaac_python=args.isaac_python,
            genmanip_root=args.genmanip_root,
            curobo_src=args.curobo_src,
            timeout_seconds=args.preview_timeout,
        )
        overviews = {
            fill_id: package / "ebench/evidence/initial_scene/scene_overview.png"
            for fill_id, package in packages.items()
            if (package / "ebench/evidence/initial_scene/scene_overview.png").is_file()
        }
        if args.render_existing:
            overviews = maybe_render_overviews(
                packages,
                isaac_python=args.isaac_python,
                genmanip_root=args.genmanip_root,
                curobo_src=args.curobo_src,
                timeout_seconds=args.preview_timeout,
            )
        visual_ready = "pass" if len(overviews) == len(packages) else "not_run"
        archive = finalize_r10_handoff(
            packages=packages,
            output_dir=args.out.resolve(),
            fill_level_ids=FILL_LEVEL_IDS,
            default_variant=args.default_variant,
            archive_id=ARCHIVE_ID,
            visual_ready=visual_ready,
            overviews=overviews,
        )
        print(archive.zip_path)
        return 0
    archive = build_r10_fill_sweep(
        r9_package=args.r9_package,
        transfer_packages=_default_transfer_packages(args.transfer_root),
        output_dir=args.out,
        default_variant=args.default_variant,
        base_scenario_id=args.base_scenario_id,
        supersedes=args.supersedes,
        render_overviews=render,
        isaac_python=args.isaac_python,
        genmanip_root=args.genmanip_root,
        curobo_src=args.curobo_src,
        preview_timeout=args.preview_timeout,
    )
    print(archive.zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

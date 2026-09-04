#!/usr/bin/env python3
"""Generate Task 12 r2 from the Task 09 r16 fixed-base oven handoff."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_forge.validation.articulated_instance_layout import (  # noqa: E402
    validate_fixed_base_articulation_layout,
)
from scripts.generate_scientific_workbench_task12_oven_unload import (  # noqa: E402
    TASK_ID,
    _configure_scene,
    _metrics,
    _task,
)

R16_ROOT = (
    ROOT / "outputs/scientific_workbench_task09_r16_20260904/handoff/"
    "scientific_workbench_task09_r16_vr"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs/scientific_workbench_task12_oven_unload_dual_glassware_vr_r2_20260904/handoff"
)
HANDOFF_ID = "scientific_workbench_task12_oven_unload_dual_glassware_vr_r2"


@dataclass(frozen=True)
class Task12OvenUnloadR2Result:
    root: Path
    archive: Path
    manifest: Path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _task_config() -> str:
    return f'''# Merge this TASKS entry into VR Teleop constants/tasks.py.
TASKS = {{
    "{HANDOFF_ID}": {{
        "scene_usd_file_path": {{
            "scene1": str(_ASSETS_DIR / "scenes/{HANDOFF_ID}/scene.usd"),
        }},
        "obj_prim_list": [
            "/World/_scene/obj_oven_cart",
            "/World/_scene/obj_oven",
            "/World/_scene/obj_sample_beaker",
            "/World/_scene/obj_sample_conical_flask",
        ],
        "layout_randomization": {{
            "table": "table",
            "objects": [
                {{
                    "objs": [
                        "obj_oven_cart",
                        "obj_oven",
                        "obj_sample_beaker",
                        "obj_sample_conical_flask",
                    ],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }},
            ],
        }},
        "robot_cfg": {{
            "position": [0.85, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        }},
    }},
}}
'''


def build_handoff(
    output: Path = DEFAULT_OUTPUT,
    *,
    base_root: Path = R16_ROOT,
) -> Task12OvenUnloadR2Result:
    output = output.resolve()
    base_root = base_root.resolve()
    root = output / HANDOFF_ID
    if output.exists():
        raise FileExistsError(f"refusing to replace output: {output}")
    if not (base_root / "scene.usd").is_file():
        raise FileNotFoundError(base_root / "scene.usd")
    shutil.copytree(base_root, root)
    shutil.rmtree(root / "evidence")
    for stale in ("task_r16.json", "task_r15.json", "task_r14.json"):
        path = root / stale
        if path.exists():
            path.unlink()

    _configure_scene(root / "scene.usd")
    layout = validate_fixed_base_articulation_layout(root / "scene.usd", ["/World/obj_oven"])
    evidence = root / "evidence"
    evidence.mkdir()
    (evidence / "articulated_instance_layout_v2.json").write_text(
        json.dumps(layout, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "task_config.py").write_text(_task_config(), encoding="utf-8")
    (root / "task.yaml").write_text(
        yaml.safe_dump(_task(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "metrics.yaml").write_text(
        yaml.safe_dump(_metrics(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "task12.json").write_text(
        json.dumps(
            {
                "schema_version": "scenario-forge-task12-oven-unload-controls/v0.2",
                "door_joint": "obj_oven.Instance.Joints.DoorHinge",
                "shutdown_control": "obj_oven.Instance.ControlPanel.MainsSwitch.Rocker",
                "articulation_root": "obj_oven",
                "base_fixed_joint": "obj_oven.Instance.Joints.BaseFixed",
                "initial_process_state": "complete",
                "cart_scale_xyz": [1.0, 1.0, 0.7],
                "oven_xyz_m": [1.51, 0.0, 0.5285],
                "shelf": "obj_oven.Instance.Shelves.Shelf_0",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "README_CN.md").write_text(
        """# Scientific Workbench Task 12 r2 双器皿取出 VR

使用 Isaac Sim 4.1 打开 `scene.usd`。烧杯与锥形瓶位于烘箱下层；面板初始为
通电、65°C、加热完成，任务要求取出两件器皿、关门并关闭电源。

烘箱根 `/World/obj_oven` 是 fixed-base articulation，全部 link 保持在 identity
`Xform /World/obj_oven/Instance/...` 下；机身不是 kinematic，由
`Instance/Joints/BaseFixed` 固定。设备架 Z 高度缩放为 0.7，烘箱底面为
0.5285 m。场景包不声明机器人策略或 benchmark 成功。
""",
        encoding="utf-8",
    )

    inherited = json.loads((base_root / "manifest.json").read_text())
    manifest = {
        "schema_version": "scenario-forge-task12-oven-unload-vr/v0.2",
        "status": "static_built_runtime_pending",
        "entrypoints": {
            "scene": "scene.usd",
            "task_config": "task_config.py",
            "task": "task.yaml",
            "metrics": "metrics.yaml",
            "controls": "task12.json",
        },
        "source_evidence": inherited.get("source_evidence", {}),
        "claims": {
            "articulated_instance_layout_v2": True,
            "fixed_base_articulation": True,
            "instance_identity_xform": True,
            "all_links_nonkinematic": True,
            "dual_empty_sdf_vessels": True,
            "initial_process_state": "complete",
            "cart_height_scale": 0.7,
            "oven_scale": 1.0,
            "vr_only": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        },
        "lineage": {
            "base_handoff": "scientific_workbench_task09_r16_vr",
            "base_manifest_sha256": _sha(base_root / "manifest.json"),
            "task_id": TASK_ID,
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    archive = output / f"{HANDOFF_ID}.zip"
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=HANDOFF_ID)
    return Task12OvenUnloadR2Result(root, archive, manifest_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_handoff(args.output).archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

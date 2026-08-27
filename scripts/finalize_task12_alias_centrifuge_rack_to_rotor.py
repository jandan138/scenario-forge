#!/usr/bin/env python3
"""Finalize the Task 12 rack-to-rotor alias without robot-success promotion."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "outputs/scientific_workbench_task12_alias_centrifuge_rack_to_rotor_vr_r1_20260827"
RUNS = ("run_00.json", "run_01.json", "run_02.json")


def finalize(package: Path) -> Path:
    package = package.resolve()
    scene = package / "vr/scene.usd"
    scene_sha = sha256(scene.read_bytes()).hexdigest()
    static_dir = package / "vr/evidence/task12_alias_static"
    runs = [json.loads((static_dir / name).read_text()) for name in RUNS]
    if not all(
        run.get("status") == "pass"
        and run.get("scene_usd_sha256") == scene_sha
        and run.get("claims", {}).get("all_15ml_tubes_stable") is True
        and run.get("claims", {}).get("no_50ml_tubes") is True
        and run.get("claims", {}).get("scene_static_stability") is True
        for run in runs
    ):
        raise RuntimeError("three alias static runs must pass")
    oracle_path = package / "vr/evidence/task12_alias_oracle/report.json"
    oracle = json.loads(oracle_path.read_text())
    if (
        oracle.get("status") != "pass"
        or oracle.get("scene_usd_sha256") != scene_sha
        or oracle.get("claims", {}).get("robot_free_transfer_oracle_success") is not True
    ):
        raise RuntimeError("hash-bound alias robot-free oracle must pass")
    adapter = package / "adapters/ebench/genmanip"
    smoke = json.loads((adapter / "adapter_smoke.json").read_text())
    if smoke.get("status") != "pass":
        raise RuntimeError("alias adapter smoke must pass")
    render_path = package / "vr/evidence/initial_scene/render_manifest.json"
    review_path = package / "vr/evidence/initial_scene/visual_review.json"
    render = json.loads(render_path.read_text())
    review = json.loads(review_path.read_text())
    if (
        render.get("status") != "pass"
        or render.get("scene_usd_sha256") != scene_sha
        or review.get("verdict") != "pass"
        or review.get("scene_usd_sha256") != scene_sha
    ):
        raise RuntimeError("alias render/visual review must pass")
    required_views = {
        "scene_overview.png",
        "rack_target_closeup.png",
        "open_review_rotor_liquid_closeup.png",
        "inserted_review_rotor_liquid_closeup.png",
        "liquid_review_tube_liquid_closeup.png",
    }
    if not required_views.issubset(render.get("views", {})):
        raise RuntimeError("alias render evidence is missing required task views")
    static_summary = {
        "schema_version": "scenario-forge.task12-alias-static-qualification/v1",
        "status": "pass",
        "runtime": "isaac41",
        "scene_usd_sha256": scene_sha,
        "runs": list(RUNS),
        "claims": {
            "scene_static_stability": True,
            "all_15ml_tubes_stable": True,
            "no_50ml_tubes": True,
            "robot_policy_success": False,
            "task_success": False,
        },
    }
    (static_dir / "report.json").write_text(
        json.dumps(static_summary, indent=2, sort_keys=True) + "\n"
    )
    visual_path = package / "visual_liquid_manifest.json"
    visual = json.loads(visual_path.read_text())
    visual["status"] = "runtime_inspected_pass"
    visual["scene_usd_sha256"] = scene_sha
    visual_path.write_text(json.dumps(visual, indent=2, sort_keys=True) + "\n")
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "scene_qualified_robot_unvalidated"
    manifest["claims"].update(static_summary["claims"])
    manifest["claims"]["robot_free_transfer_oracle_success"] = True
    manifest["claims"]["adapter_load_smoke"] = True
    manifest["claims"]["manual_close_and_latch"] = False
    manifest["claims"]["robot_policy_success"] = False
    manifest["claims"]["task_success"] = False
    manifest["claims"]["benchmark_success"] = False
    manifest["runtime_qualification"] = {
        "scene_usd_sha256": scene_sha,
        "static": "vr/evidence/task12_alias_static/report.json",
        "robot_free_oracle": "vr/evidence/task12_alias_oracle/report.json",
        "render": "vr/evidence/initial_scene/render_manifest.json",
        "visual_review": "vr/evidence/initial_scene/visual_review.json",
        "adapter_smoke": "adapters/ebench/genmanip/adapter_smoke.json",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    args = parser.parse_args()
    print(finalize(args.package))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

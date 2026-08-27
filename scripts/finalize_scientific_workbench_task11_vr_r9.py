#!/usr/bin/env python3
"""Finalize Task 11 r9 scene qualification without robot-success promotion."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "outputs/scientific_workbench_task11_vr_r9_20260827"
RUNS = ("run_00.json", "run_01.json", "run_02.json")


def finalize(package: Path) -> Path:
    package = package.resolve()
    scene = package / "vr/scene.usd"
    scene_sha = sha256(scene.read_bytes()).hexdigest()
    static_dir = package / "vr/evidence/r9_static"
    runs = [json.loads((static_dir / name).read_text()) for name in RUNS]
    if not all(
        report.get("status") == "pass"
        and report.get("scene_usd_sha256") == scene_sha
        and report.get("claims", {}).get("scene_static_stability") is True
        and report.get("claims", {}).get("all_15ml_tubes_stable") is True
        and report.get("claims", {}).get("particle_free_scene") is True
        and report.get("claims", {}).get("visual_static_liquid_only") is True
        for report in runs
    ):
        raise RuntimeError("all three hash-bound r9 static runs must pass")
    mechanical_path = package / "vr/evidence/r9_mechanical/report.json"
    mechanical = json.loads(mechanical_path.read_text())
    if (
        mechanical.get("status") != "pass"
        or mechanical.get("scene_usd_sha256") != scene_sha
        or mechanical.get("claims", {}).get("robot_free_device_mechanics") is not True
    ):
        raise RuntimeError("hash-bound r9 device mechanics must pass")
    render_path = package / "vr/evidence/initial_scene/render_manifest.json"
    review_path = package / "vr/evidence/initial_scene/visual_review.json"
    render = json.loads(render_path.read_text())
    review = json.loads(review_path.read_text())
    if render.get("status") != "pass" or render.get("scene_usd_sha256") != scene_sha:
        raise RuntimeError("r9 render evidence is incomplete")
    required_views = {
        "scene_overview.png",
        "after_run_scene_overview.png",
        "tabletop_wide.png",
        "after_run_tabletop_wide.png",
        "open_review_rotor_liquid_closeup.png",
        "liquid_review_tube_liquid_closeup.png",
    }
    if not required_views.issubset(render.get("views", {})):
        raise RuntimeError("r9 render evidence is missing required views")
    if review.get("verdict") != "pass" or review.get("scene_usd_sha256") != scene_sha:
        raise RuntimeError("r9 visual review is incomplete")
    adapter_dir = package / "adapters/ebench/genmanip"
    adapter_smoke = json.loads((adapter_dir / "adapter_smoke.json").read_text())
    adapter_manifest = json.loads((adapter_dir / "package_manifest.json").read_text())
    if (
        adapter_smoke.get("status") != "pass"
        or adapter_manifest.get("source_scene_sha256") != scene_sha
    ):
        raise RuntimeError("r9 GenManip adapter smoke is incomplete")
    summary = {
        "schema_version": "scenario-forge.task11-r9-static-qualification.v1",
        "status": "pass",
        "runtime": "isaac41",
        "scene_usd_sha256": scene_sha,
        "runs": list(RUNS),
        "claims": {
            "scene_static_stability": True,
            "all_15ml_tubes_stable": True,
            "particle_free_scene": True,
            "visual_static_liquid_only": True,
            "robot_policy_success": False,
            "task11_success": False,
        },
    }
    summary_path = static_dir / "report.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    visual_path = package / "visual_liquid_manifest.json"
    visual = json.loads(visual_path.read_text())
    visual["status"] = "runtime_inspected_pass"
    visual["scene_usd_sha256"] = scene_sha
    visual_path.write_text(json.dumps(visual, indent=2, sort_keys=True) + "\n")
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "scene_qualified_robot_unvalidated"
    manifest["claims"].update(summary["claims"])
    manifest["claims"]["robot_free_device_mechanics"] = True
    manifest["claims"]["mechanical_oracle_success"] = False
    manifest["claims"]["canonical_task11_scripted_oracle_success"] = False
    manifest["claims"]["benchmark_success"] = False
    manifest["runtime_qualification"] = {
        "scene_usd_sha256": scene_sha,
        "static": "vr/evidence/r9_static/report.json",
        "device_mechanics": "vr/evidence/r9_mechanical/report.json",
        "render": "vr/evidence/initial_scene/render_manifest.json",
        "visual_review": "vr/evidence/initial_scene/visual_review.json",
        "genmanip_adapter": "adapters/ebench/genmanip/adapter_smoke.json",
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

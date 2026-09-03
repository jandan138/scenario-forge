#!/usr/bin/env python3
"""Finalize the preheated water-bath tube-heating VR candidate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def finalize(root: Path) -> Path:
    from pxr import UsdUtils

    root = root.resolve()
    runtime = root / "vr/evidence/runtime"
    static_reports = [runtime / f"static_run_{index:02d}.json" for index in range(1, 4)]
    trajectory_reports = [
        runtime / f"trajectory_run_{index:02d}.json" for index in range(1, 4)
    ]
    render = runtime / "render_manifest.json"
    visual_review = root / "vr/evidence/initial_scene/visual_review.json"
    materialization = root / "vr/object_materialization.json"
    for path in [*static_reports, *trajectory_reports, render, visual_review, materialization]:
        if json.loads(path.read_text()).get("status") != "pass":
            raise ValueError(f"water-bath final evidence did not pass: {path}")

    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(
        str(root / "vr/scene.usd")
    )
    external = [
        str(path)
        for path in assets
        if str(path).startswith("/") and not str(path).startswith(str(root) + "/")
    ]
    closure = {
        "schema_version": "scenario-forge-package-closure/v0.1",
        "status": "pass" if not unresolved and not external else "blocked",
        "layer_count": len(layers),
        "asset_count": len(assets),
        "unresolved": [str(path) for path in unresolved],
        "external_absolute_assets": external,
    }
    closure_path = runtime / "package_closure.json"
    closure_path.write_text(json.dumps(closure, indent=2, sort_keys=True) + "\n")
    if closure["status"] != "pass":
        raise ValueError("water-bath dependency closure blocked")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "vr_action_collection_candidate"
    manifest["claims"].update(
        {
            "scene_static_stability": True,
            "robot_free_immersion_trajectory": True,
            "visual_evidence_ready": True,
            "vr_action_collection_ready": False,
        }
    )
    manifest["runtime_evidence"] = {
        "static_runs": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha(path),
            }
            for path in static_reports
        ],
        "trajectory_runs": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha(path),
            }
            for path in trajectory_reports
        ],
        "state_capture": {
            "path": "vr/evidence/runtime/trajectory_states_run_01.npz",
            "sha256": _sha(runtime / "trajectory_states_run_01.npz"),
        },
        "render_manifest": {
            "path": render.relative_to(root).as_posix(),
            "sha256": _sha(render),
        },
        "visual_review": {
            "path": visual_review.relative_to(root).as_posix(),
            "sha256": _sha(visual_review),
        },
        "object_materialization": {
            "path": materialization.relative_to(root).as_posix(),
            "sha256": _sha(materialization),
        },
        "package_closure": {
            "path": closure_path.relative_to(root).as_posix(),
            "sha256": _sha(closure_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    handoff = root / "handoff"
    handoff.mkdir(exist_ok=True)
    archive = handoff / "scientific_workbench_water_bath_tube_heat_vr_r1.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(root.rglob("*")):
            if path.is_file() and handoff not in path.parents:
                target.write(path, path.relative_to(root))
    archive.with_suffix(".zip.sha256").write_text(
        f"{_sha(archive)}  {archive.name}\n"
    )
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(finalize(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Finalize the traditional titration VR handoff from retained evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Sequence
import zipfile


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if len(args.report) != 3:
        raise ValueError("finalization requires exactly three cold-start reports")
    reports = [json.loads(path.read_text()) for path in args.report]
    if any(report.get("status") != "pass" for report in reports):
        raise ValueError("all cold-start reports must pass")
    render_manifest = json.loads((root / "evidence/initial_scene/render_manifest.json").read_text())
    if render_manifest.get("status") != "pass":
        raise ValueError("render evidence must pass")
    if (root / ".titration_render_scene.usda").exists():
        raise ValueError("temporary render scene must not enter the handoff")

    runtime = root / "evidence/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    retained = []
    for index, source in enumerate(args.report, 1):
        destination = runtime / f"cold_start_{index}.json"
        shutil.copy2(source, destination)
        retained.append(
            {
                "path": destination.relative_to(root).as_posix(),
                "sha256": _sha(destination),
            }
        )

    from pxr import UsdUtils

    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(root / "scene.usd"))
    resolved = sorted(
        {Path(layer.realPath).resolve() for layer in layers if getattr(layer, "realPath", "")}
        | {Path(str(asset)).resolve() for asset in assets}
    )
    escapes = [str(path) for path in resolved if root not in path.parents and path != root]
    closure = {
        "schema_version": "scenario-forge-package-closure/v0.1",
        "status": "pass" if not unresolved and not escapes else "blocked",
        "unresolved": sorted(str(item) for item in unresolved),
        "outside_package": escapes,
        "dependency_count": len(resolved),
        "dependencies": [
            path.relative_to(root).as_posix() for path in resolved if root in path.parents
        ],
    }
    (root / "evidence/package_closure.json").write_text(
        json.dumps(closure, indent=2, sort_keys=True) + "\n"
    )
    if closure["status"] != "pass":
        raise ValueError(f"package dependency closure blocked: {closure}")

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "pass"
    manifest["claims"].update(
        {
            "scene_static_validation": True,
            "scene_cold_start_passes": 3,
            "materialized_state_machine_success_path": True,
            "tip_receiver_alignment_verified": True,
            "robot_policy_success": False,
            "benchmark_success": False,
        }
    )
    manifest["runtime_evidence"] = retained
    manifest["render_evidence"] = "evidence/initial_scene/render_manifest.json"
    manifest["package_closure"] = "evidence/package_closure.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    archive = root.parent / f"{root.name}.zip"
    shutil.make_archive(
        str(archive.with_suffix("")), "zip", root_dir=root.parent, base_dir=root.name
    )
    with zipfile.ZipFile(archive) as handle:
        bad_member = handle.testzip()
    if bad_member is not None:
        raise ValueError(f"ZIP CRC failed at {bad_member}")
    (archive.with_suffix(".zip.sha256")).write_text(
        f"{_sha(archive)}  {archive.name}\n", encoding="utf-8"
    )
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Finalize the Task 09 r15 Instance-layout VR handoff."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scenario_forge.validation.articulated_instance_layout import (  # noqa: E402
    validate_articulated_instance_layout,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def finalize(root: Path) -> Path:
    from pxr import UsdUtils

    root = root.resolve()
    static = root / "evidence/runtime/static_play_report.json"
    render = root / "evidence/initial_scene/render_manifest.json"
    review = root / "evidence/initial_scene/visual_review.json"
    for path in (static, render, review):
        if json.loads(path.read_text()).get("status") != "pass":
            raise ValueError(f"r15 evidence did not pass: {path}")
    layout = validate_articulated_instance_layout(
        root / "scene.usd", ["/World/obj_oven"]
    )
    layout_path = root / "evidence/articulated_instance_layout.json"
    layout_path.write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n")
    layers, dependencies, unresolved = UsdUtils.ComputeAllDependencies(
        str(root / "scene.usd")
    )
    external = [
        str(path)
        for path in dependencies
        if str(path).startswith("/") and not str(path).startswith(str(root) + "/")
    ]
    closure = {
        "schema_version": "scenario-forge-package-closure/v0.1",
        "status": "pass" if not unresolved and not external else "blocked",
        "layer_count": len(layers),
        "asset_count": len(dependencies),
        "unresolved": [str(path) for path in unresolved],
        "external_absolute_assets": external,
    }
    closure_path = root / "evidence/package_closure.json"
    closure_path.write_text(json.dumps(closure, indent=2, sort_keys=True) + "\n")
    if closure["status"] != "pass":
        raise ValueError("r15 dependency closure blocked")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "isaac41_runtime_complete"
    manifest["runtime_evidence"] = {
        "static_play": "evidence/runtime/static_play_report.json",
        "static_play_sha256": _sha(static),
        "render_manifest": "evidence/initial_scene/render_manifest.json",
        "render_manifest_sha256": _sha(render),
        "visual_review": "evidence/initial_scene/visual_review.json",
        "visual_review_sha256": _sha(review),
        "articulated_instance_layout": "evidence/articulated_instance_layout.json",
        "articulated_instance_layout_sha256": _sha(layout_path),
        "package_closure": "evidence/package_closure.json",
        "package_closure_sha256": _sha(closure_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    output = root.parent
    archive = output / (root.name + ".zip")
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output, base_dir=root.name)
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        _sha(archive) + "  " + archive.name + "\n"
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

#!/usr/bin/env python3
"""Build an unvalidated Task 02 package with the 0819 colleague collision profile."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Mapping

import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT, _ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import scripts.generate_scientific_workbench_task02_r10_2 as r10_2  # noqa: E402
import scripts.generate_scientific_workbench_task02_r10_3 as r10_3  # noqa: E402
import scripts.generate_scientific_workbench_task02_r8 as r8  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
FILL_IDS = ("fill20", "fill40", "fill60", "fill80")
DEFAULT_SOURCE = (
    REPO_ROOT
    / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/packages"
)
DEFAULT_OUT = (
    REPO_ROOT
    / "outputs/scientific_workbench_task02_r10_3_colleague_collision_20260819"
)
COLLEAGUE_USD = REPO_ROOT / "external_artifacts/incoming/test_0819_liquid.usd"
COLLEAGUE_USD_SHA256 = (
    "d68e02dc93f01cb3011fa6fdb820472d2be09fab2323f667fc3aec3b36019f8b"
)
ARCHIVE_ID = "task02_r10_3_colleague_collision_unvalidated"
OVERLAY_NAME = "experimental_colleague_collision.usda"
RACK_XYZ = (-0.8845, -0.17, 0.755)
ROD_XYZ = (-0.8845, -0.17, 0.77243)

SDF_MESHES = {
    "graduated_cylinder": (
        ("Hollow_Body", "Hollow_Body_Mesh_002"),
        ("Thickened_Rim", "Torus_002"),
    ),
    "beaker": (
        ("Beaker_Hollow_Body", "Beaker_Hollow_Body_Mesh"),
        ("Rolled_Rim", "Torus"),
    ),
}
HULL_MESHES = {
    "graduated_cylinder": (
        ("Hex_Base", "Cylinder_004"),
        ("Base_Connector", "Cylinder_005"),
        ("Closed_Inner_Bottom", "Cylinder_006"),
        ("Pour_Spout", "Pour_Spout_Mesh_002"),
    ),
    "beaker": (("Pour_Spout", "Pour_Spout_Mesh"),),
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _mesh_over(component: str, mesh: str, *, approximation: str) -> str:
    if approximation == "sdf":
        schemas = (
            '"PhysicsCollisionAPI", "PhysxCollisionAPI", '
            '"PhysicsMeshCollisionAPI", "PhysxSDFMeshCollisionAPI"'
        )
        attributes = """uniform token physics:approximation = "sdf"
                            uint physxSDFMeshCollision:sdfResolution = 256
                            uint physxSDFMeshCollision:sdfSubgridResolution = 6
                            float physxSDFMeshCollision:sdfMargin = 0.01
                            float physxSDFMeshCollision:sdfNarrowBandThickness = 0.01
                            token physxSDFMeshCollision:sdfBitsPerSubgridPixel = "BitsPerPixel16"
                            bool physxSDFMeshCollision:sdfEnableRemeshing = 0
                            float physxSDFMeshCollision:sdfTriangleCountReductionFactor = 1"""
    else:
        schemas = (
            '"PhysicsCollisionAPI", "PhysxCollisionAPI", '
            '"PhysicsMeshCollisionAPI", "PhysxConvexHullCollisionAPI"'
        )
        attributes = """uniform token physics:approximation = "convexHull"
                            uint physxConvexHullCollision:hullVertexLimit = 64
                            float physxConvexHullCollision:minThickness = 0.001"""
    return f'''                    over "{component}"
                    {{
                        over "{mesh}" (
                            prepend apiSchemas = [{schemas}]
                        )
                        {{
                            bool physics:collisionEnabled = 1
                            {attributes}
                        }}
                    }}
'''


def _vessel_over(name: str, *, prefix: str) -> str:
    blocks = []
    for component, mesh in SDF_MESHES[name]:
        blocks.append(_mesh_over(component, mesh, approximation="sdf"))
    for component, mesh in HULL_MESHES[name]:
        blocks.append(_mesh_over(component, mesh, approximation="convexHull"))
    return f'''        over "{prefix}{name}"
        {{
            over "__aan_pbd_collision_proxy"
            {{
                over "PBD_Unified_Vessel_Mesh"
                {{
                    bool physics:collisionEnabled = 0
                }}
            }}
            over "Visual"
            {{
                over "Source"
                {{
{''.join(blocks)}                }}
            }}
        }}
'''


def collision_override_usda(*, ebench: bool) -> str:
    """Return the exact scene-level profile copied from test_0819_liquid.usd."""
    prefix = "obj_obj_" if ebench else "obj_"
    inner = f'''        over "fluid_runtime"
        {{
            over "ParticleSystem"
            {{
                float restOffset = 0.009
                float physxParticleIsosurface:gridSmoothingRadius = 0.005
            }}
        }}
{_vessel_over("graduated_cylinder", prefix=prefix)}{_vessel_over("beaker", prefix=prefix)}'''
    if ebench:
        inner = '    over "_scene"\n    {\n' + inner + "    }\n"
    return '\n# Experimental profile transcribed from test_0819_liquid.usd.\nover "World"\n{\n' + inner + "}\n"


def _install_overlay(scene_path: Path, *, ebench: bool) -> Path:
    """Author the profile in a separate layer and compose it into one scene."""
    original = scene_path.read_text(encoding="utf-8")
    asset = f"@{OVERLAY_NAME}@"
    if asset in original:
        raise ValueError(f"collision profile already composed in {scene_path}")
    if "subLayers = [" in original:
        updated = original.replace("subLayers = [", f"subLayers = [{asset}, ", 1)
    else:
        marker = "\n)\n"
        if marker not in original:
            raise ValueError(f"scene metadata block is missing: {scene_path}")
        updated = original.replace(
            marker, f"\n    subLayers = [{asset}]\n)\n", 1
        )
    scene_path.write_text(updated, encoding="utf-8")
    overlay = scene_path.parent / OVERLAY_NAME
    overlay.write_text(
        "#usda 1.0\n" + collision_override_usda(ebench=ebench),
        encoding="utf-8",
    )
    return overlay


def _apply_profile(destination: Path) -> None:
    _install_overlay(destination / "ebench/scene.usd", ebench=True)
    inner_scenes = tuple(
        destination.glob(
            "ebench/assets/scene_usds/scenario_forge/*/source_bundle/r7_scene/scene.usda"
        )
    )
    if len(inner_scenes) != 1:
        raise ValueError("expected exactly one eBench collected scene")
    _install_overlay(inner_scenes[0], ebench=True)
    _install_overlay(destination / "vr/scene.usd", ebench=False)


def _mark_unvalidated(destination: Path) -> None:
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "release": "r10.3-colleague-collision-unvalidated",
            "supersedes": "r10.2",
            "status": "unvalidated_experimental",
            "experimental_collision_profile": {
                "status": "transcribed_not_runtime_validated",
                "source_usd": str(COLLEAGUE_USD),
                "source_usd_sha256": COLLEAGUE_USD_SHA256,
                "particle_system": {
                    "rest_offset_m": 0.009,
                    "isosurface_grid_smoothing_radius_m": 0.005,
                },
                "vessel_collision": {
                    "sdf_mesh_count": 4,
                    "convex_hull_mesh_count": 5,
                    "legacy_unified_proxy_enabled": False,
                },
                "validation": "not_run_by_request",
                "claim_boundary": (
                    "Temporary scene-level reproduction only; this is not a new "
                    "ConvertAsset admission or runtime-success claim."
                ),
            },
        }
    )
    manifest.pop("runtime_gates", None)
    manifest.pop("visual_review", None)
    manifest.setdefault("claims", {})["ebench_load_reset_8s"] = "not_run"
    manifest["context_fixture"].update(
        {
            "rack_xyz_m": list(RACK_XYZ),
            "rod_xyz_m": list(ROD_XYZ),
            "placement": "left_edge_1cm_nominal_margin",
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package_manifest = destination / "ebench/package_manifest.json"
    value = json.loads(package_manifest.read_text(encoding="utf-8"))
    value["release_status"] = "unvalidated_experimental"
    package_manifest.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    parity_path = destination / "vr/parity_manifest.json"
    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    parity.update(
        {
            "release": "r10.3-colleague-collision-unvalidated",
            "status": "unvalidated_experimental",
            "runtime_validation": "not_run_by_request",
        }
    )
    parity.setdefault("artifacts", {})["scene_usd"] = {
        "path": "scene.usd",
        "sha256": "sha256:" + _sha(destination / "vr/scene.usd"),
    }
    parity_path.write_text(
        json.dumps(parity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    r10_2._remove_stale_runtime_evidence(destination)
    r8.refresh_hashes(destination)


def upgrade_variant(source: Path, destination: Path) -> Path:
    old_rack, old_rod = r10_3.RACK_XYZ, r10_3.ROD_XYZ
    try:
        r10_3.RACK_XYZ, r10_3.ROD_XYZ = RACK_XYZ, ROD_XYZ
        r10_3.upgrade_variant(source, destination, refresh_preview_request=False)
    finally:
        r10_3.RACK_XYZ, r10_3.ROD_XYZ = old_rack, old_rod
    _apply_profile(destination)
    _mark_unvalidated(destination)
    return destination


def build_packages(source_root: Path, output_dir: Path) -> dict[str, Path]:
    if not COLLEAGUE_USD.is_file() or _sha(COLLEAGUE_USD) != COLLEAGUE_USD_SHA256:
        raise ValueError("test_0819_liquid.usd is missing or no longer matches the reviewed file")
    return {
        fill_id: upgrade_variant(
            source_root / fill_id, output_dir / "packages" / fill_id
        )
        for fill_id in FILL_IDS
    }


def _write_readme(root: Path) -> None:
    root.joinpath("README_CN.md").write_text(
        """# Task 02 r10.3 同事碰撞参数复刻版（未验证）

这是按临时需求先交付的四档双端包。它在 r10.2 最新玻璃材质与原液体初值之上：

- 把玻璃棒和架子移到桌面左边，静态边距约 1 cm；VR 的整体 local XY ±0.01 m 随机化仍保留。
- 完整复刻 `test_0819_liquid.usd` 的粒子 `restOffset=0.009 m` 与 isosurface smoothing `0.005 m`。
- 关闭原统一 vessel proxy，量筒/烧杯视觉组件按同事方案使用 4 个 SDF + 5 个 convexHull collider。

本版按要求没有跑 Isaac、机器人或渲染验证，状态明确为 `unvalidated_experimental`。
默认使用 `fill40`；也可选择 `fill20`、`fill60`、`fill80`。每档入口：

- eBench：`variants/fillXX/ebench/scene.usd` + `config.yaml`
- VR：`variants/fillXX/vr/scene.usd` + `task_config.py`

请整包解压后使用，不要单独拷贝 USD。这个包只证明参数被完整写入，不声明液体、碰撞、机器人或 benchmark 成功。
""",
        encoding="utf-8",
    )


def build_handoff(packages: Mapping[str, Path], output_dir: Path) -> Path:
    root = output_dir / "handoff" / ARCHIVE_ID
    if root.exists():
        shutil.rmtree(root)
    for fill_id, package in packages.items():
        target = root / "variants" / fill_id
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package / "ebench", target / "ebench")
        shutil.copytree(package / "vr", target / "vr")
        shutil.copy2(package / "manifest.json", target / "manifest.json")
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "scenario-forge-dual-consumer-variant-handoff/v0.2",
                "archive_id": ARCHIVE_ID,
                "release": "r10.3-colleague-collision-unvalidated",
                "status": "unvalidated_experimental",
                "default_variant": "fill40",
                "variants": list(FILL_IDS),
                "source_usd_sha256": COLLEAGUE_USD_SHA256,
                "runtime_validation": "not_run_by_request",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _write_readme(root)
    r10_3._write_checksums(root)
    destination = output_dir / "handoff" / f"{ARCHIVE_ID}.zip"
    r10_2._zip_tree(root, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    packages = build_packages(args.source_root, args.out)
    print(build_handoff(packages, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

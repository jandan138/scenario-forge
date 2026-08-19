#!/usr/bin/env python3
"""Add the admitted glass-rod rack assembly to all Task 02 r10.2 fills."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

import yaml

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
for _path in (_BOOTSTRAP_ROOT, _BOOTSTRAP_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import scripts.generate_scientific_workbench_r10_1 as r10_1  # noqa: E402
import scripts.generate_scientific_workbench_task02_r10_2 as r10_2  # noqa: E402
import scripts.generate_scientific_workbench_task02_r10_fill_sweep as r10  # noqa: E402
import scripts.generate_scientific_workbench_task02_r8 as r8  # noqa: E402
from scenario_forge.adapters.ebench.preview import (  # noqa: E402
    write_genmanip_preview_request,
)
from scenario_forge.artifacts.usd_handoff import (  # noqa: E402
    refresh_usd_handoff_archive,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FILL_IDS = ("fill20", "fill40", "fill60", "fill80")
DEFAULT_SOURCE = (
    REPO_ROOT
    / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819/packages"
)
DEFAULT_FIXTURE = (
    REPO_ROOT
    / "outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/"
    "task07/teaching_research"
)
DEFAULT_OUT = (
    REPO_ROOT / "outputs/scientific_workbench_task02_r10_3_fill_sweep_20260819"
)
ARCHIVE_ID = "task02_r10_3_fill_sweep"
PREVALIDATION_ARCHIVE_ID = ARCHIVE_ID + "_prevalidation"
RACK_XYZ = (-0.42, -0.17, 0.755)
ROD_XYZ = (-0.42, -0.17, 0.77243)
FIXTURE_GROUP = "task02_glass_rod_rack_assembly"
ROD_ASSET_ID = "scientific_workbench_r7_glass_stirring_rod_300mm"
RACK_ASSET_ID = "scientific_workbench_r10_1_acrylic_spoon_rack"
FIXTURE_ASSET_IDS = (ROD_ASSET_ID, RACK_ASSET_ID)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _single(paths: Sequence[Path], *, label: str) -> Path:
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {label}; found {len(paths)}")
    return paths[0]


def _copytree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _fixture_paths(fixture_package: Path) -> dict[str, Path]:
    fixture_package = fixture_package.resolve()
    vr_objects = fixture_package / "adapters/vr_teleop/deps/objects"
    ebench_scenario = _single(
        list(
            (
                fixture_package
                / "adapters/ebench/genmanip/assets/scene_usds/scenario_forge"
            ).glob("*/source_bundle")
        ),
        label="Task 07 eBench source bundle",
    )
    manifest = fixture_package / "adapters/ebench/genmanip/package_manifest.json"
    required = (
        vr_objects / "obj_glass_rod",
        vr_objects / "obj_acrylic_rod_rack",
        ebench_scenario / ROD_ASSET_ID,
        ebench_scenario / RACK_ASSET_ID,
        manifest,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ValueError("fixture package is incomplete: " + ", ".join(missing))
    return {
        "vr_objects": vr_objects,
        "ebench_source_bundle": ebench_scenario,
        "ebench_manifest": manifest,
    }


def _copy_fixture_closures(destination: Path, fixture_package: Path) -> None:
    fixture = _fixture_paths(fixture_package)
    vr_objects = destination / "vr/deps/objects"
    for object_id in ("obj_glass_rod", "obj_acrylic_rod_rack"):
        _copytree(
            fixture["vr_objects"] / object_id,
            vr_objects / object_id,
        )
    target_bundle = _single(
        list(
            (
                destination / "ebench/assets/scene_usds/scenario_forge"
            ).glob("*/source_bundle/r7_scene/source_bundle")
        ),
        label="Task 02 eBench r7 source bundle",
    )
    for asset_id in FIXTURE_ASSET_IDS:
        _copytree(
            fixture["ebench_source_bundle"] / asset_id,
            target_bundle / asset_id,
        )


def _fixture_usd_blocks(*, vr: bool) -> str:
    indent = "    " if vr else "        "
    rod_reference = (
        "deps/objects/obj_glass_rod/asset.usd"
        if vr
        else f"source_bundle/{ROD_ASSET_ID}/asset.usd"
    )
    rack_reference = (
        "deps/objects/obj_acrylic_rod_rack/asset.usd"
        if vr
        else f"source_bundle/{RACK_ASSET_ID}/asset.usd"
    )
    rod_name = "obj_glass_rod" if vr else "obj_obj_glass_rod"
    rack_name = "obj_acrylic_rod_rack" if vr else "obj_obj_acrylic_rod_rack"
    return f'''{indent}def Xform "{rod_name}" (
{indent}    prepend references = @{rod_reference}@</World/GlassStirringRod>
{indent})
{indent}{{
{indent}    double3 xformOp:translate = ({ROD_XYZ[0]}, {ROD_XYZ[1]}, {ROD_XYZ[2]})
{indent}    quatd xformOp:orient = (1, 0, 0, 0)
{indent}    double3 xformOp:scale = (1, 1, 1)
{indent}    uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
{indent}}}

{indent}def Xform "{rack_name}" (
{indent}    prepend references = @{rack_reference}@</World/AcrylicSpoonRack>
{indent})
{indent}{{
{indent}    double3 xformOp:translate = ({RACK_XYZ[0]}, {RACK_XYZ[1]}, {RACK_XYZ[2]})
{indent}    quatd xformOp:orient = (1, 0, 0, 0)
{indent}    double3 xformOp:scale = (1, 1, 1)
{indent}    uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
{indent}}}

'''


def _inject_vr_scene(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'def Xform "obj_glass_rod"' in text:
        raise ValueError("VR scene already contains the r10.3 fixture")
    marker = '    def DomeLight "vr_direct_open_light"'
    if text.count(marker) != 1:
        raise ValueError("VR direct-open light insertion marker is ambiguous")
    path.write_text(
        text.replace(marker, _fixture_usd_blocks(vr=True) + marker),
        encoding="utf-8",
    )


def _inject_ebench_scene(destination: Path) -> None:
    scene = _single(
        list(
            (
                destination / "ebench/assets/scene_usds/scenario_forge"
            ).glob("*/source_bundle/r7_scene/scene.usda")
        ),
        label="Task 02 eBench r7 scene",
    )
    text = scene.read_text(encoding="utf-8")
    if 'def Xform "obj_obj_glass_rod"' in text:
        raise ValueError("eBench scene already contains the r10.3 fixture")
    markers = (
        "    }\n}\n\ndef PhysicsScene",
        "    }\n}\ndef PhysicsScene",
    )
    marker = next((item for item in markers if text.count(item) == 1), None)
    if marker is None:
        raise ValueError("eBench fixture insertion marker is ambiguous")
    replacement = _fixture_usd_blocks(vr=False) + marker
    scene.write_text(text.replace(marker, replacement), encoding="utf-8")


def task02_vr_config(*, scenario_id: str, particle_count: int) -> str:
    objects = (*r10_1.TASK02_OBJECTS, "obj_glass_rod", "obj_acrylic_rod_rack")
    config = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in objects],
        "layout_randomization": {
            "table": "table",
            "objects": [
                r10_1._local_group(("obj_graduated_cylinder", "fluid_runtime")),
                *[
                    r10_1._local_group((name,))
                    for name in r10_1.TASK02_OBJECTS[1:]
                ],
                r10_1._local_group(
                    ("obj_glass_rod", "obj_acrylic_rod_rack")
                ),
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            **r10_1.physx_scene_config(),
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "TimeStepsPerSecond": 120,
        },
        "prototype_fluid": {
            "status": "qualified_dynamic_loaded_start",
            "particle_count": particle_count,
            "liquid_metrics_active": False,
            "inactive_reason": "vr_liquid_metric_adapter_not_qualified",
            "producer_claim": "gpu_pbd_dynamic_loaded_start",
        },
    }
    body = r10_1._python_literal(config, indent=0).replace(
        '"__SCENE_PATH__"',
        f'str(_ASSETS_DIR / "scenes/{scenario_id}/scene.usd")',
    )
    return (
        "# Merge this TASKS entry into the VR teleop task registry.\n"
        f"TASKS = {{\n    {scenario_id!r}: {body},\n}}\n"
    )


def _context_objects() -> list[dict[str, Any]]:
    common = {
        "role": "context_prop",
        "metadata": {
            "metric_participation": "none",
            "dressing_release": "r10.3",
            "vr_randomization_group": FIXTURE_GROUP,
        },
    }
    rod = deepcopy(common)
    rod.update(
        {
            "id": "obj_glass_rod",
            "asset_id": ROD_ASSET_ID,
            "source_prim_path": "/World/GlassStirringRod",
            "pose": {"xyz": list(ROD_XYZ), "wxyz": [1.0, 0.0, 0.0, 0.0]},
        }
    )
    rod["metadata"].update(
        {
            "pose_source": "obj_acrylic_rod_rack.middle_socket_04_inserted_bottom",
            "rack_socket_index": 4,
        }
    )
    rack = deepcopy(common)
    rack.update(
        {
            "id": "obj_acrylic_rod_rack",
            "asset_id": RACK_ASSET_ID,
            "source_prim_path": "/World/AcrylicSpoonRack",
            "pose": {"xyz": list(RACK_XYZ), "wxyz": [1.0, 0.0, 0.0, 0.0]},
        }
    )
    rack["metadata"]["interaction_role"] = "background_stirring_tool_fixture"
    return [rod, rack]


def _update_semantics(destination: Path) -> None:
    path = destination / "scenario_r7_semantics.yaml"
    semantics = yaml.safe_load(path.read_text(encoding="utf-8"))
    existing = {item["id"] for item in semantics["objects"]}
    if existing & {"obj_glass_rod", "obj_acrylic_rod_rack"}:
        raise ValueError("semantic copy already contains the r10.3 fixture")
    semantics["objects"].extend(_context_objects())
    path.write_text(
        yaml.safe_dump(semantics, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _update_ebench_configs(destination: Path) -> None:
    additions = {
        "obj_glass_rod": {
            "type": "existed_object",
            "uid_list": ["obj_glass_rod"],
        },
        "obj_acrylic_rod_rack": {
            "type": "existed_object",
            "uid_list": ["obj_acrylic_rod_rack"],
        },
    }
    for path in (destination / "ebench/config.yaml", destination / "ebench/tasks/config.yaml"):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        object_config = value["evaluation_configs"][0]["object_config"]
        if set(additions) & set(object_config):
            raise ValueError(f"eBench config already contains r10.3 objects: {path}")
        object_config.update(deepcopy(additions))
        path.write_text(
            yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def _update_ebench_manifest(destination: Path, fixture_package: Path) -> None:
    fixture = _fixture_paths(fixture_package)
    fixture_manifest = json.loads(
        fixture["ebench_manifest"].read_text(encoding="utf-8")
    )
    selected = {
        item["asset_id"]: deepcopy(item)
        for item in fixture_manifest["source_assets"]
        if item.get("asset_id") in FIXTURE_ASSET_IDS
    }
    if set(selected) != set(FIXTURE_ASSET_IDS):
        raise ValueError("fixture source-asset records are incomplete")
    path = destination / "ebench/package_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    retained = [
        item
        for item in manifest["source_assets"]
        if item.get("asset_id") not in FIXTURE_ASSET_IDS
    ]
    for asset_id in FIXTURE_ASSET_IDS:
        record = selected[asset_id]
        canonical = str(record["canonical_usd"])
        if not canonical.startswith("source_bundle/"):
            raise ValueError(f"unexpected fixture canonical USD: {canonical}")
        record["canonical_usd"] = "source_bundle/r7_scene/" + canonical
        retained.append(record)
    manifest["source_assets"] = retained
    manifest["release_status"] = "runtime_validation_pending"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def upgrade_variant(
    source: Path,
    destination: Path,
    *,
    fixture_package: Path = DEFAULT_FIXTURE,
    refresh_preview_request: bool = True,
) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    _copy_fixture_closures(destination, fixture_package)
    _inject_ebench_scene(destination)
    _inject_vr_scene(destination / "vr/scene.usd")
    _update_semantics(destination)
    _update_ebench_configs(destination)
    _update_ebench_manifest(destination, fixture_package)

    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release"] = "r10.3"
    manifest["supersedes"] = "r10.2"
    manifest["status"] = "package_ready_runtime_validation_pending"
    manifest.pop("runtime_gates", None)
    manifest.setdefault("claims", {})["ebench_load_reset_8s"] = "pending"
    manifest["context_fixture"] = {
        "status": "source_bound_composed_runtime_pending",
        "rack_asset_id": RACK_ASSET_ID,
        "rod_asset_id": ROD_ASSET_ID,
        "rack_xyz_m": list(RACK_XYZ),
        "rod_xyz_m": list(ROD_XYZ),
        "metric_participation": "none",
        "vr_randomization_group": FIXTURE_GROUP,
    }
    manifest.setdefault("vr_contract", {}).update(
        {
            "status": "static_pass_runtime_pending",
            "obj_prim_count": 9,
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    config = task02_vr_config(
        scenario_id=str(manifest["scenario_id"]),
        particle_count=int(manifest["particle_count"]),
    )
    for path in (destination / "vr/task_config.py", destination / "vr/config.py"):
        path.write_text(config, encoding="utf-8")
    parity_path = destination / "vr/parity_manifest.json"
    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    parity.update(
        {
            "release": "r10.3",
            "status": "static_pass_runtime_pending",
            "obj_prim_count": 9,
            "fixture_randomization": {
                "objects": ["obj_glass_rod", "obj_acrylic_rod_rack"],
                "mode": "local",
                "xy_offset_m": [-0.01, 0.01],
                "yaw_deg": [0.0, 0.0],
            },
            "robot_physics_overrides": "omitted",
        }
    )
    parity.setdefault("artifacts", {})["scene_usd"] = {
        "path": "scene.usd",
        "sha256": "sha256:" + _sha(destination / "vr/scene.usd"),
    }
    parity["artifacts"]["task_config"] = {
        "path": "task_config.py",
        "sha256": "sha256:" + _sha(destination / "vr/task_config.py"),
    }
    parity_path.write_text(
        json.dumps(parity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    r10_2._remove_stale_runtime_evidence(destination)
    if refresh_preview_request:
        write_genmanip_preview_request(destination / "ebench")
    r8.refresh_hashes(destination)
    return destination


def build_packages(
    *,
    source_root: Path = DEFAULT_SOURCE,
    output_dir: Path = DEFAULT_OUT,
    fixture_package: Path = DEFAULT_FIXTURE,
) -> dict[str, Path]:
    return {
        fill_id: upgrade_variant(
            source_root / fill_id,
            output_dir / "packages" / fill_id,
            fixture_package=fixture_package,
        )
        for fill_id in FILL_IDS
    }


def _write_readme(root: Path, *, status: str) -> None:
    rows = "\n".join(
        f"| `{fill_id}` | `variants/{fill_id}/ebench/scene.usd` | "
        f"`variants/{fill_id}/vr/scene.usd` |"
        for fill_id in FILL_IDS
    )
    root.joinpath("README_CN.md").write_text(
        f"""# Task 02 r10.3 四档液体 + 玻璃棒架

状态：`{status}`。量筒、烧杯、PBD 液体及粒子数沿用 r10.2；新增的透明
亚克力架位于烧杯左侧，300 mm 玻璃棒竖直插在架子中央孔内。两者是背景器材，
不参与 Task 02 metric。

| 档位 | eBench USD | VR USD |
| --- | --- | --- |
{rows}

默认使用 `fill40`。eBench 配置为同目录 `config.yaml`；VR 配置为同目录
`task_config.py`。VR 中架子与玻璃棒按一个整体进行 local XY ±0.01 m 随机化。
本包不声明机器人策略、液体 metric 或 benchmark 成功。
""",
        encoding="utf-8",
    )


def _write_checksums(root: Path) -> None:
    lines = []
    for path in sorted(
        item for item in root.rglob("*") if item.is_file() and item.name != "SHA256SUMS"
    ):
        lines.append(f"{_sha(path)}  {path.relative_to(root).as_posix()}")
    root.joinpath("SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_prevalidation_handoff(
    packages: Mapping[str, Path], *, output_dir: Path = DEFAULT_OUT
) -> Path:
    root = output_dir / "handoff" / PREVALIDATION_ARCHIVE_ID
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
                "archive_id": PREVALIDATION_ARCHIVE_ID,
                "release": "r10.3",
                "status": "package_ready_runtime_validation_pending",
                "default_variant": "fill40",
                "variants": list(FILL_IDS),
                "claim_boundary": (
                    "Portable composition is complete; new Isaac 4.1 runtime and visual "
                    "validation are pending."
                ),
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _write_readme(root, status="package_ready_runtime_validation_pending")
    _write_checksums(root)
    destination = output_dir / "handoff" / f"{PREVALIDATION_ARCHIVE_ID}.zip"
    r10_2._zip_tree(root, destination)
    return destination


def finalize_validated_handoff(
    packages: Mapping[str, Path], *, output_dir: Path = DEFAULT_OUT
) -> Path:
    for package in packages.values():
        r10_2.finalize_validated_package(package)
    overviews = {
        fill_id: package / "ebench/evidence/initial_scene/scene_overview.png"
        for fill_id, package in packages.items()
    }
    if not all(path.is_file() for path in overviews.values()):
        raise ValueError("all four r10.3 scene overview renders are required")
    archive = r10.finalize_r10_handoff(
        packages=packages,
        output_dir=output_dir,
        fill_level_ids=FILL_IDS,
        default_variant="fill40",
        archive_id=ARCHIVE_ID,
        visual_ready="pass",
        overviews=overviews,
    )
    manifest_path = archive.root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "release": "r10.3",
            "status": "runtime_complete_visual_ready",
            "context_fixture": {
                "rack": RACK_ASSET_ID,
                "rod": ROD_ASSET_ID,
                "placement": "left_of_beaker",
                "metric_participation": "none",
            },
        }
    )
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    _write_readme(archive.root, status="runtime_complete_visual_ready")
    _write_checksums(archive.root)
    refresh_usd_handoff_archive(archive)
    return archive.zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--fixture-package", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    packages = {fill_id: args.out / "packages" / fill_id for fill_id in FILL_IDS}
    if args.finalize_existing:
        print(finalize_validated_handoff(packages, output_dir=args.out))
        return 0
    packages = build_packages(
        source_root=args.source_root,
        output_dir=args.out,
        fixture_package=args.fixture_package,
    )
    print(build_prevalidation_handoff(packages, output_dir=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
